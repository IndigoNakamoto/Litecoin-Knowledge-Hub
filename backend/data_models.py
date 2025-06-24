# backend/data_models.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Literal, Optional, Dict, Any

class PayloadArticleMetadata(BaseModel):
    """
    Pydantic model for the metadata of a single document chunk derived from Payload CMS.
    """
    # Core Identifiers
    payload_id: str = Field(..., description="The Payload ID of the source article.")
    document_id: Optional[str] = Field(None, description="A unique ID for the document chunk.")
    source: str = Field("payload", description="The source of the content.")
    content_type: str = Field("article", description="The type of content.")

    # Content Classification
    chunk_type: Literal["title_summary", "section", "text"] = Field(..., description="The type of the content chunk.")
    chunk_index: int = Field(..., description="The index of the chunk within the article.")
    is_title_chunk: bool = Field(False, description="Indicates if this chunk represents the main title and summary.")
    doc_title: str = Field(..., description="The main title of the article (from Payload's 'title').")
    section_title: Optional[str] = Field(None, description="The title of the section this chunk belongs to.")
    subsection_title: Optional[str] = Field(None, description="The title of the subsection.")
    subsubsection_title: Optional[str] = Field(None, description="The title of the sub-subsection.")

    # Searchable Fields
    author: Optional[str] = Field(None, description="The author's name or ID.")
    categories: List[str] = Field([], description="A list of category names or IDs.")
    
    # Filtering & Sorting
    status: Literal["draft", "published"] = Field(..., description="The publication status.")
    published_date: Optional[datetime] = Field(None, description="The date the article was published.")
    locale: str = Field("en", description="The locale of the content.")
    content_length: int = Field(..., description="The character length of the content in this chunk.")

    # Technical
    slug: Optional[str] = Field(None, description="The URL slug for the article.")

class DataSource(BaseModel):
    """
    Pydantic model for a data source.
    """
    id: Optional[str] = None # MongoDB _id will be converted to string and assigned here
    name: str = Field(..., description="A human-readable name for the data source.")
    type: str = Field(..., description="The type of the data source (e.g., 'markdown', 'web', 'github', 'youtube', 'twitter', 'payload').")
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
                "type": "payload",
                "uri": "articles", # Represents the 'articles' collection slug in Payload
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

class PayloadWebhookDoc(BaseModel):
    """
    Represents the 'doc' object received from a Payload CMS 'afterChange' hook.
    This model validates the incoming webhook payload for an article.
    """
    id: str
    createdAt: datetime # Add createdAt
    updatedAt: datetime # Add updatedAt
    title: str
    author: Optional[str] = None # This will be the user ID
    publishedDate: Optional[str] = None # Payload sends date as a string, make it optional
    category: Optional[List[str]] = Field(None, description="List of category IDs") # Make optional and explicitly set default to None
    content: Dict[str, Any] # This is the Lexical JSON structure
    markdown: str # This is the auto-generated markdown from the hook in Payload
    status: Literal["draft", "published"]
    slug: Optional[str] = None # Make optional

    class Config:
        extra = "allow" # Allow any other fields from Payload
