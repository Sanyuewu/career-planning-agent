# -*- coding: utf-8 -*-
"""学生画像路由：/api/portrait/* 和 /api/stats/user/* 等"""
import logging
import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from app.cache import recommend_cache
from app.constants import DEGREE_COMPETITIVENESS_MAP, ELITE_SCHOOL_KEYWORDS
from app.db import get_db_session, student_crud, portrait_history_crud
from app.deps import get_current_user, audit_log
from app.schemas.api import PortraitResponse
from app.services.portrait_service import portrait_service
from app.services.resume_service import ResumeParseResult
from app.services.stats_service import stats_service
from app.services.market_service import market_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Portrait"])


@router.get("/api/portrait/{student_id}", response_model=PortraitResponse)
async def get_portrait(student_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        if current_user and current_user.get("role") != "admin":
            if current_user.get("student_id") != student_id:
                raise HTTPException(status_code=403, detail="无权限访问此学生数据")

        basic_info = dict(student.basic_info or {})
        phone = basic_info.get("phone", "")
        email = basic_info.get("email", "")
        if phone and len(phone) > 5:
            basic_info["phone"] = phone[:3] + "****" + phone[-2:]
        if email and "@" in email:
            parts = email.split("@")
            basic_info["email"] = parts[0][:2] + "****@" + parts[1]

        return PortraitResponse(
            student_id=student.student_id,
            basic_info=basic_info,
            education=student.education or [],
            skills=student.skills or [],
            internships=student.internships or [],
            projects=student.projects or [],
            certs=student.certs or [],
            awards=student.awards or [],
            career_intent=student.career_intent,
            inferred_soft_skills=student.inferred_soft_skills or {},
            completeness=student.completeness,
            competitiveness=student.competitiveness,
            competitiveness_level=student.competitiveness_level,
            highlights=student.highlights or [],
            weaknesses=student.weaknesses or [],
            interests=student.interests or [],
            ability_profile=student.ability_profile or {},
            personality_traits=student.personality_traits or [],
            preferred_cities=student.preferred_cities or [],
            culture_preference=student.culture_preference or [],
        )


@router.put("/api/portrait/{student_id}", response_model=PortraitResponse)
async def update_portrait(student_id: str, data: dict, current_user: Optional[dict] = Depends(get_current_user)):
    """更新或创建学生画像（支持 upsert，用于手动录入场景）"""
    if current_user and current_user.get("role") != "admin":
        if current_user.get("student_id") != student_id:
            raise HTTPException(status_code=403, detail="无权限修改此学生数据")

    _errors = []
    if "skills" in data and not isinstance(data["skills"], list):
        _errors.append("skills 必须为数组")
    if "education" in data:
        for _edu in (data["education"] or []):
            if not isinstance(_edu, dict):
                _errors.append("education 元素必须为对象")
                break
    if "internships" in data:
        for _intern in (data["internships"] or []):
            if not isinstance(_intern, dict):
                _errors.append("internships 元素必须为对象")
                break
            dm = _intern.get("duration_months")
            if dm is not None and (not isinstance(dm, (int, float)) or dm < 0):
                _errors.append("internships.duration_months 必须为非负数")
                break
    if "basic_info" in data and not isinstance(data.get("basic_info"), dict):
        _errors.append("basic_info 必须为对象")
    if _errors:
        raise HTTPException(status_code=422, detail="; ".join(_errors))

    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, student_id)

        if student is None:
            parse_result = ResumeParseResult(
                basic_info=data.get("basic_info", {}),
                education=data.get("education", []),
                skills=data.get("skills", []),
                internships=data.get("internships", []),
                projects=data.get("projects", []),
                certs=data.get("certs", []),
                awards=data.get("awards", []),
                career_intent=data.get("career_intent"),
                inferred_soft_skills=data.get("inferred_soft_skills", {}),
            )
            portrait = portrait_service.build_portrait(parse_result)
            full_data = {
                "student_id": student_id,
                "basic_info": portrait.basic_info,
                "education": portrait.education,
                "skills": portrait.skills,
                "internships": portrait.internships,
                "projects": portrait.projects,
                "certs": portrait.certs,
                "awards": portrait.awards,
                "career_intent": portrait.career_intent,
                "inferred_soft_skills": portrait.inferred_soft_skills,
                "completeness": portrait.completeness,
                "competitiveness": portrait.competitiveness,
                "competitiveness_level": portrait.competitiveness_level,
                "highlights": portrait.highlights,
                "weaknesses": portrait.weaknesses,
                "preferred_cities": data.get("preferred_cities", []),
                "culture_preference": data.get("culture_preference", []),
            }
            student = await student_crud.create(session, full_data)
            snapshot_reason = "手动录入建档"
        else:
            if "basic_info" in data and isinstance(data["basic_info"], dict):
                data["basic_info"] = {k: v for k, v in data["basic_info"].items() if v not in (None, "")}
            student = await student_crud.update(session, student_id, data)
            snapshot_reason = "用户更新画像"
            _parse = ResumeParseResult(
                basic_info=student.basic_info or {},
                education=student.education or [],
                skills=student.skills or [],
                internships=student.internships or [],
                projects=student.projects or [],
                certs=student.certs or [],
                awards=student.awards or [],
                career_intent=student.career_intent,
                inferred_soft_skills=student.inferred_soft_skills or {},
            )
            _portrait = portrait_service.build_portrait(_parse)
            student = await student_crud.update(session, student_id, {
                "completeness": _portrait.completeness,
                "competitiveness": _portrait.competitiveness,
                "competitiveness_level": _portrait.competitiveness_level,
                "highlights": _portrait.highlights,
                "weaknesses": _portrait.weaknesses,
                "interests": _portrait.interests,
                "ability_profile": _portrait.ability_profile,
                "personality_traits": _portrait.personality_traits,
                "transfer_opportunities": _portrait.transfer_opportunities,
                "gap_mapped_transfers": _portrait.gap_mapped_transfers,
            })
            # 清除该学生的推荐缓存
            for key in list(recommend_cache.keys()):
                if key.startswith(f"{student_id}_"):
                    del recommend_cache[key]

        try:
            await portrait_history_crud.create_snapshot(
                session,
                student_id=student_id,
                portrait={"basic_info": student.basic_info, "skills": student.skills, "education": student.education},
                completeness=student.completeness or 0.0,
                competitiveness=student.competitiveness or 0.0,
                snapshot_reason=snapshot_reason,
            )
        except Exception as _snap_err:
            logger.warning(f"画像历史快照写入失败（不影响主流程）: {_snap_err}")

        audit_log("UPDATE", "portrait", student_id, f"reason={snapshot_reason}")
        return PortraitResponse(
            student_id=student.student_id,
            basic_info=student.basic_info or {},
            education=student.education or [],
            skills=student.skills or [],
            internships=student.internships or [],
            projects=student.projects or [],
            certs=student.certs or [],
            awards=student.awards or [],
            career_intent=student.career_intent,
            inferred_soft_skills=student.inferred_soft_skills or {},
            completeness=student.completeness,
            competitiveness=student.competitiveness,
            competitiveness_level=student.competitiveness_level,
            highlights=student.highlights or [],
            weaknesses=student.weaknesses or [],
            interests=student.interests or [],
            ability_profile=student.ability_profile or {},
            personality_traits=student.personality_traits or [],
            preferred_cities=student.preferred_cities or [],
            culture_preference=student.culture_preference or [],
        )


