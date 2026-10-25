"""FastAPI dependencies shared by every module: DB session, current user, permissions."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import Forbidden, NotFound, Unauthorized
from app.core.security import decode_access_token

DbSession = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    role: str
    hub_id: uuid.UUID | None
    permissions: frozenset[str]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise Unauthorized("Missing access token")
    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise Unauthorized("Access token is invalid or expired", code="TOKEN_EXPIRED")
    return CurrentUser(
        id=claims.user_id, role=claims.role, hub_id=claims.hub_id, permissions=claims.permissions
    )


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_permission(*codes: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Dependency factory: the user must hold every listed permission (SPEC §2.2)."""

    async def checker(user: AuthUser) -> CurrentUser:
        missing = [code for code in codes if not user.can(code)]
        if missing:
            raise Forbidden("You do not have permission for this action", details=missing)
        return user

    return checker


async def require_demo_mode() -> None:
    """Simulator routes exist only in demo deployments."""
    if not get_settings().demo_mode:
        raise NotFound("Not found")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
