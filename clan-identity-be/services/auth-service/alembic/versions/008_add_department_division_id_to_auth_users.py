"""add department_id/division_id arrays to auth_users

usersetup_basic (admin-service) gained department_id/division_id — arrays
of UUIDs, same shape as entity_id, used to resolve a role's access_scope of
"department" or "division". auth_users mirrors usersetup_basic, so it
follows here.

Revision ID: 008
Revises: 007
Create Date: 2026-08-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column("department_id", sa.ARRAY(UUID(as_uuid=True)), nullable=True),
    )
    op.add_column(
        "auth_users",
        sa.Column("division_id", sa.ARRAY(UUID(as_uuid=True)), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("auth_users", "division_id")
    op.drop_column("auth_users", "department_id")
