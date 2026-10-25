"""ShopNow simulator (S-01, S-02): an e-commerce partner living next to H4T for the demo.

Orders go through the same partner service and validation as the public partner API.
ShopNow only knows what it sent and what H4T webhooks told it.
"""

import hmac
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, utc_now
from app.core.config import get_settings
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import Page, PageParams
from app.core.security import sign_webhook
from app.modules.orders.models import Order
from app.modules.partner import service as partner_service
from app.modules.partner.models import Partner
from app.modules.partner.schemas import PartnerOrderIn, PartnerOrderOut
from app.modules.sim import generator
from app.modules.sim.models import SimShopnowOrder, SimShopnowWebhook
from app.modules.sim.schemas import ManualOrderIn, RandomOrdersIn, SimOrderOut, SimWebhookOut
from app.seed import catalog

logger = logging.getLogger(__name__)

SHOPNOW_CODE = "SHOPNOW"
SIGNATURE_HEADER = "X-H4T-Signature"


# =============================== Helpers ===============================


async def _shopnow(session: AsyncSession) -> Partner:
    partner = await session.scalar(select(Partner).where(Partner.code == SHOPNOW_CODE))
    if partner is None:
        raise NotFound("ShopNow partner is not seeded", code="PARTNER_NOT_FOUND")
    return partner


def _ensure_hub(hub_code: str) -> None:
    if hub_code not in {hub.code for hub in catalog.HUBS}:
        raise ValidationFailed("Unknown hub_code", code="HUB_NOT_FOUND", details=[hub_code])


async def _next_waybills(session: AsyncSession, count: int) -> list[str]:
    """Waybills follow the seed format SN<yymmdd><5-digit sequence>."""
    prefix = f"SN{local_today():%y%m%d}"
    last = await session.scalar(
        select(func.max(Order.waybill_code)).where(Order.waybill_code.like(f"{prefix}%"))
    )
    start = int(last[len(prefix) :]) + 1 if last else 1
    return [f"{prefix}{start + index:05d}" for index in range(count)]


def _json_payload(order: PartnerOrderIn) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    return {key: convert(value) for key, value in order.model_dump(mode="python").items()}


async def _submit(session: AsyncSession, partner: Partner, order: PartnerOrderIn) -> SimOrderOut:
    created: PartnerOrderOut = await partner_service.create_order(session, partner, order)
    record = SimShopnowOrder(
        waybill_code=created.waybill_code,
        partner_order_ref=order.partner_order_ref or created.waybill_code,
        payload=_json_payload(order),
        last_status=created.status.value,
        last_event_at=created.created_at,
    )
    session.add(record)
    await session.commit()
    return _to_out(record)


def _to_out(record: SimShopnowOrder) -> SimOrderOut:
    payload = record.payload
    return SimOrderOut(
        waybill_code=record.waybill_code,
        partner_order_ref=record.partner_order_ref,
        hub_code=payload.get("hub_code", ""),
        recipient_name=payload.get("recipient_name", ""),
        delivery_address=payload.get("delivery_address", ""),
        priority=payload.get("priority", "NORMAL"),
        promised_at=datetime.fromisoformat(payload["promised_at"]),
        last_status=record.last_status,
        current_eta=record.current_eta,
        last_event_at=record.last_event_at,
        created_at=record.created_at,
    )


# =============================== Orders ===============================


async def create_random_orders(session: AsyncSession, data: RandomOrdersIn) -> list[SimOrderOut]:
    _ensure_hub(data.hub_code)
    partner = await _shopnow(session)
    waybills = await _next_waybills(session, data.count)
    created = []
    for waybill in waybills:
        order = generator.random_order(
            data.hub_code, waybill, express=generator.is_express(data.express_ratio)
        )
        created.append(await _submit(session, partner, order))
    logger.info("[create_random_orders] hub=%s count=%d", data.hub_code, len(created))
    return created


async def create_manual_order(session: AsyncSession, data: ManualOrderIn) -> SimOrderOut:
    _ensure_hub(data.hub_code)
    partner = await _shopnow(session)
    template = generator.random_order(
        data.hub_code, (await _next_waybills(session, 1))[0], express=False
    )
    order = template.model_copy(
        update={
            "recipient_name": data.recipient_name,
            "recipient_phone": data.recipient_phone,
            "delivery_address": data.delivery_address,
            "delivery_lat": data.delivery_lat or template.delivery_lat,
            "delivery_lng": data.delivery_lng or template.delivery_lng,
            "weight_kg": data.weight_kg,
            "cod_amount": data.cod_amount,
            "items": data.items,
            "priority": data.priority,
            "promised_at": utc_now() + timedelta(hours=data.promised_in_hours),
        }
    )
    return await _submit(session, partner, order)


async def list_orders(session: AsyncSession, paging: PageParams) -> Page[SimOrderOut]:
    total = await session.scalar(select(func.count()).select_from(SimShopnowOrder)) or 0
    rows = await session.scalars(
        select(SimShopnowOrder)
        .order_by(SimShopnowOrder.created_at.desc(), SimShopnowOrder.waybill_code.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return Page(
        items=[_to_out(r) for r in rows], total=total, page=paging.page, page_size=paging.page_size
    )


async def cancel_order(session: AsyncSession, waybill_code: str) -> SimOrderOut:
    partner = await _shopnow(session)
    record = await session.scalar(
        select(SimShopnowOrder).where(SimShopnowOrder.waybill_code == waybill_code)
    )
    if record is None:
        raise NotFound("Order not found in ShopNow", code="ORDER_NOT_FOUND")
    result = await partner_service.cancel_order(
        session, partner, waybill_code, "Cancelled by buyer on ShopNow"
    )
    # ShopNow knows the outcome of its own API call even before any webhook arrives.
    record.last_status = result.status.value
    record.last_event_at = utc_now()
    await session.commit()
    return _to_out(record)


# =============================== Webhooks ===============================


async def receive_webhook(
    session: AsyncSession, body: bytes, signature: str | None
) -> SimWebhookOut:
    """Store a webhook from H4T and update ShopNow's view of the order (BR10)."""
    expected = sign_webhook(body, get_settings().shopnow_webhook_secret)
    valid = signature is not None and hmac.compare_digest(signature, expected)
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise ValidationFailed("Body must be JSON", code="INVALID_JSON") from exc
    waybill = payload.get("waybill_code")
    webhook = SimShopnowWebhook(
        event_type=str(payload.get("event", "unknown")),
        waybill_code=waybill,
        payload=payload,
        signature_valid=valid,
        received_at=utc_now(),
    )
    session.add(webhook)
    if valid and waybill:
        record = await session.scalar(
            select(SimShopnowOrder).where(SimShopnowOrder.waybill_code == waybill)
        )
        if record is not None:
            record.last_status = payload.get("status", record.last_status)
            if payload.get("eta"):
                record.current_eta = datetime.fromisoformat(payload["eta"])
            record.last_event_at = utc_now()
    await session.commit()
    return SimWebhookOut.model_validate(webhook, from_attributes=True)


async def list_webhooks(
    session: AsyncSession, paging: PageParams, waybill_code: str | None
) -> Page[SimWebhookOut]:
    query = select(SimShopnowWebhook)
    if waybill_code:
        query = query.where(SimShopnowWebhook.waybill_code == waybill_code)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.scalars(
        query.order_by(SimShopnowWebhook.received_at.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return Page(
        items=[SimWebhookOut.model_validate(r, from_attributes=True) for r in rows],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )
