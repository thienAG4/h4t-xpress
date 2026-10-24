import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey, str_enum


class OrderStatus(StrEnum):
    """Order state machine (SPEC §3.1)."""

    AWAITING_ASSIGNMENT = "AWAITING_ASSIGNMENT"
    ON_HOLD = "ON_HOLD"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    RESCHEDULED = "RESCHEDULED"
    RETURNING = "RETURNING"
    RETURNED_TO_HUB = "RETURNED_TO_HUB"
    CANCELLED = "CANCELLED"


class OrderPriority(StrEnum):
    NORMAL = "NORMAL"
    EXPRESS = "EXPRESS"


class EtaSource(StrEnum):
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"


class OrderEventType(StrEnum):
    STATUS_CHANGED = "STATUS_CHANGED"
    ETA_CHANGED = "ETA_CHANGED"
    ASSIGNED = "ASSIGNED"
    NOTE = "NOTE"
    INCIDENT = "INCIDENT"


class ActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    PARTNER = "PARTNER"


class AssignmentLeg(StrEnum):
    DELIVERY = "DELIVERY"
    PICKUP = "PICKUP"


class AssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    RELEASED = "RELEASED"
    REASSIGNED = "REASSIGNED"


class AttemptOutcome(StrEnum):
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class FailureReason(StrEnum):
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"
    CUSTOMER_UNREACHABLE = "CUSTOMER_UNREACHABLE"
    CUSTOMER_ABSENT = "CUSTOMER_ABSENT"
    WRONG_ADDRESS = "WRONG_ADDRESS"
    OTHER = "OTHER"


class Order(UUIDPrimaryKey, Timestamps, Base):
    """DON_HANG + VAN_DON from the original ERD (they were 1-1)."""

    __tablename__ = "orders"

    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("partners.id", ondelete="RESTRICT"))
    waybill_code: Mapped[str] = mapped_column(String(32))
    partner_order_ref: Mapped[str | None] = mapped_column(String(64))
    hub_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hubs.id", ondelete="RESTRICT"))
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus),
        default=OrderStatus.AWAITING_ASSIGNMENT,
        server_default=OrderStatus.AWAITING_ASSIGNMENT.value,
    )
    priority: Mapped[OrderPriority] = mapped_column(
        str_enum(OrderPriority),
        default=OrderPriority.NORMAL,
        server_default=OrderPriority.NORMAL.value,
    )

    recipient_name: Mapped[str] = mapped_column(String(120))
    recipient_phone: Mapped[str] = mapped_column(String(20))
    delivery_address: Mapped[str] = mapped_column(String(255))
    delivery_lat: Mapped[float]
    delivery_lng: Mapped[float]
    delivery_area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL")
    )

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    length_cm: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    width_cm: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    height_cm: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    cod_amount: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=0, server_default="0")
    items: Mapped[list[Any]] = mapped_column(default=list, server_default=text("'[]'::jsonb"))
    note: Mapped[str | None] = mapped_column(Text)

    promised_at: Mapped[datetime]
    current_eta: Mapped[datetime | None]
    eta_source: Mapped[EtaSource | None] = mapped_column(str_enum(EtaSource))
    eta_degraded: Mapped[bool] = mapped_column(default=False, server_default=false())

    current_driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    route_stop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("route_stops.id", ondelete="SET NULL")
    )
    handover_from_driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    active_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL")
    )

    delivered_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    failed_attempts: Mapped[int] = mapped_column(default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint("partner_id", "waybill_code"),
        Index("ix_orders_hub_id_status", "hub_id", "status"),
        Index("ix_orders_hub_id_created_at", "hub_id", "created_at"),
        Index("ix_orders_current_driver_id_status", "current_driver_id", "status"),
        Index("ix_orders_promised_at", "promised_at"),
        CheckConstraint("weight_kg > 0", name="positive_weight"),
    )


class OrderEvent(UUIDPrimaryKey, CreatedAt, Base):
    """Status history and timeline (TRACKING_DON_HANG, without the GPS stream)."""

    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    type: Mapped[OrderEventType] = mapped_column(str_enum(OrderEventType))
    from_status: Mapped[OrderStatus | None] = mapped_column(
        str_enum(OrderStatus, name="from_status")
    )
    to_status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, name="to_status"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_type: Mapped[ActorType] = mapped_column(str_enum(ActorType))
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    payload: Mapped[dict[str, Any]] = mapped_column(
        default=dict, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (Index("ix_order_events_order_id_created_at", "order_id", "created_at"),)


class Assignment(UUIDPrimaryKey, CreatedAt, Base):
    """Which driver holds an order (PHAN_CONG_GIAO_HANG)."""

    __tablename__ = "assignments"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    leg: Mapped[AssignmentLeg] = mapped_column(
        str_enum(AssignmentLeg),
        default=AssignmentLeg.DELIVERY,
        server_default=AssignmentLeg.DELIVERY.value,
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        str_enum(AssignmentStatus),
        default=AssignmentStatus.ACTIVE,
        server_default=AssignmentStatus.ACTIVE.value,
    )
    assigned_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    end_reason: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        # An order can only be held by one driver at a time.
        Index(
            "uq_assignments_one_active_per_order",
            "order_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_assignments_driver_id_status", "driver_id", "status"),
    )


class DeliveryAttempt(UUIDPrimaryKey, CreatedAt, Base):
    """Each hand-over attempt (GIAO_HANG_THAT_BAI + LICH_GIAO_LAI, plus successes)."""

    __tablename__ = "delivery_attempts"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    outcome: Mapped[AttemptOutcome] = mapped_column(str_enum(AttemptOutcome))
    failure_reason: Mapped[FailureReason | None] = mapped_column(str_enum(FailureReason))
    note: Mapped[str | None] = mapped_column(Text)
    proposed_reschedule_date: Mapped[date | None]
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    attempted_at: Mapped[datetime]

    __table_args__ = (
        CheckConstraint(
            "outcome <> 'FAILED' OR failure_reason IS NOT NULL", name="failed_requires_reason"
        ),
    )


class DeliveryAttemptFile(Base):
    """Proof-of-delivery photos (BR16)."""

    __tablename__ = "delivery_attempt_files"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )
