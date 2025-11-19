"""
Caching utilities for RAG pipeline performance optimization.
"""

import hashlib
import json
import time
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class QueryCache:
    """
    In-memory cache for query responses with TTL and size limits.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):  # 1 hour TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

    def _generate_key(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Generate a unique cache key for the query and conversation context."""
        # Include recent conversation context in the key
        recent_history = chat_history[-3:] if len(chat_history) > 3 else chat_history  # Last 3 exchanges
        normalized_query = query.strip().lower()

        # Only include recent user messages that add new context and differ from the current query
        history_entries = []
        for exchange in recent_history:
            if not isinstance(exchange, (tuple, list)) or len(exchange) == 0:
                continue

            human_message = exchange[0] if len(exchange) > 0 else ""
            if not isinstance(human_message, str):
                continue

            normalized_message = human_message.strip().lower()
            if normalized_message and normalized_message != normalized_query:
                history_entries.append(normalized_message)

        # Preserve order but remove duplicates to avoid unnecessary cache fragmentation
        seen = set()
        deduped_history = []
        for msg in history_entries:
            if msg not in seen:
                deduped_history.append(msg)
                seen.add(msg)

        key_data = {
            "query": normalized_query,
            "history": deduped_history,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, chat_history: List[Tuple[str, str]]) -> Optional[Tuple[str, List]]:
        """Get cached response if available and not expired."""
        key = self._generate_key(query, chat_history)

        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry['timestamp'] < self.ttl_seconds:
                    return entry['answer'], entry['sources']
                else:
                    # Expired, remove it
                    del self.cache[key]

        return None

    def set(self, query: str, chat_history: List[Tuple[str, str]], answer: str, sources: List) -> None:
        """Cache a query response."""
        key = self._generate_key(query, chat_history)

        with self._lock:
            # Remove oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]

            self.cache[key] = {
                'answer': answer,
                'sources': sources,
                'timestamp': time.time(),
                'query': query
            }

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': 0  # Would need to track hits/misses for this
            }


