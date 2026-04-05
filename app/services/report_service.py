# -*- coding: utf-8 -*-
"""
职业规划报告服务
遵循v4规范：6章节报告 + I4可解释溯源 + PDF/Word导出
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field

from dataclasses import dataclass, field as dc_field

logger = logging.getLogger(__name__)
from app.services.match_service import MatchResult
from app.services.portrait_service import StudentPortrait
from app.graph.job_graph_repo import job_graph
from app.ai.llm_client import llm_client, render_prompt
from app.config import settings, DATA_DIR
from app.constants import REAL_PROJECT_SUGGESTIONS, REAL_INTERNSHIP_SUGGESTIONS
from app.data.industry_insights import INDUSTRY_INSIGHTS, get_industry_for_job, get_career_path_for_job


@dataclass
class EnhancedActionItem:
    """增强版行动项"""
    title: str
    timeline: str
    description: str
    verification: str
    priority: str = "medium"
    category: str = "skill"
    resources: List[str] = dc_field(default_factory=list)
    milestones: List[str] = dc_field(default_factory=list)


class ReportEnhancer:
    """报告增强器：生成可操作的行动建议和里程碑"""

    def __init__(self):
        self.skill_resources = {
            "Python": ["Python官方教程: https://docs.python.org/zh-cn/3/tutorial/", "LeetCode Python练习: https://leetcode.cn/problemset/"],
            "Java": ["Java核心技术卷I", "Spring官方文档: https://spring.io/guides"],
            "JavaScript": ["MDN Web教程: https://developer.mozilla.org/zh-CN/", "现代JavaScript教程: https://zh.javascript.info/"],
            "React": ["React官方教程: https://react.dev/learn", "React设计模式与最佳实践"],
            "Vue": ["Vue3官方教程: https://cn.vuejs.org/guide/", "Vue.js设计与实现"],
            "MySQL": ["MySQL必知必会", "SQL练习: LeetCode数据库题目"],
            "Redis": ["Redis官方文档: https://redis.io/docs/", "Redis设计与实现"],
            "Docker": ["Docker官方教程: https://docs.docker.com/get-started/", "Docker实战"],
            "Kubernetes": ["Kubernetes官方文档: https://kubernetes.io/zh-cn/docs/", "Kubernetes权威指南"],
            "Git": ["Git官方教程: https://git-scm.com/book/zh/v2", "Pro Git中文版"],
            "Linux": ["Linux命令行与Shell脚本编程大全", "鸟哥的Linux私房菜"],
            "TensorFlow": ["TensorFlow官方教程: https://www.tensorflow.org/tutorials", "Kaggle竞赛实践"],
            "PyTorch": ["PyTorch官方教程: https://pytorch.org/tutorials/", "深度学习与PyTorch"],
        }

    def enhance_action_items(self, skill_gaps: List, student_info: dict, job_title: str) -> List[EnhancedActionItem]:
        items = []
        items.extend(self._generate_sprint_plan(skill_gaps, student_info, job_title))
        items.extend(self._generate_short_term_plan(skill_gaps, student_info, job_title))
        return items

    def _generate_sprint_plan(self, skill_gaps: List, student_info: dict, job_title: str) -> List[EnhancedActionItem]:
        items = []
        must_have_gaps = [g for g in skill_gaps if g.get("importance") == "must_have"]
        if must_have_gaps:
            skill = must_have_gaps[0].get("skill", "")
            resources = self.skill_resources.get(skill, [f"搜索'{skill}教程'获取学习资源"])
            items.append(EnhancedActionItem(
                title=f"攻克核心技能：{skill}", timeline="第1-7天",
                description=f"系统学习{skill}，完成官方教程核心章节，理解核心概念和最佳实践",
                verification=f"完成{skill}相关项目实践，代码提交GitHub并通过审查",
                priority="high", category="skill", resources=resources[:2],
            ))
        projects = student_info.get("projects", [])
        if projects:
            project_name = projects[0].get("name") or "项目"
            items.append(EnhancedActionItem(
                title=f"项目强化：{project_name}", timeline="第8-20天",
                description=f"基于现有项目{project_name}，添加新功能或优化性能，将代码提交至GitHub并编写README",
                verification="项目代码提交GitHub，完成README文档，项目可运行演示",
                priority="high", category="project", resources=["GitHub仓库创建指南", "项目文档模板"],
            ))
        elif must_have_gaps:
            skill = must_have_gaps[0].get("skill", "")
            items.append(EnhancedActionItem(
                title=f"实战项目：{skill}练习", timeline="第8-20天",
                description=f"使用{skill}完成一个完整的小项目（如Todo应用、博客系统），代码提交GitHub",
                verification="项目代码提交GitHub，完成README文档，项目可运行演示",
                priority="high", category="project", resources=self.skill_resources.get(skill, [])[:2],
            ))
        items.append(EnhancedActionItem(
            title="简历优化与投递准备", timeline="第21-30天",
            description=f"针对{job_title}岗位JD关键词优化简历，准备自我介绍和项目介绍话术，完成3次模拟面试",
            verification=f"完成3次模拟面试，简历通过筛选获得至少1次面试邀请",
            priority="high", category="interview",
            resources=["简历模板与优化指南", "自我介绍模板", "常见面试题库"],
        ))
        return items

    def _generate_short_term_plan(self, skill_gaps: List, student_info: dict, job_title: str) -> List[EnhancedActionItem]:
        items = []
        for i, gap in enumerate(skill_gaps[:3]):
            skill = gap.get("skill", "")
            importance = gap.get("importance", "nice_to_have")
            suggestion = gap.get("suggestion", "")
            items.append(EnhancedActionItem(
                title=f"补齐技能：{skill}", timeline=f"第{i+1}-2个月",
                description=suggestion or f"系统学习{skill}，完成实战项目，达到生产可用水平",
                verification=f"完成{skill}相关项目实践，代码提交GitHub并通过审查",
                priority="high" if importance == "must_have" else "medium", category="skill",
                resources=self.skill_resources.get(skill, [])[:2],
            ))
        internships = student_info.get("internships", [])
        if internships:
            last_company = internships[-1].get("company", "")
            items.append(EnhancedActionItem(
                title="深化实习经验", timeline="第3-4个月",
                description=f"基于{last_company}实习经历，总结项目成果，量化贡献，准备面试案例",
                verification="完成实习总结文档，包含3个可讲述的项目案例",
                priority="medium", category="career",
            ))
        return items

    def generate_mid_term_milestones(self, job_title: str, skill_gaps: List, student_info: dict) -> List[dict]:
        must_gaps = [g.get("skill", "") for g in skill_gaps if g.get("importance") == "must_have" and g.get("skill")][:2]
        nice_gaps = [g.get("skill", "") for g in skill_gaps if g.get("importance") != "must_have" and g.get("skill")][:2]
        gap_text = "、".join(must_gaps) if must_gaps else "核心专业技能"
        intern_months = student_info.get("total_internship_months") or 0
        # 根据实习经验动态调整起点描述
        if intern_months >= 6:
            phase1_start = f"已有{intern_months}个月实习经验，重点补齐{gap_text}"
        elif intern_months > 0:
            phase1_start = f"在{intern_months}个月实习基础上，系统深化{gap_text}"
        else:
            phase1_start = f"从零开始，优先突破{gap_text}短板"
        nice_text = "、".join(nice_gaps) if nice_gaps else "进阶技术栈"
        return [
            {"title": "第6-12个月：职场适应与专项强化", "milestone": f"独立交付{gap_text}相关模块",
             "description": f"{phase1_start}，在{job_title}岗位独立完成至少2个核心模块并通过代码评审",
             "verification": f"能够独立解决{gap_text}相关的生产问题，获得团队正向绩效反馈"},
            {"title": "第12-18个月：能力跃升与影响力扩展", "milestone": f"掌握{nice_text}，主导项目模块",
             "description": f"在{job_title}方向拓展{nice_text}技能，主导完成一个有完整交付物的复杂项目，开始承担初级导师角色",
             "verification": "完成一个可公开展示的项目成果（含设计文档），获得至少1次技术分享机会"},
            {"title": "第18-24个月：方向确定与职业突破", "milestone": "晋升或明确下一阶段路线",
             "description": f"明确{job_title}纵深发展（高级工程师/架构方向）或横向转型（管理/产品方向）路线，考取相关认证，积累行业人脉",
             "verification": "获得晋升机会、明确下一步路线，或完成1项行业认证"},
        ]

    def validate_action_items(self, items: List[dict]) -> dict:
        issues = []
        valid_count = 0
        for i, item in enumerate(items):
            has_title = bool(item.get("title"))
            has_timeline = bool(item.get("timeline"))
            has_description = bool(item.get("description")) and len(item.get("description", "")) >= 10
            has_verification = bool(item.get("verification"))
            if has_title and has_timeline and has_description:
                valid_count += 1 if has_verification else 0
                if not has_verification:
                    issues.append(f"第{i+1}项缺少验证标准")
            else:
                missing = [k for k, v in [("标题", has_title), ("时间节点", has_timeline), ("详细描述", has_description)] if not v]
                issues.append(f"第{i+1}项缺少: {', '.join(missing)}")
        quality_score = (valid_count / len(items) * 100) if items else 0
        return {"is_valid": quality_score >= 75, "quality_score": quality_score,
                "valid_count": valid_count, "total_count": len(items), "issues": issues}


report_enhancer = ReportEnhancer()


class ActionItem(BaseModel):
    """行动计划项"""
    title: str
    timeline: str
    description: str
    verification: str = ""
    jd_source: str = ""


class ReportChapter(BaseModel):
    """报告章节"""
    index: int
    icon: str
    title: str
    content_md: str
    action_items: List[ActionItem] = Field(default_factory=list)


class CareerReport(BaseModel):
    """职业规划报告"""
    report_id: Optional[str] = None
    student_id: Optional[str] = None
    student_name: str = ""
    target_job: str = ""
    overall_score: float = 0.0
    skill_coverage: float = 0.0
    completeness: float = 0.0
    confidence: float = 0.0
    chapters: List[ReportChapter] = Field(default_factory=list)
    radar_data: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completeness_warnings: List[str] = Field(default_factory=list)


class ReportService:
    """职业规划报告服务"""

    def __init__(self):
        self.graph = job_graph

    async def generate_report(
        self,
        portrait: StudentPortrait,
        match_result: MatchResult,
    ) -> CareerReport:
        """生成职业规划报告"""
        student_name = portrait.basic_info.get("name") or "同学"
        logger.info("开始生成报告: student=%s job=%s score=%.1f",
                    student_name, match_result.job_title, match_result.overall_score)
        t0 = time.monotonic()

        report = CareerReport(
            student_name=student_name,
            target_job=match_result.job_title,
            overall_score=match_result.overall_score,
            skill_coverage=match_result.dimensions.professional_skills.score / 100,
            completeness=portrait.completeness,
            confidence=match_result.confidence,
        )

        report.radar_data = self._build_radar_data(match_result)

        # O3-c + D-4: LLM调用并行执行；章节2/3/4（纯数据处理）通过 run_in_executor 并行
        logger.debug("并行调用LLM生成行动计划+AI诊断: student=%s job=%s", student_name, match_result.job_title)
        import functools as _functools

        loop = asyncio.get_event_loop()
        plan_data, ai_commentary, ch2, ch3, ch4 = await asyncio.gather(
            self._generate_action_plan(portrait, match_result),
            self._generate_ai_commentary(portrait, match_result),
            loop.run_in_executor(None, self._chapter_2_match_analysis, match_result),
            loop.run_in_executor(None, self._chapter_3_career_path, match_result),
            loop.run_in_executor(None, self._chapter_4_industry_insight, match_result),
        )

        ch1 = self._chapter_1_overview(portrait, ai_commentary=ai_commentary)
        ch5 = self._chapter_5_short_term_plan(plan_data, match_result, portrait)
        ch6 = self._chapter_6_mid_term_plan(plan_data, match_result, portrait)

        report.chapters = [ch1, ch2, ch3, ch4, ch5, ch6]

        report.completeness_warnings = self._check_completeness(report, portrait, match_result)
        logger.info("报告生成完成 [%.2fs]: student=%s job=%s chapters=%d warnings=%d",
                    time.monotonic() - t0, student_name, match_result.job_title,
                    len(report.chapters), len(report.completeness_warnings))
        return report

    def _check_completeness(
        self,
        report: "CareerReport",
        portrait: "StudentPortrait",
        match_result: "MatchResult",
    ) -> List[str]:
        """检查报告关键内容完整性，返回给用户的提示列表"""
        warnings = []
        # 简历完整度
        if portrait.completeness < 0.5:
            pct = int(portrait.completeness * 100)
            warnings.append(f"简历完整度仅 {pct}%，建议补充实习/项目/证书信息以提升评分精准度")
        # 实习经历
        if not portrait.internships:
            warnings.append("未检测到实习经历，职业素养维度得分可能偏低，建议在画像中完善实习记录")
        # 技能数量
        if len(portrait.skills or []) < 3:
            warnings.append("技能数量不足3项，建议在画像中补充更多专业技能标签")
        # 技能差距
        gap_skills = match_result.dimensions.professional_skills.gap_skills or []
        if gap_skills:
            must_gaps = [g.skill for g in gap_skills if g.importance == "must_have"]
            if must_gaps:
                warnings.append(f"存在 {len(must_gaps)} 项必要技能差距：{'/'.join(must_gaps[:3])}{'等' if len(must_gaps) > 3 else ''}，建议优先补足")
        return warnings

    def _determine_job_level(self, portrait: StudentPortrait) -> str:
        grade = portrait.basic_info.get("grade", "应届")
        months = sum((i.get("duration_months") or 0) for i in (portrait.internships or []))
        if grade in ("研究生", "硕士", "博士") or months >= 12:
            return "中高级"
        elif months >= 6 or grade in ("大四", "应届"):
            return "初中级"
        else:
            return "初级"

    async def _generate_ai_commentary(
        self, portrait: StudentPortrait, match_result: MatchResult
    ) -> str:
        """C-5: LLM生成个性化综合诊断段落（100-150字），注入第一章"""
        name = portrait.basic_info.get("name") or "同学"
        job = match_result.job_title
        score = match_result.overall_score
        highlights = "、".join((portrait.highlights or [])[:3]) or "无"
        weaknesses = "、".join((portrait.weaknesses or [])[:2]) or "无"
        skills = "、".join((portrait.skills or [])[:5]) or "暂无技能记录"
        dims = match_result.dimensions
        prompt = (
            f"你是一位专业的职业规划导师。请为以下学生生成一段个性化的AI综合诊断（100-150字，语气积极、专业）：\n"
            f"学生：{name}，目标岗位：{job}，综合匹配度：{score:.0f}分\n"
            f"核心技能：{skills}\n"
            f"核心优势：{highlights}\n"
            f"待提升项：{weaknesses}\n"
            f"各维度得分 — 基础：{dims.basic_requirements.score:.0f}分，"
            f"技能：{dims.professional_skills.score:.0f}分，"
            f"素养：{dims.professional_qualities.score:.0f}分，"
            f"潜力：{dims.development_potential.score:.0f}分\n\n"
            f"请直接输出段落文字，不要加任何标题或编号："
        )
        try:
            commentary = await llm_client.chat(prompt, temperature=0.5, max_tokens=300)
            return commentary.strip()
        except Exception as e:
            logger.warning("AI综合诊断生成失败，跳过: %s", e)
            return ""

    async def _generate_action_plan(
        self, portrait: StudentPortrait, match_result: MatchResult
    ) -> dict:
        """单次LLM调用生成短期和中期行动计划"""
        gaps = match_result.dimensions.professional_skills.gap_skills
        
        student_skills = portrait.skills or []
        matched_skills = match_result.dimensions.professional_skills.matched_skills or []
        
        # 获取学生专业信息
        student_major = portrait.basic_info.get("major", "")
        if not student_major:
            education = portrait.basic_info.get("education", [{}])[0] if portrait.basic_info.get("education") else {}
            student_major = education.get("major", "")
        
        # 获取学生优势和劣势
        student_strengths = portrait.highlights or []
        student_weaknesses = portrait.weaknesses or []
        
        internship_details = []
        for i in (portrait.internships or [])[:3]:
            internship_details.append({
                "company": i.get("company", ""),
                "role": i.get("role", ""),
                "months": i.get("duration_months") or 0,
                "description": i.get("description", "")[:100],
                "achievements": i.get("achievements", [])[:3],
            })
        
        project_details = []
        for p in (portrait.projects or [])[:3]:
            project_details.append({
                "name": p.get("name", ""),
                "tech_stack": p.get("tech_stack", []),
                "description": p.get("description", "")[:150],
                "achievements": p.get("achievements", [])[:3],
                "github_url": p.get("github_url", ""),
            })

        # 提取市场数据用于个性化 prompt
        md = match_result.dimensions.market_demand
        market_avg_salary = md.avg_salary_k if md else None
        market_jd_count = md.jd_count if md else None
        market_top_companies = md.top_companies if md else []
        
        # 提取各维度得分和置信度
        dims = match_result.dimensions
        dimension_scores = {
            "basic": dims.basic_requirements.score,
            "skills": dims.professional_skills.score,
            "qualities": dims.professional_qualities.score,
            "potential": dims.development_potential.score,
        }
        
        dimension_confidence = match_result.dimension_confidence or {}

        prompt = render_prompt(
            "report_action_plan_v1.jinja2",
            job_title=match_result.job_title,
            job_level=self._determine_job_level(portrait),
            overall_score=match_result.overall_score,
            skill_gaps=[g.model_dump() for g in gaps[:5]],
            student_grade=portrait.basic_info.get("grade", "应届"),
            student_major=student_major,
            student_strengths=student_strengths[:3],
            student_weaknesses=student_weaknesses[:3],
            internship_months=sum((i.get("duration_months") or 0) for i in portrait.internships),
            student_skills=student_skills[:10],
            matched_skills=matched_skills[:5],
            internship_details=internship_details,
            project_details=project_details,
            competitiveness_level=portrait.competitiveness_level,
            avg_salary_k=market_avg_salary,
            jd_count=market_jd_count,
            top_companies=market_top_companies,
            dimension_scores=dimension_scores,
            dimension_confidence=dimension_confidence,
            competitive_context=match_result.competitive_context,
        )

        try:
            llm_t0 = time.monotonic()
            raw = await llm_client.chat(prompt, temperature=0.4)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(raw.strip())
            logger.info("行动计划LLM生成完成 [%.2fs]", time.monotonic() - llm_t0)
            # O2-d: 对行动计划中推荐的技能做知识库命中标记
            result = self._tag_kb_verified(result)
            return result
        except Exception as e:
            logger.warning("行动计划LLM生成失败，启用规则降级: %s", e)
            job_title = match_result.job_title
            gap_names = [g.skill for g in gaps[:3]]
            return {
                "short_term": {
                    "title": "短期行动计划（30天）",
                    "goals": [f"系统学习 {gap_names[0]}" if gap_names else "巩固核心技能基础"],
                    "milestones": [
                        {"week": 1, "action": "完成技能差距自评，制定学习路线"},
                        {"week": 2, "action": f"学习 {gap_names[0]} 基础知识" if gap_names else "完成一个技术练习项目"},
                        {"week": 3, "action": "通过实战项目巩固所学技能"},
                        {"week": 4, "action": "完成阶段性成果总结与复盘"},
                    ],
                },
                "mid_term": {
                    "title": f"中期发展计划（3-6个月）— 目标岗位：{job_title}",
                    "goals": [
                        f"补齐 {', '.join(gap_names[:2])} 等关键技能" if gap_names else "提升综合竞争力",
                        "积累项目经验，丰富作品集",
                        "关注行业动态，拓展职业人脉",
                    ],
                    "milestones": [
                        {"month": 1, "action": "完成核心技能的系统学习"},
                        {"month": 2, "action": "参与开源项目或完成个人作品"},
                        {"month": 3, "action": "投递目标岗位实习/全职，获取面试反馈"},
                    ],
                },
                "_degraded": True,
            }

    def _tag_kb_verified(self, action_plan: dict) -> dict:
        """O2-d: 对行动计划中推荐的技能/资源名称做知识库命中检查，标注 kb_verified 字段。
        不改变原有结构，仅在 action_plan 顶层追加 verified_skills/unverified_skills 两个列表。
        """
        try:
            from app.services.rag_service import search_knowledge_base
            from app.constants import SKILL_SUGGESTIONS
            # 收集行动计划中提到的所有技能名（从 goals 文本中提取）
            all_text = ""
            for phase in ("short_term", "mid_term"):
                phase_data = action_plan.get(phase) or {}
                all_text += " ".join(phase_data.get("goals") or [])
                for m in (phase_data.get("milestones") or []):
                    all_text += " " + (m.get("action") or "")

            # 简单关键词提取：技术名词（2-15字的连续非标点串）
            import re as _re
            candidates = _re.findall(r'[A-Za-z][A-Za-z0-9+#\-\.]{1,14}|[\u4e00-\u9fa5]{2,8}', all_text)
            candidates = list(set(c for c in candidates if len(c) >= 2))[:20]

            verified, unverified = [], []
            for cand in candidates:
                in_skills = cand.lower() in {s.lower() for s in SKILL_SUGGESTIONS}
                in_kb = bool(search_knowledge_base(cand, top_k=1))
                if in_skills or in_kb:
                    verified.append(cand)
                else:
                    unverified.append(cand)

            action_plan["_kb_verified_skills"] = verified[:10]
            action_plan["_kb_unverified_skills"] = unverified[:5]
            logger.debug("O2-d KB验证: verified=%d unverified=%d", len(verified), len(unverified))
        except Exception as e:
            logger.debug("O2-d KB验证跳过: %s", e)
        return action_plan

    def _build_radar_data(self, match_result: MatchResult) -> dict:
        """构建雷达图数据"""
        dims = match_result.dimensions
        return {
            "radar": [
                {"dimension": "基础要求", "score": dims.basic_requirements.score},
                {"dimension": "职业技能", "score": dims.professional_skills.score},
                {"dimension": "职业素养", "score": dims.professional_qualities.score},
                {"dimension": "发展潜力", "score": dims.development_potential.score},
            ],
            "total": match_result.overall_score,
        }

    def _chapter_1_overview(self, portrait: StudentPortrait, ai_commentary: str = "") -> ReportChapter:
        """第一章：个人概述（完整详细版，含C-5 AI综合诊断）"""
        name = portrait.basic_info.get('name', '未填写')
        school = portrait.basic_info.get('school', '未填写')
        major = portrait.basic_info.get('major', '未填写')
        grade = portrait.basic_info.get('grade', '未填写')
        highlights = portrait.highlights or []
        weaknesses = portrait.weaknesses or []

        content = f"""## 基本信息
