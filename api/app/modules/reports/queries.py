"""Report queries for E-01 (FR-R-01..FR-R-05).

Definitions, so the numbers can be checked by hand:
- Orders of a period: orders **created** between `date_from` 00:00 and `date_to` 24:00
  (business time). Delivered, on-time and delivery time are measured on those orders.
- Success rate: delivered / (delivered + returned to hub). Cancelled orders are left out.
- Failed attempt rate: failed attempts / all attempts made in the period.
- On time: delivered no later than `promised_at + sla.grace_min` (SPEC §3.3).
- Active drivers: drivers who were assigned at least one order in the period.
Every KPI is also computed for the previous period of the same length.
"""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import BUSINESS_TZ, local_datetime, local_today
from app.core.deps import CurrentUser
from app.core.errors import Forbidden, ValidationFailed
from app.modules.hubs.models import Area, Hub
from app.modules.incidents.models import Incident
from app.modules.orders.models import (
    Assignment,
    AttemptOutcome,
    DeliveryAttempt,
    FailureReason,
    Order,
    OrderStatus,
)
from app.modules.rbac.models import Role, RoleCode
from app.modules.reports.schemas import (
    AreaRow,
    DriverRow,
    Granularity,
    HubRow,
    KpiOut,
    ReportOut,
    ReportScope,
    ShareRow,
    SummaryOut,
    VolumePoint,
)
from app.modules.settings.service import load_business_settings
from app.modules.users.models import User, UserStatus

MAX_DAYS = 366
TOP = 5

FAILURE_LABELS = {
    FailureReason.CUSTOMER_ABSENT: "Customer not at home",
    FailureReason.CUSTOMER_UNREACHABLE: "Customer unreachable",
    FailureReason.CUSTOMER_REFUSED: "Customer refused",
    FailureReason.WRONG_ADDRESS: "Wrong address",
    FailureReason.OTHER: "Other reason",
}
INCIDENT_LABELS = {
    "TRAFFIC_JAM": "Traffic jam",
    "WEATHER": "Bad weather",
    "TRAFFIC_ACCIDENT": "Traffic accident",
    "VEHICLE_BREAKDOWN": "Vehicle breakdown",
    "HEALTH": "Health problem",
    "GOODS_DAMAGED": "Damaged goods",
    "OTHER": "Other",
    "ETA_ANOMALY": "ETA keeps slipping",
    "DRIVER_IDLE": "Driver not moving",
}


# =============================== Scope ===============================


async def resolve_scope(
    session: AsyncSession,
    user: CurrentUser,
    date_from: date | None,
    date_to: date | None,
    hub_ids: list[uuid.UUID] | None,
) -> ReportScope:
    """Dates default to the last 30 days. A hub manager only ever sees their own hub."""
    end = date_to or local_today()
    start = date_from or end - timedelta(days=29)
    if start > end:
        raise ValidationFailed("The start date must be before the end date", code="DATE_RANGE")
    if (end - start).days >= MAX_DAYS:
        raise ValidationFailed("Choose a period of one year or less", code="DATE_RANGE")
    wanted = list(dict.fromkeys(hub_ids or []))
    if user.hub_id is not None:
        if any(hub_id != user.hub_id for hub_id in wanted):
            raise Forbidden("You can only see reports of your hub", code="OUT_OF_SCOPE")
        wanted = [user.hub_id]
    names = list(
        await session.scalars(
            select(Hub.name).where(Hub.id.in_(wanted)).order_by(Hub.name)
            if wanted
            else select(Hub.name).order_by(Hub.name)
        )
    )
    length = (end - start).days + 1
    return ReportScope(
        date_from=start,
        date_to=end,
        hub_ids=wanted,
        hub_names=names,
        previous_from=start - timedelta(days=length),
        previous_to=start - timedelta(days=1),
    )


def _window(start: date, end: date) -> tuple[datetime, datetime]:
    return local_datetime(start, time(0, 0)), local_datetime(end + timedelta(days=1), time(0, 0))


def _orders_in(scope_hubs: list[uuid.UUID], start: date, end: date) -> ColumnElement[bool]:
    since, until = _window(start, end)
    condition = and_(Order.created_at >= since, Order.created_at < until)
    if scope_hubs:
        condition = and_(condition, Order.hub_id.in_(scope_hubs))
    return condition


def _in_hubs(column: Any, hubs: list[uuid.UUID]) -> ColumnElement[bool]:
    return column.in_(hubs) if hubs else true()


