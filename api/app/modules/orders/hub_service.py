"""Hub manager views and actions (UC-02 monitoring, H-01, H-03; manual dispatch actions).

Every query is scoped to the manager's hub; another hub's order answers 404.
"""

import logging
import uuid
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_datetime, local_today, utc_now
from app.core.deps import CurrentUser, require_hub
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.pagination import Page, PageParams
from app.modules.delivery.schemas import OrderItemOut, TimelineEventOut
from app.modules.dispatch.models import DispatchOffer, OfferStatus
from app.modules.dispatch.service import offer_manually, pickup_point, rank_candidates
from app.modules.files.models import File
from app.modules.hubs.models import Hub, Shift, ShiftRegistration, ShiftRegistrationStatus
from app.modules.incidents.models import Incident, IncidentPriority, IncidentStatus
from app.modules.incidents.schemas import CandidateOut
from app.modules.orders.hub_schemas import (
    AttemptOut,
    DashboardOut,
    DriverBrief,
    HubDriverRow,
    HubOrderDetail,
    HubOrderRow,
)
from app.modules.orders.models import (
    ActorType,
    AssignmentStatus,
    DeliveryAttempt,
    DeliveryAttemptFile,
    Order,
    OrderEvent,
    OrderStatus,
)
from app.modules.orders.service import (
    ACTIVE_DRIVER_STATUSES,
    FINAL_STATUSES,
    active_assignment,
    lock_order,
    publish_order_update,
)
from app.modules.orders.state_machine import transition
from app.modules.partner.webhooks import STATUS_CHANGED, notify_partner
from app.modules.rbac.models import Role, RoleCode
from app.modules.realtime.hub import notify_user
from app.modules.routing.service import detach_order
from app.modules.settings.service import load_business_settings
from app.modules.users.models import DriverAvailability, DriverProfile, User
from app.worker.jobs import DISPATCH_RUN, enqueue

logger = logging.getLogger(__name__)

OPEN_ORDER_STATUSES = tuple(s for s in OrderStatus if s not in FINAL_STATUSES)
OPEN_INCIDENT_STATUSES = (IncidentStatus.OPEN, IncidentStatus.IN_REVIEW, IncidentStatus.RESOLVING)


def _day_start() -> datetime:
    return local_datetime(local_today(), time(0, 0))


def _at_risk() -> ColumnElement[bool]:
    """Open order whose ETA (or now, without an ETA) is already past the promised time."""
    return and_(
        Order.status.in_(OPEN_ORDER_STATUSES),
        func.coalesce(Order.current_eta, func.now()) > Order.promised_at,
    )


def _on_board(hub_id: uuid.UUID) -> ColumnElement[bool]:
    """Today's board: every open order of the hub plus the ones closed today."""
    return and_(
        Order.hub_id == hub_id,
        or_(Order.status.in_(OPEN_ORDER_STATUSES), Order.updated_at >= _day_start()),
    )


# =============================== Dashboard (H-01, UC-02) ===============================


