# -*- coding: utf-8 -*-
"""
CrewAI 工具集
提供 Agent 可用的外部工具
"""

from typing import Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

try:
    from crewai.tools import tool as _crewai_tool
    CREWAI_TOOLS_AVAILABLE = True
    def _tool(fn): return _crewai_tool(fn)
except ImportError:
    CREWAI_TOOLS_AVAILABLE = False
    def _tool(fn): return fn  # passthrough, no mock


def query_job_info(job_name: str) -> Dict[str, Any]:
    """
    查询岗位详细信息，包括技能要求、薪资范围、行业信息
    
    Args:
        job_name: 岗位名称
        
    Returns:
        包含岗位信息的字典
    """
    try:
        from app.graph.job_graph_repo import job_graph
        info = job_graph.get_job_info(job_name)
        if info:
            return {
                "success": True,
                "data": info,
                "message": f"成功获取岗位 {job_name} 的信息"
            }
        return {
            "success": False,
            "data": None,
            "message": f"未找到岗位 {job_name} 的信息"
        }
    except Exception as e:
        logger.error(f"查询岗位信息失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"查询失败: {str(e)}"
        }



def query_career_paths(job_name: str) -> Dict[str, Any]:
    """
    查询岗位的职业发展路径，包括晋升路径和转岗路径
    
    Args:
        job_name: 岗位名称
        
    Returns:
        包含职业发展路径的字典
    """
    try:
        from app.graph.job_graph_repo import job_graph
        paths = job_graph.get_all_paths(job_name)
        return {
            "success": True,
            "data": paths,
            "message": f"成功获取岗位 {job_name} 的职业发展路径"
        }
    except Exception as e:
        logger.error(f"查询职业路径失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"查询失败: {str(e)}"
        }



def query_valid_jobs() -> Dict[str, Any]:
    """
    获取所有有效岗位列表
    
    Returns:
        包含有效岗位列表的字典
    """
    try:
        from app.graph.job_graph_repo import job_graph
        jobs = job_graph.get_valid_jobs()
        return {
            "success": True,
            "data": jobs,
            "count": len(jobs) if jobs else 0,
            "message": "成功获取有效岗位列表"
        }
    except Exception as e:
        logger.error(f"查询有效岗位失败: {e}")
        return {
            "success": False,
            "data": [],
            "count": 0,
            "message": f"查询失败: {str(e)}"
        }



