"""User accounts: admin management (A-01, A-02) and the signed-in user's profile."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.deps import AuthUser, CurrentUser, DbSession, client_ip, require_permission
from app.core.pagination import Page, PageParams, page_params
from app.modules.users import service
from app.modules.users.models import UserStatus
from app.modules.users.schemas import (
    ChangePasswordIn,
    MeOut,
    MeUpdateIn,
    TemporaryPasswordOut,
    UserCreatedOut,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)

admin_router = APIRouter(prefix="/admin/users", tags=["admin: users"])
me_router = APIRouter(prefix="/me", tags=["me"])
UserManager = Annotated[CurrentUser, Depends(require_permission("user.manage"))]
Paging = Annotated[PageParams, Depends(page_params)]


# =============================== Admin ===============================


@admin_router.get("", response_model=Page[UserOut])
async def list_users(
    session: DbSession,
    _: UserManager,
    paging: Paging,
    q: str | None = None,
    role: str | None = None,
    hub_id: uuid.UUID | None = None,
    status: UserStatus | None = None,
) -> Page[UserOut]:
    """
    Search accounts.

    Inputs (query): q (name, e-mail or phone), role, hub_id, status, page, page_size
    Outputs: {"items": [UserOut], "total", "page", "page_size"}
    """
    return await service.list_users(session, paging, q=q, role=role, hub_id=hub_id, status=status)


@admin_router.post("", response_model=UserCreatedOut, status_code=201)
async def create_user(
    data: UserCreateIn, request: Request, session: DbSession, user: UserManager
) -> UserCreatedOut:
    """
    Create an account of any role.

    Errors: EMAIL_TAKEN, PHONE_TAKEN, HUB_REQUIRED, DRIVER_FIELDS_REQUIRED
    Outputs: {"user": UserOut, "temporary_password": "..." | null}
    """
    created, temporary = await service.create_user(
        session, data, actor_id=user.id, ip=client_ip(request)
    )
    return UserCreatedOut(user=created, temporary_password=temporary)


@admin_router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: uuid.UUID, session: DbSession, _: UserManager) -> UserOut:
    return await service.get_user_out(session, user_id)


@admin_router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, data: UserUpdateIn, request: Request, session: DbSession, user: UserManager
) -> UserOut:
    """Partial update. Demo accounts keep their e-mail and role (DEMO_ACCOUNT_PROTECTED)."""
    return await service.update_user(
        session, user_id, data, actor_id=user.id, ip=client_ip(request)
    )


@admin_router.post("/{user_id}/lock", response_model=UserOut)
async def lock_user(
    user_id: uuid.UUID, request: Request, session: DbSession, user: UserManager
) -> UserOut:
    """Lock an account and sign it out everywhere."""
    return await service.set_locked(
        session, user_id, locked=True, actor_id=user.id, ip=client_ip(request)
    )


@admin_router.post("/{user_id}/unlock", response_model=UserOut)
async def unlock_user(
    user_id: uuid.UUID, request: Request, session: DbSession, user: UserManager
) -> UserOut:
    return await service.set_locked(
        session, user_id, locked=False, actor_id=user.id, ip=client_ip(request)
    )


@admin_router.post("/{user_id}/reset-password", response_model=TemporaryPasswordOut)
async def reset_password(
    user_id: uuid.UUID, request: Request, session: DbSession, user: UserManager
) -> TemporaryPasswordOut:
    """Generate a temporary password, returned once. All sessions are revoked."""
    temporary = await service.reset_password(
        session, user_id, actor_id=user.id, ip=client_ip(request)
    )
    return TemporaryPasswordOut(temporary_password=temporary)


@admin_router.post("/{user_id}/revoke-sessions", status_code=204)
async def revoke_sessions(
    user_id: uuid.UUID, request: Request, session: DbSession, user: UserManager
) -> Response:
    await service.revoke_user_sessions(session, user_id, actor_id=user.id, ip=client_ip(request))
    return Response(status_code=204)


# =============================== Me ===============================


@me_router.get("", response_model=MeOut)
async def get_me(session: DbSession, user: AuthUser) -> MeOut:
    """Signed-in user with role, hub, driver profile and permission codes."""
    return await service.get_me(session, user.id)


@me_router.patch("", response_model=MeOut)
async def update_me(data: MeUpdateIn, session: DbSession, user: AuthUser) -> MeOut:
    return await service.update_me(session, user.id, data)


@me_router.post("/password", status_code=204)
async def change_password(data: ChangePasswordIn, session: DbSession, user: AuthUser) -> Response:
    """Errors: WRONG_PASSWORD, DEMO_ACCOUNT_PROTECTED."""
    await service.change_password(
        session, user.id, current=data.current_password, new=data.new_password
    )
    return Response(status_code=204)
