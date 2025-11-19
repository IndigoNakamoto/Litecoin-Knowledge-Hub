import sys
import os

# Add the project root to the Python path
# This allows absolute imports from the 'backend' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError # Re-add BaseModel and Field
from typing import List, Dict, Any, Tuple
import asyncio
import time
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Import the RAG chain constructor and data models
from backend.rag_pipeline import RAGPipeline
from backend.data_models import ChatRequest, ChatMessage, UserQuestion
from backend.api.v1.sync.payload import router as payload_sync_router
from backend.api.v1.admin.usage import router as admin_router
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
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.monitoring.metrics import user_questions_total
from backend.monitoring.llm_observability import setup_langsmith
from backend.rate_limiter import RateLimitConfig, check_rate_limit

# Rate limit configurations for health and metrics endpoints
# Health endpoint rate limits (higher than API endpoints, but still protected)
HEALTH_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=60,
    requests_per_hour=1000,
    identifier="health",
    enable_progressive_limits=False,  # Don't ban health checks aggressively
)

# Metrics endpoint rate limits (Prometheus scrapes every 15s = 4/min, so 30/min is safe)
METRICS_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=30,
    requests_per_hour=500,
    identifier="metrics",
    enable_progressive_limits=True,  # Can be more strict for metrics
)

# Liveness/readiness rate limits (very high for Kubernetes probes)
PROBE_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=120,
    requests_per_hour=2000,
    identifier="probe",
    enable_progressive_limits=False,
)

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
    from backend.monitoring.spend_limit import get_current_usage
    from backend.monitoring.metrics import (
        llm_daily_cost_usd,
        llm_hourly_cost_usd,
        llm_daily_limit_usd,
        llm_hourly_limit_usd,
    )
    from backend.monitoring.discord_alerts import send_spend_limit_alert
    from backend.redis_client import get_redis_client
    import os
    
    # Get spend limits from environment
    daily_limit = float(os.getenv("DAILY_SPEND_LIMIT_USD", "5.00"))
    hourly_limit = float(os.getenv("HOURLY_SPEND_LIMIT_USD", "1.00"))
    
    while True:
        try:
            # Update vector store metrics every 60 seconds
            _health_checker.check_vector_store()
            # Update question metrics from MongoDB every 60 seconds
            await update_question_metrics_from_db()
            
            # Update spend limit metrics every 30 seconds
            try:
                usage_info = await get_current_usage()
                
                # Update Prometheus gauges
                llm_daily_cost_usd.set(usage_info["daily"]["cost_usd"])
                llm_hourly_cost_usd.set(usage_info["hourly"]["cost_usd"])
                llm_daily_limit_usd.set(daily_limit)
                llm_hourly_limit_usd.set(hourly_limit)
                
                # Check thresholds and send Discord alerts
                redis_client = get_redis_client()
                
                # Check daily limit
                daily_cost = usage_info["daily"]["cost_usd"]
                daily_percentage = usage_info["daily"]["percentage_used"]
                
                # 80% warning threshold
                if daily_percentage >= 80:
                    alert_key_80 = "llm:alert:daily:80"
                    alert_sent = await redis_client.get(alert_key_80)
                    if not alert_sent:
                        # Send warning alert
                        await send_spend_limit_alert(
                            "daily",
                            daily_cost,
                            daily_limit,
                            daily_percentage,
                            is_exceeded=False
                        )
                        # Mark alert as sent (expire after 1 hour)
                        await redis_client.setex(alert_key_80, 3600, "1")
                
                # 100% critical threshold
                if daily_percentage >= 100:
                    alert_key_100 = "llm:alert:daily:100"
                    alert_sent = await redis_client.get(alert_key_100)
                    if not alert_sent:
                        # Send critical alert
                        await send_spend_limit_alert(
                            "daily",
                            daily_cost,
                            daily_limit,
                            daily_percentage,
                            is_exceeded=True
                        )
                        # Mark alert as sent (expire after 1 hour)
                        await redis_client.setex(alert_key_100, 3600, "1")
                
                # Check hourly limit
                hourly_cost = usage_info["hourly"]["cost_usd"]
                hourly_percentage = usage_info["hourly"]["percentage_used"]
                
                # 80% warning threshold
                if hourly_percentage >= 80:
                    alert_key_80 = "llm:alert:hourly:80"
                    alert_sent = await redis_client.get(alert_key_80)
                    if not alert_sent:
                        # Send warning alert
                        await send_spend_limit_alert(
                            "hourly",
                            hourly_cost,
                            hourly_limit,
                            hourly_percentage,
                            is_exceeded=False
                        )
                        # Mark alert as sent (expire after 1 hour)
                        await redis_client.setex(alert_key_80, 3600, "1")
                
                # 100% critical threshold
                if hourly_percentage >= 100:
                    alert_key_100 = "llm:alert:hourly:100"
                    alert_sent = await redis_client.get(alert_key_100)
                    if not alert_sent:
                        # Send critical alert
                        await send_spend_limit_alert(
                            "hourly",
                            hourly_cost,
                            hourly_limit,
                            hourly_percentage,
                            is_exceeded=True
                        )
                        # Mark alert as sent (expire after 1 hour)
                        await redis_client.setex(alert_key_100, 3600, "1")
                
            except Exception as e:
                logger.error(f"Error updating spend limit metrics: {e}", exc_info=True)
            
            await asyncio.sleep(30)  # Run every 30 seconds for spend limit monitoring
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
    
    # Startup: Refresh suggested question cache in background (non-blocking)
    async def refresh_cache_background():
        try:
            logger.info("Starting background suggested question cache refresh...")
            result = await refresh_suggested_question_cache()
            logger.info(f"Background cache refresh completed: {result}")
        except Exception as e:
            logger.error(f"Error in background cache refresh: {e}", exc_info=True)
    
    cache_refresh_task = asyncio.create_task(refresh_cache_background())
    logger.info("Started background suggested question cache refresh task")
    
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

