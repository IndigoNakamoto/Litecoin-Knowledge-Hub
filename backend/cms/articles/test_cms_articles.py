import pytest
from datetime import datetime # Added import
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import AsyncMock, ANY, MagicMock # Removed patch, Added ANY, MagicMock
from pytest_mock import MockerFixture # Added for mocker

from backend.main import app  # Assuming your FastAPI app instance is named 'app'
from backend.cms.articles import crud
from backend.cms.articles.models import ArticleCreate, ArticleUpdate, ArticleDB
from backend.cms.auth.security import create_access_token # For authentication if needed
from backend.dependencies import get_cms_db # Changed from get_db

# Test client for making API requests
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Unit Tests for CRUD operations ---

# This fixture is for unit tests that directly call CRUD functions.
# It should mock the MongoDB collection object.
@pytest.fixture
def mock_mongo_collection():
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.update_one = AsyncMock()
    # Add other methods like find, delete_one, count_documents as needed by your CRUD functions
    return collection

@pytest.mark.asyncio
async def test_create_article_generates_embedding(mock_mongo_collection: AsyncMock, mocker: MockerFixture):
    """
    Test that creating an article also generates its content_embedding.
    """
    article_in_data = {
        "title": "Test Article for Embedding",
        "slug": "test-article-for-embedding",
        "content_markdown": "This is the content of the test article.",
        "author_id": "test_author",
        "tags": ["test", "embedding"],
    }
    article_in = ArticleCreate(**article_in_data)

    # Mock the result of insert_one to include an _id
    mock_mongo_collection.insert_one.return_value = AsyncMock(inserted_id="new_article_mongo_id")
    # Mock find_one to return the "inserted" document for the refresh part of create_article
    # This needs to be a dict that can be parsed into ArticleDB
    def mock_find_one_after_insert(filter_query):
        if filter_query["_id"] == "new_article_mongo_id":
            # Construct what the document would look like in DB after insert and embedding
            # The actual embedding value comes from the mock_get_embedding patch
            return {
                "_id": "new_article_mongo_id",
                **article_in.model_dump(exclude_none=True), # Use model_dump for Pydantic V2
                "content_embedding": [0.1, 0.2, 0.3], # This is set by the mocked get_embedding
                "vetting_status": "draft", # Default from CRUD
                "created_at": datetime.utcnow(), # Set by CRUD
                "updated_at": datetime.utcnow(), # Set by CRUD
                "version": 1, # Default from CRUD
                "is_latest_active": True, # Default from CRUD
                "canonical_article_id": "new_article_mongo_id", # Set by CRUD, should be a string
                "published_at": None
            }
        return None
    mock_mongo_collection.find_one = AsyncMock(side_effect=mock_find_one_after_insert)

    # FIXED: Mock the entire embedding model instead of trying to patch the method
    mock_embedding_model = MagicMock()
    mock_embedding_model.embed_query.return_value = [0.1, 0.2, 0.3]
    
    # Replace the embedding model in the crud module
    mocker.patch.object(crud, 'document_embedding_model', mock_embedding_model)
    
    # Mock the global articles_collection used by crud functions
    mocker.patch.object(crud, 'articles_collection', mock_mongo_collection)

    created_article_db = await crud.create_article(article_data=article_in)

    # Check if the mock was called
    mock_embedding_model.embed_query.assert_called_once_with(article_in.content_markdown)
    
    # Check that insert_one was called
    mock_mongo_collection.insert_one.assert_called_once()
    inserted_document_arg = mock_mongo_collection.insert_one.call_args[0][0]
    
    assert inserted_document_arg is not None
    assert inserted_document_arg["title"] == article_in.title
    assert "content_embedding" in inserted_document_arg
    assert isinstance(inserted_document_arg["content_embedding"], list)
    assert inserted_document_arg["content_embedding"] == [0.1, 0.2, 0.3]
    assert inserted_document_arg["vetting_status"] == "draft" # Check default

    # Check the returned ArticleDB object
    assert created_article_db is not None
    assert created_article_db.id == "new_article_mongo_id"
    assert created_article_db.title == article_in.title
    assert created_article_db.content_embedding == [0.1, 0.2, 0.3]
    assert created_article_db.vetting_status == "draft"


