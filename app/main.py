# -*- coding: utf-8 -*-
"""
职业生涯规划系统 - 基于GraphRAG的七维度岗位画像和四维度人岗匹配
符合赛题要求的完整系统
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.database import init_db
from app.core.observability import setup_logging, new_trace_id, metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化日志 + 建表
    setup_logging()
    # dev：用 create_all 便捷建表；prod：schema 由 `alembic upgrade head` 管理，跳过 create_all。
    if settings.APP_ENV == "development":
        try:
            init_db()
            logger.info("数据库初始化完成（dev: create_all）")
        except Exception as e:
            logger.warning("数据库初始化失败（降级纯内存）: %s", e)
    else:
        logger.info("生产环境：schema 由 alembic 管理（启动前执行 alembic upgrade head）")
    # 启动模式可观测：降级状态一眼可见（DB / cache / 任务进度后端 / 鉴权）
    try:
        from app.core.redis_client import cache_is_distributed
        from app.services.task_progress import task_store
        logger.info(
            "启动模式 | DB=%s | cache=%s | task_store=%s | auth_enforced=%s",
            settings.DATABASE_URL.split("://", 1)[0],
            "redis" if cache_is_distributed() else "in-process",
            task_store.backend(),
            settings.AUTH_ENFORCED,
        )
    except Exception:
        pass
    yield
    # 关闭：释放资源
    try:
        from app.core.redis_client import get_cache
        await get_cache().close()
    except Exception:
        pass
    try:
        from app.services.retrieval_client import retrieval_client
        await retrieval_client.close()
    except Exception:
        pass


# 路由 import 放在 lifespan 之后，避免循环依赖时序问题
from app.routers.auth import router as auth_router
from app.routers.student import router as student_router
from app.routers.job import router as job_router
# bridge_flow（954行 god-file）已按领域拆分为以下子路由
from app.routers.match import router as match_router
from app.routers.report import router as report_router
from app.routers.chat import router as chat_router
from app.routers.stats import router as stats_router
from app.routers.agent import router as agent_router
from app.routers.admin import router as admin_router  # M2 租户配置（admin RBAC）
from app.routers.analytics import router as analytics_router  # M1 院校分析看板
from app.routers.progress import router as progress_router  # Phase 3 成长闭环（学生端）
from app.routers.platform import router as platform_router  # 平台运营（跨租户超管）


app = FastAPI(
    title="基于AI的大学生职业规划智能体",
    description="Youtu-GraphRAG驱动的职业规划智能体：七维度岗位画像 + IRCoT多步推理 + 四维度人岗匹配",
    version="3.0.0",
    lifespan=lifespan,
)

# 复用已有配置 settings.CORS_ORIGINS（.env 已配 localhost:5173,3000）。
# 显式白名单时携带凭证；未配置时退回通配但关闭凭证——避免 "*" + credentials 的无效/不安全组合。
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_and_ratelimit(request: Request, call_next):
    """为每个请求注入 trace_id；可选地按 IP 限流（RATE_LIMIT_PER_MIN>0 时启用）。"""
    new_trace_id()
    if settings.RATE_LIMIT_PER_MIN > 0 and request.url.path.startswith("/api/"):
        try:
            from app.core.redis_client import cache
            ip = request.client.host if request.client else "unknown"
            key = f"rl:{ip}:{request.url.path}"
            count = await cache.incr_with_expire(key, window=60)
            if count > settings.RATE_LIMIT_PER_MIN:
                metrics.incr("http.rate_limited")
                return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})
        except Exception:
            pass  # 限流组件异常绝不阻断正常请求
    return await call_next(request)

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(job_router)
app.include_router(match_router)
app.include_router(report_router)
app.include_router(chat_router)
app.include_router(stats_router)
app.include_router(agent_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(progress_router)
app.include_router(platform_router)


@app.get("/")
def root():
    return {
        "message": "基于AI的大学生职业规划智能体 v3.0",
        "description": "YOUTU-GraphRAG驱动：七维度岗位画像 + 四维度人岗匹配 + 职业路径图谱",
        "jobs": {
            "岗位列表(51个)": "GET /api/match/jobs",
            "岗位画像(七维度)": "GET /api/jobs/info?job=前端开发",
            "职业路径图谱": "GET /api/jobs/career-graph?job=前端开发",
            "行业趋势": "GET /api/market/industry_trends",
        },
        "student": {
            "简历解析": "POST /api/resume/parse",
            "学生画像": "GET /api/portrait/{student_id}",
            "七维度得分": "GET /api/portrait/{student_id}/score_detail",
        },
        "match": {
            "四维度匹配": "POST /api/match/compute",
            "批量匹配": "POST /api/match/batch",
            "岗位推荐": "GET /api/match/recommend/{student_id}",
        },
        "report": {
            "生成报告": "POST /api/report/generate",
            "获取报告": "GET /api/report/{report_id}",
            "AI润色": "POST /api/report/{report_id}/polish",
        },
        "chat": {
            "创建会话": "POST /api/chat/session",
            "流式对话(SSE)": "POST /api/chat/stream",
        },
    }


@app.get("/health")
def health():
    """存活探针（liveness）：进程在跑即 200。LB/K8s 用它判断是否重启。"""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """就绪探针（readiness）：依赖就位才收流量——DB 可连 + 图谱已载。
    图谱未载完（重型 FAISS 初始化中）返回 503，避免 LB 把请求打过来报错。"""
    checks = {"db": False, "graph": False, "cache": "unknown"}
    try:
        from sqlalchemy import text
        from app.core.database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception as e:
        checks["db_error"] = str(e)[:120]
    try:
        from app.services.youtu_retriever_service import youtu_retriever_service
        checks["graph"] = bool(youtu_retriever_service.jobs_index)
    except Exception as e:
        checks["graph_error"] = str(e)[:120]
    try:
        from app.core.redis_client import cache_is_distributed
        checks["cache"] = "redis" if cache_is_distributed() else "in-process"
    except Exception:
        pass

    ready_ok = checks["db"] and checks["graph"]
    return JSONResponse(
        status_code=200 if ready_ok else 503,
        content={"status": "ready" if ready_ok else "not_ready", "checks": checks},
    )


@app.get("/metrics")
def get_metrics():
    """可观测性指标快照：LLM 延迟/token/失败、工具耗时/失败率、限流计数 + 降级态。"""
    snap = metrics.snapshot()
    try:
        from app.core.redis_client import cache_is_distributed
        from app.services.task_progress import task_store
        snap["runtime"] = {
            "db_dialect": settings.DATABASE_URL.split("://", 1)[0],
            "cache_distributed": cache_is_distributed(),
            "task_store_backend": task_store.backend(),
            "auth_enforced": settings.AUTH_ENFORCED,
            "app_env": settings.APP_ENV,
        }
    except Exception:
        pass
    return snap
