"""
Shared pytest fixtures for test suite.
Provides mocks for external services and test data fixtures.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root and backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(backend_dir)
# Add both project root (for backend.* imports) and backend dir (for data_ingestion.* imports)
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Set required environment variables for imports (rag_pipeline checks at import time)
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = "test-key"
if not os.getenv("MONGO_URI"):
    os.environ["MONGO_URI"] = "mongodb://test"

import pytest
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient
import mongomock
from typing import Dict, Any, List

# Enable asyncio for tests
pytest_plugins = "pytest_asyncio"

# Configure pytest to set up paths before importing test modules
def pytest_configure(config):
    """Configure pytest - set up Python path before test collection."""
    # Ensure paths are set up (in case conftest is loaded after test files)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(backend_dir)
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

# Load test data fixtures
@pytest.fixture(scope="session")
def test_kb_docs():
    """Load deterministic test knowledge base documents."""
    fixture_path = Path(__file__).parent / "fixtures" / "kb_docs.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    # Return default test docs if file doesn't exist yet
    return [
        {
            "id": "doc1",
            "title": "Litecoin History",
            "markdown": "Litecoin was created by Charlie Lee in October 2011. It is a peer-to-peer cryptocurrency.",
            "status": "published",
            "metadata": {"author": "test", "tags": ["history"]}
        },
        {
            "id": "doc2",
            "title": "Litecoin Features",
            "markdown": "Litecoin features include: Faster blocks (2.5 minutes), Scrypt algorithm, SegWit support.",
            "status": "published",
            "metadata": {"author": "test", "tags": ["features"]}
        },
        {
            "id": "doc3",
            "title": "Draft Document",
            "markdown": "This is a draft document that should not appear in search results.",
            "status": "draft",
            "metadata": {"author": "test"}
        }
    ]

@pytest.fixture(scope="session")
def test_questions():
    """Load test user questions."""
    fixture_path = Path(__file__).parent / "fixtures" / "test_questions.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    # Return default test questions if file doesn't exist yet
    return [
        {"query": "Who created Litecoin?", "expected": "Charlie Lee"},
        {"query": "When was it created?", "expected": "2011"},
        {"query": "What are Litecoin's features?", "expected": "faster blocks"}
    ]

# Mock Redis client (works for both sync and async tests)
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing (works for both sync and async)."""
    redis_mock = AsyncMock()
    
    # Default return values for common operations
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.incrbyfloat = AsyncMock(return_value=1.0)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zremrangebyscore = AsyncMock(return_value=1)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zrange = AsyncMock(return_value=[])
    redis_mock.hget = AsyncMock(return_value="0")
    redis_mock.hincrby = AsyncMock(return_value=100)
    redis_mock.hset = AsyncMock(return_value=1)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.aclose = AsyncMock()
    
    # Store for test data
    redis_mock._storage = {}
    
    # Override get/set to use storage
    async def mock_get(key):
        return redis_mock._storage.get(key)
    
    async def mock_set(key, value, *args, **kwargs):
        redis_mock._storage[key] = value
        return True
    
    async def mock_setex(key, time, value):
        redis_mock._storage[key] = value
        return True
    
    redis_mock.get = mock_get
    redis_mock.set = mock_set
    redis_mock.setex = mock_setex
    
    yield redis_mock
    
    # Cleanup
    redis_mock._storage.clear()

# Mock MongoDB client (using mongomock for realism)
@pytest.fixture
def mock_mongo():
    """Mock MongoDB client using mongomock for realistic behavior."""
    mock_client = mongomock.MongoClient()
    yield mock_client
    mock_client.close()

# Mock Motor (async MongoDB) client
@pytest.fixture
def mock_motor_client(mock_mongo):
    """Mock Motor async MongoDB client wrapping mongomock."""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Create a mock without spec restriction to allow dynamic attributes like 'admin'
    motor_mock = MagicMock()
    
    # Get the mongomock database
    db = mock_mongo["test_db"]
    
    # Mock database access
    def get_database(name):
        return mock_mongo[name]
    
    motor_mock.__getitem__ = lambda self, name: mock_mongo[name]
    motor_mock.get_database = Mock(return_value=db)
    motor_mock.close = AsyncMock()
    
    # Mock admin.command - create admin as a mock with command method
    admin_mock = MagicMock()
    admin_mock.command = AsyncMock(return_value={"ok": 1})
    motor_mock.admin = admin_mock
    
    yield motor_mock

