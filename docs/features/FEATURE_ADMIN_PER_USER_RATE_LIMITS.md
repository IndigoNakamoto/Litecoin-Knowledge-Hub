    # Admin Per-User Rate Limit Configuration Feature

    ## Overview

    This feature adds the ability for administrators to configure per-user rate limits through the admin frontend interface. Currently, global rate limits and challenge settings are configurable via the admin UI, but per-user rate limits (for chat/stream endpoints) are only configurable via environment variables or hardcoded values.

    **Status**: ⏳ **Not Implemented** (Feature Gap)

    **Priority**: Medium - Administrative convenience

    **Last Updated**: November 2025

    **Related Features**:
    - [Advanced Abuse Prevention](./FEATURE_ADVANCED_ABUSE_PREVENTION.md)
    - [Rate Limiting and Deduplication Changes](../fixes/RATE_LIMIT_AND_DEDUPLICATION_CHANGES.md)

    ---

    ## Table of Contents

    1. [Feature Summary](#feature-summary)
    2. [Current State](#current-state)
    3. [What's Missing](#whats-missing)
    4. [Why It's Needed](#why-its-needed)
    5. [Implementation Guide](#implementation-guide)
    6. [Testing](#testing)
    7. [Deployment](#deployment)

    ---

    ## Feature Summary

    ### Problem Statement

    Currently, administrators can configure:
    - ✅ **Global rate limits** (per minute, per hour) - via admin frontend
    - ✅ **Challenge settings** (TTL, max active, request rate limit) - via admin frontend
    - ✅ **Cost throttling settings** (threshold, window, duration) - via admin frontend

    However, **per-user rate limits** are NOT configurable via the admin frontend:
    - ❌ **Chat/Stream rate limits** (per minute, per hour) - only via `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR` environment variables
    - ❌ **Strict rate limits** (for Turnstile failures) - hardcoded in `backend/main.py` (6/min, 60/hour)

    This means administrators must:
    1. Edit environment variables or code
    2. Restart the backend service
    3. Redeploy to change per-user rate limits

    ### Solution

    Add per-user rate limit configuration to the admin frontend, allowing administrators to:
    - Configure chat/stream rate limits (per minute, per hour) via UI
    - Configure strict rate limits (per minute, per hour) via UI
    - View current settings and their sources (Redis vs environment)
    - Update settings without code changes or service restarts

    ### Key Benefits

    - ✅ **Runtime Configuration**: Change rate limits without code changes or restarts
    - ✅ **Consistent UI**: All rate limit settings in one place
    - ✅ **Better UX**: No need to edit environment variables or code
    - ✅ **Dynamic Updates**: Settings take effect immediately via Redis
    - ✅ **Source Visibility**: See which settings come from Redis vs environment

    ---

    ## Current State

    ### What Works

    #### Global Rate Limits ✅
    - **Backend API**: `GET /api/v1/admin/settings/abuse-prevention` and `PUT /api/v1/admin/settings/abuse-prevention`
    - **Frontend Component**: `admin-frontend/src/components/AbusePreventionSettings.tsx`
    - **Settings Available**:
    - `global_rate_limit_per_minute` (default: 1000)
    - `global_rate_limit_per_hour` (default: 50000)
    - `enable_global_rate_limit` (default: true)

    #### Challenge Settings ✅
    - **Settings Available**:
    - `challenge_ttl_seconds` (default: 300)
    - `max_active_challenges_per_identifier` (default: 15)
    - `challenge_request_rate_limit_seconds` (default: 3)
    - `enable_challenge_response` (default: true)

    #### Cost Throttling Settings ✅
    - **Settings Available**:
    - `high_cost_threshold_usd` (default: 0.02)
    - `daily_cost_limit_usd` (default: 0.25)
    - `high_cost_window_seconds` (default: 600)
    - `cost_throttle_duration_seconds` (default: 30)
    - `enable_cost_throttling` (default: true)

    ### What's Missing

    #### Per-User Rate Limits ❌

    **Chat/Stream Rate Limits**:
    - Currently configured via environment variables:
    - `RATE_LIMIT_PER_MINUTE` (default: 60)
    - `RATE_LIMIT_PER_HOUR` (default: 1000)
    - Used in `STREAM_RATE_LIMIT` config (line 929-933 in `backend/main.py`)
    - **Not available in admin frontend**

    **Strict Rate Limits** (for Turnstile failures):
    - Currently hardcoded in `backend/main.py`:
    - `requests_per_minute=6` (line 937)
    - `requests_per_hour=60` (line 938)
    - Used in `STRICT_RATE_LIMIT` config (line 936-941 in `backend/main.py`)
    - **Not available in admin frontend**

    ---

    ## What's Missing

    ### Backend API

    The admin settings API (`backend/api/v1/admin/settings.py`) does not include:
    - `rate_limit_per_minute` (for chat/stream endpoints)
    - `rate_limit_per_hour` (for chat/stream endpoints)
    - `strict_rate_limit_per_minute` (for Turnstile failures)
    - `strict_rate_limit_per_hour` (for Turnstile failures)

    ### Frontend UI

    The admin frontend component (`admin-frontend/src/components/AbusePreventionSettings.tsx`) does not display:
    - Input fields for chat/stream rate limits
    - Input fields for strict rate limits
    - Source indicators for these settings

    ### Backend Implementation

    The rate limit configurations in `backend/main.py` are:
    - **Chat/Stream**: Read from environment variables (lines 930-931)
    - **Strict**: Hardcoded values (lines 937-938)

    Neither reads from Redis settings like global rate limits do.

    ---

    ## Why It's Needed

    ### Administrative Convenience

    1. **No Code Changes Required**: Administrators can adjust rate limits without editing code
    2. **No Service Restart**: Settings update via Redis, taking effect immediately
    3. **Consistent Interface**: All rate limit settings in one place
    4. **Better Visibility**: See current settings and their sources

    ### Operational Flexibility

    1. **Traffic Adaptation**: Adjust limits based on traffic patterns without deployment
    2. **A/B Testing**: Test different rate limit values easily
    3. **Emergency Adjustments**: Quickly tighten or loosen limits during incidents
    4. **Environment-Specific**: Different limits for dev/staging/prod via Redis

    ### Consistency

    1. **Unified Configuration**: All rate limit settings follow the same pattern
    2. **Same Storage**: All settings stored in Redis with environment variable fallback
    3. **Same UI**: All settings editable through the same admin interface

    ---

    ## Implementation Guide

    ### Step 1: Update Backend Settings Model

    **File**: `backend/api/v1/admin/settings.py`

    **Change**: Add new fields to `AbusePreventionSettings` model

    ```python
    class AbusePreventionSettings(BaseModel):
        """Abuse prevention settings model."""
        # Existing fields...
        global_rate_limit_per_minute: Optional[int] = Field(None, ge=1, description="Global rate limit per minute")
        global_rate_limit_per_hour: Optional[int] = Field(None, ge=1, description="Global rate limit per hour")
        enable_global_rate_limit: Optional[bool] = Field(None, description="Enable global rate limiting")
        
        # NEW: Add per-user rate limit fields
        rate_limit_per_minute: Optional[int] = Field(None, ge=1, description="Per-user rate limit per minute (chat/stream endpoints)")
        rate_limit_per_hour: Optional[int] = Field(None, ge=1, description="Per-user rate limit per hour (chat/stream endpoints)")
        strict_rate_limit_per_minute: Optional[int] = Field(None, ge=1, description="Strict rate limit per minute (Turnstile failures)")
        strict_rate_limit_per_hour: Optional[int] = Field(None, ge=1, description="Strict rate limit per hour (Turnstile failures)")
        
        # Existing fields...
        challenge_ttl_seconds: Optional[int] = Field(None, ge=60, description="Challenge TTL in seconds")
        # ... rest of existing fields
    ```

    ### Step 2: Update Environment Variable Fallback

    **File**: `backend/api/v1/admin/settings.py`

    **Change**: Add new settings to `get_settings_from_env()` function

    ```python
    def get_settings_from_env() -> Dict[str, Any]:
        """
        Get settings from environment variables (fallback).
        
        Returns:
            Dictionary with settings from environment
        """
        return {
            # Existing settings...
            "global_rate_limit_per_minute": int(os.getenv("GLOBAL_RATE_LIMIT_PER_MINUTE", "1000")),
            "global_rate_limit_per_hour": int(os.getenv("GLOBAL_RATE_LIMIT_PER_HOUR", "50000")),
            "enable_global_rate_limit": os.getenv("ENABLE_GLOBAL_RATE_LIMIT", "true").lower() == "true",
            
            # NEW: Add per-user rate limit settings
            "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            "rate_limit_per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
            "strict_rate_limit_per_minute": int(os.getenv("STRICT_RATE_LIMIT_PER_MINUTE", "6")),
            "strict_rate_limit_per_hour": int(os.getenv("STRICT_RATE_LIMIT_PER_HOUR", "60")),
            
            # Existing settings...
            "challenge_ttl_seconds": int(os.getenv("CHALLENGE_TTL_SECONDS", "300")),
            # ... rest of existing settings
        }
    ```

    ### Step 3: Update Backend Rate Limit Configurations

    **File**: `backend/main.py`

    **Change**: Update `STREAM_RATE_LIMIT` and `STRICT_RATE_LIMIT` to read from Redis settings

    **Location**: Around lines 929-941

    **Before**:
    ```python
    STREAM_RATE_LIMIT = RateLimitConfig(
        requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
        identifier="chat_stream",
    )

    # Stricter rate limit for Turnstile failures (10x stricter)
    STRICT_RATE_LIMIT = RateLimitConfig(
        requests_per_minute=6,
        requests_per_hour=60,
        identifier="turnstile_fallback",
        enable_progressive_limits=True,
    )
    ```

    **After**:
    ```python
    # Note: These are defaults. Actual values are read dynamically in the endpoint handlers.
    # See chat_stream_endpoint() for how STREAM_RATE_LIMIT is used.
    # See turnstile verification failure handling for how STRICT_RATE_LIMIT is used.

    # Default values (used if Redis settings not available)
    DEFAULT_STREAM_RATE_LIMIT = RateLimitConfig(
        requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
        identifier="chat_stream",
    )

    DEFAULT_STRICT_RATE_LIMIT = RateLimitConfig(
        requests_per_minute=int(os.getenv("STRICT_RATE_LIMIT_PER_MINUTE", "6")),
        requests_per_hour=int(os.getenv("STRICT_RATE_LIMIT_PER_HOUR", "60")),
        identifier="turnstile_fallback",
        enable_progressive_limits=True,
    )

    # Helper function to get rate limit config from Redis settings
    async def get_stream_rate_limit() -> RateLimitConfig:
        """
        Get stream rate limit configuration from Redis settings or environment.
        
        Returns:
            RateLimitConfig with current settings
        """
        from backend.utils.settings_reader import get_setting_from_redis_or_env
        from backend.redis_client import get_redis_client
        
        redis = await get_redis_client()
        
        requests_per_minute = await get_setting_from_redis_or_env(
            redis, "rate_limit_per_minute", "RATE_LIMIT_PER_MINUTE", 60, int
        )
        requests_per_hour = await get_setting_from_redis_or_env(
            redis, "rate_limit_per_hour", "RATE_LIMIT_PER_HOUR", 1000, int
        )
        
        return RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            identifier="chat_stream",
        )

    async def get_strict_rate_limit() -> RateLimitConfig:
        """
        Get strict rate limit configuration from Redis settings or environment.
        
        Returns:
            RateLimitConfig with current settings
        """
        from backend.utils.settings_reader import get_setting_from_redis_or_env
        from backend.redis_client import get_redis_client
        
        redis = await get_redis_client()
        
        requests_per_minute = await get_setting_from_redis_or_env(
            redis, "strict_rate_limit_per_minute", "STRICT_RATE_LIMIT_PER_MINUTE", 6, int
        )
        requests_per_hour = await get_setting_from_redis_or_env(
            redis, "strict_rate_limit_per_hour", "STRICT_RATE_LIMIT_PER_HOUR", 60, int
        )
        
        return RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            identifier="turnstile_fallback",
            enable_progressive_limits=True,
        )
    ```

    ### Step 4: Update Endpoint Handlers to Use Dynamic Configs

    **File**: `backend/main.py`

    **Change**: Update `chat_stream_endpoint()` to use dynamic rate limit config

    **Location**: Around line 951 (where `check_rate_limit(http_request, STREAM_RATE_LIMIT)` is called)

    **Before**:
    ```python
    await check_rate_limit(http_request, STREAM_RATE_LIMIT)
    ```

    **After**:
    ```python
    # Get dynamic rate limit config from Redis settings
    stream_rate_limit = await get_stream_rate_limit()
    await check_rate_limit(http_request, stream_rate_limit)
    ```

    **Change**: Update Turnstile failure handling to use dynamic strict rate limit

    **Location**: Around line 1024 (where `STRICT_RATE_LIMIT` is used)

    **Before**:
    ```python
    await check_rate_limit(http_request, STRICT_RATE_LIMIT)
    ```

    **After**:
    ```python
    # Get dynamic strict rate limit config from Redis settings
    strict_rate_limit = await get_strict_rate_limit()
    await check_rate_limit(http_request, strict_rate_limit)
    ```

    ### Step 5: Update Frontend TypeScript Types

    **File**: `admin-frontend/src/types/index.ts`

    **Change**: Add new fields to `AbusePreventionSettings` interface

    ```typescript
    export interface AbusePreventionSettings {
    global_rate_limit_per_minute?: number;
    global_rate_limit_per_hour?: number;
    enable_global_rate_limit?: boolean;
    
    // NEW: Add per-user rate limit fields
    rate_limit_per_minute?: number;
    rate_limit_per_hour?: number;
    strict_rate_limit_per_minute?: number;
    strict_rate_limit_per_hour?: number;
    
    challenge_ttl_seconds?: number;
    max_active_challenges_per_identifier?: number;
    enable_challenge_response?: boolean;
    high_cost_threshold_usd?: number;
    high_cost_window_seconds?: number;
    enable_cost_throttling?: boolean;
    cost_throttle_duration_seconds?: number;
    challenge_request_rate_limit_seconds?: number;
    }
    ```

    ### Step 6: Update Frontend UI Component

    **File**: `admin-frontend/src/components/AbusePreventionSettings.tsx`

    **Change**: Add input fields for per-user rate limits

    **Location**: Add after the global rate limit fields (around line 133)

    ```tsx
            <div className="grid gap-4 md:grid-cols-2">
                {/* Existing global rate limit fields... */}
                <div className="space-y-2">
                <Label htmlFor="global_rate_limit_per_minute">
                    Global Rate Limit (per minute)
                    {sources.global_rate_limit_per_minute && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.global_rate_limit_per_minute})
                    </span>
                    )}
                </Label>
                <Input
                    id="global_rate_limit_per_minute"
                    type="number"
                    value={settings.global_rate_limit_per_minute || ""}
                    onChange={(e) =>
                    updateSetting("global_rate_limit_per_minute", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                <div className="space-y-2">
                <Label htmlFor="global_rate_limit_per_hour">
                    Global Rate Limit (per hour)
                    {sources.global_rate_limit_per_hour && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.global_rate_limit_per_hour})
                    </span>
                    )}
                </Label>
                <Input
                    id="global_rate_limit_per_hour"
                    type="number"
                    value={settings.global_rate_limit_per_hour || ""}
                    onChange={(e) =>
                    updateSetting("global_rate_limit_per_hour", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                {/* NEW: Add per-user rate limit fields */}
                <div className="space-y-2">
                <Label htmlFor="rate_limit_per_minute">
                    Per-User Rate Limit (per minute)
                    <span className="ml-2 text-xs text-muted-foreground">
                    (Chat/Stream endpoints)
                    </span>
                    {sources.rate_limit_per_minute && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.rate_limit_per_minute})
                    </span>
                    )}
                </Label>
                <Input
                    id="rate_limit_per_minute"
                    type="number"
                    value={settings.rate_limit_per_minute || ""}
                    onChange={(e) =>
                    updateSetting("rate_limit_per_minute", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                <div className="space-y-2">
                <Label htmlFor="rate_limit_per_hour">
                    Per-User Rate Limit (per hour)
                    <span className="ml-2 text-xs text-muted-foreground">
                    (Chat/Stream endpoints)
                    </span>
                    {sources.rate_limit_per_hour && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.rate_limit_per_hour})
                    </span>
                    )}
                </Label>
                <Input
                    id="rate_limit_per_hour"
                    type="number"
                    value={settings.rate_limit_per_hour || ""}
                    onChange={(e) =>
                    updateSetting("rate_limit_per_hour", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                <div className="space-y-2">
                <Label htmlFor="strict_rate_limit_per_minute">
                    Strict Rate Limit (per minute)
                    <span className="ml-2 text-xs text-muted-foreground">
                    (Turnstile failures)
                    </span>
                    {sources.strict_rate_limit_per_minute && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.strict_rate_limit_per_minute})
                    </span>
                    )}
                </Label>
                <Input
                    id="strict_rate_limit_per_minute"
                    type="number"
                    value={settings.strict_rate_limit_per_minute || ""}
                    onChange={(e) =>
                    updateSetting("strict_rate_limit_per_minute", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                <div className="space-y-2">
                <Label htmlFor="strict_rate_limit_per_hour">
                    Strict Rate Limit (per hour)
                    <span className="ml-2 text-xs text-muted-foreground">
                    (Turnstile failures)
                    </span>
                    {sources.strict_rate_limit_per_hour && (
                    <span className="ml-2 text-xs text-muted-foreground">
                        ({sources.strict_rate_limit_per_hour})
                    </span>
                    )}
                </Label>
                <Input
                    id="strict_rate_limit_per_hour"
                    type="number"
                    value={settings.strict_rate_limit_per_hour || ""}
                    onChange={(e) =>
                    updateSetting("strict_rate_limit_per_hour", parseInt(e.target.value) || undefined)
                    }
                    min="1"
                />
                </div>

                {/* Existing challenge and cost throttling fields... */}
            </div>
    ```

    ### Step 7: Add Section Header (Optional but Recommended)

    **File**: `admin-frontend/src/components/AbusePreventionSettings.tsx`

    **Change**: Add section headers to organize the form

    ```tsx
            <form onSubmit={handleSubmit} className="space-y-6">
            {/* Global Rate Limits Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Global Rate Limits</h3>
                <div className="grid gap-4 md:grid-cols-2">
                {/* Global rate limit fields... */}
                </div>
            </div>

            {/* Per-User Rate Limits Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Per-User Rate Limits</h3>
                <p className="text-sm text-muted-foreground">
                Rate limits applied to individual users/identifiers for chat and stream endpoints.
                </p>
                <div className="grid gap-4 md:grid-cols-2">
                {/* Per-user rate limit fields... */}
                </div>
            </div>

            {/* Challenge Settings Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Challenge Settings</h3>
                <div className="grid gap-4 md:grid-cols-2">
                {/* Challenge fields... */}
                </div>
            </div>

            {/* Cost Throttling Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Cost Throttling</h3>
                <div className="grid gap-4 md:grid-cols-2">
                {/* Cost throttling fields... */}
                </div>
            </div>

            {/* Feature Flags Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Feature Flags</h3>
                {/* Feature flag checkboxes... */}
            </div>

            <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Settings"}
            </Button>
            </form>
    ```

    ---

    ## Testing

    ### Backend API Tests

    1. **Test GET endpoint returns new fields**:
    ```python
    def test_get_settings_includes_per_user_limits():
        response = client.get("/api/v1/admin/settings/abuse-prevention", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "rate_limit_per_minute" in data["settings"]
        assert "rate_limit_per_hour" in data["settings"]
        assert "strict_rate_limit_per_minute" in data["settings"]
        assert "strict_rate_limit_per_hour" in data["settings"]
    ```

    2. **Test PUT endpoint updates new fields**:
    ```python
    def test_update_per_user_rate_limits():
        payload = {
            "rate_limit_per_minute": 120,
            "rate_limit_per_hour": 2000,
            "strict_rate_limit_per_minute": 12,
            "strict_rate_limit_per_hour": 120,
        }
        response = client.put("/api/v1/admin/settings/abuse-prevention", json=payload, headers=auth_headers)
        assert response.status_code == 200
        # Verify settings saved to Redis
    ```

    3. **Test rate limits use Redis settings**:
    ```python
    async def test_stream_rate_limit_uses_redis_settings():
        # Set Redis setting
        await redis.set("admin:settings:abuse_prevention", json.dumps({
            "rate_limit_per_minute": 120,
            "rate_limit_per_hour": 2000,
        }))
        
        # Clear cache
        from backend.utils.settings_reader import clear_settings_cache
        clear_settings_cache()
        
        # Get rate limit config
        config = await get_stream_rate_limit()
        assert config.requests_per_minute == 120
        assert config.requests_per_hour == 2000
    ```

    ### Frontend Tests

    1. **Test UI displays new fields**:
    - Verify input fields for per-user rate limits are visible
    - Verify source indicators show correctly
    - Verify form submission includes new fields

    2. **Test form validation**:
    - Verify minimum value validation (>= 1)
    - Verify number input validation
    - Verify error messages display correctly

    ### Integration Tests

    1. **Test end-to-end flow**:
    - Admin updates per-user rate limits via UI
    - Settings saved to Redis
    - New requests use updated rate limits
    - Verify rate limiting works with new values

    2. **Test fallback behavior**:
    - Remove Redis settings
    - Verify environment variable fallback works
    - Verify default values used if neither Redis nor env vars set

    ---

    ## Deployment

    ### Prerequisites

    - Backend service with Redis access
    - Admin frontend deployed
    - Admin authentication configured (`ADMIN_TOKEN` environment variable)

    ### Deployment Steps

    1. **Deploy Backend Changes**:
    ```bash
    # Update backend/api/v1/admin/settings.py
    # Update backend/main.py
    # Restart backend service
    ```

    2. **Deploy Frontend Changes**:
    ```bash
    # Update admin-frontend/src/types/index.ts
    # Update admin-frontend/src/components/AbusePreventionSettings.tsx
    # Build and deploy frontend
    ```

    3. **Verify Deployment**:
    - Access admin frontend
    - Navigate to Abuse Prevention Settings
    - Verify new fields are visible
    - Update settings and verify they save
    - Test rate limiting with new values

    ### Rollback Plan

    If issues arise:
    1. Revert backend code changes
    2. Revert frontend code changes
    3. Settings in Redis will remain but won't be used (will fall back to environment variables)
    4. No data migration needed

    ---

    ## Configuration

    ### Environment Variables (Fallback)

    Add to `backend/.env`:

    ```bash
    # Per-User Rate Limits (Chat/Stream endpoints)
    RATE_LIMIT_PER_MINUTE=60
    RATE_LIMIT_PER_HOUR=1000

    # Strict Rate Limits (Turnstile failures)
    STRICT_RATE_LIMIT_PER_MINUTE=6
    STRICT_RATE_LIMIT_PER_HOUR=60
    ```

    ### Redis Settings (Runtime Configuration)

    Settings stored in Redis key: `admin:settings:abuse_prevention`

    ```json
    {
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000,
    "strict_rate_limit_per_minute": 6,
    "strict_rate_limit_per_hour": 60
    }
    ```

    ### Default Values

    | Setting | Default | Description |
    |---------|---------|-------------|
    | `rate_limit_per_minute` | 60 | Per-user requests per minute (chat/stream) |
    | `rate_limit_per_hour` | 1000 | Per-user requests per hour (chat/stream) |
    | `strict_rate_limit_per_minute` | 6 | Strict requests per minute (Turnstile failures) |
    | `strict_rate_limit_per_hour` | 60 | Strict requests per hour (Turnstile failures) |

    ---

    ## Related Documentation

    - [Advanced Abuse Prevention Feature](./FEATURE_ADVANCED_ABUSE_PREVENTION.md)
    - [Rate Limiting and Deduplication Changes](../fixes/RATE_LIMIT_AND_DEDUPLICATION_CHANGES.md)
    - [Admin Settings API](../../backend/api/v1/admin/settings.py)
    - [Rate Limiter Implementation](../../backend/rate_limiter.py)

    ---

    ## Summary

    This feature adds per-user rate limit configuration to the admin frontend, completing the rate limit management interface. Once implemented, administrators will be able to configure all rate limit settings (global, per-user, and strict) through a single UI, without requiring code changes or service restarts.

    **Status**: ⏳ **Not Implemented** - Ready for implementation

    **Estimated Implementation Time**: 2-3 hours

    **Files to Modify**:
    1. `backend/api/v1/admin/settings.py` - Add new fields to model and env fallback
    2. `backend/main.py` - Update rate limit configs to read from Redis
    3. `admin-frontend/src/types/index.ts` - Add new fields to TypeScript interface
    4. `admin-frontend/src/components/AbusePreventionSettings.tsx` - Add UI fields

    ---

    **Document Created**: November 2025  
    **Status**: ⏳ Feature Gap Documented - Ready for Implementation

