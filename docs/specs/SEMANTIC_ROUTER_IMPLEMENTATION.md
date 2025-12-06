# Semantic Router Implementation Specification

**Feature:** Intent-Based Query Routing (Liability Shield)  
**Phase:** 2  
**Priority:** High  
**Estimated Effort:** 8-12 hours  
**Status:** Specification

---

## 1. Overview

The Semantic Router intercepts user queries **before** they reach the RAG pipeline, classifying intent and blocking risky queries (price speculation, financial advice) with near-zero latency penalty.

### Objectives

- **Liability Reduction:** Block financial advice queries deterministically
- **Performance:** Add <5ms latency (99th percentile)
- **Reliability:** Fail-safe design (defaults to allowing queries if router fails)
- **Maintainability:** Easy to add new intent categories

---

## 2. Architecture

### 2.1 Two-Stage Filter Design

```
User Query
    ↓
[Stage 1: Regex Check] → Match? → Block/Route (0ms cost)
    ↓ No Match
[Stage 2: Semantic Check] → Match? → Block/Route (~15ms cost)
    ↓ No Match
[Default: technical_support] → Proceed to RAG Pipeline
```

**Why Two Stages:**
- **Regex:** Catches 80% of obvious queries instantly (e.g., "will litecoin moon?")
- **Semantic:** Catches subtle phrasing (e.g., "should I hold my bags?")
- **Cost:** Regex is free, semantic uses existing embedding model (no API calls)

### 2.2 Integration Point

**Location:** `backend/main.py` - `chat_stream_endpoint()` function  
**Placement:** After rate limiting, **before** RAG pipeline call  
**Line:** ~1233 (before `# Get streaming response from RAG pipeline`)

```python
# Current flow:
# 1. Rate limiting ✓
# 2. Challenge validation ✓
# 3. Turnstile verification ✓
# 4. Cost throttling ✓
# 5. [NEW] Semantic Router ← Insert here
# 6. RAG Pipeline
```

---

## 3. Implementation Details

### 3.1 File Structure

```
backend/
├── routers/
│   └── intent_router.py          # NEW: Main router class
├── utils/
│   └── intent_patterns.py        # NEW: Regex patterns & examples
└── main.py                        # MODIFY: Add router call
```

### 3.2 Core Router Class

**File:** `backend/routers/intent_router.py`

