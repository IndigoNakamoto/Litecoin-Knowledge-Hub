import pytest
from datetime import datetime # Added import
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY

from backend.main import app # FastAPI app instance
from backend.cms.articles.models import ArticleDB # For constructing the source ArticleDB data
from backend.cms.sync.models import RAGSyncRequest, SyncArticleData # Updated import
from backend.dependencies import get_cms_db # Changed to get_cms_db
from backend.data_ingestion.vector_store_manager import VectorStoreManager

# Test client for making API requests
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Fixture for auth token if sync endpoint is protected
# For now, assuming it might be an internal webhook or auth is handled/mocked elsewhere
@pytest.fixture(scope="module")
def auth_token():
    # Replace with actual token generation or mock if endpoint is protected
    return {}

# Mock VectorStoreManager instance and its methods
@pytest.fixture
def mock_vector_store_manager():
    manager = AsyncMock(spec=VectorStoreManager)
    manager.add_documents = AsyncMock() # Changed from add_documents_to_collection
    # manager.update_document_in_collection = AsyncMock() # Not directly used by router
    manager.delete_documents_by_metadata = AsyncMock(return_value=1) # Ensure it returns an int
    return manager

# Override VectorStoreManager dependency for the sync router
@pytest.fixture(autouse=True)
def override_vector_store_manager_dependency(mock_vector_store_manager):
    # Assuming VectorStoreManager is injected via a dependency, e.g., get_vector_store_manager
    # If it's directly instantiated, this approach needs adjustment.
    # For this example, let's assume it's available via a patchable import in sync.router
    # We need to patch the instance `rag_vector_store_manager` that is used by the router functions.
    with patch('backend.cms.sync.router.rag_vector_store_manager', new=mock_vector_store_manager) as p:
        yield p

# --- Integration Tests for RAG Sync Webhook ---

@pytest.mark.asyncio
async def test_rag_sync_webhook_add_action(client: TestClient, mock_vector_store_manager: AsyncMock, auth_token: dict):
    """
    Test POST /api/v1/sync/rag with 'add' action.
    """
    # This is the data for SyncArticleData, which is part of RAGSyncRequest
    sync_article_payload_data = SyncArticleData(
        id="sync_test_article_add",
        title="Sync Test Add",
        slug="sync-test-add",
        content_markdown="Content to be added to RAG.",
        tags=["sync", "add"],
        vetting_status="vetted", # Important for 'upsert'
        summary="A summary for sync" # summary is optional
    )

    # This is the main payload for the endpoint
    rag_sync_request_payload = RAGSyncRequest(
        action="upsert", # Changed from ADD to "upsert"
        article_data=sync_article_payload_data
    )

    response = client.post("/api/v1/sync/rag", json=rag_sync_request_payload.model_dump(mode='json'), headers=auth_token)

    assert response.status_code == 200
    # The response model is RAGSyncResponse
    response_json = response.json()
    assert response_json["status"] == "success"
    assert response_json["article_id"] == sync_article_payload_data.id
    assert "upsert" in response_json["message"]
    
    # The router calls delete_documents_by_metadata then add_documents for an upsert
    mock_vector_store_manager.delete_documents_by_metadata.assert_called_once()
    mock_vector_store_manager.add_documents.assert_called_once() # Changed from add_documents_to_collection
    called_with_docs_list = mock_vector_store_manager.add_documents.call_args[0][0] # Changed from add_documents_to_collection
    assert len(called_with_docs_list) == 1
    doc_sent_to_rag = called_with_docs_list[0]
    assert doc_sent_to_rag.page_content == sync_article_payload_data.content_markdown
    assert doc_sent_to_rag.metadata["cms_article_id"] == sync_article_payload_data.id # Changed key
    assert doc_sent_to_rag.metadata["title"] == sync_article_payload_data.title
    assert doc_sent_to_rag.metadata["vetting_status"] == sync_article_payload_data.vetting_status


