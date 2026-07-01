# -*- coding: utf-8 -*-
"""
职业规划GraphRAG服务 - 符合赛题要求的统一服务
包含：岗位画像、职业路径、学生画像、人岗匹配、职业报告
集成 YOUTU-GraphRAG 检索增强
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.llm_service import llm_service
from app.services.youtu_retriever_service import youtu_retriever_service
from app.services.student_graph_service import student_graph_service
from app.services import match_rules


class JobPortrait(BaseModel):
    """岗位画像 - 七维度"""
    title: str
    skills: List[str] = []
    certificates: List[str] = []
    innovation: str = "一般"
    learning: str = "一般"
    stress_resistance: str = "一般"
    communication: str = "一般"
    internship: str = "一般"
    salary_range: str = ""
    salary_avg_k: float = 0.0
    job_count: int = 0
    entry_friendly: bool = False
    job_description: str = ""
    location: str = ""
    industry: str = ""


class StudentPortrait(BaseModel):
    """学生画像 - 七维度"""
    student_id: str = ""
    name: str = ""
    skills: List[str] = []
    certificates: List[str] = []
    innovation: str = "一般"
    learning: str = "一般"
    stress_resistance: str = "一般"
    communication: str = "一般"
    internship: str = "一般"
    education: List[Dict] = []
    projects: List[Dict] = []
    internships: List[Dict] = []
    career_intent: str = ""
    interests: List[str] = []          # 兴趣（意愿轴用，不参与 4 维匹配打分）
    job_preferences: Dict = {}         # 结构化就业意愿：期望行业/城市/薪资/工作方式/价值取向
    completeness_score: float = 0.0
    competitiveness_score: float = 0.0

    @classmethod
    def from_node(cls, node: Optional[Dict], student_id: str = "") -> "StudentPortrait":
        """从 student_graph_service 节点（或其 attributes）重建画像 —— node→StudentPortrait 单一工厂。
        消除此前 tools/_common 三处手工重建的重复；node 为空时返回空画像。"""
        if not node:
            return cls(student_id=student_id)
        attrs = node.get("attributes", node)
        return cls(
            student_id=student_id or attrs.get("student_id", ""),
            name=attrs.get("name", ""),
            skills=attrs.get("skills", []),
            certificates=attrs.get("certificates", []),
            innovation=attrs.get("innovation", "一般"),
            learning=attrs.get("learning", "一般"),
            stress_resistance=attrs.get("stress_resistance", "一般"),
            communication=attrs.get("communication", "一般"),
            internship=attrs.get("internship", "一般"),
            education=attrs.get("education", []),
            projects=attrs.get("projects", []),
            internships=attrs.get("internships", []),
            career_intent=attrs.get("career_intent", ""),
            interests=attrs.get("interests", []),
            job_preferences=attrs.get("job_preferences", {}),
            completeness_score=float(attrs.get("completeness_score", 0) or 0),
            competitiveness_score=float(attrs.get("competitiveness_score", 0) or 0),
        )


class CareerPath(BaseModel):
    """职业路径"""
    target_job: str
    path_type: str
    confidence: float
    description: str = ""
    shared_skills: List[str] = []


class CareerPaths(BaseModel):
    """职业路径集合"""
    vertical_paths: List[CareerPath] = []
    horizontal_paths: List[CareerPath] = []


class MatchResult(BaseModel):
    """人岗匹配结果 - 四维度"""
    basic_match: float = 0.0
    skill_match: float = 0.0
    quality_match: float = 0.0
    potential_match: float = 0.0
    total_match: float = 0.0
    eligible: bool = True          # 基础要求一票否决：False=不达标
    veto_reason: str = ""          # 否决原因（eligible=False 时给出）
    details: Dict[str, Any] = {}


class CareerReport(BaseModel):
    """职业报告"""
    student: StudentPortrait
    job: JobPortrait
    match_result: MatchResult
    content: str = ""
    generated_at: str = ""
    phased_plan: Optional["PhasedPlan"] = None


class ActionItem(BaseModel):
    """行动计划项"""
    title: str
    description: str
    timeline: str
    resources: List[str] = []
    milestones: List[str] = []
    status: str = "pending"


class PhasedPlan(BaseModel):
    """分阶段职业发展计划"""
    short_term: List[ActionItem] = []
    mid_term: List[ActionItem] = []
    long_term: List[ActionItem] = []
    generated_at: str = ""


class CareerGraphRAGService:
    """基于GraphRAG的职业规划服务

    图谱数据层完全委托给 youtu_retriever_service，本服务只负责：
    业务逻辑（匹配计算、画像生成、报告生成）。
    """

    def __init__(self):
        pass  # 图谱已由 youtu_retriever_service 单例加载，无需重复

    # ── 图谱数据代理属性（只读快捷入口）────────────────────────
    @property
    def _jobs_index(self) -> Dict:
        return youtu_retriever_service.jobs_index

    @property
    def _skills_index(self) -> Dict:
        return youtu_retriever_service.skills_index

    @property
    def _career_paths(self) -> Dict:
        return youtu_retriever_service.career_paths

    # ────────────────────────────────────────────────────────────
    def get_all_jobs(self) -> List[Dict]:
        """获取所有岗位列表（来源：YOUTU jobs_index）。
        M2.3：按当前租户岗位库白名单过滤（无配置=全部，可降级）。"""
        jobs = []
        for name, node in self._jobs_index.items():
            attrs = node.get("attributes", {})
            jobs.append({
                "title": name,
                "salary_range": attrs.get("salary_range", ""),
                "job_count": attrs.get("market_demand", 0),
            })
        # 治理补全的缺失岗位（图谱无节点，如后端开发）也纳入可浏览列表
        for name in self._JOB_SKILL_SUPPLEMENT:
            if name not in self._jobs_index:
                jobs.append({"title": name, "salary_range": "", "job_count": 0})
        jobs = sorted(jobs, key=lambda x: x.get("title", ""))
        from app.services import tenant_config_service
        allow = set(tenant_config_service.filter_jobs([j["title"] for j in jobs]))
        return [j for j in jobs if j["title"] in allow]

    def generate_job_portrait(self, job_name: str) -> JobPortrait:
        """生成岗位画像（七维度）- 数据来源：YOUTU jobs_index"""
        # 精确匹配
        node = self._jobs_index.get(job_name)
        # 子串兜底
        if not node:
            jn_lower = job_name.lower()
            best: tuple = (0.0, None)
            for name, n in self._jobs_index.items():
                nl = name.lower()
                if jn_lower in nl:
                    score = len(jn_lower) / len(nl)
                    if score > best[0]:
                        best = (score, n)
                elif nl in jn_lower:
                    score = len(nl) / len(jn_lower)
                    if score > best[0]:
                        best = (score, n)
            node = best[1]

        # 治理：补全缺失岗位（如「后端开发」图谱无此节点）+ 技术岗去非技术噪声
        raw_skills = list((node or {}).get("attributes", {}).get("skills", []))
        governed = self._govern_job_skills(job_name, raw_skills)

        if not node:
            # 图谱缺失但有治理补全（后端开发）→ 用补全技能建最小画像（匹配只需技能）
            if governed:
                return JobPortrait(title=job_name, skills=self._clean_skills(governed))
            return JobPortrait(title=job_name)

        attrs = node.get("attributes", {})
        sal_avg = float(attrs.get("salary_avg_k", 0.0))
        salary_range = attrs.get("salary_range", "") or (f"均值{sal_avg:.1f}k" if sal_avg else "")
        top_regions = attrs.get("top_regions", [])
        top_industries = attrs.get("top_industries", [])

        return JobPortrait(
            title=attrs.get("name", job_name),
            skills=self._clean_skills(governed),
            certificates=attrs.get("certificates", []),
            innovation=attrs.get("innovation", "一般"),
            learning=attrs.get("learning", "一般"),
            stress_resistance=attrs.get("stress_resistance", "一般"),
            communication=attrs.get("communication", "一般"),
            internship=attrs.get("internship", "一般"),
            salary_range=salary_range,
            salary_avg_k=sal_avg,
            job_count=int(attrs.get("market_demand", 0)),
            entry_friendly=bool(attrs.get("entry_friendly", False)),
            job_description=attrs.get("job_description", ""),
            location=", ".join(top_regions[:3]) if top_regions else "",
            industry=", ".join(top_industries[:3]) if top_industries else "",
        )

    def get_career_paths(self, job_name: str) -> CareerPaths:
        """获取职业路径（垂直晋升 + 换岗路径）- 数据来源：YOUTU career_paths"""
        vertical_paths: List[CareerPath] = []
        horizontal_paths: List[CareerPath] = []

        paths = self._career_paths.get(job_name, {})

        for p in paths.get("PROMOTES_TO", []):
            target = p.get("target", "")
            sal_inc = p.get("salary_increase", "")
            overlap = p.get("skill_overlap", 0.0)
            sal_txt = f"涨薪{sal_inc}，" if sal_inc else ""
            ovl_txt = f"技能重叠{int(overlap * 100)}%" if overlap else ""
            sep = "，" if sal_txt and ovl_txt else ""
            desc = p.get("description") or f"从{job_name}晋升到{target}（{sal_txt}{sep}{ovl_txt}）"
            vertical_paths.append(CareerPath(
                target_job=target, path_type="晋升",
                confidence=p.get("confidence", 0.5),
                description=desc,
                shared_skills=p.get("shared_skills", []),
            ))

        for p in paths.get("TRANSFERS_TO", []):
            target = p.get("target", "")
            shared = p.get("shared_skills", [])
            skills_txt = f"，共同技能：{'/'.join(shared[:3])}" if shared else ""
            desc = p.get("description") or f"从{job_name}转岗到{target}{skills_txt}"
            horizontal_paths.append(CareerPath(
                target_job=target, path_type="换岗",
                confidence=p.get("confidence", 0.5),
                description=desc,
                shared_skills=shared,
            ))

        # 转岗路径不足时，用 YOUTU Jaccard 相似度补充
        if len(horizontal_paths) < 2:
            exclude = {p.target_job for p in horizontal_paths}
            additional = self._find_similar_job_paths(job_name, exclude=exclude)
            horizontal_paths.extend(additional)

        return CareerPaths(
            vertical_paths=vertical_paths[:4],
            horizontal_paths=horizontal_paths[:5],
        )

    def _find_similar_job_paths(self, job_name: str, exclude: set = None) -> List[CareerPath]:
        """转岗兜底：用 YOUTU find_similar_jobs() 的 Jaccard 结果生成路径（消除重复计算）"""
        exclude = exclude or set()
        similar = youtu_retriever_service.find_similar_jobs(job_name, top_k=10)
        paths = []
        for item in similar:
            tgt = item.get("title", "")
            if not tgt or tgt in exclude:
                continue
            shared = item.get("shared_skills", [])
            jaccard = item.get("similarity", 0.0)
            skills_txt = f"，共同技能：{'/'.join(shared[:3])}" if shared else ""
            paths.append(CareerPath(
                target_job=tgt, path_type="换岗",
                confidence=round(jaccard, 2),
                description=f"从{job_name}转岗到{tgt}{skills_txt}（基于技能重叠度推断）",
                shared_skills=shared[:5],
            ))
            if len(paths) >= 3:
                break
        return paths

    async def generate_student_portrait(
        self,
        resume_text: str = None,
        student_data: dict = None
    ) -> StudentPortrait:
        """
        生成学生画像（七维度）

        Args:
            resume_text: 简历文本
            student_data: 学生数据

        Returns:
            StudentPortrait: 学生画像
        """
        if resume_text:
            parsed_data = await llm_service.parse_resume(resume_text)
        elif student_data:
            parsed_data = student_data
        else:
            return StudentPortrait()

        dimensions = self._extract_seven_dimensions(parsed_data)

        completeness = self._calculate_completeness(parsed_data, dimensions)
        competitiveness = self._calculate_competitiveness(parsed_data, dimensions)

        skills = dimensions.get("skills", [])
        if skills and isinstance(skills[0], dict):
            skills = [s.get("name", s) if isinstance(s, dict) else s for s in skills]

        # 用 YOUTU skills_index 对技能名称做标准化（模糊匹配图谱标准名）
        skills = self._normalize_skills(skills)

        return StudentPortrait(
            student_id=parsed_data.get("student_id", ""),
            name=parsed_data.get("name", ""),
            skills=skills,
            certificates=dimensions.get("certificates", []),
            innovation=dimensions.get("innovation", "一般"),
            learning=dimensions.get("learning", "一般"),
            stress_resistance=dimensions.get("stress_resistance", "一般"),
            communication=dimensions.get("communication", "一般"),
            internship=dimensions.get("internship", "一般"),
            education=parsed_data.get("education", []),
            projects=parsed_data.get("projects", []),
            internships=parsed_data.get("internships", []),
            career_intent=parsed_data.get("career_intent", ""),
            interests=parsed_data.get("interests", []),
            job_preferences=parsed_data.get("job_preferences", {}),
            completeness_score=completeness,
            competitiveness_score=competitiveness
        )

    def _extract_seven_dimensions(self, data: Dict) -> Dict[str, Any]:
        """从数据中提取七维度能力 - 支持新的LLM返回格式"""
        skills = data.get("skills", [])
        if skills and isinstance(skills[0], dict):
            skills = [s.get("name", s) if isinstance(s, dict) else s for s in skills]

        certificates = data.get("certificates", data.get("certs", []))

        dimensions = {
            "skills": skills,
            "certificates": certificates,
            "innovation": "一般",
            "learning": "一般",
            "stress_resistance": "一般",
            "communication": "一般",
            "internship": "一般",
            "innovation_evidence": "",
            "learning_evidence": "",
            "stress_resistance_evidence": "",
            "communication_evidence": "",
            "internship_evidence": ""
        }

        if isinstance(data.get("innovation"), dict):
            dimensions["innovation"] = data["innovation"].get("level", "一般")
            dimensions["innovation_evidence"] = data["innovation"].get("evidence", "")
        elif data.get("innovation_evidence"):
            dimensions["innovation"] = "良好"
            dimensions["innovation_evidence"] = data.get("innovation_evidence", "")

        if isinstance(data.get("learning"), dict):
            dimensions["learning"] = data["learning"].get("level", "一般")
            dimensions["learning_evidence"] = data["learning"].get("evidence", "")
        elif data.get("learning_evidence"):
            dimensions["learning"] = "良好"
            dimensions["learning_evidence"] = data.get("learning_evidence", "")

        if isinstance(data.get("stress_resistance"), dict):
            dimensions["stress_resistance"] = data["stress_resistance"].get("level", "一般")
            dimensions["stress_resistance_evidence"] = data["stress_resistance"].get("evidence", "")
        elif data.get("stress_evidence"):
            dimensions["stress_resistance"] = "良好"
            dimensions["stress_resistance_evidence"] = data.get("stress_evidence", "")

        if isinstance(data.get("communication"), dict):
            dimensions["communication"] = data["communication"].get("level", "一般")
            dimensions["communication_evidence"] = data["communication"].get("evidence", "")
        elif data.get("communication_evidence"):
            dimensions["communication"] = "良好"
            dimensions["communication_evidence"] = data.get("communication_evidence", "")

        if isinstance(data.get("internship_ability"), dict):
            dimensions["internship"] = data["internship_ability"].get("level", "一般")
            dimensions["internship_evidence"] = data["internship_ability"].get("evidence", "")
        elif data.get("internship_evidence"):
            dimensions["internship"] = "良好"
            dimensions["internship_evidence"] = data.get("internship_evidence", "")
        elif data.get("internships") and len(data.get("internships", [])) > 0:
            internships = data.get("internships", [])
            if len(internships) >= 2:
                dimensions["internship"] = "优秀"
            else:
                dimensions["internship"] = "良好"
            dimensions["internship_evidence"] = f"有{len(internships)}段实习经历"

        if dimensions["innovation"] == "一般" and len(data.get("projects", [])) >= 3:
            dimensions["innovation"] = "良好"
            dimensions["innovation_evidence"] = f"参与{len(data.get('projects', []))}个项目"

        if dimensions["learning"] == "一般" and len(skills) >= 5:
            dimensions["learning"] = "良好"
            dimensions["learning_evidence"] = f"掌握{len(skills)}项技能"

        return dimensions

    def _calculate_completeness(self, data: Dict, dimensions: Dict) -> float:
        """计算完整度评分"""
        score = 0.0
        max_score = 100.0

        if data.get("name"):
            score += 10
        if data.get("education"):
            score += 15

        skills = data.get("skills", [])
        if skills:
            if isinstance(skills[0], dict):
                skills = [s.get("name", s) for s in skills]
            if len(skills) > 0:
                score += 15

        if data.get("projects") and len(data.get("projects", [])) > 0:
            score += 15
        if data.get("internships") and len(data.get("internships", [])) > 0:
            score += 15

        certificates = data.get("certificates", data.get("certs", []))
        if certificates and len(certificates) > 0:
            score += 10
        if data.get("career_intent"):
            score += 10
        if data.get("awards") and len(data.get("awards", [])) > 0:
            score += 10

        return min(score, max_score)

    def _calculate_competitiveness(self, data: Dict, dimensions: Dict) -> float:
        """计算竞争力评分"""
        score = 50.0

        skills = data.get("skills", [])
        if skills and isinstance(skills[0], dict):
            skills = [s.get("name", s) for s in skills]
        if len(skills) >= 5:
            score += 10
        if len(skills) >= 10:
            score += 5

        projects = data.get("projects", [])
        if len(projects) >= 2:
            score += 10
        if len(projects) >= 4:
            score += 5

        internships = data.get("internships", [])
        if len(internships) >= 1:
            score += 10
        if len(internships) >= 2:
            score += 5

        certificates = data.get("certificates", data.get("certs", []))
        if certificates and len(certificates) >= 1:
            score += 5

        for dim in ["innovation", "learning", "communication"]:
            if dimensions.get(dim) == "良好":
                score += 2
            elif dimensions.get(dim) == "优秀":
                score += 5

        return min(score, 100.0)

    def compute_match(
        self,
        student: StudentPortrait,
        job: JobPortrait,
        save_to_graph: bool = True,
        weights: Optional[Dict[str, float]] = None,
        apply_veto: bool = True,
    ) -> MatchResult:
        """
        计算人岗匹配（四维度）。
        权重与一票否决由 match_rules（匹配域单一事实源）裁决——REST 与 Agent 路径一致。
        weights=None 用红线默认权重；apply_veto=True 时基础要求不达标一票否决。
        匹配结果持久化到 student_graph_service（JSON），不写入职业知识图谱。
        """
        basic_match = self._match_basic_requirements(student, job)
        skill_match, matched_skills, missing_skills = self._match_skills(student, job)
        quality_match = self._match_qualities(student, job)
        potential_match = self._match_potential(student, job)

        # 权重综合（红线：默认权重不变）
        w = match_rules.resolve_weights(weights=weights)
        raw_total = match_rules.combine_total(
            basic_match, skill_match, quality_match, potential_match, w
        )
        # 一票否决（归位到匹配域，所有调用方一致）
        if apply_veto:
            total_match, eligible, veto_reason = match_rules.apply_veto(basic_match, raw_total)
        else:
            total_match = raw_total
            eligible = basic_match >= match_rules.BASIC_VETO_THRESHOLD
            veto_reason = ""

        details = {
            "basic_analysis":    self._generate_basic_analysis(student, job, basic_match),
            "skill_analysis":    self._generate_skill_analysis(student, job, skill_match),
            "quality_analysis":  self._generate_quality_analysis(student, job, quality_match),
            "potential_analysis":self._generate_potential_analysis(student, job, potential_match),
            "matched_skills":    matched_skills,
            "missing_skills":    missing_skills,
        }

        result = MatchResult(
            basic_match=basic_match,
            skill_match=skill_match,
            quality_match=quality_match,
            potential_match=potential_match,
            total_match=total_match,
            eligible=eligible,
            veto_reason=veto_reason,
            details=details,
        )

        if save_to_graph and student.student_id:
            try:
                student_graph_service.save_match_result(
                    student_id=student.student_id,
                    job_name=job.title,
                    match_result={
                        "basic_match":    basic_match,
                        "skill_match":    skill_match,
                        "quality_match":  quality_match,
                        "potential_match":potential_match,
                        "total_match":    total_match,
                        "matched_skills": matched_skills,
                        "missing_skills": missing_skills,
                        "skill_analysis": details.get("skill_analysis", ""),
                    },
                )
            except Exception as e:
                print(f"保存匹配结果失败: {e}")

            # 成长闭环：匹配快照（全保真——含 eligible/veto/有效权重 + 关联当前画像版本）。
            # 仅在 save_to_graph 时落（真实单次匹配），不污染推荐/批量的全岗位扫描。
            from app.services import snapshot_store
            snapshot_store.record_match_snapshot(
                student_id=student.student_id,
                job_name=job.title,
                match_result={
                    "total_match": total_match, "basic_match": basic_match,
                    "skill_match": skill_match, "quality_match": quality_match,
                    "potential_match": potential_match,
                    "matched_skills": matched_skills, "missing_skills": missing_skills,
                    "eligible": eligible, "veto_reason": veto_reason,
                },
                weight_used=w,
            )

        return result

    def _match_basic_requirements(self, student: StudentPortrait, job: JobPortrait) -> float:
        """基础要求匹配"""
        score = 50.0

        if student.education:
            score += 20

        if student.certificates:
            job_certs = set(job.certificates) if job.certificates else set()
            student_certs = set(student.certificates)
            if job_certs and (job_certs & student_certs):
                score += 20
            elif student.certificates:
                score += 10

        return min(score, 100.0)

    def _match_skills(self, student: StudentPortrait, job: JobPortrait):
        """职业技能匹配 - FAISS 模型向量余弦相似度（fallback: 规则词典）
        返回 (score: float, matched_skills: list, missing_skills: list)
        score 和列表使用同一套语义逻辑，保持一致性。
        """
        SIM_THRESHOLD = 0.78  # 语义匹配阈值（提高精度，减少跨领域误匹配）

        if not job.skills:
            return 50.0, list(student.skills), []
        if not student.skills:
            return 0.0, [], list(job.skills)

        student_skills = student.skills
        job_skills = job.skills

        # 精确匹配率（大小写不敏感 + 同义/缩写归并：K8s≡Kubernetes、JS≡JavaScript…）
        student_lower_map = {s.lower(): s for s in student_skills}
        student_lower = set(student_lower_map.keys())
        student_canon = {self._skill_canon(s) for s in student_skills}
        job_lower = [s.lower() for s in job_skills]

        def _is_exact(idx: int) -> bool:
            return job_lower[idx] in student_lower or self._skill_canon(job_skills[idx]) in student_canon

        exact_matches = sum(1 for ji in range(len(job_skills)) if _is_exact(ji))
        exact_ratio = exact_matches / len(job_lower)

        # ── 优先：FAISS 模型批量向量余弦相似度 ──────────────────
        try:
            import numpy as np
            encoder = (youtu_retriever_service.retriever.qa_encoder
                       if youtu_retriever_service.retriever else None)
            if encoder is not None:
                all_texts = student_skills + job_skills
                embs = encoder.encode(all_texts, convert_to_numpy=True, show_progress_bar=False)
                s_embs = embs[:len(student_skills)]
                j_embs = embs[len(student_skills):]

                # L2 归一化
                s_norm = s_embs / (np.linalg.norm(s_embs, axis=1, keepdims=True) + 1e-8)
                j_norm = j_embs / (np.linalg.norm(j_embs, axis=1, keepdims=True) + 1e-8)

                # 每个岗位技能取与任意学生技能的最大余弦相似度
                sim_matrix = j_norm @ s_norm.T          # [n_job, n_student]
                max_sims = sim_matrix.max(axis=1)       # [n_job]
                semantic_ratio = float(max_sims.mean())

                # 用阈值构建匹配/缺失列表（高频跨领域技能提高语义阈值）
                matched_skills, missing_skills = [], []
                for ji, sim in enumerate(max_sims):
                    js_orig = job_skills[ji]
                    is_exact = _is_exact(ji)
                    thr = 0.90 if js_orig in self._HIGH_FREQ_SKILLS else SIM_THRESHOLD
                    if float(sim) >= thr or is_exact:
                        matched_skills.append(js_orig)
                    else:
                        missing_skills.append(js_orig)

                final_score = min((exact_ratio * 0.5 + semantic_ratio * 0.5) * 100, 100.0)
                return final_score, matched_skills, missing_skills
        except Exception:
            pass

        # ── Fallback：规则词典 ───────────────────────────────────
        semantic_scores = []
        matched_skills, missing_skills = [], []
        for ji, job_skill in enumerate(job_lower):
            max_sim = max(
                (self._calculate_skill_similarity(stu, job_skill) for stu in student_lower),
                default=0.0
            )
            semantic_scores.append(max_sim)
            if max_sim >= SIM_THRESHOLD or _is_exact(ji):
                matched_skills.append(job_skills[ji])
            else:
                missing_skills.append(job_skills[ji])

        semantic_ratio = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0
        final_score = min((exact_ratio * 0.6 + semantic_ratio * 0.4) * 100, 100.0)
        return final_score, matched_skills, missing_skills

    def _calculate_skill_similarity(self, skill1: str, skill2: str) -> float:
        """规则词典技能相似度（_match_skills 降级时使用）"""
        if skill1 == skill2:
            return 1.0
        skill_groups = {
            'javascript': ['js', 'javascript', 'es6', 'typescript', 'ts', 'ajax'],
            'python': ['python', 'py', 'django', 'flask', 'fastapi', '数据分析'],
            'java': ['java', 'spring', 'springboot', 'spring boot', 'jvm'],
            'vue': ['vue', 'vuejs', 'vue.js', 'vue2', 'vue3', 'uniapp'],
            'react': ['react', 'reactjs', 'react.js', 'react native'],
            'css': ['css', 'css3', 'scss', 'sass', 'less', 'bootstrap'],
            'html': ['html', 'html5', 'xhtml'],
            'sql': ['sql', 'mysql', 'postgresql', 'oracle', '数据库', 'elasticsearch'],
            'linux': ['linux', 'ubuntu', 'centos', 'unix', 'shell'],
            'docker': ['docker', 'kubernetes', 'k8s'],
            'git': ['git', 'github', 'gitlab'],
            'node': ['node', 'nodejs', 'node.js', 'express'],
        }
        for variants in skill_groups.values():
            if any(v in skill1 for v in variants) and any(v in skill2 for v in variants):
                return 0.9
        if skill1 in skill2 or skill2 in skill1:
            return 0.7
        from difflib import SequenceMatcher
        return SequenceMatcher(None, skill1, skill2).ratio() * 0.5

    def _match_qualities(self, student: StudentPortrait, job: JobPortrait) -> float:
        """职业素养匹配"""
        quality_dims = ["innovation", "learning", "stress_resistance", "communication", "internship"]

        scores = {
            "优秀": 100,
            "良好": 80,
            "一般": 60,
            "较差": 40
        }

        total_score = 0
        for dim in quality_dims:
            student_val = getattr(student, dim, "一般")
            job_val = getattr(job, dim, "一般")

            student_score = scores.get(student_val, 60)
            job_score = scores.get(job_val, 60)

            if student_score >= job_score:
                total_score += 100
            elif student_score >= job_score - 20:
                total_score += 80
            else:
                total_score += 60

        return total_score / len(quality_dims)

    def _match_potential(self, student: StudentPortrait, job: JobPortrait) -> float:
        """发展潜力匹配 — 融合学生个人因素 + 图谱路径因素（各50%）"""
        # ── 学生侧（50分满分）: 项目、实习、学习力、创新力 ──
        student_score = 0.0
        if student.projects and len(student.projects) >= 2:
            student_score += 20
        elif student.projects and len(student.projects) >= 1:
            student_score += 10
        if student.internships and len(student.internships) >= 1:
            student_score += 15
        if student.learning == "优秀":
            student_score += 10
        elif student.learning == "良好":
            student_score += 7
        if student.innovation == "优秀":
            student_score += 5
        elif student.innovation == "良好":
            student_score += 3

        # ── 图谱侧（50分满分）: 岗位PROMOTES_TO+TRANSFERS_TO路径数 ──
        # 路径越多代表该岗位发展天花板越高，与赛题定义一致
        try:
            paths = self.get_career_paths(job.title)
            promotes_cnt = len(paths.vertical_paths)
            transfers_cnt = len(paths.horizontal_paths)
            # 对齐 YOUTU-GraphRAG 公式: ×10 + ×5，上限50
            graph_score = min(promotes_cnt * 10 + transfers_cnt * 5, 50)
        except Exception:
            graph_score = 25.0  # fallback: 中性分

        return min(student_score + graph_score, 100.0)

    def _generate_basic_analysis(self, student: StudentPortrait, job: JobPortrait, score: float) -> str:
        """生成基础要求分析"""
        if score >= 80:
            return f"基础要求匹配度较高({score:.1f}分)，学历和证书要求基本满足。"
        elif score >= 60:
            return f"基础要求匹配度一般({score:.1f}分)，建议补充相关证书。"
        else:
            return f"基础要求匹配度较低({score:.1f}分)，需要提升学历或获取相关证书。"

    def _generate_skill_analysis(self, student: StudentPortrait, job: JobPortrait, score: float) -> str:
        """生成技能分析"""
        matched = list(set(student.skills) & set(job.skills))
        missing = list(set(job.skills) - set(student.skills))

        analysis = f"技能匹配度{score:.1f}%。"
        if matched:
            analysis += f"已掌握技能: {', '.join(matched[:5])}。"
        if missing:
            analysis += f"待提升技能: {', '.join(missing[:5])}。"

        return analysis

    def _generate_quality_analysis(self, student: StudentPortrait, job: JobPortrait, score: float) -> str:
        """生成素养分析"""
        if score >= 80:
            return f"职业素养匹配度高({score:.1f}分)，综合能力较强。"
        elif score >= 60:
            return f"职业素养匹配度中等({score:.1f}分)，建议提升软技能。"
        else:
            return f"职业素养匹配度较低({score:.1f}分)，需要加强综合能力培养。"

    def _generate_potential_analysis(self, student: StudentPortrait, job: JobPortrait, score: float) -> str:
        """生成潜力分析"""
        if score >= 80:
            return f"发展潜力较大({score:.1f}分)，项目和实践经验丰富。"
        elif score >= 60:
            return f"发展潜力中等({score:.1f}分)，建议增加项目实践。"
        else:
            return f"发展潜力有待提升({score:.1f}分)，建议多参与实习和项目。"

    def _generate_evaluation_section(
        self,
        match_result: MatchResult,
        job: JobPortrait
    ) -> str:
        """基于匹配分数和缺失技能动态生成评估周期与量化指标"""
        score = match_result.total_match
        missing = match_result.details.get("missing_skills", [])
        n_missing = len(missing)

        # 动态评估节奏
        if score < 60:
            skill_cycle = "每2周进行一次技能自评（当前差距较大，需密集跟进）"
            resume_cycle = "每月更新简历，记录新增技能与项目成果"
            review_cycle = "每3个月进行职业规划复盘，及时调整方向"
        elif score < 80:
            skill_cycle = "每月进行一次技能自评"
            resume_cycle = "每季度更新简历和作品集"
            review_cycle = "每半年进行职业规划复盘"
        else:
            skill_cycle = "每季度进行技能自评（基础扎实，保持稳定节奏）"
            resume_cycle = "每半年更新简历"
            review_cycle = "每年进行一次深度职业规划复盘"

        # 量化评估指标
        kpis = []
        timelines = ["1个月", "2个月", "3个月"]
        for i, skill in enumerate(missing[:3]):
            kpis.append(
                f"- 技能指标{i+1}：{timelines[i]}内完成「{skill}」从入门到实践"
                f"（以完成相关项目或通过测试为验证标准）"
            )
        if job.certificates:
            kpis.append(
                f"- 证书指标：短期内完成 {job.certificates[0]} 备考，取证即视为达标"
            )
        target_score = min(score + 15, 95)
        kpis.append(
            f"- 匹配度指标：当前人岗匹配 {score:.1f}%，"
            f"目标3个月内提升至 {target_score:.0f}%"
        )
        kpis.append(
            f"- 实践指标：完成至少 {max(1, n_missing)} 个与「{job.title}」"
            f"相关的项目或实习经历"
        )

        kpis_text = "\n".join(kpis) if kpis else "- 持续深化现有技能，保持竞争优势"

        return f"""### 3.3 评估周期与指标

