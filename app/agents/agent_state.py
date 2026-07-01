# -*- coding: utf-8 -*-
"""
Agent 起始状态推导 —— 让编排器"了解你、接着走"，而非每次从 GREETING 重问。

纯函数（不 import youtu/career_agent）：读学生当前真实状态（画像完整度 / 是否匹配过 /
是否有报告），推出 FSM 应从哪个阶段起步，并预置 ctx 供守卫与 prompt 用。
与前端 nextStep 同源的判定逻辑——产品上"主页下一步"和"Agent 接着走"指向同一处。
"""

from typing import Any, Dict, Tuple

from app.agents.fsm import State, COMPLETENESS_GATE
from app.services.student_graph_service import student_graph_service
from app.services import progress_service


def derive_start_state(student_id: str) -> Tuple[State, Dict[str, Any]]:
    """返回 (起始状态, 预置 ctx)。

    PROFILING：无画像或完整度 < 门槛 → 先补全。
    MATCHING ：有画像但没匹配过 → 去匹配。
    PLANNING ：已匹配（无论有无报告）→ 直接规划路径/报告（接着走）。
    """
    node = student_graph_service.get_student(student_id)
    attrs = (node or {}).get("attributes", {})
    completeness = float(attrs.get("completeness_score", 0) or 0)

    ctx: Dict[str, Any] = {}
    if completeness:
        ctx["completeness_score"] = completeness
    if attrs.get("name"):
        ctx["student_name"] = attrs.get("name")

    if not node or completeness < COMPLETENESS_GATE:
        return State.PROFILING, ctx

    matches = student_graph_service.get_student_matches(student_id)
    if not matches:
        return State.MATCHING, ctx

    # 已匹配：预置目标岗 + has_match，直接进规划（不重做画像/匹配）
    ctx["has_match"] = True
    best = max(matches, key=lambda m: float(m.get("attributes", {}).get("total_match", 0) or 0))
    ctx["target_job"] = best.get("job_name")
    return State.PLANNING, ctx


def opening_line(state: State, ctx: Dict[str, Any]) -> str:
    """据起始状态给一句"接着走"的开场白（不是每次都'你好，从头开始'）。"""
    name = ctx.get("student_name") or "同学"
    if state == State.PROFILING:
        return f"{name}，我们先把你的职业画像补全，匹配才会准。"
    if state == State.MATCHING:
        return f"{name}，你的画像已就绪，我直接帮你做人岗匹配。"
    job = ctx.get("target_job")
    if state == State.PLANNING and job:
        return f"{name}，接着上次——你匹配过「{job}」，我来帮你规划发展路径和报告。"
    return f"{name}，我们继续推进你的职业规划。"
