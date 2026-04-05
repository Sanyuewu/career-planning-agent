# -*- coding: utf-8 -*-
"""
人岗匹配引擎 - 核心服务
遵循v4规范：
- 维度一/二：规则计算（可复现、速度快）
- 维度三/四：LLM评估（match_analysis_v1.jinja2）
- I1语义图谱匹配
- I4可解释溯源报告
"""

import hashlib
import json
import math
import logging
import time as _time_mod
from typing import Optional, List, Dict, Tuple, Any
from pydantic import BaseModel, Field
from cachetools import TTLCache
from app.graph.job_graph_repo import job_graph
from app.ai.llm_client import llm_client, render_prompt
from app.constants import DEGREE_MAP, WEIGHT_PRESETS, SKILL_SUGGESTIONS, INDUSTRY_WEIGHT_OVERRIDES
from app.services.match_service_optimized import optimized_matcher

logger = logging.getLogger(__name__)


class GapItem(BaseModel):
    """技能差距项"""
    skill: str
    importance: str = Field(description="must_have或nice_to_have")
    jd_source: str = Field(description="JD原文引用，I4可解释性核心")
    suggestion: str = Field(description="具体可操作的补齐建议")
    student_level: str = Field(default="未掌握", description="学生当前熟练度（未掌握/了解/掌握/熟练/精通）")


class DimensionScore(BaseModel):
    """维度得分"""
    score: float = Field(ge=0, le=100)
    detail: str = Field(description="得分说明")
    evidence: str = Field(description="评分依据")


class ProfessionalSkillsScore(BaseModel):
    """职业技能维度得分"""
    score: float
    matched_skills: List[str] = []
    gap_skills: List["GapItem"] = []
    semantic_matched: List[Dict] = Field(default_factory=list, description="I1语义匹配结果")
    raw_match_details: List[Dict] = Field(default_factory=list, description="原始匹配明细（含每个岗位技能的匹配情况）")
    skill_importance_map: Dict[str, str] = Field(default_factory=dict, description="岗位技能重要度映射")


class MarketDemandScore(BaseModel):
    """第5维度：市场需求度（基于真实JD数据）"""
    score: float = Field(ge=0, le=100)
    jd_count: int = Field(description="真实招聘JD数量")
    avg_salary_k: float = Field(description="平均月薪（千元）")
    top_companies: List[str] = Field(default_factory=list)
    detail: str


class MatchDimensions(BaseModel):
    """五维度匹配结果"""
    basic_requirements: DimensionScore
    professional_skills: ProfessionalSkillsScore
    professional_qualities: DimensionScore
    development_potential: DimensionScore
    market_demand: Optional[MarketDemandScore] = None


class TransferPath(BaseModel):
    """换岗建议"""
    target: str = Field(description="目标岗位名称")
    match_level: str = Field(description="匹配等级：高/中/低")
    overlap_pct: float = Field(description="技能重叠百分比")
    advantage: str = Field(description="转岗优势")
    need_learn: str = Field(description="需要学习的技能")


class MatchResult(BaseModel):
    """人岗匹配结果"""
    job_id: str
    job_title: str
    overall_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    dimension_confidence: Dict[str, float] = Field(default_factory=dict, description="各维度置信度")
    dimensions: MatchDimensions
    weight_used: Dict[str, float]
    summary: str
    is_degraded: bool = False
    competitive_context: str = ""
    transfer_paths: List[TransferPath] = Field(default_factory=list, description="换岗建议列表")
    job_context: Dict[str, Any] = Field(default_factory=dict, description="岗位背景信息（地区/文化/学历要求）")
    explanation_tree: List[Dict[str, Any]] = Field(default_factory=list, description="D-2: 可解释得分溯源树")
    # 前端详情展示字段
    confidence_breakdown: Dict[str, Any] = Field(default_factory=dict, description="置信度分项拆解")
    skill_match_details: List[Dict[str, Any]] = Field(default_factory=list, description="每个技能的匹配明细")
    gap_analysis: List[Dict[str, Any]] = Field(default_factory=list, description="差距分析（含改进建议）")
    # 准确率元数据（来自 accuracy_service，基于历史基准测试 + 用户反馈）
    accuracy_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="准确率元数据：{confidence_bucket, empirical_accuracy, industry, review_flag, review_reason}",
    )


# WEIGHT_PRESETS, DEGREE_MAP, SKILL_SUGGESTIONS 均从 app.constants 导入（见文件顶部）


