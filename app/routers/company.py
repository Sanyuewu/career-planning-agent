# -*- coding: utf-8 -*-
"""企业端路由：/api/company/*"""
import logging
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select as sa_select

from app.db import get_db_session
from app.deps import require_role
from app.constants import DEGREE_MAP
from app.graph.job_graph_repo import job_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/company", tags=["Company"])


# ── Pydantic 模型 ─────────────────────────────────────────────────────────────

class CompanyProfile(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None


class PostedJobCreate(BaseModel):
    title: str
    salary: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    skills: List[str] = []
    description: Optional[str] = None


class ReverseMatchRequest(BaseModel):
    job_name: str
    required_skills: List[str] = []
    min_score: int = 60
    degree: Optional[str] = None


# ── 企业档案 ──────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_company_profile(payload: dict = Depends(require_role("company", "admin"))):
    from app.db.models import CompanyModel
    username = payload.get("sub")
    async with get_db_session() as session:
        company = (await session.execute(
            sa_select(CompanyModel).where(CompanyModel.username == username)
        )).scalar_one_or_none()
        if company:
            return {"company_name": company.company_name, "industry": company.industry,
                    "size": company.size, "description": company.description,
                    "contact_email": company.contact_email}
    return {"company_name": "", "industry": "", "size": "", "description": "", "contact_email": ""}


@router.put("/profile")
async def update_company_profile(data: CompanyProfile, payload: dict = Depends(require_role("company", "admin"))):
    from app.db.models import CompanyModel
    username = payload.get("sub")
    async with get_db_session() as session:
        company = (await session.execute(
            sa_select(CompanyModel).where(CompanyModel.username == username)
        )).scalar_one_or_none()
        if not company:
            company = CompanyModel(username=username)
            session.add(company)
        company.company_name = data.company_name
        company.industry     = data.industry
        company.size         = data.size
        company.description  = data.description
        company.contact_email = data.contact_email
    return {"ok": True}


# ── 岗位管理 ──────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def get_company_jobs(payload: dict = Depends(require_role("company", "admin"))):
    from app.db.models import PostedJobModel
    username = payload.get("sub")
    async with get_db_session() as session:
        jobs = (await session.execute(
            sa_select(PostedJobModel)
            .where(PostedJobModel.company_username == username)
            .order_by(PostedJobModel.created_at.desc())
        )).scalars().all()
    return [{"id": str(j.id), "title": j.title, "salary": j.salary, "location": j.location,
             "experience": j.experience, "education": j.education, "skills": j.skills or [],
             "description": j.description, "status": j.status or "active",
             "view_count": j.view_count or 0, "apply_count": j.apply_count or 0} for j in jobs]


@router.post("/jobs")
async def create_company_job(data: PostedJobCreate, payload: dict = Depends(require_role("company"))):
    from app.db.models import PostedJobModel
    username = payload.get("sub")
    async with get_db_session() as session:
        job = PostedJobModel(
            id=str(uuid.uuid4()), company_username=username,
            title=data.title, salary=data.salary, location=data.location,
            experience=data.experience, education=data.education,
            skills=data.skills, description=data.description,
            status="active", view_count=0, apply_count=0,
        )
        session.add(job)
    return {"ok": True, "id": job.id}


@router.put("/jobs/{job_id}")
async def update_company_job(job_id: str, data: PostedJobCreate, payload: dict = Depends(require_role("company"))):
    from app.db.models import PostedJobModel
    username = payload.get("sub")
    async with get_db_session() as session:
        job = (await session.execute(
            sa_select(PostedJobModel).where(PostedJobModel.id == job_id, PostedJobModel.company_username == username)
        )).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="岗位不存在")
        job.title = data.title; job.salary = data.salary; job.location = data.location
        job.experience = data.experience; job.education = data.education
        job.skills = data.skills; job.description = data.description
    return {"ok": True}


@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, data: dict, payload: dict = Depends(require_role("company"))):
    from app.db.models import PostedJobModel
    username = payload.get("sub")
    new_status = data.get("status", "active")
    async with get_db_session() as session:
        job = (await session.execute(
            sa_select(PostedJobModel).where(PostedJobModel.id == job_id, PostedJobModel.company_username == username)
        )).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="岗位不存在")
        job.status = new_status
    return {"ok": True, "status": new_status}


