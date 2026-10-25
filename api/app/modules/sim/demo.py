"""Demo control panel (S-04): GPS simulator switch, traffic-jam scenario, data reset.

Everything here exists only when DEMO_MODE is on. The daily reset (03:00 business time)
is opt-in with DEMO_DAILY_RESET, so a developer's local data is never wiped by surprise.
"""

import logging
import uuid
from datetime import timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_now, local_today, utc_now
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import ValidationFailed
from app.modules.hubs.models import Hub
from app.modules.orders.models import Order, OrderStatus
from app.modules.settings.service import get_setting
from app.modules.sim.gps import gps
from app.modules.users.models import User
from app.seed.runner import run_seed

logger = logging.getLogger(__name__)

RESET_HOUR = 3


class SimulatedDriverOut(BaseModel):
    driver_id: uuid.UUID
    name: str
    hub: str
    orders_left: int
    stuck_until: str | None


class DemoStatusOut(BaseModel):
    gps_enabled: bool
    speed_factor: float
    idle_minutes: float
    daily_reset: bool
    drivers: list[SimulatedDriverOut]


async def status(session: AsyncSession) -> DemoStatusOut:
    paused = await gps.paused_until(session)
    driver_ids = await gps.simulated_drivers(session)
    rows = await session.execute(
        select(User.id, User.full_name, Hub.name, func.count(Order.id))
        .join(Order, Order.current_driver_id == User.id)
        .join(Hub, Hub.id == Order.hub_id)
        .where(User.id.in_(driver_ids), Order.status == OrderStatus.OUT_FOR_DELIVERY)
        .group_by(User.id, User.full_name, Hub.name)
        .order_by(Hub.name, User.full_name)
    )
    now = utc_now().isoformat()
    return DemoStatusOut(
        gps_enabled=bool(await get_setting(session, "sim.gps_enabled", False)),
        speed_factor=float(await get_setting(session, "sim.speed_factor", 4)),
        idle_minutes=float(await get_setting(session, "anomaly.idle_minutes", 15)),
        daily_reset=get_settings().demo_daily_reset,
        drivers=[
            SimulatedDriverOut(
                driver_id=driver_id,
                name=name,
                hub=hub,
                orders_left=count,
                stuck_until=paused.get(str(driver_id))
                if paused.get(str(driver_id), "") > now
                else None,
            )
            for driver_id, name, hub, count in rows
        ],
    )


async def set_gps(session: AsyncSession, enabled: bool) -> DemoStatusOut:
    await gps.set_setting(session, "sim.gps_enabled", enabled)
    await session.commit()
    logger.info("[demo] GPS simulator %s", "on" if enabled else "off")
    return await status(session)


async def traffic_jam(session: AsyncSession, driver_id: uuid.UUID | None) -> DemoStatusOut:
    """Hold one simulated driver still long enough for the anomaly scan to notice (BR12)."""
    candidates = await gps.simulated_drivers(session)
    if not candidates:
        raise ValidationFailed("No simulated driver is on the road", code="NO_SIMULATED_DRIVER")
    chosen = driver_id or candidates[0]
    if chosen not in candidates:
        raise ValidationFailed("This driver is not simulated", code="NO_SIMULATED_DRIVER")
    idle = float(await get_setting(session, "anomaly.idle_minutes", 15))
    paused = await gps.paused_until(session)
    paused[str(chosen)] = (utc_now() + timedelta(minutes=idle + 2)).isoformat()
    await gps.set_setting(session, "sim.paused_drivers", paused)
    await session.commit()
    logger.info("[demo] traffic jam for driver=%s (%.0f min)", chosen, idle + 2)
    return await status(session)


async def reset_demo_data() -> dict[str, int] | None:
    """Reload the demo data set (same as `python -m app.seed --reset`)."""
    counts = await run_seed(reset=True)
    gps.forget()  # cached legs belong to drivers that no longer exist
    logger.info("[demo] data reset: %s rows", sum((counts or {}).values()))
    return counts


async def maybe_daily_reset() -> bool:
    """Called every minute by the worker; resets once a day after 03:00 when enabled."""
    settings = get_settings()
    if not (settings.demo_mode and settings.demo_daily_reset) or local_now().hour != RESET_HOUR:
        return False
    async with SessionLocal() as session:
        last = await get_setting(session, "sim.last_reset", None)
    if last == local_today().isoformat():
        return False
    await reset_demo_data()
    async with SessionLocal() as session:
        await gps.set_setting(session, "sim.last_reset", local_today().isoformat())
        await session.commit()
    return True
