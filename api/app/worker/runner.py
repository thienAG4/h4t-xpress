"""Background loop running inside the API process (SPEC §5.6).

Due jobs are claimed with SELECT ... FOR UPDATE SKIP LOCKED, so a second API instance
would share the work instead of doubling it. Each job runs in its own session; one that
raises is retried with a growing delay. Every few seconds the loop also runs the dispatch
sweeper and sends due partner webhooks. After the free host wakes up, overdue jobs run first.
"""

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.delivery.service import release_reschedule
from app.modules.dispatch.service import expire_offer, run_dispatch, sweep
from app.modules.partner.webhooks import deliver_pending_webhooks
from app.worker.jobs import DISPATCH_RUN, OFFER_TIMEOUT, RESCHEDULE_RELEASE
from app.worker.models import Job, JobStatus

logger = logging.getLogger(__name__)

MAX_JOB_ATTEMPTS = 5
RETRY_STEP = timedelta(seconds=10)
STALE_AFTER = timedelta(minutes=5)  # a RUNNING job this old was left by a crashed process

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[object]]

HANDLERS: dict[str, Handler] = {
    DISPATCH_RUN: lambda session, p: run_dispatch(session, uuid.UUID(p["order_id"])),
    OFFER_TIMEOUT: lambda session, p: expire_offer(session, uuid.UUID(p["offer_id"])),
    RESCHEDULE_RELEASE: lambda session, p: release_reschedule(session, uuid.UUID(p["order_id"])),
}


@dataclass(frozen=True)
class ClaimedJob:
    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    attempts: int


# =============================== Jobs ===============================


async def _claim(limit: int) -> list[ClaimedJob]:
    now = utc_now()
    async with SessionLocal() as session:
        jobs = list(
            await session.scalars(
                select(Job)
                .where(Job.status == JobStatus.PENDING, Job.run_at <= now)
                .order_by(Job.run_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for job in jobs:
            job.status = JobStatus.RUNNING
            job.locked_at = now
            job.attempts += 1
        await session.commit()
        return [ClaimedJob(job.id, job.type, dict(job.payload), job.attempts) for job in jobs]


async def _finish(job: ClaimedJob, error: str | None) -> None:
    async with SessionLocal() as session:
        row = await session.get(Job, job.id)
        if row is None:
            return
        row.locked_at = None
        if error is None:
            row.status = JobStatus.DONE
            row.finished_at = utc_now()
            row.last_error = None
        elif job.attempts >= MAX_JOB_ATTEMPTS:
            row.status = JobStatus.FAILED
            row.finished_at = utc_now()
            row.last_error = error
        else:
            row.status = JobStatus.PENDING
            row.run_at = utc_now() + RETRY_STEP * job.attempts
            row.last_error = error
        await session.commit()


async def run_job(job: ClaimedJob) -> None:
    handler = HANDLERS.get(job.type)
    error: str | None = None
    if handler is None:
        error = f"Unknown job type {job.type}"
    else:
        async with SessionLocal() as session:
            try:
                result = await handler(session, job.payload)
                logger.debug("[run_job] %s %s -> %s", job.type, job.payload, result)
            except Exception as exc:
                await session.rollback()
                error = f"{type(exc).__name__}: {exc}"[:500]
                logger.exception("[run_job] %s failed (attempt %d)", job.type, job.attempts)
    await _finish(job, error)


async def run_due_jobs(limit: int = 20) -> int:
    """Run every job whose time has come. Returns how many ran."""
    jobs = await _claim(limit)
    for job in jobs:
        await run_job(job)
    return len(jobs)


async def requeue_stale_jobs() -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            update(Job)
            .where(Job.status == JobStatus.RUNNING, Job.locked_at < utc_now() - STALE_AFTER)
            .values(status=JobStatus.PENDING, locked_at=None)
        )
        await session.commit()
        return result.rowcount or 0  # type: ignore[attr-defined]


# =============================== Loop ===============================


class Worker:
    """Started and stopped by the FastAPI lifespan when WORKER_ENABLED is true."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._http: httpx.AsyncClient | None = None

    def start(self) -> None:
        if self._task is None:
            self._http = httpx.AsyncClient(timeout=5)
            self._task = asyncio.create_task(self._loop(), name="h4t-worker")
            logger.info("[worker] started")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        logger.info("[worker] stopped")

    async def _periodic(self) -> None:
        await requeue_stale_jobs()
        async with SessionLocal() as session:
            counts = await sweep(session)
        if counts["expired"] or counts["queued"]:
            logger.info("[worker] sweep %s", counts)
        await deliver_pending_webhooks(client=self._http)

    async def _loop(self) -> None:
        settings = get_settings()
        loop = asyncio.get_running_loop()
        next_periodic = 0.0
        while True:
            try:
                if loop.time() >= next_periodic:
                    await self._periodic()
                    next_periodic = loop.time() + settings.worker_sweep_seconds
                ran = await run_due_jobs()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[worker] loop error")
                ran = 0
            if not ran:
                await asyncio.sleep(settings.worker_poll_seconds)


worker = Worker()
