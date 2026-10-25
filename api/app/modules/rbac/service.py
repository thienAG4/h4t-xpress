"""Roles and the editable role-permission matrix (FR-A-02, SPEC §2.2)."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.modules.audit.service import record_audit
from app.modules.auth.models import RefreshToken
from app.modules.rbac.models import Permission, Role, RoleCode, RolePermission
from app.modules.rbac.schemas import PermissionOut, RoleOut
from app.modules.users.models import User

logger = logging.getLogger(__name__)

# Removing these from SYSTEM_ADMIN would leave nobody able to repair the matrix.
LOCKOUT_GUARD: dict[str, set[str]] = {RoleCode.SYSTEM_ADMIN: {"role.manage", "user.manage"}}


# =============================== Queries ===============================


async def get_permission_codes(session: AsyncSession, role_id: uuid.UUID) -> list[str]:
    result = await session.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    )
    return list(result)


async def get_role_by_code(session: AsyncSession, code: str) -> Role:
    role = await session.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise NotFound(f"Role {code} does not exist", code="ROLE_NOT_FOUND")
    return role


async def list_permissions(session: AsyncSession) -> list[PermissionOut]:
    rows = await session.scalars(select(Permission).order_by(Permission.group, Permission.code))
    return [PermissionOut(code=p.code, group=p.group, description=p.description) for p in rows]


async def list_roles(session: AsyncSession) -> list[RoleOut]:
    roles = list(await session.scalars(select(Role).order_by(Role.created_at, Role.code)))
    counts = dict(
        (await session.execute(select(User.role_id, func.count()).group_by(User.role_id))).all()
    )
    return [
        RoleOut(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=await get_permission_codes(session, role.id),
            user_count=counts.get(role.id, 0),
        )
        for role in roles
    ]


# =============================== Commands ===============================


async def update_role_permissions(
    session: AsyncSession,
    *,
    role_id: uuid.UUID,
    codes: list[str],
    force_relogin: bool,
    actor_id: uuid.UUID,
    ip: str | None,
) -> RoleOut:
    role = await session.get(Role, role_id)
    if role is None:
        raise NotFound("Role not found", code="ROLE_NOT_FOUND")

    wanted = set(codes)
    known = dict((await session.execute(select(Permission.code, Permission.id))).all())
    unknown = sorted(wanted - set(known))
    if unknown:
        raise ValidationFailed(
            "Unknown permission codes", code="UNKNOWN_PERMISSION", details=unknown
        )
    required = LOCKOUT_GUARD.get(role.code, set())
    if not required <= wanted:
        raise ValidationFailed(
            "These permissions cannot be removed from this role",
            code="LOCKOUT_PREVENTED",
            details=sorted(required - wanted),
        )

    before = await get_permission_codes(session, role.id)
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    session.add_all(RolePermission(role_id=role.id, permission_id=known[c]) for c in wanted)

    if force_relogin:
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.revoked_at.is_(None),
                RefreshToken.user_id.in_(select(User.id).where(User.role_id == role.id)),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    record_audit(
        session,
        actor_id=actor_id,
        action="role.permissions_updated",
        entity_type="role",
        entity_id=role.id,
        before={"permissions": before},
        after={"permissions": sorted(wanted), "force_relogin": force_relogin},
        ip=ip,
    )
    await session.commit()
    logger.info("[update_role_permissions] role=%s permissions=%d", role.code, len(wanted))
    return next(r for r in await list_roles(session) if r.id == role.id)
