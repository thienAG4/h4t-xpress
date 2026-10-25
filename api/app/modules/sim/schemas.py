import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.validators import normalize_phone
from app.modules.orders.models import OrderPriority
from app.modules.partner.schemas import OrderItemIn


class RandomOrdersIn(BaseModel):
    hub_code: str
    count: int = Field(default=5, ge=1, le=20)
    express_ratio: float = Field(default=0.15, ge=0, le=1)


class ManualOrderIn(BaseModel):
    """Single order typed in the simulator (S-01). Coordinates default to the hub area."""

    hub_code: str
    recipient_name: str = Field(min_length=2, max_length=120)
    recipient_phone: str
    delivery_address: str = Field(min_length=5, max_length=255)
    delivery_lat: float | None = None
    delivery_lng: float | None = None
    weight_kg: Decimal = Field(default=Decimal("1.0"), gt=0, le=100)
    cod_amount: Decimal = Field(default=Decimal(0), ge=0)
    items: list[OrderItemIn] = Field(min_length=1)
    priority: OrderPriority = OrderPriority.NORMAL
    promised_in_hours: int = Field(default=8, ge=1, le=72)

    @field_validator("recipient_phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)


class SimOrderOut(BaseModel):
    waybill_code: str
    partner_order_ref: str
    hub_code: str
    recipient_name: str
    delivery_address: str
    priority: str
    promised_at: datetime
    last_status: str | None
    current_eta: datetime | None
    last_event_at: datetime | None
    created_at: datetime


class SimWebhookOut(BaseModel):
    id: uuid.UUID
    event_type: str
    waybill_code: str | None
    payload: dict[str, Any]
    signature_valid: bool
    received_at: datetime
