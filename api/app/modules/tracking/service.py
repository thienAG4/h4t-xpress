"""Driver presence (heartbeat, GPS) and ETA estimates for each driver's route.

Until OSRM arrives (Phase 3) the ETA uses straight-line distance x road factor at an
average speed with rush-hour multipliers, so every estimate is flagged `eta_degraded`.
"""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.geo import haversine_km, traffic_factor, travel_minutes
from app.modules.hubs.models import Hub
from app.modules.orders.models import ActorType, EtaSource, Order, OrderEventType, OrderStatus
from app.modules.orders.service import ACTIVE_DRIVER_STATUSES, add_event
from app.modules.partner.webhooks import ETA_CHANGED, notify_partner
from app.modules.routing.service import pending_stops
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


def _minutes(
    settings: BusinessSettings, at: datetime, a: tuple[float, float], b: tuple[float, float]
) -> float:
    factor = traffic_factor(at, settings.traffic_factors, settings.default_traffic_factor)
    return travel_minutes(
        haversine_km(*a, *b),
        speed_kmh=settings.fallback_speed_kmh,
        road_factor=settings.fallback_road_factor,
        factor=factor,
    )


async def estimate_driver_etas(
    session: AsyncSession, driver_id: uuid.UUID, settings: BusinessSettings
) -> dict[uuid.UUID, datetime]:
    """ETA per active order of the driver: pickup first if needed, then stops in order."""
    orders = list(
        await session.scalars(
            select(Order).where(
                Order.current_driver_id == driver_id, Order.status.in_(ACTIVE_DRIVER_STATUSES)
            )
        )
    )
    if not orders:
        return {}
    hub = await session.get(Hub, orders[0].hub_id)
    hub_point = (hub.lat, hub.lng) if hub else (orders[0].delivery_lat, orders[0].delivery_lng)
    position = await driver_position(session, driver_id, hub_point)
    clock = utc_now()

    # Hand-over orders are collected from the previous driver, others at the hub.
    pickups: list[tuple[float, float]] = []
    for order in orders:
        if order.status != OrderStatus.ASSIGNED:
            continue
        point = hub_point
        if order.handover_from_driver_id:
            point = await driver_position(session, order.handover_from_driver_id, hub_point)
        if point not in pickups:
            pickups.append(point)
    for point in pickups:
        clock += timedelta(minutes=_minutes(settings, clock, position, point) + LOADING_MINUTES)
        position = point

    etas: dict[uuid.UUID, datetime] = {}
    by_stop: dict[uuid.UUID, list[Order]] = {}
    for order in orders:
        if order.route_stop_id:
            by_stop.setdefault(order.route_stop_id, []).append(order)
    for stop in await pending_stops(session, driver_id):
        stop_orders = by_stop.get(stop.id, [])
        if not stop_orders:
            continue
        clock += timedelta(minutes=_minutes(settings, clock, position, (stop.lat, stop.lng)))
        stop.eta = clock
        for order in stop_orders:
            etas[order.id] = clock
        clock += timedelta(minutes=settings.service_time_min)
        position = (stop.lat, stop.lng)
    return etas


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
    etas = await estimate_driver_etas(session, driver_id, settings)
    changed: list[Order] = []
    for order_id, eta in etas.items():
        order = await session.get(Order, order_id)
        if order is None or order.eta_source == EtaSource.MANUAL:
            continue
        previous = order.current_eta
        order.current_eta = eta
        order.eta_source = EtaSource.SYSTEM
        order.eta_degraded = True
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
