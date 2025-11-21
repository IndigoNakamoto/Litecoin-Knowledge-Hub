# RAG Pipeline Performance & Security Improvements

**Document Status**: Action Required  
**Priority**: High  
**Created**: November 21, 2025  
**Target File**: `backend/rag_pipeline.py`

---

## Executive Summary

Gemini's analysis of our RAG pipeline identified **3 critical performance issues** and **1 security logic flaw** that significantly impact user experience, latency, and cost efficiency. This document outlines each issue and provides actionable implementation guidance.

**⚠️ IMPORTANT UPDATE**: Code review identified additional issues with chat history handling that must be addressed alongside the performance fixes to prevent conversational accuracy regressions.

### Key Issues Identified

1. **🔴 CRITICAL: Fake Streaming Implementation** - High TTFT (Time To First Token), poor UX
2. **🟠 HIGH: Double Retrieval Inefficiency** - Doubles vector DB latency and costs
3. **🟡 MEDIUM: Retrieval Parameter Optimization** - Potential noise-to-signal ratio issues
4. **🟢 LOW: Prompt Injection Security Gap** - Detects but doesn't block malicious input
5. **🟠 HIGH: Chat History Handling Gaps** - Inconsistent history usage across methods, missing prompt template support

---

## Issue #1: Fake Streaming (CRITICAL)

### Current Problem

**Location**: `astream_query()` method (lines 977-1089)

Our streaming implementation is not actually streaming tokens from the LLM. Instead, it:
1. Waits for the **entire** LLM response to complete (~2-5 seconds)
2. Then loops through the completed string character-by-character

```python
# CURRENT PROBLEMATIC CODE (lines 977-984, 1071-1075)
result = await self.async_rag_chain.ainvoke({
    "input": query_text,
    "chat_history": converted_chat_history
})

answer = result.get("answer", "Error: Could not generate answer.")

# Then later... simulating streaming on already-complete answer
for i, char in enumerate(answer):
    yield {"type": "chunk", "content": char}
```

### Impact

- **User Experience**: Users see a loading spinner for 2-5 seconds, then text appears instantly
- **Perceived Latency**: Defeats the purpose of streaming (no progressive reveal)
- **Time To First Token (TTFT)**: 2000-5000ms instead of 100-300ms

### Solution: True Streaming with History Support

**⚠️ CRITICAL**: The original proposal ignored chat history, which would break conversational queries. The solution below properly handles history using history-aware retrieval and includes history in the prompt template.

**Step 1: Update RAG Prompt Template** (Required before implementing streaming)

The current `RAG_PROMPT_TEMPLATE` doesn't include `{chat_history}`. Update it to support conversational context:

```python
# Update RAG_PROMPT_TEMPLATE to include chat_history
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

{context}

{chat_history}

User: {input}
"""

# Update rag_prompt to use MessagesPlaceholder for chat_history
from langchain_core.prompts import MessagesPlaceholder

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", RAG_PROMPT_TEMPLATE.split("{context}")[0].strip()),
    ("placeholder", "{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])
```

**Step 2: Implement True Streaming with History**

Separate retrieval from generation and use `.astream()` directly on the LLM:

```python
async def astream_query(self, query_text: str, chat_history: List[Tuple[str, str]]):
    """
    True streaming version that yields chunks as they arrive from the LLM.
    Properly handles chat history for conversational queries.
    """
    start_time = time.time()
    
    # [Keep existing sanitization and cache check logic]
    # ... (sanitize, truncate history, check cache) ...
    
    try:
        # Convert chat_history to Langchain's BaseMessage format
        converted_chat_history: List[BaseMessage] = []
        for human_msg, ai_msg in truncated_history:
            converted_chat_history.append(HumanMessage(content=human_msg))
            converted_chat_history.append(AIMessage(content=ai_msg))
        
        # 1. RETRIEVAL PHASE (use history-aware retriever for better context)
        retrieval_start = time.time()
        
        # Use history-aware retriever to rephrase query with context
        # This resolves pronouns and ambiguous references
        rephrased_query_result = await self.async_history_aware_retriever.ainvoke({
            "input": query_text,
            "chat_history": converted_chat_history
        })
        
        # Extract rephrased query (history_aware_retriever returns documents)
        # We need to get the actual rephrased query text for retrieval
        # Alternative: Use history-aware retriever directly to get docs
        context_docs = rephrased_query_result if isinstance(rephrased_query_result, list) else []
        
        # If history_aware_retriever doesn't return docs directly, use it properly:
        # The history_aware_retriever is a chain that takes input+history and returns docs
        # So we can use it directly:
        context_docs = await self.async_history_aware_retriever.ainvoke({
            "input": query_text,
            "chat_history": converted_chat_history
        })
        
        retrieval_duration = time.time() - retrieval_start
        
        # Filter published sources
        published_sources = [
            doc for doc in context_docs
            if doc.metadata.get("status") == "published"
        ]
        
        if not published_sources:
            yield {"type": "sources", "sources": []}
            yield {"type": "chunk", "content": NO_KB_MATCH_RESPONSE}
            yield {"type": "complete", "no_kb_results": True}
            return
        
        # Send sources immediately (low latency UX)
        yield {"type": "sources", "sources": published_sources}
        
        # Format context
        context_text = format_docs(published_sources)
        
        # Pre-flight spend limit check
        if MONITORING_ENABLED:
            # Build prompt with history for accurate token estimation
            prompt_text = self._build_prompt_text_with_history(
                query_text, context_text, converted_chat_history
            )
            input_tokens_est, _ = self._estimate_token_usage(prompt_text, "")
            max_output_tokens = 2048
            estimated_cost = estimate_gemini_cost(
                input_tokens_est,
                max_output_tokens,
                LLM_MODEL_NAME
            )
            allowed, error_msg, _ = await check_spend_limit(estimated_cost, LLM_MODEL_NAME)
            if not allowed:
                # [Handle rejection - yield error and return]
                yield {"type": "error", "message": "Usage limit exceeded..."}
                yield {"type": "complete", "error": True}
                return
        
        # 2. TRUE STREAMING GENERATION (with history in prompt)
        llm_start = time.time()
        full_answer_accumulator = ""
        
        # Use rag_prompt | self.llm directly for streaming WITH chat_history
        async for chunk in (rag_prompt | self.llm).astream({
            "context": context_text,
            "input": query_text,
            "chat_history": converted_chat_history  # Include history for conversational context
        }):
            # Extract content from chunk
            if isinstance(chunk, str):
                content = chunk
            elif hasattr(chunk, "content"):
                content = chunk.content
            else:
                continue
            
            full_answer_accumulator += content
            yield {"type": "chunk", "content": content}
        
        llm_duration = time.time() - llm_start
        
        # 3. POST-PROCESSING
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
                LLM_MODEL_NAME
            )
            track_llm_metrics(
                model=LLM_MODEL_NAME,
                operation="generate",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=estimated_cost,
                duration_seconds=llm_duration,
                status="success"
            )
            await record_spend(estimated_cost, input_tokens, output_tokens, LLM_MODEL_NAME)
        
        # Update cache
        query_cache.set(query_text, truncated_history, full_answer_accumulator, published_sources)
        
        # Yield metadata and completion
        metadata = {
            "input_tokens": input_tokens if MONITORING_ENABLED else 0,
            "output_tokens": output_tokens if MONITORING_ENABLED else 0,
            "cost_usd": estimated_cost if MONITORING_ENABLED else 0.0,
            "duration_seconds": time.time() - start_time,
            "cache_hit": False,
            "cache_type": None,
        }
        yield {"type": "metadata", "metadata": metadata}
        yield {"type": "complete", "from_cache": False}
        
    except Exception as e:
        logger.error(f"Stream Error: {e}", exc_info=True)
        yield {"type": "error", "error": "An error occurred while processing your query."}

# Add helper method for building prompt with history
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
```