- **姓名**：{name}
- **学校**：{school}
- **专业**：{major}
- **年级**：{grade}

## 能力画像完整度
- **完整度评分**：{portrait.completeness * 100:.0f}%
- **竞争力评分**：{portrait.competitiveness}分（{portrait.competitiveness_level}级）

"""
        # 教育背景（完整列出）
        edu_list = portrait.education or []
        if edu_list:
            content += "## 教育背景\n"
            for edu in edu_list[:3]:
                degree = edu.get('degree', '')
                edu_school = edu.get('school', school)
                edu_major = edu.get('major', major)
                start = edu.get('start_year', '')
                end = edu.get('end_year', '至今')
                gpa = edu.get('gpa', '')
                line = f"- **{degree}**　{edu_school}　{edu_major}"
                if start:
                    line += f"（{start} - {end}）"
                if gpa:
                    line += f"　GPA：{gpa}"
                content += line + "\n"
            content += "\n"

        # 专业技能（完整标签列）
        if portrait.skills:
            content += "## 专业技能\n"
            content += "　".join([f"`{s}`" for s in portrait.skills[:20]]) + "\n\n"

        # 实习经历摘要
        internships = portrait.internships or []
        if internships:
            content += "## 实习经历\n"
            for intern in internships[:5]:
                company = intern.get('company', '')
                role = intern.get('role', '')
                months = intern.get('duration_months') or 0
                desc = intern.get('description', '')
                line = f"- **{company}**·{role}"
                if months:
                    line += f"（{months}个月）"
                if desc:
                    line += f"　{desc[:60]}{'...' if len(desc) > 60 else ''}"
                content += line + "\n"
            content += "\n"

        # 项目经历摘要
        projects = portrait.projects or []
        if projects:
            content += "## 项目经历\n"
            for proj in projects[:4]:
                pname = proj.get('name', '')
                techs = proj.get('tech_stack', [])
                pdesc = proj.get('description', '')
                tech_str = "、".join(techs[:4]) if techs else ""
                line = f"- **{pname}**"
                if tech_str:
                    line += f"（{tech_str}）"
                if pdesc:
                    line += f"：{pdesc[:60]}{'...' if len(pdesc) > 60 else ''}"
                content += line + "\n"
            content += "\n"

        # 证书与奖项
        certs = portrait.certs or []
        awards = portrait.awards or []
        if certs or awards:
            content += "## 证书 & 奖项\n"
            for c in certs[:5]:
                content += f"- 🏅 {c}\n"
            for a in awards[:5]:
                content += f"- 🏆 {a}\n"
            content += "\n"

        # 求职意向
        career_intent = getattr(portrait, 'career_intent', None) or portrait.basic_info.get('career_intent', '')
        if career_intent:
            content += f"## 求职意向\n{career_intent}\n\n"

        # 意向城市 & 文化偏好
        preferred_cities = getattr(portrait, 'preferred_cities', None) or []
        culture_preference = getattr(portrait, 'culture_preference', None) or []
        if preferred_cities or culture_preference:
            content += "## 求职偏好\n"
            if preferred_cities:
                content += f"- **意向城市**：{', '.join(preferred_cities[:5])}\n"
            if culture_preference:
                content += f"- **偏好文化**：{', '.join(culture_preference[:3])}\n"
            content += "\n"

        # 兴趣领域 & 个性特点
        interests = getattr(portrait, 'interests', None) or []
        personality_traits = getattr(portrait, 'personality_traits', None) or []
        if interests:
            content += f"## 兴趣领域\n{'　'.join(interests[:6])}\n\n"
        if personality_traits:
            content += f"## 个性特点\n{'　'.join(personality_traits[:5])}\n\n"

        # 软技能评估
        inferred_soft_skills = getattr(portrait, 'inferred_soft_skills', None) or {}
        if inferred_soft_skills:
            skill_label_map = {
                "communication": "沟通能力", "learning_ability": "学习能力",
                "stress_resistance": "抗压能力", "innovation": "创新能力",
                "teamwork": "团队协作", "leadership": "领导力",
                "problem_solving": "问题解决",
            }
            content += "## 软技能评估\n"
            for key, val in list(inferred_soft_skills.items())[:6]:
                label = skill_label_map.get(key, key)
                score = val.get('score', 0) if isinstance(val, dict) else val
                evidence = val.get('evidence', '') if isinstance(val, dict) else ''
                bar = '█' * int((score or 0) // 20) + '░' * (5 - int((score or 0) // 20))
                content += f"- **{label}**：{bar} {score or 0}分"
                if evidence:
                    content += f"　（{evidence[:40]}）"
                content += "\n"
            content += "\n"

        content += "## 核心优势\n"
        for h in highlights[:5]:
            content += f"- ✅ {h}\n"

        content += "\n## 待提升项\n"
        for w in weaknesses[:5]:
            content += f"- ⚠️ {w}\n"

        # C-5: AI综合诊断（LLM生成个性化评语）
        if ai_commentary:
            content += f"\n## AI综合诊断\n> {ai_commentary}\n"

        return ReportChapter(
            index=1,
            icon="📊",
            title="个人概述",
            content_md=content,
        )

    def _chapter_2_match_analysis(self, match_result: MatchResult) -> ReportChapter:
        """第二章：人岗匹配分析"""
        dims = match_result.dimensions

        md = dims.market_demand
        market_row = f"| 市场需求 | {md.score:.0f}分 | {md.detail} |\n" if md else ""

        # 分析匹配优势和不足
        strengths = []
        weaknesses = []
        
        if dims.basic_requirements.score >= 80:
            strengths.append(f"基础要求：{dims.basic_requirements.detail}")
        elif dims.basic_requirements.score < 60:
            weaknesses.append(f"基础要求：{dims.basic_requirements.detail}")
        
        if dims.professional_skills.score >= 80:
            strengths.append(f"职业技能：匹配{len(dims.professional_skills.matched_skills)}项技能")
        elif dims.professional_skills.score < 60:
            weaknesses.append(f"职业技能：仅匹配{len(dims.professional_skills.matched_skills)}项技能")
        
        if dims.professional_qualities.score >= 80:
            strengths.append(f"职业素养：{dims.professional_qualities.detail}")
        elif dims.professional_qualities.score < 60:
            weaknesses.append(f"职业素养：{dims.professional_qualities.detail}")
        
        if dims.development_potential.score >= 80:
            strengths.append(f"发展潜力：{dims.development_potential.detail}")
        elif dims.development_potential.score < 60:
            weaknesses.append(f"发展潜力：{dims.development_potential.detail}")

        # 构建核心优势部分
        strengths_content = ""
        if strengths:
            for strength in strengths:
                strengths_content += f"- ✅ {strength}\n"
        else:
            strengths_content = "- 暂无明显优势，需要全面提升\n"
        
        # 构建待提升项部分
        weaknesses_content = ""
        if weaknesses:
            for weakness in weaknesses:
                weaknesses_content += f"- ⚠️ {weakness}\n"
        else:
            weaknesses_content = "- 各维度表现均衡，可进一步优化细节\n"
        
        # 构建维度置信度部分
        confidence_content = ""
        if hasattr(match_result, 'dimension_confidence') and match_result.dimension_confidence:
            confidence_content = "\n## 评估置信度\n"
            for dim, conf in match_result.dimension_confidence.items():
                conf_pct = conf * 100
                if conf_pct >= 80:
                    confidence_content += f"- **{dim}**：{conf_pct:.1f}%（高）\n"
                elif conf_pct >= 60:
                    confidence_content += f"- **{dim}**：{conf_pct:.1f}%（中）\n"
                else:
                    confidence_content += f"- **{dim}**：{conf_pct:.1f}%（低）\n"
            confidence_content += "\n**置信度说明**：置信度反映了评估结果的可靠性，基于数据完整性和评估方法的准确性。\n"

        # 构建技能匹配详情部分
        skill_match_details = ""
        if hasattr(dims.professional_skills, 'match_details') and dims.professional_skills.match_details:
            skill_match_details = "\n## 技能匹配详情\n"
            for detail in dims.professional_skills.match_details[:10]:
                match_type = detail.get('match_type', 'unknown')
                match_type_map = {
                    'exact': '精确匹配',
                    'synonym': '同义词匹配',
                    'contains': '包含匹配',
                    'partial': '部分匹配',
                    'category': '类别匹配',
                    'semantic': '语义匹配'
                }
                match_type_name = match_type_map.get(match_type, match_type)
                skill_match_details += f"- **{detail.get('job_skill', 'N/A')}**：与**{detail.get('student_skill', 'N/A')}** {match_type_name}（得分：{detail.get('final_score', 0):.2f}）\n"

        content = f"""## 目标岗位
