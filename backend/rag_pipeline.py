import os
import asyncio
import time
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from data_ingestion.vector_store_manager import VectorStoreManager
from cache_utils import query_cache
from backend.utils.input_sanitizer import sanitize_query_input, detect_prompt_injection
# --- Environment Variable Checks ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set!")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

# --- Logging ---
logger = logging.getLogger(__name__)

# Import monitoring metrics
try:
    from backend.monitoring.metrics import (
        rag_query_duration_seconds,
        rag_cache_hits_total,
        rag_cache_misses_total,
        rag_retrieval_duration_seconds,
        rag_documents_retrieved_total,
    )
    from backend.monitoring.llm_observability import track_llm_metrics, estimate_gemini_cost
    MONITORING_ENABLED = True
except ImportError:
    # Monitoring not available, use no-op functions
    MONITORING_ENABLED = False
    def track_llm_metrics(*args, **kwargs):
        pass
    def estimate_gemini_cost(*args, **kwargs):
        return 0.0

# --- Environment Variable Checks ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set!")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

# --- Constants ---
DB_NAME = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
LLM_MODEL_NAME = "gemini-2.5-flash-lite-preview-09-2025"  # 
# Maximum number of chat history pairs (human-AI exchanges) to include in context
# This prevents token overflow and keeps context manageable. Default: 10 pairs (20 messages)
MAX_CHAT_HISTORY_PAIRS = int(os.getenv("MAX_CHAT_HISTORY_PAIRS", "3"))
NO_KB_MATCH_RESPONSE = (
    "I couldn’t find any relevant content in our knowledge base yet. "
)

# --- RAG Prompt Templates ---
# 1. History-aware question rephrasing prompt
QA_WITH_HISTORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "Given the above conversation, generate a standalone question that resolves any pronouns or ambiguous references in the user's input. Focus on the main subject of the conversation. If the input is already a complete standalone question, return it as is. Do not add extra information or make assumptions beyond resolving the context."),
    ]
)

# 2. RAG prompt for final answer generation
RAG_PROMPT_TEMPLATE = """
You are a neutral, factual expert on Litecoin, a peer-to-peer decentralized cryptocurrency. Your primary goal is to provide comprehensive, well-structured, and educational answers. Your responses must be based **exclusively** on the provided context. Do not speculate or add external knowledge.

If the context does not contain sufficient information, state this clearly.

---
**EXPERT RESPONSE STRUCTURE:**

1.  **Direct Answer & Context:**
    * Start with a direct, 1-2 sentence answer.
    * Immediately follow with any necessary background or context from the knowledge base (e.g., for privacy, explain the default public nature first).

2.  **Detailed Breakdown (The "Grok Expert" Style):**
    * Use a `##` Markdown heading for the main topic (e.g., `## Key Privacy Features`).
    * Use bullet points (*) for each key feature or term.
    * **For each bullet point:** Use bolding for the term (`* **Confidential Transactions:**`) and then **write 1-2 sentences explaining what it is and how it works**, based on the context. This is the most important step for creating depth.

3.  **Conclusion / Practical Notes:**
    * (If relevant) Conclude with any important limitations, tips, or best practices mentioned *in the context*.

---
**ADDITIONAL GUIDELINES:**

* **Formatting:** Use `##` headings, bullet points, and **bold key terms** (like **MWEB** or **Scrypt**).
* **Exclusivity:** Stick *only* to the provided context.
* **Real-time Data:** If asked for prices, state that your knowledge is static and recommend live sources.

---
**EXAMPLE (This follows all rules):**

User: What is MWEB?
Context: MimbleWimble Extension Blocks (MWEB) is an opt-in privacy and scalability upgrade for Litecoin, launched in 2022. It allows for confidential transactions, where amounts are hidden... It also uses non-interactive CoinJoin to mix inputs and outputs... While MWEB enhances privacy, it is not 100% anonymous...

Response:
x`**Litecoin's** **MWEB** (MimbleWimble Extension Blocks) is an awesome optional upgrade from 2022 that adds privacy and confidentiality to transactions.

Before **MWEB**, **Litecoin** transactions were public (like Bitcoin's). This upgrade lets you "opt-in" to a more private way of sending funds.

## Key Features of MWEB

* **Confidential Transactions:** This feature hides the *amount* of **Litecoin** you're sending from the public blockchain. Only you and the receiver can see it.
* **CoinJoin Integration:** **MWEB** automatically mixes multiple transactions together, which breaks the link between the sender and receiver and makes it much harder to trace the flow of funds.
* **Opt-In Model:** It's not mandatory! You have to choose to move your funds into the **MWEB** "extension block" to use these private features.

## Limitations
Just so you know, the context mentions that while **MWEB** is a big improvement, it doesn't guarantee 100% anonymity, as advanced analysis might still be possible.

---

{context}

User: {input}
"""
rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

