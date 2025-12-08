# Feature: Advanced RAG Techniques

## Overview

This feature implements advanced Retrieval-Augmented Generation (RAG) techniques to significantly improve retrieval quality, reduce unnecessary LLM calls, and prevent hallucinations. The techniques are derived from production RAG systems and focus on moving beyond basic vector search.

**Status**: 📋 **Planning** - Feature document created

**Priority**: High - Retrieval quality and cost efficiency improvement

**Target Users**: All users (transparent improvement to answer quality)

**Last Updated**: 2025-12-07

---

## Table of Contents

1. [Feature Summary](#feature-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Enhancements](#proposed-enhancements)
4. [Implementation Plan](#implementation-plan)
5. [Technical Architecture](#technical-architecture)
6. [Configuration](#configuration)
7. [Risks & Mitigations](#risks--mitigations)
8. [Success Criteria](#success-criteria)
9. [Future Enhancements](#future-enhancements)

---

## Feature Summary

### Problem Statement

Current RAG systems face several challenges:

1. **Semantic Distance**: Large vector distance between user questions and document statements
   - User asks: *"How much do LTC devs make?"*
   - Document contains: *"The developer salary is 80k"*
   - Result: Lower similarity score, potential retrieval miss

2. **Unnecessary RAG Calls**: All queries go through the full pipeline, even:
   - Greetings and thanks (don't need search)
   - Exact matches to suggested questions (already cached)
   - Simple FAQs (could use static responses)

3. **Hallucination Risk**: When retrieval confidence is low, the system still generates responses, potentially fabricating information

### Solution

Implement three complementary techniques:

| Technique | Problem Solved | Impact |
|-----------|---------------|--------|
| **FAQ-Based Indexing** | Semantic distance | Very High |
| **Intent Detection Layer** | Unnecessary RAG calls | High |
| **Clarifying Question Loop** | Hallucination risk | Medium |

---

## Current State Analysis

### ✅ Already Implemented

| Technique | Implementation | File Location |
|-----------|---------------|---------------|
| Query Rephrasing | Local Ollama + Gemini fallback | `services/rewriter.py`, `services/router.py` |
| Hybrid Retrieval | BM25 + Semantic + Sparse re-ranking | `rag_pipeline.py` |
| Chat History Handling | Truncation + history-aware retriever | `rag_pipeline.py` |
| Multi-layer Caching | Exact + Semantic + Redis Vector | `cache_utils.py` |
| Suggested Questions | CMS-managed via Payload | `payload_cms/src/collections/SuggestedQuestions.ts` |
| Hierarchical Chunking | Markdown-aware with title prepending | `embedding_processor.py` |

### Query Rewriting (Current Implementation)

The existing query rewriting handles context resolution effectively:

```python
# backend/services/rewriter.py
REWRITER_SYSTEM_PROMPT = """You are a Query Resolution Engine. Your task is to rewrite 
the User's input into a standalone, context-complete search query.

Rules:
1. Analyze the Chat History to resolve pronouns and ambiguous references
2. Remove filler words and make the query concise
3. If the user's input doesn't need a search (greetings, thanks), output: NO_SEARCH_NEEDED
4. DO NOT answer the question - only rewrite it
"""
```

### Hybrid Retrieval (Current Implementation)

The system already implements sophisticated hybrid retrieval:

```python
# backend/rag_pipeline.py (lines 739-833)
# 1. Vector search with Infinity embeddings
vector_results = self.vector_store_manager.vector_store.similarity_search_with_score_by_vector(
    query_vector, k=RETRIEVER_K * 2
)

# 2. BM25 keyword search  
bm25_docs = self.bm25_retriever.invoke(retrieval_query)

# 3. Merge and deduplicate with priority logic
# 4. Re-rank using sparse embeddings (BGE-M3)
```

---

## Proposed Enhancements

### Enhancement 1: FAQ-Based Indexing (Question-to-Question Matching)

**Priority**: 🔴 HIGH  
**Effort**: Medium (2-3 days)  
**Impact**: Very High  

#### Concept

Generate synthetic questions for each document chunk at ingestion time. Store both the generated question and original chunk, enabling question-to-question matching.

**Before (Current):**
```
User Query:      "How much do LTC devs make?"
Document Vector: "The developer salary is 80k"
Similarity:      ~0.65 (lower due to semantic distance)
```

**After (Proposed):**
```
User Query:       "How much do LTC devs make?"
Generated FAQ:    "What is the salary for Litecoin developers?"
Similarity:       ~0.92 (questions match questions)
```

#### ⚠️ Critical: Parent Document Pattern

**The Flaw in Naive Implementation:**

If we store the synthetic question and return it to the LLM, the model receives *"What is the developer salary?"* but not the actual answer. Truncating content (`linked_content[:500]`) risks cutting off the answer.

**The Fix:**

The Vector Store indexes the **Synthetic Question**, but the Retriever returns the **Original Document Chunk** (the "Parent"). This decouples *what we search* from *what we return*.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PARENT DOCUMENT PATTERN                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INGESTION:                                                             │
│  ┌──────────────┐     LLM generates      ┌──────────────────────────┐  │
│  │  Chunk_A     │  ──────────────────►   │  Q1: "What is salary?"   │  │
│  │  (Parent)    │        3 questions     │  Q2: "How much do devs?" │  │
│  │              │                        │  Q3: "Developer pay?"    │  │
│  └──────────────┘                        └──────────────────────────┘  │
│         │                                          │                    │
│         │                                          │                    │
│         ▼                                          ▼                    │
│  ┌──────────────┐                        ┌──────────────────────────┐  │
│  │  MongoDB     │                        │  FAISS Vector Index      │  │
│  │  (Full Text) │◄─── parent_id ────────│  (Question Embeddings)   │  │
│  └──────────────┘                        └──────────────────────────┘  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  RETRIEVAL:                                                             │
│  ┌────────────────┐    Vector     ┌─────────────────┐                  │
│  │ User: "What's  │ ──────────►   │ Match: Q2       │                  │
│  │ the coin cap?" │   Search      │ is_synthetic=T  │                  │
│  └────────────────┘               │ parent_id=A     │                  │
│                                   └────────┬────────┘                  │
│                                            │                            │
│                                            │ SWAP (resolve_parents)     │
│                                            ▼                            │
│                                   ┌─────────────────┐                  │
│                                   │ Return: Chunk_A │                  │
│                                   │ (Full Content)  │                  │
│                                   └─────────────────┘                  │
│                                            │                            │
│                                            ▼                            │
│                                   ┌─────────────────┐                  │
│                                   │ LLM receives    │                  │
│                                   │ FULL ANSWER     │                  │
│                                   └─────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### New Component: `backend/services/faq_generator.py`

```python
"""
FAQ Generator Service (Parent Document Pattern)

Generates synthetic questions for document chunks. The questions are
indexed for search, but retrieval returns the FULL parent chunk.

Key Insight: Decouple what you SEARCH from what you RETURN.
- Search: Synthetic questions (semantic match to user queries)
- Return: Original chunks (full context for LLM)
"""

import os
import logging
import hashlib
from typing import List, Dict, Tuple
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class FAQGenerator:
    """
    Generates synthetic questions using Parent Document Pattern.
    
    Questions are stored with is_synthetic=True and parent_chunk_id
    pointing to the original chunk. NO content is stored in the
    question document - only the question text for embedding.
    """
    
    GENERATION_PROMPT = """You are a question generator for a Litecoin knowledge base.
Given the following content, generate 3 natural questions that this content directly answers.

Rules:
1. Questions should be phrased as a user would naturally ask them
2. Questions should be answerable ONLY from the provided content
3. Vary question styles (what, how, why, can, does, etc.)
4. Include vocabulary variations users might use
5. Output ONLY the questions, one per line

Content:
{content}

Questions:"""

    def __init__(self, llm=None):
        """
        Initialize FAQ Generator.
        
        Args:
            llm: LangChain LLM instance. If None, uses Gemini Flash (cheap/fast).
        """
        self.llm = llm or self._get_default_llm()
    
    def _get_default_llm(self):
        """Get default LLM for question generation (use cheap model for ingestion)."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",  # Cheap for batch ingestion
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    def _generate_chunk_id(self, chunk: Document) -> str:
        """Generate a stable ID for a chunk based on content hash."""
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()[:12]
        payload_id = chunk.metadata.get("payload_id", "unknown")
        chunk_idx = chunk.metadata.get("chunk_index", 0)
        return f"{payload_id}_{chunk_idx}_{content_hash}"
    
    async def generate_questions(self, chunk: Document) -> List[str]:
        """
        Generate questions for a document chunk.
        
        Args:
            chunk: Document chunk to generate questions for
            
        Returns:
            List of generated questions (up to 3 per chunk)
        """
        content = chunk.page_content[:3000]  # Truncate for LLM context
        prompt = self.GENERATION_PROMPT.format(content=content)
        
        try:
            response = await self.llm.ainvoke(prompt)
            questions = [q.strip() for q in response.content.strip().split('\n') if q.strip()]
            questions = [q for q in questions if q.endswith('?')]
            
            logger.debug(f"Generated {len(questions)} questions for chunk")
            return questions[:3]
            
        except Exception as e:
            logger.warning(f"Failed to generate questions: {e}")
            return []
    
    async def process_chunks_with_questions(
        self, 
        chunks: List[Document]
    ) -> Tuple[List[Document], Dict[str, Document]]:
        """
        Process chunks and create synthetic question documents.
        
        CRITICAL: Questions store ONLY the question text and parent_chunk_id.
        The parent_chunks_map is used at retrieval time to swap.
        
        Args:
            chunks: Original document chunks
            
        Returns:
            Tuple of:
            - all_docs: Original chunks + synthetic question docs
            - parent_chunks_map: Dict mapping chunk_id -> full Document
        """
        all_docs = []
        parent_chunks_map: Dict[str, Document] = {}
        
        for chunk in chunks:
            # Generate stable ID for this chunk
            chunk_id = self._generate_chunk_id(chunk)
            
            # Store in parent map (for retrieval swap)
            parent_chunks_map[chunk_id] = chunk
            
            # Add original chunk (for direct document search)
            chunk_with_id = Document(
                page_content=chunk.page_content,
                metadata={
                    **chunk.metadata,
                    "chunk_id": chunk_id,
                    "is_synthetic": False,
                }
            )
            all_docs.append(chunk_with_id)
            
            # Generate synthetic questions
            questions = await self.generate_questions(chunk)
            
            for i, question in enumerate(questions):
                # CRITICAL: Only store question text, NOT the content
                # The parent_chunk_id is used to fetch full content at retrieval
                question_doc = Document(
                    page_content=question,  # Only the question for embedding
                    metadata={
                        "payload_id": chunk.metadata.get("payload_id"),
                        "doc_type": "synthetic_question",
                        "is_synthetic": True,
                        "parent_chunk_id": chunk_id,  # Points to parent
                        "question_index": i,
                        "status": chunk.metadata.get("status", "published"),
                    }
                )
                all_docs.append(question_doc)
        
        logger.info(
            f"Processed {len(chunks)} chunks → {len(all_docs)} documents "
            f"({len(all_docs) - len(chunks)} synthetic questions)"
        )
        return all_docs, parent_chunks_map


def resolve_parents(
    retrieved_docs: List[Document],
    parent_chunks_map: Dict[str, Document]
) -> List[Document]:
    """
    Swap synthetic question hits with their full-text parent chunks.
    
    This is the CRITICAL function that implements Parent Document Pattern.
    Called after vector search, before sending to LLM.
    
    Args:
        retrieved_docs: Documents returned from vector search
        parent_chunks_map: Dict mapping chunk_id -> full Document
        
    Returns:
        List of Documents with synthetic questions replaced by parents
    """
    resolved = []
    seen_parent_ids = set()  # Deduplicate (multiple Qs may hit same parent)
    
    for doc in retrieved_docs:
        if doc.metadata.get("is_synthetic", False):
            # This is a synthetic question - swap for parent
            parent_id = doc.metadata.get("parent_chunk_id")
            
            if parent_id and parent_id not in seen_parent_ids:
                parent_doc = parent_chunks_map.get(parent_id)
                if parent_doc:
                    resolved.append(parent_doc)
                    seen_parent_ids.add(parent_id)
                    logger.debug(f"Swapped synthetic Q for parent: {parent_id}")
                else:
                    logger.warning(f"Parent chunk not found: {parent_id}")
        else:
            # Regular document - keep as-is
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id not in seen_parent_ids:
                resolved.append(doc)
                if chunk_id:
                    seen_parent_ids.add(chunk_id)
    
    logger.info(f"Resolved {len(retrieved_docs)} hits → {len(resolved)} unique documents")
    return resolved
```

#### Retrieval with Parent Resolution

```python
# backend/rag_pipeline.py - updated retrieval method

async def retrieve_with_parent_resolution(
    self, 
    query: str, 
    k: int = 12
) -> List[Document]:
    """
    Retrieve documents using Parent Document Pattern.
    
    1. Search both synthetic questions AND original documents
    2. Swap any synthetic question hits with their parent chunks
    3. Deduplicate (multiple questions may point to same parent)
    4. Return full-text documents ready for LLM
    """
    from backend.services.faq_generator import resolve_parents
    
    # Combined search (questions + documents)
    all_results = await self.vector_store.asimilarity_search(query, k=k * 2)
    
    # Load parent chunks map (from MongoDB or cache)
    parent_chunks_map = await self._load_parent_chunks_map()
    
    # CRITICAL: Swap synthetic questions for full parent content
    resolved_docs = resolve_parents(all_results, parent_chunks_map)
    
    # Apply existing re-ranking (BM25 + sparse) on resolved docs
    reranked = await self._rerank_documents(query, resolved_docs[:k])
    
    return reranked

async def _load_parent_chunks_map(self) -> Dict[str, Document]:
    """
    Load parent chunks map from MongoDB.
    
    In production, this should be cached (Redis) with TTL.
    """
    if not self.vector_store_manager.mongodb_available:
        return {}
    
    chunks_map = {}
    cursor = self.vector_store_manager.collection.find(
        {"metadata.is_synthetic": {"$ne": True}},
        {"text": 1, "metadata": 1}
    )
    
    for doc in cursor:
        chunk_id = doc.get("metadata", {}).get("chunk_id")
        if chunk_id:
            chunks_map[chunk_id] = Document(
                page_content=doc["text"],
                metadata=doc.get("metadata", {})
            )
    
    return chunks_map
```

#### Cost & Latency Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Ingestion Cost** | 1,000 chunks × 3 questions = 3,000 LLM calls | Use Gemini Flash ($0.075/1M tokens) or Ollama (free) |
| **Ingestion Time** | ~2-3 seconds per chunk | Run async, batch processing, background job |
| **Storage Size** | Vector index triples (~3x) | Acceptable for <100k docs; consider separate index for large scale |
| **Runtime Latency** | +50ms for parent resolution | Cache parent_chunks_map in Redis |

#### Success Metric: Vocabulary Mismatch Test

This is the key test case that validates the feature:

| Query | Document | Old System | New System |
|-------|----------|------------|------------|
| *"What's the coin cap?"* | *"The maximum supply is 84 million."* | ❌ Miss (no keyword overlap) | ✅ Hit via synthetic Q: *"What is the maximum supply?"* |
| *"How much do devs make?"* | *"Developer salary is 80k"* | ❌ Miss | ✅ Hit via synthetic Q: *"What is the developer salary?"* |
| *"Can I send LTC privately?"* | *"MWEB enables confidential transactions"* | ❌ Miss | ✅ Hit via synthetic Q: *"How do I send private Litecoin transactions?"* |

---

### Enhancement 2: Intent Detection & Routing Layer

**Priority**: 🔴 HIGH  
**Effort**: Low (1 day)  
**Impact**: High  

#### Concept

Add a lightweight classification layer before RAG retrieval to route queries optimally:

```
Query → Intent Classifier → [FAQ | Greeting | Search]
                              ↓        ↓         ↓
                          Cached   Static     RAG
                          Answer   Response   Pipeline
```

#### New Component: `backend/services/intent_classifier.py`

```python
"""
Intent Classification Service

Routes queries to the optimal handler based on detected intent.
Reduces unnecessary RAG calls for common queries.
"""

import os
import logging
from typing import Tuple, Optional, List
from enum import Enum
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent categories."""
    GREETING = "greeting"
    THANKS = "thanks"
    FAQ_MATCH = "faq_match"
    SEARCH = "search"


class IntentClassifier:
    """
    Lightweight intent classifier for query routing.
    Uses fuzzy matching and keyword detection.
    """
    
    GREETING_PATTERNS = [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "what's up", "howdy", "greetings"
    ]
    
    THANKS_PATTERNS = [
        "thanks", "thank you", "thx", "appreciate", "helpful",
        "got it", "understood", "makes sense", "perfect"
    ]
    
    GREETING_RESPONSE = (
        "Hello! I'm here to help you learn about Litecoin. "
        "Feel free to ask me anything about Litecoin's technology, "
        "history, wallets, or how to get started!"
    )
    
    THANKS_RESPONSE = (
        "You're welcome! Is there anything else you'd like to know about Litecoin?"
    )
    
    def __init__(self, faq_questions: Optional[List[str]] = None):
        """
        Initialize the classifier.
        
        Args:
            faq_questions: List of suggested questions from CMS
        """
        self.faq_questions = faq_questions or []
        self.faq_match_threshold = float(os.getenv("FAQ_MATCH_THRESHOLD", "85"))
    
    def update_faq_questions(self, questions: List[str]):
        """Update the FAQ questions list."""
        self.faq_questions = questions
        logger.info(f"Updated FAQ questions: {len(questions)} loaded")
    
    def classify(self, query: str) -> Tuple[Intent, Optional[str], Optional[str]]:
        """
        Classify user query intent.
        
        Returns:
            (intent, matched_value, response_or_none)
        """
        query_lower = query.lower().strip()
        
        # Check greeting
        if self._is_greeting(query_lower):
            return Intent.GREETING, None, self.GREETING_RESPONSE
        
        # Check thanks
        if self._is_thanks(query_lower):
            return Intent.THANKS, None, self.THANKS_RESPONSE
        
        # Check FAQ match
        matched = self._match_faq(query)
        if matched:
            return Intent.FAQ_MATCH, matched, None
        
        return Intent.SEARCH, None, None
    
    def _is_greeting(self, query: str) -> bool:
        if len(query.split()) <= 3:
            for pattern in self.GREETING_PATTERNS:
                if pattern in query or fuzz.ratio(query, pattern) > 80:
                    return True
        return False
    
    def _is_thanks(self, query: str) -> bool:
        if len(query.split()) <= 5:
            for pattern in self.THANKS_PATTERNS:
                if pattern in query or fuzz.ratio(query, pattern) > 80:
                    return True
        return False
    
    def _match_faq(self, query: str) -> Optional[str]:
        """Fuzzy match against FAQ questions."""
        if not self.faq_questions:
            return None
        
        result = process.extractOne(
            query,
            self.faq_questions,
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= self.faq_match_threshold:
            return result[0]
        return None
```

#### Integration Point

```python
# backend/rag_pipeline.py - add at start of aquery()

async def aquery(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document], Dict]:
    start_time = time.time()
    
    # NEW: Intent classification (skip if follow-up question)
    if not chat_history and hasattr(self, 'intent_classifier'):
        intent, matched, response = self.intent_classifier.classify(query_text)
        
        if intent in (Intent.GREETING, Intent.THANKS):
            return response, [], {
                "cache_hit": False,
                "intent": intent.value,
                "duration_seconds": time.time() - start_time
            }
        
        if intent == Intent.FAQ_MATCH:
            cached = await suggested_question_cache.get(matched)
            if cached:
                answer, sources = cached
                return answer, sources, {
                    "cache_hit": True,
                    "cache_type": "faq_intent",
                    "intent": "faq_match",
                    "duration_seconds": time.time() - start_time
                }
    
    # Continue with normal RAG pipeline...
```

---

### Enhancement 3: Clarifying Question Loop

**Priority**: 🟡 MEDIUM  
**Effort**: Low (1 day)  
**Impact**: Medium  

#### Concept

Add a confidence check after retrieval. If confidence is low, ask a clarifying question instead of potentially hallucinating.

#### New Component: `backend/services/confidence_checker.py`

```python
"""
Retrieval Confidence Checker

Determines if retrieved context is sufficient to answer a query.
"""

import os
import json
import logging
from typing import Tuple, Optional, List
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class ConfidenceChecker:
    """Checks if retrieved documents can confidently answer a query."""
    
    CHECK_PROMPT = """You are a confidence evaluator for a Litecoin knowledge base.

Given the user's question and retrieved context, determine:
1. Can this question be answered with HIGH confidence using ONLY the provided context?
2. If NOT confident, what clarifying question should we ask?

User Question: {query}

Context:
{context}

Respond in JSON (no markdown):
{{"confident": true/false, "reason": "brief explanation", "clarifying_question": "question or null"}}

Rules:
- confident=true ONLY if context directly addresses the question
- If question is ambiguous (e.g., "rates" without country), confident=false
- Clarifying questions should help narrow down user intent"""

    def __init__(self, llm=None, min_similarity: float = 0.3):
        self.llm = llm or self._get_default_llm()
        self.min_similarity = min_similarity
    
    def _get_default_llm(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0.1,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    async def check(
        self,
        query: str,
        documents: List[Document],
        scores: Optional[List[float]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check retrieval confidence.
        
        Returns:
            (is_confident, clarifying_question_or_none)
        """
        if not documents:
            return False, "I couldn't find relevant information. Could you rephrase your question?"
        
        # Quick check: low similarity scores
        if scores and max(scores) < self.min_similarity:
            return False, "I'm not sure I found the right information. Could you be more specific?"
        
        # LLM confidence check
        context = "\n\n".join([d.page_content[:500] for d in documents[:5]])
        prompt = self.CHECK_PROMPT.format(query=query, context=context)
        
        try:
            response = await self.llm.ainvoke(prompt)
            result = json.loads(response.content)
            
            is_confident = result.get("confident", False)
            clarifying = result.get("clarifying_question")
            
            if not is_confident and clarifying:
                logger.info(f"Low confidence: {query[:50]}... → asking: {clarifying}")
                return False, clarifying
            
            return is_confident, None
            
        except Exception as e:
            logger.warning(f"Confidence check failed: {e}")
            return True, None  # Fail open
```

---

## Implementation Plan

### Cursor Meta-Prompts for Implementation

These are the exact prompts to use with Cursor Composer for clean implementation:

#### Prompt 1: Intent Classifier (Morning - 2 hours)

```
Create `backend/services/intent_classifier.py` using `rapidfuzz`. 

It should:
1. Load a list of FAQ questions (strings) on initialization
2. Implement a `classify(query)` method that returns a tuple of (Intent enum, matched_value, response)
3. Intent enum has: GREETING, THANKS, FAQ_MATCH, SEARCH
4. Use `process.extractOne` with `fuzz.token_sort_ratio` for FAQ matching (threshold: 85)
5. Handle 'Hello', 'Hi', 'Thanks', 'Thank you' without hitting the LLM
6. Include an `update_faq_questions(questions)` method for runtime updates

Add unit tests in `backend/tests/test_intent_classifier.py`.
```

#### Prompt 2: FAQ Generator with Parent Document Pattern (Mid-Day - 4 hours)

```
Create `backend/services/faq_generator.py` implementing the Parent Document Pattern.

CRITICAL ARCHITECTURE:
- Questions are indexed for SEARCH
- Parent chunks are returned for GENERATION
- Decouple what you search from what you return

Implementation:
1. `FAQGenerator` class that takes a list of Documents
2. For each document, use Gemini Flash to generate 3 hypothetical questions
3. When creating question Documents:
   - Store ONLY the question text in `page_content` (for embedding)
   - Set `is_synthetic=True` in metadata
   - Set `parent_chunk_id` pointing to original chunk
   - Do NOT store content in the question doc
4. Return tuple of (all_docs, parent_chunks_map)

Also create `resolve_parents(retrieved_docs, parent_chunks_map)` helper that:
- Takes retrieval results
- Checks for `is_synthetic=True`
- Swaps synthetic questions for full parent documents
- Deduplicates (multiple Qs may point to same parent)
```

#### Prompt 3: Pipeline Integration (Afternoon - 3 hours)

```
Update `backend/rag_pipeline.py` to integrate Parent Document Pattern.

In the retrieval step:
1. After getting vector search results, call `resolve_parents()` helper
2. Swap any synthetic question hits with their full-text parent chunks
3. Deduplicate (since multiple questions might point to same parent)
4. THEN send to the Re-ranker or LLM

Add a new method `_load_parent_chunks_map()` that:
- Loads parent chunks from MongoDB (where is_synthetic != True)
- Returns Dict[chunk_id, Document]
- Should be cached in Redis with TTL in production

Add feature flag: USE_FAQ_INDEXING = os.getenv("USE_FAQ_INDEXING", "false").lower() == "true"
```

#### Prompt 4: Re-indexing Script (Evening - 2 hours)

```
Create `backend/scripts/reindex_with_faq.py` that:

1. Loads all existing documents from MongoDB
2. Uses FAQGenerator to create synthetic questions for each chunk
3. Stores the parent_chunks_map in MongoDB (new collection: `parent_chunks`)
4. Rebuilds FAISS index with original chunks + synthetic questions
5. Logs progress and handles errors gracefully

Include:
- Batch processing (100 chunks at a time)
- Progress bar
- Resume capability (skip already processed chunks)
- Dry-run mode for testing
```

---

### Phase 1: Intent Detection (Day 1 - Morning)

| Task | File | Effort |
|------|------|--------|
| Create `IntentClassifier` | `backend/services/intent_classifier.py` | 2 hours |
| Add `rapidfuzz` dependency | `backend/requirements.txt` | 5 min |
| Integrate into RAG pipeline | `backend/rag_pipeline.py` | 1 hour |
| Unit tests | `backend/tests/test_intent_classifier.py` | 1 hour |

### Phase 2: FAQ Indexing with Parent Document Pattern (Day 1-2)

| Task | File | Effort |
|------|------|--------|
| Create `FAQGenerator` with parent pattern | `backend/services/faq_generator.py` | 3 hours |
| Create `resolve_parents()` helper | `backend/services/faq_generator.py` | 1 hour |
| Update ingestion pipeline | `backend/data_ingestion/embedding_processor.py` | 2 hours |
| Add `_load_parent_chunks_map()` | `backend/rag_pipeline.py` | 2 hours |
| Create re-indexing script | `backend/scripts/reindex_with_faq.py` | 2 hours |
| Integration tests | `backend/tests/test_faq_retrieval.py` | 2 hours |

### Phase 3: Confidence Checking (Day 3)

| Task | File | Effort |
|------|------|--------|
| Create `ConfidenceChecker` | `backend/services/confidence_checker.py` | 2 hours |
| Integrate post-retrieval | `backend/rag_pipeline.py` | 1 hour |
| Update frontend for clarifications | `frontend/src/app/page.tsx` | 2 hours |
| E2E tests | `backend/tests/test_clarification_flow.py` | 2 hours |

---

### Validation Test Cases

After implementation, verify with these "Vocabulary Mismatch" tests:

| Query | Document Content | Expected Behavior |
|-------|------------------|-------------------|
| *"What's the coin cap?"* | *"Maximum supply is 84 million"* | ✅ Hit via synthetic Q |
| *"How much do devs make?"* | *"Developer salary is 80k"* | ✅ Hit via synthetic Q |
| *"Can I send LTC privately?"* | *"MWEB enables confidential transactions"* | ✅ Hit via synthetic Q |
| *"Hello!"* | N/A | ✅ Static greeting (no LLM) |
| *"What is Litecoin?"* | (Suggested Question) | ✅ Cache hit (FAQ match) |

---

## Configuration

### Environment Variables

```bash
# Intent Classification
FAQ_MATCH_THRESHOLD=85              # Fuzzy match threshold (0-100)

# FAQ-Based Indexing  
ENABLE_FAQ_INDEXING=true            # Generate questions at ingestion
FAQ_QUESTIONS_PER_CHUNK=3           # Questions per document chunk

# Confidence Checking
ENABLE_CONFIDENCE_CHECK=true        # Enable clarifying questions
MIN_CONFIDENCE_SIMILARITY=0.3       # Minimum similarity threshold
```

### Feature Flags

All features can be enabled/disabled independently:

```python
# backend/rag_pipeline.py

USE_INTENT_CLASSIFICATION = os.getenv("USE_INTENT_CLASSIFICATION", "true").lower() == "true"
USE_FAQ_INDEXING = os.getenv("USE_FAQ_INDEXING", "false").lower() == "true"
USE_CONFIDENCE_CHECK = os.getenv("USE_CONFIDENCE_CHECK", "false").lower() == "true"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FAQ generation increases ingestion time | Medium | Run async, batch processing, optional flag |
| Intent misclassification | Low | Keep threshold high (85%), log for monitoring |
| Clarifying loops annoy users | Medium | Limit to 1 clarification, confidence threshold tuning |
| Increased storage (FAQ vectors) | Low | ~3x chunk count, minimal compared to base storage |

---

## Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Retrieval Precision | Unknown | +20% | Manual evaluation (100 queries) |
| Cache Hit Rate | ~15% | +30% | `rag_cache_hits_total` metric |
| Avg Response Time | ~2.5s | -500ms | `rag_query_duration_seconds` |
| LLM API Cost | $X/day | -20% | LLM spend tracking |
| Hallucination Rate | Unknown | -50% | Manual evaluation |

---

## Future Enhancements

### Not Implemented (Lower Priority)

| Technique | Reason for Deferral |
|-----------|---------------------|
| **Multi-Query Retrieval** | Query rewriting handles most cases; adds latency |
| **User Properties** | Limited value for factual Q&A system |
| **RAG on Conversation History** | Current session handling is sufficient |
| **Function Calling** | No action-oriented features currently |

### Potential Future Work

1. **Adaptive FAQ Generation**: Use retrieval feedback to improve generated questions
2. **User Feedback Loop**: "Was this helpful?" to tune confidence thresholds
3. **A/B Testing Framework**: Compare retrieval strategies
4. **Semantic Routing**: ML-based intent classification for complex queries

---

## Dependencies

### New Packages

```txt
# backend/requirements.txt additions
rapidfuzz>=3.0.0    # Fast fuzzy string matching for intent classification
```

---

## Architecture Review & Approval

### Final Assessment (Gemini Review - 2025-12-07)

**Status: ✅ APPROVED FOR IMPLEMENTATION**

---

#### 1. Parent Document Architecture: CORRECT ✅

The revised plan correctly implements the Parent Document Pattern:

| Phase | Action | Result |
|-------|--------|--------|
| **Ingestion** | Generate questions → Index questions → Link to Parent Chunk ID | Questions embedded for search |
| **Retrieval** | Search questions → Match → Swap for Parent Chunk → Generate | LLM receives full context |

> This ensures the LLM always receives the full, authoritative context, not just a synthetic question that might be hallucinated or incomplete.

---

#### 2. Intent Classifier: HIGH ROI ✅

Adding `IntentClassifier` with `rapidfuzz` is a smart, low-effort/high-impact move.

- **Why:** Creates an "off-ramp" for non-RAG queries (Greetings/Thanks)
- **Benefit:** Reduces LLM costs and latency for ~20-30% of typical chat interactions
- **Risk:** Low (threshold at 85% prevents false positives)

---

#### 3. Implementation Risks to Watch ⚠️

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Ingestion Time** | Medium | Generating 3 questions per chunk is slow. Ensure `reindex_with_faq.py` supports **resume capability** (skip already processed chunks) |
| **Vector Store Bloat** | Low | Tripling vectors. Verify FAISS index and MongoDB Atlas tier can handle increased volume |
| **"Parent Not Found" Edge Case** | Low | Handle case where synthetic question exists but parent was deleted. Current code logs warning - ensure it doesn't crash pipeline |
| **Stale Questions** | Low | When parent chunk is updated/deleted, orphan questions may remain. Consider cleanup job |

---

#### 4. Go/No-Go Checklist

- [x] Does `FAQGenerator` use a cheap/fast model (Gemini Flash/Ollama)? **YES**
- [x] Does `resolve_parents` deduplicate results (so we don't send same parent 3x)? **YES**
- [x] Is `IntentClassifier` threshold high enough (85%) to prevent false positives? **YES**
- [x] Is there a resume capability for re-indexing? **PLANNED**
- [x] Are feature flags in place for gradual rollout? **YES**

---

#### 5. Recommended Implementation Order

```
Phase 1: Intent Detection (Day 1 - Morning)
    └── Immediate latency wins, minimal risk
    └── ~20-30% of queries skip RAG entirely

Phase 2: FAQ Indexing (Day 1-2)
    └── Higher complexity, higher reward
    └── Requires re-indexing existing documents
    └── Run re-index as background job

Phase 3: Confidence Checking (Day 3)
    └── Quality improvement
    └── Depends on Phase 1 & 2 stability
```

---

#### Conclusion

> **"This plan transforms your RAG system from a simple 'keyword matcher' into a 'semantically aware' engine."**
>
> — Gemini Architecture Review

---

## Related Documentation

- [RAG Pipeline Architecture](../architecture/rag-pipeline.md)
- [Semantic Caching](./FEATURE_SEMANTIC_CACHE.md)
- [Suggested Question Caching](./FEATURE_SUGGESTED_QUESTION_CACHING.md)
- [High Performance Local RAG](./DEC6_FEATURE_HIGH_PERFORMANCE_LOCAL_RAG.md)

---

## References

### Video Tutorials

- **[Parent Document Retriever Pattern](https://www.youtube.com/watch?v=wSi0fxkH6e0)** - Advanced RAG: visualizes the "Parent-Child" splitting strategy, showing how to index small chunks (or questions) while retrieving the larger context window for the LLM. *Highly relevant to this implementation.*

### Documentation

- Advanced RAG Techniques Discussion (Pars Labs / Claire conversation)
- [LangChain RAG Best Practices](https://python.langchain.com/docs/tutorials/rag/)
- [LangChain Parent Document Retriever](https://python.langchain.com/docs/how_to/parent_document_retriever/)
- [Redis Semantic Caching](https://redis.io/docs/latest/develop/get-started/vector-database/)
- [RapidFuzz Documentation](https://maxbachmann.github.io/RapidFuzz/)

### Key Insight (Gemini Review)

> **"Semantic Distance is the #1 silent killer of RAG systems."**
> 
> Users ask *questions*, but documents contain *statements*. Vector similarity often fails to bridge that gap. The Parent Document Pattern solves this by decoupling **what you search** (synthetic questions) from **what you return** (full document content).

