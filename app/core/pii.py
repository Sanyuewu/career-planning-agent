# -*- coding: utf-8 -*-
"""
PII 静态保护：对落库的文档型数据（学生画像/报告/会话）做**透明的字段级加密**。

设计：
- 在存储层（PersistentStore / AsyncKVStore）的 value_json 写入前 encrypt、读取后 decrypt，
  内存与业务层始终拿明文——匹配引擎/报告生成零感知。DB at rest 持密文。
- **可降级**：未配置 PII_ENCRYPT_KEY 时 encrypt/decrypt 均为恒等（no-op），
  不破坏单进程基线；生产配置 Fernet 密钥后即获得静态加密能力。
- 前缀 `enc:v1:` 标识密文：存量明文行被 decrypt 原样放行；密钥缺失时密文也原样放行
  （不破坏、不误解析），便于渐进加密与密钥轮换。

依赖 cryptography（已随 python-jose[cryptography] 安装，无新增依赖）。
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "enc:v1:"
_fernet = None
_fernet_key = None


def _get_fernet():
    """惰性构建并缓存 Fernet（密钥变更时重建）。无密钥/不可用返回 None。"""
    global _fernet, _fernet_key
    key = settings.PII_ENCRYPT_KEY or ""
    if not key:
        return None
    if _fernet is not None and _fernet_key == key:
        return _fernet
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode())
        _fernet_key = key
        return _fernet
    except Exception as e:
        logger.warning("[pii] PII_ENCRYPT_KEY 无效，PII 加密禁用: %s", e)
        return None


def encrypt_text(s: Optional[str]) -> Optional[str]:
    """加密字符串（含前缀标识）。无密钥或非字符串时原样返回（no-op）。"""
    f = _get_fernet()
    if f is None or not isinstance(s, str) or s.startswith(_PREFIX):
        return s
    try:
        return _PREFIX + f.encrypt(s.encode("utf-8")).decode("ascii")
    except Exception:
        return s


def decrypt_text(s: Optional[str]) -> Optional[str]:
    """解密带前缀的密文。非密文/无密钥/解密失败时原样返回。"""
    if not isinstance(s, str) or not s.startswith(_PREFIX):
        return s
    f = _get_fernet()
    if f is None:
        return s  # 无密钥：保留密文，不误解析
    try:
        from cryptography.fernet import InvalidToken
        try:
            return f.decrypt(s[len(_PREFIX):].encode("ascii")).decode("utf-8")
        except InvalidToken:
            return s
    except Exception:
        return s


def is_enabled() -> bool:
    return _get_fernet() is not None
