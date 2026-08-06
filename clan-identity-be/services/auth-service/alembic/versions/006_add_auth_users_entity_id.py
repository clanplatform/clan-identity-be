"""add entity_id to auth_users

usersetup_basic.default_entity was renamed to entity_id (the FK to
entities.entity_id, "Branch / location"). auth_users mirrors usersetup_basic,
so it gains the same column here (mirroring how role_id was added in 005).

Revision ID: 006
Revises: 005
Create Date: 2026-07-31
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = [
    sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
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
