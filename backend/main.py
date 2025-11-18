import sys
import os

# Add the project root to the Python path
# This allows absolute imports from the 'backend' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field # Re-add BaseModel and Field
from typing import List, Dict, Any, Tuple
import asyncio
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Import the RAG chain constructor and data models
from backend.rag_pipeline import RAGPipeline
from backend.data_models import ChatRequest, ChatMessage, UserQuestion
from backend.api.v1.sync.payload import router as payload_sync_router
from backend.api.v1.questions import router as questions_router
from backend.dependencies import get_user_questions_collection
from bson import ObjectId
from fastapi.encoders import jsonable_encoder # Import jsonable_encoder
import json
import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# Import monitoring components
from backend.monitoring import (
    setup_logging,
    setup_metrics,
    MetricsMiddleware,
    get_health_status,
    get_liveness,
    get_readiness,
    generate_metrics_response,
)
from backend.monitoring.metrics import user_questions_total
from backend.monitoring.llm_observability import setup_langsmith
from backend.rate_limiter import RateLimitConfig, check_rate_limit

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO")
json_logging = os.getenv("JSON_LOGGING", "false").lower() == "true"
setup_logging(log_level=log_level, json_format=json_logging)
logger = logging.getLogger(__name__)

# Initialize metrics
setup_metrics()

# Setup LangSmith for LLM observability (optional)
langsmith_enabled = setup_langsmith()

async def update_question_metrics_from_db():
    """Update question metrics from MongoDB."""
    try:
        from backend.monitoring.metrics import user_questions_count_from_db
        collection = await get_user_questions_collection()
        
        # Get total count from MongoDB
        total_count = await collection.count_documents({})
        
        # Get counts by endpoint type
        chat_count = await collection.count_documents({"endpoint_type": "chat"})
        stream_count = await collection.count_documents({"endpoint_type": "stream"})
        
        # Update Gauge metrics
        user_questions_count_from_db.labels(endpoint_type="total").set(total_count)
        user_questions_count_from_db.labels(endpoint_type="chat").set(chat_count)
        user_questions_count_from_db.labels(endpoint_type="stream").set(stream_count)
        
    except Exception as e:
        logger.error(f"Error updating question metrics from DB: {e}", exc_info=True)

# Background task to periodically update metrics
async def update_metrics_periodically():
    """Periodically update metrics that need regular refreshing."""
    from backend.monitoring.health import _health_checker
    while True:
        try:
            # Update vector store metrics every 60 seconds
            _health_checker.check_vector_store()
            # Update question metrics from MongoDB every 60 seconds
            await update_question_metrics_from_db()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error updating metrics: {e}", exc_info=True)
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize question metrics from MongoDB
    await update_question_metrics_from_db()
    logger.info("Initialized question metrics from MongoDB")
    
    # Startup: Start background task for metrics updates
    metrics_task = asyncio.create_task(update_metrics_periodically())
    logger.info("Started background metrics update task")
    yield
    # Shutdown: Cancel the background task
    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        logger.info("Stopped background metrics update task")
    
    # Shutdown: Close all MongoDB connections to prevent connection leaks
    logger.info("Closing MongoDB connections...")
    try:
        # Close Motor client (from dependencies.py)
        from backend.dependencies import close_mongo_connection
        await close_mongo_connection()
    except Exception as e:
        logger.error(f"Error closing Motor MongoDB connection: {e}", exc_info=True)
    
    try:
        # Close shared VectorStoreManager MongoClient
        from backend.data_ingestion.vector_store_manager import close_shared_mongo_client
        close_shared_mongo_client()
    except Exception as e:
        logger.error(f"Error closing shared VectorStoreManager MongoDB client: {e}", exc_info=True)

    # Shutdown: Close Redis client
    try:
        from backend.redis_client import close_redis_client
        await close_redis_client()
    except Exception as e:
        logger.error(f"Error closing Redis client: {e}", exc_info=True)
    
    logger.info("MongoDB connection cleanup completed")

app = FastAPI(
    title="Litecoin Knowledge Hub API",
    description="AI-powered conversational tool for Litecoin information",
    version="1.0.0",
    lifespan=lifespan,
)

# Add custom JSON encoder for ObjectId
app.json_encoders = {
    ObjectId: str
}

# CORS configuration - supports both development and production
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [origin.strip() for origin in cors_origins_env.split(",")]

# Add monitoring middleware (before CORS to capture all requests)
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAGPipeline globally or as a dependency
# For simplicity, initializing globally for now. Consider dependency injection for better testability.
rag_pipeline_instance = RAGPipeline()

# Set global RAG pipeline instance for payload sync endpoints to avoid creating new connection pools
# This fixes the connection leak issue where each webhook created a new VectorStoreManager
try:
    from backend.api.v1.sync.payload import set_global_rag_pipeline
    set_global_rag_pipeline(rag_pipeline_instance)
except ImportError:
    logger.warning("Could not set global RAG pipeline for payload sync endpoints")

