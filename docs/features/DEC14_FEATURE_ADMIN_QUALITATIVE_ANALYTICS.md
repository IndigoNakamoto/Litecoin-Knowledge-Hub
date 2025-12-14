# Feature: Admin Qualitative Analytics (LLM Log Analysis + RAG Debugging)

## Overview

The project already tracks **quantitative** operational metrics (tokens, latency, cost) via Prometheus/Grafana. This feature adds **qualitative** observability by enriching logged interactions with:

- **Quality scoring** (LLM-as-a-judge: faithful vs hallucination vs refusal)
- **Topic clustering** (what users are asking about)
- **Content gap extraction** (what you should add to the knowledge base)
- **Safety/adversarial flags** (abuse, jailbreak attempts, PII)
- **Retrieval relevance debugging** (were the retrieved chunks actually relevant?)

**Status**: 📋 Planning (spec created)

**Priority**: High (directly improves knowledge-base quality and RAG trustworthiness)

**Last Updated**: 2025-12-14

---

## Table of Contents

1. [Current State (What We Log Today)](#current-state-what-we-log-today)
2. [Problem Statement (What’s Missing)](#problem-statement-whats-missing)
3. [Proposed Architecture (Shadow Pipeline)](#proposed-architecture-shadow-pipeline)
4. [Data Model (Raw Logs vs Analysis)](#data-model-raw-logs-vs-analysis)
5. [Admin Dashboard Features](#admin-dashboard-features)
6. [API Surface (Admin)](#api-surface-admin)
7. [Implementation Plan (Phased)](#implementation-plan-phased)
8. [Risks & Mitigations](#risks--mitigations)
9. [Success Criteria](#success-criteria)
10. [References (Code Locations)](#references-code-locations)

---

## Current State (What We Log Today)

### Backend logging

Today we persist two MongoDB collections relevant to “what users asked / what the bot answered”:

1. **`user_questions`**: lightweight per-request question logging for high-level analysis.
2. **`llm_request_logs`**: full request/response log for cost and auditing.

The canonical schema for LLM logs is `LLMRequestLog` in `backend/data_models.py` and includes:

- `request_id` (UUID)
- `timestamp`
- `user_question` (full text in DB)
- `assistant_response` (full text in DB)
- token usage: `input_tokens`, `output_tokens`
- cost: `cost_usd`, `pricing_version`, `model`, `operation`
- perf: `duration_seconds`, `status`, `error_message`
- caching: `cache_hit`, `cache_type`
- retrieval (today): **only** `sources_count` (integer)

**Important limitation**: although the runtime pipeline *does* have access to the retrieved documents (SSE sends `sources` to the user UI), we **do not persist** the retrieved chunk payloads or retrieval scores in `llm_request_logs` today.

### Admin frontend today

Admin already includes a “Question Logs” UI that calls:

- `GET /api/v1/admin/llm-logs/recent?limit=...`

The current endpoint is optimized for dashboard display and returns a truncated view (e.g., `user_question` is truncated to 100 characters for display) and does **not** return `assistant_response` or any retrieval context.

---

## Problem Statement (What’s Missing)

To enable qualitative analysis (judge, clustering, gaps, safety), we need structured access to:

- **Full user question** (already stored in DB; admin endpoint truncates)
- **Full assistant response** (already stored in DB; admin endpoint does not expose)
- **Retrieved context**:
  - which chunks were retrieved
  - chunk identity (payload/article ID, chunk index, section title, etc.)
  - retrieval channel (BM25 vs vector vs sparse re-rank)
  - retrieval score(s) / similarity / rank
  - (optionally) chunk excerpt text

Without persisted retrieval context, an offline evaluator cannot reliably answer:

- “Was the answer faithful to what we retrieved?”
- “Did we retrieve irrelevant junk (wasted tokens)?”
- “Is the system missing docs, or is retrieval failing?”

---

## Proposed Architecture (Shadow Pipeline)

### High-level flow

```
Live User Request
  └─> Fast RAG (current) -> respond to user
      └─> raw log write (MongoDB: llm_request_logs)
          └─> async analyzer (worker)
              └─> write analysis/enrichment (MongoDB: llm_request_analyses)
                  └─> Admin dashboard reads both
```

### Why separate “raw logs” from “analysis”

Keep `llm_request_logs` as the immutable “source of truth” for auditing and cost metrics. Store qualitative enrichments in a **separate collection** so we can:

- re-run analysis as prompts/models change (versioning)
- avoid bloating raw logs
- control retention (e.g., keep raw logs longer, analyses shorter, or vice versa)

---

## Data Model (Raw Logs vs Analysis)

### A) Raw logs (existing) — `llm_request_logs`

Already exists. Recommended additions (minimal, size-safe):

- **`retrieval_context` (optional object)**:
  - `retrieval_query` (string; includes rewritten query if applicable)
  - `retriever_k` (int)
  - `retrieval_mode` (enum: `hybrid`, `history_aware`, `redis_vector_cache`, etc.)
  - `no_kb_results` (bool) — already implied sometimes; should be explicit
  - `sources` (array of objects; see below)

**Recommended `sources[]` shape** (store IDs + tiny excerpts, not full docs by default):

- `rank` (int)
- `source_type` (enum: `vector`, `bm25`, `sparse_rerank`, `cache`)
- `score` (float | null) — depends on retriever
- `payload_id` (string | null)
- `chunk_id` (string | null)
- `chunk_index` (int | null)
- `doc_title` / `section_title` (string | null)
- `content_sha256` (string | null)
- `content_excerpt` (string | null, e.g. first 300–800 chars)

Optional (feature-flagged) for deep debugging:

- `content_full` (string | null) — **off by default**; large

### B) Analysis results (new) — `llm_request_analyses`

**Primary key**: `request_id` (string), plus `analysis_version` (string) and `analyzed_at`.

Suggested fields:

- `quality`:
  - `score_1_5` (int)
  - `label` (enum: `faithful`, `hallucination`, `refusal`, `partial`, `unknown`)
  - `rationale` (string, short)
  - `citations_required` (bool) — whether sources existed but answer didn’t cite (optional)
- `topic`:
  - `cluster_id` (string)
  - `cluster_label` (string)
  - `embedding_model` (string)
- `gaps`:
  - `is_content_gap` (bool)
  - `gap_summary` (string)
  - `suggested_docs_to_add` (array of strings)
- `safety`:
  - `is_toxic` (bool)
  - `is_jailbreak` (bool)
  - `pii_risk` (enum: `none`, `possible`, `likely`)
  - `flag_reasons` (array of strings)
- `retrieval_debug`:
  - `relevance_grade` (enum: `good`, `mixed`, `bad`)
  - `top_source_relevant` (bool | null)
  - `notes` (string, short)

Operational fields:

- `analysis_model` (string)
- `analysis_prompt_version` (string)
- `analysis_cost_usd` (float)
- `analysis_latency_seconds` (float)

---

## Admin Dashboard Features

### 1) LLM-as-a-Judge Quality Score

- **Inputs**: user question + retrieved sources (IDs + excerpt) + bot answer
- **Output**: `faithful/hallucination/refusal`, `score_1_5`
- **Admin widget**:
  - Hallucination rate (last 24h/7d)
  - “lowest-score interactions” review queue

### 2) Semantic Topic Clustering (“Heatmap”)

- **Inputs**: user question (and optional answer)
- **Output**: cluster label/id, trend metrics
- **Admin widget**:
  - topic bubble chart (volume + sentiment)
  - top rising topics

### 3) “Missing Knowledge” Extraction

- **Inputs**: interactions where `no_kb_results=true` OR retrieval is low quality (`retrieval_debug.relevance_grade=bad`)
- **Output**: content gap summary and suggested docs/pages to add
- **Admin widget**:
  - “Content gaps” list with counts and example queries

### 4) Adversarial & Safety Analysis

- **Inputs**: user question + answer (and optional full chat history later)
- **Outputs**: toxicity/jailbreak/PII flags
- **Admin widget**:
  - Threat log queue for manual review
  - filterable by severity

### 5) Retrieval Relevance Debugging

- **Inputs**: question + top N retrieved sources + answer
- **Outputs**: “relevance grade”, “top source relevant?”, notes
- **Admin widget**:
  - “wasted context” detector (high tokens + low relevance)
  - identify chunking problems (too long / irrelevant sections)

---

## API Surface (Admin)

### Existing (today)

- `GET /api/v1/admin/llm-logs/recent?limit=...`
- `GET /api/v1/admin/llm-logs/stats?hours=...` (Grafana-oriented aggregates)

### Proposed additions (for qualitative analytics)

1. **Fetch full log entry (untruncated)**
   - `GET /api/v1/admin/llm-logs/{request_id}`
   - Returns: full `LLMRequestLog` (including `assistant_response`) + (optional) `retrieval_context`

2. **Fetch analysis for a request**
   - `GET /api/v1/admin/llm-analyses/{request_id}`

3. **List interactions with analysis filters**
   - `GET /api/v1/admin/llm-analyses/recent?limit=...&label=hallucination&min_score=...`

4. **Content gap report**
   - `GET /api/v1/admin/reports/content-gaps?days=...`

5. **Threat log**
   - `GET /api/v1/admin/reports/threats?days=...&severity=...`

All endpoints should reuse the existing Bearer-token auth pattern and admin rate limiting.

---

## Implementation Plan (Phased)

### Phase 0 — Confirm and extend raw logging (schema)

- Add `retrieval_context` capture (IDs + scores + short excerpts) at request time.
- Ensure admin endpoint can fetch **full** `user_question` and `assistant_response` for a single interaction.

### Phase 1 — Analyzer worker (MVP)

- Implement a periodic job that:
  - reads “unanalyzed” logs
  - runs judge + topic + safety (start small)
  - writes `llm_request_analyses` with versioning

### Phase 2 — Admin UI widgets

- Add “Qualitative” pages:
  - Hallucination rate + review queue
  - Topic trends
  - Content gaps
  - Threat log
  - Retrieval debugging table

### Phase 3 — Optimization & governance

- Sampling strategies (analyze 1–5% of traffic, focus on long/high-cost queries)
- Retention (TTL indexes) + PII policy
- Offline re-analysis tooling (re-run with new prompts/models)

---

## Risks & Mitigations

- **Storage bloat (retrieved chunk text)**:
  - Store IDs + short excerpts by default; keep full chunk text behind a feature flag and/or TTL.
- **PII retention concerns**:
  - Add redaction step in analyzer; configurable retention policy; consider hashing sensitive fields.
- **Analyzer cost**:
  - Sample, prioritize high-cost/slow queries; batch processing; store analysis cost metrics.
- **Non-deterministic labels**:
  - Version analysis prompts; keep `analysis_version` + `analysis_model` for traceability.

---

## Success Criteria

- **Hallucination rate** can be measured and trends downward after retrieval/prompt improvements.
- **Top topics** and **content gaps** are visible within minutes/hours, not days.
- Admin can click an interaction and see:
  - full question + full answer
  - retrieved chunk IDs/excerpts and scores
  - judge label + rationale
- “Wasted context” cases can be systematically identified (high tokens + low relevance grade).

---

## References (Code Locations)

- Raw log model: `backend/data_models.py` (`LLMRequestLog`)
- Raw log write path: `backend/main.py` (`log_llm_request`, `/api/v1/chat/stream`)
- Admin log endpoints: `backend/api/v1/admin/llm_logs.py`
- Admin frontend API client: `admin-frontend/src/lib/api.ts` (`questionLogsApi`)
- Admin frontend logs UI: `admin-frontend/src/components/QuestionLogs.tsx`
- Retrieval pipeline: `backend/rag_pipeline.py` (`aquery`, `astream_query`, hybrid retrieval, vector score retrieval)


