# Commit History by Date

**Total Commits:** 416
**Total Days Worked:** 56

---

## 2025-12-18 (7 commits)

- Change navigation component to litecoin.com
- Fix greeting false-positives and reduce history anchoring
- frontend: add clear conversation action and cancel in-flight stream
- Fix: Enable monitoring profile to start Grafana and Prometheus
- Replace heuristic history routing with hybrid LLM-based semantic router
- Optimize RAG caching strategy: consolidate semantic cache and cache by rewritten query
- feat: implement canonical intent generation with synonym mapping for cache optimization

## 2025-12-17 (1 commit)

- feat: Add chat tunnel support and fix healthchecks for litecoin.com integration

## 2025-12-15 (2 commits)

- feat: configure basePath and CORS for litecoin.com/chat integration
- Fix: redirect domain root to /chat when basePath is set

## 2025-12-14 (4 commits)

- docs: Add feature spec for admin qualitative analytics
- docs: add language support feature spec
- Add RAG optimization prompt template for article generation
- Fix markdown normalization causing malformed lists

## 2025-12-13 (1 commit)

- Add OG/Twitter share metadata and update configs

## 2025-12-12 (3 commits)

- docs: Add RAG performance bottlenecks analysis
- Optimize RAG pipeline performance and improve error handling
- Fix navigation chevron rotation - remove horizontal shift on click

## 2025-12-11 (5 commits)

- Configure local MongoDB defaults and add backup tooling
- fix(security): patch critical React2Shell RCE and backend vulnerabilities
- fix(rag): avoid caching generic error responses for suggested questions
- docs(changelog): document React2Shell and backend security patches
- docs: update security documentation and implementation specs

## 2025-12-09 (1 commit)

- Add Discord alerts for spend limits and cost throttling

## 2025-12-08 (5 commits)

- feat: FAQ-Based Indexing & FAISS Performance Optimizations
- fix: Normalize markdown headings in LLM responses
- docs: Update changelog with FAQ indexing and FAISS optimizations
- feat: Add LaTeX symbol conversion and list formatting to markdown utils
- Add Litecoin.com integration plan documentation

## 2025-12-07 (10 commits)

- feat: Implement High-Performance Local RAG with Cloud Spillover
- feat(monitoring): Add Discord alerts for rate limits and Local RAG Grafana panels
- docs: Add monitoring enhancements to CHANGELOG
- feat(backend): add atomic Lua scripts for Redis concurrency safety
- fix(tests): update InfinityEmbeddings tests for new tuple return signature
- fix(tests): update tests to properly mock Lua script eval() calls
- docs: update test documentation with accurate counts (121 passed, 36 skipped)
- chore: enable local RAG features by default and update commit history
- docs: Add comprehensive Dynamic Admin Settings feature document (DEC7)
- docs: add Advanced RAG Techniques feature spec

## 2025-12-06 (9 commits)

- Add documentation: development cycles, security reviews, deployment guides, and specs
- Add MongoDB backup script and update configuration for Atlas migration
- Update admin settings, cost throttling, and add rebuild script
- Merge branch 'main' of https://github.com/IndigoNakamoto/Litecoin-Knowledge-Hub
- fix: Add missing lib files and fix .gitignore patterns
- Add article service for frontend API interactions
- docs: Update local RAG feature spec with unified 1024-dim architecture
- docs: Add response quality optimization guide to local RAG feature spec
- docs: Add Docker vs host networking notes for migration scripts

## 2025-12-04 (1 commit)

- docs: Update DEPLOYMENT.md to reflect actual 9-service production stack

## 2025-12-02 (1 commit)

- feat: implement warning design for input box when message exceeds character limit

## 2025-12-01 (13 commits)

- feat: Production-grade improvements to abuse prevention system
- fix: Update rate limiter to handle 3-value Lua script return format
- Optimize token counting with local Gemini tokenizer
- docs: Update LLM cost estimates (/million without cache, /million with cache)
- docs: Update CHANGELOG with recent milestones from commit history
- Fix UnboundLocalError in cost throttling by removing misplaced import statements
- Fix MongoDB connection string URL encoding for special characters
- Disable semantic cache for queries with chat history
- Add rebuild-backend.sh script for development
- Replace favicon.ico with favicon.png and update references
- Fix navigation scroll behavior for ChatWindow
- Implement user message pinning and jitter-free streaming
- Add rebuild-frontend.sh script for rebuilding frontend service

## 2025-11-30 (5 commits)

