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
from fastapi import HTTPException
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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
        llm_spend_limit_rejections_total,
    )
    from backend.monitoring.llm_observability import track_llm_metrics, estimate_gemini_cost
    from backend.monitoring.spend_limit import check_spend_limit, record_spend
    MONITORING_ENABLED = True
except ImportError:
    # Monitoring not available, use no-op functions
    MONITORING_ENABLED = False
    def track_llm_metrics(*args, **kwargs):
        pass
    def estimate_gemini_cost(*args, **kwargs):
        return 0.0
    async def check_spend_limit(*args, **kwargs):
        return True, None, {}
    async def record_spend(*args, **kwargs):
        return {}

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
MAX_CHAT_HISTORY_PAIRS = int(os.getenv("MAX_CHAT_HISTORY_PAIRS", "2"))
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

{chat_history}

User: {input}
"""
# Create rag_prompt for document chain (only needs context and input, chat_history is handled by history-aware retriever)
# Extract the system prompt part (everything before {context})
system_prompt = RAG_PROMPT_TEMPLATE.split("{context}")[0].strip()
# Remove {chat_history} and {input} from the system prompt since we'll add them back properly
# We need to remove these to ensure the template only has 'context' and 'input' variables
system_prompt = system_prompt.replace("{chat_history}", "").replace("{input}", "").strip()
# Construct the document prompt template with only context and input variables
# This template will be used by create_stuff_documents_chain which expects 'context' and 'input'
# The 'context' variable will be filled with retrieved documents by create_stuff_documents_chain
document_prompt_template = system_prompt + "\n\n{context}\n\nUser: {input}"
rag_prompt = ChatPromptTemplate.from_template(document_prompt_template)

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
            temperature=0.2, 
            google_api_key=google_api_key,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:    HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,   # non-negotiable
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:    HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,   # non-negotiable
                HarmCategory.HARM_CATEGORY_HATE_SPEECH:          HarmBlockThreshold.BLOCK_ONLY_HIGH,         # safe to loosen
                HarmCategory.HARM_CATEGORY_HARASSMENT:           HarmBlockThreshold.BLOCK_ONLY_HIGH,         # safe to loosen
            }
        )

        # Construct the async RAG chain
        self._setup_async_rag_chain()

    def _setup_async_rag_chain(self):
        """Sets up async conversational RAG chain for concurrent processing."""
        # Get retriever from vector store
        retriever = self.vector_store_manager.get_retriever(
            search_type="similarity",
            search_kwargs={"k": 6}
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
        return RAG_PROMPT_TEMPLATE.format(context=context_text, chat_history="", input=query_text)
    
    def _build_prompt_text_with_history(
        self, query_text: str, context_text: str, chat_history: List[BaseMessage]
    ) -> str:
        """Reconstruct the prompt text with chat history for token accounting."""
        # Format history as string for token counting
        history_text = ""
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                history_text += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                history_text += f"Assistant: {msg.content}\n"
        
        return RAG_PROMPT_TEMPLATE.format(
            context=context_text,
            chat_history=history_text,
            input=query_text
        )

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

    def _extract_token_usage_from_chain_result(self, result: Dict[str, Any]) -> Tuple[int, int]:
        """
        Extract actual token counts from LangChain chain result.
        
        The rag_chain returns a dict with "answer" that contains an AIMessage object
        which should have response_metadata with token usage information.
        
        Args:
            result: The result dict from rag_chain.invoke() or async_rag_chain.ainvoke()
        
        Returns:
            Tuple of (input_tokens, output_tokens) or (0, 0) if not available
        """
        input_tokens = 0
        output_tokens = 0
        
        try:
            answer = result.get("answer")
            if answer is None:
                return 0, 0
            
            # Check if answer is an AIMessage with response_metadata
            if hasattr(answer, 'response_metadata'):
                metadata = answer.response_metadata
                if metadata:
                    # LangChain format: response_metadata may contain token_usage
                    if 'token_usage' in metadata:
                        usage = metadata['token_usage']
                        input_tokens = usage.get('prompt_tokens', 0)
                        output_tokens = usage.get('completion_tokens', 0)
                    
                    # Also check for usage_metadata (direct Gemini API format)
                    if 'usage_metadata' in metadata:
                        usage = metadata['usage_metadata']
                        if hasattr(usage, 'prompt_token_count'):
                            input_tokens = getattr(usage, 'prompt_token_count', 0)
                        if hasattr(usage, 'candidates_token_count'):
                            output_tokens = getattr(usage, 'candidates_token_count', 0)
                
                # Check for direct usage_metadata attribute (Gemini response object)
                if hasattr(answer, 'usage_metadata'):
                    usage = answer.usage_metadata
                    input_tokens = getattr(usage, 'prompt_token_count', 0)
                    output_tokens = getattr(usage, 'candidates_token_count', 0)
        except Exception as e:
            logger.debug(f"Could not extract token usage from chain result: {e}", exc_info=True)
        
        return input_tokens, output_tokens

    def _extract_token_usage_from_llm_response(self, response: Any) -> Tuple[int, int]:
        """
        Extract actual token counts from LangChain LLM response (AIMessage).
        
        Args:
            response: The AIMessage response from LLM
        
        Returns:
            Tuple of (input_tokens, output_tokens) or (0, 0) if not available
        """
        input_tokens = 0
        output_tokens = 0
        
        try:
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if metadata:
                    # LangChain format
                    if 'token_usage' in metadata:
                        usage = metadata['token_usage']
                        input_tokens = usage.get('prompt_tokens', 0)
                        output_tokens = usage.get('completion_tokens', 0)
                    
                    # Gemini API format
                    if 'usage_metadata' in metadata:
                        usage = metadata['usage_metadata']
                        if hasattr(usage, 'prompt_token_count'):
                            input_tokens = getattr(usage, 'prompt_token_count', 0)
                        if hasattr(usage, 'candidates_token_count'):
                            output_tokens = getattr(usage, 'candidates_token_count', 0)
            
            # Direct usage_metadata attribute
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                input_tokens = getattr(usage, 'prompt_token_count', 0)
                output_tokens = getattr(usage, 'candidates_token_count', 0)
        except Exception as e:
            logger.debug(f"Could not extract token usage from LLM response: {e}", exc_info=True)
        
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

            # Recreate the async RAG chain with the updated vector store
            self._setup_async_rag_chain()
            logger.info("RAG pipeline refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing vector store: {e}", exc_info=True)

    async def aquery(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document], Dict[str, Any]]:
        """
        Async version of query method optimized for performance with caching.

        Args:
            query_text: The user's current query.
            chat_history: A list of (human_message, ai_message) tuples representing the conversation history.

        Returns:
            A tuple containing:
            - The generated answer (str)
            - A list of source documents (List[Document])
            - A metadata dict with: input_tokens, output_tokens, cost_usd, duration_seconds, cache_hit, cache_type
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
            # Ensure messages are strings before sanitization
            # Handle cases where ai_msg might be an AIMessage object or other type
            if ai_msg and not isinstance(ai_msg, str):
                if hasattr(ai_msg, 'content'):
                    ai_msg = str(ai_msg.content) if ai_msg.content else ""
                else:
                    ai_msg = str(ai_msg)
            if human_msg and not isinstance(human_msg, str):
                human_msg = str(human_msg)
            
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
            # Return cached result with metadata indicating cache hit
            answer, published_sources = cached_result
            metadata = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "duration_seconds": time.time() - start_time,
                "cache_hit": True,
                "cache_type": "query",
            }
            return answer, published_sources, metadata
        
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
                search_kwargs={"k": 6}
            )
            context_docs = retriever.invoke(query_text)
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
                metadata = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "duration_seconds": time.time() - start_time,
                    "cache_hit": False,
                    "cache_type": None,
                }
                return NO_KB_MATCH_RESPONSE, [], metadata

            # Pre-flight spend limit check (before LLM API call)
            if MONITORING_ENABLED:
                try:
                    # Estimate cost before making API call
                    prompt_text = self._build_prompt_text(query_text, context_text)
                    input_tokens_est, _ = self._estimate_token_usage(prompt_text, "")
                    # Use max expected output tokens for worst-case estimation (2048 tokens)
                    max_output_tokens = 2048
                    estimated_cost = estimate_gemini_cost(
                        input_tokens_est,
                        max_output_tokens,
                        LLM_MODEL_NAME,
                    )
                    # Check spend limit with 10% buffer
                    allowed, error_msg, _ = await check_spend_limit(estimated_cost, LLM_MODEL_NAME)
                    if not allowed:
                        # Increment rejection counter
                        if "daily" in error_msg.lower():
                            llm_spend_limit_rejections_total.labels(limit_type="daily").inc()
                        elif "hourly" in error_msg.lower():
                            llm_spend_limit_rejections_total.labels(limit_type="hourly").inc()
                        # Return user-friendly error message
                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "spend_limit_exceeded",
                                "message": "We've reached our daily usage limit. Please try again later.",
                                "type": "daily" if "daily" in error_msg.lower() else "hourly"
                            }
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    # Log error but allow request (graceful degradation)
                    logger.warning(f"Error in spend limit check: {e}", exc_info=True)

            # Generate answer using LLM with retrieved context (without StrOutputParser to preserve metadata)
            llm_start = time.time()
            llm_response = await (rag_prompt | self.llm).ainvoke({
                "input": query_text,
                "context": context_text
            })
            # Extract answer content, ensuring it's always a string
            if hasattr(llm_response, 'content'):
                content = llm_response.content
                # Ensure content is a string (handle mocks, coroutines, etc.)
                if content is None:
                    answer = ""
                elif isinstance(content, str):
                    answer = content
                else:
                    # For mocks or other types, convert to string
                    # If it's a coroutine, this will fail and we'll catch it
                    answer = str(content)
            else:
                answer = str(llm_response)
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
                
                # Extract actual token usage from LLM response, fallback to estimation
                input_tokens, output_tokens = self._extract_token_usage_from_llm_response(llm_response)
                if input_tokens == 0 and output_tokens == 0:
                    # Fallback to estimation if metadata not available
                    prompt_text = self._build_prompt_text(query_text, context_text)
                    input_tokens, output_tokens = self._estimate_token_usage(
                        prompt_text,
                        answer,
                    )
                    logger.debug("Using estimated token counts (metadata not available)")
                else:
                    logger.debug(f"Using actual token counts: input={input_tokens}, output={output_tokens}")
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
                
                # Record actual spend in Redis
                try:
                    await record_spend(estimated_cost, input_tokens, output_tokens, LLM_MODEL_NAME)
                except Exception as e:
                    logger.warning(f"Error recording spend: {e}", exc_info=True)

            # Cache the result (using truncated history)
            query_cache.set(query_text, truncated_history, answer, published_sources)

            # Build metadata dict
            metadata = {
                "input_tokens": input_tokens if MONITORING_ENABLED else 0,
                "output_tokens": output_tokens if MONITORING_ENABLED else 0,
                "cost_usd": estimated_cost if MONITORING_ENABLED else 0.0,
                "duration_seconds": time.time() - start_time,
                "cache_hit": False,
                "cache_type": None,
            }

            return answer, published_sources, metadata
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
            metadata = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "duration_seconds": time.time() - start_time,
                "cache_hit": False,
                "cache_type": None,
            }
            return "I encountered an error while processing your query. Please try again or rephrase your question.", [], metadata

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

                # Yield metadata for cache hit
                metadata = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "duration_seconds": time.time() - start_time,
                    "cache_hit": True,
                    "cache_type": "query",
                }
                yield {"type": "metadata", "metadata": metadata}

                # Signal completion with cache flag
                yield {"type": "complete", "from_cache": True}
                return

            # Cache miss
            if MONITORING_ENABLED:
                rag_cache_misses_total.labels(cache_type="query").inc()

            # Convert chat_history to Langchain's BaseMessage format
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in truncated_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                converted_chat_history.append(AIMessage(content=ai_msg))

            # 1. SINGLE RETRIEVAL (using history-aware retriever for query rephrasing)
            retrieval_start = time.time()
            
            # Use history-aware retriever to get context (rephrases query with history)
            context_docs = await self.async_history_aware_retriever.ainvoke({
                "input": query_text,
                "chat_history": converted_chat_history
            })
            
            retrieval_duration = time.time() - retrieval_start
            
            # Format context for LLM
            context_text = format_docs(context_docs)
            
            # Filter published sources
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
                metadata = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "duration_seconds": time.time() - start_time,
                    "cache_hit": False,
                    "cache_type": None,
                }
                yield {"type": "metadata", "metadata": metadata}
                yield {"type": "complete", "from_cache": False, "no_kb_results": True}
                return
            
            # Send sources immediately (low latency UX)
            yield {"type": "sources", "sources": published_sources}
            
            # 2. Pre-flight spend limit check (before LLM API call)
            if MONITORING_ENABLED:
                try:
                    # Estimate cost before making API call (use history for accurate estimation)
                    prompt_text = self._build_prompt_text_with_history(
                        query_text, context_text, converted_chat_history
                    )
                    input_tokens_est, _ = self._estimate_token_usage(prompt_text, "")
                    # Use max expected output tokens for worst-case estimation (2048 tokens)
                    max_output_tokens = 2048
                    estimated_cost = estimate_gemini_cost(
                        input_tokens_est,
                        max_output_tokens,
                        LLM_MODEL_NAME,
                    )
                    # Check spend limit with 10% buffer
                    allowed, error_msg, _ = await check_spend_limit(estimated_cost, LLM_MODEL_NAME)
                    if not allowed:
                        # Increment rejection counter
                        error_type = "daily" if "daily" in error_msg.lower() else "hourly"
                        if error_type == "daily":
                            llm_spend_limit_rejections_total.labels(limit_type="daily").inc()
                        else:
                            llm_spend_limit_rejections_total.labels(limit_type="hourly").inc()
                        # Yield user-friendly error message and complete
                        yield {
                            "type": "error",
                            "message": "We've reached our daily usage limit. Please try again later.",
                            "error_type": error_type
                        }
                        yield {"type": "complete", "error": True}
                        return
                except Exception as e:
                    # Log error but allow request (graceful degradation)
                    logger.warning(f"Error in spend limit check: {e}", exc_info=True)

            # 3. TRUE STREAMING GENERATION
            llm_start = time.time()
            full_answer_accumulator = ""
            
            # Use async_document_chain.astream() directly for true streaming
            # create_stuff_documents_chain expects 'context' to be a list of Document objects, not a formatted string
            async for chunk in self.async_document_chain.astream({
                "context": context_docs,  # Pass Document objects, not formatted string
                "input": query_text
            }):
                # Extract content from chunk
                content = ""
                if isinstance(chunk, str):
                    content = chunk
                elif isinstance(chunk, dict) and "answer" in chunk:
                    content = chunk["answer"]
                elif hasattr(chunk, "content"):
                    content = chunk.content
                
                if content:
                    full_answer_accumulator += content
                    yield {"type": "chunk", "content": content}
            
            llm_duration = time.time() - llm_start
            total_duration = time.time() - start_time

            # 4. POST-PROCESSING (Metrics & Cache)
            # Initialize variables for metadata
            input_tokens = 0
            output_tokens = 0
            estimated_cost = 0.0
            
            if MONITORING_ENABLED:
                # Calculate metrics using accumulated answer
                prompt_text = self._build_prompt_text_with_history(
                    query_text, context_text, converted_chat_history
                )
                input_tokens, output_tokens = self._estimate_token_usage(
                    prompt_text,
                    full_answer_accumulator
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
                
                # Record actual spend in Redis
                try:
                    await record_spend(estimated_cost, input_tokens, output_tokens, LLM_MODEL_NAME)
                except Exception as e:
                    logger.warning(f"Error recording spend: {e}", exc_info=True)
                
                # Track retrieval metrics
                rag_retrieval_duration_seconds.observe(retrieval_duration)
                rag_documents_retrieved_total.observe(len(published_sources))
                rag_query_duration_seconds.labels(
                    query_type="stream",
                    cache_hit="false"
                ).observe(total_duration)
            
            # Cache the result (using truncated history)
            query_cache.set(query_text, truncated_history, full_answer_accumulator, published_sources)

            # Yield metadata before completion
            metadata = {
                "input_tokens": input_tokens if MONITORING_ENABLED else 0,
                "output_tokens": output_tokens if MONITORING_ENABLED else 0,
                "cost_usd": estimated_cost if MONITORING_ENABLED else 0.0,
                "duration_seconds": total_duration,
                "cache_hit": False,
                "cache_type": None,
            }
            yield {"type": "metadata", "metadata": metadata}

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
            
            # Yield metadata for error case
            metadata = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "duration_seconds": time.time() - start_time,
                "cache_hit": False,
                "cache_type": None,
            }
            yield {"type": "metadata", "metadata": metadata}
            
            # Return generic error message without exposing internal details
            yield {"type": "error", "error": "An error occurred while processing your query. Please try again or rephrase your question."}


