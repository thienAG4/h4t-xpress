"""Driver order flow (UC-05): offers, today's route, scan, start, deliver, fail, ETA, release.

Rules from the report: BR8 scan before delivery, BR9 start after a valid scan,
BR16 proof photo for a successful delivery, BR17 reason for a failed one, EX4 a driver
may give an order back only before pickup.
"""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_datetime, local_today, parse_hhmm, utc_now
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.modules.delivery.schemas import (
    DeliverIn,
    DriverOrderDetailOut,
    DriverOrderOut,
    EtaIn,
    FailIn,
    OfferOut,
    OrderItemOut,
    RouteOut,
    StopOut,
    TimelineEventOut,
)
from app.modules.dispatch.service import current_offer, offer_order_ids
from app.modules.files.models import File
from app.modules.files.service import require_own_files
from app.modules.hubs.models import Hub
from app.modules.orders.models import (
    ActorType,
    AssignmentStatus,
    AttemptOutcome,
    DeliveryAttempt,
    DeliveryAttemptFile,
    EtaSource,
    Order,
    OrderEvent,
    OrderEventType,
    OrderPriority,
    OrderStatus,
)
from app.modules.orders.service import (
    ACTIVE_DRIVER_STATUSES,
    active_assignment,
    add_event,
    lock_order,
    publish_order_update,
)
from app.modules.orders.state_machine import transition
from app.modules.partner.webhooks import (
    DELIVERED,
    ETA_CHANGED,
    FAILED,
    STATUS_CHANGED,
    notify_partner,
)
from app.modules.reports.service import bump_daily_stat
from app.modules.routing.models import RouteStatus
from app.modules.routing.service import (
    detach_order,
    pending_stops,
    refresh_stop_status,
    today_route,
)
from app.modules.settings.service import load_business_settings
from app.modules.tracking.service import refresh_driver_etas
from app.modules.users.models import DriverProfile, User
from app.worker.jobs import DISPATCH_RUN, RESCHEDULE_RELEASE, enqueue

logger = logging.getLogger(__name__)

RESCHEDULE_RELEASE_TIME = "07:30"


# =============================== Read models ===============================


async def _to_out(session: AsyncSession, order: Order) -> DriverOrderOut:
    handover = None
    if order.handover_from_driver_id:
        giver = await session.get(User, order.handover_from_driver_id)
        handover = giver.full_name if giver else None
    return DriverOrderOut(
        id=order.id,
        waybill_code=order.waybill_code,
        status=order.status,
        priority=order.priority,
        recipient_name=order.recipient_name,
        recipient_phone=order.recipient_phone,
        delivery_address=order.delivery_address,
        delivery_lat=order.delivery_lat,
        delivery_lng=order.delivery_lng,
        items=[OrderItemOut(name=str(i["name"]), qty=int(i["qty"])) for i in order.items or []],
        weight_kg=order.weight_kg,
        cod_amount=order.cod_amount,
        note=order.note,
        promised_at=order.promised_at,
        current_eta=order.current_eta,
        eta_is_estimate=order.eta_degraded,
        handover_from=handover,
        active_incident_id=order.active_incident_id,
    )


async def offer_view(session: AsyncSession, driver_id: uuid.UUID) -> OfferOut | None:
    """The pending offer of the driver (D-06), with what they need to decide quickly."""
    offer = await current_offer(session, driver_id)
    if offer is None:
        return None
    orders = list(await session.scalars(select(Order).where(Order.id.in_(offer_order_ids(offer)))))
    if not orders:
        return None
    hub = await session.get(Hub, orders[0].hub_id)
    giver_id = orders[0].handover_from_driver_id
    giver = await session.get(User, giver_id) if giver_id else None
    pickup = f"Hand-over from {giver.full_name}" if giver else (hub.name if hub else "Hub")
    distance = offer.score_breakdown.get("distance_km")
    return OfferOut(
        id=offer.id,
        expires_at=offer.expires_at,
        seconds_left=max(0, int((offer.expires_at - utc_now()).total_seconds())),
        source=offer.source.value,
        is_rescue=offer.incident_id is not None,
        order_count=len(orders),
        waybill_codes=[order.waybill_code for order in orders],
        pickup_label=pickup,
        delivery_addresses=[order.delivery_address for order in orders],
        distance_km=float(distance) if distance is not None else None,
        priority=(
            OrderPriority.EXPRESS
            if any(order.priority == OrderPriority.EXPRESS for order in orders)
            else OrderPriority.NORMAL
        ),
        cod_total=sum((order.cod_amount for order in orders), Decimal(0)),
    )


