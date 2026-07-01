# -*- coding: utf-8 -*-
"""
SQLAlchemy 数据库引擎与会话管理。

双引擎设计：
  - 同步引擎（engine / SessionLocal / get_db）：迁移、admin 批处理、建表。
  - 异步引擎（async_engine / AsyncSessionLocal / get_async_db）：请求热路径。

DATABASE_URL 使用异步驱动 URL（如 sqlite+aiosqlite:// 或 postgresql+asyncpg://），
同步 URL 由其自动派生。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings


def _to_sync_url(async_url: str) -> str:
    """把异步驱动 URL 派生为同步 URL（用于迁移/建表）。"""
    return (
        async_url
        .replace("+aiosqlite", "")
        .replace("+asyncpg", "")
        .replace("+asyncmy", "+pymysql")
    )


ASYNC_DB_URL = settings.DATABASE_URL
SYNC_DB_URL = _to_sync_url(ASYNC_DB_URL)

_is_sqlite = SYNC_DB_URL.startswith("sqlite")
_sync_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# ── 同步引擎（迁移 / admin / 建表）──────────────────────────────
engine = create_engine(SYNC_DB_URL, connect_args=_sync_connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── 异步引擎（请求热路径）───────────────────────────────────────
async_engine = create_async_engine(ASYNC_DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖（同步）：每请求独立 Session，结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """FastAPI 依赖（异步）：每请求独立 AsyncSession。"""
    async with AsyncSessionLocal() as session:
        yield session


def init_db():
    """建表（若已存在则跳过）。应用启动时同步调用一次。"""
    from app.models import db_models  # noqa: F401 — 触发模型注册
    Base.metadata.create_all(bind=engine)
