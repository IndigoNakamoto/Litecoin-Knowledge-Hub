# Capacity Planning Guide

## Overview

This document outlines the capacity limits and scaling considerations for the Litecoin Knowledge Hub application running on an M1 Mac Mini with 16GB RAM.

## 🎉 Key Update: Cost Efficiency Improvement

**Important**: Actual observed cost per question is **$0.000425** (lower bound), which is **2.3x more efficient** than the original $0.001 estimate. This fundamentally changes capacity planning:

### Impact Summary

| Scenario | Old Cost ($0.001) | New Cost ($0.000425) | Change |
|----------|------------------|---------------------|--------|
| **Steady State** (5,000 questions/day) | $5.00 | **$2.13** | ✅ 57% reduction |
| **Viral Spike** (4,286 questions/day) | $4.29 | **$1.83** | ✅ Fits in $5/day budget! |
| **Major Event** (50,000 questions/day) | $50.00 | **$21.25** | ✅ 57% reduction |

### Key Changes

1. **Viral spikes now fit in base $5/day budget** - No need to increase to $30/day
2. **Recommended limits reduced** - $10/day handles 23,000 questions (safer wallet)
3. **Cost throttling tightened** - $0.015 threshold (was $0.03) maintains human pace
4. **Primary constraint shifted** - Hardware (CPU/RAM) is now the bottleneck, not budget

### New Recommended Configuration

```bash
# High capacity, low risk
DAILY_SPEND_LIMIT_USD=10.00   # Handles ~23,000 questions/day
HOURLY_SPEND_LIMIT_USD=3.00    # Handles ~7,000 questions/hour
HIGH_COST_THRESHOLD_USD=0.015  # ~35 questions in 10 min (3.5/min)
```

**Result**: Your dollar now buys 2.3x more intelligence, allowing you to reduce financial exposure while maintaining or increasing capacity.

## System Architecture

### Current Deployment
- **Hardware**: M1 Mac Mini with 16GB unified memory
- **Frontend**: Vercel (recommended) or Docker container
- **Backend**: Docker container (Python FastAPI)
- **Database**: MongoDB 7.0
- **Cache**: Redis 7-alpine
- **Vector Store**: FAISS (in-memory)
- **LLM**: Google Gemini 2.0 Flash Lite
- **Monitoring**: Prometheus + Grafana

### Services Running
1. MongoDB
2. Backend (FastAPI + RAG Pipeline)
3. Payload CMS (Node.js)
4. Admin Frontend (Next.js) - optional
5. Redis
6. Prometheus
7. Grafana
8. Cloudflared

## Resource Requirements

### Memory Usage (Typical)

| Service | Estimated Memory |
|---------|------------------|
| MongoDB | 500MB - 1GB |
| Backend (FAISS + embeddings + Python) | 1.5GB - 2.5GB |
| Payload CMS | 300MB - 500MB |
| Admin Frontend | 200MB - 300MB |
| Redis | 100MB - 200MB |
| Prometheus (30d retention) | 500MB - 1GB |
| Grafana | 200MB - 300MB |
| Cloudflared | 50MB - 100MB |
| Docker overhead | 500MB - 1GB |
| macOS system | 2GB - 3GB |
| **Total typical** | **~6GB - 9GB** |
| **Total with spikes** | **~10GB - 11GB** |

**Conclusion**: 16GB RAM is sufficient with ~5-7GB headroom for normal operations.

### CPU Requirements
- M1 Mac Mini handles the load efficiently
- Backend uses MPS (Metal Performance Shaders) for embeddings
- Single uvicorn worker is sufficient for expected traffic

**⚠️ Important**: With the new cost efficiency ($0.000425/question), **hardware is now the primary constraint**, not budget. At $10/day, your budget allows ~23,000 questions/day, but your M1 Mac Mini may struggle with:
- **Concurrency**: Single uvicorn worker limits concurrent requests
- **FAISS lookups**: Vector search performance at high concurrency
- **Thermal throttling**: Sustained high CPU usage may cause throttling
- **Memory pressure**: High request volume increases memory usage

**Recommendation**: Monitor CPU usage, memory pressure, and thermal performance closely. Consider multiple uvicorn workers or horizontal scaling if traffic exceeds hardware capacity.

## System Constraints

### 1. Rate Limits

#### Per-User Limits (by fingerprint)
- **Per minute**: 60 requests (default)
- **Per hour**: 100 requests (recommended) - allows 10x normal usage
- **Configuration**: `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_PER_HOUR`

**Rationale**: 
- Normal user: ~10 questions per session
- Engaged user: ~20-30 questions per hour (rare)
- 100 requests/hour provides 10x buffer for legitimate use while preventing abuse
- Previous default of 1,000/hour was excessive (100x normal usage)

#### Global Limits
- **Per minute**: 1,000 requests (default)
- **Per hour**: 50,000 requests (default)
- **Configuration**: `GLOBAL_RATE_LIMIT_PER_MINUTE`, `GLOBAL_RATE_LIMIT_PER_HOUR`

