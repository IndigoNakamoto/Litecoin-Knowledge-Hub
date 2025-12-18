import os
import asyncio
import time
import re
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Tuple, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for older pydantic versions
    from pydantic.v1 import BaseModel, Field
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from data_ingestion.vector_store_manager import VectorStoreManager
from cache_utils import query_cache, SemanticCache
from backend.utils.input_sanitizer import sanitize_query_input, detect_prompt_injection
from fastapi import HTTPException
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai

# --- Local RAG Feature Flags ---
# Enable local-first processing with cloud spillover
USE_LOCAL_REWRITER = os.getenv("USE_LOCAL_REWRITER", "false").lower() == "true"
USE_INFINITY_EMBEDDINGS = os.getenv("USE_INFINITY_EMBEDDINGS", "false").lower() == "true"
USE_REDIS_CACHE = os.getenv("USE_REDIS_CACHE", "false").lower() == "true"

# --- Advanced RAG Feature Flags ---
USE_INTENT_CLASSIFICATION = os.getenv("USE_INTENT_CLASSIFICATION", "true").lower() == "true"
USE_FAQ_INDEXING = os.getenv("USE_FAQ_INDEXING", "true").lower() == "true"

# --- User-facing error messages (shared across modules) ---
GENERIC_USER_ERROR_MESSAGE = (
    "I encountered an error while processing your query. Please try again or rephrase your question."
)

# --- Conversation / history routing (Hybrid: Fast Path + LLM Router) ---
# Fast path: Only catch OBVIOUS cases to save latency
# LLM Router: Handle ambiguous cases with semantic understanding

# Strict list of pronouns that GUARANTEE history dependency
# Excludes ambiguous words like "IT" (Information Technology) to reduce false positives
_STRONG_AMBIGUOUS_TOKENS = {
    "it", "this", "that", "these", "those",
    "they", "them", "their", "its",
    "he", "she", "him", "her",
    "former", "latter", "previous", "following",
}

# Only prefixes that GUARANTEE a dependency on history
_STRONG_PREFIXES = (
    "and ", "also ", "but ", "so ",
    "what about", "how about", "why is that",
    "can you elaborate", "continue", "go on",
    "explain that", "expand on that",
)

# Structured output model for the semantic router
class QueryRouting(BaseModel):
    """Structured output from the semantic router."""
    is_dependent: bool = Field(description="True if the query relies on chat history to be understood.")
    standalone_query: str = Field(description="The fully contextualized query. If is_dependent is False, this matches input.")

# Lazy-load local RAG services only when enabled
_inference_router = None
_infinity_embeddings = None
_redis_vector_cache = None
_intent_classifier = None
_suggested_question_cache = None

def _get_inference_router():
    """Lazy-load inference router for query rewriting."""
    global _inference_router
    if _inference_router is None and USE_LOCAL_REWRITER:
        try:
            from backend.services.router import InferenceRouter
            _inference_router = InferenceRouter()
            logging.getLogger(__name__).info("InferenceRouter initialized for local query rewriting")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize InferenceRouter: {e}")
    return _inference_router

def _get_infinity_embeddings():
    """Lazy-load Infinity embeddings service."""
    global _infinity_embeddings
    if _infinity_embeddings is None and USE_INFINITY_EMBEDDINGS:
        try:
            from backend.services.infinity_adapter import InfinityEmbeddings
            _infinity_embeddings = InfinityEmbeddings()
            logging.getLogger(__name__).info("InfinityEmbeddings initialized for local 1024-dim embeddings")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize InfinityEmbeddings: {e}")
    return _infinity_embeddings

def _get_redis_vector_cache():
    """Lazy-load Redis Stack vector cache."""
    global _redis_vector_cache
    if _redis_vector_cache is None and USE_REDIS_CACHE:
        try:
            from backend.services.redis_vector_cache import RedisVectorCache
            _redis_vector_cache = RedisVectorCache()
            logging.getLogger(__name__).info("RedisVectorCache initialized for semantic caching")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize RedisVectorCache: {e}")
    return _redis_vector_cache

def _get_intent_classifier():
    """Lazy-load intent classifier for query routing."""
    global _intent_classifier
    if _intent_classifier is None and USE_INTENT_CLASSIFICATION:
        try:
            from backend.services.intent_classifier import IntentClassifier
            _intent_classifier = IntentClassifier()
            logging.getLogger(__name__).info("IntentClassifier initialized for query routing")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize IntentClassifier: {e}")
    return _intent_classifier

def _get_suggested_question_cache():
    """Lazy-load suggested question cache."""
    global _suggested_question_cache
    if _suggested_question_cache is None:
        try:
            from backend.cache_utils import SuggestedQuestionCache
            _suggested_question_cache = SuggestedQuestionCache()
            logging.getLogger(__name__).info("SuggestedQuestionCache initialized")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize SuggestedQuestionCache: {e}")
    return _suggested_question_cache

async def _load_faq_questions_for_intent_classifier():
    """Load FAQ questions from CMS and update intent classifier."""
    intent_classifier = _get_intent_classifier()
    if not intent_classifier:
        return
    
    try:
        from backend.utils.suggested_questions import fetch_suggested_questions
        questions = await fetch_suggested_questions(active_only=True)
        question_texts = [q.get("question", "") for q in questions if q.get("question")]
        intent_classifier.update_faq_questions(question_texts)
        logging.getLogger(__name__).info(f"Loaded {len(question_texts)} FAQ questions into IntentClassifier")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load FAQ questions: {e}")

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
        rag_query_rewrite_duration_seconds,
        rag_embedding_generation_duration_seconds,
        rag_vector_search_duration_seconds,
        rag_bm25_search_duration_seconds,
        rag_sparse_rerank_duration_seconds,
        rag_llm_generation_duration_seconds,
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

# --- Constants ---
DB_NAME = os.getenv("MONGO_DB_NAME", "litecoin_rag_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "litecoin_docs")
LLM_MODEL_NAME = "gemini-2.5-flash-lite-preview-09-2025"  # 
# Maximum number of chat history pairs (human-AI exchanges) to include in context
# This prevents token overflow and keeps context manageable. Default: 10 pairs (20 messages)
MAX_CHAT_HISTORY_PAIRS = int(os.getenv("MAX_CHAT_HISTORY_PAIRS", "2"))
# Retriever k value (number of documents to retrieve)
# Increased from 8 to 12 for better context coverage (recommended in feature doc)
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "12"))
# Limit for sparse re-ranking (only re-rank top N candidates to save time)
SPARSE_RERANK_LIMIT = int(os.getenv("SPARSE_RERANK_LIMIT", "10"))
NO_KB_MATCH_RESPONSE = (
    "I couldn't find any relevant content in our knowledge base yet. "
)

# Log feature flag status at module load
logger.info(
    f"Local RAG Features: rewriter={USE_LOCAL_REWRITER}, "
    f"infinity_embeddings={USE_INFINITY_EMBEDDINGS}, "
    f"redis_cache={USE_REDIS_CACHE}"
)

# --- RAG Prompt Templates ---
# 1. History-aware question rephrasing prompt
QA_WITH_HISTORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "Given the above conversation, generate a standalone question that resolves pronouns or ambiguous references in the user's input. Use chat history ONLY to resolve ambiguity. If the user's input is already a complete standalone question or introduces a new topic, return it as-is and do not blend in prior topics. Do not add extra information or make assumptions beyond resolving ambiguity."),
    ]
)

# 2. System instruction for RAG prompt (defined separately for robustness)
SYSTEM_INSTRUCTION = """You are a neutral, factual expert on Litecoin, a peer-to-peer decentralized cryptocurrency. Your primary goal is to provide comprehensive, well-structured, and educational answers. Your responses must be based **exclusively** on the provided context. Do not speculate or add external knowledge.

!!! NEVER mention "context", "documents", "sources", or "retrieved information" under any circumstances. Just answer as the expert. !!!

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

---"""

