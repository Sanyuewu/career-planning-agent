# -*- coding: utf-8 -*-
"""
数据库模型定义
遵循v5规范：使用SQLAlchemy异步ORM
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class StudentModel(Base):
    """学生模型"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100))
    school = Column(String(200))
    major = Column(String(200))
    grade = Column(String(50))
    phone = Column(String(20))
    email = Column(String(200))
    
    basic_info = Column(JSON, default=dict)
    education = Column(JSON, default=list)
    skills = Column(JSON, default=list)
    internships = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    certs = Column(JSON, default=list)
    awards = Column(JSON, default=list)
    career_intent = Column(String(500))
    preferred_cities = Column(JSON, default=list)      # 期望工作城市
    culture_preference = Column(JSON, default=list)    # 偏好企业文化
    inferred_soft_skills = Column(JSON, default=dict)
    
    completeness = Column(Float, default=0.0)
    competitiveness = Column(Float, default=0.0)
    competitiveness_level = Column(String(20), default="一般")
    highlights = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    transfer_opportunities = Column(JSON, default=list)   # 换岗机会
    gap_mapped_transfers = Column(JSON, default=list)     # 个性化gap匹配换岗
    # 多维画像扩展
    interests = Column(JSON, default=list)               # 兴趣领域（从简历推断）
    ability_profile = Column(JSON, default=dict)         # 7维能力雷达图数据
    personality_traits = Column(JSON, default=list)      # 性格特征标签
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    match_results = relationship("MatchResultModel", back_populates="student")
    reports = relationship("ReportModel", back_populates="student")
    chat_sessions = relationship("ChatSessionModel", back_populates="student")


