# Structured Output & Citation Validation Implementation Specification

**Feature:** Enforced Citations with Source Validation  
**Phase:** 2  
**Priority:** High  
**Estimated Effort:** 12-16 hours  
**Status:** Specification

---

## 1. Overview

The Structured Output system enforces that every LLM response includes machine-readable citations, and validates that all citations reference actual retrieved documents. This eliminates citation hallucinations and enables clickable source links in the frontend.

### Objectives

- **Trust:** Every claim has a verifiable source
- **Accuracy:** Zero citation hallucinations (citations pointing to non-existent sources)
- **UX:** Beautiful, clickable citation chips in frontend
- **Compatibility:** Works with existing RAG pipeline and streaming responses

---

## 2. Architecture

### 2.1 Data Flow

```
RAG Pipeline Retrieval
    ↓
[Retrieved Documents] (List[Document])
    ↓
[Format Context with Indices] → "[1] Content... [2] Content..."
    ↓
[LLM Generation with Structured Output] → JSON: {answer, citations: [1, 2]}
    ↓
[Citation Validator] → Remove invalid citations, clean answer text
    ↓
[Frontend] → Render citations as clickable chips
```

### 2.2 Key Components

1. **Pydantic Schema:** Defines strict output format
2. **Prompt Engineering:** Instructs LLM to use citation indices
3. **Citation Validator:** Validates citations against retrieved docs
4. **Frontend Parser:** Extracts and renders citations

---

## 3. Implementation Details

### 3.1 File Structure

```
backend/
├── data_models.py                    # MODIFY: Add StructuredResponse model
├── rag_pipeline.py                   # MODIFY: Add structured output support
├── utils/
│   └── citation_validator.py        # NEW: Citation validation logic
└── main.py                           # MODIFY: Handle structured responses

frontend/
└── src/
    └── components/
        └── CitationChip.tsx         # NEW: Citation UI component
```

### 3.2 Pydantic Schema

**File:** `backend/data_models.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class CitationReference(BaseModel):
    """A single citation reference."""
    index: int = Field(..., description="1-based index of source document", ge=1)
    claim_text: Optional[str] = Field(None, description="The specific claim being cited")
    
class StructuredRAGResponse(BaseModel):
    """
    Structured response from RAG pipeline with enforced citations.
    
    This model is used with Gemini's structured output feature to ensure
    the LLM always returns citations in a machine-readable format.
    """
    answer: str = Field(
        ...,
        description=(
            "The natural language answer to the user's question. "
            "Include inline citation markers like [1], [2] where claims are made."
        )
    )
    citations: List[int] = Field(
        ...,
        description=(
            "List of 1-based indices of source documents used in the answer. "
            "Each index must correspond to a document in the provided context. "
            "Example: [1, 2] means the answer uses sources 1 and 2."
        ),
        min_length=0
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the answer (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    missing_information: Optional[str] = Field(
        None,
        description="Information that was requested but not found in the knowledge base"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Litecoin was created by Charlie Lee in 2011 [1]. It uses the Scrypt algorithm [2].",
                "citations": [1, 2],
                "confidence": 0.95,
                "missing_information": None
            }
        }
```

### 3.3 Citation Validator

**File:** `backend/utils/citation_validator.py`

