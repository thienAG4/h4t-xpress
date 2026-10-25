"""Driver presence (heartbeat, GPS) and ETA estimates for each driver's route (SPEC §3.3).

ETA = road duration of each leg (OSRM) x rush-hour factor + loading and service time.
When OSRM is unavailable the road duration falls back to straight-line distance x road
factor at an average speed, and the orders are flagged `eta_degraded` ("estimate").
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.geo import haversine_km, traffic_factor, travel_minutes
from app.modules.hubs.models import Hub
from app.modules.orders.models import ActorType, EtaSource, Order, OrderEventType, OrderStatus
from app.modules.orders.service import ACTIVE_DRIVER_STATUSES, add_event
from app.modules.partner.webhooks import ETA_CHANGED, notify_partner
from app.modules.routing.osrm import Point, RoadRoute, osrm
from app.modules.routing.service import pending_stops, today_route
from app.modules.settings.service import BusinessSettings
from app.modules.tracking.models import DriverLocation
from app.modules.users.models import DriverProfile

logger = logging.getLogger(__name__)

LOADING_MINUTES = 10  # scanning parcels at the hub or at a hand-over point


# =============================== Presence ===============================


async def heartbeat(
    session: AsyncSession,
    driver_id: uuid.UUID,
    *,
    lat: float | None,
    lng: float | None,
    accuracy_m: float | None,
) -> None:
    """The driver app is open. Coordinates are optional (the browser may refuse GPS)."""
    profile = await session.get(DriverProfile, driver_id)
    if profile is None:
        return
    now = utc_now()
    profile.last_seen_at = now
    if lat is not None and lng is not None:
        profile.last_lat, profile.last_lng = lat, lng
        session.add(
            DriverLocation(
                driver_id=driver_id, lat=lat, lng=lng, accuracy_m=accuracy_m, recorded_at=now
            )
        )
    await session.commit()


async def driver_position(
    session: AsyncSession, driver_id: uuid.UUID, fallback: tuple[float, float]
) -> tuple[float, float]:
    profile = await session.get(DriverProfile, driver_id)
    if profile and profile.last_lat is not None and profile.last_lng is not None:
        return profile.last_lat, profile.last_lng
    return fallback


# =============================== ETA ===============================


@dataclass
class EtaPlan:
    etas: dict[uuid.UUID, datetime] = field(default_factory=dict)
    degraded: bool = True
    road: RoadRoute | None = None


async def road_leg_minutes(
    settings: BusinessSettings, points: list[Point]
) -> tuple[list[float], RoadRoute | None]:
    """Free-flow minutes of each leg points[i] -> points[i + 1]; OSRM, else straight line."""
    road = await osrm.route(points)
    if road is not None and len(road.leg_durations_s) == len(points) - 1:
        return [seconds / 60 for seconds in road.leg_durations_s], road
    minutes = [
        travel_minutes(
            haversine_km(*a, *b),
            speed_kmh=settings.fallback_speed_kmh,
            road_factor=settings.fallback_road_factor,
            factor=1.0,
        )
        for a, b in pairwise(points)
    ]
    return minutes, None


def _with_traffic(settings: BusinessSettings, at: datetime, minutes: float) -> float:
    return minutes * traffic_factor(at, settings.traffic_factors, settings.default_traffic_factor)


async def estimate_driver_etas(
    session: AsyncSession, driver_id: uuid.UUID, settings: BusinessSettings
) -> EtaPlan:
    """ETA per active order of the driver: pickups first if needed, then stops in order."""
    orders = list(
        await session.scalars(
            select(Order).where(
                Order.current_driver_id == driver_id, Order.status.in_(ACTIVE_DRIVER_STATUSES)
            )
        )
    )
    if not orders:
        return EtaPlan()
    hub = await session.get(Hub, orders[0].hub_id)
    hub_point = (hub.lat, hub.lng) if hub else (orders[0].delivery_lat, orders[0].delivery_lng)
    position = await driver_position(session, driver_id, hub_point)

    # Hand-over orders are collected from the previous driver, others at the hub.
    pickups: list[Point] = []
    for order in orders:
        if order.status != OrderStatus.ASSIGNED:
            continue
        point = hub_point
        if order.handover_from_driver_id:
            point = await driver_position(session, order.handover_from_driver_id, hub_point)
        if point not in pickups:
            pickups.append(point)
    by_stop: dict[uuid.UUID, list[Order]] = {}
    for order in orders:
        if order.route_stop_id:
            by_stop.setdefault(order.route_stop_id, []).append(order)
    stops = [stop for stop in await pending_stops(session, driver_id) if stop.id in by_stop]

    points: list[Point] = [position, *pickups, *((stop.lat, stop.lng) for stop in stops)]
    legs, road = await road_leg_minutes(settings, points)
    plan = EtaPlan(degraded=road is None, road=road)
    clock = utc_now()
    for leg in legs[: len(pickups)]:
        clock += timedelta(minutes=_with_traffic(settings, clock, leg) + LOADING_MINUTES)
    for stop, leg in zip(stops, legs[len(pickups) :], strict=False):
        clock += timedelta(minutes=_with_traffic(settings, clock, leg))
        stop.eta = clock
        for order in by_stop[stop.id]:
            plan.etas[order.id] = clock
        clock += timedelta(minutes=settings.service_time_min)
    return plan


async def refresh_driver_etas(
    session: AsyncSession,
    driver_id: uuid.UUID,
    settings: BusinessSettings,
    *,
    reason: str | None = None,
) -> list[Order]:
    """Store new system ETAs (manual ones are kept) and tell the partner about big changes.

    Returns the orders whose ETA moved by at least `eta.notify_threshold_min` minutes.
    The caller commits.
    """
    plan = await estimate_driver_etas(session, driver_id, settings)
    route = await today_route(session, driver_id)
    if route is not None:
        # Remaining path from the driver's position, drawn on the maps (D-07, H-02, H-03).
        route.polyline = plan.road.polyline if plan.road else None
        route.total_distance_m = round(plan.road.distance_m) if plan.road else None
        route.total_duration_s = round(plan.road.duration_s) if plan.road else None
    changed: list[Order] = []
    for order_id, eta in plan.etas.items():
        order = await session.get(Order, order_id)
        if order is None or order.eta_source == EtaSource.MANUAL:
            continue
        previous = order.current_eta
        order.current_eta = eta
        order.eta_source = EtaSource.SYSTEM
        order.eta_degraded = plan.degraded
        moved = (
            previous is None
            or abs((eta - previous).total_seconds()) >= settings.notify_threshold_min * 60
        )
        if moved and order.status == OrderStatus.OUT_FOR_DELIVERY:
            add_event(
                session,
                order,
                OrderEventType.ETA_CHANGED,
                actor_type=ActorType.SYSTEM,
                payload={
                    "eta": eta.isoformat(),
                    "previous": previous.isoformat() if previous else None,
                },
            )
            notify_partner(session, order, ETA_CHANGED, message=reason)
            changed.append(order)
    return changed
