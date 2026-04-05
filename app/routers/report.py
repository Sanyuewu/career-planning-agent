# -*- coding: utf-8 -*-
"""报告路由：/api/report/*"""
import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import FileResponse

from app.db import get_db_session, student_crud, match_result_crud, report_crud
from app.deps import get_current_user, audit_log
from app.graph.job_graph_repo import job_graph
from app.rate_limit import limiter
from app.schemas.api import ReportUpdateRequest, ReportAdjustRequest, PolishRequest, FeedbackOptimizeRequest
from app.services.match_service import match_service
from app.services.portrait_service import StudentPortrait
from app.services.report_export_service import report_export_service
from app.services.report_service import report_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/report", tags=["Report"])


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _extract_action_plan(career_report) -> list:
    _MILESTONE_DEFAULTS = [
        {"date": "30天后", "trigger": "如未达成，建议延长至45天并参加线上辅导课程"},
        {"date": "6个月后", "trigger": "如核心技能仍有差距，调整学习侧重或报名专项培训"},
        {"date": "24个月后", "trigger": "如未达到目标岗位，考虑横向转岗或重新评估职业方向"},
    ]
    phases = []
    for idx, chapter in enumerate(career_report.chapters):
        if chapter.action_items:
            first_item = chapter.action_items[0]
            pm = _MILESTONE_DEFAULTS[idx] if idx < len(_MILESTONE_DEFAULTS) else {
                "date": "阶段结束时", "trigger": "重新评估目标达成情况并调整计划"
            }
            metric = (first_item.verification or first_item.description or "")[:50]
            phases.append({
                "phase": chapter.title,
                "timeline": first_item.timeline if chapter.action_items else "",
                "goals": [item.description for item in chapter.action_items],
                "milestone_check": {"date": pm["date"], "metric": metric, "trigger": pm["trigger"]},
            })
    return phases


def _extract_skill_gaps(match_result) -> list:
    gaps = match_result.dimensions.professional_skills.gap_skills or []
    return [{"skill": g.skill, "importance": g.importance, "suggestion": g.suggestion, "jd_source": g.jd_source} for g in gaps]


def _extract_career_path(match_result) -> list:
    paths = job_graph.get_all_paths(match_result.job_title)
    steps = []
    for p in paths.get("promotion_paths", [])[:1]:
        for node in p.get("nodes", []):
            if node:
                steps.append({"title": node.get("title", ""), "description": node.get("overview", "")})
    return steps


def _build_export_data(report, student_name: str) -> dict:
    chapters = report.chapters_json or []
    action_plan = report.action_plan or []
    if not action_plan and chapters:
        for ch in chapters:
            if ch.get("action_items"):
                action_plan = ch["action_items"]
                break
    return {
        "student_name": student_name,
        "job_name": report.job_name,
        "overall_score": report.overall_score or 0,
        "dimensions": report.dimensions or {},
        "skill_gaps": report.skill_gaps or [],
        "action_plan": action_plan,
        "career_path": report.career_path or [],
        "chapters": chapters,
    }