# ── 反向匹配 & 收藏 ───────────────────────────────────────────────────────────

@router.post("/reverse_match")
async def company_reverse_match(data: ReverseMatchRequest, payload: dict = Depends(require_role("company", "admin"))):
    from app.db.models import StudentModel
    async with get_db_session() as session:
        students = (await session.execute(
            sa_select(StudentModel).where(StudentModel.completeness >= 0.5).limit(200)
        )).scalars().all()

    required_degree_score = DEGREE_MAP.get(data.degree, 0) if data.degree else 0
    candidates = []
    for s in students:
        if required_degree_score > 0:
            edu_list = s.education or []
            student_degree = (edu_list[-1] if edu_list else {}).get("degree", "")
            if DEGREE_MAP.get(student_degree, 0) < required_degree_score:
                continue
        job_info = job_graph.get_job_info(data.job_name) or {}
        all_required = set(job_info.get("skills", []) or []) | set(data.required_skills)
        student_skills = set(s.skills or [])
        matched = student_skills & all_required
        score = int(len(matched) / len(all_required) * 100) if all_required else 50
        if score >= data.min_score:
            basic = s.basic_info or {}
            edu = s.education or []
            candidates.append({
                "student_id": s.student_id, "name": basic.get("name", ""),
                "degree": edu[0].get("degree", "") if edu else "",
                "major":  edu[0].get("major", "")  if edu else "",
                "skills": list(student_skills)[:10],
                "internship_months": sum((i.get("months") or 0) for i in (s.internships or [])),
                "competitiveness_level": s.competitiveness_level or "一般",
                "score": score,
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"candidates": candidates[:20]}


@router.get("/saved_candidates")
async def get_saved_candidates(payload: dict = Depends(require_role("company"))):
    from app.db.models import SavedCandidateModel, StudentModel
    username = payload.get("sub")
    async with get_db_session() as session:
        rows = (await session.execute(
            sa_select(SavedCandidateModel, StudentModel)
            .join(StudentModel, SavedCandidateModel.student_id == StudentModel.student_id, isouter=True)
            .where(SavedCandidateModel.company_username == username)
            .order_by(SavedCandidateModel.created_at.desc())
        )).all()
    candidates = []
    for saved, student in rows:
        if student:
            basic = student.basic_info or {}
            edu = student.education or []
            candidates.append({
                "student_id": saved.student_id, "name": basic.get("name", ""),
                "degree": edu[0].get("degree", "") if edu else "",
                "major":  edu[0].get("major", "")  if edu else "",
                "skills": (student.skills or [])[:10],
                "competitiveness_level": student.competitiveness_level or "一般",
                "score": saved.match_score or 0, "matched_job": saved.matched_job,
            })
    return candidates


@router.post("/saved_candidates")
async def save_candidate(data: dict, payload: dict = Depends(require_role("company"))):
    from app.db.models import SavedCandidateModel
    username = payload.get("sub")
    student_id = data.get("student_id")
    async with get_db_session() as session:
        existing = (await session.execute(
            sa_select(SavedCandidateModel).where(
                SavedCandidateModel.company_username == username,
                SavedCandidateModel.student_id == student_id,
            )
        )).scalar_one_or_none()
        if existing:
            return {"ok": True, "message": "已收藏"}
        session.add(SavedCandidateModel(
            company_username=username, student_id=student_id,
            matched_job=data.get("matched_job", ""),
        ))
    return {"ok": True}


@router.delete("/saved_candidates/{student_id}")
async def remove_saved_candidate(student_id: str, payload: dict = Depends(require_role("company"))):
    from app.db.models import SavedCandidateModel
    username = payload.get("sub")
    async with get_db_session() as session:
        saved = (await session.execute(
            sa_select(SavedCandidateModel).where(
                SavedCandidateModel.company_username == username,
                SavedCandidateModel.student_id == student_id,
            )
        )).scalar_one_or_none()
        if saved:
            await session.delete(saved)
    return {"ok": True}


@router.get("/market_stats")
async def company_market_stats(job_name: str, payload: dict = Depends(require_role("company", "admin"))):
    from app.db.crud.job_real_crud import JobRealCRUD
    async with get_db_session() as session:
        return await JobRealCRUD.get_stats_by_job_name(session, job_name)
