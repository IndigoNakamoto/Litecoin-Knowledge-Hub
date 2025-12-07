"""
Inference Router Service

Routes query rewriting requests to local (Ollama) or cloud (Gemini) services
based on queue depth and timeout handling. Implements circuit breaker pattern
for automatic failover.

The router prioritizes local processing for cost efficiency while ensuring
reliable fallback to cloud services when local capacity is exceeded.

Architecture:
    1. Check queue depth via semaphore
    2. If queue < MAX_LOCAL_QUEUE_DEPTH: route to local Ollama rewriter
    3. If queue full: spill over to Gemini immediately
    4. If local timeout: failover to Gemini

Usage:
    router = InferenceRouter()
    rewritten_query = await router.rewrite(query, chat_history)
"""

import os
import asyncio
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import metrics if available
try:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Router metrics
    local_rewriter_requests_total = Counter(
        "local_rewriter_requests_total",
        "Total requests to local Ollama rewriter"
    )
    gemini_rewriter_requests_total = Counter(
        "gemini_rewriter_requests_total", 
        "Total requests to Gemini cloud rewriter"
    )
    router_spillover_total = Counter(
        "router_spillover_total",
        "Total requests that spilled over to Gemini due to queue depth"
    )
    local_rewriter_timeout_total = Counter(
        "local_rewriter_timeout_total",
        "Total local rewriter requests that timed out"
    )
    rewriter_latency_seconds = Histogram(
        "rewriter_latency_seconds",
        "Rewriter latency in seconds",
        ["backend"],  # "local" or "gemini"
        buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
    )
    local_queue_depth = Gauge(
        "local_rewriter_queue_depth",
        "Current queue depth for local rewriter"
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    logger.debug("Prometheus metrics not available for router")


class RoutingDecision(Enum):
    """Routing decision outcomes."""
    LOCAL = "local"
    GEMINI_SPILLOVER = "gemini_spillover"
    GEMINI_TIMEOUT = "gemini_timeout"
    GEMINI_ERROR = "gemini_error"


@dataclass
class RewriteResult:
    """Result of a query rewrite operation."""
    rewritten_query: str
    routing_decision: RoutingDecision
    latency_seconds: float
    backend: str  # "local" or "gemini"


class InferenceRouter:
    """
    Routes inference requests to local or cloud services based on capacity.
    
    Uses a semaphore to track queue depth and implements timeout-based
    circuit breaking for reliable fallback.
    
    Attributes:
        max_queue_depth: Maximum concurrent local requests before spillover
        local_timeout: Timeout in seconds before failing over to cloud
    """
    
    def __init__(
        self,
        max_queue_depth: Optional[int] = None,
        local_timeout: Optional[float] = None,
    ):
        """
        Initialize the inference router.
        
        Args:
            max_queue_depth: Max concurrent local requests (default: MAX_LOCAL_QUEUE_DEPTH env var or 3)
            local_timeout: Local rewriter timeout in seconds (default: LOCAL_TIMEOUT_SECONDS env var or 2.0)
        """
        self.max_queue_depth = max_queue_depth or int(os.getenv("MAX_LOCAL_QUEUE_DEPTH", "3"))
        self.local_timeout = local_timeout or float(os.getenv("LOCAL_TIMEOUT_SECONDS", "2.0"))
        
        # Semaphore for queue depth tracking
        self._queue_semaphore = asyncio.Semaphore(self.max_queue_depth)
        self._current_queue_depth = 0
        self._queue_lock = asyncio.Lock()
        
        # Lazy-loaded rewriters (import here to avoid circular dependencies)
        self._local_rewriter = None
        self._gemini_rewriter = None
        
        logger.info(
            f"InferenceRouter initialized: max_queue_depth={self.max_queue_depth}, "
            f"local_timeout={self.local_timeout}s"
        )
    
    @property
    def local_rewriter(self):
        """Lazy-load local rewriter."""
        if self._local_rewriter is None:
            from backend.services.rewriter import LocalRewriter
            self._local_rewriter = LocalRewriter()
        return self._local_rewriter
    
    @property
    def gemini_rewriter(self):
        """Lazy-load Gemini rewriter."""
        if self._gemini_rewriter is None:
            from backend.services.rewriter import GeminiRewriter
            self._gemini_rewriter = GeminiRewriter()
        return self._gemini_rewriter
    
    async def _get_queue_depth(self) -> int:
        """Get current queue depth."""
        async with self._queue_lock:
            return self._current_queue_depth
    
    async def _increment_queue(self):
        """Increment queue depth counter."""
        async with self._queue_lock:
            self._current_queue_depth += 1
            if METRICS_ENABLED:
                local_queue_depth.set(self._current_queue_depth)
    
    async def _decrement_queue(self):
        """Decrement queue depth counter."""
        async with self._queue_lock:
            self._current_queue_depth = max(0, self._current_queue_depth - 1)
            if METRICS_ENABLED:
                local_queue_depth.set(self._current_queue_depth)
    
    async def rewrite(
        self,
        query: str,
        chat_history: List[Tuple[str, str]],
    ) -> str:
        """
        Rewrite query using local or cloud service based on capacity.
        
        Args:
            query: The user's current query
            chat_history: List of (human_message, ai_message) tuples
            
        Returns:
            Rewritten query string, or "NO_SEARCH_NEEDED" for non-search queries
        """
        result = await self.rewrite_with_metadata(query, chat_history)
        return result.rewritten_query
    
    async def rewrite_with_metadata(
        self,
        query: str,
        chat_history: List[Tuple[str, str]],
    ) -> RewriteResult:
        """
        Rewrite query with full metadata about routing decision.
        
        Args:
            query: The user's current query
            chat_history: List of (human_message, ai_message) tuples
            
        Returns:
            RewriteResult with rewritten query and metadata
        """
        import time
        start_time = time.time()
        
        # Check if we can acquire the semaphore without blocking
        # This indicates queue depth < max
        can_acquire = self._queue_semaphore.locked() is False or \
                      await self._get_queue_depth() < self.max_queue_depth
        
        # Try to acquire semaphore without blocking to check queue depth
        acquired = False
        try:
            # Use wait_for with 0 timeout to check availability
            acquired = self._queue_semaphore.locked() is False
            if not acquired:
                # Queue is full, spill over to Gemini
                logger.info(f"Local queue full (depth={await self._get_queue_depth()}), spilling to Gemini")
                if METRICS_ENABLED:
                    router_spillover_total.inc()
                    gemini_rewriter_requests_total.inc()
                
                rewritten = await self.gemini_rewriter.rewrite(query, chat_history)
                latency = time.time() - start_time
                
                if METRICS_ENABLED:
                    rewriter_latency_seconds.labels(backend="gemini").observe(latency)
                
                return RewriteResult(
                    rewritten_query=rewritten,
                    routing_decision=RoutingDecision.GEMINI_SPILLOVER,
                    latency_seconds=latency,
                    backend="gemini",
                )
        except Exception:
            pass
        
        # Try local rewriter with timeout
        try:
            async with self._queue_semaphore:
                await self._increment_queue()
                try:
                    if METRICS_ENABLED:
                        local_rewriter_requests_total.inc()
                    
                    async with asyncio.timeout(self.local_timeout):
                        rewritten = await self.local_rewriter.rewrite(query, chat_history)
                        latency = time.time() - start_time
                        
                        if METRICS_ENABLED:
                            rewriter_latency_seconds.labels(backend="local").observe(latency)
                        
                        logger.info(f"✅ Local rewrite succeeded in {latency:.3f}s")
                        return RewriteResult(
                            rewritten_query=rewritten,
                            routing_decision=RoutingDecision.LOCAL,
                            latency_seconds=latency,
                            backend="local",
                        )
                finally:
                    await self._decrement_queue()
                    
        except asyncio.TimeoutError:
            logger.warning(f"Local rewriter timeout after {self.local_timeout}s, failing over to Gemini")
            if METRICS_ENABLED:
                local_rewriter_timeout_total.inc()
                gemini_rewriter_requests_total.inc()
            
            # Failover to Gemini
            try:
                rewritten = await self.gemini_rewriter.rewrite(query, chat_history)
                latency = time.time() - start_time
                
                if METRICS_ENABLED:
                    rewriter_latency_seconds.labels(backend="gemini").observe(latency)
                
                return RewriteResult(
                    rewritten_query=rewritten,
                    routing_decision=RoutingDecision.GEMINI_TIMEOUT,
                    latency_seconds=latency,
                    backend="gemini",
                )
            except Exception as e:
                logger.error(f"Gemini failover also failed: {e}")
                # Return original query as last resort
                return RewriteResult(
                    rewritten_query=query,
                    routing_decision=RoutingDecision.GEMINI_ERROR,
                    latency_seconds=time.time() - start_time,
                    backend="none",
                )
                
        except Exception as e:
            logger.error(f"Local rewriter error: {e}, failing over to Gemini")
            if METRICS_ENABLED:
                gemini_rewriter_requests_total.inc()
            
            try:
                rewritten = await self.gemini_rewriter.rewrite(query, chat_history)
                latency = time.time() - start_time
                
                if METRICS_ENABLED:
                    rewriter_latency_seconds.labels(backend="gemini").observe(latency)
                
                return RewriteResult(
                    rewritten_query=rewritten,
                    routing_decision=RoutingDecision.GEMINI_ERROR,
                    latency_seconds=latency,
                    backend="gemini",
                )
            except Exception as e2:
                logger.error(f"Both local and Gemini rewriters failed: {e2}")
                return RewriteResult(
                    rewritten_query=query,
                    routing_decision=RoutingDecision.GEMINI_ERROR,
                    latency_seconds=time.time() - start_time,
                    backend="none",
                )
    
    async def health_check(self) -> dict:
        """
        Check health of routing components.
        
        Returns:
            Dict with health status of local and cloud rewriters
        """
        health = {
            "router": "healthy",
            "queue_depth": await self._get_queue_depth(),
            "max_queue_depth": self.max_queue_depth,
            "local_rewriter": "unknown",
            "gemini_rewriter": "unknown",
        }
        
        # Check local rewriter
        try:
            local_healthy = await self.local_rewriter.health_check()
            health["local_rewriter"] = "healthy" if local_healthy else "unhealthy"
        except Exception as e:
            health["local_rewriter"] = f"error: {str(e)}"
        
        # Check Gemini rewriter
        try:
            gemini_healthy = await self.gemini_rewriter.health_check()
            health["gemini_rewriter"] = "healthy" if gemini_healthy else "unhealthy"
        except Exception as e:
            health["gemini_rewriter"] = f"error: {str(e)}"
        
        return health

