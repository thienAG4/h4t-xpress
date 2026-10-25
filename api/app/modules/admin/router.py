"""System configuration endpoints (A-04 hubs and areas, A-05 shifts, A-06 settings,
A-07 audit log)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_permission
from app.core.pagination import Page, PageParams, page_params
from app.modules.admin import service
from app.modules.admin.schemas import (
    AdminHubOut,
    AreaIn,
    AreaOut,
    AuditOut,
    HubIn,
    SettingIn,
    SettingOut,
    ShiftOut,
    ShiftUpdateIn,
)

router = APIRouter(prefix="/admin", tags=["admin: configuration"])
HubAdmin = Annotated[CurrentUser, Depends(require_permission("hub.manage"))]
SettingsAdmin = Annotated[CurrentUser, Depends(require_permission("settings.manage"))]
Auditor = Annotated[CurrentUser, Depends(require_permission("audit.view"))]
Paging = Annotated[PageParams, Depends(page_params)]


# =============================== Areas and hubs (A-04) ===============================


@router.get("/areas", response_model=list[AreaOut])
async def list_areas(session: DbSession, _: HubAdmin) -> list[AreaOut]:
    return await service.list_areas(session)


@router.post("/areas", response_model=AreaOut, status_code=201)
async def create_area(data: AreaIn, session: DbSession, admin: HubAdmin) -> AreaOut:
    """Errors: AREA_CODE_TAKEN"""
    return await service.save_area(session, admin.id, data)


@router.put("/areas/{area_id}", response_model=AreaOut)
async def update_area(
    area_id: uuid.UUID, data: AreaIn, session: DbSession, admin: HubAdmin
) -> AreaOut:
    return await service.save_area(session, admin.id, data, area_id)


@router.get("/hubs", response_model=list[AdminHubOut])
async def list_hubs(session: DbSession, _: HubAdmin) -> list[AdminHubOut]:
    """Every hub, active or not, with its area and staff counts."""
    return await service.list_hubs(session)


@router.post("/hubs", response_model=AdminHubOut, status_code=201)
async def create_hub(data: HubIn, session: DbSession, admin: HubAdmin) -> AdminHubOut:
    """Errors: HUB_CODE_TAKEN, AREA_NOT_FOUND"""
    return await service.save_hub(session, admin.id, data)


@router.put("/hubs/{hub_id}", response_model=AdminHubOut)
async def update_hub(
    hub_id: uuid.UUID, data: HubIn, session: DbSession, admin: HubAdmin
) -> AdminHubOut:
    return await service.save_hub(session, admin.id, data, hub_id)


# =============================== Shifts (A-05) ===============================


@router.get("/shifts", response_model=list[ShiftOut])
async def list_shifts(
    session: DbSession, _: HubAdmin, hub_id: uuid.UUID | None = None
) -> list[ShiftOut]:
    """Shift templates per hub with today's registrations."""
    return await service.list_shifts(session, hub_id)


@router.patch("/shifts/{shift_id}", response_model=ShiftOut)
async def update_shift(
    shift_id: uuid.UUID, data: ShiftUpdateIn, session: DbSession, admin: HubAdmin
) -> ShiftOut:
    """Inputs: any of name, start_time, end_time, capacity, is_active. Errors: SHIFT_TIME_INVALID"""
    return await service.update_shift(session, admin.id, shift_id, data)


# =============================== Settings (A-06) ===============================


@router.get("/settings", response_model=list[SettingOut])
async def list_settings(session: DbSession, _: SettingsAdmin) -> list[SettingOut]:
    """Dispatch, ETA, SLA, delivery, shift, anomaly and simulator parameters."""
    return await service.list_settings(session)


@router.put("/settings/{key}", response_model=SettingOut)
async def update_setting(
    key: str, data: SettingIn, session: DbSession, admin: SettingsAdmin
) -> SettingOut:
    """
    Change one parameter; the new value applies to the next dispatch round or ETA refresh.

    Errors: SETTING_NOT_FOUND, SETTING_INVALID (with the rule that failed)
    """
    return await service.update_setting(session, admin.id, key, data.value)


# =============================== Audit log (A-07) ===============================


@router.get("/audit-logs", response_model=Page[AuditOut])
async def list_audit_logs(
    session: DbSession,
    _: Auditor,
    paging: Paging,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> Page[AuditOut]:
    """Newest first. `action` matches a prefix, e.g. "user." or "setting.updated"."""
    return await service.list_audit(
        session, paging, action=action, entity_type=entity_type, actor_id=actor_id
    )
