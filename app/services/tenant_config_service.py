# -*- coding: utf-8 -*-
"""
租户级产品化配置（M2）：每所院校可配匹配权重 / 岗位库 / 报告模板增补。

按当前租户（contextvar）读 `Tenant.config_json`（M0 已建该列），进程内缓存 + 默认。
**可降级**：无配置 = canonical 默认，行为与改造前一致；不破坏单机基线。
配置变更经 admin 路由写入并失效缓存。
"""

import json
import logging
from typing import Dict, List, Optional

from app.core.database import SessionLocal
from app.core.security_context import get_tenant
from app.models.db_models import Tenant
from app.services import match_rules

logger = logging.getLogger(__name__)

# 配置白名单 + 默认（None/"" 表示"用系统默认"）
DEFAULT_CONFIG: Dict = {
    "match_weights": None,             # None → 用 preset / 红线默认权重
    "job_library": None,               # None → 全部岗位
    "report_extra_instructions": "",   # 追加进报告 prompt 的院校定制要求
}

_cache: Dict[str, Dict] = {}


def _load(tenant: str) -> Dict:
    if tenant in _cache:
        return _cache[tenant]
    cfg = dict(DEFAULT_CONFIG)
    try:
        with SessionLocal() as db:
            t = db.get(Tenant, tenant)
            if t and t.config_json:
                data = json.loads(t.config_json)
                if isinstance(data, dict):
                    for k in cfg:
                        if data.get(k) is not None:
                            cfg[k] = data[k]
    except Exception as e:
        logger.warning("[tenant_config] 读取失败 tenant=%s: %s", tenant, e)
    _cache[tenant] = cfg
    return cfg


def get_config(tenant: Optional[str] = None) -> Dict:
    return _load(tenant or get_tenant())


def invalidate(tenant: Optional[str] = None) -> None:
    _cache.pop(tenant or get_tenant(), None)


def save_config(tenant: str, config: Dict) -> Dict:
    """写入 Tenant.config_json（仅取白名单键）并失效缓存。"""
    clean = {k: config.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    with SessionLocal() as db:
        t = db.get(Tenant, tenant)
        if t is None:
            t = Tenant(id=tenant, name=tenant)
            db.add(t)
        t.config_json = json.dumps(clean, ensure_ascii=False)
        db.commit()
    invalidate(tenant)
    return clean


# ── 给匹配/岗位/报告调用方的便捷解析（租户覆盖 → preset → 红线默认）──
def effective_match_weights(preset: Optional[str] = None,
                            tenant: Optional[str] = None) -> Dict[str, float]:
    mw = get_config(tenant).get("match_weights")
    if isinstance(mw, dict) and mw:
        return match_rules.resolve_weights(weights=mw)
    return match_rules.resolve_weights(preset=preset)


def filter_jobs(titles: List[str], tenant: Optional[str] = None) -> List[str]:
    """按租户岗位库白名单过滤（None=全部）。"""
    lib = get_config(tenant).get("job_library")
    if not lib:
        return titles
    allow = set(lib)
    return [t for t in titles if t in allow]


def report_extra_instructions(tenant: Optional[str] = None) -> str:
    return get_config(tenant).get("report_extra_instructions") or ""
