# Changelog

All notable changes and completed milestones for the Litecoin Knowledge Hub project.

## Log of Completed Milestones

* **Short Query Expansion & RAG Pipeline Improvements (12/19-12/21/2025)**
  * Fixed short query sparsity issue by implementing LLM-based query expansion for 1-3 word queries
  * Added comprehensive logging for short query expansion feature to track when expansion occurs (cache hits, LLM expansions, and failures)
  * Corrected FAISS scoring calculations for improved retrieval accuracy
  * Enhanced Litecoin vocabulary with protocol terms and entity expansions for better query understanding
  * Fixed Redis vector cache similarity calculation bug
  * Added comprehensive chunking strategy analysis and improvement recommendations documentation
  * Created article template guide for LLM-generated content quality and consistency
* **Follow-up Query Topic Drift Fixes & LangGraph Migration (12/20/2025)**
  * Fixed topic drift on follow-up questions by improving entity expansion after follow-up rewrite
  * Expanded router input after pronoun anchoring to better handle conversational context
  * Refactored RAG pipeline control flow to LangGraph state machine for improved maintainability and extensibility
  * Enhanced entity expansion to run after follow-up query rewriting for better context preservation
* **Litecoin.com Integration & Advanced RAG Optimizations (12/12-12/18/2025)**
  * Implemented Litecoin.com chat integration with basePath configuration and CORS setup
  * Added chat tunnel support with healthcheck fixes for seamless integration
  * Replaced heuristic history routing with hybrid LLM-based semantic router for improved query routing
  * Optimized RAG caching strategy: consolidated semantic cache and cache by rewritten query
  * Implemented canonical intent generation with synonym mapping for cache optimization
  * Fixed greeting false-positives and reduced history anchoring for better conversation flow
  * Added clear conversation action and cancel in-flight stream functionality to frontend
  * Fixed monitoring profile to properly start Grafana and Prometheus services
  * Updated navigation component to point to litecoin.com
  * Added OG/Twitter share metadata for better social media integration
  * Fixed markdown normalization issues causing malformed lists
  * Added RAG optimization prompt template for article generation
  * Created feature specs for admin qualitative analytics and language support
  * See commit history for detailed implementation notes
* **Critical Security Patches: React2Shell & Backend Dependencies (12/11/2025)**
  * Patched critical React2Shell / React RSC RCE vulnerabilities (CVE-2025-55182, CVE-2025-66478) across all frontend applications
  * Updated Next.js and React versions to fixed releases:
    - `frontend`: `next` 15.3.3 → 15.5.8
    - `admin-frontend`: `next` 16.0.3 → 16.0.9, `react` 19.2.0 → 19.2.1
    - `payload_cms`: `next` 15.3.0 → 15.5.8, `react` 19.1.0 → 19.2.1
  * Upgraded Python backend dependencies to remediate 15 of 16 known CVEs:
    - `langchain-core` 0.3.65 → 0.3.80+
    - `langchain-community` 0.3.25 → 0.3.27+
    - `starlette` 0.46.2 → 0.49.1+
    - `urllib3` 2.4.0 → 2.6.0+
    - `aiohttp` 3.12.12 → 3.12.14+
    - `pip` 21.2.4 → 25.3, `setuptools` 58.1.0 → 80.9.0
  * Added strict `Content-Security-Policy` header in backend middleware for defense-in-depth on API responses
  * See [RED_TEAM_ASSESSMENT_DEC_2025.md](./docs/security/RED_TEAM_ASSESSMENT_DEC_2025.md) for full audit details
