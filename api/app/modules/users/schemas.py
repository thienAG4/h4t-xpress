import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import normalize_phone, validate_password
from app.modules.rbac.models import RoleCode
from app.modules.users.models import DriverAvailability, Gender, UserStatus


class DriverProfileOut(BaseModel):
    vehicle_plate: str
    license_no: str
    availability: DriverAvailability
    rating: Decimal


class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    role: str
    role_name: str
    hub_id: uuid.UUID | None
    hub_name: str | None
    status: UserStatus
    national_id: str | None
    gender: Gender | None
    address: str | None
    last_login_at: datetime | None
    created_at: datetime
    driver: DriverProfileOut | None


class MeOut(UserOut):
    permissions: list[str]


class _PhoneMixin(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None


class UserCreateIn(_PhoneMixin):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    role: RoleCode
    hub_id: uuid.UUID | None = None
    # Leave empty to generate a temporary password that is returned once.
    password: str | None = None
    national_id: str | None = Field(default=None, max_length=20)
    gender: Gender | None = None
    address: str | None = Field(default=None, max_length=255)
    vehicle_plate: str | None = Field(default=None, max_length=20)
    license_no: str | None = Field(default=None, max_length=30)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str | None) -> str | None:
        return validate_password(value) if value else None


class UserUpdateIn(_PhoneMixin):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    role: RoleCode | None = None
    hub_id: uuid.UUID | None = None
    national_id: str | None = Field(default=None, max_length=20)
    gender: Gender | None = None
    address: str | None = Field(default=None, max_length=255)
    vehicle_plate: str | None = Field(default=None, max_length=20)
    license_no: str | None = Field(default=None, max_length=30)


class UserCreatedOut(BaseModel):
    user: UserOut
    temporary_password: str | None


class TemporaryPasswordOut(BaseModel):
    temporary_password: str


class MeUpdateIn(_PhoneMixin):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    address: str | None = Field(default=None, max_length=255)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)
