# backend/api/v1/sync/strapi.py

"""
FastAPI router for handling Strapi webhooks with enhanced debugging.
"""

import os
import json
import logging
from fastapi import APIRouter, Request, Security, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from backend.data_models import StrapiWebhookPayload
from backend.strapi.webhook_handler import handle_webhook

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

async def verify_strapi_webhook_secret(x_strapi_webhook_secret: str = Header(...)):
    """
    Verifies the Strapi webhook secret.
    """
    if not x_strapi_webhook_secret:
        logger.error("X-Strapi-Webhook-Secret header is missing")
        raise HTTPException(status_code=400, detail="X-Strapi-Webhook-Secret header is missing")
    
    expected_secret = os.environ.get("STRAPI_WEBHOOK_SECRET")
    if not expected_secret:
        logger.error("STRAPI_WEBHOOK_SECRET environment variable is not set")
        raise HTTPException(status_code=500, detail="STRAPI_WEBHOOK_SECRET is not configured on the server")

    if x_strapi_webhook_secret != expected_secret:
        logger.error(f"Invalid webhook secret received: {x_strapi_webhook_secret[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid Strapi webhook secret")
    
    logger.info("Webhook secret validation passed")

@router.post("/strapi", dependencies=[Security(verify_strapi_webhook_secret)])
async def strapi_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receives and processes webhooks from Strapi with enhanced debugging.
    """
    try:
        # Log raw request details
        logger.info(f"Received webhook from IP: {request.client.host}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Get raw body for debugging
        raw_body = await request.body()
        logger.info(f"Raw webhook body: {raw_body.decode('utf-8')}")
        
        # Parse JSON manually to handle potential parsing issues
        try:
            payload_dict = json.loads(raw_body.decode('utf-8'))
            logger.info(f"Parsed payload keys: {list(payload_dict.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate payload structure
        try:
            payload = StrapiWebhookPayload(**payload_dict)
            logger.info(f"Payload validation successful: event={payload.event}, model={payload.model}, entry_id={payload.entry.id}")
        except Exception as e:
            logger.error(f"Payload validation failed: {str(e)}")
            logger.error(f"Payload structure: {payload_dict}")
            raise HTTPException(status_code=400, detail=f"Payload validation failed: {str(e)}")
        
        # Process webhook
        try:
            background_tasks.add_task(handle_webhook, payload, background_tasks)
            logger.info("Webhook processing task queued successfully")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "message": "Webhook received and is being processed.",
                    "event": payload.event,
                    "model": payload.model,
                    "entry_id": payload.entry.id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to queue webhook processing: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook receiver: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint for testing
@router.get("/strapi/health")
async def webhook_health_check():
    """
    Health check endpoint to verify webhook endpoint is accessible.
    """
    return {"status": "healthy", "message": "Strapi webhook endpoint is operational"}

# Test endpoint for manual testing
@router.post("/strapi/test")
async def test_webhook_processing(test_payload: dict, background_tasks: BackgroundTasks):
    """
    Test endpoint for manually testing webhook processing.
    """
    logger.info(f"Test webhook called with payload: {test_payload}")
    
    try:
        payload = StrapiWebhookPayload(**test_payload)
        background_tasks.add_task(handle_webhook, payload, background_tasks)
        return {"status": "success", "message": "Test webhook processed"}
    except Exception as e:
        logger.error(f"Test webhook failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Test failed: {str(e)}")