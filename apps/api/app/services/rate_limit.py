import hashlib
import time
from functools import lru_cache

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import OpenAIAPIError


@lru_cache(maxsize=1)
def _client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)


def _safe_key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def _keys(kind: str, user_id: str, api_key_id: str) -> list[str]:
    return [f"{kind}:user:{_safe_key(user_id)}", f"{kind}:key:{_safe_key(api_key_id)}"]


def _unavailable() -> OpenAIAPIError:
    return OpenAIAPIError("API access checks temporarily unavailable.", error_type="api_error", code="access_unavailable", status_code=503)


def check_api_rate_limit(*, user_id: str, api_key_id: str) -> None:
    keys = [f"{key}:{int(time.time() // 60)}" for key in _keys("ratelimit", user_id, api_key_id)]
    script = """
    for i=1,2 do
      if tonumber(redis.call('GET',KEYS[i]) or '0') >= tonumber(ARGV[i]) then return 0 end
    end
    for i=1,2 do
      redis.call('INCR',KEYS[i]); redis.call('EXPIRE',KEYS[i],65)
    end
    return 1
    """
    try:
        allowed = _client().eval(script, 2, *keys, settings.api_requests_per_minute_per_user, settings.api_requests_per_minute_per_key)
    except RedisError as exc:
        raise _unavailable() from exc
    if not allowed:
        raise OpenAIAPIError("Rate limit exceeded. Please try again later.", error_type="rate_limit_error", code="rate_limit_exceeded", status_code=429)


def acquire_concurrency_slot(*, user_id: str, api_key_id: str) -> None:
    # No unsafe TTL: a long stream must not lose its concurrency protection.
    # After a process crash, stale counters require operator reconciliation.
    script = """
    for i=1,2 do
      if tonumber(redis.call('GET',KEYS[i]) or '0') >= tonumber(ARGV[1]) then return 0 end
    end
    for i=1,2 do redis.call('INCR',KEYS[i]) end
    return 1
    """
    try:
        allowed = _client().eval(script, 2, *_keys("concurrency", user_id, api_key_id), settings.api_max_concurrent_requests)
    except RedisError as exc:
        raise _unavailable() from exc
    if not allowed:
        raise OpenAIAPIError("Rate limit exceeded. Please try again later.", error_type="rate_limit_error", code="concurrency_limit_exceeded", status_code=429)


def release_concurrency_slot(*, user_id: str, api_key_id: str) -> None:
    script = """
    for i=1,2 do
      local value=tonumber(redis.call('GET',KEYS[i]) or '0')
      if value > 1 then redis.call('DECR',KEYS[i]) else redis.call('DEL',KEYS[i]) end
    end
    return 1
    """
    try:
        _client().eval(script, 2, *_keys("concurrency", user_id, api_key_id))
    except RedisError:
        # Retain the slot; never fail open or replace a successful billing result.
        pass
