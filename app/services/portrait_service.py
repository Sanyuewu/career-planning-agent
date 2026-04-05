# -*- coding: utf-8 -*-
"""
学生画像服务
遵循v4规范：7维度画像 + 完整度/竞争力评分
"""

import math
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import logging

from app.services.resume_service import ResumeParseResult
from app.constants import DEGREE_COMPETITIVENESS_MAP, ELITE_SCHOOL_KEYWORDS
from app.graph.job_graph_repo import job_graph
from app.services.job_graph_enhanced import enhanced_job_graph

logger = logging.getLogger(__name__)


class StudentPortrait(BaseModel):
    """学生画像"""
    student_id: Optional[str] = None
    basic_info: Dict = Field(default_factory=dict)
    education: List[Dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    internships: List[Dict] = Field(default_factory=list)
    projects: List[Dict] = Field(default_factory=list)
    certs: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    career_intent: Optional[str] = None
    inferred_soft_skills: Dict = Field(default_factory=dict)
    completeness: float = 0.0
    competitiveness: float = 0.0
    competitiveness_level: str = "C"
    highlights: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    transfer_opportunities: List[Dict] = Field(default_factory=list)
    gap_mapped_transfers: List[Dict] = Field(default_factory=list)
    # 多维画像扩展
    interests: List[str] = Field(default_factory=list)
    ability_profile: Dict = Field(default_factory=dict)
    personality_traits: List[str] = Field(default_factory=list)
    # 字段级置信度（由 accuracy_service 计算，0-1 值）
    # 供前端在低置信度字段旁显示「建议复核」提示
    field_confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="各字段提取置信度：{name, school, skills, internship_duration, ...}",
    )


