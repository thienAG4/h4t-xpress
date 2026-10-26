"""Shared order operations used by dispatch, delivery, incidents and the hub screens."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.modules.orders.models import (
    ActorType,
    Assignment,
    AssignmentStatus,
    Order,
    OrderEvent,
    OrderEventType,
    OrderStatus,
)
from app.modules.realtime.hub import notify_hub, notify_user

ACTIVE_DRIVER_STATUSES = (OrderStatus.ASSIGNED, OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY)
FINAL_STATUSES = (OrderStatus.DELIVERED, OrderStatus.RETURNED_TO_HUB, OrderStatus.CANCELLED)


# =============================== Loading ===============================


async def lock_order(session: AsyncSession, order_id: uuid.UUID) -> Order:
    """Load an order with a row lock; concurrent changes to the same order wait."""
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise NotFound("Order not found", code="ORDER_NOT_FOUND")
    return order


async def active_assignment(session: AsyncSession, order_id: uuid.UUID) -> Assignment | None:
    return await session.scalar(
        select(Assignment).where(
            Assignment.order_id == order_id, Assignment.status == AssignmentStatus.ACTIVE
        )
    )


# =============================== Timeline ===============================


def add_event(
    session: AsyncSession,
    order: Order,
    event_type: OrderEventType,
    *,
    actor_type: ActorType,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    lat: float | None = None,
    lng: float | None = None,
    at: datetime | None = None,
) -> OrderEvent:
    """Timeline entry without a status change (ETA change, incident, note)."""
    event = OrderEvent(
        order_id=order.id,
        type=event_type,
        actor_type=actor_type,
        actor_user_id=actor_id,
        payload=payload or {},
        lat=lat,
        lng=lng,
    )
    if at is not None:
        event.created_at = at
    session.add(event)
    return event


# =============================== Realtime ===============================


def order_event_data(order: Order) -> dict[str, Any]:
    return {
        "order_id": str(order.id),
        "waybill_code": order.waybill_code,
        "status": order.status.value,
        "driver_id": str(order.current_driver_id) if order.current_driver_id else None,
        "eta": order.current_eta.isoformat() if order.current_eta else None,
    }


async def publish_order_update(order: Order, *, extra_user: uuid.UUID | None = None) -> None:
    """Tell the hub dashboard and the drivers involved that an order changed."""
    data = order_event_data(order)
    await notify_hub(order.hub_id, "order.updated", data)
    await notify_user(order.current_driver_id, "order.updated", data)
    if extra_user and extra_user != order.current_driver_id:
        await notify_user(extra_user, "order.updated", data)
