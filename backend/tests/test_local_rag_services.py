"""
Unit Tests for Local RAG Services

Tests for:
- InferenceRouter: Queue-based routing logic
- LocalRewriter / GeminiRewriter: Query rewriting
- InfinityEmbeddings: Embedding generation
- RedisVectorCache: Vector cache operations

These tests use mocking to avoid requiring actual services to be running.
For integration tests with real services, see test_local_rag_integration.py.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Tuple


# ============================================================================
# InferenceRouter Tests
# ============================================================================

class TestInferenceRouter:
    """Tests for the InferenceRouter service."""
    
    @pytest.fixture
    def router(self):
        """Create a router instance with mocked rewriters."""
        with patch.dict('os.environ', {
            'MAX_LOCAL_QUEUE_DEPTH': '3',
            'LOCAL_TIMEOUT_SECONDS': '2.0',
        }):
            from backend.services.router import InferenceRouter
            router = InferenceRouter()
            return router
    
    @pytest.mark.asyncio
    async def test_router_initialization(self, router):
        """Test router initializes with correct config."""
        assert router.max_queue_depth == 3
        assert router.local_timeout == 2.0
    
    @pytest.mark.asyncio
    async def test_router_routes_to_local_when_available(self, router):
        """Test router routes to local rewriter when queue is not full."""
        # Mock local rewriter
        mock_local = AsyncMock()
        mock_local.rewrite = AsyncMock(return_value="What is Litecoin cryptocurrency?")
        router._local_rewriter = mock_local
        
        result = await router.rewrite("What is LTC?", [])
        
        assert result == "What is Litecoin cryptocurrency?"
        mock_local.rewrite.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_router_handles_no_search_needed(self, router):
        """Test router correctly returns NO_SEARCH_NEEDED."""
        mock_local = AsyncMock()
        mock_local.rewrite = AsyncMock(return_value="NO_SEARCH_NEEDED")
        router._local_rewriter = mock_local
        
        result = await router.rewrite("Thanks!", [])
        
        assert result == "NO_SEARCH_NEEDED"
    
    @pytest.mark.asyncio
    async def test_router_failover_on_timeout(self, router):
        """Test router fails over to Gemini on local timeout."""
        # Mock local rewriter to timeout
        async def slow_rewrite(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout
            return "should not reach here"
        
        mock_local = AsyncMock()
        mock_local.rewrite = slow_rewrite
        router._local_rewriter = mock_local
        router.local_timeout = 0.1  # Very short timeout
        
        # Mock Gemini rewriter for fallback
        mock_gemini = AsyncMock()
        mock_gemini.rewrite = AsyncMock(return_value="Gemini rewrite")
        router._gemini_rewriter = mock_gemini
        
        result = await router.rewrite("Test query", [])
        
        assert result == "Gemini rewrite"
        mock_gemini.rewrite.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rewrite_with_metadata(self, router):
        """Test rewrite_with_metadata returns full routing info."""
        mock_local = AsyncMock()
        mock_local.rewrite = AsyncMock(return_value="Rewritten query")
        router._local_rewriter = mock_local
        
        result = await router.rewrite_with_metadata("Test", [])
        
        assert result.rewritten_query == "Rewritten query"
        assert result.backend == "local"
        assert result.latency_seconds > 0


# ============================================================================
# Rewriter Tests
# ============================================================================

class TestLocalRewriter:
    """Tests for the LocalRewriter (Ollama) service."""
    
    @pytest.fixture
    def rewriter(self):
        """Create a LocalRewriter instance."""
        with patch.dict('os.environ', {
            'OLLAMA_URL': 'http://localhost:11434',
            'LOCAL_REWRITER_MODEL': 'llama3.2:3b',
        }):
            from backend.services.rewriter import LocalRewriter
            return LocalRewriter()
    
    @pytest.mark.asyncio
    async def test_rewriter_initialization(self, rewriter):
        """Test rewriter initializes with correct config."""
        assert "localhost:11434" in rewriter.ollama_url
        assert rewriter.model == "llama3.2:3b"
    
    @pytest.mark.asyncio
    async def test_rewriter_builds_prompt_with_history(self, rewriter):
        """Test prompt building includes chat history."""
        chat_history = [
            ("What is the $21 plan?", "The $21 plan is..."),
        ]
        prompt = rewriter._build_prompt("Does it expire?", chat_history)
        
        assert "What is the $21 plan?" in prompt
        assert "Does it expire?" in prompt
    
    @pytest.mark.asyncio
    async def test_rewriter_cleans_response(self, rewriter):
        """Test response cleaning removes quotes and prefixes."""
        assert rewriter._clean_response('"What is LTC?"', "test") == "What is LTC?"
        assert rewriter._clean_response("Rewritten Query: What is LTC?", "test") == "What is LTC?"
        assert rewriter._clean_response("NO_SEARCH_NEEDED", "test") == "NO_SEARCH_NEEDED"
        assert rewriter._clean_response("", "original") == "original"
    
    @pytest.mark.asyncio
    async def test_rewriter_calls_ollama_api(self, rewriter):
        """Test rewriter makes correct API call to Ollama."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Rewritten query"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await rewriter.rewrite("What is LTC?", [])
            
            assert result == "Rewritten query"
            mock_client_instance.post.assert_called_once()


