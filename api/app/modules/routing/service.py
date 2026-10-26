"""Driver routes for the day: stops in delivery order, orders grouped per recipient.

Orders for the same recipient and address share one stop (Figma "Order Details" shows
two delivery requests on one stop). The hub can reorder pending stops (UC-03).
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, utc_now
from app.core.errors import NotFound, ValidationFailed
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import FINAL_STATUSES
from app.modules.routing.models import Route, RouteStatus, RouteStop, StopStatus

STOP_DONE_STATUSES = (*FINAL_STATUSES, OrderStatus.DELIVERY_FAILED, OrderStatus.RESCHEDULED,
                      OrderStatus.RETURNING)  # fmt: skip


# =============================== Routes ===============================


async def get_or_create_route(
    session: AsyncSession, driver_id: uuid.UUID, hub_id: uuid.UUID, work_date: date
) -> Route:
    route = await session.scalar(
        select(Route).where(Route.driver_id == driver_id, Route.work_date == work_date)
    )
    if route is None:
        route = Route(hub_id=hub_id, driver_id=driver_id, work_date=work_date)
        session.add(route)
        await session.flush()
    return route


async def attach_order(session: AsyncSession, order: Order, driver_id: uuid.UUID) -> RouteStop:
    """Put an order on the driver's route for today, reusing a stop for the same recipient."""
    route = await get_or_create_route(session, driver_id, order.hub_id, local_today())
    stop = await session.scalar(
        select(RouteStop).where(
            RouteStop.route_id == route.id,
            RouteStop.status == StopStatus.PENDING,
            RouteStop.recipient_phone == order.recipient_phone,
            RouteStop.address == order.delivery_address,
        )
    )
    if stop is None:
        last_seq = await session.scalar(
            select(func.coalesce(func.max(RouteStop.seq), 0)).where(RouteStop.route_id == route.id)
        )
        stop = RouteStop(
            route_id=route.id,
            seq=(last_seq or 0) + 1,
            address=order.delivery_address,
            lat=order.delivery_lat,
            lng=order.delivery_lng,
            recipient_name=order.recipient_name,
            recipient_phone=order.recipient_phone,
        )
        session.add(stop)
        await session.flush()
    order.route_stop_id = stop.id
    if route.status == RouteStatus.DRAFT:
        route.status = RouteStatus.PUBLISHED
        route.published_at = utc_now()
    return stop


async def detach_order(session: AsyncSession, order: Order) -> None:
    """Take an order off its route (release, reassignment, hold)."""
    stop_id = order.route_stop_id
    order.route_stop_id = None
    if stop_id is not None:
        await session.flush()
        await refresh_stop_status(session, stop_id)


async def refresh_stop_status(session: AsyncSession, stop_id: uuid.UUID) -> None:
    """A stop is DONE when all its orders are finished, SKIPPED when it has none left."""
    stop = await session.get(RouteStop, stop_id)
    if stop is None or stop.status != StopStatus.PENDING:
        return
    statuses = list(
        await session.scalars(select(Order.status).where(Order.route_stop_id == stop_id))
    )
    if not statuses:
        stop.status = StopStatus.SKIPPED
    elif all(status in STOP_DONE_STATUSES for status in statuses):
        stop.status = StopStatus.DONE
        stop.arrived_at = stop.arrived_at or utc_now()


# =============================== Queries ===============================


async def pending_stops(session: AsyncSession, driver_id: uuid.UUID) -> list[RouteStop]:
    """Today's pending stops of a driver, in delivery order."""
    return list(
        await session.scalars(
            select(RouteStop)
            .join(Route, Route.id == RouteStop.route_id)
            .where(
                Route.driver_id == driver_id,
                Route.work_date == local_today(),
                RouteStop.status == StopStatus.PENDING,
            )
            .order_by(RouteStop.seq)
        )
    )


async def today_route(session: AsyncSession, driver_id: uuid.UUID) -> Route | None:
    return await session.scalar(
        select(Route).where(Route.driver_id == driver_id, Route.work_date == local_today())
    )


# =============================== Reordering (UC-03) ===============================


async def reorder_stops(
    session: AsyncSession, driver_id: uuid.UUID, stop_ids: list[uuid.UUID]
) -> list[RouteStop]:
    """Give the driver's pending stops a new order. The list must contain exactly those stops."""
    stops = await pending_stops(session, driver_id)
    if not stops:
        raise NotFound("The driver has no pending stops", code="ROUTE_NOT_FOUND")
    if sorted(map(str, stop_ids)) != sorted(str(stop.id) for stop in stops):
        raise ValidationFailed(
            "The new order must list every pending stop exactly once", code="STOP_LIST_MISMATCH"
        )
    by_id = {stop.id: stop for stop in stops}
    first_seq = min(stop.seq for stop in stops)
    # The (route_id, seq) constraint is deferred, so swapping numbers inside one
    # transaction is allowed; it is checked at commit.
    for offset, stop_id in enumerate(stop_ids):
        by_id[stop_id].seq = first_seq + offset
    await session.flush()
    return [by_id[stop_id] for stop_id in stop_ids]