### 2. Cost Limits (LLM Spending)

#### Default Limits
- **Daily**: $5.00 USD (`DAILY_SPEND_LIMIT_USD`)
- **Hourly**: $1.00 USD (`HOURLY_SPEND_LIMIT_USD`)

#### Cost Per Question
- **Model**: `gemini-2.0-flash-lite`
- **Pricing**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Actual observed cost per question**: ~$0.000425 - $0.001
- **Average used for calculations**: $0.000425 per question (lower bound)
- **Previous estimate**: $0.001 per question (conservative)

**Important**: The actual cost efficiency is **2.3x better** than originally calculated, meaning your budget buys significantly more capacity than initially planned.

### 3. Cost Throttling (Per Fingerprint)
- **Threshold**: $0.03 in 10-minute window (recommended) - allows 30 questions in 10 minutes
- **Throttle duration**: 30 seconds
- **Configuration**: `HIGH_COST_THRESHOLD_USD`, `HIGH_COST_WINDOW_SECONDS`

**Rationale**: 
- Normal user: ~10 questions = $0.01
- $0.03 threshold = 3x normal usage (30 questions in 10 minutes)
- Previous default of $0.10 was excessive (100 questions in 10 minutes = 10 questions/minute)
- $0.03 provides better abuse prevention while allowing legitimate power users

## Capacity Scenarios

### Scenario 1: Steady State (500 users/day, 10 questions each)

**Load**:
- 500 users × 10 questions = 5,000 questions/day
- 5,000 × $0.000425 = **$2.13/day** (well under $5.00 limit)

**Constraints**:
- ✅ Daily cost limit: $5.00 (only 43% utilized)
- ✅ Hourly cost limit: $1.00 (sufficient if spread)
- ✅ Rate limits: Well within limits
- ✅ Memory: ~6-9GB (comfortable)

**Verdict**: ✅ **Very Feasible** - With new cost efficiency, this scenario uses less than half the daily budget.

### Scenario 2: Viral Post (3,000 users/week, 10 questions each)

**Load**:
- 3,000 users × 10 questions = 30,000 questions/week
- 30,000 ÷ 7 days = ~4,286 questions/day
- 4,286 × $0.000425 = **~$1.83/day average** ✨

**Traffic Distribution Analysis**:

#### Worst Case: All in 1 Hour
- 30,000 questions in 1 hour
- Cost: $12.75/hour
- **Result**: ⚠️ **Hourly limit ($1.00) exceeded by 12.75x** - Most requests rejected

#### Moderate Spike: Over 6 Hours
- 5,000 questions/hour
- Cost: $2.13/hour
- **Result**: ⚠️ **Hourly limit ($1.00) exceeded by 2.13x** - Some requests rejected

#### Spread Over 24 Hours
- 1,250 questions/hour
- Cost: $0.53/hour
- **Result**: ✅ **Hourly limit ($1.00) sufficient** - All requests accepted

**Verdict**: ✅ **Fits in base $5.00/day budget!** - No need to increase daily limit for viral spikes. Only hourly limit may need adjustment for concentrated traffic.

### Scenario 3: Major Traffic Event (5,000 users/day, 10 questions each)

**Load**:
- 5,000 users × 10 questions = 50,000 questions/day
- 50,000 × $0.000425 = **$21.25/day** ✨
- This represents a significant traffic spike (10x the steady state capacity)

**Traffic Distribution Analysis**:

#### Worst Case: All in 1 Hour
- 50,000 questions in 1 hour
- Cost: $21.25/hour
- **Result**: ❌ **Hourly limit ($1.00) exceeded by 21x** - System will reject most requests

#### Extreme Spike: Over 3 Hours
- ~16,667 questions/hour
- Cost: ~$7.08/hour
- **Result**: ❌ **Hourly limit ($1.00) exceeded by 7x** - Most requests rejected

#### Moderate Spike: Over 8 Hours
- ~6,250 questions/hour
- Cost: ~$2.66/hour
- **Result**: ⚠️ **Hourly limit ($1.00) exceeded by 2.66x** - Some requests rejected

#### Spread Over 12 Hours
- ~4,167 questions/hour
- Cost: ~$1.77/hour
- **Result**: ⚠️ **Hourly limit ($1.00) exceeded by 77%** - Some requests rejected

#### Spread Over 24 Hours
- ~2,083 questions/hour
- Cost: ~$0.89/hour
- **Result**: ✅ **Hourly limit ($1.00) sufficient** - All requests accepted

**Rate Limit Check**:
- Global limit: 50,000 requests/hour ✅ (sufficient if spread)
- Per-user limit: 100 requests/hour ✅ (sufficient for 10 questions, prevents abuse)
- If all 5,000 users arrive in 1 hour: 50,000 requests/hour (at global limit)

**Memory Impact**:
- Peak concurrent users: ~200-500 (if spread over 24 hours)
- Memory usage: ~8-10GB (within 16GB capacity)
- **Result**: ✅ Memory is sufficient

