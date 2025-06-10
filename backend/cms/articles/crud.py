import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
import datetime

from . import models

def article_helper(article: dict) -> dict:
    """Converts MongoDB document's _id (ObjectId) to a string."""
    if "_id" in article and isinstance(article["_id"], ObjectId):
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
        
    update_data = article_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.datetime.utcnow()

    await articles_collection.update_one(
        {"_id": ObjectId(article_id)}, {"$set": update_data}
    )
    
    updated_article = await articles_collection.find_one({"_id": ObjectId(article_id)})
    if updated_article:
        return article_helper(updated_article)
    return None

async def delete_article(article_id: str) -> bool:
    """Deletes an article from the database."""
    if not ObjectId.is_valid(article_id):
        return False
    result = await articles_collection.delete_one({"_id": ObjectId(article_id)})
    return result.deleted_count > 0
