# -*- coding: utf-8 -*-
"""
Redis 客户端 —— 可优雅降级。

REDIS_URL 配置时使用真实 Redis（缓存 / 分布式锁 / 限流）；
未配置或连接失败时，自动降级为进程内实现（dict 缓存 + asyncio 锁），
保证本地开发无需 Redis 也能运行，生产配置后即获得多实例共享能力。

统一接口：
  await cache.get(key) / await cache.set(key, value, ttl) / await cache.delete(key)
  await cache.incr_with_expire(key, window)  # 限流计数
"""

import json
import time
from typing import Any, Optional

from app.config import settings

try:
    import redis.asyncio as aioredis  # redis>=4.2 自带 asyncio
    _REDIS_LIB = True
except ImportError:
    _REDIS_LIB = False


class _InProcessCache:
    """进程内降级实现：dict + TTL + asyncio.Lock。仅单进程有效。"""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}   # key -> (value, expire_ts)
        self._counters: dict[str, tuple[int, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        value, expire = item
        if expire and time.time() > expire:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expire = time.time() + ttl if ttl else 0
        self._store[key] = (value, expire)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr_with_expire(self, key: str, window: int) -> int:
        now = time.time()
        count, expire = self._counters.get(key, (0, now + window))
        if now > expire:
            count, expire = 0, now + window
        count += 1
        self._counters[key] = (count, expire)
        return count

    async def close(self):
        self._store.clear()


class _RedisCache:
    """真实 Redis 实现。"""

    def __init__(self, client):
        self._r = client

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def delete(self, key: str) -> None:
        try:
            await self._r.delete(key)
        except Exception:
            pass

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raw = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        if ttl:
            await self._r.set(key, raw, ex=ttl)
        else:
            await self._r.set(key, raw)

    async def incr_with_expire(self, key: str, window: int) -> int:
        count = await self._r.incr(key)
        if count == 1:
            await self._r.expire(key, window)
        return count

    async def close(self):
        try:
            await self._r.aclose()
        except Exception:
            pass


# ── 单例：启动时按配置选择实现 ──────────────────────────────────
_cache_impl = None


def _build_cache():
    if settings.REDIS_URL and _REDIS_LIB:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            return _RedisCache(client)
        except Exception as e:  # 连接失败也降级
            print(f"[redis] 连接失败，降级为进程内缓存: {e}")
    return _InProcessCache()


def get_cache():
    global _cache_impl
    if _cache_impl is None:
        _cache_impl = _build_cache()
    return _cache_impl


cache = get_cache()


def cache_is_distributed() -> bool:
    """当前是否使用真实 Redis（多实例共享）。"""
    return isinstance(get_cache(), _RedisCache)
