# -*- coding: utf-8 -*-
"""
扩展岗位技能需求库
基于真实招聘数据分析，构建完整的岗位技能需求映射
"""

from typing import Dict, List, Set, Any
from dataclasses import dataclass, field


@dataclass
class JobSkillRequirement:
    """岗位技能需求"""
    job_title: str
    required_skills: List[str]
    preferred_skills: List[str] = field(default_factory=list)
    skill_weights: Dict[str, float] = field(default_factory=dict)
    experience_range: tuple = (0, 0)
    education_level: str = "本科"
    certifications: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    industry: str = ""
    salary_range: tuple = (0, 0)


EXTENDED_JOB_SKILLS_DB: Dict[str, JobSkillRequirement] = {
    "Java开发工程师": JobSkillRequirement(
        job_title="Java开发工程师",
        required_skills=["Java", "Spring", "MySQL", "Redis"],
        preferred_skills=["SpringBoot", "MyBatis", "Docker", "Kubernetes", "消息队列"],
        skill_weights={"Java": 1.0, "Spring": 0.9, "MySQL": 0.8, "Redis": 0.7},
        experience_range=(1, 5),
        education_level="本科",
        certifications=["Java认证"],
        soft_skills=["团队协作", "问题解决", "沟通能力"],
        industry="互联网",
        salary_range=(10, 25),
    ),
    "Java后端开发": JobSkillRequirement(
        job_title="Java后端开发",
        required_skills=["Java", "SpringBoot", "MySQL", "Redis"],
        preferred_skills=["微服务", "分布式", "Docker", "Kubernetes"],
        skill_weights={"Java": 1.0, "SpringBoot": 0.9, "MySQL": 0.8},
        experience_range=(2, 6),
        education_level="本科",
        soft_skills=["系统设计", "团队协作"],
        industry="互联网",
        salary_range=(15, 30),
    ),
    "前端开发工程师": JobSkillRequirement(
        job_title="前端开发工程师",
        required_skills=["JavaScript", "Vue", "CSS", "HTML"],
        preferred_skills=["React", "TypeScript", "Webpack", "Node.js"],
        skill_weights={"JavaScript": 1.0, "Vue": 0.9, "CSS": 0.7, "HTML": 0.6},
        experience_range=(1, 4),
        education_level="本科",
        soft_skills=["用户体验", "细节关注"],
        industry="互联网",
        salary_range=(10, 22),
    ),
    "Vue前端开发": JobSkillRequirement(
        job_title="Vue前端开发",
        required_skills=["Vue", "JavaScript", "CSS", "TypeScript"],
        preferred_skills=["Vue3", "Pinia", "Vite", "Node.js"],
        skill_weights={"Vue": 1.0, "JavaScript": 0.9, "TypeScript": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="互联网",
        salary_range=(12, 25),
    ),
    "React前端开发": JobSkillRequirement(
        job_title="React前端开发",
        required_skills=["React", "JavaScript", "TypeScript", "CSS"],
        preferred_skills=["Redux", "Next.js", "Webpack", "Node.js"],
        skill_weights={"React": 1.0, "JavaScript": 0.9, "TypeScript": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="互联网",
        salary_range=(12, 28),
    ),
    "Python开发工程师": JobSkillRequirement(
        job_title="Python开发工程师",
        required_skills=["Python", "Django", "PostgreSQL"],
        preferred_skills=["FastAPI", "Flask", "Redis", "Docker"],
        skill_weights={"Python": 1.0, "Django": 0.9, "PostgreSQL": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        soft_skills=["逻辑思维", "自学能力"],
        industry="互联网",
        salary_range=(12, 25),
    ),
    "Python后端开发": JobSkillRequirement(
        job_title="Python后端开发",
        required_skills=["Python", "FastAPI", "MySQL"],
        preferred_skills=["Django", "Redis", "Docker", "Kubernetes"],
        skill_weights={"Python": 1.0, "FastAPI": 0.9, "MySQL": 0.8},
        experience_range=(2, 6),
        education_level="本科",
        industry="互联网",
        salary_range=(15, 30),
    ),
    "数据分析师": JobSkillRequirement(
        job_title="数据分析师",
        required_skills=["Python", "SQL", "Pandas", "数据可视化"],
        preferred_skills=["机器学习", "Tableau", "Spark", "Hadoop"],
        skill_weights={"Python": 1.0, "SQL": 0.9, "Pandas": 0.8, "数据可视化": 0.7},
        experience_range=(1, 4),
        education_level="本科",
        certifications=["数据分析师认证"],
        soft_skills=["数据敏感", "逻辑分析"],
        industry="互联网",
        salary_range=(12, 25),
    ),
    "机器学习工程师": JobSkillRequirement(
        job_title="机器学习工程师",
        required_skills=["Python", "TensorFlow", "机器学习"],
        preferred_skills=["PyTorch", "深度学习", "NLP", "CV"],
        skill_weights={"Python": 1.0, "TensorFlow": 0.9, "机器学习": 0.9},
        experience_range=(2, 6),
        education_level="硕士",
        soft_skills=["算法思维", "数学基础"],
        industry="AI",
        salary_range=(20, 40),
    ),
    "全栈开发工程师": JobSkillRequirement(
        job_title="全栈开发工程师",
        required_skills=["Java", "JavaScript", "Vue", "MySQL"],
        preferred_skills=["React", "Node.js", "Docker", "Redis"],
        skill_weights={"Java": 0.9, "JavaScript": 0.9, "Vue": 0.8, "MySQL": 0.8},
        experience_range=(2, 6),
        education_level="本科",
        soft_skills=["全栈思维", "快速学习"],
        industry="互联网",
        salary_range=(18, 35),
    ),
    "大数据开发工程师": JobSkillRequirement(
        job_title="大数据开发工程师",
        required_skills=["Spark", "Hadoop", "Python"],
        preferred_skills=["Hive", "Kafka", "Flink", "Scala"],
        skill_weights={"Spark": 1.0, "Hadoop": 0.9, "Python": 0.8},
        experience_range=(2, 6),
        education_level="本科",
        industry="大数据",
        salary_range=(18, 35),
    ),
    "DevOps工程师": JobSkillRequirement(
        job_title="DevOps工程师",
        required_skills=["Docker", "Kubernetes", "Linux"],
        preferred_skills=["Jenkins", "Git", "Nginx", "云服务"],
        skill_weights={"Docker": 1.0, "Kubernetes": 0.9, "Linux": 0.8},
        experience_range=(2, 6),
        education_level="本科",
        soft_skills=["运维思维", "自动化意识"],
        industry="互联网",
        salary_range=(18, 35),
    ),
    "测试开发工程师": JobSkillRequirement(
        job_title="测试开发工程师",
        required_skills=["Python", "Selenium", "自动化测试"],
        preferred_skills=["Jenkins", "接口测试", "性能测试", "Docker"],
        skill_weights={"Python": 1.0, "Selenium": 0.9, "自动化测试": 0.9},
        experience_range=(1, 5),
        education_level="本科",
        soft_skills=["质量意识", "细节关注"],
        industry="互联网",
        salary_range=(12, 25),
    ),
    "移动端开发工程师": JobSkillRequirement(
        job_title="移动端开发工程师",
        required_skills=["Android", "Java", "Kotlin"],
        preferred_skills=["Flutter", "iOS", "React Native"],
        skill_weights={"Android": 1.0, "Java": 0.9, "Kotlin": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="移动互联网",
        salary_range=(12, 28),
    ),
    "iOS开发工程师": JobSkillRequirement(
        job_title="iOS开发工程师",
        required_skills=["iOS", "Swift", "Objective-C"],
        preferred_skills=["Flutter", "React Native", "Cocoa"],
        skill_weights={"iOS": 1.0, "Swift": 0.9, "Objective-C": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="移动互联网",
        salary_range=(15, 30),
    ),
    "产品经理": JobSkillRequirement(
        job_title="产品经理",
        required_skills=["产品设计", "需求分析", "用户研究"],
        preferred_skills=["数据分析", "Axure", "项目管理", "SQL"],
        skill_weights={"产品设计": 1.0, "需求分析": 0.9, "用户研究": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        soft_skills=["沟通能力", "逻辑思维", "用户同理心"],
        industry="互联网",
        salary_range=(15, 30),
    ),
    "UI设计师": JobSkillRequirement(
        job_title="UI设计师",
        required_skills=["UI设计", "Figma", "Photoshop"],
        preferred_skills=["Sketch", "交互设计", "前端基础"],
        skill_weights={"UI设计": 1.0, "Figma": 0.9, "Photoshop": 0.8},
        experience_range=(1, 4),
        education_level="本科",
        soft_skills=["审美能力", "用户体验"],
        industry="互联网",
        salary_range=(10, 22),
    ),
    "运维工程师": JobSkillRequirement(
        job_title="运维工程师",
        required_skills=["Linux", "Nginx", "Shell"],
        preferred_skills=["Docker", "Kubernetes", "监控", "Python"],
        skill_weights={"Linux": 1.0, "Nginx": 0.9, "Shell": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="互联网",
        salary_range=(10, 22),
    ),
    "C/C++开发工程师": JobSkillRequirement(
        job_title="C/C++开发工程师",
        required_skills=["C/C++", "数据结构", "算法"],
        preferred_skills=["Linux", "多线程", "网络编程", "Qt"],
        skill_weights={"C/C++": 1.0, "数据结构": 0.9, "算法": 0.8},
        experience_range=(1, 6),
        education_level="本科",
        soft_skills=["底层思维", "性能优化"],
        industry="互联网",
        salary_range=(15, 30),
    ),
    "Go开发工程师": JobSkillRequirement(
        job_title="Go开发工程师",
        required_skills=["Go", "微服务", "MySQL"],
        preferred_skills=["Docker", "Kubernetes", "gRPC", "Redis"],
        skill_weights={"Go": 1.0, "微服务": 0.9, "MySQL": 0.8},
        experience_range=(1, 5),
        education_level="本科",
        industry="互联网",
        salary_range=(18, 35),
    ),
}


def get_job_requirements(job_title: str) -> JobSkillRequirement:
    """获取岗位技能需求"""
    job_lower = job_title.lower()
    
    for title, req in EXTENDED_JOB_SKILLS_DB.items():
        if title.lower() == job_lower or job_lower in title.lower():
            return req
    
    return JobSkillRequirement(
        job_title=job_title,
        required_skills=[],
        preferred_skills=[],
    )


def get_all_job_titles() -> List[str]:
    """获取所有岗位名称"""
    return list(EXTENDED_JOB_SKILLS_DB.keys())


def search_jobs_by_skill(skill: str) -> List[str]:
    """根据技能搜索相关岗位"""
    skill_lower = skill.lower()
    matched_jobs = []
    
    for title, req in EXTENDED_JOB_SKILLS_DB.items():
        all_skills = req.required_skills + req.preferred_skills
        if any(skill_lower in s.lower() for s in all_skills):
            matched_jobs.append(title)
    
    return matched_jobs


def get_skill_importance(job_title: str, skill: str) -> float:
    """获取技能在岗位中的重要性权重"""
    req = get_job_requirements(job_title)
    skill_lower = skill.lower()
    
    for req_skill, weight in req.skill_weights.items():
        if skill_lower in req_skill.lower() or req_skill.lower() in skill_lower:
            return weight
    
    if skill_lower in [s.lower() for s in req.required_skills]:
        return 0.8
    if skill_lower in [s.lower() for s in req.preferred_skills]:
        return 0.5
    
    return 0.3