def search_jobs(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    搜索岗位，根据关键词匹配岗位名称和描述
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量限制
        
    Returns:
        包含搜索结果的字典
    """
    try:
        from app.graph.job_graph_repo import job_graph
        results = job_graph.search_jobs(query, limit)
        return {
            "success": True,
            "data": results,
            "count": len(results) if results else 0,
            "message": f"搜索 '{query}' 找到 {len(results) if results else 0} 个结果"
        }
    except Exception as e:
        logger.error(f"搜索岗位失败: {e}")
        return {
            "success": False,
            "data": [],
            "count": 0,
            "message": f"搜索失败: {str(e)}"
        }



def query_student_profile(student_id: str) -> Dict[str, Any]:
    """
    查询学生画像信息
    
    Args:
        student_id: 学生ID
        
    Returns:
        包含学生画像的字典
    """
    try:
        import asyncio
        from app.db import get_db_session, student_crud
        
        async def _get_profile():
            async with get_db_session() as session:
                student = await student_crud.get_by_student_id(session, student_id)
                if student:
                    return {
                        "student_id": student.student_id,
                        "basic_info": student.basic_info or {},
                        "education": student.education or [],
                        "skills": student.skills or [],
                        "internships": student.internships or [],
                        "projects": student.projects or [],
                        "certs": student.certs or [],
                        "awards": student.awards or [],
                        "career_intent": student.career_intent,
                        "completeness": student.completeness,
                        "competitiveness": student.competitiveness,
                        "competitiveness_level": student.competitiveness_level,
                    }
                return None
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_profile())
                profile = future.result()
        else:
            profile = loop.run_until_complete(_get_profile())
        
        if profile:
            return {
                "success": True,
                "data": profile,
                "message": f"成功获取学生 {student_id} 的画像"
            }
        return {
            "success": False,
            "data": None,
            "message": f"未找到学生 {student_id}"
        }
    except Exception as e:
        logger.error(f"查询学生画像失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"查询失败: {str(e)}"
        }



def query_market_trends(job_name: str, days: int = 30) -> Dict[str, Any]:
    """
    查询岗位的市场热度趋势
    
    Args:
        job_name: 岗位名称
        days: 查询天数
        
    Returns:
        包含市场趋势的字典
    """
    try:
        import asyncio
        from app.db import get_db_session
        from app.db.crud.job_trend_crud import job_trend_crud
        
        async def _get_trends():
            async with get_db_session() as session:
                snapshots = await job_trend_crud.get_by_job_code(
                    session, job_name, limit=days
                )
                return [
                    {
                        "date": str(s.snapshot_date),
                        "demand_index": s.demand_index,
                        "jd_count": s.jd_count,
                        "avg_salary": s.avg_salary,
                        "top_skills": s.top_skills or [],
                    }
                    for s in snapshots
                ]
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_trends())
                trends = future.result()
        else:
            trends = loop.run_until_complete(_get_trends())
        
        return {
            "success": True,
            "data": trends,
            "count": len(trends),
            "message": f"成功获取岗位 {job_name} 的市场趋势"
        }
    except Exception as e:
        logger.error(f"查询市场趋势失败: {e}")
        return {
            "success": False,
            "data": [],
            "count": 0,
            "message": f"查询失败: {str(e)}"
        }



def query_real_job_data(job_name: str, limit: int = 5) -> Dict[str, Any]:
    """
    获取岗位的真实市场数据（来自招聘网站）
    
    Args:
        job_name: 岗位名称
        limit: 返回样本数量限制
        
    Returns:
        包含真实招聘数据的字典
    """
    try:
        import asyncio
        from app.db import get_db_session
        from app.db.crud.job_real_crud import job_real_crud
        
        async def _get_real_data():
            async with get_db_session() as session:
                stats = await job_real_crud.get_stats_by_job_name(session, job_name)
                samples = await job_real_crud.get_samples(session, job_name, limit)
                return {
                    "stats": stats,
                    "samples": samples
                }
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_real_data())
                result = future.result()
        else:
            result = loop.run_until_complete(_get_real_data())
        
        return {
            "success": True,
            "data": result,
            "message": f"成功获取岗位 {job_name} 的真实市场数据"
        }
    except Exception as e:
        logger.error(f"查询真实市场数据失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"查询失败: {str(e)}"
        }



def get_learning_resources(skill: str) -> Dict[str, Any]:
    """
    获取技能学习资源推荐
    
    Args:
        skill: 技能名称
        
    Returns:
        包含学习资源的字典
    """
    resources_map = {
        "Python": {
            "official": "https://docs.python.org/zh-cn/3/",
            "courses": ["Python官方文档", "Real Python", "LeetCode Python练习"],
            "books": ["《Python编程：从入门到实践》", "《流畅的Python》"],
            "estimated_hours": 100,
        },
        "Java": {
            "official": "https://docs.oracle.com/javase/",
            "courses": ["Oracle官方教程", "LeetCode Java练习"],
            "books": ["《Effective Java》", "《Java核心技术》"],
            "estimated_hours": 120,
        },
        "JavaScript": {
            "official": "https://developer.mozilla.org/zh-CN/docs/Web/JavaScript",
            "courses": ["MDN Web Docs", "JavaScript.info"],
            "books": ["《JavaScript高级程序设计》", "《你不知道的JavaScript》"],
            "estimated_hours": 80,
        },
        "Vue": {
            "official": "https://cn.vuejs.org/",
            "courses": ["Vue官方教程", "Vue Mastery"],
            "books": ["《Vue.js设计与实现》"],
            "estimated_hours": 60,
        },
        "React": {
            "official": "https://react.dev/",
            "courses": ["React官方教程", "Egghead.io"],
            "books": ["《React设计模式与最佳实践》"],
            "estimated_hours": 70,
        },
        "MySQL": {
            "official": "https://dev.mysql.com/doc/",
            "courses": ["MySQL官方教程", "MySQL Tutorial"],
            "books": ["《高性能MySQL》", "《MySQL技术内幕》"],
            "estimated_hours": 50,
        },
        "Redis": {
            "official": "https://redis.io/documentation",
            "courses": ["Redis官方教程", "Redis University"],
            "books": ["《Redis设计与实现》"],
            "estimated_hours": 30,
        },
        "Docker": {
            "official": "https://docs.docker.com/",
            "courses": ["Docker官方教程", "Docker Mastery"],
            "books": ["《Docker技术入门与实战》"],
            "estimated_hours": 20,
        },
        "Kubernetes": {
            "official": "https://kubernetes.io/zh-cn/docs/",
            "courses": ["Kubernetes官方教程", "Kubernetes the Hard Way"],
            "books": ["《Kubernetes权威指南》"],
            "estimated_hours": 80,
        },
    }
    
    skill_lower = skill.lower()
    for key, resources in resources_map.items():
        if key.lower() == skill_lower:
            return {
                "success": True,
                "data": resources,
                "message": f"成功获取技能 {skill} 的学习资源"
            }
    
    return {
        "success": True,
        "data": {
            "official": f"搜索 {skill} 官方文档",
            "courses": ["在线课程平台搜索", "GitHub开源项目"],
            "books": [f"《{skill}相关书籍》"],
            "estimated_hours": 40,
        },
        "message": f"未找到预设资源，返回通用建议"
    }



def analyze_skill_gap(
    current_skills: List[str],
    required_skills: List[str]
) -> Dict[str, Any]:
    """
    分析技能差距
    
    Args:
        current_skills: 当前技能列表
        required_skills: 需要的技能列表
        
    Returns:
        包含技能差距分析的字典
    """
    current_set = set(s.lower() for s in current_skills)
    required_set = set(s.lower() for s in required_skills)
    
    matched = current_set & required_set
    gap = required_set - current_set
    
    match_ratio = len(matched) / len(required_set) if required_set else 0
    
    priority_gaps = []
    for skill in gap:
        priority = "high" if skill in ["python", "java", "javascript", "sql"] else "medium"
        priority_gaps.append({
            "skill": skill,
            "priority": priority,
            "resources": get_learning_resources(skill).get("data", {})
        })
    
    return {
        "success": True,
        "data": {
            "matched_skills": list(matched),
            "gap_skills": list(gap),
            "match_ratio": round(match_ratio * 100, 1),
            "priority_gaps": sorted(priority_gaps, key=lambda x: x["priority"]),
        },
        "message": f"匹配度: {round(match_ratio * 100, 1)}%，需要学习 {len(gap)} 项技能"
    }


ALL_TOOLS = [
    query_job_info,
    query_career_paths,
    query_valid_jobs,
    search_jobs,
    query_student_profile,
    query_market_trends,
    query_real_job_data,
    get_learning_resources,
    analyze_skill_gap,
]


def get_tools_by_agent(agent_type: str) -> List:
    """根据Agent类型获取工具集（仅在 crewai_tools 已安装时有效）"""
    if not CREWAI_TOOLS_AVAILABLE:
        return []

    tool_mapping = {
        "resume_analyzer": [
            query_student_profile,
        ],
        "job_matcher": [
            query_job_info,
            query_career_paths,
            query_valid_jobs,
            search_jobs,
            query_market_trends,
            query_real_job_data,
            analyze_skill_gap,
        ],
        "career_advisor": [
            query_job_info,
            query_career_paths,
            query_market_trends,
            get_learning_resources,
            analyze_skill_gap,
        ],
        "report_generator": [
            query_job_info,
            query_career_paths,
            get_learning_resources,
        ],
    }

    raw_fns = tool_mapping.get(agent_type, [])
    # crewai 1.12.2 要求 BaseTool 实例，用 @tool 装饰器包装原始函数
    return [_tool(fn) for fn in raw_fns]
