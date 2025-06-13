from fastapi import APIRouter, Depends, HTTPException, status
from . import models
# Assuming User model and get_current_active_user are needed for securing the webhook
# If the webhook is called internally or by a trusted service, auth might be different (e.g., API key)
# For now, let's assume it might be protected similarly to other CMS endpoints.
from ..auth.router import get_current_active_user 
from ..users.models import User
from langchain_core.documents import Document # For creating RAG documents
from backend.data_ingestion.vector_store_manager import VectorStoreManager, get_default_embedding_model # For RAG pipeline interaction

# Initialize VectorStoreManager for the RAG pipeline's collection
# This assumes the RAG pipeline uses 'litecoin_rag_db' and 'litecoin_docs' by default.
# These should ideally be configurable if different from CMS storage.
# Reason: This manager will handle adding/deleting documents in the RAG vector store.
rag_vector_store_manager = VectorStoreManager(db_name="litecoin_rag_db", collection_name="litecoin_docs")
# Reason: This embedding model is specifically for embedding documents to be stored in RAG.
rag_document_embedding_model = get_default_embedding_model(task_type="retrieval_document")


router = APIRouter(
    prefix="/api/v1/sync",
    tags=["CMS RAG Sync"],
)

@router.post("/rag", response_model=models.RAGSyncResponse)
async def sync_article_with_rag(
    sync_request: models.RAGSyncRequest,
    # current_user: User = Depends(get_current_active_user) # Optional: if webhook needs auth
):
    """
    Webhook to synchronize a CMS article with the RAG pipeline.
    This endpoint is called by the CMS when an article's vetting_status changes
    to 'vetted', or a vetted article is updated or archived.
    """
    article_data = sync_request.article_data
    action = sync_request.action

    # Placeholder for RAG ingestion logic
    # In a real implementation, this would interact with your RAG pipeline's
    # data ingestion and vector store management components.

    try:
        if action == "upsert":
            # Reason: Prepare the document for RAG ingestion.
            # Metadata should include a unique identifier from the CMS for future updates/deletions.
            # Other fields like title, tags, summary can be useful for filtering or context in RAG.
            rag_metadata = {
                "cms_article_id": article_data.id,
                "title": article_data.title,
                "slug": article_data.slug,
                "tags": article_data.tags,
                "summary": article_data.summary,
                "vetting_status": article_data.vetting_status, # Added vetting_status
                "source": f"cms_article_{article_data.id}" # Example source identifier
            }
            # Remove None values from metadata to keep it clean
            rag_metadata = {k: v for k, v in rag_metadata.items() if v is not None}

            langchain_document = Document(
                page_content=article_data.content_markdown,
                metadata=rag_metadata
            )

            # Reason: For "upsert", first delete any existing version of this CMS article from RAG.
            # This prevents duplicates if an article is updated.
            # The deletion is based on the unique 'cms_article_id' stored in metadata.
            delete_filter = {"cms_article_id": article_data.id}
            deleted_count = rag_vector_store_manager.delete_documents_by_metadata(delete_filter)
            print(f"RAG Sync: Deleted {deleted_count} existing RAG documents for CMS article ID {article_data.id} before upsert.")

            # Reason: Add the new/updated document to the RAG vector store.
            # The add_documents method handles embedding using the provided model.
            rag_vector_store_manager.add_documents([langchain_document], embeddings_model=rag_document_embedding_model)
            
            print(f"RAG Sync: Upserted article {article_data.id} - Title: {article_data.title} into RAG.")
            return models.RAGSyncResponse(
                status="success",
                message=f"Article {article_data.id} successfully upserted into RAG.",
                article_id=article_data.id
            )

        elif action == "delete":
            # Reason: Delete the article from the RAG vector store using its unique CMS ID.
            delete_filter = {"cms_article_id": article_data.id}
            deleted_count = await rag_vector_store_manager.delete_documents_by_metadata(delete_filter) # Added await
            
            print(f"RAG Sync: Deleted {deleted_count} RAG documents for CMS article ID {article_data.id}.")
            if deleted_count > 0:
                message = f"Article {article_data.id} successfully deleted from RAG."
            else:
                message = f"Article {article_data.id} not found in RAG or already deleted."
            
            return models.RAGSyncResponse(
                status="success", # Or "not_found" if deleted_count is 0 and that's meaningful
                message=message,
                article_id=article_data.id
            )

        else:
            # Should not happen due to Pydantic validation of 'action'
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action specified.")
            
    except Exception as e:
        print(f"Error during RAG sync for article {article_data.id}, action {action}: {e}")
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during RAG synchronization: {str(e)}"
        )
