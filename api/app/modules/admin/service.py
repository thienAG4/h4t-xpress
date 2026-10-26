"""System configuration for the system admin: hubs and areas (A-04), shifts (A-05),
business settings (A-06) and the audit log (A-07). Every change is audited.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.pagination import Page, PageParams
from app.modules.admin.schemas import (
    AdminHubOut,
    AreaIn,
    AreaOut,
    AuditOut,
    HubIn,
    SettingOut,
    ShiftOut,
    ShiftUpdateIn,
)
from app.modules.audit.models import AuditLog
from app.modules.audit.service import record_audit
from app.modules.hubs.models import (
    Area,
    AreaAdjacency,
    Hub,
    Shift,
    ShiftRegistration,
    ShiftRegistrationStatus,
)
from app.modules.rbac.models import Role, RoleCode
from app.modules.settings.models import SystemSetting
from app.modules.users.models import User

logger = logging.getLogger(__name__)

# Internal simulator state is not edited by hand.
HIDDEN_SETTINGS = ("sim.paused_drivers", "sim.last_reset")


# =============================== Areas and hubs (A-04) ===============================


async def list_areas(session: AsyncSession) -> list[AreaOut]:
    areas = list(await session.scalars(select(Area).order_by(Area.name)))
    codes = {area.id: area.code for area in areas}
    neighbors: dict[uuid.UUID, list[str]] = {}
    for link in await session.scalars(select(AreaAdjacency)):
        neighbors.setdefault(link.area_id, []).append(codes[link.neighbor_area_id])
    return [
        AreaOut(
            id=area.id,
            code=area.code,
            name=area.name,
            center_lat=area.center_lat,
            center_lng=area.center_lng,
            radius_km=area.radius_km,
            neighbor_codes=sorted(neighbors.get(area.id, [])),
        )
        for area in areas
    ]


async def save_area(
    session: AsyncSession, actor_id: uuid.UUID, data: AreaIn, area_id: uuid.UUID | None = None
) -> AreaOut:
    area = await session.get(Area, area_id) if area_id else Area()
    if area is None:
        raise NotFound("Area not found", code="AREA_NOT_FOUND")
    before = {"name": area.name, "radius_km": area.radius_km} if area_id else None
    for field, value in data.model_dump().items():
        setattr(area, field, value)
    session.add(area)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise Conflict("This area code is already used", code="AREA_CODE_TAKEN") from exc
    record_audit(session, actor_id=actor_id, action="area.saved", entity_type="area",
                 entity_id=area.id, before=before, after=data.model_dump())  # fmt: skip
    await session.commit()
    return next(item for item in await list_areas(session) if item.id == area.id)


async def list_hubs(session: AsyncSession) -> list[AdminHubOut]:
    role_count = (
        select(func.count())
        .select_from(User)
        .join(Role, Role.id == User.role_id)
        .where(User.hub_id == Hub.id)
        .correlate(Hub)
    )
    rows = await session.execute(
        select(
            Hub,
            Area.name,
            role_count.where(Role.code == RoleCode.DRIVER).scalar_subquery(),
            role_count.where(Role.code == RoleCode.HUB_MANAGER).scalar_subquery(),
        )
        .join(Area, Area.id == Hub.area_id)
        .order_by(Hub.name)
    )
    return [
        AdminHubOut(
            id=hub.id,
            code=hub.code,
            name=hub.name,
            address=hub.address,
            lat=hub.lat,
            lng=hub.lng,
            area_id=hub.area_id,
            area_name=area_name,
            status=hub.status,
            drivers=drivers or 0,
            managers=managers or 0,
        )
        for hub, area_name, drivers, managers in rows
    ]


async def save_hub(
    session: AsyncSession, actor_id: uuid.UUID, data: HubIn, hub_id: uuid.UUID | None = None
) -> AdminHubOut:
    if await session.get(Area, data.area_id) is None:
        raise ValidationFailed("Choose an existing area", code="AREA_NOT_FOUND")
    hub = await session.get(Hub, hub_id) if hub_id else Hub()
    if hub is None:
        raise NotFound("Hub not found", code="HUB_NOT_FOUND")
    before = (
        {"name": hub.name, "status": hub.status, "lat": hub.lat, "lng": hub.lng} if hub_id else None
    )
    for field, value in data.model_dump().items():
        setattr(hub, field, value)
    session.add(hub)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise Conflict("This hub code is already used", code="HUB_CODE_TAKEN") from exc
    record_audit(session, actor_id=actor_id, action="hub.saved", entity_type="hub",
                 entity_id=hub.id, before=before, after=data.model_dump(mode="json"))  # fmt: skip
    await session.commit()
    return next(item for item in await list_hubs(session) if item.id == hub.id)


# =============================== Shifts (A-05) ===============================


async def list_shifts(session: AsyncSession, hub_id: uuid.UUID | None) -> list[ShiftOut]:
    registered = (
        select(func.count())
        .where(
            ShiftRegistration.shift_id == Shift.id,
            ShiftRegistration.work_date == local_today(),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
        .correlate(Shift)
        .scalar_subquery()
    )
    query = select(Shift, Hub.name, registered).join(Hub, Hub.id == Shift.hub_id)
    if hub_id:
        query = query.where(Shift.hub_id == hub_id)
    rows = await session.execute(query.order_by(Hub.name, Shift.start_time, Shift.code))
    return [
        ShiftOut(
            id=shift.id,
            hub_id=shift.hub_id,
            hub_name=hub_name,
            code=shift.code,
            name=shift.name,
            start_time=shift.start_time,
            end_time=shift.end_time,
            capacity=shift.capacity,
            is_active=shift.is_active,
            registered_today=count or 0,
        )
        for shift, hub_name, count in rows
    ]


async def update_shift(
    session: AsyncSession, actor_id: uuid.UUID, shift_id: uuid.UUID, data: ShiftUpdateIn
) -> ShiftOut:
    shift = await session.get(Shift, shift_id)
    if shift is None:
        raise NotFound("Shift not found", code="SHIFT_NOT_FOUND")
    changes = data.model_dump(exclude_unset=True)
    start = changes.get("start_time", shift.start_time)
    end = changes.get("end_time", shift.end_time)
    if end <= start:
        raise ValidationFailed("The shift must end after it starts", code="SHIFT_TIME_INVALID")
    before = {"start_time": str(shift.start_time), "end_time": str(shift.end_time),
              "capacity": shift.capacity, "is_active": shift.is_active}  # fmt: skip
    for field, value in changes.items():
        setattr(shift, field, value)
    record_audit(session, actor_id=actor_id, action="shift.updated", entity_type="shift",
                 entity_id=shift.id, before=before, after=data.model_dump(mode="json",
                 exclude_unset=True))  # fmt: skip
    await session.commit()
    return next(item for item in await list_shifts(session, shift.hub_id) if item.id == shift.id)


# =============================== Settings (A-06) ===============================


def _number(minimum: float, maximum: float, integer: bool = False) -> Any:
    def check(value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a number")
        if integer and int(value) != value:
            raise ValueError("must be a whole number")
        if not minimum <= value <= maximum:
            raise ValueError(f"must be between {minimum:g} and {maximum:g}")
        return int(value) if integer else float(value)

    return check


def _boolean(value: Any) -> Any:
    if not isinstance(value, bool):
        raise ValueError("must be true or false")
    return value


def _weights(value: Any) -> Any:
    keys = {"distance", "load", "performance", "time_fit"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"must have exactly the keys {sorted(keys)}")
    numbers = {key: _number(0, 1)(value[key]) for key in keys}
    if abs(sum(numbers.values()) - 1) > 0.001:
        raise ValueError("the four weights must add up to 1")
    return numbers


def _traffic(value: Any) -> Any:
    if not isinstance(value, list):
        raise ValueError("must be a list of {from, to, factor}")
    rules = []
    for rule in value:
        if not isinstance(rule, dict) or not {"from", "to", "factor"} <= set(rule):
            raise ValueError("each rule needs from, to and factor")
        start, end = str(rule["from"]), str(rule["to"])
        if len(start) != 5 or len(end) != 5 or start >= end:
            raise ValueError("from and to are HH:MM times with from before to")
        rules.append({"from": start, "to": end, "factor": _number(0.5, 3)(rule["factor"])})
    return rules


def _time_of_day(value: Any) -> Any:
    text = str(value)
    if len(text) != 5 or text[2] != ":" or not (text[:2] + text[3:]).isdigit():
        raise ValueError("must be a HH:MM time")
    return text


# Validation per key; a key not listed here cannot be edited from the screen.
SETTING_RULES: dict[str, Any] = {
    "dispatch.weights": _weights,
    "dispatch.offer_timeout_s": _number(10, 3600, integer=True),
    "dispatch.max_candidates_per_round": _number(1, 20, integer=True),
    "dispatch.max_rounds": _number(1, 10, integer=True),
    "dispatch.round_retry_delay_s": _number(10, 3600, integer=True),
    "dispatch.max_active_orders": _number(1, 100, integer=True),
    "dispatch.max_distance_km": _number(1, 100),
    "dispatch.location_fresh_min": _number(1, 1440, integer=True),
    "dispatch.enforce_shift_hours": _boolean,
    "eta.service_time_min": _number(0, 60),
    "eta.traffic_factors": _traffic,
    "eta.default_traffic_factor": _number(0.5, 3),
    "eta.notify_threshold_min": _number(1, 240),
    "eta.recompute_interval_s": _number(5, 600, integer=True),
    "eta.fallback_speed_kmh": _number(5, 80),
    "eta.fallback_road_factor": _number(1, 3),
    "sla.grace_min": _number(0, 1440, integer=True),
    "delivery.max_attempts": _number(1, 10, integer=True),
    "shift.cutoff_time": _time_of_day,
    "shift.max_days_ahead": _number(1, 30, integer=True),
    "anomaly.eta_increase_count": _number(2, 10, integer=True),
    "anomaly.eta_increase_total_min": _number(5, 240),
    "anomaly.idle_minutes": _number(1, 120),
    "anomaly.idle_radius_m": _number(10, 1000),
    "sim.gps_enabled": _boolean,
    "sim.speed_factor": _number(1, 50),
}


def _out(row: SystemSetting) -> SettingOut:
    return SettingOut(
        key=row.key,
        group=row.key.split(".", 1)[0],
        value=row.value,
        description=row.description,
        updated_at=row.updated_at,
    )


async def list_settings(session: AsyncSession) -> list[SettingOut]:
    rows = await session.scalars(
        select(SystemSetting)
        .where(SystemSetting.key.not_in(HIDDEN_SETTINGS))
        .order_by(SystemSetting.key)
    )
    return [_out(row) for row in rows]


async def update_setting(
    session: AsyncSession, actor_id: uuid.UUID, key: str, value: Any
) -> SettingOut:
    rule = SETTING_RULES.get(key)
    row = await session.get(SystemSetting, key)
    if row is None or rule is None:
        raise NotFound("This setting cannot be changed here", code="SETTING_NOT_FOUND")
    try:
        clean = rule(value)
    except (ValueError, TypeError) as exc:
        raise ValidationFailed(f"{key} {exc}", code="SETTING_INVALID") from exc
    before = row.value
    row.value = clean
    row.updated_by = actor_id
    record_audit(session, actor_id=actor_id, action="setting.updated", entity_type="setting",
                 entity_id=key, before={"value": before}, after={"value": clean})  # fmt: skip
    await session.commit()
    await session.refresh(row)
    logger.info("[update_setting] %s=%s by %s", key, clean, actor_id)
    return _out(row)


# =============================== Audit log (A-07) ===============================


async def list_audit(
    session: AsyncSession,
    paging: PageParams,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> Page[AuditOut]:
    query = select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.actor_user_id)
    if action:
        query = query.where(AuditLog.action.like(f"{action}%"))
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if actor_id:
        query = query.where(AuditLog.actor_user_id == actor_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.execute(
        query.order_by(AuditLog.created_at.desc()).offset(paging.offset).limit(paging.page_size)
    )
    return Page(
        items=[
            AuditOut(
                id=log.id,
                created_at=log.created_at,
                actor_name=name,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                before=log.before,
                after=log.after,
                ip=log.ip,
            )
            for log, name in rows
        ],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )
