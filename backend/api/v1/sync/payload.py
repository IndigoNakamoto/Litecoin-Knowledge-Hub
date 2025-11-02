from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import logging
import requests
from pydantic import ValidationError
from datetime import datetime

from backend.data_models import PayloadWebhookDoc
from backend.data_ingestion.embedding_processor import process_payload_documents
from backend.data_ingestion.vector_store_manager import VectorStoreManager

router = APIRouter()
logger = logging.getLogger(__name__)

def process_and_embed_document(payload_doc):
    """
    Background task to process and embed a single document from Payload.
    """
    payload_id = payload_doc.id
    start_time = datetime.utcnow()

    try:
        logger.info(f"🚀 [Task ID: {payload_id}] Starting background processing for published document '{payload_doc.title}'")

        # Initialize vector store manager
        logger.info(f"🔌 [Task ID: {payload_id}] Initializing vector store connection...")
        vector_store_manager = VectorStoreManager()
        logger.info(f"✅ [Task ID: {payload_id}] Vector store connected successfully")

        # 1. Delete existing documents for this payload_id to handle updates cleanly.
        logger.info(f"🗑️ [Task ID: {payload_id}] Deleting existing chunks from vector store...")
        deleted_count = vector_store_manager.delete_documents_by_metadata_field('payload_id', payload_id)
        logger.info(f"🗑️ [Task ID: {payload_id}] Deleted {deleted_count} existing chunk(s).")

        # 2. Process the new document into chunks.
        logger.info(f"📝 [Task ID: {payload_id}] Processing document into hierarchical chunks...")
        processed_chunks = process_payload_documents([payload_doc])

        if processed_chunks is None:
            logger.error(f"❌ [Task ID: {payload_id}] process_payload_documents returned None")
            return

        logger.info(f"📦 [Task ID: {payload_id}] Generated {len(processed_chunks)} chunks")

        # 3. Add the new chunks to the vector store.
        if processed_chunks:
            logger.info(f"💾 [Task ID: {payload_id}] Adding {len(processed_chunks)} new chunks to the vector store...")
            vector_store_manager.add_documents(processed_chunks)
            logger.info(f"✅ [Task ID: {payload_id}] Successfully added {len(processed_chunks)} chunks to the vector store.")
        else:
            logger.warning(f"⚠️ [Task ID: {payload_id}] No chunks were generated from the document.")

        # 4. Refresh the RAG pipeline to include the new documents
        logger.info(f"🔄 [Task ID: {payload_id}] Refreshing RAG pipeline with new documents...")
        try:
            # Make an internal HTTP call to refresh the RAG pipeline
            refresh_response = requests.post("http://localhost:8000/api/v1/refresh-rag", timeout=30)
            if refresh_response.status_code == 200:
                logger.info(f"✅ [Task ID: {payload_id}] RAG pipeline refreshed successfully")
            else:
                logger.warning(f"⚠️ [Task ID: {payload_id}] RAG pipeline refresh returned status {refresh_response.status_code}: {refresh_response.text}")
        except Exception as refresh_error:
            logger.warning(f"⚠️ [Task ID: {payload_id}] Failed to refresh RAG pipeline: {refresh_error}")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"🎉 [Task ID: {payload_id}] Background processing completed successfully in {duration:.2f} seconds")

    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        logger.error(f"💥 [Task ID: {payload_id}] Background processing failed after {duration:.2f} seconds: {e}", exc_info=True)


