# -*- coding: utf-8 -*-
"""
成长闭环计算层（ProgressService）—— 让"变了多少 / 为什么变 / 行动完成没"可被算出。

设计：
  - **纯计算，无 LLM / FAISS 依赖**：diff_* 接受快照 dict 直接对比（可独立单测）；
    trend / attribute_growth / action_completion_rate 经 snapshot_store 读快照再算。
  - 输出全部为 JSON-ready dict（与 analytics.py 风格一致），供 Agent context 注入、
    报告 prompt、学生端曲线、院校看板共同消费。
  - **空数据优雅降级**：无快照时返回 `available: False`，调用方不崩。
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services import snapshot_store


# ════════════════════════════════════════════════════════════════
# 纯对比（接受快照 dict，无副作用，便于单测）
# ════════════════════════════════════════════════════════════════

def diff_portraits(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
    """两版画像快照对比（list_portrait_snapshots 的元素）。"""
    p_attrs = prev.get("portrait", {}) if prev else {}
    c_attrs = curr.get("portrait", {}) if curr else {}
    prev_skills = _skill_set(p_attrs.get("skills", []))
    curr_skills = _skill_set(c_attrs.get("skills", []))
    new_skills = [s for s in _skill_list(c_attrs.get("skills", [])) if s.lower() not in prev_skills]
    lost_skills = [s for s in _skill_list(p_attrs.get("skills", [])) if s.lower() not in curr_skills]
    return {
        "from_version": prev.get("version") if prev else None,
        "to_version": curr.get("version") if curr else None,
        "new_skills": new_skills,
        "lost_skills": lost_skills,
        "completeness_delta": _delta(prev, curr, "completeness_score"),
        "competitiveness_delta": _delta(prev, curr, "competitiveness_score"),
        "certificate_delta": len(c_attrs.get("certificates", []) or []) - len(p_attrs.get("certificates", []) or []),
        "project_delta": len(c_attrs.get("projects", []) or []) - len(p_attrs.get("projects", []) or []),
    }


def diff_matches(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
    """两次匹配快照对比（同一岗位才有意义；调用方负责按 job_name 取）。"""
    prev_missing = _skill_set(prev.get("missing_skills", []))
    curr_matched = _skill_list(curr.get("matched_skills", []))
    resolved = [s for s in curr_matched if s.lower() in prev_missing]  # 上次缺、这次补上的
    return {
        "job_name": curr.get("job_name", ""),
        "total_delta": round(_num(curr.get("total_match")) - _num(prev.get("total_match")), 1),
        "dimension_deltas": {
            dim: round(_num(curr.get(dim)) - _num(prev.get(dim)), 1)
            for dim in ("basic_match", "skill_match", "quality_match", "potential_match")
        },
        "resolved_missing": resolved,
        "still_missing": _skill_list(curr.get("missing_skills", [])),
        "eligible_changed": bool(prev.get("eligible")) != bool(curr.get("eligible")),
    }


# ════════════════════════════════════════════════════════════════
# 时序聚合（经 snapshot_store 读取）
# ════════════════════════════════════════════════════════════════

def trend(student_id: str, window_days: Optional[int] = None) -> Dict[str, Any]:
    """成长趋势：竞争力/完整度曲线 + 匹配分曲线 + 技能增长。供学生端曲线与看板消费。"""
    portraits = snapshot_store.list_portrait_snapshots(student_id)
    matches = snapshot_store.list_match_snapshots(student_id)
    if window_days:
        cutoff = _now().timestamp() - window_days * 86400
        portraits = [p for p in portraits if _ts(p.get("created_at")) >= cutoff]
        matches = [m for m in matches if _ts(m.get("created_at")) >= cutoff]

    if not portraits and not matches:
        return {"available": False, "student_id": student_id}

    comp_curve = [{"date": p["created_at"], "value": p.get("competitiveness_score")}
                  for p in portraits if p.get("competitiveness_score") is not None]
    complete_curve = [{"date": p["created_at"], "value": p.get("completeness_score")}
                      for p in portraits if p.get("completeness_score") is not None]
    match_curve = [{"date": m["created_at"], "job_name": m.get("job_name"),
                    "value": m.get("total_match")} for m in matches]

    # 技能增长：首版 vs 末版画像
    skill_growth: List[str] = []
    if len(portraits) >= 2:
        skill_growth = diff_portraits(portraits[0], portraits[-1])["new_skills"]

    return {
        "available": True,
        "student_id": student_id,
        "portrait_versions": len(portraits),
        "competitiveness_curve": comp_curve,
        "completeness_curve": complete_curve,
        "match_curve": match_curve,
        "competitiveness_delta": _curve_delta(comp_curve),
        "skill_growth": skill_growth,
    }


def attribute_growth(student_id: str, from_version: Optional[int] = None,
                     to_version: Optional[int] = None) -> Dict[str, Any]:
    """成长归因：分数上涨来自哪些新技能/证书/项目。缺省取首版→末版。"""
    portraits = snapshot_store.list_portrait_snapshots(student_id)
    if len(portraits) < 2:
        return {"available": False, "student_id": student_id,
                "reason": "历史画像不足两版，暂无法归因"}
    by_ver = {p["version"]: p for p in portraits}
    prev = by_ver.get(from_version, portraits[0])
    curr = by_ver.get(to_version, portraits[-1])
    d = diff_portraits(prev, curr)

    drivers: List[str] = []
    if d["new_skills"]:
        drivers.append(f"新增技能：{', '.join(d['new_skills'][:6])}")
    if d["certificate_delta"] > 0:
        drivers.append(f"新增 {d['certificate_delta']} 项证书")
    if d["project_delta"] > 0:
        drivers.append(f"新增 {d['project_delta']} 个项目经历")
    return {
        "available": True,
        "student_id": student_id,
        "from_version": d["from_version"],
        "to_version": d["to_version"],
        "competitiveness_delta": d["competitiveness_delta"],
        "completeness_delta": d["completeness_delta"],
        "new_skills": d["new_skills"],
        "drivers": drivers,
    }


def latest_match_progress(student_id: str, job_name: Optional[str] = None) -> Dict[str, Any]:
    """最近两次（同岗位）匹配对比，给 Agent / 报告一句"上次 X→这次 Y"。"""
    matches = snapshot_store.list_match_snapshots(student_id, job_name=job_name)
    if len(matches) < 2:
        if matches:
            return {"available": False, "latest_only": True, "job_name": matches[-1].get("job_name"),
                    "total_match": matches[-1].get("total_match")}
        return {"available": False}
    # 取末两次；若未指定 job_name，尽量取同一岗位的最近两次
    if not job_name:
        last_job = matches[-1].get("job_name")
        same = [m for m in matches if m.get("job_name") == last_job]
        if len(same) >= 2:
            prev, curr = same[-2], same[-1]
        else:
            prev, curr = matches[-2], matches[-1]
    else:
        prev, curr = matches[-2], matches[-1]
    d = diff_matches(prev, curr)
    d["available"] = True
    d["prev_total"] = round(_num(prev.get("total_match")), 1)
    d["curr_total"] = round(_num(curr.get("total_match")), 1)
    return d


def action_completion_rate(student_id: str) -> Dict[str, Any]:
    """当前生效行动计划的完成率与逾期统计（无计划→available False）。

    逾期仅在 item 有可解析的 due_date 且早于今天且未完成时计入——
    现阶段报告生成的计划 due_date 多为空，故逾期为 best-effort，不虚报。
    """
    plan = snapshot_store.get_active_action_plan(student_id)
    if not plan:
        return {"available": False, "student_id": student_id}
    items = plan.get("items", [])
    total = len(items)
    done = sum(1 for it in items if it.get("status") == "done")
    overdue = 0
    now_ts = _now().timestamp()
    for it in items:
        if it.get("status") == "done":
            continue
        due = _ts(it.get("due_date"))
        if due and due < now_ts:
            overdue += 1
    return {
        "available": True,
        "student_id": student_id,
        "plan_id": plan.get("id"),
        "job_name": plan.get("job_name"),
        "total": total,
        "done": done,
        "in_progress": total - done,
        "overdue": overdue,
        "completion_pct": round(done / total * 100, 1) if total else 0.0,
    }


def agent_context_summary(student_id: str) -> Dict[str, Any]:
    """给 Agent / Chat 注入的一站式成长上下文（趋势 + 最近匹配进展 + 行动进度）。

    全部 best-effort：任一子项无数据则该字段 available=False，整体不抛。
    """
    return {
        "growth": attribute_growth(student_id),
        "match_progress": latest_match_progress(student_id),
        "actions": action_completion_rate(student_id),
    }


def format_summary_text(summary: Optional[Dict[str, Any]]) -> str:
    """把 agent_context_summary 折成注入 LLM prompt 的紧凑成长上下文（单一事实源）。

    仅拼 available=True 的部分；全无数据返回 ""，让模型知道这是首次评估。
    Agent 与 Chat 共用此格式，避免措辞漂移。
    """
    if not isinstance(summary, dict):
        return ""
    parts: List[str] = []

    g = summary.get("growth") or {}
    if g.get("available"):
        delta = g.get("competitiveness_delta")
        if delta is not None:
            sign = "+" if delta >= 0 else ""
            parts.append(f"竞争力较首次评估变化 {sign}{delta} 分")
        if g.get("drivers"):
            parts.append("成长来源：" + "；".join(g["drivers"][:3]))

    mp = summary.get("match_progress") or {}
    if mp.get("available"):
        job = mp.get("job_name", "目标岗位")
        td = mp.get("total_delta", 0)
        parts.append(f"「{job}」匹配分：上次 {mp.get('prev_total')} → 这次 {mp.get('curr_total')}"
                     f"（{'+' if td >= 0 else ''}{td}）")
        if mp.get("resolved_missing"):
            parts.append("已补上此前缺失技能：" + "、".join(mp["resolved_missing"][:4]))

    ac = summary.get("actions") or {}
    if ac.get("available"):
        line = f"行动计划完成 {ac.get('done')}/{ac.get('total')}（{ac.get('completion_pct')}%）"
        if ac.get("overdue"):
            line += f"，{ac['overdue']} 项已逾期"
        parts.append(line)

    return ("\n- " + "\n- ".join(parts)) if parts else ""


# ════════════════════════════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════════════════════════════

def _num(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _delta(prev: Optional[Dict], curr: Optional[Dict], key: str) -> Optional[float]:
    if not prev or not curr or prev.get(key) is None or curr.get(key) is None:
        return None
    return round(_num(curr.get(key)) - _num(prev.get(key)), 1)


def _skill_list(skills: Any) -> List[str]:
    out = []
    for s in (skills or []):
        if isinstance(s, dict):
            s = s.get("name", "")
        if isinstance(s, str) and s.strip():
            out.append(s.strip())
    return out


def _skill_set(skills: Any) -> set:
    return {s.lower() for s in _skill_list(skills)}


def _curve_delta(curve: List[Dict]) -> Optional[float]:
    vals = [c["value"] for c in curve if c.get("value") is not None]
    if len(vals) < 2:
        return None
    return round(_num(vals[-1]) - _num(vals[0]), 1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(iso_str: Optional[str]) -> float:
    """ISO 字符串 → epoch 秒；空/不可解析返回 0（视为很久以前，不计入窗口）。"""
    if not iso_str or not isinstance(iso_str, str):
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0
