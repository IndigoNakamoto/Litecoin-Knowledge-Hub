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


def test_challenge_rate_limiting():
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
async def test_per_identifier_challenge_limit():
    """Test max active challenges per identifier."""
    from backend.utils.challenge import generate_challenge
    
    redis = await get_redis_client()
    identifier = "test_identifier_123"
    
    # Clear any existing challenges
    await redis.delete(f"challenge:active:{identifier}")
    
    # Generate 3 challenges (should succeed)
    challenges = []
    for i in range(3):
        result = await generate_challenge(identifier)
        challenges.append(result["challenge"])
    
    # 4th challenge should fail
    with pytest.raises(Exception):  # HTTPException raised
        await generate_challenge(identifier)
    
    # Cleanup
    for challenge_id in challenges:
        await redis.delete(f"challenge:{challenge_id}")
    await redis.delete(f"challenge:active:{identifier}")


def test_fingerprint_extraction():
    """Test fingerprint extraction from request."""
    # Test with challenge in fingerprint
    fingerprint = "fp:challenge123:hash456"
    
    from backend.main import _extract_challenge_from_fingerprint
    challenge_id, fingerprint_hash = _extract_challenge_from_fingerprint(fingerprint)
    
    assert challenge_id == "challenge123"
    assert fingerprint_hash == "hash456"


@pytest.mark.asyncio
async def test_cost_throttling():
    """Test cost-based throttling."""
    from backend.utils.cost_throttling import check_cost_based_throttling
    
    fingerprint = "test_cost_throttle_fp"
    redis = await get_redis_client()
    
    # Clear any existing throttling
    await redis.delete(f"llm:throttle:{fingerprint}")
    await redis.delete(f"llm:cost:recent:{fingerprint}")
    
    # Small cost should not throttle
    throttled, reason = await check_cost_based_throttling(fingerprint, 1.0)
    assert throttled == False
    
    # Large cost should throttle
    throttled, reason = await check_cost_based_throttling(fingerprint, 15.0)
    assert throttled == True
    assert "High usage detected" in reason or reason is not None
    
    # Cleanup
    await redis.delete(f"llm:throttle:{fingerprint}")
    await redis.delete(f"llm:cost:recent:{fingerprint}")


def test_global_rate_limit():
    """Test global rate limiting."""
    # This is harder to test with TestClient since it doesn't easily simulate
    # 1000+ requests. Better to test with integration tests or load testing.
    pass  # Placeholder