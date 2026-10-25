"""System admin: roles and permission matrix (screen A-03)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.deps import CurrentUser, DbSession, client_ip, require_permission
from app.modules.rbac import service
from app.modules.rbac.schemas import PermissionOut, RoleOut, UpdateRolePermissionsIn

router = APIRouter(prefix="/admin", tags=["admin: roles"])
RoleManager = Annotated[CurrentUser, Depends(require_permission("role.manage"))]


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(session: DbSession, _: RoleManager) -> list[RoleOut]:
    """
    All roles with their permission codes and number of users.

    Outputs: [{"id", "code", "name", "permissions": ["user.manage", ...], "user_count"}]
    """
    return await service.list_roles(session)


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(session: DbSession, _: RoleManager) -> list[PermissionOut]:
    """Permission catalogue, grouped by area (driver, hub, report, admin)."""
    return await service.list_permissions(session)


@router.put("/roles/{role_id}/permissions", response_model=RoleOut)
async def update_role_permissions(
    role_id: uuid.UUID,
    data: UpdateRolePermissionsIn,
    request: Request,
    session: DbSession,
    user: RoleManager,
) -> RoleOut:
    """
    Replace the permission set of a role.

    Inputs: {"permissions": ["report.view", ...], "force_relogin": false}
    Errors: UNKNOWN_PERMISSION, LOCKOUT_PREVENTED (SYSTEM_ADMIN must keep role/user management)
    """
    return await service.update_role_permissions(
        session,
        role_id=role_id,
        codes=data.permissions,
        force_relogin=data.force_relogin,
        actor_id=user.id,
        ip=client_ip(request),
    )