**Verdict**: ❌ **Requires significant configuration changes** - Current limits insufficient for this scale.

**Required Actions**:
1. **Increase daily limit** to at least $50.00
2. **Increase hourly limit** to at least $10-15/hour (depending on traffic pattern)
3. **Monitor closely** for system stability
4. **Consider** implementing request queuing for peak hours

## Required Configuration Changes

### Updated Recommendations (Based on $0.000425/question)

**🎉 Good News**: With the new cost efficiency, you can handle much more traffic with lower budget limits, reducing financial risk.

### For 3,000 Users/Week Capacity

**Previous Recommendation** (based on $0.001/question):
```bash
HOURLY_SPEND_LIMIT_USD=6.00
DAILY_SPEND_LIMIT_USD=30.00
```

**NEW Recommendation** (based on $0.000425/question):
```bash
# High capacity, low risk - handles viral spikes on base budget
HOURLY_SPEND_LIMIT_USD=3.00   # Handles ~7,000 questions/hour (massive spike)
DAILY_SPEND_LIMIT_USD=10.00    # Handles ~23,000 questions/day
```

**Expected Costs**: ~$1.83/day = ~$12.81/week (fits comfortably in $10/day limit)

**Benefits**:
- ✅ Viral spikes (3,000 users/week) fit in $10/day budget
- ✅ 67% lower daily limit reduces financial exposure
- ✅ Still handles 4.6x steady state capacity
- ✅ Safer wallet protection against bugs/loops

### For 5,000 Users/Day Capacity

**⚠️ Warning**: This represents a 10x increase over steady state. **Hardware is now the primary constraint, not cost.**

#### Option 1: Conservative (Recommended for Litecoin.com)
```bash
# Handles spread traffic over 12-24 hours
HOURLY_SPEND_LIMIT_USD=3.00   # Handles ~7,000 questions/hour
DAILY_SPEND_LIMIT_USD=25.00    # $25/day with buffer ($21.25 base + $3.75 buffer)
```

**Expected Costs**: ~$21.25/day = ~$148.75/week = ~$637.50/month
**Best for**: Traffic spread over 12-24 hours

#### Option 2: Moderate (Handles 8-hour concentration)
```bash
# Handles traffic concentrated over 8 hours
HOURLY_SPEND_LIMIT_USD=5.00   # Handles ~11,700 questions/hour
DAILY_SPEND_LIMIT_USD=25.00    # $25/day
```

**Expected Costs**: ~$21.25/day = ~$148.75/week = ~$637.50/month
**Best for**: Traffic concentrated over 8 hours (e.g., major announcement)

#### Option 3: Aggressive (Handles extreme spikes)
```bash
# Handles traffic concentrated over 3-6 hours
HOURLY_SPEND_LIMIT_USD=10.00  # Handles ~23,500 questions/hour
DAILY_SPEND_LIMIT_USD=30.00    # $30/day with buffer
```

**Expected Costs**: ~$21.25/day = ~$148.75/week = ~$637.50/month
**Best for**: Extreme traffic spikes (viral events, major news)

**⚠️ Critical Note**: At these traffic levels, **your M1 Mac Mini hardware will be the bottleneck**, not your budget. Monitor CPU, memory, and thermal performance closely.

**Additional Considerations for 5,000 Users/Day**:
1. **⚠️ Hardware is now the primary constraint** - CPU/RAM/thermals will limit before budget
2. **Monitor system resources closely** - Memory usage may approach limits
3. **Thermal management** - Mac Mini may throttle under sustained high load
4. **Single uvicorn worker** - Consider multiple workers for higher concurrency (future)
5. **FAISS index performance** - Vector search may become bottleneck at high concurrency
6. **Cache optimization critical** - Higher cache hit rates reduce both cost and load
7. **Queue system** - Consider implementing request queuing for peak hours
8. **Load testing** - Test system under load before major events (focus on hardware limits)

**Critical Insight**: With $0.000425/question, your $10/day budget allows ~23,000 questions/day. Your M1 Mac Mini hardware will likely be the limiting factor before you hit budget constraints. Monitor CPU usage, memory pressure, and thermal throttling closely.

### Environment Variable Configuration

Add to `.env.docker.prod`:
```bash
# LLM Spend Limits (Updated for $0.000425/question efficiency)
DAILY_SPEND_LIMIT_USD=10.00   # Handles ~23,000 questions/day (high capacity, low risk)
HOURLY_SPEND_LIMIT_USD=3.00    # Handles ~7,000 questions/hour (massive spike protection)

# Rate Limits (Recommended - prevents abuse while allowing legitimate use)
RATE_LIMIT_PER_MINUTE=60       # 1 request/second max
RATE_LIMIT_PER_HOUR=100        # 10x normal usage (10 questions), prevents abuse

# Global Rate Limits (for system-wide protection)
GLOBAL_RATE_LIMIT_PER_MINUTE=2000
GLOBAL_RATE_LIMIT_PER_HOUR=100000

# Cost Throttling (Updated for new cost efficiency)
HIGH_COST_THRESHOLD_USD=0.015  # $0.015 = ~35 questions in 10 min (3.5/min, human pace)
HIGH_COST_WINDOW_SECONDS=600   # 10 minutes
COST_THROTTLE_DURATION_SECONDS=30  # 30 second throttle
```

