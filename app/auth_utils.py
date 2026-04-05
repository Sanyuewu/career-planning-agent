# -*- coding: utf-8 -*-
"""认证工具函数：密码哈希、JWT创建/校验"""
from datetime import datetime, timedelta

import bcrypt as _bcrypt_lib
from fastapi import HTTPException
from jose import jwt, JWTError

from app.config import settings


def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode("utf-8")[:72], _bcrypt_lib.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _bcrypt_lib.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload["type"] = "access"
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=7)
    payload["type"] = "refresh"
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的刷新令牌")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="刷新令牌已过期，请重新登录")
