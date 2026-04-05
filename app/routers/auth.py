# -*- coding: utf-8 -*-
"""认证路由：/api/auth/*"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import select as sa_select

from app.auth_utils import hash_password, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.db import get_db_session
from app.db.models import UserModel, StudentModel
from app.deps import get_current_user, require_role, audit_log
from app.rate_limit import limiter
from app.schemas.api import AuthRegisterRequest, AuthLoginRequest, AuthTokenResponse, RefreshTokenRequest, ChangePasswordRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=AuthTokenResponse)
async def register(req: AuthRegisterRequest):
    """用户注册：创建账号并持久化到DB"""
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    async with get_db_session() as session:
        existing = await session.execute(
            sa_select(UserModel).where(UserModel.username == req.username)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已存在")

        student_id = req.student_id or f"student_{uuid.uuid4().hex[:12]}"
        hashed = hash_password(req.password)
        user = UserModel(
            username=req.username,
            hashed_password=hashed,
            student_id=student_id,
            role=req.role,
        )
        session.add(user)
        session.add(StudentModel(student_id=student_id))

    token = create_access_token({"sub": req.username, "student_id": student_id, "role": req.role})
    audit_log("REGISTER", "user", req.username, f"role={req.role} student_id={student_id}")
    return AuthTokenResponse(access_token=token, student_id=student_id, username=req.username, role=req.role)


@router.post("/login", response_model=AuthTokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: AuthLoginRequest):
    """用户登录：从DB验证密码并返回 JWT + 刷新令牌"""
    async with get_db_session() as session:
        result = await session.execute(
            sa_select(UserModel).where(UserModel.username == req.username)
        )
        user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        audit_log("LOGIN_FAIL", "user", req.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token_payload = {"sub": user.username, "student_id": user.student_id, "role": user.role}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token({"sub": user.username})

    audit_log("LOGIN", "user", user.username, f"student_id={user.student_id}")
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        student_id=user.student_id,
        username=user.username,
        role=user.role or "student",
    )


@router.post("/refresh", response_model=AuthTokenResponse)
@limiter.limit("30/minute")
async def refresh_token(request: Request, req: RefreshTokenRequest):
    """刷新访问令牌"""
    payload = verify_refresh_token(req.refresh_token)
    username = payload.get("sub")

    async with get_db_session() as session:
        result = await session.execute(sa_select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    new_access = create_access_token({"sub": user.username, "student_id": user.student_id, "role": user.role})
    new_refresh = create_refresh_token({"sub": user.username})
    return AuthTokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        student_id=user.student_id,
        username=user.username,
        role=user.role or "student",
    )


@router.get("/me")
async def get_me(current_user: Optional[dict] = Depends(get_current_user)):
    """获取当前登录用户信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    return {
        "username": current_user.get("sub"),
        "student_id": current_user.get("student_id"),
        "role": current_user.get("role", "student"),
    }


@router.put("/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(require_role("student", "company", "admin")),
):
    """修改当前登录用户的密码"""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少6位")
    username = current_user.get("sub")
    async with get_db_session() as session:
        result = await session.execute(sa_select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not verify_password(req.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码错误")
        user.hashed_password = hash_password(req.new_password)
    audit_log("CHANGE_PASSWORD", "user", username)
    return {"ok": True, "message": "密码修改成功"}