@router.post("/payload")
async def receive_payload_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives a webhook from Payload CMS after a document is changed.
    Validates the payload and triggers a background task for processing if the document is published.
    """
    raw_payload = await request.json()
    logger.info(f"🔗 Received Payload webhook - Raw payload keys: {list(raw_payload.keys())}")

    try:
        # The webhook sends the 'doc' object directly, not the full PayloadWebhookPayload structure.
        # Extract the 'doc' and validate it against PayloadWebhookDoc.
        doc_data = raw_payload.get('doc', {})
        logger.info(f"📄 Document data keys: {list(doc_data.keys()) if isinstance(doc_data, dict) else 'Not a dict'}")

        payload_doc = PayloadWebhookDoc(**doc_data)

        # The 'operation' field is also sent at the root level of the original Payload webhook,
        # but our custom fetch in Article.ts only sends 'doc'.
        # For now, we'll assume 'update' or 'create' if 'doc' is present and status is 'published'.
        # If a 'delete' operation needs to be handled, the Payload hook in Article.ts
        # would need to send 'operation' explicitly.
        operation = "update" # Default to update, as we only trigger on publish/update in Article.ts hook

        logger.info(f"📝 Processing doc ID '{payload_doc.id}' with status '{payload_doc.status}' and operation '{operation}'")
        logger.info(f"📖 Document title: '{payload_doc.title}'" if hasattr(payload_doc, 'title') and payload_doc.title else "📖 No title found")

        # We only care about documents that are in a 'published' state for ingestion.
        if payload_doc.status == 'published':
            # Run the processing in the background to avoid blocking the webhook response.
            background_tasks.add_task(process_and_embed_document, payload_doc)
            msg = f"✅ Processing triggered for published document ID: {payload_doc.id}"
            logger.info(msg)
            return {"status": "processing_triggered", "message": msg, "document_id": payload_doc.id}
        else:
            # If the document is not published (e.g., 'draft'), we can optionally clear its old chunks.
            # This handles cases where a document is unpublished or saved as a draft.
            background_tasks.add_task(VectorStoreManager().delete_documents_by_metadata_field, 'payload_id', payload_doc.id)
            msg = f"🚫 Document ID '{payload_doc.id}' is not published (status: {payload_doc.status}). Deleting any existing chunks."
            logger.info(msg)
            return {"status": "not_published", "message": msg, "document_id": payload_doc.id}
    except ValidationError as e:
        logger.error(f"❌ Payload webhook validation error: {e.errors()}", exc_info=True)
        raise HTTPException(status_code=422, detail={"error": "Validation failed", "details": e.errors()})
    except Exception as e:
        logger.error(f"💥 Unexpected error in Payload webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "message": str(e)})


@router.get("/health")
async def webhook_health_check():
    """
    Health check endpoint for webhook connectivity testing.
    """
    try:
        # Test vector store connection
        vector_store_manager = VectorStoreManager()

        # Get total document count from MongoDB (documents have 'text' and 'metadata' fields)
        total_count = 0
        payload_count = 0

        if vector_store_manager.mongodb_available:
            total_count = vector_store_manager.collection.count_documents({})
            # Count documents that have payload_id in metadata (Payload CMS sourced)
            payload_count = vector_store_manager.collection.count_documents({
                "metadata.payload_id": {"$exists": True}
            })

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "vector_store": "connected",
                "mongodb": "available" if vector_store_manager.mongodb_available else "unavailable"
            },
            "document_counts": {
                "total": total_count,
                "from_payload_cms": payload_count
            },
            "message": "Webhook service is operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Webhook service has issues"
        }


@router.post("/test-webhook")
async def test_webhook_endpoint(request: Request):
    """
    Test endpoint to simulate webhook payload for debugging.
    """
    try:
        payload = await request.json()
        logger.info(f"🧪 Test webhook received: {payload}")

        # Validate the payload structure
        doc_data = payload.get('doc', {})
        if not doc_data:
            return {"status": "error", "message": "Missing 'doc' field in payload"}

        # Try to validate against our model
        payload_doc = PayloadWebhookDoc(**doc_data)

        return {
            "status": "success",
            "message": f"Test webhook processed successfully for document '{payload_doc.title}' (ID: {payload_doc.id})",
            "document_id": payload_doc.id,
            "document_status": payload_doc.status
        }
    except ValidationError as e:
        logger.error(f"Test webhook validation error: {e.errors()}")
        return {"status": "validation_error", "errors": e.errors()}
    except Exception as e:
        logger.error(f"Test webhook error: {e}")
        return {"status": "error", "message": str(e)}
