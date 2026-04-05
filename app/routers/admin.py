# -*- coding: utf-8 -*-
"""管理员路由：/api/admin/*"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sql_func, select as sa_select

from app.db import get_db_session
from app.deps import require_role, audit_log
from app.graph.job_graph_repo import job_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

# 共享错误环形缓冲（由 main.py 注入，此处引用同一对象）
_error_ring: deque = deque(maxlen=100)


def get_error_ring() -> deque:
    """返回错误缓冲引用（main.py 启动后通过 set_error_ring 注入）"""
    return _error_ring


def set_error_ring(ring: deque) -> None:
    global _error_ring
    _error_ring = ring


# ── 统计概览 ──────────────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(payload: dict = Depends(require_role("admin"))):
    from app.db.models import UserModel as _UM, ReportModel as _RM, MatchResultModel as _MRM
    async with get_db_session() as session:
        total_users   = (await session.execute(sa_select(sql_func.count()).select_from(_UM))).scalar()
        student_count = (await session.execute(sa_select(sql_func.count()).select_from(_UM).where(_UM.role == "student"))).scalar()
        company_count = (await session.execute(sa_select(sql_func.count()).select_from(_UM).where(_UM.role == "company"))).scalar()
        match_count   = (await session.execute(sa_select(sql_func.count()).select_from(_MRM))).scalar()
        report_count  = (await session.execute(sa_select(sql_func.count()).select_from(_RM))).scalar()

        _cst = timezone(timedelta(hours=8))
        _now = datetime.now(_cst)
        _today_start_utc = datetime(_now.year, _now.month, _now.day) - timedelta(hours=8)
        _today_end_utc   = _today_start_utc + timedelta(days=1)
        new_today     = (await session.execute(sa_select(sql_func.count()).select_from(_UM).where(
            _UM.created_at >= _today_start_utc, _UM.created_at < _today_end_utc))).scalar()
        matches_today = (await session.execute(sa_select(sql_func.count()).select_from(_MRM).where(
            _MRM.created_at >= _today_start_utc, _MRM.created_at < _today_end_utc))).scalar()

    return {
        "total_users": total_users, "student_count": student_count,
        "company_count": company_count,
        "admin_count": (total_users or 0) - (student_count or 0) - (company_count or 0),
        "match_count": match_count, "report_count": report_count,
        "new_users_today": new_today or 0, "matches_today": matches_today or 0,
    }


# ── 用户管理 ──────────────────────────────────────────────────────────────────

@router.get("/users")
async def admin_list_users(
    page: int = 1, page_size: int = 20,
    role_filter: Optional[str] = None, search: Optional[str] = None,
    payload: dict = Depends(require_role("admin")),
):
    from app.db.models import UserModel as _UM
    from app.db.crud.job_real_crud import _escape_like_pattern
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    async with get_db_session() as session:
        q = sa_select(_UM)
        if role_filter:
            q = q.where(_UM.role == role_filter)
        if search:
            safe = _escape_like_pattern(search)
            q = q.where(_UM.username.ilike(f"%{safe}%", escape="\\"))
        q = q.offset((page - 1) * page_size).limit(page_size)
        users = (await session.execute(q)).scalars().all()

        count_q = sa_select(sql_func.count()).select_from(_UM)
        if role_filter:
            count_q = count_q.where(_UM.role == role_filter)
        if search:
            count_q = count_q.where(_UM.username.ilike(f"%{safe}%", escape="\\"))
        total = (await session.execute(count_q)).scalar()

    return {
        "total": total, "page": page, "page_size": page_size,
        "users": [{"username": u.username, "role": u.role, "student_id": u.student_id,
                   "created_at": u.created_at.isoformat() if u.created_at else ""} for u in users],
    }


@router.put("/users/{username}/role")
async def admin_set_user_role(username: str, data: dict, payload: dict = Depends(require_role("admin"))):
    new_role = data.get("role", "student")
    if new_role not in ("student", "company", "admin"):
        raise HTTPException(status_code=400, detail="无效角色")
    from app.db.models import UserModel as _UM
    async with get_db_session() as session:
        user = (await session.execute(sa_select(_UM).where(_UM.username == username))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.role = new_role
    audit_log("SET_ROLE", "user", username, f"new_role={new_role} by={payload.get('sub')}")
    return {"ok": True, "username": username, "role": new_role}


@router.delete("/users/{username}")
async def admin_delete_user(username: str, payload: dict = Depends(require_role("admin"))):
    operator = payload.get("sub")
    if operator == username:
        raise HTTPException(status_code=400, detail="不能删除自己")
    from app.db.models import UserModel as _UM
    async with get_db_session() as session:
        user = (await session.execute(sa_select(_UM).where(_UM.username == username))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        await session.delete(user)
    audit_log("DELETE", "user", username, f"by={operator}")
    return {"ok": True}


# ── 岗位图谱 & 热门数据 ─────────────────────────────────────────────────────

@router.get("/hot_jobs")
async def admin_hot_jobs(limit: int = 10, payload: dict = Depends(require_role("admin"))):
    from app.db.models import JobRealModel as _JRM
    async with get_db_session() as session:
        rows = (await session.execute(
            sa_select(_JRM.job_name, sql_func.count().label("jd_count"))
            .where(_JRM.status == 1).group_by(_JRM.job_name)
            .order_by(sql_func.count().desc()).limit(limit)
        )).all()
    return {"hot_jobs": [{"job_name": r.job_name, "jd_count": r.jd_count} for r in rows]}


@router.get("/job_stats")
async def admin_job_stats(payload: dict = Depends(require_role("admin"))):
    jobs = []
    all_edges = list(job_graph.G.edges(data=True))
    promo_edges    = sum(1 for _, _, d in all_edges if d.get("type") == "PROMOTES_TO")
    transfer_edges = sum(1 for _, _, d in all_edges if d.get("type") == "CAN_TRANSFER_TO")
    all_skills: set = set()
    for node_id, attrs in job_graph.G.nodes(data=True):
        skills = attrs.get("skills") or []
        all_skills.update(skills)
        jobs.append({
            "title": attrs.get("title", node_id), "industry": attrs.get("industry", ""),
            "skill_count": len(skills),
            "promotion_count": sum(1 for _, _, d in job_graph.G.out_edges(node_id, data=True) if d.get("type") == "PROMOTES_TO"),
            "transfer_count":  sum(1 for _, _, d in job_graph.G.out_edges(node_id, data=True) if d.get("type") == "CAN_TRANSFER_TO"),
        })
    return {"total_jobs": len(jobs), "total_skills": len(all_skills),
            "promotion_edges": promo_edges, "transfer_edges": transfer_edges,
            "jobs": sorted(jobs, key=lambda x: x["title"])}


# ── 日志 & 系统操作 ────────────────────────────────────────────────────────────

@router.get("/logs")
async def admin_get_logs(level: str = "", payload: dict = Depends(require_role("admin"))):
    logs = []
    for err in list(_error_ring):
        status = err.get("status", 0)
        log_level = "error" if status >= 500 else "warn"
        if level and level != log_level:
            continue
        logs.append({"time": err.get("time", ""), "level": log_level,
                     "message": f"[{status}] {err.get('path', '')} — {err.get('detail', '')}"})
    return logs


@router.post("/refresh_job_graph")
async def admin_refresh_job_graph(payload: dict = Depends(require_role("admin"))):
    try:
        job_graph._load_graph()
        audit_log("REFRESH", "job_graph", "all", f"by={payload.get('sub')}")
        return {"ok": True, "nodes": job_graph.G.number_of_nodes(), "edges": job_graph.G.number_of_edges()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图谱刷新失败: {str(e)}")


@router.post("/fetch_live_jobs")
async def admin_fetch_live_jobs(
    job_names: Optional[List[str]] = None,
    limit: int = Query(10, ge=1, le=50),
    payload: dict = Depends(require_role("admin")),
):
    from app.services.job_fetcher import job_fetcher
    targets = job_names or job_graph.get_valid_jobs()
    summary = await job_fetcher.fetch_and_store(targets, limit_per_job=limit)
    expired = await job_fetcher.expire_old_jobs()
    total_inserted = sum(summary.values())
    audit_log("FETCH_LIVE_JOBS", "live_jobs", "all", f"by={payload.get('sub')}, inserted={total_inserted}")
    return {"ok": True, "jobs_fetched": len(targets), "total_inserted": total_inserted,
            "expired": expired, "detail": summary}


# ── 趋势 & 分布 ───────────────────────────────────────────────────────────────

@router.get("/user_trends")
async def admin_user_trends(days: int = 7, payload: dict = Depends(require_role("admin"))):
    from app.db.models import UserModel as _UM, MatchResultModel as _MRM
    _cst = timezone(timedelta(hours=8))
    today = datetime.now(_cst).date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    _d_user  = sql_func.strftime('%Y-%m-%d', sql_func.datetime(_UM.created_at,  '+8 hours')).label("d")
    _d_match = sql_func.strftime('%Y-%m-%d', sql_func.datetime(_MRM.created_at, '+8 hours')).label("d")
    async with get_db_session() as session:
        new_users_rows = (await session.execute(
            sa_select(_d_user,  sql_func.count().label("cnt")).group_by("d").order_by("d"))).all()
        active_rows = (await session.execute(
            sa_select(_d_match, sql_func.count(sql_func.distinct(_MRM.student_id)).label("cnt")).group_by("d").order_by("d"))).all()
    new_map    = {str(r.d): r.cnt for r in new_users_rows}
    active_map = {str(r.d): r.cnt for r in active_rows}
    return {"dates": [d[5:] for d in dates],
            "new_users":    [new_map.get(d, 0) for d in dates],
            "active_users": [active_map.get(d, 0) for d in dates]}


@router.get("/match_distribution")
async def admin_match_distribution(payload: dict = Depends(require_role("admin"))):
    from app.db.models import MatchResultModel as _MRM
    async with get_db_session() as session:
        rows = (await session.execute(sa_select(_MRM.overall_score))).scalars().all()
    return {"ranges": ["80分以上", "60-80分", "60分以下"],
            "counts": [sum(1 for s in rows if s >= 80),
                       sum(1 for s in rows if 60 <= s < 80),
                       sum(1 for s in rows if s < 60)]}


@router.get("/industry_stats")
async def admin_industry_stats(payload: dict = Depends(require_role("admin"))):
    from app.db.models import MatchResultModel as _MRM
    async with get_db_session() as session:
        rows = (await session.execute(
            sa_select(_MRM.job_name, sql_func.count().label("cnt"))
            .group_by(_MRM.job_name).order_by(sql_func.count().desc()).limit(8)
        )).all()
    if not rows:
        return {"jobs": [], "counts": []}
    return {"jobs": [r.job_name for r in rows], "counts": [r.cnt for r in rows]}
