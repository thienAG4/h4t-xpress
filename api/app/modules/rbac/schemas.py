import uuid

from pydantic import BaseModel


class PermissionOut(BaseModel):
    code: str
    group: str
    description: str


class RoleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    user_count: int


class UpdateRolePermissionsIn(BaseModel):
    permissions: list[str]
    # Revoke refresh tokens so users of this role get the new permissions right away.
    force_relogin: bool = False
