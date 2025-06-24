import os
import logging # Import logging
from typing import List, Dict, Any
from pymongo import MongoClient
from langchain_core.documents import Document
from langchain_mongodb import MongoDBAtlasVectorSearch
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
    Manages interactions with the MongoDB Atlas Vector Search instance.
    """
    def __init__(self, db_name: str = "litecoin_rag_db", collection_name: str = "litecoin_docs"):
        """
        Initializes the VectorStoreManager.

        Args:
            db_name: The name of the database to use.
            collection_name: The name of the collection to use.
        """
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            raise ValueError("MONGO_URI environment variable not set.")
        
        self.client = MongoClient(self.mongo_uri)
        self.db_name = db_name
        self.collection_name = collection_name
        self.collection = self.client[self.db_name][self.collection_name]
        
        self.default_query_embeddings = get_default_embedding_model(task_type="retrieval_query")

        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.collection,
            embedding=self.default_query_embeddings,
            index_name=os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index"),
            text_key="text",
            metadata_key="metadata"
        )
        logger.info(f"VectorStoreManager initialized for db: '{self.db_name}', collection: '{self.collection_name}'")

    def add_documents(self, documents: List[Document], embeddings_model=None, batch_size: int = 10):
        """
        Adds documents to the vector store in batches.

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
                self.vector_store.add_documents(batch, embedding=active_embeddings_model)
                success_count += len(batch)
                logger.info(f"Successfully added batch of {len(batch)} documents.")
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {e}", exc_info=True)
                # Re-raise the exception to propagate the error to the calling function
                raise e
        
        logger.info(f"Finished adding {success_count} of {total_docs} documents to collection '{self.collection_name}'.")

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
        Deletes documents from the vector store that match a specific metadata field and value.
        This is the generic method for deleting documents based on a metadata key-value pair.

        Args:
            field_name: The name of the metadata field to filter on (e.g., "payload_id", "source").
            field_value: The value of the metadata field to match.
        """
        if not field_name or field_value is None:
            logger.warning("Field name and value must be provided for deletion.")
            return 0
        
        mongo_filter = {field_name: field_value}
        
        logger.info(f"Attempting to delete documents with filter: {mongo_filter}")
        try:
            result = self.collection.delete_many(mongo_filter)
            logger.info(f"Deleted {result.deleted_count} documents matching filter: {mongo_filter}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"An error occurred during deletion with filter {mongo_filter}: {e}", exc_info=True)
            return 0

    def clear_all_documents(self):
        """
        Deletes all documents from the collection. Use with caution.
        """
        logger.warning(f"Attempting to delete ALL documents from collection: '{self.collection_name}' in db: '{self.db_name}'")
        try:
            result = self.collection.delete_many({})
            logger.info(f"Deleted {result.deleted_count} documents. Collection should now be empty.")
            return result.deleted_count
        except Exception as e:
            logger.error(f"An error occurred during clearing all documents: {e}", exc_info=True)
            return 0

# For direct execution and testing of this module (optional)
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example'))

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
        retrieved_docs_after_delete = retriever.get_relevant_documents("apples")
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