- refactor: rename Navigation component and centralize menu spacing config
- Implement atomic Lua scripts for cost throttling optimization
- fix: improve navigation z-index and mobile menu layout
- feat: Implement atomic rate limiter optimization to eliminate race conditions
- feat: implement Docker database security hardening

## 2025-11-29 (10 commits)

- Fix test failures: improve Redis mocking and async handling
- fix(backend): Disable HTTPS redirect middleware when behind Cloudflare
- fix(frontend): Add Cloudflare Insights to Content Security Policy
- docs: Add CORS and HTTPS redirect fix documentation
- chore: Add commit history generator script
- feat: implement semantic cache for RAG pipeline
- docs: Add feature document for categorized suggested questions
- docs: update cloud deployment readiness and playbook
- docs: update to Private Cloud strategy with dual Mac Mini cluster
- docs: add multi-region distributed private cloud option

## 2025-11-28 (14 commits)

- feat(admin): Add question logs feature with filtering and real-time updates
- refactor(admin): Improve admin dashboard components and styling
- feat(frontend): Improve error handling and retry logic
- fix(backend): Update challenge rate limit default to 1 second
- docs: Add commit history documentation
- refactor: remove rate limiting from health/metrics endpoints and exclude admin from global limits
- feat: improve chat UI layout and input box styling
- chore: update commit history and improve frontend code quality
- fix(cors): Fix CORS configuration for admin frontend
- security: Add comprehensive red team assessment and HTTPS enforcement
- fix(frontend): Use Host header for HTTPS redirect location
- security: Fix CRIT-NEW-2 rate limiting IP spoofing vulnerability
- security: Fix CRIT-NEW-1 - Bind monitoring ports to localhost only
- security: Fix CRIT-NEW-3 - Require Grafana admin password

## 2025-11-27 (18 commits)

- feat(backend): enhance abuse prevention with rate limiting, challenge response, and cost throttling
- feat(admin): add abuse prevention settings management UI
- docs(features): document advanced abuse prevention and admin rate limit features
- docs(fixes): add documentation for abuse prevention fixes and enhancements
- feat: Add user statistics tracking by fingerprint
- feat: Add user statistics router and tracking to main.py
- fix: Correctly extract base fingerprint hash for challenge validation
- test: Add test infrastructure and unit tests
- test: Add integration tests for admin settings changes
- docs: Add comprehensive test documentation
- chore: Add ADMIN_TOKEN to .env.example
- infra: Add Redis healthcheck and connection for abuse prevention features
- docs: Fix date in rate limiter documentation
- feat: Add global daily/hourly spend limit settings to admin dashboard
- fix: Prevent fingerprint collision in cost throttling
- feat: Improve error handling and retry logic in frontend
- docs: Update abuse analysis and add utility scripts
- Fix ESLint errors blocking frontend build

## 2025-11-25 (7 commits)

- docs: Update documentation with accurate implementation details
- docs: Improve README structure and add CHANGELOG
- docs: Update architecture diagram with governance, security middleware, and Redis
- docs: Expand architectural overview with three-workflow model and updated diagram
- docs: Add cloud deployment planning documents - capacity planning and readiness assessment
- docs: Add cloud deployment execution documents - playbook and readiness report template
- docs: reorganize documentation into logical subdirectories

## 2025-11-24 (8 commits)

- feat: Add admin API backend infrastructure
- feat: Add admin frontend application
- feat: Register admin API endpoints and fix CORS for admin frontend
- feat: Add dynamic settings support via Redis with env fallback
- feat: Add admin frontend service to Docker Compose
- docs: Update documentation and scripts for admin frontend
- Fix Redis connection pool exhaustion with singleton pattern
- Improve fingerprint-based rate limiting with stable hash identifiers

## 2025-11-23 (10 commits)

- fix: enable development mode rate limits for challenge endpoint
- feat: implement hybrid retrieval with BM25 and semantic search
- Merge branch 'fix/rag-hybrid-context-final' into main
- fix: implement critical RAG pipeline improvements
- Merge branch 'rag-pipeline-critical-fixes' into main
- feat(backend): enhance challenge-response system with rate limiting and progressive bans
- feat(frontend): improve challenge handling with on-demand fetching
- fix(cms): add TypeScript type annotations for admin components
- fix(cms): fix apostrophe encoding in content pages
- refactor(scripts): disable cron job setup in production script

## 2025-11-22 (23 commits)