class TestGeminiRewriter:
    """Tests for the GeminiRewriter service."""
    
    @pytest.fixture
    def rewriter(self):
        """Create a GeminiRewriter instance."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-api-key'}):
            from backend.services.rewriter import GeminiRewriter
            return GeminiRewriter()
    
    @pytest.mark.asyncio
    async def test_gemini_rewriter_initialization(self, rewriter):
        """Test Gemini rewriter initializes correctly."""
        assert rewriter.api_key == "test-api-key"
        assert "gemini" in rewriter.model.lower() or "flash" in rewriter.model.lower()
    
    @pytest.mark.asyncio
    async def test_gemini_rewriter_requires_api_key(self):
        """Test Gemini rewriter raises error without API key."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': ''}):
            from backend.services.rewriter import GeminiRewriter
            rewriter = GeminiRewriter()
            
            with pytest.raises(ValueError):
                await rewriter.rewrite("test", [])


# ============================================================================
# InfinityEmbeddings Tests
# ============================================================================

class TestInfinityEmbeddings:
    """Tests for the InfinityEmbeddings service."""
    
    @pytest.fixture
    def embeddings(self):
        """Create an InfinityEmbeddings instance."""
        with patch.dict('os.environ', {
            'INFINITY_URL': 'http://localhost:7997',
            'EMBEDDING_MODEL_ID': 'dunzhang/stella_en_1.5B_v5',
            'VECTOR_DIMENSION': '1024',
        }):
            from backend.services.infinity_adapter import InfinityEmbeddings
            return InfinityEmbeddings()
    
    @pytest.mark.asyncio
    async def test_embeddings_initialization(self, embeddings):
        """Test embeddings service initializes correctly."""
        assert "localhost:7997" in embeddings.infinity_url
        assert embeddings.model_id == "dunzhang/stella_en_1.5B_v5"
        assert embeddings.dimension == 1024
    
    @pytest.mark.asyncio
    async def test_embeddings_url_override(self):
        """Test URL can be overridden for host access."""
        from backend.services.infinity_adapter import InfinityEmbeddings
        embeddings = InfinityEmbeddings(infinity_url="http://custom:9999")
        assert embeddings.infinity_url == "http://custom:9999"
    
    @pytest.mark.asyncio
    async def test_embed_query_calls_api(self, embeddings):
        """Test embed_query makes correct API call."""
        mock_embedding = [0.1] * 1024
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": mock_embedding, "index": 0}]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await embeddings.embed_query("test query")
            
            assert len(result) == 1024
            mock_client_instance.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_documents_batch(self, embeddings):
        """Test embed_documents handles batches correctly."""
        mock_embeddings = [[0.1] * 1024, [0.2] * 1024]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {"embedding": mock_embeddings[0], "index": 0},
                    {"embedding": mock_embeddings[1], "index": 1},
                ]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance
            
            result = await embeddings.embed_documents(["doc1", "doc2"])
            
            assert len(result) == 2
            assert len(result[0]) == 1024
    
    @pytest.mark.asyncio
    async def test_embed_empty_list(self, embeddings):
        """Test embed_documents handles empty list."""
        result = await embeddings.embed_documents([])
        assert result == []


