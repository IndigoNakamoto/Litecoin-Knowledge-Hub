import sys
import os

# Add the project root to the Python path
# This allows absolute imports from the 'backend' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field # Re-add BaseModel and Field
from typing import List, Dict, Any, Tuple

# Load environment variables from .env file
load_dotenv()

# Import the RAG chain constructor and data models
from backend.rag_pipeline import RAGPipeline
from backend.data_models import ChatRequest, ChatMessage
from backend.api.v1.sources import router as sources_router
from backend.api.v1.sync.payload import router as payload_sync_router
from bson import ObjectId
from fastapi.encoders import jsonable_encoder # Import jsonable_encoder
import logging

from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set uvicorn loggers to INFO to see detailed request/response info
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

app = FastAPI()

# Add custom JSON encoder for ObjectId
app.json_encoders = {
    ObjectId: str
}

origins = [
    "http://localhost:3000",  # Allow requests from the frontend development server
]

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, # works with ["*"], but not with origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(sources_router, prefix="/api/v1/sources", tags=["Data Sources"])
app.include_router(payload_sync_router, prefix="/api/v1/sync", tags=["Payload Sync"])

# Initialize RAGPipeline globally or as a dependency
# For simplicity, initializing globally for now. Consider dependency injection for better testability.
rag_pipeline_instance = RAGPipeline()

class SourceDocument(BaseModel):
    page_content: str
    metadata: Dict[str, Any] = {} # Changed to default_factory=dict for consistency

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.options("/api/v1/chat")
async def chat_options():
    """
    Handle CORS preflight requests for the chat endpoint.
    """
    return {"status": "ok"}

@app.post("/api/v1/refresh-rag")
async def refresh_rag_pipeline():
    """
    Endpoint to manually refresh the RAG pipeline vector store.
    This is useful after adding new documents to ensure queries use the latest content.
    """
    try:
        rag_pipeline_instance.refresh_vector_store()
        return {"status": "success", "message": "RAG pipeline refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing RAG pipeline: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/clean-drafts")
async def clean_draft_documents():
    """
    Endpoint to manually clean draft/unpublished documents from the vector store.
    This removes any remaining draft content that might still be indexed.
    """
    try:
        if hasattr(rag_pipeline_instance, 'vector_store_manager'):
            deleted_count = rag_pipeline_instance.vector_store_manager.clean_draft_documents()
            # Refresh the RAG pipeline after cleanup
            rag_pipeline_instance.refresh_vector_store()
            return {
                "status": "success",
                "message": f"Cleaned up {deleted_count} draft documents and refreshed RAG pipeline",
                "documents_removed": deleted_count
            }
        else:
            return {"status": "error", "message": "Vector store manager not available"}
    except Exception as e:
        logger.error(f"Error cleaning draft documents: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to handle chat queries with conversational history.
    Processes the query through the RAG pipeline to get a generated response
    and the source documents used, taking into account previous messages.
    """
    # Convert ChatMessage list to the (human_message, ai_message) tuple format expected by RAGPipeline
    # The frontend now sends only complete exchanges, so we can simply pair consecutive human-AI messages

    paired_chat_history: List[Tuple[str, str]] = []
    i = 0
    while i < len(request.chat_history) - 1:  # Ensure we have pairs to process
        human_msg = request.chat_history[i]
        ai_msg = request.chat_history[i + 1]

        if human_msg.role == "human" and ai_msg.role == "ai":
            paired_chat_history.append((human_msg.content, ai_msg.content))
            i += 2
        else:
            # Skip malformed pairs and continue
            logger.warning(f"Skipping malformed chat history pair at index {i}")
            i += 1
            
    # Use the globally initialized RAG pipeline instance
    answer, sources = rag_pipeline_instance.query(request.query, paired_chat_history)
    
    # Transform Langchain Document objects to our Pydantic SourceDocument model
    # Additional filtering to ensure only published documents are returned (backup to RAG pipeline filtering)
    source_documents = [
        SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
        for doc in sources
        if doc.metadata.get('status') == 'published'
    ]
    
    return ChatResponse(
        answer=answer,
        sources=source_documents
    )
