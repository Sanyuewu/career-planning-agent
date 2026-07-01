# -*- coding: utf-8 -*-
"""
成长闭环学生端路由（Phase 3）：成长曲线 + 行动计划清单/勾选完成。

只读聚合 + 轻量写（勾选完成），不触发 youtu/FAISS。
全部 path 含 {student_id}，经 require_student_access 堵 IDOR：
  student=本人 / teacher=本班 / admin=本租户。
"""

from fastapi import APIRouter, Depends, HTTPException

from app.services import progress_service, snapshot_store
from app.routers.auth import require_student_access

router = APIRouter(tags=["成长闭环"])


@router.get("/api/progress/{student_id}")
async def get_progress(student_id: str, user: dict = Depends(require_student_access)):
    """学生成长视图：竞争力/匹配分曲线 + 成长归因 + 最近匹配进展 + 行动完成率。

    无历史快照时各子项返回 available=False，前端优雅降级（不报错、不画空图）。
    """
    return {
        "student_id": student_id,
        "trend": progress_service.trend(student_id),
        "growth": progress_service.attribute_growth(student_id),
        "match_progress": progress_service.latest_match_progress(student_id),
        "actions": progress_service.action_completion_rate(student_id),
    }


@router.get("/api/action/{student_id}")
async def get_action_plan(student_id: str, user: dict = Depends(require_student_access)):
    """当前生效的行动计划（含完成率）。无计划返回 has_plan=False。"""
    plan = snapshot_store.get_active_action_plan(student_id)
    if not plan:
        return {"has_plan": False, "student_id": student_id}
    return {
        "has_plan": True,
        "plan": plan,
        "completion": progress_service.action_completion_rate(student_id),
    }


@router.post("/api/action/{student_id}/item/{item_id}/complete")
async def complete_action_item(student_id: str, item_id: str,
                               user: dict = Depends(require_student_access)):
    """勾选某行动项完成。闭合"完成行动→重测匹配→看到分数变化"回路的第一步。"""
    ok = snapshot_store.complete_action_item(student_id, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="行动项不存在或已无生效计划")
    return {
        "success": True,
        "completion": progress_service.action_completion_rate(student_id),
    }