```python
import re
import logging
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from backend.data_models import StructuredRAGResponse

logger = logging.getLogger(__name__)

class CitationValidator:
    """
    Validates citations in LLM responses against retrieved documents.
    
    Removes hallucinated citations (indices that don't exist) and cleans
    the answer text to remove invalid citation markers.
    """
    
    def __init__(self):
        # Regex pattern to match citation markers like [1], [2], etc.
        self.citation_pattern = re.compile(r'\[(\d+)\]')
    
    def validate_citations(
        self,
        llm_response: StructuredRAGResponse,
        retrieved_docs: List[Document]
    ) -> Tuple[str, List[Dict[str, Any]], List[int]]:
        """
        Validate citations and return cleaned response.
        
        Args:
            llm_response: Structured response from LLM
            retrieved_docs: List of retrieved documents (0-indexed)
            
        Returns:
            Tuple of:
            - cleaned_answer: Answer text with invalid citations removed
            - valid_citations: List of validated citation objects
            - invalid_indices: List of invalid citation indices that were removed
        """
        num_docs = len(retrieved_docs)
        valid_citations = []
        invalid_indices = []
        cleaned_answer = llm_response.answer
        
        # Validate each citation index
        for citation_index in llm_response.citations:
            # Check if index is in valid range (1-based, so 1 to num_docs)
            if 1 <= citation_index <= num_docs:
                # Valid citation - extract document info
                doc = retrieved_docs[citation_index - 1]  # Convert to 0-based
                
                citation_obj = {
                    "index": citation_index,
                    "title": doc.metadata.get("doc_title", "Untitled"),
                    "url": self._extract_url(doc.metadata),
                    "slug": doc.metadata.get("slug"),
                    "payload_id": doc.metadata.get("payload_id"),
                    "chunk_type": doc.metadata.get("chunk_type"),
                }
                valid_citations.append(citation_obj)
            else:
                # Invalid citation - mark for removal
                invalid_indices.append(citation_index)
                logger.warning(
                    f"Hallucinated citation index: {citation_index} "
                    f"(only {num_docs} documents retrieved)"
                )
        
        # Remove invalid citation markers from answer text
        if invalid_indices:
            for invalid_idx in invalid_indices:
                # Remove [N] markers from text
                pattern = re.compile(rf'\[{invalid_idx}\]', re.IGNORECASE)
                cleaned_answer = pattern.sub('', cleaned_answer)
                # Clean up any double spaces left behind
                cleaned_answer = re.sub(r'\s+', ' ', cleaned_answer).strip()
        
        # Extract all citation markers from cleaned answer
        # This ensures we only return citations that are actually mentioned in the text
        mentioned_indices = set()
        for match in self.citation_pattern.finditer(cleaned_answer):
            idx = int(match.group(1))
            if 1 <= idx <= num_docs:
                mentioned_indices.add(idx)
        
        # Filter valid_citations to only include those mentioned in text
        valid_citations = [
            cit for cit in valid_citations
            if cit["index"] in mentioned_indices
        ]
        
        return cleaned_answer, valid_citations, invalid_indices
    
    def _extract_url(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract URL from document metadata.
        
        Priority:
        1. Explicit 'url' field
        2. Construct from 'slug' if available
        3. Construct from Payload CMS article URL pattern
        """
        # Check for explicit URL
        if "url" in metadata and metadata["url"]:
            return metadata["url"]
        
        # Construct from slug
        slug = metadata.get("slug")
        if slug:
            # Assuming base URL pattern (adjust based on your setup)
            base_url = "https://litecoinspace.org"  # Or from env var
            return f"{base_url}/articles/{slug}"
        
        # Construct from Payload ID (fallback)
        payload_id = metadata.get("payload_id")
        if payload_id:
            # Payload CMS article URL pattern
            payload_base = os.getenv("PAYLOAD_PUBLIC_SERVER_URL", "https://cms.lite.space")
            return f"{payload_base}/articles/{payload_id}"
        
        return None
    
    def extract_inline_citations(self, answer_text: str) -> List[Dict[str, int]]:
        """
        Extract citation positions from answer text for frontend rendering.
        
        Returns list of {index: int, position: int} for each citation marker.
        """
        citations = []
        for match in self.citation_pattern.finditer(answer_text):
            index = int(match.group(1))
            position = match.start()
            citations.append({"index": index, "position": position})
        
        return sorted(citations, key=lambda x: x["position"])
```

### 3.4 RAG Pipeline Integration

**File:** `backend/rag_pipeline.py`

**Modifications:**

1. **Add structured output support to LLM initialization:**
```python
# In RAGPipeline.__init__(), after LLM initialization:
from backend.data_models import StructuredRAGResponse

# Create structured LLM variant
self.structured_llm = self.llm.with_structured_output(StructuredRAGResponse)
```

2. **Modify prompt to include indexed context:**
```python
def _format_context_with_indices(self, docs: List[Document]) -> str:
    """
    Format retrieved documents with explicit indices for citation.
    
    Example output:
    [1] Litecoin was created by Charlie Lee in 2011. (Source: history.md)
    [2] MWEB provides confidentiality features. (Source: mweb.md)
    """
    formatted_parts = []
    for i, doc in enumerate(docs, start=1):
        title = doc.metadata.get("doc_title", "Untitled")
        content = doc.page_content[:500]  # Truncate for prompt efficiency
        formatted_parts.append(f"[{i}] {content} (Source: {title})")
    return "\n\n".join(formatted_parts)
```

