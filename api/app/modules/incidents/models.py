import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, str_enum

# Human-readable incident code, e.g. INC-000123. The sequence is created in the migration.
INCIDENT_CODE_DEFAULT = text("'INC-' || lpad(nextval('incident_code_seq')::text, 6, '0')")


class IncidentType(StrEnum):
    TRAFFIC_JAM = "TRAFFIC_JAM"
    WEATHER = "WEATHER"
    TRAFFIC_ACCIDENT = "TRAFFIC_ACCIDENT"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"
    HEALTH = "HEALTH"
    GOODS_DAMAGED = "GOODS_DAMAGED"
    OTHER = "OTHER"
    # Raised by the system (BR12), not by drivers.
    ETA_ANOMALY = "ETA_ANOMALY"
    DRIVER_IDLE = "DRIVER_IDLE"


class IncidentSource(StrEnum):
    DRIVER = "DRIVER"
    SYSTEM = "SYSTEM"


class IncidentCategory(StrEnum):
    OBJECTIVE = "OBJECTIVE"
    SUBJECTIVE = "SUBJECTIVE"


class IncidentPriority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"


class ResolutionSolution(StrEnum):
    ROUTE_SUGGESTED = "ROUTE_SUGGESTED"
    DRIVER_REASSIGNMENT = "DRIVER_REASSIGNMENT"
    HOLD_AT_HUB = "HOLD_AT_HUB"


class ResolutionStatus(StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class Incident(UUIDPrimaryKey, Timestamps, Base):
    """SU_CO_GIAO_HANG. One incident can affect several orders (incident_orders)."""

    __tablename__ = "incidents"

    code: Mapped[str] = mapped_column(String(16), unique=True, server_default=INCIDENT_CODE_DEFAULT)
    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id", ondelete="RESTRICT"))
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    type: Mapped[IncidentType] = mapped_column(str_enum(IncidentType))
    source: Mapped[IncidentSource] = mapped_column(
        str_enum(IncidentSource),
        default=IncidentSource.DRIVER,
        server_default=IncidentSource.DRIVER.value,
    )
    description: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    suggested_category: Mapped[IncidentCategory | None] = mapped_column(
        str_enum(IncidentCategory, name="suggested_category")
    )
    category: Mapped[IncidentCategory | None] = mapped_column(
        str_enum(IncidentCategory, name="category")
    )
    priority: Mapped[IncidentPriority | None] = mapped_column(str_enum(IncidentPriority))
    status: Mapped[IncidentStatus] = mapped_column(
        str_enum(IncidentStatus),
        default=IncidentStatus.OPEN,
        server_default=IncidentStatus.OPEN.value,
    )
    hub_response: Mapped[str | None] = mapped_column(Text)
    handled_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reported_at: Mapped[datetime] = mapped_column(server_default=func.now())
    classified_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]

    __table_args__ = (
        Index("ix_incidents_hub_id_status_priority", "hub_id", "status", "priority"),
        Index("ix_incidents_driver_id_reported_at", "driver_id", "reported_at"),
    )


class IncidentOrder(Base):
    __tablename__ = "incident_orders"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )


class IncidentFile(Base):
    __tablename__ = "incident_files"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )


class IncidentResolution(UUIDPrimaryKey, Timestamps, Base):
    """GIAI_PHAP: the hub manager's decision for an incident."""

    __tablename__ = "incident_resolutions"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    solution: Mapped[ResolutionSolution] = mapped_column(str_enum(ResolutionSolution))
    new_driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    route_snapshot: Mapped[dict[str, Any] | None]
    status: Mapped[ResolutionStatus] = mapped_column(
        str_enum(ResolutionStatus),
        default=ResolutionStatus.PENDING,
        server_default=ResolutionStatus.PENDING.value,
    )
    note: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now())
