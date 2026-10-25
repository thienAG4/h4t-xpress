"""Reports for executives and hub managers (E-01, E-02; FR-R-01..FR-R-06)."""

import uuid
from datetime import date
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.deps import CurrentUser, DbSession, client_ip, require_permission
from app.modules.audit.service import record_audit
from app.modules.reports import export, queries
from app.modules.reports.schemas import Granularity, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])
Viewer = Annotated[CurrentUser, Depends(require_permission("report.view"))]
Exporter = Annotated[CurrentUser, Depends(require_permission("report.view", "report.export"))]
HubIds = Annotated[list[uuid.UUID] | None, Query()]


class ExportFormat(StrEnum):
    XLSX = "xlsx"
    PDF = "pdf"


MEDIA_TYPES = {
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF: "application/pdf",
}


@router.get("", response_model=ReportOut)
async def get_report(
    session: DbSession,
    user: Viewer,
    date_from: date | None = None,
    date_to: date | None = None,
    hub_ids: HubIds = None,
    granularity: Granularity | None = None,
) -> ReportOut:
    """
    Every block of the reports page in one call (E-01).

    Inputs (query): date_from, date_to (default: last 30 days), hub_ids (repeatable;
    a hub manager always gets their own hub), granularity (day | week | month)
    Errors: DATE_RANGE, OUT_OF_SCOPE
    """
    scope = await queries.resolve_scope(session, user, date_from, date_to, hub_ids)
    return await queries.build_report(
        session, scope, granularity or queries.default_granularity(scope)
    )


@router.get("/export")
async def export_report(
    request: Request,
    session: DbSession,
    user: Exporter,
    format: ExportFormat = ExportFormat.XLSX,
    date_from: date | None = None,
    date_to: date | None = None,
    hub_ids: HubIds = None,
    granularity: Granularity | None = None,
) -> Response:
    """Download the same report as Excel or PDF (E-02). Needs report.export."""
    scope = await queries.resolve_scope(session, user, date_from, date_to, hub_ids)
    report = await queries.build_report(
        session, scope, granularity or queries.default_granularity(scope)
    )
    content = export.to_xlsx(report) if format == ExportFormat.XLSX else export.to_pdf(report)
    record_audit(
        session,
        actor_id=user.id,
        action="report.exported",
        entity_type="report",
        entity_id=None,
        after={
            "format": format.value,
            "from": scope.date_from.isoformat(),
            "to": scope.date_to.isoformat(),
            "hubs": [str(hub_id) for hub_id in scope.hub_ids],
        },
        ip=client_ip(request),
    )
    await session.commit()
    filename = f"h4t-report-{scope.date_from:%Y%m%d}-{scope.date_to:%Y%m%d}.{format.value}"
    return Response(
        content,
        media_type=MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