# ============================================================================
# RedisVectorCache Tests
# ============================================================================

class TestRedisVectorCache:
    """Tests for the RedisVectorCache service."""
    
    @pytest.fixture
    def cache(self):
        """Create a RedisVectorCache instance."""
        with patch.dict('os.environ', {
            'REDIS_STACK_URL': 'redis://localhost:6379',
            'REDIS_CACHE_INDEX_NAME': 'test:index',
            'VECTOR_DIMENSION': '1024',
            'REDIS_CACHE_SIMILARITY_THRESHOLD': '0.90',
        }):
            from backend.services.redis_vector_cache import RedisVectorCache
            return RedisVectorCache()
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache):
        """Test cache initializes with correct config."""
        assert "localhost:6379" in cache.redis_url
        assert cache.index_name == "test:index"
        assert cache.dimension == 1024
        assert cache.threshold == 0.90
    
    def test_vector_to_bytes_conversion(self, cache):
        """Test vector serialization."""
        vector = [0.1, 0.2, 0.3]
        bytes_data = cache._vector_to_bytes(vector)
        
        assert isinstance(bytes_data, bytes)
        
        # Convert back
        restored = cache._bytes_to_vector(bytes_data)
        assert len(restored) == 3
        assert abs(restored[0] - 0.1) < 0.0001
    
    def test_generate_key(self, cache):
        """Test cache key generation."""
        vector = [0.1] * 1024
        key = cache._generate_key(vector)
        
        assert key.startswith(cache.KEY_PREFIX)
        assert len(key) > len(cache.KEY_PREFIX)
    
    def test_url_masking(self, cache):
        """Test password masking in URL for logging."""
        masked = cache._mask_url("redis://:password123@localhost:6379")
        assert "password123" not in masked
        assert "***" in masked
        
        # URL without password should pass through
        clean = cache._mask_url("redis://localhost:6379")
        assert clean == "redis://localhost:6379"


# ============================================================================
# Integration Tests (with mocked external services)
# ============================================================================

class TestLocalRAGIntegration:
    """Integration tests for local RAG services working together."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_local_route(self):
        """Test full pipeline when routing to local services."""
        with patch.dict('os.environ', {
            'USE_LOCAL_REWRITER': 'true',
            'USE_INFINITY_EMBEDDINGS': 'true',
            'USE_REDIS_CACHE': 'true',
            'MAX_LOCAL_QUEUE_DEPTH': '3',
            'LOCAL_TIMEOUT_SECONDS': '2.0',
        }):
            from backend.services.router import InferenceRouter
            
            router = InferenceRouter()
            
            # Mock local rewriter
            mock_local = AsyncMock()
            mock_local.rewrite = AsyncMock(return_value="What is Litecoin cryptocurrency?")
            router._local_rewriter = mock_local
            
            # Test the rewrite
            result = await router.rewrite("What is LTC?", [])
            
            assert result == "What is Litecoin cryptocurrency?"
    
    @pytest.mark.asyncio
    async def test_feature_flags_disabled(self):
        """Test that services are not used when feature flags are disabled."""
        with patch.dict('os.environ', {
            'USE_LOCAL_REWRITER': 'false',
            'USE_INFINITY_EMBEDDINGS': 'false',
            'USE_REDIS_CACHE': 'false',
        }):
            # Re-import to get fresh flag values
            import importlib
            import backend.rag_pipeline as rag
            importlib.reload(rag)
            
            assert rag.USE_LOCAL_REWRITER is False
            assert rag.USE_INFINITY_EMBEDDINGS is False
            assert rag.USE_REDIS_CACHE is False


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

