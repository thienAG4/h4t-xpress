"""Live counters per driver and day, kept up to date by the delivery flow.

They feed the performance part of the dispatch score (BR5) and the reports (FR-R-04).
"""

import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.modules.reports.models import DailyDriverStat


async def bump_daily_stat(
    session: AsyncSession, driver_id: uuid.UUID, hub_id: uuid.UUID | None, **counters: int
) -> None:
    """Add to today's counters (assigned, delivered, failed, on_time, incidents)."""
    statement = insert(DailyDriverStat).values(
        driver_id=driver_id, date=local_today(), hub_id=hub_id, **counters
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DailyDriverStat.driver_id, DailyDriverStat.date],
        set_={
            name: getattr(DailyDriverStat, name) + getattr(statement.excluded, name)
            for name in counters
        },
    )
    await session.execute(statement)
