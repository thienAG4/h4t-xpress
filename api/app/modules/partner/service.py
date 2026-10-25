"""Partner integration: inbound order API (FR-S-01..03) and outbound webhook outbox (BR10).

Webhooks are written to `webhook_deliveries` in the same transaction as the change
(transactional outbox). The background sender arrives with the worker in Phase 2.
"""

import logging
import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import Conflict, NotFound, Unauthorized, ValidationFailed
from app.core.security import hash_token
from app.modules.hubs.models import Area, Hub, HubStatus
from app.modules.orders.models import (
    ActorType,
    Assignment,
    AssignmentStatus,
    Order,
    OrderEvent,
    OrderEventType,
    OrderStatus,
)
from app.modules.orders.state_machine import transition
from app.modules.partner.models import Partner, PartnerStatus, WebhookDelivery
from app.modules.partner.schemas import (
    PartnerDriverOut,
    PartnerEventOut,
    PartnerOrderIn,
    PartnerOrderOut,
)
from app.modules.users.models import User

logger = logging.getLogger(__name__)

CANCELLABLE = {OrderStatus.AWAITING_ASSIGNMENT, OrderStatus.ON_HOLD, OrderStatus.ASSIGNED}


# =============================== Authentication ===============================


async def authenticate_partner(session: AsyncSession, api_key: str | None) -> Partner:
    if not api_key:
        raise Unauthorized("Missing X-API-Key header", code="API_KEY_MISSING")
    partner = await session.scalar(
        select(Partner).where(Partner.api_key_hash == hash_token(api_key))
    )
    if partner is None or partner.status != PartnerStatus.ACTIVE:
        raise Unauthorized("Invalid API key", code="API_KEY_INVALID")
    return partner


# =============================== Webhook outbox ===============================


def enqueue_webhook(
    session: AsyncSession, partner_id: uuid.UUID, event_type: str, payload: dict[str, Any]
) -> None:
    """Queue a webhook in the caller's transaction (sent by the worker, SPEC §3.7)."""
    session.add(
        WebhookDelivery(
            partner_id=partner_id,
            event_type=event_type,
            payload={"event": event_type, "sent_at": utc_now().isoformat(), **payload},
            next_attempt_at=utc_now(),
        )
    )


# =============================== Orders ===============================


async def _nearest_area(session: AsyncSession, lat: float, lng: float) -> uuid.UUID | None:
    """Area whose radius contains the point, nearest centre first (None when outside all)."""
    best: tuple[float, uuid.UUID] | None = None
    for area in await session.scalars(select(Area)):
        d_lat = (lat - area.center_lat) * 111.0
        d_lng = (lng - area.center_lng) * 111.0 * math.cos(math.radians(lat))
        distance = math.hypot(d_lat, d_lng)
        if distance <= area.radius_km and (best is None or distance < best[0]):
            best = (distance, area.id)
    return best[1] if best else None


