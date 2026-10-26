import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.incidents.models import (
    IncidentCategory,
    IncidentPriority,
    IncidentSource,
    IncidentStatus,
    IncidentType,
    ResolutionSolution,
    ResolutionStatus,
)
from app.modules.orders.models import OrderPriority, OrderStatus

SYSTEM_TYPES = {IncidentType.ETA_ANOMALY, IncidentType.DRIVER_IDLE}


class IncidentReportIn(BaseModel):
    """Driver report (D-11). Type, description and at least one photo are required."""

    type: IncidentType
    description: str = Field(min_length=10, max_length=1000)
    photo_file_ids: list[uuid.UUID] = Field(default_factory=list)
    order_ids: list[uuid.UUID] | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("type")
    @classmethod
    def _driver_type(cls, value: IncidentType) -> IncidentType:
        if value in SYSTEM_TYPES:
            raise ValueError("This incident type is raised by the system only")
        return value


class PersonOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None


class IncidentOrderOut(BaseModel):
    id: uuid.UUID
    waybill_code: str
    status: OrderStatus
    priority: OrderPriority
    recipient_name: str
    delivery_address: str
    promised_at: datetime
    current_eta: datetime | None
    current_driver_name: str | None


class ResolutionOut(BaseModel):
    solution: ResolutionSolution
    status: ResolutionStatus
    new_driver_name: str | None
    decided_at: datetime
    note: str | None


class IncidentOut(BaseModel):
    id: uuid.UUID
    code: str
    type: IncidentType
    source: IncidentSource
    status: IncidentStatus
    description: str
    suggested_category: IncidentCategory | None
    category: IncidentCategory | None
    priority: IncidentPriority | None
    hub_response: str | None
    lat: float | None
    lng: float | None
    reported_at: datetime
    classified_at: datetime | None
    resolved_at: datetime | None
    driver: PersonOut
    handled_by: str | None
    photo_urls: list[str]
    orders: list[IncidentOrderOut]
    resolutions: list[ResolutionOut]


class IncidentListItem(BaseModel):
    id: uuid.UUID
    code: str
    type: IncidentType
    status: IncidentStatus
    priority: IncidentPriority | None
    category: IncidentCategory | None
    description: str
    driver_name: str
    order_count: int
    reported_at: datetime


class IncidentSummaryOut(BaseModel):
    open: int
    in_review: int
    resolving: int
    resolved_today: int
    by_priority: dict[str, int]
    by_type_30d: dict[str, int]


class ClassifyIn(BaseModel):
    category: IncidentCategory
    priority: IncidentPriority


class RespondIn(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


class ResolveIn(BaseModel):
    solution: ResolutionSolution
    driver_id: uuid.UUID | None = None
    order_ids: list[uuid.UUID] | None = None
    stop_ids: list[uuid.UUID] | None = None
    note: str | None = Field(default=None, max_length=500)


class CandidateOut(BaseModel):
    driver_id: uuid.UUID
    name: str
    phone: str | None
    distance_km: float
    active_orders: int
    score: float
    lat: float | None
    lng: float | None
