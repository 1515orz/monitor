import json
import os
import time
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SCENE_KEY = "scene:current"
SCENE_TTL = 5  # seconds

_client = aioredis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    socket_connect_timeout=0.2,
    socket_timeout=0.2,
)

# In-memory fallback when Redis is unavailable
_cache: dict | None = None
_cache_ts: float = 0.0


async def set_scene(scene: dict) -> None:
    global _cache, _cache_ts
    _cache = scene
    _cache_ts = time.monotonic()
    try:
        await _client.set(SCENE_KEY, json.dumps(scene), ex=SCENE_TTL)
    except Exception:
        logger.warning("Redis unavailable; scene stored in memory cache only")


async def get_scene() -> dict | None:
    try:
        raw = await _client.get(SCENE_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        logger.warning("Redis unavailable; falling back to memory cache")

    # Fallback: return memory cache if within TTL
    if _cache is not None and (time.monotonic() - _cache_ts) < SCENE_TTL:
        return _cache
    return None


async def is_redis_alive() -> bool:
    try:
        await _client.ping()
        return True
    except Exception:
        return False
