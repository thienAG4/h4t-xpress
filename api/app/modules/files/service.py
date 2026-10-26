"""Image uploads for proof of delivery and incident evidence (BR16, FR-D-06).

Files are stored on local disk (Docker volume `uploads`). The storage kind is recorded
per file so a Cloudinary implementation can be added without migrating old rows.
"""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.config import get_settings
from app.core.errors import NotFound, ValidationFailed
from app.modules.files.models import File, FileStorage

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _storage_root() -> Path:
    return Path(get_settings().upload_dir)


def file_url(file_id: uuid.UUID) -> str:
    return f"/api/v1/files/{file_id}"


async def save_upload(session: AsyncSession, owner_id: uuid.UUID, upload: UploadFile) -> File:
    """Validate type and size, write to disk and store the File row (committed here)."""
    mime = (upload.content_type or "").lower()
    if mime not in EXTENSIONS:
        raise ValidationFailed("Only JPEG, PNG or WebP images are accepted", code="FILE_TYPE")
    content = await upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValidationFailed("Images must be 5 MB or smaller", code="FILE_TOO_LARGE")
    if not content:
        raise ValidationFailed("The file is empty", code="FILE_EMPTY")

    file_id = uuid.uuid4()
    now = utc_now()
    key = f"{now:%Y/%m}/{file_id}.{EXTENSIONS[mime]}"
    target = _storage_root() / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    record = File(
        id=file_id,
        owner_user_id=owner_id,
        storage=FileStorage.LOCAL,
        key=key,
        url=file_url(file_id),
        mime=mime,
        size_bytes=len(content),
    )
    session.add(record)
    await session.commit()
    logger.info("[save_upload] file=%s owner=%s bytes=%d", file_id, owner_id, len(content))
    return record


async def get_file(session: AsyncSession, file_id: uuid.UUID) -> tuple[File, Path]:
    record = await session.get(File, file_id)
    if record is None:
        raise NotFound("File not found", code="FILE_NOT_FOUND")
    path = _storage_root() / record.key
    if not path.exists():
        raise NotFound("File content is missing", code="FILE_NOT_FOUND")
    return record, path


async def require_own_files(
    session: AsyncSession, owner_id: uuid.UUID, file_ids: list[uuid.UUID]
) -> list[File]:
    """Evidence must be photos uploaded by the same user (no reuse of other people's files)."""
    if not file_ids:
        return []
    rows = list(
        await session.scalars(
            select(File).where(File.id.in_(file_ids), File.owner_user_id == owner_id)
        )
    )
    if len(rows) != len(set(file_ids)):
        raise ValidationFailed("Unknown photo", code="FILE_NOT_FOUND")
    return rows
