from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId # Added for json_encoders

class ArticleBase(BaseModel):
    title: str
    slug: str
    author_id: Optional[str] = None # Made optional for frontend and backend
    tags: List[str] = []
    summary: Optional[str] = None
    content_markdown: str
    content_embedding: Optional[List[float]] = None # Added for storing embeddings

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    author_id: Optional[str] = None
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    content_markdown: Optional[str] = None
    vetting_status: Optional[str] = None
    content_embedding: Optional[List[float]] = None # Added for updating embeddings if necessary
    # vetting_status is now in ArticleUpdate


class ArticleDB(ArticleBase): # Renamed from ArticleRead to ArticleDB
    id: str = Field(..., alias="_id") # Map _id from MongoDB to id
    canonical_article_id: Optional[str] = None # Made optional, might not exist for brand new CMS articles
    content_embedding: Optional[List[float]] = None # Added field
    version: Optional[int] = None # Made optional
    is_latest_active: Optional[bool] = None # Made optional
    created_at: datetime
    updated_at: datetime
    vetting_status: str
    published_at: Optional[datetime] = None # Added field
    # author_id is already in ArticleBase, no need to duplicate

    class Config:
        from_attributes = True # Renamed from orm_mode in Pydantic V2
        populate_by_name = True # Allow populating by attribute name and alias
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None, # Handle None datetimes
            ObjectId: str # Ensure ObjectId is handled for JSON serialization
        }
        arbitrary_types_allowed = True # Allow custom types like ObjectId


class ArticleRead(ArticleDB): # ArticleRead can inherit from ArticleDB for API responses
    pass


class ArticleSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5 # Default to returning top 5 results


class ArticleSearchResponse(BaseModel):
    results: List[ArticleRead]
