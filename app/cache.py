# -*- coding: utf-8 -*-
"""跨路由共享缓存对象，避免各模块重复定义"""
from cachetools import TTLCache

# 岗位推荐缓存：30分钟，最多1000条
recommend_cache: TTLCache = TTLCache(maxsize=1000, ttl=1800)

# 市场趋势缓存：1小时
market_trends_cache: dict = {"data": None, "timestamp": 0}
MARKET_TRENDS_CACHE_TTL = 3600

# AI岗位洞察缓存：进程级，不设过期
ai_insight_cache: dict = {}