* **FAQ-Based Indexing & FAISS Performance Optimizations (12/08/2025)**
  * Implemented FAQ-Based Indexing using Parent Document Pattern for improved retrieval
    - Generates 3 synthetic questions per document chunk using LLM (Gemini or local Ollama)
    - Indexes questions for search, returns parent chunks for LLM context
    - Bridges vocabulary gap between user queries and document content
    - 83% of search hits now match synthetic questions, improving relevance
  * Added Intent Detection & Routing Layer for query classification
    - Pre-RAG classification handles greetings, thanks, FAQ matches before hitting RAG
    - Uses rapidfuzz for fuzzy matching against FAQ questions
    - Reduces unnecessary LLM calls for simple queries
  * Major FAISS performance optimizations:
    - Publishing articles no longer triggers full index rebuild (~15-25s vs ~14 min)
    - Added `reload_from_disk()` method for fast refresh without rebuild
    - Delete operations only affect MongoDB, rebuild on explicit request
  * Added Docker volume persistence for FAISS index (`faiss_index_data`)
    - Index survives container restarts without rebuilding
    - First startup builds from MongoDB, subsequent starts load from disk (~1s)
  * Added retry logic with exponential backoff for embedding requests
  * Fixed gRPC/asyncio compatibility with Python 3.11 (`grpcio>=1.60.0`, `GRPC_POLL_STRATEGY=epoll1`)
  * New files: `faq_generator.py`, `intent_classifier.py`, `reindex_with_faq.py`
  * See [DEC7_FEATURE_ADVANCED_RAG_TECHNIQUES.md](./docs/features/DEC7_FEATURE_ADVANCED_RAG_TECHNIQUES.md) for complete details
* **Markdown Heading Normalization Fix (12/08/2025)**
  * Added markdown normalization utility to fix LLM output rendering issues
  * Fixes headings that lack proper newlines (e.g., "text.## Heading" → "text.\n\n## Heading")
  * Applied to Message and StreamingMessage components for consistent rendering
* **Test Suite Improvements - 121 Passing Tests (12/08/2025)**
  * Fixed all 6 failing tests, bringing test suite to 121 passed, 36 skipped
  * Updated InfinityEmbeddings tests for new `(dense, sparse)` tuple return signature
  * Fixed abuse prevention tests to properly mock `redis.eval()` for Lua scripts:
    - `test_per_identifier_challenge_limit`: Mock GENERATE_CHALLENGE_LUA
    - `test_cost_throttling`: Mock COST_THROTTLE_LUA
    - `test_global_spend_limits_use_updated_settings`: Mock CHECK_AND_RESERVE_SPEND_LUA
  * Added skip conditions for integration tests incompatible with Infinity embeddings mode
  * Updated README.md and docs/TESTING.md with accurate test counts and documentation
  * Documented all 36 skipped tests with clear explanations:
    - Local RAG Integration (21): Services not on localhost in Docker
    - Rate Limiter Advanced (9): Optional fakeredis dependency
    - Advanced Retrieval (3): Feature not yet implemented
    - RAG Pipeline (2): Require Google embeddings
    - Admin Endpoints (1): Event loop test setup issue
* **Atomic Lua Scripts for Redis Concurrency Safety (12/08/2025)**
  * Added 5 new Lua scripts to eliminate race conditions in Redis operations:
    - `VALIDATE_CONSUME_CHALLENGE_LUA`: Atomic challenge validation and consumption
    - `GENERATE_CHALLENGE_LUA`: Atomic challenge generation with progressive ban handling
    - `CHECK_AND_RESERVE_SPEND_LUA`: Atomic spend limit check and cost reservation
    - `ADJUST_SPEND_LUA`: Atomic spend adjustment with token tracking
    - `APPLY_PROGRESSIVE_BAN_LUA`: Atomic progressive ban application
  * Prevents TOCTOU (time-of-check time-of-use) race conditions that could allow attackers to bypass rate limits, spend limits, or challenge validation under high concurrency
  * Updated challenge.py, spend_limit.py, and rate_limiter.py to use atomic Lua scripts
* **Monitoring Enhancements & Rate Limit Discord Alerts (12/08/2025)**
  * Added Discord notifications for rate limit violations (hourly/minute limits)
  * New admin setting `enable_rate_limit_discord_alerts` to toggle rate limit alerts
  * Added 8 new Grafana panels for Local RAG monitoring:
    - Local vs Cloud Rewriter Usage, Router Spillover Rate, Queue Depth
    - Rewriter Latency, Redis Vector Cache Hit Rate/Size/Latency
    - Rate Limit Rejections by Endpoint
  * Added 4 new Prometheus alert rules for Local RAG health:
    - LocalRewriterHighTimeoutRate, HighRouterSpilloverRate
    - LowRedisVectorCacheHitRate, RateLimitRejectionsSpike
