"""
CrewAI Agent协作框架集成
实现多Agent协作的职业规划系统
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    RESUME_ANALYZER = "resume_analyzer"
    JOB_MATCHER = "job_matcher"
    CAREER_ADVISOR = "career_advisor"
    REPORT_GENERATOR = "report_generator"


@dataclass
class AgentTask:
    id: str
    role: AgentRole
    description: str
    expected_output: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class AgentResult:
    task_id: str
    role: AgentRole
    success: bool
    data: Dict[str, Any]
    confidence: float = 0.0
    reasoning: str = ""
    suggestions: List[str] = field(default_factory=list)


class BaseAgent:
    def __init__(self, role: AgentRole, llm_client=None):
        self.role = role
        self.llm_client = llm_client
        self.memory: Dict[str, Any] = {}
    
    async def execute(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError
    
    def update_memory(self, key: str, value: Any):
        self.memory[key] = value
    
    def get_memory(self, key: str) -> Any:
        return self.memory.get(key)


class ResumeAnalyzerAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.RESUME_ANALYZER, llm_client)
    
    async def execute(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        resume_content = context.get("resume_content", "")
        parsed_data = context.get("parsed_data", {})
        
        analysis_result = {
            "basic_info": parsed_data.get("basic_info", {}),
            "education": parsed_data.get("education", []),
            "skills": self._extract_skills(resume_content, parsed_data),
            "experience": self._analyze_experience(parsed_data.get("internships", [])),
            "projects": self._analyze_projects(parsed_data.get("projects", [])),
            "certifications": parsed_data.get("certs", []),
            "awards": parsed_data.get("awards", []),
            "completeness_score": self._calculate_completeness(parsed_data),
            "quality_score": self._assess_quality(resume_content, parsed_data),
        }
        
        return AgentResult(
            task_id=task.id,
            role=self.role,
            success=True,
            data=analysis_result,
            confidence=self._calculate_confidence(analysis_result),
            reasoning="基于简历内容进行结构化分析，提取关键信息并评估质量",
            suggestions=self._generate_suggestions(analysis_result)
        )
    
    def _extract_skills(self, content: str, parsed_data: Dict) -> List[Dict]:
        skills = parsed_data.get("skills", [])
        skill_details = []
        for skill in skills:
            skill_details.append({
                "name": skill,
                "level": self._infer_skill_level(content, skill),
                "evidence": self._find_evidence(content, skill)
            })
        return skill_details
    
    def _infer_skill_level(self, content: str, skill: str) -> str:
        skill_lower = skill.lower()
        content_lower = content.lower()
        
        if f"精通{skill}" in content or f"精通 {skill}" in content_lower:
            return "expert"
        elif f"熟练{skill}" in content or f"熟练 {skill}" in content_lower:
            return "proficient"
        elif f"掌握{skill}" in content or f"熟悉{skill}" in content_lower:
            return "intermediate"
        else:
            return "beginner"
    
    def _find_evidence(self, content: str, skill: str) -> str:
        lines = content.split('\n')
        for line in lines:
            if skill.lower() in line.lower():
                return line.strip()[:100]
        return ""
    
    def _analyze_experience(self, experiences: List) -> List[Dict]:
        analyzed = []
        for exp in experiences:
            analyzed.append({
                "company": exp.get("company", ""),
                "role": exp.get("role", ""),
                "duration": exp.get("duration", ""),
                "key_achievements": self._extract_achievements(exp.get("description", ""))
            })
        return analyzed
    
    def _extract_achievements(self, description: str) -> List[str]:
        achievements = []
        keywords = ["完成", "实现", "优化", "提升", "负责", "主导", "参与"]
        for keyword in keywords:
            if keyword in description:
                idx = description.find(keyword)
                achievement = description[max(0, idx-10):min(len(description), idx+50)]
                achievements.append(achievement.strip())
        return achievements[:3]
    
    def _analyze_projects(self, projects: List) -> List[Dict]:
        analyzed = []
        for proj in projects:
            analyzed.append({
                "name": proj.get("name", ""),
                "tech_stack": proj.get("tech_stack", []),
                "role": proj.get("role", ""),
                "impact": self._assess_project_impact(proj)
            })
        return analyzed
    
    def _assess_project_impact(self, project: Dict) -> str:
        desc = project.get("description", "")
        if any(kw in desc for kw in ["用户", "流量", "收入", "性能", "效率"]):
            return "high"
        elif any(kw in desc for kw in ["功能", "模块", "组件"]):
            return "medium"
        else:
            return "low"
    
    def _calculate_completeness(self, data: Dict) -> float:
        required_fields = ["basic_info", "education", "skills", "internships", "projects"]
        present = sum(1 for f in required_fields if data.get(f))
        return present / len(required_fields) * 100
    
    def _assess_quality(self, content: str, data: Dict) -> float:
        score = 50.0
        
        if len(content) > 1000:
            score += 10
        if len(data.get("skills", [])) >= 5:
            score += 10
        if data.get("projects"):
            score += 10
        if data.get("internships"):
            score += 10
        if any(exp.get("duration", "") for exp in data.get("internships", [])):
            score += 10
        
        return min(score, 100.0)
    
    def _calculate_confidence(self, result: Dict) -> float:
        completeness = result.get("completeness_score", 0) / 100
        quality = result.get("quality_score", 0) / 100
        return (completeness * 0.4 + quality * 0.6)
    
    def _generate_suggestions(self, result: Dict) -> List[str]:
        suggestions = []
        
        if result.get("completeness_score", 0) < 70:
            suggestions.append("建议补充更多简历信息以提高完整度")
        if len(result.get("skills", [])) < 5:
            suggestions.append("建议添加更多专业技能以提升竞争力")
        if not result.get("projects"):
            suggestions.append("建议添加项目经历以展示实践能力")
        if not result.get("internships"):
            suggestions.append("建议添加实习经历以增强简历竞争力")
        
        return suggestions


class JobMatcherAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.JOB_MATCHER, llm_client)
    
    async def execute(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        resume_analysis = context.get("resume_analysis", {})
        target_jobs = context.get("target_jobs", [])
        
        match_results = []
        for job in target_jobs:
            match_score = self._calculate_match(resume_analysis, job)
            match_results.append({
                "job_title": job.get("title", job.get("job_title", "")),
                "match_score": match_score["overall"],
                "dimensions": match_score["dimensions"],
                "matched_skills": match_score["matched_skills"],
                "gap_skills": match_score["gap_skills"],
                "recommendation": match_score["recommendation"]
            })
        
        match_results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return AgentResult(
            task_id=task.id,
            role=self.role,
            success=True,
            data={"matches": match_results[:10]},
            confidence=self._calculate_confidence(match_results),
            reasoning="基于简历分析和岗位需求进行多维度匹配计算",
            suggestions=self._generate_suggestions(match_results)
        )
    
    def _calculate_match(self, resume: Dict, job: Dict) -> Dict:
        dimensions = {
            "basic_requirements": self._match_basic(resume, job),
            "professional_skills": self._match_skills(resume, job),
            "professional_qualities": self._match_qualities(resume, job),
            "development_potential": self._match_potential(resume, job),
            "market_demand": self._match_market(job)
        }
        
        weights = {
            "basic_requirements": 0.20,
            "professional_skills": 0.35,
            "professional_qualities": 0.20,
            "development_potential": 0.15,
            "market_demand": 0.10
        }
        
        overall = sum(dimensions[k] * weights[k] for k in dimensions)
        
        resume_skills = set(s.get("name", s) if isinstance(s, dict) else s for s in resume.get("skills", []))
        job_skills = set(job.get("required_skills", []) + job.get("preferred_skills", []))
        
        matched = list(resume_skills & job_skills)
        gap = list(job_skills - resume_skills)
        
        return {
            "overall": round(overall, 1),
            "dimensions": dimensions,
            "matched_skills": matched,
            "gap_skills": gap,
            "recommendation": self._generate_recommendation(overall, gap)
        }
    
    def _match_basic(self, resume: Dict, job: Dict) -> float:
        score = 70.0
        
        education = resume.get("education", [])
        if education:
            degree = education[0].get("degree", "") if education else ""
            required_degree = job.get("education_level", "本科")
            if self._degree_matches(degree, required_degree):
                score += 15
        
        experiences = resume.get("internships", [])
        total_months = sum(self._parse_duration(exp.get("duration", "")) for exp in experiences)
        required_exp = job.get("experience_range", (0, 0))
        if required_exp[0] <= total_months <= required_exp[1] if isinstance(required_exp, tuple) else True:
            score += 15
        
        return min(score, 100.0)
    
    def _degree_matches(self, degree: str, required: str) -> bool:
        degree_levels = {"专科": 1, "本科": 2, "硕士": 3, "博士": 4}
        student_level = degree_levels.get(degree, 0)
        required_level = degree_levels.get(required, 0)
        return student_level >= required_level
    
    def _parse_duration(self, duration: str) -> int:
        import re
        months = 0
        year_match = re.search(r'(\d+)\s*年', duration)
        month_match = re.search(r'(\d+)\s*个?月', duration)
        
        if year_match:
            months += int(year_match.group(1)) * 12
        if month_match:
            months += int(month_match.group(1))
        
        return months
    
    def _match_skills(self, resume: Dict, job: Dict) -> float:
        resume_skills = set()
        for s in resume.get("skills", []):
            if isinstance(s, dict):
                resume_skills.add(s.get("name", ""))
            else:
                resume_skills.add(s)
        
        job_skills = set(job.get("required_skills", []) + job.get("preferred_skills", []))
        
        if not job_skills:
            return 70.0
        
        matched = len(resume_skills & job_skills)
        total = len(job_skills)
        
        return min(matched / total * 100, 100.0) if total > 0 else 70.0
    
    def _match_qualities(self, resume: Dict, job: Dict) -> float:
        score = 60.0
        
        if resume.get("projects"):
            score += 15
        if resume.get("internships"):
            score += 15
        if resume.get("awards"):
            score += 10
        
        return min(score, 100.0)
    
    def _match_potential(self, resume: Dict, job: Dict) -> float:
        score = 60.0
        
        education = resume.get("education", [])
        if education:
            degree = education[0].get("degree", "") if education else ""
            if degree in ["硕士", "博士"]:
                score += 20
            elif degree == "本科":
                score += 10
        
        skills = resume.get("skills", [])
        if len(skills) >= 8:
            score += 20
        elif len(skills) >= 5:
            score += 10
        
        return min(score, 100.0)
    
    def _match_market(self, job: Dict) -> float:
        return job.get("market_heat", 5) * 10
    
    def _generate_recommendation(self, score: float, gaps: List[str]) -> str:
        if score >= 80:
            return "高度匹配，建议优先考虑"
        elif score >= 60:
            gap_str = "、".join(gaps[:3]) if gaps else "相关技能"
            return f"中等匹配，建议提升{gap_str}等技能"
        else:
            return "匹配度较低，建议考虑其他岗位或提升相关能力"
    
    def _calculate_confidence(self, results: List[Dict]) -> float:
        if not results:
            return 0.0
        return sum(r["match_score"] for r in results) / len(results) / 100
    
    def _generate_suggestions(self, results: List[Dict]) -> List[str]:
        suggestions = []
        
        high_matches = [r for r in results if r["match_score"] >= 70]
        if high_matches:
            suggestions.append(f"发现{len(high_matches)}个高匹配度岗位，建议重点关注")
        
        common_gaps = {}
        for r in results[:5]:
            for skill in r.get("gap_skills", [])[:3]:
                common_gaps[skill] = common_gaps.get(skill, 0) + 1
        
        top_gaps = sorted(common_gaps.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_gaps:
            suggestions.append(f"建议重点提升技能: {', '.join([g[0] for g in top_gaps])}")
        
        return suggestions


class CareerAdvisorAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.CAREER_ADVISOR, llm_client)
    
    async def execute(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        resume_analysis = context.get("resume_analysis", {})
        match_results = context.get("match_results", {})
        user_question = context.get("question", "")
        
        advice = {
            "career_direction": self._analyze_direction(resume_analysis, match_results),
            "development_path": self._suggest_path(resume_analysis, match_results),
            "skill_priorities": self._prioritize_skills(resume_analysis, match_results),
            "action_items": self._generate_actions(resume_analysis, match_results),
            "timeline": self._suggest_timeline(resume_analysis),
        }
        
        if user_question:
            advice["qa_response"] = self._answer_question(user_question, resume_analysis, match_results)
        
        return AgentResult(
            task_id=task.id,
            role=self.role,
            success=True,
            data=advice,
            confidence=0.85,
            reasoning="基于简历分析和匹配结果，提供个性化职业发展建议",
            suggestions=advice.get("action_items", [])[:5]
        )
    
    def _analyze_direction(self, resume: Dict, matches: Dict) -> Dict:
        top_matches = matches.get("matches", [])[:3]
        
        directions = []
        for m in top_matches:
            directions.append({
                "job": m["job_title"],
                "fit_score": m["match_score"],
                "reason": m["recommendation"]
            })
        
        return {
            "primary": directions[0] if directions else None,
            "alternatives": directions[1:3],
            "confidence": "high" if directions else "low"
        }
    
    def _suggest_path(self, resume: Dict, matches: Dict) -> List[Dict]:
        path = []
        
        experiences = resume.get("internships", [])
        if experiences:
            path.append({
                "stage": "当前阶段",
                "position": experiences[-1].get("role", "实习生"),
                "duration": "0-1年"
            })
        
        top_match = matches.get("matches", [{}])[0]
        if top_match:
            path.append({
                "stage": "短期目标",
                "position": top_match.get("job_title", ""),
                "duration": "1-3年"
            })
            path.append({
                "stage": "中期目标",
                "position": "高级" + top_match.get("job_title", "").replace("工程师", "工程师").replace("专员", "专员"),
                "duration": "3-5年"
            })
        
        return path
    
    def _prioritize_skills(self, resume: Dict, matches: Dict) -> List[Dict]:
        all_gaps = {}
        for m in matches.get("matches", [])[:5]:
            for skill in m.get("gap_skills", []):
                all_gaps[skill] = all_gaps.get(skill, 0) + 1
        
        priorities = []
        for skill, count in sorted(all_gaps.items(), key=lambda x: x[1], reverse=True)[:10]:
            priorities.append({
                "skill": skill,
                "importance": "high" if count >= 3 else "medium",
                "demand_count": count,
                "learning_resources": self._suggest_resources(skill)
            })
        
        return priorities
    
    def _suggest_resources(self, skill: str) -> List[str]:
        resources_map = {
            "Python": ["官方文档", "LeetCode", "Real Python"],
            "Java": ["官方教程", "《Effective Java》", "LeetCode"],
            "Vue": ["Vue官方文档", "Vue Mastery", "Vue School"],
            "React": ["React官方文档", "React Tutorial", "Egghead"],
            "MySQL": ["MySQL官方文档", "《高性能MySQL》"],
        }
        return resources_map.get(skill, ["官方文档", "在线教程", "实战项目"])
    
    def _generate_actions(self, resume: Dict, matches: Dict) -> List[str]:
        actions = []
        
        gaps = self._prioritize_skills(resume, matches)
        if gaps:
            actions.append(f"学习{gaps[0]['skill']}技能，参考{', '.join(gaps[0]['learning_resources'][:2])}")
        
        if not resume.get("projects"):
            actions.append("参与开源项目或个人项目，积累实践经验")
        
        if not resume.get("internships"):
            actions.append("寻找相关实习机会，获取行业经验")
        
        actions.append("完善简历，突出项目成果和技术亮点")
        actions.append("建立技术博客或GitHub，展示技术能力")
        
        return actions
    
    def _suggest_timeline(self, resume: Dict) -> Dict:
        return {
            "short_term": {
                "period": "1-3个月",
                "goals": ["完善简历", "学习核心技能", "准备面试"]
            },
            "mid_term": {
                "period": "3-6个月",
                "goals": ["参与项目实践", "获取实习机会", "建立作品集"]
            },
            "long_term": {
                "period": "6-12个月",
                "goals": ["获得目标岗位offer", "持续技能提升", "职业发展规划"]
            }
        }
    
    def _answer_question(self, question: str, resume: Dict, matches: Dict) -> str:
        question_lower = question.lower()
        
        if "方向" in question or "选择" in question:
            top_match = matches.get("matches", [{}])[0]
            return f"根据您的背景分析，建议您优先考虑{top_match.get('job_title', '相关技术岗位')}方向，匹配度达到{top_match.get('match_score', 0)}%。"
        
        elif "技能" in question or "学习" in question:
            gaps = self._prioritize_skills(resume, matches)
            if gaps:
                return f"建议您优先学习{gaps[0]['skill']}技能，这是多个目标岗位的核心要求。"
            return "您已具备较好的技能基础，建议深入学习提升专业深度。"
        
        elif "简历" in question:
            completeness = resume.get("completeness_score", 0)
            if completeness < 70:
                return f"您的简历完整度为{completeness:.0f}%，建议补充项目经历和技能详情。"
            return "您的简历较为完整，建议优化项目描述，突出成果和影响力。"
        
        else:
            return "我可以帮您分析职业方向、技能提升建议、简历优化等方面的问题，请详细描述您的疑问。"


class ReportGeneratorAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(AgentRole.REPORT_GENERATOR, llm_client)
    
    async def execute(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        resume_analysis = context.get("resume_analysis", {})
        match_results = context.get("match_results", {})
        career_advice = context.get("career_advice", {})
        
        report = {
            "title": "职业发展规划报告",
            "generated_at": datetime.now().isoformat(),
            "sections": [
                self._generate_summary_section(resume_analysis),
                self._generate_match_section(match_results),
                self._generate_skill_section(resume_analysis, match_results),
                self._generate_path_section(career_advice),
                self._generate_action_section(career_advice),
                self._generate_timeline_section(career_advice),
            ],
            "metadata": {
                "completeness": resume_analysis.get("completeness_score", 0),
                "quality_score": resume_analysis.get("quality_score", 0),
                "top_match": match_results.get("matches", [{}])[0].get("job_title", "") if match_results.get("matches") else ""
            }
        }
        
        return AgentResult(
            task_id=task.id,
            role=self.role,
            success=True,
            data=report,
            confidence=0.90,
            reasoning="整合简历分析、匹配结果和职业建议，生成结构化报告",
            suggestions=["建议定期更新报告以反映最新进展"]
        )
    
    def _generate_summary_section(self, resume: Dict) -> Dict:
        return {
            "id": "summary",
            "title": "个人画像摘要",
            "content": {
                "education": resume.get("education", []),
                "skills_count": len(resume.get("skills", [])),
                "experience_count": len(resume.get("internships", [])),
                "project_count": len(resume.get("projects", [])),
                "completeness": resume.get("completeness_score", 0),
                "quality": resume.get("quality_score", 0)
            }
        }
    
    def _generate_match_section(self, matches: Dict) -> Dict:
        match_list = matches.get("matches", [])[:5]
        return {
            "id": "match_analysis",
            "title": "岗位匹配分析",
            "content": {
                "top_matches": [
                    {
                        "job": m.get("job_title", ""),
                        "score": m.get("match_score", 0),
                        "dimensions": m.get("dimensions", {}),
                        "recommendation": m.get("recommendation", "")
                    }
                    for m in match_list
                ]
            }
        }
    
    def _generate_skill_section(self, resume: Dict, matches: Dict) -> Dict:
        skills = resume.get("skills", [])
        gaps = set()
        for m in matches.get("matches", [])[:5]:
            gaps.update(m.get("gap_skills", []))
        
        return {
            "id": "skill_analysis",
            "title": "技能分析与提升建议",
            "content": {
                "current_skills": [s.get("name", s) if isinstance(s, dict) else s for s in skills],
                "gap_skills": list(gaps)[:10],
                "priority_skills": list(gaps)[:5]
            }
        }
    
    def _generate_path_section(self, advice: Dict) -> Dict:
        return {
            "id": "career_path",
            "title": "职业发展路径",
            "content": {
                "direction": advice.get("career_direction", {}),
                "path": advice.get("development_path", [])
            }
        }
    
    def _generate_action_section(self, advice: Dict) -> Dict:
        return {
            "id": "action_plan",
            "title": "行动计划",
            "content": {
                "actions": advice.get("action_items", []),
                "skill_priorities": advice.get("skill_priorities", [])[:5]
            }
        }
    
    def _generate_timeline_section(self, advice: Dict) -> Dict:
        return {
            "id": "timeline",
            "title": "时间规划",
            "content": advice.get("timeline", {})
        }


class CrewManager:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.agents = {
            AgentRole.RESUME_ANALYZER: ResumeAnalyzerAgent(llm_client),
            AgentRole.JOB_MATCHER: JobMatcherAgent(llm_client),
            AgentRole.CAREER_ADVISOR: CareerAdvisorAgent(llm_client),
            AgentRole.REPORT_GENERATOR: ReportGeneratorAgent(llm_client),
        }
        self.task_history: List[AgentTask] = []
        self.results: Dict[str, AgentResult] = {}
    
    async def run_workflow(self, resume_content: str, parsed_data: Dict, target_jobs: List[Dict]) -> Dict:
        workflow_start = datetime.now()
        
        task1 = AgentTask(
            id="task_1_resume_analysis",
            role=AgentRole.RESUME_ANALYZER,
            description="分析简历内容，提取关键信息",
            expected_output="结构化的简历分析结果"
        )
        
        result1 = await self.agents[AgentRole.RESUME_ANALYZER].execute(
            task1,
            {"resume_content": resume_content, "parsed_data": parsed_data}
        )
        self.results[task1.id] = result1
        self.task_history.append(task1)
        
        task2 = AgentTask(
            id="task_2_job_matching",
            role=AgentRole.JOB_MATCHER,
            description="匹配岗位，计算匹配度",
            expected_output="岗位匹配结果列表",
            dependencies=[task1.id]
        )
        
        result2 = await self.agents[AgentRole.JOB_MATCHER].execute(
            task2,
            {"resume_analysis": result1.data, "target_jobs": target_jobs}
        )
        self.results[task2.id] = result2
        self.task_history.append(task2)
        
        task3 = AgentTask(
            id="task_3_career_advice",
            role=AgentRole.CAREER_ADVISOR,
            description="生成职业发展建议",
            expected_output="个性化职业建议",
            dependencies=[task1.id, task2.id]
        )
        
        result3 = await self.agents[AgentRole.CAREER_ADVISOR].execute(
            task3,
            {"resume_analysis": result1.data, "match_results": result2.data}
        )
        self.results[task3.id] = result3
        self.task_history.append(task3)
        
        task4 = AgentTask(
            id="task_4_report_generation",
            role=AgentRole.REPORT_GENERATOR,
            description="生成职业规划报告",
            expected_output="结构化报告",
            dependencies=[task1.id, task2.id, task3.id]
        )
        
        result4 = await self.agents[AgentRole.REPORT_GENERATOR].execute(
            task4,
            {
                "resume_analysis": result1.data,
                "match_results": result2.data,
                "career_advice": result3.data
            }
        )
        self.results[task4.id] = result4
        self.task_history.append(task4)
        
        return {
            "workflow_id": f"workflow_{workflow_start.strftime('%Y%m%d%H%M%S')}",
            "status": "completed",
            "duration_seconds": (datetime.now() - workflow_start).total_seconds(),
            "results": {
                "resume_analysis": result1.data,
                "job_matching": result2.data,
                "career_advice": result3.data,
                "report": result4.data
            },
            "confidence": {
                "overall": (result1.confidence + result2.confidence + result3.confidence + result4.confidence) / 4,
                "breakdown": {
                    "resume_analysis": result1.confidence,
                    "job_matching": result2.confidence,
                    "career_advice": result3.confidence,
                    "report": result4.confidence
                }
            },
            "suggestions": result3.suggestions + result4.suggestions
        }
    
    async def run_single_agent(self, role: AgentRole, context: Dict) -> AgentResult:
        task = AgentTask(
            id=f"single_{role.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            role=role,
            description=f"执行{role.value}任务",
            expected_output="任务结果"
        )
        
        result = await self.agents[role].execute(task, context)
        self.results[task.id] = result
        self.task_history.append(task)
        
        return result
    
    def get_agent_memory(self, role: AgentRole) -> Dict:
        return self.agents[role].memory
    
    def get_task_history(self) -> List[AgentTask]:
        return self.task_history
    
    def get_result(self, task_id: str) -> Optional[AgentResult]:
        return self.results.get(task_id)


crew_manager = CrewManager()