@pytest.mark.asyncio
async def test_rag_sync_webhook_update_action(client: TestClient, mock_vector_store_manager: AsyncMock, auth_token: dict):
    """
    Test POST /api/v1/sync/rag with 'update' action.
    """
    # "update" is also handled by "upsert" in the current RAGSyncRequest model
    sync_article_payload_data_for_update = SyncArticleData(
        id="sync_test_article_update",
        title="Sync Test Update",
        slug="sync-test-update",
        content_markdown="Updated content for RAG.",
        tags=["sync", "update"],
        vetting_status="vetted", # Important for 'upsert'
        summary="An updated summary"
    )

    rag_sync_request_payload_for_update = RAGSyncRequest(
        action="upsert", # Still "upsert" for updates
        article_data=sync_article_payload_data_for_update
    )

    response = client.post("/api/v1/sync/rag", json=rag_sync_request_payload_for_update.model_dump(mode='json'), headers=auth_token)

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    assert response_json["article_id"] == sync_article_payload_data_for_update.id
    assert "upsert" in response_json["message"] # Message should reflect upsert
    
    # Depending on implementation, upsert might call add_documents or update_document.
    # The current sync router logic uses add_documents_to_collection for "upsert".
    # If it were to distinguish, it might call update_document_in_collection.
    # For now, assuming it calls add_documents as per existing router logic for "upsert".
    mock_vector_store_manager.delete_documents_by_metadata.assert_called_once()
    mock_vector_store_manager.add_documents.assert_called_once() # Changed from add_documents_to_collection
    called_with_docs_list_update = mock_vector_store_manager.add_documents.call_args[0][0] # Changed from add_documents_to_collection
    assert len(called_with_docs_list_update) == 1
    doc_sent_to_rag_update = called_with_docs_list_update[0]
    assert doc_sent_to_rag_update.page_content == sync_article_payload_data_for_update.content_markdown
    assert doc_sent_to_rag_update.metadata["cms_article_id"] == sync_article_payload_data_for_update.id # Changed key
    # mock_vector_store_manager.update_document_in_collection.assert_called_once() # This would be if upsert specifically called update
    # called_with_doc_arg = mock_vector_store_manager.update_document_in_collection.call_args[0][0]
    # assert called_with_doc_arg.page_content == sync_article_payload_data_for_update.content_markdown
    # assert called_with_doc_arg.metadata["article_id"] == sync_article_payload_data_for_update.id


@pytest.mark.asyncio
async def test_rag_sync_webhook_delete_action(client: TestClient, mock_vector_store_manager: AsyncMock, auth_token: dict):
    """
    Test POST /api/v1/sync/rag with 'delete' action.
    """
    sync_article_payload_data_for_delete = SyncArticleData(
        id="sync_test_article_delete",
        title="Sync Test Delete",
        slug="sync-test-delete",
        content_markdown="Content to be deleted from RAG.",
        tags=["sync", "delete"],
        vetting_status="archived", # Important for 'delete'
        summary="Archived summary"
    )

    rag_sync_request_payload_for_delete = RAGSyncRequest(
        action="delete",
        article_data=sync_article_payload_data_for_delete
    )

    response = client.post("/api/v1/sync/rag", json=rag_sync_request_payload_for_delete.model_dump(mode='json'), headers=auth_token)

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "success"
    assert response_json["article_id"] == sync_article_payload_data_for_delete.id
    assert "delete" in response_json["message"]
    
    # The router calls delete_documents_by_metadata
    mock_vector_store_manager.delete_documents_by_metadata.assert_called_once_with(
        {"cms_article_id": sync_article_payload_data_for_delete.id}
    )
    mock_vector_store_manager.add_documents.assert_not_called() # Ensure add_documents is not called for delete action
    # mock_vector_store_manager.delete_document_from_collection.assert_called_once_with( # This was the old expectation
    #     article_id=sync_article_payload_data_for_delete.id,
    #     collection_name=ANY 
    # )

@pytest.mark.asyncio
async def test_rag_sync_webhook_invalid_action(client: TestClient, mock_vector_store_manager: AsyncMock, auth_token: dict):
    """
    Test POST /api/v1/sync/rag with an invalid action.
    """
    # This data is for the article part of the payload, should match ArticleDB structure
    # if it were to be a valid RAGSyncRequest.
    # This data is for the SyncArticleData part of the payload.
    sync_article_data_for_invalid_payload = {
        "id": "sync_test_article_invalid",
        "title": "Sync Test Invalid",
        "slug": "sync-test-invalid",
        "content_markdown": "Content for invalid action.",
        "tags": ["sync", "invalid"], # author_id is not in SyncArticleData
        "vetting_status": "draft",
        "summary": "Invalid summary"
        # content_embedding, created_at, etc. are not part of SyncArticleData
    }
    # Pydantic models will validate the action enum, so sending a truly "invalid"
    # string for action would fail at serialization before hitting the endpoint logic.
    # This test is more about how the endpoint handles an action it's not programmed for,
    # if the enum was broader or if there was a default case.
    # However, with a strict enum, this scenario is less likely unless the enum changes.

    # Let's test with a valid action but for which no specific logic might exist,
    # or if the endpoint had a default "unknown action" path.
    # For now, the RAGSyncAction enum is strict (ADD, UPDATE, DELETE).
    # A direct invalid string would cause a 422 from Pydantic.
    
    # To test robustness, one might send a payload that's valid JSON but not a valid RAGSyncRequest
    invalid_json_payload_dict = {"action": "NONEXISTENT_ACTION", "article_data": sync_article_data_for_invalid_payload}
    
    response = client.post("/api/v1/sync/rag", json=invalid_json_payload_dict, headers=auth_token)
    
    # Expect a 422 Unprocessable Entity if Pydantic validation fails due to invalid enum value for 'action'
    # or if 'article_data' doesn't match SyncArticleData schema.
    assert response.status_code == 422 
    mock_vector_store_manager.add_documents.assert_not_called()
    mock_vector_store_manager.delete_documents_by_metadata.assert_not_called()
