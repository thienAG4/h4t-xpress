import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.modules.orders.models import FailureReason, OrderPriority, OrderStatus
from app.modules.routing.models import StopStatus


class OfferOut(BaseModel):
    id: uuid.UUID
    expires_at: datetime
    seconds_left: int
    source: str
    is_rescue: bool
    order_count: int
    waybill_codes: list[str]
    pickup_label: str
    delivery_addresses: list[str]
    distance_km: float | None
    priority: OrderPriority
    cod_total: Decimal


class DeclineIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class OrderItemOut(BaseModel):
    name: str
    qty: int


class DriverOrderOut(BaseModel):
    id: uuid.UUID
    waybill_code: str
    status: OrderStatus
    priority: OrderPriority
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    items: list[OrderItemOut]
    weight_kg: Decimal
    cod_amount: Decimal
    note: str | None
    promised_at: datetime
    current_eta: datetime | None
    eta_is_estimate: bool
    handover_from: str | None
    active_incident_id: uuid.UUID | None


class StopOut(BaseModel):
    id: uuid.UUID
    seq: int
    status: StopStatus
    address: str
    lat: float
    lng: float
    recipient_name: str
    recipient_phone: str
    eta: datetime | None
    orders: list[DriverOrderOut]


class RouteOut(BaseModel):
    route_id: uuid.UUID | None
    geometry: str | None  # encoded polyline of the remaining path (OSRM), null when estimated
    hub_name: str
    hub_lat: float
    hub_lng: float
    driver_lat: float | None
    driver_lng: float | None
    to_pick_up: list[DriverOrderOut]
    ready_to_start: int
    stops: list[StopOut]


class TimelineEventOut(BaseModel):
    at: datetime
    type: str
    from_status: OrderStatus | None
    to_status: OrderStatus | None
    payload: dict[str, Any]


class DriverOrderDetailOut(DriverOrderOut):
    stop_id: uuid.UUID | None
    timeline: list[TimelineEventOut]


class ScanIn(BaseModel):
    waybill_code: str = Field(min_length=4, max_length=32)
    lat: float | None = None
    lng: float | None = None


class DeliverIn(BaseModel):
    photo_file_ids: list[uuid.UUID] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)
    lat: float | None = None
    lng: float | None = None


class FailIn(BaseModel):
    reason: FailureReason
    note: str | None = Field(default=None, max_length=500)
    proposed_date: date | None = None
    lat: float | None = None
    lng: float | None = None


class EtaIn(BaseModel):
    eta: datetime
    reason: str = Field(min_length=3, max_length=255)


class ReleaseIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class HeartbeatIn(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class StartOut(BaseModel):
    started: int
