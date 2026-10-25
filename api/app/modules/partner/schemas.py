from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.validators import normalize_phone
from app.modules.orders.models import OrderPriority, OrderStatus


class OrderItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    qty: int = Field(ge=1, le=999)


class PartnerOrderIn(BaseModel):
    """Pickup/delivery request from the e-commerce platform (FR-S-01, BR2 required fields)."""

    waybill_code: str = Field(pattern=r"^[A-Z0-9\-]{6,32}$")
    partner_order_ref: str | None = Field(default=None, max_length=64)
    hub_code: str = Field(min_length=2, max_length=32)
    recipient_name: str = Field(min_length=2, max_length=120)
    recipient_phone: str
    delivery_address: str = Field(min_length=5, max_length=255)
    delivery_lat: float = Field(ge=-90, le=90)
    delivery_lng: float = Field(ge=-180, le=180)
    weight_kg: Decimal = Field(gt=0, le=100)
    length_cm: Decimal = Field(gt=0, le=300)
    width_cm: Decimal = Field(gt=0, le=300)
    height_cm: Decimal = Field(gt=0, le=300)
    cod_amount: Decimal = Field(default=Decimal(0), ge=0)
    items: list[OrderItemIn] = Field(min_length=1)
    priority: OrderPriority = OrderPriority.NORMAL
    promised_at: datetime
    note: str | None = Field(default=None, max_length=500)

    @field_validator("recipient_phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)


class PartnerEventOut(BaseModel):
    at: datetime
    type: str
    from_status: OrderStatus | None
    to_status: OrderStatus | None


class PartnerDriverOut(BaseModel):
    name: str
    phone: str | None


class PartnerOrderOut(BaseModel):
    waybill_code: str
    partner_order_ref: str | None
    hub_code: str
    status: OrderStatus
    promised_at: datetime
    current_eta: datetime | None
    driver: PartnerDriverOut | None
    created_at: datetime
    timeline: list[PartnerEventOut]


class CancelIn(BaseModel):
    reason: str = Field(default="Cancelled by partner", max_length=255)
