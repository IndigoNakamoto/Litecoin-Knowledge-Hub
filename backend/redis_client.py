import os
from typing import Optional

import redis.asyncio as redis

_redis_client: Optional[redis.Redis] = None


def get_redis_url() -> str:
  """
  Return the Redis URL from environment or a sensible default.
  In Docker, this defaults to the `redis` service defined in docker-compose.
  """
  return os.getenv("REDIS_URL", "redis://redis:6379/0")


def get_redis_client() -> redis.Redis:
  """
  Get a shared async Redis client instance.
  This is safe to use across the app; redis-py manages connection pooling.
  """
  global _redis_client
  if _redis_client is None:
    _redis_client = redis.from_url(get_redis_url(), encoding="utf-8", decode_responses=True)
  return _redis_client


async def close_redis_client() -> None:
  """
  Gracefully close the Redis client on application shutdown.
  """
  global _redis_client
  if _redis_client is not None:
    await _redis_client.aclose()
    _redis_client = None


