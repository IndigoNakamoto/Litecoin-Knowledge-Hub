# Feature: Dynamic Admin Settings Management

## Overview

This feature extends the admin frontend to provide **runtime configuration management** for critical RAG pipeline and Local RAG settings. Administrators can adjust performance tuning parameters, feature flags, and operational settings without requiring service restarts or code deployments.

**Status**: 📋 **Planning** - Feature document created

**Priority**: Medium - Operational efficiency and flexibility enhancement

**Target Users**: System administrators and DevOps engineers

**Last Updated**: 2025-12-07

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Business Requirements](#business-requirements)
3. [Technical Architecture](#technical-architecture)
4. [Current State Analysis](#current-state-analysis)
5. [Implementation Plan](#implementation-plan)
6. [Integration Points](#integration-points)
7. [Configuration](#configuration)
8. [Risks & Mitigations](#risks--mitigations)
9. [Testing Strategy](#testing-strategy)
10. [Monitoring & Metrics](#monitoring--metrics)
11. [Success Criteria](#success-criteria)
12. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

Currently, many critical system settings are only configurable via environment variables, which requires:

1. **Service Restarts**: Changing settings requires restarting the backend service
2. **Deployment Overhead**: Configuration changes require code deployments or manual environment variable updates
3. **No Runtime Tuning**: Cannot adjust performance parameters based on real-time metrics
4. **Limited Visibility**: Settings are scattered across environment variables with no centralized management
5. **Operational Friction**: Quick adjustments for optimization or troubleshooting require DevOps intervention

### Solution

Implement a **dynamic settings management system** that:

1. **Redis-Backed Storage**: Store settings in Redis with environment variable fallback (existing pattern)
2. **Admin Frontend UI**: Provide intuitive interface for managing settings
3. **Runtime Updates**: Settings take effect immediately without service restart
4. **Settings Categories**: Organize settings into logical groups (RAG Pipeline, Local RAG, Abuse Prevention)
5. **Validation & Safety**: Validate settings before applying, prevent invalid configurations
6. **Audit Trail**: Track setting changes for troubleshooting and compliance

### Key Benefits

- ✅ **Zero-Downtime Configuration**: Adjust settings without service restarts
- ✅ **Operational Efficiency**: Quick tuning based on real-time metrics
- ✅ **Centralized Management**: All settings in one place with clear organization
- ✅ **Improved Visibility**: See current values and their sources (Redis vs environment)
- ✅ **Faster Troubleshooting**: Adjust parameters during incidents without deployment
- ✅ **A/B Testing**: Easily toggle features and compare performance

---

## Business Requirements

### Functional Requirements

1. **FR-1**: Admin must be able to view all configurable settings with current values and sources
2. **FR-2**: Admin must be able to update settings via admin frontend UI
3. **FR-3**: Settings must take effect immediately without service restart
4. **FR-4**: System must validate settings before applying (type checking, range validation)
5. **FR-5**: System must support settings rollback (revert to environment variable defaults)
6. **FR-6**: System must maintain backward compatibility (environment variables still work)
7. **FR-7**: Settings must persist across service restarts (stored in Redis)
8. **FR-8**: Admin must see which settings come from Redis vs environment variables

### Non-Functional Requirements

1. **NFR-1**: Settings update latency < 100ms (Redis write + cache clear)
2. **NFR-2**: Settings read latency < 10ms (cached Redis reads)
3. **NFR-3**: Support at least 50 configurable settings
4. **NFR-4**: Settings validation must prevent invalid configurations
5. **NFR-5**: UI must be responsive and intuitive (< 3 clicks to update any setting)
6. **NFR-6**: Settings changes must be logged for audit purposes

---

## Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Admin Frontend (Next.js)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Settings UI Components                                  │  │
│  │  - RAG Pipeline Settings                                 │  │
│  │  - Local RAG Settings                                    │  │
│  │  - Abuse Prevention Settings (existing)                  │  │
│  └───────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                │ HTTP PUT/GET
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Admin Settings API (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /api/v1/admin/settings/rag-pipeline                      │  │
│  │  /api/v1/admin/settings/local-rag                         │  │
│  │  /api/v1/admin/settings/abuse-prevention (existing)       │  │
│  └───────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                │ Read/Write
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redis (Settings Storage)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Keys:                                                    │  │
│  │  - admin:settings:rag_pipeline                           │  │
│  │  - admin:settings:local_rag                              │  │
│  │  - admin:settings:abuse_prevention (existing)            │  │
│  └───────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                │ Fallback
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Environment Variables (.env)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  RETRIEVER_K=12                                           │  │
│  │  MAX_LOCAL_QUEUE_DEPTH=3                                  │  │
│  │  REDIS_CACHE_SIMILARITY_THRESHOLD=0.90                    │  │
│  │  ...                                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Runtime Read
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend Services (Python)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Settings Reader Utility                                  │  │
│  │  - get_setting_from_redis_or_env()                        │  │
│  │  - clear_settings_cache()                                 │  │
│  └───────────────────────────┬──────────────────────────────┘  │
│                                │                                 │
│  ┌────────────────────────────┴──────────────────────────────┐ │
│  │  RAG Pipeline                                              │ │
│  │  - Reads RETRIEVER_K, MAX_CHAT_HISTORY_PAIRS              │ │
│  │  - Reads MIN_VECTOR_SIMILARITY                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Inference Router                                          │ │
│  │  - Reads MAX_LOCAL_QUEUE_DEPTH                             │ │
│  │  - Reads LOCAL_TIMEOUT_SECONDS                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Redis Vector Cache                                        │ │
│  │  - Reads REDIS_CACHE_SIMILARITY_THRESHOLD                  │ │
│  │  - Reads SEMANTIC_CACHE_TTL_SECONDS                        │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Component | Technology | Purpose | Location |
|-----------|-----------|---------|----------|
| **Admin Settings API** | FastAPI (Python) | CRUD operations for settings | `backend/api/v1/admin/settings/` |
| **Settings Reader** | Python utility | Read settings with Redis/env fallback | `backend/utils/settings_reader.py` |
| **Admin Frontend** | Next.js (React) | Settings management UI | `admin-frontend/src/components/` |
| **Redis Storage** | Redis | Persistent settings storage | Existing Redis instance |
| **Settings Reader** | Python utility | Read settings with Redis/env fallback (no caching) | `backend/utils/settings_reader.py` |

---

## Current State Analysis

### Existing Architecture

**Settings Management** (Current):
- ✅ Abuse Prevention settings already use Redis + env fallback pattern
- ✅ Settings reader utility exists (`backend/utils/settings_reader.py`)
- ✅ Admin settings API exists (`backend/api/v1/admin/settings.py`)
- ✅ Admin frontend has Abuse Prevention Settings component
- ❌ RAG Pipeline settings are environment-only
- ❌ Local RAG settings are environment-only
- ❌ No UI for RAG/Local RAG settings

**Settings Categories** (Current):
- ✅ Abuse Prevention: Fully implemented with UI
- ❌ RAG Pipeline: Environment variables only
- ❌ Local RAG: Environment variables only

### Existing Code Analysis (Bugs Found)

**Critical Bug #1: In-Memory Caching Already Exists**
The existing `backend/utils/settings_reader.py` already uses in-memory caching (lines 15-16, 39-51):
```python
_settings_cache: Optional[Dict[str, Any]] = None
# ...
if _settings_cache is None:
    settings_json = await redis.get(SETTINGS_REDIS_KEY)
    _settings_cache = json.loads(settings_json) if settings_json else {}
```
This confirms the "Zombie Settings" problem is **REAL** and must be fixed.

**Critical Bug #2: Hardcoded to Single Category**
Line 13 hardcodes to `admin:settings:abuse_prevention` - cannot support multiple categories without refactoring:
```python
SETTINGS_REDIS_KEY = "admin:settings:abuse_prevention"  # Hardcoded!
```

**Bug #3: Incomplete Bool Conversion**
Line 58 only checks for `"true"`, doesn't handle `"false"`, `"0"`, `"no"`, `"off"` as False:
```python
# Current (buggy):
return bool(value) if isinstance(value, bool) else str(value).lower() == "true"

# Fixed:
if isinstance(value, bool):
    return value
return str(value).lower() in ('true', '1', 't', 'yes', 'on')
```

**Bug #4: Services Read Settings at Init Time**
Services read `os.getenv()` in `__init__`, not per-request:
- `router.py` lines 109-110: Settings baked in at instantiation
- `rewriter.py` lines 127-128: Settings baked in at instantiation  
- `redis_vector_cache.py` lines 112-115: Settings baked in at instantiation

These settings won't pick up dynamic changes until service restart.

**Bug #5: Missing Prompt - QA_WITH_HISTORY_PROMPT**
`rag_pipeline.py` line 129 has another hardcoded prompt for history-aware rephrasing:
```python
QA_WITH_HISTORY_PROMPT = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("human", "Given the above conversation, generate a standalone question..."),
])
```
This should also be dynamically configurable.

### Integration Challenges

1. **Settings Reader Pattern**
   - **Current**: Only used for abuse prevention settings
   - **Proposed**: Extend to all settings categories
   - **Solution**: Reuse existing pattern, add new setting keys

2. **Backend Service Integration**
   - **Current**: Services read directly from `os.getenv()`
   - **Proposed**: Services read via settings reader utility
   - **Solution**: Refactor service initialization to use settings reader

3. **Multi-Worker Architecture & "Zombie Settings"**
   - **Current**: In-memory cache in settings reader (single process assumption)
   - **Proposed**: Direct Redis reads (no in-memory cache)
   - **Solution**: Redis is fast enough (sub-millisecond), skip Python-level caching to avoid inconsistent behavior across Gunicorn/Uvicorn workers
   - **Critical**: Each worker process has separate memory; cache invalidation in one worker doesn't affect others

4. **Feature Flags**
   - **Current**: Feature flags checked at module load time
   - **Proposed**: Runtime toggle of feature flags
   - **Solution**: Lazy-load services based on runtime flag values

---

## Multi-Worker Architecture Considerations

### The "Zombie Settings" Problem

In production, FastAPI typically runs with multiple workers (via Gunicorn or Uvicorn). Each worker is a **separate operating system process** with its own memory space.

**The Problem Scenario**:
1. Admin updates `RETRIEVER_K` from 12 to 5 via the API
2. The API request hits **Worker A**
3. Worker A updates Redis and clears *its own* in-memory cache
4. **Worker B** (handling the next user query) **still has the old value (12) in its memory** until its local cache expires
5. **Result**: Users experience inconsistent behavior (flapping between old and new settings) depending on which worker handles their request

**The Solution**: **No In-Memory Caching**
- Read directly from Redis every time
- Redis latency is sub-millisecond (microsecond scale on localhost/Docker network)
- The performance benefit of in-memory caching is negligible
- Eliminates the "Zombie Settings" problem entirely

**Future Optimization** (if absolutely needed):
- Implement a very short TTL (e.g., 5 seconds) rather than manual invalidation
- Or use Redis Pub/Sub for cross-worker cache invalidation
- But for Phase 1, direct Redis reads are the simplest and safest approach

---

## Settings That Cannot Be Truly Dynamic

Some settings have architectural limitations that prevent true runtime changes:

| Setting | Limitation | Recommendation |
|---------|------------|----------------|
| `max_local_queue_depth` | Controls `asyncio.Semaphore` size, created at `InferenceRouter.__init__` | Mark as "Restart Required" in UI. Alternative: Implement semaphore recreation (complex). |
| `ollama_url` | HTTP client configured at service init | Mark as "Restart Required" in UI |
| `infinity_url` | HTTP client configured at service init | Mark as "Restart Required" in UI |
| `redis_stack_url` | Redis connection configured at init | Mark as "Restart Required" in UI |
| `vector_dimension` | Would require re-indexing all vectors | Not configurable via admin (env only) |
| `embedding_model_id` | Would require re-indexing all vectors | Not configurable via admin (env only) |

**UI Recommendation**: Display these settings as read-only with a "Restart Required" badge, or exclude them from the admin UI entirely and document them as environment-variable-only.

**Workaround for `max_local_queue_depth`**:
```python
class InferenceRouter:
    async def _ensure_semaphore_size(self, redis):
        """Recreate semaphore if max_queue_depth changed."""
        current_max = await get_local_rag_setting(
            redis, "max_local_queue_depth", "MAX_LOCAL_QUEUE_DEPTH", 3, int
        )
        if current_max != self._configured_max:
            # Wait for all current operations to complete
            # Then recreate semaphore
            self._queue_semaphore = asyncio.Semaphore(current_max)
            self._configured_max = current_max
```
This is complex and may cause race conditions - **not recommended for Phase 1**.

---

## Implementation Plan

### Phase 1: Backend API Extensions

**Objective**: Extend admin settings API to support RAG Pipeline and Local RAG settings

**API Directory Reorganization**:
Create a `settings/` subdirectory for better organization:
```
backend/api/v1/admin/settings/
├── __init__.py          # Router aggregation
├── base.py              # Shared utilities (verify_admin_token, etc.)
├── abuse_prevention.py  # Move from settings.py (existing)
├── rag_pipeline.py      # NEW
├── local_rag.py         # NEW
└── prompts.py           # NEW
```

**New Files**:
- `backend/api/v1/admin/settings/__init__.py` - Router aggregation
- `backend/api/v1/admin/settings/base.py` - Shared auth dependency, utilities
- `backend/api/v1/admin/settings/rag_pipeline.py`
- `backend/api/v1/admin/settings/local_rag.py`
- `backend/api/v1/admin/settings/prompts.py`
- `backend/constants/prompts.py` - Default prompt constants

**Modified Files**:
- `backend/api/v1/admin/settings.py` - Refactor into `settings/abuse_prevention.py`
- `backend/main.py` - Update router imports

**Settings Models**:

```python
# backend/api/v1/admin/settings/rag_pipeline.py
class RAGPipelineSettings(BaseModel):
    """RAG pipeline tuning settings."""
    retriever_k: Optional[int] = Field(None, ge=1, le=50, description="Number of documents to retrieve")
    max_chat_history_pairs: Optional[int] = Field(None, ge=1, le=20, description="Max chat history pairs")
    min_vector_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum vector similarity threshold")
    llm_model_name: Optional[str] = Field(None, description="LLM model name")
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM temperature")
    max_output_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Max output tokens")
```

```python
# backend/api/v1/admin/settings/local_rag.py
class LocalRAGSettings(BaseModel):
    """Local RAG configuration settings."""
    max_local_queue_depth: Optional[int] = Field(None, ge=1, le=20, description="Max concurrent local requests")
    local_timeout_seconds: Optional[float] = Field(None, ge=0.5, le=10.0, description="Local rewriter timeout")
    redis_cache_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Cache similarity threshold")
    semantic_cache_ttl_seconds: Optional[int] = Field(None, ge=60, description="Cache TTL in seconds")
    enable_local_rewriter: Optional[bool] = Field(None, description="Enable local query rewriting")
    enable_infinity_embeddings: Optional[bool] = Field(None, description="Enable Infinity embeddings")
    enable_redis_cache: Optional[bool] = Field(None, description="Enable Redis vector cache")
```

```python
# backend/api/v1/admin/settings/prompts.py
class PromptSettings(BaseModel):
    """Prompt templates for RAG pipeline and rewriter."""
    rewriter_system_prompt: Optional[str] = Field(
        None, 
        min_length=50, 
        max_length=5000,
        description="System prompt for query rewriting (rewriter service)"
    )
    rag_system_instruction: Optional[str] = Field(
        None,
        min_length=50,
        max_length=10000,
        description="System instruction for RAG answer generation (main LLM prompt)"
    )
    qa_with_history_prompt: Optional[str] = Field(
        None,
        min_length=20,
        max_length=2000,
        description="Prompt for history-aware query rephrasing (resolves pronouns/context)"
    )
    no_kb_match_response: Optional[str] = Field(
        None,
        min_length=10,
        max_length=500,
        description="Response when no knowledge base match is found"
    )
```

**API Endpoints**:
```python
@router.get("/rag-pipeline")
async def get_rag_pipeline_settings(request: Request) -> Dict[str, Any]:
    """Get RAG pipeline settings."""
    # Similar to existing abuse prevention endpoint

@router.put("/rag-pipeline")
async def update_rag_pipeline_settings(
    request: Request,
    settings: RAGPipelineSettings
) -> Dict[str, Any]:
    """Update RAG pipeline settings."""
    # Similar to existing abuse prevention endpoint

@router.get("/prompts")
async def get_prompt_settings(request: Request) -> Dict[str, Any]:
    """Get prompt template settings."""
    # Returns current prompts with sources

@router.put("/prompts")
async def update_prompt_settings(
    request: Request,
    settings: PromptSettings
) -> Dict[str, Any]:
    """Update prompt template settings."""
    # Validates prompt length, saves to Redis
    # Prompts take effect on next request

# Reset to default (DELETE) endpoints
@router.delete("/rag-pipeline")
async def reset_rag_pipeline_settings(request: Request) -> Dict[str, Any]:
    """Reset RAG pipeline settings to environment variable defaults."""
    # Delete from Redis, return env defaults

@router.delete("/local-rag")
async def reset_local_rag_settings(request: Request) -> Dict[str, Any]:
    """Reset Local RAG settings to environment variable defaults."""

@router.delete("/prompts")
async def reset_prompt_settings(request: Request) -> Dict[str, Any]:
    """Reset prompts to hardcoded defaults."""
```

**Shared Auth Dependency** (in `base.py`):
```python
# backend/api/v1/admin/settings/base.py
from fastapi import Depends, HTTPException, Request
import hmac
import os

async def require_admin_auth(request: Request):
    """FastAPI dependency for admin authentication."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    expected_token = os.getenv("ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured")
    
    if not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")

# Usage in endpoints:
@router.get("/rag-pipeline", dependencies=[Depends(require_admin_auth)])
async def get_rag_pipeline_settings(request: Request) -> Dict[str, Any]:
    ...
```

**Default Prompt Constants** (`backend/constants/prompts.py`):
```python
# backend/constants/prompts.py
"""Default prompt templates for RAG pipeline and rewriter services."""

DEFAULT_REWRITER_PROMPT = """You are a Query Resolution Engine. Your task is to rewrite the User's input into a standalone, context-complete search query.

Rules:
1. Analyze the Chat History to resolve pronouns and ambiguous references
2. Remove filler words and make the query concise
3. If the user's input doesn't need a search (greetings, thanks, acknowledgments), output exactly: NO_SEARCH_NEEDED
4. DO NOT answer the question - only rewrite it
5. Output ONLY the rewritten query or NO_SEARCH_NEEDED

Examples:
- Chat: "What is the $21 plan?" / User: "Does it expire?" → "Does the $21 Litecoin plan expire?"
- Chat: "Tell me about MWEB" / User: "How do I enable it?" → "How do I enable MWEB on Litecoin?"
- User: "Thanks!" → NO_SEARCH_NEEDED
"""

DEFAULT_SYSTEM_INSTRUCTION = """You are a neutral, factual expert on Litecoin...
[Full prompt from rag_pipeline.py SYSTEM_INSTRUCTION]
"""

DEFAULT_QA_WITH_HISTORY_PROMPT = """Given the above conversation, generate a standalone question that resolves any pronouns or ambiguous references in the user's input. Focus on the main subject of the conversation. If the input is already a complete standalone question, return it as is. Do not add extra information or make assumptions beyond resolving the context."""

DEFAULT_NO_KB_MATCH_RESPONSE = "I couldn't find any relevant content in our knowledge base yet."
```

**Prompt Validation** (for `prompts.py`):
```python
def validate_prompt(prompt: str, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate prompt for security and quality.
    
    Returns:
        (is_valid, error_message)
    """
    # Check for prompt injection patterns
    from backend.utils.input_sanitizer import detect_prompt_injection
    is_injection, pattern = detect_prompt_injection(prompt)
    if is_injection:
        return False, f"Prompt contains injection pattern: {pattern}"
    
    # Check length (already handled by Pydantic Field)
    # Additional validation can be added here
    
    return True, None
```

**Success Criteria**:
- ✅ API endpoints return current settings with sources
- ✅ Settings can be updated via API
- ✅ Settings are validated before saving
- ✅ **Prompts are validated for injection patterns**
- ✅ Settings persist in Redis

**Estimated Time**: 5-7 hours (includes prompt validation)

---

### Phase 2: Settings Reader Utility Extensions

**Objective**: Extend settings reader to support new setting categories with robust type conversion

**Modified File**: `backend/utils/settings_reader.py`

**Critical Architecture Decision**: **No In-Memory Caching**
- **Rationale**: In production, FastAPI runs with multiple workers (Gunicorn/Uvicorn). Each worker is a separate OS process with its own memory.
- **Problem**: If Worker A clears its cache after an update, Worker B still has stale values until its cache expires → "Zombie Settings"
- **Solution**: Read directly from Redis every time. Redis latency is sub-millisecond (microsecond scale on localhost/Docker), so the performance benefit of in-memory caching is negligible.
- **Future**: If absolutely needed, implement a very short TTL (5 seconds) rather than manual invalidation, or use Redis Pub/Sub for cross-worker cache invalidation.

**Key Refactoring Required**:
1. **Remove in-memory cache** - Delete `_settings_cache` global variable
2. **Add `category` parameter** - Support multiple Redis keys
3. **Fix bool conversion** - Handle all falsy values correctly

**Type Conversion Safety**:
Redis stores everything as strings. The settings reader must handle robust type conversion:

```python
def cast_value(value: Any, target_type: type) -> Any:
    """Safely convert Redis/env value to target type."""
    if value is None:
        return None
    
    if target_type == bool:
        # Handle both bool and string representations
        if isinstance(value, bool):
            return value
        # Handle various string boolean representations
        return str(value).lower() in ('true', '1', 't', 'yes', 'on')
    
    if target_type == int:
        return int(value)
    
    if target_type == float:
        return float(value)
    
    return str(value)
```

**Updated Settings Reader Pattern** (with category support):
```python
async def get_setting_from_redis_or_env(
    redis,
    category: str,  # NEW: "rag_pipeline", "local_rag", "prompts", "abuse_prevention"
    setting_key: str,
    env_var: str,
    default_value: Any,
    value_type: type = str
) -> Any:
    """
    Get setting from Redis first, then fall back to environment variable.
    
    CRITICAL: No in-memory caching. Read from Redis every time to avoid
    "Zombie Settings" in multi-worker environments.
    
    Args:
        redis: Redis client instance
        category: Settings category (determines Redis key)
        setting_key: Key within the category settings dict
        env_var: Environment variable name for fallback
        default_value: Default if neither Redis nor env has the setting
        value_type: Type to convert the value to (int, float, bool, str)
    """
    # Try Redis first (read directly, NO CACHE)
    try:
        settings_json = await redis.get(f"admin:settings:{category}")
        if settings_json:
            settings = json.loads(settings_json)
            if setting_key in settings:
                return cast_value(settings[setting_key], value_type)
    except Exception as e:
        logger.debug(f"Error reading setting from Redis: {e}")
    
    # Fall back to environment variable
    env_value = os.getenv(env_var)
    if env_value is not None:
        return cast_value(env_value, value_type)
    
    # Use default
    return default_value


# Convenience functions for each category
async def get_rag_pipeline_setting(redis, key: str, env_var: str, default: Any, vtype: type = str):
    return await get_setting_from_redis_or_env(redis, "rag_pipeline", key, env_var, default, vtype)

async def get_local_rag_setting(redis, key: str, env_var: str, default: Any, vtype: type = str):
    return await get_setting_from_redis_or_env(redis, "local_rag", key, env_var, default, vtype)

async def get_prompt_setting(redis, key: str, env_var: str, default: Any, vtype: type = str):
    return await get_setting_from_redis_or_env(redis, "prompts", key, env_var, default, vtype)

async def get_abuse_prevention_setting(redis, key: str, env_var: str, default: Any, vtype: type = str):
    return await get_setting_from_redis_or_env(redis, "abuse_prevention", key, env_var, default, vtype)
```

**Success Criteria**:
- ✅ Settings reader supports all new setting categories
- ✅ Type conversion handles bool, int, float, str correctly
- ✅ No in-memory caching (direct Redis reads)
- ✅ Fallback to environment variables works
- ✅ Test bool conversion thoroughly (Redis "false" string → Python `False`)

**Estimated Time**: 3-4 hours (includes type conversion testing)

---

### Phase 3: Backend Service Integration

**Objective**: Update services to read settings via settings reader

**Modified Files**:
- `backend/rag_pipeline.py` - Read RETRIEVER_K, MAX_CHAT_HISTORY_PAIRS, MIN_VECTOR_SIMILARITY, SYSTEM_INSTRUCTION, NO_KB_MATCH_RESPONSE
- `backend/services/router.py` - Read MAX_LOCAL_QUEUE_DEPTH, LOCAL_TIMEOUT_SECONDS
- `backend/services/rewriter.py` - Read REWRITER_SYSTEM_PROMPT
- `backend/services/redis_vector_cache.py` - Read REDIS_CACHE_SIMILARITY_THRESHOLD, SEMANTIC_CACHE_TTL_SECONDS

**Implementation Pattern**:
```python
# Before (direct env read):
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "12"))

# After (settings reader):
async def get_retriever_k(redis) -> int:
    """Get RETRIEVER_K setting from Redis or env."""
    return await get_setting_from_redis_or_env(
        redis,
        "retriever_k",
        "RETRIEVER_K",
        12,
        int
    )

# In RAG pipeline:
redis = await get_redis_client()
retriever_k = await get_retriever_k(redis)
```

**Lazy Loading for Feature Flags**:
```python
# Feature flags need special handling - check on each request
async def should_use_local_rewriter(redis) -> bool:
    """Check if local rewriter should be used."""
    return await get_setting_from_redis_or_env(
        redis,
        "enable_local_rewriter",
        "USE_LOCAL_REWRITER",
        False,
        bool
    )

# In router service:
if await should_use_local_rewriter(redis):
    # Use local rewriter

# Prompt Management:
async def get_rewriter_prompt(redis) -> str:
    """Get rewriter system prompt from Redis or env."""
    return await get_setting_from_redis_or_env(
        redis,
        "rewriter_system_prompt",
        "REWRITER_SYSTEM_PROMPT",
        DEFAULT_REWRITER_PROMPT,  # Fallback to hardcoded default
        str
    )

# In rewriter service:
prompt = await get_rewriter_prompt(redis)
```

**Success Criteria**:
- ✅ All services read settings via settings reader
- ✅ Settings changes take effect on next request
- ✅ Feature flags can be toggled at runtime
- ✅ Backward compatibility maintained (env vars still work)

**Estimated Time**: 8-10 hours

---

### Phase 4: Admin Frontend Components

**Objective**: Create generic, data-driven UI components for settings management

**Architecture Decision**: **Generic Settings Component**
- **Rationale**: You have 3 categories now, but will have 10+ later. Data-driving the UI prevents code duplication.
- **Strategy**: Build a generic `SettingsCard` component that takes a configuration object (label, key, type, min, max, description).

**New Files**:
- `admin-frontend/src/components/SettingsCard.tsx` - Generic settings component
- `admin-frontend/src/components/RAGPipelineSettings.tsx` - Uses SettingsCard
- `admin-frontend/src/components/LocalRAGSettings.tsx` - Uses SettingsCard
- `admin-frontend/src/components/PromptSettings.tsx` - Uses SettingsCard with textarea fields

**Modified Files**:
- `admin-frontend/src/types/index.ts` - Add new setting types
- `admin-frontend/src/lib/api.ts` - Add new API clients
- `admin-frontend/src/app/dashboard/page.tsx` - Add new components

**New UI Component: Textarea** (`admin-frontend/src/components/ui/textarea.tsx`):
```typescript
// textarea.tsx - Based on shadcn/ui pattern
import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
```

**Generic SettingsCard Component**:
```typescript
// SettingsCard.tsx
interface SettingField {
  key: string;
  label: string;
  type: 'number' | 'text' | 'boolean' | 'select' | 'textarea';  // Added textarea
  min?: number;
  max?: number;
  step?: number;
  minLength?: number;   // For textarea validation
  maxLength?: number;   // For textarea validation
  rows?: number;        // For textarea height
  description?: string;
  options?: { value: string; label: string }[]; // For select type
}

interface SettingsCardProps {
  title: string;
  description: string;
  fields: SettingField[];
  settings: Record<string, any>;
  sources: Record<string, "redis" | "environment">;
  onUpdate: (key: string, value: any) => void;
  onSubmit: () => Promise<void>;
  loading?: boolean;
}

export function SettingsCard({ title, description, fields, settings, sources, onUpdate, onSubmit, loading }: SettingsCardProps) {
  // Generic form rendering based on field configuration
  // Handles number inputs, text inputs, checkboxes, selects
  // Shows source indicators (Redis vs environment)
  // Validates based on min/max constraints
}
```

**Component Usage**:
```typescript
// RAGPipelineSettings.tsx
const RAG_PIPELINE_FIELDS: SettingField[] = [
  {
    key: 'retriever_k',
    label: 'Retriever K',
    type: 'number',
    min: 1,
    max: 50,
    description: 'Number of documents to retrieve'
  },
  {
    key: 'max_chat_history_pairs',
    label: 'Max Chat History Pairs',
    type: 'number',
    min: 1,
    max: 20,
    description: 'Maximum chat history pairs to include'
  },
  // ... more fields
];

export function RAGPipelineSettings() {
  const [settings, setSettings] = useState<RAGPipelineSettings>({});
  const [sources, setSources] = useState<Record<string, "redis" | "environment">>({});
  
  return (
    <SettingsCard
      title="RAG Pipeline Settings"
      description="Tune retrieval and generation parameters"
      fields={RAG_PIPELINE_FIELDS}
      settings={settings}
      sources={sources}
      onUpdate={(key, value) => setSettings(prev => ({ ...prev, [key]: value }))}
      onSubmit={handleSubmit}
    />
  );
}
```

**Settings Categories**:

**RAG Pipeline Settings**:
- Retriever K (1-50)
- Max Chat History Pairs (1-20)
- Min Vector Similarity (0.0-1.0)
- LLM Model Name (dropdown)
- LLM Temperature (0.0-2.0)
- Max Output Tokens (1-8192)

**Local RAG Settings**:
- Max Local Queue Depth (1-20)
- Local Timeout Seconds (0.5-10.0)
- Redis Cache Similarity Threshold (0.0-1.0)
- Semantic Cache TTL Seconds (60+)
- Enable Local Rewriter (toggle)
- Enable Infinity Embeddings (toggle)
- Enable Redis Cache (toggle)

**Prompt Settings**:
- Rewriter System Prompt (textarea, 50-5000 chars) - Query rewriting prompt
- RAG System Instruction (textarea, 50-10000 chars) - Main LLM system prompt
- QA With History Prompt (textarea, 20-2000 chars) - History-aware rephrasing prompt
- No KB Match Response (textarea, 10-500 chars) - Response when no match found

**SettingsCard Textarea Rendering** (example):
```typescript
// In SettingsCard.tsx render logic
{field.type === 'textarea' && (
  <div className="space-y-2">
    <Label htmlFor={field.key}>
      {field.label}
      {sources[field.key] && (
        <span className="ml-2 text-xs text-muted-foreground">
          ({sources[field.key]})
        </span>
      )}
    </Label>
    <Textarea
      id={field.key}
      value={settings[field.key] || ""}
      onChange={(e) => onUpdate(field.key, e.target.value)}
      rows={field.rows || 6}
      minLength={field.minLength}
      maxLength={field.maxLength}
      placeholder={field.description}
    />
    {field.maxLength && (
      <div className="text-xs text-muted-foreground text-right">
        {(settings[field.key]?.length || 0).toLocaleString()} / {field.maxLength.toLocaleString()} characters
      </div>
    )}
  </div>
)}
```

**Success Criteria**:
- ✅ UI components match existing AbusePreventionSettings style
- ✅ Settings can be viewed and updated
- ✅ Source indicators show Redis vs environment
- ✅ Validation errors are displayed
- ✅ Success/error messages are clear

**Estimated Time**: 6-8 hours

---

### Phase 5: Testing & Validation

**Objective**: Ensure settings management works correctly

**Test Cases**:

1. **API Tests**:
   - GET settings returns current values with sources
   - PUT settings validates and saves correctly
   - Invalid settings are rejected
   - Settings persist across service restarts

2. **Integration Tests**:
   - Settings changes take effect on next request
   - Feature flags toggle services correctly
   - Cache invalidation works
   - Environment variable fallback works

3. **UI Tests**:
   - Settings load correctly
   - Updates save successfully
   - Validation errors display
   - Source indicators are accurate

**Success Criteria**:
- ✅ All tests pass
- ✅ Settings work in production-like environment
- ✅ Performance meets targets (< 100ms update latency)

**Estimated Time**: 4-6 hours

---

## Integration Points

### Current System Integration

| Component | Current | New Integration | Impact |
|-----------|---------|----------------|--------|
| **RAG Pipeline** | Direct `os.getenv()` | Settings reader | Refactor initialization |
| **Inference Router** | Direct `os.getenv()` | Settings reader | Refactor initialization |
| **Redis Vector Cache** | Direct `os.getenv()` | Settings reader | Refactor initialization |
| **Admin Frontend** | Abuse Prevention only | Add RAG/Local RAG | New components |
| **Settings API** | Abuse Prevention only | Add RAG/Local RAG | New endpoints |

### Compatibility Matrix

| Component | Current | Proposed | Compatible? | Migration Strategy |
|-----------|---------|----------|------------|-------------------|
| Settings Reader | Abuse Prevention only | All settings | ✅ Yes | Extend existing pattern |
| Backend Services | Direct env reads | Settings reader | Needs refactor | Gradual migration |
| Admin Frontend | Single category | Multiple categories | ✅ Yes | Add new components |
| Redis Storage | Single key | Multiple keys | ✅ Yes | Use separate keys |

---

## Configuration

### Settings Categories

**1. RAG Pipeline Settings** (`admin:settings:rag_pipeline`):
```json
{
  "retriever_k": 12,
  "max_chat_history_pairs": 2,
  "min_vector_similarity": 0.3,
  "llm_model_name": "gemini-2.5-flash-lite-preview-09-2025",
  "llm_temperature": 0.2,
  "max_output_tokens": null
}
```

**2. Local RAG Settings** (`admin:settings:local_rag`):
```json
{
  "max_local_queue_depth": 3,
  "local_timeout_seconds": 2.0,
  "redis_cache_similarity_threshold": 0.90,
  "semantic_cache_ttl_seconds": 259200,
  "enable_local_rewriter": false,
  "enable_infinity_embeddings": false,
  "enable_redis_cache": false
}
```

**3. Prompt Settings** (`admin:settings:prompts`):
```json
{
  "rewriter_system_prompt": "You are a Query Resolution Engine...",
  "rag_system_instruction": "You are a neutral, factual expert on Litecoin...",
  "qa_with_history_prompt": "Given the above conversation, generate a standalone question...",
  "no_kb_match_response": "I couldn't find any relevant content in our knowledge base yet."
}
```

**4. Abuse Prevention Settings** (`admin:settings:abuse_prevention`):
- Already implemented, no changes needed

### Environment Variable Fallback

All settings maintain environment variable fallback:

| Setting | Redis Key | Environment Variable | Default |
|---------|-----------|---------------------|---------|
| `retriever_k` | `retriever_k` | `RETRIEVER_K` | `12` |
| `max_local_queue_depth` | `max_local_queue_depth` | `MAX_LOCAL_QUEUE_DEPTH` | `3` |
| `redis_cache_similarity_threshold` | `redis_cache_similarity_threshold` | `REDIS_CACHE_SIMILARITY_THRESHOLD` | `0.90` |
| `rewriter_system_prompt` | `rewriter_system_prompt` | `REWRITER_SYSTEM_PROMPT` | (hardcoded default) |
| `rag_system_instruction` | `rag_system_instruction` | `RAG_SYSTEM_INSTRUCTION` | (hardcoded default) |
| `no_kb_match_response` | `no_kb_match_response` | `NO_KB_MATCH_RESPONSE` | (hardcoded default) |
| `qa_with_history_prompt` | `qa_with_history_prompt` | `QA_WITH_HISTORY_PROMPT` | (hardcoded default) |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **"Zombie Settings" in Multi-Worker** | High | Medium | **No in-memory cache** - read directly from Redis every time |
| **Invalid Settings Applied** | High | Low | Comprehensive validation before save |
| **Performance Degradation** | Low | Low | Redis reads are sub-millisecond, no caching needed |
| **Feature Flag Toggle Issues** | Medium | Medium | Lazy-load services, test thoroughly |
| **Prompt Injection via Admin** | High | Low | Validate prompts don't contain injection patterns, sanitize on save |
| **Prompt Length/Token Limits** | Medium | Low | Enforce max length, validate token count if possible |
| **Settings Loss on Redis Restart** | Low | Low | Environment variable fallback |
| **Backward Compatibility** | Medium | Low | Maintain env var support, gradual migration |

### Critical Decisions

1. **Settings Storage Strategy**:
   - **Option A**: Single Redis key with all settings (JSON blob)
   - **Option B**: Separate Redis keys per category - **SELECTED**
   - **Rationale**: Better organization, easier to manage, matches existing pattern

2. **In-Memory Caching Strategy**:
   - **Option A**: In-memory cache with manual invalidation
   - **Option B**: No in-memory cache, direct Redis reads - **SELECTED**
   - **Rationale**: Avoids "Zombie Settings" in multi-worker environments. Redis latency is sub-millisecond, so caching provides minimal benefit.

3. **Feature Flag Runtime Toggle**:
   - **Option A**: Require service restart for feature flags
   - **Option B**: Runtime toggle with lazy service loading - **SELECTED**
   - **Rationale**: Maximum flexibility, enables A/B testing

4. **Settings Validation**:
   - **Option A**: Client-side only
   - **Option B**: Server-side validation with client-side hints - **SELECTED**
   - **Rationale**: Security and data integrity

5. **Frontend Component Architecture**:
   - **Option A**: Separate component for each settings category
   - **Option B**: Generic SettingsCard component with data-driven configuration - **SELECTED**
   - **Rationale**: Scalable, prevents code duplication, easier to maintain

---

## Testing Strategy

### Unit Tests

1. **Settings Reader**:
   - Test Redis read with env fallback
   - Test cache invalidation
   - Test type conversion

2. **Settings API**:
   - Test GET endpoint returns correct values
   - Test PUT endpoint validates and saves
   - Test invalid settings are rejected

3. **Backend Services**:
   - Test services read settings correctly
   - Test feature flag toggling
   - Test settings changes take effect

### Integration Tests

1. **End-to-End Flow**:
   - Update setting via API
   - Verify setting takes effect on next request
   - Verify setting persists across restart

2. **Feature Flag Toggle**:
   - Toggle feature flag via UI
   - Verify service behavior changes
   - Verify no errors on toggle

3. **Settings Rollback**:
   - Delete setting from Redis
   - Verify fallback to environment variable
   - Verify system continues working

### UI Tests

1. **Settings Display**:
   - Verify all settings load correctly
   - Verify source indicators are accurate
   - Verify validation errors display

2. **Settings Update**:
   - Update setting via UI
   - Verify success message
   - Verify setting reflects in next read

---

## Monitoring & Metrics

### New Metrics

```python
# Settings management metrics
settings_updates_total = Counter(
    "admin_settings_updates_total",
    "Total number of settings updates",
    ["category"]  # "rag_pipeline", "local_rag", "abuse_prevention"
)

settings_update_duration_seconds = Histogram(
    "admin_settings_update_duration_seconds",
    "Settings update operation duration",
    ["category"]
)

settings_validation_errors_total = Counter(
    "admin_settings_validation_errors_total",
    "Total number of settings validation errors",
    ["category", "error_type"]
)

settings_redis_reads_total = Counter(
    "admin_settings_redis_reads_total",
    "Total number of settings reads from Redis",
    ["category"]
)

settings_redis_read_duration_seconds = Histogram(
    "admin_settings_redis_read_duration_seconds",
    "Redis read duration for settings",
    ["category"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]
)
```

### Key Performance Indicators

1. **Update Latency**: < 100ms for settings update
2. **Read Latency**: < 1ms for settings read from Redis (sub-millisecond)
3. **Validation Success Rate**: > 99% (invalid settings rejected)
4. **Type Conversion Success Rate**: 100% (all Redis string values correctly converted)

### Grafana Dashboards

1. **Settings Management Dashboard**:
   - Settings update frequency by category
   - Update latency by category
   - Validation error rate
   - Cache hit/miss ratio

---

## Success Criteria

### Functional Success

- ✅ Admin can view all settings with current values and sources
- ✅ Admin can update settings via UI
- ✅ Settings take effect immediately without restart
- ✅ Settings validation prevents invalid configurations
- ✅ Settings persist across service restarts
- ✅ Environment variable fallback works correctly

### Performance Success

- ✅ Settings update latency < 100ms
- ✅ Settings read latency < 10ms (cached)
- ✅ No performance degradation in RAG pipeline
- ✅ Cache hit rate > 90%

### User Experience Success

- ✅ UI is intuitive and responsive
- ✅ Settings are organized logically
- ✅ Validation errors are clear and actionable
- ✅ Success/error messages are informative

---

## Future Enhancements

### Phase 2: Advanced Features

1. **Settings History**: Track all setting changes with timestamps and user info
2. **Settings Presets**: Save and load configuration presets (e.g., "High Performance", "Cost Optimized")
3. **Settings Templates**: Pre-configured settings for common scenarios
4. **Bulk Updates**: Update multiple settings at once
5. **Settings Export/Import**: Export settings to JSON, import from file
6. **Prompt Versioning**: Track prompt changes, rollback to previous versions
7. **Prompt Testing**: Test prompt changes on sample queries before applying
8. **Prompt Templates Library**: Pre-built prompt templates for different use cases

### Phase 3: Advanced Validation

1. **Dependent Settings**: Validate settings that depend on other settings
2. **Range Suggestions**: Suggest optimal ranges based on metrics
3. **Impact Analysis**: Show estimated impact of setting changes
4. **Rollback UI**: One-click rollback to previous values

### Phase 4: Observability Integration

1. **Settings Impact Metrics**: Track how setting changes affect performance
2. **A/B Testing**: Compare performance with different settings
3. **Auto-Tuning**: Suggest optimal settings based on metrics
4. **Alerting**: Alert when settings cause performance degradation

---

## Implementation Checklist

### Phase 0: Backend Refactoring (Prerequisites)
- [ ] **Create `backend/api/v1/admin/settings/` directory structure**
- [ ] **Create `backend/api/v1/admin/settings/__init__.py` with router aggregation**
- [ ] **Create `backend/api/v1/admin/settings/base.py` with shared auth dependency**
- [ ] **Move existing `settings.py` to `settings/abuse_prevention.py`**
- [ ] **Create `backend/constants/prompts.py` with default prompts**
- [ ] Update `backend/main.py` router imports

### Phase 1: Backend API Extensions
- [ ] Create `backend/api/v1/admin/settings/rag_pipeline.py`
- [ ] Create `backend/api/v1/admin/settings/local_rag.py`
- [ ] Create `backend/api/v1/admin/settings/prompts.py`
- [ ] **Add DELETE endpoints for reset functionality**
- [ ] **Add prompt validation (length, injection detection)**
- [ ] Write API tests
- [ ] Document API endpoints

### Phase 2: Settings Reader Extensions
- [ ] Extend settings reader utility
- [ ] **Implement robust type conversion (bool, int, float, str)**
- [ ] **Remove in-memory caching (read directly from Redis)**
- [ ] **Test bool conversion thoroughly (Redis "false" → Python False)**
- [ ] Test environment variable fallback
- [ ] Test multi-worker scenario (no stale cache)

### Phase 3: Backend Service Integration
- [ ] Refactor `rag_pipeline.py` to use settings reader
- [ ] **Refactor `rag_pipeline.py` to read prompts dynamically (SYSTEM_INSTRUCTION, NO_KB_MATCH_RESPONSE)**
- [ ] Refactor `router.py` to use settings reader
- [ ] **Refactor `rewriter.py` to read REWRITER_SYSTEM_PROMPT dynamically**
- [ ] Refactor `redis_vector_cache.py` to use settings reader
- [ ] Implement lazy loading for feature flags
- [ ] **Ensure prompts are re-read on each request (no caching)**
- [ ] Write integration tests

### Phase 4: Admin Frontend Components
- [ ] **Create `admin-frontend/src/components/ui/textarea.tsx`**
- [ ] **Create generic `SettingsCard.tsx` component (data-driven)**
- [ ] **Extend SettingsCard to support textarea fields for prompts**
- [ ] Create `RAGPipelineSettings.tsx` (uses SettingsCard)
- [ ] Create `LocalRAGSettings.tsx` (uses SettingsCard)
- [ ] Create `PromptSettings.tsx` (uses SettingsCard with textareas)
- [ ] Add TypeScript types
- [ ] Add API client functions (GET/PUT/DELETE for each category)
- [ ] Integrate into dashboard
- [ ] **Add character count indicators for prompt fields**
- [ ] **Add "Reset to Default" buttons for each category**
- [ ] Write UI tests

### Phase 5: Testing & Validation

**Backend Test Files**:
- [ ] `backend/tests/test_settings_reader.py` - Test type conversion (especially bool), Redis fallback, category support
- [ ] `backend/tests/test_admin_settings_api.py` - Test all settings endpoints (GET/PUT/DELETE for each category)
- [ ] `backend/tests/test_prompt_validation.py` - Test prompt injection detection, length validation

**Test Cases for Bool Conversion** (critical):
```python
def test_bool_conversion():
    assert cast_value("false", bool) == False
    assert cast_value("False", bool) == False
    assert cast_value("0", bool) == False
    assert cast_value("no", bool) == False
    assert cast_value("off", bool) == False
    assert cast_value("true", bool) == True
    assert cast_value("True", bool) == True
    assert cast_value("1", bool) == True
    assert cast_value("yes", bool) == True
    assert cast_value("on", bool) == True
    assert cast_value(True, bool) == True
    assert cast_value(False, bool) == False
```

**Frontend Test Files**:
- [ ] `admin-frontend/__tests__/SettingsCard.test.tsx` - Test generic component with all field types
- [ ] `admin-frontend/__tests__/PromptSettings.test.tsx` - Test textarea, character count, validation

**Integration Tests**:
- [ ] Write integration tests
- [ ] Perform end-to-end testing
- [ ] Validate performance targets (< 1ms Redis reads)
- [ ] Test in production-like environment
- [ ] **Test multi-worker scenario (no Zombie Settings)**

### Phase 6: Documentation & Deployment
- [ ] Update API documentation
- [ ] Create user guide for admin frontend
- [ ] Document settings and their effects
- [ ] Create runbook for operations
- [ ] Deploy to production

---

## References

- Existing implementation: `backend/api/v1/admin/settings.py`
- Settings reader utility: `backend/utils/settings_reader.py`
- Admin frontend: `admin-frontend/src/components/AbusePreventionSettings.tsx`
- Local RAG feature: `docs/features/DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md`
- RAG Pipeline prompts: `backend/rag_pipeline.py` (lines 127-194)
- Rewriter prompts: `backend/services/rewriter.py` (lines 33-49)
- Router service: `backend/services/router.py` (lines 97-124)
- Redis vector cache: `backend/services/redis_vector_cache.py` (lines 96-123)

---

## Appendix: Decision Log

### Decision 1: Settings Storage Strategy
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Separate Redis keys per category  
**Rationale**: Better organization, easier to manage, matches existing pattern  
**Status**: ✅ Approved

### Decision 2: Feature Flag Runtime Toggle
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Runtime toggle with lazy service loading  
**Rationale**: Maximum flexibility, enables A/B testing  
**Status**: ✅ Approved

### Decision 3: In-Memory Caching Strategy
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: No in-memory caching, direct Redis reads  
**Rationale**: Avoids "Zombie Settings" in multi-worker environments. Redis latency is sub-millisecond.  
**Status**: ✅ Approved

### Decision 4: Settings Validation Strategy
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Server-side validation with client-side hints  
**Rationale**: Security and data integrity  
**Status**: ✅ Approved

### Decision 5: Frontend Component Architecture
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Generic SettingsCard component with data-driven configuration  
**Rationale**: Scalable, prevents code duplication, easier to maintain as settings categories grow  
**Status**: ✅ Approved

### Decision 6: API Directory Structure
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Create `settings/` subdirectory with separate files per category  
**Rationale**: Better organization, separation of concerns, easier to maintain  
**Status**: ✅ Approved

### Decision 7: Prompt Constants Location
**Date**: 2025-12-07  
**Status**: ✅ **APPROVED**  
**Decision**: Create `backend/constants/prompts.py` with all default prompts  
**Rationale**: Single source of truth for fallback values, easy to find and update  
**Status**: ✅ Approved

---

---

## Implementation Strategy: Using This Spec as a Meta-Prompt

This feature specification is designed to be used as a **meta-prompt** for AI-assisted development (e.g., Cursor Composer, GitHub Copilot).

### Step 1: Scaffold the Backend (Morning)

**Prompt for Cursor Composer**:
```
Based on the "Phase 1: Backend API Extensions" and "Phase 2: Settings Reader Utility Extensions" 
sections of this feature spec, scaffold:

1. Pydantic models in `backend/api/v1/admin/settings/rag_pipeline.py` and `local_rag.py`
2. Updated `settings_reader.py` utility with robust type conversion

Requirements:
- Settings reader MUST read directly from Redis (no in-memory caching)
- Type conversion must handle: bool (including "false" string → False), int, float, str
- Follow the existing pattern from `backend/api/v1/admin/settings.py` (abuse prevention)
- Ensure Redis keys match Python variable names (snake_case)
```

### Step 2: Type Conversion Testing (Morning)

**Critical Test Cases**:
```python
# Test bool conversion thoroughly
assert cast_value("false", bool) == False
assert cast_value("False", bool) == False
assert cast_value("0", bool) == False
assert cast_value("true", bool) == True
assert cast_value("True", bool) == True
assert cast_value("1", bool) == True
```

### Step 3: Build API Endpoints (Mid-Day)

Use Pydantic `Field(..., alias="...")` if Redis keys differ from Python variable names, though keeping them identical is better.

### Step 4: Frontend Generic Component (Afternoon)

**Prompt for Cursor Composer**:
```
Based on the "Phase 4: Admin Frontend Components" section, create:

1. Generic `SettingsCard.tsx` component that takes a configuration object
2. `RAGPipelineSettings.tsx` that uses SettingsCard with field definitions
3. `LocalRAGSettings.tsx` that uses SettingsCard with field definitions

The SettingsCard should handle:
- Number inputs (with min/max/step)
- Text inputs
- Boolean checkboxes
- Select dropdowns
- Source indicators (Redis vs environment)
- Validation errors
- Loading states
```

### Step 5: Runtime Toggle Verification (Evening)

**Test Scenario**:
1. Start a long-running generation process
2. Toggle a setting mid-stream (if streaming) or immediately after
3. Verify the next request picks up the new setting value
4. Test with multiple workers to ensure no "Zombie Settings"

---

**Document Version**: 1.2  
**Last Updated**: 2025-12-07  
**Author**: System Architecture Team  
**Reviewers**: TBD  
**Red Team Review**: ✅ Incorporated multi-worker architecture considerations and "Zombie Settings" mitigation  
**Codebase Review**: ✅ Analyzed existing code, documented bugs found, added limitations section

