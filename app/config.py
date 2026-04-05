# -*- coding: utf-8 -*-
"""
配置管理模块 - 所有环境变量统一在此声明
遵循v5规范：使用Pydantic Settings读取.env
"""

import os
import secrets
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
try:
    from typing import Literal, Optional
except ImportError:
    from typing_extensions import Literal, Optional

_logger = logging.getLogger(__name__)

# 默认密钥标记，用于检测是否使用默认值
_DEFAULT_JWT_SECRET = "career-planner-secret-key-change-in-production"


class Settings(BaseSettings):
    APP_ENV: Literal["development", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = ""  # 逗号分隔的允许域名列表，如 "https://a.vercel.app,https://b.vercel.app"
    
    LLM_PROVIDER: Literal["deepseek", "qwen", "ollama", "groq"] = "deepseek"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_TIMEOUT: int = 60
    MOCK_LLM: bool = False
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/career.db"
    GRAPH_BACKEND: Literal["neo4j", "networkx"] = "networkx"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    
    FILE_STORAGE: Literal["local", "minio"] = "local"
    LOCAL_STORAGE_DIR: str = "./data/uploads"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = ""
    
    FEATURE_SEMANTIC_MATCH: bool = True
    FEATURE_EMOTION_ANALYSIS: bool = True
    SEMANTIC_MATCH_THRESHOLD: float = 0.85
    EMOTION_ANXIETY_THRESHOLD: float = 0.35
    RESUME_PARSE_TIMEOUT: int = 120
    REPORT_GENERATE_TIMEOUT: int = 60
    
    GROQ_API_KEY: str = ""
    JWT_SECRET: str = Field(default=_DEFAULT_JWT_SECRET, min_length=32)
    JWT_EXPIRE_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.GROQ_API_KEY and not self.LLM_API_KEY:
            self.LLM_API_KEY = self.GROQ_API_KEY
            self.LLM_PROVIDER = "groq"
            self.LLM_MODEL = "llama-3.3-70b-versatile"
            self.LLM_BASE_URL = "https://api.groq.com/openai/v1"
    
    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v == _DEFAULT_JWT_SECRET:
            _logger.warning(
                "⚠️  SECURITY WARNING: JWT_SECRET is using default value! "
                "Please set a random secret in .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v
    
    def is_jwt_secret_default(self) -> bool:
        return self.JWT_SECRET == _DEFAULT_JWT_SECRET


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROFILE_JSON_PATH = DATA_DIR / "job_profiles.json"
GRAPH_JSON_PATH = DATA_DIR / "job_graph.json"
