# -*- coding: utf-8 -*-
"""
RAG 检索服务 - 支持 JSON 关键词检索（降级方案）+ ChromaDB 语义检索（可选）

知识库文件：data/knowledge_base.json（23条IT岗位结构化条目）
ChromaDB 在 Python 3.12 下不兼容时，自动降级为 JSON TF-IDF 风格关键词匹配。

集合说明：
  job_profiles  - 23条IT岗位标准画像（由 build_rag_index.py 构建）
  real_jds      - 基于真实JD描述的语义库（由 build_rag_index.py 构建）
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# JSON 知识库降级检索（不依赖 chromadb）
# -----------------------------------------------------------------------

def _load_knowledge_base() -> List[Dict[str, Any]]:
    kb_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base.json"
    try:
        with open(kb_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("knowledge_base.json 加载失败: %s", e)
        return []


_KB_ENTRIES: List[Dict[str, Any]] = []


def _get_kb() -> List[Dict[str, Any]]:
    global _KB_ENTRIES
    if not _KB_ENTRIES:
        _KB_ENTRIES = _load_knowledge_base()
    return _KB_ENTRIES


def search_knowledge_base(query: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """
    TF-IDF 风格关键词匹配，从 knowledge_base.json 中检索最相关条目。
    返回 [{job, description, core_skills, salary_range, market_outlook, entry_advice, score}, ...]
    """
    entries = _get_kb()
    if not entries:
        return []

    query_lower = query.lower()
    query_tokens = set(query_lower.replace("，", " ").replace(",", " ").split())

    scored: List[tuple] = []
    for entry in entries:
        score = 0.0
        # 精确岗位名匹配权重最高
        job_lower = entry.get("job", "").lower()
        if job_lower in query_lower or query_lower in job_lower:
            score += 10.0
        # 关键词命中
        for kw in entry.get("keywords", []):
            if kw.lower() in query_lower:
                score += 3.0
        # 技能词命中
        for skill in entry.get("core_skills", []):
            skill_lower = skill.lower()
            if skill_lower in query_lower or any(t in skill_lower for t in query_tokens if len(t) >= 2):
                score += 1.0
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "job": e["job"],
            "description": e.get("description", ""),
            "core_skills": e.get("core_skills", []),
            "salary_range": e.get("salary_range", ""),
            "market_outlook": e.get("market_outlook", ""),
            "entry_advice": e.get("entry_advice", ""),
            "promotion_path": e.get("promotion_path", ""),
            "transfer_options": e.get("transfer_options", []),
            "score": round(s, 1),
        }
        for s, e in scored[:top_k]
    ]


class RAGService:
    """RAG 服务存根（ChromaDB 在 Python 3.12 下不兼容，已切换为 JSON 知识库降级方案）
    保留此类仅为兼容旧调用路径，实际检索由模块级 search_knowledge_base() 承担。
    """

    _ready = False  # 始终为 False，调用方可用此字段判断是否降级

    async def query_job_context(self, job_name: str, query: str, k: int = 2, **kwargs) -> List[Dict[str, Any]]:
        """兼容旧调用：转发至 JSON 知识库检索"""
        hits = search_knowledge_base(query or job_name, top_k=k)
        return [{"content": f"{h['description']} {h.get('market_outlook', '')}", "role": h["job"], "score": h["score"]} for h in hits]

    async def query_real_jd_context(self, job_name: str, k: int = 2) -> List[Dict[str, Any]]:
        return await self.query_job_context(job_name, job_name, k)


rag_service = RAGService()
