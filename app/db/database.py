# -*- coding: utf-8 -*-
"""
数据库连接管理
遵循v5规范：支持SQLite/PostgreSQL
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings, DATA_DIR
from app.db.models import Base


DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_file = DATA_DIR / "career.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{db_file}"

async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    future=True,
    pool_timeout=30,  # 连接池超时30秒
    pool_recycle=1800,  # 连接回收时间30分钟
)

async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

sync_engine = create_engine(
    DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", ""),
    echo=settings.LOG_LEVEL == "DEBUG",
)

sync_session_factory = sessionmaker(
    sync_engine,
    expire_on_commit=False,
)


async def init_db():
    """初始化数据库表"""
    async with async_engine.begin() as conn:
        # D-5: SQLite 外键约束需要每次连接时开启
        if DATABASE_URL.startswith("sqlite"):
            await conn.execute(text("PRAGMA foreign_keys = ON"))

        await conn.run_sync(Base.metadata.create_all)
        # 热迁移：兼容旧 DB，添加新列（已存在则忽略）
        for _sql in [
            "ALTER TABLE reports ADD COLUMN chapters_json TEXT",
            "ALTER TABLE job_real ADD COLUMN industry TEXT DEFAULT ''",
            "ALTER TABLE students ADD COLUMN interests TEXT",
            "ALTER TABLE students ADD COLUMN ability_profile TEXT",
            "ALTER TABLE students ADD COLUMN personality_traits TEXT",
        ]:
            try:
                await conn.execute(text(_sql))
            except Exception:
                pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """数据库会话上下文管理器"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
