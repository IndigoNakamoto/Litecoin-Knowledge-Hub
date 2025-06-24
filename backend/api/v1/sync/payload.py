from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import logging
from pydantic import ValidationError

from backend.data_models import PayloadWebhookDoc
from backend.data_ingestion.embedding_processor import process_payload_documents
from backend.data_ingestion.vector_store_manager import VectorStoreManager

router = APIRouter()
logger = logging.getLogger(__name__)

def process_and_embed_document(payload_doc):
    """
    Background task to process and embed a single document from Payload.
    """
    try:
        vector_store_manager = VectorStoreManager()
        payload_id = payload_doc.id
        
        logger.info(f"[Task ID: {payload_id}] Starting processing for published document.")

        # 1. Delete existing documents for this payload_id to handle updates cleanly.
        logger.info(f"[Task ID: {payload_id}] Deleting existing chunks from vector store.")
        deleted_count = vector_store_manager.delete_documents_by_metadata_field('payload_id', payload_id)
        logger.info(f"[Task ID: {payload_id}] Deleted {deleted_count} existing chunk(s).")

        # 2. Process the new document into chunks.
        logger.info(f"[Task ID: {payload_id}] Processing document into hierarchical chunks.")
        processed_chunks = process_payload_documents([payload_doc])
        
        # 3. Add the new chunks to the vector store.
        if processed_chunks:
            logger.info(f"[Task ID: {payload_id}] Adding {len(processed_chunks)} new chunks to the vector store.")
            vector_store_manager.add_documents(processed_chunks)
            logger.info(f"[Task ID: {payload_id}] Successfully added new chunks to the vector store.")
        else:
            logger.warning(f"[Task ID: {payload_id}] No chunks were generated from the document.")
            
    except Exception as e:
        logger.error(f"Error in background task for payload ID {payload_doc.id}: {e}", exc_info=True)


@router.post("/payload")
async def receive_payload_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives a webhook from Payload CMS after a document is changed.
    Validates the payload and triggers a background task for processing if the document is published.
    """
    raw_payload = await request.json()
    logger.info(f"Received raw Payload webhook: {raw_payload}")

    try:
        # The webhook sends the 'doc' object directly, not the full PayloadWebhookPayload structure.
        # Extract the 'doc' and validate it against PayloadWebhookDoc.
        payload_doc = PayloadWebhookDoc(**raw_payload.get('doc', {}))
        
        # The 'operation' field is also sent at the root level of the original Payload webhook,
        # but our custom fetch in Article.ts only sends 'doc'.
        # For now, we'll assume 'update' or 'create' if 'doc' is present and status is 'published'.
        # If a 'delete' operation needs to be handled, the Payload hook in Article.ts
        # would need to send 'operation' explicitly.
        operation = "update" # Default to update, as we only trigger on publish/update in Article.ts hook

        logger.info(f"Received webhook for doc ID '{payload_doc.id}' with status '{payload_doc.status}' and assumed operation '{operation}'.")
        
        # We only care about documents that are in a 'published' state for ingestion.
        if payload_doc.status == 'published':
            # Run the processing in the background to avoid blocking the webhook response.
            background_tasks.add_task(process_and_embed_document, payload_doc)
            msg = f"Processing triggered for published document ID: {payload_doc.id}"
            logger.info(msg)
            return {"status": "processing_triggered", "message": msg}
        else:
            # If the document is not published (e.g., 'draft'), we can optionally clear its old chunks.
            # This handles cases where a document is unpublished or saved as a draft.
            background_tasks.add_task(VectorStoreManager().delete_documents_by_metadata_field, 'payload_id', payload_doc.id)
            msg = f"Document ID '{payload_doc.id}' is not published (status: {payload_doc.status}). Deleting any existing chunks."
            logger.info(msg)
            return {"status": "not_published", "message": msg}
    except ValidationError as e:
        logger.error(f"Payload webhook validation error: {e.errors()}", exc_info=True)
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing Payload webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