**{match_result.job_title}** · 综合匹配度 **{match_result.overall_score}分**

## 匹配概况

### 核心优势
{strengths_content}

### 待提升项
{weaknesses_content}

## 五维度评分

| 维度 | 得分 | 说明 |
|------|------|------|
| 基础要求 | {dims.basic_requirements.score}分 | {dims.basic_requirements.detail} |
| 职业技能 | {dims.professional_skills.score}分 | 匹配{len(dims.professional_skills.matched_skills)}项技能 |
| 职业素养 | {dims.professional_qualities.score}分 | {dims.professional_qualities.detail} |
| 发展潜力 | {dims.development_potential.score}分 | {dims.development_potential.detail} |
{market_row}
{confidence_content}
{skill_match_details}
## 关键差距（I4可解释溯源）
"""
        action_items = []
        for gap in dims.professional_skills.gap_skills[:5]:
            content += f"""### {gap.skill}
- **重要性**：{gap.importance}
- **JD原文**：{gap.jd_source}
- **补齐建议**：{gap.suggestion}

"""
            action_items.append(ActionItem(
                title=f"补齐{gap.skill}",
                timeline="1-4周",
                description=gap.suggestion,
                jd_source=gap.jd_source,
            ))

        # 添加竞争定位信息
        if match_result.competitive_context:
            content += f"""## 竞争定位
{match_result.competitive_context}
"""

        return ReportChapter(
            index=2,
            icon="🎯",
            title="人岗匹配分析",
            content_md=content,
            action_items=action_items,
        )

    def _chapter_3_career_path(self, match_result: MatchResult) -> ReportChapter:
        """第三章：职业路径规划（含换岗难度/预计周期）"""
        paths = self.graph.get_all_paths(match_result.job_title)

        content = f"## 目标岗位：{match_result.job_title}\n\n"

        promotion_paths = paths.get("promotion_paths", [])
        if promotion_paths:
            content += "### 垂直晋升路径\n\n"
            for i, path in enumerate(promotion_paths[:2], 1):
                path_str = " → ".join([n.get("title", "") for n in path["nodes"] if n])
                content += f"**路径{i}**：{path_str}\n\n"
                for trans in path["transitions"]:
                    content += f"- **{trans['to']}**（{trans.get('years', '')}）：{trans.get('description', '')}\n"
                content += "\n"
        else:
            # fallback：用行业岗位发展路径填充，确保章节不为空
            from app.data.industry_insights import get_career_path_for_job
            fallback_paths = get_career_path_for_job(match_result.job_title)
            content += "### 垂直晋升路径\n\n"
            if fallback_paths:
                for p in fallback_paths:
                    content += f"- **{p['level']}**（{p['years']}，{p['salary']}）：{', '.join(p['skills'][:3])}\n"
                content += "\n"
            else:
                content += "（请参考岗位知识图谱中的晋升路径）\n\n"

        _difficulty_label = {"easy": "低难度", "medium": "中等难度", "hard": "高难度"}
        transfer_paths = paths.get("transfer_paths", [])
        if transfer_paths:
            content += "### 横向换岗路径\n\n"
            for tp in transfer_paths[:3]:
                difficulty = tp.get("difficulty", "")
                months = tp.get("months_estimate")
                diff_text = f"难度：{_difficulty_label.get(difficulty, difficulty)}" if difficulty else ""
                month_text = f"预计准备周期 **{months} 个月**" if months else ""
                meta = "  |  ".join(filter(None, [diff_text, month_text]))
                content += f"""#### → {tp['target']}
- **匹配度**：{tp['match_level']}（技能重叠度 {tp.get('overlap_pct', 0):.0f}%）
- **迁移优势**：{tp.get('advantage', '')}
- **需补足**：{tp.get('need_learn', '')}
"""
                if meta:
                    content += f"- **转岗参考**：{meta}\n"
                content += "\n"
        else:
            content += "### 横向换岗路径\n（暂无关联换岗路径，可参考岗位图谱探索）\n\n"

        return ReportChapter(
            index=3,
            icon="🗺️",
            title="职业路径规划",
            content_md=content,
        )

    def _chapter_4_industry_insight(self, match_result: MatchResult) -> ReportChapter:
        """第四章：行业洞察（使用 industry_insights.py + 市场真实数据）"""
        job_info = self.graph.get_job_info(match_result.job_title)

        # 行业识别：优先从岗位画像，否则用智能映射
        raw_industry = job_info.get("industry", "") if job_info else ""
        industry = raw_industry or get_industry_for_job(match_result.job_title)

        # 从 industry_insights.py 取深度洞察数据
        default_trend = {
            "trend": "稳定发展",
            "growth_rate": "未知",
            "drivers": ["技术进步", "行业需求"],
            "challenges": ["市场竞争", "技术更新快"],
            "future": "行业将持续发展，复合型技术能力更受青睐",
            "hot_skills": [],
            "salary_range": "参考岗位JD",
            "hiring_seasons": "金三银四 / 金九银十",
            "interview_focus": "技术能力 + 项目经验",
            "competitive_ratio": "中等",
            "top_cities": ["北京", "上海", "深圳"],
        }
        insight = INDUSTRY_INSIGHTS.get(industry, default_trend)

        salary = job_info.get("salary", "待定") if job_info else "待定"
        tags = job_info.get("tags", []) if job_info else []
        overview = job_info.get("overview", "") if job_info else ""

        # 从图谱获取 must_have / nice_to_have 技能分层
        must_skills, nice_skills = [], []
        if self.graph and job_info:
            job_id = f"job_{match_result.job_title}"
            for _, neighbor, data in self.graph.G.out_edges(job_id, data=True):
                etype = data.get("type") or data.get("edge_type")
                if etype == "REQUIRES":
                    sname = neighbor.replace("skill_", "")
                    if data.get("is_must", True):
                        must_skills.append(sname)
                    else:
                        nice_skills.append(sname)

        # 市场参考数据（优先真实数据）
        md = match_result.dimensions.market_demand
        if md and md.jd_count:
            demand_trend = f"当前市场在招岗位约 {md.jd_count} 个"
            salary_ref = f"平均月薪约 {md.avg_salary_k:.0f}K（真实JD数据）" if md.avg_salary_k else f"{salary}（岗位画像库参考）"
            top_cos = md.top_companies or []
            company_text = "、".join(top_cos[:5]) if top_cos else "数据更新中"
            competition = "竞争激烈" if md.jd_count > 500 else ("竞争中等" if md.jd_count > 100 else "供需平衡")
        else:
            demand_trend = "数据更新中"
            salary_ref = insight.get("salary_range", salary)
            company_text = "数据更新中"
            competition = "参考行业基准"

        # 学历门槛
        degree_req = job_info.get("degree", "") if job_info else ""
        majors = job_info.get("majors", []) if job_info else []
        entry_threshold = f"{degree_req}，{'/'.join(majors[:3])}相关专业优先" if degree_req and majors else (degree_req or "本科及以上（参见岗位JD）")

        content = f"""## 岗位概况