class EmbeddingCache:
    """
    Cache for query embeddings to reduce API calls for similar queries.
    """

    def __init__(self, max_size: int = 500, similarity_threshold: float = 0.95):
        self.cache: Dict[str, np.ndarray] = {}
        self.query_map: Dict[str, str] = {}  # query -> cache_key
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self._lock = threading.Lock()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for better caching."""
        return query.strip().lower()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def get_similar(self, query: str) -> Optional[np.ndarray]:
        """Get cached embedding for a similar query if available."""
        normalized_query = self._normalize_query(query)

        with self._lock:
            # Check for exact match first
            if normalized_query in self.query_map:
                cache_key = self.query_map[normalized_query]
                if cache_key in self.cache:
                    return self.cache[cache_key]

            # Check for similar queries
            for cached_query, cache_key in self.query_map.items():
                if cache_key in self.cache:
                    # Simple heuristic: if queries share many words, check similarity
                    query_words = set(normalized_query.split())
                    cached_words = set(cached_query.split())
                    overlap = len(query_words & cached_words) / len(query_words | cached_words)

                    if overlap > 0.7:  # 70% word overlap
                        return self.cache[cache_key]

        return None

    def set(self, query: str, embedding: np.ndarray) -> None:
        """Cache an embedding for a query."""
        normalized_query = self._normalize_query(query)
        cache_key = hashlib.md5(normalized_query.encode()).hexdigest()

        with self._lock:
            # Remove oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                # Remove a random entry (simple LRU approximation)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                # Clean up query_map
                self.query_map = {q: k for q, k in self.query_map.items() if k != oldest_key}

            self.cache[cache_key] = embedding
            self.query_map[normalized_query] = cache_key

    def clear(self) -> None:
        """Clear all cached embeddings."""
        with self._lock:
            self.cache.clear()
            self.query_map.clear()


class SuggestedQuestionCache:
    """
    Redis-based cache for suggested question responses with 24-hour TTL.
    This is an ADDITIONAL cache layer on top of the existing QueryCache.
    """
    
    def __init__(self, ttl_seconds: int = 86400):
        """
        Initialize the Suggested Question Cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default: 86400 = 24 hours)
        """
        self.ttl_seconds = ttl_seconds
        self._redis_client = None
    
    def _get_redis_client(self):
        """Get Redis client instance."""
        if self._redis_client is None:
            try:
                from backend.redis_client import get_redis_client
                self._redis_client = get_redis_client()
            except Exception as e:
                logger.warning(f"Failed to get Redis client: {e}")
                return None
        return self._redis_client
    
    def _normalize_question(self, question: str) -> str:
        """
        Normalize question text for consistent cache keys.
        
        Args:
            question: The question text to normalize
            
        Returns:
            Normalized question string
        """
        # Convert to lowercase
        normalized = question.lower()
        # Strip leading/trailing whitespace
        normalized = normalized.strip()
        # Collapse multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def _generate_key(self, question: str) -> str:
        """
        Generate a cache key for the question (no chat history).
        
        Args:
            question: The question text
            
        Returns:
            MD5 hash of the normalized question
        """
        normalized = self._normalize_question(question)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _serialize_document(self, doc: Any) -> Dict[str, Any]:
        """
        Serialize a Langchain Document to a dictionary.
        
        Args:
            doc: Document object or dict
            
        Returns:
            Dictionary representation
        """
        if isinstance(doc, dict):
            return doc
        elif isinstance(doc, Document):
            return {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
        else:
            # Fallback for other types
            return {
                "page_content": str(doc),
                "metadata": {}
            }
    
    def _deserialize_document(self, doc_dict: Dict[str, Any]) -> Document:
        """
        Deserialize a dictionary to a Langchain Document.
        
        Args:
            doc_dict: Dictionary representation
            
        Returns:
            Document object
        """
        return Document(
            page_content=doc_dict.get("page_content", ""),
            metadata=doc_dict.get("metadata", {})
        )
    
    async def get(self, question: str) -> Optional[Tuple[str, List[Document]]]:
        """
        Get cached response for a question.
        
        Args:
            question: The question text
            
        Returns:
            Tuple of (answer, sources) if cached, None otherwise
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            return None
        
        try:
            key = f"suggested_question:{self._generate_key(question)}"
            cached_data = await redis_client.get(key)
            
            if cached_data is None:
                return None
            
            # Parse JSON data
            data = json.loads(cached_data)
            answer = data.get("answer", "")
            sources_data = data.get("sources", [])
            
            # Deserialize sources back to Document objects
            sources = [self._deserialize_document(doc_dict) for doc_dict in sources_data]
            
            return answer, sources
        except Exception as e:
            logger.warning(f"Error getting from Suggested Question Cache: {e}")
            return None
    
    async def set(self, question: str, answer: str, sources: List) -> None:
        """
        Store a response in the cache.
        
        Args:
            question: The question text
            answer: The generated answer
            sources: List of source documents (Document objects or dicts)
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            logger.warning("Redis client unavailable, cannot cache suggested question")
            return
        
        try:
            key = f"suggested_question:{self._generate_key(question)}"
            
            # Serialize sources to dictionaries
            sources_data = [self._serialize_document(doc) for doc in sources]
            
            # Create cache entry
            cache_entry = {
                "answer": answer,
                "sources": sources_data,
                "question": question,
                "cached_at": time.time()
            }
            
            # Store in Redis with TTL
            await redis_client.setex(
                key,
                self.ttl_seconds,
                json.dumps(cache_entry)
            )
        except Exception as e:
            logger.warning(f"Error setting Suggested Question Cache: {e}")
    
    async def is_cached(self, question: str) -> bool:
        """
        Check if a question is cached.
        
        Args:
            question: The question text
            
        Returns:
            True if cached, False otherwise
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            return False
        
        try:
            key = f"suggested_question:{self._generate_key(question)}"
            exists = await redis_client.exists(key)
            return exists > 0
        except Exception as e:
            logger.warning(f"Error checking Suggested Question Cache: {e}")
            return False
    
    async def clear(self) -> None:
        """
        Clear all cached entries.
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            logger.warning("Redis client unavailable, cannot clear suggested question cache")
            return
        
        try:
            # Get all keys matching the pattern
            pattern = "suggested_question:*"
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            # Delete all keys
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} entries from Suggested Question Cache")
        except Exception as e:
            logger.warning(f"Error clearing Suggested Question Cache: {e}")
    
    async def get_cache_size(self) -> int:
        """
        Get the number of cached entries.
        
        Returns:
            Number of cached entries
        """
        redis_client = self._get_redis_client()
        if redis_client is None:
            return 0
        
        try:
            pattern = "suggested_question:*"
            count = 0
            async for _ in redis_client.scan_iter(match=pattern):
                count += 1
            return count
        except Exception as e:
            logger.warning(f"Error getting Suggested Question Cache size: {e}")
            return 0


# Global cache instances
query_cache = QueryCache()
embedding_cache = EmbeddingCache()
suggested_question_cache = SuggestedQuestionCache()

# Thread pool for async operations
async_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rag_async")
