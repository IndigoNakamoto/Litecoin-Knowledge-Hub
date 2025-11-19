"""
Admin API endpoint for LLM usage statistics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from backend.monitoring.spend_limit import get_current_usage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/usage")
async def get_usage() -> Dict[str, Any]:
    """
    Get current daily and hourly LLM usage statistics.
    
    Returns:
        Dictionary with daily and hourly usage information including costs, limits, percentages, and tokens.
    """
    try:
        usage_info = await get_current_usage()
        return usage_info
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage statistics")


@router.get("/usage/status")
async def get_usage_status() -> Dict[str, Any]:
    """
    Get simplified usage status for frontend warnings.
    Returns warning level if approaching limits.
    
    Returns:
        Dictionary with status, warning level, and usage percentages.
    """
    try:
        usage_info = await get_current_usage()
        
        daily_percentage = usage_info["daily"]["percentage_used"]
        hourly_percentage = usage_info["hourly"]["percentage_used"]
        
        # Determine warning level
        warning_level = None
        if daily_percentage >= 100 or hourly_percentage >= 100:
            warning_level = "error"
        elif daily_percentage >= 80 or hourly_percentage >= 80:
            warning_level = "warning"
        elif daily_percentage >= 60 or hourly_percentage >= 60:
            warning_level = "info"
        
        return {
            "status": "ok" if warning_level is None else warning_level,
            "warning_level": warning_level,
            "daily_percentage": daily_percentage,
            "hourly_percentage": hourly_percentage,
            "daily_remaining": usage_info["daily"]["remaining_usd"],
            "hourly_remaining": usage_info["hourly"]["remaining_usd"],
        }
    except Exception as e:
        logger.error(f"Error getting usage status: {e}", exc_info=True)
        # Return safe defaults on error
        return {
            "status": "ok",
            "warning_level": None,
            "daily_percentage": 0.0,
            "hourly_percentage": 0.0,
            "daily_remaining": 5.0,
            "hourly_remaining": 0.25,
        }

