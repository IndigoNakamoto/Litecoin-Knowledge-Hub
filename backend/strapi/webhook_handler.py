"""
Webhook handler optimized for your Article content type fields
"""

import asyncio
import traceback
import logging
from fastapi import BackgroundTasks, HTTPException
from langchain_core.documents import Document
from backend.data_models import StrapiWebhookPayload
from backend.strapi.rich_text_chunker import StrapiRichTextChunker
from datetime import datetime
from ..data_ingestion.vector_store_manager import VectorStoreManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_webhook(payload: StrapiWebhookPayload, background_tasks: BackgroundTasks):
    """
    Handle Strapi webhooks for Article content type.
    
    This version processes your specific Article fields:
    - Title (required)
    - Summary (optional)  
    - Content (required, rich text)
    - Author (required)
    - Slug (optional)
    - Tags (required)
    - Published (required, datetime)
    """
    try:
        logger.info(f"Processing webhook: event='{payload.event}', model='{payload.model}', entry_id={payload.entry.id}")
        logger.info(f"Article details: title='{payload.entry.Title}', author='{payload.entry.Author}'")
        
        vector_store_manager = VectorStoreManager()
        
        # Handle publish and update events
        if payload.event in ["entry.publish", "entry.update"]:
            if payload.model == "article":
                strapi_id = payload.entry.id
                logger.info(f"Processing '{payload.event}' for article '{payload.entry.Title}' (ID: {strapi_id})")

                document_id = payload.entry.documentId
                if not document_id:
                    logger.error(f"CRITICAL: 'documentId' is missing in the payload for entry {strapi_id}. Cannot reliably delete.")
                    raise HTTPException(status_code=400, detail="Payload missing 'documentId'")

                try:
                    # Delete existing documents first to ensure consistency
                    logger.info(f"Deleting existing documents for article {strapi_id} using documentId: {document_id}")
                    deletion_result = vector_store_manager.delete_documents_by_document_id(document_id)
                    logger.info(f"Deletion result: {deletion_result}")
                except Exception as e:
                    logger.error(f"Error deleting existing documents: {str(e)}")
                    # Continue processing even if deletion fails

                try:
                    # Use the rich text chunker to create structured documents
                    chunker = StrapiRichTextChunker()
                    # The webhook payload 'entry' needs to be converted to the format expected by the chunker
                    article_data = {
                        "id": payload.entry.id,
                        "attributes": {
                            "title": payload.entry.Title,
                            "summary": payload.entry.Summary,
                            "content": payload.entry.Content,
                            # Add other attributes if the chunker needs them
                        }
                    }
                    documents = chunker.chunk_document(article_data)
                    
                    # Enrich all chunks with common metadata
                    base_metadata = process_article_for_embedding(payload.entry)
                    for doc in documents:
                        # Combine metadata, giving precedence to the specific chunk metadata
                        doc.metadata = {**base_metadata, **doc.metadata}

                    logger.info(f"Chunked article into {len(documents)} documents.")

                    # Add to vector store in background
                    background_tasks.add_task(
                        safe_add_documents,
                        vector_store_manager,
                        documents,
                        strapi_id,
                        payload.entry.Title
                    )
                    logger.info(f"Successfully queued upsert for article '{payload.entry.Title}' (ID: {strapi_id})")

                except Exception as e:
                    logger.error(f"Error processing article content for {strapi_id}: {str(e)}")
                    logger.error(f"Article data: {payload.entry.dict()}")
                    raise

        # Handle unpublish and delete events
        elif payload.event in ["entry.unpublish", "entry.delete"]:
            if payload.model == "article":
                strapi_id = payload.entry.id
                document_id = payload.entry.documentId
                article_title = getattr(payload.entry, 'Title', f'ID {strapi_id}')

                if not document_id:
                    logger.error(f"CRITICAL: 'documentId' is missing in the payload for entry {strapi_id}. Cannot reliably delete.")
                    # Do not proceed with deletion if the stable ID is missing
                    return

                logger.info(f"Processing '{payload.event}' for article '{article_title}' (ID: {strapi_id}, documentId: {document_id})")
                
                background_tasks.add_task(
                    safe_delete_documents, 
                    vector_store_manager, 
                    document_id,
                    article_title
                )
                logger.info(f"Successfully queued deletion for article '{article_title}' (documentId: {document_id})")
                
        # Handle other events
        else:
            logger.warning(f"Received unhandled event: '{payload.event}' for model '{payload.model}'. No action taken.")

    except Exception as e:
        logger.error(f"Critical error in handle_webhook: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Payload data: {payload.dict()}")
        raise