# Add security headers middleware (after metrics, before CORS)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,  # From CORS_ORIGINS env var
    allow_credentials=True,  # Keep for future cookie-based auth
    allow_methods=["GET", "POST", "OPTIONS"],  # Only required methods
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],  # Only required headers
)

# Global exception handlers for error sanitization
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors with sanitized responses."""
    logger.error(f"Request validation error: {exc.errors()}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "message": "Invalid request data. Please check your input and try again."}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with sanitized responses."""
    logger.error(f"Validation error: {exc.errors()}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "message": "Invalid request data. Please check your input and try again."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions - ensure detail is properly formatted and sanitized."""
    # If detail is already a dict with sanitized message, use it
    if isinstance(exc.detail, dict):
        # Check if it contains internal error details that need sanitization
        detail = exc.detail.copy()
        if "message" in detail and isinstance(detail["message"], str):
            # Check if message contains internal details (file paths, stack traces, etc.)
            if any(indicator in detail["message"] for indicator in ["/", "\\", "Traceback", "File", "line"]):
                detail["message"] = "An error occurred while processing your request. Please try again."
        return JSONResponse(status_code=exc.status_code, content=detail)
    # If detail is a string, wrap it in a sanitized format
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Request failed", "message": "An error occurred while processing your request. Please try again."}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An error occurred while processing your request. Please try again."}
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
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])

# Import cache utilities and suggested questions utility
from backend.cache_utils import suggested_question_cache
from backend.utils.suggested_questions import fetch_suggested_questions
from backend.monitoring.metrics import (
    suggested_question_cache_refresh_duration_seconds,
    suggested_question_cache_refresh_errors_total,
    suggested_question_cache_size,
    suggested_question_cache_hits_total,
    suggested_question_cache_misses_total,
    suggested_question_cache_lookup_duration_seconds,
)