**Configuration Rationale**:

**Spend Limits**:
- **$10/day**: Handles 4.6x steady state capacity while reducing financial exposure by 67%
- **$3/hour**: Allows ~2 requests/second continuously for an hour (hardware will limit before budget)
- **Lower limits = safer wallet** against bugs, loops, or abuse

**Rate Limits**:
- **60 requests/minute**: Prevents rapid-fire abuse while allowing normal conversation flow
- **100 requests/hour**: Allows 10x normal usage (10 questions) but prevents excessive abuse

**Cost Throttling**:
- **$0.015 threshold**: At $0.000425/question = ~35 questions in 10 minutes (3.5/min)
- **Previous $0.03**: Would allow ~70 questions (7/min) - too loose with new pricing
- **Maintains "human speed" logic**: Prevents bot spam while allowing legitimate power users

## Cost Optimization Strategies

### 1. Semantic Caching
- **Impact**: Can reduce LLM calls by 20-30% for similar questions
- **Configuration**: Already enabled via `query_cache` in RAG pipeline
- **Recommendation**: Monitor cache hit rates, target 30-50%

### 2. Prompt Optimization
- Reduce token usage per query
- Optimize context retrieval (fewer documents when possible)
- **Potential savings**: 10-20% cost reduction

### 3. Model Selection
- Currently using `gemini-2.0-flash-lite` (most cost-effective)
- Alternative: `gemini-2.5-flash-lite-preview-09-2025` (slightly more expensive)
- **Recommendation**: Stay with current model

### 4. Traffic Distribution
- Encourage users to spread usage over time
- Implement queue system for peak hours (future enhancement)

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Cost Metrics**
   - `llm_daily_cost_usd` - Current daily spend
   - `llm_hourly_cost_usd` - Current hourly spend
   - `llm_cost_usd_total` - Total accumulated cost

2. **Traffic Metrics**
   - `http_requests_total` - Request rate
   - `rate_limit_rejections_total` - Rate limit hits

3. **Cache Performance**
   - `rag_cache_hits_total` / `rag_cache_misses_total` - Cache hit rate

4. **System Health**
   - Memory usage (via Docker stats)
   - Response times (`http_request_duration_seconds`)

### Recommended Alerts

Configure in `monitoring/alerts.yml`:

```yaml
# Daily Spend Limit Warning (80% threshold)
- alert: DailySpendLimitWarning
  expr: (llm_daily_cost_usd / llm_daily_limit_usd) * 100 >= 80

# Hourly Spend Limit Warning (80% threshold)
- alert: HourlySpendLimitWarning
  expr: (llm_hourly_cost_usd / llm_hourly_limit_usd) * 100 >= 80

# High Request Rate
- alert: HighRequestRate
  expr: rate(http_requests_total[5m]) > 100
```

## Scaling Recommendations

### Current Capacity (with adjustments - Updated for $0.000425/question)

- **Maximum steady state**: ~500 users/day (10 questions each) = **$2.13/day**
- **Viral spike capacity**: ~3,000 users/week = **$1.83/day** (fits in $5/day budget!)
- **Major event capacity**: ~5,000 users/day = **$21.25/day** (fits in $25/day budget)
- **Cost**: 
  - Steady state: ~$2.13/day = ~$14.88/week
  - Viral spike: ~$1.83/day = ~$12.81/week
  - Major event: ~$21.25/day = ~$148.75/week = ~$637.50/month

**🎉 Key Changes**:
- Viral spikes now fit in base $5/day budget (no limit increase needed)
- Major events require only $25/day (not $60-75/day)
- **Primary constraint shifted from cost to hardware** (M1 Mac Mini CPU/RAM)

### To Scale Beyond 3,000 Users/Week

1. **Increase Hardware**
   - Upgrade to 32GB RAM Mac Mini (or M1 Pro/Max)
   - Consider dedicated server for production

2. **Distributed Architecture**
   - Move MongoDB to MongoDB Atlas
   - Use Redis Cloud for cache
   - Deploy backend to cloud (AWS/GCP/Azure)

3. **Load Balancing**
   - Multiple backend instances
   - Horizontal scaling with Docker Swarm/Kubernetes

4. **Cost Management**
   - Implement tiered rate limits
   - Add user authentication for premium tiers
   - Queue system for free tier during peak hours

## Cost Estimates

### Weekly Cost Breakdown (Updated for $0.000425/question)

| Scenario | Users/Week | Questions/Week | Daily Avg | Old Cost ($0.001) | New Cost ($0.000425) | Verdict |
|----------|------------|----------------|-----------|-------------------|---------------------|---------|
| Steady | 3,500 | 35,000 | 5,000/day | $35 | **$14.88** | ✅ Easy |
| Moderate | 3,000 | 30,000 | 4,286/day | $30 | **$12.75** | ✅ Fits in $10 limit |
| Light | 2,000 | 20,000 | 2,857/day | $20 | **$8.50** | ✅ Very comfortable |
| Heavy | 5,000 | 50,000 | 7,143/day | $50 | **$21.25** | ✅ Manageable |