3. **Update RAG prompt:**
```python
STRUCTURED_RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_INSTRUCTION),
    ("system", (
        "Context (with citation indices):\n{context}\n\n"
        "IMPORTANT: You MUST cite your sources using the [index] numbers above. "
        "For example, if you use information from the first source, include [1] in your answer. "
        "Only cite sources that are actually provided in the context."
    )),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])
```

4. **Modify query methods to use structured output:**
```python
async def aquery_structured(
    self,
    query_text: str,
    chat_history: List[Tuple[str, str]]
) -> Tuple[str, List[Document], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Async query with structured output and citation validation.
    
    Returns:
        Tuple of (answer, sources, citations, metadata)
    """
    from backend.utils.citation_validator import CitationValidator
    
    # ... existing retrieval code ...
    
    # Format context with indices
    context_text = self._format_context_with_indices(context_docs)
    
    # Generate structured response
    result = await self.structured_llm.ainvoke({
        "input": query_text,
        "context": context_text,
        "chat_history": converted_chat_history
    })
    
    # Validate citations
    validator = CitationValidator()
    cleaned_answer, valid_citations, invalid_indices = validator.validate_citations(
        result,
        context_docs
    )
    
    # Log validation results
    if invalid_indices:
        logger.warning(
            f"Removed {len(invalid_indices)} invalid citations: {invalid_indices}"
        )
    
    return cleaned_answer, published_sources, valid_citations, metadata
```

### 3.5 Main Endpoint Integration

**File:** `backend/main.py`

**Modify response model:**
```python
class CitationInfo(BaseModel):
    """Citation information for frontend."""
    index: int
    title: str
    url: Optional[str] = None
    slug: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    citations: List[CitationInfo] = []  # NEW: Validated citations
```

**Update chat endpoint:**
```python
# In chat_stream_endpoint(), after RAG pipeline call:
answer, sources, citations, metadata = await rag_pipeline_instance.aquery_structured(
    request.query,
    paired_chat_history
)

# Include citations in response
citations_json = [CitationInfo(**cit) for cit in citations]

# Send citations in stream
yield f"data: {json.dumps({
    'status': 'citations',
    'citations': jsonable_encoder(citations_json),
    'isComplete': False
})}\n\n"
```

### 3.6 Frontend Integration

**File:** `frontend/src/components/CitationChip.tsx`

```typescript
import React from 'react';

interface CitationChipProps {
  index: number;
  title: string;
  url?: string;
  onClick?: (index: number) => void;
}

export const CitationChip: React.FC<CitationChipProps> = ({
  index,
  title,
  url,
  onClick,
}) => {
  const handleClick = () => {
    if (onClick) {
      onClick(index);
    } else if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center px-2 py-1 mx-1 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200 transition-colors cursor-pointer"
      title={title}
      aria-label={`Citation ${index}: ${title}`}
    >
      [{index}]
    </button>
  );
};
```

**File:** `frontend/src/components/Message.tsx` (modify existing)

```typescript
// Add citation parsing
import { CitationChip } from './CitationChip';

// Parse answer text for citations
const parseCitations = (text: string, citations: CitationInfo[]) => {
  const parts: React.ReactNode[] = [];
  const citationMap = new Map(citations.map(c => [c.index, c]));
  const citationPattern = /\[(\d+)\]/g;
  
  let lastIndex = 0;
  let match;
  
  while ((match = citationPattern.exec(text)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    
    // Add citation chip
    const index = parseInt(match[1], 10);
    const citation = citationMap.get(index);
    if (citation) {
      parts.push(
        <CitationChip
          key={`citation-${index}-${match.index}`}
          index={index}
          title={citation.title}
          url={citation.url}
        />
      );
    }
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  
  return parts.length > 0 ? parts : text;
};

// In Message component render:
{parseCitations(content, message.citations || [])}
```

---

## 4. Validation Algorithm Details

### 4.1 Citation Validation Steps

1. **Index Range Check:** Verify citation index is 1 ≤ index ≤ num_docs
2. **Text Extraction:** Extract citation markers from answer text
3. **Consistency Check:** Ensure cited indices appear in answer text
4. **Cleanup:** Remove invalid markers from text
5. **URL Resolution:** Construct URLs from metadata (slug, payload_id, etc.)

