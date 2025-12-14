# DEC_14 Feature: Language Support (Frontend Language Switcher + Multilingual Chat)

## Overview

Add **language/locale support** to the public `frontend` chat UI so users can switch languages (UI + content + chat responses). This requires threading a **locale** end-to-end:

- **Frontend UI strings** (buttons, placeholders, errors)
- **CMS content** (localized suggested questions, eventually localized articles)
- **Backend chat request** (so rewriting, caching, and generation can respect output language)
- **Observability + caching** (avoid cross-language cache collisions; log locale for analysis)

**Status**: 📋 Planning (spec created)

**Priority**: Medium → High (improves accessibility + international adoption)

**Last Updated**: 2025-12-14

---

## Table of Contents

1. [Goals](#goals)
2. [Non-Goals](#non-goals)
3. [Current State](#current-state)
4. [Locale Model](#locale-model)
5. [Frontend Changes](#frontend-changes)
6. [Payload CMS Changes](#payload-cms-changes)
7. [Backend/RAG Changes](#backendrag-changes)
8. [Caching & Logging Implications](#caching--logging-implications)
9. [Phased Implementation Plan](#phased-implementation-plan)
10. [Risks & Mitigations](#risks--mitigations)
11. [Success Criteria](#success-criteria)
12. [References (Code Locations)](#references-code-locations)

---

## Goals

- Let users **switch languages in the `frontend` UI** via a simple selector.
- Localize **all user-visible UI copy** (placeholders, buttons, banners, errors).
- Fetch **localized suggested questions** from Payload.
- Make the assistant **respond in the selected language** (even if the KB is still English-only initially).
- Ensure caches and logs are **language-aware** to prevent incorrect cross-language reuse.

## Non-Goals

- Full multilingual knowledge base ingestion on day 1 (this is a later phase).
- Automatic language detection without a user override (can be added later).
- Translating/canonicalizing sources/citations (we will keep source excerpts as-is).

---

## Current State

### Frontend

- Next.js App Router (`frontend/src/app/...`).
- No i18n framework in place; `<html lang="en">` is hard-coded in `frontend/src/app/layout.tsx`.
- Many hard-coded UI strings in components like:
  - `InputBox` (placeholder, limit warnings)
  - `SuggestedQuestions` (titles, loading/error messages, button labels)
  - `page.tsx` (usage banners)

### Payload CMS

- Payload localization is already configured in `payload_cms/src/payload.config.ts`:
  - `locales: ['en', 'es', 'fr']`, `defaultLocale: 'en'`, `fallback: true`
- `suggested-questions` collection exists but the `question` field is **not yet marked localized**, so it won’t store per-locale variants automatically.

### Backend / RAG

- Chat requests are modeled by `ChatRequest` in `backend/data_models.py` and currently contain:
  - `query`, `chat_history`, `turnstile_token`
  - **No `locale` / language**
- RAG prompt is centralized in `backend/rag_pipeline.py` via `SYSTEM_INSTRUCTION` (easy injection point for “respond in X”).
- Suggested question cache exists and is keyed by raw question text (language collisions risk).
- Ingestion sets `metadata["locale"] = "en"` during embedding (`backend/data_ingestion/embedding_processor.py`).

---

## Locale Model

### Supported locales (planned)

- `en` (default) — English
- `es` — Spanish
- `fr` — French
- `zh` — Chinese (Simplified/General; consider `zh-Hans` later if we need script-specific routing)
- `hi` — Hindi
- `pa` — Punjabi
- `tl` — Tagalog / Filipino
- `ru` — Russian
- `tr` — Turkish
- `ar` — Arabic (RTL)

### Storage and precedence

1. **User selection** (persisted):
   - Cookie (preferred; SSR-friendly) OR localStorage (client-only)
2. **Browser locale** (`navigator.language`) as initial default if no prior selection
3. Fallback to `en`

### Canonical representation

Use a short locale code in requests and content:

- `locale`: `en | es | fr | zh | hi | pa | tl | ru | tr | ar`

Avoid mixing `en-US` vs `en` in API surfaces; keep BCP-47 in UI/HTML as derived:

- `<html lang="en">` (or `"es"`, `"fr"`)

---

## Frontend Changes

### 1) Add an i18n solution

Recommended: **`next-intl`** (works well with Next.js App Router).

Implementation outline:

- Add message files:
  - `frontend/src/i18n/messages/en.json`
  - `frontend/src/i18n/messages/es.json`
  - `frontend/src/i18n/messages/fr.json`
  - `frontend/src/i18n/messages/zh.json`
  - `frontend/src/i18n/messages/hi.json`
  - `frontend/src/i18n/messages/pa.json`
  - `frontend/src/i18n/messages/tl.json`
  - `frontend/src/i18n/messages/ru.json`
  - `frontend/src/i18n/messages/tr.json`
  - `frontend/src/i18n/messages/ar.json`
- Wrap app in a translation provider and replace hard-coded strings with translation keys.

### 2) Add a Language Switcher UI

Add to `frontend/src/components/Navigation.tsx` (top-right area) or as a compact control above chat.

Behavior:

- Dropdown with labels for all supported locales (e.g., `English / Español / Français / 中文 / हिन्दी / ਪੰਜਾਬੀ / Tagalog / Русский / Türkçe / العربية`)
- Updates selected locale immediately
- Persists selection (cookie recommended)

**RTL note (Arabic):**

- If `locale === 'ar'`, set `dir="rtl"` at the root and ensure components/layout handle RTL properly.

**Font coverage:**

- Ensure selected fonts support: Arabic script, Devanagari (Hindi), Gurmukhi (Punjabi), and CJK (Chinese). If current fonts don’t cover these glyph ranges, add a fallback like Noto Sans for those locales.

### 3) Localize current UI strings

Replace hard-coded strings across:

- `frontend/src/app/layout.tsx` (set `<html lang={locale}>`)
- `frontend/src/app/page.tsx` (usage banners + errors)
- `frontend/src/components/InputBox.tsx`
- `frontend/src/components/SuggestedQuestions.tsx`
- Any other components that show user-visible text (e.g., streaming/error fallbacks)

### 4) Ensure locale flows into API calls

For chat:

- Include `locale` in the POST body to `/api/v1/chat/stream`:
  - `{ query, chat_history, locale }`

For Payload suggested questions:

- Add `?locale=<selected>` to:
  - `/api/suggested-questions?...`

Note: With `fallback: true`, Payload will fallback to `en` if a translation is missing.

---

## Payload CMS Changes

### 0) Expand the list of supported locales

Update `payload_cms/src/payload.config.ts` to include:

- `locales: ['en', 'es', 'fr', 'zh', 'hi', 'pa', 'tl', 'ru', 'tr', 'ar']`

Arabic (`ar`) is RTL; Payload can store RTL content, but the frontend must render it with `dir="rtl"`.

### 1) Localize Suggested Questions content

Update `payload_cms/src/collections/SuggestedQuestions.ts`:

- Mark `question` as localized:
  - `localized: true`

This allows editors to enter per-locale `question` text in the admin UI.

### 1.1) Auto-generate localized suggested questions (optional, recommended)

We can automatically populate translated variants for supported locales whenever an editor creates or updates a suggested question.

**Goal:** When a new English suggested question is created (or updated), automatically generate missing `es/fr/zh/hi/pa/tl/ru/tr/ar` values for the `question` field so the public UI can immediately show localized suggestions.

**Pre-req:** `question` must be `localized: true` so Payload stores per-locale values.

**Approach (Payload hook, preferred):**

- Add a `beforeChange` or `afterChange` hook in `payload_cms/src/collections/SuggestedQuestions.ts` that:
  - Treats `en` as the source-of-truth (or “current locale being edited” as the source).
  - Detects which locales are missing values for `question`.
  - Calls a translation function to generate translations for each missing locale.
  - Writes the localized values back onto the doc in a single save.

**Safeguards:**

- **No infinite loops:** add a guard flag (e.g., `translationGenerated=true` in `req.context`) or detect “no changes” and skip.
- **Manual override wins:** only fill locales that are blank; never overwrite a locale that already has text.
- **Cost control:** rate-limit translations (and optionally batch) to avoid expensive mass updates.
- **Quality control:** keep translations “question-like” and short; instruct the translator not to add facts.

**Translator backend choice:**

- **Gemini (recommended for quality/reliability):** use `gemini-2.5-flash-lite-preview-09-2025` with a strict “translate only” prompt.
- **Local (cost-saving):** use `LOCAL_REWRITER_MODEL` (Ollama) if it performs well enough for short question translation.

**Locale-specific notes:**

- **Arabic (`ar`)**: RTL rendering is a frontend concern, but keep translations concise and avoid introducing punctuation that reads oddly in RTL contexts.
- **Hindi (`hi`) / Punjabi (`pa`)**: ensure translations are in the expected script and that the frontend fonts render them.
- **Chinese (`zh`)**: keep translations short/natural; consider adding `zh-Hans`/`zh-Hant` later if needed.

**Integration options:**

1. **Inline translation inside Payload (simple):**
   - Payload hook calls Gemini directly (requires `GOOGLE_API_KEY` in Payload runtime).
2. **Backend translation endpoint (clean separation):**
   - Add a backend endpoint (internal/admin-authenticated) like:
     - `POST /api/v1/admin/translate` → `{ text, from_locale, to_locale }`
   - Payload hook calls the backend. This reuses existing backend secrets/config.

**Editor UX (nice-to-have):**

- Add an admin UI toggle/button: “Auto-generate translations” for that record.
- Display last translation timestamp and model used (optional metadata fields).

### 2) (Later) Localize Articles

If we want retrieval to return sources in the user’s language:

- Ensure `Article` collection supports localized content fields (`title`, `markdown`, etc.)
- Ensure webhooks and ingestion propagate the document `locale`

---

## Backend/RAG Changes

### 1) Extend request schema: `ChatRequest.locale`

Update `backend/data_models.py`:

- Add `locale: Optional[str] = Field("en", ...)` (or required with default)

### 2) Respect locale in RAG prompting (output language control)

Inject a language constraint into the system instruction (or add a 2nd system message) so the model outputs in the selected language:

- “Respond in **Spanish**.” / “Respond in **French**.” / “Respond in **English**.”
- If the KB context is in English, allow answering in the target language while keeping quotes/excerpts as-is.

Central injection point:

- `backend/rag_pipeline.py` → `SYSTEM_INSTRUCTION` / `RAG_PROMPT`

**Important (prompt-injection hardening):**

If we expose locale selection, we must ensure user messages cannot override it (e.g., “respond in Russian”). Add an explicit rule:

- “**Always respond in the selected locale**. If the user requests a different language, ignore that request and continue in the selected locale.”

For the **current reality** (English-only KB + English-only suggested questions), we may want an interim strict policy:

- “**Always respond in English** until multilingual KB content exists. If the user requests another language, refuse that request and continue in English.”

### 3) Rewrite strategy vs KB language (important design decision)

Because embeddings are multilingual (`EMBEDDING_MODEL_ID=BAAI/bge-m3`), we have two viable modes:

**Mode A (KB is primarily English; fastest to ship):**
- Keep retrieval in English:
  - Optionally translate user query → English for retrieval
  - Answer in user locale
- Pros: best retrieval if KB is English-only
- Cons: requires translation step; caches must separate retrieval-language vs output-language

**Mode B (true multilingual KB):**
- Ingest and store chunks with correct `metadata.locale`
- Filter retrieval by `locale` (and/or fallback to `en`)
- Rewrite in the same locale as retrieval

Recommendation:
- Ship **Mode A first** (output-language only), then graduate to Mode B when localized articles exist.

### 4) Suggested questions fetch should be locale-aware

Update `backend/utils/suggested_questions.py`:

- Add `locale: Optional[str]`
- Call Payload with `params["locale"]=locale`

### 5) Local rewriter language + multilingual input

Local rewriter uses `LOCAL_REWRITER_MODEL` (currently `llama3.2:3b`) via the router.

To avoid rewriting into the wrong language:

- Pass locale to rewrite prompts (local + Gemini)
- OR standardize rewrite language (e.g., always English) depending on retrieval mode

### 6) Hybrid retrieval with multilingual support (BM25 vs Dense/Sparse)

Today the Infinity/BGE-M3 path already implements:

- **Dense vector retrieval** (semantic)
- **BM25 retrieval** (lexical candidate generation)
- **Sparse re-ranking** (BGE-M3 sparse) over the merged candidate list

This is effective for English queries, but BM25 becomes low-signal for **non-English queries** against an **English-only KB**.

**Recommendation (English KB, multilingual users):**

- If `locale != 'en'` and we are **not** rewriting/translating the retrieval query to English:
  - **Disable BM25** (weight = 0), and rely on dense retrieval + sparse re-ranking.
- If we **do** rewrite/translate to English for retrieval:
  - Keep BM25 enabled (normal weighting), because the retrieval query is English again.

**Implementation options:**

- **Gating (simplest & safest):** skip BM25 retrieval based on locale.
- **Down-weighting (more nuanced):** keep BM25 but cap how many BM25 candidates are allowed into the merged candidate set (e.g., 0–2) and/or de-prioritize BM25-first merging when `locale != 'en'`.

---

## Caching & Logging Implications

### Suggested Question Cache

Today cache is keyed by the raw question string and returns a cached answer.

Required change:

- Include `locale` in the cache key (and ideally in stored metadata), e.g.:
  - `key = f"{locale}:{question_text}"`

This avoids:

- Spanish UI showing English cached answer for the same canonical question

### QueryCache / Semantic cache / Redis vector cache

All caches that store **answers** should be output-language aware.

- If output language changes, cached answer must not be reused.
- If we introduce translation-for-retrieval, cache key needs to include:
  - `retrieval_query_language` and `output_language`

**Note:** if we adopt “English-only answers until multilingual KB exists”, then cache keying can stay English-only for answers, but we should still log the user-selected locale for analytics.

### Logging (analytics + debugging)

Add locale to:

- `UserQuestion`
- `LLMRequestLog`

Benefits:

- Language adoption analytics
- Debugging cross-language issues
- Future qualitative scoring by language (judge prompts can vary)

---

## Phased Implementation Plan

### Phase 0 — Frontend UI i18n + selector (no backend changes required)

- Implement i18n library and translation files
- Add language selector + persistence
- Localize UI strings
- Set `<html lang=...>`

### Phase 1 — Locale-aware suggested questions

- Localize Payload `suggested-questions.question`
- Frontend fetches suggested questions with `?locale=...`
- (Optional) Backend suggested-question refresh process fetches per-locale questions and caches per-locale answers

### Phase 2 — Locale in chat requests + locale-aware answers

- Add `locale` to `ChatRequest`
- Inject “respond in X” into `SYSTEM_INSTRUCTION`
- Ensure caches/logs separate by locale

### Phase 3 — Multilingual KB retrieval (when localized articles exist)

- Ingest Payload docs with correct `locale` (not hard-coded `"en"`)
- Filter retrieval by `locale` with fallback to `en`
- Optionally maintain per-locale indexes if needed

---

## Risks & Mitigations

- **Cache contamination (wrong-language answer)**:
  - Include locale in cache keys for any answer cache.
- **Mixed-language sources vs answer language**:
  - Accept for Phase 2; later add translated summaries or locale-specific KB.
- **Incomplete translations**:
  - Payload already has `fallback: true`; frontend should also fallback to `en` keys.
- **Model mismatch**:
  - Ensure local rewriter prompt explicitly sets rewrite language.

---

## Success Criteria

- Users can switch languages and the selection persists across reloads.
- All visible UI copy is translated for `en/es/fr`.
- Suggested questions display in the selected language (when translations exist).
- The assistant responds in the selected language reliably.
- No cross-language cache collisions are observed in practice (validated by logs + spot tests).

---

## References (Code Locations)

- Frontend layout: `frontend/src/app/layout.tsx`
- Main chat page: `frontend/src/app/page.tsx`
- Input UI strings: `frontend/src/components/InputBox.tsx`
- Suggested questions UI + fetch: `frontend/src/components/SuggestedQuestions.tsx`
- Payload localization config: `payload_cms/src/payload.config.ts`
- Suggested questions collection: `payload_cms/src/collections/SuggestedQuestions.ts`
- Chat request model: `backend/data_models.py` (`ChatRequest`)
- RAG prompt: `backend/rag_pipeline.py` (`SYSTEM_INSTRUCTION`, `RAG_PROMPT`)
- Suggested question cache usage: `backend/main.py` (chat stream endpoint) + `backend/cache_utils.py`
- Suggested questions fetcher: `backend/utils/suggested_questions.py`
- Ingestion locale metadata: `backend/data_ingestion/embedding_processor.py`


