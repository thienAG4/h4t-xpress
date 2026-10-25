"""ShopNow simulator endpoints (demo deployments only, public like a shop front)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.core.deps import DbSession, require_demo_mode
from app.core.pagination import Page, PageParams, page_params
from app.modules.sim import service
from app.modules.sim.schemas import ManualOrderIn, RandomOrdersIn, SimOrderOut, SimWebhookOut

router = APIRouter(
    prefix="/sim/shopnow", tags=["simulator"], dependencies=[Depends(require_demo_mode)]
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