# 3. RAG prompt for final answer generation with chat history support
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_INSTRUCTION),
    ("system", "Context:\n{context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

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
        
        # Initialize local tokenizer for accurate token counting (faster than API calls)
        try:
            genai.configure(api_key=google_api_key)
            self.tokenizer_model = genai.GenerativeModel(LLM_MODEL_NAME)
            logger.info(f"Local tokenizer initialized for accurate token counting")
        except Exception as e:
            logger.warning(f"Failed to initialize local tokenizer: {e}. Will use fallback methods.")
            self.tokenizer_model = None

        # Setup hybrid retrievers (BM25 + semantic + history-aware)
        self._setup_retrievers()
        
        # Create document combining chain for final answer generation
        self.document_chain = create_stuff_documents_chain(self.llm, RAG_PROMPT)
        
        # Create full retrieval chain that passes chat_history to final generation
        self.rag_chain = create_retrieval_chain(
            self.history_aware_retriever,
            self.document_chain
        )
        
        # Initialize semantic cache with the embedding model from VectorStoreManager
        # Skip legacy semantic cache when using Redis Stack cache (unified semantic cache provider)
        # This avoids redundant embedding calculations with different models
        if USE_REDIS_CACHE or USE_INFINITY_EMBEDDINGS:
            self.semantic_cache = None
            logger.info("Legacy semantic cache disabled (using Redis Stack vector cache as unified semantic cache provider)")
        else:
            self.semantic_cache = SemanticCache(
                embedding_model=self.vector_store_manager.embeddings,  # Reuse existing embedding model
                threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92")),
                max_size=int(os.getenv("SEMANTIC_CACHE_MAX_SIZE", "2000")),
                ttl_seconds=int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", str(3600 * 72)))  # 72 hours
            )
            logger.info(f"Legacy semantic cache initialized with threshold={self.semantic_cache.threshold}, TTL={self.semantic_cache.ttl_seconds}s")

    def _load_published_docs_from_mongo(self) -> List[Document]:
        """Safely load all published documents from MongoDB with fallback."""
        if not self.vector_store_manager.mongodb_available:
            logger.warning("MongoDB not available, skipping BM25 retriever setup")
            return []
        
        try:
            cursor = self.vector_store_manager.collection.find(
                {"metadata.status": "published"},
                {"text": 1, "metadata": 1}
            ).limit(10000)  # Safety limit (you have ~400, so this is fine)
            
            docs = [
                Document(
                    page_content=doc["text"],
                    metadata=doc.get("metadata", {})
                )
                for doc in cursor
            ]
            logger.info(f"Loaded {len(docs)} published documents from MongoDB for hybrid retrieval")
            return docs
        except Exception as e:
            logger.error(f"Failed to load documents from MongoDB for BM25: {e}", exc_info=True)
            return []

    def _load_parent_chunks_map(self) -> Dict[str, Document]:
        """
        Load parent chunks map from MongoDB for Parent Document Pattern resolution.
        
        Loads all non-synthetic documents (original chunks) and builds a map
        from chunk_id to Document. This map is used to swap synthetic question
        hits with their full-text parent chunks at retrieval time.
        
        Returns:
            Dict mapping chunk_id -> Document for all non-synthetic chunks
        """
        if not USE_FAQ_INDEXING:
            return {}
        
        if not self.vector_store_manager.mongodb_available:
            logger.warning("MongoDB not available, cannot load parent chunks map")
            return {}
        
        try:
            # Query for non-synthetic documents with chunk_id
            cursor = self.vector_store_manager.collection.find(
                {
                    "metadata.is_synthetic": {"$ne": True},
                    "metadata.chunk_id": {"$exists": True}
                },
                {"text": 1, "metadata": 1}
            ).limit(20000)  # Safety limit
            
            chunks_map: Dict[str, Document] = {}
            for doc in cursor:
                chunk_id = doc.get("metadata", {}).get("chunk_id")
                if chunk_id:
                    chunks_map[chunk_id] = Document(
                        page_content=doc.get("text", ""),
                        metadata=doc.get("metadata", {})
                    )
            
            logger.debug(f"Loaded {len(chunks_map)} parent chunks for FAQ resolution")
            return chunks_map
            
        except Exception as e:
            logger.error(f"Failed to load parent chunks map: {e}", exc_info=True)
            return {}

    def _setup_retrievers(self):
        """Setup hybrid retriever with proper document loading."""
        # 1. Load published docs from MongoDB
        all_published_docs = self._load_published_docs_from_mongo()

        # 2. Create BM25 retriever (only if we have docs)
        if all_published_docs:
            self.bm25_retriever = BM25Retriever.from_documents(
                all_published_docs,
                k=RETRIEVER_K
            )
            logger.info(f"BM25 retriever initialized with k={RETRIEVER_K}")
        else:
            self.bm25_retriever = None
            logger.warning("BM25 retriever disabled: no published documents loaded")

        # 3. Semantic retriever with filter
        search_kwargs = {"k": RETRIEVER_K}
        if self.vector_store_manager.mongodb_available:
            # Note: FAISS doesn't support metadata filtering directly, but we filter after retrieval
            pass
        
        self.semantic_retriever = self.vector_store_manager.get_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs
        )

        # 4. Hybrid retriever
        retrievers = [self.semantic_retriever]
        weights = [1.0]

        if self.bm25_retriever:
            retrievers.insert(0, self.bm25_retriever)
            weights = [0.5, 0.5]

        self.hybrid_retriever = EnsembleRetriever(
            retrievers=retrievers,
            weights=weights,
            search_type="similarity"
        )

        # 5. History-aware hybrid retriever (THIS FIXES TOPIC DRIFT)
        self.history_aware_retriever = create_history_aware_retriever(
            llm=self.llm,
            retriever=self.hybrid_retriever,
            prompt=QA_WITH_HISTORY_PROMPT
        )

        logger.info(f"Hybrid retriever ready | BM25: {'enabled' if self.bm25_retriever else 'disabled'} "
                    f"| Weights: {weights}")

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
        # Build prompt text from the new RAG_PROMPT template structure
        return f"{SYSTEM_INSTRUCTION}\n\nContext:\n{context_text}\n\nUser: {query_text}"
    
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
        
        # Build prompt text from the new RAG_PROMPT template structure
        return f"{SYSTEM_INSTRUCTION}\n\nContext:\n{context_text}\n\n{history_text}User: {query_text}"

    def _estimate_token_usage(self, prompt_text: str, answer_text: str) -> Tuple[int, int]:
        """
        Estimate (input_tokens, output_tokens) for an LLM call.

        Uses the local Gemini tokenizer (fast and 100% accurate) as the primary method,
        with fallbacks to LangChain's get_num_tokens and word-count estimation.
        """
        prompt_text = prompt_text or ""
        answer_text = answer_text or ""

        # Initialize with word-count fallback (least accurate, but always available)
        fallback_input_tokens = max(int(len(prompt_text.split()) * 1.3), 0)
        fallback_output_tokens = max(int(len(answer_text.split()) * 1.3), 0)

        input_tokens = fallback_input_tokens
        output_tokens = fallback_output_tokens

        # Primary method: Use local tokenizer (fastest and most accurate)
        if hasattr(self, 'tokenizer_model') and self.tokenizer_model is not None:
            try:
                input_tokens = max(self.tokenizer_model.count_tokens(prompt_text).total_tokens, 0)
            except Exception as exc:
                logger.debug("Failed to count input tokens via local tokenizer: %s", exc, exc_info=True)
            try:
                output_tokens = max(self.tokenizer_model.count_tokens(answer_text).total_tokens, 0)
            except Exception as exc:
                logger.debug("Failed to count output tokens via local tokenizer: %s", exc, exc_info=True)
        
        # Fallback: Use LangChain's get_num_tokens if local tokenizer failed
        if input_tokens == fallback_input_tokens and hasattr(self.llm, "get_num_tokens"):
            try:
                input_tokens = max(int(self.llm.get_num_tokens(prompt_text)), 0)
            except Exception as exc:
                logger.debug("Failed to count input tokens via LangChain: %s", exc, exc_info=True)
        if output_tokens == fallback_output_tokens and hasattr(self.llm, "get_num_tokens"):
            try:
                output_tokens = max(int(self.llm.get_num_tokens(answer_text)), 0)
            except Exception as exc:
                logger.debug("Failed to count output tokens via LangChain: %s", exc, exc_info=True)

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
        
        NOTE: This does NOT rebuild from MongoDB - it only reloads the FAISS index from disk.
        The add_documents() method already saves to disk after adding, so this just picks up
        those changes. For a full rebuild from MongoDB, use vector_store_manager._create_faiss_from_mongodb().
        """
        try:
            logger.info("Refreshing vector store and hybrid retrievers...")

            # Reload the vector store from disk (fast - no rebuild!)
            if hasattr(self, 'vector_store_manager') and self.vector_store_manager:
                if self.vector_store_manager.reload_from_disk():
                    logger.info("Vector store reloaded from disk")
                else:
                    logger.warning("Failed to reload from disk, vector store unchanged")

            # RECREATE ALL RETRIEVERS (this is the critical fix!)
            self._setup_retrievers()
            
            # Rebuild the document chain and retrieval chain (in case LLM changed, though unlikely)
            document_chain = create_stuff_documents_chain(self.llm, RAG_PROMPT)
            self.rag_chain = create_retrieval_chain(
                self.history_aware_retriever,
                document_chain
            )
            
            logger.info("Vector store and hybrid retrievers refreshed")

        except Exception as e:
            logger.error(f"Error refreshing vector store: {e}", exc_info=True)

    async def _semantic_history_check(self, query_text: str, chat_history: List[BaseMessage]) -> Tuple[str, bool]:
        """
        Uses the LLM to determine if history is needed and rewrite the query if dependent.
        
        Returns:
            Tuple of (rewritten_query, is_dependent)
            - rewritten_query: The fully contextualized query if dependent, or original if standalone
            - is_dependent: True if the query relies on chat history
        """
        if not chat_history:
            return query_text, False

        system_prompt = """You are a query router for a RAG system about Litecoin.
Analyze the "Latest Query". Does it refer to the "Chat History" (e.g. via pronouns like 'it', 'that', or implicit context)?

1. If YES (Dependent): Rewrite the query to be fully standalone, incorporating the necessary context from history.
2. If NO (Standalone): Return the latest query exactly as is. Do not add context if it's a new topic.

