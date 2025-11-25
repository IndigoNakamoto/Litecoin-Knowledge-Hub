# Advanced Retrieval Capabilities Implementation

## Overview

This document describes the implementation of advanced retrieval capabilities for the Litecoin RAG Chat system, including hybrid search and history-aware retrieval using LangChain's built-in components.

## Implementation Summary

### ✅ Completed Features

#### 1. **Hybrid Search**
- **Dense Retrieval**: Google `text-embedding-004` semantic similarity via FAISS vector store
- **Sparse Retrieval**: BM25 keyword-based search using LangChain's `BM25Retriever`
- **Fusion Method**: Weighted ensemble (50% BM25, 50% semantic) using LangChain's `EnsembleRetriever`
- **Fallback**: Graceful degradation to dense-only when BM25 unavailable (e.g., no published documents)

#### 2. **History-Aware Retrieval**
- **Query Rephrasing**: Uses LangChain's `create_history_aware_retriever` to generate standalone questions from conversational context
- **Context Resolution**: Resolves pronouns and ambiguous references in follow-up queries
- **Integration**: History-aware retriever wraps the hybrid retriever for seamless conversation flow

#### 3. **System Integration**
- **RAGPipeline Integration**: Hybrid retrieval integrated directly into `RAGPipeline._setup_retrievers()`
- **Document Filtering**: Only published documents are used for BM25 indexing and retrieval
- **Index Management**: BM25 index built from published MongoDB documents on initialization

## Technical Architecture

### Core Components

The implementation uses LangChain's built-in retrieval components:

```python
# In RAGPipeline._setup_retrievers()
# 1. BM25 Retriever (sparse)
self.bm25_retriever = BM25Retriever.from_documents(
    all_published_docs,
    k=RETRIEVER_K
)

# 2. Semantic Retriever (dense)
self.semantic_retriever = self.vector_store_manager.get_retriever(
    search_type="similarity",
    search_kwargs={"k": RETRIEVER_K}
)

# 3. Hybrid Retriever (ensemble)
self.hybrid_retriever = EnsembleRetriever(
    retrievers=[self.bm25_retriever, self.semantic_retriever],
    weights=[0.5, 0.5],
    search_type="similarity"
)

# 4. History-Aware Retriever
self.history_aware_retriever = create_history_aware_retriever(
    llm=self.llm,
    retriever=self.hybrid_retriever,
    prompt=QA_WITH_HISTORY_PROMPT
)
```

### Key Classes and Components

1. **BM25Retriever** (LangChain): Sparse retrieval using Okapi BM25 algorithm
2. **EnsembleRetriever** (LangChain): Combines dense and sparse retrieval with weighted scores
3. **create_history_aware_retriever** (LangChain): Wraps retriever with LLM-based query rephrasing
4. **RAGPipeline**: Orchestrates the complete retrieval pipeline

### Integration Points

- **VectorStoreManager**: Provides semantic retriever via FAISS/MongoDB integration
- **RAGPipeline**: Contains all retrieval setup and orchestration in `_setup_retrievers()`
- **Document Processing**: Works with existing hierarchical chunking and metadata structure
- **MongoDB**: Source of published documents for BM25 indexing

### Retrieval Flow

1. **Document Loading**: Published documents loaded from MongoDB (`_load_published_docs_from_mongo()`)
2. **BM25 Indexing**: BM25 retriever created from published documents (if available)
3. **Hybrid Setup**: Ensemble retriever combines BM25 and semantic retrievers with equal weights
4. **History-Aware Wrapper**: LLM rephrases queries based on chat history before retrieval
5. **Retrieval**: History-aware retriever fetches documents using hybrid search
6. **Filtering**: Only published documents are returned to the user

## Performance Improvements

### Retrieval Accuracy
- **Hybrid Search**: Better handling of keyword-heavy queries (BM25) and semantic queries (embeddings)
- **History-Aware**: Resolves context-dependent queries in conversations
- **Document Filtering**: Ensures only published content is retrieved

### Example Improvements

**Query**: "litecoin mining"
- **Before**: Basic semantic similarity only
- **After**: Hybrid search combines keyword matching (BM25) with semantic similarity
- **Result**: More comprehensive coverage of mining-related content

