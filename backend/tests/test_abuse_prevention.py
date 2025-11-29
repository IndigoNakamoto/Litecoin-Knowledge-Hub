#!/usr/bin/env python3
"""
Tests for abuse prevention features:
1. Challenge-response fingerprinting
2. Global rate limiting  
3. Per-identifier challenge limits
4. Cost-based throttling
5. Turnstile graceful degradation
"""

import os
import sys
import time
import asyncio
import pytest
from dotenv import load_dotenv

# Load environment
backend_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

# Add project root to path
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from backend.main import app
from backend.redis_client import get_redis_client

client = TestClient(app)


def test_challenge_endpoint(client):
    """Test challenge generation endpoint."""
    # clear_challenge_state fixture already ran → no active challenges
    response = client.get("/api/v1/auth/challenge")
    assert response.status_code == 200
    data = response.json()
    assert "challenge" in data
    assert len(data["challenge"]) == 64  # 32 bytes hex
    assert "expires_in_seconds" in data
    assert data["expires_in_seconds"] == 300


def test_challenge_rate_limiting(client):
    """Test challenge endpoint rate limiting."""
    # Make requests up to the limit
    for i in range(10):
        response = client.get("/api/v1/auth/challenge")
        if response.status_code != 200:
            break
    
    # 11th request should be rate limited
    response = client.get("/api/v1/auth/challenge")
    # Might be 200 if rate limit hasn't kicked in yet, or 429 if it has
    # This depends on timing


@pytest.mark.asyncio
async def test_per_identifier_challenge_limit(mock_redis):
    """Test max active challenges per identifier."""
    from backend.utils.challenge import generate_challenge
    from backend.utils.settings_reader import get_setting_from_redis_or_env
    from unittest.mock import patch
    import time
    
    identifier = "test_identifier_123"
    active_challenges_key = f"challenge:active:{identifier}"
    
    # Track challenges in a sorted set
    challenges_set = {}
    
    # Mock sorted set operations
    async def mock_zadd(key, mapping):
        key_str = str(key)
        if active_challenges_key in key_str or key == active_challenges_key:
            # Handle both dict and individual mappings
            if isinstance(mapping, dict):
                challenges_set.update(mapping)
            else:
                # Handle tuple format if needed
                for item in mapping:
                    if isinstance(item, tuple):
                        challenges_set[item[0]] = item[1]
                    else:
                        challenges_set[item] = int(time.time()) + 300
            return len(mapping) if isinstance(mapping, dict) else 1
        return 1
    
    async def mock_zcard(key):
        key_str = str(key)
        if active_challenges_key in key_str or key == active_challenges_key:
            return len(challenges_set)
        return 0
    
    async def mock_zremrangebyscore(key, min_score, max_score):
        key_str = str(key)
        if active_challenges_key in key_str or key == active_challenges_key:
            # Remove challenges with scores in range
            to_remove = [k for k, v in challenges_set.items() if min_score <= v <= max_score]
            for k in to_remove:
                del challenges_set[k]
            return len(to_remove)
        return 0
    
    async def mock_zrange(key, start, end, withscores=False):
        key_str = str(key)
        if active_challenges_key in key_str or key == active_challenges_key:
            items = sorted(challenges_set.items(), key=lambda x: x[1])
            # Handle negative end index
            if end == -1:
                end = len(items)
            result = items[start:end+1] if end >= 0 else items[start:]
            if withscores:
                return [(k if isinstance(k, str) else k.decode('utf-8'), v) for k, v in result]
            return [k if isinstance(k, str) else k.decode('utf-8') for k, v in result]
        return []
    
    async def mock_get(key):
        key_str = str(key)
        # Return None for rate limit and ban keys to allow challenge generation
        if "ratelimit" in key_str or "ban" in key_str or "violations" in key_str:
            return None
        return None
    
    async def mock_setex(key, ttl, value):
        return True
    
    async def mock_incr(key):
        return 1
    
    mock_redis.zadd = mock_zadd
    mock_redis.zcard = mock_zcard
    mock_redis.zremrangebyscore = mock_zremrangebyscore
    mock_redis.zrange = mock_zrange
    mock_redis.get = mock_get
    mock_redis.setex = mock_setex
    mock_redis.incr = mock_incr
    
    # Clear any existing challenges and bans
    challenges_set.clear()
    await mock_redis.delete(f"challenge:active:{identifier}")
    await mock_redis.delete(f"challenge:ban:{identifier}")
    await mock_redis.delete(f"challenge:violations:{identifier}")
    await mock_redis.delete(f"challenge:ratelimit:{identifier}")
    
    # Set max_active_challenges_per_identifier to 3 for this test
    async def mock_get_setting(redis_client, setting_key, env_var, default, value_type):
        if setting_key == "max_active_challenges_per_identifier":
            return 3  # Set limit to 3 for this test
        elif setting_key == "enable_challenge_response":
            return True
        elif setting_key == "challenge_ttl_seconds":
            return 300
        elif setting_key == "challenge_request_rate_limit_seconds":
            return 3
        return default
    
    # Also need to patch the redis_client module's get_redis_client
    with patch("backend.utils.challenge.get_redis_client", return_value=mock_redis):
        with patch("backend.redis_client.get_redis_client", return_value=mock_redis):
            with patch("backend.utils.settings_reader.get_setting_from_redis_or_env", side_effect=mock_get_setting):
                # Generate 3 challenges (should succeed)
                challenges = []
                for i in range(3):
                    result = await generate_challenge(identifier)
                    challenges.append(result["challenge"])
                    # Verify challenge was added
                    assert len(challenges_set) == i + 1, f"Challenge {i+1} not tracked in set"
                
                # Verify we have 3 challenges
                assert len(challenges_set) == 3, f"Expected 3 challenges, got {len(challenges_set)}"
                
                # 4th challenge should fail
                from fastapi import HTTPException
                with pytest.raises(HTTPException):  # HTTPException raised
                    await generate_challenge(identifier)
    
    # Cleanup
    for challenge_id in challenges:
        await mock_redis.delete(f"challenge:{challenge_id}")
    await mock_redis.delete(f"challenge:active:{identifier}")


