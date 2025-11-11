"""간단 토큰 버킷 레이트리밋."""
from __future__ import annotations

import time

from fastapi import HTTPException, status

from backend.deps.redis import get_redis


async def enforce_rate_limit(key: str, limit: int = 60, window: int = 60) -> None:
    """주어진 키(IP/토큰)에 대해 분당 호출 수 제한."""

    redis = get_redis()
    now = int(time.time())
    bucket_key = f"rate:{key}:{now // window}"
    current = await redis.incr(bucket_key)
    if current == 1:
        await redis.expire(bucket_key, window)
    if current > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded")
