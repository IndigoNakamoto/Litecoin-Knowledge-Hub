import os
from typing import List
from pymongo import MongoClient
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch

def get_vector_store(collection_name: str, db_name: str = "litecoin_rag_db"):
    """
    Initializes and returns the MongoDB Atlas Vector Search instance.

    Args:
        collection_name: The name of the collection to use.
        db_name: The name of the database to use.

    Returns:
        An instance of MongoDBAtlasVectorSearch.
    """
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable not set.")

    client = MongoClient(mongo_uri)
    collection = client[db_name][collection_name]

    # Reason: Initializing the Google Generative AI Embeddings model.
    # This is the same model used in the embedding processor and is required
    # by the vector store to create embeddings for queries.
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-004")

    # Reason: Using MongoDBAtlasVectorSearch to interact with the vector store.
    # This class handles the logic of creating and querying vector embeddings
    # within MongoDB Atlas.
    vector_store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
    )
    return vector_store

def insert_documents_to_vector_store(docs: List[Document], collection_name: str):
    """
    Inserts documents into the specified vector store collection.

    Args:
        docs: A list of documents to insert.
        collection_name: The name of the collection to insert into.
    """
    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(docs)
    print(f"Successfully inserted {len(docs)} documents into collection '{collection_name}'.")

if __name__ == '__main__':
    from dotenv import load_dotenv
    from litecoin_docs_loader import load_litecoin_docs
    from embedding_processor import process_and_embed_documents

    load_dotenv()

    # Example usage:
    file_path = "backend/data_ingestion/sample_litecoin_docs.md"
    collection_name = "litecoin_docs"
    
    documents = load_litecoin_docs(file_path)
    processed_docs = process_and_embed_documents(documents)
    insert_documents_to_vector_store(processed_docs, collection_name)