def process_article_for_embedding(entry) -> dict:
    """
    Process your Article entry fields into a metadata dictionary.
    The content processing is now handled by the StrapiRichTextChunker.
    
    Args:
        entry: ArticleEntry object with your specific fields
        
    Returns:
        dict: metadata
    """
    # Process published_date
    published_date_iso = None
    if hasattr(entry, 'Published') and entry.Published:
        try:
            # Assuming 'Published' is in ISO 8601 format, e.g., 'YYYY-MM-DDTHH:MM:SS.sssZ'
            # Use .fromisoformat() for strict ISO 8601 parsing.
            # If your Strapi sends 'Z' for UTC, it's typically handled.
            # If it sends a different timezone offset, you might need dateutil.parser.isoparse.
            published_dt = datetime.fromisoformat(entry.Published.replace('Z', '+00:00')) # Replace Z with +00:00 for strict parsing
            published_date_iso = published_dt.isoformat()
        except ValueError as e:
            logger.warning(f"Could not parse 'Published' date string '{entry.Published}': {e}")
            # Fallback or leave as None if parsing fails
            published_date_iso = None

    # Build metadata
    metadata = {
        'strapi_id': entry.id,
        'document_id': entry.documentId, # Add the stable document ID
        'source': 'strapi',
        'content_type': 'article',
        'title': getattr(entry, 'Title', ''),
        'summary': getattr(entry, 'Summary', '') or '',
        'author': getattr(entry, 'Author', ''),
        'slug': getattr(entry, 'Slug', '') or '',
        'tags': getattr(entry, 'Tags', ''),
        'published_date': published_date_iso, # Use the parsed and re-formatted date
        'created_at': entry.createdAt.isoformat() if hasattr(entry, 'createdAt') else None,
        'updated_at': entry.updatedAt.isoformat() if hasattr(entry, 'updatedAt') else None,
        'published_at': entry.publishedAt.isoformat() if hasattr(entry, 'publishedAt') and entry.publishedAt else None,
    }
    
    return metadata

def extract_text_from_blocks(content_blocks) -> str:
    """
    Extract plain text from Strapi's rich text blocks format.
    
    Handles the actual format from your webhook:
    [{"type": "paragraph", "children": [{"type": "text", "text": "test432"}]}]
    """
    # This function is now superseded by the logic in StrapiRichTextChunker,
    # but we keep it here to avoid breaking other parts of the code that might
    # still reference it. The core logic is now in the chunker.
    if not content_blocks:
        return ""
    
    text_parts = []
    for block in content_blocks:
        if block.get('type') in ['paragraph', 'heading']:
            text_parts.append("".join(child.get('text', '') for child in block.get('children', [])))
    
    return ' '.join(text_parts).strip()

def clean_rich_text_content(rich_text_content) -> str:
    """
    Clean and extract text from Strapi's rich text (blocks) content.
    
    Strapi's rich text editor typically outputs JSON blocks or HTML.
    You'll need to customize this based on your actual content format.
    """
    if isinstance(rich_text_content, str):
        # If it's already a string, return as-is (might be HTML)
        # You could add HTML stripping here if needed
        return rich_text_content
    
    elif isinstance(rich_text_content, list):
        # If it's a list of blocks (Strapi blocks format)
        text_parts = []
        for block in rich_text_content:
            if isinstance(block, dict):
                # Extract text from different block types
                if block.get('type') == 'paragraph':
                    # Handle paragraph blocks
                    children = block.get('children', [])
                    for child in children:
                        if isinstance(child, dict) and child.get('text'):
                            text_parts.append(child['text'])
                elif block.get('type') == 'heading':
                    # Handle heading blocks
                    children = block.get('children', [])
                    for child in children:
                        if isinstance(child, dict) and child.get('text'):
                            text_parts.append(child['text'])
                # Add more block types as needed
        
        return ' '.join(text_parts)
    
    elif isinstance(rich_text_content, dict):
        # If it's a single block object
        return str(rich_text_content.get('text', ''))
    
    else:
        # Fallback to string conversion
        return str(rich_text_content)

async def safe_add_documents(vector_store_manager: VectorStoreManager, documents: list, strapi_id: int, title: str = ""):
    """Safely add documents to vector store with enhanced logging."""
    try:
        logger.info(f"Adding documents to vector store for article '{title}' (ID: {strapi_id})")
        
        # Handle both async and sync add_documents methods
        try:
            result = await vector_store_manager.add_documents(documents)
        except TypeError:
            result = vector_store_manager.add_documents(documents)
            
        logger.info(f"✅ Successfully added documents for article '{title}' (ID: {strapi_id})")
        if result:
            logger.info(f"   Result: {result}")
            
    except Exception as e:
        logger.error(f"❌ Failed to add documents for article '{title}' (ID: {strapi_id}): {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

async def safe_delete_documents(vector_store_manager: VectorStoreManager, document_id: str, title: str = ""):
    """Safely delete documents from vector store with enhanced logging using the stable document_id."""
    try:
        logger.info(f"Deleting documents from vector store for article '{title}' (documentId: {document_id})")
        result = vector_store_manager.delete_documents_by_document_id(document_id)
        logger.info(f"✅ Successfully deleted documents for article '{title}' (documentId: {document_id})")
        if result:
            logger.info(f"   Result: {result}")
            
    except Exception as e:
        logger.error(f"❌ Failed to delete documents for article '{title}' (documentId: {document_id}): {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