# Example of how to use the RAGPipeline class (for testing or direct script use)
if __name__ == "__main__":
    # This ensures .env is loaded if running this script directly
    from dotenv import load_dotenv
    dotenv_path_actual = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path_actual):
        print(f"RAGPipeline direct run: Loading .env from {dotenv_path_actual}")
        load_dotenv(dotenv_path=dotenv_path_actual, override=True)
    else:
        print("RAGPipeline direct run: .env file not found. Ensure GOOGLE_API_KEY and MONGO_URI are set.")

    async def main():
        print("Testing RAGPipeline class with local embeddings and Google Flash 2.5...")
        try:
            pipeline = RAGPipeline()  # Uses default collection

            # Test 1: Initial query
            initial_query = "What is Litecoin?"
            print(f"\nQuerying pipeline with: '{initial_query}' (initial query)")
            answer, sources, metadata = await pipeline.aquery(initial_query, chat_history=[])
            print("\n--- Answer (Initial Query) ---")
            print(answer)
            print("\n--- Sources (Initial Query) ---")
            if sources:
                for i, doc in enumerate(sources):
                    print(f"Source {i+1}: {doc.page_content[:150]}... (Metadata: {doc.metadata.get('title', 'N/A')})")
            else:
                print("No sources retrieved.")

            # Test 2: Follow-up query with history
            follow_up_query = "Who created it?"
            simulated_history = [
                ("What is Litecoin?", "Litecoin is a peer-to-peer cryptocurrency and open-source software project released under the MIT/X11 license. It was inspired by Bitcoin but designed to have a faster block generation rate and use a different hashing algorithm.")
            ]
            print(f"\nQuerying pipeline with: '{follow_up_query}' (follow-up query)")
            answer, sources, metadata = await pipeline.aquery(follow_up_query, chat_history=simulated_history)
            
            print("\n--- Answer (Follow-up Query) ---")
            print(answer)
            print("\n--- Sources (Follow-up Query) ---")
            if sources:
                for i, doc in enumerate(sources):
                    print(f"Source {i+1}: {doc.page_content[:150]}... (Metadata: {doc.metadata.get('title', 'N/A')})")
            else:
                print("No sources retrieved.")
                
        except ValueError as ve:
            print(f"Initialization Error: {ve}")
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the async main function
    asyncio.run(main())
