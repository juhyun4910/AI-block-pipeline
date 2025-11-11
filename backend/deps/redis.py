"""Redis 클라이언트 의존성.

비전공자 팁: Redis는 빠른 메모리 데이터베이스로, 작업 큐와 레이트리밋에 사용됩니다.
"""
from __future__ import annotations

import redis.asyncio as redis

from backend.deps.settings import settings


def get_redis() -> redis.Redis:
    """레이트리밋 등에서 사용할 Redis 클라이언트."""

    return redis.from_url(settings.redis_url, decode_responses=True)


__all__ = ["get_redis"]
