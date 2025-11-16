import os
import logging
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
import torch
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from cache_utils import embedding_cache
import numpy as np

logger = logging.getLogger(__name__)

# Global shared MongoClient instance for connection pool sharing
# This prevents creating multiple connection pools when multiple VectorStoreManager instances are created
_shared_mongo_client: Optional[MongoClient] = None
_shared_mongo_client_lock = None

def _get_shared_mongo_client() -> Optional[MongoClient]:
    """
    Returns a shared MongoClient instance for connection pool sharing.
    This ensures all VectorStoreManager instances use the same connection pool.
    """
    global _shared_mongo_client, _shared_mongo_client_lock
    
    # Lazy import threading to avoid circular dependencies
    if _shared_mongo_client_lock is None:
        import threading
        _shared_mongo_client_lock = threading.Lock()
    
    if _shared_mongo_client is None:
        mongo_uri = os.getenv("MONGO_URI")
        if mongo_uri:
            try:
                with _shared_mongo_client_lock:
                    # Double-check pattern in case another thread created it
                    if _shared_mongo_client is None:
                        _shared_mongo_client = MongoClient(
                            mongo_uri,
                            serverSelectionTimeoutMS=5000,
                            maxPoolSize=50,
                            minPoolSize=10,
                            maxIdleTimeMS=30000,
                            waitQueueTimeoutMS=5000,
                            retryWrites=True,
                            retryReads=True
                        )
                        _shared_mongo_client.admin.command('ping')
                        logger.info("Shared MongoDB client created with connection pooling")
            except Exception as e:
                logger.warning(f"Failed to create shared MongoDB client: {e}")
                return None
    
    return _shared_mongo_client

def close_shared_mongo_client():
    """
    Closes the shared MongoClient instance.
    Should be called during application shutdown.
    """
    global _shared_mongo_client
    if _shared_mongo_client is not None:
        try:
            _shared_mongo_client.close()
            logger.info("Shared MongoDB client closed")
        except Exception as e:
            logger.error(f"Error closing shared MongoDB client: {e}")
        finally:
            _shared_mongo_client = None

# Auto-detect Apple M1/M2/M3 GPU (Metal Performance Shaders)
if torch.backends.mps.is_available():
    device = "mps"
    logger.info("Using Apple MPS (M1/M2/M3 GPU) for embeddings.")
elif torch.cuda.is_available():
    device = "cuda"
    logger.info("Using NVIDIA CUDA (GPU) for embeddings.")
else:
    device = "cpu"
    logger.info("GPU not available. Using CPU for embeddings.")

# Default local embedding model - fast and efficient for semantic search
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_KWARGS = {"device": device}
ENCODE_KWARGS = {"normalize_embeddings": True}  # Normalize embeddings for better similarity search

def get_local_embedding_model():
    """
    Helper function to get a local embedding model using sentence-transformers.
    This eliminates the need for Google API calls and avoids 504 errors.
    """
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=DEFAULT_EMBEDDING_MODEL,
            model_kwargs=EMBEDDING_MODEL_KWARGS,
            encode_kwargs=ENCODE_KWARGS
        )
        logger.info(f"Local embedding model '{DEFAULT_EMBEDDING_MODEL}' initialized successfully")
        return embeddings
    except Exception as e:
        logger.error(f"Failed to initialize local embedding model: {e}")
        raise


