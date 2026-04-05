# -*- coding: utf-8 -*-
"""
API 请求/响应 Pydantic 模型
从 main.py 提取，供路由层统一引用
"""
from datetime import datetime
from typing import Generic, TypeVar, Optional, List

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── 通用响应 ──────────────────────────────────────────────

class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = True
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    success: bool = True
    code: int = 200
    message: str = "success"
    data: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10


# ── 认证 ──────────────────────────────────────────────────

class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    student_id: Optional[str] = None
    role: str = "student"


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 86400  # 24小时
    student_id: Optional[str] = None
    username: str
    role: str = "student"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ── 画像 ──────────────────────────────────────────────────

class PortraitResponse(BaseModel):
    student_id: str
    basic_info: dict
    education: List[dict]
    skills: List[str]
    internships: List[dict]
    projects: List[dict]
    certs: List[str]
    awards: List[str]
    career_intent: Optional[str]
    inferred_soft_skills: dict
    completeness: float
    competitiveness: float
    competitiveness_level: str
    highlights: List[str]
    weaknesses: List[str]
    interests: List[str] = []
    ability_profile: dict = {}
    personality_traits: List[str] = []
    preferred_cities: List[str] = []
    culture_preference: List[str] = []


# ── 匹配 ──────────────────────────────────────────────────

class MatchRequest(BaseModel):
    student_id: str
    job_name: str
    weight_preset: Optional[str] = "default"


class MatchResponse(BaseModel):
    job_id: str
    job_title: str
    overall_score: float
    confidence: float
    dimensions: dict
    gap_skills: Optional[List[dict]] = None
    matched_skills: Optional[List[str]] = None
    weight_used: dict
    summary: str
    is_degraded: bool = False
    market_demand: Optional[dict] = None
    job_context: dict = Field(default_factory=dict)
    competitive_context: str = ""
    explanation_tree: List[dict] = Field(default_factory=list)
    transfer_paths: List[dict] = Field(default_factory=list)
    confidence_breakdown: dict = Field(default_factory=dict)
    skill_match_details: List[dict] = Field(default_factory=list)
    gap_analysis: List[dict] = Field(default_factory=list)


class BatchMatchRequest(BaseModel):
    student_id: str
    job_names: List[str]


# ── 对话 ──────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    state: Optional[str]
    emotion: Optional[str]
    timestamp: str


# ── 报告 ──────────────────────────────────────────────────

class ReportUpdateRequest(BaseModel):
    action_plan: Optional[List[dict]] = None
    skill_gaps: Optional[List[dict]] = None
    career_path: Optional[List[dict]] = None


class ReportAdjustRequest(BaseModel):
    feedback_summary: str = ""
    focus_chapters: List[str] = []


class PolishRequest(BaseModel):
    chapter_titles: List[str] = []
    feedback_hint: str = ""


class FeedbackOptimizeRequest(BaseModel):
    rating: int = 3
    issues: List[str] = []
    comment: str = ""
    chapters: Optional[List[str]] = None


# ── 岗位 ──────────────────────────────────────────────────

class JobInfoResponse(BaseModel):
    title: str
    salary: Optional[str] = None
    industry: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    skills: List[str] = []
    overview: Optional[str] = None
    responsibilities: List[str] = []
    demand_level: Optional[str] = None
    top_regions: List[str] = []
    culture_types: List[str] = []
    majors: List[str] = []
    tags: List[str] = []


class CareerPathResponse(BaseModel):
    promotion_paths: List[dict] = []
    transfer_paths: List[dict] = []


# ── 反馈 ──────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    student_id: Optional[str] = None
    target_type: str
    target_id: str
    rating: int
    comment: Optional[str] = None
