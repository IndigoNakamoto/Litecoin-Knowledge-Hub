## Purpose

The backend now supports rebuilding the FAISS index **from MongoDB-stored embeddings** (instead of recomputing embeddings from raw text). This prevents the expensive “re-embed everything” behavior when a Payload CMS article is unpublished (e.g., `published -> draft`) and the system rebuilds FAISS after deleting that article’s chunks.

Older MongoDB chunk documents may not have an `embedding` field yet. This document explains how to backfill them.

## What changed (high level)

- New chunk inserts now store:
  - `text`
  - `metadata`
  - `embedding` (dense vector)
- FAISS rebuilds now prefer stored embeddings and only embed missing ones in a controlled way.

## One-time backfill

### 1) Dry run (recommended)

From the repo root:

- Run:
  - `python backend/utils/backfill_embeddings.py --dry-run`

This prints how many MongoDB docs are missing embeddings.

### 2) Backfill (writes to MongoDB)

From the repo root:

- Run:
  - `python backend/utils/backfill_embeddings.py --force`

Optional knobs:
- `--batch-size 10` (default reads `EMBEDDING_BACKFILL_BATCH_SIZE`, else 10)
- `--limit 1000` (backfill only N docs, useful for testing)
- `--filter-payload-id <id>` (backfill only a single article’s chunks)

### Infinity embeddings mode

If you use the Infinity service for embeddings, ensure these env vars are set:
- `USE_INFINITY_EMBEDDINGS=true`
- `INFINITY_URL` (e.g., `http://infinity:7997` in Docker, or `http://localhost:7997` on host)
- `EMBEDDING_MODEL_ID` (default: `BAAI/bge-m3`)

Then run:
- `USE_INFINITY_EMBEDDINGS=true python backend/utils/backfill_embeddings.py --force`

## Rebuild behavior when embeddings are missing

FAISS rebuilds support a guarded backfill path controlled by:
- `ALLOW_EMBEDDING_BACKFILL_ON_REBUILD`

If `ALLOW_EMBEDDING_BACKFILL_ON_REBUILD=true`, rebuilds will write missing embeddings back into MongoDB while rebuilding.

If `ALLOW_EMBEDDING_BACKFILL_ON_REBUILD=false` (default), rebuilds may still embed missing docs for that one rebuild, but will **not** persist them (so operators can choose to run backfill explicitly).

## How to verify it worked

After backfill:
- Unpublish an article (or trigger the unpublish webhook)
- Confirm logs show FAISS rebuild happening **without** the old “Embedding batch X/Y from MongoDB...” spam (you may still see “Embedding backfill batch ...” only if some docs were missing embeddings).


