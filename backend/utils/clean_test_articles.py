#!/usr/bin/env python3
"""
Cleanup utility to remove test articles from the vector store.

This script removes all documents with payload_id starting with "test-" from MongoDB
and rebuilds the FAISS index to ensure only real Payload CMS articles remain.
"""

import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Also add project root for backend.* imports
project_root = os.path.abspath(os.path.join(backend_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging

# Set up logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    dotenv_path = os.path.join(backend_dir, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)
        logger.info(f"Loaded environment variables from: {dotenv_path}")
    else:
        # Try project root .env as fallback
        project_dotenv = os.path.join(project_root, '.env')
        if os.path.exists(project_dotenv):
            load_dotenv(project_dotenv, override=True)
            logger.info(f"Loaded environment variables from: {project_dotenv}")
        else:
            logger.debug(f"No .env file found at {dotenv_path} or {project_dotenv}. Using environment variables from shell.")
except ImportError:
    # dotenv not available, just use environment variables from shell
    logger.debug("python-dotenv not installed. Using environment variables from shell.")

from data_ingestion.vector_store_manager import VectorStoreManager

def find_test_articles(vector_store_manager):
    """
    Find all documents with payload_id starting with "test-".
    """
    if not vector_store_manager.mongodb_available:
        logger.error("MongoDB not available. Cannot find test articles.")
        return []
    
    try:
        # Find all documents with payload_id starting with "test-"
        # Using regex to match payload_id starting with "test-"
        test_filter = {"metadata.payload_id": {"$regex": "^test-", "$options": "i"}}
        
        test_docs = list(vector_store_manager.collection.find(test_filter))
        
        # Group by payload_id to show counts
        test_article_ids = {}
        for doc in test_docs:
            payload_id = doc.get("metadata", {}).get("payload_id")
            if payload_id:
                if payload_id not in test_article_ids:
                    test_article_ids[payload_id] = 0
                test_article_ids[payload_id] += 1
        
        logger.info(f"Found {len(test_docs)} chunks from {len(test_article_ids)} test articles:")
        for payload_id, count in sorted(test_article_ids.items()):
            logger.info(f"  - {payload_id}: {count} chunks")
        
        return list(test_article_ids.keys())
    
    except Exception as e:
        logger.error(f"Error finding test articles: {e}", exc_info=True)
        return []

def cleanup_test_articles(vector_store_manager, dry_run=False):
    """
    Remove all test articles from MongoDB and rebuild FAISS index.
    
    Args:
        vector_store_manager: VectorStoreManager instance
        dry_run: If True, only show what would be deleted without actually deleting
    """
    if not vector_store_manager.mongodb_available:
        logger.error("MongoDB not available. Cannot clean test articles.")
        return 0
    
    try:
        # Find test articles
        test_article_ids = find_test_articles(vector_store_manager)
        
        if not test_article_ids:
            logger.info("No test articles found.")
            return 0
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete {len(test_article_ids)} test articles")
            return len(test_article_ids)
        
        # Delete each test article by payload_id
        total_deleted = 0
        for payload_id in test_article_ids:
            try:
                deleted_count = vector_store_manager.delete_documents_by_metadata_field(
                    'payload_id', payload_id
                )
                total_deleted += deleted_count
                logger.info(f"Deleted {deleted_count} chunks for test article: {payload_id}")
            except Exception as e:
                logger.error(f"Error deleting test article {payload_id}: {e}", exc_info=True)
        
        logger.info(f"✅ Successfully deleted {total_deleted} chunks from {len(test_article_ids)} test articles")
        logger.info("FAISS index has been rebuilt without test articles")
        
        return total_deleted
    
    except Exception as e:
        logger.error(f"Error cleaning test articles: {e}", exc_info=True)
        return 0

def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up test articles from the vector store")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true", help="Actually perform the deletion (required if not dry-run)")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.force:
        print("❌ ERROR: Must specify --force to actually perform deletion, or --dry-run to preview")
        return False
    
    print("🧹 Starting test articles cleanup")
    print("=" * 50)
    
    # Check if MONGO_URI is set
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("❌ ERROR: MONGO_URI environment variable is not set.")
        print("   Please ensure you have a .env file with MONGO_URI configured.")
        print(f"   Expected .env file at: {os.path.join(backend_dir, '.env')}")
        print(f"   Or at: {os.path.join(project_root, '.env')}")
        return False
    
    # Initialize vector store manager
    try:
        vector_store_manager = VectorStoreManager()
        logger.info("Vector store manager initialized")
        
        if not vector_store_manager.mongodb_available:
            print("❌ ERROR: MongoDB is not available.")
            print("   Please check:")
            print("   1. MONGO_URI is set correctly in your .env file")
            print("   2. MongoDB is running and accessible")
            print(f"   Current MONGO_URI: {mongo_uri[:20]}... (hidden)")
            return False
    except Exception as e:
        logger.error(f"Failed to initialize vector store manager: {e}")
        return False
    
    # Clean test articles
    if args.dry_run:
        print("🔍 DRY RUN: Finding test articles...")
        test_article_ids = find_test_articles(vector_store_manager)
        if test_article_ids:
            print(f"\nWould delete {len(test_article_ids)} test articles:")
            for payload_id in sorted(test_article_ids):
                print(f"  - {payload_id}")
        else:
            print("No test articles found.")
    else:
        print("🗑️ Removing test articles...")
        deleted_count = cleanup_test_articles(vector_store_manager, dry_run=False)
        if deleted_count > 0:
            print(f"✅ Successfully cleaned {deleted_count} chunks from test articles")
            print("\n💡 Tip: The FAISS index has been rebuilt. You may want to restart your backend server")
            print("   to ensure the RAG pipeline uses the updated vector store.")
        else:
            print("ℹ️ No test articles found to clean.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

