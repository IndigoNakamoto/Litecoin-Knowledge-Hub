#!/usr/bin/env python3
"""
FAQ Re-indexing Script (Parent Document Pattern)

Re-indexes all documents from MongoDB with synthetic FAQ questions
generated for each chunk. This script implements the Parent Document Pattern
where questions are indexed for search, but parent chunks are returned.

Key Features:
- Generates synthetic questions for each document chunk
- Adds chunk_id to original chunks for parent resolution
- Supports resume capability (skips already processed chunks)
- Dry-run mode for testing
- Supports both Gemini and local Ollama backends
- Graceful shutdown with Ctrl+C (saves progress)

IMPORTANT: This script is designed to run from your Mac terminal (host),
not inside a Docker container.

Usage:
    # From project root - use Gemini (default)
    python scripts/reindex_with_faq.py
    
    # Use local Ollama (no rate limits, faster!)
    python scripts/reindex_with_faq.py --local
    
    # Dry-run mode (no writes)
    python scripts/reindex_with_faq.py --dry-run
    
    # Force re-process all documents (ignore existing chunk_ids)
    python scripts/reindex_with_faq.py --force
    
    # Process specific batch size
    python scripts/reindex_with_faq.py --batch-size 50

Environment Variables:
    FAQ_LLM_BACKEND: "gemini" or "local" (default: gemini)
    FAQ_OLLAMA_URL: Ollama URL (default: http://localhost:11434)
    FAQ_OLLAMA_MODEL: Ollama model (default: llama3.2:3b)
    GOOGLE_API_KEY: Required for Gemini backend

Output:
    - Updates MongoDB with chunk_id and is_synthetic metadata
    - Adds synthetic question documents to MongoDB
    - Rebuilds FAISS index with all documents
"""

import os
import sys
import asyncio
import argparse
import logging
import signal
from pathlib import Path
from typing import List, Set, Optional