**评估节奏**（基于当前匹配度 {score:.1f}%）：
- 技能自评：{skill_cycle}
- 简历更新：{resume_cycle}
- 规划复盘：{review_cycle}

**量化评估指标**（可验证里程碑）：
{kpis_text}

**动态调整机制**：每次复盘后，若任一指标未达成，优先调整对应短期计划；若匹配度提升超过10%，可提前进入中期阶段目标。"""

    def _generate_phased_plan(
        self,
        student: StudentPortrait,
        job: JobPortrait,
        match_result: MatchResult
    ) -> PhasedPlan:
        """
        生成分阶段职业发展计划

        Args:
            student: 学生画像
            job: 岗位画像
            match_result: 匹配结果

        Returns:
            PhasedPlan: 分阶段计划
        """
        missing_skills = match_result.details.get("missing_skills", [])
        matched_skills = match_result.details.get("matched_skills", [])

        short_term = []
        mid_term = []
        long_term = []

        if missing_skills:
            for i, skill in enumerate(missing_skills[:3]):
                short_term.append(ActionItem(
                    title=f"学习{skill}",
                    description=f"系统学习{skill}相关知识和实践应用",
                    timeline=f"第{i+1}-{i+2}个月",
                    resources=[
                        f"在线课程: {skill}入门到精通",
                        f"实践项目: {skill}小项目练习",
                        f"技术文档: {skill}官方文档"
                    ],
                    milestones=[
                        f"完成{skill}基础学习",
                        f"完成至少1个{skill}实践项目",
                        f"通过{skill}相关测试"
                    ],
                    status="pending"
                ))

        if job.certificates:
            for i, cert in enumerate(job.certificates[:2]):
                short_term.append(ActionItem(
                    title=f"考取{cert}",
                    description=f"准备并考取{cert}证书",
                    timeline=f"第{i*2+1}-{i*2+3}个月",
                    resources=[
                        f"{cert}考试大纲",
                        f"{cert}培训课程",
                        f"{cert}模拟题库"
                    ],
                    milestones=[
                        f"完成{cert}课程学习",
                        f"通过模拟考试",
                        f"获得{cert}证书"
                    ],
                    status="pending"
                ))

        mid_term.append(ActionItem(
            title="项目经验积累",
            description="完成与目标岗位相关的项目实践",
            timeline="第3-6个月",
            resources=[
                "GitHub开源项目",
                "个人项目开发",
                "实习项目参与"
            ],
            milestones=[
                "完成2-3个相关项目",
                "建立个人作品集",
                "获得项目经验证明"
            ],
            status="pending"
        ))

        mid_term.append(ActionItem(
            title="实习机会获取",
            description="获取目标岗位的实习机会",
            timeline="第4-6个月",
            resources=[
                "校园招聘平台",
                "企业官网投递",
                "内推渠道"
            ],
            milestones=[
                "完善简历",
                "通过面试",
                "获得实习offer"
            ],
            status="pending"
        ))

        long_term.append(ActionItem(
            title="专业技能深化",
            description="深化目标岗位核心技能",
            timeline="第6-12个月",
            resources=[
                "高级技术课程",
                "行业技术博客",
                "技术社区参与"
            ],
            milestones=[
                "掌握高级技能",
                "参与技术分享",
                "建立技术影响力"
            ],
            status="pending"
        ))

        long_term.append(ActionItem(
            title="职业发展准备",
            description="为职业晋升和转岗做准备",
            timeline="第9-12个月",
            resources=[
                "职业规划咨询",
                "行业人脉拓展",
                "管理技能学习"
            ],
            milestones=[
                "明确职业发展路径",
                "建立行业人脉",
                "获得转正或晋升机会"
            ],
            status="pending"
        ))

        return PhasedPlan(
            short_term=short_term,
            mid_term=mid_term,
            long_term=long_term,
            generated_at=datetime.now().isoformat()
        )

    # 与核心岗位技能无关的噪声词黑名单（来自图谱 LLM 抽取误差）
    _SKILL_BLACKLIST = {
        "新能源", "市场推广", "财务", "法律", "广告",
    }
    # 高频跨领域技能（出现在 >15% 岗位），语义匹配阈值上调，减少误匹配；精确匹配不受限
    _HIGH_FREQ_SKILLS = {
        "绩效管理", "招聘", "合同审查", "薪酬管理", "英语",
        "Excel", "行政", "营销", "数据分析", "项目管理",
        "成本核算", "知识产权", "商务谈判", "专利申请", "PS",
        "新媒体运营",
    }
    # 命名标准化映射（图谱名 → 标准名）
    _SKILL_ALIAS = {
        "Vue.js": "Vue", "vue.js": "Vue",
        "Node.JS": "Node.js", "nodejs": "Node.js",
        "Golang": "Go",
        "scikit-learn": "sklearn",
    }
    # 同义/缩写归并组：组内视为同一技能（用于精确匹配判定）。
    # 真实学生常写缩写（K8s/JS/Golang），岗位写全称——让它们能匹配上。仅扩匹配召回，不改权重/veto。
    _SYNONYM_GROUPS = [
        {"javascript", "js"},
        {"typescript", "ts"},
        {"kubernetes", "k8s"},
        {"go", "golang"},
        {"node.js", "nodejs", "node"},
        {"vue", "vue.js", "vuejs"},
        {"react", "react.js", "reactjs"},
        {"spring", "spring boot", "springboot"},
        {"postgresql", "postgres"},
        {"tensorflow", "tf"},
    ]
    _SYNONYM_CANON = {m: sorted(g)[0] for g in _SYNONYM_GROUPS for m in g}

    def _skill_canon(self, s: str) -> str:
        """技能名归并到同义组代表名（小写）；非同义词原样小写。"""
        low = (s or "").strip().lower()
        return self._SYNONYM_CANON.get(low, low)

    # ── 图谱数据治理：图谱 LLM 抽取把 HR/财务/法务噪声系统性塞进技术岗 ──────────
    # 这些技能对 HR/销售/法务岗是合法的，仅在“技术岗”语境下是噪声 → 按域剔除（不全局黑名单）。
    _NONTECH_NOISE = {
        "绩效管理", "招聘", "薪酬管理", "合同审查", "知识产权", "专利申请", "成本核算",
        "新能源", "市场推广", "诉讼", "仲裁", "劳动关系", "招投标", "招商", "审计", "税务", "会计",
    }
    # 明确的技术岗（在这些岗位上才剔除上面的非技术噪声）
    _TECH_JOBS = {
        "前端开发", "后端开发", "测试工程师", "软件测试", "硬件测试", "C/C++", "Java",
        "算法工程师", "运维工程师", "数据分析", "数据运营", "硬件工程师", "实施工程师", "技术支持工程师",
    }
    # 补全图谱缺失/稀疏岗位（按真实岗位要求人工补；非为过测试，gold 另行诚实标注）
    _JOB_SKILL_SUPPLEMENT = {
        "后端开发": ["Java", "Spring Boot", "Spring", "MyBatis", "MySQL", "Redis",
                     "Linux", "Git", "Maven", "微服务", "消息队列", "分布式"],
    }

    def _govern_job_skills(self, job_name: str, skills: List[str]) -> List[str]:
        """岗位技能治理：补全缺失/稀疏岗位 + 按域剔除非技术噪声。只读、纯函数。"""
        out = list(skills or [])
        supp = self._JOB_SKILL_SUPPLEMENT.get(job_name)
        if supp and len(out) < 3:            # 缺失/稀疏 → 用补全技能
            out = list(supp)
        if job_name in self._TECH_JOBS:       # 技术岗 → 去 HR/财务/法务噪声
            out = [s for s in out if s not in self._NONTECH_NOISE]
        return out

    def _clean_skills(self, skills: List[str]) -> List[str]:
        """去重 + 去噪声 + 命名标准化"""
        seen = set()
        result = []
        for s in skills:
            if not s or not s.strip():
                continue
            # 命名标准化
            s = self._SKILL_ALIAS.get(s, s)
            # 黑名单过滤
            if s in self._SKILL_BLACKLIST:
                continue
            # 去重（不区分大小写）
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(s)
        return result

    def _normalize_skills(self, skills: List[str]) -> List[str]:
        """将 LLM 提取的技能名标准化为图谱中的标准名称。
        策略：精确匹配优先；否则做不区分大小写子串匹配，取最短图谱名（最具体）。
        """
        graph_skills = set(self._skills_index.keys())
        if not graph_skills:
            return skills

        normalized = []
        for raw in skills:
            if not raw:
                continue
            raw_lower = raw.lower().strip()
            # 1. 精确匹配（不区分大小写）
            matched = next((gs for gs in graph_skills if gs.lower() == raw_lower), None)
            # 2. 图谱名是原始名的子串，或原始名是图谱名的子串
            if not matched:
                candidates = [
                    gs for gs in graph_skills
                    if raw_lower in gs.lower() or gs.lower() in raw_lower
                ]
                if candidates:
                    # 取最短的（避免过泛）
                    matched = min(candidates, key=len)
            normalized.append(matched if matched else raw)
        return normalized



career_graphrag_service = CareerGraphRAGService()
