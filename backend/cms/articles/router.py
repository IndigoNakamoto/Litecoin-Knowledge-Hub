from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from . import models, crud
from ..auth.router import get_current_active_user
from ..users.models import User

router = APIRouter(
    prefix="/api/v1/articles",
    tags=["CMS Articles"],
)

@router.post("/", response_model=models.ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article_endpoint(article: models.ArticleCreate, current_user: User = Depends(get_current_active_user)):
    """
    Create a new article.
    """
    # Add author_id from the current authenticated user
    article.author_id = str(current_user.id) # Assign directly to the Pydantic model
    
    return await crud.create_article(article_data=article)

@router.get("/", response_model=List[models.ArticleRead])
async def get_articles_endpoint():
    """
    Retrieve all articles.
    """
    return await crud.get_articles()

@router.get("/{article_id}", response_model=models.ArticleRead)
async def get_article_endpoint(article_id: str):
    """
    Retrieve a single article by its ID.
    """
    db_article = await crud.get_article(article_id)
    if db_article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return db_article

@router.put("/{article_id}", response_model=models.ArticleRead)
async def update_article_endpoint(article_id: str, article: models.ArticleUpdate, current_user: User = Depends(get_current_active_user)):
    """
    Update an existing article.
    """
    updated_article = await crud.update_article(article_id, article)
    if updated_article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return updated_article

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article_endpoint(article_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Delete an article.
    """
    deleted = await crud.delete_article(article_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return
