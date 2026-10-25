"""Distance and travel-time helpers: dispatch scoring and the ETA fallback when OSRM fails.

The fallback is deliberately simple and flags orders `eta_degraded`: straight-line
distance x road factor at an average urban speed, times a rush-hour factor.
"""

import math
from datetime import datetime

from app.core.clock import BUSINESS_TZ

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def traffic_factor(at: datetime, rules: list[dict[str, object]], default: float) -> float:
    """Rush-hour multiplier from settings: [{"from": "07:00", "to": "09:00", "factor": 1.5}]."""
    local = at.astimezone(BUSINESS_TZ).strftime("%H:%M")
    for rule in rules:
        if str(rule["from"]) <= local < str(rule["to"]):
            return float(str(rule["factor"]))
    return default


def travel_minutes(
    distance_km: float, *, speed_kmh: float, road_factor: float, factor: float
) -> float:
    return distance_km * road_factor / speed_kmh * 60 * factor
