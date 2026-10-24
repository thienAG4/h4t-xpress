import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, str_enum


class RouteStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class StopStatus(StrEnum):
    PENDING = "PENDING"
    ARRIVED = "ARRIVED"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class Route(UUIDPrimaryKey, Timestamps, Base):
    """A driver's delivery run for one day (UC-03)."""

    __tablename__ = "routes"

    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id", ondelete="CASCADE"))
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    work_date: Mapped[date]
    status: Mapped[RouteStatus] = mapped_column(
        str_enum(RouteStatus), default=RouteStatus.DRAFT, server_default=RouteStatus.DRAFT.value
    )
    polyline: Mapped[str | None] = mapped_column(Text)
    total_distance_m: Mapped[int | None]
    total_duration_s: Mapped[int | None]
    published_at: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]

    __table_args__ = (
        Index("ix_routes_hub_id_work_date", "hub_id", "work_date"),
        Index("ix_routes_driver_id_work_date", "driver_id", "work_date"),
    )


class RouteStop(UUIDPrimaryKey, Timestamps, Base):
    """One stop on a route; orders for the same recipient share a stop."""

    __tablename__ = "route_stops"

    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    seq: Mapped[int]
    address: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float]
    lng: Mapped[float]
    recipient_name: Mapped[str] = mapped_column(String(120))
    recipient_phone: Mapped[str] = mapped_column(String(20))
    eta: Mapped[datetime | None]
    status: Mapped[StopStatus] = mapped_column(
        str_enum(StopStatus), default=StopStatus.PENDING, server_default=StopStatus.PENDING.value
    )
    arrived_at: Mapped[datetime | None]

    __table_args__ = (
        # Deferred so drag-and-drop reordering can swap sequence numbers in one transaction.
        UniqueConstraint("route_id", "seq", deferrable=True, initially="DEFERRED"),
    )
