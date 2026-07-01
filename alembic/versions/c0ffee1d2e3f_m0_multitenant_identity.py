"""M0 多租户 + 身份/组织表

为 kv_store / agent_runs 增加 tenant 列（存量行回填 default）；
新建 tenants / users / class_groups / teacher_classes 身份与组织表。

Revision ID: c0ffee1d2e3f
Revises: 19bc6f009bf8
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0ffee1d2e3f"
down_revision: Union[str, Sequence[str], None] = "19bc6f009bf8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 多租户列（存量行 server_default 回填 'default'）──
    op.add_column("kv_store",
                  sa.Column("tenant", sa.String(64), nullable=False, server_default="default"))
    op.create_index("ix_kv_tenant_ns", "kv_store", ["tenant", "namespace"], unique=False)
    op.add_column("agent_runs",
                  sa.Column("tenant", sa.String(64), nullable=False, server_default="default"))

    # ── 身份与租户/组织表 ──
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("student_id", sa.String(64), nullable=True),
        sa.Column("class_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_tenant_role", "users", ["tenant_id", "role"], unique=False)
    op.create_table(
        "class_groups",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classes_tenant", "class_groups", ["tenant_id"], unique=False)
    op.create_table(
        "teacher_classes",
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("class_id", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["class_id"], ["class_groups.id"]),
        sa.PrimaryKeyConstraint("teacher_id", "class_id"),
    )


def downgrade() -> None:
    op.drop_table("teacher_classes")
    op.drop_index("ix_classes_tenant", table_name="class_groups")
    op.drop_table("class_groups")
    op.drop_index("ix_users_tenant_role", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
    op.drop_column("agent_runs", "tenant")
    op.drop_index("ix_kv_tenant_ns", table_name="kv_store")
    op.drop_column("kv_store", "tenant")
