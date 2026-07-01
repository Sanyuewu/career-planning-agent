# -*- coding: utf-8 -*-
"""
CareerPlanningAgent — 以 LLM 为大脑的职业规划智能体
核心机制：ReAct（Reasoning + Acting）循环
  1. LLM 推理下一步 → 2. 执行工具 → 3. 结果反馈给 LLM → 循环直至目标完成
"""

import json
import uuid
import logging
from time import perf_counter
from typing import AsyncGenerator, Dict, List, Any, Optional

from app.core.llm_service import llm_service
from app.agents.tools import tool_executor
from app.agents.fsm import State, next_state, can_advance, STATE_GOAL
from app.agents.registry import tools_for, tool_names_for
from app.agents.run_recorder import RunRecorder
from app.core.observability import new_trace_id

logger = logging.getLogger(__name__)


AGENT_SYSTEM_PROMPT = """你是一位专业的大学生职业规划顾问智能体，能够自主调用工具完成职业规划任务。

【你拥有的工具】
- get_student_portrait：获取学生七维度能力画像
- get_all_jobs：获取所有可选岗位列表
- get_job_portrait：获取指定岗位的要求和画像
- compute_match：计算学生与岗位的四维度匹配分
- recommend_jobs：推荐最匹配的岗位（批量计算）
- get_career_paths：查询岗位的晋升和转岗路径
- query_graph：用自然语言检索职业知识图谱
- generate_report：生成完整职业发展报告
- evaluate_output：自评已收集信息的充分性

【工作原则】
1. 先分析用户目标，制定执行计划，再逐步调用工具
2. 每次只调用最关键的1-2个工具，根据结果决定下一步
3. 技能匹配分<60分时，主动查询转岗路径或推荐其他岗位
4. 所有结论必须基于工具返回的真实数据，不得编造数据
5. 在生成最终报告前，先确保已了解学生画像和目标岗位
6. 给出最终结论时，语言简洁专业，突出关键数字和可操作建议

【输出风格】
- 调用工具前简要说明意图（1句话）
- 最终结论用结构化格式呈现（分点列举）
- 不要重复已经告知的信息"""

MAX_STEPS = 12        # 单次 ReAct 最大循环次数，防止无限调用
STATE_STEP_BUDGET = 4  # FSM 单状态内 ReAct 步数预算


