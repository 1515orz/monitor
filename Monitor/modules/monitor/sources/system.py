import os

import redis.asyncio as aioredis

from modules.monitor import video_stream

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

_redis_client = aioredis.Redis(
    host=REDIS_HOST, port=REDIS_PORT,
    socket_connect_timeout=0.2,
    socket_timeout=0.2,
)


async def fetch_system_status() -> dict[str, object]:
    redis_ok = False
    try:
        await _redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "fps": video_stream.get_fps(),
        "redis": redis_ok,
        "zmq": video_stream.is_connected(),
    }
