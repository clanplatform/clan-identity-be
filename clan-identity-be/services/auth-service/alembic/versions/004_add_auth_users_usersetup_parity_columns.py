"""add auth_users columns for usersetup_basic parity

Brings auth_users to field parity with admin-service usersetup_basic by adding
the three columns it was missing:
  user_group_id     UUID       (bare reference)
  send_invite_email BOOLEAN     (invite flag)
  allowed_origins   TEXT[]      (per-user redirect targets)

Revision ID: 004
Revises: 003
Create Date: 2026-07-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = [
    sa.Column("user_group_id", UUID(as_uuid=True), nullable=True),
    sa.Column("send_invite_email", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("allowed_origins", sa.ARRAY(sa.Text()), nullable=True),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = [col["name"] for col in inspector.get_columns("auth_users")]

    for column in _NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("auth_users", column)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = [col["name"] for col in inspector.get_columns("auth_users")]

    for column in reversed(_NEW_COLUMNS):
        if column.name in existing:
            op.drop_column("auth_users", column.name)
