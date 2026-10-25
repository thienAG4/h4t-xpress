import uuid
from datetime import datetime, time
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.hubs.models import HubStatus, ShiftCode


class AreaOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    center_lat: float
    center_lng: float
    radius_km: float
    neighbor_codes: list[str]


class AreaIn(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=100)
    center_lat: float = Field(ge=-90, le=90)
    center_lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=50)


class AdminHubOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    address: str
    lat: float
    lng: float
    area_id: uuid.UUID
    area_name: str
    status: HubStatus
    drivers: int
    managers: int


class HubIn(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=255)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    area_id: uuid.UUID
    status: HubStatus = HubStatus.ACTIVE


class ShiftOut(BaseModel):
    id: uuid.UUID
    hub_id: uuid.UUID
    hub_name: str
    code: ShiftCode
    name: str
    start_time: time
    end_time: time
    capacity: int
    is_active: bool
    registered_today: int


class ShiftUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    start_time: time | None = None
    end_time: time | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)
    is_active: bool | None = None


class SettingOut(BaseModel):
    key: str
    group: str
    value: Any
    description: str | None
    updated_at: datetime | None


class SettingIn(BaseModel):
    value: Any

    @field_validator("value")
    @classmethod
    def _present(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("A value is required")
        return value


class AuditOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None