### Key Changes

1. **Update Prompt Template**: Add `{chat_history}` placeholder and use `MessagesPlaceholder` in `rag_prompt`
2. **History-Aware Retrieval**: Use `async_history_aware_retriever` to rephrase queries with context
3. **Separate Retrieval**: Do retrieval once before streaming
4. **Direct LLM Streaming**: Use `(rag_prompt | self.llm).astream()` with history included
5. **Accumulate Answer**: Build full answer string while streaming for metrics/cache
6. **Immediate Sources**: Send sources to frontend before LLM generation starts

### Implementation Priority

**Priority**: 🔴 **CRITICAL** - Implement immediately  
**Estimated Effort**: 2-3 hours  
**Testing Required**: Frontend streaming UI, cache behavior, error handling

---

## Issue #2: Double Retrieval Inefficiency (HIGH)

### Current Problem

**Location**: `query()` method (lines 461-516)

The sync `query()` method performs vector search **twice**:

```python
# FIRST RETRIEVAL (line 466)
context_docs = retriever.get_relevant_documents(query_text)
context_text = format_docs(context_docs)

# Pre-flight cost check uses context_docs...

# SECOND RETRIEVAL (line 513)
result = self.rag_chain.invoke({
    "input": query_text,
    "chat_history": converted_chat_history
})
# ↑ This invokes history_aware_retriever AGAIN internally
```

### Impact

- **Latency**: Doubles vector database query time (50-200ms × 2)
- **Cost**: Doubles FAISS/embedding compute costs
- **Inefficiency**: Wasted resources on identical queries

### Solution: Single Retrieval Pattern with History Support

**⚠️ CRITICAL**: The original proposal used a plain retriever (no history-aware rephrasing) and passed history to `document_chain`, but the current `rag_prompt` template doesn't support `{chat_history}`. The solution below fixes both issues.

**Prerequisites**: Update `RAG_PROMPT_TEMPLATE` as described in Issue #1 before implementing this fix.

Refactor to retrieve once using history-aware retriever, then pass context directly to LLM:

```python
def query(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document]]:
    """
    Processes a query through the conversational RAG pipeline (single retrieval).
    Uses history-aware retrieval for better conversational context.
    """
    start_time = time.time()
    
    # [Keep existing sanitization, truncation, cache check]
    # ... (sanitize, truncate history, check cache) ...
    
    try:
        converted_chat_history: List[BaseMessage] = []
        for human_msg, ai_msg in truncated_history:
            converted_chat_history.append(HumanMessage(content=human_msg))
            converted_chat_history.append(AIMessage(content=ai_msg))
        
        # SINGLE RETRIEVAL (using history-aware retriever for query rephrasing)
        retrieval_start = time.time()
        
        # Use history-aware retriever to get context (rephrases query with history)
        context_docs = self.history_aware_retriever.invoke({
            "input": query_text,
            "chat_history": converted_chat_history
        })
        
        context_text = format_docs(context_docs)
        retrieval_duration = time.time() - retrieval_start
        
        # Filter published sources
        published_sources = [
            doc for doc in context_docs
            if doc.metadata.get("status") == "published"
        ]
        
        if not published_sources:
            # [Track metrics and return]
            if MONITORING_ENABLED:
                rag_retrieval_duration_seconds.observe(retrieval_duration)
                rag_documents_retrieved_total.observe(0)
                rag_query_duration_seconds.labels(
                    query_type="sync",
                    cache_hit="false"
                ).observe(time.time() - start_time)
            return NO_KB_MATCH_RESPONSE, []
        
        # Pre-flight spend limit check
        if MONITORING_ENABLED:
            prompt_text = self._build_prompt_text_with_history(
                query_text, context_text, converted_chat_history
            )
            input_tokens_est, _ = self._estimate_token_usage(prompt_text, "")
            max_output_tokens = 2048
            estimated_cost = estimate_gemini_cost(
                input_tokens_est,
                max_output_tokens,
                LLM_MODEL_NAME
            )
            try:
                loop = asyncio.get_running_loop()
                logger.debug("Skipping spend limit check in sync method (event loop running)")
            except RuntimeError:
                allowed, error_msg, _ = asyncio.run(check_spend_limit(estimated_cost, LLM_MODEL_NAME))
                if not allowed:
                    # [Handle rejection - raise HTTPException]
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "spend_limit_exceeded",
                            "message": "We've reached our daily usage limit. Please try again later.",
                            "type": "daily" if "daily" in error_msg.lower() else "hourly"
                        }
                    )
        
        # Generate answer using document_chain directly (bypassing retriever in chain)
        # Note: document_chain now supports chat_history after prompt template update
        llm_start = time.time()
        answer_result = self.document_chain.invoke({
            "context": context_text,
            "input": query_text,
            "chat_history": converted_chat_history  # Now supported in updated prompt
        })
        llm_duration = time.time() - llm_start
        
        answer = answer_result if isinstance(answer_result, str) else answer_result.get("answer", "Error")
        
        # [Track metrics, cache result, return - same as current implementation]
        # ... (existing metric tracking and caching code) ...
        
        return answer, published_sources
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return "I encountered an error while processing your query.", []
```