# Add project paths for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Load environment variables (try multiple locations)
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env.docker.prod")
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
_shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _shutdown_requested
    if _shutdown_requested:
        logger.warning("\n⚠️  Force quit! Progress may be lost.")
        sys.exit(1)
    _shutdown_requested = True
    logger.info("\n🛑 Shutdown requested. Finishing current batch... (Ctrl+C again to force quit)")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def main(dry_run: bool = False, force: bool = False, batch_size: int = 100, use_local: bool = False):
    """
    Main FAQ re-indexing function.
    
    Args:
        dry_run: If True, don't write anything to MongoDB
        force: If True, reprocess all documents (ignore existing chunk_ids)
        batch_size: Number of chunks to process in each batch
        use_local: If True, use local Ollama instead of Gemini
    """
    global _shutdown_requested
    
    # Determine backend
    backend = "local" if use_local else os.getenv("FAQ_LLM_BACKEND", "gemini")
    
    # Check requirements based on backend
    if backend == "local":
        ollama_url = os.getenv("FAQ_OLLAMA_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        ollama_model = os.getenv("FAQ_OLLAMA_MODEL", os.getenv("LOCAL_REWRITER_MODEL", "llama3.2:3b"))
        logger.info(f"Using LOCAL backend: {ollama_url} with model {ollama_model}")
    else:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_API_KEY environment variable not set!")
            logger.info("Either set GOOGLE_API_KEY or use --local flag for Ollama")
            sys.exit(1)
        logger.info("Using GEMINI backend")
    
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.error("MONGO_URI environment variable not set!")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("FAQ Re-indexing Script (Parent Document Pattern)")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Backend: {backend.upper()}")
    logger.info(f"Force reprocess: {force}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"MongoDB: {mongo_uri[:50]}...")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 70)
    
    # Import dependencies
    try:
        from pymongo import MongoClient
        from langchain_core.documents import Document
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    # Import FAQ generator
    try:
        from backend.services.faq_generator import FAQGenerator
    except ImportError as e:
        logger.error(f"Could not import FAQGenerator: {e}")
        logger.info("Make sure you're running from the project root")
        sys.exit(1)
    
    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("✓ MongoDB connected")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Get collection
    db_name = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
    collection_name = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
    collection = client[db_name][collection_name]
    
    # Fetch existing chunk_ids to enable resume
    existing_chunk_ids: Set[str] = set()
    if not force:
        logger.info("Checking for existing chunk_ids (for resume capability)...")
        cursor = collection.find(
            {"metadata.chunk_id": {"$exists": True}},
            {"metadata.chunk_id": 1}
        )
        for doc in cursor:
            chunk_id = doc.get("metadata", {}).get("chunk_id")
            if chunk_id:
                existing_chunk_ids.add(chunk_id)
        logger.info(f"Found {len(existing_chunk_ids)} existing chunk_ids")
    
    # Fetch all published, non-synthetic documents
    logger.info(f"Fetching documents from {db_name}.{collection_name}...")
    query = {
        "metadata.status": "published",
        "metadata.is_synthetic": {"$ne": True}  # Exclude existing synthetic questions
    }
    
    cursor = collection.find(query, {"text": 1, "metadata": 1, "_id": 1})
    
    documents: List[Document] = []
    doc_mongo_ids: List[str] = []
    skipped_with_chunk_id = 0
    
    for doc in cursor:
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        
        if not text:
            continue
        
        # Check if already processed (has chunk_id)
        if not force and metadata.get("chunk_id"):
            skipped_with_chunk_id += 1
            continue
        
        documents.append(Document(
            page_content=text,
            metadata=metadata
        ))
        doc_mongo_ids.append(str(doc["_id"]))
    
    total_docs = len(documents)
    logger.info(f"Found {total_docs} documents to process")
    if skipped_with_chunk_id > 0:
        logger.info(f"Skipped {skipped_with_chunk_id} already processed documents (use --force to reprocess)")
    
    if total_docs == 0:
        logger.info("No documents to process! Exiting.")
        client.close()
        return
    
    # Initialize FAQ Generator with selected backend
    logger.info("Initializing FAQ Generator...")
    faq_generator = FAQGenerator(backend=backend)
    
    # Health check
    logger.info("Running health check...")
    if not await faq_generator.health_check():
        logger.error(f"Health check failed for {backend} backend!")
        if backend == "local":
            logger.info("Make sure Ollama is running: ollama serve")
            logger.info(f"And the model is pulled: ollama pull {os.getenv('FAQ_OLLAMA_MODEL', 'llama3.2:3b')}")
        else:
            logger.info("Check your GOOGLE_API_KEY is valid")
        sys.exit(1)
    
    # Process documents in batches
    logger.info(f"Processing {total_docs} documents in batches of {batch_size}...")
    
    total_chunks_processed = 0
    total_questions_generated = 0
    total_docs_updated = 0
    errors = []
    
    for i in range(0, total_docs, batch_size):
        # Check for shutdown request
        if _shutdown_requested:
            logger.info(f"\n🛑 Stopping after {total_chunks_processed} chunks processed")
            break
        
        batch_docs = documents[i:i + batch_size]
        batch_ids = doc_mongo_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_docs + batch_size - 1) // batch_size
        
        logger.info(f"\n--- Batch {batch_num}/{total_batches} ({len(batch_docs)} documents) ---")
        
        try:
            # Generate FAQ questions for batch
            all_docs, parent_chunks_map = await faq_generator.process_chunks_with_questions(batch_docs)
            
            # Count results
            synthetic_docs = [d for d in all_docs if d.metadata.get("is_synthetic", False)]
            original_docs = [d for d in all_docs if not d.metadata.get("is_synthetic", False)]
            
            logger.info(f"  Generated: {len(original_docs)} original chunks + {len(synthetic_docs)} synthetic questions")
            total_chunks_processed += len(original_docs)
            total_questions_generated += len(synthetic_docs)
            
            if dry_run:
                logger.info("  [DRY RUN] Skipping MongoDB writes")
                continue
            
            # Update original documents with chunk_id and is_synthetic=False
            for doc, mongo_id in zip(batch_docs, batch_ids):
                # Find the corresponding processed doc (has chunk_id now)
                chunk_id = None
                for processed_doc in original_docs:
                    if processed_doc.page_content == doc.page_content:
                        chunk_id = processed_doc.metadata.get("chunk_id")
                        break
                
                if chunk_id:
                    # Update the existing MongoDB document
                    from bson import ObjectId
                    collection.update_one(
                        {"_id": ObjectId(mongo_id)},
                        {"$set": {
                            "metadata.chunk_id": chunk_id,
                            "metadata.is_synthetic": False
                        }}
                    )
                    total_docs_updated += 1
            
            # Insert synthetic questions as new documents
            synthetic_inserts = []
            for syn_doc in synthetic_docs:
                synthetic_inserts.append({
                    "text": syn_doc.page_content,
                    "metadata": syn_doc.metadata
                })
            
            if synthetic_inserts:
                result = collection.insert_many(synthetic_inserts)
                logger.info(f"  Inserted {len(result.inserted_ids)} synthetic questions")
            
            logger.info(f"  ✓ Batch {batch_num} complete")
            
        except Exception as e:
            logger.error(f"  ✗ Error processing batch {batch_num}: {e}")
            errors.append((batch_num, str(e)))
            continue
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("FAQ Re-indexing Complete!")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Documents processed: {total_docs}")
    logger.info(f"Original chunks with chunk_id: {total_chunks_processed}")
    logger.info(f"Synthetic questions generated: {total_questions_generated}")
    if not dry_run:
        logger.info(f"MongoDB documents updated: {total_docs_updated}")
    if errors:
        logger.warning(f"Errors encountered: {len(errors)}")
        for batch_num, error in errors:
            logger.warning(f"  Batch {batch_num}: {error}")
    logger.info("")
    
    if not dry_run:
        logger.info("Next steps:")
        logger.info("1. Rebuild FAISS index if using Infinity embeddings:")
        logger.info("   python scripts/reindex_vectors.py")
        logger.info("2. Or restart the backend to rebuild index from MongoDB")
        logger.info("3. Set USE_FAQ_INDEXING=true to enable parent document resolution")
    
    logger.info("=" * 70)
    
    # Cleanup
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-index documents with synthetic FAQ questions (Parent Document Pattern)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Gemini (default, requires GOOGLE_API_KEY)
  python scripts/reindex_with_faq.py
  
  # Use local Ollama (no rate limits, faster!)
  python scripts/reindex_with_faq.py --local
  
  # Test without writing to DB
  python scripts/reindex_with_faq.py --dry-run --local
  
  # Force reprocess all documents
  python scripts/reindex_with_faq.py --force --local
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write anything to MongoDB (test mode)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess all documents (ignore existing chunk_ids)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents to process in each batch (default: 100)"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local Ollama instead of Gemini (no rate limits!)"
    )
    parser.add_argument(
        "--gemini",
        action="store_true",
        help="Use Gemini API (default, requires GOOGLE_API_KEY)"
    )
    
    args = parser.parse_args()
    
    # Handle backend selection (--local takes precedence)
    use_local = args.local and not args.gemini
    
    asyncio.run(main(
        dry_run=args.dry_run,
        force=args.force,
        batch_size=args.batch_size,
        use_local=use_local
    ))

