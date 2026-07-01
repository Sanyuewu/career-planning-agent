# -*- coding: utf-8 -*-
"""
平台运营路由（平台超管，跨租户）——全部 `require_role("platform_admin")`。
总览 / 各校指标 / 开通学校 / 单校下钻。只读聚合 + 开通（建租户+初始 admin）。
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.core.security_context import set_tenant, get_tenant
from app.models.db_models import Tenant, User
from app.routers.auth import require_role, _hash_password
from app.services import platform_directory
from app.services.student_graph_service import student_graph_service

router = APIRouter(prefix="/api/platform", tags=["平台运营"])


class CreateTenantRequest(BaseModel):
    name: str
    tenant_id: Optional[str] = None          # 学校代码，缺省自动生成
    admin_username: str
    admin_password: str


@router.get("/overview")
async def overview(user: dict = Depends(require_role("platform_admin"))):
    """全平台总览：业务总量 + 跨校对标（按提升% 排序）。"""
    tenants = platform_directory.tenants_with_stats()
    return {
        "totals": platform_directory.platform_totals(),
        "tenants": tenants,
        "top": tenants[:5],
    }


@router.get("/tenants")
async def list_tenants(user: dict = Depends(require_role("platform_admin"))):
    """各学校指标表。"""
    return {"tenants": platform_directory.tenants_with_stats()}


@router.post("/tenants")
async def create_tenant(req: CreateTenantRequest, user: dict = Depends(require_role("platform_admin"))):
    """开通一所学校：建租户 + 初始管理员账号（该 admin 之后自行管理本校）。"""
    tid = (req.tenant_id or "").strip() or str(uuid.uuid4())[:8]
    if tid == platform_directory.PLATFORM_TENANT:
        raise HTTPException(status_code=400, detail="非法学校代码")
    with SessionLocal() as db:
        if db.get(Tenant, tid):
            raise HTTPException(status_code=400, detail="学校代码已存在")
        if db.query(User).filter(User.username == req.admin_username).first():
            raise HTTPException(status_code=400, detail="管理员用户名已存在")
        db.add(Tenant(id=tid, name=req.name))
        db.add(User(
            id=str(uuid.uuid4()), username=req.admin_username,
            password_hash=_hash_password(req.admin_password),
            tenant_id=tid, role="admin", student_id=None, class_id=None,
        ))
        db.commit()
    return {"tenant_id": tid, "name": req.name, "admin_username": req.admin_username}


@router.get("/tenants/{tenant_id}")
async def tenant_detail(tenant_id: str, user: dict = Depends(require_role("platform_admin"))):
    """单校下钻：该校指标 + 学生名册（临时切到该租户只读）。"""
    stats = next((t for t in platform_directory.tenants_with_stats() if t["id"] == tenant_id), None)
    if not stats:
        raise HTTPException(status_code=404, detail="学校不存在")
    prev = get_tenant()
    set_tenant(tenant_id)
    try:
        students = student_graph_service.get_all_students()
        roster = [{
            "student_id": (s.get("attributes", {}) or {}).get("student_id"),
            "name": (s.get("attributes", {}) or {}).get("name", ""),
            "competitiveness": round(float((s.get("attributes", {}) or {}).get("competitiveness_score", 0) or 0)),
            "completeness": round(float((s.get("attributes", {}) or {}).get("completeness_score", 0) or 0)),
        } for s in students]
    finally:
        set_tenant(prev)
    return {"tenant": stats, "students": roster}