### Key Changes

1. **Single History-Aware Retrieval**: Use `history_aware_retriever.invoke()` once (rephrases query with history, then retrieves)
2. **Bypass Retriever in Chain**: Use `document_chain.invoke()` directly with pre-retrieved context
3. **Preserve History**: Pass `chat_history` to `document_chain` (now supported after prompt template update)
4. **Consistent with Streaming**: Same pattern as `astream_query` for maintainability

### Additional Fix Required: `aquery()` Method Bug

**Current Issue**: The `aquery()` method (lines 614-850) converts chat history but doesn't use it:
- Line 688: Uses plain `retriever` (not history-aware)
- Line 757-760: Doesn't pass `chat_history` to the prompt

**Fix**: Apply the same single retrieval pattern with history support:

```python
async def aquery(self, query_text: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Document], Dict[str, Any]]:
    # ... (existing sanitization, cache check) ...
    
    # Use history-aware retriever (same as query method)
    context_docs = await self.async_history_aware_retriever.ainvoke({
        "input": query_text,
        "chat_history": converted_chat_history
    })
    
    # ... (filter sources, spend check) ...
    
    # Generate with history in prompt
    llm_response = await (rag_prompt | self.llm).ainvoke({
        "input": query_text,
        "context": context_text,
        "chat_history": converted_chat_history  # Include history
    })
    
    # ... (rest of method) ...
```

### Implementation Priority

**Priority**: 🟠 **HIGH** - Implement after streaming fix  
**Estimated Effort**: 2-3 hours (includes fixing `aquery()` bug)  
**Testing Required**: Response accuracy, latency benchmarks, cache behavior, conversational flow tests

---

## Issue #3: Retrieval Parameter Optimization (MEDIUM)

### Current Configuration

**Inconsistency Found**: Different `k` values across methods:
- `_setup_rag_chain()`: `k=7` (line 190)
- `_setup_async_rag_chain()`: `k=15` (line 218)
- `query()` method: `k=15` (line 464)
- `aquery()` method: `k=15` (line 686)
- `astream_query()` method: `k=15` (line 937)

### Analysis

**Context Window**: Gemini Flash supports 1M tokens (huge capacity)  
**Current Risk**: 
- Inconsistent `k` values may cause different behavior between sync/async
- Retrieving 15 documents increases noise-to-signal ratio if chunks are large
- Need to standardize on a single configurable value

### Recommendation

1. **Standardize `k` Value**: Create a single configurable constant:
   ```python
   # Add to constants section
   RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "10"))  # Default: 10 documents
   ```

2. **Optimal Range**: Based on typical chunk sizes (100-500 tokens):
   - **If chunks are large** (500+ tokens): Use `k=7` for better accuracy
   - **If chunks are small** (100-200 tokens): Use `k=10-15` for sufficient context
   - **Recommended default**: `k=10` balances accuracy vs. cost

