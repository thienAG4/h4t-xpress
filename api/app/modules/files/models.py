import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, str_enum


class FileStorage(StrEnum):
    LOCAL = "LOCAL"
    CLOUDINARY = "CLOUDINARY"


class File(UUIDPrimaryKey, CreatedAt, Base):
    """Uploaded image (proof of delivery, incident evidence)."""

    __tablename__ = "files"

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    storage: Mapped[FileStorage] = mapped_column(str_enum(FileStorage))
    key: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    mime: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    width: Mapped[int | None]
    height: Mapped[int | None]
