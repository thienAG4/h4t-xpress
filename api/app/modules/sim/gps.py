"""GPS simulator (SPEC §7.2, S-04): drivers on the road move along the OSRM road geometry
and deliver when they reach a stop. Demo deployments only; switched by `sim.gps_enabled`.

It never answers offers and never moves the shared accounts driver1 and driver2, nor any
driver whose app sent a heartbeat in the last 90 seconds (a person is using it). The
"traffic jam" scenario holds one driver still, so the anomaly scan raises DRIVER_IDLE.
"""

import logging
import math
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, utc_now
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.delivery import service as delivery
from app.modules.delivery.schemas import DeliverIn, FailIn
from app.modules.files.models import File, FileStorage
from app.modules.files.service import file_url
from app.modules.hubs.models import Hub
from app.modules.orders.models import FailureReason, Order, OrderStatus
from app.modules.orders.service import publish_order_update
from app.modules.realtime.hub import notify_hub
from app.modules.routing.osrm import Point, decode_polyline, osrm
from app.modules.routing.service import pending_stops
from app.modules.settings.models import SystemSetting
from app.modules.settings.service import get_setting, load_business_settings
from app.modules.tracking.models import DriverLocation
from app.modules.tracking.service import refresh_driver_etas
from app.modules.users.models import DriverProfile, User

logger = logging.getLogger(__name__)

TICK_SECONDS = 3.0
BASE_SPEED_KMH = 28.0
ARRIVE_METERS = 25.0
ETA_REFRESH_SECONDS = 30.0
FAIL_RATE = 0.1
HUMAN_IDLE = timedelta(seconds=90)
HUMAN_ACCOUNTS = ("driver1@demo.h4t", "driver2@demo.h4t")
PROOF_KEY = "sim/proof-of-delivery.jpg"