3. **Update All Retrievers**: Use `RETRIEVAL_K` everywhere:
   ```python
   retriever = self.vector_store_manager.get_retriever(
       search_type="similarity",
       search_kwargs={"k": RETRIEVAL_K}
   )
   ```

### Testing Approach

```python
# A/B test different k values
k_values = [5, 7, 10, 15]
test_queries = ["What is MWEB?", "How does Litecoin mining work?", ...]

for k in k_values:
    # Test quality and latency
    # Measure: relevance score, response accuracy, retrieval time
```

### Implementation Priority

**Priority**: 🟡 **MEDIUM** - Optimize after critical fixes  
**Estimated Effort**: 1 hour testing  
**Testing Required**: Answer quality evaluation

---

## Issue #4: Prompt Injection Security Enhancement (LOW)

### Current Problem

**Location**: Lines 420-423, 632-635, 867-870

```python
is_injection, pattern = detect_prompt_injection(query_text)
if is_injection:
    logger.warning(f"Prompt injection detected (pattern: {pattern}). Sanitizing...")
query_text = sanitize_query_input(query_text)  # Continues processing!
```

### Security Gap

The code **detects** prompt injection but still processes the request after sanitization. While `sanitize_query_input()` attempts to neutralize the attack, a defense-in-depth approach should **abort** the request.

### Recommendation

**Option 1: Hard Reject** (Most Secure)

```python
is_injection, pattern = detect_prompt_injection(query_text)
if is_injection:
    logger.warning(f"Prompt injection blocked (pattern: {pattern})")
    raise HTTPException(
        status_code=400,
        detail={
            "error": "invalid_input",
            "message": "Your query contains disallowed content. Please rephrase."
        }
    )
```

**Option 2: Sanitize + Rate Limit** (Balanced)

```python
is_injection, pattern = detect_prompt_injection(query_text)
if is_injection:
    logger.warning(f"Injection attempt from user. Pattern: {pattern}")
    # Increment user's injection attempt counter in Redis
    # Block user if attempts > 3 in 1 hour
    query_text = sanitize_query_input(query_text)
```

**Option 3: Keep Current** (If Sanitization is Robust)

Current approach is acceptable if:
- `sanitize_prompt_injection()` has been thoroughly tested
- You trust the neutralization logic
- You want to allow legitimate queries that accidentally match patterns

### Implementation Priority

**Priority**: 🟢 **LOW** - Review after performance fixes  
**Estimated Effort**: 30 minutes  
**Testing Required**: Security audit, false positive rate

---

## Issue #5: Chat History Handling Gaps (HIGH)

### Current Problem

**Location**: Multiple methods and prompt template

Code review identified critical inconsistencies in chat history handling:

1. **Prompt Template Missing History**: `RAG_PROMPT_TEMPLATE` (line 84) doesn't include `{chat_history}` placeholder
2. **`aquery()` Bug**: Converts history but doesn't use it (lines 688, 757-760)
3. **Inconsistent History Usage**: 
   - `query()` uses history-aware retriever but history not in final prompt
   - `astream_query()` uses history-aware retriever but history not in final prompt
   - `aquery()` doesn't use history at all

### Impact

