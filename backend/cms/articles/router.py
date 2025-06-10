from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from . import models

router = APIRouter(
    prefix="/api/v1/articles",
    tags=["CMS Articles"],
)

# In-memory "database" for now
fake_articles_db = {}

@router.post("/", response_model=models.ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(article: models.ArticleCreate):
    # In a real app, this would be an async call to the database
    # For now, we'll simulate it.
    # This is a simplified placeholder and does not reflect the final data model
    article_id = str(len(fake_articles_db) + 1)
    article_data = article.dict()
    
    # Simulate the full ArticleRead model
    full_article_data = {
        "_id": article_id,
        "canonical_article_id": article_id, # Simplified for now
        "version": 1,
        "is_latest_active": True,
        "created_at": "2025-06-09T20:09:42Z", # Placeholder
        "updated_at": "2025-06-09T20:09:42Z", # Placeholder
        "vetting_status": "draft",
        **article_data
    }
    
    fake_articles_db[article_id] = full_article_data
    return full_article_data

@router.get("/", response_model=List[models.ArticleRead])
async def get_articles():
    return list(fake_articles_db.values())

@router.get("/{article_id}", response_model=models.ArticleRead)
async def get_article(article_id: str):
    if article_id not in fake_articles_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return fake_articles_db[article_id]

@router.put("/{article_id}", response_model=models.ArticleRead)
async def update_article(article_id: str, article: models.ArticleUpdate):
    if article_id not in fake_articles_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    stored_article_data = fake_articles_db[article_id]
    update_data = article.dict(exclude_unset=True)
    
    updated_article = stored_article_data.copy()
    updated_article.update(update_data)
    updated_article["updated_at"] = "2025-06-09T20:09:42Z" # Placeholder
    
    fake_articles_db[article_id] = updated_article
    return updated_article

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: str):
    if article_id not in fake_articles_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    del fake_articles_db[article_id]
    return
