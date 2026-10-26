"""Driver order flow endpoints (D-06..D-14): presence, offers, route and order actions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.deps import CurrentUser, DbSession, require_permission
from app.modules.delivery import service
from app.modules.delivery.schemas import (
    DeclineIn,
    DeliverIn,
    DriverOrderDetailOut,
    DriverOrderOut,
    EtaIn,
    FailIn,
    HeartbeatIn,
    OfferOut,
    ReleaseIn,
    RouteOut,
    ScanIn,
    StartOut,
)
from app.modules.dispatch import service as dispatch_service
from app.modules.tracking import service as tracking_service

router = APIRouter(prefix="/driver", tags=["driver: delivery"])
OnlineDriver = Annotated[CurrentUser, Depends(require_permission("availability.toggle"))]
OfferDriver = Annotated[CurrentUser, Depends(require_permission("offer.respond"))]
OrderDriver = Annotated[CurrentUser, Depends(require_permission("order.update_own"))]
EtaDriver = Annotated[CurrentUser, Depends(require_permission("eta.update_own"))]


# =============================== Presence ===============================


@router.post("/heartbeat", status_code=204)
async def heartbeat(data: HeartbeatIn, session: DbSession, driver: OnlineDriver) -> Response:
    """
    Sent every 15 seconds while the app is open (BR4 freshness, BR10 position).

    Inputs: {"lat", "lng", "accuracy_m"}, all optional when GPS is refused.
    """
    await tracking_service.heartbeat(
        session, driver.id, lat=data.lat, lng=data.lng, accuracy_m=data.accuracy_m
    )
    return Response(status_code=204)


# =============================== Offers (D-06) ===============================


@router.get("/offers/current", response_model=OfferOut | None)
async def get_current_offer(session: DbSession, driver: OfferDriver) -> OfferOut | None:
    """The open offer with its countdown, or null."""
    return await service.offer_view(session, driver.id)


@router.post("/offers/{offer_id}/accept", response_model=RouteOut)
async def accept_offer(offer_id: uuid.UUID, session: DbSession, driver: OfferDriver) -> RouteOut:
    """
    Take the order(s) of the offer (BR8). Returns the updated route.

    Errors: OFFER_NOT_FOUND, OFFER_CLOSED, OFFER_EXPIRED, ORDER_NOT_AVAILABLE
    """
    await dispatch_service.accept_offer(session, driver.id, offer_id)
    return await service.route_view(session, driver.id)


@router.post("/offers/{offer_id}/decline", status_code=204)
async def decline_offer(
    offer_id: uuid.UUID, data: DeclineIn, session: DbSession, driver: OfferDriver
) -> Response:
    """Inputs: {"reason"} (optional). Errors: OFFER_NOT_FOUND, OFFER_CLOSED."""
    await dispatch_service.decline_offer(session, driver.id, offer_id, data.reason)
    return Response(status_code=204)


# =============================== Route (D-07, D-08) ===============================


@router.get("/route", response_model=RouteOut)
async def get_route(session: DbSession, driver: OrderDriver) -> RouteOut:
    """
    Today's work: parcels to collect first, then stops in delivery order.

    Outputs: {"hub_name", "hub_lat", "hub_lng", "driver_lat", "driver_lng",
              "to_pick_up": [order], "ready_to_start", "stops": [stop]}
    """
    return await service.route_view(session, driver.id)


@router.post("/route/start", response_model=StartOut)
async def start_route(session: DbSession, driver: OrderDriver) -> StartOut:
    """Leave with every scanned parcel (BR9). Errors: NOTHING_TO_START."""
    return StartOut(started=await service.start_delivery(session, driver.id))


@router.get("/orders/{order_id}", response_model=DriverOrderDetailOut)
async def get_order(
    order_id: uuid.UUID, session: DbSession, driver: OrderDriver
) -> DriverOrderDetailOut:
    return await service.order_detail(session, driver.id, order_id)


# =============================== Order actions (D-09..D-13) ===============================


@router.post("/orders/{order_id}/scan", response_model=DriverOrderOut)
async def scan_order(
    order_id: uuid.UUID, data: ScanIn, session: DbSession, driver: OrderDriver
) -> DriverOrderOut:
    """
    Confirm the parcel in hand by its waybill code (manual entry on the web).

    Inputs: {"waybill_code", "lat", "lng"}. Errors: WAYBILL_MISMATCH, INVALID_TRANSITION
    """
    return await service.scan(
        session, driver.id, order_id, data.waybill_code, lat=data.lat, lng=data.lng
    )


@router.post("/orders/{order_id}/deliver", response_model=DriverOrderOut)
async def deliver_order(
    order_id: uuid.UUID, data: DeliverIn, session: DbSession, driver: OrderDriver
) -> DriverOrderOut:
    """
    Successful hand-over with proof photos (BR16).

    Inputs: {"photo_file_ids": [...], "note", "lat", "lng"}. Errors: EVIDENCE_REQUIRED
    """
    return await service.deliver(session, driver.id, order_id, data)


@router.post("/orders/{order_id}/fail", response_model=DriverOrderOut)
async def fail_order(
    order_id: uuid.UUID, data: FailIn, session: DbSession, driver: OrderDriver
) -> DriverOrderOut:
    """
    Failed attempt with a reason (BR17); reschedule or return to the hub.

    Inputs: {"reason", "note", "proposed_date"}. Errors: RESCHEDULE_DATE_INVALID
    """
    return await service.fail(session, driver.id, order_id, data)


@router.put("/orders/{order_id}/eta", response_model=DriverOrderOut)
async def update_eta(
    order_id: uuid.UUID, data: EtaIn, session: DbSession, driver: EtaDriver
) -> DriverOrderOut:
    """Manual ETA with a reason (D-12). Errors: ETA_IN_PAST."""
    return await service.update_eta(session, driver.id, order_id, data)


@router.post("/orders/{order_id}/release", status_code=204)
async def release_order(
    order_id: uuid.UUID, data: ReleaseIn, session: DbSession, driver: OrderDriver
) -> Response:
    """Give an order back before pickup (EX4). Errors: INVALID_TRANSITION."""
    await service.release(session, driver.id, order_id, data.reason)
    return Response(status_code=204)
