# -*- coding: utf-8 -*-
"""Agent 主编排路由：FSM 五阶段状态门控 + 状态内 ReAct + SSE 流式推送。"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.career_agent import career_agent
from app.routers._common import AgentRunRequest
from app.routers.auth import get_current_user, assert_student_access

router = APIRouter(tags=["Agent"])


@router.post("/api/agent/run")
async def agent_run(req: AgentRunRequest, user: dict = Depends(get_current_user)):
    """
    FSM Agent 主编排路径：五阶段状态门控 + 状态内 ReAct + SSE 流式推送。
    流程 GREETING→PROFILING→MATCHING→PLANNING→REPORTING→DONE，
    转移由 FSM 硬守卫裁决（画像完整度门槛、匹配/路径前置条件）。

    SSE 事件类型：
      {"type":"run_start",  "run_id":...}
      {"type":"state",      "state":"PROFILING", "goal":"本阶段任务"}
      {"type":"token",      "delta":"思考增量", "state":...}
      {"type":"thought_end","state":...}
      {"type":"tool_call",  "name":"工具名", "args":{...}, "state":...}
      {"type":"tool_result","name":"工具名", "result":{...}, "summary":"摘要"}
      {"type":"transition", "from":"PROFILING", "to":"MATCHING"}
      {"type":"blocked",    "state":..., "reason":"门槛未达"}
      {"type":"done",       "content":"最终结论"}
      {"type":"error",      "content":"错误信息"}
    """
    assert_student_access(user, req.student_id)

    async def _gen():
        async for chunk in career_agent.run_pipeline_stream(
            goal=req.goal,
            student_id=req.student_id,
        ):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
