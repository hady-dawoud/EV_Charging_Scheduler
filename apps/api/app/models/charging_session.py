from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ChargingSession(TimestampMixin, Base):
    __tablename__ = "charging_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
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
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reservations.reservation_id", ondelete="SET NULL"),
        index=True,
        nullable=True,
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
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default="active",
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    energy_kwh: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0",
        nullable=False,
    )
    cost_total: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    connector_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    charger_power_kw: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    user = relationship("User")
    station = relationship("Station")
    reservation = relationship("Reservation")
