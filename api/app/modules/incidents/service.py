"""Delivery incidents (SPEC §3.4): driver report, hub classification, response, resolution.

Order of the hub's steps follows the report's If-Else logic (4.1.4.1):
classify -> respond -> choose a solution -> resolve. Each step is enforced here.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_datetime, local_today, parse_hhmm, utc_now
from app.core.deps import CurrentUser, require_hub
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.pagination import Page, PageParams
from app.modules.dispatch.service import offer_manually, pickup_point, rank_candidates
from app.modules.files.models import File
from app.modules.files.service import require_own_files
from app.modules.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentFile,
    IncidentOrder,
    IncidentPriority,
    IncidentResolution,
    IncidentStatus,
    IncidentType,
    ResolutionSolution,
    ResolutionStatus,
)
from app.modules.incidents.schemas import (
    CandidateOut,
    IncidentListItem,
    IncidentOrderOut,
    IncidentOut,
    IncidentReportIn,
    IncidentSummaryOut,
    PersonOut,
    ResolutionOut,
    ResolveIn,
)
from app.modules.orders.models import (
    ActorType,
    AssignmentStatus,
    Order,
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
from app.modules.partner.webhooks import INCIDENT, STATUS_CHANGED, notify_partner
from app.modules.realtime.hub import notify_hub, notify_user
from app.modules.reports.service import bump_daily_stat
from app.modules.routing.service import detach_order, reorder_stops
from app.modules.settings.service import load_business_settings
from app.modules.tracking.service import refresh_driver_etas
from app.modules.users.models import User

logger = logging.getLogger(__name__)

# Default suggestion shown to the hub; the hub manager makes the final call.
SUGGESTED_CATEGORY = {
    IncidentType.TRAFFIC_JAM: IncidentCategory.OBJECTIVE,
    IncidentType.WEATHER: IncidentCategory.OBJECTIVE,
    IncidentType.VEHICLE_BREAKDOWN: IncidentCategory.SUBJECTIVE,
    IncidentType.HEALTH: IncidentCategory.SUBJECTIVE,
    IncidentType.GOODS_DAMAGED: IncidentCategory.SUBJECTIVE,
}

# Short reason shared with the partner, plus the apology they forward to the customer.
CUSTOMER_REASON = {
    IncidentType.TRAFFIC_JAM: "heavy traffic on the way",
    IncidentType.WEATHER: "bad weather",
    IncidentType.TRAFFIC_ACCIDENT: "a traffic accident on the route",
    IncidentType.VEHICLE_BREAKDOWN: "a problem with the delivery vehicle",
    IncidentType.HEALTH: "the driver being unable to continue",
    IncidentType.GOODS_DAMAGED: "a problem with the parcel",
    IncidentType.OTHER: "an unexpected problem",
}
APOLOGY = (
    "We are sorry for the delay. Your parcel may arrive later than planned because of {reason}."
)

OPEN_STATUSES = (IncidentStatus.OPEN, IncidentStatus.IN_REVIEW, IncidentStatus.RESOLVING)
PRIORITY_RANK = {IncidentPriority.HIGH: 0, IncidentPriority.MEDIUM: 1, IncidentPriority.LOW: 2}
STATUS_RANK = {
    IncidentStatus.OPEN: 0,
    IncidentStatus.IN_REVIEW: 1,
    IncidentStatus.RESOLVING: 2,
    IncidentStatus.RESOLVED: 3,
    IncidentStatus.CLOSED_NO_ACTION: 4,
}


# =============================== Read models ===============================


async def _to_out(session: AsyncSession, incident: Incident) -> IncidentOut:
    driver = await session.get(User, incident.driver_id)
    handler = await session.get(User, incident.handled_by) if incident.handled_by else None
    photos = await session.scalars(
        select(File.url)
        .join(IncidentFile, IncidentFile.file_id == File.id)
        .where(IncidentFile.incident_id == incident.id)
    )
    orders = list(
        await session.scalars(
            select(Order)
            .join(IncidentOrder, IncidentOrder.order_id == Order.id)
            .where(IncidentOrder.incident_id == incident.id)
            .order_by(Order.waybill_code)
        )
    )
    order_rows = []
    for order in orders:
        holder = (
            await session.get(User, order.current_driver_id) if order.current_driver_id else None
        )
        order_rows.append(
            IncidentOrderOut(
                id=order.id,
                waybill_code=order.waybill_code,
                status=order.status,
                priority=order.priority,
                recipient_name=order.recipient_name,
                delivery_address=order.delivery_address,
                promised_at=order.promised_at,
                current_eta=order.current_eta,
                current_driver_name=holder.full_name if holder else None,
            )
        )
    resolutions = []
    for resolution in await session.scalars(
        select(IncidentResolution)
        .where(IncidentResolution.incident_id == incident.id)
        .order_by(IncidentResolution.decided_at.desc())  # latest decision first
    ):
        new_driver = (
            await session.get(User, resolution.new_driver_id) if resolution.new_driver_id else None
        )
        resolutions.append(
            ResolutionOut(
                solution=resolution.solution,
                status=resolution.status,
                new_driver_name=new_driver.full_name if new_driver else None,
                decided_at=resolution.decided_at,
                note=resolution.note,
            )
        )
    assert driver is not None
    return IncidentOut(
        id=incident.id,
        code=incident.code,
        type=incident.type,
        source=incident.source,
        status=incident.status,
        description=incident.description,
        suggested_category=incident.suggested_category,
        category=incident.category,
        priority=incident.priority,
        hub_response=incident.hub_response,
        lat=incident.lat,
        lng=incident.lng,
        reported_at=incident.reported_at,
        classified_at=incident.classified_at,
        resolved_at=incident.resolved_at,
        driver=PersonOut(id=driver.id, name=driver.full_name, phone=driver.phone),
        handled_by=handler.full_name if handler else None,
        photo_urls=list(photos),
        orders=order_rows,
        resolutions=resolutions,
    )


async def _hub_incident(
    session: AsyncSession, hub_id: uuid.UUID, incident_id: uuid.UUID
) -> Incident:
    incident = await session.scalar(
        select(Incident).where(Incident.id == incident_id).with_for_update()
    )
    if incident is None or incident.hub_id != hub_id:
        raise NotFound("Incident not found", code="INCIDENT_NOT_FOUND")
    return incident


# =============================== Driver: report (FR-D-06) ===============================


async def report(session: AsyncSession, driver: CurrentUser, data: IncidentReportIn) -> IncidentOut:
    """Validation follows the If-Else of the report: description and evidence first."""
    if driver.hub_id is None:
        raise ValidationFailed("Your account is not linked to a hub", code="HUB_REQUIRED")
    if not data.photo_file_ids:
        raise ValidationFailed(
            "Please describe the incident and attach evidence", code="EVIDENCE_REQUIRED"
        )
    photos = await require_own_files(session, driver.id, data.photo_file_ids)

    held = list(
        await session.scalars(
            select(Order).where(
                Order.current_driver_id == driver.id, Order.status.in_(ACTIVE_DRIVER_STATUSES)
            )
        )
    )
    if data.order_ids is not None:
        wanted = set(data.order_ids)
        held = [order for order in held if order.id in wanted]
        if len(held) != len(wanted):
            raise ValidationFailed(
                "Some orders are not yours or not active", code="ORDER_NOT_FOUND"
            )
    if not held:
        raise ValidationFailed("You have no active order to report on", code="NO_ACTIVE_ORDER")

    express = any(order.priority == OrderPriority.EXPRESS for order in held)
    late = any(order.current_eta and order.current_eta > order.promised_at for order in held)
    incident = Incident(
        hub_id=driver.hub_id,
        driver_id=driver.id,
        type=data.type,
        description=data.description.strip(),
        lat=data.lat,
        lng=data.lng,
        suggested_category=SUGGESTED_CATEGORY.get(data.type),
        priority=IncidentPriority.HIGH if express or late else None,
        status=IncidentStatus.OPEN,
        reported_at=utc_now(),
    )
    session.add(incident)
    await session.flush()
    session.add_all(IncidentFile(incident_id=incident.id, file_id=photo.id) for photo in photos)
    reason = CUSTOMER_REASON.get(data.type, CUSTOMER_REASON[IncidentType.OTHER])
    for order in held:
        session.add(IncidentOrder(incident_id=incident.id, order_id=order.id))
        order.active_incident_id = incident.id
        add_event(
            session,
            order,
            OrderEventType.INCIDENT,
            actor_type=ActorType.USER,
            actor_id=driver.id,
            payload={"incident_id": str(incident.id), "type": data.type.value},
            lat=data.lat,
            lng=data.lng,
        )
        notify_partner(
            session,
            order,
            INCIDENT,
            reason=data.type.value,
            message=APOLOGY.format(reason=reason),
        )
    await bump_daily_stat(session, driver.id, driver.hub_id, incidents=1)
    await session.commit()
    await session.refresh(incident)
    logger.info("[report_incident] %s driver=%s orders=%d", incident.code, driver.id, len(held))
    out = await _to_out(session, incident)
    await notify_hub(
        driver.hub_id,
        "incident.created",
        {"incident_id": str(incident.id), "code": incident.code, "type": data.type.value},
    )
    return out


async def list_for_driver(session: AsyncSession, driver_id: uuid.UUID) -> list[IncidentOut]:
    incidents = await session.scalars(
        select(Incident)
        .where(Incident.driver_id == driver_id)
        .order_by(Incident.reported_at.desc())
        .limit(20)
    )
    return [await _to_out(session, incident) for incident in incidents]


async def get_for_driver(
    session: AsyncSession, driver_id: uuid.UUID, incident_id: uuid.UUID
) -> IncidentOut:
    incident = await session.get(Incident, incident_id)
    if incident is None or incident.driver_id != driver_id:
        raise NotFound("Incident not found", code="INCIDENT_NOT_FOUND")
    return await _to_out(session, incident)


# =============================== Hub: lists (H-04, H-05) ===============================


async def summary(session: AsyncSession, hub_id: uuid.UUID) -> IncidentSummaryOut:
    by_status = dict(
        (
            await session.execute(
                select(Incident.status, func.count())
                .where(Incident.hub_id == hub_id, Incident.status.in_(OPEN_STATUSES))
                .group_by(Incident.status)
            )
        ).all()
    )
    priority_rows = await session.execute(
        select(Incident.priority, func.count())
        .where(Incident.hub_id == hub_id, Incident.status.in_(OPEN_STATUSES))
        .group_by(Incident.priority)
    )
    # Incidents not classified yet have no priority; they are counted as UNSET.
    by_priority = {
        (priority.value if priority else "UNSET"): count for priority, count in priority_rows
    }
    day_start = local_datetime(local_today(), parse_hhmm("00:00"))
    resolved_today = await session.scalar(
        select(func.count()).where(
            Incident.hub_id == hub_id,
            Incident.status == IncidentStatus.RESOLVED,
            Incident.resolved_at >= day_start,
        )
    )
    by_type = dict(
        (
            await session.execute(
                select(Incident.type, func.count())
                .where(
                    Incident.hub_id == hub_id,
                    Incident.reported_at >= utc_now() - timedelta(days=30),
                )
                .group_by(Incident.type)
            )
        ).all()
    )
    return IncidentSummaryOut(
        open=by_status.get(IncidentStatus.OPEN, 0),
        in_review=by_status.get(IncidentStatus.IN_REVIEW, 0),
        resolving=by_status.get(IncidentStatus.RESOLVING, 0),
        resolved_today=resolved_today or 0,
        by_priority=by_priority,
        by_type_30d={str(key): value for key, value in by_type.items()},
    )


async def list_for_hub(
    session: AsyncSession,
    hub_id: uuid.UUID,
    paging: PageParams,
    *,
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    open_only: bool = False,
) -> Page[IncidentListItem]:
    order_count = (
        select(func.count())
        .where(IncidentOrder.incident_id == Incident.id)
        .correlate(Incident)
        .scalar_subquery()
    )
    query = (
        select(Incident, User.full_name, order_count)
        .join(User, User.id == Incident.driver_id)
        .where(Incident.hub_id == hub_id)
    )
    if status:
        query = query.where(Incident.status == status)
    if open_only:
        query = query.where(Incident.status.in_(OPEN_STATUSES))
    if priority:
        query = query.where(Incident.priority == priority)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    # Open incidents first, then HIGH priority, then newest.
    priority_rank = case(PRIORITY_RANK, value=Incident.priority, else_=len(PRIORITY_RANK))
    status_rank = case(STATUS_RANK, value=Incident.status, else_=len(STATUS_RANK))
    rows = await session.execute(
        query.order_by(status_rank, priority_rank, Incident.reported_at.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return Page(
        items=[
            IncidentListItem(
                id=incident.id,
                code=incident.code,
                type=incident.type,
                status=incident.status,
                priority=incident.priority,
                category=incident.category,
                description=incident.description,
                driver_name=driver_name,
                order_count=count,
                reported_at=incident.reported_at,
            )
            for incident, driver_name, count in rows
        ],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


async def get_for_hub(
    session: AsyncSession, hub_id: uuid.UUID, incident_id: uuid.UUID
) -> IncidentOut:
    incident = await session.get(Incident, incident_id)
    if incident is None or incident.hub_id != hub_id:
        raise NotFound("Incident not found", code="INCIDENT_NOT_FOUND")
    return await _to_out(session, incident)


# =============================== Hub: classify and respond ===============================


async def classify(
    session: AsyncSession,
    manager: CurrentUser,
    incident_id: uuid.UUID,
    category: IncidentCategory,
    priority: IncidentPriority,
) -> IncidentOut:
    incident = await _hub_incident(session, require_hub(manager), incident_id)
    if incident.status not in (IncidentStatus.OPEN, IncidentStatus.IN_REVIEW):
        raise Conflict("This incident is already being resolved", code="INCIDENT_CLOSED")
    incident.category = category
    incident.priority = priority
    incident.status = IncidentStatus.IN_REVIEW
    incident.classified_at = utc_now()
    incident.handled_by = manager.id
    await session.commit()
    await notify_hub(incident.hub_id, "incident.updated", {"incident_id": str(incident.id)})
    return await _to_out(session, incident)


async def respond(
    session: AsyncSession, manager: CurrentUser, incident_id: uuid.UUID, message: str
) -> IncidentOut:
    incident = await _hub_incident(session, require_hub(manager), incident_id)
    if incident.category is None:
        raise ValidationFailed("Please classify the incident", code="INCIDENT_NOT_CLASSIFIED")
    incident.hub_response = message.strip()
    incident.handled_by = manager.id
    await session.commit()
    await notify_user(incident.driver_id, "incident.updated", {"incident_id": str(incident.id)})
    return await _to_out(session, incident)


async def candidates(
    session: AsyncSession, manager: CurrentUser, incident_id: uuid.UUID
) -> list[CandidateOut]:
    """Replacement drivers ranked around the incident location (UC-04)."""
    hub_id = require_hub(manager)
    incident = await session.get(Incident, incident_id)
    if incident is None or incident.hub_id != hub_id:
        raise NotFound("Incident not found", code="INCIDENT_NOT_FOUND")
    settings = await load_business_settings(session)
    if incident.lat is not None and incident.lng is not None:
        origin = (incident.lat, incident.lng)
    else:
        first = await session.scalar(
            select(Order)
            .join(IncidentOrder, IncidentOrder.order_id == Order.id)
            .where(IncidentOrder.incident_id == incident.id)
        )
        origin = await pickup_point(session, first) if first else (0.0, 0.0)
    ranked = await rank_candidates(
        session, settings, hub_id=hub_id, origin=origin, exclude={incident.driver_id}, for_hub=True
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


# =============================== Hub: resolve (UC-03, UC-04) ===============================


async def resolve(
    session: AsyncSession, manager: CurrentUser, incident_id: uuid.UUID, data: ResolveIn
) -> IncidentOut:
    hub_id = require_hub(manager)
    incident = await _hub_incident(session, hub_id, incident_id)
    if incident.category is None:
        raise ValidationFailed("Please classify the incident", code="INCIDENT_NOT_CLASSIFIED")
    if not incident.hub_response:
        raise ValidationFailed("Please enter a response to the driver", code="RESPONSE_REQUIRED")
    if incident.status not in (IncidentStatus.OPEN, IncidentStatus.IN_REVIEW):
        raise Conflict("This incident is already being resolved", code="INCIDENT_CLOSED")

    orders = await _incident_orders(session, incident)
    if data.solution == ResolutionSolution.ROUTE_SUGGESTED:
        await _resolve_reroute(session, manager, incident, orders, data)
    elif data.solution == ResolutionSolution.DRIVER_REASSIGNMENT:
        await _resolve_reassign(session, manager, incident, orders, data)
    else:
        await _resolve_hold(session, manager, incident, orders, data)
    await session.commit()

    await notify_hub(hub_id, "incident.updated", {"incident_id": str(incident.id)})
    await notify_user(incident.driver_id, "incident.updated", {"incident_id": str(incident.id)})
    for order in orders:
        await publish_order_update(order, extra_user=incident.driver_id)
    if data.solution == ResolutionSolution.DRIVER_REASSIGNMENT and data.driver_id:
        await notify_user(data.driver_id, "offer.created", {"incident_id": str(incident.id)})
    if data.solution == ResolutionSolution.ROUTE_SUGGESTED:
        await notify_user(incident.driver_id, "route.updated", {"incident_id": str(incident.id)})
    logger.info("[resolve_incident] %s solution=%s", incident.code, data.solution)
    return await _to_out(session, incident)


async def _incident_orders(session: AsyncSession, incident: Incident) -> list[Order]:
    """Orders still tied to the incident, locked: held by the reporting driver, or waiting
    for a new driver after a rescue offer was declined."""
    ids = list(
        await session.scalars(
            select(IncidentOrder.order_id).where(IncidentOrder.incident_id == incident.id)
        )
    )
    orders = [await lock_order(session, order_id) for order_id in ids]
    return [
        order
        for order in orders
        if (
            order.current_driver_id == incident.driver_id and order.status in ACTIVE_DRIVER_STATUSES
        )
        or (
            order.active_incident_id == incident.id
            and order.status == OrderStatus.AWAITING_ASSIGNMENT
        )
    ]


def _record(
    session: AsyncSession,
    manager: CurrentUser,
    incident: Incident,
    solution: ResolutionSolution,
    *,
    status: ResolutionStatus,
    new_driver_id: uuid.UUID | None = None,
    snapshot: dict[str, object] | None = None,
    note: str | None = None,
) -> None:
    session.add(
        IncidentResolution(
            incident_id=incident.id,
            solution=solution,
            new_driver_id=new_driver_id,
            route_snapshot=snapshot,
            status=status,
            note=note,
            decided_by=manager.id,
            decided_at=utc_now(),
        )
    )


def _close(incident: Incident, orders: list[Order]) -> None:
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = utc_now()
    for order in orders:
        if order.active_incident_id == incident.id:
            order.active_incident_id = None


async def _resolve_reroute(
    session: AsyncSession,
    manager: CurrentUser,
    incident: Incident,
    orders: list[Order],
    data: ResolveIn,
) -> None:
    """Objective incident: the driver continues with a new stop order (UC-03)."""
    if not data.stop_ids:
        raise ValidationFailed("Send the new order of stops", code="STOP_LIST_REQUIRED")
    settings = await load_business_settings(session)
    await reorder_stops(session, incident.driver_id, data.stop_ids)
    await refresh_driver_etas(
        session, incident.driver_id, settings, reason="The driver is taking a new route."
    )
    _record(
        session,
        manager,
        incident,
        ResolutionSolution.ROUTE_SUGGESTED,
        status=ResolutionStatus.DONE,
        snapshot={"stop_ids": [str(stop_id) for stop_id in data.stop_ids]},
        note=data.note,
    )
    _close(incident, orders)


async def _take_back(
    session: AsyncSession, manager: CurrentUser, order: Order, *, reason: str
) -> None:
    """Move an order away from the reporting driver, back to AWAITING_ASSIGNMENT."""
    previous_driver = order.current_driver_id
    in_hand = order.status in (OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY)
    transition(
        session,
        order,
        OrderStatus.AWAITING_ASSIGNMENT,
        actor_type=ActorType.USER,
        actor_id=manager.id,
        payload={"reason": reason, "handover_from": str(previous_driver) if in_hand else None},
    )
    assignment = await active_assignment(session, order.id)
    if assignment is not None:
        assignment.status = AssignmentStatus.REASSIGNED
        assignment.ended_at = utc_now()
        assignment.end_reason = reason
    order.handover_from_driver_id = previous_driver if in_hand else None
    order.current_driver_id = None
    order.current_eta = None
    await detach_order(session, order)


async def _resolve_reassign(
    session: AsyncSession,
    manager: CurrentUser,
    incident: Incident,
    orders: list[Order],
    data: ResolveIn,
) -> None:
    """Subjective incident: another driver takes over the parcels (UC-04)."""
    if data.driver_id is None:
        raise ValidationFailed("Choose a replacement driver", code="DRIVER_REQUIRED")
    if data.driver_id == incident.driver_id:
        raise ValidationFailed("Choose a different driver", code="DRIVER_NOT_AVAILABLE")
    if data.order_ids is not None:
        wanted = set(data.order_ids)
        orders = [order for order in orders if order.id in wanted]
    if not orders:
        raise ValidationFailed("No active order to hand over", code="NO_ACTIVE_ORDER")

    for order in orders:
        if order.status != OrderStatus.AWAITING_ASSIGNMENT:
            await _take_back(session, manager, order, reason=f"Incident {incident.code}")
    await session.flush()
    await offer_manually(
        session,
        hub_id=incident.hub_id,
        driver_id=data.driver_id,
        orders=orders,
        incident_id=incident.id,
    )
    _record(
        session,
        manager,
        incident,
        ResolutionSolution.DRIVER_REASSIGNMENT,
        status=ResolutionStatus.PENDING,
        new_driver_id=data.driver_id,
        note=data.note,
    )
    incident.status = IncidentStatus.RESOLVING
    for order in orders:
        notify_partner(
            session, order, STATUS_CHANGED, message="Another driver is taking over your parcel."
        )


async def _resolve_hold(
    session: AsyncSession,
    manager: CurrentUser,
    incident: Incident,
    orders: list[Order],
    data: ResolveIn,
) -> None:
    """No replacement available: keep the parcels at the hub (luồng 4a of UC-04)."""
    for order in orders:
        if order.status != OrderStatus.AWAITING_ASSIGNMENT:
            await _take_back(
                session, manager, order, reason=f"Incident {incident.code}: hold at hub"
            )
        transition(
            session,
            order,
            OrderStatus.ON_HOLD,
            actor_type=ActorType.USER,
            actor_id=manager.id,
            payload={"reason": "Held at hub after an incident"},
        )
        notify_partner(
            session,
            order,
            STATUS_CHANGED,
            message="Your parcel is kept at the hub for a new delivery.",
        )
    _record(
        session,
        manager,
        incident,
        ResolutionSolution.HOLD_AT_HUB,
        status=ResolutionStatus.DONE,
        note=data.note,
    )
    _close(incident, orders)
