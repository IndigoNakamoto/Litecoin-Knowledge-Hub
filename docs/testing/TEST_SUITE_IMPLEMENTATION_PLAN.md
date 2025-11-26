# Comprehensive Test Suite Implementation Plan

## Overview

This document outlines the plan to implement a professional-grade test suite for the Litecoin Knowledge Hub. The goal is to achieve **80-90% code coverage** with realistic, production-ready tests that validate critical functionality before the Litecoin Foundation announcement goes wide.

**Status**: 📝 **Planning Phase**

**Priority**: 🔴 **CRITICAL** - Highest leverage improvement before public launch

**Estimated Time**: 6-8 hours total

**Last Updated**: 2025-11-20

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Grok's Suggestions Evaluation](#groks-suggestions-evaluation)
3. [Implementation Plan](#implementation-plan)
4. [Test Structure](#test-structure)
5. [Test Cases](#test-cases)
6. [Coverage Goals](#coverage-goals)
7. [CI/CD Integration](#cicd-integration)
8. [Success Criteria](#success-criteria)
9. [Risks & Mitigations](#risks--mitigations)

---

## Current State Assessment

### What Exists ✅

1. **Test Files Present** (16 files in `backend/tests/`):
   - `test_rag_pipeline.py` - Standalone script, not pytest-structured
   - `test_conversational_memory.py` - Standalone script
   - `test_rate_limiter.py` - **Proper pytest tests** ✅
   - `test_webhook_auth.py` - Standalone script with manual testing
   - `test_spend_limit.py` - **Proper pytest tests** ✅
   - Various other test scripts

2. **Dependencies Available**:
   - `pytest` ✅
   - `pytest-asyncio` ✅
   - `pytest-mock` ✅
   - `fastapi` (includes `TestClient`) ✅

3. **Test Infrastructure**:
   - ❌ No `conftest.py` (shared fixtures)
   - ❌ No proper test structure (mix of pytest and standalone scripts)
   - ❌ No coverage tracking (`pytest-cov` not in requirements)
   - ❌ No integration tests using `TestClient`
   - ❌ No frontend tests

### What's Missing ❌

1. **Shared Test Infrastructure**:
   - No `conftest.py` with shared fixtures
   - No test database/vector store setup/teardown
   - No mock configurations for external services

2. **Integration Tests**:
   - No FastAPI endpoint tests using `TestClient`
   - No end-to-end conversational flow tests
   - No webhook integration tests

3. **Test Coverage**:
   - No coverage reporting
   - No coverage badges
   - Unknown actual coverage percentage

4. **Frontend Tests**:
   - No Playwright or other E2E tests
   - No component tests

---

## Grok's Suggestions Evaluation

### ✅ **Excellent Suggestions** (Implement As-Is)

1. **Backend Test Structure** - The proposed file structure is solid
2. **Conversational Memory Tests** - Critical for demonstrating RAG quality
3. **Rate Limiting Progressive Bans** - Important for production readiness
4. **Spend Limit Hard Stops** - Already partially tested, needs expansion
5. **Webhook HMAC Validation** - Security-critical, needs proper pytest structure
6. **Coverage Badge** - Great for visibility

### ⚠️ **Needs Adaptation**

1. **conftest.py Fixtures** - Grok's example is too simplistic:
   - Need to handle MongoDB/Redis test isolation
   - Need to mock Google API calls (cost control)
   - Need proper vector store test fixtures
   - Need FastAPI TestClient fixture

2. **Test Data** - Need actual test fixtures:
   - Small KB document set for deterministic tests
   - Mock LLM responses for cost control
   - Test user questions

3. **Frontend Tests** - Playwright is good, but:
   - Need to ensure backend is running or mocked
   - Need to handle async operations properly

### ❌ **Missing from Grok's Plan**

1. **Existing Test Migration** - Need to convert standalone scripts to pytest
2. **Test Database Isolation** - Each test should have clean state
3. **Mock Strategy** - When to mock vs. use real services
4. **CI/CD Integration** - How tests run in CI
5. **Performance Tests** - Response time assertions

---

## Implementation Plan

### Phase 1: Foundation (2 hours) 🔴 **START HERE**

**Goal**: Set up test infrastructure and convert existing tests to pytest structure.

#### Tasks:

1. **Create `conftest.py`** with shared fixtures:
   ```python
   # backend/tests/conftest.py
   - TestClient fixture for FastAPI
   - Mock Redis client fixture
   - Mock MongoDB client fixture  
   - Mock Google API (LLM) fixture
   - Test vector store fixture (isolated)
   - Test data fixtures (KB documents)
   ```

2. **Add `pytest-cov` to requirements.txt**:
   ```bash
   pip install pytest-cov
   ```

3. **Create test data fixtures**:
   - `backend/tests/fixtures/kb_docs.json` - Small, deterministic KB documents
   - `backend/tests/fixtures/test_questions.json` - Test user questions

4. **Convert existing standalone tests**:
   - Run each standalone script and refactor into pytest functions, preserving asserts
   - `test_conversational_memory.py` → pytest structure
   - `test_webhook_auth.py` → pytest structure (keep manual tests as separate)

5. **Add `mongomock` to requirements.txt**:
   ```bash
   pip install mongomock
   ```

### Phase 2: Core Backend Tests (3-4 hours) 🔴 **HIGH PRIORITY**

**Goal**: Comprehensive tests for critical backend functionality.

#### Tasks:

1. **`test_rag_pipeline.py`** (Expand existing):
   - ✅ Initial query retrieval
   - ✅ Follow-up questions with context
   - ✅ Cache hit/miss behavior
   - ✅ No KB match handling
   - ✅ Source filtering (published only)
   - ✅ Chat history truncation

2. **`test_conversational_memory.py`** (Convert & expand):
   - ✅ Pronoun resolution ("Who created it?")
   - ✅ Ambiguous reference resolution ("What about the second one?")
   - ✅ Multi-turn conversations
   - ✅ History truncation at MAX_CHAT_HISTORY_PAIRS

3. **`test_rate_limiting.py`** (Expand existing):
   - ✅ Sliding window accuracy
   - ✅ Progressive ban escalation (1min → 5min → 15min → 60min)
   - ✅ Ban expiration
   - ✅ Cloudflare header handling
   - ✅ IP extraction from various headers

4. **`test_spend_limits.py`** (Expand existing):
   - ✅ Daily limit hard stop
   - ✅ Hourly limit hard stop
   - ✅ Pre-flight cost estimation
   - ✅ Cost recording
   - ✅ Graceful degradation on Redis errors

5. **`test_webhook_auth.py`** (Convert to pytest):
   - ✅ Valid HMAC signature acceptance
   - ✅ Invalid signature rejection
   - ✅ Expired timestamp rejection (5-minute window)
   - ✅ Missing headers rejection
   - ✅ Replay attack prevention

6. **`test_sync_payload.py`** (NEW):
   - ✅ Create document → appears in vector store
   - ✅ Update document → vector store updated
   - ✅ Delete document → removed from vector store
   - ✅ Unpublish document → removed from vector store
   - ✅ Draft documents → not in vector store

### Phase 3: API Integration Tests (1-2 hours) 🟡 **MEDIUM PRIORITY**

**Goal**: Test FastAPI endpoints end-to-end.

#### Tasks:

1. **`test_api_chat.py`** (NEW):
   - ✅ POST `/api/v1/chat` - Basic query
   - ✅ POST `/api/v1/chat` - With chat history
   - ✅ POST `/api/v1/chat` - Rate limiting
   - ✅ POST `/api/v1/chat` - Spend limit exceeded (integration test)
   - ✅ POST `/api/v1/chat` - Suggested question cache hit
   - ✅ POST `/api/v1/chat` - Response time < 0.5s (performance assertion)

2. **`test_api_stream.py`** (NEW):
   - ✅ POST `/api/v1/chat/stream` - Streaming response
   - ✅ POST `/api/v1/chat/stream` - Cache hit streaming
   - ✅ POST `/api/v1/chat/stream` - Error handling

3. **`test_api_health.py`** (NEW):
   - ✅ GET `/health` - Public health check
   - ✅ GET `/health/detailed` - Detailed health
   - ✅ GET `/health/live` - Liveness probe
   - ✅ GET `/health/ready` - Readiness probe

### Phase 4: Frontend Tests (1-2 hours) 🟢 **LOW PRIORITY**

**Goal**: Basic E2E tests for critical user flows.

#### Tasks:

1. **Setup Playwright**:
   ```bash
   cd frontend
   npm init playwright@latest
   ```

2. **`tests/chat.spec.ts`**:
   - ✅ Initial question submission
   - ✅ Follow-up question with context
   - ✅ Streaming response display
   - ✅ Error handling UI

### Phase 5: Coverage & CI/CD (30 minutes) 🟢 **POLISH**

**Goal**: Make tests visible and automated.

#### Tasks:

1. **Add coverage reporting**:
   ```bash
   pytest --cov=backend --cov-report=term-missing --cov-report=html
   ```

2. **Add coverage badge to README**:
   ```markdown
   ![Tests](https://github.com/your-repo/actions/workflows/tests.yml/badge.svg)
   ![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)
   ```

3. **Create test script**:
   ```bash
   # scripts/run-tests.sh
   pytest backend/tests/ -v --cov=backend --cov-report=term-missing
   ```

---

## Test Structure

### Directory Layout

```
backend/
  tests/
    conftest.py                    # Shared fixtures
    fixtures/
      kb_docs.json                 # Test knowledge base documents
      test_questions.json          # Test user questions
    test_rag_pipeline.py          # RAG pipeline unit tests
    test_conversational_memory.py  # Conversational memory tests
    test_rate_limiting.py         # Rate limiting tests (expand existing)
    test_spend_limits.py          # Spend limit tests (expand existing)
    test_webhook_auth.py          # Webhook auth tests (convert to pytest)
    test_sync_payload.py          # Payload sync integration tests (NEW)
    test_api_chat.py              # Chat API endpoint tests (NEW)
    test_api_stream.py            # Stream API endpoint tests (NEW)
    test_api_health.py            # Health endpoint tests (NEW)

frontend/
  tests/
    chat.spec.ts                  # Playwright E2E tests (NEW)
```

### conftest.py Structure (Refined Version)

**Note**: This refined version includes async support, proper cleanup, and uses `mongomock` for realistic MongoDB testing.

```python
# backend/tests/conftest.py

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import os
import json
import time
from backend.main import app
from backend.dependencies import get_redis_client, get_mongo_client, get_vector_store
from backend.rag_pipeline import ingest_documents  # Assuming this exists for ingestion

# Enable asyncio for tests
pytest_plugins = "pytest_asyncio"

# Load test data
@pytest.fixture(scope="session")
def test_kb_docs():
    """Load deterministic test knowledge base documents."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "kb_docs.json")
    with open(fixture_path, 'r') as f:
        return json.load(f)

@pytest.fixture(scope="session")
def test_questions():
    """Load test user questions."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_questions.json")
    with open(fixture_path, 'r') as f:
        return json.load(f)

# FastAPI TestClient with overrides
@pytest.fixture
def client(override_dependencies):
    return TestClient(app)

# Override dependencies for isolation
@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch, mock_redis, mock_mongo, mock_llm):
    """Automatically override dependencies for all tests."""
    monkeypatch.setattr("backend.dependencies.get_redis_client", lambda: mock_redis)
    monkeypatch.setattr("backend.dependencies.get_mongo_client", lambda: mock_mongo)
    # Add more overrides as needed

# Mock Redis
@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.incrbyfloat = AsyncMock(return_value=1.0)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zremrangebyscore = AsyncMock(return_value=1)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zrange = AsyncMock(return_value=[])
    redis_mock.hget = AsyncMock(return_value="0")
    redis_mock.hincrby = AsyncMock(return_value=100)
    yield redis_mock
    # Cleanup if needed

# Mock MongoDB (using mongomock for realism)
@pytest.fixture
def mock_mongo():
    """Mock MongoDB client using mongomock for realistic behavior."""
    import mongomock
    mock_client = mongomock.MongoClient()
    yield mock_client
    mock_client.close()

# Mock Google LLM API
@pytest.fixture
def mock_llm(monkeypatch):
    """Mock Google Generative AI for cost control and deterministic responses."""
    mock_generate = AsyncMock()
    mock_generate.return_value = MagicMock(
        text="Mock LLM response",
        usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=20)
    )
    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", mock_generate)
    yield mock_generate

# Isolated vector store with test data
@pytest.fixture(autouse=True)
def test_vector_store(test_kb_docs, tmp_path):
    """Setup isolated FAISS vector store with test docs using tmp_path for isolation."""
    # Use tmp_path for temporary FAISS index to avoid collisions
    vs = get_vector_store()  # Assuming this returns a new instance or clears
    vs.delete_collection()  # Clear if exists
    ingest_documents(test_kb_docs)  # Ingest test data
    yield vs
    vs.delete_collection()  # Teardown
```

### Test Fixture Files

**`fixtures/kb_docs.json`** (example):
```json
[
  {
    "id": "doc1",
    "title": "Litecoin History",
    "markdown": "Litecoin was created by Charlie Lee in October 2011.",
    "status": "published",
    "metadata": {"author": "test", "tags": ["history"]}
  },
  {
    "id": "doc2",
    "title": "Litecoin Features",
    "markdown": "Features: Faster blocks, Scrypt algorithm, SegWit.",
    "status": "published",
    "metadata": {"author": "test", "tags": ["features"]}
  },
  {
    "id": "doc3",
    "title": "Draft Document",
    "markdown": "This is a draft document.",
    "status": "draft",
    "metadata": {"author": "test"}
  }
]
```

**`fixtures/test_questions.json`**:
```json
[
  {"query": "Who created Litecoin?", "expected": "Charlie Lee"},
  {"query": "When was it created?", "expected": "2011"}
]
```

---

## Test Cases

### 1. Conversational Memory Tests

**File**: `test_conversational_memory.py`

```python
def test_follow_up_questions(client, test_kb_docs):
    """Test that follow-up questions resolve pronouns correctly."""
    # First message establishes context
    resp1 = client.post("/api/v1/chat", json={
        "query": "Who created Litecoin?",
        "chat_history": []
    })
    assert resp1.status_code == 200
    assert "Charlie Lee" in resp1.json()["answer"].lower()
    
    # Follow-up with pronoun reference
    resp2 = client.post("/api/v1/chat", json={
        "query": "When did he create it?",
        "chat_history": [
            {"role": "human", "content": "Who created Litecoin?"},
            {"role": "ai", "content": resp1.json()["answer"]}
        ]
    })
    assert resp2.status_code == 200
    answer = resp2.json()["answer"].lower()
    assert any(year in answer for year in ["2011", "october 2011"])

def test_ambiguous_reference_resolution(client, test_kb_docs):
    """Test resolution of ambiguous references like 'the second one'."""
    # Simulate conversation where AI mentioned multiple items
    history = [
        {"role": "human", "content": "What are some Litecoin features?"},
        {"role": "ai", "content": "Litecoin has: 1) Faster blocks, 2) Scrypt algorithm, 3) SegWit support"}
    ]
    
    resp = client.post("/api/v1/chat", json={
        "query": "What about the second one?",
        "chat_history": history
    })
    assert resp.status_code == 200
    # Should resolve to Scrypt algorithm
    assert "scrypt" in resp.json()["answer"].lower()
```

### 2. Rate Limiting Tests

**File**: `test_rate_limiting.py` (expand existing)

```python
@pytest.mark.asyncio
async def test_progressive_ban_escalation(client, mock_redis):
    """Test that progressive bans escalate: 1min → 5min → 15min → 60min."""
    config = RateLimitConfig(
        requests_per_minute=2,  # Low limit for testing
        requests_per_hour=100,
        identifier="test",
        enable_progressive_limits=True
    )
    
    # First violation: 1 minute ban
    # ... make 3 requests rapidly
    # Assert ban_expiry is now + 60 seconds
    
    # Second violation: 5 minute ban
    # ... wait for first ban to expire, then violate again
    # Assert ban_expiry is now + 300 seconds
```

### 3. Spend Limit Tests

**File**: `test_spend_limits.py` (expand existing)

```python
@pytest.mark.asyncio
async def test_daily_limit_hard_stop(client, mock_redis, mock_llm):
    """Test that requests are rejected when daily limit is exceeded."""
    # Set daily cost to limit - 0.1
    mock_redis.get = AsyncMock(return_value=str(DAILY_SPEND_LIMIT_USD - 0.1))
    
    # Make request that would exceed limit
    resp = client.post("/api/v1/chat", json={"query": "What is Litecoin?"})
    
    assert resp.status_code == 429
    assert "spend_limit_exceeded" in resp.json()["error"]
    assert "daily" in resp.json()["type"]
```

**File**: `test_api_chat.py` (spend limit integration test)

```python
def test_chat_spend_limit_exceeded(client, mock_redis):
    """Integration test: Chat endpoint rejects requests when spend limit exceeded."""
    # Set daily cost over limit
    mock_redis.get.return_value = str(1000)  # Over daily limit
    
    resp = client.post("/api/v1/chat", json={"query": "Test"})
    
    assert resp.status_code == 429
    assert "spend_limit_exceeded" in resp.json()["error"]
    assert "daily spend limit" in resp.json()["error"]["message"].lower()
```

### 4. Webhook Auth Tests

**File**: `test_webhook_auth.py` (convert to pytest)

```python
def test_valid_hmac_signature(client):
    """Test that valid HMAC signatures are accepted."""
    payload = {"operation": "create", "doc": {...}}
    signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
    
    resp = client.post(
        "/api/v1/sync/payload",
        json=payload,
        headers={
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": str(int(time.time()))
        }
    )
    assert resp.status_code == 200

def test_replay_attack_prevention(client):
    """Test that old timestamps (>5 minutes) are rejected."""
    payload = {"operation": "create", "doc": {...}}
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
    signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
    
    resp = client.post(
        "/api/v1/sync/payload",
        json=payload,
        headers={
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": old_timestamp
        }
    )
    assert resp.status_code == 401
```

### 5. Payload Sync Tests

**File**: `test_sync_payload.py` (NEW)

```python
def test_create_document_appears_in_vector_store(client, test_vector_store):
    """Test that creating a document in Payload syncs to vector store."""
    payload = {
        "operation": "create",
        "doc": {
            "id": "test-doc-123",
            "title": "Test Document",
            "markdown": "This is test content about Litecoin.",
            "status": "published"
        }
    }
    
    # Send webhook
    resp = client.post("/api/v1/sync/payload", json=payload, headers=valid_headers)
    assert resp.status_code == 200
    
    # Wait for background processing
    time.sleep(2)
    
    # Query vector store
    results = test_vector_store.similarity_search("Litecoin", k=1)
    assert len(results) > 0
    assert "test-doc-123" in results[0].metadata.get("id")

def test_unpublish_removes_from_vector_store(client, test_vector_store):
    """Test that unpublishing a document removes it from vector store search results."""
    # First create/publish
    create_payload = {
        "operation": "create",
        "doc": {
            "id": "test-unpub",
            "title": "Test Unpublish",
            "markdown": "This is test content for unpublish test.",
            "status": "published"
        }
    }
    resp = client.post("/api/v1/sync/payload", json=create_payload, headers=valid_headers)
    assert resp.status_code == 200
    
    time.sleep(2)
    results = test_vector_store.similarity_search("test content", k=1)
    assert len(results) > 0
    assert "test-unpub" in results[0].metadata.get("id")
    
    # Unpublish
    unpub_payload = {
        "operation": "update",
        "doc": {
            "id": "test-unpub",
            "title": "Test Unpublish",
            "markdown": "This is test content for unpublish test.",
            "status": "unpublished"
        }
    }
    resp = client.post("/api/v1/sync/payload", json=unpub_payload, headers=valid_headers)
    assert resp.status_code == 200
    
    time.sleep(2)
    results = test_vector_store.similarity_search("test content", k=1)
    # Document should be removed from search results (only published docs are searchable)
    assert len(results) == 0 or "test-unpub" not in [r.metadata.get("id") for r in results]
```

---

## Coverage Goals

### Target Coverage by Module

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `rag_pipeline.py` | ~30% | 85% | 🔴 Critical |
| `rate_limiter.py` | ~70% | 90% | 🔴 Critical |
| `monitoring/spend_limit.py` | ~60% | 85% | 🔴 Critical |
| `api/v1/sync/payload.py` | ~20% | 85%+ | 🔴 Critical (security-sensitive) |
| `main.py` (endpoints) | ~10% | 75% | 🟡 High |
| `cache_utils.py` | ~0% | 70% | 🟢 Medium |
| **Overall** | **~25%** | **80-90%** | **🔴 Critical** |

### Coverage Commands

```bash
# Run tests with coverage
pytest backend/tests/ -v --cov=backend --cov-report=term-missing

# Generate HTML report
pytest backend/tests/ --cov=backend --cov-report=html
open htmlcov/index.html

# Coverage for specific module
pytest backend/tests/test_rag_pipeline.py --cov=backend.rag_pipeline --cov-report=term-missing
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov=backend --cov-report=xml
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY_TEST }}
          MONGO_URI: ${{ secrets.MONGO_URI_TEST }}
          REDIS_URL: ${{ secrets.REDIS_URL_TEST }}
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

---

## Success Criteria

### Must Have ✅

1. **Coverage**: ≥80% overall, ≥85% for critical modules
2. **All Critical Tests Passing**: 
   - Conversational memory
   - Rate limiting
   - Spend limits
   - Webhook auth
3. **CI/CD Integration**: Tests run on every PR
4. **Coverage Badge**: Visible in README

### Nice to Have 🎯

1. **Frontend E2E Tests**: Basic Playwright tests
2. **Performance Tests**: Response time assertions
3. **Load Tests**: Rate limiting under load

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `conftest.py` with shared fixtures (using refined version with async support)
- [ ] Add `pytest-cov` to requirements.txt
- [ ] Add `mongomock` to requirements.txt
- [ ] Create test data fixtures (`kb_docs.json`, `test_questions.json`)
- [ ] Run each standalone script and refactor into pytest functions, preserving asserts
- [ ] Convert `test_conversational_memory.py` to pytest
- [ ] Convert `test_webhook_auth.py` to pytest structure

### Phase 2: Core Backend Tests
- [ ] Expand `test_rag_pipeline.py` with comprehensive cases
- [ ] Expand `test_conversational_memory.py` with edge cases
- [ ] Expand `test_rate_limiting.py` with progressive ban tests
- [ ] Expand `test_spend_limits.py` with hard stop tests
- [ ] Create `test_sync_payload.py` for Payload sync

### Phase 3: API Integration Tests
- [ ] Create `test_api_chat.py`
- [ ] Create `test_api_stream.py`
- [ ] Create `test_api_health.py`

### Phase 4: Frontend Tests
- [ ] Setup Playwright
- [ ] Create `tests/chat.spec.ts`

### Phase 5: Coverage & CI/CD
- [ ] Add coverage reporting
- [ ] Add coverage badge to README
- [ ] Create test script (`scripts/run-tests.sh`)
- [ ] Setup GitHub Actions workflow

---

## Notes & Considerations

### Mocking Strategy

**Mock External Services**:
- Google Generative AI (LLM) - Cost control, deterministic responses
- Redis - For rate limiting and spend tracking tests
- MongoDB - For vector store tests (use test database)

**Use Real Services** (with test data):
- FAISS vector store - Use isolated test index
- FastAPI app - Use TestClient with overridden dependencies

### Test Data Management

- **Small, Deterministic KB**: Use 5-10 test documents with known content
- **Isolated Test Environment**: Each test should start with clean state
- **No Production Data**: Never use production MongoDB/Redis in tests

### Performance Considerations

- **Fast Tests**: Mock LLM calls (no real API calls in unit tests)
- **Integration Tests**: Can use real services but with test data
- **Parallel Execution**: Use `pytest-xdist` for parallel test execution

---

## References

- [Grok's Original Suggestions](./user_instructions/example_project_kickoff_prompt.md) (attached input)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Playwright Documentation](https://playwright.dev/)

---

---

## Risks & Mitigations

### Potential Issues and Solutions

1. **Flaky Tests from Async Operations**
   - **Risk**: Tests may fail intermittently due to async timing issues
   - **Mitigation**: Use `pytest-asyncio` properly, add appropriate `await` statements, and use `asyncio.sleep()` with reasonable timeouts in integration tests

2. **Test Database/Redis Collisions**
   - **Risk**: Tests running in parallel may interfere with each other
   - **Mitigation**: Use `tmp_path` for FAISS indexes, `mongomock` for isolated MongoDB, and unique keys per test for Redis

3. **Mock LLM Responses Not Matching Real Behavior**
   - **Risk**: Tests pass but production fails due to mock mismatch
   - **Mitigation**: Keep mocks simple but realistic, add integration tests that use real LLM (with cost controls) for critical paths

4. **Slow Test Execution**
   - **Risk**: Test suite takes too long, developers skip running tests
   - **Mitigation**: Mock external services in unit tests, use `pytest-xdist` for parallel execution, keep integration tests minimal

5. **Coverage Gaps in Edge Cases**
   - **Risk**: High coverage percentage but missing critical edge cases
   - **Mitigation**: Focus on critical paths first (RAG, auth, rate limiting), use coverage reports to identify untested branches

6. **CI/CD Test Failures**
   - **Risk**: Tests pass locally but fail in CI
   - **Mitigation**: Use Docker containers for consistent environments, test CI workflow locally with `act` (GitHub Actions local runner)

---

## Refined Implementation Tips

### Handling ⚠️ Adaptations

1. **conftest.py Fixtures**:
   - Use `tmp_path` for temporary FAISS indexes to avoid collisions
   - Add proper async support via `pytest-asyncio`
   - Implement cleanup in `yield` fixtures to ensure test isolation

2. **Test Data**:
   - Make `kb_docs.json` include varied cases (published/draft, with/without metadata)
   - Use deterministic test data for reproducible results
   - Keep test data small (5-10 documents) for fast execution

3. **Frontend Tests**:
   - If time is tight, mock the backend with Playwright's `page.route()` to avoid spinning up the full stack
   - Use `page.wait_for_selector()` for async operations

### Addressing ❌ Missing Items

1. **Existing Test Migration**:
   - Run each standalone script and refactor into pytest functions, preserving asserts
   - Keep original scripts as reference until migration is complete

2. **Test Database Isolation**:
   - Use `mongomock` for unit tests (fast, isolated)
   - Use temp Mongo container for integration tests (more realistic)

3. **Mock Strategy**:
   - **Rule**: Mock externals (LLM, Redis) for unit tests; use real (with test data) for integration
   - Document strategy in `conftest.py` comments

4. **Performance Tests**:
   - Add simple assertions like `assert response_time < 0.5` in API tests
   - Use `time.time()` before/after requests for timing

5. **CI/CD Integration**:
   - Add GitHub Actions badge: `[![Tests](https://github.com/your-repo/actions/workflows/tests.yml/badge.svg)](https://github.com/your-repo/actions/workflows/tests.yml)`
   - Ensure test secrets are configured in GitHub repository settings

---

## Final Polish Checklist

- [ ] Run `pytest --cov` after Phase 2—iterate until 85% on core files
- [ ] Commit with: `feat: Add comprehensive test suite (85% coverage, 50+ tests)`
- [ ] Update README milestone: `✅ Comprehensive test suite implemented (coverage: 88%)`
- [ ] Add test script to `package.json` or `Makefile` for easy execution
- [ ] Document test execution in `DEVELOPMENT.md`

---

**Next Steps**: Start with Phase 1 (Foundation) - Create `conftest.py` and convert existing tests to pytest structure.