class CareerPlanningAgent:
    """ReAct 智能体：FSM 五阶段编排 + 状态内 ReAct，流式 SSE。唯一入口 run_pipeline_stream。"""

    # ════════════════════════════════════════════════════════════
    # FSM 编排管线：五阶段状态门控 + 状态内 ReAct
    # ════════════════════════════════════════════════════════════

    async def run_pipeline_stream(
        self, goal: str, student_id: str,
        session_id: Optional[str] = None, start_state: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        FSM 主编排：GREETING→PROFILING→MATCHING→PLANNING→REPORTING→DONE。
        每个状态内运行"工具被裁剪到该阶段"的 ReAct；状态间转移由 FSM 硬守卫裁决，
        不满足门槛（如画像完整度 < 70）则停在当前状态并引导补全。
        全程落 AgentRun/AgentStep，trace_id 贯穿，SSE 事件实时推送。
        """
        trace_id = new_trace_id()
        run_id = str(uuid.uuid4())
        recorder = RunRecorder(run_id, student_id, goal, trace_id, session_id)
        ctx: Dict[str, Any] = {"student_id": student_id, "goal": goal}
        # 成长闭环：进 run 前拉一次该学生历史成长上下文（best-effort，sync 读放线程池）。
        # 让 Agent 从"应答者"变"伴随者"——开口就知道上次分、涨因、行动进度。
        try:
            from app.services import progress_service
            ctx["progress"] = await asyncio.to_thread(
                progress_service.agent_context_summary, student_id
            )
        except Exception:
            ctx["progress"] = None
        t_start = perf_counter()
        ttft_ms: Optional[int] = None

        def _sse(event: Dict) -> str:
            event.setdefault("trace_id", trace_id)
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 了解你、接着走：未显式指定起始状态时，从学生真实状态推导，不重做已完成阶段
        if start_state:
            state = State(start_state)
        else:
            from app.agents import agent_state
            state, seed = await asyncio.to_thread(agent_state.derive_start_state, student_id)
            ctx.update(seed)

        try:
            yield _sse({"type": "run_start", "run_id": run_id, "goal": goal})

            # 接着走的开场白（据起始状态，而非每次"从头你好"）
            from app.agents.agent_state import opening_line
            _open = opening_line(state, ctx)
            yield _sse({"type": "thought", "content": _open, "state": state.value})
            recorder.step("thought", state=state.value, result=_open)

            while state != State.DONE:
                sub_goal = STATE_GOAL[state]
                tools = tools_for(state)
                yield _sse({"type": "state", "state": state.value, "goal": sub_goal})
                recorder.step("enter", state=state.value, result=sub_goal)

                if tools:
                    allowed_names = set(tool_names_for(state))
                    messages = self._build_state_messages(goal, student_id, state, sub_goal, ctx)
                    for _ in range(STATE_STEP_BUDGET):
                        # ── 流式 ReAct：thought 文本 token 级推流，工具调用累积后执行 ──
                        content_acc = ""
                        tool_calls: List[Dict] = []
                        async for ev in llm_service.chat_with_tools_stream(
                            messages=messages, tools=tools, temperature=0.3,
                        ):
                            if ev["type"] == "content":
                                if ttft_ms is None:
                                    ttft_ms = int((perf_counter() - t_start) * 1000)
                                content_acc += ev["delta"]
                                yield _sse({"type": "token", "delta": ev["delta"], "state": state.value})
                            else:  # final
                                content_acc = ev.get("content", content_acc)
                                tool_calls = ev.get("tool_calls", []) or []

                        if content_acc:
                            yield _sse({"type": "thought_end", "state": state.value})
                            recorder.step("thought", state=state.value, result=content_acc[:500])

                        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content_acc or None}
                        if tool_calls:
                            assistant_msg["tool_calls"] = tool_calls
                        messages.append(assistant_msg)

                        if not tool_calls:
                            break

                        for tc in tool_calls:
                            fn = tc["function"]["name"]
                            try:
                                args = json.loads(tc["function"]["arguments"] or "{}")
                            except json.JSONDecodeError:
                                args = {}
                            yield _sse({"type": "tool_call", "name": fn, "args": args, "state": state.value})
                            recorder.step("tool_call", state=state.value, tool_name=fn, args=args)

                            # FSM 硬约束：本阶段不允许的工具直接拒绝执行，不让 LLM 越权
                            if fn not in allowed_names:
                                result = {"error": f"工具 {fn} 不在当前阶段 {state.value} 的允许范围内"}
                                lat = 0
                            else:
                                t0 = perf_counter()
                                result = await tool_executor.execute(fn, args, ctx)
                                lat = int((perf_counter() - t0) * 1000)

                            recorder.step("tool_result", state=state.value, tool_name=fn,
                                          result=result, latency_ms=lat)
                            yield _sse({
                                "type": "tool_result", "name": fn, "result": result,
                                "summary": _summarize_result(fn, result), "state": state.value,
                            })
                            self._update_ctx(ctx, fn, args, result)
                            messages.append({
                                "role": "tool", "tool_call_id": tc["id"],
                                "content": json.dumps(result, ensure_ascii=False),
                            })

                # ── FSM 硬守卫：能否离开本状态 ──
                allowed, reason = can_advance(state, ctx)
                if not allowed:
                    yield _sse({"type": "blocked", "state": state.value, "reason": reason})
                    recorder.step("blocked", state=state.value, result=reason)
                    recorder.finish("blocked", final_state=state.value, ttft_ms=ttft_ms,
                                    latency_ms=int((perf_counter() - t_start) * 1000))
                    return

                nxt = next_state(state)
                yield _sse({"type": "transition", "from": state.value, "to": nxt.value})
                recorder.step("transition", state=nxt.value, result=f"{state.value}->{nxt.value}")
                state = nxt

            summary = self._final_summary(ctx)
            yield _sse({"type": "done", "content": summary, "state": State.DONE.value})
            recorder.finish("done", final_state=State.DONE.value, ttft_ms=ttft_ms,
                            latency_ms=int((perf_counter() - t_start) * 1000))

        except Exception as e:
            logger.exception("[%s] pipeline 异常", trace_id)
            yield _sse({"type": "error", "content": str(e), "state": state.value})
            recorder.finish("error", final_state=state.value, ttft_ms=ttft_ms,
                            latency_ms=int((perf_counter() - t_start) * 1000))

    @staticmethod
    def _build_state_messages(goal: str, student_id: str, state: State,
                              sub_goal: str, ctx: Dict) -> List[Dict]:
        known = []
        if ctx.get("completeness_score") is not None:
            known.append(f"画像完整度：{ctx.get('completeness_score')}")
        if ctx.get("target_job"):
            known.append(f"目标岗位：{ctx.get('target_job')}")
        known_str = ("\n已知信息：" + "；".join(known)) if known else ""
        growth_str = _format_growth_context(ctx.get("progress"))
        return [
            {"role": "system", "content": (
                AGENT_SYSTEM_PROMPT
                + f"\n\n【当前阶段】{state.value}\n【本阶段任务】{sub_goal}\n"
                  "只调用本阶段提供的工具，完成本阶段任务后停止，不要越权进入下一阶段。"
                + ("\n\n【该学生历史成长】（基于真实快照，可在结论中引用具体数字，"
                   "如未提供则说明这是首次评估）" + growth_str if growth_str else "")
            )},
            {"role": "user", "content": (
                f"学生ID：{student_id}\n用户目标：{goal}{known_str}\n\n请完成本阶段任务。"
            )},
        ]

    @staticmethod
    def _update_ctx(ctx: Dict, fn: str, args: Dict, result: Any) -> None:
        """从工具结果提取 FSM 守卫所需的信号。"""
        if not isinstance(result, dict) or result.get("error"):
            return
        if fn == "get_student_portrait":
            ctx["completeness_score"] = result.get("completeness_score", 0)
            ctx["student_name"] = result.get("name", "")
        elif fn == "compute_match":
            ctx["has_match"] = True
            ctx.setdefault("matches", []).append(
                {"job": result.get("job_name"), "total": result.get("total_match"),
                 "eligible": result.get("eligible", True)}
            )
            ctx["target_job"] = args.get("job_name") or ctx.get("target_job")
        elif fn == "recommend_jobs":
            recs = result.get("recommendations", [])
            if recs:
                ctx["has_match"] = True
                ctx["recommendations"] = recs
                ctx.setdefault("target_job", recs[0].get("job_name"))
        elif fn == "get_career_paths":
            ctx["has_paths"] = True
            ctx["career_paths"] = {
                "vertical": result.get("vertical_paths", []),
                "horizontal": result.get("horizontal_paths", []),
            }
        elif fn == "generate_report":
            ctx["report_id"] = result.get("report_id")
            ctx["report_chapters"] = result.get("chapters", [])

    @staticmethod
    def _final_summary(ctx: Dict) -> str:
        parts = []
        if ctx.get("target_job"):
            parts.append(f"目标岗位：{ctx['target_job']}")
        recs = ctx.get("recommendations") or []
        if recs:
            top = "、".join(f"{r.get('job_name')}({r.get('total_match')}分)" for r in recs[:3])
            parts.append(f"推荐岗位：{top}")
        if ctx.get("report_id"):
            parts.append(f"已生成职业发展报告（report_id={ctx['report_id'][:8]}…）")
        return "职业规划全流程完成。" + ("；".join(parts) if parts else "")


def _format_growth_context(progress: Optional[Dict]) -> str:
    """成长上下文格式化（委托 progress_service 单一事实源，Agent 与 Chat 措辞一致）。"""
    from app.services import progress_service
    return progress_service.format_summary_text(progress)


def _summarize_result(tool_name: str, result: Dict) -> str:
    """生成工具结果的一句话摘要，用于前端展示。"""
    if "error" in result:
        return f"执行失败：{result['error']}"

    summaries = {
        "get_student_portrait": lambda r: (
            f"学生「{r.get('name','?')}」：{len(r.get('skills',[]))}个技能，"
            f"竞争力{r.get('competitiveness_score',0):.0f}分"
        ),
        "get_all_jobs": lambda r: f"共 {len(r.get('jobs',[]))} 个可选岗位",
        "get_job_portrait": lambda r: (
            f"「{r.get('title','?')}」：需要{len(r.get('skills',[]))}项技能，"
            f"均薪{r.get('salary_avg_k',0):.1f}k"
        ),
        "compute_match": lambda r: (
            f"「{r.get('job_name','?')}」匹配分：{r.get('total_match',0)}分"
            f"（技能{r.get('skill_match',0):.0f}｜素质{r.get('quality_match',0):.0f}）"
        ),
        "recommend_jobs": lambda r: (
            f"推荐前{len(r.get('recommendations',[]))}个岗位，"
            f"最高匹配：{r['recommendations'][0]['job_name'] if r.get('recommendations') else '无'}"
        ),
        "get_career_paths": lambda r: (
            f"「{r.get('job_name','?')}」：{len(r.get('vertical_paths',[]))}条晋升路径，"
            f"{len(r.get('horizontal_paths',[]))}条转岗路径"
        ),
        "query_graph": lambda r: f"图谱检索完成，获取{len(r.get('answer',''))}字上下文",
        "generate_report": lambda r: (
            f"报告生成{'成功' if r.get('status')=='completed' else '失败'}，"
            f"ID：{r.get('report_id','?')[:8]}…"
        ),
        "evaluate_output": lambda r: f"完整度评分：{r.get('score',0)}分",
    }

    fn = summaries.get(tool_name)
    try:
        return fn(result) if fn else str(result)[:100]
    except Exception:
        return str(result)[:100]


career_agent = CareerPlanningAgent()