```python
import re
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class IntentRouter:
    """
    Two-stage intent router for query classification.
    
    Stage 1: Fast regex pattern matching (0ms)
    Stage 2: Semantic similarity check using embeddings (~15ms)
    """
    
    # Intent categories
    INTENT_PRICE_SPECULATION = "price_speculation"
    INTENT_COMPETITOR_ATTACK = "competitor_attack"
    INTENT_TECHNICAL_SUPPORT = "technical_support"
    INTENT_GENERAL_CHAT = "general_chat"
    
    def __init__(self, embedding_model):
        """
        Initialize router with embedding model for semantic matching.
        
        Args:
            embedding_model: The embedding model instance (from VectorStoreManager)
        """
        self.embedding_model = embedding_model
        self.regex_patterns = self._load_regex_patterns()
        self.semantic_examples = self._load_semantic_examples()
        self.semantic_embeddings = None  # Lazy-loaded
        self.semantic_threshold = 0.85  # High confidence threshold
        
    def _load_regex_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for fast intent matching."""
        return {
            self.INTENT_PRICE_SPECULATION: [
                # Price prediction patterns
                r"(will|should|going to|predict|forecast|expect).*price",
                r"(moon|pump|dump|crash|rally|prediction|bull|bear).*litecoin",
                r"(buy|sell|invest|trade|hodl|hold).*(now|today|tomorrow|soon)",
                r"(worth|value|price).*(now|today|tomorrow|future)",
                r"(should i|can i|is it safe).*(buy|sell|invest|trade)",
                r"(investment|trading|speculation).*advice",
                r"(financial|investment).*recommendation",
            ],
            self.INTENT_COMPETITOR_ATTACK: [
                # Negative comparison patterns
                r"why is .* better than litecoin",
                r"is .* a scam",
                r"litecoin.*dead|dying|obsolete",
            ],
        }
    
    def _load_semantic_examples(self) -> Dict[str, List[str]]:
        """Load example phrases for semantic matching."""
        return {
            self.INTENT_PRICE_SPECULATION: [
                "Will Litecoin go up?",
                "Is it a good investment?",
                "Should I buy Litecoin now?",
                "What will the price be tomorrow?",
                "Is Litecoin going to moon?",
                "Should I hold my Litecoin?",
                "Is it worth investing in Litecoin?",
            ],
            self.INTENT_TECHNICAL_SUPPORT: [
                "How do I mine Litecoin?",
                "What is MWEB?",
                "How does Litecoin work?",
                "Explain Scrypt algorithm",
                "How to send Litecoin?",
            ],
        }
    
    def _get_semantic_embeddings(self) -> Dict[str, np.ndarray]:
        """Lazy-load semantic embeddings for example phrases."""
        if self.semantic_embeddings is None:
            logger.info("Pre-computing semantic embeddings for intent examples...")
            self.semantic_embeddings = {}
            
            for intent, examples in self.semantic_examples.items():
                # Encode all examples and average them for intent representation
                example_embeddings = []
                for example in examples:
                    embedding = self.embedding_model.embed_query(example)
                    example_embeddings.append(embedding)
                
                # Average embeddings to create intent centroid
                if example_embeddings:
                    self.semantic_embeddings[intent] = np.mean(example_embeddings, axis=0)
            
            logger.info(f"Pre-computed embeddings for {len(self.semantic_embeddings)} intent categories")
        
        return self.semantic_embeddings
    
    async def route(self, query: str) -> Tuple[str, float, str]:
        """
        Route query to intent category.
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (intent, confidence, method)
            - intent: Intent category name
            - confidence: Confidence score (0.0-1.0)
            - method: "regex" or "semantic" or "default"
        """
        query_lower = query.lower().strip()
        
        # Stage 1: Fast Regex Check (Cost: 0ms)
        for intent, patterns in self.regex_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    logger.info(f"Router: Regex matched '{intent}' for query: {query[:50]}...")
                    return (intent, 1.0, "regex")
        
        # Stage 2: Semantic Check (Cost: ~15ms)
        try:
            semantic_embeddings = self._get_semantic_embeddings()
            query_embedding = self.embedding_model.embed_query(query)
            
            best_intent = None
            best_score = 0.0
            
            for intent, intent_embedding in semantic_embeddings.items():
                # Cosine similarity
                similarity = np.dot(query_embedding, intent_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(intent_embedding)
                )
                
                if similarity > best_score:
                    best_score = similarity
                    best_intent = intent
            
            if best_score >= self.semantic_threshold:
                logger.info(
                    f"Router: Semantic matched '{best_intent}' "
                    f"(score={best_score:.3f}) for query: {query[:50]}..."
                )
                return (best_intent, best_score, "semantic")
        except Exception as e:
            logger.warning(f"Semantic routing failed: {e}. Falling back to default.", exc_info=True)
        
        # Default: Technical support (proceed to RAG)
        logger.debug(f"Router: No match, defaulting to '{self.INTENT_TECHNICAL_SUPPORT}'")
        return (self.INTENT_TECHNICAL_SUPPORT, 0.0, "default")
    
    def get_blocked_response(self, intent: str) -> str:
        """
        Get hardcoded response for blocked intents.
        
        Args:
            intent: Intent category that should be blocked
            
        Returns:
            Hardcoded response message
        """
        responses = {
            self.INTENT_PRICE_SPECULATION: (
                "I cannot provide financial advice or price predictions. "
                "I am a technical assistant focused on helping you understand Litecoin's technology, "
                "features, and how to use it. For current price information, please check a reputable "
                "market data source."
            ),
            self.INTENT_COMPETITOR_ATTACK: (
                "I focus on providing factual information about Litecoin. "
                "I cannot engage in comparisons with other cryptocurrencies or make claims about "
                "their legitimacy. If you have questions about Litecoin's features or technology, "
                "I'm happy to help!"
            ),
        }
        
        return responses.get(intent, "I cannot help with that type of query.")
```

