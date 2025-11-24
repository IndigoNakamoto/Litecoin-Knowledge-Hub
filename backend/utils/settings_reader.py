"""
Utility functions for reading abuse prevention settings from Redis with environment variable fallback.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Redis key for storing settings
SETTINGS_REDIS_KEY = "admin:settings:abuse_prevention"

# Cache for settings to avoid repeated Redis calls
_settings_cache: Optional[Dict[str, Any]] = None


async def get_setting_from_redis_or_env(
    redis,
    setting_key: str,
    env_var: str,
    default_value: Any,
    value_type: type = str
) -> Any:
    """
    Get a setting value from Redis first, then fall back to environment variable.
    
    Args:
        redis: Redis client instance
        setting_key: Key in Redis settings dict (snake_case)
        env_var: Environment variable name
        default_value: Default value if neither Redis nor env has the setting
        value_type: Type to convert the value to (int, float, bool, str)
        
    Returns:
        Setting value of the specified type
    """
    global _settings_cache
    
    # Try to get from Redis cache first
    if _settings_cache is None:
        try:
            settings_json = await redis.get(SETTINGS_REDIS_KEY)
            if settings_json:
                _settings_cache = json.loads(settings_json)
            else:
                _settings_cache = {}
        except Exception as e:
            logger.debug(f"Error reading settings from Redis: {e}")
            _settings_cache = {}
    
    # Check Redis settings first
    if setting_key in _settings_cache:
        value = _settings_cache[setting_key]
        try:
            if value_type == bool:
                return bool(value) if isinstance(value, bool) else str(value).lower() == "true"
            elif value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            else:
                return str(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting setting {setting_key} to {value_type}: {e}, using env fallback")
    
    # Fall back to environment variable
    env_value = os.getenv(env_var)
    if env_value is not None:
        try:
            if value_type == bool:
                return env_value.lower() == "true"
            elif value_type == int:
                return int(env_value)
            elif value_type == float:
                return float(env_value)
            else:
                return str(env_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting env var {env_var} to {value_type}: {e}, using default")
    
    # Use default value
    return default_value


def clear_settings_cache():
    """
    Clear the settings cache. Call this after updating settings in Redis.
    """
    global _settings_cache
    _settings_cache = None