@pytest.mark.asyncio
async def test_update_article_updates_embedding(mock_mongo_collection: AsyncMock, mocker: MockerFixture):
    """
    Test that updating an article's content also updates its content_embedding.
    """
    # Use a valid ObjectId format (24-character hex string)
    valid_article_id = "507f1f77bcf86cd799439011"
    
    original_db_doc_dict = {
        "_id": valid_article_id,
        "title": "Original Title",
        "slug": "original-title",
        "content_markdown": "Original content.",
        "author_id": "test_author",
        "tags": ["original"],
        "vetting_status": "draft",
        "content_embedding": [0.1, 0.1, 0.1],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "canonical_article_id": "orig-canon-id",
        "version": 1,
        "is_latest_active": True,
        "published_at": None
    }
    
    article_update_payload = ArticleUpdate(
        content_markdown="Updated content for embedding test.",
        title="Updated Title"
    )
    new_embedding = [0.9, 0.8, 0.7]
    
    # Updated document after the update operation
    updated_db_doc_dict = {
        **original_db_doc_dict,
        "title": article_update_payload.title,
        "content_markdown": article_update_payload.content_markdown,
        "content_embedding": new_embedding,
        "updated_at": datetime.utcnow(),
    }

    # Set up find_one to return different values for different calls
    # First call: return original document (for current state check)
    # Second call: return updated document (after update operation)
    find_one_call_count = 0
    def mock_find_one_side_effect(filter_query):
        nonlocal find_one_call_count
        find_one_call_count += 1
        
        query_id = filter_query.get("_id")
        if query_id is not None:
            query_id_str = str(query_id)
            if query_id_str == valid_article_id or query_id == valid_article_id:
                if find_one_call_count == 1:
                    return original_db_doc_dict
                else:
                    return updated_db_doc_dict
        return None
    
    mock_mongo_collection.find_one.side_effect = mock_find_one_side_effect
    mock_mongo_collection.update_one = AsyncMock()

    # Mock the entire embedding model instead of trying to patch the method
    mock_embedding_model = MagicMock()
    mock_embedding_model.embed_query.return_value = new_embedding
    
    # Replace the embedding model in the crud module
    mocker.patch.object(crud, 'document_embedding_model', mock_embedding_model)
    
    # Mock the global articles_collection used by crud functions
    mocker.patch.object(crud, 'articles_collection', mock_mongo_collection)
    # Mock httpx.AsyncClient for the webhook call
    mock_httpx_client_post = mocker.patch('httpx.AsyncClient.post', new_callable=AsyncMock)

    updated_article_db = await crud.update_article(
        article_id=valid_article_id,
        article_data=article_update_payload
    )

    # Check if the mock was called
    mock_embedding_model.embed_query.assert_called_once_with(article_update_payload.content_markdown)
    assert mock_mongo_collection.find_one.call_count == 2  # Called twice: before and after update
    mock_mongo_collection.update_one.assert_called_once()
    mock_httpx_client_post.assert_not_called() # Assert webhook is not called for draft updates
    
    update_filter_arg = mock_mongo_collection.update_one.call_args[0][0]
    update_doc_arg = mock_mongo_collection.update_one.call_args[0][1]["$set"]
    
    assert update_filter_arg == {"_id": ANY}  # ObjectId will be used
    assert update_doc_arg["content_markdown"] == article_update_payload.content_markdown
    assert update_doc_arg["title"] == article_update_payload.title
    assert update_doc_arg["content_embedding"] == new_embedding
    assert "updated_at" in update_doc_arg

    assert updated_article_db is not None
    assert updated_article_db.content_embedding == new_embedding
    assert updated_article_db.content_markdown == article_update_payload.content_markdown
    assert updated_article_db.title == article_update_payload.title


# --- Integration Tests for API Endpoints ---

# This fixture provides a mock MongoDB collection for API tests via dependency override.
@pytest.fixture
def mock_mongodb_collection_for_api():
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.find = AsyncMock() # For search_articles_vector
    return collection

@pytest.fixture(autouse=True)
def override_api_db_dependency(mock_mongodb_collection_for_api):
    # This assumes your get_cms_db dependency in backend/dependencies.py
    # returns the MongoDB collection object.
    original_get_cms_db = app.dependency_overrides.get(get_cms_db)
    app.dependency_overrides[get_cms_db] = lambda: mock_mongodb_collection_for_api
    
    # Mock get_current_active_user
    from backend.cms.auth.router import get_current_active_user
    from backend.cms.users.models import User as UserModel # Alias to avoid conflict if User is used elsewhere
    
    mock_user = UserModel(
        id="testuserid", 
        email="test@example.com", 
        is_active=True, 
        is_superuser=False, 
        hashed_password="fakehashedpassword",
        created_at=datetime.utcnow(), # Added
        updated_at=datetime.utcnow()  # Added
    )
    original_get_current_active_user = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    
    yield
    
    if original_get_cms_db:
        app.dependency_overrides[get_cms_db] = original_get_cms_db
    else:
        del app.dependency_overrides[get_cms_db]
        
    if original_get_current_active_user:
        app.dependency_overrides[get_current_active_user] = original_get_current_active_user
    else:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
