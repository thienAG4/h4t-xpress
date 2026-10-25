import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class Granularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ReportScope(BaseModel):
    date_from: date
    date_to: date
    hub_ids: list[uuid.UUID]  # empty = every hub the user may see
    hub_names: list[str]
    previous_from: date
    previous_to: date


class KpiOut(BaseModel):
    """One KPI card: the value for the period and the same measure for the period before."""

    value: float | None
    previous: float | None


class SummaryOut(BaseModel):
    scope: ReportScope
    total_orders: KpiOut
    delivered: KpiOut
    success_rate: KpiOut  # delivered / (delivered + returned)
    failed_attempt_rate: KpiOut  # failed attempts / all attempts
    on_time_rate: KpiOut  # delivered within promised_at + grace / delivered
    avg_delivery_minutes: KpiOut  # created -> delivered
    incidents: KpiOut
    active_drivers: KpiOut
    total_drivers: int


class VolumePoint(BaseModel):
    period: date
    label: str
    orders: int
    delivered: int


class ShareRow(BaseModel):
    key: str
    label: str
    count: int
    share: float


class AreaRow(BaseModel):
    area: str
    delivered: int
    on_time: int
    on_time_rate: float | None


class DriverRow(BaseModel):
    rank: int
    previous_rank: int | None
    driver_id: uuid.UUID
    name: str
    hub: str
    delivered: int
    success_rate: float | None
    on_time_rate: float | None


class HubRow(BaseModel):
    rank: int
    previous_rank: int | None
    hub_id: uuid.UUID
    name: str
    orders: int
    delivered: int
    on_time_rate: float | None


class ReportOut(BaseModel):
    """Everything E-01 shows, in one call (the page and both exports use it)."""

    summary: SummaryOut
    granularity: Granularity
    volume: list[VolumePoint]
    failure_reasons: list[ShareRow]
    incident_types: list[ShareRow]
    on_time_by_area: list[AreaRow]
    top_drivers: list[DriverRow]
    top_hubs: list[HubRow]
