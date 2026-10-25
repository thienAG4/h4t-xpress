import uuid
from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel

from app.modules.hubs.models import ShiftCode, ShiftRegistrationStatus
from app.modules.hubs.schemas import HubOut
from app.modules.users.models import DriverAvailability


class SlotStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    REGISTERED = "REGISTERED"
    FULL = "FULL"
    CLOSED = "CLOSED"  # registration deadline passed (shift.cutoff_time)
    CONFLICT = "CONFLICT"  # overlaps another shift of the driver that day


class ShiftSlotOut(BaseModel):
    shift_id: uuid.UUID
    code: ShiftCode
    name: str
    start_time: time
    end_time: time
    capacity: int
    taken: int
    status: SlotStatus
    registration_id: uuid.UUID | None


class ShiftDayOut(BaseModel):
    work_date: date
    slots: list[ShiftSlotOut]


class ShiftRegistrationIn(BaseModel):
    shift_id: uuid.UUID
    work_date: date


class RegistrationOut(BaseModel):
    id: uuid.UUID
    shift_id: uuid.UUID
    shift_code: ShiftCode
    shift_name: str
    start_time: time
    end_time: time
    work_date: date
    status: ShiftRegistrationStatus


class AvailabilityIn(BaseModel):
    online: bool


class AvailabilityOut(BaseModel):
    availability: DriverAvailability


class DriverTodayOut(BaseModel):
    date: date
    hub: HubOut | None
    availability: DriverAvailability
    shifts_today: list[RegistrationOut]
    upcoming: list[RegistrationOut]
    active_orders: int
    delivered_today: int
