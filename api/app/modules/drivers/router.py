"""Driver app endpoints for Phase 1: home summary, shifts and availability."""

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.clock import local_today
from app.core.deps import CurrentUser, DbSession, require_permission
from app.modules.drivers import service
from app.modules.drivers.schemas import (
    AvailabilityIn,
    AvailabilityOut,
    DriverTodayOut,
    RegistrationOut,
    ShiftDayOut,
    ShiftRegistrationIn,
)

router = APIRouter(prefix="/driver", tags=["driver"])
ShiftDriver = Annotated[CurrentUser, Depends(require_permission("shift.register"))]
AvailabilityDriver = Annotated[CurrentUser, Depends(require_permission("availability.toggle"))]


@router.get("/today", response_model=DriverTodayOut)
async def get_today(session: DbSession, driver: ShiftDriver) -> DriverTodayOut:
    """
    Driver home (D-04).

    Outputs: {"date", "hub", "availability", "shifts_today", "upcoming",
              "active_orders", "delivered_today"}
    """
    return await service.get_today(session, driver)


@router.get("/shifts", response_model=list[ShiftDayOut])
async def list_shifts(
    session: DbSession,
    driver: ShiftDriver,
    date_from: date | None = None,
    days: Annotated[int, Query(ge=1, le=14)] = 7,
) -> list[ShiftDayOut]:
    """Shift slots per day with capacity and status (AVAILABLE/REGISTERED/FULL/CLOSED/CONFLICT)."""
    return await service.list_shift_days(session, driver, date_from or local_today(), days)


@router.get("/shift-registrations", response_model=list[RegistrationOut])
async def list_registrations(session: DbSession, driver: ShiftDriver) -> list[RegistrationOut]:
    today = local_today()
    return await service.list_registrations(session, driver, today, today + timedelta(days=14))


@router.post("/shift-registrations", response_model=RegistrationOut, status_code=201)
async def register_shift(
    data: ShiftRegistrationIn, session: DbSession, driver: ShiftDriver
) -> RegistrationOut:
    """
    Register for a shift.

    Inputs: {"shift_id", "work_date": "2026-10-26"}
    Errors: SHIFT_NOT_FOUND, SHIFT_CLOSED, SHIFT_FULL, SHIFT_OVERLAP, ALREADY_REGISTERED
    """
    return await service.register_shift(session, driver, data.shift_id, data.work_date)


@router.delete("/shift-registrations/{registration_id}", status_code=204)
async def cancel_registration(
    registration_id: uuid.UUID, session: DbSession, driver: ShiftDriver
) -> Response:
    """Errors: REGISTRATION_NOT_FOUND, SHIFT_STARTED."""
    await service.cancel_registration(session, driver, registration_id)
    return Response(status_code=204)


@router.put("/availability", response_model=AvailabilityOut)
async def set_availability(
    data: AvailabilityIn, session: DbSession, driver: AvailabilityDriver
) -> AvailabilityOut:
    """Inputs: {"online": true}. Errors: NO_SHIFT_TODAY."""
    return AvailabilityOut(
        availability=await service.set_availability(session, driver, data.online)
    )
