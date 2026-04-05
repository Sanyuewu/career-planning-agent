# -*- coding: utf-8 -*-
"""
市场趋势服务
提供行业趋势、热门技能等市场数据
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketService:
    """市场趋势服务"""
    
    INDUSTRY_TRENDS = [
        {
            "industry": "互联网/IT",
            "trend": "up",
            "job_count": 12580,
            "avg_salary": "18-35K",
            "growth": "+15%",
            "hot_skills": ["Python", "AI/ML", "云计算", "大数据", "前端开发"],
            "outlook": "持续增长"
        },
        {
            "industry": "金融科技",
            "trend": "up",
            "job_count": 8920,
            "avg_salary": "20-40K",
            "growth": "+22%",
            "hot_skills": ["区块链", "风控模型", "量化分析", "Python"],
            "outlook": "快速发展"
        },
        {
            "industry": "新能源",
            "trend": "up",
            "job_count": 6540,
            "avg_salary": "15-28K",
            "growth": "+35%",
            "hot_skills": ["电池技术", "智能驾驶", "储能系统", "电气工程"],
            "outlook": "爆发式增长"
        },
        {
            "industry": "医疗健康",
            "trend": "up",
            "job_count": 7890,
            "avg_salary": "15-30K",
            "growth": "+18%",
            "hot_skills": ["医疗AI", "生物信息", "临床试验", "数据分析"],
            "outlook": "稳定增长"
        },
        {
            "industry": "智能制造",
            "trend": "up",
            "job_count": 5620,
            "avg_salary": "12-25K",
            "growth": "+12%",
            "hot_skills": ["工业机器人", "PLC编程", "自动化控制", "数字孪生"],
            "outlook": "转型升级"
        },
        {
            "industry": "电子商务",
            "trend": "stable",
            "job_count": 9450,
            "avg_salary": "12-25K",
            "growth": "+5%",
            "hot_skills": ["运营", "数据分析", "直播带货", "供应链"],
            "outlook": "平稳发展"
        },
        {
            "industry": "教育培训",
            "trend": "down",
            "job_count": 3200,
            "avg_salary": "10-20K",
            "growth": "-15%",
            "hot_skills": ["在线教育", "课程设计", "教育科技"],
            "outlook": "行业调整"
        }
    ]
    
    async def get_industry_trends(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取行业趋势数据：优先从真实JD数据库计算，兜底静态专家数据
        """
        try:
            from app.db.crud.job_real_crud import job_real_crud
            from app.db.database import get_db_session
            async with get_db_session() as session:
                real_stats = await job_real_crud.get_industry_stats(session)
            if real_stats:
                trends = []
                for item in real_stats[:7]:
                    trends.append({
                        "industry": item["industry"],
                        "trend": "up",
                        "job_count": item["jd_count"],
                        "avg_salary": f"{int(item['avg_salary_k'])}K" if item["avg_salary_k"] else "面议",
                        "top_jobs": item["top_jobs"],
                        "data_source": "真实JD数据库",
                    })
                return {
                    "trends": trends,
                    "updated_at": datetime.utcnow().isoformat(),
                    "data_source": "真实JD数据库（9958条）",
                    "total_jd_count": sum(i["jd_count"] for i in real_stats),
                }
        except Exception as e:
            logger.warning("行业统计从DB获取失败，降级静态数据: %s", e)
        return {
            "trends": self.INDUSTRY_TRENDS,
            "updated_at": datetime.utcnow().isoformat(),
            "data_source": "专家静态数据（兜底）",
        }

    async def get_job_market_details(self, job_title: str) -> Dict[str, Any]:
        """
        获取岗位市场详情：从真实JD数据库计算薪资/规模/地区分布，兜底返回空壳
        """
        try:
            from app.db.crud.job_real_crud import job_real_crud
            from app.db.database import get_db_session
            async with get_db_session() as session:
                details = await job_real_crud.get_job_market_details(session, job_title)
            if details:
                return {
                    "salary_distribution": {"ranges": details.get("salary_distribution", [])},
                    "company_size": details.get("company_size", []),
                    "location_distribution": details.get("location_distribution", []),
                    "top_companies": details.get("top_companies", []),
                    "data_count": details.get("data_count", 0),
                    "data_source": details.get("data_source", ""),
                }
        except Exception as e:
            logger.warning("岗位市场详情DB查询失败: %s", e)
        return {"salary_distribution": {}, "company_size": [], "location_distribution": [], "data_source": "暂无数据"}
    
    async def get_learning_resources(self, student_id: str, skill_gaps: List[str] = None) -> Dict[str, Any]:
        """
        获取学习资源推荐
        
        Args:
            student_id: 学生ID
            skill_gaps: 技能差距列表
            
        Returns:
            学习资源推荐
        """
        resources = []
        
        default_gaps = skill_gaps or ["Python", "数据分析", "机器学习"]
        
        learning_resources_db = {
            "Python": [
                {
                    "title": "Python核心编程",
                    "type": "course",
                    "platform": "Coursera",
                    "url": "https://www.coursera.org/learn/python",
                    "duration": "40小时",
                    "rating": 4.8
                },
                {
                    "title": "Python数据分析实战",
                    "type": "book",
                    "platform": "O'Reilly",
                    "url": "https://www.oreilly.com/",
                    "duration": "30小时",
                    "rating": 4.7
                }
            ],
            "数据分析": [
                {
                    "title": "数据分析入门到精通",
                    "type": "course",
                    "platform": "Udemy",
                    "url": "https://www.udemy.com/",
                    "duration": "25小时",
                    "rating": 4.6
                }
            ],
            "机器学习": [
                {
                    "title": "机器学习实战",
                    "type": "course",
                    "platform": "Coursera",
                    "url": "https://www.coursera.org/learn/machine-learning",
                    "duration": "60小时",
                    "rating": 4.9
                }
            ]
        }
        
        for i, skill in enumerate(default_gaps[:3]):
            skill_resources = learning_resources_db.get(skill, [
                {
                    "title": f"{skill}入门教程",
                    "type": "course",
                    "platform": "Bilibili",
                    "url": "https://www.bilibili.com/",
                    "duration": "20小时",
                    "rating": 4.5
                }
            ])
            
            resources.append({
                "skill": skill,
                "priority": "high" if i == 0 else "medium" if i == 1 else "low",
                "estimated_hours": 40 - i * 10,
                "resources": skill_resources
            })
        
        return {
            "resources": resources
        }


    async def get_salary_comparison(self, job_name: str) -> Dict[str, Any]:
        """
        实时均薪 vs 历史均薪对比。
        live_avg_k: live_jobs 近 7 天活跃记录的均薪
        historical_avg_k: job_real 历史 JD 均薪
        change_pct: 涨跌百分比（保留 1 位小数）
        若 live_jobs 数量 < 10 条，返回 insufficient_data=True
        """
        from app.db.crud.job_real_crud import job_real_crud
        from app.db.database import get_db_session

        live_avg_k: float = 0.0
        live_count: int = 0
        historical_avg_k: float = 0.0
        historical_count: int = 0

        try:
            from app.db.crud.live_job_crud import LiveJobCRUD
            async with get_db_session() as session:
                stats_list = await LiveJobCRUD.stats(session, job_names=[job_name])
            if stats_list:
                row = stats_list[0]
                live_avg_k = row.get("avg_salary_k", 0.0) or 0.0
                live_count = row.get("jd_count", 0) or 0
        except Exception as e:
            logger.warning("[B-6] live_jobs 查询失败: %s", e)

        try:
            async with get_db_session() as session:
                hist = await job_real_crud.get_stats_by_job_name(session, job_name)
            if hist:
                historical_avg_k = hist.get("avg_salary_k", 0.0) or 0.0
                historical_count = hist.get("count", 0) or 0
        except Exception as e:
            logger.warning("[B-6] job_real 查询失败: %s", e)

        insufficient_data = live_count < 10

        change_pct: float = 0.0
        if not insufficient_data and historical_avg_k > 0 and live_avg_k > 0:
            change_pct = round((live_avg_k - historical_avg_k) / historical_avg_k * 100, 1)

        return {
            "job_name": job_name,
            "live_avg_k": round(live_avg_k, 1),
            "live_count": live_count,
            "historical_avg_k": round(historical_avg_k, 1),
            "historical_count": historical_count,
            "change_pct": change_pct,
            "insufficient_data": insufficient_data,
        }


market_service = MarketService()