async def _get_report_with_name(session, report_id: str):
    report = await report_crud.get_by_report_id(session, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    student = await student_crud.get_by_student_id(session, report.student_id)
    name = (student.basic_info or {}).get("name") or report.student_id if student else report.student_id
    return report, name


# ── 后台任务 ──────────────────────────────────────────────────────────────────

async def _run_report_generation(report_id: str, student_id: str, job_name: str):
    """后台异步任务：执行完整的报告生成流程"""
    try:
        async with get_db_session() as session:
            await report_crud.update_status(session, report_id, "processing")

        async with get_db_session() as session:
            student = await student_crud.get_by_student_id(session, student_id)
            if not student:
                raise ValueError(f"学生 {student_id} 不存在")
            portrait = StudentPortrait(
                student_id=student.student_id,
                basic_info=student.basic_info or {},
                education=student.education or [],
                skills=student.skills or [],
                internships=student.internships or [],
                projects=student.projects or [],
                certs=student.certs or [],
                awards=student.awards or [],
                career_intent=student.career_intent,
                inferred_soft_skills=student.inferred_soft_skills or {},
                completeness=student.completeness,
                competitiveness=student.competitiveness,
                competitiveness_level=student.competitiveness_level,
                highlights=student.highlights or [],
                weaknesses=student.weaknesses or [],
            )

        async def _generate():
            async with get_db_session() as _s:
                await report_crud.update_progress(_s, report_id, 25, "正在计算人岗匹配得分...")
            async with get_db_session() as match_session:
                _match = await match_service.compute_match(portrait.model_dump(), job_name, db_session=match_session)

            async with get_db_session() as _s:
                await report_crud.update_progress(_s, report_id, 60, "AI正在生成报告章节...")
            _report = await report_service.generate_report(portrait, _match)

            async with get_db_session() as _s:
                await report_crud.update_progress(_s, report_id, 90, "正在整理报告内容...")
            return _match, _report

        try:
            match_result, career_report = await asyncio.wait_for(_generate(), timeout=120)
        except asyncio.TimeoutError:
            raise TimeoutError("报告生成超时（>120s），请稍后重试")

        action_plan = _extract_action_plan(career_report)
        skill_gaps = _extract_skill_gaps(match_result)
        career_path = _extract_career_path(match_result)

        chapters_json = [
            {
                "title": ch.title,
                "type": ch.index,
                "icon": ch.icon,
                "content": ch.content_md,
                "action_items": [item.model_dump() for item in (ch.action_items or [])],
            }
            for ch in career_report.chapters
        ]
        if career_report.completeness_warnings:
            chapters_json.append({"type": "completeness_warnings", "items": career_report.completeness_warnings})

        async with get_db_session() as session:
            await report_crud.update_content(
                session, report_id,
                {
                    "overall_score": match_result.overall_score,
                    "dimensions": match_result.dimensions.model_dump(),
                    "action_plan": action_plan,
                    "skill_gaps": skill_gaps,
                    "career_path": career_path,
                    "chapters_json": chapters_json,
                },
                status="completed",
            )
    except Exception as e:
        async with get_db_session() as session:
            await report_crud.update_status(session, report_id, "failed", str(e))


# ── 路由 ──────────────────────────────────────────────────────────────────────

@router.post("/generate")
@limiter.limit("5/minute")
async def generate_report(
    request: Request,
    student_id: str,
    job_name: str,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """触发报告生成，立即返回 task_id，后台异步执行"""
    if current_user and current_user.get("role") == "student":
        if current_user.get("student_id") != student_id:
            raise HTTPException(status_code=403, detail="无权限为此学生生成报告")
    async with get_db_session() as session:
        existing = await report_crud.get_by_student_and_job(session, student_id, job_name)
        if existing and existing.status in ("pending", "processing"):
            return {"task_id": existing.report_id, "reused": True}
        report = await report_crud.create(session, student_id, job_name)
        report_id = report.report_id

    background_tasks.add_task(_run_report_generation, report_id, student_id, job_name)
    return {"task_id": report_id}


@router.get("/status/{task_id}")
async def get_report_status(task_id: str):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, task_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        if report.status in ("pending", "processing") and report.created_at:
            age_seconds = (datetime.utcnow() - report.created_at).total_seconds()
            if age_seconds > 300:
                await report_crud.update_status(session, task_id, "failed", "生成超时，请重试")
                report.status = "failed"
                report.error_message = "生成超时，请重试"

        _extra = report.extra_data or {}
        _stored_progress = _extra.get("_progress", 0)
        _stored_msg = _extra.get("_progress_msg", "")
        _status_msg = {
            "pending": "正在初始化...",
            "processing": _stored_msg or "AI正在深度分析，请稍候...",
            "completed": "报告生成完成",
            "failed": report.error_message or "生成失败，请重试",
        }
        if report.status == "completed":
            _progress = 100
        elif report.status == "pending":
            _progress = 10
        elif report.status == "processing":
            _progress = _stored_progress if _stored_progress > 10 else 20
        else:
            _progress = 0

        return {
            "status": report.status,
            "progress": _progress,
            "message": _status_msg.get(report.status, "处理中..."),
            "error_msg": report.error_message if report.status == "failed" else None,
            "result": {
                "report_id": report.report_id,
                "job_name": report.job_name,
                "overall_score": report.overall_score,
                "confidence": None,
                "dimensions": report.dimensions,
                "action_plan": report.action_plan,
                "skill_gaps": report.skill_gaps,
                "career_path": report.career_path,
                "chapters_json": report.chapters_json or [],
                "created_at": str(report.created_at),
            } if report.status == "completed" else None,
        }


@router.get("/{report_id}")
async def get_report(report_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        if current_user and current_user.get("role") != "admin":
            if current_user.get("student_id") != report.student_id:
                raise HTTPException(status_code=403, detail="无权限访问此报告")
        return {
            "report_id": report.report_id,
            "student_id": report.student_id,
            "job_name": report.job_name,
            "overall_score": report.overall_score,
            "dimensions": report.dimensions,
            "action_plan": report.action_plan,
            "skill_gaps": report.skill_gaps,
            "career_path": report.career_path,
            "chapters_json": report.chapters_json or [],
            "created_at": str(report.created_at),
        }


@router.put("/{report_id}")
async def update_report(report_id: str, request: ReportUpdateRequest, current_user: Optional[dict] = Depends(get_current_user)):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        if current_user and current_user.get("role") != "admin":
            if current_user.get("student_id") != report.student_id:
                raise HTTPException(status_code=403, detail="无权限修改此报告")

        update_data = {}
        if request.action_plan is not None:
            update_data["action_plan"] = request.action_plan
        if request.skill_gaps is not None:
            update_data["skill_gaps"] = request.skill_gaps
        if request.career_path is not None:
            update_data["career_path"] = request.career_path

        if update_data:
            await report_crud.update_content(session, report_id, update_data)
            audit_log("UPDATE", "report", report_id, f"fields={list(update_data.keys())}")

    return {"success": True, "message": "报告更新成功", "report_id": report_id}


@router.get("/{report_id}/word")
async def export_report_word(report_id: str):
    async with get_db_session() as session:
        report, student_name = await _get_report_with_name(session, report_id)
        report_data = _build_export_data(report, student_name)
    file_path = report_export_service.export_to_word(report_data)
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"career_report_{report_id}.docx",
    )


@router.get("/{report_id}/html")
async def export_report_html(report_id: str):
    async with get_db_session() as session:
        report, student_name = await _get_report_with_name(session, report_id)
        report_data = _build_export_data(report, student_name)
    file_path = report_export_service.export_to_html(report_data)
    return FileResponse(file_path, media_type="text/html", filename=f"career_report_{report_id}.html")


@router.get("/{report_id}/pdf")
async def export_report_pdf(report_id: str):
    async with get_db_session() as session:
        report, student_name = await _get_report_with_name(session, report_id)
        report_data = _build_export_data(report, student_name)
    file_path = report_export_service.export_to_pdf(report_data)
    if file_path.endswith(".html"):
        return FileResponse(file_path, media_type="text/html", filename=f"career_report_{report_id}.html")
    return FileResponse(file_path, media_type="application/pdf", filename=f"career_report_{report_id}.pdf")


@router.post("/{report_id}/adjust")
async def adjust_report(report_id: str, req: ReportAdjustRequest):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        chapters = list(report.chapters_json or [])
        feedback_hint = req.feedback_summary or ""
        focus = req.focus_chapters or []
        polished_chapters = []
        for ch in chapters:
            ch_title = ch.get("title", "")
            should_polish = (not focus) or any(f in ch_title for f in focus) or ch_title in focus
            ch_content = ch.get("content_md") or ch.get("content", "")
            if should_polish and ch_content:
                try:
                    from app.services.report_service import ReportChapter, ActionItem
                    ch_obj = ReportChapter(
                        index=ch.get("index", 0), icon=ch.get("icon", ""),
                        title=ch_title, content_md=ch_content,
                        action_items=[ActionItem(**a) for a in (ch.get("action_items") or [])],
                    )
                    hint_prompt = f"\n\n用户反馈：{feedback_hint}" if feedback_hint else ""
                    ch_obj.content_md += hint_prompt
                    polished = await report_service.polish_chapter_content(ch_obj)
                    ch_dict = dict(ch)
                    ch_dict["content_md"] = polished.content_md.replace(hint_prompt, "")
                    ch_dict["content"] = ch_dict["content_md"]
                    polished_chapters.append(ch_dict)
                except Exception:
                    polished_chapters.append(ch)
            else:
                polished_chapters.append(ch)

        await report_crud.update_content(session, report_id, {"chapters_json": polished_chapters})

    return {"report_id": report_id, "adjusted": True, "chapters_count": len(polished_chapters)}


@router.post("/{report_id}/polish")
async def polish_report(report_id: str, req: PolishRequest = None):
    """章节粒度润色：支持指定章节、保存润色前快照"""
    if req is None:
        req = PolishRequest()
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        snapshot = {"action_plan": report.action_plan, "skill_gaps": report.skill_gaps, "chapters_json": report.chapters_json}
        snapshot_hash = hashlib.md5(json.dumps(snapshot, ensure_ascii=False, default=str).encode()).hexdigest()[:8]
        extra = dict(report.extra_data or {})
        extra["pre_polish_snapshot"] = snapshot
        extra["pre_polish_hash"] = snapshot_hash
        extra["polished_at"] = datetime.utcnow().isoformat()

        chapters = list(report.chapters_json or [])
        focus = req.chapter_titles or []
        polished_chapters = []
        for ch in chapters:
            ch_title = ch.get("title", "")
            should_polish = (not focus) or any(f in ch_title for f in focus) or ch_title in focus
            ch_content = ch.get("content_md") or ch.get("content", "")
            if should_polish and ch_content:
                try:
                    from app.services.report_service import ReportChapter, ActionItem
                    ch_obj = ReportChapter(
                        index=ch.get("index", 0), icon=ch.get("icon", ""),
                        title=ch_title, content_md=ch_content,
                        action_items=[ActionItem(**a) for a in (ch.get("action_items") or [])],
                    )
                    if req.feedback_hint:
                        ch_obj.content_md += f"\n\n润色方向参考：{req.feedback_hint}"
                    polished = await report_service.polish_chapter_content(ch_obj)
                    ch_dict = dict(ch)
                    polished_text = polished.content_md.replace(f"\n\n润色方向参考：{req.feedback_hint}", "")
                    ch_dict["content_md"] = polished_text
                    ch_dict["content"] = polished_text
                    polished_chapters.append(ch_dict)
                except Exception:
                    polished_chapters.append(ch)
            else:
                polished_chapters.append(ch)

        polish_base = not focus or any("行动" in f or "计划" in f for f in focus)
        if polish_base:
            polished_base = await report_service.polish_report(report.action_plan or [], report.skill_gaps or [])
            new_action_plan = polished_base.get("action_plan", report.action_plan)
            new_skill_gaps = polished_base.get("skill_gaps", report.skill_gaps)
        else:
            new_action_plan = report.action_plan
            new_skill_gaps = report.skill_gaps

        await report_crud.update_content(session, report_id, {
            "action_plan": new_action_plan,
            "skill_gaps": new_skill_gaps,
            "chapters_json": polished_chapters,
            "extra_data": extra,
        }, status="completed")

    async with get_db_session() as session:
        updated = await report_crud.get_by_report_id(session, report_id)
        return {
            "report_id": updated.report_id,
            "student_id": updated.student_id,
            "job_name": updated.job_name,
            "overall_score": updated.overall_score,
            "dimensions": updated.dimensions,
            "action_plan": updated.action_plan,
            "skill_gaps": updated.skill_gaps,
            "career_path": updated.career_path,
            "chapters_json": updated.chapters_json or [],
            "created_at": str(updated.created_at),
            "snapshot_hash": snapshot_hash,
        }


@router.post("/{report_id}/undo_polish")
async def undo_polish(report_id: str):
    """撤销润色：恢复到润色前的快照"""
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        extra = dict(report.extra_data or {})
        snapshot = extra.get("pre_polish_snapshot")
        if not snapshot:
            raise HTTPException(status_code=400, detail="没有可回滚的润色快照")
        extra.pop("pre_polish_snapshot", None)
        extra.pop("pre_polish_hash", None)
        extra.pop("polished_at", None)
        await report_crud.update_content(session, report_id, {
            "action_plan": snapshot.get("action_plan"),
            "skill_gaps": snapshot.get("skill_gaps"),
            "chapters_json": snapshot.get("chapters_json"),
            "extra_data": extra,
        })
    return {"report_id": report_id, "undone": True, "message": "已回滚至润色前内容"}


@router.post("/{report_id}/feedback_optimize")
async def feedback_optimize_report(report_id: str, req: FeedbackOptimizeRequest):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        chapters_json = report.chapters_json or []
        if not chapters_json:
            raise HTTPException(status_code=400, detail="报告章节内容为空")

        extra = dict(report.extra_data or {})
        extra["pre_feedback_snapshot"] = {"chapters_json": chapters_json, "action_plan": report.action_plan, "skill_gaps": report.skill_gaps}
        extra["feedback_rating"] = req.rating
        extra["feedback_issues"] = req.issues
        extra["feedback_at"] = datetime.utcnow().isoformat()

        optimized_chapters = await report_service.feedback_optimize_chapters(
            chapters_json=chapters_json,
            rating=req.rating,
            issues=req.issues,
            comment=req.comment,
            focus_chapters=req.chapters,
        )
        await report_crud.update_content(session, report_id, {"chapters_json": optimized_chapters, "extra_data": extra})

    return {"report_id": report_id, "optimized": True, "chapters_count": len(optimized_chapters), "chapters_json": optimized_chapters, "snapshot_saved": True}


@router.get("/{report_id}/completeness")
async def check_report_completeness(report_id: str):
    async with get_db_session() as session:
        report = await report_crud.get_by_report_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

    issues = []
    score = 100
    if not report.action_plan:
        issues.append({"field": "action_plan", "label": "行动计划", "severity": "error", "msg": "行动计划为空"})
        score -= 30
    elif len(report.action_plan) < 2:
        issues.append({"field": "action_plan", "label": "行动计划", "severity": "warning", "msg": "行动计划阶段不足（建议至少2个阶段）"})
        score -= 10
    if not report.skill_gaps:
        issues.append({"field": "skill_gaps", "label": "技能差距", "severity": "warning", "msg": "技能差距分析为空"})
        score -= 20
    if not report.career_path:
        issues.append({"field": "career_path", "label": "职业路径", "severity": "warning", "msg": "职业发展路径为空"})
        score -= 20
    if not report.overall_score or report.overall_score == 0:
        issues.append({"field": "overall_score", "label": "综合评分", "severity": "error", "msg": "综合评分未生成"})
        score -= 30
    if not report.dimensions:
        issues.append({"field": "dimensions", "label": "四维度评分", "severity": "error", "msg": "四维度评分未生成"})
        score -= 30

    return {
        "report_id": report_id,
        "completeness_score": max(score, 0),
        "is_complete": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues,
    }


@router.get("/{report_id}/quality")
async def get_report_quality(report_id: str):
    result = await report_service.auto_quality_check(report_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result
