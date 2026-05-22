"""create charging sessions

Revision ID: 0004_create_charging_sessions
Revises: 0003_create_reservations
Create Date: 2026-05-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_charging_sessions"
down_revision: str | None = "0003_create_reservations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "charging_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(length=255), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_request_id", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("energy_kwh", sa.Float(), server_default="0", nullable=False),
        sa.Column("cost_total", sa.Float(), nullable=True),
        sa.Column("connector_type", sa.String(length=100), nullable=True),
        sa.Column("charger_power_kw", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.station_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.reservation_id"], ondelete="SET NULL"),
    )

    op.create_index("ix_charging_sessions_user_id", "charging_sessions", ["user_id"], unique=False)
    op.create_index("ix_charging_sessions_station_id", "charging_sessions", ["station_id"], unique=False)
    op.create_index("ix_charging_sessions_reservation_id", "charging_sessions", ["reservation_id"], unique=False)
    op.create_index("ix_charging_sessions_client_request_id", "charging_sessions", ["client_request_id"], unique=False)
    op.create_index("ix_charging_sessions_request_id", "charging_sessions", ["request_id"], unique=False)
    op.create_index("ix_charging_sessions_status", "charging_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_charging_sessions_status", table_name="charging_sessions")
    op.drop_index("ix_charging_sessions_request_id", table_name="charging_sessions")
    op.drop_index("ix_charging_sessions_client_request_id", table_name="charging_sessions")
    op.drop_index("ix_charging_sessions_reservation_id", table_name="charging_sessions")
    op.drop_index("ix_charging_sessions_station_id", table_name="charging_sessions")
    op.drop_index("ix_charging_sessions_user_id", table_name="charging_sessions")
    op.drop_table("charging_sessions")