async def route_view(session: AsyncSession, driver_id: uuid.UUID) -> RouteOut:
    """Today's work (D-07): parcels still to collect, then stops in delivery order."""
    user = await session.get(User, driver_id)
    profile = await session.get(DriverProfile, driver_id)
    hub = await session.get(Hub, user.hub_id) if user and user.hub_id else None
    orders = list(
        await session.scalars(
            select(Order)
            .where(Order.current_driver_id == driver_id, Order.status.in_(ACTIVE_DRIVER_STATUSES))
            .order_by(Order.promised_at)
        )
    )
    by_stop: dict[uuid.UUID, list[Order]] = {}
    for order in orders:
        if order.route_stop_id:
            by_stop.setdefault(order.route_stop_id, []).append(order)
    stops = []
    for stop in await pending_stops(session, driver_id):
        stop_orders = by_stop.get(stop.id, [])
        if not stop_orders:
            continue
        stops.append(
            StopOut(
                id=stop.id,
                seq=stop.seq,
                status=stop.status,
                address=stop.address,
                lat=stop.lat,
                lng=stop.lng,
                recipient_name=stop.recipient_name,
                recipient_phone=stop.recipient_phone,
                eta=stop.eta,
                orders=[await _to_out(session, order) for order in stop_orders],
            )
        )
    return RouteOut(
        hub_name=hub.name if hub else "",
        hub_lat=hub.lat if hub else 0,
        hub_lng=hub.lng if hub else 0,
        driver_lat=profile.last_lat if profile else None,
        driver_lng=profile.last_lng if profile else None,
        to_pick_up=[await _to_out(session, o) for o in orders if o.status == OrderStatus.ASSIGNED],
        ready_to_start=sum(1 for o in orders if o.status == OrderStatus.PICKED_UP),
        stops=stops,
    )


async def order_detail(
    session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID
) -> DriverOrderDetailOut:
    order = await session.get(Order, order_id)
    if order is None or order.current_driver_id != driver_id:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    events = await session.scalars(
        select(OrderEvent)
        .where(OrderEvent.order_id == order.id)
        .order_by(OrderEvent.created_at, OrderEvent.id)
    )
    base = await _to_out(session, order)
    return DriverOrderDetailOut(
        **base.model_dump(),
        stop_id=order.route_stop_id,
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
    )