### 3.3 Integration with Main Endpoint

**File:** `backend/main.py`  
**Location:** In `chat_stream_endpoint()` function, after cost throttling (~1077), before RAG pipeline (~1233)

```python
# Add import at top of file
from backend.routers.intent_router import IntentRouter

# Initialize router globally (reuse embedding model from RAG pipeline)
intent_router = None

def get_intent_router() -> IntentRouter:
    """Lazy-initialize intent router with RAG pipeline's embedding model."""
    global intent_router
    if intent_router is None:
        intent_router = IntentRouter(rag_pipeline_instance.vector_store_manager.embeddings)
    return intent_router

# In chat_stream_endpoint(), after cost throttling (~1077):
# ... existing code ...

# Semantic Router Check (NEW)
try:
    router = get_intent_router()
    intent, confidence, method = await router.route(request.query)
    
    # Check if intent should be blocked
    if intent in [IntentRouter.INTENT_PRICE_SPECULATION, IntentRouter.INTENT_COMPETITOR_ATTACK]:
        # Return blocked response immediately (no LLM call)
        blocked_response = router.get_blocked_response(intent)
        
        # Log the blocked query
        logger.info(
            f"Query blocked by router: intent={intent}, method={method}, "
            f"confidence={confidence:.3f}, query={request.query[:50]}..."
        )
        
        # Track metrics
        if MONITORING_ENABLED:
            from backend.monitoring.metrics import (
                intent_router_blocks_total,
                intent_router_latency_seconds,
            )
            intent_router_blocks_total.labels(intent=intent, method=method).inc()
        
        # Stream blocked response
        async def generate_blocked_stream():
            # Send sources (empty)
            yield f"data: {json.dumps({'status': 'sources', 'sources': [], 'isComplete': False})}\n\n"
            
            # Stream blocked response
            for char in blocked_response:
                yield f"data: {json.dumps({'status': 'streaming', 'chunk': char, 'isComplete': False})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for UX
            
            # Signal completion
            yield f"data: {json.dumps({'status': 'complete', 'chunk': '', 'isComplete': True})}\n\n"
        
        return StreamingResponse(
            generate_blocked_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    # Intent is allowed - proceed to RAG pipeline
    logger.debug(f"Router: Query allowed (intent={intent}, method={method})")
    
except Exception as e:
    # Fail-safe: Log error but allow query to proceed
    logger.error(f"Intent router error: {e}. Allowing query to proceed.", exc_info=True)
    # Continue to RAG pipeline

# ... existing RAG pipeline code continues ...
```

---

## 4. Monitoring & Metrics

### 4.1 Prometheus Metrics

**File:** `backend/monitoring/metrics.py`

```python
# Intent Router Metrics
intent_router_blocks_total = Counter(
    "intent_router_blocks_total",
    "Total queries blocked by intent router",
    ["intent", "method"]  # method: "regex" or "semantic"
)

intent_router_latency_seconds = Histogram(
    "intent_router_latency_seconds",
    "Intent router processing latency",
    ["method"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

intent_router_confidence_score = Histogram(
    "intent_router_confidence_score",
    "Intent router confidence scores",
    ["intent", "method"],
    buckets=[0.0, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
)
```

### 4.2 Logging

- **INFO:** Blocked queries (intent, method, confidence, query preview)
- **DEBUG:** All routing decisions (including allowed queries)
- **WARNING:** Router failures (fallback to default)

---

## 5. Configuration

### 5.1 Environment Variables

