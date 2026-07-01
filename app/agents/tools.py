# -*- coding: utf-8 -*-
"""
Agent Tool 层
把现有业务函数封装为 LLM Function Calling 可调用的工具。
LLM 通过 tool_calls 选择工具，本层负责实际执行并返回结构化结果。
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict

from app.services.career_graphrag_service import career_graphrag_service, StudentPortrait
from app.services.youtu_retriever_service import youtu_retriever_service
from app.services.student_graph_service import student_graph_service
from app.services import tenant_config_service
from app.core.observability import metrics, get_trace_id

logger = logging.getLogger(__name__)

# 工具执行可靠性参数
TOOL_TIMEOUT = 40      # 单工具超时（秒）；generate_report/query_graph 较重
TOOL_RETRIES = 1       # 失败重试次数
# 注：权重预设与一票否决阈值已归位到 app/services/match_rules.py（匹配域单一事实源）


# ── Tool 描述（发给 LLM 的 schema）─────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_student_portrait",
            "description": (
                "获取学生的七维度能力画像，包括技能列表、证书、软技能维度评级、"
                "完整度评分和竞争力评分。在分析学生情况前必须先调用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "学生唯一ID"}
                },
                "required": ["student_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_jobs",
            "description": "获取系统中所有可匹配的岗位列表（51个岗位名称、薪资范围）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_portrait",
            "description": (
                "获取指定岗位的七维度画像：技能要求、证书要求、创新/学习/抗压/"
                "沟通/实习能力要求，以及薪资范围和市场需求量。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "岗位名称，如'前端开发'"}
                },
                "required": ["job_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_match",
            "description": (
                "计算学生与指定岗位的四维度匹配分（基础要求/技能匹配/素质匹配/发展潜力），"
                "返回各维度得分、总分、已匹配技能和缺失技能。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "学生ID"},
                    "job_name":   {"type": "string", "description": "岗位名称"},
                    "weight_preset": {
                        "type": "string",
                        "description": "权重方案：general/tech/management/research/operation",
                        "enum": ["general", "tech", "management", "research", "operation"],
                    },
                },
                "required": ["student_id", "job_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_jobs",
            "description": (
                "根据学生技能，对所有岗位批量计算匹配分并排序，"
                "返回最适合的前N个岗位及其匹配分数。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "学生ID"},
                    "top_n":      {"type": "integer", "description": "返回前N个岗位，默认5"},
                },
                "required": ["student_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_career_paths",
            "description": (
                "从知识图谱查询指定岗位的职业发展路径，包括：\n"
                "- 纵向晋升路径（PROMOTES_TO）：从当前岗位可晋升至哪些岗位\n"
                "- 横向转岗路径（TRANSFERS_TO）：可横向转换至哪些相关岗位\n"
                "每条路径附带置信度、涨薪幅度、共同技能。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "岗位名称"}
                },
                "required": ["job_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_graph",
            "description": (
                "用自然语言检索职业知识图谱（YOUTU-GraphRAG四层检索），"
                "获取岗位技能要求、行业趋势、职业发展建议等信息。"
                "适合回答开放性问题，如'XX行业前景如何''XX岗位需要什么能力'。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "自然语言查询"},
                    "top_k": {"type": "integer", "description": "返回结果数量，默认8"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": (
                "为学生生成完整的职业发展报告，包含：职业探索与岗位匹配分析、"
                "短中期目标规划、30天行动计划、评估周期与指标。"
                "调用前需确保已了解学生画像和目标岗位。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id":  {"type": "string", "description": "学生ID"},
                    "target_job":  {"type": "string", "description": "目标岗位名称"},
                },
                "required": ["student_id", "target_job"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_output",
            "description": (
                "对已收集的分析结果进行质量自评，判断是否已有足够信息完成用户目标，"
                "返回完整度评分(0-100)和缺失信息列表。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal":           {"type": "string", "description": "用户原始目标"},
                    "collected_data": {"type": "string", "description": "已收集数据的摘要"},
                },
                "required": ["goal", "collected_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_progress_summary",
            "description": (
                "获取学生的历史成长摘要（基于真实快照）：竞争力变化与归因、"
                "最近两次同岗位匹配分对比（上次→这次）、已补上的缺失技能、"
                "行动计划完成率与逾期数。用于在路径规划/报告中引用具体的成长数字，"
                "体现'学生在变好'。首次评估无历史时返回 available=False。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "学生ID"}
                },
                "required": ["student_id"],
            },
        },
    },
]


# ── Tool 执行器 ──────────────────────────────────────────────────────────
class ToolExecutor:
    """将 LLM 的 tool_call 路由到实际业务函数并返回结果。"""

    async def execute(self, tool_name: str, arguments: Dict, context: Dict) -> Dict[str, Any]:
        """
        执行工具，返回结构化结果（成功=原始 dict，失败={"error":...}）。
        外层包裹超时、重试、指标与日志（带 trace_id），保证工具调用可靠且可观测。
        context 包含当前 student_id、report_store 等共享状态。
        """
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            return {"error": f"未知工具: {tool_name}"}

        last_err = None
        for attempt in range(TOOL_RETRIES + 1):
            t0 = time.perf_counter()
            try:
                result = await asyncio.wait_for(handler(arguments, context), timeout=TOOL_TIMEOUT)
                elapsed = (time.perf_counter() - t0) * 1000
                metrics.observe(f"tool.{tool_name}.ms", elapsed)
                metrics.incr(f"tool.{tool_name}.ok")
                logger.info("[%s] tool=%s ok %.0fms (try %d)",
                            get_trace_id(), tool_name, elapsed, attempt + 1)
                return result
            except asyncio.TimeoutError:
                last_err = f"工具超时（>{TOOL_TIMEOUT}s）"
                metrics.incr(f"tool.{tool_name}.timeout")
                logger.warning("[%s] tool=%s timeout (try %d)", get_trace_id(), tool_name, attempt + 1)
            except Exception as e:
                last_err = str(e)
                metrics.incr(f"tool.{tool_name}.error")
                logger.warning("[%s] tool=%s error: %s (try %d)", get_trace_id(), tool_name, e, attempt + 1)

        return {"error": last_err, "tool": tool_name}

    # ── 各工具实现 ─────────────────────────────────────────────────────

    async def _tool_get_student_portrait(self, args: Dict, ctx: Dict) -> Dict:
        student_id = args.get("student_id") or ctx.get("student_id", "")
        data = student_graph_service.get_student(student_id)
        if not data:
            return {"error": f"未找到学生: {student_id}"}
        attrs = data.get("attributes", {})
        return {
            "student_id":           student_id,
            "name":                 attrs.get("name", ""),
            "skills":               attrs.get("skills", []),
            "certificates":         attrs.get("certificates", []),
            "innovation":           attrs.get("innovation", "一般"),
            "learning":             attrs.get("learning", "一般"),
            "stress_resistance":    attrs.get("stress_resistance", "一般"),
            "communication":        attrs.get("communication", "一般"),
            "internship":           attrs.get("internship", "一般"),
            "completeness_score":   attrs.get("completeness_score", 0),
            "competitiveness_score":attrs.get("competitiveness_score", 0),
            "career_intent":        attrs.get("career_intent", ""),
            "education":            attrs.get("education", []),
            "projects_count":       len(attrs.get("projects", [])),
            "internships_count":    len(attrs.get("internships", [])),
        }

    async def _tool_get_all_jobs(self, args: Dict, ctx: Dict) -> Dict:
        jobs = career_graphrag_service.get_all_jobs()
        return {"jobs": [{"title": j["title"], "salary": j.get("salary_range", "")} for j in jobs]}

    async def _tool_get_job_portrait(self, args: Dict, ctx: Dict) -> Dict:
        job_name = args["job_name"]
        p = career_graphrag_service.generate_job_portrait(job_name)
        return {
            "title":            p.title,
            "skills":           p.skills[:12],
            "certificates":     p.certificates,
            "innovation":       p.innovation,
            "learning":         p.learning,
            "stress_resistance":p.stress_resistance,
            "communication":    p.communication,
            "internship":       p.internship,
            "salary_range":     p.salary_range,
            "salary_avg_k":     p.salary_avg_k,
            "market_demand":    p.job_count,
            "entry_friendly":   p.entry_friendly,
        }

    async def _tool_compute_match(self, args: Dict, ctx: Dict) -> Dict:
        student_id   = args.get("student_id") or ctx.get("student_id", "")
        job_name     = args["job_name"]
        # 缺省用红线 canonical 默认权重（与 REST 一致）；LLM 可显式选 tech/management 等预设
        preset       = args.get("weight_preset", "default")

        student_data = student_graph_service.get_student(student_id)
        if not student_data:
            return {"error": f"未找到学生: {student_id}"}

        student = StudentPortrait.from_node(student_data, student_id=student_id)
        job = career_graphrag_service.generate_job_portrait(job_name)
        # 有效权重：租户级覆盖 > preset > 红线默认；veto 由匹配域统一裁决，与 REST 一致
        result = career_graphrag_service.compute_match(
            student, job, save_to_graph=False,
            weights=tenant_config_service.effective_match_weights(preset=preset),
        )

        return {
            "job_name":        job_name,
            "total_match":     round(result.total_match, 1),
            "basic_match":     round(result.basic_match, 1),
            "skill_match":     round(result.skill_match, 1),
            "quality_match":   round(result.quality_match, 1),
            "potential_match": round(result.potential_match, 1),
            "matched_skills":  result.details.get("matched_skills", [])[:8],
            "missing_skills":  result.details.get("missing_skills", [])[:8],
            "eligible":        result.eligible,
            "veto_reason":     result.veto_reason,
            "weight_preset":   preset,
        }

    async def _tool_recommend_jobs(self, args: Dict, ctx: Dict) -> Dict:
        student_id = args.get("student_id") or ctx.get("student_id", "")
        top_n      = int(args.get("top_n", 5))

        student_data = student_graph_service.get_student(student_id)
        if not student_data:
            return {"error": f"未找到学生: {student_id}"}

        student = StudentPortrait.from_node(student_data, student_id=student_id)
        all_jobs = career_graphrag_service.get_all_jobs()   # 已按租户岗位库过滤
        w = tenant_config_service.effective_match_weights()
        scores = []
        for job_info in all_jobs:
            try:
                job = career_graphrag_service.generate_job_portrait(job_info["title"])
                r   = career_graphrag_service.compute_match(student, job, save_to_graph=False, weights=w)
                scores.append({
                    "job_name":    job_info["title"],
                    "total_match": round(r.total_match, 1),
                    "skill_match": round(r.skill_match, 1),
                    "missing_skills": r.details.get("missing_skills", [])[:4],
                })
            except Exception:
                pass

        scores.sort(key=lambda x: -x["total_match"])
        return {"recommendations": scores[:top_n], "total_evaluated": len(scores)}

    async def _tool_get_career_paths(self, args: Dict, ctx: Dict) -> Dict:
        job_name = args["job_name"]
        paths    = career_graphrag_service.get_career_paths(job_name)
        return {
            "job_name": job_name,
            "vertical_paths": [
                {
                    "target":         p.target_job,
                    "confidence":     p.confidence,
                    "description":    p.description,
                    "shared_skills":  p.shared_skills[:4],
                }
                for p in paths.vertical_paths
            ],
            "horizontal_paths": [
                {
                    "target":         p.target_job,
                    "confidence":     p.confidence,
                    "description":    p.description,
                    "shared_skills":  p.shared_skills[:4],
                }
                for p in paths.horizontal_paths
            ],
        }

    async def _tool_query_graph(self, args: Dict, ctx: Dict) -> Dict:
        query  = args["query"]
        top_k  = int(args.get("top_k", 8))
        result = await youtu_retriever_service.query(query, top_k=top_k)
        return {
            "query":   query,
            "answer":  result.get("answer", result.get("context", ""))[:1500],
        }

    async def _tool_generate_report(self, args: Dict, ctx: Dict) -> Dict:
        """触发后台报告生成任务，将 report_id 存入 context 供后续使用。"""
        import uuid, asyncio
        from app.routers._common import _generate_report_task, _report_store
        from app.services.task_progress import task_store

        student_id = args.get("student_id") or ctx.get("student_id", "")
        target_job = args["target_job"]

        task_id   = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        await task_store.create(
            task_id, report_id=report_id,
            status="pending", progress=0, student_id=student_id,
        )

        await _generate_report_task(task_id, report_id, student_id, target_job)

        ctx["last_report_id"] = report_id   # 存入上下文供后续工具使用
        report_data = _report_store.get(report_id, {})
        chapters    = report_data.get("chapters_json", [])
        return {
            "report_id":  report_id,
            "target_job": target_job,
            "chapters":   [c["title"] for c in chapters],
            "status":     "completed" if chapters else "failed",
        }

    async def _tool_evaluate_output(self, args: Dict, ctx: Dict) -> Dict:
        """LLM 自评：判断已收集信息是否足以完成目标。"""
        from app.core.llm_service import llm_service
        goal           = args["goal"]
        collected_data = args["collected_data"]

        prompt = (
            f"用户目标：{goal}\n\n"
            f"已收集数据摘要：{collected_data}\n\n"
            "请评估：\n"
            "1. 当前数据是否足以完成用户目标？（0-100分，80分以上视为充分）\n"
            "2. 还缺少哪些关键信息？\n"
            "3. 下一步建议行动（调用哪个工具或直接输出结论）\n\n"
            '请以JSON格式返回：{"score":数字,"missing":["缺少的信息"],"next_action":"建议"}'
        )
        try:
            resp = await llm_service.chat(
                [{"role": "user", "content": prompt}], temperature=0.2
            )
            import re
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return {"score": 50, "missing": ["评估失败"], "next_action": "继续收集数据"}

    async def _tool_get_progress_summary(self, args: Dict, ctx: Dict) -> Dict:
        """成长闭环：返回学生历史成长摘要（趋势归因 + 匹配进展 + 行动完成率）。
        纯快照读取放线程池，不阻塞事件循环。"""
        from app.services import progress_service
        student_id = args.get("student_id") or ctx.get("student_id", "")
        if not student_id:
            return {"error": "缺少 student_id"}
        return await asyncio.to_thread(progress_service.agent_context_summary, student_id)


tool_executor = ToolExecutor()
