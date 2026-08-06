"""convert auth_users.entity_id to array

usersetup_basic.entity_id was converted from a single UUID to UUID[] — one
user can now belong to multiple entities (branches). auth_users mirrors
usersetup_basic, so it follows here. Existing single values are wrapped into
a 1-element array; NULL stays NULL. The first array element is treated as the
user's default/primary branch.

Revision ID: 007
Revises: 006
Create Date: 2026-08-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    col = next(
        (c for c in inspector.get_columns("auth_users") if c["name"] == "entity_id"),
        None,
    )
    if col is not None and not isinstance(col["type"], sa.ARRAY):
        op.alter_column(
            "auth_users",
            "entity_id",
            type_=sa.ARRAY(UUID(as_uuid=True)),
            postgresql_using="(CASE WHEN entity_id IS NULL THEN NULL ELSE ARRAY[entity_id] END)",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    col = next(
        (c for c in inspector.get_columns("auth_users") if c["name"] == "entity_id"),
        None,
    )
    if col is not None and isinstance(col["type"], sa.ARRAY):
        op.alter_column(
            "auth_users",
            "entity_id",
            type_=UUID(as_uuid=True),
            postgresql_using="entity_id[1]",
        )
