# Updated router.py to match CRUD function signatures

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from motor.motor_asyncio import AsyncIOMotorCollection

from . import models, crud
from ..auth.router import get_current_active_user
from ..users.models import User
from backend.dependencies import get_cms_db

router = APIRouter(
    prefix="/api/v1/articles",
    tags=["CMS Articles"],
)

@router.post("/", response_model=models.ArticleRead, status_code=status.HTTP_201_CREATED, response_model_by_alias=True)
async def create_article_endpoint(
    article: models.ArticleCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new article.
    """
    # Add author_id from the current authenticated user if not set
    if not hasattr(article, 'author_id') or article.author_id is None:
        if hasattr(article, 'author_id'):
            article.author_id = str(current_user.id)
    
    # FIXED: Match CRUD function signature
    return await crud.create_article(article_data=article)

@router.get("/", response_model=List[models.ArticleRead], response_model_by_alias=True)
async def get_articles_endpoint(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)  # Add this line
):
    """
    Retrieve all articles.
    """
    # FIXED: CRUD function doesn't take db, skip, limit parameters
    return await crud.get_articles()

@router.get("/{article_id}", response_model=models.ArticleRead, response_model_by_alias=True)
async def get_article_endpoint(
    article_id: str
):
    """
    Retrieve a single article by its ID.
    """
    # FIXED: Match CRUD function signature
    db_article = await crud.get_article(article_id=article_id)
    if db_article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return db_article

@router.put("/{article_id}", response_model=models.ArticleRead, response_model_by_alias=True)
async def update_article_endpoint(
    article_id: str,
    article: models.ArticleUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing article.
    """
    # FIXED: Match CRUD function signature
    updated_article = await crud.update_article(article_id=article_id, article_data=article)
    if updated_article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return updated_article

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article_endpoint(
    article_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an article.
    """
    # FIXED: Match CRUD function signature
    deleted = await crud.delete_article(article_id=article_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return

@router.get("/search/", response_model=List[models.ArticleRead], response_model_by_alias=True)
async def search_articles_endpoint(
    query: str = Query(..., min_length=3, description="Search query for articles"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for articles within the CMS based on a query string.
    Utilizes vector embeddings for semantic search.
    """
    if not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search query cannot be empty.")
    
    try:
        # FIXED: Match CRUD function signature
        search_results = await crud.search_articles(query_text=query, top_k=limit)
        
        if not search_results:
            return []
        return search_results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during article search: {str(e)}")