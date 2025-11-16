#!/usr/bin/env python3
"""
Cleanup utility to remove orphaned embeddings from FAISS for articles that were deleted from Payload CMS
but whose embeddings weren't removed due to the webhook validation bug.
"""

import requests
import logging
from datetime import datetime
from data_ingestion.vector_store_manager import VectorStoreManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_payload_articles(payload_url="http://localhost:3000"):
    """
    Fetch all articles from Payload CMS to get the current list of valid article IDs.
    """
    try:
        # Query Payload CMS for all articles (including drafts and published)
        response = requests.get(
            f"{payload_url}/api/articles?limit=1000&depth=0",  # Adjust limit as needed
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            docs = data.get('docs', [])
            valid_ids = {doc['id'] for doc in docs}
            logger.info(f"Found {len(valid_ids)} articles currently in Payload CMS")
            return valid_ids
        else:
            logger.error(f"Failed to fetch articles from Payload CMS: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error fetching articles from Payload CMS: {e}")
        return None

def find_orphaned_embeddings(payload_ids_in_cms, vector_store_manager):
    """
    Find embeddings in FAISS that belong to articles no longer in Payload CMS.
    """
    orphaned_payload_ids = []

    try:
        # Get all documents with payload_id metadata from MongoDB
        pipeline = [
            {"$match": {"metadata.payload_id": {"$exists": True}}},
            {"$group": {"_id": "$metadata.payload_id", "count": {"$sum": 1}}}
        ]

        results = list(vector_store_manager.collection.aggregate(pipeline))

        logger.info(f"Found {len(results)} unique payload_ids in vector store")

        for result in results:
            payload_id = result['_id']
            chunk_count = result['count']

            if payload_id not in payload_ids_in_cms:
                orphaned_payload_ids.append((payload_id, chunk_count))
                logger.info(f"Orphaned: {payload_id} ({chunk_count} chunks)")

        return orphaned_payload_ids

    except Exception as e:
        logger.error(f"Error querying vector store: {e}")
        return []

def cleanup_orphaned_embeddings(orphaned_payload_ids, vector_store_manager, dry_run=True):
    """
    Remove orphaned embeddings from FAISS.
    """
    total_deleted = 0

    for payload_id, chunk_count in orphaned_payload_ids:
        try:
            if not dry_run:
                logger.info(f"Deleting embeddings for orphaned article: {payload_id}")
                deleted_count = vector_store_manager.delete_documents_by_metadata_field('payload_id', payload_id)
                logger.info(f"Deleted {deleted_count} chunks for {payload_id}")
                total_deleted += deleted_count
            else:
                logger.info(f"DRY RUN: Would delete {chunk_count} chunks for {payload_id}")
                total_deleted += chunk_count

        except Exception as e:
            logger.error(f"Error deleting embeddings for {payload_id}: {e}")

    return total_deleted

def refresh_rag_pipeline():
    """
    Refresh the RAG pipeline after cleanup.
    """
    try:
        logger.info("Refreshing RAG pipeline...")
        response = requests.post("http://localhost:8000/api/v1/refresh-rag", timeout=30)
        if response.status_code == 200:
            logger.info("✅ RAG pipeline refreshed successfully")
            return True
        else:
            logger.warning(f"⚠️ RAG pipeline refresh returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to refresh RAG pipeline: {e}")
        return False

def main():
    """
    Main cleanup function.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Clean up orphaned embeddings from deleted Payload CMS articles")
    parser.add_argument("--payload-url", default="http://localhost:3000", help="Payload CMS URL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true", help="Actually perform the deletion (required if not dry-run)")

    args = parser.parse_args()

    if not args.dry_run and not args.force:
        print("❌ ERROR: Must specify --force to actually perform deletion, or --dry-run to preview")
        return False

    print("🧹 Starting orphaned embeddings cleanup")
    print("=" * 50)

    # Initialize vector store manager
    try:
        vector_store_manager = VectorStoreManager()
        logger.info("Vector store manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store manager: {e}")
        return False

    # Get current articles from Payload CMS
    print(f"📡 Fetching current articles from Payload CMS: {args.payload_url}")
    payload_ids_in_cms = get_payload_articles(args.payload_url)

    if payload_ids_in_cms is None:
        print("❌ Failed to fetch articles from Payload CMS. Aborting.")
        return False

    # Find orphaned embeddings
    print("🔍 Finding orphaned embeddings...")
    orphaned_embeddings = find_orphaned_embeddings(payload_ids_in_cms, vector_store_manager)

    if not orphaned_embeddings:
        print("✅ No orphaned embeddings found!")
        return True

    print(f"📊 Found {len(orphaned_embeddings)} orphaned articles with embeddings:")
    total_chunks = sum(count for _, count in orphaned_embeddings)
    print(f"   Total orphaned chunks: {total_chunks}")

    # Perform cleanup
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - Previewing cleanup:")
        deleted_count = cleanup_orphaned_embeddings(orphaned_embeddings, vector_store_manager, dry_run=True)
        print(f"\nWould delete {deleted_count} total chunks")
    else:
        print(f"\n🗑️ Performing cleanup...")
        deleted_count = cleanup_orphaned_embeddings(orphaned_embeddings, vector_store_manager, dry_run=False)
        print(f"\nDeleted {deleted_count} total chunks")

        # Refresh RAG pipeline
        print("\n🔄 Refreshing RAG pipeline...")
        refresh_rag_pipeline()

    print("\n" + "=" * 50)
    if args.dry_run:
        print("✅ DRY RUN COMPLETED - No changes made")
        print("Run with --force to actually perform the cleanup")
    else:
        print("✅ CLEANUP COMPLETED")
        print(f"Removed embeddings for {len(orphaned_embeddings)} deleted articles")

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