- **岗位名称**：{match_result.job_title}
- **所属行业**：{industry}（{insight.get('trend', '')} · {insight.get('growth_rate', '')}）
- **薪资参考**：{salary_ref}
- **市场需求**：{demand_trend}
- **竞争状况**：{competition}
- **主要招聘企业**：{company_text}
- **学历门槛**：{entry_threshold}
"""
        if overview:
            content += f"\n> {overview}\n"

        content += f"""
## 行业趋势分析（{industry}）

- **行业增长**：{insight['trend']}（{insight.get('growth_rate', '')}）
- **增长驱动因素**：{', '.join(insight['drivers'])}
- **面临挑战**：{', '.join(insight['challenges'])}
- **未来展望**：{insight['future']}
"""

        if insight.get("hot_skills"):
            content += f"\n**当前行业热门技能**：{'  |  '.join(insight['hot_skills'][:6])}\n"

        content += "\n## 必备技能（Must Have）\n"
        if must_skills:
            for i, skill in enumerate(must_skills[:8], 1):
                content += f"**{i}.** {skill}  \n"
        elif job_info and job_info.get("skills"):
            for skill in job_info["skills"][:6]:
                content += f"- {skill}\n"
        elif insight.get("hot_skills"):
            for skill in insight["hot_skills"][:5]:
                content += f"- {skill}\n"

        if nice_skills:
            content += "\n## 加分技能（Nice to Have）\n"
            for skill in nice_skills[:5]:
                content += f"- {skill}\n"

        if tags:
            content += f"\n## 岗位标签\n{'  '.join([f'`{t}`' for t in tags[:8]])}\n"

        # 岗位发展路径（来自 industry_insights）
        career_paths = get_career_path_for_job(match_result.job_title)
        if career_paths:
            content += "\n## 岗位发展路径（行业基准）\n"
            for p in career_paths:
                content += f"### {p['level']}\n- **年限**：{p['years']}　**薪资**：{p['salary']}\n- **核心技能**：{', '.join(p['skills'])}\n\n"

        # 求职策略
        score = match_result.overall_score
        if score >= 80:
            advice = f"匹配度 **{score:.0f}分**（强竞争区间）。建议重点准备项目介绍和技术深度问答，体现差异化优势。"
        elif score >= 60:
            advice = f"匹配度 **{score:.0f}分**（基本匹配区间）。优先补齐必备技能缺口，建议先投中小型企业积累经验再冲大厂。"
        else:
            advice = f"匹配度 **{score:.0f}分**（差距较大）。建议以关联岗位为跳板，6-12个月夯实基础后再正面竞争。"

        content += f"""
