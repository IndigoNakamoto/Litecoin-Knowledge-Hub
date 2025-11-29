import os
import time
import uuid
import ipaddress
from dataclasses import dataclass, field
from typing import Optional, List

from fastapi import HTTPException, Request, status

from backend.redis_client import get_redis_client
from backend.monitoring.metrics import (
    rate_limit_rejections_total,
    rate_limit_bans_total,
    rate_limit_violations_total,
)


@dataclass
class RateLimitConfig:
  requests_per_minute: int
  requests_per_hour: int
  identifier: str  # e.g. "chat", "chat_stream"
  enable_progressive_limits: bool = True
  progressive_ban_durations: List[int] = field(
      default_factory=lambda: [60, 300, 900, 3600]  # 1min, 5min, 15min, 60min
  )


def _is_valid_ip(ip_str: str) -> bool:
  """
  Validate that a string is a valid IP address (IPv4 or IPv6).
  
  Args:
    ip_str: String to validate
    
  Returns:
    True if valid IP address, False otherwise
  """
  if not ip_str or not isinstance(ip_str, str):
    return False
  
  ip_str = ip_str.strip()
  if not ip_str:
    return False
    
  try:
    ipaddress.ip_address(ip_str)
    return True
  except ValueError:
    return False


def _get_ip_from_request(request: Request) -> str:
  """
  Extract client IP address with security hardening against IP spoofing.
  
  Security Priority:
  1. CF-Connecting-IP (Cloudflare) - Always trusted when present
  2. X-Forwarded-For - Only trusted when behind trusted proxy (via env var)
  3. request.client.host - Direct connection IP (fallback)
  
  This prevents IP spoofing attacks where attackers send fake X-Forwarded-For
  headers to bypass rate limiting.
  
  Args:
    request: FastAPI Request object
    
  Returns:
    Client IP address as string, or "unknown" if unable to determine
  """
  # 1. Cloudflare header (always trusted when present)
  # Cloudflare Tunnel sets this header and it cannot be spoofed by clients
  cf_ip = request.headers.get("CF-Connecting-IP")
  if cf_ip:
    cf_ip = cf_ip.strip()
    if _is_valid_ip(cf_ip):
      return cf_ip
    # Invalid CF-Connecting-IP - log warning but continue to fallback
  
  # 2. X-Forwarded-For header (only trusted when behind trusted proxy)
  # CRITICAL: This header can be spoofed by clients if not behind a trusted proxy
  # Only trust it if explicitly configured via environment variable
  trust_x_forwarded_for = os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() in ("true", "1", "yes")
  
  if trust_x_forwarded_for:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
      # XFF may contain a list of IPs: "client, proxy1, proxy2"
      # The left-most is the original client IP
      first_ip = xff.split(",")[0].strip()
      if _is_valid_ip(first_ip):
        return first_ip
      # Invalid IP in X-Forwarded-For - log warning but continue to fallback
  # else:
  #   If TRUST_X_FORWARDED_FOR is not set, we ignore X-Forwarded-For entirely
  #   This prevents IP spoofing attacks
  
  # 3. Direct connection IP (fallback)
  # This is the actual client IP when connecting directly (not through proxy)
  client_host = request.client.host if request.client else None
  if client_host and _is_valid_ip(client_host):
    return client_host
  
  # Last resort: return "unknown" if we can't determine a valid IP
  # This should be rare and indicates a misconfiguration
  return "unknown"


def _get_rate_limit_identifier(request: Request) -> str:
  """
  Extract rate limit identifier from request.
  
  Priority:
  1. X-Fingerprint header (fingerprint with challenge)
  2. Authorization header (user_id if available - for future auth)
  3. IP address (fallback)
  
  Returns:
    Identifier string (fingerprint, user_id, or IP)
  """
  # Try to extract fingerprint from header
  fingerprint = request.headers.get("X-Fingerprint")
  if fingerprint:
    # Fingerprint format: fp:challenge:hash or just hash
    # Use the full fingerprint as identifier for rate limiting
    return fingerprint
  
  # TODO: Future - extract user_id from Authorization header
  # For now, fall back to IP
  
  # Fallback to IP address
  return _get_ip_from_request(request)


async def _check_progressive_ban(
    redis, client_ip: str, config: RateLimitConfig
) -> Optional[int]:
  """
  Check if IP is currently banned due to progressive rate limiting.
  Returns ban expiration timestamp if banned, None otherwise.
  """
  if not config.enable_progressive_limits:
    return None

  ban_key = f"rl:ban:{config.identifier}:{client_ip}"
  ban_expiry = await redis.get(ban_key)
  
  if ban_expiry:
    ban_expiry_int = int(ban_expiry)
    now = int(time.time())
    if ban_expiry_int > now:
      return ban_expiry_int
    else:
      # Ban expired, clean it up
      await redis.delete(ban_key)
  
  return None


