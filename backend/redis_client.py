import os
from typing import Optional

import redis.asyncio as redis

_redis_client: Optional[redis.Redis] = None


def get_redis_url() -> str:
  """
  Return the Redis URL from environment or a sensible default.
  In Docker, this defaults to the `redis` service defined in docker-compose.
  
  Supports password authentication via:
  1. REDIS_URL with password included: redis://:password@host:port/db
  2. REDIS_PASSWORD environment variable (will be injected into URL if REDIS_URL doesn't contain password)
  """
  redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
  redis_password = os.getenv("REDIS_PASSWORD")
  
  # If REDIS_PASSWORD is set and REDIS_URL doesn't already contain a password, inject it
  if redis_password and "@" not in redis_url:
    # Insert password into URL: redis://:password@host:port/db
    redis_url = redis_url.replace("redis://", f"redis://:{redis_password}@")
  
  return redis_url


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


