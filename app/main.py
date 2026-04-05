# -*- coding: utf-8 -*-
"""
FastAPI后端API服务 — 路由入口
路由逻辑已拆分至 app/routers/，此文件仅保留应用初始化、中间件和共享端点。
"""

import logging
import os
import sys
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32":
    os.environ.setdefault("STARLETTE_ENV_FILE_ENCODING", "utf-8")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select as _sa_select, literal as _sa_literal

from app.ai.llm_client import LLMCallError
from app.config import settings
from app.db import get_db_session, init_db
from app.db.models import StudentModel as _SM, ReportModel as _RM, JobRealModel as _JRM
from app.graph.job_graph_repo import job_graph
from app.rate_limit import limiter
from app.schemas.api import FeedbackRequest
from app.services.chat_agent_service import chat_agent_service
from app.cache import recommend_cache, market_trends_cache, MARKET_TRENDS_CACHE_TTL

# Routers
from app.routers.agent import router as agent_router
from app.routers.admin import router as admin_router, set_error_ring as _set_admin_error_ring
from app.routers.assessment import router as assessment_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.company import router as company_router
from app.routers.graph import router as graph_router
from app.routers.market import router as market_router
from app.routers.match import router as match_router
from app.routers.portrait import router as portrait_router
from app.routers.report import router as report_router
from app.routers.resume import router as resume_router

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# ── 错误监控缓冲（与 admin router 共享） ──────────────────────────────────────
_error_ring: deque = deque(maxlen=100)


def _record_error(path: str, status: int, detail: str, trace_id: str = ""):
    _error_ring.appendleft({
        "time": datetime.utcnow().isoformat(),
        "path": path,
        "status": status,
        "detail": detail[:300],
        "trace_id": trace_id,
    })


# ── 应用生命周期 ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_jwt_secret_default():
        logger.warning(
            "⚠️  SECURITY: JWT_SECRET 正在使用默认值！请在 .env 中设置随机密钥，否则 Token 可被伪造。"
            "生成密钥命令: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
        if settings.APP_ENV == "production":
            raise RuntimeError("生产环境禁止使用默认 JWT_SECRET，请配置安全的密钥后启动")
    await init_db()
    _models_dir = Path(__file__).parent.parent / "models" / "all-MiniLM-L6-v2"
    if not _models_dir.exists():
        logger.warning(
            "⚠️  Embedding模型未找到（%s）。语义匹配将使用 Mock 向量。"
            "请运行: python scripts/download_models.py 下载模型", _models_dir
        )
    _set_admin_error_ring(_error_ring)
    from app.core.scheduler import start_scheduler
    start_scheduler()
    yield
    from app.core.scheduler import stop_scheduler
    stop_scheduler()


# ── 应用实例 ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="职业规划智能体API",
    description="AI大学生职业规划智能体后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 限流
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# LLM 错误处理
@app.exception_handler(LLMCallError)
async def llm_error_handler(request: Request, exc: LLMCallError):
    logger.error(f"LLM调用失败: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={"detail": "AI服务暂时不可用，请稍后重试。如问题持续，请联系管理员。", "code": 503},
    )

# CORS
def _get_cors_origins() -> List[str]:
    if settings.APP_ENV == "production":
        return ["https://your-domain.com"]
    return [
        f"http://localhost:{p}" for p in (5173, 5174, 5175, 5176, 5177, 3000)
    ] + [
        f"http://127.0.0.1:{p}" for p in (5173, 5174, 5175, 5176, 5177, 3000)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
)

# X-Request-ID 中间件
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = trace_id
    if response.status_code >= 400:
        _record_error(str(request.url.path), response.status_code, f"HTTP {response.status_code}", trace_id)
    return response

# ── 路由注册 ──────────────────────────────────────────────────────────────────

app.include_router(agent_router)
app.include_router(admin_router)
app.include_router(assessment_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(company_router)
app.include_router(graph_router)
app.include_router(market_router)
app.include_router(match_router)
app.include_router(portrait_router)
app.include_router(report_router)
app.include_router(resume_router)

# ── 共享端点 ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "职业规划智能体API服务运行中", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """服务健康检查"""
    checks: dict = {}
    try:
        async with get_db_session() as session:
            await session.execute(_sa_select(_sa_literal(1)))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    checks["llm_provider"] = settings.LLM_PROVIDER
    checks["llm_configured"] = bool(settings.LLM_API_KEY)
    checks["mock_mode"] = settings.MOCK_LLM
    checks["active_chat_sessions"] = len(chat_agent_service.sessions)
    checks["recommend_cache_entries"] = len(recommend_cache)
    checks["market_trends_cache_valid"] = (
        market_trends_cache.get("data") is not None
        and (time.time() - market_trends_cache.get("timestamp", 0)) < MARKET_TRENDS_CACHE_TTL
    )

    overall = "healthy" if checks["database"] == "ok" else "degraded"
    return {"status": overall, "checks": checks, "version": "1.0.0"}


@app.get("/api/stats/public")
async def get_public_stats():
    """平台公开统计数据（无需登录，供首页展示）"""
    from sqlalchemy import func as _func
    async with get_db_session() as session:
        student_count = (await session.execute(_sa_select(_func.count()).select_from(_SM))).scalar() or 0
        report_count = (await session.execute(
            _sa_select(_func.count()).select_from(_RM).where(_RM.status == "completed")
        )).scalar() or 0
        jd_total = (await session.execute(
            _sa_select(_func.count()).select_from(_JRM).where(_JRM.status == 1)
        )).scalar() or 0
    job_count = len([n for n in job_graph.G.nodes if str(n).startswith("job_")])
    return {"student_count": student_count, "report_count": report_count, "job_count": job_count, "jd_total": jd_total}


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """提交用户反馈"""
    if req.rating not in (0, 1):
        raise HTTPException(status_code=400, detail="rating 必须是 0 或 1")
    if req.target_type not in ("match", "report"):
        raise HTTPException(status_code=400, detail="target_type 无效")
    from app.db.models import FeedbackModel as _FM
    from sqlalchemy import func as _func
    async with get_db_session() as session:
        if req.student_id:
            existing = (await session.execute(
                _sa_select(_FM).where(_FM.student_id == req.student_id, _FM.target_id == req.target_id)
            )).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=409, detail="已提交过反馈")
        session.add(_FM(
            student_id=req.student_id,
            target_type=req.target_type,
            target_id=req.target_id,
            rating=req.rating,
            comment=req.comment,
        ))
    return {"ok": True}


@app.get("/api/feedback/stats/{target_type}")
async def get_feedback_stats(target_type: str, target_id: str):
    from app.db.models import FeedbackModel as _FM
    from sqlalchemy import func as _func
    async with get_db_session() as session:
        row = (await session.execute(
            _sa_select(
                _func.count().label("total"),
                _func.sum(_FM.rating).label("positive"),
            ).where(_FM.target_type == target_type, _FM.target_id == target_id)
        )).one()
    total = row.total or 0
    positive = int(row.positive or 0)
    return {
        "total": total,
        "positive": positive,
        "satisfaction_pct": round(positive / total * 100) if total > 0 else None,
    }


@app.get("/api/debug/errors")
async def get_recent_errors(limit: int = 20):
    return {"total": len(_error_ring), "errors": list(_error_ring)[:limit]}


@app.post("/api/debug/client-error")
async def report_client_error(request: Request):
    try:
        body = await request.json()
        _record_error(
            path=body.get("url", "frontend"),
            status=0,
            detail=body.get("message", "Unknown client error"),
            trace_id=body.get("traceId", ""),
        )
    except Exception:
        pass
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
