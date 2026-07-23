"""extend login_attempts with device/network/risk enrichment fields

Revision ID: 003
Revises: 002
Create Date: 2026-07-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = [
    # Tenant / session context
    sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
    sa.Column("session_id", UUID(as_uuid=True), nullable=True),
    # Network
    sa.Column("ip_type", sa.String(10), nullable=True),
    sa.Column("isp", sa.String(150), nullable=True),
    sa.Column("region", sa.String(100), nullable=True),
    sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("is_proxy", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("is_tor", sa.Boolean(), nullable=False, server_default=sa.false()),
    # Device (parsed from User-Agent)
    sa.Column("device_type", sa.String(20), nullable=True),
    sa.Column("device_name", sa.String(100), nullable=True),
    sa.Column("browser", sa.String(50), nullable=True),
    sa.Column("browser_version", sa.String(20), nullable=True),
    sa.Column("os", sa.String(50), nullable=True),
    sa.Column("os_version", sa.String(20), nullable=True),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = [col["name"] for col in inspector.get_columns("login_attempts")]

    for column in _NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("login_attempts", column)

    # risk_score was VARCHAR(10) and never populated — convert to SMALLINT
    risk_col = next(
        (c for c in inspector.get_columns("login_attempts") if c["name"] == "risk_score"),
        None,
    )
    if risk_col is not None and not isinstance(risk_col["type"], sa.SmallInteger):
        op.alter_column(
            "login_attempts",
            "risk_score",
            type_=sa.SmallInteger(),
            postgresql_using="risk_score::smallint",
        )

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("login_attempts")]
    if "ix_login_attempts_tenant_id" not in existing_indexes:
        op.create_index("ix_login_attempts_tenant_id", "login_attempts", ["tenant_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("login_attempts")]
    if "ix_login_attempts_tenant_id" in existing_indexes:
        op.drop_index("ix_login_attempts_tenant_id", table_name="login_attempts")

    existing = [col["name"] for col in inspector.get_columns("login_attempts")]
    for column in reversed(_NEW_COLUMNS):
        if column.name in existing:
            op.drop_column("login_attempts", column.name)

    op.alter_column(
        "login_attempts",
        "risk_score",
        type_=sa.String(10),
        postgresql_using="risk_score::varchar",
    )