class PortraitService:
    """学生画像服务"""
    
    def build_portrait(self, parse_result: ResumeParseResult) -> StudentPortrait:
        """从解析结果构建学生画像 + 换岗机会"""
        portrait = StudentPortrait(
            basic_info=parse_result.basic_info,
            education=parse_result.education,
            skills=parse_result.skills,
            internships=parse_result.internships,
            projects=parse_result.projects,
            certs=parse_result.certs,
            awards=parse_result.awards,
            career_intent=parse_result.career_intent,
            inferred_soft_skills=parse_result.inferred_soft_skills,
            completeness=parse_result.completeness,
        )
        
        if parse_result.career_intent:
            self._last_career_intent = parse_result.career_intent
        
        # 计算核心画像属性
        portrait.competitiveness = self._calculate_competitiveness(portrait)
        portrait.competitiveness_level = self._get_competitiveness_level(portrait.competitiveness)
        portrait.highlights = self._extract_highlights(portrait)
        portrait.weaknesses = self._extract_weaknesses(portrait)
        portrait.interests = self._infer_interests(portrait)
        portrait.ability_profile = self._build_ability_profile(portrait)
        portrait.personality_traits = self._infer_personality(portrait)
        
        # 新增：如果有职业意向，自动获取换岗机会
        if portrait.career_intent:
            try:
                transfers_data = job_graph.get_main_with_transfers(portrait.career_intent)
                portrait.transfer_opportunities = transfers_data.get("transfers", [])
                # 将需补技能与简历gap关联
                portrait.gap_mapped_transfers = self._map_gaps_to_transfers(
                    parse_result.skills, 
                    portrait.weaknesses, 
                    transfers_data.get("transfers", [])
                )
            except Exception as e:
                logger.warning(f"换岗路径查询失败（不影响主流程）: {e}")
                portrait.transfer_opportunities = []
                portrait.gap_mapped_transfers = []
        else:
            portrait.transfer_opportunities = []
            portrait.gap_mapped_transfers = []

        # 字段级置信度（嵌入画像，供前端显示「建议复核」）
        try:
            from app.services.accuracy_service import accuracy_service
            portrait.field_confidence = accuracy_service.compute_portrait_field_confidence(
                portrait.model_dump()
            )
        except Exception:
            pass  # 置信度不影响主流程

        return portrait
    
    def _calculate_competitiveness(self, portrait: StudentPortrait) -> float:
        """计算竞争力评分（0-100），6维度归一化加权"""
        edu = portrait.education[0] if portrait.education else {}
        degree = edu.get("degree", "本科")
        school = edu.get("school") or ""

        # 1. 学历背景（22%）
        degree_base = DEGREE_COMPETITIVENESS_MAP.get(degree, 70)
        school_bonus = 20 if any(kw in school for kw in ELITE_SCHOOL_KEYWORDS) else (8 if "大学" in school or "学院" in school else 0)
        # GPA 加成：GPA ≥ 3.5/4.0（或 ≥ 85/100）给予额外 5 分
        gpa = edu.get("gpa")
        gpa_bonus = 0
        if gpa:
            try:
                gpa_val = float(str(gpa).replace('/', ' ').split()[0])
                if gpa_val >= 3.5:    # 4.0 制
                    gpa_bonus = 5
                elif gpa_val >= 85:   # 百分制
                    gpa_bonus = 5
                elif gpa_val >= 3.0 or gpa_val >= 80:
                    gpa_bonus = 2
            except (ValueError, IndexError):
                pass
        edu_score = min(degree_base + school_bonus + gpa_bonus, 100)

        # 2. 专业技能深度（28%）
        skill_count = len(portrait.skills)
        # 技能数量对数增长，15个技能满分；技能有熟练度标注额外加成
        skill_score = min(math.log(skill_count + 1, 2) / math.log(16, 2) * 100, 100) if skill_count > 0 else 0

        # 3. 实践经验（25%）
        intern_months = sum((i.get("duration_months") or 1) for i in portrait.internships)
        intern_score = min(intern_months / 12 * 70 + (20 if portrait.internships else 0), 100)
        project_count = len(portrait.projects)
        project_score = min(project_count / 4 * 100, 100)
        experience_score = intern_score * 0.6 + project_score * 0.4

        # 4. 综合素质（15%）
        award_count = len(portrait.awards)
        cert_count = len(portrait.certs)
        quality_score = min(award_count * 15 + cert_count * 10, 100)

        # 5. 软技能（5%）
        soft_skills = portrait.inferred_soft_skills or {}
        soft_vals = [v.get("score", 1) for v in soft_skills.values() if v and v.get("score") is not None]
        soft_score = (sum(soft_vals) / len(soft_vals) * 10) if soft_vals else 50
        soft_score = max(0.0, min(100.0, soft_score))

        # 6. 技能质量加成（5%）：技能数 ≥ 8 且有熟练度标注时提升评分
        skill_quality = min(skill_count / 8 * 100, 100) if skill_count > 0 else 0

        total = (edu_score * 0.22 + skill_score * 0.28 + experience_score * 0.25
                 + quality_score * 0.15 + soft_score * 0.05 + skill_quality * 0.05)
        return round(min(total, 100), 2)
    
    def _get_competitiveness_level(self, score: float) -> str:
        """获取竞争力等级"""
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        else:
            return "D"
    
    def _extract_highlights(self, portrait: StudentPortrait) -> List[str]:
        """提取核心亮点"""
        highlights = []
        
        if portrait.skills and len(portrait.skills) >= 3:
            highlights.append(f"掌握{len(portrait.skills)}项专业技能：{','.join(portrait.skills[:5])}")
        
        if portrait.internships:
            companies = [i.get("company", "") for i in portrait.internships if i.get("company")]
            if companies:
                highlights.append(f"有{len(portrait.internships)}段实习经历：{','.join(companies[:3])}")
        
        if portrait.awards:
            highlights.append(f"获得{len(portrait.awards)}项奖项：{','.join(portrait.awards[:3])}")
        
        if portrait.projects and len(portrait.projects) >= 2:
            highlights.append(f"参与{len(portrait.projects)}个项目实践")
        
        soft_skills = portrait.inferred_soft_skills or {}
        strong_soft = [k for k, v in soft_skills.items() if v and (v.get("score") or 0) >= 7]
        if strong_soft:
            cn_names = {
                "communication": "沟通能力",
                "stress_resistance": "抗压能力",
                "learning_ability": "学习能力",
                "innovation": "创新能力",
                "teamwork": "团队协作",
            }
            highlights.append(f"软技能突出：{','.join([cn_names.get(k, k) for k in strong_soft[:3]])}")
        
        return highlights[:5]
    
    def _extract_weaknesses(self, portrait: StudentPortrait) -> List[str]:
        """提取明显短板"""
        weaknesses = []
        
        if not portrait.internships:
            weaknesses.append("缺乏实习经历")
        
        if not portrait.projects:
            weaknesses.append("缺乏项目经验")
        
        if len(portrait.skills) < 3:
            weaknesses.append("技能储备不足")
        
        soft_skills = portrait.inferred_soft_skills or {}
        weak_soft = [k for k, v in soft_skills.items() if not v or (v.get("score") or 0) < 5]
        if len(weak_soft) >= 3:
            weaknesses.append("软技能评估信息不足")
        
        if not portrait.certs:
            weaknesses.append("无专业证书")
        
        return weaknesses[:3]

    # ── 多维画像推断 ──────────────────────────────────────────────────────────

    _INTEREST_MAP: Dict[str, List[str]] = {
        "编程/技术开发": ["Python", "Java", "C++", "Go", "Rust", "算法", "数据结构", "后端", "开发"],
        "数据分析": ["数据分析", "SQL", "Excel", "SPSS", "R语言", "数据挖掘", "Tableau", "BI"],
        "人工智能/机器学习": ["机器学习", "深度学习", "TensorFlow", "PyTorch", "AI", "NLP", "CV"],
        "前端/UI设计": ["HTML", "CSS", "Vue", "React", "前端", "UI", "Figma", "设计", "Angular"],
        "运营/市场营销": ["运营", "市场", "营销", "SEO", "用户增长", "品牌", "内容创作"],
        "法律/知识产权": ["法律", "合同", "专利", "知识产权", "法务", "诉讼"],
        "金融/财务": ["金融", "会计", "财务", "投资", "股票", "风控", "审计", "CPA"],
        "项目/产品管理": ["项目管理", "PMP", "Scrum", "产品", "需求分析", "原型"],
    }

    def _infer_interests(self, portrait: StudentPortrait) -> List[str]:
        """从技能/项目/实习文本推断兴趣领域标签（最多5个）"""
        all_text = " ".join(portrait.skills)
        for p in portrait.projects:
            all_text += " " + p.get("name", "") + " " + " ".join(p.get("tech_stack", []))
            all_text += " " + (p.get("description") or "")
        for i in portrait.internships:
            all_text += " " + i.get("role", "") + " " + (i.get("description") or "")
        all_text = all_text.lower()
        return [
            label for label, kws in self._INTEREST_MAP.items()
            if any(kw.lower() in all_text for kw in kws)
        ][:5]

    def _build_ability_profile(self, portrait: StudentPortrait) -> Dict:
        """构建7维能力雷达图数据（0-100）"""
        soft = portrait.inferred_soft_skills or {}

        def _soft(key: str) -> float:
            item = soft.get(key) or {}
            s = item.get("score")
            return min(float(s) * 10, 100) if s is not None else 50.0

        # 只统计 IT/技术类技能，排除非技术软技能，避免销售/管理类学生虚高技术分
        _NON_TECH_KEYWORDS = {
            '市场', '销售', '客户', '商务', '谈判', '沟通', '团队', '管理', '办公',
            '运营', '策划', '品牌', '推广', '活动', '招聘', '培训', '绩效', '薪酬',
            '财务', '会计', '审计', '税务', '法律', '合规', '风控', '采购', '物流',
            '行政', '文案', '新媒体', '内容', '公关', '投标', '标书', '报价',
        }
        tech_skills = [
            s for s in (portrait.skills or [])
            if not any(kw in s for kw in _NON_TECH_KEYWORDS)
        ]
        skill_cnt = len(tech_skills)
        tech_score = round(min(math.log(skill_cnt + 1, 2) / math.log(16, 2) * 100, 100), 1)

        intern_months = sum((i.get("duration_months") or 1) for i in portrait.internships)
        exec_score = round(min(intern_months / 6 * 50 + len(portrait.projects) * 10, 100), 1)

        return {
            "技术能力": tech_score,
            "沟通能力": _soft("communication"),
            "学习能力": _soft("learning_ability"),
            "创新能力": _soft("innovation"),
            "团队协作": _soft("teamwork"),
            "执行力":   exec_score,
            "抗压能力": _soft("stress_resistance"),
        }

    def _infer_personality(self, portrait: StudentPortrait) -> List[str]:
        """从简历特征推断性格标签（最多5个）"""
        traits: List[str] = []
        soft = portrait.inferred_soft_skills or {}

        if len(portrait.skills) >= 6:
            traits.append("逻辑严密")
        if len(portrait.projects) >= 3:
            traits.append("执行力强")
        if len(portrait.internships) >= 2:
            traits.append("适应性强")
        if portrait.awards:
            traits.append("上进心强")

        comm = (soft.get("communication") or {}).get("score") or 0
        if comm >= 7:
            traits.append("善于沟通")

        innov = (soft.get("innovation") or {}).get("score") or 0
        innovation_kw = ["设计", "创新", "research", "研究", "AI", "算法", "产品"]
        skill_text = " ".join(portrait.skills).lower()
        if innov >= 6 or any(k in skill_text for k in innovation_kw):
            traits.append("创新型")

        if not traits:
            traits.append("踏实勤恳")

        return traits[:5]

    def _map_gaps_to_transfers(self, skills: List[str], weaknesses: List[str], transfers: List[Dict]) -> List[Dict]:
        """将简历gap/skills映射到换岗路径的need_learn"""
        skill_set = set(skills)
        gaps = weaknesses + [s for s in skill_set if "无" in s.lower() or len(s) < 3]
        
        enhanced_suggestions = enhanced_job_graph.suggest_transfer_paths(
            current_job=self._extract_main_job_intent(),
            current_skills=list(skill_set),
            limit=5,
        )
        
        mapped = []
        for i, tf in enumerate(transfers):
            need_learn = tf.get("need_learn", "").split("、")
            matched_gaps = [g for g in need_learn if any(gap.lower() in g.lower() for gap in gaps)]
            
            enhanced_score = 0
            for suggestion in enhanced_suggestions:
                if suggestion.target_job in tf.get("target", ""):
                    enhanced_score = suggestion.match_score
                    break
            
            base_priority = len(matched_gaps) * 10 + (100 if tf.get("match_level") == "高" else 50)
            priority = base_priority - enhanced_score * 0.5
            
            # 从匹配度推断转岗难度和预计周期
            _difficulty_map = {"高": "easy", "中": "medium", "低": "hard"}
            _months_map = {"高": 3, "中": 6, "低": 12}
            match_level_str = tf.get("match_level", "中")

            mapped.append({
                **tf,
                "personalized_gaps": matched_gaps,
                "is_good_fit": len(matched_gaps) <= 2,
                "priority": priority,
                "enhanced_match_score": enhanced_score,
                "difficulty": tf.get("difficulty") or _difficulty_map.get(match_level_str, "medium"),
                "months_estimate": tf.get("months_estimate") or _months_map.get(match_level_str, 6),
            })
        
        return sorted(mapped, key=lambda x: x["priority"], reverse=True)[:3]
    
    def _extract_main_job_intent(self) -> str:
        """从最近的画像构建中提取主要求职意向"""
        return getattr(self, '_last_career_intent', '后端开发工程师')


portrait_service = PortraitService()


async def get_portrait(student_id: str):
    """获取学生画像（供推荐API使用）"""
    from app.db.database import get_db_session
    from sqlalchemy import select as _sa_select
    from app.db.models import StudentModel
    
    async with get_db_session() as session:
        result = await session.execute(
            _sa_select(StudentModel)
            .where(StudentModel.student_id == student_id)
            .order_by(StudentModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        
        return StudentPortrait(
            basic_info=model.basic_info or {},
            education=model.education or [],
            skills=model.skills or [],
            internships=model.internships or [],
            projects=model.projects or [],
            certs=model.certs or [],
            awards=model.awards or [],
            career_intent=model.career_intent,
            inferred_soft_skills=model.inferred_soft_skills or {},
            completeness=model.completeness or 0.5,
            competitiveness=model.competitiveness or 50.0,
        )
