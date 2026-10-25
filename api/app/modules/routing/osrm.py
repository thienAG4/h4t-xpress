"""OSRM client (SPEC §5.7): road durations, route geometry and the best visiting order.

Every call is short (a few seconds at most) and never raises: on a timeout, an HTTP error
or an "NoRoute" answer it returns None and the caller falls back to straight-line
estimates (NFR-04). After a failure OSRM is skipped for a minute, so a slow public
server cannot slow down accepting an offer or delivering a parcel.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

Point = tuple[float, float]  # (lat, lng)

COOL_DOWN_S = 60
CACHE_TTL_S = 300
CACHE_SIZE = 256


@dataclass(frozen=True)
class RoadRoute:
    leg_durations_s: list[float]
    duration_s: float
    distance_m: float
    polyline: str  # Google encoded polyline, precision 5


@dataclass(frozen=True)
class Trip:
    order: list[int]  # indexes of the input points, starting point first
    route: RoadRoute


class OsrmClient:
    def __init__(self) -> None:
        self._down_until = 0.0
        self._cache: dict[str, tuple[float, RoadRoute]] = {}
        self._http: httpx.AsyncClient | None = None

    def use_client(self, http: httpx.AsyncClient | None) -> None:
        """Tests inject an httpx client with a mock transport."""
        self._http = http
        self._cache.clear()
        self._down_until = 0.0

    @property
    def available(self) -> bool:
        return get_settings().osrm_enabled and time.monotonic() >= self._down_until

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        if not self.available:
            return None
        settings = get_settings()
        url = f"{settings.osrm_url.rstrip('/')}{path}"
        try:
            if self._http is not None:
                response = await self._http.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=settings.osrm_timeout_s) as http:
                    response = await http.get(url, params=params)
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "[osrm] %s failed: %s; straight-line estimates for %ss", path, exc, COOL_DOWN_S
            )
            self._down_until = time.monotonic() + COOL_DOWN_S
            return None
        if response.status_code != 200 or data.get("code") != "Ok":
            logger.info("[osrm] %s answered %s %s", path, response.status_code, data.get("code"))
            return None
        return dict(data)

    @staticmethod
    def _coordinates(points: list[Point]) -> str:
        # OSRM expects lng,lat pairs.
        return ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in points)

    @staticmethod
    def _road_route(raw: dict[str, Any]) -> RoadRoute:
        legs = raw.get("legs") or []
        return RoadRoute(
            leg_durations_s=[float(leg["duration"]) for leg in legs],
            duration_s=float(raw["duration"]),
            distance_m=float(raw["distance"]),
            polyline=str(raw.get("geometry") or ""),
        )

    async def route(self, points: list[Point]) -> RoadRoute | None:
        """Driving route through the points in the given order."""
        if len(points) < 2:
            return None
        key = self._coordinates(points)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_S:
            return cached[1]
        data = await self._get(
            f"/route/v1/driving/{key}", {"overview": "full", "geometries": "polyline"}
        )
        routes = data.get("routes") if data else None
        if not routes:
            return None
        result = self._road_route(routes[0])
        if len(self._cache) >= CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = (time.monotonic(), result)
        return result

    async def trip(self, points: list[Point]) -> Trip | None:
        """Fastest order to visit every point, starting at the first one, not returning."""
        if len(points) < 3:
            return None
        data = await self._get(
            f"/trip/v1/driving/{self._coordinates(points)}",
            {
                "source": "first",
                "roundtrip": "false",
                "overview": "full",
                "geometries": "polyline",
            },
        )
        if not data or not data.get("trips"):
            return None
        waypoints = data["waypoints"]
        # waypoint_index is the position of each input point in the optimised trip.
        positions = [int(w["waypoint_index"]) for w in waypoints]
        order = sorted(range(len(points)), key=lambda index: positions[index])
        return Trip(order=order, route=self._road_route(data["trips"][0]))


osrm = OsrmClient()


def decode_polyline(encoded: str) -> list[Point]:
    """Google polyline (precision 5) -> [(lat, lng)]. Used by tests and the GPS simulator."""
    points: list[Point] = []
    index = lat = lng = 0
    while index < len(encoded):
        values = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        lat += values[0]
        lng += values[1]
        points.append((lat / 1e5, lng / 1e5))
    return points
