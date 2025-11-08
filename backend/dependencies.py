import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Support both MONGO_DETAILS and MONGO_URI for flexibility
# MONGO_DETAILS is preferred, but fall back to MONGO_URI if not set
MONGO_DETAILS = os.getenv("MONGO_DETAILS") or os.getenv("MONGO_URI")
MONGO_DATABASE_NAME = os.getenv("MONGO_DATABASE_NAME", "litecoin_rag_db") # Default DB name
CMS_ARTICLES_COLLECTION_NAME = os.getenv("CMS_ARTICLES_COLLECTION_NAME", "cms_articles") # Default collection

# Global MongoDB client instance to avoid reconnecting on every request
# This should ideally be managed by the FastAPI app lifecycle (startup/shutdown events)
# For now, simple global client for the dependency.
mongo_client: AsyncIOMotorClient = None

async def get_mongo_client() -> AsyncIOMotorClient:
    global mongo_client
    if mongo_client is None:
        if not MONGO_DETAILS:
            raise ConnectionError("MONGO_DETAILS or MONGO_URI environment variable must be set.")
        try:
            print(f"Attempting to connect to MongoDB at: {MONGO_DETAILS}")
            mongo_client = AsyncIOMotorClient(MONGO_DETAILS)
            # Verify connection
            await mongo_client.admin.command('ping') 
            print("Successfully connected to MongoDB.")
        except ConnectionFailure as e:
            print(f"Failed to connect to MongoDB: {e}")
            mongo_client = None # Reset on failure
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
        except Exception as e: # Catch other potential errors during client creation
            print(f"An unexpected error occurred during MongoDB client initialization: {e}")
            mongo_client = None
            raise ConnectionError(f"An unexpected error occurred: {e}")
    return mongo_client

async def get_cms_db() -> AsyncIOMotorCollection:
    """
    Dependency function to get the MongoDB collection for CMS articles.
    """
    try:
        client = await get_mongo_client()
        if client is None:
            # This case should ideally be handled by get_mongo_client raising an error
            raise ConnectionError("MongoDB client is not available.")
        
        database = client[MONGO_DATABASE_NAME]
        cms_articles_collection = database[CMS_ARTICLES_COLLECTION_NAME]
        return cms_articles_collection
    except ConnectionError as e:
        # Re-raise connection errors to be handled by FastAPI or calling code
        raise e
    except Exception as e:
        # Catch any other unexpected errors during DB access
        print(f"Error accessing CMS DB collection: {e}")
        raise ConnectionError(f"Error accessing CMS DB collection: {e}")

USER_QUESTIONS_COLLECTION_NAME = os.getenv("USER_QUESTIONS_COLLECTION_NAME", "user_questions") # Default collection

async def get_user_questions_collection() -> AsyncIOMotorCollection:
    """
    Dependency function to get the MongoDB collection for logging user questions.
    """
    try:
        client = await get_mongo_client()
        if client is None:
            raise ConnectionError("MongoDB client is not available.")
        
        database = client[MONGO_DATABASE_NAME]
        user_questions_collection = database[USER_QUESTIONS_COLLECTION_NAME]
        return user_questions_collection
    except ConnectionError as e:
        raise e
    except Exception as e:
        print(f"Error accessing user questions collection: {e}")
        raise ConnectionError(f"Error accessing user questions collection: {e}")

# Example of how to close the client on app shutdown (if used with app events)
# async def close_mongo_connection():
#     global mongo_client
#     if mongo_client:
#         mongo_client.close()
#         print("MongoDB connection closed.")

# In main.py, you would add:
# app.add_event_handler("startup", get_mongo_client) # To initialize on startup
# app.add_event_handler("shutdown", close_mongo_connection)
