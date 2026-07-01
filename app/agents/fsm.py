# -*- coding: utf-8 -*-
"""
业务五阶段状态机（FSM）。

FSM 负责确定性的流程门控：定义状态顺序、每个状态的子目标、以及状态间
转移的硬守卫（guard）。ReAct 在单个状态内做动态推理与工具调用，但能否
跨状态由 FSM 在代码层强制裁决——这是"确定性流程"与"LLM 自由推理"的分界。

硬门槛：
  PROFILING → MATCHING : completeness_score ≥ COMPLETENESS_GATE，否则拒绝、引导补全
  MATCHING  → PLANNING : 已完成至少一次人岗匹配
  PLANNING  → REPORTING: 已检索职业路径
（基础要求"一票否决"在 tools.compute_match 内实现，属匹配维度内的硬约束）
"""

from enum import Enum
from typing import Dict, List, Tuple


class State(str, Enum):
    GREETING = "GREETING"
    PROFILING = "PROFILING"
    MATCHING = "MATCHING"
    PLANNING = "PLANNING"
    REPORTING = "REPORTING"
    DONE = "DONE"


# 线性推进顺序
ORDER: List[State] = [
    State.GREETING, State.PROFILING, State.MATCHING,
    State.PLANNING, State.REPORTING, State.DONE,
]

# 画像完整度硬门槛
COMPLETENESS_GATE = 70

# 各状态的子目标（注入 ReAct system prompt，约束本阶段该做什么）
STATE_GOAL: Dict[State, str] = {
    State.GREETING:  "向用户问候并确认开始职业规划。无需调用工具。",
    State.PROFILING: "调用 get_student_portrait 获取学生七维度画像，评估画像完整度。",
    State.MATCHING:  "基于学生画像，调用 recommend_jobs 批量推荐，或对指定岗位调用 compute_match，完成人岗匹配。",
    State.PLANNING:  "对目标岗位调用 get_career_paths 查询晋升/转岗路径，必要时用 query_graph 检索行业信息。",
    State.REPORTING: "调用 generate_report 生成完整职业发展报告。",
    State.DONE:      "流程已完成。",
}


def next_state(cur: State) -> State:
    idx = ORDER.index(cur)
    return ORDER[min(idx + 1, len(ORDER) - 1)]


def can_advance(state: State, ctx: Dict) -> Tuple[bool, str]:
    """
    判断当前状态是否满足"离开本状态、进入下一状态"的硬守卫。
    返回 (是否允许, 受阻原因)。受阻时上层应停下并引导用户补全。
    """
    if state == State.PROFILING:
        score = ctx.get("completeness_score", 0) or 0
        if score < COMPLETENESS_GATE:
            return False, (
                f"画像完整度 {score} 低于门槛 {COMPLETENESS_GATE}，"
                "请先补全技能、学历、项目经历等关键信息再进行匹配。"
            )
    elif state == State.MATCHING:
        if not ctx.get("has_match"):
            return False, "尚未完成任何人岗匹配，无法进入路径规划。"
    elif state == State.PLANNING:
        if not ctx.get("has_paths"):
            return False, "尚未检索到职业发展路径，无法生成报告。"
    return True, ""
