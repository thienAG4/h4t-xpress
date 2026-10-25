"""Hub manager endpoints: dashboard, orders, drivers and manual dispatch actions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_hub, require_permission
from app.core.errors import NotFound
from app.core.pagination import Page, PageParams, page_params
from app.modules.delivery import service as delivery_service
from app.modules.delivery.schemas import RouteOut
from app.modules.incidents.schemas import CandidateOut
from app.modules.orders import hub_service as service
from app.modules.orders.hub_schemas import (
    DashboardOut,
    HoldIn,
    HubDriverRow,
    HubOrderDetail,
    HubOrderRow,
    ReassignIn,
)
from app.modules.orders.models import OrderStatus
from app.modules.users.models import User

router = APIRouter(prefix="/hub", tags=["hub"])
DashboardViewer = Annotated[CurrentUser, Depends(require_permission("hub.dashboard.view"))]
OrderViewer = Annotated[CurrentUser, Depends(require_permission("order.view_hub"))]
OrderManager = Annotated[CurrentUser, Depends(require_permission("order.reassign"))]
DriverViewer = Annotated[CurrentUser, Depends(require_permission("driver.view_hub"))]
Paging = Annotated[PageParams, Depends(page_params)]


# =============================== Monitoring ===============================


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(session: DbSession, manager: DashboardViewer) -> DashboardOut:
    """
    Hub overview (H-01).

    Outputs: {"date", "total", "by_status", "at_risk", "delivered_today",
              "on_time_rate_today", "open_incidents", "high_priority_incidents",
              "drivers_online", "drivers_on_shift"}
    """
    return await service.dashboard(session, require_hub(manager))


@router.get("/orders", response_model=Page[HubOrderRow])
async def list_orders(
    session: DbSession,
    manager: OrderViewer,
    paging: Paging,
    status: Annotated[list[OrderStatus] | None, Query()] = None,
    at_risk: bool = False,
    q: str | None = None,
    today_only: bool = True,
) -> Page[HubOrderRow]:
    """
    Orders of the hub, SLA risks first (UC-02).

    Inputs (query): status (repeatable), at_risk, q (waybill, name or phone), today_only
    """
    return await service.list_orders(
        session,
        require_hub(manager),
        paging,
        statuses=status,
        risk_only=at_risk,
        q=q,
        today_only=today_only,
    )


@router.get("/orders/{order_id}", response_model=HubOrderDetail)
async def get_order(
    order_id: uuid.UUID, session: DbSession, manager: OrderViewer
) -> HubOrderDetail:
    """Order page with driver position, timeline and delivery attempts (H-03)."""
    return await service.order_detail(session, require_hub(manager), order_id)


@router.get("/drivers", response_model=list[HubDriverRow])
async def list_drivers(session: DbSession, manager: DriverViewer) -> list[HubDriverRow]:
    """Drivers of the hub with live position and load, online first."""
    return await service.list_drivers(session, require_hub(manager))


@router.get("/drivers/{driver_id}/route", response_model=RouteOut)
async def get_driver_route(
    driver_id: uuid.UUID, session: DbSession, manager: DriverViewer
) -> RouteOut:
    """The same route the driver sees (D-07), for the tracking map."""
    driver = await session.get(User, driver_id)
    if driver is None or driver.hub_id != require_hub(manager):
        raise NotFound("Driver not found", code="DRIVER_NOT_FOUND")
    return await delivery_service.route_view(session, driver_id)


# =============================== Actions ===============================


@router.get("/orders/{order_id}/candidates", response_model=list[CandidateOut])
async def list_candidates(
    order_id: uuid.UUID, session: DbSession, manager: OrderManager
) -> list[CandidateOut]:
    """Eligible drivers for a manual offer (H-07), best score first."""
    return await service.order_candidates(session, require_hub(manager), order_id)


@router.post("/orders/{order_id}/reassign", response_model=HubOrderDetail)
async def reassign_order(
    order_id: uuid.UUID, data: ReassignIn, session: DbSession, manager: OrderManager
) -> HubOrderDetail:
    """
    Offer the order to a chosen driver; the driver still has to accept (FR-H-01).

    Inputs: {"driver_id"}
    Errors: INVALID_TRANSITION (parcel already picked up), DRIVER_NOT_AVAILABLE, DRIVER_BUSY
    """
    return await service.reassign(session, manager, order_id, data.driver_id)


@router.post("/orders/{order_id}/hold", response_model=HubOrderDetail)
async def hold_order(
    order_id: uuid.UUID, data: HoldIn, session: DbSession, manager: OrderManager
) -> HubOrderDetail:
    """Keep a waiting order at the hub. Errors: INVALID_TRANSITION."""
    return await service.hold(session, manager, order_id, data.reason)


@router.post("/orders/{order_id}/release-hold", response_model=HubOrderDetail)
async def release_hold(
    order_id: uuid.UUID, session: DbSession, manager: OrderManager
) -> HubOrderDetail:
    """ON_HOLD -> AWAITING_ASSIGNMENT; dispatch starts a new cycle."""
    return await service.release_hold(session, manager, order_id)


@router.post("/orders/{order_id}/returned", response_model=HubOrderDetail)
async def confirm_returned(
    order_id: uuid.UUID, session: DbSession, manager: OrderManager
) -> HubOrderDetail:
    """The returned parcel is back at the hub (RETURNING -> RETURNED_TO_HUB)."""
    return await service.confirm_returned(session, manager, order_id)
