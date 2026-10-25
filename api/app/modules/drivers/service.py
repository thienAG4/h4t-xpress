"""Driver self-service: shift registration (UC-01, FR-D-01) and availability (FR-D-02)."""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_datetime, local_now, local_today, parse_hhmm, utc_now
from app.core.deps import CurrentUser
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.modules.drivers.schemas import (
    DriverTodayOut,
    RegistrationOut,
    ShiftDayOut,
    ShiftSlotOut,
    SlotStatus,
)
from app.modules.hubs.models import Shift, ShiftRegistration, ShiftRegistrationStatus
from app.modules.hubs.service import get_hub_out
from app.modules.orders.models import AttemptOutcome, DeliveryAttempt, Order, OrderStatus
from app.modules.settings.service import get_setting
from app.modules.users.models import DriverAvailability, DriverProfile

logger = logging.getLogger(__name__)

ACTIVE_ORDER_STATUSES = (OrderStatus.ASSIGNED, OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY)


def _require_hub(driver: CurrentUser) -> uuid.UUID:
    if driver.hub_id is None:
        raise ValidationFailed("Your account is not linked to a hub", code="HUB_REQUIRED")
    return driver.hub_id


def _overlaps(a: Shift, b: Shift) -> bool:
    return a.start_time < b.end_time and b.start_time < a.end_time


async def _registration_window(session: AsyncSession) -> tuple[date, date, bool]:
    """(first date, last date, whether today's shifts are still open) for registration."""
    cutoff = parse_hhmm(await get_setting(session, "shift.cutoff_time", "06:00"))
    max_days = int(await get_setting(session, "shift.max_days_ahead", 7))
    today = local_today()
    return today, today + timedelta(days=max_days), local_now().time() < cutoff


# =============================== Shift slots ===============================


