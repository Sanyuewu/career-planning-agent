# -*- coding: utf-8 -*-
"""
工具注册表 —— 按 FSM 状态裁剪 ReAct 可见的工具子集。

让 ReAct 在每个状态内"只看得到该阶段该用的工具"，既降低 LLM 误调用的概率，
也让 FSM 的阶段语义落到工具可见性这一硬约束上。
"""

from typing import Dict, List

from app.agents.fsm import State
from app.agents.tools import TOOL_SCHEMAS

# 状态 → 允许的工具名集合
STATE_TOOLS: Dict[State, List[str]] = {
    State.GREETING:  [],
    State.PROFILING: ["get_student_portrait"],
    State.MATCHING:  ["get_all_jobs", "get_job_portrait", "compute_match", "recommend_jobs"],
    State.PLANNING:  ["get_career_paths", "query_graph", "evaluate_output", "get_progress_summary"],
    State.REPORTING: ["generate_report", "get_progress_summary"],
    State.DONE:      [],
}

_SCHEMA_BY_NAME = {t["function"]["name"]: t for t in TOOL_SCHEMAS}


def tools_for(state: State) -> List[Dict]:
    """返回该状态下 ReAct 可见的工具 schema 列表。"""
    names = STATE_TOOLS.get(state, [])
    return [_SCHEMA_BY_NAME[n] for n in names if n in _SCHEMA_BY_NAME]


def tool_names_for(state: State) -> List[str]:
    return list(STATE_TOOLS.get(state, []))
