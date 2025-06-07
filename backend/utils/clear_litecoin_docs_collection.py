import os
import sys
from dotenv import load_dotenv

# Add the parent directory (backend) to sys.path to allow imports from data_ingestion
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.vector_store_manager import VectorStoreManager

def clear_collection():
    """
    Initializes VectorStoreManager and clears all documents
    from the 'litecoin_docs' collection.
    """
    # Determine the path to the .env file. Assumes .env is in the 'backend' directory.
    # If this script is in backend/utils/, then backend/ is one level up from this script's dir.
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    # Load environment variables from .env file if it exists
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded environment variables from: {dotenv_path}")
    else:
        # Fallback to .env.example if .env is not found
        dotenv_example_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.example')
        if os.path.exists(dotenv_example_path):
            load_dotenv(dotenv_path=dotenv_example_path)
            print(f"Loaded environment variables from: {dotenv_example_path} (as .env was not found)")
        else:
            print("Warning: Neither .env nor .env.example found in the backend directory. Critical environment variables might be missing.")

    try:
        print("Initializing VectorStoreManager to clear 'litecoin_docs' collection...")
        # VectorStoreManager defaults to 'litecoin_rag_db' and 'litecoin_docs'
        manager = VectorStoreManager() 
        
        deleted_count = manager.clear_all_documents()
        
        print(f"\nSuccessfully cleared the '{manager.collection_name}' collection in database '{manager.db_name}'.")
        print(f"Number of documents deleted: {deleted_count}")
        
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        print("Please ensure MONGO_URI and GOOGLE_API_KEY are set in your .env or .env.example file in the backend directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Prompt the user for confirmation before proceeding
    confirm = input("Are you sure you want to delete ALL documents from the 'litecoin_docs' collection? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_collection()
    else:
        print("Operation cancelled by the user.")
