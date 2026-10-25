import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.delivery.schemas import OrderItemOut, TimelineEventOut
from app.modules.orders.models import AttemptOutcome, FailureReason, OrderPriority, OrderStatus
from app.modules.users.models import DriverAvailability


class DashboardOut(BaseModel):
    date: date
    total: int
    by_status: dict[str, int]
    at_risk: int
    delivered_today: int
    on_time_rate_today: float | None
    open_incidents: int
    high_priority_incidents: int
    drivers_online: int
    drivers_on_shift: int


class HubOrderRow(BaseModel):
    id: uuid.UUID
    waybill_code: str
    status: OrderStatus
    priority: OrderPriority
    recipient_name: str
    delivery_address: str
    driver_id: uuid.UUID | None
    driver_name: str | None
    promised_at: datetime
    current_eta: datetime | None
    at_risk: bool
    has_incident: bool
    created_at: datetime


class DriverBrief(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    lat: float | None
    lng: float | None


class AttemptOut(BaseModel):
    outcome: AttemptOutcome
    failure_reason: FailureReason | None
    note: str | None
    attempted_at: datetime
    photo_urls: list[str]


class HubOrderDetail(HubOrderRow):
    recipient_phone: str
    delivery_lat: float
    delivery_lng: float
    items: list[OrderItemOut]
    weight_kg: Decimal
    cod_amount: Decimal
    eta_is_estimate: bool
    driver: DriverBrief | None
    handover_from: str | None
    incident_id: uuid.UUID | None
    hub_lat: float
    hub_lng: float
    timeline: list[TimelineEventOut]
    attempts: list[AttemptOut]


class HubDriverRow(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    availability: DriverAvailability
    last_seen_at: datetime | None
    lat: float | None
    lng: float | None
    active_orders: int
    shift_today: str | None
    has_pending_offer: bool


class ReassignIn(BaseModel):
    driver_id: uuid.UUID


class HoldIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