async def refresh_suggested_question_cache():
    """
    Refresh the suggested question cache by pre-generating responses for all active questions.
    This function fetches active questions from Payload CMS and generates responses via RAG pipeline.
    """
    start_time = time.time()
    cached_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        logger.info("Starting suggested question cache refresh...")
        
        # Fetch active questions from Payload CMS
        questions = await fetch_suggested_questions(active_only=True)
        total_questions = len(questions)
        
        if total_questions == 0:
            logger.warning("No active suggested questions found in Payload CMS")
            return {
                "status": "success",
                "cached": 0,
                "skipped": 0,
                "errors": 0,
                "total": 0,
                "duration_seconds": time.time() - start_time
            }
        
        logger.info(f"Fetched {total_questions} active suggested questions from Payload CMS")
        
        # Process each question
        for question_data in questions:
            question_text = question_data.get("question", "").strip()
            if not question_text:
                logger.warning(f"Skipping question with empty text (ID: {question_data.get('id', 'unknown')})")
                skipped_count += 1
                continue
            
            try:
                # Check if already cached
                is_cached = await suggested_question_cache.is_cached(question_text)
                if is_cached:
                    logger.debug(f"Question already cached, skipping: {question_text[:50]}...")
                    skipped_count += 1
                    continue
                
                # Generate response via RAG pipeline (empty chat history for suggested questions)
                logger.info(f"Generating response for question: {question_text[:50]}...")
                answer, sources = await rag_pipeline_instance.aquery(question_text, [])
                
                # Store in Suggested Question Cache
                await suggested_question_cache.set(question_text, answer, sources)
                cached_count += 1
                logger.debug(f"Cached response for question: {question_text[:50]}...")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing question '{question_text[:50]}...': {e}", exc_info=True)
                suggested_question_cache_refresh_errors_total.inc()
        
        # Update cache size metric
        cache_size = await suggested_question_cache.get_cache_size()
        suggested_question_cache_size.set(cache_size)
        
        duration = time.time() - start_time
        suggested_question_cache_refresh_duration_seconds.observe(duration)
        
        logger.info(
            f"Suggested question cache refresh complete. "
            f"Cached: {cached_count}, Skipped: {skipped_count}, Errors: {error_count}, Total: {total_questions}, "
            f"Duration: {duration:.2f}s"
        )
        
        return {
            "status": "success",
            "cached": cached_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total": total_questions,
            "duration_seconds": duration
        }
        
    except Exception as e:
        error_count += 1
        duration = time.time() - start_time
        logger.error(f"Error during suggested question cache refresh: {e}", exc_info=True)
        suggested_question_cache_refresh_errors_total.inc()
        suggested_question_cache_refresh_duration_seconds.observe(duration)
        
        return {
            "status": "error",
            "cached": cached_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total": 0,
            "duration_seconds": duration,
            "error": str(e)
        }

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
async def metrics_endpoint(request: Request, format: str = "prometheus"):
    """
    Prometheus metrics endpoint.
    Rate limited but allows Prometheus scraping (scrapes every 15s = 4/min).
    30/min limit is safe for Prometheus while preventing abuse.
    
    Args:
        request: FastAPI request object (for rate limiting)
        format: Output format - "prometheus" or "openmetrics"
    """
    await check_rate_limit(request, METRICS_RATE_LIMIT)
    metrics_bytes, content_type = generate_metrics_response(format=format)
    return Response(content=metrics_bytes, media_type=content_type)

@app.get("/health")
async def health_endpoint(request: Request):
    """
    Public health check endpoint (sanitized).
    Returns minimal information suitable for public access.
    """
    await check_rate_limit(request, HEALTH_RATE_LIMIT)
    from backend.monitoring.health import _get_health_checker
    return _get_health_checker().get_public_health()

@app.get("/health/detailed")
async def detailed_health_endpoint(request: Request):
    """
    Detailed health check for internal monitoring (Grafana, etc.).
    Returns full health information including document counts and cache stats.
    Rate limited but with higher limits for monitoring tools.
    """
    await check_rate_limit(request, HEALTH_RATE_LIMIT)
    # TODO: Consider adding authentication or IP allowlisting for extra security
    return get_health_status()

@app.get("/health/live")
async def liveness_endpoint(request: Request):
    """
    Kubernetes liveness probe endpoint.
    Returns minimal response, high rate limit for frequent probes.
    """
    await check_rate_limit(request, PROBE_RATE_LIMIT)
    return get_liveness()

