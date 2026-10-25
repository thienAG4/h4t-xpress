"""Account management for system admins (FR-A-01) and self-service profile (/me)."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Row, Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationFailed
from app.core.pagination import Page, PageParams
from app.core.security import generate_temporary_password, hash_password, verify_password
from app.modules.audit.service import record_audit
from app.modules.auth.models import RefreshToken
from app.modules.hubs.models import Hub
from app.modules.rbac.models import Role, RoleCode
from app.modules.rbac.service import get_permission_codes, get_role_by_code
from app.modules.users.models import DriverProfile, User, UserStatus
from app.modules.users.schemas import (
    DriverProfileOut,
    MeOut,
    MeUpdateIn,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)

logger = logging.getLogger(__name__)

DEMO_EMAIL_DOMAIN = "@demo.h4t"
ROLES_WITH_HUB = {RoleCode.HUB_MANAGER, RoleCode.DRIVER}


# =============================== Read model ===============================


def _user_select() -> Select[User, str, str, str, DriverProfile]:
    """User with role, hub name and driver profile (hub and profile may be NULL)."""
    return (
        select(User, Role.code, Role.name, Hub.name, DriverProfile)
        .join(Role, Role.id == User.role_id)
        .outerjoin(Hub, Hub.id == User.hub_id)
        .outerjoin(DriverProfile, DriverProfile.user_id == User.id)
    )


def _to_out(row: Row[User, str, str, str, DriverProfile]) -> UserOut:
    user, role_code, role_name = row[0], row[1], row[2]
    hub_name: str | None = row[3]
    profile: DriverProfile | None = row[4]
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=role_code,
        role_name=role_name,
        hub_id=user.hub_id,
        hub_name=hub_name,
        status=user.status,
        national_id=user.national_id,
        gender=user.gender,
        address=user.address,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        driver=DriverProfileOut(
            vehicle_plate=profile.vehicle_plate,
            license_no=profile.license_no,
            availability=profile.availability,
            rating=profile.rating,
        )
        if profile
        else None,
    )


async def get_user_out(session: AsyncSession, user_id: uuid.UUID) -> UserOut:
    row = (await session.execute(_user_select().where(User.id == user_id))).first()
    if row is None:
        raise NotFound("User not found", code="USER_NOT_FOUND")
    return _to_out(row)


async def list_users(
    session: AsyncSession,
    paging: PageParams,
    *,
    q: str | None = None,
    role: str | None = None,
    hub_id: uuid.UUID | None = None,
    status: UserStatus | None = None,
) -> Page[UserOut]:
    query = _user_select()
    if q:
        pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).like(pattern),
                func.lower(User.email).like(pattern),
                User.phone.like(pattern),
            )
        )
    if role:
        query = query.where(Role.code == role)
    if hub_id:
        query = query.where(User.hub_id == hub_id)
    if status:
        query = query.where(User.status == status)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.execute(
        query.order_by(Role.code, User.full_name).offset(paging.offset).limit(paging.page_size)
    )
    return Page(
        items=[_to_out(row) for row in rows],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


# =============================== Validation helpers ===============================


def _is_protected_demo_account(user: User) -> bool:
    """Public demo: shared accounts cannot be locked or have credentials changed (SPEC §7.4)."""
    return get_settings().demo_mode and user.email.endswith(DEMO_EMAIL_DOMAIN)


async def _ensure_unique(
    session: AsyncSession, *, email: str | None, phone: str | None, exclude: uuid.UUID | None
) -> None:
    if email:
        query = select(User.id).where(func.lower(User.email) == email.lower())
        if exclude:
            query = query.where(User.id != exclude)
        if await session.scalar(query):
            raise Conflict("This e-mail is already used", code="EMAIL_TAKEN")
    if phone:
        query = select(User.id).where(User.phone == phone)
        if exclude:
            query = query.where(User.id != exclude)
        if await session.scalar(query):
            raise Conflict("This phone number is already used", code="PHONE_TAKEN")


async def _ensure_hub(session: AsyncSession, role: RoleCode, hub_id: uuid.UUID | None) -> None:
    if role in ROLES_WITH_HUB and hub_id is None:
        raise ValidationFailed("A hub is required for this role", code="HUB_REQUIRED")
    if hub_id is not None and await session.get(Hub, hub_id) is None:
        raise NotFound("Hub not found", code="HUB_NOT_FOUND")


async def _load_user(session: AsyncSession, user_id: uuid.UUID) -> tuple[User, Role]:
    row = (
        await session.execute(
            select(User, Role).join(Role, Role.id == User.role_id).where(User.id == user_id)
        )
    ).first()
    if row is None:
        raise NotFound("User not found", code="USER_NOT_FOUND")
    return row[0], row[1]


async def revoke_sessions(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return int(getattr(result, "rowcount", 0) or 0)


# =============================== Admin commands ===============================


async def create_user(
    session: AsyncSession, data: UserCreateIn, *, actor_id: uuid.UUID, ip: str | None
) -> tuple[UserOut, str | None]:
    """Create any account. Returns the user and a temporary password when none was given."""
    email = data.email.lower()
    await _ensure_unique(session, email=email, phone=data.phone, exclude=None)
    await _ensure_hub(session, data.role, data.hub_id)
    if data.role == RoleCode.DRIVER and not (data.vehicle_plate and data.license_no):
        raise ValidationFailed(
            "Vehicle plate and licence number are required for drivers",
            code="DRIVER_FIELDS_REQUIRED",
        )

    role = await get_role_by_code(session, data.role)
    temporary = None if data.password else generate_temporary_password()
    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=data.phone,
        password_hash=hash_password(data.password or temporary or ""),
        role_id=role.id,
        hub_id=data.hub_id if data.role in ROLES_WITH_HUB else None,
        national_id=data.national_id,
        gender=data.gender,
        address=data.address,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()
    if data.role == RoleCode.DRIVER:
        hub = await session.get(Hub, data.hub_id)
        session.add(
            DriverProfile(
                user_id=user.id,
                vehicle_plate=data.vehicle_plate or "",
                license_no=data.license_no or "",
                home_area_id=hub.area_id if hub else None,
            )
        )
    record_audit(
        session,
        actor_id=actor_id,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        after={"email": email, "role": data.role.value},
        ip=ip,
    )
    await session.commit()
    logger.info("[create_user] role=%s email=%s", data.role, email)
    return await get_user_out(session, user.id), temporary


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: UserUpdateIn,
    *,
    actor_id: uuid.UUID,
    ip: str | None,
) -> UserOut:
    user, role = await _load_user(session, user_id)
    changes = data.model_dump(exclude_unset=True)
    # Forms send the whole record; only values that really differ count as changes.
    if changes.get("email") and changes["email"].lower() == user.email:
        changes.pop("email")
    if changes.get("role") == role.code:
        changes.pop("role")
    protected = _is_protected_demo_account(user)
    if protected and ({"email", "role"} & changes.keys()):
        raise Forbidden("Demo accounts keep their e-mail and role", code="DEMO_ACCOUNT_PROTECTED")

    new_role = RoleCode(changes.get("role") or role.code)
    if new_role != role.code and RoleCode.DRIVER in (new_role, role.code):
        raise ValidationFailed(
            "Switching to or from the driver role is not supported",
            code="ROLE_CHANGE_NOT_SUPPORTED",
        )
    if changes.get("email"):
        changes["email"] = changes["email"].lower()
    await _ensure_unique(
        session, email=changes.get("email"), phone=changes.get("phone"), exclude=user.id
    )
    hub_id = changes.get("hub_id", user.hub_id)
    await _ensure_hub(session, new_role, hub_id)

    before: dict[str, Any] = {}
    for field in ("full_name", "email", "phone", "national_id", "gender", "address", "hub_id"):
        if field in changes:
            before[field] = str(getattr(user, field)) if getattr(user, field) else None
            setattr(user, field, changes[field])
    if new_role != role.code:
        before["role"] = role.code
        user.role_id = (await get_role_by_code(session, new_role)).id
        user.hub_id = hub_id if new_role in ROLES_WITH_HUB else None

    profile = await session.get(DriverProfile, user.id)
    if profile:
        for field in ("vehicle_plate", "license_no"):
            if changes.get(field):
                setattr(profile, field, changes[field])

    record_audit(
        session,
        actor_id=actor_id,
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={key: str(value) if value is not None else None for key, value in changes.items()},
        ip=ip,
    )
    await session.commit()
    return await get_user_out(session, user.id)


async def set_locked(
    session: AsyncSession, user_id: uuid.UUID, *, locked: bool, actor_id: uuid.UUID, ip: str | None
) -> UserOut:
    user, _ = await _load_user(session, user_id)
    if user.id == actor_id:
        raise ValidationFailed("You cannot lock your own account", code="CANNOT_LOCK_SELF")
    if _is_protected_demo_account(user):
        raise Forbidden("Demo accounts cannot be locked", code="DEMO_ACCOUNT_PROTECTED")
    before = user.status
    user.status = UserStatus.LOCKED if locked else UserStatus.ACTIVE
    if locked:
        await revoke_sessions(session, user.id)
    record_audit(
        session,
        actor_id=actor_id,
        action="user.locked" if locked else "user.unlocked",
        entity_type="user",
        entity_id=user.id,
        before={"status": before},
        after={"status": user.status},
        ip=ip,
    )
    await session.commit()
    return await get_user_out(session, user.id)


async def reset_password(
    session: AsyncSession, user_id: uuid.UUID, *, actor_id: uuid.UUID, ip: str | None
) -> str:
    """Set a temporary password (shown once) and sign the user out everywhere."""
    user, _ = await _load_user(session, user_id)
    if _is_protected_demo_account(user):
        raise Forbidden("Demo account passwords cannot be changed", code="DEMO_ACCOUNT_PROTECTED")
    temporary = generate_temporary_password()
    user.password_hash = hash_password(temporary)
    await revoke_sessions(session, user.id)
    record_audit(
        session,
        actor_id=actor_id,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        ip=ip,
    )
    await session.commit()
    return temporary


async def revoke_user_sessions(
    session: AsyncSession, user_id: uuid.UUID, *, actor_id: uuid.UUID, ip: str | None
) -> int:
    await _load_user(session, user_id)
    count = await revoke_sessions(session, user_id)
    record_audit(
        session,
        actor_id=actor_id,
        action="user.sessions_revoked",
        entity_type="user",
        entity_id=user_id,
        after={"revoked": count},
        ip=ip,
    )
    await session.commit()
    return count


# =============================== Self service (/me) ===============================


async def get_me(session: AsyncSession, user_id: uuid.UUID) -> MeOut:
    out = await get_user_out(session, user_id)
    role_id = await session.scalar(select(User.role_id).where(User.id == user_id))
    assert role_id is not None
    return MeOut(**out.model_dump(), permissions=await get_permission_codes(session, role_id))


async def update_me(session: AsyncSession, user_id: uuid.UUID, data: MeUpdateIn) -> MeOut:
    user, _ = await _load_user(session, user_id)
    changes = data.model_dump(exclude_unset=True)
    await _ensure_unique(session, email=None, phone=changes.get("phone"), exclude=user.id)
    for field, value in changes.items():
        setattr(user, field, value)
    await session.commit()
    return await get_me(session, user_id)


async def change_password(
    session: AsyncSession, user_id: uuid.UUID, *, current: str, new: str
) -> None:
    user, _ = await _load_user(session, user_id)
    if _is_protected_demo_account(user):
        raise Forbidden("Demo account passwords cannot be changed", code="DEMO_ACCOUNT_PROTECTED")
    if not verify_password(current, user.password_hash):
        raise Unauthorized("Current password is incorrect", code="WRONG_PASSWORD")
    user.password_hash = hash_password(new)
    await session.commit()
