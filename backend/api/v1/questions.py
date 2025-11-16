from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel
import logging

from backend.data_models import UserQuestion
from backend.dependencies import get_user_questions_collection
from backend.utils.input_sanitizer import sanitize_mongodb_query_param

logger = logging.getLogger(__name__)

router = APIRouter()

def document_to_user_question(doc: dict) -> UserQuestion:
    """Converts a MongoDB document to a UserQuestion model."""
    # Create a copy to avoid modifying the original
    doc_copy = doc.copy()
    if "_id" in doc_copy:
        doc_copy["id"] = str(doc_copy["_id"])
        del doc_copy["_id"]
    # MongoDB datetime objects are already datetime instances, no conversion needed
    # But handle string conversion if needed for JSON serialization
    return UserQuestion(**doc_copy)

class UserQuestionsResponse(BaseModel):
    """Response model for paginated user questions."""
    questions: List[UserQuestion]
    total: int
    page: int
    page_size: int
    total_pages: int

@router.get("/", response_model=UserQuestionsResponse)
async def get_user_questions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    analyzed: Optional[bool] = Query(None, description="Filter by analyzed status"),
    endpoint_type: Optional[str] = Query(None, description="Filter by endpoint type (chat or stream)"),
    collection: AsyncIOMotorCollection = Depends(get_user_questions_collection)
):
    """
    Retrieves user questions with pagination and optional filtering.
    Only accessible by admins (authentication should be added).
    """
    try:
        # Sanitize endpoint_type parameter to prevent NoSQL injection
        if endpoint_type:
            endpoint_type = sanitize_mongodb_query_param(endpoint_type)
            # Validate it's one of the allowed values
            if endpoint_type not in ["chat", "stream"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid endpoint_type. Must be 'chat' or 'stream'."
                )
        
        # Build query filter
        query_filter = {}
        if analyzed is not None:
            query_filter["analyzed"] = analyzed
        if endpoint_type:
            query_filter["endpoint_type"] = endpoint_type
        
        # Get total count
        total = await collection.count_documents(query_filter)
        
        # Calculate pagination
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        
        # Fetch questions, sorted by timestamp (newest first)
        cursor = collection.find(query_filter).sort("timestamp", -1).skip(skip).limit(page_size)
        questions_docs = await cursor.to_list(length=page_size)
        
        # Convert to UserQuestion models
        questions = [document_to_user_question(doc) for doc in questions_docs]
        
        return UserQuestionsResponse(
            questions=questions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error fetching user questions: {e}", exc_info=True)
        # Don't expose internal error details to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user questions. Please try again later."
        )

@router.get("/stats")
async def get_questions_stats(
    collection: AsyncIOMotorCollection = Depends(get_user_questions_collection)
):
    """
    Get statistics about user questions.
    Only accessible by admins (authentication should be added).
    """
    try:
        total_questions = await collection.count_documents({})
        analyzed_count = await collection.count_documents({"analyzed": True})
        unanalyzed_count = await collection.count_documents({"analyzed": False})
        chat_count = await collection.count_documents({"endpoint_type": "chat"})
        stream_count = await collection.count_documents({"endpoint_type": "stream"})
        
        # Get date range
        oldest_doc = await collection.find_one(sort=[("timestamp", 1)])
        newest_doc = await collection.find_one(sort=[("timestamp", -1)])
        
        return {
            "total_questions": total_questions,
            "analyzed": analyzed_count,
            "unanalyzed": unanalyzed_count,
            "by_endpoint": {
                "chat": chat_count,
                "stream": stream_count
            },
            "date_range": {
                "oldest": oldest_doc["timestamp"].isoformat() if oldest_doc else None,
                "newest": newest_doc["timestamp"].isoformat() if newest_doc else None
            }
        }
    except Exception as e:
        logger.error(f"Error fetching question stats: {e}", exc_info=True)
        # Don't expose internal error details to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching question statistics. Please try again later."
        )