async def test_create_article_api_generates_embedding(client: TestClient, mock_mongodb_collection_for_api: AsyncMock, mocker: MockerFixture):
    """
    Test POST /api/v1/articles creates an article with an embedding.
    """
    api_article_data_for_creation = {
        "title": "API Test Article",
        "slug": "api-test-article",
        "content_markdown": "Content for API test.",
        "author_id": "api_author",
        "tags": ["api", "test"],
    }

    # Create a datetime object once to ensure consistency if used in assertions
    now = datetime.utcnow()
    mock_return_data_for_create_api = {
        "_id": "mock_api_new_article_id", # Key should be '_id' for model_validate
        "title": api_article_data_for_creation["title"],
        "slug": api_article_data_for_creation["slug"],
        "content_markdown": api_article_data_for_creation["content_markdown"],
        "author_id": api_article_data_for_creation["author_id"],
        "tags": api_article_data_for_creation["tags"],
        "content_embedding": [0.5, 0.5, 0.5],
        "vetting_status": "draft",
        "created_at": now,
        "updated_at": now,
        "canonical_article_id": "mock-canon-id-create",
        "version": 1,
        "is_latest_active": True,
        "published_at": None
    }

    validated_mock_return = ArticleDB.model_validate(mock_return_data_for_create_api)

    # Mock the CRUD function called by the router
    mock_router_calls_crud_create = mocker.patch('backend.cms.articles.router.crud.create_article', new_callable=AsyncMock)
    mock_router_calls_crud_create.return_value = validated_mock_return
    
    # Make the API call
    response = client.post("/api/v1/articles/", json=api_article_data_for_creation)

    assert response.status_code == 201 # Ensure it's 201 Created
    response_data = response.json()
    assert response_data["title"] == api_article_data_for_creation["title"]
    assert "content_embedding" in response_data
    assert isinstance(response_data["content_embedding"], list)
    assert response_data["content_embedding"] == [0.5, 0.5, 0.5]
    
    # Check that the router called crud.create_article with the correct Pydantic model
    mock_router_calls_crud_create.assert_called_once()
    
    # FIXED: Check the actual parameter names used by the router
    # Looking at router.py, it uses: crud.create_article(db=db, article_in=article)
    call_args = mock_router_calls_crud_create.call_args
    if call_args[1]:  # Check keyword arguments
        # Router uses keyword arguments
        if 'article_in' in call_args[1]:
            assert isinstance(call_args[1]['article_in'], ArticleCreate)
            assert call_args[1]['article_in'].title == api_article_data_for_creation['title']
        elif 'article_data' in call_args[1]:
            assert isinstance(call_args[1]['article_data'], ArticleCreate)
            assert call_args[1]['article_data'].title == api_article_data_for_creation['title']
    else:
        # Router uses positional arguments - check first non-db argument
        # Assuming first arg is db, second is article
        assert isinstance(call_args[0][1], ArticleCreate)
        assert call_args[0][1].title == api_article_data_for_creation['title']


@pytest.mark.asyncio
async def test_search_articles_api(client: TestClient, mock_mongodb_collection_for_api: AsyncMock, mocker: MockerFixture):
    """
    Test GET /api/v1/articles/search returns relevant articles.
    """
    search_query = "find this content"
    # These are ArticleDB instances that `crud.search_articles` would return
    mock_search_results_from_crud = [
        ArticleDB(
            _id="article1", title="Relevant Article 1", content_markdown="Content that matches 'find this content'", # Use _id
            slug="relevant-article-1", author_id="author1", tags=[], vetting_status="vetted",
            content_embedding=[0.1, 0.2, 0.3], created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            canonical_article_id="canon1", version=1, is_latest_active=True, published_at=datetime.utcnow()
        ),
        ArticleDB(
            _id="article2", title="Less Relevant Article", content_markdown="Some other text", # Use _id
            slug="less-relevant-article", author_id="author2", tags=[], vetting_status="draft",
            content_embedding=[0.7, 0.8, 0.9], created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            canonical_article_id="canon2", version=1, is_latest_active=True, published_at=None
        )
    ]
    # Convert ArticleDB instances to dicts with 'id' key, as if article_helper was applied,
    # then validated by ArticleRead for the response.
    mock_search_results_as_dicts = [
        obj.model_dump(by_alias=True) for obj in mock_search_results_from_crud
    ]

    # The router calls crud.search_articles(query_text=query, top_k=limit)
    mock_crud_search_articles_patch = mocker.patch('backend.cms.articles.router.crud.search_articles', new_callable=AsyncMock)
    mock_crud_search_articles_patch.return_value = mock_search_results_as_dicts # Return list of dicts

    response = client.get(f"/api/v1/articles/search/?query={search_query}")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["title"] == "Relevant Article 1"
        
    mock_crud_search_articles_patch.assert_called_once_with(query_text=search_query, top_k=10) # Default limit is 10


@pytest.mark.asyncio
async def test_search_articles_api_no_results(client: TestClient, mock_mongodb_collection_for_api: AsyncMock, mocker: MockerFixture):
    """
    Test GET /api/v1/articles/search returns empty list for no matches.
    """
    search_query = "unfindable gibberish query"
    # Router calls crud.search_articles(query_text=query, top_k=limit)
    mock_search_articles_patch = mocker.patch('backend.cms.articles.router.crud.search_articles', new_callable=AsyncMock)
    mock_search_articles_patch.return_value = []
    
    response = client.get(f"/api/v1/articles/search/?query={search_query}")

    assert response.status_code == 200
    assert response.json() == []
    mock_search_articles_patch.assert_called_once_with(query_text=search_query, top_k=10) # Default limit is 10