def _rate(part: float | None, whole: float | None) -> float | None:
    return round(part / whole, 4) if part is not None and whole else None


# =============================== Summary ===============================


async def _period_kpis(
    session: AsyncSession, hubs: list[uuid.UUID], start: date, end: date, grace: timedelta
) -> dict[str, float | None]:
    in_period = _orders_in(hubs, start, end)
    delivered = Order.status == OrderStatus.DELIVERED
    totals = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(delivered),
                func.count().filter(Order.status == OrderStatus.RETURNED_TO_HUB),
                func.count().filter(delivered, Order.delivered_at <= Order.promised_at + grace),
                func.avg(func.extract("epoch", Order.delivered_at - Order.created_at) / 60).filter(
                    delivered
                ),
            ).where(in_period)
        )
    ).one()
    total, done, returned, on_time, avg_minutes = totals
    since, until = _window(start, end)
    attempts = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(DeliveryAttempt.outcome == AttemptOutcome.FAILED),
            )
            .join(Order, Order.id == DeliveryAttempt.order_id)
            .where(
                DeliveryAttempt.attempted_at >= since,
                DeliveryAttempt.attempted_at < until,
                _in_hubs(Order.hub_id, hubs),
            )
        )
    ).one()
    incidents = await session.scalar(
        select(func.count()).where(
            Incident.reported_at >= since,
            Incident.reported_at < until,
            _in_hubs(Incident.hub_id, hubs),
        )
    )
    active_drivers = await session.scalar(
        select(func.count(func.distinct(Assignment.driver_id)))
        .join(Order, Order.id == Assignment.order_id)
        .where(
            Assignment.assigned_at >= since,
            Assignment.assigned_at < until,
            _in_hubs(Order.hub_id, hubs),
        )
    )
    return {
        "total_orders": total,
        "delivered": done,
        "success_rate": _rate(done, done + returned),
        "failed_attempt_rate": _rate(attempts[1], attempts[0]),
        "on_time_rate": _rate(on_time, done),
        "avg_delivery_minutes": round(float(avg_minutes), 1) if avg_minutes is not None else None,
        "incidents": incidents or 0,
        "active_drivers": active_drivers or 0,
    }


async def summary(session: AsyncSession, scope: ReportScope, grace: timedelta) -> SummaryOut:
    now = await _period_kpis(session, scope.hub_ids, scope.date_from, scope.date_to, grace)
    before = await _period_kpis(
        session, scope.hub_ids, scope.previous_from, scope.previous_to, grace
    )
    drivers = await session.scalar(
        select(func.count())
        .select_from(User)
        .join(Role, Role.id == User.role_id)
        .where(
            Role.code == RoleCode.DRIVER,
            User.status == UserStatus.ACTIVE,
            _in_hubs(User.hub_id, scope.hub_ids),
        )
    )
    return SummaryOut(
        scope=scope,
        total_drivers=drivers or 0,
        **{key: KpiOut(value=now[key], previous=before[key]) for key in now},
    )


# =============================== Breakdowns ===============================


def _bucket(granularity: Granularity) -> Any:
    local = func.timezone(str(BUSINESS_TZ), Order.created_at)
    return func.date_trunc(granularity.value, local)


def _periods(start: date, end: date, granularity: Granularity) -> list[date]:
    """Every bucket start between the dates, so empty days still show as zero."""
    if granularity == Granularity.MONTH:
        current = start.replace(day=1)
    elif granularity == Granularity.WEEK:
        current = start - timedelta(days=start.weekday())
    else:
        current = start
    result = []
    while current <= end:
        result.append(current)
        if granularity == Granularity.MONTH:
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            current += timedelta(days=7 if granularity == Granularity.WEEK else 1)
    return result


def _label(period: date, granularity: Granularity) -> str:
    if granularity == Granularity.MONTH:
        return period.strftime("%b %Y")
    if granularity == Granularity.WEEK:
        return f"Week of {period.strftime('%d %b')}"
    return period.strftime("%d %b")


