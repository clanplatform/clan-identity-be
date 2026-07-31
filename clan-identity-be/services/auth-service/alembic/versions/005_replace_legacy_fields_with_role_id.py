"""replace legacy usersetup_basic mirror fields with role_id

usersetup_basic (admin-service) dropped 13 unused fields (employment metadata,
org-structure refs, and the old manage_roles / usersetup_roles_entity
role-assignment mechanism) and replaced role assignment with a single
usersetup_basic.role_id column. auth_users mirrors usersetup_basic, so it
follows the same change here:
  - Dropped: start_date, end_date, tem_employee, department, division,
    job_code, manage_roles, default_dept, reporting_to, entities,
    default_entity, view, dashboard_view
  - Added: role_id (UUID, mirrors usersetup_basic.role_id / user_role.id)

Revision ID: 005
Revises: 004
Create Date: 2026-07-31
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DROPPED_COLUMNS = [
    "start_date", "end_date", "tem_employee",
    "department", "division", "job_code",
    "manage_roles", "default_dept", "reporting_to",
    "entities", "default_entity",
    "view", "dashboard_view",
]

_NEW_COLUMNS = [
    sa.Column("role_id", UUID(as_uuid=True), nullable=True),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = [col["name"] for col in inspector.get_columns("auth_users")]

    for column in _NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("auth_users", column)

    for column_name in _DROPPED_COLUMNS:
        if column_name in existing:
            op.drop_column("auth_users", column_name)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing = [col["name"] for col in inspector.get_columns("auth_users")]

    if "role_id" in existing:
        op.drop_column("auth_users", "role_id")

    op.add_column("auth_users", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("auth_users", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("auth_users", sa.Column("tem_employee", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("auth_users", sa.Column("department", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("division", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("job_code", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("manage_roles", sa.ARRAY(UUID(as_uuid=True)), nullable=True))
    op.add_column("auth_users", sa.Column("default_dept", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("reporting_to", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("entities", sa.ARRAY(UUID(as_uuid=True)), nullable=True))
    op.add_column("auth_users", sa.Column("default_entity", UUID(as_uuid=True), nullable=True))
    op.add_column("auth_users", sa.Column("view", sa.String(50), nullable=True))
    op.add_column("auth_users", sa.Column("dashboard_view", sa.String(50), nullable=True))
