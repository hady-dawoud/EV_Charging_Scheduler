"""add google subject to users

Revision ID: 0008_google_auth_user_sub
Revises: 0007_user_vehicles
Create Date: 2026-06-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_google_auth_user_sub"
down_revision: str | None = "0007_user_vehicles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
