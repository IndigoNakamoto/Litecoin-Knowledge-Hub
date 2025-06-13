from pydantic import BaseModel
from typing import Literal, Optional

class SyncArticleData(BaseModel):
    id: str # The ID of the article in the CMS
    title: str
    slug: str
    tags: list[str]
    summary: Optional[str] = None
    content_markdown: str
    vetting_status: str # e.g., "vetted", "archived"
    # Add any other fields from ArticleRead that are necessary for the RAG ingestion pipeline
    # For example, if the RAG pipeline uses 'author' or 'created_at' for metadata.
    # For now, keeping it minimal to what's obviously needed for content and status.

class RAGSyncRequest(BaseModel):
    action: Literal["upsert", "delete"] # "upsert" for new/updated vetted articles, "delete" for archived
    article_data: SyncArticleData

class RAGSyncResponse(BaseModel):
    status: str
    message: str
    article_id: str