async def _apply_progressive_ban(
    redis, client_ip: str, config: RateLimitConfig
) -> int:
  """
  Apply progressive ban based on violation count.
  Returns ban expiration timestamp.
  """
  violation_key = f"rl:violations:{config.identifier}:{client_ip}"
  ban_key = f"rl:ban:{config.identifier}:{client_ip}"
  
  # Get current violation count
  violation_count = await redis.incr(violation_key)
  await redis.expire(violation_key, 86400)  # Reset violations after 24 hours
  
  # Determine ban duration based on violation count
  ban_index = min(violation_count - 1, len(config.progressive_ban_durations) - 1)
  ban_duration = config.progressive_ban_durations[ban_index]
  
  # Set ban expiration
  now = int(time.time())
  ban_expiry = now + ban_duration
  await redis.setex(ban_key, ban_duration, ban_expiry)
  
  # Record metrics
  rate_limit_bans_total.labels(endpoint_type=config.identifier).inc()
  rate_limit_violations_total.labels(endpoint_type=config.identifier).inc()
  
  return ban_expiry


async def _get_sliding_window_count(
    redis, key: str, window_seconds: int, now: int, deduplication_id: Optional[str] = None
) -> int:
  """
  Get count of requests in sliding window using Redis sorted sets.
  Supports deduplication via deduplication_id (idempotency).
  
  Args:
    deduplication_id: Optional identifier to use for deduplication (e.g., challenge ID).
                     If provided, same ID will overwrite previous entry (idempotent).
                     If None, uses timestamp + UUID for unique tracking.
  """
  # Remove entries outside the window
  cutoff = now - window_seconds
  await redis.zremrangebyscore(key, 0, cutoff)
  
  # FIX: Use deduplication_id as the member if provided.
  # This ensures double-clicks with the same challenge ID are counted as ONE request.
  if deduplication_id:
    member_id = deduplication_id
  else:
    # Fallback to unique ID for requests without fingerprint/challenge
    member_id = f"{now}:{uuid.uuid4().hex[:8]}"
  
  # ZADD is idempotent: adding the same member again just updates the timestamp
  await redis.zadd(key, {member_id: now})
  
  # Set TTL slightly longer than window to ensure cleanup
  await redis.expire(key, window_seconds + 60)
  
  # Get count of requests in window
  count = await redis.zcard(key)
  return count


# Global rate limit configuration (will be read dynamically from Redis/env)
# These are defaults, actual values are read in check_global_rate_limit()


async def check_global_rate_limit(redis, now: int) -> None:
  """
  Check global rate limits across all identifiers.
  
  Raises:
    HTTPException: If global rate limit is exceeded
  """
  # Read settings from Redis with env fallback
  from backend.utils.settings_reader import get_setting_from_redis_or_env
  
  enable_global_rate_limit = await get_setting_from_redis_or_env(
    redis, "enable_global_rate_limit", "ENABLE_GLOBAL_RATE_LIMIT", True, bool
  )
  
  if not enable_global_rate_limit:
    return
  
  global_rate_limit_per_minute = await get_setting_from_redis_or_env(
    redis, "global_rate_limit_per_minute", "GLOBAL_RATE_LIMIT_PER_MINUTE", 1000, int
  )
  
  global_rate_limit_per_hour = await get_setting_from_redis_or_env(
    redis, "global_rate_limit_per_hour", "GLOBAL_RATE_LIMIT_PER_HOUR", 50000, int
  )
  
  # Global rate limit keys (no identifier suffix)
  global_minute_key = "rl:global:m"
  global_hour_key = "rl:global:h"
  
  # Get counts using sliding windows
  global_minute_count = await _get_sliding_window_count(redis, global_minute_key, 60, now)
  global_hour_count = await _get_sliding_window_count(redis, global_hour_key, 3600, now)
  
  # Check global limits
  exceeded_minute = global_minute_count > global_rate_limit_per_minute
  exceeded_hour = global_hour_count > global_rate_limit_per_hour
  
  if exceeded_minute or exceeded_hour:
    # Compute Retry-After based on sliding window
    if exceeded_minute:
      oldest_in_window = await redis.zrange(global_minute_key, 0, 0, withscores=True)
      if oldest_in_window:
        oldest_timestamp = int(oldest_in_window[0][1])
        retry_after = max(1, 60 - (now - oldest_timestamp))
      else:
        retry_after = 60
    else:
      oldest_in_window = await redis.zrange(global_hour_key, 0, 0, withscores=True)
      if oldest_in_window:
        oldest_timestamp = int(oldest_in_window[0][1])
        retry_after = max(1, 3600 - (now - oldest_timestamp))
      else:
        retry_after = 3600
    
    detail = {
      "error": "rate_limited",
      "message": "Service temporarily unavailable due to high demand. Please try again shortly.",
      "limits": {
        "per_minute": global_rate_limit_per_minute,
        "per_hour": global_rate_limit_per_hour,
      },
      "retry_after_seconds": retry_after,
    }
    
    headers = {"Retry-After": str(retry_after)}
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail=detail,
      headers=headers,
    )


