# -*- coding: utf-8 -*-
"""
管理端路由：仅 admin 角色、限本租户。
- M2：租户级产品化配置（权重/岗位库/报告模板）。
- M5：院校组织管理 CRUD（班级 / 用户 / 学生分班 / 教师带班）+ 学生名册。
  复用 M0 `User/ClassGroup/TeacherClass` 表；范围/join 经 `student_directory`（单源）。
"""

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.db_models import User, ClassGroup, TeacherClass
from app.routers.auth import require_role, _hash_password
from app.services import tenant_config_service, student_directory

router = APIRouter(prefix="/api/admin", tags=["管理"])


class TenantConfigRequest(BaseModel):
    match_weights: Optional[Dict[str, float]] = None       # {basic,skill,quality,potential}
    job_library: Optional[List[str]] = None                # 岗位白名单；None=全部
    report_extra_instructions: Optional[str] = None        # 报告 prompt 院校定制增补


@router.get("/tenant/config")
async def get_tenant_config(user: dict = Depends(require_role("admin"))):
    """读取本租户配置（含默认值）。"""
    return tenant_config_service.get_config(user["tenant_id"])


@router.put("/tenant/config")
async def put_tenant_config(req: TenantConfigRequest,
                            user: dict = Depends(require_role("admin"))):
    """更新本租户配置（仅显式提供的字段被覆盖；admin 只能改自己租户）。"""
    cur = dict(tenant_config_service.get_config(user["tenant_id"]))
    cur.update(req.model_dump(exclude_unset=True))
    saved = tenant_config_service.save_config(user["tenant_id"], cur)
    return {"success": True, "config": saved}


# ════════════════════════════════════════════════════════════
# M5 院校组织管理（班级 / 用户 / 分班 / 带班）—— 全部仅本租户
# ════════════════════════════════════════════════════════════

class ClassCreateRequest(BaseModel):
    name: str


class AssignClassRequest(BaseModel):
    class_id: Optional[str] = None   # None = 取消分班


class TeacherClassRequest(BaseModel):
    teacher_id: str
    class_id: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "teacher"                 # teacher / admin / student
    student_id: Optional[str] = None
    class_id: Optional[str] = None


# ── 班级 ─────────────────────────────────────────────────────
@router.get("/classes")
async def list_classes(user: dict = Depends(require_role("admin"))):
    """本租户班级列表 + 每班学生数。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        rows = db.query(ClassGroup).filter(ClassGroup.tenant_id == tid).all()
        return [{
            "id": c.id, "name": c.name,
            "student_count": db.query(User).filter(
                User.tenant_id == tid, User.class_id == c.id).count(),
        } for c in rows]


@router.post("/classes")
async def create_class(req: ClassCreateRequest, user: dict = Depends(require_role("admin"))):
    tid = user["tenant_id"]
    cid = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(ClassGroup(id=cid, tenant_id=tid, name=req.name))
        db.commit()
    return {"id": cid, "name": req.name}


@router.delete("/classes/{class_id}")
async def delete_class(class_id: str, user: dict = Depends(require_role("admin"))):
    """删除班级：连带解除学生分班与教师带班关联（仅本租户）。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        c = db.get(ClassGroup, class_id)
        if not c or c.tenant_id != tid:
            raise HTTPException(status_code=404, detail="班级不存在")
        db.query(User).filter(User.tenant_id == tid, User.class_id == class_id).update(
            {User.class_id: None})
        db.query(TeacherClass).filter(TeacherClass.class_id == class_id).delete()
        db.delete(c)
        db.commit()
    return {"success": True, "deleted": class_id}


