import asyncio
import time

from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url)
    return _redis


_LOCK_LUA = """
local last = redis.call('GET', KEYS[1])
local now = tonumber(ARGV[1])
local min_interval_ms = tonumber(ARGV[2])
if last and (now - tonumber(last)) < min_interval_ms then
  return now - tonumber(last)
end
redis.call('SET', KEYS[1], now, 'PX', min_interval_ms * 10)
return 0
"""


async def acquire_host_slot(host: str, min_interval_seconds: float) -> None:
    """Per-host rate limiting (not per-source — a competitor may have
    several tracked pages on one domain, docs/scraping.md). Polls a Redis
    key holding the last-request timestamp for this host, atomically
    checked-and-set via a Lua script so concurrent workers on the same
    host never both pass the gate for the same window."""
    redis = _get_redis()
    min_interval_ms = int(min_interval_seconds * 1000)
    key = f"crawl:host_rate_limit:{host}"

    while True:
        now_ms = int(time.time() * 1000)
        wait_ms = await redis.eval(_LOCK_LUA, 1, key, now_ms, min_interval_ms)
        if wait_ms == 0:
            return
        await asyncio.sleep(wait_ms / 1000)
