"""Public hub list (needed by the sign-up form before the driver has an account)."""

from fastapi import APIRouter

from app.core.deps import DbSession
from app.modules.hubs import service
from app.modules.hubs.schemas import HubOut

router = APIRouter(prefix="/hubs", tags=["hubs"])


@router.get("", response_model=list[HubOut])
async def list_hubs(session: DbSession) -> list[HubOut]:
    """Active hubs: [{"id", "code", "name", "address", "area_name", "lat", "lng"}]."""
    return await service.list_hubs(session)
