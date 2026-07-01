# -*- coding: utf-8 -*-
"""报告路由：generate / status / get / update / polish / undo / export / feedback_optimize。"""

import json
import uuid
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends

from app.services.youtu_retriever_service import youtu_retriever_service
from app.core.llm_service import llm_service
from app.routers._common import (
    _report_store,
    _report_to_frontend, _build_export_response, _generate_report_task,
    ReportUpdateRequest, PolishRequest, FeedbackOptimizeRequest,
)
from app.services.task_progress import task_store
from app.routers.auth import get_current_user, assert_student_access

router = APIRouter(tags=["报告"])


async def _load_owned_report(report_id: str, user: dict) -> dict:
    """加载报告并校验归属（跨租户已被存储层拦为 404；同租户再校验学生归属）。"""
    data = await _report_store.get(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="报告不存在")
    assert_student_access(user, data.get("student_id", ""))
    return data


@router.post("/api/report/generate")
async def generate_report(
    student_id: str = Query(...),
    job_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """
    生成职业报告（异步任务）
    前端 POST /api/report/generate?student_id=&job_name=
    返回 task_id，前端轮询 /api/report/status/{task_id}
    """
    assert_student_access(user, student_id)
    task_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())

    await task_store.create(
        task_id,
        report_id=report_id,
        status="pending",
        progress=0,
        student_id=student_id,
        job_name=job_name,
        created_at=datetime.now().isoformat(),
    )

    asyncio.ensure_future(_generate_report_task(task_id, report_id, student_id, job_name))

    return {
        "task_id": task_id,
        "report_id": report_id,
        "student_id": student_id,
        "job_name": job_name,
    }


@router.get("/api/report/status/{task_id}")
async def get_report_status(task_id: str, user: dict = Depends(get_current_user)):
    """轮询报告生成状态"""
    task = await task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    assert_student_access(user, task.get("student_id", ""))

    result = None
    if task["status"] == "completed":
        report_id = task.get("report_id", "")
        report_data = await _report_store.get(report_id)
        if report_data:
            result = _report_to_frontend(report_id, report_data)

    return {
        "status": task["status"],
        "progress": task.get("progress", 0),
        "message": {"pending": "等待中", "processing": "生成中", "completed": "已完成", "failed": "生成失败"}.get(task["status"], ""),
        "error_msg": task.get("error_msg"),
        "report_id": task.get("report_id"),
        "result": result,
    }


@router.get("/api/report/{report_id}")
async def get_report(report_id: str, user: dict = Depends(get_current_user)):
    """获取完整报告"""
    data = await _load_owned_report(report_id, user)
    return _report_to_frontend(report_id, data)


@router.put("/api/report/{report_id}")
async def update_report(report_id: str, req: ReportUpdateRequest,
                        user: dict = Depends(get_current_user)):
    """更新报告内容（真实写入 report_store）"""
    data = await _load_owned_report(report_id, user)

    if req.action_plan is not None:
        data.setdefault("phased_plan", {})["short_term"] = req.action_plan
    if req.skill_gaps is not None:
        mr = data.setdefault("match_result", {})
        mr.setdefault("details", {})["missing_skills"] = [g.get("skill", g) if isinstance(g, dict) else g for g in req.skill_gaps]
    if req.career_path is not None:
        data["career_paths"] = req.career_path
    if req.chapters_json is not None:
        data["chapters_json"] = req.chapters_json

    await _report_store.save(report_id, data)
    return {"success": True, "message": "报告已更新"}


