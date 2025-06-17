# backend/strapi/webhook_handler.py

"""
Handles the business logic for processing Strapi webhooks.
"""

from fastapi import BackgroundTasks, HTTPException
from backend.data_models import StrapiWebhookPayload, StrapiArticle
from backend.data_ingestion.embedding_processor_strapi import process_strapi_article
from backend.data_ingestion.vector_store_manager import VectorStoreManager

async def handle_webhook(payload: StrapiWebhookPayload, background_tasks: BackgroundTasks):
    """
    Handles the incoming webhook payload from Strapi.

    Args:
        payload (StrapiWebhookPayload): The webhook payload.
        background_tasks (BackgroundTasks): FastAPI background tasks.
    """
    vector_store_manager = VectorStoreManager()

    if payload.event in ["entry.publish", "entry.update"]:
        if payload.model == "article":
            # Convert WebhookEntry to a dict that matches StrapiArticle structure
            article_data = {
                "id": payload.entry.id,
                "attributes": {
                    "title": payload.entry.title,
                    "slug": payload.entry.slug,
                    "content": payload.entry.content,
                    "author": payload.entry.author,
                    "tags": payload.entry.tags,
                    "publishedAt": payload.entry.published_at,
                    "createdAt": payload.entry.created_at,
                    "updatedAt": payload.entry.updated_at,
                }
            }
            article = StrapiArticle(**article_data)
            documents = process_strapi_article(article)
            if documents:
                background_tasks.add_task(vector_store_manager.add_documents, documents)
                print(f"Processing {len(documents)} documents for article {article.id} in the background.")

    elif payload.event in ["entry.unpublish", "entry.delete"]:
        if payload.model == "article":
            strapi_id = payload.entry.id
            background_tasks.add_task(vector_store_manager.delete_documents_by_strapi_id, strapi_id)
            print(f"Deleting documents for article {strapi_id} in the background.")
    else:
        print(f"Received unhandled event type: {payload.event}")
