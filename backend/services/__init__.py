"""
Local RAG Services Module

This module provides services for high-performance local RAG processing
with automatic cloud spillover. Components include:

- InferenceRouter: Routes queries to local (Ollama) or cloud (Gemini) rewriters
- LocalRewriter/GeminiRewriter: Query rewriting with context awareness  
- InfinityEmbeddings: Local 1024-dim embeddings via Infinity service
- RedisVectorCache: Redis Stack vector cache with HNSW index

See docs/features/DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md for details.
"""

__all__ = []

# Lazy imports to avoid errors when services are not configured
try:
    from backend.services.infinity_adapter import InfinityEmbeddings, InfinityEmbeddingsLangChain
    __all__.extend(["InfinityEmbeddings", "InfinityEmbeddingsLangChain"])
except ImportError:
    pass

try:
    from backend.services.router import InferenceRouter
    __all__.append("InferenceRouter")
except ImportError:
    pass

try:
    from backend.services.rewriter import LocalRewriter, GeminiRewriter
    __all__.extend(["LocalRewriter", "GeminiRewriter"])
except ImportError:
    pass

try:
    from backend.services.redis_vector_cache import RedisVectorCache
    __all__.append("RedisVectorCache")
except ImportError:
    pass

