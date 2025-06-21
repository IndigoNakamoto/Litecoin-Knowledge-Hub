from fastapi import APIRouter, Request, HTTPException
import logging
from backend.data_ingestion.embedding_processor_payload import PayloadEmbeddingProcessor
from backend.data_ingestion.vector_store_manager import VectorStoreManager

router = APIRouter()

logger = logging.getLogger(__name__)
embedding_processor = PayloadEmbeddingProcessor()
vector_store_manager = VectorStoreManager()

@router.post("/payload")
async def receive_payload_webhook(request: Request):
    """
    Receives a webhook from Payload CMS after a document is changed.
    """
    try:
        data = await request.json()
        logger.info(f"Received webhook from Payload: {data}")
        
        doc_data = data.get('doc')
        if not doc_data:
            logger.error("No 'doc' key found in webhook payload.")
            raise HTTPException(status_code=400, detail="Missing 'doc' in payload")

        logger.info(f"Processing document with ID: {doc_data.get('id')}")
        
        # Process the data
        documents = embedding_processor.process(doc_data)
        logger.info(f"Processed {len(documents)} documents for embedding.")
        
        # Add the documents to the vector store
        if documents:
            logger.info(f"Adding {len(documents)} documents to the vector store.")
            vector_store_manager.add_documents(documents)
            logger.info("Successfully added documents to the vector store.")
        else:
            logger.warning("No documents were processed, so nothing was added to the vector store.")
        
        return {"status": "success", "processed_documents": len(documents)}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing webhook")
