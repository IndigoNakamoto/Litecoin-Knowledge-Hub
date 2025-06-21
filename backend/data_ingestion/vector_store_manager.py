import os
from typing import List, Dict, Any
from pymongo import MongoClient
from langchain_core.documents import Document
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings # Added for explicit embedding model usage

# Assuming get_embedding_client is defined in embedding_processor.py
# If it's just GoogleGenerativeAIEmbeddings, we can initialize directly.
# For now, let's keep it flexible.
# from .embedding_processor import get_embedding_client # This would cause circular dependency if embedding_processor imports this.

def get_default_embedding_model(task_type: str = "retrieval_document"):
    """
    Helper function to get a default Google Generative AI Embedding model.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type=task_type, google_api_key=google_api_key)

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
        
        # Default embedding model for the store's operations if not overridden
        # This embedding model is used by Langchain's MongoDBAtlasVectorSearch for its internal query embedding
        # if an embedding function isn't explicitly passed to methods like similarity_search.
        # For adding documents, we typically pass an embedding model with 'retrieval_document' task_type.
        # For querying, the RAG pipeline should use an embedding model with 'retrieval_query' task_type.
        self.default_query_embeddings = get_default_embedding_model(task_type="retrieval_query")

        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.collection,
            embedding=self.default_query_embeddings, # Used for similarity search if query isn't pre-embedded
            index_name=os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index"), # Ensure your index name is correct
            text_key="text",  # Explicitly define the field name for document content
            metadata_key="metadata"  # Explicitly define the field name for metadata
        )
        print(f"VectorStoreManager initialized for db: '{self.db_name}', collection: '{self.collection_name}'")

    def add_documents(self, documents: List[Document], embeddings_model=None, batch_size: int = 100):
        """
        Adds documents to the vector store in batches.

        Args:
            documents: A list of Langchain Document objects.
            embeddings_model: The embedding model to use for creating document embeddings.
                              If None, defaults to a model with 'retrieval_document' task type.
            batch_size: The number of documents to process in each batch.
        """
        if not documents:
            print("No documents provided to add.")
            return

        active_embeddings_model = embeddings_model
        if active_embeddings_model is None:
            active_embeddings_model = get_default_embedding_model(task_type="retrieval_document")
        
        total_docs = len(documents)
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}...")
            try:
                self.vector_store.add_documents(batch, embedding=active_embeddings_model)
                print(f"Successfully added batch of {len(batch)} documents.")
            except Exception as e:
                print(f"Error adding batch {i//batch_size + 1}: {e}")
                # Optionally, re-raise the exception if you want to halt the process
                # raise e
        
        print(f"Finished adding {total_docs} documents to collection '{self.collection_name}'.")

    def get_retriever(self, search_type="similarity", search_kwargs=None):
        """
        Returns a retriever instance from the vector store.

        Args:
            search_type: The type of search (e.g., "similarity", "mmr").
            search_kwargs: Dictionary of arguments for the retriever (e.g., {"k": 5}).
        """
        if search_kwargs is None:
            search_kwargs = {"k": 3} # Default to retrieving top 3 documents
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def delete_documents_by_metadata(self, metadata_filter: Dict[str, Any]):
        """
        Deletes documents from the vector store that match the metadata filter.

        Args:
            metadata_filter: A dictionary defining the filter for metadata.
                             Example: {"source": "some_file.md"}
        """
        if not metadata_filter:
            print("No metadata filter provided for deletion.")
            return 0
        
        # Reason: Based on debugging, it's confirmed that langchain-mongodb flattens the metadata
        # fields into the root of the MongoDB document, rather than storing them in a 'metadata' sub-document.
        # Therefore, the filter should target the keys directly at the root level.
        mongo_filter = metadata_filter
        
        print(f"Attempting to delete documents with filter: {mongo_filter}")
        result = self.collection.delete_many(mongo_filter)
        print(f"Deleted {result.deleted_count} documents matching filter: {metadata_filter}")
        return result.deleted_count

    def delete_documents_by_strapi_id(self, strapi_id: int):
        """
        Deletes all document chunks associated with a specific Strapi entry ID.

        Args:
            strapi_id: The integer ID of the Strapi entry.
        """
        if not isinstance(strapi_id, int):
            print("Invalid Strapi ID provided for deletion.")
            return 0
        
        # The filter targets the 'strapi_id' field which is stored at the root of the document.
        mongo_filter = {"strapi_id": strapi_id}
        
        print(f"Attempting to delete documents with Strapi ID: {strapi_id}")
        result = self.collection.delete_many(mongo_filter)
        print(f"Deleted {result.deleted_count} documents for Strapi ID: {strapi_id}")
        return result.deleted_count

    def delete_documents_by_document_id(self, document_id: str):
        """
        Deletes all document chunks associated with a specific Strapi document ID.
        This is the correct way to delete an article and all its localizations.

        Args:
            document_id: The string ID of the Strapi document.
        """
        if not isinstance(document_id, str):
            print("Invalid Strapi document_id provided for deletion.")
            return 0
        
        # The filter targets the 'document_id' field which is stored at the root of the document.
        mongo_filter = {"document_id": document_id}
        
        print(f"Attempting to delete documents with document_id: {document_id}")
        result = self.collection.delete_many(mongo_filter)
        print(f"Deleted {result.deleted_count} documents for document_id: {document_id}")
        return result.deleted_count

    def clear_all_documents(self):
        """
        Deletes all documents from the collection. Use with caution.
        """
        print(f"Attempting to delete ALL documents from collection: '{self.collection_name}' in db: '{self.db_name}'")
        result = self.collection.delete_many({})
        print(f"Deleted {result.deleted_count} documents. Collection should now be empty.")
        return result.deleted_count

# For direct execution and testing of this module (optional)
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example')) # Load from backend/.env.example

    print("Testing VectorStoreManager...")
    try:
        # Initialize manager (ensure MONGO_URI and GOOGLE_API_KEY are in .env.example)
        manager = VectorStoreManager(collection_name="test_collection")
        
        # Clear any previous test data
        manager.clear_all_documents()

        # Create dummy documents
        doc1 = Document(page_content="This is test document one about apples.", metadata={"source": "test_file_1.txt", "id": 1})
        doc2 = Document(page_content="This is test document two about oranges.", metadata={"source": "test_file_2.txt", "id": 2})
        doc3 = Document(page_content="Another test document, also about apples and fruits.", metadata={"source": "test_file_1.txt", "id": 3})
        
        docs_to_add = [doc1, doc2, doc3]

        # Add documents
        print(f"\nAdding {len(docs_to_add)} documents...")
        doc_embedding_model = get_default_embedding_model(task_type="retrieval_document")
        manager.add_documents(docs_to_add, embeddings_model=doc_embedding_model)

        # Test retrieval
        print("\nTesting retrieval for 'apples'...")
        retriever = manager.get_retriever(search_kwargs={"k": 2})
        # The retriever uses the default_query_embeddings (task_type='retrieval_query')
        retrieved_docs = retriever.get_relevant_documents("apples")
        print(f"Retrieved {len(retrieved_docs)} documents for 'apples':")
        for i, doc in enumerate(retrieved_docs):
            print(f"  Doc {i+1}: {doc.page_content[:50]}... (Metadata: {doc.metadata})")
        
        # Test deletion by metadata
        print("\nTesting deletion for metadata {'source': 'test_file_1.txt'}...")
        deleted_count = manager.delete_documents_by_metadata({"source": "test_file_1.txt"})
        print(f"Deleted {deleted_count} documents.")

        # Verify deletion by trying to retrieve again (should be fewer or different docs)
        print("\nTesting retrieval for 'apples' after deletion...")
        retrieved_docs_after_delete = retriever.get_relevant_documents("apples")
        print(f"Retrieved {len(retrieved_docs_after_delete)} documents for 'apples' after deletion:")
        for i, doc in enumerate(retrieved_docs_after_delete):
            print(f"  Doc {i+1}: {doc.page_content[:50]}... (Metadata: {doc.metadata})")
            assert doc.metadata["source"] != "test_file_1.txt"

        # Clean up: delete the test collection or remaining documents
        print("\nCleaning up: Deleting all documents from test_collection...")
        manager.clear_all_documents()
        print("\nVectorStoreManager test finished.")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        print("Please ensure MONGO_URI and GOOGLE_API_KEY are set in your .env.example file in the backend directory.")
    except Exception as e:
        print(f"An error occurred during VectorStoreManager test: {e}")
