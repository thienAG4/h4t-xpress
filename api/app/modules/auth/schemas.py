import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import normalize_identifier, normalize_phone, validate_password
from app.modules.auth.models import OtpPurpose
from app.modules.rbac.models import RoleCode
from app.modules.users.schemas import MeOut


class RegisterDriverIn(BaseModel):
    """Driver sign-up (D-01). Vehicle fields come from the report's 'Chức năng 1'."""

    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    email: EmailStr
    password: str
    hub_id: uuid.UUID
    vehicle_plate: str = Field(min_length=4, max_length=20)
    license_no: str = Field(min_length=6, max_length=30)
    national_id: str | None = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)


class OtpSentOut(BaseModel):
    phone_hint: str
    expires_at: datetime
    resend_available_at: datetime
    # Only in demo mode: the code is shown on screen instead of being sent by SMS (D11).
    demo_code: str | None = None


class VerifyOtpIn(BaseModel):
    phone: str
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)


class ResendOtpIn(BaseModel):
    phone: str
    purpose: OtpPurpose = OtpPurpose.REGISTER

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, description="E-mail or phone number")
    password: str = Field(min_length=1)

    @field_validator("identifier")
    @classmethod
    def _identifier(cls, value: str) -> str:
        return normalize_identifier(value)


class DemoLoginIn(BaseModel):
    role: RoleCode


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: MeOut


class ForgotPasswordIn(BaseModel):
    identifier: str

    @field_validator("identifier")
    @classmethod
    def _identifier(cls, value: str) -> str:
        return normalize_identifier(value)


class ForgotPasswordOut(BaseModel):
    sent: bool = True
    phone_hint: str | None = None
    demo_code: str | None = None


class ResetPasswordIn(BaseModel):
    identifier: str
    code: str = Field(pattern=r"^\d{6}$")
    new_password: str

    @field_validator("identifier")
    @classmethod
    def _identifier(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)
