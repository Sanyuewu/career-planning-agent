# -*- coding: utf-8 -*-
"""
认证与授权路由（M0 企业化）。

- 身份入库：用户从 data/users.json 平文件迁入 DB（User/Tenant 表），多租户。
- JWT：携带 tenant_id/role/student_id/class_id；密钥从 env（settings.JWT_SECRET）。
- 密码：bcrypt（兼容验证存量 sha256，登录时机会性 rehash）。
- get_current_user：解码令牌 → 设置安全上下文（租户/用户贯穿全链路）。
- 授权：can_access_student / assert_student_access / require_student_access（堵 IDOR）。
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

import bcrypt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings, BASE_DIR
from app.core.database import SessionLocal
from app.core.security_context import set_current_user, DEFAULT_TENANT
from app.models.db_models import User, Tenant, TeacherClass

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────
_DEV_FALLBACK_SECRET = "youtu-graphrag-career-planner-secret-2026"


def _secret_key() -> str:
    """JWT 密钥：优先 env；空则 dev 回退（生产空密钥告警）。"""
    if settings.JWT_SECRET:
        return settings.JWT_SECRET
    if settings.APP_ENV == "production":
        logger.error("JWT_SECRET 未配置（生产环境）——请在 env 设置，当前回退至不安全的开发密钥！")
    return _DEV_FALLBACK_SECRET


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600           # 1 小时
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 天

USERS_FILE = BASE_DIR / "data" / "users.json"

bearer_scheme = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth", tags=["认证"])


# ── 密码哈希（bcrypt，兼容验证存量 sha256）──────────────────
def _hash_password(password: str) -> str:
    # bcrypt 上限 72 字节，超长截断（不影响安全性）
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, stored: str) -> bool:
    try:
        if stored.startswith("$2"):  # bcrypt
            return bcrypt.checkpw(password.encode("utf-8")[:72], stored.encode("utf-8"))
        # 存量 sha256：salt$hex
        salt, h = stored.split("$", 1)
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == h
    except Exception:
        return False


# ── users.json → DB 一次性迁移（幂等）────────────────────────
_users_migrated = False


def _ensure_tenant(db, tenant_id: str) -> None:
    if not db.get(Tenant, tenant_id):
        db.add(Tenant(id=tenant_id, name=tenant_id))


def _migrate_users_json() -> None:
    """首次运行：把 data/users.json 的账号迁入 User 表（保留 json 作冷备）。"""
    global _users_migrated
    if _users_migrated:
        return
    _users_migrated = True
    if not USERS_FILE.exists():
        return
    try:
        import json
        users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        with SessionLocal() as db:
            _ensure_tenant(db, DEFAULT_TENANT)
            for uname, u in (users or {}).items():
                if db.query(User).filter(User.username == uname).first():
                    continue
                db.add(User(
                    id=str(uuid.uuid4()),
                    username=uname,
                    password_hash=u.get("password_hash", ""),  # 存量 sha256，登录时 rehash
                    tenant_id=DEFAULT_TENANT,
                    role=u.get("role", "student"),
                    student_id=u.get("student_id"),
                    class_id=None,
                ))
            db.commit()
        logger.info("[auth] users.json 已迁入 DB User 表")
    except Exception as e:
        logger.warning("[auth] 迁移 users.json 失败: %s", e)


# ── JWT ───────────────────────────────────────────────
def _create_token(data: dict, expires_seconds: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])


def _build_auth_result(username: str, student_id: str, role: str,
                       tenant_id: str, user_id: str, class_id: Optional[str]) -> dict:
    claims = {
        "sub": username, "user_id": user_id, "student_id": student_id,
        "role": role, "tenant_id": tenant_id, "class_id": class_id,
    }
    return {
        "access_token": _create_token(claims, ACCESS_TOKEN_EXPIRE_SECONDS),
        "refresh_token": _create_token({**claims, "type": "refresh"}, REFRESH_TOKEN_EXPIRE_SECONDS),
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "student_id": student_id,
        "username": username,
        "role": role,
        "tenant_id": tenant_id,
    }


# ── 当前用户依赖（设置安全上下文）────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        if not settings.AUTH_ENFORCED:
            # dev 便捷：无 token 落 default 租户 admin（保持单机基线可手测）
            user = {"user_id": "dev-admin", "username": "dev", "student_id": "",
                    "role": "admin", "tenant_id": DEFAULT_TENANT, "class_id": None}
            set_current_user(user)
            return user
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    try:
        payload = _decode_token(credentials.credentials)
        username: str = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=401, detail="令牌无效")
        user = {
            "user_id": payload.get("user_id", ""),
            "username": username,
            "student_id": payload.get("student_id", ""),
            "role": payload.get("role", "student"),
            "tenant_id": payload.get("tenant_id", DEFAULT_TENANT),
            "class_id": payload.get("class_id"),
        }
        set_current_user(user)   # 租户/用户贯穿后续同步引擎与存储层
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="令牌已过期或无效")


# ── 授权：数据范围裁决（堵 IDOR）────────────────────────────
def _student_in_teacher_classes(student_id: str, teacher_id: str) -> bool:
    with SessionLocal() as db:
        stu = db.query(User).filter(User.student_id == student_id).first()
        if not stu or not stu.class_id:
            return False
        link = db.query(TeacherClass).filter(
            TeacherClass.teacher_id == teacher_id,
            TeacherClass.class_id == stu.class_id,
        ).first()
        return link is not None


def can_access_student(user: dict, student_id: str) -> bool:
    """student=本人；teacher=本人所带班的学生；admin=本租户（跨租户已由存储层 tenant 过滤拦截）。"""
    if not student_id:
        return False
    role = user.get("role", "student")
    if role == "admin":
        return True
    if role == "teacher":
        return _student_in_teacher_classes(student_id, user.get("user_id", ""))
    return user.get("student_id") == student_id


def assert_student_access(user: dict, student_id: str) -> None:
    if not can_access_student(user, student_id):
        raise HTTPException(status_code=403, detail="无权访问该学生数据")


async def require_student_access(
    student_id: str, user: dict = Depends(get_current_user),
) -> dict:
    """路由依赖：用于 path 含 {student_id} 的端点，越权直接 403。"""
    assert_student_access(user, student_id)
    return user


def require_role(*roles: str):
    """RBAC 依赖工厂：限定端点仅指定角色可访问（如 require_role("admin")）。"""
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="需要更高权限")
        return user
    return _dep


def visible_student_ids(user: dict) -> Optional[Set[str]]:
    """数据范围门（**安全单一事实源**，看板/管理共用）：当前用户可见的学生 student_id 集合。
    admin→None（本租户全部，租户隔离由存储层保证）；teacher→其所带班级的学生；其它→空集。"""
    role = user.get("role")
    if role == "admin":
        return None
    if role != "teacher":
        return set()
    with SessionLocal() as db:
        class_ids = [tc.class_id for tc in db.query(TeacherClass).filter(
            TeacherClass.teacher_id == user.get("user_id", "")).all()]
        if not class_ids:
            return set()
        rows = db.query(User.student_id).filter(
            User.class_id.in_(class_ids), User.student_id.isnot(None)).all()
        return {r[0] for r in rows if r[0]}


# ── 请求模型 ──────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    password: str
    student_id: Optional[str] = None
    role: str = "student"
    tenant_id: Optional[str] = None
    class_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── 路由 ──────────────────────────────────────────────
@router.post("/register")
async def register(req: RegisterRequest):
    """自助注册——**仅能建学生账号**（安全：不接受自助提权）。
    teacher/admin 由院校 admin 经 /api/admin/users 建；platform_admin 仅脚本种子。
    role/student_id 由服务端强制，忽略请求里的提权尝试。"""
    _migrate_users_json()
    tenant_id = req.tenant_id or DEFAULT_TENANT   # 学生可凭学校租户码自助加入；管理员后续分班
    with SessionLocal() as db:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        _ensure_tenant(db, tenant_id)
        user_id = str(uuid.uuid4())
        student_id = str(uuid.uuid4())            # 一律新生成，不接受自带 student_id
        db.add(User(
            id=user_id, username=req.username,
            password_hash=_hash_password(req.password),
            tenant_id=tenant_id, role="student",  # 强制学生，堵自助提权洞
            student_id=student_id, class_id=None,
        ))
        db.commit()
    return _build_auth_result(req.username, student_id, "student", tenant_id, user_id, None)


@router.post("/login")
async def login(req: LoginRequest):
    """登录"""
    _migrate_users_json()
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not _verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        # 存量 sha256 登录成功 → 机会性升级为 bcrypt
        if not user.password_hash.startswith("$2"):
            user.password_hash = _hash_password(req.password)
            db.commit()
        return _build_auth_result(user.username, user.student_id or "", user.role,
                                  user.tenant_id, user.id, user.class_id)


@router.post("/refresh")
async def refresh_token(req: RefreshRequest):
    """刷新 access_token"""
    try:
        payload = _decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="非刷新令牌")
        username = payload.get("sub", "")
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                raise HTTPException(status_code=401, detail="用户不存在")
            return _build_auth_result(user.username, user.student_id or "", user.role,
                                      user.tenant_id, user.id, user.class_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="刷新令牌已过期或无效")


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """当前登录用户信息"""
    return user