**Key Insight**: With new pricing, viral spikes (3,000 users/week) now fit comfortably in a $10/day budget instead of requiring $30/day.

### Daily Cost Breakdown (5,000 Users/Day Scenario)

| Traffic Pattern | Users/Day | Questions/Day | Peak Hour Load | Old Cost | New Cost | Configuration Needed |
|----------------|-----------|---------------|----------------|----------|----------|---------------------|
| Spread (24h) | 5,000 | 50,000 | ~2,083/hr | $50 | **$21.25** | HOURLY=$3, DAILY=$25 |
| Moderate (12h) | 5,000 | 50,000 | ~4,167/hr | $50 | **$21.25** | HOURLY=$3, DAILY=$25 |
| Concentrated (8h) | 5,000 | 50,000 | ~6,250/hr | $50 | **$21.25** | HOURLY=$5, DAILY=$25 |
| Extreme (3h) | 5,000 | 50,000 | ~16,667/hr | $50 | **$21.25** | HOURLY=$10, DAILY=$30 |

### Monthly Cost Estimates (Updated for $0.000425/question)

- **Light usage** (2,000 users/week): ~$36/month (was $80-90)
- **Moderate usage** (3,000 users/week): ~$54/month (was $120-140)
- **Heavy usage** (5,000 users/week): ~$90/month (was $200-220)
- **Major event** (5,000 users/day sustained): ~$637.50/month (was $1,500-2,250)
  - Base cost: $21.25/day × 30 days = $637.50/month
  - With buffer: $25-30/day × 30 days = $750-900/month

**Cost Reduction**: Your dollar now buys **2.3x more intelligence** than originally calculated!

*Note: Costs based on $0.000425 per question (lower bound). Actual costs vary based on query complexity and cache hit rates. 5,000 users/day represents a major traffic event and may not be sustained long-term. **Hardware (CPU/RAM) is now the primary constraint, not budget.***

## Best Practices

### 1. Start Conservative
- Begin with lower limits and monitor
- Gradually increase based on actual usage patterns
- Set alerts at 80% of limits

### 2. Monitor Cache Performance
- Higher cache hit rates = lower costs
- Target 30-50% cache hit rate
- Review and optimize cache TTL settings

### 3. Traffic Pattern Analysis
- Use Grafana dashboards to identify peak hours
- Adjust hourly limits based on actual patterns
- Plan for viral spikes (have buffer capacity)

### 4. Regular Review
- Weekly cost review
- Monthly capacity planning
- Quarterly architecture review

## Troubleshooting

### Issue: Requests Being Rejected (429 errors)

**Possible Causes**:
1. Hourly spend limit exceeded
2. Daily spend limit exceeded
3. Rate limit exceeded
4. Cost throttling triggered

**Solutions**:
1. Check `llm_hourly_cost_usd` and `llm_daily_cost_usd` metrics
2. Increase limits if legitimate traffic
3. Check rate limit metrics
4. Review cost throttling settings

### Issue: High Memory Usage

**Possible Causes**:
1. FAISS index growing too large
2. MongoDB memory leak
3. Too many concurrent requests

**Solutions**:
1. Monitor FAISS index size
2. Check MongoDB connection pooling
3. Review request concurrency
4. Consider reducing Prometheus retention

### Issue: Slow Response Times

**Possible Causes**:
1. LLM API rate limits
2. High database load
3. Network issues
4. Memory pressure

**Solutions**:
1. Check LLM API status
2. Optimize database queries
3. Review network connectivity
4. Monitor system resources

## Abuse Prevention & Long-Term Protection

### Overview

Preventing abuse is critical for maintaining system stability and controlling costs. The system implements multiple layers of protection that work together to prevent abuse over time.

### Multi-Layer Protection Strategy

#### Layer 1: Client Fingerprinting

**Purpose**: Identify and track individual users/devices to prevent abuse.

**Implementation**:
- **Browser Fingerprinting**: Collects browser characteristics (user agent, screen resolution, timezone, etc.)
- **Challenge-Response System**: Server generates one-time challenges that must be included in fingerprints
- **Prevents**: Fingerprint replay attacks, simple bot detection bypass

**Configuration**:
```bash
# Enable challenge-response fingerprinting (recommended: true)
ENABLE_CHALLENGE_RESPONSE=true
CHALLENGE_TTL_SECONDS=300  # 5 minutes
MAX_ACTIVE_CHALLENGES_PER_IDENTIFIER=15
CHALLENGE_REQUEST_RATE_LIMIT_SECONDS=3
```

**How It Works**:
1. Client requests challenge from `/api/v1/auth/challenge`
2. Server generates unique challenge ID (UUID)
3. Client includes challenge in fingerprint hash
4. Server validates challenge is used only once
5. Challenge expires after TTL

