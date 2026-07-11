"""drop device_fingerprint from sessions

Revision ID: 002
Revises: 001
Create Date: 2026-07-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [col["name"] for col in inspector.get_columns("sessions")]
    if "device_fingerprint" in columns:
        op.drop_column("sessions", "device_fingerprint")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [col["name"] for col in inspector.get_columns("sessions")]
    if "device_fingerprint" not in columns:
        op.add_column(
            "sessions",
            sa.Column("device_fingerprint", sa.String(length=255), nullable=True),
        )