## 求职策略建议
{advice}

## 市场洞察
- **招聘旺季**：{insight.get('hiring_seasons', '金三银四 / 金九银十')}
- **面试重点**：{insight.get('interview_focus', '技术能力 + 项目经验')}
- **竞争参考**：{insight.get('competitive_ratio', '中等')}
- **主要城市**：{', '.join(insight.get('top_cities', ['北京', '上海', '深圳'])[:5])}
- **行业专家观点**：{industry}行业正处于{insight['trend']}阶段，{insight['drivers'][0]}等因素将持续推动行业发展
"""
        return ReportChapter(
            index=4,
            icon="📈",
            title="行业洞察",
            content_md=content,
        )

    def _chapter_5_short_term_plan(
        self, plan_data: dict, match_result: MatchResult, portrait: StudentPortrait = None
    ) -> ReportChapter:
        """第五章：短期行动计划（含30天冲刺 + 0-6个月）- 增强版"""
        content = ""
        action_items = []
        
        skill_gaps = []
        if (
            match_result.dimensions
            and match_result.dimensions.professional_skills
            and match_result.dimensions.professional_skills.gap_skills
        ):
            skill_gaps = [g.model_dump() for g in match_result.dimensions.professional_skills.gap_skills]
        
        student_info = {}
        if portrait:
            student_info = {
                "projects": [p.model_dump() if hasattr(p, 'model_dump') else p for p in (portrait.projects or [])],
                "internships": [i.model_dump() if hasattr(i, 'model_dump') else i for i in (portrait.internships or [])],
            }
        
        enhanced_items = report_enhancer.enhance_action_items(
            skill_gaps=skill_gaps,
            student_info=student_info,
            job_title=match_result.job_title,
        )
        
        sprint_items = [item for item in enhanced_items if "第" in item.timeline and "天" in item.timeline]
        if sprint_items:
            content += "## ⚡ 30天冲刺计划（立即行动）\n\n"
            for item in sprint_items:
                content += f"""### {item.title}
- **时间**：{item.timeline}
- **行动**：{item.description}
- **完成标志**：{item.verification}

"""
                action_items.append(ActionItem(
                    title=item.title,
                    timeline=item.timeline,
                    description=item.description,
                    verification=item.verification,
                ))
        
        short_term_items = [item for item in enhanced_items if "月" in item.timeline]
        content += "## 短期行动计划（0-6个月）\n\n"
        
        if short_term_items:
            for item in short_term_items:
                content += f"""### {item.title}
- **时间节点**：{item.timeline}
- **具体行动**：{item.description}
- **验证方式**：{item.verification}

"""
                action_items.append(ActionItem(
                    title=item.title,
                    timeline=item.timeline,
                    description=item.description,
                    verification=item.verification,
                ))
        else:
            gaps = match_result.dimensions.professional_skills.gap_skills if match_result.dimensions else []
            for gap in gaps[:3]:
                content += f"""### 补齐{gap.skill}
- **时间节点**：1-4周
- **具体行动**：{gap.suggestion}
- **验证方式**：完成相关项目实践

