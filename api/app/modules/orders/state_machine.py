"""Allowed order status transitions (SPEC §3.1, BR3: no skipping, no going back).

Every status change must go through `transition`, which also writes the timeline event.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import Conflict
from app.modules.orders.models import ActorType, Order, OrderEvent, OrderEventType, OrderStatus

S = OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    S.AWAITING_ASSIGNMENT: frozenset({S.ASSIGNED, S.ON_HOLD, S.CANCELLED}),
    S.ON_HOLD: frozenset({S.AWAITING_ASSIGNMENT, S.CANCELLED}),
    S.ASSIGNED: frozenset({S.PICKED_UP, S.AWAITING_ASSIGNMENT, S.CANCELLED}),
    # Back to AWAITING_ASSIGNMENT only through an incident (parcel scanned, driver cannot leave).
    S.PICKED_UP: frozenset({S.OUT_FOR_DELIVERY, S.AWAITING_ASSIGNMENT}),
    S.OUT_FOR_DELIVERY: frozenset({S.DELIVERED, S.DELIVERY_FAILED, S.AWAITING_ASSIGNMENT}),
    S.DELIVERY_FAILED: frozenset({S.RESCHEDULED, S.RETURNING}),
    S.RESCHEDULED: frozenset({S.AWAITING_ASSIGNMENT}),
    S.RETURNING: frozenset({S.RETURNED_TO_HUB}),
    S.DELIVERED: frozenset(),
    S.RETURNED_TO_HUB: frozenset(),
    S.CANCELLED: frozenset(),
}

TERMINAL_STATUSES = frozenset(s for s, targets in ALLOWED_TRANSITIONS.items() if not targets)


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition(
    session: AsyncSession,
    order: Order,
    target: OrderStatus,
    *,
    actor_type: ActorType,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    lat: float | None = None,
    lng: float | None = None,
    at: datetime | None = None,
) -> OrderEvent:
    """Change the status and add the timeline event (caller commits). Raises INVALID_TRANSITION."""
    current = OrderStatus(order.status)
    if not can_transition(current, target):
        raise Conflict(
            f"Order cannot go from {current.value} to {target.value}",
            code="INVALID_TRANSITION",
            details={"from": current.value, "to": target.value},
        )
    event = OrderEvent(
        order_id=order.id,
        type=OrderEventType.STATUS_CHANGED,
        from_status=current,
        to_status=target,
        actor_user_id=actor_id,
        actor_type=actor_type,
        lat=lat,
        lng=lng,
        payload=payload or {},
        created_at=at or utc_now(),
    )
    order.status = target
    session.add(event)
    return event
