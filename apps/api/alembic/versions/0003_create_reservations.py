"""create reservations

Revision ID: 0003_create_reservations
Revises: 0002_create_stations
Create Date: 2026-05-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_reservations"
down_revision: str | None = "0002_create_stations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(length=255), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("recommendation_rank", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="confirmed", nullable=False),
        sa.Column("reserved_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.station_id"], ondelete="RESTRICT"),
    )

    op.create_index("ix_reservations_user_id", "reservations", ["user_id"], unique=False)
    op.create_index("ix_reservations_station_id", "reservations", ["station_id"], unique=False)
    op.create_index("ix_reservations_client_request_id", "reservations", ["client_request_id"], unique=False)
    op.create_index("ix_reservations_request_id", "reservations", ["request_id"], unique=False)
    op.create_index("ix_reservations_status", "reservations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_request_id", table_name="reservations")
    op.drop_index("ix_reservations_client_request_id", table_name="reservations")
    op.drop_index("ix_reservations_station_id", table_name="reservations")
    op.drop_index("ix_reservations_user_id", table_name="reservations")
    op.drop_table("reservations")
