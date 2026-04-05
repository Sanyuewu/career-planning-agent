# -*- coding: utf-8 -*-
"""能力测评路由：/api/assessment/*"""
import logging
from typing import Optional, List, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import get_db_session, student_crud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assessment", tags=["Assessment"])


class AssessmentSubmitRequest(BaseModel):
    student_id: Optional[str] = None
    answers: List[Dict] = []
    job_hint: str = ""


@router.get("/questions")
async def get_assessment_questions(job_hint: str = ""):
    """获取测评题目（三套：逻辑推理 + 职业倾向 + 技术自评）"""
    from app.data.assessment_questions import (
        LOGIC_QUESTIONS, CAREER_TENDENCY_QUESTIONS, get_questions_for_job,
    )
    return {
        "logic": LOGIC_QUESTIONS,
        "career_tendency": CAREER_TENDENCY_QUESTIONS,
        "tech_self_assessment": get_questions_for_job(job_hint),
        "tech_job_hint": job_hint or "后端开发（默认）",
    }


@router.post("/submit")
async def submit_assessment(req: AssessmentSubmitRequest):
    """提交测评答案，返回得分 + 自动合并 ability_profile（权重 0.4×测评 + 0.6×原值）"""
    from app.data.assessment_questions import calculate_assessment_score
    result = calculate_assessment_score(req.answers, req.job_hint)

    if req.student_id:
        try:
            async with get_db_session() as session:
                student = await student_crud.get_by_student_id(session, req.student_id)
                if student:
                    old_profile = student.ability_profile or {}
                    update = result.get("ability_profile_update", {})
                    merged = {dim: round(old_profile.get(dim, 50.0) * 0.6 + new_val, 1)
                              for dim, new_val in update.items()}
                    for dim, val in old_profile.items():
                        if dim not in merged:
                            merged[dim] = val
                    await student_crud.update(session, req.student_id, {"ability_profile": merged})
                    result["profile_updated"] = True
                    result["merged_ability_profile"] = merged

                    # D-4: 双写测评结果到独立表
                    from app.db.crud.assessment_result_crud import assessment_result_crud
                    total = result.get("overall_score") or result.get("total_score") or 0
                    label = result.get("result_label") or result.get("career_type") or ""
                    await assessment_result_crud.create(
                        session,
                        student_id=req.student_id,
                        assessment_type=result.get("assessment_type", "mixed"),
                        job_hint=req.job_hint,
                        scores=result.get("scores") or result.get("details") or {},
                        total_score=float(total),
                        result_label=str(label),
                    )
        except Exception as e:
            logger.warning("assessment update ability_profile failed: %s", e)
            result["profile_updated"] = False

    return result