```bash
# Intent Router Configuration
INTENT_ROUTER_ENABLED=true                    # Enable/disable router
INTENT_ROUTER_SEMANTIC_THRESHOLD=0.85        # Semantic matching threshold
INTENT_ROUTER_FAIL_CLOSED=false              # If true, block on router failure (default: allow)
```

### 5.2 Admin Dashboard Integration

**Future Enhancement:** Add admin controls to:
- View blocked query statistics
- Adjust semantic threshold
- Add/remove regex patterns
- Whitelist specific queries

---

## 6. Testing Strategy

### 6.1 Unit Tests

**File:** `backend/tests/test_intent_router.py`

```python
import pytest
from backend.routers.intent_router import IntentRouter

@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""
    # Implementation...

def test_regex_price_speculation(mock_embedding_model):
    """Test regex matching for price speculation queries."""
    router = IntentRouter(mock_embedding_model)
    
    test_queries = [
        "Will Litecoin go up?",
        "Should I buy now?",
        "Is Litecoin going to moon?",
    ]
    
    for query in test_queries:
        intent, confidence, method = await router.route(query)
        assert intent == IntentRouter.INTENT_PRICE_SPECULATION
        assert method == "regex"
        assert confidence == 1.0

def test_semantic_matching(mock_embedding_model):
    """Test semantic matching for subtle queries."""
    router = IntentRouter(mock_embedding_model)
    
    # Subtle query that regex might miss
    query = "Should I hold my bags?"
    intent, confidence, method = await router.route(query)
    
    # Should match via semantic (if threshold met)
    if confidence >= router.semantic_threshold:
        assert intent == IntentRouter.INTENT_PRICE_SPECULATION
        assert method == "semantic"

def test_fail_safe(mock_embedding_model):
    """Test that router failures don't block legitimate queries."""
    router = IntentRouter(mock_embedding_model)
    
    # Simulate embedding model failure
    router.embedding_model = None
    
    query = "What is MWEB?"
    intent, confidence, method = await router.route(query)
    
    # Should default to technical_support
    assert intent == IntentRouter.INTENT_TECHNICAL_SUPPORT
    assert method == "default"
```

### 6.2 Integration Tests

- Test router integration with chat endpoint
- Verify blocked responses are returned correctly
- Verify allowed queries proceed to RAG pipeline
- Test fail-safe behavior (router exception → allow query)

---

## 7. Performance Considerations

### 7.1 Latency Targets

- **Regex Stage:** <1ms (p99)
- **Semantic Stage:** <20ms (p99)
- **Total Router Overhead:** <25ms (p99)

### 7.2 Optimization Strategies

1. **Lazy Loading:** Semantic embeddings computed on first use
2. **Caching:** Consider caching regex results for repeated queries
3. **Async:** All operations are async-compatible

---

## 8. Deployment Checklist

- [ ] Create `backend/routers/intent_router.py`
- [ ] Create `backend/utils/intent_patterns.py` (if patterns grow large)
- [ ] Add router initialization in `main.py`
- [ ] Integrate router call in `chat_stream_endpoint()`
- [ ] Add Prometheus metrics
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Update documentation
- [ ] Deploy to staging
- [ ] Monitor metrics for 24 hours
- [ ] Deploy to production

---

## 9. Future Enhancements

1. **Admin Dashboard:** UI for managing patterns and thresholds
2. **A/B Testing:** Compare router accuracy vs. manual review
3. **Machine Learning:** Train classifier on labeled query dataset
4. **Whitelist:** Allow admins to whitelist specific queries
5. **Analytics:** Track false positive/negative rates

---

## 10. References

- **Current System Prompt:** `backend/rag_pipeline.py:83` (SYSTEM_INSTRUCTION)
- **Chat Endpoint:** `backend/main.py:935` (`chat_stream_endpoint`)
- **Embedding Model:** `backend/data_ingestion/vector_store_manager.py`