class MatchService:
    """人岗匹配服务"""

    def __init__(self):
        self.graph = job_graph
        # O3-a: 匹配结果内存缓存，TTL=30分钟，最多500条
        self._result_cache: TTLCache = TTLCache(maxsize=500, ttl=1800)

    def _cache_key(self, student_portrait: dict, job_name: str, weight_preset: str) -> str:
        """生成缓存 key = student_id:job_name:preset:skills_hash"""
        student_id = student_portrait.get("student_id") or student_portrait.get("basic_info", {}).get("name", "")
        skills = sorted(student_portrait.get("skills") or [])
        skills_hash = hashlib.md5(json.dumps(skills, ensure_ascii=False).encode()).hexdigest()[:8]
        return f"{student_id}:{job_name}:{weight_preset}:{skills_hash}"

    async def compute_match(
        self,
        student_portrait: dict,
        job_name: str,
        weight_preset: str = "default",
        db_session=None,
    ) -> MatchResult:
        """
        计算人岗匹配度（异步，维度三/四使用LLM评估）

        Args:
            student_portrait: 学生画像字典
            job_name: 目标岗位名称
            weight_preset: 权重预设

        Returns:
            MatchResult: 匹配结果
        """
        t0 = _time_mod.monotonic()
        student_name = student_portrait.get("basic_info", {}).get("name", "unknown")
        logger.info("开始计算匹配度: student=%s job=%s preset=%s", student_name, job_name, weight_preset)

        # O3-a: 缓存命中检查
        cache_key = self._cache_key(student_portrait, job_name, weight_preset)
        if cache_key in self._result_cache:
            cached = self._result_cache[cache_key]
            cached.summary = cached.summary.replace("（已缓存）", "") + "（已缓存）"
            logger.info("匹配结果缓存命中 [%.2fms]: student=%s job=%s",
                        (_time_mod.monotonic() - t0) * 1000, student_name, job_name)
            return cached

        job_info = self.graph.get_job_info(job_name)
        if not job_info:
            logger.warning("未找到岗位: %s", job_name)
            raise ValueError(f"未找到岗位: {job_name}")

        weights = dict(WEIGHT_PRESETS.get(weight_preset, WEIGHT_PRESETS["default"]))
        # 行业动态权重覆盖
        industry = job_info.get("industry_category", "")
        for kw, override in INDUSTRY_WEIGHT_OVERRIDES.items():
            if kw in industry:
                weights.update(override)
                logger.debug("应用行业权重覆盖: industry=%s override=%s", kw, override)
                break

        basic_score = self._score_basic(student_portrait, job_info)
        skills_result = self._score_skills(student_portrait, job_info)

        qualities_score, potential_score, is_degraded, competitive_context = await self._score_qualities_potential(
            student_portrait, job_info, skills_result,
            prior_basic_score=basic_score.score,
        )

        # 第5维度：市场需求度（需要数据库会话）
        market_score = None
        if db_session is not None:
            market_score = await self._score_market_demand(job_name, db_session)

        dimensions = MatchDimensions(
            basic_requirements=basic_score,
            professional_skills=skills_result,
            professional_qualities=qualities_score,
            development_potential=potential_score,
            market_demand=market_score,
        )

        overall = self._compute_overall(
            {
                "basic": basic_score.score,
                "skills": skills_result.score,
                "qualities": qualities_score.score,
                "potential": potential_score.score,
            },
            weights,
        )

        # 计算各维度得分
        dim_scores = {
            "basic": basic_score.score,
            "skills": skills_result.score,
            "qualities": qualities_score.score,
            "potential": potential_score.score,
        }
        
        confidence_result = self._compute_confidence(
            student_portrait.get("completeness", 0.5),
            student_portrait.get("soft_skills_null_count", 0),
            dim_scores,
        )
        
        confidence = confidence_result['overall']

        summary = self._generate_summary(overall, dimensions, job_name)
        transfer_paths = self._get_transfer_paths(job_name)

        logger.info(
            "匹配计算完成 [%.2fs]: student=%s job=%s score=%.1f confidence=%.2f degraded=%s "
            "basic=%.1f skills=%.1f qualities=%.1f potential=%.1f",
            _time_mod.monotonic() - t0, student_name, job_name, overall, confidence, is_degraded,
            basic_score.score, skills_result.score, qualities_score.score, potential_score.score,
        )

        # 岗位背景信息（地区/文化/学历要求）— 从 job graph node attrs 提取
        job_context = {
            "top_regions":     job_info.get("top_regions", []),
            "culture_types":   job_info.get("culture_types", []),
            "top_companies":   job_info.get("top_companies", []),
            "education_level": job_info.get("education_level", ""),
            "majors":          job_info.get("majors", []),
            "industry":        job_info.get("industry", job_info.get("industry_category", "")),
        }

        # D-2: 构建可解释得分溯源树
        explanation_tree = self._build_explanation_tree(
            student_portrait, job_info, dim_scores, weights,
            basic_score, skills_result, qualities_score, potential_score, overall
        )

        # 前端详情字段：confidence_breakdown / skill_match_details / gap_analysis
        confidence_breakdown = self._build_confidence_breakdown(
            student_portrait, skills_result, confidence
        )
        skill_match_details = self._build_skill_match_details(skills_result)
        gap_analysis = self._build_gap_analysis(skills_result.gap_skills)

        # 准确率元数据：基于历史 benchmark + 用户反馈校准
        from app.services.accuracy_service import accuracy_service
        job_industry = job_info.get("industry_category", "其他") or "其他"
        accuracy_meta = accuracy_service.get_accuracy_metadata(
            confidence=confidence,
            industry=job_industry,
        )
        # 生产日志（非阻塞，供后续校准用）
        student_id = student_portrait.get("student_id") or ""
        accuracy_service.log_match_event(
            student_id=student_id,
            job_name=job_name,
            industry=job_industry,
            confidence=confidence,
            matched_count=len(skills_result.matched_skills),
            gap_count=len(skills_result.gap_skills),
            overall_score=overall,
        )

        result = MatchResult(
            job_id=job_name,
            job_title=job_name,
            overall_score=overall,
            confidence=confidence,
            dimension_confidence=confidence_result['dimensions'],
            dimensions=dimensions,
            weight_used=weights,
            summary=summary,
            is_degraded=is_degraded,
            competitive_context=competitive_context,
            transfer_paths=transfer_paths,
            job_context=job_context,
            explanation_tree=explanation_tree,
            confidence_breakdown=confidence_breakdown,
            skill_match_details=skill_match_details,
            gap_analysis=gap_analysis,
            accuracy_metadata=accuracy_meta,
        )
        # O3-a: 缓存结果（db_session 的动态 market_score 不参与缓存 key，不影响主要评分）
        self._result_cache[cache_key] = result
        return result

    def _build_explanation_tree(
        self,
        student: dict,
        job_info: dict,
        dim_scores: dict,
        weights: dict,
        basic_score,
        skills_result,
        qualities_score,
        potential_score,
        overall: float,
    ) -> List[Dict[str, Any]]:
        """D-2: 构建可解释得分溯源树，每个维度附带子因素明细"""
        dim_name_map = {
            "basic": "基础要求",
            "skills": "专业技能",
            "qualities": "职业素质",
            "potential": "发展潜力",
        }
        weight_map = {
            "basic": weights.get("basic", 0.2),
            "skills": weights.get("skills", 0.35),
            "qualities": weights.get("qualities", 0.25),
            "potential": weights.get("potential", 0.2),
        }

        tree = []

        # 基础要求
        student_edu = (student.get("education") or [{}])[0].get("degree", "")
        req_edu = job_info.get("education_level", "")
        tree.append({
            "dim": "basic",
            "label": dim_name_map["basic"],
            "score": round(dim_scores["basic"], 1),
            "weight": weight_map["basic"],
            "contribution": round(dim_scores["basic"] * weight_map["basic"], 1),
            "factors": [
                {"name": "学历匹配", "value": f"你的学历：{student_edu or '未知'}，要求：{req_edu or '不限'}"},
                {"name": "专业匹配", "value": f"岗位推荐专业：{', '.join((job_info.get('majors') or [])[:3]) or '不限'}"},
            ],
        })

        # 专业技能
        student_skills = set(student.get("skills") or [])
        required_skills = set(job_info.get("skills") or [])
        matched = student_skills & required_skills
        missing = required_skills - student_skills
        tree.append({
            "dim": "skills",
            "label": dim_name_map["skills"],
            "score": round(dim_scores["skills"], 1),
            "weight": weight_map["skills"],
            "contribution": round(dim_scores["skills"] * weight_map["skills"], 1),
            "factors": [
                {"name": "技能命中", "value": f"命中 {len(matched)}/{len(required_skills)} 项：{', '.join(list(matched)[:5]) or '无'}"},
                {"name": "技能缺口", "value": f"缺少：{', '.join(list(missing)[:5]) or '无'}"},
            ],
        })

        # 职业素质 & 发展潜力（LLM评分，只展示得分）
        internship_count = len(student.get("internships") or [])
        project_count = len(student.get("projects") or [])
        tree.append({
            "dim": "qualities",
            "label": dim_name_map["qualities"],
            "score": round(dim_scores["qualities"], 1),
            "weight": weight_map["qualities"],
            "contribution": round(dim_scores["qualities"] * weight_map["qualities"], 1),
            "factors": [
                {"name": "实习经历", "value": f"{internship_count} 段实习"},
                {"name": "项目经历", "value": f"{project_count} 个项目"},
            ],
        })

        soft_skills = student.get("inferred_soft_skills") or {}
        # 兼容两种数据结构：{k: score} 或 {k: {score: x, evidence: ...}}
        def _soft_score(v):
            if isinstance(v, dict):
                return v.get("score", 0) or 0
            return v or 0
        top_soft = sorted(soft_skills.items(), key=lambda x: _soft_score(x[1]), reverse=True)[:3]
        tree.append({
            "dim": "potential",
            "label": dim_name_map["potential"],
            "score": round(dim_scores["potential"], 1),
            "weight": weight_map["potential"],
            "contribution": round(dim_scores["potential"] * weight_map["potential"], 1),
            "factors": [
                {"name": "软技能优势", "value": "、".join(f"{k}({_soft_score(v):.0f})" for k, v in top_soft) or "暂无数据"},
            ],
        })

        return tree

    def _get_transfer_paths(self, job_name: str) -> List[TransferPath]:
        """获取换岗建议"""
        try:
            raw_paths = self.graph.get_transfer_paths(job_name)
            return [
                TransferPath(
                    target=p.get("target", ""),
                    match_level=p.get("match_level", "中"),
                    overlap_pct=p.get("overlap_pct", 0.5),
                    advantage=p.get("advantage", ""),
                    need_learn=p.get("need_learn", ""),
                )
                for p in raw_paths[:5]
            ]
        except Exception:
            return []

    def _score_basic(self, student: dict, job: dict) -> DimensionScore:
        """维度一：基础要求（学历40% / 专业30% / 地区15% / 文化15%）- 规则计算"""
        s_edu = student.get("education", [{}])[0] if student.get("education") else {}
        s_degree = s_edu.get("degree") or "本科"
        s_major = s_edu.get("major") or ""

        j_degree_req = job.get("education_level", "本科")
        j_majors = job.get("majors", ["计算机", "软件", "信息", "电子"])

        s_deg_score = DEGREE_MAP.get(s_degree, 60)
        j_deg_score = DEGREE_MAP.get(j_degree_req, 60)

        if s_deg_score >= j_deg_score:
            degree_score = 100
        else:
            degree_score = round((s_deg_score / j_deg_score) * 100, 2)

        if any(m in s_major for m in j_majors):
            major_score = 100
        elif any(kw in s_major for kw in ["计算机", "软件", "信息", "电子", "数据", "网络"]):
            major_score = 70
        else:
            major_score = 40

        # 地区匹配（有偏好才算分，无偏好给中性分70不惩罚）
        top_regions = job.get("top_regions", [])
        preferred_cities = student.get("preferred_cities", [])
        if preferred_cities and top_regions:
            def _norm(c): return c.replace("市", "").replace("省", "")
            norm_pref = [_norm(c) for c in preferred_cities]
            norm_regions = [_norm(r) for r in top_regions]
            city_hits = sum(1 for c in norm_pref if any(c in r or r in c for r in norm_regions))
            location_score = min(100, 60 + city_hits * 20) if city_hits else 40
            location_match: Optional[bool] = city_hits > 0
        else:
            location_score = 70
            location_match = None  # 未设偏好

        # 文化匹配（有偏好才算分，无偏好给中性分70不惩罚）
        culture_types = job.get("culture_types", [])
        culture_preference = student.get("culture_preference", [])
        if culture_preference and culture_types:
            pref_lower = [p.lower() for p in culture_preference]
            cult_lower = [c.lower() for c in culture_types]
            cult_hits = sum(1 for p in pref_lower if any(p in c or c in p for c in cult_lower))
            culture_score = min(100, 60 + cult_hits * 20) if cult_hits else 40
            culture_match: Optional[bool] = cult_hits > 0
        else:
            culture_score = 70
            culture_match = None  # 未设偏好

        total_score = round(
            degree_score * 0.40 + major_score * 0.30 +
            location_score * 0.15 + culture_score * 0.15,
            2
        )

        loc_desc = ("城市匹配✓" if location_match is True else
                    "城市不匹配" if location_match is False else "未设城市偏好")
        cult_desc = ("文化契合✓" if culture_match is True else
                     "文化不契合" if culture_match is False else "未设文化偏好")
        detail = (
            f"学历{'达标' if degree_score >= 100 else '略低'}（{s_degree}），"
            f"专业{'匹配' if major_score >= 70 else '相关度较低'}，"
            f"{loc_desc}，{cult_desc}"
        )

        top_companies = job.get("top_companies", [])
        region_note  = f"热招城市：{'/'.join(top_regions[:3])}"   if top_regions  else ""
        culture_note = f"文化标签：{'/'.join(culture_types[:2])}" if culture_types else ""
        company_note = f"代表雇主：{'/'.join(top_companies[:2])}" if top_companies else ""
        extra = " | ".join(x for x in [region_note, culture_note, company_note] if x)

        evidence = (
            f"学生：{s_degree} {s_major}"
            + (f" | 偏好城市：{'/'.join(preferred_cities[:3])}" if preferred_cities else "")
            + (f" | 偏好文化：{'/'.join(culture_preference[:2])}" if culture_preference else "")
            + f" | 岗位要求：{j_degree_req}及以上，{','.join(j_majors[:3])}相关专业"
            + (f" | {extra}" if extra else "")
        )

        return DimensionScore(score=total_score, detail=detail, evidence=evidence)

    def _score_skills(self, student: dict, job: dict) -> ProfessionalSkillsScore:
        """维度二：职业技能（含I1语义扩展）- 使用优化版匹配器"""
        student_skills_raw = list(student.get("skills", []))
        
        # 获取学生专业信息
        student_major = ""
        education = student.get("education", [{}])[0] if student.get("education") else {}
        if education:
            student_major = education.get("major") or ""
        if not student_major:
            student_major = student.get("major") or ""
        
        job_skills = list(job.get("skills", []))
        if not job_skills:
            job_skills = list(job.get("专业技能", []))

        job_id = job.get("title", "")
        if self.graph and job_id:
            job_node_id = f"job_{job_id}" if not job_id.startswith("job_") else job_id
            for _, neighbor, data in self.graph.G.out_edges(job_node_id, data=True):
                edge_type = data.get("type") or data.get("edge_type")
                if edge_type == "REQUIRES":
                    skill_name = neighbor.replace("skill_", "")
                    if skill_name not in job_skills:
                        job_skills.append(skill_name)

        # 推断岗位类型
        job_type = "general"
        job_title = job.get("title", "").lower()
        if any(keyword in job_title for keyword in ['前端', 'frontend', 'web']):
            job_type = "frontend"
        elif any(keyword in job_title for keyword in ['后端', 'backend', 'server']):
            job_type = "backend"
        elif any(keyword in job_title for keyword in ['数据', 'data', '分析', 'analytics']):
            job_type = "data"
        elif any(keyword in job_title for keyword in ['devops', '运维', '部署', 'docker', 'k8s']):
            job_type = "devops"
        elif any(keyword in job_title for keyword in ['ai', '人工智能', '机器学习', 'ml', 'deep learning']):
            job_type = "ai"
        
        skill_result = optimized_matcher.match_skills(
            student_skills_raw,
            job_skills,
            self.graph,
            job_type=job_type,
            student_major=student_major,
        )

        matched = set(skill_result.matched_skills)
        gaps = set(skill_result.gap_skills)

        skill_importance_map: dict = {}
        if self.graph and job_id:
            job_node_id2 = f"job_{job_id}" if not job_id.startswith("job_") else job_id
            for _, neighbor, data in self.graph.G.out_edges(job_node_id2, data=True):
                etype = data.get("type") or data.get("edge_type")
                if etype == "REQUIRES":
                    skill_name = neighbor.replace("skill_", "")
                    skill_importance_map[skill_name] = "must_have" if data.get("is_must", True) else "nice_to_have"

        score = skill_result.score

        # 构建学生技能熟练度索引（来自 match_details 的 proficiency 字段）
        student_proficiency_index: dict = {}
        for d in skill_result.match_details:
            stu_skill = (d.get("student_skill") or "").lower()
            prof = d.get("proficiency") or "default"
            if stu_skill:
                student_proficiency_index[stu_skill] = prof

        _PROF_DISPLAY = {"精通": "精通", "熟练": "熟练", "掌握": "掌握", "了解": "了解", "default": "未掌握"}

        gap_items = []
        for skill in gaps:
            importance = skill_importance_map.get(skill, "must_have")
            # 查找学生对该技能的实际水平（部分匹配：学生可能有相近技能但未达标）
            skill_lower = skill.lower()
            student_level = "未掌握"
            for stu_key, prof in student_proficiency_index.items():
                if skill_lower in stu_key or stu_key in skill_lower:
                    student_level = _PROF_DISPLAY.get(prof, "了解")
                    break
            gap_items.append(GapItem(
                skill=skill,
                importance=importance,
                jd_source=f"岗位JD技能要求项：{skill}",
                suggestion=SKILL_SUGGESTIONS.get(skill, f"建议学习{skill}相关课程或项目实践"),
                student_level=student_level,
            ))

        semantic_matched = [d for d in skill_result.match_details if d.get('match_type') == 'semantic']

        return ProfessionalSkillsScore(
            score=score,
            matched_skills=list(matched),
            gap_skills=gap_items,
            semantic_matched=semantic_matched,
            raw_match_details=skill_result.match_details,
            skill_importance_map=skill_importance_map,
        )

    async def _score_qualities_potential(
        self, student: dict, job: dict, skills_result: ProfessionalSkillsScore,
        prior_basic_score: float = 0.0
    ) -> Tuple[DimensionScore, DimensionScore, bool, str]:
        """维度三/四：软技能和发展潜力 - LLM评估（带规则兜底）"""
        # 构建LLM调用上下文
        # 字段名来自 job_graph.json 节点 attrs（rebuild_data.py 写入）
        job_soft_skills = {
            "创新能力": job.get("creativity", ""),
            "学习能力": job.get("learning", ""),
            "抗压能力": job.get("stress_resistance", ""),
            "沟通能力": job.get("communication", ""),
            "团队协作": "",       # graph 中暂无此字段，由 LLM 根据岗位 overview 推断
            "问题解决": "",       # 同上
            "实习经历要求": job.get("internship", ""),
        }
        # 过滤掉空串，避免给 LLM 传入无意义条目
        job_soft_skills = {k: v for k, v in job_soft_skills.items() if v}
        # P1：模糊信息量化 — 将文字描述预转为分值基准，供 LLM 参照而非自行猜测
        _quantified = {k: self._quantify_soft_skill_text(v) for k, v in job_soft_skills.items()}
        job_soft_skill_scores = {k: v["score"] for k, v in _quantified.items()}
        # 模糊描述标注（供 prompt 注入说明）
        vague_annotations = {
            k: f"岗位要求'{v['vague_word']}{job_soft_skills[k][:20]}...'（模糊描述，已按行业中位数量化为{v['score']}分）"
            for k, v in _quantified.items() if v["is_vague"]
        }
        student_soft_skills = student.get("inferred_soft_skills", {})
        
        # 提取学生软技能证据
        soft_skill_evidence = {}
        for skill, data in student_soft_skills.items():
            if data and data.get("evidence"):
                soft_skill_evidence[skill] = data["evidence"]
        
        # 测评结果注入：将 ability_profile 中的逻辑/职业倾向/技术自评得分提供给 LLM
        ability_profile = student.get("ability_profile") or {}
        assessment_ctx = {}
        if ability_profile:
            if "logic_score" in ability_profile:
                assessment_ctx["逻辑思维得分"] = f"{ability_profile['logic_score']}/100"
            if "career_tendency" in ability_profile:
                assessment_ctx["职业倾向"] = ability_profile["career_tendency"]
            if "tech_score" in ability_profile:
                assessment_ctx["技术自评得分"] = f"{ability_profile['tech_score']}/100"

        student_ctx = {
            "awards": student.get("awards", []),
            "projects": student.get("projects", []),
            "total_internship_months": sum(
                (i.get("duration_months") or 0) for i in student.get("internships", [])
            ),
            "skills": (student.get("skills") or [])[:15],
            "internship_details": [
                {"company": i.get("company", ""), "role": i.get("role", ""), "months": i.get("duration_months") or 0, "description": i.get("description", "")[:100]}
                for i in (student.get("internships") or [])[:3]
            ],
            "project_details": [
                {"name": p.get("name", ""), "tech_stack": p.get("tech_stack", []), "description": (p.get("description", "") or "")[:150], "achievements": p.get("achievements", [])[:3]}
                for p in (student.get("projects") or [])[:3]
            ],
            "soft_skill_evidence": soft_skill_evidence,
            "assessment_results": assessment_ctx,
        }

        try:
            # RAG：优先使用 JSON 知识库降级检索，chromadb 不可用时仍可获得岗位上下文
            rag_context = ""
            try:
                from app.services.rag_service import search_knowledge_base
                job_title = job.get("title", "")
                kb_hits = search_knowledge_base(job_title, top_k=1)
                if kb_hits:
                    kb = kb_hits[0]
                    parts = []
                    if kb.get("description"):
                        parts.append(f"岗位描述：{kb['description']}")
                    if kb.get("core_skills"):
                        parts.append(f"核心技能：{', '.join(kb['core_skills'])}")
                    if kb.get("market_outlook"):
                        parts.append(f"市场前景：{kb['market_outlook']}")
                    if kb.get("promotion_path"):
                        parts.append(f"晋升路径：{kb['promotion_path']}")
                    rag_context = "\n".join(parts)
            except Exception as e:
                logger.debug("知识库降级检索失败: %s", e)

            prompt = render_prompt(
                "match_analysis_v1.jinja2",
                job_soft_skills=job_soft_skills,
                job_soft_skill_scores=job_soft_skill_scores,
                vague_annotations=vague_annotations,
                student_soft_skills=student_soft_skills,
                student=student_ctx,
                semantic_matched_skills=skills_result.semantic_matched,
                rag_context=rag_context,
                assessment_results=assessment_ctx,
                prior_basic_score=prior_basic_score,
                prior_skills_score=skills_result.score,
            )
            import time as _time2
            llm_t0 = _time2.monotonic()
            raw = await llm_client.chat(prompt, temperature=0.2)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            data = json.loads(raw.strip())

            # P2：幻觉防控 — 强类型校验 + 范围钳制
            qual_score = max(0.0, min(100.0, float(data.get("qualities_score", 50))))
            qual_detail = str(data.get("qualities_detail", "LLM评估"))
            pot_score   = max(0.0, min(100.0, float(data.get("potential_score", 50))))
            pot_detail  = str(data.get("potential_detail", "LLM评估"))
            competitive_context = str(data.get("competitive_context", ""))
            # 防止模型输出无意义的单字或空字符串
            if len(qual_detail) < 10:
                qual_detail = "软技能评估依据不足，取中立分"
            if len(pot_detail) < 10:
                pot_detail = "发展潜力评估依据不足，取中立分"
            # 分数合理性自检：LLM 给出极端分（<10 或 >95）时需有证据支撑，否则回调到安全区间
            if qual_score < 10 and not soft_skill_evidence:
                qual_score = 30.0
            if qual_score > 95 and not soft_skill_evidence:
                qual_score = 88.0

            # A-1: Critic 步骤 — 第二次 LLM 调用以 temperature=0 校验评分合理性
            # 仅在两分数偏差 > 15 时才触发，避免额外延迟
            qual_score, pot_score, qual_detail, pot_detail = await self._critic_validate(
                qual_score, pot_score, qual_detail, pot_detail,
                student, job
            )

            logger.info("维度三/四 LLM评估完成 [%.2fs]: qualities=%.1f potential=%.1f",
                        _time2.monotonic() - llm_t0, qual_score, pot_score)
            return (
                DimensionScore(score=qual_score, detail=qual_detail, evidence="来源：LLM+Critic基于简历软技能评估"),
                DimensionScore(score=pot_score, detail=pot_detail, evidence="来源：LLM基于竞赛/项目/实习评估"),
                False,  # not degraded
                competitive_context,
            )
        except Exception as e:
            logger.warning("维度三/四 LLM评估失败，启用规则降级: %s", e)
            # ---- 规则降级：根据简历硬指标估算 ----
            internship_months = sum(
                (i.get("duration_months") or 0) for i in student.get("internships", [])
            )
            project_count = len(student.get("projects") or [])
            award_count = len(student.get("awards") or [])
            skill_count = len(student.get("skills") or [])
            soft_count = len(student.get("inferred_soft_skills") or {})

            # 素质分：实习 + 软技能
            qual_base = 40
            qual_base += min(internship_months * 2, 20)  # 最多+20
            qual_base += min(soft_count * 4, 20)          # 最多+20
            qual_base += min(project_count * 3, 12)       # 最多+12
            qual_score = min(qual_base, 95.0)

            # 潜力分：项目 + 竞赛 + 技能广度
            pot_base = 40
            pot_base += min(project_count * 5, 20)   # 最多+20
            pot_base += min(award_count * 5, 15)     # 最多+15
            pot_base += min(skill_count * 1.5, 15)   # 最多+15
            pot_base += min(internship_months, 10)   # 最多+10
            pot_score = min(pot_base, 95.0)

            return (
                DimensionScore(score=qual_score, detail="规则评估（LLM不可用）", evidence="来源：基于实习/项目/软技能数量的规则估算"),
                DimensionScore(score=pot_score, detail="规则评估（LLM不可用）", evidence="来源：基于竞赛/项目/技能广度的规则估算"),
                True,   # degraded
                "",
            )

    async def _critic_validate(
        self,
        qual_score: float,
        pot_score: float,
        qual_detail: str,
        pot_detail: str,
        student: dict,
        job_info: dict,
    ) -> Tuple[float, float, str, str]:
        """
        A-1: Critic 步骤 — 用 temperature=0 的第二次 LLM 调用校验评分合理性。
        两分数偏差 > 15 时才触发（减少不必要延迟）。
        若 Critic 判定不合理，将分数向均值拉回并标记 flagged=True。
        """
        avg_score = (qual_score + pot_score) / 2
        if abs(qual_score - pot_score) < 15:
            return qual_score, pot_score, qual_detail, pot_detail

        critic_prompt = (
            f"你是一位严格的评分审计员。请判断以下评分是否合理，如不合理请给出修正后的分数（不超过±10分调整）。\n\n"
            f"职业素养分：{qual_score:.0f}  — 依据：{qual_detail[:200]}\n"
            f"发展潜力分：{pot_score:.0f}  — 依据：{pot_detail[:200]}\n\n"
            f"学生技能数量：{len(student.get('skills') or [])}  "
            f"实习月数：{sum((i.get('duration_months') or 0) for i in (student.get('internships') or []))}  "
            f"项目数量：{len(student.get('projects') or [])}\n\n"
            "请判断：上述两个分数是否存在明显幻觉（无证据的高分 / 证据充分却给低分）？\n"
            "只输出JSON，不要任何解释：\n"
            "{\"qualities_ok\": true/false, \"qualities_corrected\": 0-100, "
            "\"potential_ok\": true/false, \"potential_corrected\": 0-100}"
        )
        try:
            raw = await llm_client.chat(critic_prompt, temperature=0.0, max_tokens=150)
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            critic = json.loads(raw)
            if not critic.get("qualities_ok", True):
                corrected_q = float(critic.get("qualities_corrected", qual_score))
                corrected_q = max(0.0, min(100.0, corrected_q))
                logger.info("A-1 Critic修正 qualities: %.1f → %.1f", qual_score, corrected_q)
                qual_score = corrected_q
                qual_detail = qual_detail + "（Critic已校验）"
            if not critic.get("potential_ok", True):
                corrected_p = float(critic.get("potential_corrected", pot_score))
                corrected_p = max(0.0, min(100.0, corrected_p))
                logger.info("A-1 Critic修正 potential: %.1f → %.1f", pot_score, corrected_p)
                pot_score = corrected_p
                pot_detail = pot_detail + "（Critic已校验）"
        except Exception as e:
            logger.debug("A-1 Critic解析失败，保留原分数: %s", e)
        return qual_score, pot_score, qual_detail, pot_detail

    async def _score_market_demand(
        self, job_name: str, db_session
    ) -> MarketDemandScore:
        """
        第5维度：市场需求度
        基于真实招聘数据（9958条JD）计算岗位市场热度
        """
        try:
            from app.db.crud.job_real_crud import job_real_crud
            stats = await job_real_crud.get_stats_by_job_name(db_session, job_name)
            jd_count = stats["count"]
            avg_salary_k = stats["avg_salary_k"]
            top_companies = stats["top_companies"]
            
            # 新增：技能需求趋势
            skill_trends = stats.get("skill_trends", {})
            
            # 新增：行业分布
            industry_distribution = stats.get("industry_distribution", {})
            
            # 新增：经验要求分布
            experience_distribution = stats.get("experience_distribution", {})

            # 评分：对数标准化（0条→10分，100条→~66分，500+条→100分）
            if jd_count <= 0:
                score = 10.0
                detail = f"暂无真实招聘数据，市场热度待观察"
            else:
                # 基础评分
                base_score = min(math.log2(jd_count + 1) / math.log2(500) * 90 + 10, 100)
                
                # 薪资加分（如果有薪资数据）
                salary_bonus = 0
                if avg_salary_k > 0:
                    # 薪资高于平均水平的加分
                    if avg_salary_k > 20:
                        salary_bonus = 5
                    elif avg_salary_k > 15:
                        salary_bonus = 3
                    elif avg_salary_k > 10:
                        salary_bonus = 1
                
                # 综合评分
                score = min(base_score + salary_bonus, 100)
                score = round(score, 2)
                
                # 构建详细描述
                details = []
                details.append(f"市场真实招聘 {jd_count} 条")
                if avg_salary_k > 0:
                    details.append(f"均薪约 {avg_salary_k:.1f}k/月")
                if skill_trends:
                    hot_skills = [skill for skill, trend in skill_trends.items() if trend == "上升"]
                    if hot_skills:
                        details.append(f"热门技能：{', '.join(hot_skills[:3])}")
                if industry_distribution:
                    top_industries = sorted(industry_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
                    top_industries_str = ", ".join([f"{industry}({count}%)" for industry, count in top_industries])
                    details.append(f"主要行业：{top_industries_str}")
                
                detail = "，".join(details)

            return MarketDemandScore(
                score=score,
                jd_count=jd_count,
                avg_salary_k=avg_salary_k,
                top_companies=top_companies[:3],
                detail=detail,
            )
        except Exception as e:
            logger.error("市场需求评分失败: %s", e)
            raise

    def _build_confidence_breakdown(
        self,
        student: dict,
        skills_result: "ProfessionalSkillsScore",
        overall_confidence: float,
    ) -> Dict[str, Any]:
        """构建前端置信度分项拆解"""
        total_skills = len(skills_result.matched_skills) + len(skills_result.gap_skills)
        match_precision = (
            len(skills_result.matched_skills) / total_skills if total_skills > 0 else 0.0
        )
        completeness = float(student.get("completeness", 0.5))
        semantic_count = len(skills_result.semantic_matched)
        soft_skills = student.get("inferred_soft_skills") or {}
        evidence_count = sum(
            1 for v in soft_skills.values()
            if isinstance(v, dict) and v.get("evidence")
        )
        evidence_strength = min(
            overall_confidence * 0.6 + evidence_count * 0.05 + match_precision * 0.3,
            1.0,
        )
        return {
            "dataQuality": round(completeness, 2),
            "matchPrecision": round(match_precision, 2),
            "evidenceStrength": round(evidence_strength, 2),
            "factors": {
                "技能覆盖率": f"{len(skills_result.matched_skills)}/{total_skills} 项技能匹配",
                "数据完整度": f"{int(completeness * 100)}%",
                "语义扩展": f"{semantic_count} 项语义匹配",
                "软技能证据": f"{evidence_count} 项有文字证据",
            },
        }

    @staticmethod
    def _build_skill_match_details(
        skills_result: "ProfessionalSkillsScore",
    ) -> List[Dict[str, Any]]:
        """从 raw_match_details + gap_skills 构建前端技能明细列表"""
        details: List[Dict[str, Any]] = []
        seen_job_skills: set = set()

        for d in skills_result.raw_match_details:
            job_skill = d.get("job_skill", "")
            if not job_skill or job_skill in seen_job_skills:
                continue
            seen_job_skills.add(job_skill)
            match_type = d.get("match_type", "exact")
            if match_type == "exact" or match_type == "alias" or match_type == "partial":
                status = "matched" if d.get("match_score", 0) >= 0.85 else "partial"
            elif match_type == "semantic":
                status = "semantic_matched"
            else:
                status = "partial"
            details.append({
                "skillName": job_skill,
                "matchStatus": status,
                "importance": skills_result.skill_importance_map.get(job_skill, "nice_to_have"),
                "studentEvidence": d.get("student_skill", ""),
                "similarityScore": round(d.get("match_score", 0), 2),
                "jobRequirement": job_skill,
            })

        for gap in skills_result.gap_skills:
            if gap.skill in seen_job_skills:
                continue
            seen_job_skills.add(gap.skill)
            details.append({
                "skillName": gap.skill,
                "matchStatus": "missing",
                "importance": gap.importance,
                "studentEvidence": None,
                "similarityScore": 0.0,
                "jobRequirement": gap.skill,
            })

        return details

    @staticmethod
    def _build_gap_analysis(gap_skills: List["GapItem"]) -> List[Dict[str, Any]]:
        """从 gap_skills 构建结构化差距分析（含改进建议）"""
        _level_severity = {
            "未掌握": "critical",
            "了解": "moderate",
            "掌握": "minor",
            "熟练": "minor",
            "精通": "minor",
        }
        _level_desc = {
            "未掌握": "完全未涉及",
            "了解": "有基础了解但不足以胜任",
            "掌握": "基本掌握但与岗位要求有差距",
        }
        result = []
        for gap in gap_skills:
            is_must = gap.importance == "must_have"
            level = gap.student_level or "未掌握"
            severity = "critical" if (is_must and level in ("未掌握", "了解")) else (
                "moderate" if is_must else _level_severity.get(level, "moderate")
            )
            level_desc = _level_desc.get(level, f"当前水平：{level}")
            impact = (
                f"该技能为岗位{'必须' if is_must else '加分'}项，{level_desc}，"
                + ("将影响核心业务能力。" if is_must else "会降低候选竞争力。")
            )
            priority = "high" if severity == "critical" else ("medium" if severity == "moderate" else "low")
            result.append({
                "severity": severity,
                "gapDescription": f"{gap.skill}（{'必须掌握' if is_must else '建议掌握'}）：{level_desc}",
                "impact": impact,
                "improvementSuggestions": [
                    {
                        "priority": priority,
                        "suggestion": gap.suggestion,
                        "timeline": "1-2个月" if severity == "critical" else "2-3个月",
                        "resources": [],
                    }
                ],
            })
        # critical 优先排序
        result.sort(key=lambda x: {"critical": 0, "moderate": 1, "minor": 2}[x["severity"]])
        return result

    @staticmethod
    def _quantify_soft_skill_text(text: str) -> dict:
        """
        将模糊文字描述转换为 0-100 分值，供 LLM prompt 提供量化基准。
        规则：关键词匹配 → 分值区间，避免 LLM 对空文字盲目打分。
        返回: {"score": int, "is_vague": bool, "vague_word": str}
        """
        if not text:
            return {"score": 0, "is_vague": False, "vague_word": ""}
        t = text
        high_kw   = ["优秀", "出色", "卓越", "强烈", "丰富", "深厚", "高水平", "专业级", "领导"]
        medium_kw = ["良好", "较强", "具备", "熟悉", "有一定", "积极", "主动", "乐于"]
        low_kw    = ["基本", "初步", "了解", "一般", "无严格要求", "不限", "无硬性"]
        vague_kw  = ["良好", "较强", "优秀", "一定"]  # 模糊描述词
        vague_word = next((k for k in vague_kw if k in t), "")
        is_vague = bool(vague_word)
        if any(k in t for k in high_kw):
            score = 85
        elif any(k in t for k in medium_kw):
            score = 70
        elif any(k in t for k in low_kw):
            score = 50
        else:
            score = 60  # 有描述但无明确程度词 → 中立分
        return {"score": score, "is_vague": is_vague, "vague_word": vague_word}

    def _compute_overall(self, dim_scores: dict, weights: dict) -> float:
        """计算综合得分"""
        return round(sum(dim_scores[d] * weights[d] for d in weights), 2)

    def _compute_confidence(
        self, completeness: float, soft_skills_null_count: int, dim_scores: dict
    ) -> dict:
        """计算置信度
        规则：
        1. 基于画像完整度
        2. 软技能空值每项扣0.05
        3. 完整度低于50%时上限0.6
        4. 为不同维度提供独立置信度
        5. 考虑技能匹配率对置信度的影响
        6. 考虑数据质量对置信度的影响
        """
        # 基础置信度计算
        base = completeness
        penalty = soft_skills_null_count * 0.05
        overall_confidence = base - penalty
        
        # 技能匹配率对置信度的影响
        skills_score = dim_scores.get('skills', 0)
        skills_match_rate = skills_score / 100.0
        overall_confidence = overall_confidence * 0.7 + skills_match_rate * 0.3
        
        if completeness < 0.5:
            overall_confidence = min(overall_confidence, 0.3 + completeness * 0.6)
        
        # 确保置信度在合理范围内
        overall_confidence = max(0.2, min(overall_confidence, 1.0))
        
        # 为不同维度计算置信度
        dimension_confidence = {}
        
        # 基础要求维度置信度
        basic_score = dim_scores.get('basic', 0)
        if basic_score >= 80:
            dimension_confidence['basic'] = min(overall_confidence + 0.1, 1.0)
        elif basic_score < 60:
            dimension_confidence['basic'] = max(overall_confidence - 0.1, 0.1)
        else:
            dimension_confidence['basic'] = overall_confidence
        
        # 职业技能维度置信度
        if skills_score >= 80:
            dimension_confidence['skills'] = min(overall_confidence + 0.15, 1.0)
        elif skills_score < 60:
            dimension_confidence['skills'] = max(overall_confidence - 0.1, 0.1)
        else:
            dimension_confidence['skills'] = overall_confidence
        
        # 职业素养维度置信度
        qualities_score = dim_scores.get('qualities', 0)
        if qualities_score >= 80:
            dimension_confidence['qualities'] = min(overall_confidence + 0.1, 1.0)
        elif qualities_score < 60:
            dimension_confidence['qualities'] = max(overall_confidence - 0.1, 0.1)
        else:
            dimension_confidence['qualities'] = overall_confidence
        
        # 发展潜力维度置信度
        potential_score = dim_scores.get('potential', 0)
        if potential_score >= 80:
            dimension_confidence['potential'] = min(overall_confidence + 0.1, 1.0)
        elif potential_score < 60:
            dimension_confidence['potential'] = max(overall_confidence - 0.1, 0.1)
        else:
            dimension_confidence['potential'] = overall_confidence
        
        return {
            'overall': round(overall_confidence, 3),
            'dimensions': {k: round(v, 3) for k, v in dimension_confidence.items()}
        }

    def _generate_summary(
        self, overall: float, dimensions: MatchDimensions, job_name: str
    ) -> str:
        """生成匹配总结（结构化、可量化、具体指向短板）"""
        if overall >= 80:
            level, advice = "高度匹配", "可直接投递，重点准备项目深挖和技术细节问答。"
        elif overall >= 65:
            level, advice = "较好匹配", "基础条件满足，建议补齐关键技能缺口后投递以提高通过率。"
        elif overall >= 50:
            level, advice = "基本匹配", "与岗位要求有一定差距，建议先针对必须技能进行系统补强。"
        else:
            level, advice = "差距较大", "当前阶段与岗位要求差距明显，建议以关联度更高的初级岗位作为过渡。"

        gaps = dimensions.professional_skills.gap_skills
        must_gaps = [g.skill for g in gaps if g.importance == "must_have"][:3]
        nice_gaps = [g.skill for g in gaps if g.importance == "nice_to_have"][:2]

        matched_count = len(dimensions.professional_skills.matched_skills)
        total_skills = matched_count + len(gaps)

        parts = [f"与「{job_name}」岗位{level}（综合得分 {overall:.0f}/100）。"]
        parts.append(f"技能匹配 {matched_count}/{total_skills} 项（覆盖率 {dimensions.professional_skills.score:.0f}%）。")

        if must_gaps:
            parts.append(f"必须补齐：{'、'.join(must_gaps)}。")
        if nice_gaps:
            parts.append(f"加分项：{'、'.join(nice_gaps)}。")

        parts.append(advice)
        return "".join(parts)


match_service = MatchService()