- docs: Add minimal viable protection plan (5 items, <8 hours)
- Add abuse prevention utility modules
- Update Redis client for async test support
- Add global rate limiting and fingerprint-based rate limiting
- Integrate abuse prevention features into main API
- Update supporting infrastructure for abuse prevention
- Add frontend challenge-response fingerprinting integration
- Add abuse prevention tests and update existing tests
- Update environment variables documentation
- docs: Add comprehensive testing documentation and test article cleanup utilities
- feat: Improve development environment configuration and rate limiting
- feat: Improve vector store management and exclude test articles from sync
- docs: Update advanced abuse prevention feature doc to reflect MVP implementation
- feat: Add Google Embeddings support for vector store
- fix: Adjust cost throttling threshold default to --.10
- feat: Enforce challenge-response fingerprinting when enabled
- refactor: Improve RAG pipeline safety and performance
- docs: Add semantic cache feature documentation and update abuse prevention docs
- feat(frontend): redesign homepage and add new content pages
- feat(admin): style admin login page to match frontend
- fix(infrastructure): improve Docker setup and Next.js config
- Revert "feat(admin): style admin login page to match frontend"
- feat(admin): replace Payload logo with Litecoin logo

## 2025-11-21 (13 commits)

- test: Add test infrastructure for Phase 1
- test: Add test data fixtures for Phase 1
- test: Convert standalone tests to pytest structure (Phase 1)
- test: Fix import errors in existing test files
- feat: Add comprehensive LLM request logging to MongoDB
- docs: Add documentation for LLM logging and monitoring
- chore: Add utility scripts for testing and monitoring
- feat: Update Grafana dashboard with improved token metrics
- refactor: remove dead code and migrate to async-only RAG pipeline
- fix(rag): Fix document chain prompt template and streaming implementation
- Fix datetime serialization in Redis cache and service dependencies
- docs: Add advanced abuse prevention feature documentation
- docs: Add advanced abuse prevention feature documentation

## 2025-11-20 (16 commits)

- docs: add CC BY-NC-SA 4.0 license information to README
- chore: organize test scripts by moving them to scripts/ directory
- docs: Update security assessment with additional vulnerabilities
- Merge branch 'main' of https://github.com/IndigoNakamoto/Litecoin-Knowledge-Hub
- docs: Add cost estimates per million questions
- docs: consolidate red team assessment documents into single combined report
- feat(security): Enable MongoDB and Redis authentication (CRIT-3, CRIT-4)
- docs: Add MongoDB/Redis authentication documentation
- feat(scripts): Add MongoDB authentication helper scripts
- docs(security): Update assessment - CRIT-3 and CRIT-4 resolved
- fix(mongodb): Fix conditional authentication initialization
- fix(security): Resolve CRIT-NEW-3 and CRIT-NEW-4 - Access control and admin endpoint security
- test: Add test script for admin endpoint authentication
- docs: Update security assessment - All public launch blockers resolved
- Add commercial license information
- docs: Add comprehensive test suite implementation plan

## 2025-11-19 (15 commits)

- Fix CRIT-8: Secure CORS configuration
- Fix error information disclosure vulnerabilities (CRIT-NEW-2, CRIT-9, HIGH-NEW-5)
- docs: add spend limit monitoring and Discord alerting feature documentation
- docs: Add suggested question caching feature documentation
- Fix HIGH-NEW-2 and HIGH-NEW-4: Sanitize health endpoints and add rate limiting
- Update security score and blocker status in assessment
- Fix remaining blocker reference (singular, not plural)
- feat: implement suggested question caching with Redis
- feat: add monitoring and metrics for suggested question cache
- feat: add deployment configuration and cron job automation
- docs: update documentation for suggested question caching feature
- feat: Implement LLM spend limit monitoring with Redis tracking, Prometheus metrics, Discord alerts, and frontend warnings
- chore: Add automatic Docker cleanup to production scripts
- chore: Add backend/.env.bak to .gitignore
- docs: update README to reflect current security assessment status

## 2025-11-18 (23 commits)

