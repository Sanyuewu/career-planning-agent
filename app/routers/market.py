# -*- coding: utf-8 -*-
"""市场趋势路由：/api/market/*"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func as sql_func

from app.cache import market_trends_cache, MARKET_TRENDS_CACHE_TTL
from app.db import get_db_session, job_trend_crud
from app.db.models import JobTrendSnapshotModel
from app.graph.job_graph_repo import job_graph
from app.services.market_service import market_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["Market"])


@router.get("/trends")
async def get_market_trends(top_k: int = 10):
    """获取就业市场岗位热度排行榜（带预计算缓存）"""
    now = time.time()
    cached = market_trends_cache.get("data")
    cache_time = market_trends_cache.get("timestamp", 0)

    if cached and (now - cache_time) < MARKET_TRENDS_CACHE_TTL:
        return {"trends": cached[:top_k], "from_cache": True}

    async with get_db_session() as session:
        stmt = (
            select(
                JobTrendSnapshotModel.job_code,
                sql_func.max(JobTrendSnapshotModel.demand_index).label("demand_index"),
                sql_func.max(JobTrendSnapshotModel.jd_count).label("jd_count"),
                sql_func.max(JobTrendSnapshotModel.snapshot_date).label("last_updated"),
            )
            .group_by(JobTrendSnapshotModel.job_code)
            .order_by(sql_func.max(JobTrendSnapshotModel.demand_index).desc())
            .limit(50)
        )
        rows = (await session.execute(stmt)).fetchall()
        trends = [
            {
                "job_title": row.job_code,
                "demand_index": round(row.demand_index or 0, 1),
                "match_count": row.jd_count or 0,
                "last_updated": str(row.last_updated),
            }
            for row in rows
        ]
        market_trends_cache["data"] = trends
        market_trends_cache["timestamp"] = now
        return {"trends": trends[:top_k], "from_cache": False}


@router.get("/trend")
async def get_job_trend(
    job: Optional[str] = Query(None, description="岗位名称"),
    job_name: Optional[str] = Query(None, description="岗位名称（别名）"),
):
    """获取单个岗位的市场热度趋势 + 所属行业深度洞察"""
    job = job or job_name
    if not job:
        raise HTTPException(status_code=422, detail="缺少参数 job 或 job_name")
    from app.data.industry_insights import get_industry_for_job, INDUSTRY_INSIGHTS
    from app.db.crud.job_real_crud import job_real_crud as _jrc
    async with get_db_session() as session:
        snapshots = await job_trend_crud.get_by_job_code(session, job, limit=30)
        job_info = job_graph.get_job_info(job)
        stats = await _jrc.get_stats_by_job_name(session, job)

    industry_name = get_industry_for_job(job)
    raw = INDUSTRY_INSIGHTS.get(industry_name, {})
    industry_insight = {
        "industry_name": industry_name,
        "trend": raw.get("trend"),
        "growth_rate": raw.get("growth_rate"),
        "drivers": raw.get("drivers", []),
        "challenges": raw.get("challenges", []),
        "future": raw.get("future"),
        "hot_skills": raw.get("hot_skills", []),
        "salary_range": raw.get("salary_range"),
        "hiring_seasons": raw.get("hiring_seasons"),
        "interview_focus": raw.get("interview_focus"),
        "competitive_ratio": raw.get("competitive_ratio"),
        "top_cities": raw.get("top_cities", []),
    } if raw else None

    return {
        "job_title": job,
        "salary": job_info.get("salary", "待定") if job_info else "待定",
        "industry": job_info.get("industry", "") if job_info else "",
        "jd_count": stats.get("count", 0),
        "avg_salary_k": stats.get("avg_salary_k", 0),
        "top_companies": stats.get("top_companies", [])[:5],
        "snapshots": [
            {"date": str(s.snapshot_date), "demand_index": s.demand_index, "top_skills": s.top_skills or []}
            for s in reversed(snapshots)
        ],
        "industry_insight": industry_insight,
    }


@router.get("/real_jobs")
async def get_real_jobs(job_name: str, limit: int = 5):
    """获取目标岗位的真实招聘样本"""
    from app.db.crud.job_real_crud import job_real_crud as _jrc
    async with get_db_session() as session:
        samples = await _jrc.get_samples(session, job_name, min(limit, 20))
        stats = await _jrc.get_stats_by_job_name(session, job_name)
    return {
        "job_name": job_name,
        "total": stats["count"],
        "avg_salary_k": stats["avg_salary_k"],
        "top_companies": stats["top_companies"][:5],
        "samples": samples,
    }


@router.get("/industry_trends")
async def get_industry_trends():
    return await market_service.get_industry_trends()


@router.get("/salary_comparison")
async def get_salary_comparison(job_name: str = Query(..., description="岗位名称")):
    return await market_service.get_salary_comparison(job_name)