# ── 用户 / 学生名册 ──────────────────────────────────────────
@router.get("/users")
async def list_users(role: Optional[str] = Query(None),
                     user: dict = Depends(require_role("admin"))):
    """本租户用户列表（可按 role 过滤）。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        q = db.query(User).filter(User.tenant_id == tid)
        if role:
            q = q.filter(User.role == role)
        return [{
            "id": u.id, "username": u.username, "role": u.role,
            "student_id": u.student_id, "class_id": u.class_id,
        } for u in q.all()]


@router.post("/users")
async def create_user(req: CreateUserRequest, user: dict = Depends(require_role("admin"))):
    """admin 在本租户建账号（teacher/admin/student）——补齐组织管理闭环（建师→带班→分班）。"""
    tid = user["tenant_id"]
    if req.role not in ("teacher", "admin", "student"):
        raise HTTPException(status_code=400, detail="角色非法")
    with SessionLocal() as db:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        uid = str(uuid.uuid4())
        sid = req.student_id or (str(uuid.uuid4()) if req.role == "student" else None)
        db.add(User(id=uid, username=req.username, password_hash=_hash_password(req.password),
                    tenant_id=tid, role=req.role, student_id=sid, class_id=req.class_id))
        db.commit()
    return {"id": uid, "username": req.username, "role": req.role,
            "student_id": sid, "class_id": req.class_id}


@router.get("/roster")
async def admin_roster(user: dict = Depends(require_role("admin"))):
    """学生名册（账号⨝画像⨝匹配摘要，复用 student_directory，与看板同源）。"""
    return {"students": student_directory.roster(user)}


@router.put("/students/{student_id}/class")
async def assign_student_class(student_id: str, req: AssignClassRequest,
                               user: dict = Depends(require_role("admin"))):
    """给学生分班 / 取消分班（class_id=None）。学生账号与目标班级须属本租户。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        stu = db.query(User).filter(
            User.tenant_id == tid, User.student_id == student_id).first()
        if not stu:
            raise HTTPException(status_code=404, detail="学生账号不存在")
        if req.class_id:
            c = db.get(ClassGroup, req.class_id)
            if not c or c.tenant_id != tid:
                raise HTTPException(status_code=400, detail="班级不存在")
        stu.class_id = req.class_id
        db.commit()
    return {"success": True, "student_id": student_id, "class_id": req.class_id}


# ── 教师带班 ─────────────────────────────────────────────────
@router.get("/teacher-classes")
async def list_teacher_classes(user: dict = Depends(require_role("admin"))):
    """本租户教师↔班级 关联（带教师名/班级名）。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        teachers = {u.id: u for u in db.query(User).filter(
            User.tenant_id == tid, User.role == "teacher").all()}
        classes = {c.id: c for c in db.query(ClassGroup).filter(
            ClassGroup.tenant_id == tid).all()}
        links = db.query(TeacherClass).filter(
            TeacherClass.teacher_id.in_(list(teachers.keys()) or [""])).all()
        return [{
            "teacher_id": l.teacher_id, "teacher_name": teachers[l.teacher_id].username,
            "class_id": l.class_id,
            "class_name": classes[l.class_id].name if l.class_id in classes else "",
        } for l in links if l.teacher_id in teachers]


@router.post("/teacher-classes")
async def assign_teacher_class(req: TeacherClassRequest,
                               user: dict = Depends(require_role("admin"))):
    """指派教师带班（教师与班级须属本租户）。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        t = db.query(User).filter(
            User.tenant_id == tid, User.id == req.teacher_id, User.role == "teacher").first()
        c = db.get(ClassGroup, req.class_id)
        if not t:
            raise HTTPException(status_code=400, detail="教师不存在")
        if not c or c.tenant_id != tid:
            raise HTTPException(status_code=400, detail="班级不存在")
        if not db.query(TeacherClass).filter_by(
                teacher_id=req.teacher_id, class_id=req.class_id).first():
            db.add(TeacherClass(teacher_id=req.teacher_id, class_id=req.class_id))
            db.commit()
    return {"success": True}


@router.delete("/teacher-classes")
async def unassign_teacher_class(teacher_id: str = Query(...), class_id: str = Query(...),
                                 user: dict = Depends(require_role("admin"))):
    """解除教师带班（先校验教师属本租户，防跨租户解绑）。"""
    tid = user["tenant_id"]
    with SessionLocal() as db:
        t = db.query(User).filter(User.tenant_id == tid, User.id == teacher_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="教师不存在")
        link = db.query(TeacherClass).filter_by(
            teacher_id=teacher_id, class_id=class_id).first()
        if link:
            db.delete(link)
            db.commit()
    return {"success": True}