async def volume(
    session: AsyncSession, scope: ReportScope, granularity: Granularity, grace: timedelta
) -> list[VolumePoint]:
    """Per period: created, delivered, delivered on time, returned (feeds the KPI trend lines)."""
    bucket = _bucket(granularity)
    delivered = Order.status == OrderStatus.DELIVERED
    rows = await session.execute(
        select(
            bucket,
            func.count(),
            func.count().filter(delivered),
            func.count().filter(delivered, Order.delivered_at <= Order.promised_at + grace),
            func.count().filter(Order.status == OrderStatus.RETURNED_TO_HUB),
        )
        .where(_orders_in(scope.hub_ids, scope.date_from, scope.date_to))
        .group_by(bucket)
    )
    counts = {moment.date(): tuple(values) for moment, *values in rows}
    empty = (0, 0, 0, 0)
    return [
        VolumePoint(
            period=period,
            label=_label(period, granularity),
            orders=counts.get(period, empty)[0],
            delivered=counts.get(period, empty)[1],
            on_time=counts.get(period, empty)[2],
            returned=counts.get(period, empty)[3],
        )
        for period in _periods(scope.date_from, scope.date_to, granularity)
    ]


def _shares(rows: list[tuple[str, str, int]]) -> list[ShareRow]:
    total = sum(count for _, _, count in rows) or 1
    return [
        ShareRow(key=key, label=label, count=count, share=round(count / total, 4))
        for key, label, count in sorted(rows, key=lambda row: -row[2])
    ]


async def failure_reasons(session: AsyncSession, scope: ReportScope) -> list[ShareRow]:
    since, until = _window(scope.date_from, scope.date_to)
    rows = await session.execute(
        select(DeliveryAttempt.failure_reason, func.count())
        .join(Order, Order.id == DeliveryAttempt.order_id)
        .where(
            DeliveryAttempt.outcome == AttemptOutcome.FAILED,
            DeliveryAttempt.attempted_at >= since,
            DeliveryAttempt.attempted_at < until,
            _in_hubs(Order.hub_id, scope.hub_ids),
        )
        .group_by(DeliveryAttempt.failure_reason)
    )
    return _shares(
        [
            (str(reason.value), FAILURE_LABELS.get(reason, reason.value), count)
            for reason, count in rows
            if reason is not None
        ]
    )


async def incident_types(session: AsyncSession, scope: ReportScope) -> list[ShareRow]:
    since, until = _window(scope.date_from, scope.date_to)
    rows = await session.execute(
        select(Incident.type, func.count())
        .where(
            Incident.reported_at >= since,
            Incident.reported_at < until,
            _in_hubs(Incident.hub_id, scope.hub_ids),
        )
        .group_by(Incident.type)
    )
    return _shares(
        [
            (str(kind.value), INCIDENT_LABELS.get(kind.value, kind.value), count)
            for kind, count in rows
        ]
    )


async def on_time_by_area(
    session: AsyncSession, scope: ReportScope, grace: timedelta
) -> list[AreaRow]:
    rows = await session.execute(
        select(
            func.coalesce(Area.name, "Outside known areas"),
            func.count(),
            func.count().filter(Order.delivered_at <= Order.promised_at + grace),
        )
        .select_from(Order)
        .outerjoin(Area, Area.id == Order.delivery_area_id)
        .where(
            _orders_in(scope.hub_ids, scope.date_from, scope.date_to),
            Order.status == OrderStatus.DELIVERED,
        )
        .group_by(Area.name)
    )
    result = [
        AreaRow(area=name, delivered=done, on_time=on_time, on_time_rate=_rate(on_time, done))
        for name, done, on_time in rows
    ]
    return sorted(result, key=lambda row: -(row.on_time_rate or 0))


async def _driver_ranking(
    session: AsyncSession, hubs: list[uuid.UUID], start: date, end: date, grace: timedelta
) -> list[tuple[uuid.UUID, str, str, int, int, int, int]]:
    """(driver, name, hub, delivered, on_time, attempts, delivered_attempts), best first."""
    since, until = _window(start, end)
    attempts = (
        select(
            DeliveryAttempt.driver_id.label("driver_id"),
            func.count().label("attempts"),
            func.count().filter(DeliveryAttempt.outcome == AttemptOutcome.DELIVERED).label("ok"),
        )
        .where(DeliveryAttempt.attempted_at >= since, DeliveryAttempt.attempted_at < until)
        .group_by(DeliveryAttempt.driver_id)
        .subquery()
    )
    delivered: Select[Any] = (
        select(
            Order.current_driver_id,
            User.full_name,
            Hub.name,
            func.count(),
            func.count().filter(Order.delivered_at <= Order.promised_at + grace),
            func.coalesce(func.max(attempts.c.attempts), 0),
            func.coalesce(func.max(attempts.c.ok), 0),
        )
        .join(User, User.id == Order.current_driver_id)
        .join(Hub, Hub.id == Order.hub_id)
        .outerjoin(attempts, attempts.c.driver_id == Order.current_driver_id)
        .where(_orders_in(hubs, start, end), Order.status == OrderStatus.DELIVERED)
        .group_by(Order.current_driver_id, User.full_name, Hub.name)
    )
    rows: list[tuple[uuid.UUID, str, str, int, int, int, int]] = [
        (driver, name, hub, done, on_time, attempts_count, ok)
        for driver, name, hub, done, on_time, attempts_count, ok in await session.execute(delivered)
    ]
    rows.sort(key=lambda row: (-row[3], -(row[4] / row[3] if row[3] else 0), row[1]))
    return rows


