"""Upload and serve images. Content URLs use an unguessable UUID so <img> tags work
without an Authorization header (trade-off documented in SPEC §5.7)."""

import uuid

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.deps import AuthUser, DbSession
from app.modules.files import service

router = APIRouter(prefix="/files", tags=["files"])


class FileOut(BaseModel):
    id: uuid.UUID
    url: str
    mime: str
    size_bytes: int


@router.post("", response_model=FileOut, status_code=201)
async def upload_file(file: UploadFile, session: DbSession, user: AuthUser) -> FileOut:
    """
    Upload one image (multipart field `file`).

    Errors: FILE_TYPE (only JPEG/PNG/WebP), FILE_TOO_LARGE (> 5 MB), FILE_EMPTY
    Outputs: {"id", "url", "mime", "size_bytes"}
    """
    record = await service.save_upload(session, user.id, file)
    return FileOut(id=record.id, url=record.url, mime=record.mime, size_bytes=record.size_bytes)


@router.get("/{file_id}")
async def get_file(file_id: uuid.UUID, session: DbSession) -> FileResponse:
    record, path = await service.get_file(session, file_id)
    return FileResponse(
        path, media_type=record.mime, headers={"Cache-Control": "private, max-age=86400"}
    )