**Protection Level**: ⭐⭐⭐ (Good - prevents basic replay attacks)

#### Layer 2: Cloudflare Turnstile (CAPTCHA)

**Purpose**: Verify that requests come from real humans, not bots.

**Implementation**:
- Cloudflare Turnstile integration (privacy-friendly alternative to reCAPTCHA)
- Optional but recommended for production
- Falls back to stricter rate limits if Turnstile fails

**Configuration**:
```bash
# Enable Turnstile verification
ENABLE_TURNSTILE=true
TURNSTILE_SECRET_KEY=your-secret-key
TURNSTILE_SITE_KEY=your-site-key
```

**How It Works**:
1. Frontend requests Turnstile token
2. User completes invisible challenge (if needed)
3. Token included in API request
4. Backend verifies token with Cloudflare
5. If verification fails, stricter rate limits apply

**Protection Level**: ⭐⭐⭐⭐ (Very Good - prevents automated bots)

#### Layer 3: Rate Limiting

**Purpose**: Limit the number of requests per user/time period.

**Implementation**:
- **Per-User Limits**: Tracked by fingerprint (60/min, 100/hour recommended)
- **Global Limits**: System-wide limits (1,000/min, 50,000/hour)
- **Progressive Bans**: Escalating ban durations for repeat violators

**Configuration**:
```bash
# Per-user rate limits (Recommended values)
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=100    # 10x normal usage, prevents abuse

# Global rate limits
GLOBAL_RATE_LIMIT_PER_MINUTE=1000
GLOBAL_RATE_LIMIT_PER_HOUR=50000

# Progressive ban durations (seconds)
# 1st violation: 1min, 2nd: 5min, 3rd: 15min, 4th: 60min
```

**Why 100 requests/hour instead of 1,000?**
- **Normal usage**: ~10 questions per user = 10 requests
- **Engaged user**: ~20-30 questions = 20-30 requests (rare)
- **100 requests/hour**: Provides 10x buffer for legitimate power users
- **1,000 requests/hour**: Was excessive (100x normal usage), allowed abuse
- **Balance**: 100/hour prevents abuse while not impacting legitimate users

**Progressive Ban System**:
- 1st violation: 60 seconds ban
- 2nd violation: 300 seconds (5 minutes) ban
- 3rd violation: 900 seconds (15 minutes) ban
- 4th+ violation: 3600 seconds (1 hour) ban
- Violations reset after 24 hours

**Protection Level**: ⭐⭐⭐⭐ (Very Good - prevents rapid-fire abuse)

#### Layer 4: Cost-Based Throttling

**Purpose**: Prevent individual users from consuming excessive resources.

**Implementation**:
- Tracks spending per fingerprint in sliding window
- Throttles users who exceed cost threshold
- Prevents single user from consuming entire budget

**Configuration**:
```bash
# Enable cost throttling (Updated for $0.000425/question)
ENABLE_COST_THROTTLING=true
HIGH_COST_THRESHOLD_USD=0.015  # $0.015 = ~35 questions in 10 min (3.5/min, human pace)
HIGH_COST_WINDOW_SECONDS=600  # 10 minutes
COST_THROTTLE_DURATION_SECONDS=30  # 30 second throttle
```

**How It Works**:
1. Track estimated cost per request
2. Sum costs per fingerprint in 10-minute window
3. If threshold exceeded ($0.015), throttle for 30 seconds
4. Prevents single user from consuming >$0.015 in 10 minutes (~35 questions)

**Why $0.015 instead of $0.03 or $0.10?**

| Threshold | Questions in 10 min | Questions/min | Multiple of Normal | Protection Level |
|-----------|-------------------|---------------|-------------------|------------------|
| **$0.015** (Recommended) | ~35 | 3.5/min | 3.5x | ⭐⭐⭐⭐ Good |
| $0.03 (Old) | ~70 | 7/min | 7x | ⭐⭐⭐ Moderate |
| $0.10 (Very Old) | ~235 | 23.5/min | 23.5x | ⭐ Very Weak |

**Rationale**:
- **Normal usage**: 10 questions = ~$0.00425
- **$0.015 threshold**: Allows ~35 questions in 10 minutes (3.5x normal, maintains "human speed")
- **$0.03 threshold**: Would allow ~70 questions (7/min) - too loose with new pricing efficiency
- **$0.10 threshold**: Would allow ~235 questions (23.5/min) - completely ineffective
- **Better protection**: $0.015 prevents bot spam while still allowing legitimate power users
- **Maintains intent**: Keeps the "3-4 questions per minute" human pace logic

**Protection Level**: ⭐⭐⭐⭐⭐ (Excellent - prevents cost-based abuse)

#### Layer 5: Daily/Hourly Spend Limits

**Purpose**: Hard limits on total system spending.

**Implementation**:
- Global daily and hourly cost limits
- Requests rejected if limits would be exceeded
- Prevents budget overruns

