#!/usr/bin/env python3
"""
Tests for user statistics tracking by fingerprint.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from dotenv import load_dotenv
from unittest.mock import patch

# Load environment
backend_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

# Add project root to path
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)


@pytest.mark.asyncio
async def test_track_unique_user(mock_redis):
    """Test tracking unique users."""
    from backend.api.v1.admin.users import track_unique_user
    
    fingerprint = "test_fp_hash_123"
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        # Track user
        await track_unique_user(fingerprint)
    
    # Verify global set
    global_key = "users:unique:all_time"
    count = await mock_redis.scard(global_key)
    assert count >= 1  # Should have at least our test fingerprint
    
    # Verify daily set
    daily_key = f"users:unique:daily:{today_str}"
    daily_count = await mock_redis.scard(daily_key)
    assert daily_count >= 1


@pytest.mark.asyncio
async def test_get_all_time_unique_users(mock_redis):
    """Test getting all-time unique user count."""
    from backend.api.v1.admin.users import get_all_time_unique_users
    
    # Add test fingerprints
    global_key = "users:unique:all_time"
    await mock_redis.sadd(global_key, "fp1", "fp2", "fp3")
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        count = await get_all_time_unique_users()
        assert count >= 3


@pytest.mark.asyncio
async def test_get_daily_unique_users(mock_redis):
    """Test getting daily unique user count."""
    from backend.api.v1.admin.users import get_daily_unique_users
    
    date_str = "2024-01-15"
    daily_key = f"users:unique:daily:{date_str}"
    await mock_redis.sadd(daily_key, "fp1", "fp2")
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        count = await get_daily_unique_users(date_str)
        assert count >= 2


@pytest.mark.asyncio
async def test_get_users_over_time(mock_redis):
    """Test getting users over time."""
    from backend.api.v1.admin.users import get_users_over_time
    
    # Create some test data
    now = datetime.utcnow()
    for i in range(3):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        daily_key = f"users:unique:daily:{date_str}"
        await mock_redis.sadd(daily_key, f"fp{i}")
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        results = await get_users_over_time(days=3)
        assert len(results) == 3
        assert all("date" in r and "unique_users" in r for r in results)


@pytest.mark.asyncio
async def test_get_average_users_per_day(mock_redis):
    """Test calculating average users per day."""
    from backend.api.v1.admin.users import get_average_users_per_day
    
    # Create test data with known values
    now = datetime.utcnow()
    for i in range(3):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        daily_key = f"users:unique:daily:{date_str}"
        await mock_redis.sadd(daily_key, f"fp{i}")
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        average = await get_average_users_per_day(days=3)
        assert isinstance(average, float)
        assert average >= 0


@pytest.mark.asyncio
async def test_track_unique_user_idempotent(mock_redis):
    """Test that tracking the same user twice doesn't create duplicates."""
    from backend.api.v1.admin.users import track_unique_user, get_all_time_unique_users
    
    fingerprint = "test_duplicate_fp"
    
    # Patch get_redis_client to return mock
    with patch("backend.api.v1.admin.users.get_redis_client", return_value=mock_redis):
        # Track twice
        await track_unique_user(fingerprint)
        count1 = await get_all_time_unique_users()
        
        await track_unique_user(fingerprint)
        count2 = await get_all_time_unique_users()
        
        # Count should be same (sets are unique)
        assert count2 == count1  # Or count2 == count1 + 0 (no new entry)

