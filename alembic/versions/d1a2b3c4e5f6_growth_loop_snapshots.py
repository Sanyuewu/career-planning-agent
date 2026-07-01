"""成长闭环时序层：画像/匹配快照 + 独立行动计划表

新建 portrait_snapshots / match_snapshots / action_plans 三张 append-only 表，
承载"画像→差距→行动→进步→再画像"闭环的历史态。沿用 M0 tenant 行级隔离，
只加新表+索引，不碰存量表结构（KVStore 当前态热路径不受影响）。

Revision ID: d1a2b3c4e5f6
Revises: c0ffee1d2e3f
Create Date: 2026-06-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1a2b3c4e5f6"
down_revision: Union[str, Sequence[str], None] = "c0ffee1d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 画像快照（append-only）──
    op.create_table(
        "portrait_snapshots",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("student_id", sa.String(64), nullable=False),
        sa.Column("tenant", sa.String(64), nullable=False, server_default="default"),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="resume_update"),
        sa.Column("portrait_json", sa.Text(), nullable=False),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("competitiveness_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ps_student_ver", "portrait_snapshots", ["student_id", "version"], unique=False)
    op.create_index("ix_ps_tenant_time", "portrait_snapshots", ["tenant", "created_at"], unique=False)

    # ── 匹配快照（append-only）──
    op.create_table(
        "match_snapshots",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("student_id", sa.String(64), nullable=False),
        sa.Column("tenant", sa.String(64), nullable=False, server_default="default"),
        sa.Column("portrait_version", sa.Integer(), nullable=True),
        sa.Column("job_name", sa.String(128), nullable=False),
        sa.Column("total_match", sa.Float(), nullable=False),
        sa.Column("basic_match", sa.Float(), nullable=False),
        sa.Column("skill_match", sa.Float(), nullable=False),
        sa.Column("quality_match", sa.Float(), nullable=False),
        sa.Column("potential_match", sa.Float(), nullable=False),
        sa.Column("matched_skills", sa.Text(), nullable=True),
        sa.Column("missing_skills", sa.Text(), nullable=True),
        sa.Column("weight_used", sa.Text(), nullable=True),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("veto_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ms_student_time", "match_snapshots", ["student_id", "created_at"], unique=False)
    op.create_index("ix_ms_tenant", "match_snapshots", ["tenant"], unique=False)

    # ── 行动计划（独立实体）──
    op.create_table(
        "action_plans",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("student_id", sa.String(64), nullable=False),
        sa.Column("tenant", sa.String(64), nullable=False, server_default="default"),
        sa.Column("portrait_version", sa.Integer(), nullable=True),
        sa.Column("job_name", sa.String(128), nullable=True),
        sa.Column("items_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_student_status", "action_plans", ["student_id", "status"], unique=False)
    op.create_index("ix_ap_tenant", "action_plans", ["tenant"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ap_tenant", table_name="action_plans")
    op.drop_index("ix_ap_student_status", table_name="action_plans")
    op.drop_table("action_plans")
    op.drop_index("ix_ms_tenant", table_name="match_snapshots")
    op.drop_index("ix_ms_student_time", table_name="match_snapshots")
    op.drop_table("match_snapshots")
    op.drop_index("ix_ps_tenant_time", table_name="portrait_snapshots")
    op.drop_index("ix_ps_student_ver", table_name="portrait_snapshots")
    op.drop_table("portrait_snapshots")