# Set global VectorStoreManager instance for health checker to avoid creating new connection pools
try:
    from backend.monitoring.health import set_global_vector_store_manager
    set_global_vector_store_manager(rag_pipeline_instance.vector_store_manager)
except (ImportError, AttributeError) as e:
    logger.warning(f"Could not set global VectorStoreManager for health checker: {e}")

# Include API routers
app.include_router(payload_sync_router, prefix="/api/v1/sync", tags=["Payload Sync"])
app.include_router(questions_router, prefix="/api/v1/questions", tags=["User Questions"])

class SourceDocument(BaseModel):
    page_content: str
    metadata: Dict[str, Any] = {} # Changed to default_factory=dict for consistency

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]

@app.get("/")
def read_root():
    return {
        "name": "Litecoin Knowledge Hub API",
        "version": "1.0.0",
        "status": "operational",
        "langsmith_enabled": langsmith_enabled,
    }

@app.get("/metrics")
async def metrics_endpoint(format: str = "prometheus"):
    """
    Prometheus metrics endpoint.
    
    Args:
        format: Output format - "prometheus" or "openmetrics"
    """
    metrics_bytes, content_type = generate_metrics_response(format=format)
    return Response(content=metrics_bytes, media_type=content_type)

@app.get("/health")
async def health_endpoint():
    """Comprehensive health check endpoint."""
    return get_health_status()

@app.get("/health/live")
async def liveness_endpoint():
    """Kubernetes liveness probe endpoint."""
    return get_liveness()

@app.get("/health/ready")
async def readiness_endpoint():
    """Kubernetes readiness probe endpoint."""
    return get_readiness()

@app.options("/api/v1/chat")
async def chat_options():
    """
    Handle CORS preflight requests for the chat endpoint.
    """
    return {"status": "ok"}

async def log_user_question(question: str, chat_history_length: int, endpoint_type: str):
    """
    Helper function to log user questions to MongoDB for later analysis.
    This runs asynchronously and won't block the main request.
    """
    try:
        collection = await get_user_questions_collection()
        user_question = UserQuestion(
            question=question,
            chat_history_length=chat_history_length,
            endpoint_type=endpoint_type
        )
        await collection.insert_one(user_question.model_dump())
        
        # Increment Prometheus metric
        user_questions_total.labels(endpoint_type=endpoint_type).inc()
        
        logger.info(f"Logged user question: {question[:50]}...")
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to log user question: {e}", exc_info=True)

CHAT_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    identifier="chat",
)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Endpoint to handle chat queries with conversational history.
    Processes the query through the RAG pipeline to get a generated response
    and the source documents used, taking into account previous messages.
    """
    # Rate limiting
    await check_rate_limit(http_request, CHAT_RATE_LIMIT)

    # Log the user question in the background
    background_tasks.add_task(
        log_user_question,
        question=request.query,
        chat_history_length=len(request.chat_history),
        endpoint_type="chat"
    )
    
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
            
    # Use the globally initialized RAG pipeline instance with async processing
    answer, sources = await rag_pipeline_instance.aquery(request.query, paired_chat_history)
    
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

STREAM_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    identifier="chat_stream",
)


@app.post("/api/v1/chat/stream")
async def chat_stream_endpoint(request: ChatRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Streaming endpoint for chat queries with real-time response delivery.
    Returns Server-Sent Events with incremental chunks of the response.
    """
    # Rate limiting
    await check_rate_limit(http_request, STREAM_RATE_LIMIT)

    # Log the user question in the background
    background_tasks.add_task(
        log_user_question,
        question=request.query,
        chat_history_length=len(request.chat_history),
        endpoint_type="stream"
    )

    # Convert ChatMessage list to the (human_message, ai_message) tuple format expected by RAGPipeline
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

    async def generate_stream():
        try:
            # Send initial status
            payload = {
                "status": "thinking",
                "chunk": "",
                "isComplete": False
            }
            yield f"data: {json.dumps(payload)}\n\n"

            # Get streaming response from RAG pipeline
            from_cache = False
            async for chunk_data in rag_pipeline_instance.astream_query(request.query, paired_chat_history):
                if chunk_data["type"] == "chunk":
                    # Use proper JSON encoding for the chunk content
                    payload = {
                        "status": "streaming",
                        "chunk": chunk_data['content'],
                        "isComplete": False
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                elif chunk_data["type"] == "sources":
                    # Send sources information
                    sources_json = jsonable_encoder([
                        SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
                        for doc in chunk_data["sources"]
                        if doc.metadata.get('status') == 'published'
                    ])
                    payload = {
                        "status": "sources",
                        "sources": sources_json,
                        "isComplete": False
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                elif chunk_data["type"] == "complete":
                    from_cache = chunk_data.get("from_cache", False)
                    payload = {
                        "status": "complete",
                        "chunk": "",
                        "isComplete": True,
                        "fromCache": from_cache
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            payload = {
                "status": "error",
                "error": str(e),
                "isComplete": True
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )
