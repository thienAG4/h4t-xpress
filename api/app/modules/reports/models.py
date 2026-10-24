import datetime as dt
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DailyDriverStat(Base):
    """Per-driver daily counters, used for performance scoring (BR5) and FR-R-04."""

    __tablename__ = "daily_driver_stats"

    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[dt.date] = mapped_column(primary_key=True)
    hub_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hubs.id", ondelete="SET NULL"))
    assigned: Mapped[int] = mapped_column(default=0, server_default="0")
    delivered: Mapped[int] = mapped_column(default=0, server_default="0")
    failed: Mapped[int] = mapped_column(default=0, server_default="0")
    on_time: Mapped[int] = mapped_column(default=0, server_default="0")
    incidents: Mapped[int] = mapped_column(default=0, server_default="0")
