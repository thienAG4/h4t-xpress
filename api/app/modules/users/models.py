import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, str_enum


class UserStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class DriverAvailability(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class User(UUIDPrimaryKey, Timestamps, Base):
    """Merges NGUOI_DUNG and TAI_KHOAN from the original ERD (they were 1-1)."""

    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"))
    # Required for HUB_MANAGER (checked in the service layer, the role lives in another table).
    hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id", ondelete="SET NULL"))
    national_id: Mapped[str | None] = mapped_column(String(20))
    gender: Mapped[Gender | None] = mapped_column(str_enum(Gender))
    address: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(
        str_enum(UserStatus), default=UserStatus.ACTIVE, server_default=UserStatus.ACTIVE.value
    )
    last_login_at: Mapped[datetime | None]

    __table_args__ = (Index("ix_users_role_id_hub_id", "role_id", "hub_id"),)


class DriverProfile(Timestamps, Base):
    """Driver-specific attributes (TAI_XE in the original ERD)."""

    __tablename__ = "driver_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    vehicle_plate: Mapped[str] = mapped_column(String(20))
    license_no: Mapped[str] = mapped_column(String(30))
    home_area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )
    availability: Mapped[DriverAvailability] = mapped_column(
        str_enum(DriverAvailability),
        default=DriverAvailability.OFFLINE,
        server_default=DriverAvailability.OFFLINE.value,
    )
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("5.00"))
    last_lat: Mapped[float | None]
    last_lng: Mapped[float | None]
    last_seen_at: Mapped[datetime | None]

    __table_args__ = (
        Index("ix_driver_profiles_availability_last_seen_at", "availability", "last_seen_at"),
    )
