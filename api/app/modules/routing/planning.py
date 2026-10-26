"""Route planning for the hub (H-02, UC-03): today's routes, road geometry, the best
visiting order from OSRM (nearest neighbour when OSRM is down), and saving a new order.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_hub
from app.core.errors import NotFound, ValidationFailed
from app.core.geo import haversine_km
from app.modules.hubs.models import Hub
from app.modules.orders.models import Order
from app.modules.orders.service import ACTIVE_DRIVER_STATUSES, publish_order_update
from app.modules.realtime.hub import notify_hub, notify_user
from app.modules.routing.models import Route, RouteStop, StopStatus
from app.modules.routing.osrm import Point, osrm
from app.modules.routing.schemas import (
    OptimizeOut,
    PlanOrderOut,
    PlanStopOut,
    RouteDetailOut,
    RouteSummaryOut,
)
from app.modules.routing.service import pending_stops, reorder_stops
from app.modules.settings.service import load_business_settings
from app.modules.tracking.service import driver_position, refresh_driver_etas, road_leg_minutes
from app.modules.users.models import DriverProfile, User

logger = logging.getLogger(__name__)


# =============================== Queries ===============================


async def list_routes(
    session: AsyncSession, hub_id: uuid.UUID, work_date: date
) -> list[RouteSummaryOut]:
    """Every driver route of the hub for one day, busiest first."""
    active = Order.status.in_(ACTIVE_DRIVER_STATUSES)
    stop_counts = (
        select(
            RouteStop.route_id,
            func.count().label("total"),
            func.count().filter(RouteStop.status == StopStatus.PENDING).label("pending"),
            func.min(RouteStop.eta)
            .filter(RouteStop.status == StopStatus.PENDING)
            .label("next_eta"),
            func.max(RouteStop.eta)
            .filter(RouteStop.status == StopStatus.PENDING)
            .label("last_eta"),
        )
        .group_by(RouteStop.route_id)
        .subquery()
    )
    order_counts = (
        select(
            RouteStop.route_id,
            func.count(Order.id).filter(active).label("active"),
            func.count(Order.id)
            .filter(active, func.coalesce(Order.current_eta, func.now()) > Order.promised_at)
            .label("risk"),
        )
        .join(Order, Order.route_stop_id == RouteStop.id)
        .group_by(RouteStop.route_id)
        .subquery()
    )
    rows = await session.execute(
        select(
            Route,
            User.full_name,
            func.coalesce(stop_counts.c.total, 0),
            func.coalesce(stop_counts.c.pending, 0),
            func.coalesce(order_counts.c.active, 0),
            func.coalesce(order_counts.c.risk, 0),
            stop_counts.c.next_eta,
            stop_counts.c.last_eta,
        )
        .join(User, User.id == Route.driver_id)
        .outerjoin(stop_counts, stop_counts.c.route_id == Route.id)
        .outerjoin(order_counts, order_counts.c.route_id == Route.id)
        .where(Route.hub_id == hub_id, Route.work_date == work_date)
        .order_by(case((func.coalesce(order_counts.c.active, 0) > 0, 0), else_=1), User.full_name)
    )
    return [
        RouteSummaryOut(
            id=route.id,
            driver_id=route.driver_id,
            driver_name=name,
            status=route.status,
            work_date=route.work_date,
            stops_total=total,
            stops_pending=pending,
            orders_active=active_count,
            orders_at_risk=risk,
            total_distance_m=route.total_distance_m,
            total_duration_s=route.total_duration_s,
            next_eta=next_eta,
            last_eta=last_eta,
        )
        for route, name, total, pending, active_count, risk, next_eta, last_eta in rows
    ]


async def _hub_route(session: AsyncSession, hub_id: uuid.UUID, route_id: uuid.UUID) -> Route:
    route = await session.get(Route, route_id)
    if route is None or route.hub_id != hub_id:
        raise NotFound("Route not found", code="ROUTE_NOT_FOUND")
    return route


async def route_detail(
    session: AsyncSession, hub_id: uuid.UUID, route_id: uuid.UUID
) -> RouteDetailOut:
    route = await _hub_route(session, hub_id, route_id)
    driver = await session.get(User, route.driver_id)
    profile = await session.get(DriverProfile, route.driver_id)
    hub = await session.get(Hub, route.hub_id)
    assert driver is not None and hub is not None
    stops = list(
        await session.scalars(
            select(RouteStop).where(RouteStop.route_id == route.id).order_by(RouteStop.seq)
        )
    )
    orders = list(
        await session.scalars(
            select(Order)
            .where(Order.route_stop_id.in_([stop.id for stop in stops]))
            .order_by(Order.promised_at)
        )
    )
    by_stop: dict[uuid.UUID, list[PlanOrderOut]] = {}
    for order in orders:
        assert order.route_stop_id is not None
        by_stop.setdefault(order.route_stop_id, []).append(
            PlanOrderOut(
                id=order.id,
                waybill_code=order.waybill_code,
                status=order.status,
                priority=order.priority,
                promised_at=order.promised_at,
                current_eta=order.current_eta,
            )
        )
    return RouteDetailOut(
        id=route.id,
        status=route.status,
        work_date=route.work_date,
        driver_id=driver.id,
        driver_name=driver.full_name,
        driver_phone=driver.phone,
        driver_lat=profile.last_lat if profile else None,
        driver_lng=profile.last_lng if profile else None,
        hub_name=hub.name,
        hub_lat=hub.lat,
        hub_lng=hub.lng,
        geometry=route.polyline,
        total_distance_m=route.total_distance_m,
        total_duration_s=route.total_duration_s,
        eta_is_estimate=route.polyline is None,
        stops=[
            PlanStopOut(
                id=stop.id,
                seq=stop.seq,
                status=stop.status,
                address=stop.address,
                lat=stop.lat,
                lng=stop.lng,
                recipient_name=stop.recipient_name,
                eta=stop.eta,
                orders=by_stop.get(stop.id, []),
            )
            for stop in stops
        ],
    )


# =============================== Optimisation ===============================


def nearest_neighbour(start: Point, points: list[Point]) -> list[int]:
    """Greedy visiting order (indexes into `points`) when OSRM is not available."""
    remaining = list(range(len(points)))
    order: list[int] = []
    here = start
    while remaining:
        best = min(remaining, key=lambda index: haversine_km(*here, *points[index]))
        order.append(best)
        remaining.remove(best)
        here = points[best]
    return order


async def optimize(session: AsyncSession, hub_id: uuid.UUID, route_id: uuid.UUID) -> OptimizeOut:
    """Suggest the fastest order of the pending stops from the driver's position (or the
    hub before the route starts). Nothing is saved."""
    settings = await load_business_settings(session)
    route = await _hub_route(session, hub_id, route_id)
    hub = await session.get(Hub, route.hub_id)
    assert hub is not None
    stops = await pending_stops(session, route.driver_id)
    if len(stops) < 2:
        raise ValidationFailed("At least two pending stops are needed", code="NOTHING_TO_OPTIMIZE")
    start = await driver_position(session, route.driver_id, (hub.lat, hub.lng))
    points: list[Point] = [(stop.lat, stop.lng) for stop in stops]

    current_legs, current_road = await road_leg_minutes(settings, [start, *points])
    trip = await osrm.trip([start, *points])
    geometry: str | None
    if trip is not None:
        suggested = [index - 1 for index in trip.order if index != 0]
        method, suggested_s, geometry = "osrm", trip.route.duration_s, trip.route.polyline
    else:
        suggested = nearest_neighbour(start, points)
        legs, road = await road_leg_minutes(settings, [start, *(points[i] for i in suggested)])
        method = "nearest_neighbor"
        suggested_s = sum(legs) * 60
        geometry = road.polyline if road else None
    current_s = current_road.duration_s if current_road else sum(current_legs) * 60
    current_ids = [stop.id for stop in stops]
    suggested_ids = [stops[index].id for index in suggested]
    current_geometry = current_road.polyline if current_road else None
    # Keep the current order when the suggestion is not clearly faster (avoid churn).
    changed = suggested_ids != current_ids and suggested_s < current_s - 60
    return OptimizeOut(
        method=method,
        current_stop_ids=current_ids,
        suggested_stop_ids=suggested_ids if changed else current_ids,
        current_duration_s=round(current_s),
        suggested_duration_s=round(suggested_s if changed else current_s),
        suggested_geometry=geometry if changed else current_geometry,
        changed=changed,
    )


# =============================== Commands ===============================


async def save_stop_order(
    session: AsyncSession, manager: CurrentUser, route_id: uuid.UUID, stop_ids: list[uuid.UUID]
) -> RouteDetailOut:
    """Store a new order of the pending stops, recompute ETAs and tell the driver."""
    hub_id = require_hub(manager)
    settings = await load_business_settings(session)
    route = await _hub_route(session, hub_id, route_id)
    await reorder_stops(session, route.driver_id, stop_ids)
    changed = await refresh_driver_etas(
        session, route.driver_id, settings, reason="The hub changed the delivery order."
    )
    await session.commit()
    await notify_user(route.driver_id, "route.updated", {"route_id": str(route.id)})
    await notify_hub(hub_id, "route.updated", {"route_id": str(route.id)})
    for order in changed:
        await publish_order_update(order)
    logger.info("[save_stop_order] route=%s stops=%d by=%s", route.id, len(stop_ids), manager.id)
    return await route_detail(session, hub_id, route.id)