def format_docs(docs: List[Document]) -> str:
    """Helper function to format a list of documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


class RAGPipeline:
    """
    Simplified RAG Pipeline using FAISS with local embeddings and Google Flash 2.5 LLM.
    """
    
    def __init__(self, vector_store_manager=None, db_name=None, collection_name=None):
        """
        Initializes the RAGPipeline.

        Args:
            vector_store_manager: An instance of VectorStoreManager. If provided, it's used.
                                  Otherwise, a new VectorStoreManager instance is created.
            db_name: Name of the database. Defaults to MONGO_DB_NAME env var or "litecoin_rag_db".
            collection_name: Name of the collection. Defaults to MONGO_COLLECTION_NAME env var or "litecoin_docs".
        """
        self.db_name = db_name or DB_NAME
        self.collection_name = collection_name or COLLECTION_NAME
        
        if vector_store_manager:
            self.vector_store_manager = vector_store_manager
            logger.info(f"RAGPipeline using provided VectorStoreManager for collection: {vector_store_manager.collection_name}")
        else:
            # Initialize VectorStoreManager with local embeddings
            self.vector_store_manager = VectorStoreManager(
                db_name=self.db_name,
                collection_name=self.collection_name
            )
            logger.info(f"RAGPipeline initialized with VectorStoreManager for collection: {self.collection_name} (MongoDB: {'available' if self.vector_store_manager.mongodb_available else 'unavailable'})")
            logger.info(f"Chat history context limit: {MAX_CHAT_HISTORY_PAIRS} pairs (configure via MAX_CHAT_HISTORY_PAIRS env var)")

        # Initialize LLM with Google Flash 2.5
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME, 
            temperature=0.7, 
            google_api_key=google_api_key
        )

        # Construct the RAG chains (both sync and async)
        self._setup_rag_chain()
        self._setup_async_rag_chain()

    def _setup_rag_chain(self):
        """Sets up the conversational RAG chain with memory."""
        # Get retriever from vector store
        retriever = self.vector_store_manager.get_retriever(
            search_type="similarity",
            search_kwargs={"k": 7}
        )

        # Create history-aware retriever for standalone question generation
        from langchain.chains import create_history_aware_retriever, create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain
        
        self.history_aware_retriever = create_history_aware_retriever(
            self.llm,
            retriever,
            QA_WITH_HISTORY_PROMPT
        )

        # Create document combining chain for final answer generation
        self.document_chain = create_stuff_documents_chain(self.llm, rag_prompt)

        # Create conversational retrieval chain using LCEL
        self.rag_chain = RunnablePassthrough.assign(
            context=self.history_aware_retriever
        ).assign(
            answer=self.document_chain
        )

    def _setup_async_rag_chain(self):
        """Sets up async conversational RAG chain for concurrent processing."""
        # Get retriever from vector store
        retriever = self.vector_store_manager.get_retriever(
            search_type="similarity",
            search_kwargs={"k": 15}
        )

        # Create history-aware retriever for standalone question generation
        from langchain.chains import create_history_aware_retriever
        
        self.async_history_aware_retriever = create_history_aware_retriever(
            self.llm,
            retriever,
            QA_WITH_HISTORY_PROMPT
        )

        # Create document combining chain for final answer generation
        from langchain.chains.combine_documents import create_stuff_documents_chain
        self.async_document_chain = create_stuff_documents_chain(self.llm, rag_prompt)

        # Create conversational retrieval chain using LCEL
        self.async_rag_chain = RunnablePassthrough.assign(
            context=self.async_history_aware_retriever
        ).assign(
            answer=self.async_document_chain
        )

    def _truncate_chat_history(self, chat_history: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Truncates chat history to the configured maximum length, keeping the most recent exchanges.
        
        Args:
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.
            
        Returns:
            A truncated list containing at most MAX_CHAT_HISTORY_PAIRS exchanges, keeping the most recent ones.
        """
        if len(chat_history) <= MAX_CHAT_HISTORY_PAIRS:
            return chat_history
        
        # Keep only the most recent N pairs
        truncated = chat_history[-MAX_CHAT_HISTORY_PAIRS:]
        logger.warning(f"Chat history truncated from {len(chat_history)} to {len(truncated)} pairs (max: {MAX_CHAT_HISTORY_PAIRS})")
        return truncated

    def _build_prompt_text(self, query_text: str, context_text: str) -> str:
        """Reconstruct the prompt text fed to the LLM for token accounting."""
        return RAG_PROMPT_TEMPLATE.format(context=context_text, input=query_text)

    def _estimate_token_usage(self, prompt_text: str, answer_text: str) -> Tuple[int, int]:
        """
        Estimate (input_tokens, output_tokens) for an LLM call.

        Uses the Gemini tokenizer via ChatGoogleGenerativeAI.get_num_tokens when
        available, with a word-count based fallback to ensure metrics are always
        recorded.
        """
        prompt_text = prompt_text or ""
        answer_text = answer_text or ""

        # Fallback approximations emulate prior behaviour but on full prompt text.
        fallback_input_tokens = max(int(len(prompt_text.split()) * 1.3), 0)
        fallback_output_tokens = max(int(len(answer_text.split()) * 1.3), 0)

        input_tokens = fallback_input_tokens
        output_tokens = fallback_output_tokens

        if hasattr(self.llm, "get_num_tokens"):
            try:
                input_tokens = max(int(self.llm.get_num_tokens(prompt_text)), 0)
            except Exception as exc:
                logger.debug("Failed to count input tokens via Gemini: %s", exc, exc_info=True)
            try:
                output_tokens = max(int(self.llm.get_num_tokens(answer_text)), 0)
            except Exception as exc:
                logger.debug("Failed to count output tokens via Gemini: %s", exc, exc_info=True)

        return input_tokens, output_tokens

    def refresh_vector_store(self):
        """
        Refreshes the vector store by reloading from disk and recreating the RAG chain.
        This should be called after new documents are added to ensure queries use the latest content.
        """
        try:
            logger.info("Refreshing RAG pipeline vector store...")

            # Reload the vector store from disk
            if hasattr(self, 'vector_store_manager') and self.vector_store_manager:
                # Rebuild FAISS from MongoDB
                self.vector_store_manager.vector_store = self.vector_store_manager._create_faiss_from_mongodb()
                logger.info("Vector store reloaded from disk")

            # Recreate the RAG chain with the updated vector store
            self._setup_rag_chain()
            self._setup_async_rag_chain()
            logger.info("RAG pipeline refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing vector store: {e}", exc_info=True)

    def query(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document]]:
        """
        Processes a query through the conversational RAG pipeline with memory and caching.

        Args:
            query_text: The user's current query.
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.

        Returns:
            A tuple containing the generated answer (str) and a list of source documents (List[Document]).
        """
        start_time = time.time()
        
        # Sanitize query for prompt injection and other attacks
        # Additional layer of protection even though Pydantic validators already sanitize
        is_injection, pattern = detect_prompt_injection(query_text)
        if is_injection:
            logger.warning(f"Prompt injection detected in query (pattern: {pattern}). Sanitizing...")
        query_text = sanitize_query_input(query_text)
        
        # Sanitize chat history messages as well
        sanitized_history = []
        for human_msg, ai_msg in chat_history:
            sanitized_human = sanitize_query_input(human_msg) if human_msg else human_msg
            sanitized_ai = sanitize_query_input(ai_msg) if ai_msg else ai_msg
            sanitized_history.append((sanitized_human, sanitized_ai))
        
        # Truncate chat history to prevent token overflow
        truncated_history = self._truncate_chat_history(sanitized_history)
        
        # Check cache first (using truncated history for cache key)
        cached_result = query_cache.get(query_text, truncated_history)
        if cached_result:
            logger.debug(f"Cache hit for query: '{query_text}'")
            if MONITORING_ENABLED:
                rag_cache_hits_total.labels(cache_type="query").inc()
                rag_query_duration_seconds.labels(
                    query_type="sync",
                    cache_hit="true"
                ).observe(time.time() - start_time)
            return cached_result
        
        # Cache miss
        if MONITORING_ENABLED:
            rag_cache_misses_total.labels(cache_type="query").inc()

        try:
            # Convert chat_history to Langchain's BaseMessage format for the history-aware retriever
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in truncated_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                converted_chat_history.append(AIMessage(content=ai_msg))

            # Track retrieval time
            retrieval_start = time.time()
            
            # Invoke the conversational retrieval chain with chat history
            result = self.rag_chain.invoke({
                "input": query_text,
                "chat_history": converted_chat_history
            })

            retrieval_duration = time.time() - retrieval_start
            
            answer = result.get("answer", "Error: Could not generate answer.")
            # Get source documents from the chain result
            context_docs = result.get("context", [])
            context_text = format_docs(context_docs)

            # Filter out draft/unpublished documents from sources
            published_sources = [
                doc for doc in context_docs
                if doc.metadata.get("status") == "published"
            ]

            # Track metrics or short-circuit when no published sources found
            if not published_sources:
                if MONITORING_ENABLED:
                    rag_retrieval_duration_seconds.observe(retrieval_duration)
                    rag_documents_retrieved_total.observe(0)
                    total_duration = time.time() - start_time
                    rag_query_duration_seconds.labels(
                        query_type="sync",
                        cache_hit="false"
                    ).observe(total_duration)
                return NO_KB_MATCH_RESPONSE, []

            # Track metrics
            if MONITORING_ENABLED:
                rag_retrieval_duration_seconds.observe(retrieval_duration)
                rag_documents_retrieved_total.observe(len(published_sources))
                total_duration = time.time() - start_time
                rag_query_duration_seconds.labels(
                    query_type="sync",
                    cache_hit="false"
                ).observe(total_duration)
                
                # Estimate and track LLM costs using Gemini tokenizer where possible
                prompt_text = self._build_prompt_text(query_text, context_text)
                input_tokens, output_tokens = self._estimate_token_usage(
                    prompt_text,
                    answer,
                )
                estimated_cost = estimate_gemini_cost(
                    input_tokens,
                    output_tokens,
                    LLM_MODEL_NAME,
                )
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=estimated_cost,
                    duration_seconds=total_duration,
                    status="success",
                )

            # Cache the result (using truncated history)
            query_cache.set(query_text, truncated_history, answer, published_sources)

            return answer, published_sources
        except Exception as e:
            # Log full error details for debugging but don't expose to user
            logger.error(f"Error during conversational RAG query execution: {e}", exc_info=True)
            
            if MONITORING_ENABLED:
                total_duration = time.time() - start_time
                rag_query_duration_seconds.labels(
                    query_type="sync",
                    cache_hit="false"
                ).observe(total_duration)
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    duration_seconds=total_duration,
                    status="error",
                )
            
            # Return generic error message without exposing internal details
            return "I encountered an error while processing your query. Please try again or rephrase your question.", []

    async def aquery(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document]]:
        """
        Async version of query method optimized for performance with caching.

        Args:
            query_text: The user's current query.
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.

        Returns:
            A tuple containing the generated answer (str) and a list of source documents (List[Document]).
        """
        start_time = time.time()
        
        # Sanitize query for prompt injection and other attacks
        # Additional layer of protection even though Pydantic validators already sanitize
        is_injection, pattern = detect_prompt_injection(query_text)
        if is_injection:
            logger.warning(f"Prompt injection detected in query (pattern: {pattern}). Sanitizing...")
        query_text = sanitize_query_input(query_text)
        
        # Sanitize chat history messages as well
        sanitized_history = []
        for human_msg, ai_msg in chat_history:
            sanitized_human = sanitize_query_input(human_msg) if human_msg else human_msg
            sanitized_ai = sanitize_query_input(ai_msg) if ai_msg else ai_msg
            sanitized_history.append((sanitized_human, sanitized_ai))
        
        # Truncate chat history to prevent token overflow
        truncated_history = self._truncate_chat_history(sanitized_history)
        
        # Check cache first (using truncated history for cache key)
        cached_result = query_cache.get(query_text, truncated_history)
        if cached_result:
            logger.debug(f"Cache hit for query: '{query_text}'")
            if MONITORING_ENABLED:
                rag_cache_hits_total.labels(cache_type="query").inc()
                rag_query_duration_seconds.labels(
                    query_type="async",
                    cache_hit="true"
                ).observe(time.time() - start_time)
            return cached_result
        
        # Cache miss
        if MONITORING_ENABLED:
            rag_cache_misses_total.labels(cache_type="query").inc()

        try:
            # Convert chat_history to Langchain's BaseMessage format
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in truncated_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                converted_chat_history.append(AIMessage(content=ai_msg))

            # Track retrieval time
            retrieval_start = time.time()
            
            # Use direct vector search for performance
            retriever = self.vector_store_manager.get_retriever(
                search_type="similarity",
                search_kwargs={"k": 15}
            )
            context_docs = retriever.get_relevant_documents(query_text)
            retrieval_duration = time.time() - retrieval_start

            # Format context for LLM
            context_text = format_docs(context_docs)

            # Filter out draft/unpublished documents from sources
            published_sources = [
                doc for doc in context_docs
                if doc.metadata.get("status") == "published"
            ]

            if not published_sources:
                if MONITORING_ENABLED:
                    rag_retrieval_duration_seconds.observe(retrieval_duration)
                    rag_documents_retrieved_total.observe(0)
                    total_duration = time.time() - start_time
                    rag_query_duration_seconds.labels(
                        query_type="async",
                        cache_hit="false"
                    ).observe(total_duration)
                return NO_KB_MATCH_RESPONSE, []

            # Generate answer using LLM with retrieved context
            llm_start = time.time()
            chain = rag_prompt | self.llm | StrOutputParser()
            answer = await chain.ainvoke({
                "input": query_text,
                "context": context_text
            })
            llm_duration = time.time() - llm_start

            # Use retrieved docs as sources
            sources = context_docs

            # Track metrics
            if MONITORING_ENABLED:
                rag_retrieval_duration_seconds.observe(retrieval_duration)
                rag_documents_retrieved_total.observe(len(published_sources))
                total_duration = time.time() - start_time
                rag_query_duration_seconds.labels(
                    query_type="async",
                    cache_hit="false"
                ).observe(total_duration)
                
                # Estimate and track LLM costs using Gemini tokenizer when possible
                prompt_text = self._build_prompt_text(query_text, context_text)
                input_tokens, output_tokens = self._estimate_token_usage(
                    prompt_text,
                    answer,
                )
                estimated_cost = estimate_gemini_cost(
                    input_tokens,
                    output_tokens,
                    LLM_MODEL_NAME,
                )
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=estimated_cost,
                    duration_seconds=llm_duration,
                    status="success",
                )

            # Cache the result (using truncated history)
            query_cache.set(query_text, truncated_history, answer, published_sources)

            return answer, published_sources
        except Exception as e:
            # Log full error details for debugging but don't expose to user
            logger.error(f"Error during async RAG query execution: {e}", exc_info=True)
            
            if MONITORING_ENABLED:
                total_duration = time.time() - start_time
                rag_query_duration_seconds.labels(
                    query_type="async",
                    cache_hit="false"
                ).observe(total_duration)
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    duration_seconds=total_duration,
                    status="error",
                )
            
            # Return generic error message without exposing internal details
            return "I encountered an error while processing your query. Please try again or rephrase your question.", []

    async def astream_query(self, query_text: str, chat_history: List[Tuple[str, str]]):
        """
        Streaming version of aquery that yields response chunks progressively.

        Args:
            query_text: The user's current query.
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.

        Yields:
            Dict with streaming data: {"type": "chunk", "content": "..."} or {"type": "sources", "sources": [...]} or {"type": "complete"}
        """
        start_time = time.time()
        try:
            # Sanitize query for prompt injection and other attacks
            # Additional layer of protection even though Pydantic validators already sanitize
            is_injection, pattern = detect_prompt_injection(query_text)
            if is_injection:
                logger.warning(f"Prompt injection detected in query (pattern: {pattern}). Sanitizing...")
            query_text = sanitize_query_input(query_text)
            
            # Sanitize chat history messages as well
            sanitized_history = []
            for human_msg, ai_msg in chat_history:
                sanitized_human = sanitize_query_input(human_msg) if human_msg else human_msg
                sanitized_ai = sanitize_query_input(ai_msg) if ai_msg else ai_msg
                sanitized_history.append((sanitized_human, sanitized_ai))
            
            # Truncate chat history to prevent token overflow
            truncated_history = self._truncate_chat_history(sanitized_history)
            
            # Check cache first (using truncated history for cache key)
            cached_result = query_cache.get(query_text, truncated_history)
            if cached_result:
                logger.debug(f"Cache hit for query: '{query_text}'")
                cached_answer, cached_sources = cached_result
                
                # Track cache hit metrics
                if MONITORING_ENABLED:
                    rag_cache_hits_total.labels(cache_type="query").inc()
                    rag_query_duration_seconds.labels(
                        query_type="stream",
                        cache_hit="true"
                    ).observe(time.time() - start_time)

                # Send sources first
                yield {"type": "sources", "sources": cached_sources}

                # Stream cached response character by character for consistent UX
                for i, char in enumerate(cached_answer):
                    yield {"type": "chunk", "content": char}
                    # Small delay to control streaming speed
                    if i % 10 == 0:  # Yield control every 10 characters
                        await asyncio.sleep(0.001)

                # Signal completion with cache flag
                yield {"type": "complete", "from_cache": True}
                return

            # Cache miss
            if MONITORING_ENABLED:
                rag_cache_misses_total.labels(cache_type="query").inc()

            # Track retrieval time
            retrieval_start = time.time()
            
            # For non-cached responses, use async conversational RAG chain
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in truncated_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                converted_chat_history.append(AIMessage(content=ai_msg))

            # Invoke the async conversational retrieval chain with chat history
            result = await self.async_rag_chain.ainvoke({
                "input": query_text,
                "chat_history": converted_chat_history
            })

            retrieval_duration = time.time() - retrieval_start

            answer = result.get("answer", "Error: Could not generate answer.")
            # Get source documents from the chain result
            context_docs = result.get("context", [])
            context_text = format_docs(context_docs)

            # Filter out draft/unpublished documents from sources
            published_sources = [
                doc for doc in context_docs
                if doc.metadata.get("status") == "published"
            ]

            if not published_sources:
                if MONITORING_ENABLED:
                    rag_retrieval_duration_seconds.observe(retrieval_duration)
                    rag_documents_retrieved_total.observe(0)
                    total_duration = time.time() - start_time
                    rag_query_duration_seconds.labels(
                        query_type="stream",
                        cache_hit="false"
                    ).observe(total_duration)
                # Inform client that no sources were available
                yield {"type": "sources", "sources": []}
                yield {"type": "chunk", "content": NO_KB_MATCH_RESPONSE}
                yield {"type": "complete", "from_cache": False, "no_kb_results": True}
                return

            total_duration = time.time() - start_time

            # Track metrics
            if MONITORING_ENABLED:
                rag_retrieval_duration_seconds.observe(retrieval_duration)
                rag_documents_retrieved_total.observe(len(published_sources))
                rag_query_duration_seconds.labels(
                    query_type="stream",
                    cache_hit="false"
                ).observe(total_duration)
                
                # Estimate and track LLM costs using Gemini tokenizer when possible
                prompt_text = self._build_prompt_text(query_text, context_text)
                input_tokens, output_tokens = self._estimate_token_usage(
                    prompt_text,
                    answer,
                )
                estimated_cost = estimate_gemini_cost(
                    input_tokens,
                    output_tokens,
                    LLM_MODEL_NAME,
                )
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=estimated_cost,
                    duration_seconds=total_duration,
                    status="success",
                )

            # Send sources first
            yield {"type": "sources", "sources": published_sources}

            # Cache the result (using truncated history)
            query_cache.set(query_text, truncated_history, answer, published_sources)

            # Now stream the full response character by character for smooth animation
            for i, char in enumerate(answer):
                yield {"type": "chunk", "content": char}
                # Small delay to control streaming speed (optional - frontend handles timing)
                if i % 10 == 0:  # Yield control every 10 characters
                    await asyncio.sleep(0.001)

            # Signal completion
            yield {"type": "complete", "from_cache": False}

        except Exception as e:
            # Log full error details for debugging but don't expose to user
            logger.error(f"Error during streaming RAG query execution: {e}", exc_info=True)
            
            # Track error metrics
            if MONITORING_ENABLED:
                total_duration = time.time() - start_time
                rag_query_duration_seconds.labels(
                    query_type="stream",
                    cache_hit="false"
                ).observe(total_duration)
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="generate",
                    duration_seconds=total_duration,
                    status="error",
                )
            
            # Return generic error message without exposing internal details
            yield {"type": "error", "error": "An error occurred while processing your query. Please try again or rephrase your question."}


