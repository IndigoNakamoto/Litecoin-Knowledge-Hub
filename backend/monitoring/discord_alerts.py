"""
Discord Alerting Module for LLM Spend Limit Monitoring

This module provides Discord webhook integration for sending alerts when
spend limits are approached or exceeded.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Discord webhook URL (optional)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


async def send_spend_limit_alert(
    limit_type: str,
    current_cost: float,
    limit: float,
    percentage: float,
    is_exceeded: bool
) -> bool:
    """
    Send a Discord alert for spend limit threshold crossing.
    
    Args:
        limit_type: "daily" or "hourly"
        current_cost: Current cost in USD
        limit: Limit in USD
        percentage: Percentage of limit used
        is_exceeded: True if limit is exceeded, False if at warning threshold (80%)
    
    Returns:
        True if alert was sent successfully, False otherwise
    """
    if not DISCORD_WEBHOOK_URL:
        # Discord webhook not configured, skip silently
        return False
    
    try:
        # Determine alert level and color
        if is_exceeded:
            title = f"🚨 LLM Spend Limit EXCEEDED - {limit_type.upper()}"
            description = f"The {limit_type} LLM spend limit has been **EXCEEDED**."
            color = 0xFF0000  # Red
            status_emoji = "🔴"
        else:
            title = f"⚠️ LLM Spend Limit WARNING - {limit_type.upper()}"
            description = f"The {limit_type} LLM spend limit has been approached (80% threshold)."
            color = 0xFFAA00  # Orange/Yellow
            status_emoji = "🟡"
        
        remaining = max(0.0, limit - current_cost)
        
        # Format Discord embed
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": [
                {
                    "name": "Current Usage",
                    "value": f"${current_cost:.4f} / ${limit:.2f} ({percentage:.1f}%)",
                    "inline": False
                },
                {
                    "name": "Limit Type",
                    "value": limit_type.upper(),
                    "inline": True
                },
                {
                    "name": "Current Cost",
                    "value": f"${current_cost:.4f}",
                    "inline": True
                },
                {
                    "name": "Limit",
                    "value": f"${limit:.2f}",
                    "inline": True
                },
                {
                    "name": "Percentage Used",
                    "value": f"{percentage:.1f}%",
                    "inline": True
                },
                {
                    "name": "Remaining",
                    "value": f"${remaining:.4f}",
                    "inline": True
                },
            ],
            "footer": {
                "text": "Litecoin Knowledge Hub - Cost Monitoring"
            },
            "timestamp": None  # Will be set by Discord
        }
        
        payload = {
            "embeds": [embed]
        }
        
        # Send webhook request
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(DISCORD_WEBHOOK_URL, json=payload)
            response.raise_for_status()
        
        logger.info(f"Discord alert sent successfully: {limit_type} limit {'exceeded' if is_exceeded else 'warning'}")
        return True
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to send Discord alert (HTTP error): {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}", exc_info=True)
        return False

