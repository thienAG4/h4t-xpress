"""Route planning endpoints for hub managers (H-02, UC-03)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.clock import local_today
from app.core.deps import CurrentUser, DbSession, require_hub, require_permission
from app.modules.routing import planning
from app.modules.routing.schemas import OptimizeOut, RouteDetailOut, RouteSummaryOut, StopOrderIn

router = APIRouter(prefix="/hub/routes", tags=["hub: routes"])
Planner = Annotated[CurrentUser, Depends(require_permission("route.plan"))]


@router.get("", response_model=list[RouteSummaryOut])
async def list_routes(
    session: DbSession, manager: Planner, work_date: date | None = None
) -> list[RouteSummaryOut]:
    """
    Driver routes of the hub for one day (default today), routes with active orders first.

    Outputs: [{"id", "driver_name", "status", "stops_total", "stops_pending",
               "orders_active", "orders_at_risk", "total_distance_m", "next_eta", ...}]
    """
    return await planning.list_routes(session, require_hub(manager), work_date or local_today())


@router.get("/{route_id}", response_model=RouteDetailOut)
async def get_route(route_id: uuid.UUID, session: DbSession, manager: Planner) -> RouteDetailOut:
    """Stops with their orders, driver position and the road geometry (encoded polyline)."""
    return await planning.route_detail(session, require_hub(manager), route_id)


@router.post("/{route_id}/optimize", response_model=OptimizeOut)
async def optimize_route(route_id: uuid.UUID, session: DbSession, manager: Planner) -> OptimizeOut:
    """
    Preview the fastest order of the pending stops (OSRM trip, else nearest neighbour).
    Nothing is saved. Errors: NOTHING_TO_OPTIMIZE
    """
    return await planning.optimize(session, require_hub(manager), route_id)


@router.put("/{route_id}/stops/order", response_model=RouteDetailOut)
async def save_stop_order(
    route_id: uuid.UUID, data: StopOrderIn, session: DbSession, manager: Planner
) -> RouteDetailOut:
    """
    Save a new order of the pending stops; ETAs are recomputed and the driver notified.

    Inputs: {"stop_ids": [...]} (every pending stop exactly once). Errors: STOP_LIST_MISMATCH
    """
    return await planning.save_stop_order(session, manager, route_id, data.stop_ids)