@router.get("/api/portrait/{student_id}/history")
async def get_portrait_history(student_id: str, limit: int = 10, current_user: Optional[dict] = Depends(get_current_user)):
    """获取学生画像历史快照（成长轨迹）"""
    if current_user and current_user.get("role") != "admin":
        if current_user.get("student_id") != student_id:
            raise HTTPException(status_code=403, detail="无权限查看此学生历史")
    async with get_db_session() as session:
        history = await portrait_history_crud.get_history(session, student_id, limit=limit)
        return {
            "history": [
                {
                    "snapshot_id": h.snapshot_id,
                    "version": h.version,
                    "completeness": h.completeness,
                    "competitiveness": h.competitiveness,
                    "snapshot_reason": h.snapshot_reason,
                    "created_at": str(h.created_at),
                }
                for h in history
            ]
        }


@router.get("/api/stats/user/{student_id}")
async def get_user_stats(student_id: str):
    return await stats_service.get_user_stats(student_id)


@router.get("/api/portrait/{student_id}/skill_scores")
async def get_skill_scores(student_id: str):
    return await stats_service.get_skill_scores(student_id)


@router.get("/api/portrait/{student_id}/competitiveness_history")
async def get_competitiveness_history(student_id: str):
    return await stats_service.get_competitiveness_history(student_id)


