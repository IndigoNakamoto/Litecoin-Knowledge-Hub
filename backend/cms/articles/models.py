from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ArticleBase(BaseModel):
    title: str
    slug: str
    author_id: str # Assuming author_id is a string for now
    tags: List[str] = []
    category: str
    summary: Optional[str] = None
    tiptap_content_json: dict
    word_count: Optional[int] = None
    linked_assets: List[dict] = []
    custom_fields: Optional[dict] = None

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    author_id: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    tiptap_content_json: Optional[dict] = None
    word_count: Optional[int] = None
    linked_assets: Optional[List[dict]] = None
    custom_fields: Optional[dict] = None
    vetting_status: Optional[str] = None


class ArticleRead(ArticleBase):
    id: str = Field(..., alias="_id")
    canonical_article_id: str
    version: int
    is_latest_active: bool
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    vetting_status: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            # ObjectId needs a custom encoder if we use it
        }