- feat: enhance SuggestedQuestions with mobile support and question metadata
- refactor(ui): enhance styling - Update color palette to Litecoin brand colors (#0066CC blue, #A6B0C3 silver) - Update typography: add Inter font, make question text bolder - Unify hover styling across interactive elements with blue shadow effects - Refine "I'm Feeling Lit" button: reduce size, remove hover background change - Add consistent blue shadow (shadow-primary/10) to all hover states - Update question card hover to match input box focus styling
- feat: reduce query length limit from 1000 to 400 characters
- config: reduce chat history pairs from 3 to 2
- style: improve ESLint configuration and fix unused parameter
- fix: improve Payload CMS Dockerfile public folder handling
- feat: add production shutdown script
- fix: update MAX_QUERY_LENGTH in page.tsx to match validation limit
- feat: implement webhook authentication with HMAC signature verification
- test: add webhook authentication test suite
- docs: add webhook authentication documentation
- docs: update Red Team Assessment Report - CRIT-1 resolved
- Security: Remove unused Sources API endpoints (CRIT-2)
- docs: update security assessment - reflect CRIT-3/4 risk acceptance and CRIT-7 partial resolution
- feat: implement sliding window rate limiting and progressive bans
- test: add comprehensive rate limiter test suite
- docs: update security assessment with CRIT-12 resolution
- feat(security): Implement security headers for CRIT-6
- fix(frontend): Add error handling for URL parsing in next.config.ts
- docs: Add security assessment addendum with additional findings
- scripts: Add Docker BuildKit cleanup and fix utility
- security: Remove unauthenticated User Questions API (CRIT-NEW-1)
- Security: Remove debug code and fix sensitive data exposure (CRIT-7, HIGH-NEW-3)

## 2025-11-17 (14 commits)

- refactor: centralize environment variable management
- refactor: rename staging environment to prod-local
- fix(payload-cms): improve webhook error handling and access control
- fix(docker): resolve Next.js permission errors in dev containers
- chore(rag): update LLM model and refine prompt
- Tune RAG pipeline: reduce chat history and retrieval count
- Add network aliases and improve service dependencies
- Add Docker Compose command detection to run-prod-local.sh
- Add production deployment script
- Remove CMS frontend pages
- Improve chat scrolling behavior and UI
- Remove unused .next volumes from docker-compose.dev.yml
- Add development and production management scripts
- feat: Add "I'm Feeling Lit" button and paginated suggested questions

## 2025-11-16 (8 commits)

- feat: add comprehensive input sanitization and security hardening
- security: remove unauthenticated admin endpoints
- refactor: replace hardcoded localhost URLs with environment variables
- fix: prevent MongoDB leaks and add staging verification flow
- feat: add Redis-backed rate limiting and improve rate-limit UX - Add Redis service to dev/prod docker-compose and wire REDIS_URL - Implement Redis-backed rate limiter for chat and streaming endpoints (20/min, 300/hour per IP) - Expose rate limit rejection metric in Prometheus - Surface clear 429 “you’re sending messages too quickly” message in frontend - Add k6 rate-limit-test.js script for exercising rate limits end-to-end
- chore: update Payload CMS to v3.64.0
- fix(payload): resolve admin panel authentication and access control issues
- docs: update red team critique with current security assessment

## 2025-11-15 (8 commits)

- refactor(rag): improve RAG prompt template with structured response format
- Upgrade to Gemini 2.5 Flash Lite model
- Chore: Reorganize and delete documents
- fix: remove recursive splitter and improve chunking strategy
- Chore: Reorganize documents
- Chore: Move tests to test folder
- Chore: add .env.example files
- fix(docker): resolve container restart loops for frontend and payload-cms

## 2025-11-14 (2 commits)

- fix: ensure production builds with NODE_ENV and add verification tools
- feat: update UI design system with new typography and color scheme

## 2025-11-13 (4 commits)

- Add Docker dev environment and fix streaming character loss
- feat(rag): enhance responses with relevant knowledge base information
- Improve streaming message UI with enhanced animations and styling
- refactor: improve RAG prompt to be more factual and structured

## 2025-11-12 (1 commit)

- chore: production compose + Cloudflare tunnel; fix CORS/CSRF and env plumbing

## 2025-11-11 (1 commit)

- feat: add Mongo stack and tighten KB handling

## 2025-11-10 (1 commit)

- chore: simplify navigation header

## 2025-11-09 (2 commits)

- Add durable LLM cost tracking and align backend container deps
- Merge branch 'feature/import-navigation'

## 2025-11-08 (3 commits)

- chore: add monitoring stack
- feat: import navigation layout
- Refine navigation and page styling

## 2025-11-06 (3 commits)

- feat: integrate Payload CMS for suggested questions management
- feat: add configurable chat history context length limiting
- fix: resolve JSON parsing errors in SSE streaming

## 2025-11-05 (7 commits)

- Remove unused files
- refactor: rebuild RAG pipeline with local embeddings and simplified architecture
- feat: enhance frontend UI/UX with improved typography, markdown styling, and autoscroll
- Merge branch 'rebuild-rag-pipeline-local-embeddings' into main
- feat: add comprehensive deployment guide and Docker infrastructure
- Change model from gemini 2.5 flash lite to 2.0 flash lite.
- Add suggested questions

## 2025-11-04 (7 commits)

- refactor(HybridRetriever): privatize instance attributes and fix MongoDB query
- perf: implement comprehensive RAG pipeline optimizations
- perf: optimize retrieval pipeline for sub-second performance
- feat: implement streaming chat responses with real-time UI updates
- feat: enhance chat UI with improved formatting and suggested questions
- feat: fix Payload CMS webhook deletes and enhance UI/UX
- feat: implement hierarchical category system for Payload CMS

## 2025-11-03 (10 commits)

- Move knowledge base folder to docs folder
- feat: Add status badge display to Payload CMS articles admin interface
- feat: Implement CMS content lifecycle management (publish/delete/draft filtering)
- feat: enhance chat UI with markdown support and loading states
- feat: enhance chat UI with markdown support, loading states, and auto-scroll
- feat: implement conversational memory and history-aware retrieval
- docs: update README with conversational memory and Payload CMS completion
- feat: implement advanced retrieval pipeline for RAG system
- refactor: simplify RAG prompt by removing conversational instruction
- feat: implement async RAG pipeline for concurrent user scaling

## 2025-11-02 (1 commit)

- Implement hybrid FAISS+MongoDB vector store for local development

## 2025-10-29 (1 commit)

- Add Conversation Memory & Context as a phase 2 feature

## 2025-06-24 (1 commit)

- docs(architecture): Synchronize architectural docs with Payload CMS integration

## 2025-06-23 (2 commits)

- feat: Relocate Payload CMS to project root
- Remove unused payload files from backend

## 2025-06-21 (5 commits)

- Research: Guided Conversation Proposal
- Docs: Update in preparation for M5, M6, and M7.
- feat(cms): Integrate Payload CMS and initial content sync
- docs(milestones): Refactor and align milestone documents with project roadmap
- docs: link to milestone documents in README

## 2025-06-20 (3 commits)

- Docs: Revise document language
- Diagrams: Create feature integration and system diagrams
- Docs: Show Phase 1 Architecture diagram

## 2025-06-19 (3 commits)

- PLAN: Reviewed Payload CMS diagrams and proposed migration plan.
- DOCS: Updated documentation for Payload CMS migration
- Docs: Fix Architecture diagram

## 2025-06-18 (6 commits)

- Docs: Fix status icon fir milestone 6
- feat(strapi): Implement hierarchical chunking for rich text content
- fix(strapi): Ensure webhook data integrity using stable documentId
- docs: Add E2E test and move completed tasks to cline_docs/archive
- Fix link to task_archrive
- feat(strapi): Enhance rich text parser to support links

## 2025-06-17 (11 commits)

- feat(cms): Pivot from Ghost to Strapi for content management
- docs: Update README and milestone for Strapi pivot
- docs: Revise system architecture diagram syntax
- Remove reference docs and code folder as they are outdated/no longer needed
- feat(cms): Initialize Strapi application and update docs
- feat(cms):  Add Strapi setup instructions
- docs(strapi): Sync documentation with Strapi CMS file structure
- feat(strapi): Implement content API integration
- docs: Sync README with Strapi integration progress
- feat(strapi-sync): implement webhook for real-time content synchronization
- docs(project-status): align documentation with strapi sync testing phase

## 2025-06-13 (2 commits)

- feat!: migrate from custom CMS to Ghost CMS integration strategy
- refactor: Rename project to Litecoin-Knowledge-Hub

## 2025-06-12 (1 commit)

- Save current progress for custom CMS. Decided to use FOSS Ghost CMS system.

## 2025-06-10 (6 commits)

- Docs: Update project overview
- docs: Update README with current project status and details
- Docs: Update progress icon to yellow square
- Docs: Fix Mermaid diagram by enclosing the text content of node D in double quotes
- Docs: Fix Mermaid diagram attempt 2
- Docs: Revise Architecture mermaid graph

## 2025-06-09 (12 commits)

- Fix: Resolve metadata filtering test failure in backend/test_rag_pipeline.py Update: documents
- feat: Implement conversational memory in RAG chat
- feat(docs): Plan future UX and retrieval enhancements
- Modify(docs): Organize tasks
- docs: Complete CMS editor planning (CMS-PLAN-001) and update current tasks
- docs: Update CMS editor planning
- Docs: Update CMS Requirements with CMS Research findings.
- docs: Integrate CMS requirements into project documentation
- Docs: Remove comments for file structure
- feat(cms): Initial scaffold of core CMS components
- feat(cms): Implement Phase 1 - Core Setup & Basic Content Management
- docs: Update documentation for CMS-IMP-001 completion

## 2025-06-07 (15 commits)

- Docs(kb): Improve template and added more sections to the golden knowledge base index
- Here's a suggested commit message for the changes made:
- Docs(proj): Organize articles into folder
- docs: Update paths for knowledge_base/articles move
- docs: Add knowledge base contribution guidelines to README. Move active M4-FAQ-001 from active to completed task.
- feat(backend): implement CRUD API for data source management
- feat(rag): Full knowledge base ingestion and validation
- feat(rag): Enhance vector index for advanced metadata filtering
- docs(project): Update milestone docs to reflect backend completion
- docs(project): Synchronize all docs with M4 backend completion
- docs(readme): Consolidate contribution guide
- Estimate hours
- feat: Implement frontend chat UI and integrate with backend API
- docs: Update documentation to include AI-Integrated Knowledge Base CMS
- Docs: Deep search articles

## 2025-06-06 (31 commits)

- Docs(project): Change phrasing
- Docs(project): Refactor README milestones for conciseness and DRY principle
- Updated `cline_docs/milestones/milestone_3_core_rag_pipeline.md` to provide a more granular and accurate representation of the Core RAG Pipeline Implementation progress.
- Updated `cline_docs/milestones/milestone_3_core_rag_pipeline.md` to provide a more granular and accurate representation of the Core RAG Pipeline Implementation progress.
- feat: Add Google AI setup instructions for API key
- Modify: sample document using Grok Deep Search "What is litecoin" response.
- feat: Add reference doc folder to manage documents, examples, reference code, etc.
- Docs(project): Organize prompts
- feat(ingestion): Refactor and test data ingestion pipeline
- Docs(milestone 3): Update estimated time spent
- fix(ingestion): repair and validate multi-source data loaders
- fix(rag): Correct collection name for document retrieval
- Docs(currentTask): Move completed tasks to completed section
- feat(backend): Implement and enhance core RAG pipeline
- Docs(project): Update project status and milestones post-RAG pipeline completion
- Docs(fix): formatting for milestone 3
- Docs(project): Populate task backlog for Milestone 4 (FAQ Feature)
- Modify: improve rag prompt template
- feat(docs): Plan and document data source management API
- Docs(modify): move M4-DATASRC-001 to active task
- Docs(modify): move M4-FAQ-001 to backlog task
- feat(docs): Detail plan for Data Source Management API
- Docs(project): Archive completed tasks and update summaries
- feat: Establish content-first strategy and knowledge base foundation
- feat(kb): Define initial 50-article knowledge base structure
- feat(rag): Implement advanced RAG pipeline optimizations
- feat(rag): Enhance pipeline with metadata filtering and validation
- fix(data_ingestion): Ensure correct Markdown front matter parsing
- feat: Add utility script to clear litecoin_docs collection
- docs(rag): Improve knowledge base and update current task
- Docs(rag): Add research on advanced technologies and update hours in milestone 4

## 2025-06-05 (20 commits)

- Save documents
- Add frontend
- Save current task
- chore: Removing existing scaffold to reset project state
- feat: Add clean scaffold for frontend and backend applications
- Update: CurrentTask and codebaseSummary
- Change: prompt from txt to markdown
- docs: Refine AI prompt for Litecoin RAG Chat specialization
- feat(backend): Implement basic Langchain setup and chat endpoint
- Doc: Add log of completed major milestone
- feat: Define RAG-001: Data Ingestion and MongoDB Vector Store Setup
- Docs: Add Milestone 3 to Log of Complete Major Milestones/Phases
- docs: Define project milestones and update time estimates
- docs: Update README.md with project status and milestones
- feat(rag): build initial data ingestion pipeline__
- Docs: Update milestone 3
- feat: Enhance RAG pipeline setup and documentation
- feat(ingestion): Implement multi-source data ingestion framework
- docs(project): Synchronize documentation with ingestion framework
- docs(project): Update time spent estimate
