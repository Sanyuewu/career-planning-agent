# -*- coding: utf-8 -*-
"""
学生目录：把"账号(User) ⨝ 画像(kv_store) ⨝ 匹配"的 **app 级 join** 收敛到一处，
供院校分析看板（M1 `analytics`）与院校管理（M5 `admin`）共用，避免 join 与
数据范围逻辑被复制（复制 = 漂移 = 越权风险）。

数据范围门 `visible_student_ids` 在 `app/routers/auth.py`（安全单一事实源）；
本模块只做"取范围 + 拼画像/匹配摘要"，**不触发 youtu 模型**（只读已落库数据）。
"""

from typing import Dict, List

from app.routers.auth import visible_student_ids
from app.services.student_graph_service import student_graph_service


def _attrs(s: Dict) -> Dict:
    return s.get("attributes", s)


def scoped_students(user: Dict) -> List[Dict]:
    """当前租户内、user 可见的学生节点（含 kv_store 画像）。范围门见 auth。"""
    students = student_graph_service.get_all_students()   # 已按租户过滤
    vis = visible_student_ids(user)
    if vis is None:
        return students
    return [s for s in students if _attrs(s).get("student_id") in vis]


def roster(user: Dict) -> List[Dict]:
    """学生 roster 摘要（看板下钻 / 管理名册共用）：账号画像 + 最佳匹配 + 有无画像。"""
    out: List[Dict] = []
    for s in scoped_students(user):
        a = _attrs(s)
        sid = a.get("student_id")
        ms = student_graph_service.get_student_matches(sid) if sid else []
        best_job, best = "", 0.0
        if ms:
            bm = max(ms, key=lambda m: float(m.get("attributes", {}).get("total_match", 0) or 0))
            best = float(bm.get("attributes", {}).get("total_match", 0) or 0)
            best_job = bm.get("job_name", "")
        out.append({
            "student_id": sid,
            "name": a.get("name", ""),
            "completeness": round(float(a.get("completeness_score", 0) or 0)),
            "competitiveness": round(float(a.get("competitiveness_score", 0) or 0)),
            "best_match": round(best),
            "best_job": best_job,
            "career_intent": a.get("career_intent", ""),
            "has_profile": bool(a.get("name") or a.get("skills")),
        })
    out.sort(key=lambda x: -x["competitiveness"])
    return out
