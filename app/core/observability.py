# -*- coding: utf-8 -*-
"""
可观测性：结构化日志 + trace_id 上下文 + 轻量指标。

- setup_logging()：按 settings 配置普通或 JSON 结构化日志。
- trace_id：通过 contextvar 贯穿一次请求/Agent run 的所有日志与指标。
- metrics：进程内计数/计时收集（Phase 4 可接 OpenTelemetry / Prometheus 导出）。
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Dict

from app.config import settings


def _force_utf8_console() -> None:
    """尽早把 stdout/stderr 重配为 UTF-8（errors=replace），
    避免 Windows GBK 控制台遇到 ✓/emoji 等字符在 import 期就抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# 模块导入即生效（早于重型依赖的日志输出）
_force_utf8_console()

# 贯穿全链路的追踪 ID
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex[:16]
    _trace_id.set(tid)
    return tid


def set_trace_id(tid: str) -> None:
    _trace_id.set(tid)


def get_trace_id() -> str:
    return _trace_id.get()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        tid = _trace_id.get()
        if tid:
            payload["trace_id"] = tid
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _TraceFilter(logging.Filter):
    """给普通文本日志注入 trace_id 字段。"""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_id.get() or "-"
        return True


def setup_logging() -> None:
    # Windows 控制台默认 GBK，含非 GBK 字符（如 ✓/emoji）的日志会抛 UnicodeEncodeError。
    # 将 stdout/stderr 重配为 UTF-8（errors=replace），避免日志崩溃。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # 清理既有 handler，避免 uvicorn/重复配置叠加
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if settings.JSON_LOGS:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.addFilter(_TraceFilter())
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"
        ))
    root.addHandler(handler)


# ── 轻量指标 ────────────────────────────────────────────────────
class _Metrics:
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._timers: Dict[str, list] = {}

    def incr(self, name: str, value: float = 1.0) -> None:
        if not settings.ENABLE_METRICS:
            return
        self._counters[name] = self._counters.get(name, 0) + value

    def observe(self, name: str, ms: float) -> None:
        if not settings.ENABLE_METRICS:
            return
        self._timers.setdefault(name, []).append(ms)

    def snapshot(self) -> Dict:
        out = {"counters": dict(self._counters), "timers": {}}
        for k, vals in self._timers.items():
            if not vals:
                continue
            s = sorted(vals)
            out["timers"][k] = {
                "count": len(s),
                "p50_ms": round(s[len(s) // 2], 1),
                "p95_ms": round(s[int(len(s) * 0.95)], 1) if len(s) > 1 else round(s[0], 1),
                "max_ms": round(s[-1], 1),
            }
        return out


metrics = _Metrics()


class timed:
    """上下文管理器：记录一段耗时到指标。

    用法： with timed("agent.tool.compute_match"): ...
    """
    def __init__(self, name: str):
        self.name = name
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        metrics.observe(self.name, (time.perf_counter() - self._t0) * 1000)
        return False
