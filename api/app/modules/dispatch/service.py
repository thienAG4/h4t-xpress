"""Automatic driver assignment and offer handling (SPEC §3.2: BR4-BR8, EX1-EX4).

One dispatch run looks at a single order:
1. an offer is already waiting for an answer      -> nothing to do (BR6)
2. the current round still has untried candidates  -> offer the best one
3. the round is used up                            -> new round after a delay, or ON_HOLD
   after `max_rounds` rounds (EX3)
Rounds only count offers made since the order last entered AWAITING_ASSIGNMENT, so a
released hold, a reschedule or a reassignment starts a fresh cycle.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_datetime, local_now, local_today, utc_now
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.geo import haversine_km
from app.modules.dispatch.models import DispatchOffer, OfferSource, OfferStatus
from app.modules.hubs.models import Hub, Shift, ShiftRegistration, ShiftRegistrationStatus
from app.modules.incidents.models import (
    Incident,
    IncidentResolution,
    IncidentStatus,
    ResolutionStatus,
)
from app.modules.orders.models import (
    ActorType,
    Assignment,
    Order,
    OrderEvent,
    OrderPriority,
    OrderStatus,
)
from app.modules.orders.service import ACTIVE_DRIVER_STATUSES, lock_order, publish_order_update
from app.modules.orders.state_machine import transition
from app.modules.partner.webhooks import DRIVER_ASSIGNED, STATUS_CHANGED, notify_partner
from app.modules.rbac.models import Role, RoleCode
from app.modules.realtime.hub import notify_hub, notify_user
from app.modules.reports.models import DailyDriverStat
from app.modules.reports.service import bump_daily_stat
from app.modules.routing.service import attach_order
from app.modules.settings.service import BusinessSettings, load_business_settings
from app.modules.tracking.service import driver_position, refresh_driver_etas
from app.modules.users.models import DriverAvailability, DriverProfile, User, UserStatus
from app.worker.jobs import DISPATCH_RUN, OFFER_TIMEOUT, enqueue, has_pending

logger = logging.getLogger(__name__)

DEFAULT_PERFORMANCE = 0.8
JOB_MINUTES = 60  # rough length of one delivery job, for the time-fit score


@dataclass
class Candidate:
    driver_id: uuid.UUID
    full_name: str
    phone: str | None
    lat: float | None
    lng: float | None
    distance_km: float
    active_orders: int
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)


# =============================== Candidates (BR4, BR5) ===============================


async def _performance(
    session: AsyncSession, driver_ids: list[uuid.UUID]
) -> dict[uuid.UUID, float]:
    """0.7 x on-time rate + 0.3 x (1 - incident rate) over the last 30 days."""
    since = local_today() - timedelta(days=30)
    rows = await session.execute(
        select(
            DailyDriverStat.driver_id,
            func.sum(DailyDriverStat.delivered),
            func.sum(DailyDriverStat.on_time),
            func.sum(DailyDriverStat.assigned),
            func.sum(DailyDriverStat.incidents),
        )
        .where(DailyDriverStat.driver_id.in_(driver_ids), DailyDriverStat.date >= since)
        .group_by(DailyDriverStat.driver_id)
    )
    result: dict[uuid.UUID, float] = {}
    for driver_id, delivered, on_time, assigned, incidents in rows:
        if not delivered or not assigned:
            continue
        on_time_rate = (on_time or 0) / delivered
        incident_rate = min(1.0, (incidents or 0) / assigned)
        result[driver_id] = 0.7 * on_time_rate + 0.3 * (1 - incident_rate)
    return result


async def _active_counts(
    session: AsyncSession, driver_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    rows = await session.execute(
        select(Order.current_driver_id, func.count())
        .where(Order.current_driver_id.in_(driver_ids), Order.status.in_(ACTIVE_DRIVER_STATUSES))
        .group_by(Order.current_driver_id)
    )
    return {driver_id: count for driver_id, count in rows if driver_id}


async def _minutes_left_in_shift(
    session: AsyncSession, driver_ids: list[uuid.UUID]
) -> dict[uuid.UUID, float]:
    rows = await session.execute(
        select(ShiftRegistration.driver_id, func.max(Shift.end_time))
        .join(Shift, Shift.id == ShiftRegistration.shift_id)
        .where(
            ShiftRegistration.driver_id.in_(driver_ids),
            ShiftRegistration.work_date == local_today(),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
        .group_by(ShiftRegistration.driver_id)
    )
    now = local_now()
    return {
        driver_id: (local_datetime(now.date(), end) - now).total_seconds() / 60
        for driver_id, end in rows
    }


async def rank_candidates(
    session: AsyncSession,
    settings: BusinessSettings,
    *,
    hub_id: uuid.UUID,
    origin: tuple[float, float],
    exclude: set[uuid.UUID] | None = None,
    for_hub: bool = False,
) -> list[Candidate]:
    """Eligible drivers of the hub, best first.

    Eligible (BR4): active driver account of this hub, ONLINE, app seen recently,
    registered for a shift today (inside its hours when enforced), no other pending
    offer, below the active-order limit. For a hub decision (`for_hub`) a pending
    automatic offer does not count: the manual offer replaces it.
    """
    now = utc_now()
    shift_condition = and_(
        ShiftRegistration.driver_id == User.id,
        ShiftRegistration.work_date == local_today(),
        ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
    )
    if settings.enforce_shift_hours:
        now_time = local_now().time()
        shift_condition = and_(
            shift_condition, Shift.start_time <= now_time, Shift.end_time > now_time
        )
    in_shift = exists(
        select(ShiftRegistration.id)
        .join(Shift, Shift.id == ShiftRegistration.shift_id)
        .where(shift_condition)
    )
    busy_sources = [OfferSource.MANUAL] if for_hub else [OfferSource.MANUAL, OfferSource.AUTO]
    has_pending_offer = exists(
        select(DispatchOffer.id).where(
            DispatchOffer.driver_id == User.id,
            DispatchOffer.status == OfferStatus.PENDING,
            DispatchOffer.source.in_(busy_sources),
        )
    )
    rows = (
        await session.execute(
            select(User, DriverProfile)
            .join(Role, Role.id == User.role_id)
            .join(DriverProfile, DriverProfile.user_id == User.id)
            .where(
                Role.code == RoleCode.DRIVER,
                User.status == UserStatus.ACTIVE,
                User.hub_id == hub_id,
                DriverProfile.availability == DriverAvailability.ONLINE,
                DriverProfile.last_seen_at >= now - timedelta(minutes=settings.location_fresh_min),
                in_shift,
                ~has_pending_offer,
            )
        )
    ).all()
    pairs = [(user, profile) for user, profile in rows if user.id not in (exclude or set())]
    if not pairs:
        return []

    ids = [user.id for user, _ in pairs]
    counts = await _active_counts(session, ids)
    performance = await _performance(session, ids)
    minutes_left = (
        await _minutes_left_in_shift(session, ids) if settings.enforce_shift_hours else {}
    )
    weights = settings.weights

    candidates: list[Candidate] = []
    for user, profile in pairs:
        active = counts.get(user.id, 0)
        if active >= settings.max_active_orders:
            continue
        if profile.last_lat is not None and profile.last_lng is not None:
            distance = haversine_km(profile.last_lat, profile.last_lng, *origin)
        else:
            distance = settings.max_distance_km / 2  # unknown position: neutral score
        breakdown = {
            "distance": max(0.0, 1 - distance / settings.max_distance_km),
            "load": 1 - active / settings.max_active_orders,
            "performance": performance.get(user.id, DEFAULT_PERFORMANCE),
            "time_fit": (
                min(1.0, max(0.0, minutes_left.get(user.id, 0) / JOB_MINUTES))
                if settings.enforce_shift_hours
                else 1.0
            ),
        }
        score = 100 * sum(weights.get(key, 0) * value for key, value in breakdown.items())
        candidates.append(
            Candidate(
                driver_id=user.id,
                full_name=user.full_name,
                phone=user.phone,
                lat=profile.last_lat,
                lng=profile.last_lng,
                distance_km=round(distance, 2),
                active_orders=active,
                score=round(score, 2),
                breakdown={key: round(value, 3) for key, value in breakdown.items()},
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.distance_km))
    return candidates


async def pickup_point(session: AsyncSession, order: Order) -> tuple[float, float]:
    """Where the next driver collects the parcel: the hub, or the previous driver (hand-over)."""
    hub = await session.get(Hub, order.hub_id)
    hub_point = (hub.lat, hub.lng) if hub else (order.delivery_lat, order.delivery_lng)
    if order.handover_from_driver_id:
        return await driver_position(session, order.handover_from_driver_id, hub_point)
    return hub_point


# =============================== Dispatch run (BR6-BR8, EX2, EX3) ===============================


def _pending_offer_for(order_id: uuid.UUID) -> Any:
    """SQL condition: a pending offer covers this order, alone or inside a rescue bundle."""
    return and_(
        DispatchOffer.status == OfferStatus.PENDING,
        or_(
            DispatchOffer.order_id == order_id,
            DispatchOffer.bundle_order_ids.contains([str(order_id)]),
        ),
    )


async def _cycle_start(session: AsyncSession, order: Order) -> datetime:
    """When the order last (re)entered AWAITING_ASSIGNMENT."""
    started = await session.scalar(
        select(func.max(OrderEvent.created_at)).where(
            OrderEvent.order_id == order.id,
            OrderEvent.to_status == OrderStatus.AWAITING_ASSIGNMENT,
        )
    )
    return started or order.created_at


async def run_dispatch(session: AsyncSession, order_id: uuid.UUID) -> str:
    """Make the next offer for one order. Returns what happened (for logs and tests)."""
    settings = await load_business_settings(session)
    order = await lock_order(session, order_id)
    if order.status != OrderStatus.AWAITING_ASSIGNMENT:
        return "not_awaiting"
    if order.active_incident_id is not None:
        return "incident_open"  # the hub picks the replacement driver (UC-04)
    if await session.scalar(select(DispatchOffer.id).where(_pending_offer_for(order.id)).limit(1)):
        return "waiting_for_answer"

    since = await _cycle_start(session, order)
    offers = list(
        await session.scalars(
            select(DispatchOffer).where(
                DispatchOffer.order_id == order.id,
                DispatchOffer.source == OfferSource.AUTO,
                DispatchOffer.offered_at >= since,
            )
        )
    )
    current_round = max((offer.round for offer in offers), default=0)
    origin = await pickup_point(session, order)
    now = utc_now()

    if current_round > 0:
        tried = {offer.driver_id for offer in offers if offer.round == current_round}
        if len(tried) < settings.max_candidates_per_round:
            candidates = await rank_candidates(
                session, settings, hub_id=order.hub_id, origin=origin, exclude=tried
            )
            if candidates:
                return await _make_offer(
                    session, settings, order, candidates[0], current_round, len(tried) + 1
                )
        if current_round >= settings.max_rounds:
            await _hold(session, order, f"No driver accepted after {current_round} rounds")
            return "on_hold"
        last_activity = max(offer.responded_at or offer.expires_at for offer in offers)
        next_round_at = last_activity + timedelta(seconds=settings.round_retry_delay_s)
        if now < next_round_at:
            enqueue(session, DISPATCH_RUN, {"order_id": str(order.id)}, run_at=next_round_at)
            await session.commit()
            return "next_round_scheduled"

    candidates = await rank_candidates(session, settings, hub_id=order.hub_id, origin=origin)
    if not candidates:
        # EX2: nobody available right now; try again later without using up a round.
        enqueue(
            session,
            DISPATCH_RUN,
            {"order_id": str(order.id)},
            run_at=now + timedelta(seconds=settings.round_retry_delay_s),
        )
        await session.commit()
        return "no_driver"
    return await _make_offer(session, settings, order, candidates[0], current_round + 1, 1)


async def _make_offer(
    session: AsyncSession,
    settings: BusinessSettings,
    order: Order,
    candidate: Candidate,
    round_no: int,
    rank: int,
    *,
    source: OfferSource = OfferSource.AUTO,
    bundle: list[uuid.UUID] | None = None,
    incident_id: uuid.UUID | None = None,
) -> str:
    now = utc_now()
    offer = DispatchOffer(
        order_id=order.id,
        driver_id=candidate.driver_id,
        round=round_no,
        rank=rank,
        score=Decimal(str(candidate.score)),
        score_breakdown={**candidate.breakdown, "distance_km": candidate.distance_km},
        source=source,
        status=OfferStatus.PENDING,
        offered_at=now,
        expires_at=now + timedelta(seconds=settings.offer_timeout_s),
        bundle_order_ids=[str(order_id) for order_id in bundle or []],
        incident_id=incident_id,
    )
    session.add(offer)
    try:
        await session.flush()
    except IntegrityError:
        # The driver received another offer at the same moment (one pending per driver).
        await session.rollback()
        retry = utc_now() + timedelta(seconds=5)
        enqueue(session, DISPATCH_RUN, {"order_id": str(order.id)}, run_at=retry)
        await session.commit()
        return "driver_busy"
    enqueue(session, OFFER_TIMEOUT, {"offer_id": str(offer.id)}, run_at=offer.expires_at)
    await session.commit()
    logger.info(
        "[make_offer] order=%s driver=%s round=%d rank=%d score=%.1f",
        order.waybill_code, candidate.driver_id, round_no, rank, candidate.score,
    )  # fmt: skip
    await notify_user(candidate.driver_id, "offer.created", {"offer_id": str(offer.id)})
    return "offered"


async def _hold(session: AsyncSession, order: Order, reason: str) -> None:
    """EX3: nobody accepted; the hub decides what to do with the order."""
    transition(
        session, order, OrderStatus.ON_HOLD, actor_type=ActorType.SYSTEM, payload={"reason": reason}
    )
    notify_partner(
        session,
        order,
        STATUS_CHANGED,
        message="Delivery is delayed, a driver will be assigned soon.",
    )
    await session.commit()
    await notify_hub(order.hub_id, "order.on_hold", {"order_id": str(order.id), "reason": reason})
    await publish_order_update(order)


# =============================== Offers (driver side) ===============================


async def current_offer(session: AsyncSession, driver_id: uuid.UUID) -> DispatchOffer | None:
    return await session.scalar(
        select(DispatchOffer).where(
            DispatchOffer.driver_id == driver_id,
            DispatchOffer.status == OfferStatus.PENDING,
            DispatchOffer.expires_at > utc_now(),
        )
    )


def offer_order_ids(offer: DispatchOffer) -> list[uuid.UUID]:
    if offer.bundle_order_ids:
        return [uuid.UUID(str(order_id)) for order_id in offer.bundle_order_ids]
    return [offer.order_id]


async def _lock_offer(session: AsyncSession, offer_id: uuid.UUID) -> DispatchOffer:
    offer = await session.scalar(
        select(DispatchOffer).where(DispatchOffer.id == offer_id).with_for_update()
    )
    if offer is None:
        raise NotFound("Offer not found", code="OFFER_NOT_FOUND")
    return offer


async def _requeue_orders(session: AsyncSession, offer: DispatchOffer) -> None:
    """Automatic offers move on to the next driver; a failed rescue goes back to the hub."""
    if offer.incident_id is not None:
        return
    for order_id in offer_order_ids(offer):
        enqueue(session, DISPATCH_RUN, {"order_id": str(order_id)})


async def _rescue_failed(session: AsyncSession, offer: DispatchOffer) -> Incident | None:
    """A hub rescue offer was declined or expired: the incident goes back to review."""
    if offer.incident_id is None:
        return None
    incident = await session.get(Incident, offer.incident_id)
    resolution = await session.scalar(
        select(IncidentResolution)
        .where(
            IncidentResolution.incident_id == offer.incident_id,
            IncidentResolution.status == ResolutionStatus.PENDING,
        )
        .order_by(IncidentResolution.decided_at.desc())
    )
    if resolution is not None:
        resolution.status = ResolutionStatus.FAILED
    if incident is not None and incident.status == IncidentStatus.RESOLVING:
        incident.status = IncidentStatus.IN_REVIEW
    return incident


async def expire_offer(session: AsyncSession, offer_id: uuid.UUID) -> bool:
    """Job handler (BR7): an unanswered offer counts as declined; offer the next driver."""
    offer = await _lock_offer(session, offer_id)
    if offer.status != OfferStatus.PENDING or offer.expires_at > utc_now() + timedelta(seconds=1):
        return False
    offer.status = OfferStatus.EXPIRED
    incident = await _rescue_failed(session, offer)
    await _requeue_orders(session, offer)
    await session.commit()
    await notify_user(offer.driver_id, "offer.expired", {"offer_id": str(offer.id)})
    if incident is not None:
        await notify_hub(incident.hub_id, "incident.updated", {"incident_id": str(incident.id)})
    return True


async def decline_offer(
    session: AsyncSession, driver_id: uuid.UUID, offer_id: uuid.UUID, reason: str | None
) -> None:
    offer = await _lock_offer(session, offer_id)
    if offer.driver_id != driver_id:
        raise NotFound("Offer not found", code="OFFER_NOT_FOUND")
    if offer.status != OfferStatus.PENDING:
        raise Conflict("This offer is no longer open", code="OFFER_CLOSED")
    offer.status = OfferStatus.DECLINED
    offer.responded_at = utc_now()
    offer.decline_reason = reason
    incident = await _rescue_failed(session, offer)
    await _requeue_orders(session, offer)
    await session.commit()
    if incident is not None:
        await notify_hub(incident.hub_id, "incident.updated", {"incident_id": str(incident.id)})


async def accept_offer(
    session: AsyncSession, driver_id: uuid.UUID, offer_id: uuid.UUID
) -> list[Order]:
    """BR8: the order goes to the first driver who accepts within the timeout."""
    settings = await load_business_settings(session)
    offer = await _lock_offer(session, offer_id)
    if offer.driver_id != driver_id:
        raise NotFound("Offer not found", code="OFFER_NOT_FOUND")
    if offer.status != OfferStatus.PENDING:
        raise Conflict("This offer is no longer open", code="OFFER_CLOSED")
    if offer.expires_at <= utc_now():
        offer.status = OfferStatus.EXPIRED
        await _rescue_failed(session, offer)
        await _requeue_orders(session, offer)
        await session.commit()
        raise Conflict("This offer has expired", code="OFFER_EXPIRED")

    driver = await session.get(User, driver_id)
    assert driver is not None
    assigned: list[Order] = []
    for order_id in offer_order_ids(offer):
        order = await lock_order(session, order_id)
        if order.status != OrderStatus.AWAITING_ASSIGNMENT:
            continue  # cancelled or put on hold meanwhile
        assign_order(session, order, driver, offer)
        await attach_order(session, order, driver.id)
        assigned.append(order)
    if not assigned:
        offer.status = OfferStatus.CANCELLED
        await session.commit()
        raise Conflict("The order is no longer available", code="ORDER_NOT_AVAILABLE")

    offer.status = OfferStatus.ACCEPTED
    offer.responded_at = utc_now()
    incident = await _complete_rescue(session, offer, assigned)
    await bump_daily_stat(session, driver.id, driver.hub_id, assigned=len(assigned))
    await session.flush()
    await refresh_driver_etas(session, driver.id, settings)
    for order in assigned:
        notify_partner(session, order, DRIVER_ASSIGNED, driver=driver)
    await session.commit()

    for order in assigned:
        await publish_order_update(order, extra_user=order.handover_from_driver_id)
    if incident is not None:
        await notify_hub(incident.hub_id, "incident.updated", {"incident_id": str(incident.id)})
        await notify_user(incident.driver_id, "incident.updated", {"incident_id": str(incident.id)})
    logger.info("[accept_offer] driver=%s orders=%d", driver_id, len(assigned))
    return assigned


def assign_order(session: AsyncSession, order: Order, driver: User, offer: DispatchOffer) -> None:
    transition(
        session,
        order,
        OrderStatus.ASSIGNED,
        actor_type=ActorType.SYSTEM,
        payload={
            "driver_id": str(driver.id),
            "offer_id": str(offer.id),
            "source": offer.source.value,
        },
    )
    session.add(Assignment(order_id=order.id, driver_id=driver.id, assigned_at=utc_now()))
    order.current_driver_id = driver.id


async def _complete_rescue(
    session: AsyncSession, offer: DispatchOffer, orders: list[Order]
) -> Incident | None:
    if offer.incident_id is None:
        return None
    incident = await session.get(Incident, offer.incident_id)
    resolution = await session.scalar(
        select(IncidentResolution).where(
            IncidentResolution.incident_id == offer.incident_id,
            IncidentResolution.status == ResolutionStatus.PENDING,
        )
    )
    if resolution is not None:
        resolution.status = ResolutionStatus.DONE
    if incident is not None:
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = utc_now()
    for order in orders:
        if order.active_incident_id == offer.incident_id:
            order.active_incident_id = None
    return incident


# =============================== Manual offers (hub, UC-04) ===============================


async def offer_manually(
    session: AsyncSession,
    *,
    hub_id: uuid.UUID,
    driver_id: uuid.UUID,
    orders: list[Order],
    incident_id: uuid.UUID | None = None,
) -> DispatchOffer:
    """Send one offer covering `orders` to a driver picked by the hub manager.

    The orders must already be AWAITING_ASSIGNMENT. The caller commits.
    """
    settings = await load_business_settings(session)
    driver = await session.scalar(
        select(User)
        .join(Role, Role.id == User.role_id)
        .where(User.id == driver_id, Role.code == RoleCode.DRIVER, User.hub_id == hub_id)
    )
    if driver is None or driver.status != UserStatus.ACTIVE:
        raise ValidationFailed("Choose an active driver of this hub", code="DRIVER_NOT_AVAILABLE")
    pending = await session.scalar(
        select(DispatchOffer)
        .where(DispatchOffer.driver_id == driver_id, DispatchOffer.status == OfferStatus.PENDING)
        .with_for_update()
    )
    if pending is not None and pending.source == OfferSource.MANUAL:
        raise Conflict("This driver is answering another hub offer", code="DRIVER_BUSY")
    if pending is not None:
        # The hub's choice wins over an automatic offer; that order goes back to dispatch.
        pending.status = OfferStatus.CANCELLED
        await _requeue_orders(session, pending)
        await session.flush()
    for order in orders:
        if order.status != OrderStatus.AWAITING_ASSIGNMENT:
            raise Conflict(
                "Only orders waiting for a driver can be offered", code="INVALID_TRANSITION"
            )

    lead = orders[0]
    origin = await pickup_point(session, lead)
    ranked = await rank_candidates(session, settings, hub_id=hub_id, origin=origin, for_hub=True)
    match = next((c for c in ranked if c.driver_id == driver_id), None)
    profile = await session.get(DriverProfile, driver_id)
    candidate = match or Candidate(
        driver_id=driver_id,
        full_name=driver.full_name,
        phone=driver.phone,
        lat=profile.last_lat if profile else None,
        lng=profile.last_lng if profile else None,
        distance_km=0,
        active_orders=0,
        score=0,
    )
    now = utc_now()
    offer = DispatchOffer(
        order_id=lead.id,
        driver_id=driver_id,
        round=0,
        rank=0,
        score=Decimal(str(candidate.score)),
        score_breakdown={**candidate.breakdown, "distance_km": candidate.distance_km},
        source=OfferSource.MANUAL,
        status=OfferStatus.PENDING,
        offered_at=now,
        expires_at=now + timedelta(seconds=settings.offer_timeout_s),
        bundle_order_ids=[str(order.id) for order in orders] if len(orders) > 1 else [],
        incident_id=incident_id,
    )
    session.add(offer)
    await session.flush()
    enqueue(session, OFFER_TIMEOUT, {"offer_id": str(offer.id)}, run_at=offer.expires_at)
    return offer


# =============================== Sweeper (worker) ===============================


async def sweep(session: AsyncSession, *, limit: int = 50) -> dict[str, int]:
    """Safety net run every few seconds: expire overdue offers and make sure every waiting
    order has a dispatch job (covers seed data, drivers coming online, a sleeping host)."""
    now = utc_now()
    overdue = list(
        await session.scalars(
            select(DispatchOffer.id)
            .where(
                DispatchOffer.status == OfferStatus.PENDING,
                DispatchOffer.expires_at < now - timedelta(seconds=2),
            )
            .limit(limit)
        )
    )
    expired = 0
    for offer_id in overdue:
        if await expire_offer(session, offer_id):
            expired += 1

    covered = exists(
        select(DispatchOffer.id).where(
            DispatchOffer.status == OfferStatus.PENDING,
            or_(
                DispatchOffer.order_id == Order.id,
                DispatchOffer.bundle_order_ids.contains(
                    func.jsonb_build_array(cast(Order.id, String))
                ),
            ),
        )
    )
    waiting = list(
        await session.scalars(
            select(Order.id)
            .where(
                Order.status == OrderStatus.AWAITING_ASSIGNMENT,
                Order.active_incident_id.is_(None),
                ~covered,
            )
            .order_by((Order.priority == OrderPriority.EXPRESS).desc(), Order.promised_at)
            .limit(limit)
        )
    )
    queued = 0
    for order_id in waiting:
        if not await has_pending(session, DISPATCH_RUN, "order_id", str(order_id)):
            enqueue(session, DISPATCH_RUN, {"order_id": str(order_id)})
            queued += 1
    await session.commit()
    return {"expired": expired, "queued": queued}
