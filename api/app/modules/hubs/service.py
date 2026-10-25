"""Hub reference data used by forms (driver sign-up, user management)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hubs.models import Area, Hub, HubStatus
from app.modules.hubs.schemas import HubOut


async def list_hubs(session: AsyncSession) -> list[HubOut]:
    rows = await session.execute(
        select(Hub, Area.name)
        .join(Area, Area.id == Hub.area_id)
        .where(Hub.status == HubStatus.ACTIVE)
        .order_by(Hub.name)
    )
    return [_to_out(hub, area_name) for hub, area_name in rows]


async def get_hub_out(session: AsyncSession, hub_id: uuid.UUID) -> HubOut | None:
    row = (
        await session.execute(
            select(Hub, Area.name).join(Area, Area.id == Hub.area_id).where(Hub.id == hub_id)
        )
    ).first()
    return _to_out(*row) if row else None


def _to_out(hub: Hub, area_name: str) -> HubOut:
    return HubOut(
        id=hub.id,
        code=hub.code,
        name=hub.name,
        address=hub.address,
        area_name=area_name,
        lat=hub.lat,
        lng=hub.lng,
    )
