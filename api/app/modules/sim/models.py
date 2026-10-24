from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey


class SimShopnowOrder(UUIDPrimaryKey, Timestamps, Base):
    """ShopNow's own copy of an order: only what it sent and what webhooks told it."""

    __tablename__ = "sim_shopnow_orders"

    waybill_code: Mapped[str] = mapped_column(String(32), unique=True)
    partner_order_ref: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]]
    last_status: Mapped[str | None] = mapped_column(String(32))
    current_eta: Mapped[datetime | None]
    last_event_at: Mapped[datetime | None]


class SimShopnowWebhook(UUIDPrimaryKey, Base):
    """Webhook received by ShopNow, shown in the simulator and on the tracking page."""

    __tablename__ = "sim_shopnow_webhooks"

    event_type: Mapped[str] = mapped_column(String(64))
    waybill_code: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]]
    signature_valid: Mapped[bool]
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("ix_sim_shopnow_webhooks_waybill_code_received_at", "waybill_code", "received_at"),
    )
