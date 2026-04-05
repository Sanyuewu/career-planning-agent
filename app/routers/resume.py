# -*- coding: utf-8 -*-
"""简历解析路由：/api/resume/*"""
import logging
import os
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends

from app.db import get_db_session, student_crud, portrait_history_crud
from app.deps import get_current_user
from app.rate_limit import limiter
from app.services.portrait_service import portrait_service
from app.services.resume_service import resume_service, ResumeParseResult, ResumeParseResponse, ResumeUploadResponse, compute_parse_quality

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["Resume"])

_ALLOWED_RESUME_EXTS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}
_MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10 MB

_FILE_SIGNATURES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".docx",
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": ".doc",
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
}


def _validate_file_type(content: bytes, declared_ext: str) -> str:
    for signature, ext in _FILE_SIGNATURES.items():
        if content.startswith(signature):
            if ext != declared_ext and ext != ".doc":
                logger.warning(f"文件类型不匹配: 声明 {declared_ext}, 实际 {ext}")
            return ext
    raise HTTPException(status_code=400, detail="无法识别的文件类型，请上传有效的 PDF、DOCX 或图片文件")


@router.post("/parse", response_model=ResumeUploadResponse)
@limiter.limit("10/minute")
async def parse_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(get_current_user),
):
    """解析上传的简历文件（支持PDF/DOCX/JPG/PNG，最大10MB）"""
    suffix = os.path.splitext(file.filename or "resume.pdf")[1].lower() or ".pdf"
    if suffix not in _ALLOWED_RESUME_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式 {suffix}，请上传 PDF、DOCX 或图片文件")

    task_id = f"parse_{uuid.uuid4().hex[:8]}"
    if current_user and current_user.get("student_id"):
        student_id = current_user["student_id"]
        is_update = True
    else:
        student_id = f"student_{uuid.uuid4().hex[:8]}"
        is_update = False

    content = await file.read()
    if len(content) > _MAX_RESUME_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，请上传10MB以内的文件")

    try:
        _validate_file_type(content, suffix)
    except HTTPException:
        raise HTTPException(status_code=400, detail="文件内容与声明类型不匹配，请上传有效的 PDF、DOCX 或图片文件")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    parse_error: Optional[HTTPException] = None
    try:
        result = await resume_service.parse_resume(tmp_path)
    except ValueError as exc:
        logger.warning(f"简历解析业务错误: {exc}")
        parse_error = HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error(f"简历处理内部错误: {exc}", exc_info=True)
        parse_error = HTTPException(status_code=500, detail="简历处理出错，请稍后重试或联系管理员")
    finally:
        os.unlink(tmp_path)

    if parse_error:
        raise parse_error

    portrait = portrait_service.build_portrait(result)

    async with get_db_session() as session:
        student_data = {
            "student_id": student_id,
            "basic_info": result.basic_info,
            "education": result.education,
            "skills": result.skills,
            "internships": result.internships,
            "projects": result.projects,
            "certs": result.certs,
            "awards": result.awards,
            "career_intent": result.career_intent,
            "inferred_soft_skills": result.inferred_soft_skills,
            "completeness": portrait.completeness,
            "competitiveness": portrait.competitiveness,
            "competitiveness_level": portrait.competitiveness_level,
            "highlights": portrait.highlights,
            "weaknesses": portrait.weaknesses,
            "interests": portrait.interests,
            "ability_profile": portrait.ability_profile,
            "personality_traits": portrait.personality_traits,
            "transfer_opportunities": portrait.transfer_opportunities,
            "gap_mapped_transfers": portrait.gap_mapped_transfers,
        }
        if is_update:
            existing = await student_crud.get_by_student_id(session, student_id)
            if existing:
                await student_crud.update(session, student_id, {k: v for k, v in student_data.items() if k != "student_id"})
            else:
                await student_crud.create(session, student_data)
        else:
            await student_crud.create(session, student_data)
        try:
            await portrait_history_crud.create_snapshot(
                session,
                student_id=student_id,
                portrait={"basic_info": result.basic_info, "skills": result.skills},
                completeness=portrait.completeness,
                competitiveness=portrait.competitiveness,
                snapshot_reason="简历解析建档",
            )
        except Exception as _snap_err:
            logger.warning(f"简历解析快照写入失败: {_snap_err}")

    resp = ResumeParseResponse(
        student_id=student_id,
        basic_info=result.basic_info,
        education=result.education,
        skills=result.skills,
        internships=result.internships,
        projects=result.projects,
        certs=result.certs,
        awards=result.awards,
        career_intent=result.career_intent,
        inferred_soft_skills=result.inferred_soft_skills,
        completeness=portrait.completeness,
        missing_dims=result.missing_dims,
        competitiveness=portrait.competitiveness,
        competitiveness_level=portrait.competitiveness_level,
        transfer_opportunities=portrait.transfer_opportunities,
        gap_mapped_transfers=portrait.gap_mapped_transfers,
    )
    resp.parse_quality = compute_parse_quality(resp)
    return ResumeUploadResponse(task_id=task_id, message="解析成功", result=resp)


