# -*- coding: utf-8 -*-
"""
核心流程路由的共享基础设施。

由 bridge_flow.py（954 行 god-file）拆分而来：持久化存储句柄、前端格式转换、
请求模型，供 report/chat/match/agent/stats 子路由与 agents.tools 复用。
（报告生成业务已迁至 app/services/report_generation_service.py，本文件只留薄委托。）
"""

import io
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.student_graph_service import student_graph_service
from app.services.async_store import AsyncKVStore
from app.services import match_rules

# ── 异步持久化存储（按 id 异步读写 + Redis 读穿，无全量内存） ──
_report_store = AsyncKVStore("report")   # report_id  → report dict
_chat_store = AsyncKVStore("chat")        # session_id → session dict
# 任务进度（报告生成期间轮询）已迁至 app/services/task_progress.py，
# 走可降级 cache（Redis 共享 / 进程内降级），支持多实例。此处不再保留进程内 dict。


# ════════════════════════════════════════════════════════════
# 前端格式转换 / 工具函数
# ════════════════════════════════════════════════════════════

def _match_result_to_frontend(mr, job_name: str = "", weights: Dict = None) -> Dict:
    """后端 MatchResult → 前端 MatchResult 格式（含一票否决与实际权重）"""
    details = mr.details if isinstance(mr.details, dict) else {}
    return {
        "job_title": job_name,
        "overall_score": round(mr.total_match, 1),
        "confidence": round(mr.total_match / 100, 2),
        "eligible": getattr(mr, "eligible", True),
        "veto_reason": getattr(mr, "veto_reason", ""),
        "dimensions": {
            "basic_requirements": {
                "score": round(mr.basic_match, 1),
                "detail": details.get("basic_analysis", ""),
            },
            "professional_skills": {
                "score": round(mr.skill_match, 1),
                "detail": details.get("skill_analysis", ""),
            },
            "professional_qualities": {
                "score": round(mr.quality_match, 1),
                "detail": details.get("quality_analysis", ""),
            },
            "development_potential": {
                "score": round(mr.potential_match, 1),
                "detail": details.get("potential_analysis", ""),
            },
        },
        "matched_skills": details.get("matched_skills", []),
        "gap_skills": [{"skill": s} for s in details.get("missing_skills", [])],
        "summary": details.get("skill_analysis", ""),
        "weight_used": weights or match_rules.DEFAULT_WEIGHTS,
    }


def _report_to_frontend(report_id: str, data: Dict) -> Dict:
    """report_store 条目 → 前端 ReportDetail 格式"""
    mr = data.get("match_result", {})
    dimensions = mr if isinstance(mr, dict) else {}
    phased = data.get("phased_plan", {})

    # 构建 action_plan（短期+中期列表合并）
    action_plan = []
    for phase_key, phase_label in [("short_term", "短期"), ("mid_term", "中期")]:
        for item in (phased.get(phase_key) or []):
            if isinstance(item, dict):
                action_plan.append({
                    "phase": phase_label,
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "timeline": item.get("timeline", ""),
                    "milestones": item.get("milestones", []),
                })

    # skill_gaps：从 match_result details 取
    skill_gaps = [{"skill": s, "priority": "high"} for s in dimensions.get("details", {}).get("missing_skills", [])]

    # career_path：从 career_paths 字段取
    career_path = data.get("career_paths", [])

    return {
        "report_id": report_id,
        "student_id": data.get("student_id", ""),
        "job_name": data.get("job_name", ""),
        "overall_score": dimensions.get("total_match", 0),
        "confidence": round(dimensions.get("total_match", 0) / 100, 2),
        "dimensions": {
            "basic_requirements": {"score": dimensions.get("basic_match", 0)},
            "professional_skills": {"score": dimensions.get("skill_match", 0)},
            "professional_qualities": {"score": dimensions.get("quality_match", 0)},
            "development_potential": {"score": dimensions.get("potential_match", 0)},
        },
        "action_plan": action_plan,
        "skill_gaps": skill_gaps,
        "career_path": career_path,
        "chapters_json": data.get("chapters_json", []),
        "created_at": data.get("created_at", ""),
    }


def _report_content_to_chapters(content: str, job_name: str) -> List[Dict]:
    """把 Markdown 报告内容拆分为 chapters_json"""
    chapters = []
    current_title = ""
    current_body: List[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_title:
                chapters.append({"title": current_title, "content": "\n".join(current_body).strip()})
            current_title = line.lstrip("# ").strip()
            current_body = []
        elif line.startswith("# "):
            pass  # 跳过 h1 大标题
        else:
            current_body.append(line)

    if current_title:
        chapters.append({"title": current_title, "content": "\n".join(current_body).strip()})

    return chapters


def _get_student_portrait_from_store(student_id: str):
    """从 student_graph_service 取学生数据并转换为 StudentPortrait"""
    from app.services.career_graphrag_service import StudentPortrait
    node = student_graph_service.get_student(student_id)
    if not node:
        return None
    return StudentPortrait.from_node(node, student_id=student_id)


async def _build_export_response(report_id: str, fmt: str) -> StreamingResponse:
    """公共导出逻辑：从报告存储取数据，调用导出服务生成文件流"""
    data = await _report_store.get(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="报告不存在")

    from app.services.report_export_service import report_export_service

    export_data = {
        "student": {"student_id": data.get("student_id"), "name": ""},
        "job": {"title": data.get("job_name")},
        "match_result": data.get("match_result", {}),
        "phased_plan": data.get("phased_plan", {}),
        "chapters_json": data.get("chapters_json", []),
    }

    if fmt == "pdf":
        file_bytes = report_export_service.export_to_pdf(export_data)
        media_type = "application/pdf"
        filename = f"career_report_{report_id[:8]}.pdf"
    else:
        file_bytes = report_export_service.export_to_docx(export_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"career_report_{report_id[:8]}.docx"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _generate_report_task(task_id: str, report_id: str, student_id: str, job_name: str):
    """后台报告生成任务的薄委托（业务已迁至 report_generation_service，瘦身 _common）。
    保留本名供 report.py / tools.py 既有 import 调用；惰性 import 避免与该 service 的循环导入。"""
    from app.services.report_generation_service import generate_report_task
    return await generate_report_task(task_id, report_id, student_id, job_name)


# ════════════════════════════════════════════════════════════
# 请求模型
# ════════════════════════════════════════════════════════════

class MatchComputeRequest(BaseModel):
    student_id: str
    job_name: str
    weight_preset: str = "default"


class ReportUpdateRequest(BaseModel):
    action_plan: Optional[List[Any]] = None
    skill_gaps: Optional[List[Any]] = None
    career_path: Optional[List[Any]] = None
    chapters_json: Optional[List[Any]] = None


class PolishRequest(BaseModel):
    chapter_titles: Optional[List[str]] = None
    feedback_hint: Optional[str] = None


class ChatMessageRequest(BaseModel):
    session_id: str
    content: Optional[str] = None   # 前端有时用 content
    message: Optional[str] = None   # 前端有时用 message
    student_id: Optional[str] = None

    @property
    def text(self) -> str:
        return self.content or self.message or ""


class FeedbackOptimizeRequest(BaseModel):
    rating: int = 3
    issues: List[str] = []
    comment: str = ""


class AgentRunRequest(BaseModel):
    student_id: str
    goal: str
    chapters: Optional[List[str]] = None
