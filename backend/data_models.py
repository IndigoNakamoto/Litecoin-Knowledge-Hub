from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class DataSource(BaseModel):
    """
    Pydantic model for a data source.
    """
    id: Optional[str] = None # MongoDB _id will be converted to string and assigned here
    name: str = Field(..., description="A human-readable name for the data source.")
    type: str = Field(..., description="The type of the data source (e.g., 'markdown', 'web', 'github', 'youtube', 'twitter').")
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