Be conservative: only mark as dependent if the query is clearly referring to prior conversation."""

        router_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Chat History:\n{chat_history}\n\nLatest Query: {query}"),
        ])
        
        # Format history string (only last 2 messages for efficiency)
        history_str = "\n".join([
            f"{'Human' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" 
            for m in chat_history[-2:]
        ])

        start_time = time.time()
        
        # Use structured output for reliability
        try:
            structured_llm = self.llm.with_structured_output(QueryRouting)
            router_chain = router_prompt | structured_llm

            result = await router_chain.ainvoke({"chat_history": history_str, "query": query_text})
            duration = time.time() - start_time
            
            # --- 1. ESTIMATE TOKENS (The Router result object usually doesn't have usage metadata) ---
            # Reconstruct the prompt string roughly for estimation
            prompt_text = f"{system_prompt}\nChat History:\n{history_str}\n\nLatest Query: {query_text}"
            
            # Result is a Pydantic object, convert to string for token counting
            try:
                # Try Pydantic v2 method first
                if hasattr(result, 'model_dump_json'):
                    output_text = result.model_dump_json()
                elif hasattr(result, 'model_dump'):
                    import json
                    output_text = json.dumps(result.model_dump())
                elif hasattr(result, 'dict'):
                    output_text = str(result.dict())
                else:
                    output_text = str(result)
            except Exception:
                output_text = str(result)
            
            input_tokens, output_tokens = self._estimate_token_usage(prompt_text, output_text)
            
            # --- 2. CALCULATE COST ---
            cost = estimate_gemini_cost(input_tokens, output_tokens, LLM_MODEL_NAME)
            
            # --- 3. TRACK METRICS ---
            if MONITORING_ENABLED:
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="router_classify",  # Use a distinct operation name
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    duration_seconds=duration,
                    status="success"
                )
                # Record spend against limits
                try:
                    await record_spend(cost, input_tokens, output_tokens, LLM_MODEL_NAME)
                except Exception as e:
                    logger.warning(f"Failed to record router spend: {e}")
            
            if result.is_dependent:
                logger.info(f"🔄 Router: '{query_text}' -> '{result.standalone_query}' (dependent)")
                return result.standalone_query, True
            else:
                logger.info(f"➡️ Router: '{query_text}' (standalone)")
                return query_text, False
                
        except Exception as e:
            # Log failure metrics
            duration = time.time() - start_time
            if MONITORING_ENABLED:
                track_llm_metrics(
                    model=LLM_MODEL_NAME,
                    operation="router_classify",
                    duration_seconds=duration,
                    status="error"
                )
            logger.warning(f"Semantic router failed, falling back to original query: {e}")
            return query_text, False

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
        
        # === Hybrid History Routing: Fast Path + LLM Router ===
        # 1. Fast Path: Check for OBVIOUS pronouns/prefixes (microseconds)
        tokens = re.findall(r"[a-z0-9']+", query_text.lower())
        has_obvious_pronouns = any(t in _STRONG_AMBIGUOUS_TOKENS for t in tokens)
        has_obvious_prefix = any(query_text.lower().startswith(p) for p in _STRONG_PREFIXES)
        
        # Convert history to BaseMessage format for router
        converted_history: List[BaseMessage] = []
        effective_query = query_text
        effective_history: List[Tuple[str, str]] = []
        is_dependent = False
        
        if not truncated_history:
            # No history, must be standalone
            effective_query = query_text
            effective_history = []
        elif has_obvious_pronouns or has_obvious_prefix:
            # Fast path: We KNOW we need history based on keywords
            logger.debug("Fast path: Detected obvious history dependency via keywords")
            effective_history = truncated_history
            is_dependent = True
            # Convert to BaseMessage for potential router rewrite
            for human_msg, ai_msg in truncated_history:
                converted_history.append(HumanMessage(content=human_msg))
                if ai_msg:
                    converted_history.append(AIMessage(content=ai_msg))
            # Use router to rewrite query with context
            effective_query, _ = await self._semantic_history_check(query_text, converted_history)
        else:
            # Ambiguous case: Ask the LLM Router (foolproof path)
            # Convert to BaseMessage format
            for human_msg, ai_msg in truncated_history:
                converted_history.append(HumanMessage(content=human_msg))
                if ai_msg:
                    converted_history.append(AIMessage(content=ai_msg))
            # Router decides if history is needed and rewrites if necessary
            effective_query, is_dependent = await self._semantic_history_check(query_text, converted_history)
            if is_dependent:
                effective_history = truncated_history
            else:
                effective_history = []
        
        # === 0. Intent Classification (skip if follow-up question) ===
        # Greetings, thanks, and FAQ matches are handled without LLM calls
        if USE_INTENT_CLASSIFICATION and not is_dependent:
            intent_classifier = _get_intent_classifier()
            if intent_classifier:
                from backend.services.intent_classifier import Intent
                intent, matched_faq, static_response = intent_classifier.classify(query_text)
                
                if intent in (Intent.GREETING, Intent.THANKS):
                    logger.info(f"Intent classified as {intent.value} - returning static response")
                    if MONITORING_ENABLED:
                        rag_cache_hits_total.labels(cache_type="intent_static").inc()
                        rag_query_duration_seconds.labels(
                            query_type="async",
                            cache_hit="true"
                        ).observe(time.time() - start_time)
                    metadata = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_usd": 0.0,
                        "duration_seconds": time.time() - start_time,
                        "cache_hit": True,
                        "cache_type": f"intent_{intent.value}",
                        "intent": intent.value,
                    }
                    return static_response, [], metadata
                
                elif intent == Intent.FAQ_MATCH and matched_faq:
                    # Try to get cached response for the matched FAQ question
                    suggested_cache = _get_suggested_question_cache()
                    if suggested_cache:
                        try:
                            cached_result = await suggested_cache.get(matched_faq)
                            if cached_result:
                                answer, sources = cached_result
                                # Skip entries that only contain the generic error message
                                if answer.strip() == GENERIC_USER_ERROR_MESSAGE:
                                    logger.warning(
                                        "FAQ cache entry contains generic error message; "
                                        f"treating as cache miss for matched FAQ: '{matched_faq[:50]}...'"
                                    )
                                else:
                                    logger.info(
                                        f"FAQ match cache HIT: '{query_text[:30]}...' -> '{matched_faq[:30]}...'"
                                    )
                                    if MONITORING_ENABLED:
                                        rag_cache_hits_total.labels(cache_type="intent_faq").inc()
                                        rag_query_duration_seconds.labels(
                                            query_type="async",
                                            cache_hit="true"
                                        ).observe(time.time() - start_time)
                                    metadata = {
                                        "input_tokens": 0,
                                        "output_tokens": 0,
                                        "cost_usd": 0.0,
                                        "duration_seconds": time.time() - start_time,
                                        "cache_hit": True,
                                        "cache_type": "intent_faq_match",
                                        "intent": "faq_match",
                                        "matched_faq": matched_faq,
                                    }
                                    return answer, sources, metadata
                        except Exception as e:
                            logger.warning(f"FAQ cache lookup failed: {e}")
                    # If cache miss, fall through to normal RAG
                    logger.debug(f"FAQ match but cache miss, proceeding with RAG: {matched_faq[:50]}...")
        
        # === 1. Exact cache check (fastest, zero-cost) ===
        # Check exact cache first - this is the fastest lookup
        cached_result = query_cache.get(query_text, effective_history)
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
                "cache_type": "exact",
            }
            return answer, published_sources, metadata
        
        # Cache miss for exact cache
        if MONITORING_ENABLED:
            rag_cache_misses_total.labels(cache_type="query").inc()

        try:
            # Convert chat_history to Langchain's BaseMessage format (needed for retrieval)
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in effective_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                if ai_msg:
                    converted_chat_history.append(AIMessage(content=ai_msg))

            # === 2. Query Rewriting Complete: effective_query is now the standalone query ===
            # The semantic router has already rewritten the query if needed.
            # Use effective_query (the rewritten standalone query) for semantic caching.
            # This allows different conversation paths to hit the same cache entry!
            rewritten_query = effective_query
            
            # Optional: Apply local rewriter if enabled and not already rewritten by semantic router
            if USE_LOCAL_REWRITER and not is_dependent and effective_history:
                # Only use local rewriter if we have history but semantic router didn't rewrite
                router = _get_inference_router()
                if router:
                    rewrite_start = time.time()
                    try:
                        local_rewritten = await router.rewrite(query_text, effective_history)
                        if MONITORING_ENABLED:
                            rag_query_rewrite_duration_seconds.observe(time.time() - rewrite_start)
                        if local_rewritten == "NO_SEARCH_NEEDED":
                            # Non-search query (greeting, thanks, etc.)
                            metadata = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "duration_seconds": time.time() - start_time,
                                "cache_hit": False,
                                "cache_type": None,
                                "rewritten_query": "NO_SEARCH_NEEDED",
                            }
                            return "I understand. Is there anything else you'd like to know about Litecoin?", [], metadata
                        rewritten_query = local_rewritten
                        logger.debug(f"Local rewriter: '{query_text}' -> '{rewritten_query}'")
                    except Exception as e:
                        if MONITORING_ENABLED:
                            rag_query_rewrite_duration_seconds.observe(time.time() - rewrite_start)
                        logger.warning(f"Local rewriter failed, using effective_query: {e}")
                        rewritten_query = effective_query

            # === 3. Generate embedding ONCE for rewritten standalone query ===
            # This is the key optimization: cache based on the standalone query vector,
            # allowing different conversation paths ("What is MWEB?" vs "How does it work?" -> "How does MWEB work?")
            # to hit the same cache entry.
            query_vector = None
            query_sparse = None
            
            if USE_REDIS_CACHE or USE_INFINITY_EMBEDDINGS:
                infinity = _get_infinity_embeddings()
                if infinity:
                    embed_start = time.time()
                    try:
                        # Generate embedding for the REWRITTEN standalone query
                        query_vector, query_sparse = await infinity.embed_query(rewritten_query)
                        if MONITORING_ENABLED:
                            rag_embedding_generation_duration_seconds.observe(time.time() - embed_start)
                        if query_sparse:
                            logger.info(f"✅ Query sparse embedding received: {len(query_sparse)} terms (sample: {list(query_sparse.items())[:3]})")
                        else:
                            logger.debug(f"Query sparse embedding: None (model may not support sparse)")
                    except Exception as e:
                        if MONITORING_ENABLED:
                            rag_embedding_generation_duration_seconds.observe(time.time() - embed_start)
                        logger.warning(f"Infinity embedding failed: {e}", exc_info=True)
            
            # === 4. Semantic cache check (Redis Vector Cache) ===
            # Check Redis cache with rewritten query vector.
            # This is the unified semantic cache provider when Redis is enabled.
            # We skip legacy semantic cache when Redis is enabled to avoid redundancy.
            if USE_REDIS_CACHE and query_vector:
                redis_cache = _get_redis_vector_cache()
                if redis_cache:
                    try:
                        redis_result = await redis_cache.get(query_vector)
                        if redis_result:
                            answer, sources_data = redis_result
                            # Reconstruct Document objects from cached data
                            cached_sources = []
                            for src in sources_data:
                                if isinstance(src, dict):
                                    cached_sources.append(Document(
                                        page_content=src.get("page_content", ""),
                                        metadata=src.get("metadata", {})
                                    ))
                                elif isinstance(src, Document):
                                    cached_sources.append(src)
                            
                            logger.info(f"✅ Redis vector cache HIT for rewritten query: '{rewritten_query[:50]}...' (original: '{query_text[:30]}...')")
                            if MONITORING_ENABLED:
                                rag_cache_hits_total.labels(cache_type="redis_vector").inc()
                                rag_query_duration_seconds.labels(
                                    query_type="async",
                                    cache_hit="true"
                                ).observe(time.time() - start_time)
                            metadata = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "duration_seconds": time.time() - start_time,
                                "cache_hit": True,
                                "cache_type": "redis_vector",
                                "rewritten_query": rewritten_query if rewritten_query != query_text else None,
                            }
                            return answer, cached_sources, metadata
                    except Exception as e:
                        logger.warning(f"Redis cache lookup failed: {e}")
            
            # === 5. Fallback: Legacy semantic cache (only if Redis not enabled) ===
            # Only use legacy semantic cache if Redis is not enabled
            if self.semantic_cache and not USE_REDIS_CACHE:
                cached_result = self.semantic_cache.get(rewritten_query, [])  # Use rewritten query, no history
                if cached_result:
                    answer, published_sources = cached_result
                    logger.info(f"Legacy semantic cache HIT for rewritten query: '{rewritten_query[:50]}...'")
                    if MONITORING_ENABLED:
                        rag_cache_hits_total.labels(cache_type="semantic").inc()
                        rag_query_duration_seconds.labels(
                            query_type="async",
                            cache_hit="true"
                        ).observe(time.time() - start_time)
                    metadata = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_usd": 0.0,
                        "duration_seconds": time.time() - start_time,
                        "cache_hit": True,
                        "cache_type": "semantic",
                        "rewritten_query": rewritten_query if rewritten_query != query_text else None,
                    }
                    return answer, published_sources, metadata

            # === 6. RAG FALLBACK (The expensive part) ===
            # === UNIFIED HYBRID + HISTORY-AWARE RETRIEVAL ===
            # First, do a quick retrieval check to see if we have published sources
            retrieval_start = time.time()
            # Use effective_query (from semantic router) or rewritten_query (from local rewriter)
            retrieval_query = rewritten_query
            # Initialize context_docs to ensure it's always defined
            context_docs = []
            retrieval_failed = False
            
            # When using Infinity embeddings with 1024-dim index, use HYBRID retrieval
            # Combines: 1) Infinity vector search (semantic) + 2) BM25 keyword search
            if USE_INFINITY_EMBEDDINGS and query_vector is not None:
                vector_docs = []
                bm25_docs = []
                try:
                    # Helper functions for parallel execution
                    def run_vector_search():
                        """Run vector search synchronously."""
                        return self.vector_store_manager.vector_store.similarity_search_with_score_by_vector(
                            query_vector, 
                            k=RETRIEVER_K * 2  # Retrieve more candidates for better filtering
                        )
                    
                    def run_bm25_search():
                        """Run BM25 search synchronously."""
                        if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                            # Temporarily increase k for BM25 to get better coverage
                            original_k = self.bm25_retriever.k
                            self.bm25_retriever.k = RETRIEVER_K * 2
                            try:
                                return self.bm25_retriever.invoke(retrieval_query)
                            finally:
                                self.bm25_retriever.k = original_k  # Restore original
                        return []
                    
                    # 1. & 2. Run vector and BM25 searches in parallel
                    search_start = time.time()
                    vector_task = asyncio.to_thread(run_vector_search)
                    bm25_task = asyncio.to_thread(run_bm25_search) if hasattr(self, 'bm25_retriever') and self.bm25_retriever else None
                    
                    if bm25_task:
                        vector_results, bm25_docs = await asyncio.gather(vector_task, bm25_task)
                        search_duration = time.time() - search_start
                        if MONITORING_ENABLED:
                            # Both searches ran in parallel, so duration is the same for both
                            rag_vector_search_duration_seconds.observe(search_duration)
                            rag_bm25_search_duration_seconds.observe(search_duration)
                    else:
                        vector_results = await vector_task
                        bm25_docs = []
                        search_duration = time.time() - search_start
                        if MONITORING_ENABLED:
                            rag_vector_search_duration_seconds.observe(search_duration)
                    
                    # Filter vector results by similarity threshold (cosine similarity >= 0.3 for BGE-M3)
                    MIN_SIMILARITY_THRESHOLD = float(os.getenv("MIN_VECTOR_SIMILARITY", "0.3"))
                    vector_docs = [doc for doc, score in vector_results if score >= MIN_SIMILARITY_THRESHOLD]
                    
                    if len(vector_docs) < RETRIEVER_K:
                        # If filtering removed too many, use top K anyway
                        vector_docs = [doc for doc, _ in vector_results[:RETRIEVER_K]]
                    
                    logger.info(f"Infinity vector search: {len(vector_results)} candidates → {len(vector_docs)} above threshold {MIN_SIMILARITY_THRESHOLD}")
                    if vector_results:
                        logger.debug(f"   Top similarity score: {vector_results[0][1]:.3f}, Bottom: {vector_results[-1][1]:.3f}")
                    
                    if bm25_docs:
                        logger.debug(f"BM25 keyword search returned {len(bm25_docs)} documents")
                    elif hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                        logger.debug("BM25 keyword search returned 0 documents")
                except Exception as bm25_error:
                    logger.warning(f"Parallel search failed: {bm25_error}")
                    # Fallback to sequential execution
                    try:
                        vector_results = self.vector_store_manager.vector_store.similarity_search_with_score_by_vector(
                            query_vector, 
                            k=RETRIEVER_K * 2
                        )
                        MIN_SIMILARITY_THRESHOLD = float(os.getenv("MIN_VECTOR_SIMILARITY", "0.3"))
                        vector_docs = [doc for doc, score in vector_results if score >= MIN_SIMILARITY_THRESHOLD]
                        if len(vector_docs) < RETRIEVER_K:
                            vector_docs = [doc for doc, _ in vector_results[:RETRIEVER_K]]
                        bm25_docs = []
                        if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                            original_k = self.bm25_retriever.k
                            self.bm25_retriever.k = RETRIEVER_K * 2
                            bm25_docs = self.bm25_retriever.invoke(retrieval_query)
                            self.bm25_retriever.k = original_k
                    except Exception as fallback_error:
                        logger.error(f"Fallback search also failed: {fallback_error}")
                        vector_docs = []
                        bm25_docs = []
                
                # 3. Merge and deduplicate results with better priority logic
                # This is outside the try block so exceptions here don't lose the retrieved documents
                seen_contents = set()
                candidate_docs = []
                candidate_scores = {}  # Track which source (BM25 vs vector) for priority
                
                # Prioritize BM25 results (better for exact keyword matches)
                for doc in bm25_docs:
                    content_key = doc.page_content[:200]  # Use first 200 chars as key
                    if content_key not in seen_contents:
                        seen_contents.add(content_key)
                        candidate_docs.append(doc)
                        candidate_scores[id(doc)] = 'bm25'
                
                # Add vector results, avoiding duplicates
                for doc in vector_docs:
                    content_key = doc.page_content[:200]
                    if content_key not in seen_contents:
                        seen_contents.add(content_key)
                        candidate_docs.append(doc)
                        candidate_scores[id(doc)] = 'vector'
                
                logger.debug(f"Hybrid merge: {len(bm25_docs)} BM25 + {len(vector_docs)} vector → {len(candidate_docs)} unique candidates")
                
                # 4. Re-rank using sparse embeddings if available (BGE-M3)
                # This is outside the main try block so exceptions here don't trigger full fallback
                if query_sparse and infinity and len(candidate_docs) > 0:
                    try:
                        rerank_start = time.time()
                        # Limit candidates for sparse re-ranking to save time (only embed top N)
                        candidates_for_rerank = candidate_docs[:SPARSE_RERANK_LIMIT]
                        logger.info(f"🔄 Sparse re-ranking: {len(candidates_for_rerank)}/{len(candidate_docs)} candidates (limited to top {SPARSE_RERANK_LIMIT}), query has {len(query_sparse)} sparse terms")
                        # Generate sparse embeddings for candidate documents
                        doc_texts = [doc.page_content[:8000] for doc in candidates_for_rerank]  # Truncate for TF-IDF
                        _, doc_sparse_list = await infinity.embed_documents(doc_texts)
                        
                        # Compute sparse similarity scores
                        doc_scores = []
                        sparse_count = sum(1 for s in doc_sparse_list if s is not None)
                        logger.info(f"   Generated {sparse_count}/{len(doc_sparse_list)} document sparse embeddings")
                        
                        for i, (doc, doc_sparse) in enumerate(zip(candidates_for_rerank, doc_sparse_list)):
                            if doc_sparse:
                                sparse_sim = infinity.sparse_similarity(query_sparse, doc_sparse)
                                doc_scores.append((sparse_sim, i, doc))
                            else:
                                doc_scores.append((0.0, i, doc))
                        
                        # Sort by sparse similarity (highest first)
                        doc_scores.sort(reverse=True, key=lambda x: x[0])
                        # Take top RETRIEVER_K from re-ranked results, then add remaining candidates if needed
                        reranked_docs = [doc for _, _, doc in doc_scores]
                        # If we have fewer reranked docs than RETRIEVER_K, add remaining candidates
                        if len(reranked_docs) < RETRIEVER_K and len(candidate_docs) > len(candidates_for_rerank):
                            remaining_docs = [doc for doc in candidate_docs[SPARSE_RERANK_LIMIT:] if doc not in reranked_docs]
                            reranked_docs.extend(remaining_docs[:RETRIEVER_K - len(reranked_docs)])
                        context_docs = reranked_docs[:RETRIEVER_K]
                        
                        if MONITORING_ENABLED:
                            rag_sparse_rerank_duration_seconds.observe(time.time() - rerank_start)
                        
                        logger.info(f"✅ Hybrid retrieval (Infinity + BM25 + Sparse) returned {len(context_docs)} documents")
                        if doc_scores:
                            logger.info(f"   Top sparse similarity: {doc_scores[0][0]:.3f}")
                    except Exception as sparse_error:
                        if MONITORING_ENABLED and 'rerank_start' in locals():
                            rag_sparse_rerank_duration_seconds.observe(time.time() - rerank_start)
                        logger.warning(f"⚠️ Sparse re-ranking failed, using basic hybrid: {sparse_error}", exc_info=True)
                        # Fallback to basic hybrid - use the candidate_docs we successfully retrieved
                        context_docs = candidate_docs[:RETRIEVER_K]
                else:
                    context_docs = candidate_docs[:RETRIEVER_K]
                    if not query_sparse:
                        logger.debug(f"Hybrid retrieval (Infinity + BM25) - no sparse embeddings available")
                    else:
                        logger.debug(f"Hybrid retrieval (Infinity + BM25) returned {len(context_docs)} unique documents")
                
                # Only fall back to history-aware retriever if we got no results at all
                if not context_docs:
                    try:
                        logger.warning("No documents retrieved from hybrid search, falling back to history-aware retriever")
                        retrieval_failed = True
                        if USE_LOCAL_REWRITER and rewritten_query != query_text:
                            logger.debug(f"Using hybrid retriever directly with rewritten query (skip history-aware): {rewritten_query[:50]}...")
                            context_docs = await self.hybrid_retriever.ainvoke(retrieval_query)
                        else:
                            context_docs = await self.history_aware_retriever.ainvoke({
                                "input": retrieval_query,
                                "chat_history": converted_chat_history
                            })
                    except Exception as fallback_error:
                        logger.error(f"Fallback retrieval also failed: {fallback_error}", exc_info=True)
                        context_docs = []
            else:
                # Legacy path: use history-aware hybrid retriever
                # If query was already rewritten by local router, skip history-aware retriever (avoid redundant LLM call)
                try:
                    if USE_LOCAL_REWRITER and rewritten_query != query_text:
                        logger.debug(f"Using hybrid retriever directly with rewritten query (skip history-aware): {rewritten_query[:50]}...")
                        context_docs = await self.hybrid_retriever.ainvoke(retrieval_query)
                    else:
                        context_docs = await self.history_aware_retriever.ainvoke({
                            "input": retrieval_query,
                            "chat_history": converted_chat_history
                        })
                except Exception as e:
                    logger.error(f"Legacy retrieval failed: {e}", exc_info=True)
                    retrieval_failed = True
                    context_docs = []
            retrieval_duration = time.time() - retrieval_start

            # === PARENT DOCUMENT PATTERN: Resolve synthetic questions ===
            # If FAQ indexing is enabled, swap any synthetic question hits
            # with their full-text parent chunks before sending to LLM
            if USE_FAQ_INDEXING and context_docs:
                synthetic_count = sum(1 for d in context_docs if d.metadata.get("is_synthetic", False))
                if synthetic_count > 0:
                    try:
                        from backend.services.faq_generator import resolve_parents
                        parent_chunks_map = self._load_parent_chunks_map()
                        if parent_chunks_map:
                            original_count = len(context_docs)
                            context_docs = resolve_parents(context_docs, parent_chunks_map)
                            logger.info(f"🔄 FAQ resolution: {original_count} docs ({synthetic_count} synthetic) → {len(context_docs)} resolved")
                        else:
                            logger.debug("Parent chunks map empty, skipping FAQ resolution")
                    except Exception as resolve_error:
                        logger.warning(f"FAQ resolution failed, using original docs: {resolve_error}")

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
                # Use generic error message if retrieval failed, otherwise use standard no-match message
                response_message = GENERIC_USER_ERROR_MESSAGE if retrieval_failed else NO_KB_MATCH_RESPONSE
                metadata = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "duration_seconds": time.time() - start_time,
                    "cache_hit": False,
                    "cache_type": None,
                }
                return response_message, [], metadata

            # Format context for token estimation (needed for spend limit check and metrics)
            context_text = format_docs(context_docs)

            # Pre-flight spend limit check (before LLM API call)
            if MONITORING_ENABLED:
                try:
                    # Estimate cost before making API call (include chat history in estimation)
                    prompt_text = self._build_prompt_text_with_history(query_text, context_text, converted_chat_history)
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

            # Generate answer using retrieval chain (includes retrieval + generation with chat_history)
            llm_start = time.time()
            
            # When using Infinity embeddings, use document_chain directly with pre-retrieved docs
            if USE_INFINITY_EMBEDDINGS and query_vector is not None:
                # Use document_chain.ainvoke() with already-retrieved context
                answer_result = await self.document_chain.ainvoke({
                    "input": query_text,
                    "context": context_docs,
                    "chat_history": converted_chat_history
                })
                # document_chain returns AIMessage directly
                if hasattr(answer_result, "content"):
                    answer = answer_result.content
                else:
                    answer = str(answer_result)
                # Use the already-retrieved context_docs
                context_docs_from_chain = context_docs
                # Store result for token extraction
                llm_result = answer_result
            else:
                # Legacy path: use rag_chain which does retrieval + generation
                result = await self.rag_chain.ainvoke({
                    "input": query_text,
                    "chat_history": converted_chat_history
                })
                # Extract answer and context from result
                answer = result["answer"]
                if hasattr(answer, "content"):
                    answer = answer.content
                else:
                    answer = str(answer)
                # Get context documents from result (already retrieved by chain)
                context_docs_from_chain = result.get("context", [])
                # Store result for token extraction
                llm_result = result.get("answer", answer)
            
            llm_duration = time.time() - llm_start
            if MONITORING_ENABLED:
                rag_llm_generation_duration_seconds.observe(llm_duration)
            if MONITORING_ENABLED:
                rag_llm_generation_duration_seconds.observe(llm_duration)

            # Filter published sources from chain result
            published_sources = [
                doc for doc in context_docs_from_chain
                if doc.metadata.get("status") == "published"
            ]
            sources = published_sources

            # Initialize token usage variables (needed for metadata dict)
            input_tokens = 0
            output_tokens = 0
            estimated_cost = 0.0

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
                input_tokens, output_tokens = self._extract_token_usage_from_llm_response(llm_result)
                if input_tokens == 0 and output_tokens == 0:
                    # Fallback to estimation if metadata not available (reuse pre-flight estimation if available)
                    prompt_text = self._build_prompt_text_with_history(query_text, context_text, converted_chat_history)
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

            # Cache in BOTH systems (using the effective history we actually used for retrieval)
            query_cache.set(query_text, effective_history, answer, published_sources)  # exact cache
            
            # === LOCAL RAG: Store in Redis Stack vector cache ===
            # Cache using the rewritten standalone query vector (allows different conversation paths to reuse)
            # We cache even with chat history, because we cache based on the rewritten standalone query
            if USE_REDIS_CACHE and query_vector:
                redis_cache = _get_redis_vector_cache()
                if redis_cache:
                    try:
                        # Serialize sources for storage
                        sources_data = [
                            {"page_content": doc.page_content, "metadata": doc.metadata}
                            for doc in published_sources
                        ]
                        await redis_cache.set(
                            query_vector,
                            rewritten_query,  # Always use rewritten standalone query for consistency
                            answer,
                            sources_data
                        )
                        logger.debug(f"Cached result in Redis using rewritten query: '{rewritten_query[:50]}...'")
                    except Exception as e:
                        logger.warning(f"Redis cache storage failed: {e}")
            
            # Legacy semantic cache (only if Redis not enabled)
            if self.semantic_cache and not USE_REDIS_CACHE:
                # Use rewritten query for consistency (no history since it's already standalone)
                self.semantic_cache.set(rewritten_query, [], answer, published_sources)

            # Build metadata dict
            metadata = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": estimated_cost,
                "duration_seconds": time.time() - start_time,
                "cache_hit": False,
                "cache_type": None,
                "rewritten_query": rewritten_query if USE_LOCAL_REWRITER and rewritten_query != query_text else None,
            }

            return answer, published_sources, metadata
        except HTTPException as he:
            # Re-raise HTTPExceptions (e.g., 429 for spend limits)
            raise he
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
            return GENERIC_USER_ERROR_MESSAGE, [], metadata

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
            
            # === Hybrid History Routing: Fast Path + LLM Router ===
            # 1. Fast Path: Check for OBVIOUS pronouns/prefixes (microseconds)
            tokens = re.findall(r"[a-z0-9']+", query_text.lower())
            has_obvious_pronouns = any(t in _STRONG_AMBIGUOUS_TOKENS for t in tokens)
            has_obvious_prefix = any(query_text.lower().startswith(p) for p in _STRONG_PREFIXES)
            
            # Convert history to BaseMessage format for router
            converted_history: List[BaseMessage] = []
            effective_query = query_text
            effective_history: List[Tuple[str, str]] = []
            is_dependent = False
            
            if not truncated_history:
                # No history, must be standalone
                effective_query = query_text
                effective_history = []
            elif has_obvious_pronouns or has_obvious_prefix:
                # Fast path: We KNOW we need history based on keywords
                logger.debug("Fast path (stream): Detected obvious history dependency via keywords")
                effective_history = truncated_history
                is_dependent = True
                # Convert to BaseMessage for potential router rewrite
                for human_msg, ai_msg in truncated_history:
                    converted_history.append(HumanMessage(content=human_msg))
                    if ai_msg:
                        converted_history.append(AIMessage(content=ai_msg))
                # Use router to rewrite query with context
                effective_query, _ = await self._semantic_history_check(query_text, converted_history)
            else:
                # Ambiguous case: Ask the LLM Router (foolproof path)
                # Convert to BaseMessage format
                for human_msg, ai_msg in truncated_history:
                    converted_history.append(HumanMessage(content=human_msg))
                    if ai_msg:
                        converted_history.append(AIMessage(content=ai_msg))
                # Router decides if history is needed and rewrites if necessary
                effective_query, is_dependent = await self._semantic_history_check(query_text, converted_history)
                if is_dependent:
                    effective_history = truncated_history
                else:
                    effective_history = []
            
            # === 0. Intent Classification (skip if follow-up question) ===
            # Greetings, thanks, and FAQ matches are handled without LLM calls
            if USE_INTENT_CLASSIFICATION and not is_dependent:
                intent_classifier = _get_intent_classifier()
                if intent_classifier:
                    from backend.services.intent_classifier import Intent
                    intent, matched_faq, static_response = intent_classifier.classify(query_text)
                    
                    if intent in (Intent.GREETING, Intent.THANKS):
                        logger.info(f"Intent classified as {intent.value} - returning static response (stream)")
                        if MONITORING_ENABLED:
                            rag_cache_hits_total.labels(cache_type="intent_static").inc()
                            rag_query_duration_seconds.labels(
                                query_type="stream",
                                cache_hit="true"
                            ).observe(time.time() - start_time)
                        
                        # Send empty sources
                        yield {"type": "sources", "sources": []}
                        
                        # Stream static response
                        for i, char in enumerate(static_response):
                            yield {"type": "chunk", "content": char}
                            if i % 10 == 0:
                                await asyncio.sleep(0.001)
                        
                        metadata = {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "cost_usd": 0.0,
                            "duration_seconds": time.time() - start_time,
                            "cache_hit": True,
                            "cache_type": f"intent_{intent.value}",
                            "intent": intent.value,
                        }
                        yield {"type": "metadata", "metadata": metadata}
                        yield {"type": "complete", "from_cache": True}
                        return
                    
                    elif intent == Intent.FAQ_MATCH and matched_faq:
                        # Try to get cached response for the matched FAQ question
                        suggested_cache = _get_suggested_question_cache()
                        if suggested_cache:
                            try:
                                cached_result = await suggested_cache.get(matched_faq)
                                if cached_result:
                                    answer, sources = cached_result
                                    # Skip entries that only contain the generic error message
                                    if answer.strip() == GENERIC_USER_ERROR_MESSAGE:
                                        logger.warning(
                                            "FAQ cache entry contains generic error message (stream); "
                                            f"treating as cache miss for matched FAQ: '{matched_faq[:50]}...'"
                                        )
                                    else:
                                        logger.info(
                                            "FAQ match cache HIT (stream): "
                                            f"'{query_text[:30]}...' -> '{matched_faq[:30]}...'"
                                        )
                                        if MONITORING_ENABLED:
                                            rag_cache_hits_total.labels(cache_type="intent_faq").inc()
                                            rag_query_duration_seconds.labels(
                                                query_type="stream",
                                                cache_hit="true"
                                            ).observe(time.time() - start_time)
                                        
                                        # Send sources first
                                        yield {"type": "sources", "sources": sources}
                                        
                                        # Stream cached answer
                                        for i, char in enumerate(answer):
                                            yield {"type": "chunk", "content": char}
                                            if i % 10 == 0:
                                                await asyncio.sleep(0.001)
                                        
                                        metadata = {
                                            "input_tokens": 0,
                                            "output_tokens": 0,
                                            "cost_usd": 0.0,
                                            "duration_seconds": time.time() - start_time,
                                            "cache_hit": True,
                                            "cache_type": "intent_faq_match",
                                            "intent": "faq_match",
                                            "matched_faq": matched_faq,
                                        }
                                        yield {"type": "metadata", "metadata": metadata}
                                        yield {"type": "complete", "from_cache": True}
                                        return
                            except Exception as e:
                                logger.warning(f"FAQ cache lookup failed (stream): {e}")
                        # If cache miss, fall through to normal RAG
                        logger.debug(
                            f"FAQ match but cache miss, proceeding with RAG (stream): {matched_faq[:50]}..."
                        )
            
            # === 1. Exact cache check (fastest, zero-cost) ===
            # Check exact cache first - this is the fastest lookup
            cached_result = query_cache.get(query_text, effective_history)
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
                    "cache_type": "exact",
                }
                yield {"type": "metadata", "metadata": metadata}

                # Signal completion with cache flag
                yield {"type": "complete", "from_cache": True}
                return

            # Cache miss for exact cache
            if MONITORING_ENABLED:
                rag_cache_misses_total.labels(cache_type="query").inc()

            # Convert chat_history to Langchain's BaseMessage format (needed for retrieval)
            converted_chat_history: List[BaseMessage] = []
            for human_msg, ai_msg in effective_history:
                converted_chat_history.append(HumanMessage(content=human_msg))
                if ai_msg:
                    converted_chat_history.append(AIMessage(content=ai_msg))

            # === 2. Query Rewriting Complete: effective_query is now the standalone query ===
            # The semantic router has already rewritten the query if needed.
            # Use effective_query (the rewritten standalone query) for semantic caching.
            rewritten_query = effective_query
            
            # Optional: Apply local rewriter if enabled and not already rewritten by semantic router
            if USE_LOCAL_REWRITER and not is_dependent and effective_history:
                # Only use local rewriter if we have history but semantic router didn't rewrite
                router = _get_inference_router()
                if router:
                    rewrite_start = time.time()
                    try:
                        local_rewritten = await router.rewrite(query_text, effective_history)
                        if MONITORING_ENABLED:
                            rag_query_rewrite_duration_seconds.observe(time.time() - rewrite_start)
                        if local_rewritten == "NO_SEARCH_NEEDED":
                            yield {"type": "sources", "sources": []}
                            response = "I understand. Is there anything else you'd like to know about Litecoin?"
                            for char in response:
                                yield {"type": "chunk", "content": char}
                            metadata = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "duration_seconds": time.time() - start_time,
                                "cache_hit": False,
                                "cache_type": None,
                                "rewritten_query": "NO_SEARCH_NEEDED",
                            }
                            yield {"type": "metadata", "metadata": metadata}
                            yield {"type": "complete", "from_cache": False}
                            return
                        rewritten_query = local_rewritten
                        logger.debug(f"Local rewriter (stream): '{query_text}' -> '{rewritten_query}'")
                    except Exception as e:
                        if MONITORING_ENABLED:
                            rag_query_rewrite_duration_seconds.observe(time.time() - rewrite_start)
                        logger.warning(f"Local rewriter failed in stream, using effective_query: {e}")
                        rewritten_query = effective_query

            # === 3. Generate embedding ONCE for rewritten standalone query ===
            # This is the key optimization: cache based on the standalone query vector
            query_vector = None
            query_sparse = None
            
            if USE_REDIS_CACHE or USE_INFINITY_EMBEDDINGS:
                infinity = _get_infinity_embeddings()
                if infinity:
                    embed_start = time.time()
                    try:
                        # Generate embedding for the REWRITTEN standalone query
                        query_vector, query_sparse = await infinity.embed_query(rewritten_query)
                        if MONITORING_ENABLED:
                            rag_embedding_generation_duration_seconds.observe(time.time() - embed_start)
                        if query_sparse:
                            logger.info(f"✅ Query sparse embedding received (stream): {len(query_sparse)} terms (sample: {list(query_sparse.items())[:3]})")
                        else:
                            logger.debug(f"Query sparse embedding (stream): None (model may not support sparse)")
                    except Exception as e:
                        if MONITORING_ENABLED:
                            rag_embedding_generation_duration_seconds.observe(time.time() - embed_start)
                        logger.warning(f"Infinity embedding failed in stream: {e}", exc_info=True)
            
            # === 4. Semantic cache check (Redis Vector Cache) ===
            # Check Redis cache with rewritten standalone query vector
            if USE_REDIS_CACHE and query_vector:
                redis_cache = _get_redis_vector_cache()
                if redis_cache:
                    try:
                        redis_result = await redis_cache.get(query_vector)
                        if redis_result:
                            cached_answer, sources_data = redis_result
                            # Reconstruct Document objects
                            cached_sources = []
                            for src in sources_data:
                                if isinstance(src, dict):
                                    cached_sources.append(Document(
                                        page_content=src.get("page_content", ""),
                                        metadata=src.get("metadata", {})
                                    ))
                                elif isinstance(src, Document):
                                    cached_sources.append(src)
                            
                            logger.info(f"✅ Redis vector cache HIT for rewritten query (stream): '{rewritten_query[:50]}...' (original: '{query_text[:30]}...')")
                            if MONITORING_ENABLED:
                                rag_cache_hits_total.labels(cache_type="redis_vector").inc()
                                rag_query_duration_seconds.labels(
                                    query_type="stream",
                                    cache_hit="true"
                                ).observe(time.time() - start_time)
                            
                            yield {"type": "sources", "sources": cached_sources}
                            for i, char in enumerate(cached_answer):
                                yield {"type": "chunk", "content": char}
                                if i % 10 == 0:
                                    await asyncio.sleep(0.001)
                            metadata = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "duration_seconds": time.time() - start_time,
                                "cache_hit": True,
                                "cache_type": "redis_vector",
                                "rewritten_query": rewritten_query if rewritten_query != query_text else None,
                            }
                            yield {"type": "metadata", "metadata": metadata}
                            yield {"type": "complete", "from_cache": True}
                            return
                    except Exception as e:
                        logger.warning(f"Redis cache lookup failed in stream: {e}")

            # === 6. RAG FALLBACK (The expensive part) ===
                redis_cache = _get_redis_vector_cache()
                if redis_cache:
                    try:
                        redis_result = await redis_cache.get(query_vector)
                        if redis_result:
                            cached_answer, sources_data = redis_result
                            # Reconstruct Document objects
                            cached_sources = []
                            for src in sources_data:
                                if isinstance(src, dict):
                                    cached_sources.append(Document(
                                        page_content=src.get("page_content", ""),
                                        metadata=src.get("metadata", {})
                                    ))
                                elif isinstance(src, Document):
                                    cached_sources.append(src)
                            
                            logger.info(f"Redis vector cache HIT (after rewrite, stream) for: {rewritten_query[:50]}...")
                            if MONITORING_ENABLED:
                                rag_cache_hits_total.labels(cache_type="redis_vector").inc()
                                rag_query_duration_seconds.labels(
                                    query_type="stream",
                                    cache_hit="true"
                                ).observe(time.time() - start_time)
                            
                            yield {"type": "sources", "sources": cached_sources}
                            for i, char in enumerate(cached_answer):
                                yield {"type": "chunk", "content": char}
                                if i % 10 == 0:
                                    await asyncio.sleep(0.001)
                            metadata = {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost_usd": 0.0,
                                "duration_seconds": time.time() - start_time,
                                "cache_hit": True,
                                "cache_type": "redis_vector",
                                "rewritten_query": rewritten_query,
                            }
                            yield {"type": "metadata", "metadata": metadata}
                            yield {"type": "complete", "from_cache": True}
                            return
                    except Exception as e:
                        logger.warning(f"Redis cache lookup for rewritten query failed in stream: {e}")

            # === UNIFIED HYBRID + HISTORY-AWARE RETRIEVAL ===
            retrieval_start = time.time()
            # Use effective_query (from semantic router) or rewritten_query (from local rewriter)
            retrieval_query = rewritten_query
            # Initialize context_docs to ensure it's always defined
            context_docs = []
            retrieval_failed = False
            
            # When using Infinity embeddings with 1024-dim index, use HYBRID retrieval
            # Combines: 1) Infinity vector search (semantic) + 2) BM25 keyword search
            if USE_INFINITY_EMBEDDINGS and query_vector is not None:
                vector_docs = []
                bm25_docs = []
                try:
                    # Helper functions for parallel execution
                    def run_vector_search():
                        """Run vector search synchronously."""
                        return self.vector_store_manager.vector_store.similarity_search_with_score_by_vector(
                            query_vector, 
                            k=RETRIEVER_K * 2  # Retrieve more candidates for better filtering
                        )
                    
                    def run_bm25_search():
                        """Run BM25 search synchronously."""
                        if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                            # Temporarily increase k for BM25 to get better coverage
                            original_k = self.bm25_retriever.k
                            self.bm25_retriever.k = RETRIEVER_K * 2
                            try:
                                return self.bm25_retriever.invoke(retrieval_query)
                            finally:
                                self.bm25_retriever.k = original_k  # Restore original
                        return []
                    
                    # 1. & 2. Run vector and BM25 searches in parallel
                    search_start = time.time()
                    vector_task = asyncio.to_thread(run_vector_search)
                    bm25_task = asyncio.to_thread(run_bm25_search) if hasattr(self, 'bm25_retriever') and self.bm25_retriever else None
                    
                    if bm25_task:
                        vector_results, bm25_docs = await asyncio.gather(vector_task, bm25_task)
                        search_duration = time.time() - search_start
                        if MONITORING_ENABLED:
                            # Both searches ran in parallel, so duration is the same for both
                            rag_vector_search_duration_seconds.observe(search_duration)
                            rag_bm25_search_duration_seconds.observe(search_duration)
                    else:
                        vector_results = await vector_task
                        bm25_docs = []
                        search_duration = time.time() - search_start
                        if MONITORING_ENABLED:
                            rag_vector_search_duration_seconds.observe(search_duration)
                    
                    # Filter vector results by similarity threshold (cosine similarity >= 0.3 for BGE-M3)
                    MIN_SIMILARITY_THRESHOLD = float(os.getenv("MIN_VECTOR_SIMILARITY", "0.3"))
                    vector_docs = [doc for doc, score in vector_results if score >= MIN_SIMILARITY_THRESHOLD]
                    
                    if len(vector_docs) < RETRIEVER_K:
                        # If filtering removed too many, use top K anyway
                        vector_docs = [doc for doc, _ in vector_results[:RETRIEVER_K]]
                    
                    logger.info(f"Infinity vector search (stream): {len(vector_results)} candidates → {len(vector_docs)} above threshold {MIN_SIMILARITY_THRESHOLD}")
                    if vector_results:
                        logger.debug(f"   Top similarity score: {vector_results[0][1]:.3f}, Bottom: {vector_results[-1][1]:.3f}")
                    
                    if bm25_docs:
                        logger.debug(f"BM25 keyword search (stream) returned {len(bm25_docs)} documents")
                    elif hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                        logger.debug("BM25 keyword search (stream) returned 0 documents")
                except Exception as bm25_error:
                    logger.warning(f"Parallel search failed in stream: {bm25_error}")
                    # Fallback to sequential execution
                    try:
                        vector_results = self.vector_store_manager.vector_store.similarity_search_with_score_by_vector(
                            query_vector, 
                            k=RETRIEVER_K * 2
                        )
                        MIN_SIMILARITY_THRESHOLD = float(os.getenv("MIN_VECTOR_SIMILARITY", "0.3"))
                        vector_docs = [doc for doc, score in vector_results if score >= MIN_SIMILARITY_THRESHOLD]
                        if len(vector_docs) < RETRIEVER_K:
                            vector_docs = [doc for doc, _ in vector_results[:RETRIEVER_K]]
                        bm25_docs = []
                        if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
                            original_k = self.bm25_retriever.k
                            self.bm25_retriever.k = RETRIEVER_K * 2
                            bm25_docs = self.bm25_retriever.invoke(retrieval_query)
                            self.bm25_retriever.k = original_k
                    except Exception as fallback_error:
                        logger.error(f"Fallback search also failed in stream: {fallback_error}")
                        vector_docs = []
                        bm25_docs = []
                
                # 3. Merge and deduplicate results with better priority logic
                # This is outside the try block so exceptions here don't lose the retrieved documents
                seen_contents = set()
                candidate_docs = []
                candidate_scores = {}  # Track which source (BM25 vs vector) for priority
                
                # Prioritize BM25 results (better for exact keyword matches)
                for doc in bm25_docs:
                    content_key = doc.page_content[:200]  # Use first 200 chars as key
                    if content_key not in seen_contents:
                        seen_contents.add(content_key)
                        candidate_docs.append(doc)
                        candidate_scores[id(doc)] = 'bm25'
                
                # Add vector results, avoiding duplicates
                for doc in vector_docs:
                    content_key = doc.page_content[:200]
                    if content_key not in seen_contents:
                        seen_contents.add(content_key)
                        candidate_docs.append(doc)
                        candidate_scores[id(doc)] = 'vector'
                
                logger.debug(f"Hybrid merge (stream): {len(bm25_docs)} BM25 + {len(vector_docs)} vector → {len(candidate_docs)} unique candidates")
                
                # 4. Re-rank using sparse embeddings if available (BGE-M3)
                # This is outside the main try block so exceptions here don't trigger full fallback
                if query_sparse and infinity and len(candidate_docs) > 0:
                    try:
                        rerank_start = time.time()
                        # Limit candidates for sparse re-ranking to save time (only embed top N)
                        candidates_for_rerank = candidate_docs[:SPARSE_RERANK_LIMIT]
                        logger.info(f"🔄 Sparse re-ranking (stream): {len(candidates_for_rerank)}/{len(candidate_docs)} candidates (limited to top {SPARSE_RERANK_LIMIT}), query has {len(query_sparse)} sparse terms")
                        # Generate sparse embeddings for candidate documents
                        doc_texts = [doc.page_content[:8000] for doc in candidates_for_rerank]  # Truncate for TF-IDF
                        _, doc_sparse_list = await infinity.embed_documents(doc_texts)
                        
                        # Compute sparse similarity scores
                        doc_scores = []
                        sparse_count = sum(1 for s in doc_sparse_list if s is not None)
                        logger.info(f"   Generated {sparse_count}/{len(doc_sparse_list)} document sparse embeddings (stream)")
                        
                        for i, (doc, doc_sparse) in enumerate(zip(candidates_for_rerank, doc_sparse_list)):
                            if doc_sparse:
                                sparse_sim = infinity.sparse_similarity(query_sparse, doc_sparse)
                                doc_scores.append((sparse_sim, i, doc))
                            else:
                                doc_scores.append((0.0, i, doc))
                        
                        # Sort by sparse similarity (highest first)
                        doc_scores.sort(reverse=True, key=lambda x: x[0])
                        # Take top RETRIEVER_K from re-ranked results, then add remaining candidates if needed
                        reranked_docs = [doc for _, _, doc in doc_scores]
                        # If we have fewer reranked docs than RETRIEVER_K, add remaining candidates
                        if len(reranked_docs) < RETRIEVER_K and len(candidate_docs) > len(candidates_for_rerank):
                            remaining_docs = [doc for doc in candidate_docs[SPARSE_RERANK_LIMIT:] if doc not in reranked_docs]
                            reranked_docs.extend(remaining_docs[:RETRIEVER_K - len(reranked_docs)])
                        context_docs = reranked_docs[:RETRIEVER_K]
                        
                        if MONITORING_ENABLED:
                            rag_sparse_rerank_duration_seconds.observe(time.time() - rerank_start)
                        
                        logger.info(f"✅ Hybrid retrieval (stream: Infinity + BM25 + Sparse) returned {len(context_docs)} documents")
                        if doc_scores:
                            logger.info(f"   Top sparse similarity (stream): {doc_scores[0][0]:.3f}")
                    except Exception as sparse_error:
                        if MONITORING_ENABLED and 'rerank_start' in locals():
                            rag_sparse_rerank_duration_seconds.observe(time.time() - rerank_start)
                        logger.warning(f"⚠️ Sparse re-ranking failed in stream, using basic hybrid: {sparse_error}", exc_info=True)
                        # Fallback to basic hybrid - use the candidate_docs we successfully retrieved
                        context_docs = candidate_docs[:RETRIEVER_K]
                else:
                    context_docs = candidate_docs[:RETRIEVER_K]
                    if not query_sparse:
                        logger.debug(f"Hybrid retrieval (stream: Infinity + BM25) - no sparse embeddings available")
                    else:
                        logger.debug(f"Hybrid retrieval (stream) returned {len(context_docs)} unique documents")
                    
                # Only fall back to history-aware retriever if we got no results at all
                if not context_docs:
                    try:
                        logger.warning("No documents retrieved from hybrid search, falling back to history-aware retriever")
                        retrieval_failed = True
                        if USE_LOCAL_REWRITER and rewritten_query != query_text:
                            logger.debug(f"Using hybrid retriever directly with rewritten query (skip history-aware, stream): {rewritten_query[:50]}...")
                            context_docs = await self.hybrid_retriever.ainvoke(retrieval_query)
                        else:
                            context_docs = await self.history_aware_retriever.ainvoke({
                                "input": retrieval_query,
                                "chat_history": converted_chat_history
                            })
                    except Exception as fallback_error:
                        logger.error(f"Fallback retrieval also failed in stream: {fallback_error}", exc_info=True)
                        context_docs = []
            else:
                # Legacy path: use history-aware hybrid retriever
                # If query was already rewritten by local router, skip history-aware retriever (avoid redundant LLM call)
                try:
                    if USE_LOCAL_REWRITER and rewritten_query != query_text:
                        logger.debug(f"Using hybrid retriever directly with rewritten query (skip history-aware, stream): {rewritten_query[:50]}...")
                        context_docs = await self.hybrid_retriever.ainvoke(retrieval_query)
                    else:
                        context_docs = await self.history_aware_retriever.ainvoke({
                            "input": retrieval_query,
                            "chat_history": converted_chat_history
                        })
                except Exception as e:
                    logger.error(f"Legacy retrieval failed in stream: {e}", exc_info=True)
                    retrieval_failed = True
                    context_docs = []
            retrieval_duration = time.time() - retrieval_start
            
            # === PARENT DOCUMENT PATTERN: Resolve synthetic questions ===
            # If FAQ indexing is enabled, swap any synthetic question hits
            # with their full-text parent chunks before sending to LLM
            if USE_FAQ_INDEXING and context_docs:
                synthetic_count = sum(1 for d in context_docs if d.metadata.get("is_synthetic", False))
                if synthetic_count > 0:
                    try:
                        from backend.services.faq_generator import resolve_parents
                        parent_chunks_map = self._load_parent_chunks_map()
                        if parent_chunks_map:
                            original_count = len(context_docs)
                            context_docs = resolve_parents(context_docs, parent_chunks_map)
                            logger.info(f"🔄 FAQ resolution (stream): {original_count} docs ({synthetic_count} synthetic) → {len(context_docs)} resolved")
                        else:
                            logger.debug("Parent chunks map empty, skipping FAQ resolution")
                    except Exception as resolve_error:
                        logger.warning(f"FAQ resolution failed, using original docs: {resolve_error}")
            
            # Filter published sources
            published_sources = [
                doc for doc in context_docs
                if doc.metadata.get("status") == "published"
            ]
            
            # Format context for token estimation (needed for metrics)
            context_text = format_docs(context_docs)
            
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
                # Use generic error message if retrieval failed, otherwise use standard no-match message
                response_message = GENERIC_USER_ERROR_MESSAGE if retrieval_failed else NO_KB_MATCH_RESPONSE
                yield {"type": "chunk", "content": response_message}
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
                except HTTPException:
                    # Re-raise HTTPExceptions from spend limit check
                    raise
                except Exception as e:
                    # Log error but allow request (graceful degradation)
                    logger.warning(f"Error in spend limit check: {e}", exc_info=True)

            # 3. TRUE STREAMING GENERATION
            llm_start = time.time()
            full_answer_accumulator = ""
            answer_obj = None  # Store answer object for metadata extraction
            
            # When using Infinity embeddings, use document_chain directly with pre-retrieved docs
            # This avoids the rag_chain's internal retrieval which would fail with placeholder embeddings
            if USE_INFINITY_EMBEDDINGS and query_vector is not None:
                # Use document_chain.astream() with already-retrieved context
                async for chunk in self.document_chain.astream({
                    "input": query_text,
                    "context": context_docs,
                    "chat_history": converted_chat_history
                }):
                    # document_chain yields AIMessageChunk directly
                    content = ""
                    if hasattr(chunk, "content"):
                        answer_obj = chunk
                        content = chunk.content
                    elif isinstance(chunk, str):
                        content = chunk
                    
                    if content:
                        full_answer_accumulator += content
                        yield {"type": "chunk", "content": content}
            else:
                # Legacy path: use rag_chain.astream() for full retrieval + generation
                async for chunk in self.rag_chain.astream({
                    "input": query_text,
                    "chat_history": converted_chat_history
                }):
                    # Extract content from chunk
                    # rag_chain.astream() yields dicts with "answer" key containing AIMessageChunk
                    content = ""
                    if isinstance(chunk, dict) and "answer" in chunk:
                        answer_obj = chunk["answer"]
                        if hasattr(answer_obj, "content"):
                            content = answer_obj.content
                        elif isinstance(answer_obj, str):
                            content = answer_obj
                    elif isinstance(chunk, str):
                        content = chunk
                    elif hasattr(chunk, "content"):
                        # Direct AIMessageChunk
                        answer_obj = chunk
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
                # Extract actual token usage from answer object if available, otherwise estimate
                if answer_obj:
                    input_tokens, output_tokens = self._extract_token_usage_from_llm_response(answer_obj)
                    if input_tokens == 0 and output_tokens == 0:
                        # Fallback to estimation if metadata not available
                        prompt_text = self._build_prompt_text_with_history(
                            query_text, context_text, converted_chat_history
                        )
                        input_tokens, output_tokens = self._estimate_token_usage(
                            prompt_text,
                            full_answer_accumulator
                        )
                        logger.debug("Using estimated token counts (metadata not available)")
                    else:
                        logger.debug(f"Using actual token counts: input={input_tokens}, output={output_tokens}")
                else:
                    # Fallback to estimation if no answer object
                    prompt_text = self._build_prompt_text_with_history(
                        query_text, context_text, converted_chat_history
                    )
                    input_tokens, output_tokens = self._estimate_token_usage(
                        prompt_text,
                        full_answer_accumulator
                    )
                    logger.debug("Using estimated token counts (no answer object)")
                
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
            
            # Cache in BOTH systems (using the effective history we actually used for retrieval)
            query_cache.set(query_text, effective_history, full_answer_accumulator, published_sources)  # exact cache
            
            # === LOCAL RAG: Store in Redis Stack vector cache (streaming) ===
            # Cache using the rewritten standalone query vector (allows different conversation paths to reuse)
            # We cache even with chat history, because we cache based on the rewritten standalone query
            if USE_REDIS_CACHE and query_vector:
                redis_cache = _get_redis_vector_cache()
                if redis_cache:
                    try:
                        sources_data = [
                            {"page_content": doc.page_content, "metadata": doc.metadata}
                            for doc in published_sources
                        ]
                        await redis_cache.set(
                            query_vector,
                            rewritten_query,  # Always use rewritten standalone query for consistency
                            full_answer_accumulator,
                            sources_data
                        )
                        logger.debug(f"Cached result in Redis using rewritten query (stream): '{rewritten_query[:50]}...'")
                    except Exception as e:
                        logger.warning(f"Redis cache storage failed in stream: {e}")
            
            # Legacy semantic cache (only if Redis not enabled)
            if self.semantic_cache and not USE_REDIS_CACHE:
                # Use rewritten query for consistency (no history since it's already standalone)
                self.semantic_cache.set(rewritten_query, [], full_answer_accumulator, published_sources)

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

        except HTTPException as he:
            # Re-raise HTTPExceptions (e.g., 429 for spend limits)
            raise he
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
