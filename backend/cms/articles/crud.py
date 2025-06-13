import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
import datetime

from . import models
from langchain_google_genai import GoogleGenerativeAIEmbeddings # Added for semantic search
import httpx # Added for calling RAG sync webhook
from ..sync.models import RAGSyncRequest, SyncArticleData # Added for webhook payload

# Base URL for the RAG sync webhook (assuming it's running on the same host/port)
# In a production environment, this should come from config.
RAG_SYNC_WEBHOOK_URL = os.getenv("RAG_SYNC_WEBHOOK_URL", "http://localhost:8000/api/v1/sync/rag")


# Initialize embedding models (ensure GOOGLE_API_KEY is set in environment)
# Reason: query_embedding_model is for embedding search queries.
query_embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_query")
# Reason: document_embedding_model is for embedding article content for storage.
document_embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_document")

def article_helper(article: dict) -> dict:
    """Converts MongoDB document's _id (ObjectId) to a string and maps to 'id' field."""
    if "_id" in article and isinstance(article["_id"], ObjectId):
        article["id"] = str(article["_id"])  # Add this line for frontend compatibility
        article["_id"] = str(article["_id"])
    return article

# Retrieve MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set.")

client = AsyncIOMotorClient(MONGO_URI)
database = client.litecoin_rag_chat # Database name
articles_collection = database.get_collection("cms_articles") # Collection name

async def create_article(article_data: models.ArticleCreate) -> models.ArticleRead:
    """
    Creates a new article in the database.
    This is the first version of the article, so a new canonical_article_id is created.
    """
    article_dict = article_data.model_dump() # Use model_dump for Pydantic V2
    
    # Embed content_markdown for vector search
    # Reason: The content_embedding field will be used by the Atlas Vector Search index.
    if article_dict.get("content_markdown"):
        article_dict["content_embedding"] = document_embedding_model.embed_query(article_dict["content_markdown"])
    else:
        # Handle cases where content_markdown might be empty, though it's a required field in ArticleBase
        # Storing a None or an empty list might be options, or raising an error.
        # For now, let's assume content_markdown is always present and non-empty.
        # If it can be empty, the embedding model might raise an error or return a specific vector.
        # For simplicity, we'll proceed assuming it's valid.
        # If it's truly optional or can be empty, this logic needs refinement.
        pass # Or set article_dict["content_embedding"] = None / [] if schema allows

    # Set initial versioning and timestamps
    article_dict["version"] = 1
    article_dict["is_latest_active"] = True
    article_dict["created_at"] = datetime.datetime.utcnow()
    article_dict["updated_at"] = datetime.datetime.utcnow()
    article_dict["vetting_status"] = "draft" # All new articles start as drafts
    
    # Insert the article and get the MongoDB-generated _id
    result = await articles_collection.insert_one(article_dict)
    new_article_id = result.inserted_id
    
    # The canonical_article_id is the _id of the first version
    await articles_collection.update_one(
        {"_id": new_article_id}, {"$set": {"canonical_article_id": str(new_article_id)}} # Ensure canonical_article_id is string
    )
    
    # Retrieve the newly created article to return the full model
    created_article = await articles_collection.find_one({"_id": new_article_id})
    # Apply article_helper to convert ObjectId to string id before validation
    return models.ArticleRead.model_validate(article_helper(created_article))

async def get_articles() -> List[models.ArticleRead]:
    """Retrieves all articles from the database."""
    articles = []
    async for article in articles_collection.find():
        articles.append(article_helper(article))
    return articles

async def get_article(article_id: str) -> Optional[models.ArticleRead]:
    """Retrieves a single article by its ID."""
    if not ObjectId.is_valid(article_id):
        return None
    article = await articles_collection.find_one({"_id": ObjectId(article_id)})
    if article:
        return article_helper(article)
    return None

