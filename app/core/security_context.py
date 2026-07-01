# -*- coding: utf-8 -*-
"""
安全上下文：把"当前用户 + 当前租户"通过 contextvar 贯穿一次请求的全链路。

为什么用 contextvar（复刻 observability.py 的 trace_id 模式）：
匹配引擎 / student_graph_service 是**同步**代码，被路由、Agent 工具、后台任务从
多处调用。若靠改函数签名层层透传 tenant，改动面巨大且易漏。contextvar 让这些
同步代码无需改签名即可读到当前租户，实现行级多租户隔离。

降级：未登录 / 无租户上下文（dev、测试、后台启动）时落到单一 DEFAULT_TENANT，
行为与改造前一致——不破坏单进程 SQLite 基线。
"""

from contextvars import ContextVar
from typing import Dict, Optional

# 单租户/历史数据的缺省租户名。多校上线前的存量数据全部归此租户。
DEFAULT_TENANT = "default"

_tenant_id: ContextVar[str] = ContextVar("tenant_id", default=DEFAULT_TENANT)
_current_user: ContextVar[Optional[Dict]] = ContextVar("current_user", default=None)


def set_tenant(tenant_id: Optional[str]) -> None:
    _tenant_id.set(tenant_id or DEFAULT_TENANT)


def get_tenant() -> str:
    return _tenant_id.get() or DEFAULT_TENANT


def set_current_user(user: Optional[Dict]) -> None:
    """设置当前用户，并同步把租户上下文切到该用户所属租户。"""
    _current_user.set(user)
    if user:
        set_tenant(user.get("tenant_id"))


def get_current_user_ctx() -> Optional[Dict]:
    return _current_user.get()


def reset_context() -> None:
    """请求结束 / 测试隔离时复位（避免 contextvar 跨请求泄漏）。"""
    _tenant_id.set(DEFAULT_TENANT)
    _current_user.set(None)