@router.post("/parse-text", response_model=ResumeUploadResponse)
async def parse_resume_text(
    data: dict,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """解析纯文本简历（手动录入时的文本解析入口）"""
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    if len(text.encode("utf-8")) > 100 * 1024:
        raise HTTPException(status_code=413, detail="文本内容过长，请限制在100KB以内")

    task_id = f"parse_{uuid.uuid4().hex[:8]}"
    if current_user and current_user.get("student_id"):
        student_id = current_user["student_id"]
        is_update = True
    else:
        student_id = f"student_{uuid.uuid4().hex[:8]}"
        is_update = False

    result = await resume_service.parse_text(text)
    portrait = portrait_service.build_portrait(result)

    async with get_db_session() as session:
        student_data = {
            "student_id": student_id,
            "basic_info": result.basic_info,
            "education": result.education,
            "skills": result.skills,
            "internships": result.internships,
            "projects": result.projects,
            "certs": result.certs,
            "awards": result.awards,
            "career_intent": result.career_intent,
            "inferred_soft_skills": result.inferred_soft_skills,
            "completeness": portrait.completeness,
            "competitiveness": portrait.competitiveness,
            "competitiveness_level": portrait.competitiveness_level,
            "highlights": portrait.highlights,
            "weaknesses": portrait.weaknesses,
            "interests": portrait.interests,
            "ability_profile": portrait.ability_profile,
            "personality_traits": portrait.personality_traits,
            "transfer_opportunities": portrait.transfer_opportunities,
            "gap_mapped_transfers": portrait.gap_mapped_transfers,
        }
        if is_update:
            existing = await student_crud.get_by_student_id(session, student_id)
            if existing:
                await student_crud.update(session, student_id, {k: v for k, v in student_data.items() if k != "student_id"})
            else:
                await student_crud.create(session, student_data)
        else:
            await student_crud.create(session, student_data)

    resp = ResumeParseResponse(
        student_id=student_id,
        basic_info=result.basic_info,
        education=result.education,
        skills=result.skills,
        internships=result.internships,
        projects=result.projects,
        certs=result.certs,
        awards=result.awards,
        career_intent=result.career_intent,
        inferred_soft_skills=result.inferred_soft_skills,
        completeness=portrait.completeness,
        missing_dims=result.missing_dims,
        competitiveness=portrait.competitiveness,
        competitiveness_level=portrait.competitiveness_level,
        transfer_opportunities=portrait.transfer_opportunities,
        gap_mapped_transfers=portrait.gap_mapped_transfers,
    )
    resp.parse_quality = compute_parse_quality(resp)
    return ResumeUploadResponse(task_id=task_id, message="解析成功", result=resp)
