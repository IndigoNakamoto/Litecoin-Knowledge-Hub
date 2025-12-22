#!/usr/bin/env python3
"""
Backfill embeddings for existing MongoDB chunks.

Why:
  VectorStoreManager can now rebuild FAISS from MongoDB-stored embeddings (no re-embed),
  but older docs may lack the `embedding` field. This script computes and stores them.

Usage (examples):
  - Dry run (recommended first):
      python backend/utils/backfill_embeddings.py --dry-run

  - Backfill with Infinity (common in this repo), batch size 10:
      USE_INFINITY_EMBEDDINGS=true python backend/utils/backfill_embeddings.py --force --batch-size 10

  - Limit work (useful for testing):
      python backend/utils/backfill_embeddings.py --force --limit 100
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, UpdateOne


logger = logging.getLogger(__name__)


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


def _get_mongo_collection(client: MongoClient):
    db_name = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
    collection_name = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
    return client[db_name][collection_name]


def _embed_with_infinity(texts: List[str]) -> List[List[float]]:
    import httpx

    infinity_url = os.getenv("INFINITY_URL", "http://localhost:7997")
    model_id = os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-m3")

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{infinity_url}/embeddings",
            json={
                "input": texts,
                "model": model_id,
                "encoding_format": "float",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        if len(embeddings) != len(texts):
            raise ValueError(f"Infinity embedding count mismatch: got {len(embeddings)}, expected {len(texts)}")
        return embeddings


def _embed_with_legacy_model(texts: List[str]) -> Tuple[List[List[float]], str]:
    # Import here to avoid heavy imports when using Infinity mode.
    from backend.data_ingestion.vector_store_manager import DEFAULT_EMBEDDING_MODEL, get_embedding_model

    embeddings_model = get_embedding_model()
    vectors = embeddings_model.embed_documents(texts)
    return vectors, DEFAULT_EMBEDDING_MODEL


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing embeddings in MongoDB chunk documents")
    parser.add_argument("--dry-run", action="store_true", help="Report how many docs would be updated (no writes)")
    parser.add_argument("--force", action="store_true", help="Actually write embeddings to MongoDB")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("EMBEDDING_BACKFILL_BATCH_SIZE", "10")))
    parser.add_argument("--limit", type=int, default=0, help="Max docs to process (0 = no limit)")
    parser.add_argument(
        "--filter-payload-id",
        type=str,
        default="",
        help="Only backfill docs for a specific payload_id (matches metadata.payload_id)",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.force:
        print("ERROR: Specify --dry-run or --force")
        return 2

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("ERROR: MONGO_URI is not set")
        return 2

    use_infinity = _bool_env("USE_INFINITY_EMBEDDINGS", "false")
    model_id = os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-m3") if use_infinity else os.getenv("EMBEDDING_MODEL", "")

    logger.info("Backfill starting (use_infinity=%s, batch_size=%s, limit=%s)", use_infinity, args.batch_size, args.limit)
    if args.filter_payload_id:
        logger.info("Filtering by metadata.payload_id=%s", args.filter_payload_id)

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    collection = _get_mongo_collection(client)

    base_filter: Dict[str, Any] = {"$or": [{"embedding": {"$exists": False}}, {"embedding": []}, {"embedding": None}]}
    if args.filter_payload_id:
        base_filter["metadata.payload_id"] = args.filter_payload_id

    total_missing = collection.count_documents(base_filter)
    print(f"MongoDB docs missing embeddings: {total_missing}")
    if args.dry_run:
        print("Dry-run mode: no updates will be written.")
        return 0

    # Stream docs in _id order for stable pagination.
    processed = 0
    updated = 0
    last_id: Optional[Any] = None

    while True:
        page_filter = dict(base_filter)
        if last_id is not None:
            page_filter["_id"] = {"$gt": last_id}

        cursor = collection.find(page_filter, projection={"text": 1, "metadata": 1}).sort("_id", 1)
        if args.limit and processed >= args.limit:
            break

        batch_docs = []
        for doc in cursor.limit(args.batch_size):
            batch_docs.append(doc)
        if not batch_docs:
            break

        # Respect --limit across batches.
        if args.limit:
            remaining = max(args.limit - processed, 0)
            batch_docs = batch_docs[:remaining]

        texts = [(d.get("text") or "") for d in batch_docs]
        metadatas = [dict(d.get("metadata") or {}) for d in batch_docs]

        # Filter out empty texts to avoid embedding errors.
        embed_inputs: List[Tuple[int, str]] = [(i, t) for i, t in enumerate(texts) if t]
        if not embed_inputs:
            last_id = batch_docs[-1]["_id"]
            processed += len(batch_docs)
            continue

        idxs, embed_texts = zip(*embed_inputs)
        idxs = list(idxs)
        embed_texts = list(embed_texts)

        if use_infinity:
            vectors = _embed_with_infinity(embed_texts)
            embedding_model = model_id
        else:
            vectors, embedding_model = _embed_with_legacy_model(embed_texts)

        embedding_dim = len(vectors[0]) if vectors else 0

        updates: List[UpdateOne] = []
        for local_i, vec in zip(idxs, vectors):
            md = metadatas[local_i]
            md.setdefault("embedding_model", embedding_model)
            if embedding_dim:
                md.setdefault("embedding_dim", embedding_dim)

            updates.append(
                UpdateOne(
                    {"_id": batch_docs[local_i]["_id"]},
                    {"$set": {"embedding": vec, "metadata": md}},
                )
            )

        if updates:
            result = collection.bulk_write(updates, ordered=False)
            updated += result.modified_count

        processed += len(batch_docs)
        last_id = batch_docs[-1]["_id"]

        logger.info("Progress: processed=%s updated=%s remaining_estimate=%s", processed, updated, max(total_missing - updated, 0))

        if args.limit and processed >= args.limit:
            break

    print(f"Done. Processed={processed}, Updated={updated}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add project root so `backend.*` imports work when running as a script.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    raise SystemExit(main())


