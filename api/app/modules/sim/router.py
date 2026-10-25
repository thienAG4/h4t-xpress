"""ShopNow simulator endpoints (demo deployments only, public like a shop front)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from app.core.deps import CurrentUser, DbSession, require_demo_mode, require_permission
from app.core.pagination import Page, PageParams, page_params
from app.modules.sim import demo, service, tracking
from app.modules.sim.schemas import (
    ManualOrderIn,
    RandomOrdersIn,
    SimOrderOut,
    SimWebhookOut,
    TrackOut,
)

router = APIRouter(
    prefix="/sim/shopnow", tags=["simulator"], dependencies=[Depends(require_demo_mode)]
)
track_router = APIRouter(
    prefix="/sim/track", tags=["simulator"], dependencies=[Depends(require_demo_mode)]
)
Paging = Annotated[PageParams, Depends(page_params)]


@router.post("/orders/random", response_model=list[SimOrderOut], status_code=201)
async def create_random_orders(data: RandomOrdersIn, session: DbSession) -> list[SimOrderOut]:
    """
    Generate N plausible orders around a hub and send them through the partner API (S-01).

    Inputs: {"hub_code": "DIAN", "count": 5, "express_ratio": 0.15}
    """
    return await service.create_random_orders(session, data)


@router.post("/orders", response_model=SimOrderOut, status_code=201)
async def create_manual_order(data: ManualOrderIn, session: DbSession) -> SimOrderOut:
    """One order typed in the simulator form (S-01)."""
    return await service.create_manual_order(session, data)


@router.get("/orders", response_model=Page[SimOrderOut])
async def list_orders(session: DbSession, paging: Paging) -> Page[SimOrderOut]:
    """ShopNow's order list with the last status it knows (S-02)."""
    return await service.list_orders(session, paging)


@router.post("/orders/{waybill_code}/cancel", response_model=SimOrderOut)
async def cancel_order(waybill_code: str, session: DbSession) -> SimOrderOut:
    """Buyer cancels before pickup. Errors: ORDER_NOT_FOUND, CANCEL_NOT_ALLOWED."""
    return await service.cancel_order(session, waybill_code)


@router.post("/webhooks", response_model=SimWebhookOut, status_code=202)
async def receive_webhook(
    request: Request,
    session: DbSession,
    x_h4t_signature: Annotated[str | None, Header()] = None,
) -> SimWebhookOut:
    """Webhook receiver. The HMAC-SHA256 signature is checked and the result stored."""
    return await service.receive_webhook(session, await request.body(), x_h4t_signature)


@router.get("/webhooks", response_model=Page[SimWebhookOut])
async def list_webhooks(
    session: DbSession, paging: Paging, waybill_code: str | None = None
) -> Page[SimWebhookOut]:
    return await service.list_webhooks(session, paging, waybill_code)


@track_router.get("/{waybill_code}", response_model=TrackOut)
async def track_order(waybill_code: str, session: DbSession) -> TrackOut:
    """
    Customer tracking page (S-03), public: timeline, ETA, delay reason and apology.

    Errors: ORDER_NOT_FOUND
    """
    return await tracking.track(session, waybill_code)


# =============================== Demo control panel (S-04) ===============================

demo_router = APIRouter(
    prefix="/sim/demo", tags=["simulator"], dependencies=[Depends(require_demo_mode)]
)
Resetter = Annotated[CurrentUser, Depends(require_permission("settings.manage"))]


class GpsSwitchIn(BaseModel):
    enabled: bool


class TrafficJamIn(BaseModel):
    driver_id: uuid.UUID | None = None


class ResetOut(BaseModel):
    rows: int


@demo_router.get("", response_model=demo.DemoStatusOut)
async def get_demo_status(session: DbSession) -> demo.DemoStatusOut:
    """GPS simulator state and the drivers it is moving."""
    return await demo.status(session)


@demo_router.put("/gps", response_model=demo.DemoStatusOut)
async def switch_gps(data: GpsSwitchIn, session: DbSession) -> demo.DemoStatusOut:
    """Inputs: {"enabled": true}. Simulated drivers move and deliver while it is on."""
    return await demo.set_gps(session, data.enabled)


@demo_router.post("/traffic-jam", response_model=demo.DemoStatusOut)
async def start_traffic_jam(data: TrafficJamIn, session: DbSession) -> demo.DemoStatusOut:
    """
    Stop one simulated driver; after `anomaly.idle_minutes` the system raises DRIVER_IDLE.

    Inputs: {"driver_id": null | uuid}. Errors: NO_SIMULATED_DRIVER
    """
    return await demo.traffic_jam(session, data.driver_id)


@demo_router.post("/reset", response_model=ResetOut)
async def reset_demo(_: Resetter) -> ResetOut:
    """Reload the demo data set. Everyone is signed out. System admin only."""
    counts = await demo.reset_demo_data()
    return ResetOut(rows=sum((counts or {}).values()))
