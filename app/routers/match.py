# -*- coding: utf-8 -*-
"""人岗匹配路由：compute / history / recommend / batch。"""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Depends

from app.services.career_graphrag_service import career_graphrag_service
from app.services.student_graph_service import student_graph_service
from app.services import tenant_config_service
from app.routers._common import (
    MatchComputeRequest,
    _get_student_portrait_from_store,
    _match_result_to_frontend,
)
from app.routers.auth import get_current_user, require_student_access, assert_student_access

router = APIRouter(tags=["匹配"])


def _intent_fit(job_title, career_intent, interests, preferences):
    """
    意愿契合度（0-100，独立于 4 维能力匹配）：career_intent / interests / 期望行业 与岗位的契合。
    纯文本/关键词匹配，透明可解释；返回 (score, reasons)。
    """
    title = (job_title or "").lower()
    score, reasons = 0, []
    ci = (career_intent or "").strip()
    if ci:
        cil = ci.lower()
        if cil in title or title in cil or any(len(w) >= 2 and w in title for w in cil.replace("工程师", "").split()):
            score += 60
            reasons.append(f"与求职意愿「{ci}」相符")
    for it in (interests or []):
        itl = str(it).lower()
        if itl and (itl in title or any(len(w) >= 2 and w in title for w in itl.split())):
            score += 15
            reasons.append(f"契合兴趣「{it}」")
    for ind in ((preferences or {}).get("industries") or []):
        if str(ind).lower() in title:
            score += 15
            reasons.append(f"属期望行业「{ind}」")
    return min(score, 100), reasons[:2]


@router.post("/api/match/compute")
async def compute_match(req: MatchComputeRequest, user: dict = Depends(get_current_user)):
    """
    四维度人岗匹配
    1. 从 student_graph_service 取学生画像
    2. 从 YOUTU 图谱取岗位画像（七维度）
    3. 计算四维度匹配
    4. 保存匹配记录
    """
    assert_student_access(user, req.student_id)
    student = _get_student_portrait_from_store(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生画像不存在，请先上传简历")

    job = await asyncio.to_thread(career_graphrag_service.generate_job_portrait, req.job_name)
    if not job.title:
        raise HTTPException(status_code=404, detail=f"未找到岗位：{req.job_name}")

    # 有效权重：租户级覆盖 > 请求 preset > 红线默认；一票否决在 compute_match 内统一裁决
    weights = tenant_config_service.effective_match_weights(req.weight_preset)
    result = await asyncio.to_thread(
        career_graphrag_service.compute_match, student, job,
        save_to_graph=True, weights=weights,
    )
    return _match_result_to_frontend(result, req.job_name, weights=weights)


@router.get("/api/match/history/{student_id}")
async def get_match_history(student_id: str, user: dict = Depends(require_student_access)):
    """获取匹配历史"""
    records = student_graph_service.get_student_matches(student_id)
    return [
        {
            "job_title": r.get("job_name", ""),
            "overall_score": r.get("attributes", {}).get("total_match", 0),
            "created_at": r.get("attributes", {}).get("created_at", ""),
        }
        for r in records
    ]


@router.get("/api/match/recommend/{student_id}")
async def recommend_jobs(student_id: str, top_k: int = Query(5, ge=1, le=20),
                         user: dict = Depends(require_student_access)):
    """
    岗位推荐：能力 × 意愿 双轴（赛题3b"结合个人意愿定目标"）。
    能力轴 = 技能重叠（不变）；意愿轴 = career_intent/interests/期望行业 契合度（独立计算，
    不进 4 维匹配打分，守技术指标）。能力高但意愿低时显式做"抗从众"标注。
    """
    student = _get_student_portrait_from_store(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生画像不存在")

    # 原始画像取意愿字段
    node = student_graph_service.get_student(student_id) or {}
    attrs = node.get("attributes", {})
    interests = attrs.get("interests", [])
    preferences = attrs.get("job_preferences", {})

    # 能力轴 = 遍历全部岗位算 4 维综合分（复用既有引擎，打分逻辑不变；整体放线程池）
    # get_all_jobs 已按租户岗位库过滤；权重用租户有效权重（contextvar 经 to_thread 传播）
    def _rank():
        w = tenant_config_service.effective_match_weights()
        scored = []
        for j in career_graphrag_service.get_all_jobs():
            try:
                job = career_graphrag_service.generate_job_portrait(j["title"])
                if not job.title:
                    continue
                mr = career_graphrag_service.compute_match(student, job, save_to_graph=False, weights=w)
                scored.append((j["title"], round(mr.total_match, 1),
                               mr.details.get("matched_skills", [])[:5]))
            except Exception:
                continue
        return scored

    scored = await asyncio.to_thread(_rank)

    recommendations = []
    for title, ability, matched in scored:
        ifit, reasons = _intent_fit(title, student.career_intent, interests, preferences)
        rec = {
            "job_title": title,
            "score": ability,            # 能力轴（4 维综合分，逻辑不变）
            "intent_fit": ifit,          # 意愿轴（独立计算）
            "matched_skills": matched,
            "summary": f"能力匹配 {round(ability)}%" + (f" · 意愿契合 {ifit}%" if ifit else ""),
        }
        # 抗从众标注：能力高但意愿低
        if ability >= 65 and ifit < 40:
            rec["intent_note"] = "能力匹配高，但与你的求职意愿偏离——避免盲目跟风，先确认是否真的想做"
        elif ifit >= 60:
            rec["intent_note"] = "能力与意愿双高，重点推荐"
        elif reasons:
            rec["intent_note"] = "；".join(reasons)
        recommendations.append(rec)

    # 结合意愿微调排序（能力为主，意愿权重 0.2，不喧宾夺主）
    recommendations.sort(key=lambda r: r["score"] + r["intent_fit"] * 0.2, reverse=True)
    return {"recommendations": recommendations[:top_k]}


@router.post("/api/match/batch")
async def batch_match(body: Dict[str, Any], user: dict = Depends(get_current_user)):
    """
    批量人岗匹配
    顺序调用 compute_match，不引入外部依赖
    """
    student_id = body.get("student_id", "")
    job_names = body.get("job_names", [])
    assert_student_access(user, student_id)

    student = _get_student_portrait_from_store(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生画像不存在")

    def _do_batch():
        w = tenant_config_service.effective_match_weights()
        out = []
        for job_name in job_names[:10]:  # 最多10个，避免超时
            try:
                job = career_graphrag_service.generate_job_portrait(job_name)
                if job.title:
                    mr = career_graphrag_service.compute_match(student, job, save_to_graph=False, weights=w)
                    out.append(_match_result_to_frontend(mr, job_name, weights=w))
            except Exception:
                pass
        return out

    return await asyncio.to_thread(_do_batch)   # 重型批量匹配整体放线程池