async def _own_order(session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = await lock_order(session, order_id)
    if order.current_driver_id != driver_id:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    return order


def _require_status(order: Order, *allowed: OrderStatus) -> None:
    if order.status not in allowed:
        raise Conflict(
            f"Not possible while the order is {order.status.value}",
            code="INVALID_TRANSITION",
            details={"status": order.status.value},
        )


# =============================== Pickup and start (BR8, BR9) ===============================


async def scan(
    session: AsyncSession,
    driver_id: uuid.UUID,
    order_id: uuid.UUID,
    waybill_code: str,
    *,
    lat: float | None,
    lng: float | None,
) -> DriverOrderOut:
    """Confirm the parcel in hand by its waybill (at the hub or at a hand-over)."""
    order = await _own_order(session, driver_id, order_id)
    _require_status(order, OrderStatus.ASSIGNED)
    if waybill_code.strip().upper() != order.waybill_code.upper():
        raise ValidationFailed(
            "This waybill does not match the order", code="WAYBILL_MISMATCH"
        )  # EX4 of process 2
    payload = (
        {"handover_from": str(order.handover_from_driver_id)}
        if order.handover_from_driver_id
        else {}
    )
    transition(
        session,
        order,
        OrderStatus.PICKED_UP,
        actor_type=ActorType.USER,
        actor_id=driver_id,
        payload=payload,
        lat=lat,
        lng=lng,
    )
    notify_partner(session, order, STATUS_CHANGED)
    await session.commit()
    await publish_order_update(order)
    return await _to_out(session, order)


async def start_delivery(session: AsyncSession, driver_id: uuid.UUID) -> int:
    """Leave with every scanned parcel: PICKED_UP -> OUT_FOR_DELIVERY (BR9), ETAs computed."""
    settings = await load_business_settings(session)
    orders = list(
        await session.scalars(
            select(Order)
            .where(Order.current_driver_id == driver_id, Order.status == OrderStatus.PICKED_UP)
            .with_for_update()
        )
    )
    if not orders:
        raise Conflict("Scan at least one parcel before starting", code="NOTHING_TO_START")
    for order in orders:
        transition(
            session,
            order,
            OrderStatus.OUT_FOR_DELIVERY,
            actor_type=ActorType.USER,
            actor_id=driver_id,
        )
    route = await today_route(session, driver_id)
    if route is not None and route.status != RouteStatus.IN_PROGRESS:
        route.status = RouteStatus.IN_PROGRESS
        route.started_at = utc_now()
    await session.flush()
    await refresh_driver_etas(session, driver_id, settings)
    for order in orders:
        notify_partner(session, order, STATUS_CHANGED, message="Your parcel is on its way.")
    await session.commit()
    for order in orders:
        await publish_order_update(order)
    return len(orders)


# =============================== Outcome (BR16, BR17) ===============================


def _attempt(
    session: AsyncSession,
    order: Order,
    driver_id: uuid.UUID,
    outcome: AttemptOutcome,
    *,
    lat: float | None,
    lng: float | None,
    note: str | None,
) -> DeliveryAttempt:
    attempt = DeliveryAttempt(
        id=uuid.uuid4(),
        order_id=order.id,
        driver_id=driver_id,
        outcome=outcome,
        note=note,
        lat=lat,
        lng=lng,
        attempted_at=utc_now(),
    )
    session.add(attempt)
    return attempt


async def _close_assignment(session: AsyncSession, order: Order, reason: str | None = None) -> None:
    assignment = await active_assignment(session, order.id)
    if assignment is not None:
        assignment.status = AssignmentStatus.COMPLETED
        assignment.ended_at = utc_now()
        assignment.end_reason = reason


async def deliver(
    session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID, data: DeliverIn
) -> DriverOrderOut:
    settings = await load_business_settings(session)
    order = await _own_order(session, driver_id, order_id)
    _require_status(order, OrderStatus.OUT_FOR_DELIVERY)
    if not data.photo_file_ids:
        raise ValidationFailed(
            "A photo of the delivered parcel is required", code="EVIDENCE_REQUIRED"
        )
    photos: list[File] = await require_own_files(session, driver_id, data.photo_file_ids)

    attempt = _attempt(
        session,
        order,
        driver_id,
        AttemptOutcome.DELIVERED,
        lat=data.lat,
        lng=data.lng,
        note=data.note,
    )
    await session.flush()
    session.add_all(DeliveryAttemptFile(attempt_id=attempt.id, file_id=p.id) for p in photos)
    transition(
        session,
        order,
        OrderStatus.DELIVERED,
        actor_type=ActorType.USER,
        actor_id=driver_id,
        payload={"photo_file_ids": [str(p.id) for p in photos]},
        lat=data.lat,
        lng=data.lng,
    )
    now = utc_now()
    order.delivered_at = now
    order.current_eta = now
    await _close_assignment(session, order)
    await session.flush()
    if order.route_stop_id:
        await refresh_stop_status(session, order.route_stop_id)
    on_time = now <= order.promised_at + timedelta(minutes=settings.sla_grace_min)
    await bump_daily_stat(session, driver_id, order.hub_id, delivered=1, on_time=int(on_time))
    await refresh_driver_etas(session, driver_id, settings)
    notify_partner(session, order, DELIVERED, proof_url=photos[0].url)
    await session.commit()
    await publish_order_update(order)
    logger.info("[deliver] order=%s driver=%s on_time=%s", order.waybill_code, driver_id, on_time)
    return await _to_out(session, order)


async def fail(
    session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID, data: FailIn
) -> DriverOrderOut:
    """Failed attempt: reschedule when a date is proposed and attempts remain, else return."""
    settings = await load_business_settings(session)
    order = await _own_order(session, driver_id, order_id)
    _require_status(order, OrderStatus.OUT_FOR_DELIVERY)
    today = local_today()
    if data.proposed_date and not today < data.proposed_date <= today + timedelta(days=7):
        raise ValidationFailed(
            "Choose a date within the next 7 days", code="RESCHEDULE_DATE_INVALID"
        )

    attempt = _attempt(
        session, order, driver_id, AttemptOutcome.FAILED, lat=data.lat, lng=data.lng, note=data.note
    )
    attempt.failure_reason = data.reason
    attempt.proposed_reschedule_date = data.proposed_date
    transition(
        session,
        order,
        OrderStatus.DELIVERY_FAILED,
        actor_type=ActorType.USER,
        actor_id=driver_id,
        payload={"reason": data.reason.value, "note": data.note},
        lat=data.lat,
        lng=data.lng,
    )
    order.failed_attempts += 1
    await _close_assignment(session, order, f"Failed: {data.reason.value}")

    if data.proposed_date and order.failed_attempts < settings.max_attempts:
        transition(
            session,
            order,
            OrderStatus.RESCHEDULED,
            actor_type=ActorType.SYSTEM,
            payload={"date": data.proposed_date.isoformat()},
        )
        release_at = local_datetime(data.proposed_date, parse_hhmm(RESCHEDULE_RELEASE_TIME))
        enqueue(session, RESCHEDULE_RELEASE, {"order_id": str(order.id)}, run_at=release_at)
        next_step = f"Rescheduled to {data.proposed_date.isoformat()}"
    else:
        transition(session, order, OrderStatus.RETURNING, actor_type=ActorType.SYSTEM)
        next_step = "Returning to the hub"
    await session.flush()
    if order.route_stop_id:
        await refresh_stop_status(session, order.route_stop_id)
    await bump_daily_stat(session, driver_id, order.hub_id, failed=1)
    await refresh_driver_etas(session, driver_id, settings)
    notify_partner(session, order, FAILED, reason=data.reason.value, message=next_step)
    await session.commit()
    await publish_order_update(order)
    return await _to_out(session, order)


# =============================== ETA and release ===============================


async def update_eta(
    session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID, data: EtaIn
) -> DriverOrderOut:
    """Manual ETA from the driver (D-12). Kept until the driver reaches the stop."""
    settings = await load_business_settings(session)
    order = await _own_order(session, driver_id, order_id)
    _require_status(order, *ACTIVE_DRIVER_STATUSES)
    if data.eta <= utc_now():
        raise ValidationFailed("The new ETA must be in the future", code="ETA_IN_PAST")
    previous = order.current_eta
    order.current_eta = data.eta
    order.eta_source = EtaSource.MANUAL
    order.eta_degraded = False
    add_event(
        session,
        order,
        OrderEventType.ETA_CHANGED,
        actor_type=ActorType.USER,
        actor_id=driver_id,
        payload={"eta": data.eta.isoformat(), "reason": data.reason, "source": "MANUAL"},
    )
    moved = (
        previous is None
        or abs((data.eta - previous).total_seconds()) >= settings.notify_threshold_min * 60
    )
    if moved:
        notify_partner(session, order, ETA_CHANGED, message=data.reason)
    await session.commit()
    await publish_order_update(order)
    return await _to_out(session, order)


async def release(
    session: AsyncSession, driver_id: uuid.UUID, order_id: uuid.UUID, reason: str
) -> None:
    """EX4: give an order back before pickup; dispatch looks for another driver."""
    order = await _own_order(session, driver_id, order_id)
    _require_status(order, OrderStatus.ASSIGNED)
    assignment = await active_assignment(session, order.id)
    if assignment is not None:
        assignment.status = AssignmentStatus.RELEASED
        assignment.ended_at = utc_now()
        assignment.end_reason = reason
    transition(
        session,
        order,
        OrderStatus.AWAITING_ASSIGNMENT,
        actor_type=ActorType.USER,
        actor_id=driver_id,
        payload={"reason": reason},
    )
    order.current_driver_id = None
    order.current_eta = None
    await detach_order(session, order)
    enqueue(session, DISPATCH_RUN, {"order_id": str(order.id)})
    notify_partner(session, order, STATUS_CHANGED, message="We are assigning another driver.")
    await session.commit()
    await publish_order_update(order, extra_user=driver_id)


async def release_reschedule(session: AsyncSession, order_id: uuid.UUID) -> bool:
    """Job handler: on the agreed day the order goes back to dispatch."""
    order = await lock_order(session, order_id)
    if order.status != OrderStatus.RESCHEDULED:
        return False
    transition(session, order, OrderStatus.AWAITING_ASSIGNMENT, actor_type=ActorType.SYSTEM)
    order.current_driver_id = None
    order.current_eta = None
    order.route_stop_id = None
    order.handover_from_driver_id = None
    enqueue(session, DISPATCH_RUN, {"order_id": str(order.id)})
    notify_partner(session, order, STATUS_CHANGED, message="Delivery is scheduled for today.")
    await session.commit()
    await publish_order_update(order)
    return True
