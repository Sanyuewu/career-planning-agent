# -*- coding: utf-8 -*-
"""
平台运营数据层 —— **跨租户**只读聚合（平台超管专用）。

与院校/学生层相反：这里**刻意绕过 `get_tenant()` 租户过滤**，按 tenant 分组看全平台。
仅供 `routers/platform.py`（`require_role("platform_admin")`）调用——超管是唯一
获授权跨租户读的角色。只读、不触发 youtu、不写。
"""

from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models.db_models import KVStore, Tenant, User, PortraitSnapshot
from app.services.snapshot_store import _bucket_monthly_avg

PLATFORM_TENANT = "__platform__"   # sentinel，超管自身所属，不算"学校"


def platform_totals() -> Dict[str, Any]:
    """全平台业务量：学校 / 学生 / 报告 / 匹配 总数。"""
    with SessionLocal() as db:
        tenants = db.execute(
            select(func.count()).select_from(Tenant).where(Tenant.id != PLATFORM_TENANT)
        ).scalar() or 0
        students = db.execute(
            select(func.count()).select_from(KVStore).where(KVStore.namespace == "student")
        ).scalar() or 0
        reports = db.execute(
            select(func.count()).select_from(KVStore).where(KVStore.namespace == "report")
        ).scalar() or 0
        matches = db.execute(
            select(func.count()).select_from(KVStore).where(KVStore.namespace == "match")
        ).scalar() or 0
    return {"tenants": int(tenants), "students": int(students),
            "reports": int(reports), "matches": int(matches)}


def tenants_with_stats() -> List[Dict[str, Any]]:
    """各学校（租户）指标：学生数 / 教师数 / 报告数 / 平均竞争力 / 环比提升%。按提升% 降序。"""
    with SessionLocal() as db:
        tenants = db.execute(select(Tenant).where(Tenant.id != PLATFORM_TENANT)).scalars().all()
        scount = dict(db.execute(
            select(KVStore.tenant, func.count()).where(KVStore.namespace == "student").group_by(KVStore.tenant)
        ).all())
        rcount = dict(db.execute(
            select(KVStore.tenant, func.count()).where(KVStore.namespace == "report").group_by(KVStore.tenant)
        ).all())
        tcount: Dict[str, int] = {}
        for tid, role, c in db.execute(
            select(User.tenant_id, User.role, func.count()).group_by(User.tenant_id, User.role)
        ).all():
            if role == "teacher":
                tcount[tid] = int(c)
        psnaps = db.execute(
            select(PortraitSnapshot.tenant, PortraitSnapshot.created_at, PortraitSnapshot.competitiveness_score)
        ).all()

    by_tenant = defaultdict(list)
    for ten, dt, comp in psnaps:
        if comp is not None:
            by_tenant[ten].append((dt, comp))

    out = []
    for t in tenants:
        pairs = by_tenant.get(t.id, [])
        avg = round(sum(c for _, c in pairs) / len(pairs), 1) if pairs else 0.0
        series = _bucket_monthly_avg(pairs)
        imp = None
        if len(series) >= 2 and series[0]["avg"]:
            imp = round((series[-1]["avg"] - series[0]["avg"]) / series[0]["avg"] * 100, 1)
        out.append({
            "id": t.id, "name": t.name,
            "student_count": int(scount.get(t.id, 0)),
            "teacher_count": tcount.get(t.id, 0),
            "report_count": int(rcount.get(t.id, 0)),
            "avg_competitiveness": avg,
            "improvement_pct": imp,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        })
    out.sort(key=lambda x: (x["improvement_pct"] is None, -(x["improvement_pct"] or 0)))
    return out