### 4.2 Edge Cases Handled

- **Hallucinated Citations:** `[3]` when only 2 docs retrieved → Removed
- **Missing Citations:** LLM forgets to cite → Warning logged, answer still returned
- **Invalid Indices:** `[0]` or `[-1]` → Removed
- **Duplicate Citations:** `[1] [1]` → Both kept (user can see multiple references)
- **Out-of-Order Citations:** `[2] [1]` → Both kept (order doesn't matter)

---

## 5. Monitoring & Metrics

### 5.1 Prometheus Metrics

```python
# Citation Validation Metrics
citation_validation_total = Counter(
    "citation_validation_total",
    "Total citation validations performed",
    ["status"]  # "valid", "invalid_removed", "missing"
)

citation_hallucinations_total = Counter(
    "citation_hallucinations_total",
    "Total hallucinated citations removed",
    ["invalid_index_range"]
)

citation_validation_duration_seconds = Histogram(
    "citation_validation_duration_seconds",
    "Citation validation processing time",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)
```

### 5.2 Logging

- **WARNING:** Hallucinated citations (index, num_docs)
- **INFO:** Citation validation summary (valid/invalid counts)
- **DEBUG:** Detailed citation extraction process

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
def test_citation_validation_valid():
    """Test validation with valid citations."""
    response = StructuredRAGResponse(
        answer="Litecoin was created in 2011 [1]. It uses Scrypt [2].",
        citations=[1, 2],
        confidence=0.95
    )
    docs = [
        Document(page_content="Created in 2011", metadata={"doc_title": "History"}),
        Document(page_content="Uses Scrypt", metadata={"doc_title": "Tech"}),
    ]
    
    validator = CitationValidator()
    cleaned, citations, invalid = validator.validate_citations(response, docs)
    
    assert len(citations) == 2
    assert len(invalid) == 0
    assert "[1]" in cleaned
    assert "[2]" in cleaned

def test_citation_validation_hallucination():
    """Test removal of hallucinated citations."""
    response = StructuredRAGResponse(
        answer="Some claim [3].",
        citations=[3],  # Only 2 docs provided
        confidence=0.8
    )
    docs = [
        Document(page_content="Doc 1", metadata={}),
        Document(page_content="Doc 2", metadata={}),
    ]
    
    validator = CitationValidator()
    cleaned, citations, invalid = validator.validate_citations(response, docs)
    
    assert len(citations) == 0
    assert len(invalid) == 1
    assert "[3]" not in cleaned
```

### 6.2 Integration Tests

- Test structured output generation with Gemini
- Test citation validation with real retrieved documents
- Test frontend citation rendering
- Test streaming responses with citations

---

## 7. Performance Considerations

### 7.1 Latency Impact

- **Citation Validation:** <5ms (regex + list operations)
- **Structured Output:** Same as regular LLM call (no extra latency)
- **Total Overhead:** <10ms

### 7.2 Optimization

- Cache citation validator instance
- Pre-compile regex patterns
- Batch citation URL resolution

---

## 8. Deployment Checklist

- [ ] Add `StructuredRAGResponse` to `data_models.py`
- [ ] Create `citation_validator.py`
- [ ] Modify RAG pipeline for structured output
- [ ] Update prompt templates
- [ ] Add citation validation to query methods
- [ ] Update main endpoint to handle citations
- [ ] Create `CitationChip` component
- [ ] Update `Message` component for citation parsing
- [ ] Add Prometheus metrics
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Test with real queries
- [ ] Deploy to staging
- [ ] Monitor citation validation metrics
- [ ] Deploy to production

---

## 9. Future Enhancements

1. **Citation Granularity:** Link citations to specific sentences/paragraphs
2. **Citation Confidence:** Show confidence scores per citation
3. **Citation Analytics:** Track which sources are cited most often
4. **Auto-Citation:** Automatically add citations for un-cited claims
5. **Citation Search:** Allow users to filter answers by source

---

## 10. References

- **Current RAG Pipeline:** `backend/rag_pipeline.py`
- **Data Models:** `backend/data_models.py`
- **Chat Endpoint:** `backend/main.py:935`
- **Gemini Structured Output:** https://ai.google.dev/gemini-api/docs/structured-output

