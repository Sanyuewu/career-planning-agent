# -*- coding: utf-8 -*-
"""
写穿持久化存储（PersistentStore）。

为 bridge_flow 的运行时状态（会话 / 报告）提供 dict 兼容接口，
但每次写入透明持久化到 KVStore 表，启动时从 DB 回填到内存缓存。
目标：服务重启后会话与报告不丢失，且支持后续多实例（共享同一 DB）。

用法与普通 dict 基本一致：
    store[key] = value      # 写穿到 DB
    store.get(key)          # 读内存缓存
    store.save(key)         # 就地修改 value 内部字段后，显式落库
    del store[key]          # 删除并从 DB 移除

使用同步引擎做持久化（SQLite 写入极快）；持久化失败不影响请求主流程。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterator

from app.core.database import SessionLocal, init_db
from app.core.security_context import get_tenant, DEFAULT_TENANT
from app.core.pii import encrypt_text, decrypt_text
from app.models.db_models import KVStore

logger = logging.getLogger(__name__)

_tables_ready = False


def _ensure_tables() -> None:
    """幂等建表，保证 store 在 init_db 之前实例化也能正常工作。"""
    global _tables_ready
    if _tables_ready:
        return
    try:
        init_db()
        _tables_ready = True
    except Exception as e:
        logger.warning("建表失败: %s", e)


class PersistentStore:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self._mem: Dict[str, Dict] = {}
        _ensure_tables()
        self._load()

    # ── 启动回填 ────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            with SessionLocal() as db:
                rows = db.query(KVStore).filter(KVStore.namespace == self.namespace).all()
                for row in rows:
                    try:
                        self._mem[row.key] = json.loads(decrypt_text(row.value_json))
                    except (json.JSONDecodeError, TypeError):
                        continue
            logger.info("[store:%s] 回填 %d 条记录", self.namespace, len(self._mem))
        except Exception as e:
            # DB 不可用时退化为纯内存，不阻断启动
            logger.warning("[store:%s] 回填失败，降级纯内存: %s", self.namespace, e)

    # ── 多租户可见性（M0：行级隔离，按当前租户 contextvar 过滤）──────
    @staticmethod
    def _visible(value: Any) -> bool:
        """value 是否属于当前租户。存量无 tenant 字段者归 DEFAULT_TENANT。"""
        if not isinstance(value, dict):
            return False
        return value.get("tenant", DEFAULT_TENANT) == get_tenant()

    # ── 持久化 ──────────────────────────────────────────────────
    def _persist(self, key: str, value: Dict) -> None:
        try:
            # 写入即打上租户标签（已有者保留），存储层与读过滤共用同一标签
            if isinstance(value, dict):
                value.setdefault("tenant", get_tenant())
            sid = value.get("student_id") if isinstance(value, dict) else None
            tenant = value.get("tenant", DEFAULT_TENANT) if isinstance(value, dict) else DEFAULT_TENANT
            # PII 静态保护：value_json 落库前加密（无密钥时 no-op）；student_id/tenant 列保持明文供索引
            payload = encrypt_text(json.dumps(value, ensure_ascii=False, default=str))
            with SessionLocal() as db:
                obj = db.get(KVStore, {"namespace": self.namespace, "key": key})
                if obj is None:
                    obj = KVStore(namespace=self.namespace, key=key)
                    db.add(obj)
                obj.value_json = payload
                obj.student_id = sid
                obj.tenant = tenant
                obj.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning("[store:%s] 持久化失败 key=%s: %s", self.namespace, key, e)

    def _remove(self, key: str) -> None:
        try:
            with SessionLocal() as db:
                obj = db.get(KVStore, {"namespace": self.namespace, "key": key})
                if obj is not None:
                    db.delete(obj)
                    db.commit()
        except Exception as e:
            logger.warning("[store:%s] 删除失败 key=%s: %s", self.namespace, key, e)

    # ── dict 兼容接口（读操作按当前租户过滤）─────────────────────
    def __getitem__(self, key: str) -> Dict:
        value = self._mem[key]              # 缺失抛 KeyError
        if not self._visible(value):        # 跨租户视同不存在
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: Dict) -> None:
        self._mem[key] = value
        self._persist(key, value)           # 内部按当前租户打标签

    def __delitem__(self, key: str) -> None:
        self._mem.pop(key, None)
        self._remove(key)

    def __contains__(self, key: str) -> bool:
        value = self._mem.get(key)
        return value is not None and self._visible(value)

    def __iter__(self) -> Iterator[str]:
        return iter(k for k, v in self._mem.items() if self._visible(v))

    def __len__(self) -> int:
        return sum(1 for v in self._mem.values() if self._visible(v))

    def get(self, key: str, default: Any = None) -> Any:
        value = self._mem.get(key)
        return value if (value is not None and self._visible(value)) else default

    def values(self):
        return [v for v in self._mem.values() if self._visible(v)]

    def items(self):
        return [(k, v) for k, v in self._mem.items() if self._visible(v)]

    def keys(self):
        return [k for k, v in self._mem.items() if self._visible(v)]

    def save(self, key: str) -> None:
        """就地修改 value 内部字段后，显式落库。"""
        if key in self._mem:
            self._persist(key, self._mem[key])
