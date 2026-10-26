"""Incident endpoints: drivers report (D-11), hub managers handle (H-04..H-08)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_hub, require_permission
from app.core.pagination import Page, PageParams, page_params
from app.modules.incidents import service
from app.modules.incidents.models import IncidentPriority, IncidentStatus
from app.modules.incidents.schemas import (
    CandidateOut,
    ClassifyIn,
    IncidentListItem,
    IncidentOut,
    IncidentReportIn,
    IncidentSummaryOut,
    ResolveIn,
    RespondIn,
)

driver_router = APIRouter(prefix="/driver/incidents", tags=["driver: incidents"])
hub_router = APIRouter(prefix="/hub/incidents", tags=["hub: incidents"])
Reporter = Annotated[CurrentUser, Depends(require_permission("incident.report"))]
Handler = Annotated[CurrentUser, Depends(require_permission("incident.manage"))]
Paging = Annotated[PageParams, Depends(page_params)]


# =============================== Driver ===============================


@driver_router.post("", response_model=IncidentOut, status_code=201)
async def report_incident(
    data: IncidentReportIn, session: DbSession, driver: Reporter
) -> IncidentOut:
    """
    Report a problem on the road (UC-03 step 1).

    Inputs: {"type", "description", "photo_file_ids": [...], "order_ids": [...] | null,
             "lat", "lng"}. Without order_ids every order in hand is affected.
    Errors: EVIDENCE_REQUIRED, NO_ACTIVE_ORDER, FILE_NOT_FOUND
    """
    return await service.report(session, driver, data)


@driver_router.get("", response_model=list[IncidentOut])
async def list_my_incidents(session: DbSession, driver: Reporter) -> list[IncidentOut]:
    return await service.list_for_driver(session, driver.id)


@driver_router.get("/{incident_id}", response_model=IncidentOut)
async def get_my_incident(
    incident_id: uuid.UUID, session: DbSession, driver: Reporter
) -> IncidentOut:
    """Status and the hub's answer, refreshed by the `incident.updated` event."""
    return await service.get_for_driver(session, driver.id, incident_id)


# =============================== Hub ===============================


@hub_router.get("/summary", response_model=IncidentSummaryOut)
async def get_summary(session: DbSession, manager: Handler) -> IncidentSummaryOut:
    """Counters of H-04: open, in review, resolving, resolved today, by priority, by type."""
    return await service.summary(session, require_hub(manager))


@hub_router.get("", response_model=Page[IncidentListItem])
async def list_incidents(
    session: DbSession,
    manager: Handler,
    paging: Paging,
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    open_only: bool = False,
    q: Annotated[str | None, Query(max_length=60)] = None,
    days: Annotated[int | None, Query(ge=1, le=366)] = None,
) -> Page[IncidentListItem]:
    """
    Incident list (H-05), open and high priority first.

    Inputs: status, priority, open_only, q (incident code, driver name or waybill),
            days (reported in the last N days), page, page_size
    """
    return await service.list_for_hub(
        session,
        require_hub(manager),
        paging,
        status=status,
        priority=priority,
        open_only=open_only,
        q=q,
        days=days,
    )


@hub_router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: uuid.UUID, session: DbSession, manager: Handler) -> IncidentOut:
    return await service.get_for_hub(session, require_hub(manager), incident_id)


@hub_router.post("/{incident_id}/classify", response_model=IncidentOut)
async def classify_incident(
    incident_id: uuid.UUID, data: ClassifyIn, session: DbSession, manager: Handler
) -> IncidentOut:
    """
    Set category and priority (UC-03 step 2, BR13).

    Inputs: {"category": "OBJECTIVE" | "SUBJECTIVE", "priority": "LOW" | "MEDIUM" | "HIGH"}
    Errors: INCIDENT_CLOSED
    """
    return await service.classify(session, manager, incident_id, data.category, data.priority)


@hub_router.post("/{incident_id}/respond", response_model=IncidentOut)
async def respond_incident(
    incident_id: uuid.UUID, data: RespondIn, session: DbSession, manager: Handler
) -> IncidentOut:
    """Answer the driver (BR14). Errors: INCIDENT_NOT_CLASSIFIED."""
    return await service.respond(session, manager, incident_id, data.message)


@hub_router.get("/{incident_id}/candidates", response_model=list[CandidateOut])
async def list_candidates(
    incident_id: uuid.UUID, session: DbSession, manager: Handler
) -> list[CandidateOut]:
    """Replacement drivers around the incident location (UC-04)."""
    return await service.candidates(session, manager, incident_id)


@hub_router.post("/{incident_id}/resolve", response_model=IncidentOut)
async def resolve_incident(
    incident_id: uuid.UUID, data: ResolveIn, session: DbSession, manager: Handler
) -> IncidentOut:
    """
    Apply a solution (BR15).

    Inputs: {"solution": "ROUTE_SUGGESTED", "stop_ids": [...]}
            {"solution": "DRIVER_REASSIGNMENT", "driver_id", "order_ids": [...] | null}
            {"solution": "HOLD_AT_HUB", "note"}
    Errors: INCIDENT_NOT_CLASSIFIED, RESPONSE_REQUIRED, INCIDENT_CLOSED,
            DRIVER_NOT_AVAILABLE, DRIVER_BUSY
    """
    return await service.resolve(session, manager, incident_id, data)
