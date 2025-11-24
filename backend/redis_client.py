import os
import logging
from typing import Optional
from contextvars import ContextVar

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Global Redis client singleton shared across all requests
_global_redis_client: Optional[redis.Redis] = None

# Use ContextVar to allow per-context (per-test) Redis client overrides
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
  Get a shared async Redis client instance.
  
  Priority:
  1. ContextVar (for test overrides)
  2. Global singleton (shared across all HTTP requests)
  
  This ensures all HTTP requests share the same connection pool while
  still allowing tests to inject mock clients via ContextVar.
  """
  global _global_redis_client
  
  # Check ContextVar first (for test overrides)
  client = _redis_client.get()
  if client is not None:
    return client
  
  # Use global singleton for all requests
  if _global_redis_client is None:
    redis_url = get_redis_url()
    # Hide password in logs for security
    log_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
    logger.info(f"Creating global Redis client singleton with connection pool (max_connections=100, socket_timeout=5)")
    logger.info(f"Redis URL: {log_url}")
    _global_redis_client = redis.from_url(
      redis_url,
      encoding="utf-8",
      decode_responses=True,
      max_connections=100,
      socket_timeout=5
    )
    logger.info("Global Redis client singleton created successfully")
  return _global_redis_client


def _set_test_redis_client(client: redis.Redis) -> None:
  """
  Internal helper function to set a test Redis client.
  Used by pytest fixtures to inject mock Redis clients per test context.
  """
  _redis_client.set(client)


async def close_redis_client() -> None:
  """
  Gracefully close the Redis client on application shutdown.
  Closes both the ContextVar client (if set) and the global client.
  """
  global _global_redis_client
  
  # Close ContextVar client if set
  client = _redis_client.get()
  if client is not None:
    await client.aclose()
    _redis_client.set(None)
  
  # Close global client if set
  if _global_redis_client is not None:
    logger.info("Closing global Redis client singleton")
    await _global_redis_client.aclose()
    _global_redis_client = None
    logger.info("Global Redis client singleton closed")