class MatchResultModel(Base):
    """匹配结果模型"""
    __tablename__ = "match_results"
    __table_args__ = (
        Index("idx_match_student_created", "student_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    job_name = Column(String(200), nullable=False)
    
    overall_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    dimensions = Column(JSON, default=dict)
    weight_used = Column(JSON, default=dict)
    summary = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("StudentModel", back_populates="match_results")


class ReportModel(Base):
    """报告模型"""
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_report_student_job", "student_id", "job_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    job_name = Column(String(200), nullable=False)
    
    overall_score = Column(Float, default=0.0)
    dimensions = Column(JSON, default=dict)
    action_plan = Column(JSON, default=list)
    skill_gaps = Column(JSON, default=list)
    career_path = Column(JSON, default=list)
    
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    chapters_json = Column(JSON, nullable=True)   # 存储全部6章原始内容（title/type/content/action_items）
    extra_data = Column(JSON, nullable=True)       # 润色快照等扩展数据

    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("StudentModel", back_populates="reports")


class ChatSessionModel(Base):
    """对话会话模型"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"))
    
    state = Column(String(50), default="GREETING")
    messages = Column(JSON, default=list)
    emotion_history = Column(JSON, default=list)
    current_emotion = Column(String(50))
    emotion_score = Column(Float, default=1.0)
    turn_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship("StudentModel", back_populates="chat_sessions")


class PortraitHistoryModel(Base):
    """画像历史快照模型"""
    __tablename__ = "portrait_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False)
    version = Column(Integer, default=1)
    
    portrait = Column(JSON, default=dict)
    completeness = Column(Float, default=0.0)
    competitiveness = Column(Float, default=0.0)
    snapshot_reason = Column(String(200))
    diff_summary = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    """注册用户模型（持久化，替代内存_user_store）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    student_id = Column(String(64), nullable=False)
    role = Column(String(20), default="student")
    created_at = Column(DateTime, default=datetime.utcnow)


class JobTrendSnapshotModel(Base):
    """岗位趋势快照模型"""
    __tablename__ = "job_trend_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_code = Column(String(100), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False)

    jd_count = Column(Integer, default=0)
    avg_salary = Column(Integer, default=0)
    demand_index = Column(Float, default=0.0)
    top_skills = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)


class JobRealModel(Base):
    """真实招聘数据模型（来自市场9958条JD）"""
    __tablename__ = "job_real"
    __table_args__ = (
        Index("idx_job_real_job_name", "job_name"),
        Index("idx_job_real_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, default=0)          # 对应图谱岗位ID，0=未匹配
    job_name = Column(String(200), nullable=False)
    salary = Column(String(200), default="")
    company_name = Column(String(500), default="")
    address = Column(String(500), default="")
    size = Column(String(100), default="")
    industry = Column(String(200), default="")   # 所属行业（来自XLS真实数据）
    description = Column(Text, default="")
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class LiveJobModel(Base):
    """实时抓取岗位数据（与历史 job_real 分离，保持数据来源可溯）"""
    __tablename__ = "live_jobs"
    __table_args__ = (
        Index("idx_live_jobs_job_name", "job_name"),
        Index("idx_live_jobs_fetched_at", "fetched_at"),
        Index("idx_live_jobs_source", "source"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(200), nullable=False)       # 标准化岗位名（对应图谱）
    raw_title = Column(String(300), default="")          # 原始抓取标题
    company = Column(String(300), default="")
    city = Column(String(100), default="")
    salary_raw = Column(String(100), default="")         # 原始薪资字符串
    salary_min_k = Column(Float, default=0.0)            # 月薪下限（千元）
    salary_max_k = Column(Float, default=0.0)            # 月薪上限（千元）
    skills = Column(JSON, default=list)                  # 解析出的技能标签列表
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    source = Column(String(50), default="")              # 数据来源标识
    source_url = Column(String(500), default="")
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Integer, default=1)               # 0=已过期(>7天)，1=有效

    created_at = Column(DateTime, default=datetime.utcnow)


class CompanyModel(Base):
    """企业用户档案模型"""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, index=True)   # 关联 UserModel.username
    company_name = Column(String(200), default="")
    industry = Column(String(100), default="")
    size = Column(String(50), default="")
    description = Column(Text, default="")
    contact_email = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostedJobModel(Base):
    """企业发布的岗位模型"""
    __tablename__ = "posted_jobs"

    id = Column(String(64), primary_key=True)
    company_username = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    salary = Column(String(100), default="")
    location = Column(String(100), default="")
    experience = Column(String(100), default="")
    education = Column(String(100), default="")
    skills = Column(JSON, default=list)
    description = Column(Text, default="")
    status = Column(String(20), default="active")  # active/inactive
    view_count = Column(Integer, default=0)
    apply_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SavedCandidateModel(Base):
    """企业收藏的候选人模型"""
    __tablename__ = "saved_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_username = Column(String(100), nullable=False, index=True)
    student_id = Column(String(64), nullable=False, index=True)
    matched_job = Column(String(200), default="")
    match_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_saved_candidates_company_student", "company_username", "student_id", unique=True),
    )


class UserMemoryModel(Base):
    """用户跨会话长期记忆（A-4）"""
    __tablename__ = "user_memories"
    __table_args__ = (
        Index("idx_user_memories_student", "student_id"),
        Index("idx_user_memories_key", "student_id", "memory_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(64), nullable=False, index=True)
    memory_key = Column(String(100), nullable=False)   # 记忆类型: career_goal/worry/strength/preference
    memory_value = Column(Text, nullable=False)         # 记忆内容
    source_session = Column(String(64), nullable=True)  # 来源会话ID
    confidence = Column(Float, default=1.0)             # 置信度（0-1）
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeedbackModel(Base):
    """用户满意度反馈模型"""
    __tablename__ = "feedbacks"
    __table_args__ = (
        Index("idx_feedback_target", "target_type", "target_id"),
        Index("idx_feedback_student", "student_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(64), nullable=True, index=True)        # 匿名允许
    target_type = Column(String(20), nullable=False)      # "match" | "report"
    target_id = Column(String(64), nullable=False)        # result_id 或 report_id
    rating = Column(Integer, nullable=False)              # 1=有帮助  0=没帮助
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# D-1: 技能独立表（替代 job_skills_extended.py 硬编码字典）
# ──────────────────────────────────────────────────────────────────────
class SkillModel(Base):
    """技能库模型（D-1）"""
    __tablename__ = "skills"
    __table_args__ = (
        Index("idx_skills_name", "name"),
        Index("idx_skills_category", "category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    aliases = Column(JSON, default=list)          # 同义词列表
    category = Column(String(50), default="")     # 技能分类: programming/database/frontend/...
    parent_skill = Column(String(100), nullable=True)   # 父技能（如 Spring → Java）
    popularity = Column(Integer, default=0)       # 热度分（0-100）
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# D-2: 学习资源独立表（替代 tools/__init__.py 硬编码）
# ──────────────────────────────────────────────────────────────────────
class LearningResourceModel(Base):
    """学习资源库模型（D-2）"""
    __tablename__ = "learning_resources"
    __table_args__ = (
        Index("idx_lr_skill", "skill"),
        Index("idx_lr_type", "resource_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(30), default="课程")  # 课程/书籍/文档/视频/练习
    title = Column(String(300), nullable=False)
    url = Column(String(500), default="")
    estimated_hours = Column(Integer, default=0)   # 预计学习时长（小时）
    difficulty = Column(String(20), default="入门")  # 入门/中级/高级
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# D-3: 行业数据持久化（替代 industry_insights.py 硬编码）
# ──────────────────────────────────────────────────────────────────────
class IndustryInsightModel(Base):
    """行业洞察持久化模型（D-3）"""
    __tablename__ = "industry_insights_db"
    __table_args__ = (
        Index("idx_ii_industry", "industry"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry = Column(String(100), unique=True, nullable=False, index=True)
    growth_rate = Column(String(50), default="")       # 如 "12%"
    hot_skills = Column(JSON, default=list)
    hiring_seasons = Column(JSON, default=list)
    competitive_ratio = Column(String(50), default="")  # 如 "1:15"
    avg_salary_k = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# D-4: 测评结果持久化（与 students.ability_profile 双写，支持统计分析）
# ──────────────────────────────────────────────────────────────────────
class AssessmentResultModel(Base):
    """测评结果持久化模型（D-4）"""
    __tablename__ = "assessment_results"
    __table_args__ = (
        Index("idx_ar_student", "student_id"),
        Index("idx_ar_type", "assessment_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    assessment_type = Column(String(30), nullable=False)  # logic/career_tendency/tech_self
    job_hint = Column(String(100), default="")
    scores = Column(JSON, default=dict)        # 详细分项分数
    total_score = Column(Float, default=0.0)
    result_label = Column(String(100), default="")   # 综合结论标签
    submitted_at = Column(DateTime, default=datetime.utcnow)
