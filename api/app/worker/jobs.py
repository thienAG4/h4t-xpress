"""Job types and the helper that queues a job in the caller's transaction."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.worker.models import Job, JobStatus

DISPATCH_RUN = "dispatch.run"  # look for the next driver of an order (BR6)
OFFER_TIMEOUT = "dispatch.offer_timeout"  # expire an unanswered offer (BR7)
RESCHEDULE_RELEASE = "order.reschedule_release"  # RESCHEDULED -> AWAITING_ASSIGNMENT


def enqueue(
    session: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    *,
    run_at: datetime | None = None,
) -> Job:
    """Add a job to the current transaction; it runs once the caller commits."""
    job = Job(type=job_type, payload=payload, run_at=run_at or utc_now())
    session.add(job)
    return job


async def has_pending(session: AsyncSession, job_type: str, key: str, value: str) -> bool:
    """True when a PENDING/RUNNING job of this type already targets payload[key] == value."""
    found = await session.scalar(
        select(Job.id)
        .where(
            Job.type == job_type,
            Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
            Job.payload[key].astext == value,
        )
        .limit(1)
    )
    return found is not None
