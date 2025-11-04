"""
Advanced Retrieval Capabilities for Litecoin RAG Chat

This module implements advanced retrieval techniques including:
- Hybrid search (dense + sparse retrieval)
- Query expansion and intent recognition
- Re-ranking with cross-encoders
- Reciprocal rank fusion for score combination
"""

import os
import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from data_ingestion.vector_store_manager import VectorStoreManager
from cache_utils import embedding_cache
import re

logger = logging.getLogger(__name__)

class BM25Indexer:
    """
    BM25-based sparse retrieval indexer for keyword-based document search.
    """

    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.doc_ids = []

    def index_documents(self, documents: List[Document]):
        """
        Index documents for BM25 retrieval.

        Args:
            documents: List of Langchain Document objects
        """
        self.documents = documents
        self.doc_ids = [doc.metadata.get('payload_id', str(i)) for i, doc in enumerate(documents)]

        # Tokenize documents for BM25
        tokenized_corpus = []
        for doc in documents:
            # Clean and tokenize text
            text = doc.page_content.lower()
            # Remove extra whitespace and split
            tokens = re.findall(r'\b\w+\b', text)
            tokenized_corpus.append(tokens)

        # Create BM25 index
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"Indexed {len(documents)} documents with BM25")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of (document_index, score) tuples
        """
        if not self.bm25:
            return []

        # Tokenize query
        query_tokens = re.findall(r'\b\w+\b', query.lower())
        if not query_tokens:
            return []

        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)

        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

        return results

    def get_document(self, index: int) -> Optional[Document]:
        """Get document by index."""
        if 0 <= index < len(self.documents):
            return self.documents[index]
        return None


class QueryExpansionService:
    """
    Service for expanding user queries to improve retrieval.
    """

    def __init__(self):
        # Litecoin/crypto specific expansions
        self.expansion_rules = {
            'litecoin': ['ltc', 'lite coin', 'litecoin cryptocurrency'],
            'price': ['value', 'cost', 'market price', 'current price', 'usd', 'exchange rate'],
            'mining': ['miner', 'mine', 'hashing', 'scrypt', 'mining hardware'],
            'wallet': ['wallets', 'address', 'private key', 'public key', 'send', 'receive'],
            'transaction': ['tx', 'transfer', 'send', 'receive', 'fee', 'confirmation'],
            'blockchain': ['block chain', 'distributed ledger', 'decentralized'],
            'halving': ['reward reduction', 'mining reward', 'block reward'],
            'mempool': ['memory pool', 'unconfirmed transactions', 'pending tx'],
            'segwit': ['segregated witness', 'transaction malleability'],
            'mimblewimble': ['mimble wimble', 'privacy protocol', 'confidential transactions'],
            'coinjoin': ['coin join', 'privacy mixing', 'tumbling'],
        }

        # Initialize LLM for dynamic expansion
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.1,
                google_api_key=google_api_key
            )
        else:
            self.llm = None
            logger.warning("GOOGLE_API_KEY not found, dynamic query expansion disabled")

    def expand_query(self, query: str, use_llm: bool = True) -> List[str]:
        """
        Expand query with synonyms and related terms.

        Args:
            query: Original query
            use_llm: Whether to use LLM for dynamic expansion

        Returns:
            List of expanded query variations
        """
        expanded_queries = [query]  # Always include original

        # Static expansion based on rules
        query_lower = query.lower()
        for term, expansions in self.expansion_rules.items():
            if term in query_lower:
                for expansion in expansions:
                    # Replace term with expansion
                    new_query = re.sub(r'\b' + re.escape(term) + r'\b', expansion, query_lower, flags=re.IGNORECASE)
                    if new_query not in [q.lower() for q in expanded_queries]:
                        expanded_queries.append(new_query)

        # Dynamic LLM-based expansion
        if use_llm and self.llm and len(expanded_queries) < 5:
            try:
                prompt = f"""
                Given the query: "{query}"

                Generate 2-3 alternative phrasings or related queries that would help find relevant information.
                Focus on cryptocurrency/Litecoin context. Keep them concise and natural.

                Return only the queries, one per line, no numbering or bullets.
                """

                response = self.llm.invoke(prompt)
                llm_suggestions = response.content.strip().split('\n')

                for suggestion in llm_suggestions:
                    suggestion = suggestion.strip()
                    if suggestion and suggestion not in expanded_queries:
                        # Clean up any numbering or bullets
                        suggestion = re.sub(r'^[\d\-\*\.\s]+', '', suggestion).strip()
                        if suggestion:
                            expanded_queries.append(suggestion)

            except Exception as e:
                logger.warning(f"LLM query expansion failed: {e}")

        # Limit to top 5 variations to avoid explosion
        return expanded_queries[:5]

    async def expand_query_async(self, query: str, use_llm: bool = True) -> List[str]:
        """
        Async version of expand_query that runs LLM calls concurrently.

        Args:
            query: Original query
            use_llm: Whether to use LLM for dynamic expansion

        Returns:
            List of expanded query variations
        """
        expanded_queries = [query]  # Always include original

        # Static expansion based on rules (fast, no async needed)
        query_lower = query.lower()
        for term, expansions in self.expansion_rules.items():
            if term in query_lower:
                for expansion in expansions:
                    # Replace term with expansion
                    new_query = re.sub(r'\b' + re.escape(term) + r'\b', expansion, query_lower, flags=re.IGNORECASE)
                    if new_query not in [q.lower() for q in expanded_queries]:
                        expanded_queries.append(new_query)

        # Dynamic LLM-based expansion (async)
        if use_llm and self.llm and len(expanded_queries) < 3:
            try:
                prompt = f"""
                Given the query: "{query}"

                Generate 2-3 alternative phrasings or related queries that would help find relevant information.
                Focus on cryptocurrency/Litecoin context. Keep them concise and natural.

                Return only the queries, one per line, no numbering or bullets.
                """

                # Run LLM call in thread pool to avoid blocking
                from cache_utils import async_executor
                response = await asyncio.get_event_loop().run_in_executor(
                    async_executor, self.llm.invoke, prompt
                )
                llm_suggestions = response.content.strip().split('\n')

                for suggestion in llm_suggestions:
                    suggestion = suggestion.strip()
                    if suggestion and suggestion not in expanded_queries:
                        # Clean up any numbering or bullets
                        suggestion = re.sub(r'^[\d\-\*\.\s]+', '', suggestion).strip()
                        if suggestion:
                            expanded_queries.append(suggestion)

            except Exception as e:
                logger.warning(f"Async LLM query expansion failed: {e}")

        # Limit to top 3 variations to avoid explosion
        return expanded_queries[:3]


class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever combining dense (semantic) and sparse (BM25) retrieval.
    """

    def __init__(self, vector_store_manager: VectorStoreManager, bm25_indexer: BM25Indexer,
                 dense_weight: float = 0.7, sparse_weight: float = 0.3):
        super().__init__()
        # Store references for hybrid retrieval
        self._vector_store_manager = vector_store_manager
        self._bm25_indexer = bm25_indexer
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        """
        Retrieve documents using hybrid search with reciprocal rank fusion.
        """
        # Get dense retrieval results (semantic similarity)
        dense_retriever = self._vector_store_manager.get_retriever(
            search_type="similarity",
            search_kwargs={"k": 20}  # Get more candidates for fusion
        )
        dense_docs = dense_retriever.get_relevant_documents(query)

        # Get sparse retrieval results (BM25)
        sparse_results = self._bm25_indexer.search(query, top_k=20)

        # Convert to common format for fusion
        dense_scores = {}
        for i, doc in enumerate(dense_docs):
            doc_id = doc.metadata.get('payload_id', f"dense_{i}")
            # Convert similarity to rank-based score (higher is better)
            dense_scores[doc_id] = len(dense_docs) - i

        sparse_scores = {}
        for idx, score in sparse_results:
            doc = self._bm25_indexer.get_document(idx)
            if doc:
                doc_id = doc.metadata.get('payload_id', f"sparse_{idx}")
                sparse_scores[doc_id] = score

        # Reciprocal Rank Fusion
        fused_scores = {}
        all_doc_ids = set(dense_scores.keys()) | set(sparse_scores.keys())

        for doc_id in all_doc_ids:
            dense_rank = dense_scores.get(doc_id, 0)
            sparse_rank = sparse_scores.get(doc_id, 0)

            # RRF score = (1/(k + r)) where k=60 is a common default
            k = 60
            rrf_score = (1 / (k + dense_rank)) + (1 / (k + sparse_rank))
            fused_scores[doc_id] = rrf_score

        # Sort by fused scores and return top documents
        sorted_doc_ids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        # Reconstruct documents from scores
        result_docs = []
        seen_docs = set()

        for doc_id, score in sorted_doc_ids[:10]:  # Return top 10
            # Find document from dense results
            for doc in dense_docs:
                if doc.metadata.get('payload_id', '') == doc_id:
                    if doc.page_content not in seen_docs:
                        result_docs.append(doc)
                        seen_docs.add(doc.page_content)
                    break
            else:
                # Find document from sparse results
                for idx, _ in sparse_results:
                    doc = self._bm25_indexer.get_document(idx)
                    if doc and doc.metadata.get('payload_id', '') == doc_id:
                        if doc.page_content not in seen_docs:
                            result_docs.append(doc)
                            seen_docs.add(doc.page_content)
                        break

        return result_docs[:10]  # Ensure we don't exceed 10


