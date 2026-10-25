"""Business time helpers. Data is stored in UTC; business days follow Vietnam time."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now() -> datetime:
    return datetime.now(BUSINESS_TZ)


def local_today() -> date:
    return local_now().date()


def local_datetime(day: date, at: time) -> datetime:
    """Combine a business date and a wall-clock time into an aware datetime."""
    return datetime.combine(day, at, BUSINESS_TZ)


def parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))
