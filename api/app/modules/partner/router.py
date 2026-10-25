"""Inbound partner API (SPEC §5.4). Authenticated with the X-API-Key header."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.deps import DbSession
from app.modules.partner import service
from app.modules.partner.models import Partner
from app.modules.partner.schemas import CancelIn, PartnerOrderIn, PartnerOrderOut

router = APIRouter(prefix="/partner/v1", tags=["partner"])


async def current_partner(
    session: DbSession, x_api_key: Annotated[str | None, Header()] = None
) -> Partner:
    return await service.authenticate_partner(session, x_api_key)


ApiPartner = Annotated[Partner, Depends(current_partner)]


@router.post("/orders", response_model=PartnerOrderOut, status_code=201)
async def create_order(
    data: PartnerOrderIn, session: DbSession, partner: ApiPartner
) -> PartnerOrderOut:
    """
    Submit an order that has arrived at the last-mile hub.

    Inputs: {"waybill_code", "hub_code", "recipient_name", "recipient_phone", "delivery_address",
             "delivery_lat", "delivery_lng", "weight_kg", "length_cm", "width_cm", "height_cm",
             "cod_amount", "items": [{"name", "qty"}], "priority", "promised_at"}
    Errors: API_KEY_MISSING/INVALID (401), VALIDATION_ERROR, HUB_NOT_FOUND, PROMISE_IN_PAST,
            DUPLICATE_WAYBILL (409)
    """
    return await service.create_order(session, partner, data)


@router.get("/orders/{waybill_code}", response_model=PartnerOrderOut)
async def get_order(waybill_code: str, session: DbSession, partner: ApiPartner) -> PartnerOrderOut:
    """Current status, ETA, driver (while in progress) and the status timeline."""
    return await service.get_order(session, partner, waybill_code)


@router.post("/orders/{waybill_code}/cancel", response_model=PartnerOrderOut)
async def cancel_order(
    waybill_code: str, session: DbSession, partner: ApiPartner, data: CancelIn | None = None
) -> PartnerOrderOut:
    """Cancel before pickup. Errors: ORDER_NOT_FOUND, CANCEL_NOT_ALLOWED (409)."""
    reason = data.reason if data else "Cancelled by partner"
    return await service.cancel_order(session, partner, waybill_code, reason)
