# -*- coding: utf-8 -*-
"""全局限流器（slowapi），供 main.py 和各路由模块共享同一实例"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