# Mock Google LLM API
@pytest.fixture
def mock_llm(monkeypatch):
    """Mock Google Generative AI for cost control and deterministic responses."""
    mock_response = MagicMock()
    mock_response.text = "Mock LLM response based on the provided context."
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 20
    mock_response.usage_metadata.total_token_count = 30
    
    mock_generate = AsyncMock(return_value=mock_response)
    
    # Patch the LangChain Google Generative AI
    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
        mock_generate
    )
    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI.invoke",
        Mock(return_value=mock_response)
    )
    
    yield mock_generate

# Isolated vector store with test data
@pytest.fixture
def test_vector_store(test_kb_docs, tmp_path, monkeypatch):
    """Setup isolated FAISS vector store with test docs using tmp_path for isolation."""
    from langchain_core.documents import Document
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    import shutil
    
    # Use tmp_path for temporary FAISS index to avoid collisions
    index_dir = tmp_path / "faiss_index"
    index_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize embeddings (using local model)
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        # Create documents from test KB
        documents = []
        for doc in test_kb_docs:
            if doc.get("status") == "published":  # Only published docs
                documents.append(Document(
                    page_content=doc["markdown"],
                    metadata={
                        "id": doc["id"],
                        "title": doc["title"],
                        "status": doc["status"],
                        **doc.get("metadata", {})
                    }
                ))
        
        # Create FAISS index
        if documents:
            vector_store = FAISS.from_documents(documents, embeddings)
        else:
            # Create empty index with dummy text
            vector_store = FAISS.from_texts(["dummy"], embeddings)
        
        yield vector_store
        
    finally:
        # Cleanup
        if index_dir.exists():
            shutil.rmtree(index_dir, ignore_errors=True)

# FastAPI TestClient with dependency overrides
@pytest.fixture
def client(mock_redis, mock_motor_client, mock_llm, monkeypatch):
    """FastAPI TestClient with mocked dependencies."""
    from backend.main import app
    from backend import dependencies
    from backend import redis_client
    
    # Override dependencies
    async def override_get_redis_client():
        return mock_redis
    
    async def override_get_mongo_client():
        return mock_motor_client
    
    async def override_get_cms_db():
        db = mock_motor_client["test_db"]
        return db["cms_articles"]
    
    async def override_get_user_questions_collection():
        db = mock_motor_client["test_db"]
        return db["user_questions"]
    
    # Apply overrides
    app.dependency_overrides[dependencies.get_mongo_client] = override_get_mongo_client
    app.dependency_overrides[dependencies.get_cms_db] = override_get_cms_db
    app.dependency_overrides[dependencies.get_user_questions_collection] = override_get_user_questions_collection
    
    # Override Redis client (synchronous access for TestClient)
    # Note: TestClient runs in a thread, so we need to handle async properly
    original_get_redis = redis_client.get_redis_client
    monkeypatch.setattr(redis_client, "get_redis_client", lambda: mock_redis)
    
    # Override environment variables for testing
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://test")
    monkeypatch.setenv("REDIS_URL", "redis://test")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret-key")
    
    # Create TestClient with lifespan disabled for testing
    # We'll use a context manager to ensure cleanup
    test_client = TestClient(app)
    
    try:
        yield test_client
    finally:
        # Cleanup overrides
        app.dependency_overrides.clear()
        # Restore original Redis client getter
        monkeypatch.setattr(redis_client, "get_redis_client", original_get_redis)

# Helper fixture for webhook HMAC signature generation
@pytest.fixture
def webhook_secret():
    """Test webhook secret for HMAC signature generation."""
    return "test-webhook-secret-key"

@pytest.fixture
def generate_hmac_signature(webhook_secret):
    """Helper to generate HMAC signatures for webhook tests."""
    import hmac
    import hashlib
    
    def _generate(payload: str, secret: str = None) -> str:
        if secret is None:
            secret = webhook_secret
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    return _generate

# Helper fixture for valid webhook headers
@pytest.fixture
def valid_webhook_headers(generate_hmac_signature, webhook_secret):
    """Generate valid webhook headers for testing."""
    def _generate_headers(payload: str) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        signature = generate_hmac_signature(payload, webhook_secret)
        return {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": timestamp
        }
    return _generate_headers

