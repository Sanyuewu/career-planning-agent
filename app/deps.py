# -*- coding: utf-8 -*-
"""
共享依赖：JWT 认证守卫、审计日志
供 app/routers/ 下各路由模块 import 使用
"""
import logging
import re
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

_audit_logger = logging.getLogger("audit")


def _mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """脱敏敏感数据，仅保留前后各visible_chars字符"""
    if not value or len(value) <= visible_chars * 2:
        return "***"
    return f"{value[:visible_chars]}***{value[-visible_chars:]}"


def _mask_student_id(student_id: str) -> str:
    if not student_id:
        return ""
    if student_id.startswith("student_"):
        return f"student_{_mask_sensitive(student_id[8:], 2)}"
    return _mask_sensitive(student_id, 2)


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 7:
        return "***"
    return f"{phone[:3]}****{phone[-3:]}"


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    parts = email.split("@")
    return f"{parts[0][:2]}***@{parts[1]}"


def audit_log(action: str, resource: str, resource_id: str, detail: str = "") -> None:
    masked_id = _mask_sensitive(resource_id) if resource_id else ""
    masked_detail = detail
    if "student_id=" in detail:
        masked_detail = re.sub(
            r'student_id=([a-zA-Z0-9_]+)',
            lambda m: f'student_id={_mask_sensitive(m.group(1))}',
            detail,
        )
    _audit_logger.info(f"[AUDIT] action={action} resource={resource} id={masked_id} {masked_detail}")


async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[dict]:
    """可选认证守卫：有 token 时验证，无 token 时返回 None"""
    if not cred:
        return None
    try:
        return jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期")


def require_role(*roles: str):
    """角色权限守卫，用于 Depends()，强制要求指定角色之一"""
    async def _guard(cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
        if not cred:
            raise HTTPException(status_code=401, detail="请先登录")
        try:
            payload = jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token无效或已过期")
        if payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return payload
    return _guard