def _meters(a: Point, b: Point) -> float:
    d_lat = (b[0] - a[0]) * 111_320
    d_lng = (b[1] - a[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(d_lat, d_lng)


def _advance(path: list[Point], meters: float) -> list[Point]:
    """Walk `meters` along the path; returns the rest of the path, current point first."""
    while meters > 0 and len(path) > 1:
        segment = _meters(path[0], path[1])
        if segment <= meters:
            meters -= segment
            path = path[1:]
        else:
            share = meters / segment
            here = (
                path[0][0] + (path[1][0] - path[0][0]) * share,
                path[0][1] + (path[1][1] - path[0][1]) * share,
            )
            path = [here, *path[1:]]
            meters = 0
    return path


def ensure_proof_photo() -> None:
    """A neutral picture used as proof of delivery for simulated drivers."""
    target = Path(get_settings().upload_dir) / PROOF_KEY
    if target.exists():
        return
    from PIL import Image, ImageDraw  # reportlab already depends on Pillow

    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (640, 480), (234, 242, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((200, 150, 440, 330), fill=(196, 160, 112), outline=(120, 90, 50), width=4)
    draw.line((200, 200, 440, 200), fill=(120, 90, 50), width=3)
    draw.text((210, 360), "Delivered - GPS simulator (demo)", fill=(16, 112, 248))
    image.save(target, "JPEG", quality=85)


@dataclass
class _Leg:
    stop_id: uuid.UUID
    path: list[Point]


class GpsSimulator:
    def __init__(self) -> None:
        self._legs: dict[uuid.UUID, _Leg] = {}
        self._eta_refreshed: dict[uuid.UUID, float] = {}
        self._rng = random.Random()

    def forget(self) -> None:
        """Drop cached legs, e.g. after the demo data was reloaded."""
        self._legs.clear()
        self._eta_refreshed.clear()

    # =============================== Settings ===============================

    @staticmethod
    async def paused_until(session: AsyncSession) -> dict[str, str]:
        value = await get_setting(session, "sim.paused_drivers", {})
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    async def set_setting(session: AsyncSession, key: str, value: object) -> None:
        row = await session.get(SystemSetting, key)
        if row is None:
            session.add(SystemSetting(key=key, value=value, description=key))
        else:
            row.value = value

    # =============================== Tick ===============================

    async def simulated_drivers(self, session: AsyncSession) -> list[uuid.UUID]:
        """Drivers out for delivery that nobody is driving by hand."""
        rows = await session.scalars(
            select(Order.current_driver_id)
            .join(User, User.id == Order.current_driver_id)
            .join(DriverProfile, DriverProfile.user_id == User.id)
            .where(
                Order.status == OrderStatus.OUT_FOR_DELIVERY,
                User.email.not_in(HUMAN_ACCOUNTS),
                (DriverProfile.last_seen_at.is_(None))
                | (DriverProfile.last_seen_at < utc_now() - HUMAN_IDLE),
            )
            .distinct()
        )
        return [driver_id for driver_id in rows if driver_id is not None]

    async def tick(self) -> int:
        """Move every simulated driver once. Returns how many moved or delivered."""
        if not get_settings().demo_mode:
            return 0
        async with SessionLocal() as session:
            if not await get_setting(session, "sim.gps_enabled", False):
                return 0
            factor = float(await get_setting(session, "sim.speed_factor", 4))
            paused = await self.paused_until(session)
            drivers = await self.simulated_drivers(session)
        moved = 0
        hubs: set[uuid.UUID] = set()
        for driver_id in drivers:
            async with SessionLocal() as session:
                hold = paused.get(str(driver_id))
                still = hold is not None and datetime.fromisoformat(hold) > utc_now()
                hub_id = await self._step(session, driver_id, factor, still)
                if hub_id is not None:
                    hubs.add(hub_id)
                    moved += 1
        for hub_id in hubs:
            await notify_hub(hub_id, "driver.location", {"drivers": moved})
        return moved

    async def _step(
        self, session: AsyncSession, driver_id: uuid.UUID, factor: float, still: bool
    ) -> uuid.UUID | None:
        profile = await session.get(DriverProfile, driver_id)
        if profile is None:
            return None
        orders = list(
            await session.scalars(
                select(Order).where(
                    Order.current_driver_id == driver_id,
                    Order.status == OrderStatus.OUT_FOR_DELIVERY,
                )
            )
        )
        stop_ids = {order.route_stop_id for order in orders}
        stop = next((s for s in await pending_stops(session, driver_id) if s.id in stop_ids), None)
        if stop is None or not orders:
            return None
        hub = await session.get(Hub, orders[0].hub_id)
        assert hub is not None
        here: Point = (
            (profile.last_lat, profile.last_lng)
            if profile.last_lat is not None and profile.last_lng is not None
            else (hub.lat, hub.lng)
        )
        target: Point = (stop.lat, stop.lng)

        if still:
            # Traffic jam scenario: keep reporting the same position (BR12 needs GPS points).
            session.add(
                DriverLocation(
                    driver_id=driver_id,
                    lat=here[0],
                    lng=here[1],
                    speed_kmh=0,
                    recorded_at=utc_now(),
                )
            )
            await session.commit()
            return hub.id

        leg = self._legs.get(driver_id)
        if leg is None or leg.stop_id != stop.id:
            road = await osrm.route([here, target])
            path = decode_polyline(road.polyline) if road and road.polyline else []
            leg = _Leg(stop.id, [here, *path[1:], target] if path else [here, target])
            self._legs[driver_id] = leg
        speed = BASE_SPEED_KMH * self._rng.uniform(0.8, 1.2)
        leg.path = _advance(leg.path, speed * factor * TICK_SECONDS / 3.6)
        position = leg.path[0]
        profile.last_lat, profile.last_lng = round(position[0], 6), round(position[1], 6)
        session.add(
            DriverLocation(
                driver_id=driver_id,
                lat=profile.last_lat,
                lng=profile.last_lng,
                speed_kmh=round(speed, 1),
                recorded_at=utc_now(),
            )
        )

        if len(leg.path) == 1 or _meters(position, target) <= ARRIVE_METERS:
            await session.commit()
            self._legs.pop(driver_id, None)
            await self._arrive(
                session, driver_id, [o for o in orders if o.route_stop_id == stop.id]
            )
            return hub.id

        if time.monotonic() - self._eta_refreshed.get(driver_id, 0) >= ETA_REFRESH_SECONDS:
            self._eta_refreshed[driver_id] = time.monotonic()
            settings = await load_business_settings(session)
            changed = await refresh_driver_etas(session, driver_id, settings)
            await session.commit()
            for order in changed:
                await publish_order_update(order)
        else:
            await session.commit()
        return hub.id

    async def _arrive(
        self, session: AsyncSession, driver_id: uuid.UUID, orders: list[Order]
    ) -> None:
        """At the door: deliver with the simulator photo, or (sometimes) nobody is home."""
        ensure_proof_photo()
        for order in orders:
            if self._rng.random() < FAIL_RATE:
                await delivery.fail(
                    session,
                    driver_id,
                    order.id,
                    FailIn(
                        reason=FailureReason.CUSTOMER_ABSENT,
                        note="Simulated: nobody at home",
                        proposed_date=local_today() + timedelta(days=1),
                        lat=order.delivery_lat,
                        lng=order.delivery_lng,
                    ),
                )
                continue
            photo_id = uuid.uuid4()
            session.add(
                File(
                    id=photo_id,
                    owner_user_id=driver_id,
                    storage=FileStorage.LOCAL,
                    key=PROOF_KEY,
                    url=file_url(photo_id),
                    mime="image/jpeg",
                    size_bytes=(Path(get_settings().upload_dir) / PROOF_KEY).stat().st_size,
                )
            )
            await session.flush()
            await delivery.deliver(
                session,
                driver_id,
                order.id,
                DeliverIn(
                    photo_file_ids=[photo_id],
                    note="Delivered by the GPS simulator",
                    lat=order.delivery_lat,
                    lng=order.delivery_lng,
                ),
            )
        logger.info("[gps_sim] driver=%s reached a stop with %d order(s)", driver_id, len(orders))


gps = GpsSimulator()
