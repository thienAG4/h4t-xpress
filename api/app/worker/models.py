from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, str_enum


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class Job(UUIDPrimaryKey, CreatedAt, Base):
    """Background job queue, polled with SELECT ... FOR UPDATE SKIP LOCKED (SPEC §5.6)."""

    __tablename__ = "jobs"

    type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(
        default=dict, server_default=text("'{}'::jsonb")
    )
    run_at: Mapped[datetime]
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus), default=JobStatus.PENDING, server_default=JobStatus.PENDING.value
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_jobs_status_run_at", "status", "run_at"),)
