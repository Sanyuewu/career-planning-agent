# -*- coding: utf-8 -*-
"""
可靠性原语：超时、重试、熔断。可复用于 LLM 调用与外部 HTTP（检索服务）。

提供异步装饰器与一个通用熔断器：
  @with_timeout(seconds)
  @with_retry(retries=2, base_delay=0.5, exceptions=(...))
  CircuitBreaker(threshold, cooldown)
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def with_timeout(seconds: float) -> Callable:
    """为异步函数加超时。超时抛 asyncio.TimeoutError。"""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(fn(*args, **kwargs), timeout=seconds)
        return wrapper
    return deco


def with_retry(
    retries: int = 2,
    base_delay: float = 0.5,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """异步重试，指数退避（base_delay * 2**attempt）。耗尽后抛最后一次异常。"""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last = None
            for attempt in range(retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    if attempt < retries:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        logger.warning("retry %s (%d/%d): %s", fn.__name__, attempt + 1, retries, e)
            raise last
        return wrapper
    return deco


class CircuitBreaker:
    """
    通用熔断器：连续失败 >= threshold 打开；冷却 cooldown 秒后半开试探。
    用法：
        cb = CircuitBreaker()
        if cb.allow():
            try: ...; cb.record_success()
            except: cb.record_failure(); ...
    """
    def __init__(self, threshold: int = 3, cooldown: int = 30):
        self.threshold = threshold
        self.cooldown = cooldown
        self._fails = 0
        self._opened_at = 0.0

    def allow(self) -> bool:
        if self._fails < self.threshold:
            return True
        return (time.time() - self._opened_at) >= self.cooldown

    def record_success(self) -> None:
        self._fails = 0
        self._opened_at = 0.0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= self.threshold:
            self._opened_at = time.time()

    @property
    def is_open(self) -> bool:
        return self._fails >= self.threshold and (time.time() - self._opened_at) < self.cooldown
