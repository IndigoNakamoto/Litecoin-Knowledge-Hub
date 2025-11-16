import os
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

from backend.redis_client import get_redis_client
from backend.monitoring.metrics import rate_limit_rejections_total


@dataclass
class RateLimitConfig:
  requests_per_minute: int
  requests_per_hour: int
  identifier: str  # e.g. "chat", "chat_stream"


def _get_ip_from_request(request: Request) -> str:
  """
  Extract client IP, preferring Cloudflare / proxy headers when present.
  """
  # Cloudflare header
  cf_ip = request.headers.get("CF-Connecting-IP")
  if cf_ip:
    return cf_ip

  # Standard proxy header
  xff = request.headers.get("X-Forwarded-For")
  if xff:
    # XFF may contain a list of IPs. The left-most is the original client.
    return xff.split(",")[0].strip()

  client_host = request.client.host if request.client else "unknown"
  return client_host


async def check_rate_limit(request: Request, config: RateLimitConfig) -> None:
  """
  Enforce rate limits based on client IP and endpoint-specific configuration.
  Uses a simple fixed-window counter in Redis for minute and hour windows.
  """
  redis = get_redis_client()
  client_ip = _get_ip_from_request(request)
  now = int(time.time())

  # Fixed windows: align to current minute / hour
  current_minute = now // 60
  current_hour = now // 3600

  base_key = f"rl:{config.identifier}:{client_ip}"
  minute_key = f"{base_key}:m:{current_minute}"
  hour_key = f"{base_key}:h:{current_hour}"

  # Atomically increment counters and set TTLs
  async with redis.pipeline(transaction=True) as pipe:
    pipe.incr(minute_key)
    pipe.expire(minute_key, 90)  # slightly longer than a minute
    pipe.incr(hour_key)
    pipe.expire(hour_key, 3700)  # slightly longer than an hour
    minute_count, _, hour_count, _ = await pipe.execute()

  # Check limits
  exceeded_minute = minute_count > config.requests_per_minute
  exceeded_hour = hour_count > config.requests_per_hour

  if exceeded_minute or exceeded_hour:
    # Record metrics
    rate_limit_rejections_total.labels(endpoint_type=config.identifier).inc()
    # Compute an approximate Retry-After in seconds
    retry_after = 60 if exceeded_minute else 3600
    detail = {
      "error": "rate_limited",
      "message": "Too many requests. Please slow down.",
      "limits": {
        "per_minute": config.requests_per_minute,
        "per_hour": config.requests_per_hour,
      },
    }
    headers = {"Retry-After": str(retry_after)}
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail=detail,
      headers=headers,
    )


