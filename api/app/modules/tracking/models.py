import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt


class DriverLocation(CreatedAt, Base):
    """GPS stream. High volume, so it uses a bigint identity key instead of UUID."""

    __tablename__ = "driver_locations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lat: Mapped[float]
    lng: Mapped[float]
    accuracy_m: Mapped[float | None]
    speed_kmh: Mapped[float | None]
    recorded_at: Mapped[datetime]

    # A btree on (driver_id, recorded_at) also serves "latest first" scans backwards.
    __table_args__ = (
        Index("ix_driver_locations_driver_id_recorded_at", "driver_id", "recorded_at"),
    )
