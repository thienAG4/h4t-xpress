import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey, str_enum


class PartnerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class WebhookStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Partner(UUIDPrimaryKey, Timestamps, Base):
    """E-commerce platform that sends orders in and receives status webhooks."""

    __tablename__ = "partners"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    api_key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    webhook_url: Mapped[str] = mapped_column(String(500))
    # Kept in plain text because it is needed to sign outgoing webhooks (HMAC-SHA256).
    webhook_secret: Mapped[str] = mapped_column(String(128))
    status: Mapped[PartnerStatus] = mapped_column(
        str_enum(PartnerStatus),
        default=PartnerStatus.ACTIVE,
        server_default=PartnerStatus.ACTIVE.value,
    )


class WebhookDelivery(UUIDPrimaryKey, CreatedAt, Base):
    """Transactional outbox for partner webhooks (BR10, EX7)."""

    __tablename__ = "webhook_deliveries"

    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]]
    status: Mapped[WebhookStatus] = mapped_column(
        str_enum(WebhookStatus),
        default=WebhookStatus.PENDING,
        server_default=WebhookStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None]

    __table_args__ = (
        Index("ix_webhook_deliveries_status_next_attempt_at", "status", "next_attempt_at"),
    )
