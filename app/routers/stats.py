# -*- coding: utf-8 -*-
"""统计与画像子接口：user stats / skill_scores / competitiveness_history / score_detail。"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Depends

from app.services.career_graphrag_service import career_graphrag_service
from app.services.student_graph_service import student_graph_service
from app.routers._common import _report_store, _chat_store
from app.routers.auth import require_student_access

router = APIRouter(tags=["统计与画像"])


@router.get("/api/stats/user/{student_id}")
async def get_user_stats(student_id: str, user: dict = Depends(require_student_access)):
    """用户统计 - 字段对齐前端 UserStatsResponse"""
    node = student_graph_service.get_student(student_id)
    attrs = node.get("attributes", node) if node else {}

    matches = student_graph_service.get_student_matches(student_id)
    scores = [m.get("attributes", {}).get("total_match", 0) for m in matches]

    # 报告/会话数量：按 student_id 索引计数（无需全量载入内存）
    report_count = await _report_store.count_by_student(student_id)
    chat_count = await _chat_store.count_by_student(student_id)

    created_at = attrs.get("created_at", datetime.now().isoformat())

    # 技能学习进度：用图谱匹配的岗位技能作为目标
    skills = attrs.get("skills", [])
    skill_progress: Dict[str, Any] = {}
    if skills:
        all_jobs = career_graphrag_service.get_all_jobs()
        # 取前3个岗位的技能要求作为目标
        for job in all_jobs[:3]:
            portrait = career_graphrag_service.generate_job_portrait(job["title"])
            for req_skill in portrait.skills[:5]:
                if req_skill not in skill_progress:
                    current = 80 if req_skill in skills else 20
                    skill_progress[req_skill] = {"current": current, "target": 100}
                if len(skill_progress) >= 6:
                    break
            if len(skill_progress) >= 6:
                break

    return {
        "portrait_completeness": round(float(attrs.get("completeness_score", 0))),
        "match_count": len(matches),
        "report_count": report_count,
        "chat_session_count": chat_count,
        "last_active_at": created_at,
        "achievements": [],
        "activity_trend": [],
        "skill_progress": skill_progress,
        # 兼容旧字段
        "student_id": student_id,
        "completeness": round(float(attrs.get("completeness_score", 0))),
        "competitiveness": round(float(attrs.get("competitiveness_score", 0))),
        "avg_match_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_match": max(scores, default=0),
        "skills_count": len(skills),
    }


@router.get("/api/portrait/{student_id}/skill_scores")
async def get_skill_scores(student_id: str, user: dict = Depends(require_student_access)):
    """
    学生技能评分
    来源：学生画像技能列表 × YOUTU 图谱岗位技能要求对比
    """
    node = student_graph_service.get_student(student_id)
    if not node:
        raise HTTPException(status_code=404, detail="学生不存在")
    attrs = node.get("attributes", node)
    student_skills = set(str(s).lower() for s in attrs.get("skills", []))
    certs = set(attrs.get("certificates", []))

    # 从 YOUTU 图谱聚合所有岗位的技能要求频次
    skill_freq: Dict[str, int] = {}
    all_jobs = career_graphrag_service.get_all_jobs()
    for job in all_jobs:
        portrait = career_graphrag_service.generate_job_portrait(job["title"])
        for sk in portrait.skills:
            skill_freq[sk] = skill_freq.get(sk, 0) + 1

    # 计算学生已掌握技能的得分（频次越高 = 越通用 = 越有价值）
    skills_out = []
    for sk in attrs.get("skills", []):
        freq = skill_freq.get(sk, 0)
        score = min(100, 50 + freq * 5)  # 基础50分 + 图谱热度加成
        level = "精通" if score >= 85 else "熟练" if score >= 65 else "了解"
        skills_out.append({
            "name": sk,
            "score": score,
            "level": level,
            "category": "技术技能",
            "certified": sk in certs,
            "evidence": [f"图谱中 {freq} 个岗位要求此技能"],
            "learning_progress": min(100, score + 10),
        })

    # 软技能：直接从学生七维属性映射
    dim_map = {
        "innovation": ("创新能力", "innovation"),
        "learning": ("学习能力", "learning"),
        "stress_resistance": ("抗压能力", "stress_resistance"),
        "communication": ("沟通能力", "communication"),
        "internship": ("实习经历", "internship"),
    }
    level_score = {"优秀": 90, "良好": 75, "一般": 55}
    soft_skills_out = []
    for dim_key, (dim_label, attr_key) in dim_map.items():
        level = attrs.get(attr_key, "一般")
        score = level_score.get(level, 55)
        soft_skills_out.append({
            "name": dim_label,
            "score": score,
            "evidence": f"简历评估结果：{level}",
            "improvement_suggestions": [] if level == "优秀" else [f"建议进一步提升{dim_label}"],
        })

    return {"skills": skills_out, "soft_skills": soft_skills_out}


# 竞争力历史曲线已并入成长闭环：GET /api/progress/{student_id}（trend.competitiveness_curve，
# 基于真实画像快照）。原 /competitiveness_history 含硬编码同侪对比，已下线去冗余。


@router.get("/api/portrait/{student_id}/score_detail")
async def get_score_detail(student_id: str, user: dict = Depends(require_student_access)):
    """
    画像评分详情（competitiveness breakdown）
    来源：YOUTU 图谱岗位要求 × 学生画像七维度对比
    """
    node = student_graph_service.get_student(student_id)
    if not node:
        raise HTTPException(status_code=404, detail="学生不存在")
    attrs = node.get("attributes", node)

    level_score = {"优秀": 90, "良好": 75, "一般": 55}
    dims = {
        "技能匹配": min(100, len(attrs.get("skills", [])) * 8),
        "创新能力": level_score.get(attrs.get("innovation", "一般"), 55),
        "学习能力": level_score.get(attrs.get("learning", "一般"), 55),
        "抗压能力": level_score.get(attrs.get("stress_resistance", "一般"), 55),
        "沟通能力": level_score.get(attrs.get("communication", "一般"), 55),
        "实习经历": level_score.get(attrs.get("internship", "一般"), 55),
        "证书认证": min(100, len(attrs.get("certificates", [])) * 20 + 40),
    }
    overall = round(sum(dims.values()) / len(dims))
    return {"overall": overall, "dimensions": dims,
            "completeness": round(float(attrs.get("completeness_score", 0)))}
