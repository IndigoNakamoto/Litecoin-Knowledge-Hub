from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class DataSource(BaseModel):
    """
    Pydantic model for a data source.
    """
    id: Optional[str] = None # MongoDB _id will be converted to string and assigned here
    name: str = Field(..., description="A human-readable name for the data source.")
    type: str = Field(..., description="The type of the data source (e.g., 'markdown', 'web', 'github', 'youtube', 'twitter', 'strapi').")
    uri: str = Field(..., description="The URI or path to the data source (e.g., file path, URL, GitHub repo URL).")
    status: str = Field("active", description="The current status of the data source (e.g., 'active', 'inactive', 'ingesting', 'error').")
    last_ingested_at: Optional[datetime] = Field(None, description="Timestamp of the last successful ingestion.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the data source record was created.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the data source record was last updated.")

    class Config:
        # No populate_by_name needed as _id is explicitly handled in document_to_data_source
        json_schema_extra = {
            "example": {
                "name": "Litecoin Basics Articles",
                "type": "markdown",
                "uri": "knowledge_base/articles/",
                "status": "active"
            }
        }

class DataSourceUpdate(BaseModel):
    """
    Pydantic model for updating a data source. All fields are optional.
    """
    name: Optional[str] = Field(None, description="A human-readable name for the data source.")
    type: Optional[str] = Field(None, description="The type of the data source.")
    uri: Optional[str] = Field(None, description="The URI or path to the data source.")
    status: Optional[str] = Field(None, description="The current status of the data source.")
    last_ingested_at: Optional[datetime] = Field(None, description="Timestamp of the last successful ingestion.")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the data source record was last updated.")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Litecoin Articles",
                "status": "inactive"
            }
        }

class ChatMessage(BaseModel):
    """
    Pydantic model for a single chat message in the conversation history.
    """
    role: Literal["human", "ai"] = Field(..., description="The role of the sender, either 'human' or 'ai'.")
    content: str = Field(..., description="The content of the chat message.")

class ChatRequest(BaseModel):
    """
    Pydantic model for a chat request, including the current query and chat history.
    """
    query: str = Field(..., description="The user's current query.")
    chat_history: List[ChatMessage] = Field([], description="A list of previous chat messages in the conversation.")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is Litecoin?",
                "chat_history": [
                    {"role": "human", "content": "Hi, how are you?"},
                    {"role": "ai", "content": "I'm doing well, thank you! How can I help you with Litecoin today?"}
                ]
            }
        }


class StrapiArticleAttributes(BaseModel):
    """
    Pydantic model for the 'attributes' of a Strapi article entry.
    """
    title: str
    slug: str
    content: str
    author: Optional[str] = None
    tags: Optional[str] = None
    published_at: Optional[datetime] = Field(None, alias="publishedAt")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

class StrapiArticle(BaseModel):
    """
    Pydantic model for a complete Strapi article entry, including its ID and attributes.
    """
    id: int
    attributes: StrapiArticleAttributes


# Models for Strapi Webhook Payloads

class WebhookEntry(BaseModel):
    """
    Pydantic model for the 'entry' part of a Strapi webhook payload.
    This is intentionally flexible to accommodate different content types.
    """
    id: int
    # The rest of the fields are dynamic and will be handled as a dict
    # For a specific content type like 'article', you could create a more specific model
    # that inherits from this, e.g., WebhookArticleEntry(WebhookEntry, StrapiArticleAttributes)
    # But for a generic handler, this is sufficient.
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    published_at: Optional[datetime] = Field(None, alias="publishedAt")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class StrapiWebhookPayload(BaseModel):
    """
    Pydantic model for a Strapi webhook payload.
    """
    event: str = Field(..., description="The type of event (e.g., 'entry.publish', 'entry.unpublish').")
    model: str = Field(..., description="The content type of the entry (e.g., 'article').")
    entry: WebhookEntry = Field(..., description="The content entry that triggered the webhook.")
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "entry.publish",
                "createdAt": "2024-06-17T19:30:00.000Z",
                "model": "article",
                "entry": {
                    "id": 1,
                    "title": "What is Litecoin?",
                    "slug": "what-is-litecoin",
                    "content": "Litecoin is a peer-to-peer cryptocurrency...",
                    "author": "Charlie Lee",
                    "tags": "crypto, litecoin, beginner",
                    "publishedAt": "2024-06-17T19:30:00.000Z",
                    "createdAt": "2024-06-17T19:25:00.000Z",
                    "updatedAt": "2024-06-17T19:30:00.000Z"
                }
            }
        }
