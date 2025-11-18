import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.data_models import DataSource, DataSourceUpdate # Import DataSourceUpdate
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
import os
from dotenv import load_dotenv
from fastapi import status # Import status

# Load environment variables for tests
load_dotenv()

# Define test MongoDB client and collections
TEST_MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/test_litecoin_rag_chat")
test_client = MongoClient(TEST_MONGO_URI)
test_db = test_client.test_litecoin_rag_chat
test_data_sources_collection = test_db.data_sources
test_litecoin_docs_collection = test_db.litecoin_docs

# Import the dependency functions from the sources router
from backend.api.v1.sources import get_data_sources_collection, get_litecoin_docs_collection

# Override the dependency functions in the main app for testing
app.dependency_overrides[get_data_sources_collection] = lambda: test_data_sources_collection
app.dependency_overrides[get_litecoin_docs_collection] = lambda: test_litecoin_docs_collection

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_db_before_each_test():
    """Clears the test database collections before each test."""
    test_data_sources_collection.delete_many({})
    test_litecoin_docs_collection.delete_many({})
    yield
    # Cleanup after test
    test_data_sources_collection.delete_many({})
    test_litecoin_docs_collection.delete_many({})

def test_create_data_source():
    """Test creating a new data source."""
    source_data = {
        "name": "Test Article",
        "type": "markdown",
        "uri": "knowledge_base/test_articles/test.md"
    }
    response = client.post("/api/v1/sources", json=source_data)
    assert response.status_code == status.HTTP_201_CREATED
    created_source = DataSource(**response.json())
    assert created_source.name == source_data["name"]
    assert created_source.type == source_data["type"]
    assert created_source.uri == source_data["uri"]
    assert created_source.status == "ingesting" # Initial status after creation
    assert created_source.id is not None

    # Verify it's in the database
    db_source = test_data_sources_collection.find_one({"_id": ObjectId(created_source.id)})
    assert db_source is not None
    assert db_source["name"] == source_data["name"]

def test_create_data_source_duplicate_uri():
    """Test creating a data source with a duplicate URI."""
    source_data = {
        "name": "Test Article",
        "type": "markdown",
        "uri": "knowledge_base/test_articles/test.md"
    }
    client.post("/api/v1/sources", json=source_data) # First creation
    response = client.post("/api/v1/sources", json=source_data) # Second creation
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Data source with this URI already exists." in response.json()["detail"]

def test_get_all_data_sources():
    """Test retrieving all data sources."""
    source1_data = {"name": "Source 1", "type": "web", "uri": "http://example.com/1"}
    source2_data = {"name": "Source 2", "type": "github", "uri": "https://github.com/repo/2"}
    client.post("/api/v1/sources", json=source1_data)
    client.post("/api/v1/sources", json=source2_data)

    response = client.get("/api/v1/sources")
    assert response.status_code == status.HTTP_200_OK
    sources = response.json()
    assert len(sources) == 2
    assert any(s["name"] == "Source 1" for s in sources)
    assert any(s["name"] == "Source 2" for s in sources)

def test_get_single_data_source():
    """Test retrieving a single data source by ID."""
    source_data = {"name": "Single Source", "type": "markdown", "uri": "knowledge_base/single.md"}
    post_response = client.post("/api/v1/sources", json=source_data)
    source_id = post_response.json()["id"]

    response = client.get(f"/api/v1/sources/{source_id}")
    assert response.status_code == status.HTTP_200_OK
    retrieved_source = DataSource(**response.json())
    assert retrieved_source.id == source_id
    assert retrieved_source.name == source_data["name"]

def test_get_single_data_source_not_found():
    """Test retrieving a non-existent data source."""
    response = client.get("/api/v1/sources/60d5ecf0f8c7b7e1f0e3e3e3") # Non-existent but valid ObjectId format
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Data source not found." in response.json()["detail"]

def test_get_single_data_source_invalid_id():
    """Test retrieving a data source with an invalid ID format."""
    response = client.get("/api/v1/sources/invalid-id")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid source ID format." in response.json()["detail"]