async def list_shift_days(
    session: AsyncSession, driver: CurrentUser, date_from: date, days: int
) -> list[ShiftDayOut]:
    """Shift slots of the driver's hub for each day, with capacity and own status."""
    hub_id = _require_hub(driver)
    shifts = list(
        await session.scalars(
            select(Shift)
            .where(Shift.hub_id == hub_id, Shift.is_active.is_(True))
            .order_by(Shift.start_time, Shift.end_time)
        )
    )
    date_to = date_from + timedelta(days=days - 1)
    taken_rows = await session.execute(
        select(ShiftRegistration.shift_id, ShiftRegistration.work_date, func.count())
        .where(
            ShiftRegistration.shift_id.in_([s.id for s in shifts]),
            ShiftRegistration.work_date.between(date_from, date_to),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
        .group_by(ShiftRegistration.shift_id, ShiftRegistration.work_date)
    )
    taken = {(shift_id, day): count for shift_id, day, count in taken_rows}
    mine = {
        (reg.shift_id, reg.work_date): reg
        for reg in await session.scalars(
            select(ShiftRegistration).where(
                ShiftRegistration.driver_id == driver.id,
                ShiftRegistration.work_date.between(date_from, date_to),
                ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
            )
        )
    }
    by_id = {shift.id: shift for shift in shifts}
    first_open, last_open, today_open = await _registration_window(session)

    result: list[ShiftDayOut] = []
    for offset in range(days):
        day = date_from + timedelta(days=offset)
        my_shifts = [by_id[shift_id] for (shift_id, d) in mine if d == day and shift_id in by_id]
        slots = []
        for shift in shifts:
            registration = mine.get((shift.id, day))
            count = taken.get((shift.id, day), 0)
            if registration:
                status = SlotStatus.REGISTERED
            elif day < first_open or day > last_open or (day == first_open and not today_open):
                status = SlotStatus.CLOSED
            elif count >= shift.capacity:
                status = SlotStatus.FULL
            elif any(_overlaps(shift, other) for other in my_shifts):
                status = SlotStatus.CONFLICT
            else:
                status = SlotStatus.AVAILABLE
            slots.append(
                ShiftSlotOut(
                    shift_id=shift.id,
                    code=shift.code,
                    name=shift.name,
                    start_time=shift.start_time,
                    end_time=shift.end_time,
                    capacity=shift.capacity,
                    taken=count,
                    status=status,
                    registration_id=registration.id if registration else None,
                )
            )
        result.append(ShiftDayOut(work_date=day, slots=slots))
    return result


# =============================== Registrations ===============================


async def list_registrations(
    session: AsyncSession, driver: CurrentUser, date_from: date, date_to: date
) -> list[RegistrationOut]:
    rows = await session.execute(
        select(ShiftRegistration, Shift)
        .join(Shift, Shift.id == ShiftRegistration.shift_id)
        .where(
            ShiftRegistration.driver_id == driver.id,
            ShiftRegistration.work_date.between(date_from, date_to),
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
        .order_by(ShiftRegistration.work_date, Shift.start_time)
    )
    return [_registration_out(reg, shift) for reg, shift in rows]


async def register_shift(
    session: AsyncSession, driver: CurrentUser, shift_id: uuid.UUID, work_date: date
) -> RegistrationOut:
    """
    Register for a shift (UC-01). Rules: own hub only, inside the registration window,
    before the same-day cutoff, under capacity, and no overlap with another own shift.
    """
    hub_id = _require_hub(driver)
    # Row lock on the shift serialises concurrent registrations for its capacity.
    shift = await session.scalar(select(Shift).where(Shift.id == shift_id).with_for_update())
    if shift is None or shift.hub_id != hub_id or not shift.is_active:
        raise NotFound("Shift not found in your hub", code="SHIFT_NOT_FOUND")

    first_open, last_open, today_open = await _registration_window(session)
    if work_date < first_open or work_date > last_open:
        raise ValidationFailed("This date is outside the registration window", code="SHIFT_CLOSED")
    if work_date == first_open and not today_open:
        raise ValidationFailed("Registration for today is closed", code="SHIFT_CLOSED")

    same_day = list(
        await session.execute(
            select(ShiftRegistration, Shift)
            .join(Shift, Shift.id == ShiftRegistration.shift_id)
            .where(
                ShiftRegistration.driver_id == driver.id,
                ShiftRegistration.work_date == work_date,
            )
        )
    )
    existing = next((reg for reg, s in same_day if s.id == shift.id), None)
    if existing and existing.status == ShiftRegistrationStatus.REGISTERED:
        raise Conflict("You are already registered for this shift", code="ALREADY_REGISTERED")
    if any(
        reg.status == ShiftRegistrationStatus.REGISTERED and _overlaps(shift, other)
        for reg, other in same_day
    ):
        raise Conflict("This shift overlaps another shift you registered", code="SHIFT_OVERLAP")

    taken = await session.scalar(
        select(func.count()).where(
            ShiftRegistration.shift_id == shift.id,
            ShiftRegistration.work_date == work_date,
            ShiftRegistration.status == ShiftRegistrationStatus.REGISTERED,
        )
    )
    if (taken or 0) >= shift.capacity:
        raise Conflict("This shift is full", code="SHIFT_FULL")

    if existing:
        existing.status = ShiftRegistrationStatus.REGISTERED
        existing.cancelled_at = None
        registration = existing
    else:
        registration = ShiftRegistration(
            driver_id=driver.id, shift_id=shift.id, work_date=work_date
        )
        session.add(registration)
    await session.commit()
    logger.info("[register_shift] driver=%s shift=%s date=%s", driver.id, shift.code, work_date)
    return _registration_out(registration, shift)


async def cancel_registration(
    session: AsyncSession, driver: CurrentUser, registration_id: uuid.UUID
) -> None:
    row = (
        await session.execute(
            select(ShiftRegistration, Shift)
            .join(Shift, Shift.id == ShiftRegistration.shift_id)
            .where(
                ShiftRegistration.id == registration_id,
                ShiftRegistration.driver_id == driver.id,
            )
        )
    ).first()
    if row is None or row[0].status != ShiftRegistrationStatus.REGISTERED:
        raise NotFound("Registration not found", code="REGISTRATION_NOT_FOUND")
    registration, shift = row
    if local_datetime(registration.work_date, shift.start_time) <= local_now():
        raise ValidationFailed("A shift that has started cannot be cancelled", code="SHIFT_STARTED")
    registration.status = ShiftRegistrationStatus.CANCELLED
    registration.cancelled_at = utc_now()
    await session.commit()


def _registration_out(registration: ShiftRegistration, shift: Shift) -> RegistrationOut:
    return RegistrationOut(
        id=registration.id,
        shift_id=shift.id,
        shift_code=shift.code,
        shift_name=shift.name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        work_date=registration.work_date,
        status=registration.status,
    )


# =============================== Availability & home ===============================


async def set_availability(
    session: AsyncSession, driver: CurrentUser, online: bool
) -> DriverAvailability:
    """Turn 'ready for orders' on/off (FR-D-02). Going online needs a shift today (BR4)."""
    profile = await session.get(DriverProfile, driver.id)
    if profile is None:
        raise NotFound("Driver profile not found", code="DRIVER_PROFILE_NOT_FOUND")
    if online:
        today = local_today()
        if not await list_registrations(session, driver, today, today):
            raise ValidationFailed(
                "Register for a shift today before going online", code="NO_SHIFT_TODAY"
            )
    profile.availability = DriverAvailability.ONLINE if online else DriverAvailability.OFFLINE
    profile.last_seen_at = utc_now()
    await session.commit()
    return profile.availability


async def get_today(session: AsyncSession, driver: CurrentUser) -> DriverTodayOut:
    """Driver home (D-04): hub, availability, today's and upcoming shifts, counters."""
    profile = await session.get(DriverProfile, driver.id)
    if profile is None:
        raise NotFound("Driver profile not found", code="DRIVER_PROFILE_NOT_FOUND")
    today = local_today()
    registrations = await list_registrations(session, driver, today, today + timedelta(days=7))
    active_orders = await session.scalar(
        select(func.count()).where(
            Order.current_driver_id == driver.id, Order.status.in_(ACTIVE_ORDER_STATUSES)
        )
    )
    day_start = local_datetime(today, parse_hhmm("00:00"))
    delivered_today = await session.scalar(
        select(func.count()).where(
            DeliveryAttempt.driver_id == driver.id,
            DeliveryAttempt.outcome == AttemptOutcome.DELIVERED,
            DeliveryAttempt.attempted_at >= day_start,
        )
    )
    return DriverTodayOut(
        date=today,
        hub=await get_hub_out(session, driver.hub_id) if driver.hub_id else None,
        availability=profile.availability,
        shifts_today=[r for r in registrations if r.work_date == today],
        upcoming=[r for r in registrations if r.work_date > today],
        active_orders=active_orders or 0,
        delivered_today=delivered_today or 0,
    )
