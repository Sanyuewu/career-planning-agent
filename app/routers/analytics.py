# -*- coding: utf-8 -*-
"""
院校分析看板（M1，院校侧/买单方业务线）。

只读聚合，按角色数据范围：admin=本租户全部、teacher=本人所带班级的学生。
**不触发 youtu 模型**——全部从已落库的画像/匹配/报告记录聚合，故 CI 与响应都快。
（刻意不 import `_common`，避免拉入 career_graphrag_service → youtu 重型加载；
 报告计数自建一个 `AsyncKVStore("report")` 实例，与 `_common._report_store` 同表同 namespace。）
"""

from collections import Counter

from fastapi import APIRouter, Depends, Query

from app.services.student_graph_service import student_graph_service
from app.services.async_store import AsyncKVStore
from app.services.student_directory import scoped_students, roster   # 单源 join + 范围门
from app.services import snapshot_store
from app.routers.auth import require_role

router = APIRouter(prefix="/api/analytics", tags=["院校分析"])

_report_store = AsyncKVStore("report")   # 与 _common 同表同 namespace，仅用于报告计数


def _attrs(s: dict) -> dict:
    return s.get("attributes", s)


def _matches(sid: str) -> list:
    return student_graph_service.get_student_matches(sid) if sid else []


# ── 端点（全部 teacher/admin 可见，student → 403）────────────────
@router.get("/overview")
async def overview(user: dict = Depends(require_role("teacher", "admin"))):
    """概览 KPI：学生数 / 有画像 / 平均完整度·竞争力 / 有匹配 / 就业意愿分布。"""
    students = scoped_students(user)
    n = len(students)
    comp = [float(_attrs(s).get("completeness_score", 0) or 0) for s in students]
    compet = [float(_attrs(s).get("competitiveness_score", 0) or 0) for s in students]
    with_match, intents = 0, Counter()
    for s in students:
        a = _attrs(s)
        if a.get("student_id") and _matches(a["student_id"]):
            with_match += 1
        ci = (a.get("career_intent") or "").strip()
        if ci:
            intents[ci] += 1
    return {
        "student_count": n,
        "with_portrait": sum(1 for c in comp if c > 0),
        "avg_completeness": round(sum(comp) / n, 1) if n else 0,
        "avg_competitiveness": round(sum(compet) / n, 1) if n else 0,
        "with_match": with_match,
        "intent_distribution": [{"intent": k, "count": v} for k, v in intents.most_common(8)],
    }


@router.get("/competitiveness_distribution")
async def competitiveness_distribution(user: dict = Depends(require_role("teacher", "admin"))):
    """竞争力分桶（待提升<55 / 中 55–75 / 强 ≥75）。"""
    students = scoped_students(user)
    buckets = {"待提升": 0, "中": 0, "强": 0}
    for s in students:
        c = float(_attrs(s).get("competitiveness_score", 0) or 0)
        buckets["强" if c >= 75 else "中" if c >= 55 else "待提升"] += 1
    labels = {"待提升": "待提升(<55)", "中": "中(55-75)", "强": "强(≥75)"}
    return {"distribution": [{"label": labels[k], "count": v} for k, v in buckets.items()]}


@router.get("/skill_gaps")
async def skill_gaps(top_n: int = Query(10, ge=1, le=30),
                     user: dict = Depends(require_role("teacher", "admin"))):
    """技能缺口热力：聚合可见学生匹配记录的 missing_skills → top-N。"""
    students = scoped_students(user)
    counter = Counter()
    for s in students:
        sid = _attrs(s).get("student_id")
        for m in _matches(sid):
            for sk in (m.get("attributes", {}).get("missing_skills") or []):
                if sk:
                    counter[sk] += 1
    return {"skill_gaps": [{"skill": k, "count": v} for k, v in counter.most_common(top_n)]}


@router.get("/at_risk")
async def at_risk(user: dict = Depends(require_role("teacher", "admin"))):
    """预警名单：竞争力<55 或 完整度<70 或 无匹配/无报告，附命中原因。"""
    students = scoped_students(user)
    report_sids = {r.get("student_id") for r in await _report_store.values() if r.get("student_id")}
    out = []
    for s in students:
        a = _attrs(s)
        sid = a.get("student_id")
        compet = float(a.get("competitiveness_score", 0) or 0)
        comp = float(a.get("completeness_score", 0) or 0)
        reasons = []
        if compet < 55:
            reasons.append("竞争力偏低")
        if comp < 70:
            reasons.append("画像不完整")
        if not _matches(sid):
            reasons.append("未做人岗匹配")
        if sid not in report_sids:
            reasons.append("无生涯报告")
        if reasons:
            out.append({"student_id": sid, "name": a.get("name", ""),
                        "competitiveness": round(compet), "completeness": round(comp),
                        "reasons": reasons})
    out.sort(key=lambda x: x["competitiveness"])
    return {"at_risk": out, "count": len(out)}


@router.get("/students")
async def students_roster(user: dict = Depends(require_role("teacher", "admin"))):
    """班级/全校学生 roster（复用 `student_directory.roster`，与管理面同源）。"""
    r = roster(user)
    return {"students": r, "count": len(r)}


@router.get("/trends")
async def trends(user: dict = Depends(require_role("teacher", "admin"))):
    """成长趋势（买单价值"全校在变好"）：复用成长闭环快照，按角色范围做群体时序聚合。
    竞争力/匹配分按月曲线 + 环比提升% + 行动完成率。只读、不触发 youtu。"""
    students = scoped_students(user)
    ids = [_attrs(s).get("student_id") for s in students if _attrs(s).get("student_id")]

    comp = snapshot_store.cohort_competitiveness_series(ids)
    match = snapshot_store.cohort_match_series(ids)
    action = snapshot_store.cohort_action_completion(ids)

    improvement = None
    if len(comp) >= 2 and comp[0]["avg"]:
        improvement = round((comp[-1]["avg"] - comp[0]["avg"]) / comp[0]["avg"] * 100, 1)

    return {
        "cohort_size": len(ids),
        "competitiveness_series": comp,
        "match_series": match,
        "improvement_pct": improvement,
        "action_completion": action,
        "available": bool(comp or match),
    }