async def top_drivers(
    session: AsyncSession, scope: ReportScope, grace: timedelta
) -> list[DriverRow]:
    now = await _driver_ranking(session, scope.hub_ids, scope.date_from, scope.date_to, grace)
    before = await _driver_ranking(
        session, scope.hub_ids, scope.previous_from, scope.previous_to, grace
    )
    previous = {row[0]: index + 1 for index, row in enumerate(before)}
    return [
        DriverRow(
            rank=index + 1,
            previous_rank=previous.get(driver_id),
            driver_id=driver_id,
            name=name,
            hub=hub,
            delivered=done,
            success_rate=_rate(ok, attempts),
            on_time_rate=_rate(on_time, done),
        )
        for index, (driver_id, name, hub, done, on_time, attempts, ok) in enumerate(now[:TOP])
    ]


async def _hub_ranking(
    session: AsyncSession, hubs: list[uuid.UUID], start: date, end: date, grace: timedelta
) -> list[tuple[uuid.UUID, str, int, int, int]]:
    rows = await session.execute(
        select(
            Hub.id,
            Hub.name,
            func.count(Order.id),
            func.count(Order.id).filter(Order.status == OrderStatus.DELIVERED),
            func.count(Order.id).filter(
                Order.status == OrderStatus.DELIVERED,
                Order.delivered_at <= Order.promised_at + grace,
            ),
        )
        .join(Order, Order.hub_id == Hub.id)
        .where(_orders_in(hubs, start, end))
        .group_by(Hub.id, Hub.name)
    )
    result = [(hub_id, name, orders, done, on_time) for hub_id, name, orders, done, on_time in rows]
    result.sort(key=lambda row: (-row[3], row[1]))
    return result


async def top_hubs(session: AsyncSession, scope: ReportScope, grace: timedelta) -> list[HubRow]:
    now = await _hub_ranking(session, scope.hub_ids, scope.date_from, scope.date_to, grace)
    before = await _hub_ranking(
        session, scope.hub_ids, scope.previous_from, scope.previous_to, grace
    )
    previous = {row[0]: index + 1 for index, row in enumerate(before)}
    return [
        HubRow(
            rank=index + 1,
            previous_rank=previous.get(hub_id),
            hub_id=hub_id,
            name=name,
            orders=orders,
            delivered=done,
            on_time_rate=_rate(on_time, done),
        )
        for index, (hub_id, name, orders, done, on_time) in enumerate(now[:TOP])
    ]


# =============================== Full report ===============================


async def build_report(
    session: AsyncSession, scope: ReportScope, granularity: Granularity
) -> ReportOut:
    settings = await load_business_settings(session)
    grace = timedelta(minutes=settings.sla_grace_min)
    return ReportOut(
        summary=await summary(session, scope, grace),
        granularity=granularity,
        volume=await volume(session, scope, granularity, grace),
        failure_reasons=await failure_reasons(session, scope),
        incident_types=await incident_types(session, scope),
        on_time_by_area=await on_time_by_area(session, scope, grace),
        top_drivers=await top_drivers(session, scope, grace),
        top_hubs=await top_hubs(session, scope, grace),
    )


def default_granularity(scope: ReportScope) -> Granularity:
    days = (scope.date_to - scope.date_from).days + 1
    if days <= 45:
        return Granularity.DAY
    if days <= 180:
        return Granularity.WEEK
    return Granularity.MONTH


def local_now_label() -> str:
    return datetime.now(BUSINESS_TZ).strftime("%d %b %Y %H:%M")