@router.get("/api/portrait/{student_id}/score_detail")
async def get_portrait_score_detail(student_id: str):
    """获取画像完整度与竞争力分项明细"""
    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

    edu_list = student.education or []
    edu = edu_list[0] if edu_list else {}
    degree = edu.get("degree", "本科")
    school = edu.get("school") or ""
    basic_info = student.basic_info or {}
    skills = student.skills or []
    internships = student.internships or []
    projects = student.projects or []
    awards = student.awards or []
    certs = student.certs or []
    soft_skills = student.inferred_soft_skills or {}

    degree_base = DEGREE_COMPETITIVENESS_MAP.get(degree, 70)
    if any(kw in school for kw in ELITE_SCHOOL_KEYWORDS):
        school_note = "985/211/双一流加成 +20"
        school_bonus = 20
    elif "大学" in school or "学院" in school:
        school_note = "普通高校加成 +8"
        school_bonus = 8
    else:
        school_note = "无学校加成"
        school_bonus = 0
    edu_score = min(degree_base + school_bonus, 100)

    skill_count = len(skills)
    skill_score = min(math.log(skill_count + 1, 2) / math.log(16, 2) * 100, 100) if skill_count > 0 else 0

    intern_months = sum((i.get("duration_months") or 1) for i in internships)
    intern_score = min(intern_months / 12 * 70 + (20 if internships else 0), 100)
    project_count = len(projects)
    project_score = min(project_count / 4 * 100, 100)
    experience_score = intern_score * 0.6 + project_score * 0.4

    quality_score = min(len(awards) * 15 + len(certs) * 10, 100)

    soft_vals = [v.get("score", 1) for v in soft_skills.values() if v and v.get("score") is not None]
    soft_score = min(max((sum(soft_vals) / len(soft_vals) * 10) if soft_vals else 50, 0), 100)

    comp_total = round(min(edu_score * 0.25 + skill_score * 0.30 + experience_score * 0.25
                           + quality_score * 0.15 + soft_score * 0.05, 100), 1)

    basic_fields = {"姓名": basic_info.get("name"), "学校": basic_info.get("school"),
                    "专业": basic_info.get("major"), "年级": basic_info.get("grade")}
    basic_filled = sum(1 for v in basic_fields.values() if v)
    missing_basic = [k for k, v in basic_fields.items() if not v]

    return {
        "student_id": student_id,
        "competitiveness_breakdown": [
            {"dimension": "学历背景", "score": round(edu_score), "weight": 0.25,
             "detail": f"{degree}（{school or '未填写'}）{school_note}，基础分 {degree_base}"},
            {"dimension": "专业技能深度", "score": round(skill_score), "weight": 0.30,
             "detail": f"{skill_count} 项技能（满分需16项）"},
            {"dimension": "实践经验", "score": round(experience_score), "weight": 0.25,
             "detail": f"实习 {intern_months} 个月（{round(intern_score)}分）× 60% + {project_count} 个项目（{round(project_score)}分）× 40%"},
            {"dimension": "综合素质", "score": round(quality_score), "weight": 0.15,
             "detail": f"{len(awards)} 项奖项（×15分）+ {len(certs)} 项证书（×10分）"},
            {"dimension": "软技能", "score": round(soft_score), "weight": 0.05,
             "detail": f"均分 {round(soft_score)}分（{'有推断数据' if soft_vals else '无数据取中立分50'})"},
        ],
        "competitiveness_total": comp_total,
        "completeness_breakdown": [
            {"dimension": "基本信息", "score": round(basic_filled / 4 * 100), "weight": 0.30,
             "detail": f"已填 {basic_filled}/4 项" + (f"，缺：{'/'.join(missing_basic)}" if missing_basic else "，完整")},
            {"dimension": "技能标签", "score": min(skill_count * 10, 100), "weight": 0.20,
             "detail": f"{skill_count} 项（≥10项满分）"},
            {"dimension": "教育经历", "score": 100 if edu_list else 0, "weight": 0.15,
             "detail": f"{'已填写' if edu_list else '未填写'} {len(edu_list)} 条"},
            {"dimension": "实习经历", "score": round(min(intern_months / 6 * 100, 100)), "weight": 0.15,
             "detail": f"{len(internships)} 段，共 {intern_months} 个月（≥6个月满分）"},
            {"dimension": "项目经历", "score": min(project_count * 25, 100), "weight": 0.15,
             "detail": f"{project_count} 个项目（≥4个满分）"},
            {"dimension": "证书/奖项", "score": round(quality_score), "weight": 0.05,
             "detail": f"{len(certs)} 项证书 + {len(awards)} 项奖项"},
        ],
    }


@router.get("/api/user/{student_id}/achievements")
async def get_achievements(student_id: str):
    return {"achievements": await stats_service.get_achievements(student_id)}


@router.get("/api/recommend/learning_resources/{student_id}")
async def get_learning_resources(student_id: str, skills: str = None):
    skill_gaps = skills.split(",") if skills else None
    return await market_service.get_learning_resources(student_id, skill_gaps)