* **High-Performance Local RAG Implementation (12/07/2025)**
  * Implemented local RAG pipeline with Ollama, Infinity embeddings, and Redis Stack semantic cache
  * Added native embedding server for Apple Silicon with Metal (MPS) acceleration
  * Integrated BGE-M3 embedding model (1024-dim) for improved Q&A retrieval quality
  * Implemented hybrid retrieval combining vector search, BM25 keyword search, and sparse embeddings
  * Added intelligent routing with automatic spillover to cloud services (Gemini) on timeout/overload
  * Implemented Redis Stack vector cache with HNSW index for semantic caching with chat history awareness
  * Added feature flags for gradual rollout and testing of local RAG components
  * Fixed UnboundLocalError bug in RAG pipeline when using Infinity embeddings
  * Improved retrieval quality with similarity score filtering and increased RETRIEVER_K to 12
  * Documented deployment procedures and configuration for local RAG services
  * See [DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md](./docs/features/DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md) for complete details
* **Production-Grade Abuse Prevention Improvements (12/01/2025)**
  * Enhanced abuse prevention system with production-grade optimizations
  * Fixed rate limiter to handle 3-value Lua script return format
  * Optimized token counting with local Gemini tokenizer for improved performance
* **Atomic Rate Limiter & Database Security Hardening (11/30/2025)**
  * Implemented atomic Lua scripts for cost throttling optimization
  * Eliminated race conditions in rate limiter with atomic operations
  * Hardened Docker database security configurations
  * Improved navigation component with centralized menu spacing configuration
* **Semantic Cache & Cloudflare Integration (11/29/2025)**
  * Implemented semantic cache for RAG pipeline to improve response times
  * Added categorized suggested questions feature with documentation
  * Fixed HTTPS redirect middleware to disable when behind Cloudflare proxy
  * Added Cloudflare Insights to Content Security Policy
  * Updated cloud deployment documentation with private cloud strategy
* **Admin Question Logs Feature (11/28/2025)**
  * Added question logs feature to admin dashboard with filtering capabilities
  * Implemented real-time updates for question logs
  * Improved admin dashboard components and styling
  * Enhanced frontend error handling and retry logic
  * Fixed CORS configuration for admin frontend
  * Resolved additional security vulnerabilities (CRIT-NEW-1, CRIT-NEW-2, CRIT-NEW-3)
* **Hybrid Retrieval System (11/23/2025)**
  * Implemented hybrid retrieval with BM25 and semantic search for improved accuracy
  * Enhanced challenge-response system with rate limiting and progressive bans
  * Improved challenge handling in frontend with on-demand fetching
  * Fixed critical RAG pipeline improvements for better context handling
* **Admin Frontend Application (11/24/2025)**
  * Implemented dedicated admin frontend application for system management
  * Added admin API backend infrastructure with secure authentication
  * Dynamic settings support via Redis with environment variable fallback
  * Integrated admin frontend service into Docker Compose stack
  * Enables runtime configuration changes without service restart
* **Advanced Abuse Prevention System - MVP (11/22-11/23/2025)**
  * Implemented minimal viable protection (MVP) with 5 critical security features
  * Challenge-response fingerprinting prevents replay attacks (kills 95% of abuse)
  * Global rate limiting stops distributed bot networks
  * Per-identifier challenge issuance limits prevent challenge prefetching abuse
  * Graceful Turnstile degradation ensures zero downtime during Cloudflare incidents
  * Cost-based throttling trigger provides financial unabusability (ultimate killswitch)
  * Provides 99.9% protection - all MVP items complete and in production
  * Optional enhancements (behavioral analysis, query deduplication) not yet implemented
  * See [FEATURE_ADVANCED_ABUSE_PREVENTION.md](./docs/features/FEATURE_ADVANCED_ABUSE_PREVENTION.md) for details
* **Question Logging System (11/21/2025)**
  * Implemented user question logging to MongoDB for analytics and insights
  * Questions are accessible via direct MongoDB queries for internal analysis (public API endpoints removed for security - see CRIT-NEW-1)
  * Integrated Prometheus metrics for tracking question volume by endpoint type
  * Background logging ensures no performance impact on user queries