**Follow-up Query**: "Who created it?" (after "What is Litecoin?")
- **History-Aware**: Rephrases to "Who created Litecoin?" using conversation context
- **Result**: Accurate retrieval even with ambiguous pronouns

## Configuration Options

Retrieval behavior is controlled via environment variables:

```bash
RETRIEVER_K=8                    # Number of documents to retrieve (default: 8)
MAX_CHAT_HISTORY_PAIRS=2         # Maximum conversation pairs for context (default: 2)
```

The hybrid retriever uses fixed weights (0.5/0.5) and cannot be configured at runtime. BM25 retriever is automatically disabled if no published documents are available.

## Dependencies

```txt
rank-bm25                        # BM25 sparse retrieval (used by LangChain BM25Retriever)
langchain==0.3.25                # Core LangChain framework
langchain-community==0.3.25      # BM25Retriever and EnsembleRetriever
langchain_google_genai==2.0.10   # Google Gemini LLM for history-aware retrieval
```

Note: `scipy`, `sentence-transformers`, and `transformers` are listed in requirements.txt but are not currently used for retrieval (they may be used for other features).

## Testing and Validation

### Test Coverage
- **Hybrid Search**: BM25 + dense retrieval integration via `EnsembleRetriever`
- **History-Aware**: Query rephrasing with conversation context
- **End-to-End**: Full RAG pipeline with hybrid retrieval in `aquery()` and `astream_query()`

### System Behavior
- **Graceful Degradation**: Falls back to semantic-only when BM25 unavailable
- **Document Filtering**: Only published documents included in retrieval results
- **Index Refresh**: `refresh_vector_store()` rebuilds BM25 index when documents are updated

## Limitations and Future Enhancements

### Current Limitations
1. **No Query Expansion**: Static or dynamic query expansion is not implemented
2. **No Re-ranking**: Cross-encoder re-ranking is not implemented
3. **Fixed Weights**: Hybrid retriever uses fixed 0.5/0.5 weights (not configurable)
4. **No RRF**: Uses weighted ensemble instead of Reciprocal Rank Fusion

### Potential Improvements
1. **Query Expansion**: Add static synonym rules or LLM-based query variations
2. **Re-ranking**: Integrate cross-encoder model for relevance scoring
3. **Configurable Weights**: Allow runtime configuration of BM25/semantic weights
4. **RRF Fusion**: Switch from weighted ensemble to Reciprocal Rank Fusion
5. **Metadata Boosting**: Recency, authority, and content type weighting
6. **Performance Optimization**: Caching of BM25 index and retrieval results

### Scalability Considerations
- **Index Updates**: BM25 index rebuilt on `refresh_vector_store()` call
- **Memory Management**: BM25 index held in memory (consider disk-based for large collections)
- **Document Limit**: Current implementation loads up to 10,000 published documents for BM25

## Deployment Notes

### Environment Requirements
- **Python 3.9+**: Compatible with existing stack
- **MongoDB**: Required for published document storage and BM25 indexing
- **Memory**: BM25 index held in memory (scales with document count)

### Monitoring
- **Performance Metrics**: Query latency tracked via Prometheus metrics
- **Retrieval Metrics**: `rag_retrieval_duration_seconds` and `rag_documents_retrieved_total`
- **Fallback Usage**: Logs indicate when BM25 retriever is disabled

### Initialization
The hybrid retriever is set up during `RAGPipeline.__init__()` via `_setup_retrievers()`. The BM25 index is built from published MongoDB documents at initialization time. If MongoDB is unavailable or no published documents exist, the system gracefully falls back to semantic-only retrieval.

## Conclusion

The hybrid retrieval implementation enhances the Litecoin RAG Chat system's ability to retrieve relevant information by combining keyword-based (BM25) and semantic (embedding) search. The history-aware retriever ensures that conversational queries are properly contextualized, resolving ambiguous references and maintaining topic coherence across multi-turn conversations.

The system uses LangChain's proven components for reliability and maintainability, with graceful fallbacks to ensure robust operation even when components are unavailable. The implementation is integrated directly into the `RAGPipeline` class, making it a core part of the RAG system rather than a separate module.
