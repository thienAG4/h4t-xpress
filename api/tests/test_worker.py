"""Background worker (SPEC §5.6): due jobs run once, failures retry then give up,
jobs left RUNNING by a crashed process are picked up again."""

import uuid

from httpx import AsyncClient

from app.core.db import SessionLocal
from app.modules.dispatch.service import sweep
from app.worker.jobs import DISPATCH_RUN, enqueue
from app.worker.runner import MAX_JOB_ATTEMPTS, requeue_stale_jobs, run_due_jobs
from tests.helpers import DRIVER, create_order, pending_offer, reset_dispatch, scalar, sql


async def _queue(job_type: str, payload: dict[str, str]) -> uuid.UUID:
    async with SessionLocal() as session:
        job = enqueue(session, job_type, payload)
        await session.commit()
        return job.id


async def _job(job_id: uuid.UUID) -> tuple[str, int, str | None]:
    rows = await sql("select status, attempts, last_error from jobs where id = :id", id=job_id)
    return rows[0][0], rows[0][1], rows[0][2]


async def test_due_dispatch_job_makes_an_offer(client: AsyncClient) -> None:
    await reset_dispatch({DRIVER: 0.3})
    order_id = await create_order(client, "WK000001")
    job_id = await _queue(DISPATCH_RUN, {"order_id": str(order_id)})

    assert await run_due_jobs() >= 1
    assert (await _job(job_id))[0] == "DONE"
    assert await pending_offer(order_id) is not None
    assert await run_due_jobs() == 0  # the offer timeout job waits for expires_at


async def test_failing_job_is_retried_then_marked_failed() -> None:
    await reset_dispatch({})
    job_id = await _queue(DISPATCH_RUN, {"order_id": str(uuid.uuid4())})

    await run_due_jobs()
    status, attempts, error = await _job(job_id)
    assert (status, attempts) == ("PENDING", 1) and error and "NotFound" in error
    assert await scalar("select run_at > now() from jobs where id = :id", id=job_id)

    await sql(
        "update jobs set attempts = :n, run_at = now() where id = :id",
        n=MAX_JOB_ATTEMPTS - 1,
        id=job_id,
    )
    await run_due_jobs()
    assert (await _job(job_id))[0] == "FAILED"


async def test_unknown_job_type_fails_cleanly() -> None:
    await reset_dispatch({})
    job_id = await _queue("does.not.exist", {})
    await sql("update jobs set attempts = :n where id = :id", n=MAX_JOB_ATTEMPTS - 1, id=job_id)
    await run_due_jobs()
    status, _, error = await _job(job_id)
    assert status == "FAILED" and error == "Unknown job type does.not.exist"


async def test_stale_running_job_is_requeued() -> None:
    await reset_dispatch({})
    job_id = await _queue(DISPATCH_RUN, {"order_id": str(uuid.uuid4())})
    await sql(
        "update jobs set status = 'RUNNING', locked_at = now() - interval '1 hour' where id = :id",
        id=job_id,
    )
    assert await requeue_stale_jobs() == 1
    assert (await _job(job_id))[0] == "PENDING"


async def test_sweeper_queues_waiting_orders_once(client: AsyncClient) -> None:
    await reset_dispatch({})
    order_id = await create_order(client, "WK000002")
    async with SessionLocal() as session:
        first = await sweep(session, limit=500)
    async with SessionLocal() as session:
        second = await sweep(session, limit=500)
    assert first["queued"] >= 1 and second["queued"] == 0
    queued = await scalar(
        "select count(*) from jobs where type = :t and status = 'PENDING' "
        "and payload->>'order_id' = :o",
        t=DISPATCH_RUN,
        o=str(order_id),
    )
    assert queued == 1
