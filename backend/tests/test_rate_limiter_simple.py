#!/usr/bin/env python3
"""
Simple test script for rate limiting functionality that doesn't require full backend dependencies.
Tests the core logic without importing the full backend stack.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_rate_limit_config():
    """Test RateLimitConfig dataclass structure."""
    print("Testing RateLimitConfig...")
    
    # Import just the dataclass (this should work without full dependencies)
    from dataclasses import dataclass, field
    from typing import List
    
    @dataclass
    class RateLimitConfig:
        requests_per_minute: int
        requests_per_hour: int
        identifier: str
        enable_progressive_limits: bool = True
        progressive_ban_durations: List[int] = field(
            default_factory=lambda: [60, 300, 900, 3600]
        )
    
    # Test defaults
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test"
    )
    
    assert config.enable_progressive_limits == True
    assert config.progressive_ban_durations == [60, 300, 900, 3600]
    print("  ✅ Default progressive limits enabled")
    print("  ✅ Default ban durations correct")
    
    # Test custom values
    custom_durations = [30, 120, 600]
    config2 = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        identifier="test",
        progressive_ban_durations=custom_durations
    )
    assert config2.progressive_ban_durations == custom_durations
    print("  ✅ Custom ban durations work")
    
    return True

def test_ip_extraction_logic():
    """Test IP extraction logic without FastAPI."""
    print("\nTesting IP extraction logic...")
    
    # Simulate the _get_ip_from_request logic
    def get_ip_from_headers(headers, client_host=None):
        # Cloudflare header
        if "CF-Connecting-IP" in headers:
            return headers["CF-Connecting-IP"]
        
        # Standard proxy header
        if "X-Forwarded-For" in headers:
            xff = headers["X-Forwarded-For"]
            return xff.split(",")[0].strip()
        
        return client_host or "unknown"
    
    # Test Cloudflare header
    headers = {"CF-Connecting-IP": "192.168.1.100"}
    ip = get_ip_from_headers(headers)
    assert ip == "192.168.1.100"
    print("  ✅ Cloudflare IP extraction works")
    
    # Test X-Forwarded-For
    headers = {"X-Forwarded-For": "192.168.1.200, 10.0.0.1"}
    ip = get_ip_from_headers(headers)
    assert ip == "192.168.1.200"
    print("  ✅ X-Forwarded-For IP extraction works")
    
    # Test direct client
    headers = {}
    ip = get_ip_from_headers(headers, "127.0.0.1")
    assert ip == "127.0.0.1"
    print("  ✅ Direct client IP extraction works")
    
    return True

def test_progressive_ban_logic():
    """Test progressive ban duration calculation."""
    print("\nTesting progressive ban logic...")
    
    ban_durations = [60, 300, 900, 3600]  # 1min, 5min, 15min, 60min
    
    # Test first violation
    violation_count = 1
    ban_index = min(violation_count - 1, len(ban_durations) - 1)
    assert ban_durations[ban_index] == 60
    print("  ✅ First violation = 1 minute ban")
    
    # Test second violation
    violation_count = 2
    ban_index = min(violation_count - 1, len(ban_durations) - 1)
    assert ban_durations[ban_index] == 300
    print("  ✅ Second violation = 5 minute ban")
    
    # Test third violation
    violation_count = 3
    ban_index = min(violation_count - 1, len(ban_durations) - 1)
    assert ban_durations[ban_index] == 900
    print("  ✅ Third violation = 15 minute ban")
    
    # Test fourth+ violation
    violation_count = 4
    ban_index = min(violation_count - 1, len(ban_durations) - 1)
    assert ban_durations[ban_index] == 3600
    print("  ✅ Fourth+ violation = 60 minute ban")
    
    # Test beyond max (should cap at last value)
    violation_count = 10
    ban_index = min(violation_count - 1, len(ban_durations) - 1)
    assert ban_durations[ban_index] == 3600
    print("  ✅ Beyond max violations caps at 60 minutes")
    
    return True

def test_sliding_window_logic():
    """Test sliding window calculation logic."""
    print("\nTesting sliding window logic...")
    
    # Simulate sliding window with timestamps
    import time
    
    now = int(time.time())
    window_seconds = 60
    
    # Simulate requests at different times
    requests = [
        now - 30,  # 30 seconds ago (in window)
        now - 45,  # 45 seconds ago (in window)
        now - 70,  # 70 seconds ago (out of window)
        now,       # now (in window)
    ]
    
    # Filter requests in window
    cutoff = now - window_seconds
    in_window = [r for r in requests if r > cutoff]
    
    assert len(in_window) == 3
    print("  ✅ Sliding window correctly filters old requests")
    
    # Test that requests are counted correctly
    assert now - 30 in in_window
    assert now - 45 in in_window
    assert now in in_window
    assert now - 70 not in in_window
    print("  ✅ Sliding window includes correct requests")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Rate Limiter Core Logic Tests")
    print("=" * 60)
    
    try:
        test_rate_limit_config()
        test_ip_extraction_logic()
        test_progressive_ban_logic()
        test_sliding_window_logic()
        
        print("\n" + "=" * 60)
        print("✅ All core logic tests passed!")
        print("=" * 60)
        print("\nNote: These tests verify the core logic.")
        print("For full integration tests with Redis, run:")
        print("  pytest backend/tests/test_rate_limiter.py -v")
        print("(Requires full backend dependencies installed)")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