@router.post("/api/report/{report_id}/polish")
async def polish_report(report_id: str, req: PolishRequest,
                        user: dict = Depends(get_current_user)):
    """LLM 润色报告章节（YOUTU 图谱上下文增强）"""
    data = await _load_owned_report(report_id, user)

    # 保存润色前快照
    data["snapshot"] = json.dumps(data.get("chapters_json", []), ensure_ascii=False)

    job_name = data.get("job_name", "")
    chapters = data.get("chapters_json", [])
    target = req.chapter_titles or [c["title"] for c in chapters]

    # YOUTU 检索图谱上下文
    youtu_ctx = await youtu_retriever_service.query(
        f"关于{job_name}岗位的职业发展建议和核心技能要求",
        top_k=8,
    )
    graph_context = youtu_ctx.get("answer", "")

    polished = []
    for ch in chapters:
        if ch["title"] in target:
            hint = req.feedback_hint or ""
            prompt = (
                f"请润色以下职业报告章节，使其更具体、可操作、专业。\n"
                f"图谱参考信息：{graph_context[:500]}\n"
                f"{'补充要求：' + hint if hint else ''}\n\n"
                f"章节标题：{ch['title']}\n"
                f"章节内容：\n{ch['content']}\n\n"
                f"请直接输出润色后的内容，不要加任何说明："
            )
            try:
                polished_content = await llm_service.chat(
                    [{"role": "user", "content": prompt}], temperature=0.4
                )
                polished.append({"title": ch["title"], "content": polished_content.strip()})
            except Exception:
                polished.append(ch)
        else:
            polished.append(ch)

    data["chapters_json"] = polished
    await _report_store.save(report_id, data)
    return {**_report_to_frontend(report_id, data), "snapshot_hash": report_id}


@router.post("/api/report/{report_id}/undo_polish")
async def undo_polish(report_id: str, user: dict = Depends(get_current_user)):
    """撤销润色，还原到润色前快照"""
    data = await _load_owned_report(report_id, user)

    if not data.get("snapshot"):
        return {"report_id": report_id, "undone": False, "message": "无可撤销的快照"}

    data["chapters_json"] = json.loads(data["snapshot"])
    data["snapshot"] = None
    await _report_store.save(report_id, data)
    return {"report_id": report_id, "undone": True, "message": "已还原到润色前"}


@router.get("/api/report/{report_id}/pdf")
async def export_report_pdf(report_id: str, user: dict = Depends(get_current_user)):
    """导出报告为 PDF"""
    await _load_owned_report(report_id, user)   # 归属校验（防越权下载他人报告）
    return await _build_export_response(report_id, "pdf")


@router.get("/api/report/{report_id}/word")
async def export_report_word(report_id: str, user: dict = Depends(get_current_user)):
    """导出报告为 Word"""
    await _load_owned_report(report_id, user)   # 归属校验
    return await _build_export_response(report_id, "word")


@router.post("/api/report/{report_id}/feedback_optimize")
async def feedback_optimize_report(report_id: str, req: FeedbackOptimizeRequest,
                                   user: dict = Depends(get_current_user)):
    """
    基于评分和问题清单优化报告（YOUTU 图谱 + LLM）
    """
    data = await _load_owned_report(report_id, user)

    job_name = data.get("job_name", "")
    chapters = data.get("chapters_json", [])
    focus = req.chapters if hasattr(req, "chapters") and req.chapters else [c["title"] for c in chapters]

    # 保存快照
    data["snapshot"] = json.dumps(chapters, ensure_ascii=False)

    issues_text = "、".join(req.issues) if req.issues else "无"
    youtu_ctx = await youtu_retriever_service.query(
        f"{job_name}岗位 {issues_text} 改进建议",
        top_k=6,
    )
    graph_context = youtu_ctx.get("answer", "")

    optimized = []
    for ch in chapters:
        if ch["title"] in focus:
            prompt = (
                f"用户对报告评分 {req.rating}/5，问题：{issues_text}，补充说明：{req.comment}。\n"
                f"图谱参考：{graph_context[:400]}\n\n"
                f"请优化以下章节，解决上述问题：\n章节：{ch['title']}\n{ch['content']}\n\n"
                f"输出优化后的内容："
            )
            try:
                new_content = await llm_service.chat(
                    [{"role": "user", "content": prompt}], temperature=0.4
                )
                optimized.append({"title": ch["title"], "content": new_content.strip()})
            except Exception:
                optimized.append(ch)
        else:
            optimized.append(ch)

    data["chapters_json"] = optimized
    await _report_store.save(report_id, data)
    return {
        "report_id": report_id,
        "optimized": True,
        "chapters_count": len(optimized),
        "chapters_json": optimized,
        "snapshot_saved": True,
    }


# 注：动态调整闭环（赛题3c）已并入成长闭环的可组合端点——
# 完成行动 POST /api/action/{sid}/item/{id}/complete、补技能 PUT /api/portrait/{sid}、
# 重新评估 POST /api/match/compute（save_to_graph=True 自动落快照）、看 delta GET /api/progress/{sid}。
# 原 /report/{id}/checkin 单体端点（与上述重复、且耦合 report_id）已下线去冗余。