"""
                action_items.append(ActionItem(
                    title=f"补齐{gap.skill}",
                    timeline="1-4周",
                    description=gap.suggestion,
                    jd_source=gap.jd_source,
                ))
        
        validation = report_enhancer.validate_action_items([
            {"title": a.title, "timeline": a.timeline, "description": a.description, "verification": a.verification}
            for a in action_items
        ])
        if not validation["is_valid"]:
            import logging
            logging.warning(f"行动项质量验证未通过: {validation['issues']}")

        # 注入真实项目/竞赛推荐（结构化数据，非LLM生成）
        job_title = match_result.job_title
        real_projects = None
        for key in REAL_PROJECT_SUGGESTIONS:
            if key in job_title or any(k in job_title for k in key.split("/")):
                real_projects = REAL_PROJECT_SUGGESTIONS[key]
                break
        if not real_projects:
            real_projects = REAL_PROJECT_SUGGESTIONS.get("default", [])

        if real_projects:
            content += "\n## 推荐真实项目与竞赛（结构化数据）\n\n"
            content += "> 以下为真实项目/开源实践推荐，非AI生成，可直接参与练习：\n\n"
            for proj in real_projects:
                content += f"- {proj}\n"

        # 注入真实实习推荐
        internship_rec = None
        for key in REAL_INTERNSHIP_SUGGESTIONS:
            if key == "default":
                continue
            if key in job_title or any(k in job_title for k in key.split("/")):
                internship_rec = REAL_INTERNSHIP_SUGGESTIONS[key]
                break
        if not internship_rec:
            internship_rec = REAL_INTERNSHIP_SUGGESTIONS.get("default", {})

        if internship_rec:
            content += "\n## 实习机会推荐（真实渠道）\n\n"
            platforms = internship_rec.get("platforms", [])
            target_cos = internship_rec.get("target_companies", [])
            tips = internship_rec.get("tips", "")
            if platforms:
                content += "### 求职平台\n"
                for p in platforms:
                    content += f"- {p}\n"
                content += "\n"
            if target_cos:
                content += "### 目标公司方向\n"
                for co in target_cos:
                    content += f"- {co}\n"
                content += "\n"
            if tips:
                content += f"### 申请策略\n{tips}\n"

        return ReportChapter(
            index=5,
            icon="📅",
            title="短期行动计划",
            content_md=content,
            action_items=action_items,
        )

    def _chapter_6_mid_term_plan(
        self, plan_data: dict, match_result: MatchResult, portrait: StudentPortrait = None
    ) -> ReportChapter:
        """第六章：中期成长计划（6-24个月）—— 使用增强版生成"""
        mid_term = plan_data.get("mid_term", [])
        content = "## 中期成长计划（6-24个月）\n\n"
        action_items = []
        
        skill_gaps = []
        if (
            match_result.dimensions
            and match_result.dimensions.professional_skills
            and match_result.dimensions.professional_skills.gap_skills
        ):
            skill_gaps = [g.model_dump() for g in match_result.dimensions.professional_skills.gap_skills]
        
        student_info = {}
        if portrait:
            student_info = {
                "projects": [p.model_dump() if hasattr(p, 'model_dump') else p for p in (portrait.projects or [])],
                "internships": [i.model_dump() if hasattr(i, 'model_dump') else i for i in (portrait.internships or [])],
            }
        
        enhanced_milestones = report_enhancer.generate_mid_term_milestones(
            job_title=match_result.job_title,
            skill_gaps=skill_gaps,
            student_info=student_info,
        )

        if mid_term:
            for item in mid_term:
                content += f"""### {item.get('title', '')}
- **里程碑**：{item.get('milestone', '')}
- **具体行动**：{item.get('description', '')}

"""
                action_items.append(ActionItem(
                    title=item.get("title", ""),
                    timeline=item.get("milestone", ""),
                    description=item.get("description", ""),
                ))
        elif enhanced_milestones:
            for milestone in enhanced_milestones:
                content += f"""### {milestone['title']}
- **里程碑**：{milestone['milestone']}
- **具体行动**：{milestone['description']}
- **验证方式**：{milestone['verification']}

"""
                action_items.append(ActionItem(
                    title=milestone["title"],
                    timeline=milestone["milestone"],
                    description=milestone["description"],
                ))
        else:
            gaps = []
            if (
                match_result.dimensions
                and match_result.dimensions.professional_skills
                and match_result.dimensions.professional_skills.gap_skills
            ):
                gaps = [g.skill for g in match_result.dimensions.professional_skills.gap_skills[:3] if g.skill]
            gap_text = "、".join(gaps) if gaps else "核心专业技能"

            content += f"""### 第6-12个月：职场适应与专项强化
- 深化 **{gap_text}** 等关键技能至生产可用水平，通过实际项目交付验证
- 在{match_result.job_title}岗位独立完成核心任务，建立职场口碑
- 参与团队核心模块，积累可量化的项目成果

### 第12-18个月：能力跃升与影响力扩展
- 围绕{match_result.job_title}方向完成一个有完整交付物的复杂项目
- 学习进阶技能，拓展{gap_text.split('、')[0] if gaps else match_result.job_title}相关技术栈广度
- 寻求晋升机会，承担更高责任的任务或带新人

### 第18-24个月：方向确定与职业突破
- 明确{match_result.job_title}纵深发展或横向转型的长期路线
- 考取相关职业资格认证，强化简历竞争力
- 积累行业人脉，参与开源或技术社区提升行业可见度
- 制定3年职业规划，评估晋升或跳槽的最佳窗口期

## 阶段性里程碑
- ✅ 6个月：独立完成主要工作任务，获得正向绩效反馈
- ✅ 12个月：完成{gap_text.split('、')[0] if gaps else '核心技能'}强化，参与核心项目
- ✅ 18个月：具备晋升基础条件或明确下一步方向
- ✅ 24个月：完成职业方向确定，制定3-5年规划
"""

        return ReportChapter(
            index=6,
            icon="🚀",
            title="中期成长计划",
            content_md=content,
            action_items=action_items,
        )

    async def polish_report(self, action_plan: list, skill_gaps: list) -> dict:
        """使用LLM对报告行动计划和技能建议进行智能润色
        
        优化策略：
        1. 对行动计划中的goals进行具体化、可量化润色
        2. 对技能差距建议添加学习资源、时间预估
        3. 保持原有字段结构不变
        """
        if not action_plan and not skill_gaps:
            return {"action_plan": [], "skill_gaps": []}
        
        prompt = render_prompt(
            "polish_report_v1.jinja2",
            action_plan=action_plan or [],
            skill_gaps=skill_gaps or [],
        )
        
        try:
            raw = await llm_client.chat(prompt, temperature=0.4)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            result = json.loads(raw.strip())
            
            if "action_plan" not in result:
                result["action_plan"] = action_plan
            if "skill_gaps" not in result:
                result["skill_gaps"] = skill_gaps
                
            return result
            
        except Exception as e:
            import logging
            logging.warning(f"报告润色失败，返回原始数据: {e}")
            return {"action_plan": action_plan, "skill_gaps": skill_gaps}
    
    async def polish_chapter_content(self, chapter: ReportChapter) -> ReportChapter:
        """润色单个章节的Markdown内容"""
        if not chapter.content_md or len(chapter.content_md) < 50:
            return chapter
        
        prompt = f"""请润色以下职业规划报告章节内容，使其更专业、流畅、有说服力。
保持原有结构和格式（Markdown），只优化语言表达，不改变核心信息。

章节标题：{chapter.title}