async def update_article(article_id: str, article_data: models.ArticleUpdate) -> Optional[models.ArticleRead]:
    """
    Updates an existing article.
    In a real versioning system, this would create a new version.
    For this simplified CRUD, we'll just update the existing document.
    """
    if not ObjectId.is_valid(article_id):
        return None

    # Retrieve the current state of the article before updating
    # Reason: To compare old and new vetting_status for webhook trigger.
    current_article_doc = await articles_collection.find_one({"_id": ObjectId(article_id)})
    if not current_article_doc:
        return None # Article not found
    
    current_vetting_status = current_article_doc.get("vetting_status")

    update_data = article_data.model_dump(exclude_unset=True) # Use model_dump for Pydantic V2
    update_data["updated_at"] = datetime.datetime.utcnow()

    # If content_markdown is being updated, re-embed it
    # Reason: Ensures the search index has the latest content embedding.
    if "content_markdown" in update_data and update_data["content_markdown"]:
        update_data["content_embedding"] = document_embedding_model.embed_query(update_data["content_markdown"])
    elif "content_markdown" in update_data and not update_data["content_markdown"]:
        # Handle case where content_markdown is explicitly set to empty
        # Depending on requirements, could set embedding to None, empty list, or remove the field.
        # For now, if it's emptied, we might want to remove the embedding or set to a null-like vector.
        # This example will set it to None, assuming the DB schema/index can handle it.
        update_data["content_embedding"] = None # Or handle as per specific requirements

    await articles_collection.update_one(
        {"_id": ObjectId(article_id)}, {"$set": update_data}
    )
    
    updated_article_doc = await articles_collection.find_one({"_id": ObjectId(article_id)})
    if not updated_article_doc:
        return None

    new_vetting_status = updated_article_doc.get("vetting_status")

    # Trigger RAG sync webhook if vetting_status changes significantly
    # Reason: Keeps the RAG pipeline synchronized with vetted/archived CMS content.
    webhook_action: Optional[str] = None
    if new_vetting_status == "vetted" and current_vetting_status != "vetted":
        webhook_action = "upsert"
    elif new_vetting_status == "vetted" and current_vetting_status == "vetted": # Content of a vetted article updated
        webhook_action = "upsert"
    elif new_vetting_status == "archived" and current_vetting_status == "vetted": # Vetted article archived
         webhook_action = "delete"
    # Add more conditions if other status changes trigger RAG sync (e.g., un-vetting)

    if webhook_action:
        try:
            # Prepare payload for the webhook
            sync_data = SyncArticleData(
                id=str(updated_article_doc["_id"]),
                title=updated_article_doc["title"],
                slug=updated_article_doc["slug"],
                tags=updated_article_doc.get("tags", []),
                summary=updated_article_doc.get("summary"),
                content_markdown=updated_article_doc["content_markdown"],
                vetting_status=new_vetting_status
                # Ensure all fields required by SyncArticleData are present
            )
            rag_sync_payload = RAGSyncRequest(action=webhook_action, article_data=sync_data)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(RAG_SYNC_WEBHOOK_URL, json=rag_sync_payload.model_dump())
                response.raise_for_status() # Raise an exception for bad status codes
                print(f"RAG Sync webhook called successfully for article {updated_article_doc['_id']}: {response.json()}")
        except httpx.HTTPStatusError as e:
            print(f"Error calling RAG Sync webhook for article {updated_article_doc['_id']}: {e.response.status_code} - {e.response.text}")
            # Decide on error handling: proceed with CMS update? Log and alert?
        except Exception as e:
            print(f"An unexpected error occurred calling RAG Sync webhook for article {updated_article_doc['_id']}: {e}")


    return models.ArticleRead.model_validate(article_helper(updated_article_doc))

async def delete_article(article_id: str) -> bool:
    """Deletes an article from the database."""
    if not ObjectId.is_valid(article_id):
        return False
    result = await articles_collection.delete_one({"_id": ObjectId(article_id)})
    return result.deleted_count > 0

async def search_articles(query_text: str, top_k: int = 5) -> List[models.ArticleRead]:
    """
    Performs semantic search for articles based on the query_text.
    """
    # Reason: Embed the search query using the specified Google model and task type.
    query_embedding = query_embedding_model.embed_query(query_text)

    # Reason: Define the MongoDB Atlas Vector Search aggregation pipeline.
    # This assumes a vector search index named 'cms_content_search_index'
    # exists on the 'cms_articles' collection, targeting a field 'content_embedding'.
    vector_search_pipeline = [
        {
            "$vectorSearch": {
                "index": "cms_content_search_index", # Assumed index name
                "path": "content_embedding",       # Assumed field with article embeddings
                "queryVector": query_embedding,
                "numCandidates": top_k * 10,        # Number of candidates to consider
                "limit": top_k                      # Number of results to return
            }
        },
        {
            "$project": { # Optionally project fields to match ArticleRead, or handle in Pydantic
                "_id": 1,
                "title": 1,
                "slug": 1,
                "author_id": 1,
                "tags": 1,
                "summary": 1,
                "content_markdown": 1, # May not be needed for search results display, but ArticleRead requires it
                "canonical_article_id": 1,
                "version": 1,
                "is_latest_active": 1,
                "created_at": 1,
                "updated_at": 1,
                "vetting_status": 1,
                "score": {"$meta": "vectorSearchScore"} # Include search score if needed
            }
        }
    ]

    articles_cursor = articles_collection.aggregate(vector_search_pipeline)
    search_results = []
    async for article_doc in articles_cursor:
        # Reason: Convert MongoDB document to ArticleRead Pydantic model.
        # The article_helper ensures _id is converted to a string.
        # Pydantic's model_validate will map the fields.
        try:
            # Ensure all required fields for ArticleRead are present or provide defaults
            # The $project stage helps ensure fields are available.
            # If 'score' is not part of ArticleRead, it will be ignored by model_validate.
            validated_article = models.ArticleRead.model_validate(article_helper(article_doc))
            search_results.append(validated_article)
        except Exception as e:
            # Handle or log validation errors if necessary
            print(f"Error validating article {article_doc.get('_id')}: {e}") # Basic logging
            continue # Skip articles that fail validation

    return search_results
