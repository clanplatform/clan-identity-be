"""add tenant_id to auth_users

Revision ID: 001
Revises:
Create Date: 2026-06-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [col["name"] for col in inspector.get_columns("auth_users")]
    if "tenant_id" not in columns:
        op.add_column(
            "auth_users",
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        )

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("auth_users")]
    if "ix_auth_users_tenant_id" not in existing_indexes:
        op.create_index("ix_auth_users_tenant_id", "auth_users", ["tenant_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("auth_users")]
    if "ix_auth_users_tenant_id" in existing_indexes:
        op.drop_index("ix_auth_users_tenant_id", table_name="auth_users")

    columns = [col["name"] for col in inspector.get_columns("auth_users")]
    if "tenant_id" in columns:
        op.drop_column("auth_users", "tenant_id")
