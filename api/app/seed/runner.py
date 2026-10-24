from datetime import UTC, datetime

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.db import Base, engine
from app.models import (
    Area,
    AreaAdjacency,
    Assignment,
    DailyDriverStat,
    DeliveryAttempt,
    DispatchOffer,
    DriverProfile,
    Hub,
    Incident,
    IncidentOrder,
    IncidentResolution,
    Order,
    OrderEvent,
    Partner,
    Permission,
    Role,
    RolePermission,
    Shift,
    ShiftRegistration,
    SimShopnowOrder,
    SystemSetting,
    User,
)
from app.seed.generator import DemoDataBuilder

# Parents before children (foreign keys).
INSERT_ORDER: list[type[Base]] = [
    Role,
    Permission,
    RolePermission,
    Area,
    AreaAdjacency,
    Hub,
    Shift,
    User,
    DriverProfile,
    Partner,
    SystemSetting,
    ShiftRegistration,
    Order,
    Incident,
    IncidentOrder,
    IncidentResolution,
    OrderEvent,
    Assignment,
    DispatchOffer,
    DeliveryAttempt,
    DailyDriverStat,
    SimShopnowOrder,
]
BATCH_SIZE = 1000


async def truncate_all(conn: AsyncConnection) -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def has_data(conn: AsyncConnection) -> bool:
    result = await conn.execute(select(Role.id).limit(1))
    return result.first() is not None


async def run_seed(
    *,
    reset: bool = False,
    if_empty: bool = False,
    history_days: int | None = None,
    random_seed: int | None = None,
    now: datetime | None = None,
) -> dict[str, int] | None:
    """Insert demo data in one transaction. Returns row counts, or None when skipped."""
    settings = get_settings()
    async with engine.begin() as conn:
        if if_empty and await has_data(conn):
            return None
        if reset:
            await truncate_all(conn)
        elif await has_data(conn):
            raise RuntimeError("Database already has data. Use --reset or --if-empty.")

        builder = DemoDataBuilder(
            now=now or datetime.now(UTC),
            history_days=settings.seed_history_days if history_days is None else history_days,
            random_seed=settings.seed_random_seed if random_seed is None else random_seed,
            demo_mode=settings.demo_mode,
            demo_password=settings.demo_password,
            shopnow_api_key=settings.shopnow_api_key,
            shopnow_webhook_secret=settings.shopnow_webhook_secret,
            shopnow_webhook_url=settings.shopnow_webhook_url,
        )
        rows = builder.build()

        missing = set(rows) - set(INSERT_ORDER)
        if missing:
            raise RuntimeError(
                f"Seed rows without insert order: {sorted(m.__name__ for m in missing)}"
            )

        counts: dict[str, int] = {}
        for model in INSERT_ORDER:
            data = rows.get(model, [])
            for start in range(0, len(data), BATCH_SIZE):
                await conn.execute(insert(model), data[start : start + BATCH_SIZE])
            counts[model.__tablename__] = len(data)
    return counts
