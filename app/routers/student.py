# -*- coding: utf-8 -*-
"""
学生画像桥接路由
将前端期望的 /api/portrait / /api/resume 路径映射到后端现有服务。

前端期望路径：
  POST /api/resume/parse           → 解析简历文件
  GET  /api/portrait/{student_id}  → 获取学生画像
  PUT  /api/portrait/{student_id}  → 更新学生画像
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.services.career_graphrag_service import career_graphrag_service
from app.services.student_graph_service import student_graph_service
from app.routers.auth import get_current_user, require_student_access

router = APIRouter(tags=["学生画像"])

# ── 软能力等级 → 数值映射 ────────────────────────────────
_LEVEL_SCORE = {"优秀": 5, "良好": 4, "一般": 3, "较低": 2, "较差": 1}
_COMPETITIVENESS_LEVEL = [
    (85, "优秀"),
    (70, "良好"),
    (55, "一般"),
    (40, "较低"),
    (0,  "较差"),
]


def _competitiveness_level(score: float) -> str:
    for threshold, label in _COMPETITIVENESS_LEVEL:
        if score >= threshold:
            return label
    return "较差"


# ── student_graph_service 节点 → 前端 PortraitResponse ───
def _node_to_portrait(node: Dict[str, Any], student_id: str) -> Dict[str, Any]:
    attrs = node.get("attributes", {}) if "attributes" in node else node

    name = attrs.get("name", "")
    skills: List[str] = attrs.get("skills", [])
    certs: List[str] = attrs.get("certificates", attrs.get("certs", []))
    education: List = attrs.get("education", [])

    # basic_info：从 education[0] 尽量补全
    school = major = grade = ""
    if education:
        edu0 = education[0] if isinstance(education[0], dict) else {}
        school = edu0.get("school", "")
        major = edu0.get("major", "")
        grade = edu0.get("grade", edu0.get("degree", ""))

    # inferred_soft_skills
    soft_keys = ["innovation", "learning", "stress_resistance", "communication", "internship"]
    inferred: Dict[str, Any] = {}
    for key in soft_keys:
        level = attrs.get(key, "一般")
        inferred[key] = {
            "score": _LEVEL_SCORE.get(level, 3),
            "evidence": attrs.get(f"{key}_evidence", ""),
        }

    completeness = float(attrs.get("completeness_score", 0))
    competitiveness = float(attrs.get("competitiveness_score", 0))

    return {
        "student_id": student_id,
        "basic_info": {
            "name": name,
            "school": school,
            "major": major,
            "grade": grade,
        },
        "education": education,
        "skills": skills,
        "internships": attrs.get("internships", []),
        "projects": attrs.get("projects", []),
        "certs": certs,
        "awards": attrs.get("awards", []),
        "career_intent": attrs.get("career_intent", ""),
        "inferred_soft_skills": inferred,
        "completeness": completeness,
        "competitiveness": competitiveness,
        "competitiveness_level": _competitiveness_level(competitiveness),
        "highlights": attrs.get("highlights", []),
        "weaknesses": attrs.get("weaknesses", []),
        "transfer_opportunities": attrs.get("transfer_opportunities", []),
        "interests": attrs.get("interests", []),
    }


# ── 请求模型 ─────────────────────────────────────────────
class PortraitUpdateRequest(BaseModel):
    basic_info: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    certs: Optional[List[str]] = None
    awards: Optional[List[str]] = None
    education: Optional[List[Any]] = None
    internships: Optional[List[Any]] = None
    projects: Optional[List[Any]] = None
    career_intent: Optional[str] = None
    interests: Optional[List[str]] = None


# ── 路由 ─────────────────────────────────────────────────
@router.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """
    解析简历文件（PDF / DOCX / TXT）
    1. 读取文件内容
    2. 调 career_graphrag_service.generate_student_portrait(resume_text)
    3. 存入 student_graph_service（学生账号→画像绑定到本人 student_id）
    4. 返回前端 PortraitResponse 格式（含 student_id）
    """
    try:
        raw = await file.read()

        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=raw, filetype="pdf")
                text = "\n".join(page.get_text() for page in doc)
            except Exception:
                text = raw.decode("utf-8", errors="ignore")
        elif filename.endswith(".docx"):
            try:
                import docx, io
                document = docx.Document(io.BytesIO(raw))
                text = "\n".join(p.text for p in document.paragraphs)
            except Exception:
                text = raw.decode("utf-8", errors="ignore")
        else:
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw.decode("utf-8", errors="ignore")

        portrait = await career_graphrag_service.generate_student_portrait(
            resume_text=text
        )

        # 学生账号：画像绑定到本人 student_id（便于后续 get/update 归属校验）
        portrait_data = portrait.model_dump()
        if user.get("role") == "student" and user.get("student_id"):
            portrait_data["student_id"] = user["student_id"]

        # 持久化到 student_graph_service（写入即按当前租户打标签）
        student_id = student_graph_service.save_student(portrait_data)
        portrait_dict = portrait.model_dump()
        portrait_dict["student_id"] = student_id

        node = {"attributes": portrait_dict}
        result = _node_to_portrait(node, student_id)

        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portrait/{student_id}")
async def get_portrait(student_id: str, user: dict = Depends(require_student_access)):
    """获取学生画像（前端 PortraitResponse 格式）"""
    node = student_graph_service.get_student(student_id)
    if not node:
        raise HTTPException(status_code=404, detail="学生不存在")
    return _node_to_portrait(node, student_id)


@router.put("/api/portrait/{student_id}")
async def update_portrait(student_id: str, req: PortraitUpdateRequest,
                          user: dict = Depends(require_student_access)):
    """更新学生画像字段"""
    node = student_graph_service.get_student(student_id)
    if not node:
        raise HTTPException(status_code=404, detail="学生不存在")

    updates: Dict[str, Any] = {}
    if req.basic_info:
        updates["name"] = req.basic_info.get("name", "")
        # 将 basic_info 扁平写入 attributes
        updates.update({k: v for k, v in req.basic_info.items() if v is not None})
    if req.skills is not None:
        updates["skills"] = req.skills
    if req.certs is not None:
        updates["certificates"] = req.certs
    if req.awards is not None:
        updates["awards"] = req.awards
    if req.education is not None:
        updates["education"] = req.education
    if req.internships is not None:
        updates["internships"] = req.internships
    if req.projects is not None:
        updates["projects"] = req.projects
    if req.career_intent is not None:
        updates["career_intent"] = req.career_intent
    if req.interests is not None:
        updates["interests"] = req.interests

    student_graph_service.update_student(student_id, updates)

    updated_node = student_graph_service.get_student(student_id)
    return _node_to_portrait(updated_node, student_id)


@router.delete("/api/portrait/{student_id}")
async def delete_portrait(student_id: str, user: dict = Depends(require_student_access)):
    """删除学生画像及其匹配记录（数据被遗忘权；教育隐私合规）。"""
    ok = student_graph_service.delete_student(student_id)
    if not ok:
        raise HTTPException(status_code=404, detail="学生不存在")
    return {"success": True, "deleted": student_id}
