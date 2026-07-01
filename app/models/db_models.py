# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM 模型定义。

运行时数据表示（D-A/D-B 收敛后）：
  - 文档型实体（会话/报告/学生/匹配）→ KVStore（kv_store 表，按 namespace 区分）。
  - Agent 可观测 → AgentRun / AgentStep。
  - 身份与租户（M0）→ Tenant / User / ClassGroup / TeacherClass（规范化表，需关系查询）。

多租户（M0）：共享库 + tenant 列，行级隔离。文档型实体的 tenant 落在 KVStore.tenant；
身份/组织实体自带 tenant_id。隔离靠存储层按 tenant 过滤 + 端点授权 + 测试三重保证。
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security_context import DEFAULT_TENANT


class KVStore(Base):
    """
    通用键值持久化表，运行时富结构状态（会话/报告/学生/匹配）的写穿存储。
    以 JSON 整体存储，按 namespace 区分实体类型；student_id 建索引供统计计数。
    namespace ∈ {chat, report, student, match}。
    """
    __tablename__ = "kv_store"
    __table_args__ = (
        Index("ix_kv_ns_sid", "namespace", "student_id"),
        Index("ix_kv_tenant_ns", "tenant", "namespace"),
    )

    namespace  = Column(String(32), primary_key=True)
    key        = Column(String(64), primary_key=True)
    value_json = Column(Text,       nullable=False)
    student_id = Column(String(64), nullable=True)
    # M0 多租户：行级隔离键；存量数据 server_default 落 DEFAULT_TENANT。
    tenant     = Column(String(64), nullable=False,
                        default=DEFAULT_TENANT, server_default=DEFAULT_TENANT)
    updated_at = Column(DateTime,   nullable=False, default=datetime.utcnow)


class AgentRun(Base):
    """一次 Agent 任务运行（一个目标 → 多步工具调用）。用于可观测与回放。"""
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_sid", "student_id"),)

    id          = Column(String(64),  primary_key=True)     # run_id
    student_id  = Column(String(64),  nullable=False)
    tenant      = Column(String(64),  nullable=False,
                         default=DEFAULT_TENANT, server_default=DEFAULT_TENANT)
    session_id  = Column(String(64),  nullable=True)        # 关联会话（如有）
    goal        = Column(Text,        nullable=True)
    status      = Column(String(16),  nullable=False, default="running")  # running/done/error
    final_state = Column(String(32),  nullable=True)        # 结束时的 FSM 状态
    trace_id    = Column(String(64),  nullable=True)        # 贯穿全链路的追踪 ID
    step_count  = Column(Integer,     nullable=False, default=0)
    ttft_ms     = Column(Integer,     nullable=True)        # 首 token 时间
    latency_ms  = Column(Integer,     nullable=True)        # 端到端耗时
    created_at  = Column(DateTime,    nullable=False, default=datetime.utcnow)

    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")


class AgentStep(Base):
    """Agent 运行中的单步：thought / tool_call / tool_result / transition。"""
    __tablename__ = "agent_steps"
    __table_args__ = (Index("ix_agent_steps_run", "run_id"),)

    id          = Column(Integer,    primary_key=True, autoincrement=True)
    run_id      = Column(String(64), ForeignKey("agent_runs.id"), nullable=False)
    step_no     = Column(Integer,    nullable=False)
    type        = Column(String(24), nullable=False)        # thought/tool_call/tool_result/transition/done/error
    state       = Column(String(32), nullable=True)         # 该步所处 FSM 状态
    tool_name   = Column(String(64), nullable=True)
    args_json   = Column(Text,       nullable=True)
    result_json = Column(Text,       nullable=True)
    latency_ms  = Column(Integer,    nullable=True)
    token_usage = Column(Integer,    nullable=True)
    created_at  = Column(DateTime,   nullable=False, default=datetime.utcnow)

    run = relationship("AgentRun", back_populates="steps")


# ── M0 身份与租户（规范化表，需关系查询，不入 KVStore）─────────────────────
class Tenant(Base):
    """租户（院校）。多租户行级隔离的归属单位；config_json 预留 M2 租户级配置。"""
    __tablename__ = "tenants"

    id         = Column(String(64),  primary_key=True)      # 租户/校代码
    name       = Column(String(128), nullable=False)
    config_json = Column(Text,       nullable=True)         # 预留：权重/模板/岗位库按校配置
    created_at = Column(DateTime,    nullable=False, default=datetime.utcnow)


class User(Base):
    """登录账号。一个账号属于一个租户、一种角色；学生账号经 student_id 关联其画像。"""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )

    id            = Column(String(64),  primary_key=True)   # user_id (uuid)
    username      = Column(String(64),  nullable=False)
    password_hash = Column(String(255), nullable=False)
    tenant_id     = Column(String(64),  nullable=False, default=DEFAULT_TENANT)
    role          = Column(String(16),  nullable=False, default="student")  # student/teacher/admin
    student_id    = Column(String(64),  nullable=True)      # 学生账号→其画像 key（teacher/admin 为空）
    class_id      = Column(String(64),  nullable=True)      # 学生所属班级（数据范围用）
    created_at    = Column(DateTime,    nullable=False, default=datetime.utcnow)


