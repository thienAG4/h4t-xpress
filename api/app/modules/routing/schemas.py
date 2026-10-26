import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.orders.models import OrderPriority, OrderStatus
from app.modules.routing.models import RouteStatus, StopStatus


class RouteSummaryOut(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    driver_name: str
    status: RouteStatus
    work_date: date
    stops_total: int
    stops_pending: int
    orders_active: int
    orders_at_risk: int
    total_distance_m: int | None
    total_duration_s: int | None
    next_eta: datetime | None
    last_eta: datetime | None


class PlanOrderOut(BaseModel):
    id: uuid.UUID
    waybill_code: str
    status: OrderStatus
    priority: OrderPriority
    promised_at: datetime
    current_eta: datetime | None


class PlanStopOut(BaseModel):
    id: uuid.UUID
    seq: int
    status: StopStatus
    address: str
    lat: float
    lng: float
    recipient_name: str
    eta: datetime | None
    orders: list[PlanOrderOut]


class RouteDetailOut(BaseModel):
    id: uuid.UUID
    status: RouteStatus
    work_date: date
    driver_id: uuid.UUID
    driver_name: str
    driver_phone: str | None
    driver_lat: float | None
    driver_lng: float | None
    hub_name: str
    hub_lat: float
    hub_lng: float
    geometry: str | None
    total_distance_m: int | None
    total_duration_s: int | None
    eta_is_estimate: bool
    stops: list[PlanStopOut]


class OptimizeOut(BaseModel):
    """Suggested visiting order of the pending stops (not saved)."""

    method: str  # "osrm" or "nearest_neighbor"
    current_stop_ids: list[uuid.UUID]
    suggested_stop_ids: list[uuid.UUID]
    current_duration_s: int | None
    suggested_duration_s: int | None
    suggested_geometry: str | None
    changed: bool


class StopOrderIn(BaseModel):
    stop_ids: list[uuid.UUID] = Field(min_length=1)
