# -*- coding: utf-8 -*-
"""
检索服务 HTTP 客户端。

当配置了 RETRIEVAL_SERVICE_URL 时，把重型的自然语言检索 query() 调用
转发到独立的检索微服务（HTTP），从而让该负载可独立扩容；未配置时不启用，
由 youtu_retriever_service 走进程内检索（降级）。

内置：超时、重试、简单熔断（连续失败打开、冷却后半开）、Redis 热点缓存。
注意：结构化索引（jobs_index/career_paths）与匹配用的 encoder 仍在进程内，
本客户端只负责 NL query() 这一条重链路。
"""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.redis_client import cache

logger = logging.getLogger(__name__)


class _CircuitBreaker:
    """极简熔断：连续失败 >= threshold 打开；冷却 cooldown 秒后半开试探。"""
    def __init__(self, threshold: int = 3, cooldown: int = 30):
        self.threshold = threshold
        self.cooldown = cooldown
        self._fails = 0
        self._opened_at = 0.0

    def allow(self) -> bool:
        if self._fails < self.threshold:
            return True
        # 已打开：冷却结束则半开放行一次
        if time.time() - self._opened_at >= self.cooldown:
            return True
        return False

    def record_success(self) -> None:
        self._fails = 0
        self._opened_at = 0.0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= self.threshold:
            self._opened_at = time.time()


class RetrievalClient:
    def __init__(self):
        self.base_url = settings.RETRIEVAL_SERVICE_URL.rstrip("/")
        self.timeout = settings.RETRIEVAL_TIMEOUT
        self._breaker = _CircuitBreaker()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout, trust_env=False)
        return self._client

    @staticmethod
    def _cache_key(question: str, top_k: int) -> str:
        h = hashlib.md5(f"{question}|{top_k}".encode("utf-8")).hexdigest()
        return f"retrieval:{h}"

    async def query(self, question: str, top_k: int = 10) -> Optional[Dict[str, Any]]:
        """
        远程检索。成功返回结果 dict；不可用/失败返回 None（调用方据此降级到进程内）。
        """
        if not self.enabled or not self._breaker.allow():
            return None

        # 热点缓存
        key = self._cache_key(question, top_k)
        cached = await cache.get(key)
        if cached is not None:
            return cached

        last_err = None
        for attempt in range(2):
            try:
                client = await self._get_client()
                resp = await client.post(
                    f"{self.base_url}/retrieve",
                    json={"query": question, "top_k": top_k},
                )
                resp.raise_for_status()
                data = resp.json()
                self._breaker.record_success()
                await cache.set(key, data, ttl=settings.CACHE_TTL)
                return data
            except Exception as e:
                last_err = e
                logger.warning("[retrieval] 远程检索失败 (try %d): %s", attempt + 1, e)

        self._breaker.record_failure()
        logger.warning("[retrieval] 远程检索不可用，降级进程内: %s", last_err)
        return None

    async def health(self) -> bool:
        if not self.enabled:
            return False
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/health")
            return resp.status_code == 200 and resp.json().get("ready", False)
        except Exception:
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


retrieval_client = RetrievalClient()
