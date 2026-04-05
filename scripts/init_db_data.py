# -*- coding: utf-8 -*-
"""
D-1/D-2/D-3 数据初始化脚本
将静态 Python 数据迁移到 SQLite 数据库表中（幂等，可重复执行）

用法：
    python scripts/init_db_data.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("init_db_data")


# ---------- D-1: 技能库 ----------
async def init_skills(db):
    from app.db.models import SkillModel
    from app.data.job_skills_extended import EXTENDED_JOB_SKILLS_DB
    from app.services.match_service_optimized import OptimizedSkillMatcher
    from sqlalchemy import select

    matcher = OptimizedSkillMatcher()

    # 收集所有技能并分类
    all_skills: dict = {}   # name → {aliases, category, parent_skill, popularity}
    for job_title, jr in EXTENDED_JOB_SKILLS_DB.items():
        for skill in jr.required_skills:
            clean, _ = matcher.clean_skill_name(skill)
            if clean not in all_skills:
                cat = matcher.get_skill_category(clean)
                all_skills[clean] = {
                    "name": skill,
                    "category": cat,
                    "popularity": 0,
                    "aliases": [],
                    "parent_skill": None,
                }
            all_skills[clean]["popularity"] += 2   # 必要技能热度 +2
        for skill in jr.preferred_skills:
            clean, _ = matcher.clean_skill_name(skill)
            if clean not in all_skills:
                cat = matcher.get_skill_category(clean)
                all_skills[clean] = {
                    "name": skill,
                    "category": cat,
                    "popularity": 0,
                    "aliases": [],
                    "parent_skill": None,
                }
            all_skills[clean]["popularity"] += 1

    # 同义词关系
    ALIAS_MAP = {
        "springboot": ("Spring", ["SpringBoot", "Spring Boot"]),
        "vue":        ("Vue",    ["Vue.js", "Vue3", "Vue2"]),
        "react":      ("React",  ["React.js", "ReactJS"]),
        "nodejs":     ("Node.js", ["NodeJS", "Node"]),
        "pytorch":    ("PyTorch", ["Torch"]),
        "tensorflow": ("TensorFlow", ["TF", "tf2"]),
        "postgresql": ("PostgreSQL", ["Postgres", "PG"]),
        "mongodb":    ("MongoDB", ["Mongo"]),
        "elasticsearch": ("Elasticsearch", ["ES", "ElasticSearch"]),
        "kubernetes": ("Kubernetes", ["K8s", "k8s"]),
        "docker":     ("Docker", ["容器化"]),
        "typescript": ("TypeScript", ["TS", "ts"]),
        "javascript": ("JavaScript", ["JS", "js", "ES6"]),
        "python":     ("Python", ["Python3", "Python2", "py"]),
        "java":       ("Java", ["Java8", "Java11", "Java17"]),
        "golang":     ("Go", ["Golang", "go语言"]),
        "mysql":      ("MySQL", ["MySQL5", "MySQL8"]),
        "redis":      ("Redis", ["缓存"]),
    }
    for clean_key, (canonical, aliases) in ALIAS_MAP.items():
        if clean_key in all_skills:
            all_skills[clean_key]["name"] = canonical
            all_skills[clean_key]["aliases"] = aliases

    # 父技能关系
    PARENT_MAP = {
        "springboot": "Java", "spring": "Java", "mybatis": "Java",
        "vue3": "Vue", "nuxt": "Vue",
        "react native": "React", "next": "React",
        "pytorch": "Python", "tensorflow": "Python", "numpy": "Python",
        "pandas": "Python", "fastapi": "Python", "django": "Python",
        "postgresql": "SQL", "mysql": "SQL", "sqlite": "SQL",
    }
    for clean_key, parent in PARENT_MAP.items():
        if clean_key in all_skills:
            all_skills[clean_key]["parent_skill"] = parent

    # 写入数据库（upsert：已存在则更新热度，不存在则插入）
    inserted, updated = 0, 0
    for clean_key, info in all_skills.items():
        existing = (await db.execute(
            select(SkillModel).where(SkillModel.name == info["name"])
        )).scalar_one_or_none()
        if existing:
            existing.popularity = max(existing.popularity, info["popularity"])
            existing.aliases = info["aliases"] or existing.aliases
            existing.category = info["category"] or existing.category
            updated += 1
        else:
            db.add(SkillModel(
                name=info["name"],
                aliases=info["aliases"],
                category=info["category"],
                parent_skill=info["parent_skill"],
                popularity=min(info["popularity"] * 5, 100),
            ))
            inserted += 1

    await db.commit()
    logger.info("D-1 技能库: 新增 %d 条，更新 %d 条（共 %d 条）", inserted, updated, inserted + updated)


# ---------- D-2: 学习资源库 ----------
async def init_learning_resources(db):
    from app.db.models import LearningResourceModel
    from app.constants import SKILL_SUGGESTIONS
    from sqlalchemy import select

    # 基于 SKILL_SUGGESTIONS 生成学习资源记录
    RESOURCES = [
        # (skill, type, title, url, hours, difficulty)
        ("Python",       "课程", "Python官方教程",           "https://docs.python.org/zh-cn/3/tutorial/", 40, "入门"),
        ("Python",       "课程", "廖雪峰Python教程",          "https://www.liaoxuefeng.com/wiki/1016959663602400", 30, "入门"),
        ("Java",         "课程", "Java官方文档",              "https://docs.oracle.com/en/java/", 60, "中级"),
        ("Java",         "书籍", "《Effective Java》",        "", 40, "高级"),
        ("JavaScript",   "课程", "MDN Web文档",               "https://developer.mozilla.org/zh-CN/docs/Web/JavaScript", 50, "入门"),
        ("TypeScript",   "文档", "TypeScript官方手册",         "https://www.typescriptlang.org/docs/", 20, "中级"),
        ("Vue",          "文档", "Vue3官方文档",              "https://cn.vuejs.org/guide/introduction.html", 25, "入门"),
        ("React",        "文档", "React官方文档",             "https://react.dev/learn", 25, "入门"),
        ("MySQL",        "课程", "MySQL官方教程",             "https://dev.mysql.com/doc/", 30, "入门"),
        ("MySQL",        "课程", "数据库45讲（极客时间）",     "", 20, "中级"),
        ("Redis",        "书籍", "《Redis设计与实现》",        "", 30, "中级"),
        ("Docker",       "文档", "Docker官方文档",            "https://docs.docker.com/get-started/", 15, "入门"),
        ("Kubernetes",   "文档", "K8s官方教程",               "https://kubernetes.io/zh-cn/docs/tutorials/", 40, "中级"),
        ("Git",          "文档", "Pro Git在线书籍",           "https://git-scm.com/book/zh/v2", 10, "入门"),
        ("PyTorch",      "课程", "PyTorch官方教程",           "https://pytorch.org/tutorials/", 50, "中级"),
        ("PyTorch",      "课程", "动手学深度学习",             "https://zh.d2l.ai/", 80, "高级"),
        ("TensorFlow",   "课程", "TensorFlow官方入门",        "https://www.tensorflow.org/tutorials?hl=zh-cn", 40, "中级"),
        ("Spring",       "文档", "Spring Framework文档",      "https://spring.io/projects/spring-framework", 50, "中级"),
        ("Go",           "文档", "Go官方入门指南",             "https://go.dev/tour/welcome/1", 20, "入门"),
        ("Linux",        "课程", "鸟哥的Linux私房菜",          "", 60, "入门"),
        ("算法",         "书籍", "《算法导论》",               "", 100, "高级"),
        ("算法",         "练习", "LeetCode刷题（Hot 100）",   "https://leetcode.cn/studyplan/top-100-liked/", 60, "中级"),
        ("数据结构",     "书籍", "《大话数据结构》",            "", 30, "入门"),
        ("机器学习",     "课程", "吴恩达机器学习课程",          "https://www.coursera.org/learn/machine-learning", 50, "中级"),
        ("深度学习",     "课程", "CS231n斯坦福计算机视觉",      "http://cs231n.stanford.edu/", 80, "高级"),
        ("SQL",          "练习", "牛客网SQL练习",              "https://www.nowcoder.com/exam/oj?page=1&tab=SQL篇&topicId=199", 15, "入门"),
        ("网络",         "书籍", "《计算机网络：自顶向下方法》",  "", 50, "中级"),
        ("操作系统",     "课程", "MIT 6.828实验",             "https://pdos.csail.mit.edu/6.828/2020/", 80, "高级"),
        ("Flutter",      "文档", "Flutter官方文档",            "https://docs.flutter.dev/get-started", 30, "入门"),
        ("Kotlin",       "文档", "Kotlin官方文档",             "https://kotlinlang.org/docs/home.html", 25, "入门"),
        ("Rust",         "书籍", "《The Rust Programming Language》", "https://doc.rust-lang.org/book/", 60, "高级"),
        ("Swift",        "文档", "Apple官方Swift教程",         "https://developer.apple.com/swift/resources/", 40, "入门"),
        ("C++",          "书籍", "《C++ Primer》",             "", 80, "中级"),
        ("设计模式",     "书籍", "《设计模式：可复用面向对象软件的基础》", "", 40, "高级"),
        ("微服务",       "书籍", "《微服务设计》",              "", 30, "高级"),
    ]

    inserted, skipped = 0, 0
    for skill, rtype, title, url, hours, diff in RESOURCES:
        existing = (await db.execute(
            select(LearningResourceModel).where(
                LearningResourceModel.skill == skill,
                LearningResourceModel.title == title,
            )
        )).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        db.add(LearningResourceModel(
            skill=skill,
            resource_type=rtype,
            title=title,
            url=url,
            estimated_hours=hours,
            difficulty=diff,
        ))
        inserted += 1

    await db.commit()
    logger.info("D-2 学习资源: 新增 %d 条，跳过 %d 条（已存在）", inserted, skipped)


# ---------- D-3: 行业洞察 ----------
async def init_industry_insights(db):
    from app.db.models import IndustryInsightModel
    from app.data.industry_insights import INDUSTRY_INSIGHTS
    from sqlalchemy import select
    import re

    inserted, updated = 0, 0
    for industry, data in INDUSTRY_INSIGHTS.items():
        # 从文本提取平均薪资数字（如 "15-50K" → 32.5）
        avg_k = 0.0
        salary_raw = data.get("salary_range", "")
        nums = re.findall(r'\d+', salary_raw)
        if nums:
            vals = [float(n) for n in nums[:2] if float(n) < 200]
            avg_k = sum(vals) / len(vals) if vals else 0.0

        existing = (await db.execute(
            select(IndustryInsightModel).where(IndustryInsightModel.industry == industry)
        )).scalar_one_or_none()

        if existing:
            existing.growth_rate = data.get("growth_rate", "")
            existing.hot_skills = data.get("hot_skills", [])
            existing.hiring_seasons = data.get("hiring_seasons", "").split(" / ") if isinstance(data.get("hiring_seasons"), str) else []
            existing.competitive_ratio = data.get("competitive_ratio", "")
            existing.avg_salary_k = avg_k
            updated += 1
        else:
            seasons_raw = data.get("hiring_seasons", "")
            seasons = seasons_raw.split(" / ") if isinstance(seasons_raw, str) else []
            db.add(IndustryInsightModel(
                industry=industry,
                growth_rate=data.get("growth_rate", ""),
                hot_skills=data.get("hot_skills", []),
                hiring_seasons=seasons,
                competitive_ratio=data.get("competitive_ratio", ""),
                avg_salary_k=avg_k,
            ))
            inserted += 1

    await db.commit()
    logger.info("D-3 行业洞察: 新增 %d 条，更新 %d 条（共 %d 条）", inserted, updated, inserted + updated)


# ---------- 主入口 ----------
async def main():
    from app.db.database import init_db, get_db_session

    logger.info("初始化数据库表结构...")
    await init_db()

    async with get_db_session() as db:
        logger.info("=== D-1: 初始化技能库 ===")
        await init_skills(db)

        logger.info("=== D-2: 初始化学习资源库 ===")
        await init_learning_resources(db)

        logger.info("=== D-3: 初始化行业洞察 ===")
        await init_industry_insights(db)

    logger.info("✅ 数据初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
