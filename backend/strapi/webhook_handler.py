# backend/strapi/webhook_handler.py

"""
Handles the business logic for processing Strapi webhooks.
"""

from fastapi import BackgroundTasks, HTTPException
from langchain_core.documents import Document
from backend.data_models import StrapiWebhookPayload
from backend.data_ingestion.embedding_processor_strapi import StrapiEmbeddingProcessor
from backend.data_ingestion.vector_store_manager import VectorStoreManager
from backend.strapi.client import StrapiClient

async def handle_webhook(payload: StrapiWebhookPayload, background_tasks: BackgroundTasks):
    """
    Handles the incoming webhook payload from Strapi.

    Args:
        payload (StrapiWebhookPayload): The webhook payload.
        background_tasks (BackgroundTasks): FastAPI background tasks.
    """
    vector_store_manager = VectorStoreManager()
    embedding_processor = StrapiEmbeddingProcessor()
    strapi_client = StrapiClient()

    if payload.event in ["entry.publish", "entry.update"]:
        if payload.model == "article":
            strapi_id = payload.entry.id
            
            # Fetch the full article data from Strapi API
            try:
                article_data = await strapi_client.get_article(strapi_id)
                if not article_data:
                    print(f"Article with ID {strapi_id} not found in Strapi.")
                    return
            except Exception as e:
                print(f"Error fetching article {strapi_id} from Strapi: {e}")
                return

            # Process the full entry to get content and metadata
            content, metadata = embedding_processor.process_entry(article_data)
            
            # For now, we will treat the entire article as a single document.
            documents = [Document(page_content=content, metadata=metadata)]

            if documents:
                # In an update event, we should first delete the old documents
                if payload.event == "entry.update":
                    background_tasks.add_task(vector_store_manager.delete_documents_by_strapi_id, strapi_id)

                background_tasks.add_task(vector_store_manager.add_documents, documents)
                print(f"Processing {len(documents)} documents for article {strapi_id} in the background.")

    elif payload.event in ["entry.unpublish", "entry.delete"]:
        if payload.model == "article":
            strapi_id = payload.entry.id
            background_tasks.add_task(vector_store_manager.delete_documents_by_strapi_id, strapi_id)
            print(f"Deleting documents for article {strapi_id} in the background.")
    else:
        print(f"Received unhandled event type: {payload.event}")