class VectorStoreManager:
    """
    Simplified VectorStoreManager using FAISS with local embeddings.
    Manages interactions with FAISS vector store and optional MongoDB document storage.
    """
    
    def __init__(self, db_name: str = "litecoin_rag_db", collection_name: str = "litecoin_docs"):
        """
        Initializes the VectorStoreManager with local embeddings.

        Args:
            db_name: The name of the database to use.
            collection_name: The name of the collection to use.
        """
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongodb_available = False
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None  # Will use shared client, not own instance
        self._owns_client = False  # Track if we own the client (for cleanup)

        # Use shared MongoDB connection pool instead of creating new one
        # This prevents connection pool accumulation when multiple VectorStoreManager instances are created
        if self.mongo_uri:
            try:
                self.client = _get_shared_mongo_client()
                if self.client:
                    self.mongodb_available = True
                    self.collection = self.client[self.db_name][self.collection_name]
                    logger.info(f"MongoDB connection successful using shared connection pool (db: {self.db_name}, collection: {self.collection_name})")
                else:
                    logger.warning("Shared MongoDB client unavailable. Using FAISS only mode.")
                    self.mongodb_available = False
            except Exception as e:
                logger.warning(f"MongoDB connection failed: {e}. Using FAISS only mode.")
                self.mongodb_available = False
        else:
            logger.warning("MONGO_URI not set. Using FAISS only mode.")
            self.mongodb_available = False

        # Initialize local embeddings
        self.embeddings = get_local_embedding_model()
        self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", "./backend/faiss_index")
        
        # Ensure directory exists
        os.makedirs(self.faiss_index_path, exist_ok=True)

        # Try to load existing FAISS index, otherwise create empty or from MongoDB
        index_file = os.path.join(self.faiss_index_path, "index.faiss")
        if os.path.exists(index_file):
            logger.info(f"Loading existing FAISS index from {self.faiss_index_path}")
            try:
                self.vector_store = FAISS.load_local(
                    self.faiss_index_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load existing FAISS index: {e}. Creating new index.")
                self.vector_store = self._create_empty_faiss_index()
        elif self.mongodb_available:
            logger.info("No existing FAISS index found, creating from MongoDB documents")
            self.vector_store = self._create_faiss_from_mongodb()
        else:
            logger.info("No existing FAISS index and MongoDB unavailable, creating empty FAISS index")
            self.vector_store = self._create_empty_faiss_index()

        logger.info(f"VectorStoreManager initialized (MongoDB: {'available' if self.mongodb_available else 'unavailable'})")

    def _create_empty_faiss_index(self):
        """Creates an empty FAISS index."""
        # Create a minimal index with empty text
        vector_store = FAISS.from_texts([""], self.embeddings)
        vector_store.save_local(self.faiss_index_path)
        logger.info(f"Created empty FAISS index at {self.faiss_index_path}")
        return vector_store

    def _create_faiss_from_mongodb(self):
        """Creates FAISS vector store from existing MongoDB documents."""
        if not self.mongodb_available:
            return self._create_empty_faiss_index()
            
        # Load all documents from MongoDB
        mongo_docs = list(self.collection.find({}))
        documents = []
        for doc in mongo_docs:
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            if text:  # Only add non-empty documents
                documents.append(Document(page_content=text, metadata=metadata))

        if documents:
            logger.info(f"Creating FAISS index from {len(documents)} documents in MongoDB")
            vector_store = FAISS.from_documents(documents, self.embeddings)
            vector_store.save_local(self.faiss_index_path)
            logger.info(f"FAISS index created and saved to {self.faiss_index_path}")
            return vector_store
        else:
            logger.info("No documents in MongoDB, creating empty FAISS index")
            return self._create_empty_faiss_index()

    def _save_faiss_index(self):
        """Saves the current FAISS index to disk."""
        try:
            self.vector_store.save_local(self.faiss_index_path)
            logger.info(f"FAISS index saved to {self.faiss_index_path}")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")

    def add_documents(self, documents: List[Document], batch_size: int = 10):
        """
        Adds documents to FAISS vector store and MongoDB storage in batches.

        Args:
            documents: A list of Langchain Document objects.
            batch_size: The number of documents to process in each batch.
        """
        if not documents:
            logger.info("No documents provided to add.")
            return

        total_docs = len(documents)
        success_count = 0
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}...")
            try:
                # Add to FAISS
                self.vector_store.add_documents(batch, embedding=self.embeddings)

                # Store in MongoDB if available
                if self.mongodb_available:
                    for doc in batch:
                        mongo_doc = {
                            "text": doc.page_content,
                            "metadata": doc.metadata
                        }
                        self.collection.insert_one(mongo_doc)

                success_count += len(batch)
                logger.info(f"Successfully added batch of {len(batch)} documents.")
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {e}", exc_info=True)
                raise e

        # Save FAISS index after all additions
        self._save_faiss_index()
        if self.mongodb_available:
            logger.info(f"Finished adding {success_count} of {total_docs} documents to FAISS and MongoDB collection '{self.collection_name}'.")
        else:
            logger.info(f"Finished adding {success_count} of {total_docs} documents to FAISS (MongoDB not available).")

    def get_cached_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts with caching to reduce computation.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = embedding_cache.get_similar(text)
            if cached is not None:
                cached_embeddings.append(cached.tolist())
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts using local model
        if uncached_texts:
            logger.info(f"Generating embeddings for {len(uncached_texts)} uncached texts using local model")
            new_embeddings = self.embeddings.embed_documents(uncached_texts)

            # Cache the new embeddings
            for text, embedding in zip(uncached_texts, new_embeddings):
                embedding_cache.set(text, np.array(embedding))

            # Insert new embeddings into results
            for i, (idx, embedding) in enumerate(zip(uncached_indices, new_embeddings)):
                cached_embeddings.insert(idx, embedding)

        return cached_embeddings

    def get_retriever(self, search_type="similarity", search_kwargs=None):
        """
        Returns a retriever instance from the vector store.

        Args:
            search_type: The type of search (e.g., "similarity", "mmr").
            search_kwargs: Dictionary of arguments for the retriever (e.g., {"k": 5}).
        """
        if search_kwargs is None:
            search_kwargs = {"k": 10}
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def delete_documents_by_metadata_field(self, field_name: str, field_value: Any):
        """
        Deletes documents from MongoDB and rebuilds FAISS index.
        This is the generic method for deleting documents based on a metadata key-value pair.

        Args:
            field_name: The name of the metadata field to filter on (e.g., "payload_id", "source").
            field_value: The value of the metadata field to match.
        """
        if not field_name or field_value is None:
            logger.warning("Field name and value must be provided for deletion.")
            return 0

        if not self.mongodb_available:
            logger.warning("MongoDB not available. Cannot perform selective deletion. Use clear_all_documents to reset FAISS index.")
            return 0

        mongo_filter = {f"metadata.{field_name}": field_value}

        logger.info(f"Attempting to delete documents with filter: {mongo_filter}")
        try:
            result = self.collection.delete_many(mongo_filter)
            logger.info(f"Deleted {result.deleted_count} documents matching filter: {mongo_filter}")

            # Rebuild FAISS index from remaining MongoDB documents
            self.vector_store = self._create_faiss_from_mongodb()

            return result.deleted_count
        except Exception as e:
            logger.error(f"An error occurred during deletion with filter {mongo_filter}: {e}", exc_info=True)
            return 0

    def clean_draft_documents(self):
        """
        Removes all documents with status != 'published' from both MongoDB and FAISS index.
        This is useful for cleaning up draft content that might still be indexed.
        """
        if not self.mongodb_available:
            logger.warning("MongoDB not available. Cannot clean draft documents.")
            return 0

        try:
            logger.info("🧹 Starting cleanup of draft/unpublished documents...")

            # Find documents that are not published (draft, etc.)
            draft_filter = {"metadata.status": {"$ne": "published"}}
            draft_docs_cursor = self.collection.find(draft_filter)
            draft_payload_ids = []

            # Collect payload IDs to delete from FAISS (FAISS doesn't support metadata queries)
            for doc in draft_docs_cursor:
                payload_id = doc.get("metadata", {}).get("payload_id")
                if payload_id:
                    draft_payload_ids.append(payload_id)

            # Delete draft documents from MongoDB
            result = self.collection.delete_many(draft_filter)
            logger.info(f"🗑️ Deleted {result.deleted_count} draft documents from MongoDB")

            # If we have payload IDs, also clean any chunks that might use different status values
            additional_deleted = 0
            if draft_payload_ids:
                additional_filter = {"metadata.payload_id": {"$in": draft_payload_ids}}
                additional_result = self.collection.delete_many(additional_filter)
                additional_deleted = additional_result.deleted_count
                if additional_deleted > 0:
                    logger.info(f"🗑️ Deleted {additional_deleted} additional chunks by payload_id")

            # Rebuild FAISS index from remaining published documents
            self.vector_store = self._create_faiss_from_mongodb()
            logger.info("✅ FAISS index rebuilt after draft cleanup")

            total_deleted = result.deleted_count + additional_deleted
            return total_deleted

        except Exception as e:
            logger.error(f"An error occurred during draft document cleanup: {e}", exc_info=True)
            return 0

    def clear_all_documents(self):
        """
        Deletes all documents from MongoDB and creates empty FAISS index. Use with caution.
        """
        if self.mongodb_available:
            logger.warning(f"Attempting to delete ALL documents from collection: '{self.collection_name}' in db: '{self.db_name}'")
            try:
                result = self.collection.delete_many({})
                logger.info(f"Deleted {result.deleted_count} documents. Collection should now be empty.")
            except Exception as e:
                logger.error(f"An error occurred during clearing all documents: {e}", exc_info=True)
                return 0
        else:
            logger.warning("MongoDB not available. Clearing FAISS index only.")

        # Create empty FAISS index
        self.vector_store = self._create_empty_faiss_index()
        logger.info("FAISS index cleared and saved.")

        return 0 if not self.mongodb_available else result.deleted_count

    def close(self):
        """
        Closes MongoDB connection if this instance owns it.
        Note: With shared connection pool, this is a no-op as the shared client
        should be closed via close_shared_mongo_client() during application shutdown.
        """
        if self._owns_client and self.client:
            try:
                self.client.close()
                logger.info("VectorStoreManager MongoDB client closed")
            except Exception as e:
                logger.error(f"Error closing VectorStoreManager MongoDB client: {e}")
            finally:
                self.client = None
                self.mongodb_available = False


