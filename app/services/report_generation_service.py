# -*- coding: utf-8 -*-
"""
报告生成业务（从 routers/_common.py 抽出，给"路由共享层"瘦身）。

`generate_report_task` 是后台异步任务：YOUTU 四层检索 + 四维匹配 + LLM 生成报告
+ 分阶段计划 + 评估章节 + 成长闭环 ActionPlan 落库。属于业务逻辑，归 service 层。

注：报告持久句柄 `_report_store` 仍住在 `_common`（多路由共享）；任务进度已迁至
`app/services/task_progress.py` 走可降级 cache（Redis 共享 / 进程内降级），支持多实例。
"""

import asyncio
import logging
from datetime import datetime

from app.services.career_graphrag_service import career_graphrag_service
from app.services.youtu_retriever_service import youtu_retriever_service
from app.services import tenant_config_service, snapshot_store, progress_service
from app.core.llm_service import llm_service
from app.routers._common import (
    _report_store,
    _get_student_portrait_from_store, _report_content_to_chapters,
)
from app.services.task_progress import task_store

logger = logging.getLogger(__name__)


async def generate_report_task(task_id: str, report_id: str, student_id: str, job_name: str):
    """后台异步任务：YOUTU-GraphRAG 检索 + LLM 生成报告。失败落 task_store 状态，不抛。"""
    try:
        await task_store.update(task_id, status="processing", progress=20)

        student = _get_student_portrait_from_store(student_id)
        if not student:
            raise ValueError("学生画像不存在，请先上传简历")

        await task_store.update(task_id, progress=35)
        # 重型同步匹配/检索放线程池，避免阻塞事件循环
        job = await asyncio.to_thread(career_graphrag_service.generate_job_portrait, job_name)

        # save_to_graph=True：报告生成时这次匹配也落库+快照 → 成长曲线有基线，
        # 学生首次"重新评估"就能算出 prev→curr delta（修此前 save_to_graph=False 的基线缺失）。
        await task_store.update(task_id, progress=50)
        match_result = await asyncio.to_thread(
            career_graphrag_service.compute_match, student, job, save_to_graph=True
        )

        # ── YOUTU-GraphRAG 四层融合检索：L1属性+L2实体+L3关键词+L4社区 ──
        await task_store.update(task_id, progress=65)
        graph_context = ""
        try:
            multilayer = youtu_retriever_service.retrieve_multilayer(
                f"{job_name} 职业发展路径 晋升 转岗 技能要求",
                job_name=job_name,
                top_k=8,
            )
            graph_context = multilayer.get("combined_context", "")
            # 兜底：若四层融合为空，退化到语义查询
            if not graph_context:
                youtu_result = await youtu_retriever_service.query(
                    f"{job_name} 职业发展路径 晋升 转岗 技能要求", top_k=10
                )
                graph_context = youtu_result.get("context", "") or youtu_result.get("answer", "")
        except Exception:
            pass

        # ── LLM 生成报告正文（基于图谱上下文 + 匹配数据）──
        await task_store.update(task_id, progress=75)
        missing_skills = match_result.details.get("missing_skills", [])
        matched_skills = match_result.details.get("matched_skills", [])

        report_prompt = f"""你是一位专业的大学生职业规划顾问，请基于以下数据为学生生成一份完整的个性化职业发展报告。

【学生画像】
姓名：{student.name or '学生'}
已掌握技能：{', '.join(student.skills[:15]) or '暂无'}
证书：{', '.join(student.certificates) or '暂无'}
创新能力：{student.innovation} | 学习能力：{student.learning} | 抗压能力：{student.stress_resistance}
沟通能力：{student.communication} | 实习能力：{student.internship}
完整度评分：{student.completeness_score:.0f}分 | 竞争力评分：{student.competitiveness_score:.0f}分

【目标岗位：{job.title}】
薪资范围：{job.salary_range or '面议'}
岗位要求技能：{', '.join(job.skills[:15]) or '暂无'}
证书要求：{', '.join(job.certificates) or '暂无'}
创新要求：{job.innovation} | 学习要求：{job.learning} | 抗压要求：{job.stress_resistance}
沟通要求：{job.communication} | 实习要求：{job.internship}

【四维度匹配结果】
综合匹配度：{match_result.total_match:.1f}%
- 基础要求匹配：{match_result.basic_match:.1f}%
- 职业技能匹配：{match_result.skill_match:.1f}%
  · 已匹配技能：{', '.join(matched_skills[:10]) or '暂无'}
  · 待提升技能：{', '.join(missing_skills[:10]) or '暂无'}
- 职业素养匹配：{match_result.quality_match:.1f}%
- 发展潜力匹配：{match_result.potential_match:.1f}%

【YOUTU知识图谱检索结果（职业路径与岗位数据）】
{graph_context[:2000] if graph_context else '（图谱检索暂无结果，请根据已知数据分析）'}

请严格按照如下结构生成职业发展报告，使用 ## 作为二级标题：

## 一、职业探索与岗位匹配分析
深度解读四维度匹配结果，结合图谱数据分析岗位市场情况，指出学生的核心优势和关键差距。

## 二、职业目标设定与路径规划
基于图谱中的晋升路径（PROMOTES_TO）和转岗路径（TRANSFERS_TO）数据，制定清晰的短期（0-6个月）和中期（6-18个月）发展目标，规划具体的职业成长路径。

## 三、30天快速行动计划
列出未来30天内具体可执行的行动项：技能学习计划（优先补充缺失技能）、项目实践建议、证书考取安排，每项附带明确的时间节点和可验证的里程碑。

要求：每节不少于200字，内容针对该学生实际情况，语言专业具体，禁止泛泛而谈。"""

        # M2.3 院校定制：把租户配置的报告增补要求追加进 prompt（无配置=空，行为不变）
        _extra = tenant_config_service.report_extra_instructions()
        if _extra:
            report_prompt += f"\n\n【院校定制要求】\n{_extra}"

        # 成长闭环：若该学生有历史快照，注入成长趋势，让报告从"你现在 X 分"
        # 升级为"上次 X→这次 Y，因新增 …"（best-effort，无历史则不变）
        try:
            _summary = await asyncio.to_thread(progress_service.agent_context_summary, student_id)
            _growth = progress_service.format_summary_text(_summary)
            if _growth:
                report_prompt += (
                    "\n\n【该学生历史成长（真实快照，请在第一章对比分析中引用具体数字）】"
                    + _growth
                )
        except Exception:
            pass

        report_content = await llm_service.chat([
            {
                "role": "system",
                "content": (
                    "你是一位专业的大学生职业规划顾问，基于YOUTU知识图谱数据生成个性化职业规划报告。"
                    "输出严格使用Markdown格式，## 开头的二级标题分节，内容具体、专业、有针对性。"
                )
            },
            {"role": "user", "content": report_prompt}
        ], temperature=0.6)

        # ── 结构化数据：分阶段计划（前端卡片用）+ 评估周期与指标（第四章）──
        await task_store.update(task_id, progress=90)
        phased_plan = await asyncio.to_thread(
            career_graphrag_service._generate_phased_plan, student, job, match_result
        )
        phased_dict = phased_plan.model_dump() if phased_plan else {}

        # 评估周期与量化指标：基于匹配分数动态生成，作为第四章追加
        evaluation_section = await asyncio.to_thread(
            career_graphrag_service._generate_evaluation_section, match_result, job
        )

        chapters = _report_content_to_chapters(report_content, job_name)
        # 追加第四章：评估周期与动态调整计划
        chapters.append({
            "title": "四、评估周期与动态调整",
            "content": evaluation_section,
        })

        await _report_store.save(report_id, {
            "report_id": report_id,
            "student_id": student_id,
            "job_name": job_name,
            "match_result": match_result.model_dump(),
            "chapters_json": chapters,
            "phased_plan": phased_dict,
            "career_paths": [],
            "snapshot": None,
            "created_at": datetime.now().isoformat(),
        })

        # 成长闭环：把短/中期行动从报告附录拆为独立 ActionPlan 实体（可勾选完成/追踪逾期）
        action_items = (phased_dict.get("short_term") or []) + (phased_dict.get("mid_term") or [])
        snapshot_store.record_action_plan(
            student_id=student_id, items=action_items, job_name=job_name,
        )

        await task_store.update(task_id, status="completed", progress=100, report_id=report_id)

    except Exception as e:
        await task_store.update(task_id, status="failed", error_msg=str(e))
