"""create stations

Revision ID: 0002_create_stations
Revises: 0001_users_refresh_tokens
Create Date: 2026-05-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_create_stations"
down_revision: str | None = "0001_users_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("station_id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=False),
        sa.Column("postcode", sa.String(length=50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=True),
        sa.Column("transformer_id", sa.String(length=255), nullable=True),
        sa.Column("cp_count_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("connector_mix_total", sa.String(length=255), nullable=True),
        sa.Column("station_max_power_kw_proxy", sa.Float(), nullable=True),
        sa.Column("station_capacity_kw_assumed", sa.Float(), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_fleet_only", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requires_membership", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("exclude_from_recommendations", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("access_notes", sa.Text(), nullable=True),
        sa.Column("location_source", sa.String(length=255), nullable=True),
        sa.Column("location_confidence", sa.String(length=50), nullable=True),
        sa.Column("needs_followup", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sessions_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("energy_total_kwh", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_stations_zone_id", "stations", ["zone_id"], unique=False)
    op.create_index("ix_stations_transformer_id", "stations", ["transformer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stations_transformer_id", table_name="stations")
    op.drop_index("ix_stations_zone_id", table_name="stations")
    op.drop_table("stations")
