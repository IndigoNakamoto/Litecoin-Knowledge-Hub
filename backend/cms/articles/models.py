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


class ArticleRead(ArticleBase):
    id: str = Field(..., alias="_id") # Map _id from MongoDB to id
    canonical_article_id: str
    version: int
    is_latest_active: bool
    created_at: datetime
    updated_at: datetime
    vetting_status: str
    # author_id is already in ArticleBase, no need to duplicate

    class Config:
        from_attributes = True # Renamed from orm_mode in Pydantic V2
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str # Ensure ObjectId is handled for JSON serialization
        }
        arbitrary_types_allowed = True # Allow custom types like ObjectId
