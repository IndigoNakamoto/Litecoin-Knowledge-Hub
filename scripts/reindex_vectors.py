#!/usr/bin/env python3
"""
Vector Re-indexing Script

Re-indexes all documents from MongoDB with 1024-dim Infinity embeddings.
This script creates a new FAISS index compatible with the local RAG pipeline.

IMPORTANT: This script is designed to run from your Mac terminal (host),
not inside a Docker container. It uses localhost URLs by default.

Usage:
    # From project root, with Infinity service running:
    docker-compose -f docker-compose.prod.yml --profile local-rag up -d infinity
    
    # Run the script
    python scripts/reindex_vectors.py
    
    # Or with custom Infinity URL
    INFINITY_URL=http://localhost:7997 python scripts/reindex_vectors.py

Output:
    - backend/faiss_index_1024/index.faiss - New 1024-dim FAISS index
    - backend/faiss_index_1024/index.pkl - Document store metadata
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / "backend" / ".env")

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main re-indexing function."""
    
    # Configuration
    BATCH_SIZE = 8  # Small batch for MPS stability
    # Use absolute path for container compatibility
    # When running in container, use /app/backend/faiss_index_1024
    # When running on host, use PROJECT_ROOT / "backend" / "faiss_index_1024"
    if os.path.exists("/app/backend"):
        OUTPUT_DIR = Path("/app/backend/faiss_index_1024")
    else:
        OUTPUT_DIR = PROJECT_ROOT / "backend" / "faiss_index_1024"
    
    # Use localhost URLs when running from host
    infinity_url = os.getenv("INFINITY_URL", "http://localhost:7997")
    mongo_uri = os.getenv("MONGO_URI")
    
    if not mongo_uri:
        logger.error("MONGO_URI environment variable not set!")
        logger.info("Set it in .env.local or export it before running this script")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Vector Re-indexing Script")
    logger.info("=" * 60)
    logger.info(f"Infinity URL: {infinity_url}")
    logger.info(f"MongoDB: {mongo_uri[:50]}...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info("=" * 60)
    
    # Import dependencies
    try:
        from pymongo import MongoClient
        import faiss
        from langchain_core.documents import Document
        from langchain_community.vectorstores import FAISS
        from langchain_community.docstore.in_memory import InMemoryDocstore
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Install with: pip install pymongo faiss-cpu langchain langchain-community")
        sys.exit(1)
    
    # Import Infinity adapter
    try:
        from backend.services.infinity_adapter import InfinityEmbeddings
    except ImportError:
        logger.error("Could not import InfinityEmbeddings")
        logger.info("Make sure you're running from the project root")
        sys.exit(1)
    
    # Initialize Infinity embeddings with host URL
    logger.info("Initializing Infinity embeddings...")
    infinity = InfinityEmbeddings(infinity_url=infinity_url)
    
    # Check Infinity health
    if not await infinity.health_check():
        logger.error(f"Infinity service not healthy at {infinity_url}")
        logger.info("Start Infinity with: docker-compose -f docker-compose.prod.yml --profile local-rag up -d infinity")
        sys.exit(1)
    logger.info("✓ Infinity service healthy")
    
    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("✓ MongoDB connected")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Get documents
    db_name = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
    collection_name = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
    
    collection = client[db_name][collection_name]
    
    # Fetch all documents (or filter for published only)
    logger.info(f"Fetching documents from {db_name}.{collection_name}...")
    cursor = collection.find(
        {"metadata.status": "published"},  # Only published documents
        {"text": 1, "metadata": 1, "_id": 1}
    )
    
    documents: List[Document] = []
    doc_ids: List[str] = []
    
    for doc in cursor:
        text = doc.get("text", "")
        if text:
            documents.append(Document(
                page_content=text,
                metadata=doc.get("metadata", {})
            ))
            doc_ids.append(str(doc["_id"]))
    
    total_docs = len(documents)
    logger.info(f"Found {total_docs} published documents to re-index")
    
    if total_docs == 0:
        logger.warning("No documents found! Check your MongoDB connection and filters.")
        sys.exit(1)
    
    # Generate embeddings in batches
    logger.info("Generating 1024-dim embeddings...")
    all_embeddings: List[List[float]] = []
    
    # Truncate long documents to avoid MPS memory issues
    # BGE-M3 max is 8192 tokens, but MPS struggles with very long sequences
    MAX_CHARS = 8000  # Conservative limit for MPS stability
    texts = []
    truncated_count = 0
    for doc in documents:
        text = doc.page_content
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "..."
            truncated_count += 1
        texts.append(text)
    
    if truncated_count > 0:
        logger.info(f"Truncated {truncated_count} documents exceeding {MAX_CHARS:,} chars")
    
    for i in range(0, total_docs, BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")
        
        try:
            batch_dense, _ = await infinity.embed_documents(batch)  # Extract dense embeddings only
            batch_embeddings = batch_dense
            all_embeddings.extend(batch_embeddings)
            
            # Progress update
            processed = min(i + BATCH_SIZE, total_docs)
            logger.info(f"  ✓ {processed}/{total_docs} documents processed")
            
        except Exception as e:
            logger.error(f"Error embedding batch {batch_num}: {e}")
            logger.info("Ensure Infinity service is running and accessible")
            sys.exit(1)
    
    # Verify dimensions
    if all_embeddings:
        dim = len(all_embeddings[0])
        logger.info(f"Embedding dimension: {dim}")
        
        if dim != 1024:
            logger.warning(f"Expected 1024 dimensions, got {dim}")
    
    # Convert to numpy array
    logger.info("Building FAISS index...")
    vectors = np.array(all_embeddings, dtype=np.float32)
    
    # Normalize for cosine similarity
    faiss.normalize_L2(vectors)
    
    # Create FAISS index
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product after L2 norm = cosine similarity
    index.add(vectors)
    
    logger.info(f"FAISS index created: {index.ntotal} vectors, dimension {dimension}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Build docstore and index_to_docstore_id mapping
    # This is needed for LangChain FAISS compatibility
    docstore_dict: Dict[str, Document] = {}
    index_to_docstore_id: Dict[int, str] = {}
    
    for i, (doc, doc_id) in enumerate(zip(documents, doc_ids)):
        docstore_dict[doc_id] = doc
        index_to_docstore_id[i] = doc_id
    
    docstore = InMemoryDocstore(docstore_dict)
    
    # Create LangChain FAISS wrapper
    # We need a placeholder embedding function for LangChain compatibility
    class PlaceholderEmbeddings:
        """Placeholder for LangChain compatibility."""
        def embed_documents(self, texts): 
            raise NotImplementedError("Use InfinityEmbeddings instead")
        def embed_query(self, text):
            raise NotImplementedError("Use InfinityEmbeddings instead")
    
    vector_store = FAISS(
        embedding_function=PlaceholderEmbeddings(),
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )
    
    # Save the index
    index_path = str(OUTPUT_DIR)
    vector_store.save_local(index_path)
    
    logger.info(f"✓ FAISS index saved to {index_path}")
    
    # Also save raw FAISS index for direct access
    faiss.write_index(index, str(OUTPUT_DIR / "index_raw.faiss"))
    
    # Save metadata mapping
    import pickle
    metadata_path = OUTPUT_DIR / "metadata_mapping.pkl"
    with open(metadata_path, "wb") as f:
        pickle.dump({
            "doc_ids": doc_ids,
            "dimension": dimension,
            "total_vectors": len(all_embeddings),
            "model": infinity.model_id,
        }, f)
    
    logger.info(f"✓ Metadata saved to {metadata_path}")
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Re-indexing Complete!")
    logger.info("=" * 60)
    logger.info(f"Documents indexed: {total_docs}")
    logger.info(f"Vector dimension: {dimension}")
    logger.info(f"Index location: {OUTPUT_DIR}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Update FAISS_INDEX_PATH in your .env to point to faiss_index_1024")
    logger.info("2. Set USE_INFINITY_EMBEDDINGS=true to use the new embeddings")
    logger.info("3. Restart the backend to load the new index")
    logger.info("=" * 60)
    
    # Cleanup
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