**Configuration**:
```bash
DAILY_SPEND_LIMIT_USD=30.00
HOURLY_SPEND_LIMIT_USD=10.00
```

**Protection Level**: ⭐⭐⭐⭐⭐ (Excellent - absolute budget protection)

### Monitoring & Detection

#### Key Metrics to Monitor

1. **Rate Limit Violations**
   ```promql
   rate(rate_limit_rejections_total[5m])
   rate(rate_limit_bans_total[5m])
   rate(rate_limit_violations_total[5m])
   ```

2. **Cost Per Fingerprint**
   - Monitor via logs: `Cost-based throttling triggered for fingerprint`
   - Track patterns of high-cost users

3. **Challenge Abuse**
   - Monitor challenge generation rate
   - Alert on excessive challenge requests

4. **Turnstile Failures**
   - Track Turnstile verification failures
   - High failure rate may indicate bot activity

#### Recommended Alerts

Add to `monitoring/alerts.yml`:

```yaml
# High Rate Limit Violations
- alert: HighRateLimitViolations
  expr: rate(rate_limit_violations_total[5m]) > 10
  for: 5m
  annotations:
    summary: "High rate limit violations detected"
    description: "{{ $value }} violations per second"

# Excessive Cost Per Fingerprint
- alert: ExcessiveCostPerFingerprint
  expr: |
    count(count_over_time(rate(llm_cost_usd_total[10m]) > 0.03))
  for: 5m
  annotations:
    summary: "Multiple fingerprints exceeding cost threshold"
    description: "{{ $value }} fingerprints throttled in last 10 minutes"

# Turnstile Failure Spike
- alert: TurnstileFailureSpike
  expr: rate(turnstile_verification_failures_total[5m]) > 5
  for: 5m
  annotations:
    summary: "High Turnstile verification failure rate"
    description: "{{ $value }} failures per second - possible bot attack"
```

### Best Practices for Long-Term Protection

#### 1. Regular Review of Limits

**Weekly Review**:
- Check rate limit violation patterns
- Review cost per fingerprint statistics
- Identify unusual usage patterns

**Monthly Review**:
- Adjust rate limits based on legitimate usage
- Review and update cost thresholds
- Analyze abuse attempt patterns

#### 2. Gradual Tightening

**Don't Set Limits Too Strict Initially**:
- Start with generous limits
- Monitor actual usage patterns
- Gradually tighten based on data

**Example Progression**:
- Month 1: Monitor with current limits
- Month 2: Tighten if abuse detected
- Month 3: Optimize based on legitimate usage patterns

#### 3. Adaptive Rate Limiting

**Consider Implementing**:
- Lower limits during off-peak hours
- Higher limits for verified users (future)
- Dynamic limits based on system load

#### 4. Logging & Auditing

**Track Key Events**:
- All rate limit violations (with fingerprint)
- Cost throttling events
- Turnstile failures
- Progressive ban applications

**Retention**:
- Keep logs for at least 30 days
- Archive for 90 days for analysis
- Use for pattern detection

#### 5. IP-Based Fallback

**Current System**:
- Primary: Fingerprint-based identification
- Fallback: IP address (if no fingerprint)

**Recommendation**:
- Monitor IP-based rate limiting
- Consider IP reputation services (future)
- Track IPs with high violation rates

#### 6. User Authentication (Future Enhancement)

**Potential Addition**:
- Optional user accounts
- Higher limits for authenticated users
- Track abuse by account
- Ability to ban accounts

**Benefits**:
- Better abuse tracking
- Ability to whitelist legitimate users
- More granular control

### Handling Abuse Patterns

#### Pattern 1: Distributed Abuse (Multiple Fingerprints)

**Detection**:
- Multiple fingerprints from same IP
- Similar usage patterns across fingerprints
- Rapid fingerprint generation

**Mitigation**:
- IP-based rate limiting (already implemented)
- Monitor challenge generation rate
- Consider IP reputation blocking (future)

#### Pattern 2: Cost-Based Abuse (Single High-Value User)

**Detection**:
- Single fingerprint consuming >$0.03 in 10 minutes (30+ questions)
- Repeated cost throttling for same fingerprint

**Mitigation**:
- Cost throttling (already implemented) - throttles after $0.03 threshold
- Progressive bans for cost violations (future enhancement)
- Manual review and permanent ban (if needed)

#### Pattern 3: Rapid-Fire Requests

**Detection**:
- High requests/minute from single fingerprint
- Rate limit violations

**Mitigation**:
- Rate limiting (already implemented)
- Progressive bans (already implemented)
- Challenge-response system slows down requests

#### Pattern 4: Bot Networks

**Detection**:
- High Turnstile failure rate
- Similar fingerprints from different IPs
- Unusual request patterns

**Mitigation**:
- Turnstile verification (already implemented)
- Challenge-response system
- Monitor and block suspicious IP ranges (manual)

### Configuration Recommendations by Scenario

