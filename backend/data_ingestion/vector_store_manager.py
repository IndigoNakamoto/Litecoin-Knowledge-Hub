import os
import logging # Import logging
from typing import List, Dict, Any
from pymongo import MongoClient
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__) # Initialize logger

def get_default_embedding_model(task_type: str = "retrieval_document"):
    """
    Helper function to get a default Google Generative AI Embedding model.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        task_type=task_type,
        google_api_key=google_api_key,
        request_options={"timeout": 120} # Set timeout to 120 seconds
    )

class VectorStoreManager:
    """
    Manages interactions with FAISS vector store and MongoDB document storage.
    """
    def __init__(self, db_name: str = "litecoin_rag_db", collection_name: str = "litecoin_docs"):
        """
        Initializes the VectorStoreManager.

        Args:
            db_name: The name of the database to use.
            collection_name: The name of the collection to use.
        """
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongodb_available = False

        if self.mongo_uri:
            try:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.client.admin.command('ping')
                self.mongodb_available = True
                self.db_name = db_name
                self.collection_name = collection_name
                self.collection = self.client[self.db_name][self.collection_name]
                logger.info("MongoDB connection successful")
            except Exception as e:
                logger.warning(f"MongoDB connection failed: {e}. Using FAISS only mode.")
                self.mongodb_available = False
        else:
            logger.warning("MONGO_URI not set. Using FAISS only mode.")
            self.mongodb_available = False

        self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", "./backend/faiss_index")
        self.default_query_embeddings = get_default_embedding_model(task_type="retrieval_query")

        # Try to load existing FAISS index, otherwise create empty or from MongoDB
        index_file = os.path.join(self.faiss_index_path, "index.faiss")
        if os.path.exists(index_file):
            logger.info(f"Loading existing FAISS index from {self.faiss_index_path}")
            self.vector_store = FAISS.load_local(self.faiss_index_path, self.default_query_embeddings, allow_dangerous_deserialization=True)
        elif self.mongodb_available:
            logger.info("No existing FAISS index found, creating from MongoDB documents")
            self.vector_store = self._create_faiss_from_mongodb()
        else:
            logger.info("No existing FAISS index and MongoDB unavailable, creating empty FAISS index")
            embeddings_model = get_default_embedding_model(task_type="retrieval_document")
            self.vector_store = FAISS.from_texts([""], embeddings_model)  # Empty index

        logger.info(f"VectorStoreManager initialized (MongoDB: {'available' if self.mongodb_available else 'unavailable'})")

    def _create_faiss_from_mongodb(self):
        """Creates FAISS vector store from existing MongoDB documents."""
        # Load all documents from MongoDB
        mongo_docs = list(self.collection.find({}))
        documents = []
        for doc in mongo_docs:
            # Assuming documents are stored with 'text' and 'metadata' fields
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            documents.append(Document(page_content=text, metadata=metadata))

        if documents:
            logger.info(f"Creating FAISS index from {len(documents)} documents in MongoDB")
            embeddings_model = get_default_embedding_model(task_type="retrieval_document")
            vector_store = FAISS.from_documents(documents, embeddings_model)
            # Save the index
            vector_store.save_local(self.faiss_index_path)
            return vector_store
        else:
            logger.info("No documents in MongoDB, creating empty FAISS index")
            embeddings_model = get_default_embedding_model(task_type="retrieval_document")
            vector_store = FAISS.from_texts([""], embeddings_model)  # Empty index
            vector_store.save_local(self.faiss_index_path)
            return vector_store

    def _save_faiss_index(self):
        """Saves the current FAISS index to disk."""
        self.vector_store.save_local(self.faiss_index_path)
        logger.info(f"FAISS index saved to {self.faiss_index_path}")

    def add_documents(self, documents: List[Document], embeddings_model=None, batch_size: int = 10):
        """
        Adds documents to FAISS vector store and MongoDB storage in batches.

        Args:
            documents: A list of Langchain Document objects.
            embeddings_model: The embedding model to use for creating document embeddings.
                              If None, defaults to a model with 'retrieval_document' task type.
            batch_size: The number of documents to process in each batch.
        Raises:
            Exception: If an error occurs during the embedding or addition of documents.
        """
        if not documents:
            logger.info("No documents provided to add.")
            return

        active_embeddings_model = embeddings_model
        if active_embeddings_model is None:
            active_embeddings_model = get_default_embedding_model(task_type="retrieval_document")

        total_docs = len(documents)
        success_count = 0
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}...")
            try:
                # Add to FAISS
                self.vector_store.add_documents(batch, embedding=active_embeddings_model)

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
                # Re-raise the exception to propagate the error to the calling function
                raise e

        # Save FAISS index after all additions
        self._save_faiss_index()
        logger.info(f"Finished adding {success_count} of {total_docs} documents to FAISS and MongoDB collection '{self.collection_name}'.")

    def get_retriever(self, search_type="similarity", search_kwargs=None):
        """
        Returns a retriever instance from the vector store.

        Args:
            search_type: The type of search (e.g., "similarity", "mmr").
            search_kwargs: Dictionary of arguments for the retriever (e.g., {"k": 5}).
        """
        if search_kwargs is None:
            search_kwargs = {"k": 3}
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
        embeddings_model = get_default_embedding_model(task_type="retrieval_document")
        self.vector_store = FAISS.from_texts([""], embeddings_model)  # Empty index
        self._save_faiss_index()
        logger.info("FAISS index cleared and saved.")

        return 0 if not self.mongodb_available else result.deleted_count

# For direct execution and testing of this module (optional)
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

    logger.info("Testing VectorStoreManager...")
    try:
        manager = VectorStoreManager(collection_name="test_collection")
        
        manager.clear_all_documents()

        doc1 = Document(page_content="This is test document one about apples.", metadata={"source": "test_file_1.txt", "id": 1})
        doc2 = Document(page_content="This is test document two about oranges.", metadata={"source": "test_file_2.txt", "id": 2})
        doc3 = Document(page_content="Another test document, also about apples and fruits.", metadata={"source": "test_file_1.txt", "id": 3})
        
        docs_to_add = [doc1, doc2, doc3]

        logger.info(f"\nAdding {len(docs_to_add)} documents...")
        doc_embedding_model = get_default_embedding_model(task_type="retrieval_document")
        manager.add_documents(docs_to_add, embeddings_model=doc_embedding_model)

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
            assert doc.metadata["source"] != "test_file_1.txt"

        logger.info("\nCleaning up: Deleting all documents from test_collection...")
        manager.clear_all_documents()
        logger.info("\nVectorStoreManager test finished.")

    except ValueError as ve:
        logger.error(f"Configuration Error: {ve}")
        logger.error("Please ensure MONGO_URI and GOOGLE_API_KEY are set in your .env.example file in the backend directory.")
    except Exception as e:
        logger.error(f"An error occurred during VectorStoreManager test: {e}")
