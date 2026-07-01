# -*- coding: utf-8 -*-
"""
配置管理模块 - 所有环境变量统一在此声明
遵循v5规范：使用Pydantic Settings读取.env
"""

import logging
import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings

# config 是最先加载的应用模块。在任何重型数值库（torch / faiss / numpy-MKL）import 之前，
# 关闭 Intel MKL/OpenMP 与 Fortran 运行时的控制台信号处理器——否则 Windows 控制台事件
# （关窗 / Ctrl 断开）会触发 `forrtl: severe (window-CLOSE)` 直接杀进程（服务"关窗即崩"根因）。
# 仅设默认值，不覆盖用户显式配置。
for _k, _v in (
    ("FOR_DISABLE_CONSOLE_CTRL_HANDLER", "1"),  # Intel Fortran 运行时（faiss/scipy 拉入）
    ("KMP_HANDLE_SIGNALS", "0"),                 # Intel OpenMP 信号处理
):
    os.environ.setdefault(_k, _v)
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

_logger = logging.getLogger(__name__)


# config 是最先被加载的应用模块——在此尽早将控制台重配为 UTF-8，
# 避免 Windows GBK 控制台在重型依赖（torch/sentence-transformers/YOUTU）
# 加载阶段输出 ✓/emoji 时抛 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


class Settings(BaseSettings):
    APP_ENV: Literal["development", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = ""

    LLM_PROVIDER: Literal["deepseek", "qwen", "ollama", "groq"] = "deepseek"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_TIMEOUT: int = 60
    MOCK_LLM: bool = False

    # ── LLM 降级（主 Provider 失败时切换）─────────────────────────
    LLM_FALLBACK_API_KEY: str = ""
    LLM_FALLBACK_MODEL: str = ""
    LLM_FALLBACK_BASE_URL: str = ""
    LLM_MAX_RETRIES: int = 2

    # ── 持久化 ───────────────────────────────────────────────────
    # 默认 SQLite（aiosqlite 异步驱动）；生产可切 postgresql+asyncpg://...
    DATABASE_URL: str = "sqlite+aiosqlite:///data/career_planner.db"

    # ── Redis（可选，未配置则进程内降级）─────────────────────────
    REDIS_URL: str = ""              # 如 redis://localhost:6379/0；空 = 禁用
    CACHE_TTL: int = 1800            # 热点检索缓存秒数

    # ── 检索微服务（可选，未配置则进程内 YOUTU 降级）──────────────
    RETRIEVAL_SERVICE_URL: str = ""  # 如 http://localhost:8090；空 = 进程内
    RETRIEVAL_TIMEOUT: int = 30

    # ── 可观测性 ─────────────────────────────────────────────────
    JSON_LOGS: bool = False          # True = 结构化 JSON 日志
    ENABLE_METRICS: bool = True

    # ── 限流（每 IP 每分钟请求数；0 = 关闭，保持基线行为）──────────
    RATE_LIMIT_PER_MIN: int = 0

    # ── 认证 / 多租户（M0）─────────────────────────────────────────
    JWT_SECRET: str = ""            # 生产必填；空则用 dev 回退密钥（仅 development 允许）
    AUTH_ENFORCED: bool = True      # False=dev 便捷：无 token 落 default 租户 admin
    PII_ENCRYPT_KEY: str = ""       # PII 字段加密密钥（Fernet base64；空则仅脱敏不加密）

    GRAPH_BACKEND: Literal["neo4j", "networkx"] = "networkx"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()


BASE_DIR = Path(__file__).parent.parent
