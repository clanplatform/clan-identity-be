"""add job_code_id to auth_users

usersetup_basic (admin-service) gained job_code_id (job_codes.id).
auth_users mirrors usersetup_basic, so it follows here. No local FK — the
job_codes table lives only in admin-service's database, same as how
role_id/user_group_id are bare references here.

Revision ID: 009
Revises: 008
Create Date: 2026-08-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column("job_code_id", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("auth_users", "job_code_id")
