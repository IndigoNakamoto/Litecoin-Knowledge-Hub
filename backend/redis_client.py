import os
from typing import Optional
from contextvars import ContextVar

import redis.asyncio as redis

# Use ContextVar to allow per-context (per-test) Redis clients
# This solves the "different event loop" problem in async tests
_redis_client: ContextVar[Optional[redis.Redis]] = ContextVar("redis_client", default=None)


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


async def get_redis_client() -> redis.Redis:
  """
  Get a shared async Redis client instance for the current context.
  Uses ContextVar to allow per-test mocking in pytest-asyncio tests.
  This is safe to use across the app; redis-py manages connection pooling.
  """
  client = _redis_client.get()
  if client is None:
    client = redis.from_url(get_redis_url(), encoding="utf-8", decode_responses=True)
    _redis_client.set(client)
  return client


def _set_test_redis_client(client: redis.Redis) -> None:
  """
  Internal helper function to set a test Redis client.
  Used by pytest fixtures to inject mock Redis clients per test context.
  """
  _redis_client.set(client)


async def close_redis_client() -> None:
  """
  Gracefully close the Redis client on application shutdown.
  """
  client = _redis_client.get()
  if client is not None:
    await client.aclose()
    _redis_client.set(None)


