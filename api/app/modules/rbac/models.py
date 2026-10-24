import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey


class RoleCode(StrEnum):
    DRIVER = "DRIVER"
    HUB_MANAGER = "HUB_MANAGER"
    EXECUTIVE = "EXECUTIVE"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class Role(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "roles"

    # Plain string (not an enum) so new roles can be added without a migration.
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(default=True, server_default=true())


class Permission(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    group: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