# Example of how to use the RAGPipeline class (for testing or direct script use)
if __name__ == "__main__":
    # This ensures .env is loaded if running this script directly
    from dotenv import load_dotenv
    import logging
    logging.basicConfig(level=logging.INFO)
    
    dotenv_path_actual = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path_actual):
        logger.info(f"RAGPipeline direct run: Loading .env from {dotenv_path_actual}")
        load_dotenv(dotenv_path=dotenv_path_actual, override=True)
    else:
        logger.warning("RAGPipeline direct run: .env file not found. Ensure GOOGLE_API_KEY and MONGO_URI are set.")

    logger.info("Testing RAGPipeline class with local embeddings and Google Flash 2.5...")
    try:
        pipeline = RAGPipeline()  # Uses default collection

        # Test 1: Initial query
        initial_query = "What is Litecoin?"
        logger.info(f"Querying pipeline with: '{initial_query}' (initial query)")
        answer, sources = pipeline.query(initial_query, chat_history=[])
        logger.info("Answer (Initial Query): " + answer[:100] + "...")
        logger.info(f"Sources (Initial Query): {len(sources)} sources retrieved")

        # Test 2: Follow-up query with history
        follow_up_query = "Who created it?"
        simulated_history = [
            ("What is Litecoin?", "Litecoin is a peer-to-peer cryptocurrency and open-source software project released under the MIT/X11 license. It was inspired by Bitcoin but designed to have a faster block generation rate and use a different hashing algorithm.")
        ]
        logger.info(f"Querying pipeline with: '{follow_up_query}' (follow-up query)")
        answer, sources = pipeline.query(follow_up_query, chat_history=simulated_history)
        
        logger.info("Answer (Follow-up Query): " + answer[:100] + "...")
        logger.info(f"Sources (Follow-up Query): {len(sources)} sources retrieved")
            
    except ValueError as ve:
        logger.error(f"Initialization Error: {ve}")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
