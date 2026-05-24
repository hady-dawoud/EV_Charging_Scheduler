from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Station(TimestampMixin, Base):
    __tablename__ = "stations"

    station_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    station_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    postcode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    zone_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    transformer_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    cp_count_total: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    connector_mix_total: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    station_max_power_kw_proxy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    station_capacity_kw_assumed: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    is_fleet_only: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    requires_membership: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    exclude_from_recommendations: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    access_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    location_source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    location_confidence: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    needs_followup: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    sessions_total: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    energy_total_kwh: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0",
        nullable=False,
    )
