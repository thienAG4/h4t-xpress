"""Order state machine (SPEC §3.1, BR3). Pure unit tests, no database access."""

import pytest

from app.core.errors import Conflict
from app.modules.orders.models import ActorType, Order, OrderStatus
from app.modules.orders.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    can_transition,
    transition,
)

S = OrderStatus


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, item: object) -> None:
        self.added.append(item)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.AWAITING_ASSIGNMENT, S.ASSIGNED),
        (S.ASSIGNED, S.PICKED_UP),
        (S.PICKED_UP, S.OUT_FOR_DELIVERY),
        (S.OUT_FOR_DELIVERY, S.DELIVERED),
        (S.OUT_FOR_DELIVERY, S.AWAITING_ASSIGNMENT),  # reassignment after an incident
        (S.DELIVERY_FAILED, S.RESCHEDULED),
        (S.RETURNING, S.RETURNED_TO_HUB),
    ],
)
def test_allowed_transitions(current: OrderStatus, target: OrderStatus) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.AWAITING_ASSIGNMENT, S.OUT_FOR_DELIVERY),  # skipping steps
        (S.PICKED_UP, S.ASSIGNED),  # going back
        (S.PICKED_UP, S.CANCELLED),  # too late to cancel
        (S.DELIVERED, S.DELIVERY_FAILED),
    ],
)
def test_forbidden_transitions(current: OrderStatus, target: OrderStatus) -> None:
    assert not can_transition(current, target)


def test_every_status_is_covered_and_terminals_are_final() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(OrderStatus)
    assert {S.DELIVERED, S.RETURNED_TO_HUB, S.CANCELLED} == TERMINAL_STATUSES


def test_transition_updates_status_and_records_event() -> None:
    session = _FakeSession()
    order = Order(status=S.AWAITING_ASSIGNMENT)
    event = transition(
        session,  # type: ignore[arg-type]
        order,
        S.ASSIGNED,
        actor_type=ActorType.SYSTEM,
        payload={"driver_id": "x"},
    )
    assert order.status == S.ASSIGNED
    assert session.added == [event]
    assert (event.from_status, event.to_status) == (S.AWAITING_ASSIGNMENT, S.ASSIGNED)


def test_invalid_transition_raises_conflict() -> None:
    order = Order(status=S.DELIVERED)
    with pytest.raises(Conflict) as error:
        transition(_FakeSession(), order, S.CANCELLED, actor_type=ActorType.PARTNER)  # type: ignore[arg-type]
    assert error.value.code == "INVALID_TRANSITION"
    assert order.status == S.DELIVERED
