from __future__ import annotations

import hashlib
import time

from fastapi import status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import OpenAIAPIError


DEFAULT_REQUESTS_PER_MINUTE = 60
WINDOW_SECONDS = 60


def _client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _safe_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def check_api_rate_limit(*, user_id: str, api_key_id: str) -> None:
    user_key = f"ratelimit:user:{_safe_key(user_id)}"
    api_key = f"ratelimit:key:{_safe_key(api_key_id)}"

    try:
        client = _client()
        now_bucket = int(time.time() // WINDOW_SECONDS)

        limits = {
            f"{user_key}:{now_bucket}": settings.api_requests_per_minute_per_user or DEFAULT_REQUESTS_PER_MINUTE,
            f"{api_key}:{now_bucket}": settings.api_requests_per_minute_per_key or DEFAULT_REQUESTS_PER_MINUTE,
        }

        for key, limit in limits.items():
            current = client.incr(key)
            if current == 1:
                client.expire(key, WINDOW_SECONDS + 5)
            if current > limit:
                raise OpenAIAPIError(
                    "Rate limit exceeded. Please try again later.",
                    error_type="rate_limit_error",
                    code="rate_limit_exceeded",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
    except OpenAIAPIError:
        raise
    except RedisError:
        return


def acquire_concurrency_slot(*, user_id: str, api_key_id: str) -> None:
    user_key = f"concurrency:user:{_safe_key(user_id)}"
    api_key_key = f"concurrency:key:{_safe_key(api_key_id)}"

    try:
        client = _client()
        for key in (user_key, api_key_key):
            current = client.incr(key)
            client.expire(key, WINDOW_SECONDS + 5)
            if current > settings.api_max_concurrent_requests:
                client.decr(key)
                raise OpenAIAPIError(
                    "Rate limit exceeded. Please try again later.",
                    error_type="rate_limit_error",
                    code="concurrency_limit_exceeded",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
    except OpenAIAPIError:
        raise
    except RedisError:
        return


def release_concurrency_slot(*, user_id: str, api_key_id: str) -> None:
    user_key = f"concurrency:user:{_safe_key(user_id)}"
    api_key_key = f"concurrency:key:{_safe_key(api_key_id)}"
    try:
        client = _client()
        for key in (user_key, api_key_key):
            current = client.decr(key)
            if current < 0:
                client.set(key, 0, ex=WINDOW_SECONDS + 5)
    except RedisError:
        return
