import uuid
from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey, str_enum


class HubStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ShiftCode(StrEnum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    FULL_DAY = "FULL_DAY"


class ShiftRegistrationStatus(StrEnum):
    REGISTERED = "REGISTERED"
    CANCELLED = "CANCELLED"


class Area(UUIDPrimaryKey, CreatedAt, Base):
    """Delivery area (KhuVucHoatDong was free text in the original ERD)."""

    __tablename__ = "areas"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    center_lat: Mapped[float]
    center_lng: Mapped[float]
    radius_km: Mapped[float]


class AreaAdjacency(Base):
    __tablename__ = "area_adjacency"

    area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True
    )
    neighbor_area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (CheckConstraint("area_id <> neighbor_area_id", name="not_self"),)


class Hub(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "hubs"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float]
    lng: Mapped[float]
    area_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"))
    status: Mapped[HubStatus] = mapped_column(
        str_enum(HubStatus), default=HubStatus.ACTIVE, server_default=HubStatus.ACTIVE.value
    )


class Shift(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "shifts"

    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id", ondelete="CASCADE"))
    code: Mapped[ShiftCode] = mapped_column(str_enum(ShiftCode))
    name: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[time]
    end_time: Mapped[time]
    capacity: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    __table_args__ = (
        UniqueConstraint("hub_id", "code"),
        CheckConstraint("end_time > start_time", name="valid_time_range"),
        CheckConstraint("capacity > 0", name="positive_capacity"),
    )


class ShiftRegistration(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "shift_registrations"

    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    work_date: Mapped[date]
    status: Mapped[ShiftRegistrationStatus] = mapped_column(
        str_enum(ShiftRegistrationStatus),
        default=ShiftRegistrationStatus.REGISTERED,
        server_default=ShiftRegistrationStatus.REGISTERED.value,
    )
    cancelled_at: Mapped[datetime | None]

    __table_args__ = (
        UniqueConstraint("driver_id", "shift_id", "work_date"),
        Index("ix_shift_registrations_shift_id_work_date", "shift_id", "work_date"),
    )
