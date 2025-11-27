# Cost Throttling Enhancements

**Date:** November 2025  
**Status:** ✅ Implemented

---

## Executive Summary

Enhanced the cost-based throttling system by:
1. Lowering the 10-minute threshold from $0.10 to $0.02 (5x more aggressive)
2. Adding a daily cost limit of $0.25 per identifier (hard cap)

These changes significantly reduce abuse potential while maintaining reasonable limits for legitimate users.

---

## Changes Made

### 1. Lowered 10-Minute Threshold

**Before**: $0.10 per 10-minute window  
**After**: $0.02 per 10-minute window

**Impact**:
- **5x more aggressive** throttling
- Triggers throttling much earlier (20-41 requests vs 100-206 requests)
- Provides earlier detection of abuse patterns

**Configuration**:
- Redis setting: `high_cost_threshold_usd` (default: 0.02)
- Environment variable: `HIGH_COST_THRESHOLD_USD` (fallback)

### 2. Added Daily Cost Limit

**New Feature**: $0.25 per identifier per day (hard cap)

**Impact**:
- **Hard cap** on daily spending per identifier
- Prevents sustained abuse over multiple hours
- Daily limit checked before 10-minute threshold
- Returns "Daily usage limit reached. Please try again tomorrow." when exceeded

**Configuration**:
- Redis setting: `daily_cost_limit_usd` (default: 0.25)
- Environment variable: `DAILY_COST_LIMIT_USD` (fallback)

**Redis Keys**:
- Daily tracking: `llm:cost:daily:{stable_identifier}:{YYYY-MM-DD}`
- TTL: 2 days (ensures cleanup even if date changes during request)

---

## Implementation Details

### Backend Changes

**File**: `backend/utils/cost_throttling.py`

**Key Changes**:
1. Added daily cost limit check before 10-minute threshold check
2. Daily limit uses date-based Redis keys for tracking
3. Both limits use stable identifier (prevents bypass with new challenges)
4. Daily limit violation triggers longer throttle duration (2x normal)

**Code Flow**:
```python
# 1. Check daily limit first (hard cap)
if new_daily_cost >= daily_cost_limit_usd:
    # Hard throttle - daily limit exceeded
    return True, "Daily usage limit reached. Please try again tomorrow."

# 2. Check 10-minute threshold
if new_total_cost >= high_cost_threshold_usd:
    # Soft throttle - 10-minute window exceeded
    return True, "High usage detected. Please complete security verification..."
```

### Admin Settings Updates

**File**: `backend/api/v1/admin/settings.py`

**Added Field**:
- `daily_cost_limit_usd: Optional[float]` - Daily cost limit per identifier

**Updated Defaults**:
- `high_cost_threshold_usd`: 0.10 → 0.02
- Added `daily_cost_limit_usd`: 0.25

### Frontend Updates

**Files**:
- `admin-frontend/src/types/index.ts` - Added `daily_cost_limit_usd` field
- `admin-frontend/src/components/AbusePreventionSettings.tsx` - Added input field for daily limit

---

## Impact Analysis

### Abuse Reduction

**Single Attacker**:
- **Before**: $0.10 per 10 minutes = $0.60/hour = $14.40/day
- **After (10-min threshold)**: $0.02 per 10 minutes = $0.12/hour = $2.88/day
- **After (daily limit)**: **$0.25/day maximum** (hard cap)
- **Reduction**: **98% cost reduction** (from $14.40/day to $0.25/day)

**Distributed Attack (50 proxies)**:
- **Before**: 50 × $0.60/hour = $30/hour = $720/day
- **After (10-min threshold)**: 50 × $0.12/hour = $6/hour = $144/day
- **After (daily limit)**: 50 × $0.25/day = **$12.50/day maximum** (hard cap)
- **Reduction**: **98% cost reduction** (from $720/day to $12.50/day)

**Large Botnet (1,000 proxies)**:
- **Before**: 1,000 × $0.60/hour = $600/hour = $14,400/day
- **After (daily limit)**: 1,000 × $0.25/day = **$250/day maximum** (hard cap)
- **Reduction**: **98% cost reduction** (from $14,400/day to $250/day)

### Legitimate User Impact

With cost per turn of $0.000485 to $0.001:

**10-Minute Threshold ($0.02)**:
- Allows 20-41 requests per 10 minutes before throttling
- Reasonable for normal usage patterns

**Daily Limit ($0.25)**:
- Allows 250-515 requests per day per identifier
- More than sufficient for legitimate users
- Prevents sustained abuse

---

## Testing

### Test Scenarios

1. **10-Minute Threshold**:
   - Send requests totaling $0.02 in 10 minutes
   - Verify throttling triggers
   - Verify throttle duration (30 seconds)

2. **Daily Limit**:
   - Send requests totaling $0.25 in a day
   - Verify hard throttle triggers
   - Verify message: "Daily usage limit reached"
   - Verify limit resets at midnight UTC

3. **Both Limits**:
   - Hit 10-minute threshold first
   - Then hit daily limit
   - Verify daily limit takes precedence

4. **Date Boundary**:
   - Hit daily limit near midnight UTC
   - Verify limit resets correctly at date change

---

## Configuration

### Environment Variables

```bash
# 10-minute threshold (triggers throttling)
HIGH_COST_THRESHOLD_USD=0.02

# Daily limit (hard cap)
DAILY_COST_LIMIT_USD=0.25

# Window duration (10 minutes)
HIGH_COST_WINDOW_SECONDS=600

# Throttle duration
COST_THROTTLE_DURATION_SECONDS=30
```

### Redis Settings

Settings stored in: `admin:settings:abuse_prevention`

```json
{
  "high_cost_threshold_usd": 0.02,
  "daily_cost_limit_usd": 0.25,
  "high_cost_window_seconds": 600,
  "cost_throttle_duration_seconds": 30
}
```

---

## Related Documentation

- [Rate Limiting and Deduplication Changes](./RATE_LIMIT_AND_DEDUPLICATION_CHANGES.md)
- [Abuse Potential Analysis](../security/ABUSE_POTENTIAL_ANALYSIS.md)
- [Advanced Abuse Prevention Feature](../features/FEATURE_ADVANCED_ABUSE_PREVENTION.md)

---

**Document Created**: November 2025  
**Status**: ✅ Implemented