@app.get("/health/ready")
async def readiness_endpoint(request: Request):
    """
    Kubernetes readiness probe endpoint.
    Returns sanitized response, high rate limit for frequent probes.
    """
    await check_rate_limit(request, PROBE_RATE_LIMIT)
    from backend.monitoring.health import _get_health_checker
    return _get_health_checker().get_public_readiness()

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

    try:
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
        
        # Check Suggested Question Cache FIRST (for empty chat history)
        if len(paired_chat_history) == 0:
            lookup_start = time.time()
            cached_result = await suggested_question_cache.get(request.query)
            lookup_duration = time.time() - lookup_start
            suggested_question_cache_lookup_duration_seconds.observe(lookup_duration)
            
            if cached_result:
                # Cache hit - return immediately
                logger.debug(f"Suggested Question Cache hit for: {request.query[:50]}...")
                suggested_question_cache_hits_total.labels(cache_type="suggested_question").inc()
                answer, sources = cached_result
                
                # Transform Langchain Document objects to our Pydantic SourceDocument model
                source_documents = [
                    SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
                    for doc in sources
                    if doc.metadata.get('status') == 'published'
                ]
                
                return ChatResponse(
                    answer=answer,
                    sources=source_documents
                )
            else:
                # Cache miss - fall through to QueryCache → RAG pipeline
                suggested_question_cache_misses_total.labels(cache_type="suggested_question").inc()
                logger.debug(f"Suggested Question Cache miss for: {request.query[:50]}...")
                
        # Use the globally initialized RAG pipeline instance with async processing
        # This will check QueryCache internally, then run RAG pipeline if needed
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
    except HTTPException:
        # Re-raise HTTP exceptions (rate limiting, etc.) - they're already properly formatted
        raise
    except Exception as e:
        # Log full error details server-side
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        # Raise HTTPException which will be handled by global exception handler
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "An error occurred while processing your query. Please try again or rephrase your question."}
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

            # Check Suggested Question Cache FIRST (for empty chat history)
            from_cache = False
            if len(paired_chat_history) == 0:
                lookup_start = time.time()
                cached_result = await suggested_question_cache.get(request.query)
                lookup_duration = time.time() - lookup_start
                suggested_question_cache_lookup_duration_seconds.observe(lookup_duration)
                
                if cached_result:
                    # Cache hit - stream cached response
                    logger.debug(f"Suggested Question Cache hit for: {request.query[:50]}...")
                    suggested_question_cache_hits_total.labels(cache_type="suggested_question").inc()
                    answer, sources = cached_result
                    
                    # Filter published sources
                    published_sources = [
                        doc for doc in sources
                        if doc.metadata.get('status') == 'published'
                    ]
                    
                    # Send sources first
                    sources_json = jsonable_encoder([
                        SourceDocument(page_content=doc.page_content, metadata=doc.metadata)
                        for doc in published_sources
                    ])
                    payload = {
                        "status": "sources",
                        "sources": sources_json,
                        "isComplete": False
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    
                    # Stream cached response character by character for consistent UX
                    for i, char in enumerate(answer):
                        payload = {
                            "status": "streaming",
                            "chunk": char,
                            "isComplete": False
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        # Small delay to control streaming speed
                        if i % 10 == 0:  # Yield control every 10 characters
                            await asyncio.sleep(0.001)
                    
                    # Signal completion with cache flag
                    payload = {
                        "status": "complete",
                        "chunk": "",
                        "isComplete": True,
                        "fromCache": "suggested_question"
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    return
                else:
                    # Cache miss - fall through to QueryCache → RAG pipeline
                    suggested_question_cache_misses_total.labels(cache_type="suggested_question").inc()
                    logger.debug(f"Suggested Question Cache miss for: {request.query[:50]}...")

            # Get streaming response from RAG pipeline
            # This will check QueryCache internally, then run RAG pipeline if needed
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
            logger.error(f"Error in streaming response: {e}", exc_info=True)
            payload = {
                "status": "error",
                "error": "An error occurred while processing your query. Please try again or rephrase your question.",
                "isComplete": True
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # CORS headers handled by middleware - removed hardcoded wildcards
        }
    )


# Admin endpoint for cache refresh
ADMIN_CACHE_REFRESH_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=5,
    requests_per_hour=20,
    identifier="admin_cache_refresh",
)

def verify_admin_token(authorization: str = None) -> bool:
    """
    Verify admin token from Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        True if token is valid, False otherwise
    """
    if not authorization:
        return False
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return False
    except ValueError:
        return False
    
    # Get expected token from environment
    expected_token = os.getenv("ADMIN_TOKEN")
    if not expected_token:
        logger.warning("ADMIN_TOKEN not set, admin endpoint authentication disabled")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    import hmac
    return hmac.compare_digest(token, expected_token)


@app.post("/api/v1/admin/refresh-suggested-cache")
async def refresh_suggested_cache_endpoint(request: Request):
    """
    Admin endpoint to manually refresh the suggested question cache.
    
    Requires Bearer token authentication via Authorization header.
    Example: Authorization: Bearer <ADMIN_TOKEN>
    
    Returns:
        JSON response with refresh statistics
    """
    # Rate limiting
    await check_rate_limit(request, ADMIN_CACHE_REFRESH_RATE_LIMIT)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    
    # Verify authentication
    if not verify_admin_token(auth_header):
        logger.warning(
            f"Unauthorized cache refresh attempt from IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid or missing admin token"}
        )
    
    # Refresh cache
    try:
        result = await refresh_suggested_question_cache()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error refreshing suggested question cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": "Failed to refresh cache"}
        )