async def check_rate_limit(request: Request, config: RateLimitConfig) -> None:
  """
  Enforce rate limits using Stable Identifier for the bucket and Full Identifier for deduplication.
  Uses sliding window rate limiting with Redis sorted sets for accurate tracking.
  Supports progressive bans for repeated violations.
  Checks global rate limits after individual limits.
  """
  # Skip rate limiting for OPTIONS requests (CORS preflight)
  if request.method == "OPTIONS":
    return
  
  redis = await get_redis_client()
  
  # 1. Get the Full Fingerprint (e.g., "fp:challengeABC:userHash123" OR "2001:db8::1")
  full_fingerprint = _get_rate_limit_identifier(request)
  
  # 2. Extract Stable Identifier (e.g., "userHash123")
  # FIX: Only split if it looks like a fingerprint (starts with "fp:")
  # This prevents breaking IPv6 addresses which also contain colons.
  # This ensures the RATE LIMIT applies to the USER, not just the current challenge session.
  if full_fingerprint.startswith("fp:"):
    # Format: "fp:challenge:hash" - extract the stable hash (last part)
    stable_identifier = full_fingerprint.split(':')[-1]
  else:
    # It's likely an IP address (IPv4 or IPv6) or a raw hash
    # Use as-is to avoid breaking IPv6 addresses (e.g., "2001:db8::1")
    stable_identifier = full_fingerprint
  
  now = int(time.time())

  # Check for existing progressive ban (use IP for ban tracking to prevent ban evasion)
  client_ip = _get_ip_from_request(request)
  ban_expiry = await _check_progressive_ban(redis, client_ip, config)
  if ban_expiry:
    retry_after = ban_expiry - now
    detail = {
      "error": "rate_limited",
      "message": "Too many requests. You have been temporarily banned.",
      "limits": {
        "per_minute": config.requests_per_minute,
        "per_hour": config.requests_per_hour,
      },
      "ban_expires_at": ban_expiry,
      "retry_after_seconds": retry_after,
    }
    headers = {"Retry-After": str(retry_after)}
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail=detail,
      headers=headers,
    )
  
  # Skip global rate limit check for admin endpoints
  # Admin requests should not be subject to global rate limiting
  is_admin_request = request.url.path.startswith("/api/v1/admin")
  
  # Check global rate limits AFTER individual limits (but skip for admin requests)
  if not is_admin_request:
    await check_global_rate_limit(redis, now)

  # 3. Use STABLE identifier for the Redis Key (The Bucket)
  # This ensures rate limits apply to the user, not just the current challenge session
  base_key = f"rl:{config.identifier}:{stable_identifier}"
  minute_key = f"{base_key}:m"
  hour_key = f"{base_key}:h"

  # 4. Use FULL fingerprint for Deduplication (The Receipt)
  # This ensures double-clicks are deduplicated, but different challenges count toward the limit
  minute_count = await _get_sliding_window_count(redis, minute_key, 60, now, deduplication_id=full_fingerprint)
  hour_count = await _get_sliding_window_count(redis, hour_key, 3600, now, deduplication_id=full_fingerprint)

  # Check limits
  exceeded_minute = minute_count > config.requests_per_minute
  exceeded_hour = hour_count > config.requests_per_hour

  if exceeded_minute or exceeded_hour:
    # Record metrics
    rate_limit_rejections_total.labels(endpoint_type=config.identifier).inc()
    
    # Apply progressive ban if enabled (use IP for ban tracking)
    if config.enable_progressive_limits:
      ban_expiry = await _apply_progressive_ban(redis, client_ip, config)
      retry_after = ban_expiry - now
      violation_count_key = f"rl:violations:{config.identifier}:{client_ip}"
      violation_count = await redis.get(violation_count_key)
      violation_count = int(violation_count) if violation_count else 1
    else:
      # Compute Retry-After based on sliding window
      # For minute limit, wait until oldest request in window expires
      if exceeded_minute:
        oldest_in_window = await redis.zrange(minute_key, 0, 0, withscores=True)
        if oldest_in_window:
          oldest_timestamp = int(oldest_in_window[0][1])
          retry_after = max(1, 60 - (now - oldest_timestamp))
        else:
          retry_after = 60
      else:
        oldest_in_window = await redis.zrange(hour_key, 0, 0, withscores=True)
        if oldest_in_window:
          oldest_timestamp = int(oldest_in_window[0][1])
          retry_after = max(1, 3600 - (now - oldest_timestamp))
        else:
          retry_after = 3600
      violation_count = None
      ban_expiry = None

    detail = {
      "error": "rate_limited",
      "message": "Too many requests. Please slow down." if not config.enable_progressive_limits else "Too many requests. You have been temporarily banned.",
      "limits": {
        "per_minute": config.requests_per_minute,
        "per_hour": config.requests_per_hour,
      },
    }
    
    if violation_count is not None:
      detail["violation_count"] = violation_count
    if ban_expiry is not None:
      detail["ban_expires_at"] = ban_expiry
      detail["retry_after_seconds"] = retry_after
    
    headers = {"Retry-After": str(retry_after)}
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail=detail,
      headers=headers,
    )


