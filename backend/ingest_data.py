import os
from dotenv import load_dotenv
from data_ingestion.litecoin_docs_loader import load_litecoin_docs
from data_ingestion.embedding_processor import process_and_embed_documents
from data_ingestion.vector_store_manager import insert_documents_to_vector_store

def main():
    """
    Main function to run the data ingestion pipeline.
    """
    # Reason: Loading environment variables from .env file to get
    # access to MONGO_URI and GOOGLE_API_KEY.
    load_dotenv()

    # Configuration
    file_path = "backend/data_ingestion/sample_litecoin_docs.md"
    collection_name = "litecoin_docs"
    db_name = "litecoin_rag_db"

    print("Starting data ingestion pipeline...")

    # Step 1: Load data from the source file
    print(f"Loading documents from {file_path}...")
    documents = load_litecoin_docs(file_path)
    print(f"Loaded {len(documents)} document(s).")

    # Step 2: Split documents into chunks
    print("Splitting documents into smaller chunks...")
    processed_docs = process_and_embed_documents(documents)
    print(f"Split documents into {len(processed_docs)} chunks.")

    # Step 3: Insert documents into the vector store
    print(f"Inserting documents into MongoDB collection '{collection_name}' in db '{db_name}'...")
    insert_documents_to_vector_store(processed_docs, collection_name)
    print("Data ingestion pipeline completed successfully.")

if __name__ == "__main__":
    main()