class ReRanker:
    """
    Re-ranks retrieved documents using cross-encoder for better relevance.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize re-ranker with cross-encoder model.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        try:
            self.cross_encoder = CrossEncoder(model_name)
            logger.info(f"Loaded cross-encoder model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {e}. Using fallback ranking.")
            self.cross_encoder = None

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """
        Re-rank documents by relevance to query.

        Args:
            query: Search query
            documents: Documents to re-rank
            top_k: Number of top documents to return

        Returns:
            Re-ranked list of documents
        """
        if not self.cross_encoder or not documents:
            return documents[:top_k]

        try:
            # Prepare query-document pairs
            query_doc_pairs = [[query, doc.page_content] for doc in documents]

            # Get relevance scores
            scores = self.cross_encoder.predict(query_doc_pairs)

            # Sort documents by scores
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # Return top-k
            reranked_docs = [doc for doc, score in scored_docs[:top_k]]

            # Add relevance score to metadata
            for i, (doc, score) in enumerate(scored_docs[:top_k]):
                doc.metadata['rerank_score'] = float(score)
                doc.metadata['rerank_rank'] = i + 1

            return reranked_docs

        except Exception as e:
            logger.warning(f"Re-ranking failed: {e}. Returning original order.")
            return documents[:top_k]


class AdvancedRetrievalPipeline:
    """
    Complete advanced retrieval pipeline combining all techniques.
    """

    def __init__(self, vector_store_manager: VectorStoreManager):
        self.vector_store_manager = vector_store_manager
        self.bm25_indexer = BM25Indexer()
        self.query_expander = QueryExpansionService()
        self.reranker = ReRanker()
        self.hybrid_retriever = None

        # Build BM25 index from existing documents
        self._build_bm25_index()

    def _build_bm25_index(self):
        """Build BM25 index from vector store documents."""
        try:
            # Try to load documents from MongoDB if available
            if self.vector_store_manager.mongodb_available:
                mongo_docs = list(self.vector_store_manager.collection.find({"metadata.status": "published"}))
                documents = []
                for doc in mongo_docs:
                    text = doc.get('text', '')
                    metadata = doc.get('metadata', {})
                    if text.strip():  # Only include non-empty documents
                        documents.append(Document(page_content=text, metadata=metadata))

                if documents:
                    self.bm25_indexer.index_documents(documents)
                    self.hybrid_retriever = HybridRetriever(
                        self.vector_store_manager,
                        self.bm25_indexer
                    )
                    logger.info(f"Built BM25 index with {len(documents)} documents from MongoDB")
                else:
                    logger.warning("No published documents found in MongoDB for BM25 indexing")
            else:
                # Fallback: try to get some documents from FAISS (limited approach)
                try:
                    retriever = self.vector_store_manager.get_retriever(search_kwargs={"k": 50})
                    # Use a very broad query to get diverse documents
                    broad_queries = ["litecoin", "cryptocurrency", "blockchain", "mining", "wallet"]
                    all_docs = set()

                    for query in broad_queries:
                        docs = retriever.get_relevant_documents(query)
                        all_docs.update(docs)

                    documents = list(all_docs)
                    if documents:
                        self.bm25_indexer.index_documents(documents)
                        self.hybrid_retriever = HybridRetriever(
                            self.vector_store_manager,
                            self.bm25_indexer
                        )
                        logger.info(f"Built BM25 index with {len(documents)} documents from FAISS sampling")
                    else:
                        logger.warning("No documents found for BM25 indexing")
                except Exception as e:
                    logger.error(f"Failed to build BM25 index from FAISS: {e}")

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")

    def retrieve(self, query: str, expand_query: bool = True, rerank: bool = True,
                top_k: int = 10) -> List[Document]:
        """
        Perform advanced retrieval with query expansion, hybrid search, and re-ranking.

        Args:
            query: User query
            expand_query: Whether to expand query
            rerank: Whether to re-rank results
            top_k: Number of documents to return

        Returns:
            List of retrieved and ranked documents
        """
        # Query expansion (using sync version for compatibility with existing sync interface)
        if expand_query:
            expanded_queries = self.query_expander.expand_query(query)
            logger.info(f"Expanded query '{query}' to {len(expanded_queries)} variations")
        else:
            expanded_queries = [query]

        all_candidates = []

        # Retrieve candidates for each query variation
        for q in expanded_queries:
            if self.hybrid_retriever:
                candidates = self.hybrid_retriever.get_relevant_documents(q)
            else:
                # Fallback to dense retrieval only
                retriever = self.vector_store_manager.get_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 15}
                )
                candidates = retriever.get_relevant_documents(q)

            all_candidates.extend(candidates)

        # Remove duplicates based on content
        seen_content = set()
        unique_candidates = []
        for doc in all_candidates:
            if doc.page_content not in seen_content:
                unique_candidates.append(doc)
                seen_content.add(doc.page_content)

        # Re-ranking DISABLED for performance - always use top candidates directly
        # if rerank and len(unique_candidates) > top_k:
        #     final_docs = self.reranker.rerank(query, unique_candidates, top_k=top_k)
        # else:
        #     final_docs = unique_candidates[:top_k]
        final_docs = unique_candidates[:top_k]

        # Filter to published documents only
        published_docs = [
            doc for doc in final_docs
            if doc.metadata.get("status") == "published"
        ]

        logger.info(f"Retrieved {len(published_docs)} relevant documents for query: {query}")
        return published_docs

    async def retrieve_async(self, query: str, expand_query: bool = True, rerank: bool = True,
                           top_k: int = 10) -> List[Document]:
        """
        Async version of retrieve with concurrent query expansion and retrieval.

        Args:
            query: User query
            expand_query: Whether to expand query
            rerank: Whether to re-rank results
            top_k: Number of documents to return

        Returns:
            List of retrieved and ranked documents
        """
        # Async query expansion
        if expand_query:
            expanded_queries = await self.query_expander.expand_query_async(query)
            logger.info(f"Async expanded query '{query}' to {len(expanded_queries)} variations")
        else:
            expanded_queries = [query]

        all_candidates = []

        # Retrieve candidates for each query variation (can be parallelized in future)
        for q in expanded_queries:
            if self.hybrid_retriever:
                candidates = self.hybrid_retriever.get_relevant_documents(q)
            else:
                # Fallback to dense retrieval only
                retriever = self.vector_store_manager.get_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 15}
                )
                candidates = retriever.get_relevant_documents(q)

            all_candidates.extend(candidates)

        # Remove duplicates based on content
        seen_content = set()
        unique_candidates = []
        for doc in all_candidates:
            if doc.page_content not in seen_content:
                unique_candidates.append(doc)
                seen_content.add(doc.page_content)

        # Re-ranking DISABLED for performance - always use top candidates directly
        # if rerank and len(unique_candidates) > top_k:
        #     final_docs = self.reranker.rerank(query, unique_candidates, top_k=top_k)
        # else:
        #     final_docs = unique_candidates[:top_k]
        final_docs = unique_candidates[:top_k]

        # Filter to published documents only
        published_docs = [
            doc for doc in final_docs
            if doc.metadata.get("status") == "published"
        ]

        logger.info(f"Async retrieved {len(published_docs)} relevant documents for query: {query}")
        return published_docs

    def update_index(self):
        """Update BM25 index when new documents are added."""
        self._build_bm25_index()
