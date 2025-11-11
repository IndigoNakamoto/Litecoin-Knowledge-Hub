"""
Caching utilities for RAG pipeline performance optimization.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple, List
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

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


# Global cache instances
query_cache = QueryCache()
embedding_cache = EmbeddingCache()

# Thread pool for async operations
async_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rag_async")
