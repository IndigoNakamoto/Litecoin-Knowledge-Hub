# backend/api/v1/sync/strapi.py

"""
FastAPI router for handling Strapi webhooks.
"""

import os
from fastapi import APIRouter, Request, Security, HTTPException, BackgroundTasks, Header
from backend.data_models import StrapiWebhookPayload
from backend.strapi.webhook_handler import handle_webhook

router = APIRouter()

async def verify_strapi_webhook_secret(x_strapi_webhook_secret: str = Header(...)):
    """
    Verifies the Strapi webhook secret.
    """
    if not x_strapi_webhook_secret:
        raise HTTPException(status_code=400, detail="X-Strapi-Webhook-Secret header is missing")
    
    expected_secret = os.environ.get("STRAPI_WEBHOOK_SECRET")
    if not expected_secret:
        raise HTTPException(status_code=500, detail="STRAPI_WEBHOOK_SECRET is not configured on the server")

    if x_strapi_webhook_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid Strapi webhook secret")

@router.post("/strapi", dependencies=[Security(verify_strapi_webhook_secret)])
async def strapi_webhook_receiver(payload: StrapiWebhookPayload, background_tasks: BackgroundTasks):
    """
    Receives and processes webhooks from Strapi.
    """
    background_tasks.add_task(handle_webhook, payload, background_tasks)
    return {"status": "success", "message": "Webhook received and is being processed."}