# For direct execution and testing of this module (optional)
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

    logger.info("Testing VectorStoreManager with local embeddings...")
    try:
        manager = VectorStoreManager(collection_name="test_collection")
        
        manager.clear_all_documents()

        doc1 = Document(page_content="This is test document one about apples.", metadata={"source": "test_file_1.txt", "id": 1})
        doc2 = Document(page_content="This is test document two about oranges.", metadata={"source": "test_file_2.txt", "id": 2})
        doc3 = Document(page_content="Another test document, also about apples and fruits.", metadata={"source": "test_file_1.txt", "id": 3})
        
        docs_to_add = [doc1, doc2, doc3]

        logger.info(f"\nAdding {len(docs_to_add)} documents...")
        manager.add_documents(docs_to_add)

        logger.info("\nTesting retrieval for 'apples'...")
        retriever = manager.get_retriever(search_kwargs={"k": 2})
        retrieved_docs = retriever.get_relevant_documents("apples")
        logger.info(f"Retrieved {len(retrieved_docs)} documents for 'apples':")
        for i, doc in enumerate(retrieved_docs):
            logger.info(f"  Doc {i+1}: {doc.page_content[:50]}... (Metadata: {doc.metadata})")
        
        logger.info("\nTesting deletion for metadata field 'source' with value 'test_file_1.txt'...")
        deleted_count = manager.delete_documents_by_metadata_field("source", "test_file_1.txt")
        logger.info(f"Deleted {deleted_count} documents.")

        logger.info("\nTesting retrieval for 'apples' after deletion...")
        retriever_after_delete = manager.get_retriever(search_kwargs={"k": 2})
        retrieved_docs_after_delete = retriever_after_delete.get_relevant_documents("apples")
        logger.info(f"Retrieved {len(retrieved_docs_after_delete)} documents for 'apples' after deletion:")
        for i, doc in enumerate(retrieved_docs_after_delete):
            logger.info(f"  Doc {i+1}: {doc.page_content[:50]}... (Metadata: {doc.metadata})")
            if doc.metadata.get("source") == "test_file_1.txt":
                logger.warning(f"  ⚠️ Found document that should have been deleted!")

        logger.info("\nCleaning up: Deleting all documents from test_collection...")
        manager.clear_all_documents()
        logger.info("\nVectorStoreManager test finished.")

    except Exception as e:
        logger.error(f"An error occurred during VectorStoreManager test: {e}")
        import traceback
        traceback.print_exc()