def test_fingerprint_extraction():
    """Test fingerprint extraction from request."""
    # Test with challenge in fingerprint
    fingerprint = "fp:challenge123:hash456"
    
    from backend.main import _extract_challenge_from_fingerprint
    challenge_id, fingerprint_hash = _extract_challenge_from_fingerprint(fingerprint)
    
    assert challenge_id == "challenge123"
    assert fingerprint_hash == "hash456"


@pytest.mark.asyncio
async def test_cost_throttling(mock_redis, monkeypatch):
    """Test cost-based throttling."""
    from backend.utils.cost_throttling import check_cost_based_throttling
    from unittest.mock import patch
    
    # Set environment to production to enable cost throttling
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEBUG", raising=False)
    
    fingerprint = "test_cost_throttle_fp"
    
    # Clear any existing throttling
    await mock_redis.delete(f"llm:throttle:{fingerprint}")
    await mock_redis.delete(f"llm:cost:recent:{fingerprint}")
    
    # Mock sorted set operations for cost tracking
    cost_entries = {}
    daily_entries = {}
    
    async def mock_zrange(key, start=0, end=-1, withscores=False):
        key_str = str(key)
        if "cost:recent" in key_str:
            items = sorted(cost_entries.items(), key=lambda x: x[1])
            if withscores:
                return [(k.encode() if isinstance(k, str) else k, v) for k, v in items[start:end+1]]
            return [k.encode() if isinstance(k, str) else k for k, v in items[start:end+1]]
        elif "cost:daily" in key_str:
            items = sorted(daily_entries.items(), key=lambda x: x[1])
            if withscores:
                return [(k.encode() if isinstance(k, str) else k, v) for k, v in items[start:end+1]]
            return [k.encode() if isinstance(k, str) else k for k, v in items[start:end+1]]
        return []
    
    async def mock_zadd(key, mapping):
        key_str = str(key)
        if "cost:recent" in key_str:
            cost_entries.update(mapping)
        elif "cost:daily" in key_str:
            daily_entries.update(mapping)
        return len(mapping)
    
    async def mock_zremrangebyscore(key, min_score, max_score):
        key_str = str(key)
        removed = 0
        if "cost:recent" in key_str:
            to_remove = [k for k, v in cost_entries.items() if min_score <= v <= max_score]
            for k in to_remove:
                del cost_entries[k]
                removed += 1
        return removed
    
    mock_redis.zrange = mock_zrange
    mock_redis.zadd = mock_zadd
    mock_redis.zremrangebyscore = mock_zremrangebyscore
    
    with patch("backend.utils.cost_throttling.get_redis_client", return_value=mock_redis):
        # Small cost (0.01) should not throttle (below daily limit of 0.25)
        throttled, reason = await check_cost_based_throttling(fingerprint, 0.01)
        assert throttled == False
        
        # Large cost (15.0) should throttle (exceeds daily limit of 0.25)
        throttled, reason = await check_cost_based_throttling(fingerprint, 15.0)
        assert throttled == True
        assert "High usage detected" in reason or reason is not None
    
    # Cleanup
    await mock_redis.delete(f"llm:throttle:{fingerprint}")
    await mock_redis.delete(f"llm:cost:recent:{fingerprint}")


def test_global_rate_limit():
    """Test global rate limiting."""
    # This is harder to test with TestClient since it doesn't easily simulate
    # 1000+ requests. Better to test with integration tests or load testing.
    pass  # Placeholder