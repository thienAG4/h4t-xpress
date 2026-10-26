"""Anomaly scan run by the worker every minute (BR12, EX5, EX6).

- DRIVER_IDLE: a driver out for delivery has not moved more than `anomaly.idle_radius_m`
  during the last `anomaly.idle_minutes`, with GPS points covering the whole window.
- ETA_ANOMALY: an order's ETA was pushed back `anomaly.eta_increase_count` times in a row
  within the last hour, by `anomaly.eta_increase_total_min` minutes or more in total.

A driver with an open incident is skipped, so one problem raises one incident.
"""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.geo import haversine_km
from app.modules.incidents.models import Incident, IncidentType
from app.modules.incidents.service import OPEN_STATUSES, raise_system_incident
from app.modules.orders.models import Order, OrderEvent, OrderEventType, OrderStatus
from app.modules.settings.service import get_setting
from app.modules.tracking.models import DriverLocation

logger = logging.getLogger(__name__)

ETA_LOOKBACK = timedelta(hours=1)


def _has_open_incident() -> object:
    return exists(
        select(Incident.id).where(
            Incident.driver_id == Order.current_driver_id, Incident.status.in_(OPEN_STATUSES)
        )
    )


async def _orders_on_road(session: AsyncSession) -> dict[uuid.UUID, list[Order]]:
    orders = await session.scalars(
        select(Order).where(
            Order.status == OrderStatus.OUT_FOR_DELIVERY,
            Order.current_driver_id.is_not(None),
            Order.active_incident_id.is_(None),
            ~_has_open_incident(),  # type: ignore[operator]
        )
    )
    by_driver: dict[uuid.UUID, list[Order]] = {}
    for order in orders:
        assert order.current_driver_id is not None
        by_driver.setdefault(order.current_driver_id, []).append(order)
    return by_driver


async def _is_idle(
    session: AsyncSession, driver_id: uuid.UUID, since: datetime, radius_m: float
) -> tuple[float, float] | None:
    """Position of an idle driver, or None while they keep moving (or GPS is missing)."""
    points = list(
        await session.execute(
            select(DriverLocation.lat, DriverLocation.lng, DriverLocation.recorded_at)
            .where(DriverLocation.driver_id == driver_id, DriverLocation.recorded_at >= since)
            .order_by(DriverLocation.recorded_at)
        )
    )
    if len(points) < 3 or points[0][2] > since + timedelta(minutes=1):
        return None  # not enough GPS to cover the window
    first = (points[0][0], points[0][1])
    if all(haversine_km(*first, lat, lng) * 1000 <= radius_m for lat, lng, _ in points):
        return points[-1][0], points[-1][1]
    return None


def _eta_slips(events: list[OrderEvent], count: int, total_min: float) -> bool:
    """The last `count` ETA changes all moved later and add up to `total_min` or more."""
    changes: list[tuple[datetime, datetime]] = []
    for event in events[-count:]:
        eta, previous = event.payload.get("eta"), event.payload.get("previous")
        if not eta or not previous:
            return False
        changes.append((datetime.fromisoformat(previous), datetime.fromisoformat(eta)))
    if len(changes) < count or any(new <= old for old, new in changes):
        return False
    return (changes[-1][1] - changes[0][0]) >= timedelta(minutes=total_min)


async def scan(session: AsyncSession) -> list[Incident]:
    idle_minutes = float(await get_setting(session, "anomaly.idle_minutes", 15))
    radius_m = float(await get_setting(session, "anomaly.idle_radius_m", 50))
    slip_count = int(await get_setting(session, "anomaly.eta_increase_count", 3))
    slip_total = float(await get_setting(session, "anomaly.eta_increase_total_min", 30))
    now = utc_now()
    raised: list[Incident] = []

    for driver_id, orders in (await _orders_on_road(session)).items():
        position = await _is_idle(
            session, driver_id, now - timedelta(minutes=idle_minutes), radius_m
        )
        if position is not None:
            raised.append(
                await raise_system_incident(
                    session,
                    driver_id=driver_id,
                    hub_id=orders[0].hub_id,
                    kind=IncidentType.DRIVER_IDLE,
                    description=(
                        f"Detected by the system: the driver has not moved more than "
                        f"{radius_m:.0f} m for {idle_minutes:.0f} minutes while out for delivery."
                    ),
                    orders=orders,
                    lat=position[0],
                    lng=position[1],
                )
            )
            continue

        slipping = []
        for order in orders:
            events = list(
                await session.scalars(
                    select(OrderEvent)
                    .where(
                        OrderEvent.order_id == order.id,
                        OrderEvent.type == OrderEventType.ETA_CHANGED,
                        OrderEvent.created_at >= now - ETA_LOOKBACK,
                    )
                    .order_by(OrderEvent.created_at)
                )
            )
            if _eta_slips(events, slip_count, slip_total):
                slipping.append(order)
        if slipping:
            raised.append(
                await raise_system_incident(
                    session,
                    driver_id=driver_id,
                    hub_id=slipping[0].hub_id,
                    kind=IncidentType.ETA_ANOMALY,
                    description=(
                        f"Detected by the system: the ETA was pushed back {slip_count} times "
                        f"in a row, {slip_total:.0f} minutes or more in total."
                    ),
                    orders=slipping,
                )
            )
    if raised:
        logger.info("[anomaly_scan] raised %d incident(s)", len(raised))
    return raised