async def create_order(
    session: AsyncSession, partner: Partner, data: PartnerOrderIn
) -> PartnerOrderOut:
    """Validate and store a new order in AWAITING_ASSIGNMENT (BR1-BR2 of process 2)."""
    hub = await session.scalar(select(Hub).where(Hub.code == data.hub_code))
    if hub is None or hub.status != HubStatus.ACTIVE:
        raise ValidationFailed("Unknown hub_code", code="HUB_NOT_FOUND", details=[data.hub_code])
    if data.promised_at <= utc_now():
        raise ValidationFailed("promised_at must be in the future", code="PROMISE_IN_PAST")
    duplicate = await session.scalar(
        select(Order.id).where(
            Order.partner_id == partner.id, Order.waybill_code == data.waybill_code
        )
    )
    if duplicate:
        raise Conflict("This waybill was already received", code="DUPLICATE_WAYBILL")

    order = Order(
        partner_id=partner.id,
        waybill_code=data.waybill_code,
        partner_order_ref=data.partner_order_ref,
        hub_id=hub.id,
        status=OrderStatus.AWAITING_ASSIGNMENT,
        priority=data.priority,
        recipient_name=data.recipient_name.strip(),
        recipient_phone=data.recipient_phone,
        delivery_address=data.delivery_address.strip(),
        delivery_lat=data.delivery_lat,
        delivery_lng=data.delivery_lng,
        delivery_area_id=await _nearest_area(session, data.delivery_lat, data.delivery_lng),
        weight_kg=data.weight_kg,
        length_cm=data.length_cm,
        width_cm=data.width_cm,
        height_cm=data.height_cm,
        cod_amount=data.cod_amount,
        items=[item.model_dump() for item in data.items],
        note=data.note,
        promised_at=data.promised_at,
    )
    session.add(order)
    await session.flush()
    session.add(
        OrderEvent(
            order_id=order.id,
            type=OrderEventType.STATUS_CHANGED,
            from_status=None,
            to_status=OrderStatus.AWAITING_ASSIGNMENT,
            actor_type=ActorType.PARTNER,
            payload={"partner": partner.code},
        )
    )
    await session.commit()
    logger.info(
        "[create_order] partner=%s waybill=%s hub=%s", partner.code, order.waybill_code, hub.code
    )
    return await get_order(session, partner, order.waybill_code)


async def _load_order(session: AsyncSession, partner: Partner, waybill_code: str) -> Order:
    order = await session.scalar(
        select(Order).where(Order.partner_id == partner.id, Order.waybill_code == waybill_code)
    )
    if order is None:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    return order


async def get_order(session: AsyncSession, partner: Partner, waybill_code: str) -> PartnerOrderOut:
    """Status, ETA, assigned driver and timeline as the partner is allowed to see them."""
    order = await _load_order(session, partner, waybill_code)
    hub_code = await session.scalar(select(Hub.code).where(Hub.id == order.hub_id))
    driver = None
    if order.current_driver_id and order.status not in (
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNED_TO_HUB,
    ):
        user = await session.get(User, order.current_driver_id)
        driver = PartnerDriverOut(name=user.full_name, phone=user.phone) if user else None
    events = await session.scalars(
        select(OrderEvent)
        .where(OrderEvent.order_id == order.id)
        .order_by(OrderEvent.created_at, OrderEvent.id)
    )
    return PartnerOrderOut(
        waybill_code=order.waybill_code,
        partner_order_ref=order.partner_order_ref,
        hub_code=hub_code or "",
        status=order.status,
        promised_at=order.promised_at,
        current_eta=order.current_eta,
        driver=driver,
        created_at=order.created_at,
        timeline=[
            PartnerEventOut(
                at=e.created_at, type=e.type, from_status=e.from_status, to_status=e.to_status
            )
            for e in events
        ],
    )


async def cancel_order(
    session: AsyncSession, partner: Partner, waybill_code: str, reason: str
) -> PartnerOrderOut:
    """Cancel before pickup only (SPEC §3.7). Releases the driver if one was assigned."""
    order = await _load_order(session, partner, waybill_code)
    if order.status not in CANCELLABLE:
        raise Conflict(
            "The order can no longer be cancelled",
            code="CANCEL_NOT_ALLOWED",
            details={"status": order.status},
        )
    active = await session.scalar(
        select(Assignment).where(
            Assignment.order_id == order.id, Assignment.status == AssignmentStatus.ACTIVE
        )
    )
    if active:
        active.status = AssignmentStatus.RELEASED
        active.ended_at = utc_now()
        active.end_reason = "Cancelled by partner"
    transition(
        session,
        order,
        OrderStatus.CANCELLED,
        actor_type=ActorType.PARTNER,
        payload={"reason": reason},
    )
    order.cancelled_at = utc_now()
    order.current_driver_id = None
    enqueue_webhook(
        session,
        partner.id,
        "order.status_changed",
        {
            "waybill_code": order.waybill_code,
            "status": OrderStatus.CANCELLED.value,
            "reason": reason,
        },
    )
    await session.commit()
    return await get_order(session, partner, waybill_code)
