from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    station_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("stations.station_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    client_request_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    recommendation_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="confirmed",
        server_default="confirmed",
        index=True,
        nullable=False,
    )
    reserved_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reserved_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estimated_cost_gbp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    estimated_duration_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    charger_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    distance_km: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    user = relationship("User")
    station = relationship("Station")
