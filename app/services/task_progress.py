# -*- coding: utf-8 -*-
"""
报告任务进度存储 —— 可降级（Redis 共享 / 进程内）。

历史上报告进度是 `_common._task_store` 进程内 dict，单实例 OK，但 **多实例（--scale>1）
下报告进度轮询会 404**（CLAUDE.md 明列的 #1 规模化债：状态写在 A 实例，轮询打到 B 实例读不到）。

本模块把进度搬到既有可降级 `cache`（`app/core/redis_client`）：
  - 配置 REDIS_URL → 多实例共享，轮询任意实例都能读到；
  - 未配置 → 自动降级进程内（单实例行为不变，本地零依赖）。
进度是瞬态，用 TTL 自动回收，不污染持久层。每个 task_id 仅一个写者（其后台任务），
update 的 get→merge→set 无并发竞态。
"""

from typing import Any, Dict, Optional

from app.core.redis_client import cache, cache_is_distributed


class TaskProgressStore:
    PREFIX = "task:"
    TTL = 3600  # 进度保留 1h，足够前端轮询完一次报告生成

    async def create(self, task_id: str, **fields: Any) -> None:
        payload = {"task_id": task_id, **fields}   # task_id 自动入库，调用点无需重复传
        await cache.set(self.PREFIX + task_id, payload, ttl=self.TTL)

    async def update(self, task_id: str, **fields: Any) -> None:
        cur = await cache.get(self.PREFIX + task_id)
        cur = dict(cur) if isinstance(cur, dict) else {}
        cur.update(fields)
        await cache.set(self.PREFIX + task_id, cur, ttl=self.TTL)

    async def get(self, task_id: str) -> Optional[Dict]:
        return await cache.get(self.PREFIX + task_id)

    @staticmethod
    def backend() -> str:
        """当前后端：redis（多实例共享）/ in-process（单实例降级）。供 /metrics、/ready 观测。"""
        return "redis" if cache_is_distributed() else "in-process"


task_store = TaskProgressStore()