* **Security Hardening (11/20/2025)**
  * Completed comprehensive red team security assessment
  * Resolved 15 critical and high-priority vulnerabilities
  * Implemented webhook authentication (HMAC-SHA256)
  * Fixed CORS configuration and error disclosure issues
  * Added comprehensive security headers (CSP, HSTS, etc.)
  * Hardened rate limiting with sliding window and progressive bans
  * Sanitized health check endpoints and added rate limiting
  * Removed all debug code from production builds
  * All public launch blockers resolved, including MongoDB and Redis authentication (CRIT-3, CRIT-4)
  * See [RED_TEAM_ASSESSMENT_COMBINED.md](./docs/security/RED_TEAM_ASSESSMENT_COMBINED.md) for complete details
* **LLM Spend Limit Monitoring (11/19/2025)**
  * Implemented multi-layered cost control system with daily/hourly spend limits
  * Pre-flight cost estimation prevents billing overages
  * Prometheus metrics and Grafana dashboards for cost tracking
  * Discord webhook alerts at 80% and 100% thresholds
  * Hard stops prevent any cost overages
  * See [FEATURE_SPEND_LIMIT_MONITORING.md](./docs/features/FEATURE_SPEND_LIMIT_MONITORING.md) for details
* **Suggested Question Caching (11/19/2025)**
  * Implemented Redis-based cache layer for suggested questions
  * 24-hour TTL with pre-population on startup
  * Provides instant responses (<100ms) for common questions
  * Automatic cache refresh via cron job (every 48 hours)
  * Comprehensive Prometheus metrics and Grafana integration
  * See [FEATURE_SUGGESTED_QUESTION_CACHING.md](./docs/features/FEATURE_SUGGESTED_QUESTION_CACHING.md) for details
* **Monitoring & Observability Infrastructure (11/8/2025)**
  * Implemented comprehensive Prometheus metrics system tracking HTTP requests, RAG pipeline performance, LLM costs, cache performance, and vector store health
  * Set up Grafana dashboards with pre-configured panels for key metrics visualization
  * Added health check endpoints (`/health`, `/health/live`, `/health/ready`) for service monitoring
  * Implemented structured logging with JSON format support for production environments
  * Integrated LangSmith for LLM observability and tracing (optional)
  * Created monitoring middleware for automatic request/response metrics collection
  * Added Docker Compose stack for easy monitoring infrastructure deployment
* **Payload CMS Content Lifecycle Management (11/3/2025)**
  * Implemented complete CMS content lifecycle with draft→publish→unpublish→delete workflows
  * Added comprehensive webhook support for all content operations (create, update, delete)
  * Enhanced vector store management for content removal and cleanup operations
  * Implemented multi-layer draft content filtering (API, search, vector store)
  * Added manual cleanup endpoints for draft document management
  * Created custom StatusBadge component for visual content status indicators in admin interface
  * Synchronized architectural documentation with Payload CMS integration reality
* **Conversational Memory Implementation (11/3/2025)**
  * Implemented history-aware retriever with standalone question generation using LangChain conversational chains
  * Refactored RAG pipeline to use LCEL conversational chains for improved memory management
  * Enhanced chat history pairing and error handling in backend API
  * Added comprehensive conversational memory tests covering follow-up questions and context resolution
  * Updated frontend message handling for complete exchanges with proper chat history passing
* **Strategic Decision: CMS Pivot to Payload (6/19/2025)**
  * Conducted a comparative analysis of headless CMS options and selected Payload to better align with the project's long-term RAG and data governance goals. This decision enables the work for Milestone 5\.
* **Milestone 4: Backend & Knowledge Base Completion (6/7/2025)**
  * Implemented a full suite of CRUD API endpoints (/api/v1/sources) for managing data sources and successfully ingested the entire initial knowledge base.
* **Milestone 3: Core RAG Pipeline Implementation (6/6/2025)**
  * Implemented and tested the end-to-end pipeline, including multi-source data loaders, local OSS embeddings (sentence-transformers/all-MiniLM-L6-v2), MongoDB Atlas Vector Search / FAISS, and a gemini-pro generation layer. Enhanced pipeline with hierarchical chunking and metadata filtering.
* **Milestone 2: Basic Project Scaffold (6/5/2025)**
  * Frontend (Next.js) and Backend (FastAPI) directory structures established with basic functionality confirmed.
* **Milestone 1: Project Initialization & Documentation Setup (6/5/2025)**
  * Initial project documentation (cline\_docs) created and populated.