- **Conversational Accuracy**: Follow-up queries fail (e.g., "What is Litecoin?" → "Who created it?" won't resolve "it")
- **Inconsistent Behavior**: Different methods handle history differently
- **User Experience**: Users expect conversational context to work across all endpoints

### Solution

**Step 1: Update Prompt Template** (Required for all fixes)

```python
# Update RAG_PROMPT_TEMPLATE to include chat_history section
RAG_PROMPT_TEMPLATE = """
[... existing template content ...]

---

{context}

{chat_history}

User: {input}
"""

# Update rag_prompt to use MessagesPlaceholder
from langchain_core.prompts import MessagesPlaceholder

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", RAG_PROMPT_TEMPLATE.split("{context}")[0].strip()),
    ("placeholder", "{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])
```

**Step 2: Fix All Three Methods**

- **`query()`**: Already uses history-aware retriever; add history to `document_chain.invoke()` call
- **`aquery()`**: Use history-aware retriever AND pass history to prompt (fixes bug)
- **`astream_query()`**: Use history-aware retriever AND pass history to streaming prompt

**Step 3: Add Helper Method**

```python
def _build_prompt_text_with_history(
    self, query_text: str, context_text: str, chat_history: List[BaseMessage]
) -> str:
    """Reconstruct the prompt text with chat history for token accounting."""
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
```

### Implementation Priority

**Priority**: 🟠 **HIGH** - Must be done in Phase 0/1 before other fixes  
**Estimated Effort**: 1-2 hours (prompt update + method fixes)  
**Testing Required**: Conversational flow tests, follow-up query accuracy

---

## Review Feedback Summary

A comprehensive code review identified additional issues beyond the original analysis:

### Key Findings

1. **Chat History Gaps** (HIGH): Prompt template doesn't support history, `aquery()` bug, inconsistent usage
2. **Inconsistent `k` Values**: Different retrieval counts across methods (k=7 vs k=15)
3. **Missing Edge Cases**: No handling for very long answers in streaming, token extraction could be improved

### Review Recommendations

1. **Update Prompt Template First**: All other fixes depend on this
2. **Standardize History Handling**: Ensure all three methods use history consistently
3. **Fix `aquery()` Bug**: Currently ignores history despite converting it
4. **Add Conversational Tests**: Critical for preventing regressions
5. **Standardize `k` Parameter**: Use environment variable for consistency

### Document Updates

This document has been updated to incorporate all review findings:
- ✅ Added Issue #5 for chat history gaps
- ✅ Updated all code snippets to include history handling
- ✅ Added Phase 0 for prompt template update
- ✅ Enhanced testing checklist with conversational tests
- ✅ Updated roadmap to include `aquery()` bug fix
- ✅ Added notes section with detailed history handling requirements

---

## Implementation Roadmap

### Phase 0: Prerequisites (Day 0)

1. **Update RAG Prompt Template** (30 minutes)
   - Add `{chat_history}` placeholder to `RAG_PROMPT_TEMPLATE`
   - Update `rag_prompt` to use `MessagesPlaceholder` for chat history
   - Add `_build_prompt_text_with_history()` helper method
   - Test prompt formatting with sample history

2. **Create Backup Branch** (15 minutes)
   - Create feature branch: `feature/rag-pipeline-improvements`
   - Document current behavior for comparison

### Phase 1: Critical Performance (Week 1)

1. ✅ **Day 1-2**: Implement true streaming in `astream_query()`
   - Update prompt template (if not done in Phase 0)
   - Separate retrieval from generation
   - Use history-aware retriever for query rephrasing
   - Use `.astream()` directly on LLM with history
   - Test with frontend streaming UI
   - Verify cache behavior
   - **Test conversational flows** (e.g., "What is Litecoin?" → "Who created it?")

2. ✅ **Day 3**: Fix double retrieval in `query()` and `aquery()`
   - Refactor `query()` to single history-aware retrieval
   - Fix `aquery()` bug (add history support)
   - Use `document_chain` directly with pre-retrieved context
   - Benchmark latency improvements
   - **Test conversational accuracy** (ensure no regressions)

3. ✅ **Day 4**: Testing and validation
   - End-to-end testing (sync, async, streaming)
   - Conversational flow tests
   - Performance benchmarks (before/after)
   - Monitor Grafana metrics
   - Test edge cases (empty history, long history, etc.)

4. ✅ **Day 5**: Documentation and deployment
   - Update API documentation
   - Deploy to staging
   - Monitor production metrics
   - Verify TTFT improvements in production

### Phase 2: Optimization (Week 2)

5. ✅ **Day 6-7**: Standardize and optimize `k` parameter
   - Add `RETRIEVAL_K` environment variable
   - Update all retriever calls to use consistent `k`
   - A/B test k=5, 7, 10, 15
   - Measure answer quality and relevance scores
   - Optimize based on results
   - Update documentation with chosen value

6. ✅ **Day 8**: Review prompt injection security
   - Evaluate current approach
   - Implement chosen option (recommend Option 2: Sanitize + Rate Limit)
   - Test false positive rate with sample queries
   - Add user-specific injection attempt tracking

7. ✅ **Day 9-10**: Performance benchmarking and documentation
   - Final performance report (TTFT, latency, cost improvements)
   - Update monitoring dashboards
   - Document lessons learned
   - Update architecture diagrams in `high_level_design.md`

---

## Testing Checklist

### Streaming Tests
- [ ] TTFT < 500ms for non-cached queries
- [ ] Tokens appear progressively in frontend
- [ ] Cache hit streaming works correctly
- [ ] Error handling yields proper error messages
- [ ] Metadata contains accurate token counts
- [ ] Sources appear before streaming starts
- [ ] Full answer accumulates correctly for cache
- [ ] **Chat history properly handled in streaming** (test follow-up queries)
- [ ] **History-aware retrieval works** (pronouns resolve correctly)

### Retrieval Tests
- [ ] Single retrieval confirmed via logs
- [ ] Response accuracy unchanged (or improved with history)
- [ ] Latency reduced by ~50-200ms
- [ ] Spend limit checks still work
- [ ] Cache behavior preserved
- [ ] **History-aware retrieval works** (query rephrasing with context)
- [ ] **Conversational accuracy maintained** (test: "What is X?" → "Who created it?")
- [ ] **`aquery()` method uses history** (fixes existing bug)
- [ ] **Consistent behavior across `query()`, `aquery()`, `astream_query()`**

### Integration Tests
- [ ] Frontend receives streaming chunks correctly
- [ ] Error states handled gracefully
- [ ] Monitoring metrics accurate
- [ ] Cost tracking remains correct
- [ ] No regressions in existing functionality

---

## Monitoring Metrics

Track these metrics in Grafana after implementation:

### Time To First Token (TTFT)
```promql
# Should drop from 2000-5000ms to <500ms
histogram_quantile(0.95, 
  rate(rag_query_duration_seconds_bucket{query_type="stream",cache_hit="false"}[5m])
)
```

### Retrieval Efficiency
```promql
# Should show single retrieval per query
rate(rag_retrieval_duration_seconds[5m])

# Document count should remain consistent
rate(rag_documents_retrieved_total[5m])
```

### Cost Impact
```promql
# Should decrease slightly due to single retrieval
rate(llm_cost_usd_total[1h])

# Token usage should remain similar
rate(llm_tokens_total[1h])
```

### User Experience
```promql
# Query duration should improve
histogram_quantile(0.95,
  rate(rag_query_duration_seconds_bucket[5m])
)
```

---

## Code Review Checklist

Before merging changes, verify:

- [ ] **Prompt template updated** with `{chat_history}` placeholder
- [ ] **`rag_prompt` uses `MessagesPlaceholder`** for chat history
- [ ] True streaming implemented (no `ainvoke()` then character loop)
- [ ] **History-aware retrieval used** in all methods
- [ ] Single retrieval in `query()` method
- [ ] **`aquery()` bug fixed** (uses history-aware retrieval and passes history to prompt)
- [ ] Chat history properly handled in all three methods
- [ ] **Conversational tests pass** (follow-up queries work correctly)
- [ ] Cache behavior preserved
- [ ] Error handling comprehensive
- [ ] Monitoring metrics updated correctly
- [ ] Token counting accurate (includes history in estimation)
- [ ] Spend limit checks still work
- [ ] Frontend compatibility maintained
- [ ] Unit tests updated
- [ ] Integration tests pass
- [ ] **Consistent `k` value** across all methods (or configurable via env var)

---

## Expected Performance Improvements

### Before Improvements
- **TTFT**: 2000-5000ms (fake streaming)
- **Retrieval Latency**: 100-400ms (double retrieval)
- **Total Query Time**: 3000-6000ms
- **User Experience**: Loading spinner → instant text

### After Improvements
- **TTFT**: 100-300ms (true streaming)
- **Retrieval Latency**: 50-200ms (single retrieval)
- **Total Query Time**: 2000-4000ms (but progressive)
- **User Experience**: Progressive text reveal

### Key Benefits
- ✅ **80-90% reduction in perceived latency** (TTFT)
- ✅ **50% reduction in retrieval time** (single retrieval)
- ✅ **Better user experience** (progressive reveal)
- ✅ **Lower costs** (single retrieval, same accuracy)

---

## References

- **Original Analysis**: Gemini 2.5 Flash Code Review (Nov 2025)
- **Related Files**:
  - `backend/rag_pipeline.py` (primary target)
  - `backend/monitoring/llm_observability.py` (metrics)
  - `backend/utils/input_sanitizer.py` (security)
  - `backend/cache_utils.py` (caching)
- **Related Documentation**:
  - `docs/FEATURE_SPEND_LIMIT_MONITORING.md`
  - `docs/monitoring/monitoring-guide.md`
  - `docs/architecture/high_level_design.md`

---

## Notes

### Model Name
The current model name `gemini-2.5-flash-lite-preview-09-2025` has been verified and is working correctly in production. No changes needed.

### Chat History Handling (CRITICAL)

**Current State**:
- `RAG_PROMPT_TEMPLATE` does NOT include `{chat_history}` placeholder
- `rag_prompt` does NOT use `MessagesPlaceholder` for history
- `query()` uses history-aware retriever but history not in final prompt
- `aquery()` converts history but doesn't use it (BUG)
- `astream_query()` uses history-aware retriever but history not in final prompt

**Required Changes**:
1. Update `RAG_PROMPT_TEMPLATE` to include `{chat_history}` section
2. Update `rag_prompt` to use `MessagesPlaceholder(variable_name="chat_history")`
3. Ensure all three methods (`query`, `aquery`, `astream_query`) pass `chat_history` to prompts
4. Use history-aware retrievers consistently for query rephrasing

**Why This Matters**:
- Without history in prompts, conversational queries fail (e.g., "What is Litecoin?" → "Who created it?" won't resolve "it")
- History-aware retrieval rephrases queries but doesn't provide full conversational context to generation
- Both retrieval rephrasing AND prompt history are needed for optimal conversational accuracy

### Backward Compatibility
Ensure that the streaming changes don't break existing API consumers. The response format should remain the same, only the delivery mechanism changes. Adding history to prompts should not break existing queries (empty history works fine).

### Additional Issues Identified

1. **Inconsistent `k` values**: `_setup_rag_chain()` uses `k=7`, others use `k=15`. Standardize via env var.
2. **`aquery()` bug**: Doesn't use history despite converting it. Fix in Phase 1.
3. **Token estimation**: Could prioritize actual metadata over estimation when available (low priority).

---

## Conclusion

These improvements will significantly enhance:
- **User Experience**: True streaming reduces perceived latency by 80-90%
- **Performance**: Eliminating double retrieval cuts costs and latency by 50%
- **Efficiency**: Optimized retrieval parameters improve answer quality
- **Security**: Enhanced prompt injection handling provides defense-in-depth
- **Conversational Accuracy**: Proper history handling ensures follow-up queries work correctly

**Critical Success Factors**:
1. **Prompt Template Update**: Must be done first (Phase 0) before any other changes
2. **History Consistency**: All three methods must handle history identically
3. **Testing**: Extensive conversational flow testing required to prevent regressions

**Next Action**: 
1. Begin Phase 0: Update prompt template and create backup branch
2. Then proceed with Phase 1: Implement streaming fix with history support
3. Test thoroughly with conversational queries before deploying

---

**Last Updated**: November 21, 2025  
**Status**: Ready for Implementation  
**Owner**: Backend Team