原始内容：
{chapter.content_md}

润色要求：
1. 使用专业、简洁的职场语言
2. 增强逻辑连贯性和可读性
3. 保持Markdown格式不变
4. 不改变任何数据、分数、岗位名称等关键信息
5. 控制在原文长度的90%-110%之间

只输出润色后的Markdown内容，不要包含任何解释："""
        
        try:
            polished = await llm_client.chat(prompt, temperature=0.3)
            polished = polished.strip()
            if polished.startswith("```markdown"):
                lines = polished.split("\n")
                polished = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            chapter.content_md = polished
        except Exception:
            pass
        
        return chapter

    async def feedback_optimize_chapters(
        self,
        chapters_json: list,
        rating: int,
        issues: List[str],
        comment: str,
        focus_chapters: Optional[List[str]] = None,
    ) -> list:
        """根据用户评星+具体反馈，LLM针对性重新优化报告章节"""
        if not chapters_json:
            return chapters_json

        sentiment = "满意" if rating >= 4 else ("一般" if rating == 3 else "不满意")
        issue_text = f"具体问题：{'、'.join(issues)}。" if issues else ""
        comment_text = f"用户补充：{comment}" if comment else ""
        intensity = "轻度润色，语言更流畅专业" if rating >= 4 else "深度重写，大幅提升内容质量和建议可行性"

        issue_hints = {
            "内容不准确": "确保所有数据、岗位名称准确，补充更多真实行业信息",
            "建议不实用": "确保每条建议都可立即执行，附上具体资源链接或工具名称",
            "路径规划不清晰": "为每个职业阶段补充时间节点、薪资区间和核心技能要求",
            "行业洞察太泛": "补充具体的行业增长数据、头部公司名称和热门细分方向",
            "计划缺少细节": "将每项计划细化为可衡量的里程碑，添加验证方式",
        }
        targeted_hints = [issue_hints[i] for i in issues if i in issue_hints]
        hints_block = "\n".join(f"- {h}" for h in targeted_hints) if targeted_hints else ""

        optimized = []
        for ch in chapters_json:
            if ch.get("type") == "completeness_warnings":
                optimized.append(ch)
                continue
            title = ch.get("title", "")
            if focus_chapters and not any(f in title for f in focus_chapters):
                optimized.append(ch)
                continue
            content_md = ch.get("content_md") or ch.get("content", "")
            if not content_md or len(content_md) < 50:
                optimized.append(ch)
                continue

            chapter_hints = ""
            if "路径" in title:
                chapter_hints = "- 为每个职业阶段补充：典型年限、市场薪资区间、需掌握的核心技能\n"
            elif "洞察" in title:
                chapter_hints = "- 补充具体行业增长率、头部招聘企业（3-5家）、最新热门技能方向\n"
            elif "计划" in title or "行动" in title:
                chapter_hints = "- 确保每项行动有可量化的完成标准；补充具体学习资源名称\n"
            elif "概述" in title or "overview" in title.lower():
                chapter_hints = "- 突出学生核心竞争力；确保技能和经历部分完整展示\n"
            elif "匹配" in title:
                chapter_hints = "- 加强对每个维度得分的解读；量化技能差距的补足难度和时间\n"

            prompt = f"""你是职业规划专家，正在根据用户反馈优化职业报告章节。

用户评分：{rating}/5（{sentiment}）
{issue_text}{comment_text}
优化力度：{intensity}

针对性优化要求：
{hints_block if hints_block else '- 整体提升语言专业性和内容可读性'}
{chapter_hints}通用规则：
- 保持 Markdown 格式和段落结构不变
- 不改变岗位名称、分数等关键数据
- 控制在原文长度的 90%～120% 之间

章节标题：{title}

原始内容：
{content_md}

只输出优化后的 Markdown，不要包含任何解释："""

            try:
                t0 = time.monotonic()
                polished = await llm_client.chat(prompt, temperature=0.35)
                polished = polished.strip()
                if polished.startswith("```"):
                    lines = polished.split("\n")
                    polished = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                ch_copy = dict(ch)
                ch_copy["content_md"] = polished
                ch_copy["content"] = polished   # 保持与 DB 字段一致
                optimized.append(ch_copy)
                logger.info("反馈优化章节 '%s' [%.2fs]", title, time.monotonic() - t0)
            except Exception as e:
                logger.warning("反馈优化章节 '%s' 失败: %s", title, e)
                optimized.append(ch)

        return optimized

    def export_markdown(self, report: CareerReport) -> str:
        """导出Markdown格式"""
        lines = [
            "# 🎓 职业生涯发展报告",
            "",
            f"**报告对象**：{report.student_name}",
            f"**目标岗位**：{report.target_job}",
            f"**综合匹配度**：{report.overall_score}分",
            f"**生成时间**：{report.created_at}",
            "",
            "---",
            "",
        ]

        for chapter in report.chapters:
            lines.append(f"## {chapter.icon} {chapter.title}")
            lines.append("")
            lines.append(chapter.content_md)
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"> 报告生成时间：{report.created_at}")
        lines.append("> 本报告由AI职业规划智能体生成，仅供参考")

        return "\n".join(lines)


    # ------------------------------------------------------------------
    # A-3: 报告质量自检
    # ------------------------------------------------------------------
    async def auto_quality_check(self, report_id: str) -> dict:
        """
        对已生成报告做自检，返回质量评分和改进建议。
        检查维度：完整度 / 章节长度 / 行动计划有效性 / 技能缺口覆盖
        """
        from app.db.database import get_db_session
        from app.db.crud.report_crud import report_crud

        async with get_db_session() as session:
            report_row = await report_crud.get_by_report_id(session, report_id)

        if not report_row:
            return {"error": "report_not_found"}

        chapters = report_row.chapters_json or []
        action_plan = report_row.action_plan or []
        skill_gaps = report_row.skill_gaps or []
        overall_score = report_row.overall_score or 0

        issues = []
        score = 100

        # 1. 章节完整度
        if len(chapters) < 4:
            issues.append({"dim": "章节完整度", "desc": f"章节数不足（{len(chapters)}/6），报告可能不完整"})
            score -= 20
        for ch in chapters:
            content = ch.get("content", "") or ""
            if len(content) < 80:
                issues.append({"dim": "章节内容", "desc": f"章节《{ch.get('title','')}》内容过短（{len(content)}字）"})
                score -= 5

        # 2. 行动计划有效性
        if len(action_plan) == 0:
            issues.append({"dim": "行动计划", "desc": "未生成行动计划，缺乏可操作性"})
            score -= 15
        elif len(action_plan) < 3:
            issues.append({"dim": "行动计划", "desc": f"行动计划条数较少（{len(action_plan)}条），建议补充"})
            score -= 5

        # 3. 技能缺口覆盖
        if overall_score < 60 and len(skill_gaps) == 0:
            issues.append({"dim": "技能缺口", "desc": "匹配度偏低但未识别技能缺口，建议重新分析"})
            score -= 10

        score = max(score, 0)
        quality_level = "优秀" if score >= 85 else "良好" if score >= 70 else "一般" if score >= 50 else "待改进"

        logger.info("[QualityCheck] report=%s score=%d level=%s issues=%d", report_id, score, quality_level, len(issues))
        return {
            "report_id": report_id,
            "quality_score": score,
            "quality_level": quality_level,
            "issues": issues,
            "chapter_count": len(chapters),
            "action_plan_count": len(action_plan),
        }


report_service = ReportService()
