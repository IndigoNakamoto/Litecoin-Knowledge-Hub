# Testing Guide

## Test Suite Overview

The Litecoin Knowledge Hub has a comprehensive test suite with **121 passing tests** covering all critical backend functionality.

| Metric | Count |
|--------|-------|
| **Total Tests** | 157 |
| **Passing** | 121 |
| **Skipped** | 36 |
| **Warnings** | 30 (non-blocking deprecations) |

## Quick Start

### Running Tests in Production Container

If you have the production stack running:

```bash
# Run all tests
docker exec litecoin-backend python -m pytest /app/backend/tests -v

# Run with short output
docker exec litecoin-backend python -m pytest /app/backend/tests -q

# Run specific test file
docker exec litecoin-backend python -m pytest /app/backend/tests/test_rate_limiter.py -v
```

### Running Tests in Development Environment

```bash
# Using docker-compose dev environment
docker compose -f docker-compose.dev.yml run --rm \
  -v "$(pwd)/backend/tests:/app/tests" \
  -v "$(pwd)/backend:/app/backend" \
  backend pytest tests/ -vv
```

## Prerequisites

Create the required `.env` file in `backend/`:

```bash
cat > backend/.env << 'EOF'
ADMIN_TOKEN=litecoin-is-the-silver-to-bitcoins-gold
GOOGLE_API_KEY=test-key
MONGO_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
WEBHOOK_SECRET=test-webhook-secret-key
PAYLOAD_CMS_URL=http://localhost:3001
NEXT_PUBLIC_SKIP_CHALLENGE=true
EOF
```

## Test Categories

### Core Functionality (All Passing ✅)

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_abuse_prevention.py` | 6 | Challenge-response, rate limiting, cost throttling |
| `test_admin_endpoints.py` | 10 | Admin auth, settings, stats APIs |
| `test_admin_settings_integration.py` | 11 | Dynamic Redis settings propagation |
| `test_conversational_memory.py` | 7 | Context-aware retrieval, chat history |
| `test_rate_limiter.py` | 15 | Sliding window, progressive bans, IP extraction |
| `test_rate_limiter_simple.py` | 4 | Basic rate limit logic |
| `test_spend_limit.py` | 12 | Daily/hourly limits, key formats |
| `test_spend_limit_integration.py` | 6 | Discord alerts, Prometheus metrics |
| `test_security_headers.py` | 2 | Security headers, CORS |
| `test_security_headers_hsts.py` | 2 | HSTS in production |
| `test_https_redirect.py` | 6 | HTTPS enforcement |
| `test_webhook_auth.py` | 7 | HMAC signatures, replay prevention |
| `test_webhook_manual.py` | 3 | Webhook connectivity, payloads |
| `test_delete_fix.py` | 2 | Delete webhook handling |
| `test_astream_query.py` | 1 | Streaming responses |
| `test_local_rag_services.py` | 22 | Router, rewriter, embeddings, cache |
| `test_user_statistics.py` | 6 | User tracking, stats |

### Skipped Tests (36 total)

Tests are skipped when optional dependencies or infrastructure aren't available:

#### Local RAG Integration Tests (21 tests)
**File:** `test_local_rag_integration.py`

These tests check Ollama, Infinity, and Redis Stack services but expect them on `localhost`. Inside Docker, services communicate via container names (`ollama:11434`, `infinity:7997`), not `localhost`.

- `TestOllamaIntegration` (6) - "Ollama service not available on localhost:11434"
- `TestInfinityIntegration` (6) - "Embedding server not available on localhost:7997"
- `TestRedisStackIntegration` (4) - "Redis Stack not available on localhost:6380"
- `TestFullPipelineIntegration` (3) - "Not all local RAG services are available"
- `TestPerformance` (2) - Service availability checks

**Note:** The unit tests in `test_local_rag_services.py` (22 tests) cover the same logic with mocks.

#### Rate Limiter Advanced Tests (9 tests)
**Files:** `test_rate_limit_atomic.py`, `test_rate_limiter_idempotency.py`

Skip reason: `fakeredis not available, install with: pip install fakeredis`

These tests use `fakeredis` for realistic Redis simulation. Core rate limiter logic is covered by `test_rate_limiter.py` (15 tests) and `test_rate_limiter_simple.py` (4 tests).

#### Advanced Retrieval Tests (3 tests)
**File:** `test_advanced_retrieval.py`

Skip reason: `advanced_retrieval module not available`

These are placeholder tests for a feature not yet implemented.

#### RAG Pipeline Tests (2 tests)
**File:** `test_rag_pipeline.py`

- `test_hierarchical_chunking_and_retrieval` - Skipped when using Infinity embeddings mode
- `test_metadata_filtering` - `litecoin_docs_loader` module not available

#### Admin Endpoints (1 test)
**File:** `test_admin_endpoints.py`

- `test_track_unique_user` - Event loop closure issue in test setup

## Optional Commands

### Run with Coverage

```bash
docker exec litecoin-backend python -m pytest /app/backend/tests \
  --cov=backend --cov-report=term-missing -v
```

### Run Only Fast Tests

```bash
docker exec litecoin-backend python -m pytest /app/backend/tests \
  -m "not slow" -v
```

### Run Single Test File

```bash
docker exec litecoin-backend python -m pytest \
  /app/backend/tests/test_conversational_memory.py -v
```

### Run with Detailed Failure Output

```bash
docker exec litecoin-backend python -m pytest /app/backend/tests \
  -v --tb=long
```

## Warnings

The 30 warnings are non-blocking deprecation notices:

- **Pydantic V2**: Class-based config deprecation (will be fixed in future update)
- **LangChain**: `HuggingFaceEmbeddings` deprecation (migration planned)
- **HTTPX**: Content upload deprecation
- **Pytest**: `PytestReturnNotNoneWarning` for tests returning bool instead of None

These do not affect test functionality or application behavior.

## Continuous Integration

Tests run automatically on:
- Pull requests to `main` branch
- Push to `main` branch
- Manual workflow dispatch

## Adding New Tests

1. Create test file in `backend/tests/` with `test_` prefix
2. Use existing fixtures from `conftest.py`:
   - `mock_redis` - Async Redis mock
   - `mock_llm` - LLM response mock
   - `client` - FastAPI TestClient
   - `admin_client` - Admin-authenticated TestClient
3. Follow existing patterns for async tests (`@pytest.mark.asyncio`)
4. Run tests locally before committing

## Test Architecture

```
backend/tests/
├── conftest.py                    # Shared fixtures
├── test_abuse_prevention.py       # Challenge, rate limit, cost throttling
├── test_admin_endpoints.py        # Admin API tests
├── test_admin_settings_integration.py
├── test_advanced_retrieval.py     # Placeholder tests
├── test_astream_query.py          # Streaming tests
├── test_conversational_memory.py  # Chat context tests
├── test_delete_fix.py             # Webhook delete handling
├── test_https_redirect.py         # HTTPS enforcement
├── test_local_rag_integration.py  # Integration tests (skipped in CI)
├── test_local_rag_services.py     # Unit tests for local RAG
├── test_rag_pipeline.py           # RAG pipeline tests
├── test_rate_limit_atomic.py      # Requires fakeredis
├── test_rate_limiter.py           # Core rate limiter tests
├── test_rate_limiter_idempotency.py
├── test_rate_limiter_simple.py
├── test_security_headers.py
├── test_security_headers_hsts.py
├── test_spend_limit.py
├── test_spend_limit_integration.py
├── test_user_statistics.py
├── test_webhook_auth.py
└── test_webhook_manual.py
```
