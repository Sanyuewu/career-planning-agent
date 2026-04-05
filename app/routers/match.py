# -*- coding: utf-8 -*-
"""人岗匹配路由：/api/match/* 和 /api/jobs/*"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from sqlalchemy import select as sa_select, func as sql_func

from app.cache import recommend_cache, ai_insight_cache
from app.db import get_db_session, student_crud, match_result_crud, job_trend_crud
from app.db.models import JobRealModel
from app.deps import get_current_user
from app.graph.job_graph_repo import job_graph
from app.rate_limit import limiter
from app.schemas.api import MatchRequest, MatchResponse, BatchMatchRequest, JobInfoResponse, CareerPathResponse
from app.services.match_service import match_service, MatchResult

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Match"])


@router.post("/api/match/compute", response_model=MatchResponse)
@limiter.limit("20/minute")
async def compute_match(request: Request, body: MatchRequest, current_user: Optional[dict] = Depends(get_current_user)):
    if current_user and current_user.get("role") != "admin":
        if current_user.get("student_id") != body.student_id:
            raise HTTPException(status_code=403, detail="无权限为此学生计算匹配")

    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, body.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        _soft = student.inferred_soft_skills or {}
        _null_count = sum(1 for v in _soft.values() if not v or v.get("score") is None)
        portrait = {
            "basic_info": student.basic_info or {},
            "education": student.education or [],
            "skills": student.skills or [],
            "internships": student.internships or [],
            "projects": student.projects or [],
            "certs": student.certs or [],
            "awards": student.awards or [],
            "career_intent": student.career_intent,
            "inferred_soft_skills": _soft,
            "completeness": student.completeness,
            "soft_skills_null_count": _null_count,
            "preferred_cities": student.preferred_cities or [],
            "culture_preference": student.culture_preference or [],
        }

    async with get_db_session() as match_session:
        result = await match_service.compute_match(
            portrait, body.job_name, db_session=match_session,
            weight_preset=body.weight_preset or "default"
        )

    async with get_db_session() as session:
        await match_result_crud.upsert(
            session,
            student_id=body.student_id,
            job_name=body.job_name,
            result_data={
                "overall_score": result.overall_score,
                "confidence": result.confidence,
                "dimensions": result.dimensions.model_dump(),
                "weight_used": result.weight_used,
                "summary": result.summary,
            }
        )
        try:
            from app.db.crud.job_real_crud import JobRealCRUD
            all_results = await match_result_crud.get_by_student(session, body.student_id, limit=1000)
            job_match_count = sum(1 for r in all_results if r.job_name == body.job_name)
            md = result.dimensions.market_demand
            real_jd_count = md.jd_count if md else 0
            real_avg_salary = int((md.avg_salary_k or 0) * 1000) if md else 0
            demand_index = JobRealCRUD.calc_demand_index(real_jd_count, job_match_count)
            await job_trend_crud.create_snapshot(
                session,
                job_code=body.job_name,
                snapshot_date=datetime.utcnow(),
                jd_count=real_jd_count if real_jd_count > 0 else job_match_count,
                avg_salary=real_avg_salary,
                demand_index=demand_index,
                top_skills=result.dimensions.professional_skills.matched_skills[:5],
            )
        except Exception as _trend_err:
            logger.warning(f"岗位趋势写入失败: {_trend_err}")

    return MatchResponse(
        job_id=result.job_id,
        job_title=result.job_title,
        overall_score=result.overall_score,
        confidence=result.confidence,
        dimensions=result.dimensions.model_dump(),
        gap_skills=[g.model_dump() for g in result.dimensions.professional_skills.gap_skills] if result.dimensions.professional_skills.gap_skills else [],
        matched_skills=result.dimensions.professional_skills.matched_skills or [],
        weight_used=result.weight_used,
        summary=result.summary,
        is_degraded=result.is_degraded,
        market_demand=result.dimensions.market_demand.model_dump() if result.dimensions.market_demand else None,
        job_context=result.job_context or {},
        competitive_context=result.competitive_context or "",
        explanation_tree=result.explanation_tree or [],
        transfer_paths=[t.model_dump() for t in result.transfer_paths] if result.transfer_paths else [],
        confidence_breakdown=result.confidence_breakdown or {},
        skill_match_details=result.skill_match_details or [],
        gap_analysis=result.gap_analysis or [],
    )


@router.get("/api/jobs/search")
async def search_jobs(query: str, limit: int = 10):
    return job_graph.search_jobs(query, limit)


@router.get("/api/jobs/info", response_model=JobInfoResponse)
async def get_job_info(job: str = Query(..., description="岗位名称")):
    info = job_graph.get_job_info(job)
    if not info:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return JobInfoResponse(
        title=info.get("title", job),
        salary=info.get("salary"),
        industry=info.get("industry"),
        education=info.get("education"),
        experience=info.get("experience"),
        skills=info.get("skills", []),
        overview=info.get("overview"),
        responsibilities=info.get("responsibilities", []),
        demand_level=info.get("demand_level"),
        top_regions=info.get("top_regions", []),
        culture_types=info.get("culture_types", []),
        majors=info.get("majors", []),
        tags=info.get("tags", []),
    )


@router.get("/api/jobs/ai_insight")
async def get_job_ai_insight(job_name: str = Query(..., description="岗位名称")):
    """AI 岗位洞察（LLM 实时生成，进程级缓存）"""
    if job_name in ai_insight_cache:
        return ai_insight_cache[job_name]

    info = job_graph.get_job_info(job_name)
    if not info:
        raise HTTPException(status_code=404, detail="岗位不存在")

    skills_str = "、".join((info.get("skills") or [])[:8])
    salary = info.get("salary", "待定")
    industry = info.get("industry", "IT")

    prompt = (
        f'你是职业规划专家。请对【{job_name}】岗位生成一段AI洞察（100-150字），'
        f'必须包含：①当前市场需求热度 ②3条核心竞争力要求 ③入门路径建议。'
        f'参考信息：行业={industry}，薪资={salary}，核心技能={skills_str}。'
        f'用简洁的中文段落输出，不要用标题或列表格式，直接输出洞察内容。'
    )
    try:
        from app.ai.llm_client import llm_client as _llm
        insight_text = await _llm.chat(prompt, max_tokens=300)
    except Exception as e:
        logger.warning("AI岗位洞察生成失败: %s job=%s", e, job_name)
        try:
            from app.services.rag_service import search_knowledge_base
            kb_hits = search_knowledge_base(job_name, top_k=1)
            if kb_hits:
                kb = kb_hits[0]
                insight_text = f"{kb.get('description', '')} {kb.get('market_outlook', '')} {kb.get('entry_advice', '')}".strip()
            else:
                raise ValueError("no kb hit")
        except Exception:
            insight_text = f"{job_name}是当前{industry}领域的核心岗位，需要掌握{skills_str[:40]}等技能。建议结合实际项目积累经验，逐步提升至生产级开发能力。"

    result = {
        "job_name": job_name,
        "insight": insight_text,
        "core_skills": (info.get("skills") or [])[:5],
        "salary": salary,
        "industry": industry,
        "generated_by": "AI",
    }
    ai_insight_cache[job_name] = result
    return result


@router.get("/api/jobs/career-graph", response_model=CareerPathResponse)
async def get_job_career_graph(job: str = Query(..., description="岗位名称")):
    paths = job_graph.get_career_paths(job)
    return CareerPathResponse(
        promotion_paths=paths.get("promotion_paths", []),
        transfer_paths=paths.get("transfer_paths", []),
    )


@router.get("/api/jobs/real")
async def get_job_real_data(job: str = Query(..., description="岗位名称"), limit: int = 10):
    from app.db.crud.job_real_crud import JobRealCRUD
    async with get_db_session() as session:
        jobs = await JobRealCRUD().get_samples(session, job, min(limit, 50))
        stats = await JobRealCRUD().get_stats_by_job_name(session, job)
    return {"job": job, "jd_count": stats.get("count", 0), "avg_salary_k": stats.get("avg_salary_k"), "jobs": jobs}


@router.get("/api/jobs/live")
async def get_live_jobs(
    job_name: Optional[str] = None,
    city: Optional[str] = None,
    salary_min_k: Optional[float] = None,
    limit: int = 20,
    offset: int = 0,
):
    from app.db.crud.live_job_crud import LiveJobCRUD
    async with get_db_session() as session:
        jobs = await LiveJobCRUD.query(session, job_name=job_name, city=city, salary_min_k=salary_min_k, limit=limit, offset=offset)
        count = await LiveJobCRUD.count_active(session)
    return {"jobs": jobs, "count": count, "offset": offset}


@router.get("/api/jobs/live/stats")
async def get_live_job_stats(job_names: Optional[str] = None):
    from app.db.crud.live_job_crud import LiveJobCRUD
    names = [n.strip() for n in job_names.split(",")] if job_names else None
    async with get_db_session() as session:
        stats = await LiveJobCRUD.stats(session, job_names=names)
        total = await LiveJobCRUD.count_active(session)
    return {"stats": stats, "total_active": total, "as_of": datetime.utcnow().isoformat()}


@router.get("/api/match/jobs")
async def get_all_jobs():
    return job_graph.get_valid_jobs()


@router.get("/api/match/history/{student_id}")
async def get_match_history(student_id: str, limit: int = 10, current_user: Optional[dict] = Depends(get_current_user)):
    if current_user and current_user.get("role") != "admin":
        if current_user.get("student_id") != student_id:
            raise HTTPException(status_code=403, detail="无权限查看此学生匹配历史")
    async with get_db_session() as session:
        results = await match_result_crud.get_by_student(session, student_id, limit)
        items = []
        for r in results:
            dims = r.dimensions or {}
            prof = dims.get("professional_skills", {}) if isinstance(dims, dict) else {}
            gap_skills = prof.get("gap_skills", []) if isinstance(prof, dict) else []
            matched_skills = prof.get("matched_skills", []) if isinstance(prof, dict) else []
            items.append({
                "job_id": r.result_id,
                "job_title": r.job_name,
                "overall_score": r.overall_score,
                "confidence": r.confidence,
                "dimensions": dims,
                "gap_skills": gap_skills,
                "matched_skills": matched_skills,
                "summary": r.summary,
                "created_at": str(r.created_at),
            })
        return items


@router.post("/api/match/batch")
async def batch_compute_match(req: BatchMatchRequest):
    if len(req.job_names) > 10:
        raise HTTPException(status_code=400, detail="批量匹配最多支持10个岗位")
    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, req.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        portrait = {
            "basic_info": student.basic_info or {},
            "education": student.education or [],
            "skills": student.skills or [],
            "internships": student.internships or [],
            "projects": student.projects or [],
            "certs": student.certs or [],
            "awards": student.awards or [],
            "career_intent": student.career_intent,
            "inferred_soft_skills": student.inferred_soft_skills or {},
            "completeness": student.completeness,
        }

    _sem = asyncio.Semaphore(8)

    async def _match_one(job: str):
        async with _sem:
            return await match_service.compute_match(portrait, job)

    results = await asyncio.gather(*[_match_one(j) for j in req.job_names], return_exceptions=True)
    return [
        {
            "job_id": r.job_id,
            "job_title": r.job_title,
            "overall_score": r.overall_score,
            "confidence": r.confidence,
            "dimensions": r.dimensions.model_dump(),
            "gap_skills": [g.model_dump() for g in (r.dimensions.professional_skills.gap_skills or [])],
            "matched_skills": r.dimensions.professional_skills.matched_skills or [],
            "summary": r.summary,
        }
        for r in results
        if isinstance(r, MatchResult)
    ]


@router.get("/api/match/recommend/{student_id}")
@limiter.limit("5/minute")
async def recommend_jobs(
    request: Request,
    student_id: str,
    top_k: int = 5,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """根据学生画像反向推荐最匹配的岗位"""
    if current_user and current_user.get("role") != "admin":
        if current_user.get("student_id") != student_id:
            raise HTTPException(status_code=403, detail="无权限获取此学生的岗位推荐")

    async with get_db_session() as session:
        student = await student_crud.get_by_student_id(session, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        portrait_version = int(student.updated_at.timestamp()) if student.updated_at else 0
        cache_key = f"{student_id}_{top_k}_{portrait_version}"
        cached = recommend_cache.get(cache_key)
        if cached:
            return {"recommendations": cached, "from_cache": True}

        portrait = {
            "basic_info": student.basic_info or {},
            "education": student.education or [],
            "skills": student.skills or [],
            "internships": student.internships or [],
            "projects": student.projects or [],
            "certs": student.certs or [],
            "awards": student.awards or [],
            "career_intent": student.career_intent,
            "inferred_soft_skills": student.inferred_soft_skills or {},
            "completeness": student.completeness,
        }

    from app.services.recommend_service_optimized import optimized_recommender
    async with get_db_session() as session:
        result = await session.execute(
            sa_select(JobRealModel.job_name, JobRealModel.description, sql_func.count(JobRealModel.id).label("popularity"))
            .group_by(JobRealModel.job_name)
            .limit(200)
        )
        job_pool = [
            {"job_name": r[0], "description": r[1] or "", "skills": [], "popularity": r[2] if r[2] else 50}
            for r in result.fetchall() if r[0]
        ]

    recommendations, metrics = await optimized_recommender.recommend(student_id, portrait, job_pool, top_k=top_k)

    if recommendations:
        _sem = asyncio.Semaphore(5)

        async def _enhance(rec):
            async with _sem:
                try:
                    mr = await match_service.compute_match(portrait, rec["job_title"])
                    rec["score"] = mr.overall_score
                    rec["matched_skills"] = mr.dimensions.professional_skills.matched_skills[:5]
                    rec["summary"] = mr.summary
                except Exception:
                    rec["score"] = min(round(rec.get("score", 50), 1), 100)
                return rec

        recommendations = list(await asyncio.gather(*[_enhance(r) for r in recommendations]))

    recommendations = sorted(recommendations, key=lambda x: x.get("score", 0), reverse=True)
    recommend_cache[cache_key] = recommendations
    return {
        "recommendations": recommendations,
        "metrics": {
            "diversity": metrics.diversity,
            "novelty": metrics.novelty,
            "coverage": metrics.coverage,
            "response_ms": metrics.avg_response_ms,
        },
    }
