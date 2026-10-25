"""Read tunable business parameters from system_settings, with code defaults.

`load_business_settings` reads every key once per use case, so a dispatch round or an
ETA refresh sees one consistent set of values.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import SystemSetting


async def get_setting(session: AsyncSession, key: str, default: Any) -> Any:
    value = await session.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    return default if value is None else value


@dataclass(frozen=True)
class BusinessSettings:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "distance": 0.4,
            "load": 0.25,
            "performance": 0.2,
            "time_fit": 0.15,
        }
    )
    offer_timeout_s: int = 600
    max_candidates_per_round: int = 5
    max_rounds: int = 3
    round_retry_delay_s: int = 300
    max_active_orders: int = 20
    max_distance_km: float = 15
    location_fresh_min: int = 10
    enforce_shift_hours: bool = True
    service_time_min: float = 5
    traffic_factors: list[dict[str, Any]] = field(default_factory=list)
    default_traffic_factor: float = 1.1
    notify_threshold_min: float = 15
    fallback_speed_kmh: float = 25
    fallback_road_factor: float = 1.4
    sla_grace_min: int = 120
    max_attempts: int = 3


_KEYS = {
    "dispatch.weights": "weights",
    "dispatch.offer_timeout_s": "offer_timeout_s",
    "dispatch.max_candidates_per_round": "max_candidates_per_round",
    "dispatch.max_rounds": "max_rounds",
    "dispatch.round_retry_delay_s": "round_retry_delay_s",
    "dispatch.max_active_orders": "max_active_orders",
    "dispatch.max_distance_km": "max_distance_km",
    "dispatch.location_fresh_min": "location_fresh_min",
    "dispatch.enforce_shift_hours": "enforce_shift_hours",
    "eta.service_time_min": "service_time_min",
    "eta.traffic_factors": "traffic_factors",
    "eta.default_traffic_factor": "default_traffic_factor",
    "eta.notify_threshold_min": "notify_threshold_min",
    "eta.fallback_speed_kmh": "fallback_speed_kmh",
    "eta.fallback_road_factor": "fallback_road_factor",
    "sla.grace_min": "sla_grace_min",
    "delivery.max_attempts": "max_attempts",
}


async def load_business_settings(session: AsyncSession) -> BusinessSettings:
    rows = await session.execute(
        select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(_KEYS))
    )
    values = {_KEYS[key]: value for key, value in rows if value is not None}
    return BusinessSettings(**values)
