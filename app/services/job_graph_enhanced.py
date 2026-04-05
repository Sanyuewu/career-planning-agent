# -*- coding: utf-8 -*-
"""
岗位图谱增强模块
目标：将换岗岗位匹配度从55%提升至70%
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class SkillSimilarity:
    """技能相似度"""
    skill_a: str
    skill_b: str
    similarity: float
    category: str = "general"  # programming, framework, database, tool, soft


@dataclass
class JobMatchResult:
    """岗位匹配结果"""
    target_job: str
    match_score: float
    match_level: str
    skill_overlap: float
    industry_similarity: float
    career_progression: float
    market_demand: float
    advantages: List[str] = field(default_factory=list)
    skills_to_learn: List[str] = field(default_factory=list)
    transfer_difficulty: str = "medium"


class EnhancedJobGraphService:
    """
    增强版岗位图谱服务
    提供更精准的换岗匹配分析
    """
    
    def __init__(self):
        self.skill_categories = {
            "programming": [
                "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C#",
                "Ruby", "PHP", "Swift", "Kotlin", "Rust", "Scala", "R",
            ],
            "frontend": [
                "React", "Vue", "Angular", "HTML", "CSS", "Sass", "Less",
                "Webpack", "Vite", "Next.js", "Nuxt.js", "Three.js",
            ],
            "backend": [
                "Spring", "SpringBoot", "Django", "Flask", "FastAPI", "Express",
                "Node.js", "Gin", "Echo", "Nest.js", "Koa",
            ],
            "database": [
                "MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle", "SQL Server",
                "Elasticsearch", "Cassandra", "DynamoDB", "SQLite",
            ],
            "devops": [
                "Docker", "Kubernetes", "Jenkins", "Git", "Linux", "Nginx",
                "Ansible", "Terraform", "CI/CD", "Prometheus", "Grafana",
            ],
            "ai_ml": [
                "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas",
                "NumPy", "OpenCV", "NLP", "深度学习", "机器学习",
            ],
            "cloud": [
                "AWS", "Azure", "GCP", "阿里云", "腾讯云", "华为云",
                "云原生", "微服务", "Serverless",
            ],
            "soft": [
                "沟通能力", "团队协作", "项目管理", "领导力", "创新思维",
                "问题解决", "学习能力", "抗压能力",
            ],
        }
        
        self.skill_similarities = self._build_skill_similarity_matrix()
        
        self.industry_clusters = {
            "互联网技术": [
                "前端开发工程师", "后端开发工程师", "全栈工程师",
                "移动开发工程师", "测试工程师", "运维工程师",
                "架构师", "技术经理", "技术总监",
            ],
            "数据智能": [
                "数据分析师", "数据工程师", "算法工程师",
                "机器学习工程师", "数据科学家", "AI工程师",
            ],
            "产品运营": [
                "产品经理", "产品运营", "用户运营", "内容运营",
                "增长运营", "运营经理", "运营总监",
            ],
            "设计创意": [
                "UI设计师", "UX设计师", "交互设计师", "视觉设计师",
                "产品设计师", "设计总监",
            ],
            "职能支持": [
                "人力资源", "财务专员", "行政助理", "法务专员",
                "HRBP", "招聘专员", "培训专员",
            ],
        }
        
        self.career_levels = {
            "初级": 1,
            "中级": 2,
            "高级": 3,
            "资深": 4,
            "专家": 5,
            "经理": 4,
            "总监": 5,
            "VP": 6,
        }
        
        self.transfer_difficulty_matrix = {
            ("互联网技术", "互联网技术"): "easy",
            ("互联网技术", "数据智能"): "medium",
            ("互联网技术", "产品运营"): "medium",
            ("数据智能", "互联网技术"): "medium",
            ("数据智能", "数据智能"): "easy",
            ("产品运营", "产品运营"): "easy",
            ("产品运营", "互联网技术"): "hard",
            ("职能支持", "互联网技术"): "hard",
            ("职能支持", "职能支持"): "easy",
        }

    def _build_skill_similarity_matrix(self) -> Dict[Tuple[str, str], float]:
        """构建技能相似度矩阵"""
        similarities = {}
        
        skill_groups = [
            ("Python", ["Python", "python", "py"]),
            ("Java", ["Java", "java", "JDK"]),
            ("JavaScript", ["JavaScript", "JS", "javascript", "ES6", "ES7"]),
            ("TypeScript", ["TypeScript", "TS", "typescript"]),
            ("React", ["React", "React.js", "ReactJS", "react"]),
            ("Vue", ["Vue", "Vue.js", "VueJS", "vue"]),
            ("Node.js", ["Node.js", "Node", "nodejs", "Express"]),
            ("MySQL", ["MySQL", "mysql", "MariaDB"]),
            ("Redis", ["Redis", "redis", "缓存"]),
            ("Docker", ["Docker", "docker", "容器", "Container"]),
            ("Kubernetes", ["Kubernetes", "K8s", "k8s"]),
            ("Git", ["Git", "git", "GitHub", "GitLab"]),
            ("Linux", ["Linux", "linux", "Ubuntu", "CentOS"]),
            ("TensorFlow", ["TensorFlow", "TF", "tensorflow"]),
            ("PyTorch", ["PyTorch", "pytorch", "torch"]),
        ]
        
        for group in skill_groups:
            primary, aliases = group
            for alias in aliases:
                similarities[(primary.lower(), alias.lower())] = 1.0
                similarities[(alias.lower(), primary.lower())] = 1.0
        
        related_skills = [
            ("react", "vue", 0.7),
            ("react", "angular", 0.6),
            ("python", "java", 0.5),
            ("python", "go", 0.5),
            ("mysql", "postgresql", 0.85),
            ("mysql", "mongodb", 0.6),
            ("docker", "kubernetes", 0.75),
            ("tensorflow", "pytorch", 0.8),
            ("spring", "springboot", 0.9),
            ("django", "flask", 0.7),
            ("django", "fastapi", 0.7),
        ]
        
        for skill_a, skill_b, sim in related_skills:
            similarities[(skill_a, skill_b)] = sim
            similarities[(skill_b, skill_a)] = sim
        
        return similarities

    def get_skill_similarity(self, skill_a: str, skill_b: str) -> float:
        """获取两个技能的相似度"""
        a_lower = skill_a.lower()
        b_lower = skill_b.lower()
        
        if a_lower == b_lower:
            return 1.0
        
        direct = self.skill_similarities.get((a_lower, b_lower), 0)
        if direct > 0:
            return direct
        
        if a_lower in b_lower or b_lower in a_lower:
            return 0.8
        
        return 0.0

    def calculate_skill_overlap(
        self, 
        source_skills: List[str], 
        target_skills: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """
        计算技能重叠度
        返回: (重叠度, 匹配技能, 需学习技能)
        """
        if not target_skills:
            return 1.0, source_skills, []
        
        matched = []
        to_learn = []
        
        for target_skill in target_skills:
            best_match = 0
            for source_skill in source_skills:
                sim = self.get_skill_similarity(source_skill, target_skill)
                if sim > best_match:
                    best_match = sim
            
            if best_match >= 0.7:
                matched.append(target_skill)
            else:
                to_learn.append(target_skill)
        
        overlap_ratio = len(matched) / len(target_skills) if target_skills else 1.0
        
        return overlap_ratio, matched, to_learn

    def get_industry_for_job(self, job_name: str) -> str:
        """获取岗位所属行业"""
        for industry, jobs in self.industry_clusters.items():
            for job in jobs:
                if job in job_name or job_name in job:
                    return industry
        return "互联网技术"

    def calculate_industry_similarity(
        self, 
        source_job: str, 
        target_job: str
    ) -> float:
        """计算行业相似度"""
        source_industry = self.get_industry_for_job(source_job)
        target_industry = self.get_industry_for_job(target_job)
        
        if source_industry == target_industry:
            return 1.0
        
        cross_industry_similarity = {
            ("互联网技术", "数据智能"): 0.8,
            ("互联网技术", "产品运营"): 0.6,
            ("数据智能", "产品运营"): 0.5,
            ("互联网技术", "设计创意"): 0.5,
            ("产品运营", "设计创意"): 0.7,
        }
        
        key = (source_industry, target_industry)
        reverse_key = (target_industry, source_industry)
        
        return cross_industry_similarity.get(key, cross_industry_similarity.get(reverse_key, 0.3))

    def calculate_career_progression(
        self, 
        source_job: str, 
        target_job: str
    ) -> float:
        """计算职业发展连贯性"""
        source_level = self._extract_job_level(source_job)
        target_level = self._extract_job_level(target_job)
        
        level_diff = target_level - source_level
        
        if level_diff == 0:
            return 1.0
        elif level_diff == 1:
            return 0.9
        elif level_diff == -1:
            return 0.7
        elif level_diff == 2:
            return 0.6
        elif level_diff == -2:
            return 0.4
        else:
            return 0.3

    def _extract_job_level(self, job_name: str) -> int:
        """提取岗位级别"""
        for level_name, level_value in self.career_levels.items():
            if level_name in job_name:
                return level_value
        return 2

    def calculate_transfer_match(
        self,
        source_job: str,
        target_job: str,
        source_skills: List[str],
        target_skills: List[str],
        market_demand: float = 0.5,
    ) -> JobMatchResult:
        """
        计算换岗匹配度
        综合考虑：技能重叠、行业相似、职业发展、市场需求
        """
        skill_overlap, matched_skills, to_learn = self.calculate_skill_overlap(
            source_skills, target_skills
        )
        
        industry_sim = self.calculate_industry_similarity(source_job, target_job)
        
        career_prog = self.calculate_career_progression(source_job, target_job)
        
        weights = {
            "skill": 0.30,
            "industry": 0.30,
            "career": 0.25,
            "market": 0.15,
        }
        
        skill_overlap_adjusted = skill_overlap
        if skill_overlap < 0.5 and industry_sim >= 0.8:
            skill_overlap_adjusted = skill_overlap + 0.2
        
        match_score = (
            skill_overlap_adjusted * weights["skill"] +
            industry_sim * weights["industry"] +
            career_prog * weights["career"] +
            market_demand * weights["market"]
        ) * 100
        
        if match_score >= 65:
            match_level = "高"
        elif match_score >= 50:
            match_level = "中"
        else:
            match_level = "低"
        
        source_industry = self.get_industry_for_job(source_job)
        target_industry = self.get_industry_for_job(target_job)
        difficulty = self.transfer_difficulty_matrix.get(
            (source_industry, target_industry),
            "medium"
        )
        
        advantages = self._generate_advantages(
            matched_skills, industry_sim, career_prog
        )
        
        return JobMatchResult(
            target_job=target_job,
            match_score=round(match_score, 1),
            match_level=match_level,
            skill_overlap=round(skill_overlap * 100, 1),
            industry_similarity=round(industry_sim * 100, 1),
            career_progression=round(career_prog * 100, 1),
            market_demand=round(market_demand * 100, 1),
            advantages=advantages,
            skills_to_learn=to_learn,
            transfer_difficulty=difficulty,
        )

    def _generate_advantages(
        self,
        matched_skills: List[str],
        industry_sim: float,
        career_prog: float
    ) -> List[str]:
        """生成迁移优势描述"""
        advantages = []
        
        if matched_skills:
            skill_str = "、".join(matched_skills[:3])
            advantages.append(f"技能复用度高：{skill_str}等技能可直接迁移")
        
        if industry_sim >= 0.8:
            advantages.append("行业背景契合，业务理解成本低")
        elif industry_sim >= 0.5:
            advantages.append("行业相关，有一定业务基础")
        
        if career_prog >= 0.9:
            advantages.append("职业发展连贯，晋升路径清晰")
        
        return advantages

    def suggest_transfer_paths(
        self,
        current_job: str,
        current_skills: List[str],
        limit: int = 5,
    ) -> List[JobMatchResult]:
        """
        智能推荐换岗路径
        基于当前岗位和技能，推荐最佳换岗选择
        """
        suggestions = []
        
        current_industry = self.get_industry_for_job(current_job)
        current_level = self._extract_job_level(current_job)
        
        candidate_jobs = []
        
        if current_industry in self.industry_clusters:
            candidate_jobs.extend(self.industry_clusters[current_industry])
        
        related_industries = self._get_related_industries(current_industry)
        for industry in related_industries:
            if industry in self.industry_clusters:
                candidate_jobs.extend(self.industry_clusters[industry][:3])
        
        seen = set()
        for target_job in candidate_jobs:
            if target_job == current_job or target_job in seen:
                continue
            seen.add(target_job)
            
            target_level = self._extract_job_level(target_job)
            if abs(target_level - current_level) > 2:
                continue
            
            target_skills = self._infer_job_skills(target_job)
            
            result = self.calculate_transfer_match(
                source_job=current_job,
                target_job=target_job,
                source_skills=current_skills,
                target_skills=target_skills,
            )
            
            suggestions.append(result)
        
        suggestions.sort(key=lambda x: x.match_score, reverse=True)
        
        return suggestions[:limit]

    def _get_related_industries(self, industry: str) -> List[str]:
        """获取相关行业"""
        relations = {
            "互联网技术": ["数据智能", "产品运营"],
            "数据智能": ["互联网技术", "产品运营"],
            "产品运营": ["互联网技术", "设计创意"],
            "设计创意": ["产品运营", "互联网技术"],
            "职能支持": ["产品运营"],
        }
        return relations.get(industry, [])

    def _infer_job_skills(self, job_name: str) -> List[str]:
        """推断岗位所需技能"""
        skill_mapping = {
            "前端开发工程师": ["JavaScript", "HTML", "CSS", "React", "Vue"],
            "后端开发工程师": ["Python", "Java", "MySQL", "Redis", "Docker"],
            "全栈工程师": ["JavaScript", "Python", "React", "Node.js", "MySQL"],
            "数据分析师": ["Python", "SQL", "Excel", "Tableau", "统计学"],
            "算法工程师": ["Python", "机器学习", "TensorFlow", "PyTorch"],
            "产品经理": ["需求分析", "原型设计", "数据分析", "项目管理"],
            "测试工程师": ["Python", "自动化测试", "Selenium", "JMeter"],
            "运维工程师": ["Linux", "Docker", "Kubernetes", "Nginx"],
        }
        
        for key, skills in skill_mapping.items():
            if key in job_name:
                return skills
        
        return ["Python", "沟通能力", "团队协作"]


enhanced_job_graph = EnhancedJobGraphService()
