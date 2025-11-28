#!/usr/bin/env python3
"""
Script to clear unique user tracking data from Redis.

This script clears:
1. All-time unique users set (users:unique:all_time)
2. Today's unique users set (users:unique:daily:YYYY-MM-DD)

Useful for testing or resetting user statistics.
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory (backend) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.redis_client import get_redis_client


async def clear_unique_users(clear_all_time: bool = True, clear_today: bool = True):
    """
    Clear unique user tracking data from Redis.
    
    Args:
        clear_all_time: If True, clear the all-time unique users set
        clear_today: If True, clear today's unique users set
    """
    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded environment variables from: {dotenv_path}")
    else:
        # Try .env.local or .env.example
        for env_file in ['.env.local', '.env.example']:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), env_file)
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path)
                print(f"Loaded environment variables from: {env_path}")
                break
        else:
            print("Warning: No .env file found. Using environment variables from system.")

    try:
        print("Connecting to Redis...")
        redis = await get_redis_client()
        
        cleared_keys = []
        
        # Clear all-time unique users
        if clear_all_time:
            global_key = "users:unique:all_time"
            count_before = await redis.scard(global_key)
            await redis.delete(global_key)
            cleared_keys.append(f"All-time unique users (users:unique:all_time) - {count_before} users cleared")
            print(f"✅ Cleared all-time unique users set ({count_before} users)")
        
        # Clear today's unique users
        if clear_today:
            now = datetime.utcnow()
            today_str = now.strftime("%Y-%m-%d")
            daily_key = f"users:unique:daily:{today_str}"
            count_before = await redis.scard(daily_key)
            await redis.delete(daily_key)
            cleared_keys.append(f"Today's unique users (users:unique:daily:{today_str}) - {count_before} users cleared")
            print(f"✅ Cleared today's unique users set ({count_before} users for {today_str})")
        
        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        for key_info in cleared_keys:
            print(f"  • {key_info}")
        print("="*60)
        print("\n✅ Unique user tracking data cleared successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Redis is running and accessible")
        print("  2. Check that REDIS_URL is set correctly in your .env file")
        print("  3. Verify Redis connection settings")
        sys.exit(1)


def main():
    """Main entry point with user confirmation."""
    print("="*60)
    print("Clear Unique User Tracking Data")
    print("="*60)
    print("\nThis will clear:")
    print("  • All-time unique users set (users:unique:all_time)")
    print("  • Today's unique users set (users:unique:daily:YYYY-MM-DD)")
    print("\n⚠️  This action cannot be undone!")
    print()
    
    confirm = input("Are you sure you want to clear unique user tracking data? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    # Run the async function
    asyncio.run(clear_unique_users(clear_all_time=True, clear_today=True))


if __name__ == "__main__":
    main()