async def dashboard(session: AsyncSession, hub_id: uuid.UUID) -> DashboardOut:
    settings = await load_business_settings(session)
    grace = timedelta(minutes=settings.sla_grace_min)
    status_rows = await session.execute(
        select(Order.status, func.count()).where(_on_board(hub_id)).group_by(Order.status)
    )
    by_status: dict[str, int] = {status.value: count for status, count in status_rows}
    at_risk = await session.scalar(select(func.count()).where(Order.hub_id == hub_id, _at_risk()))

    delivered, on_time = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(Order.delivered_at <= Order.promised_at + grace),
            ).where(
                Order.hub_id == hub_id,
                Order.status == OrderStatus.DELIVERED,
                Order.delivered_at >= _day_start(),
            )
        )
    ).one()
    open_incidents, high_incidents = (
        await session.execute(
            select(
                func.count(), func.count().filter(Incident.priority == IncidentPriority.HIGH)
            ).where(Incident.hub_id == hub_id, Incident.status.in_(OPEN_INCIDENT_STATUSES))
        )
    ).one()

    on_shift = exists(
        select(ShiftRegistration.id).where(
            ShiftRegistration.driver_id == User.id,
            ShiftRegistration.work_date == local_today(),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
    )
    online, registered = (
        await session.execute(
            select(
                func.count().filter(DriverProfile.availability == DriverAvailability.ONLINE),
                func.count().filter(on_shift),
            )
            .select_from(User)
            .join(DriverProfile, DriverProfile.user_id == User.id)
            .where(User.hub_id == hub_id)
        )
    ).one()

    return DashboardOut(
        date=local_today(),
        total=sum(by_status.values()),
        by_status=by_status,
        at_risk=at_risk or 0,
        delivered_today=delivered,
        on_time_rate_today=round(on_time / delivered, 3) if delivered else None,
        open_incidents=open_incidents,
        high_priority_incidents=high_incidents,
        drivers_online=online,
        drivers_on_shift=registered,
    )


# =============================== Orders ===============================


def _order_rows(hub_id: uuid.UUID) -> Any:
    risk = case((_at_risk(), True), else_=False)
    return (
        select(Order, User.full_name, risk)
        .outerjoin(User, User.id == Order.current_driver_id)
        .where(Order.hub_id == hub_id)
    )


def _row(order: Order, driver_name: str | None, at_risk: bool) -> HubOrderRow:
    return HubOrderRow(
        id=order.id,
        waybill_code=order.waybill_code,
        status=order.status,
        priority=order.priority,
        recipient_name=order.recipient_name,
        delivery_address=order.delivery_address,
        driver_id=order.current_driver_id,
        driver_name=driver_name,
        promised_at=order.promised_at,
        current_eta=order.current_eta,
        at_risk=bool(at_risk),
        has_incident=order.active_incident_id is not None,
        created_at=order.created_at,
    )


async def list_orders(
    session: AsyncSession,
    hub_id: uuid.UUID,
    paging: PageParams,
    *,
    statuses: list[OrderStatus] | None = None,
    risk_only: bool = False,
    q: str | None = None,
    today_only: bool = True,
) -> Page[HubOrderRow]:
    """Order table of UC-02 with the "SLA risk" filter (flow 2a). Risky orders come first."""
    query = _order_rows(hub_id)
    if today_only:
        query = query.where(_on_board(hub_id))
    if statuses:
        query = query.where(Order.status.in_(statuses))
    if risk_only:
        query = query.where(_at_risk())
    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Order.waybill_code).like(pattern),
                func.lower(Order.recipient_name).like(pattern),
                Order.recipient_phone.like(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    risk_first = case((_at_risk(), 0), else_=1)
    rows = await session.execute(
        query.order_by(risk_first, Order.promised_at, Order.id)
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return Page(
        items=[_row(order, name, risk) for order, name, risk in rows],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


async def _driver_brief(session: AsyncSession, driver_id: uuid.UUID | None) -> DriverBrief | None:
    if driver_id is None:
        return None
    user = await session.get(User, driver_id)
    if user is None:
        return None
    profile = await session.get(DriverProfile, driver_id)
    return DriverBrief(
        id=user.id,
        name=user.full_name,
        phone=user.phone,
        lat=profile.last_lat if profile else None,
        lng=profile.last_lng if profile else None,
    )


async def _attempts(session: AsyncSession, order_id: uuid.UUID) -> list[AttemptOut]:
    attempts = await session.scalars(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.order_id == order_id)
        .order_by(DeliveryAttempt.attempted_at)
    )
    result = []
    for attempt in attempts:
        photos = await session.scalars(
            select(File.url)
            .join(DeliveryAttemptFile, DeliveryAttemptFile.file_id == File.id)
            .where(DeliveryAttemptFile.attempt_id == attempt.id)
        )
        result.append(
            AttemptOut(
                outcome=attempt.outcome,
                failure_reason=attempt.failure_reason,
                note=attempt.note,
                attempted_at=attempt.attempted_at,
                photo_urls=list(photos),
            )
        )
    return result


async def order_detail(
    session: AsyncSession, hub_id: uuid.UUID, order_id: uuid.UUID
) -> HubOrderDetail:
    """Order page of the hub (H-02): delivery data, driver position, timeline, attempts."""
    row = (await session.execute(_order_rows(hub_id).where(Order.id == order_id))).first()
    if row is None:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    order, driver_name, risk = row
    hub = await session.get(Hub, hub_id)
    assert hub is not None
    giver = None
    if order.handover_from_driver_id:
        giver = await session.get(User, order.handover_from_driver_id)
    events = await session.scalars(
        select(OrderEvent)
        .where(OrderEvent.order_id == order.id)
        .order_by(OrderEvent.created_at, OrderEvent.id)
    )
    return HubOrderDetail(
        **_row(order, driver_name, risk).model_dump(),
        recipient_phone=order.recipient_phone,
        delivery_lat=order.delivery_lat,
        delivery_lng=order.delivery_lng,
        items=[OrderItemOut(name=str(i["name"]), qty=int(i["qty"])) for i in order.items or []],
        weight_kg=order.weight_kg,
        cod_amount=order.cod_amount,
        eta_is_estimate=order.eta_degraded,
        driver=await _driver_brief(session, order.current_driver_id),
        handover_from=giver.full_name if giver else None,
        incident_id=order.active_incident_id,
        hub_lat=hub.lat,
        hub_lng=hub.lng,
        timeline=[
            TimelineEventOut(
                at=event.created_at,
                type=event.type.value,
                from_status=event.from_status,
                to_status=event.to_status,
                payload=event.payload,
            )
            for event in events
        ],
        attempts=await _attempts(session, order.id),
    )


# =============================== Drivers (H-03) ===============================


async def list_drivers(session: AsyncSession, hub_id: uuid.UUID) -> list[HubDriverRow]:
    """Drivers of the hub with live position, load and today's shift. Online first."""
    active = (
        select(func.count())
        .where(Order.current_driver_id == User.id, Order.status.in_(ACTIVE_DRIVER_STATUSES))
        .correlate(User)
        .scalar_subquery()
    )
    shift = (
        select(func.string_agg(Shift.name, ", "))
        .join(ShiftRegistration, ShiftRegistration.shift_id == Shift.id)
        .where(
            ShiftRegistration.driver_id == User.id,
            ShiftRegistration.work_date == local_today(),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
        .correlate(User)
        .scalar_subquery()
    )
    pending = exists(
        select(DispatchOffer.id).where(
            DispatchOffer.driver_id == User.id, DispatchOffer.status == OfferStatus.PENDING
        )
    )
    online_first = case((DriverProfile.availability == DriverAvailability.ONLINE, 0), else_=1)
    rows = await session.execute(
        select(User, DriverProfile, active, shift, pending)
        .join(Role, Role.id == User.role_id)
        .join(DriverProfile, DriverProfile.user_id == User.id)
        .where(User.hub_id == hub_id, Role.code == RoleCode.DRIVER)
        .order_by(online_first, User.full_name)
    )
    return [
        HubDriverRow(
            id=user.id,
            name=user.full_name,
            phone=user.phone,
            availability=profile.availability,
            last_seen_at=profile.last_seen_at,
            lat=profile.last_lat,
            lng=profile.last_lng,
            active_orders=count or 0,
            shift_today=shift_name,
            has_pending_offer=bool(has_offer),
        )
        for user, profile, count, shift_name, has_offer in rows
    ]


async def order_candidates(
    session: AsyncSession, hub_id: uuid.UUID, order_id: uuid.UUID
) -> list[CandidateOut]:
    """Drivers the order could be offered to (H-07), ranked like automatic dispatch."""
    order = await session.get(Order, order_id)
    if order is None or order.hub_id != hub_id:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    settings = await load_business_settings(session)
    exclude = {order.current_driver_id} if order.current_driver_id else None
    ranked = await rank_candidates(
        session,
        settings,
        hub_id=hub_id,
        origin=await pickup_point(session, order),
        exclude=exclude,
        for_hub=True,
    )
    return [
        CandidateOut(
            driver_id=c.driver_id,
            name=c.full_name,
            phone=c.phone,
            distance_km=c.distance_km,
            active_orders=c.active_orders,
            score=c.score,
            lat=c.lat,
            lng=c.lng,
        )
        for c in ranked
    ]


# =============================== Actions ===============================


async def _hub_order(session: AsyncSession, hub_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = await lock_order(session, order_id)
    if order.hub_id != hub_id:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    return order


def _require_no_incident(order: Order) -> None:
    """Orders of an open incident are handled from the incident screen (H-06)."""
    if order.active_incident_id is not None:
        raise Conflict("Handle this order from its open incident", code="INCIDENT_OPEN")


async def _cancel_pending_offers(session: AsyncSession, order: Order) -> list[uuid.UUID]:
    """Withdraw open offers for the order; returns the drivers who must close their popup."""
    offers = await session.scalars(
        select(DispatchOffer).where(
            DispatchOffer.order_id == order.id, DispatchOffer.status == OfferStatus.PENDING
        )
    )
    drivers = []
    for offer in offers:
        offer.status = OfferStatus.CANCELLED
        drivers.append(offer.driver_id)
    return drivers


async def _notify_withdrawn(drivers: list[uuid.UUID], order: Order) -> None:
    for driver_id in drivers:
        await notify_user(driver_id, "offer.expired", {"order_id": str(order.id)})


async def hold(
    session: AsyncSession, manager: CurrentUser, order_id: uuid.UUID, reason: str
) -> HubOrderDetail:
    """Keep a waiting order at the hub; automatic dispatch skips it until released."""
    hub_id = require_hub(manager)
    order = await _hub_order(session, hub_id, order_id)
    _require_no_incident(order)
    withdrawn = await _cancel_pending_offers(session, order)
    transition(
        session, order, OrderStatus.ON_HOLD, actor_type=ActorType.USER, actor_id=manager.id,
        payload={"reason": reason},
    )  # fmt: skip
    notify_partner(session, order, STATUS_CHANGED, message="Your parcel is kept at the hub.")
    await session.commit()
    await _notify_withdrawn(withdrawn, order)
    await publish_order_update(order)
    return await order_detail(session, hub_id, order.id)


async def release_hold(
    session: AsyncSession, manager: CurrentUser, order_id: uuid.UUID
) -> HubOrderDetail:
    """ON_HOLD -> AWAITING_ASSIGNMENT; a new dispatch cycle starts right away."""
    hub_id = require_hub(manager)
    order = await _hub_order(session, hub_id, order_id)
    transition(
        session, order, OrderStatus.AWAITING_ASSIGNMENT, actor_type=ActorType.USER,
        actor_id=manager.id,
    )  # fmt: skip
    enqueue(session, DISPATCH_RUN, {"order_id": str(order.id)})
    await session.commit()
    await publish_order_update(order)
    return await order_detail(session, hub_id, order.id)


async def reassign(
    session: AsyncSession, manager: CurrentUser, order_id: uuid.UUID, driver_id: uuid.UUID
) -> HubOrderDetail:
    """Offer an order to a driver chosen by the hub (FR-H-01).

    An assigned order is taken back from its driver first. A parcel that is already
    picked up is physically with a driver, so it has to go through an incident (UC-04).
    """
    hub_id = require_hub(manager)
    order = await _hub_order(session, hub_id, order_id)
    _require_no_incident(order)
    if order.status in (OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY):
        raise Conflict(
            "The parcel is with a driver; resolve it through an incident",
            code="INVALID_TRANSITION",
        )
    if order.current_driver_id == driver_id:
        raise ValidationFailed("This driver already has the order", code="DRIVER_NOT_AVAILABLE")

    previous = order.current_driver_id
    if order.status == OrderStatus.ASSIGNED:
        assignment = await active_assignment(session, order.id)
        if assignment is not None:
            assignment.status = AssignmentStatus.REASSIGNED
            assignment.ended_at = utc_now()
            assignment.end_reason = "Reassigned by hub"
        transition(
            session, order, OrderStatus.AWAITING_ASSIGNMENT, actor_type=ActorType.USER,
            actor_id=manager.id, payload={"reason": "Reassigned by hub"},
        )  # fmt: skip
        order.current_driver_id = None
        await detach_order(session, order)
    elif order.status == OrderStatus.ON_HOLD:
        transition(
            session, order, OrderStatus.AWAITING_ASSIGNMENT, actor_type=ActorType.USER,
            actor_id=manager.id,
        )  # fmt: skip
    withdrawn = await _cancel_pending_offers(session, order)
    await session.flush()
    offer = await offer_manually(session, hub_id=hub_id, driver_id=driver_id, orders=[order])
    await session.commit()

    await _notify_withdrawn(withdrawn, order)
    await notify_user(driver_id, "offer.created", {"offer_id": str(offer.id)})
    await publish_order_update(order, extra_user=previous)
    logger.info("[reassign] order=%s from=%s to=%s", order.waybill_code, previous, driver_id)
    return await order_detail(session, hub_id, order.id)


async def confirm_returned(
    session: AsyncSession, manager: CurrentUser, order_id: uuid.UUID
) -> HubOrderDetail:
    """RETURNING -> RETURNED_TO_HUB once the parcel is back on the shelf."""
    hub_id = require_hub(manager)
    order = await _hub_order(session, hub_id, order_id)
    transition(
        session, order, OrderStatus.RETURNED_TO_HUB, actor_type=ActorType.USER, actor_id=manager.id
    )
    notify_partner(session, order, STATUS_CHANGED, message="The parcel is back at the hub.")
    await session.commit()
    await publish_order_update(order)
    return await order_detail(session, hub_id, order.id)