class ClassGroup(Base):
    """班级。teacher 的数据范围以"所带班级"为边界。"""
    __tablename__ = "class_groups"
    __table_args__ = (Index("ix_classes_tenant", "tenant_id"),)

    id         = Column(String(64),  primary_key=True)      # class_id (uuid)
    tenant_id  = Column(String(64),  nullable=False, default=DEFAULT_TENANT)
    name       = Column(String(128), nullable=False)
    created_at = Column(DateTime,    nullable=False, default=datetime.utcnow)


class TeacherClass(Base):
    """老师↔班级 关联（多对多）。决定 teacher 能看哪些班的学生。"""
    __tablename__ = "teacher_classes"

    teacher_id = Column(String(64), ForeignKey("users.id"), primary_key=True)
    class_id   = Column(String(64), ForeignKey("class_groups.id"), primary_key=True)


# ── 成长闭环时序层（append-only 快照，叠加在 KVStore 当前态之上）──────────────
# 设计：KVStore 仍存"当前态"供热路径查询；以下三表存"历史态"，让
# "画像→差距→行动→进步→再画像"闭环里的"变了多少 / 行动完成没"可被记录与计算。
# 与 KVStore 同走 tenant 行级隔离；写入失败不破坏主流程（见 snapshot_store）。

class PortraitSnapshot(Base):
    """学生画像快照（不可变）。每次画像更新（简历/手动/复评）append 一条，version 递增。
    portrait_json 与 KVStore 学生画像同等敏感，落库前经 PII 加密边界处理。"""
    __tablename__ = "portrait_snapshots"
    __table_args__ = (
        Index("ix_ps_student_ver", "student_id", "version"),
        Index("ix_ps_tenant_time", "tenant", "created_at"),
    )

    id          = Column(String(64),  primary_key=True)     # snapshot_id (uuid)
    student_id  = Column(String(64),  nullable=False)
    tenant      = Column(String(64),  nullable=False,
                         default=DEFAULT_TENANT, server_default=DEFAULT_TENANT)
    version     = Column(Integer,     nullable=False)        # 该学生的递增版本号 1,2,3...
    trigger     = Column(String(32),  nullable=False, default="resume_update")  # resume_update/manual_edit/periodic_review
    portrait_json = Column(Text,      nullable=False)        # 当时的完整画像（PII 加密存储）
    completeness_score    = Column(Float, nullable=True)
    competitiveness_score = Column(Float, nullable=True)
    created_at  = Column(DateTime,    nullable=False, default=datetime.utcnow)


class MatchSnapshot(Base):
    """人岗匹配快照（不可变）。每次匹配 append 一条，关联当时的画像版本以支持归因追溯。"""
    __tablename__ = "match_snapshots"
    __table_args__ = (
        Index("ix_ms_student_time", "student_id", "created_at"),
        Index("ix_ms_tenant", "tenant"),
    )

    id               = Column(String(64),  primary_key=True)   # match_snapshot_id (uuid)
    student_id       = Column(String(64),  nullable=False)
    tenant           = Column(String(64),  nullable=False,
                              default=DEFAULT_TENANT, server_default=DEFAULT_TENANT)
    portrait_version = Column(Integer,     nullable=True)      # 关联 PortraitSnapshot.version（基于哪版画像算）
    job_name         = Column(String(128), nullable=False)
    total_match      = Column(Float,       nullable=False)
    basic_match      = Column(Float,       nullable=False)
    skill_match      = Column(Float,       nullable=False)
    quality_match    = Column(Float,       nullable=False)
    potential_match  = Column(Float,       nullable=False)
    matched_skills   = Column(Text,        nullable=True)      # JSON list
    missing_skills   = Column(Text,        nullable=True)      # JSON list
    weight_used      = Column(Text,        nullable=True)      # JSON dict（红线/租户有效权重）
    eligible         = Column(Boolean,     nullable=False, default=True)
    veto_reason      = Column(Text,        nullable=True)
    created_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)


class ActionPlan(Base):
    """行动计划（独立实体，不再淹没在报告 JSON 里）。items_json 每项含 status/due_date/completed_at，
    支持学生侧勾选完成与逾期追踪，闭合"完成行动→重测→看到分数变化"的回路。"""
    __tablename__ = "action_plans"
    __table_args__ = (
        Index("ix_ap_student_status", "student_id", "status"),
        Index("ix_ap_tenant", "tenant"),
    )

    id               = Column(String(64), primary_key=True)   # plan_id (uuid)
    student_id       = Column(String(64), nullable=False)
    tenant           = Column(String(64), nullable=False,
                              default=DEFAULT_TENANT, server_default=DEFAULT_TENANT)
    portrait_version = Column(Integer,    nullable=True)       # 基于哪版画像生成
    job_name         = Column(String(128), nullable=True)     # 目标岗位（如有）
    items_json       = Column(Text,       nullable=False)      # [{"id","title","description","timeline","status","due_date","completed_at","milestones":[]}]
    status           = Column(String(16), nullable=False, default="active")  # active/completed/superseded
    created_at       = Column(DateTime,   nullable=False, default=datetime.utcnow)
    completed_at     = Column(DateTime,   nullable=True)
