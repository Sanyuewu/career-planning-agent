# -*- coding: utf-8 -*-
"""
异步键值存储（AsyncKVStore）。

D-B：会话/报告（文档型）从 PersistentStore（同步写穿 + 全量内存）升级为
按 id 异步读写 + Redis 读穿缓存——不再每实例全量载入内存，写入不阻塞事件循环。
底层仍是 kv_store 表（与 D-A 学生/匹配同表不同 namespace），无需新迁移。

用法（均为 async）：
    await store.get(key)            # 读穿缓存，未命中查 DB
    await store.save(key, value)    # upsert + 更新缓存
    await store.delete(key)         # 删行 + 失效缓存
    await store.exists(key)
    await store.values()            # 该 namespace 全部值（统计用）
    await store.count_by_student(sid)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.core.redis_client import cache
from app.config import settings
from app.core.security_context import get_tenant
from app.core.pii import encrypt_text, decrypt_text
from app.models.db_models import KVStore
from app.services.state_store import _ensure_tables

logger = logging.getLogger(__name__)


class AsyncKVStore:
    """文档型存储（report/chat）。M0：所有读写按当前租户（contextvar）行级隔离。"""

    def __init__(self, namespace: str):
        self.namespace = namespace
        _ensure_tables()   # 同步幂等建表，保证 kv_store 存在

    def _ck(self, key: str) -> str:
        # 缓存 key 带租户，避免跨租户缓存串读
        return f"kv:{get_tenant()}:{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Dict]:
        cached = await cache.get(self._ck(key))
        if cached is not None:
            return cached
        tenant = get_tenant()
        async with AsyncSessionLocal() as db:
            obj = await db.get(KVStore, {"namespace": self.namespace, "key": key})
            if obj is None or obj.tenant != tenant:   # 跨租户不可见
                return None
            try:
                val = json.loads(decrypt_text(obj.value_json))
            except (json.JSONDecodeError, TypeError):
                return None
        await cache.set(self._ck(key), val, ttl=settings.CACHE_TTL)
        return val

    async def save(self, key: str, value: Dict) -> None:
        sid = value.get("student_id") if isinstance(value, dict) else None
        # PII 静态保护：value_json 落库前加密（无密钥时 no-op）
        payload = encrypt_text(json.dumps(value, ensure_ascii=False, default=str))
        async with AsyncSessionLocal() as db:
            obj = await db.get(KVStore, {"namespace": self.namespace, "key": key})
            if obj is None:
                obj = KVStore(namespace=self.namespace, key=key)
                db.add(obj)
            obj.value_json = payload
            obj.student_id = sid
            obj.tenant = get_tenant()
            obj.updated_at = datetime.utcnow()
            await db.commit()
        await cache.set(self._ck(key), value, ttl=settings.CACHE_TTL)

    async def delete(self, key: str) -> None:
        tenant = get_tenant()
        async with AsyncSessionLocal() as db:
            obj = await db.get(KVStore, {"namespace": self.namespace, "key": key})
            if obj is not None and obj.tenant == tenant:
                await db.delete(obj)
                await db.commit()
        await cache.delete(self._ck(key))

    async def exists(self, key: str) -> bool:
        if await cache.get(self._ck(key)) is not None:
            return True
        tenant = get_tenant()
        async with AsyncSessionLocal() as db:
            obj = await db.get(KVStore, {"namespace": self.namespace, "key": key})
            return obj is not None and obj.tenant == tenant

    async def values(self) -> List[Dict]:
        """当前租户在该 namespace 下的全部值（统计/列表用，按需查询而非常驻内存）。"""
        out: List[Dict] = []
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(KVStore.value_json).where(
                    KVStore.namespace == self.namespace,
                    KVStore.tenant == get_tenant(),
                )
            )).scalars().all()
        for raw in rows:
            try:
                out.append(json.loads(decrypt_text(raw)))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    async def count_by_student(self, student_id: str) -> int:
        async with AsyncSessionLocal() as db:
            n = (await db.execute(
                select(func.count()).select_from(KVStore).where(
                    KVStore.namespace == self.namespace,
                    KVStore.student_id == student_id,
                    KVStore.tenant == get_tenant(),
                )
            )).scalar_one()
        return int(n or 0)