def test_update_data_source():
    """Test updating an existing data source."""
    source_data = {"name": "Old Name", "type": "markdown", "uri": "knowledge_base/old.md"}
    post_response = client.post("/api/v1/sources", json=source_data)
    source_id = post_response.json()["id"]

    update_model = DataSourceUpdate(name="New Name", status="active")
    updated_data_json = update_model.model_dump(exclude_unset=True)
    
    response = client.put(f"/api/v1/sources/{source_id}", json=updated_data_json)
    assert response.status_code == status.HTTP_200_OK
    updated_source = DataSource(**response.json())
    assert updated_source.id == source_id
    assert updated_source.name == "New Name"
    assert updated_source.status == "active"
    assert updated_source.updated_at > updated_source.created_at # Ensure updated_at is changed

def test_update_data_source_uri_change_deletes_embeddings():
    """
    Test updating a data source's URI, which should trigger deletion of old embeddings.
    """
    old_uri = "knowledge_base/old_uri.md"
    new_uri = "knowledge_base/new_uri.md"
    source_data = {"name": "URI Change Test", "type": "markdown", "uri": old_uri}
    post_response = client.post("/api/v1/sources", json=source_data)
    source_id = post_response.json()["id"]

    # Simulate existing embeddings for the old URI
    test_litecoin_docs_collection.insert_many([
        {"page_content": "chunk 1", "source_uri": old_uri, "embedding": [0.1]*768},
        {"page_content": "chunk 2", "source_uri": old_uri, "embedding": [0.2]*768},
        {"page_content": "chunk 3", "source_uri": "other_uri.md", "embedding": [0.3]*768},
    ])
    assert test_litecoin_docs_collection.count_documents({"source_uri": old_uri}) == 2
    assert test_litecoin_docs_collection.count_documents({"source_uri": "other_uri.md"}) == 1

    update_model = DataSourceUpdate(uri=new_uri)
    updated_data_json = update_model.model_dump(exclude_unset=True)
    
    response = client.put(f"/api/v1/sources/{source_id}", json=updated_data_json)
    assert response.status_code == status.HTTP_200_OK
    updated_source = DataSource(**response.json())
    assert updated_source.uri == new_uri
    assert updated_source.status == "ingesting" # Status should change to ingesting

    # Verify old embeddings are deleted
    assert test_litecoin_docs_collection.count_documents({"source_uri": old_uri}) == 0
    # Other embeddings should remain
    assert test_litecoin_docs_collection.count_documents({"source_uri": "other_uri.md"}) == 1
    # Note: In a real scenario, new embeddings for 'new_uri' would be created by ingestion process.
    # This test verifies that the URI update triggers deletion of old embeddings.

def test_delete_data_source():
    """Test deleting a data source and its associated embeddings."""
    source_data = {"name": "Delete Test", "type": "markdown", "uri": "knowledge_base/delete.md"}
    post_response = client.post("/api/v1/sources", json=source_data)
    source_id = post_response.json()["id"]
    source_uri = source_data["uri"]

    # Simulate existing embeddings for this source
    test_litecoin_docs_collection.insert_many([
        {"page_content": "chunk A", "source_uri": source_uri, "embedding": [0.1]*768},
        {"page_content": "chunk B", "source_uri": source_uri, "embedding": [0.2]*768},
        {"page_content": "chunk C", "source_uri": "other_source.md", "embedding": [0.3]*768},
    ])
    assert test_data_sources_collection.count_documents({}) == 1
    assert test_litecoin_docs_collection.count_documents({"source_uri": source_uri}) == 2

    response = client.delete(f"/api/v1/sources/{source_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify data source record is deleted
    assert test_data_sources_collection.count_documents({}) == 0
    # Verify associated embeddings are deleted
    assert test_litecoin_docs_collection.count_documents({"source_uri": source_uri}) == 0
    # Verify other embeddings are not deleted
    assert test_litecoin_docs_collection.count_documents({"source_uri": "other_source.md"}) == 1

def test_delete_data_source_not_found():
    """Test deleting a non-existent data source."""
    response = client.delete("/api/v1/sources/60d5ecf0f8c7b7e1f0e3e3e3")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Data source not found." in response.json()["detail"]

def test_delete_data_source_invalid_id():
    """Test deleting a data source with an invalid ID format."""
    response = client.delete("/api/v1/sources/invalid-id")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid source ID format." in response.json()["detail"]
