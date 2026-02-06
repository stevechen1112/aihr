"""
Admin Service Redis 快取（T4-18）
==================================

獨立 Redis 實例，用於：
- Admin Dashboard 資料快取（5 分鐘 TTL）
- Analytics 結果快取
- 避免重複計算影響主 Redis
"""

import os
import json
import hashlib
import logging
from functools import wraps
from typing import Optional

import redis

logger = logging.getLogger("unihr.admin_service.cache")

# 連線到獨立的 Admin Redis（預設 fallback 到主 Redis 的 DB 2）
ADMIN_REDIS_URL = os.getenv(
    "ADMIN_REDIS_URL",
    f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/2"
)

try:
    admin_redis = redis.from_url(ADMIN_REDIS_URL, decode_responses=True)
    admin_redis.ping()
    _redis_available = True
    logger.info("✅ Admin Redis connected: %s", ADMIN_REDIS_URL)
except Exception as e:
    admin_redis = None
    _redis_available = False
    logger.warning("⚠️ Admin Redis unavailable: %s — caching disabled", e)


# ---------------------------------------------------------------------------
# 快取常數
# ---------------------------------------------------------------------------
DEFAULT_TTL = 300        # 5 分鐘
DASHBOARD_TTL = 300      # Dashboard 數據
ANALYTICS_TTL = 600      # Analytics 結果 10 分鐘
TENANT_LIST_TTL = 120    # 租戶列表 2 分鐘


def cache_key(*parts: str) -> str:
    """生成快取 key"""
    return "admin:" + ":".join(str(p) for p in parts)


def get_cached(key: str) -> Optional[dict]:
    """取得快取值"""
    if not _redis_available or admin_redis is None:
        return None
    try:
        data = admin_redis.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.debug("Cache get error: %s", e)
        return None


def set_cached(key: str, value: dict, ttl: int = DEFAULT_TTL) -> None:
    """設定快取值"""
    if not _redis_available or admin_redis is None:
        return
    try:
        admin_redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug("Cache set error: %s", e)


def invalidate(pattern: str = "admin:*") -> int:
    """清除快取"""
    if not _redis_available or admin_redis is None:
        return 0
    try:
        keys = admin_redis.keys(pattern)
        if keys:
            return admin_redis.delete(*keys)
        return 0
    except Exception as e:
        logger.debug("Cache invalidate error: %s", e)
        return 0


def cached_response(prefix: str, ttl: int = DEFAULT_TTL):
    """
    Decorator：快取 API 回應

    Usage:
        @cached_response("dashboard", ttl=300)
        async def get_dashboard(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 從 kwargs 中提取可快取的參數
            cache_params = {k: v for k, v in kwargs.items()
                           if k not in ("db", "current_user")}
            param_hash = hashlib.md5(
                json.dumps(cache_params, sort_keys=True, default=str).encode()
            ).hexdigest()[:12]

            key = cache_key(prefix, param_hash)
            cached = get_cached(key)
            if cached is not None:
                return cached

            result = await func(*args, **kwargs)

            # 如果結果是 dict 或可序列化的，就快取
            if isinstance(result, dict):
                set_cached(key, result, ttl)

            return result
        return wrapper
    return decorator
