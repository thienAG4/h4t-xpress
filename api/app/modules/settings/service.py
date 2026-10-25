"""Read tunable business parameters from system_settings, with code defaults."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import SystemSetting


async def get_setting(session: AsyncSession, key: str, default: Any) -> Any:
    value = await session.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    return default if value is None else value