#### For Steady State (500 users/day)
```bash
# Moderate protection - prevents abuse while allowing legitimate use
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=100           # 10x normal usage, prevents abuse
HIGH_COST_THRESHOLD_USD=0.015     # $0.015 = ~35 questions in 10 min (3.5/min, human pace)
ENABLE_TURNSTILE=true
ENABLE_CHALLENGE_RESPONSE=true
```

#### For Viral Spikes (3,000 users/week)
```bash
# Same as steady state - limits scale with traffic
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=100           # Prevents abuse during spikes
HIGH_COST_THRESHOLD_USD=0.015     # Keep same - maintains human pace logic
ENABLE_TURNSTILE=true
ENABLE_CHALLENGE_RESPONSE=true
```

#### For Major Events (5,000 users/day)
```bash
# Slightly stricter to prevent abuse during high traffic
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=100           # Keep same - prevents abuse
HIGH_COST_THRESHOLD_USD=0.015     # Keep same - hardware will limit before cost
ENABLE_TURNSTILE=true
ENABLE_CHALLENGE_RESPONSE=true
GLOBAL_RATE_LIMIT_PER_HOUR=100000  # Increase global limit for capacity
```

**Note**: Cost throttling threshold ($0.015) remains consistent across scenarios. At $0.000425/question, this maintains the "3.5 questions per minute" human pace logic regardless of traffic level.

**Note**: Per-user rate limits should remain consistent across scenarios to prevent abuse. Global limits can be adjusted for capacity.

### Emergency Response Procedures

#### If Abuse Detected

1. **Immediate Actions**:
   - Review logs for abuse patterns
   - Identify fingerprint(s) or IP(s) involved
   - Check current cost/rate limit status

2. **Short-Term Mitigation**:
   - Manually ban fingerprint/IP in Redis (if needed)
   - Temporarily lower cost thresholds (e.g., $0.02 or $0.01)
   - Increase rate limit strictness

3. **Long-Term Response**:
   - Analyze abuse pattern
   - Update detection rules
   - Consider additional protections

#### Manual Ban Procedures

**Ban by Fingerprint**:
```bash
# Connect to Redis
docker exec -it litecoin-redis redis-cli

# Set ban (example)
SET "rl:ban:chat_stream:fp:challenge:hash" "9999999999" EX 3600
```

**Ban by IP**:
```bash
# Set IP ban
SET "rl:ban:chat_stream:192.168.1.100" "9999999999" EX 3600
```

### Continuous Improvement

#### Monthly Tasks

1. **Review Metrics**:
   - Rate limit violation trends
   - Cost per fingerprint distribution
   - Turnstile failure rates

2. **Analyze Patterns**:
   - Identify new abuse patterns
   - Review legitimate user impact
   - Adjust thresholds as needed

3. **Update Documentation**:
   - Document new abuse patterns
   - Update response procedures
   - Share learnings with team

#### Quarterly Tasks

1. **Comprehensive Review**:
   - Full system security audit
   - Review all limits and thresholds
   - Analyze cost trends

2. **Enhancement Planning**:
   - Identify gaps in protection
   - Plan new security features
   - Research new abuse prevention techniques

3. **Testing**:
   - Test abuse scenarios
   - Verify protection mechanisms
   - Load testing with abuse patterns

## References

- [Environment Variables Documentation](./ENVIRONMENT_VARIABLES.md)
- [Monitoring Setup Guide](./monitoring/setup-guide.md)
- [Production Deployment Guide](./DEPLOYMENT.md)
- [Architecture Overview](./architecture/high_level_design.md)
- [Advanced Abuse Prevention Feature](./FEATURE_ADVANCED_ABUSE_PREVENTION.md)
- [Client Fingerprinting Feature](./FEATURE_CLIENT_FINGERPRINTING.md)
- [Cloudflare Turnstile Feature](./FEATURE_CLOUDFLARE_TURNSTILE.md)

## Changelog

- **2025-01-XX**: Updated for actual cost efficiency ($0.000425/question)
  - **Cost efficiency improvement**: 2.3x better than original estimate
  - **Viral spikes now fit in $5/day budget** (was $30/day)
  - **Reduced recommended limits**: $10/day handles 23,000 questions (safer wallet)
  - **Tightened cost throttling**: $0.015 threshold (was $0.03) maintains human pace
  - **Primary constraint shifted**: Hardware (CPU/RAM) is now the bottleneck, not budget
  - Updated all cost calculations and scenarios
  - Added hardware constraint warnings and monitoring recommendations

- **2025-01-XX**: Initial capacity planning document created
  - Analyzed 500 users/day steady state capacity
  - Analyzed 3,000 users/week viral spike scenario
  - Analyzed 5,000 users/day major event scenario (Litecoin.com peak traffic)
  - Documented required configuration changes for all scenarios
  - Provided cost estimates and scaling recommendations
  - Added detailed traffic distribution analysis
  - Added comprehensive abuse prevention and long-term protection guide
    - Multi-layer protection strategy (5 layers)
    - Monitoring and detection recommendations
    - Best practices for long-term protection
    - Abuse pattern handling procedures
    - Emergency response procedures

