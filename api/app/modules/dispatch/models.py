import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, str_enum


class OfferStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OfferSource(StrEnum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class DispatchOffer(UUIDPrimaryKey, CreatedAt, Base):
    """A job offer sent to one driver (PHAN_CONG_PICKUP, generalised to both legs).

    BR6: one driver at a time per order. BR7: an offer expires after `offer_timeout_s`.
    """

    __tablename__ = "dispatch_offers"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    round: Mapped[int]
    rank: Mapped[int]
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        default=dict, server_default=text("'{}'::jsonb")
    )
    source: Mapped[OfferSource] = mapped_column(
        str_enum(OfferSource), default=OfferSource.AUTO, server_default=OfferSource.AUTO.value
    )
    status: Mapped[OfferStatus] = mapped_column(
        str_enum(OfferStatus), default=OfferStatus.PENDING, server_default=OfferStatus.PENDING.value
    )
    offered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    responded_at: Mapped[datetime | None]
    decline_reason: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        Index(
            "uq_dispatch_offers_one_pending_per_order",
            "order_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "uq_dispatch_offers_one_pending_per_driver",
            "driver_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("ix_dispatch_offers_status_expires_at", "status", "expires_at"),
        Index("ix_dispatch_offers_order_id_round", "order_id", "round"),
    )
