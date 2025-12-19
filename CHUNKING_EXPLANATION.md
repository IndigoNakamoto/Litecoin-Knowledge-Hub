# How Your System Chunks the Litecoin Ordinals Article

## Overview

Your system uses a **hierarchical markdown parser** that creates semantic chunks based on the document's heading structure. Each paragraph under a heading becomes a single chunk, with hierarchical context prepended.

## Chunking Strategy

### Key Principles

1. **One paragraph = One chunk**: Each paragraph (or group of consecutive paragraphs) under a heading becomes a single semantic chunk
2. **Hierarchical context**: Each chunk gets prepended with its heading hierarchy:
   - `Title: {H1}`
   - `Section: {H2}`
   - `Subsection: {H3}`
   - `Sub-subsection: {H4}`
3. **For Payload documents**: H1 headings are treated as H2 (section level), since the document title comes from metadata
4. **No further splitting**: Unlike character-based splitters, paragraphs are NOT split further - they remain intact as semantic units

### How Your Article Was Chunked

The Litecoin Ordinals article was split into **21 chunks**:

1. **Chunk 1**: Introduction paragraph under `# Litecoin Ordinals` (treated as H2 section)
2. **Chunk 2**: `## Brief Background` section
3. **Chunk 3**: `## How They Work Simply` section
4. **Chunk 4**: `# Overview` section (treated as H2)
5. **Chunk 5**: `## Background` section
6. **Chunk 6**: `## How Litecoin Ordinals Works` section (first paragraph)
7. **Chunk 7**: `### Technical Specifications` subsection
8. **Chunk 8**: `### Security Model` subsection
9. **Chunk 9**: `## Use Cases` section (first paragraph)
10. **Chunk 10**: `### For Everyday Users` subsection
11. **Chunk 11**: `### For Developers` subsection
12. **Chunk 12**: `### For Businesses` subsection
13. **Chunk 13**: `## Comparison with Bitcoin Ordinals` section
14. **Chunk 14**: `## History & Timeline` section
15. **Chunk 15**: `### What is Litecoin Ordinals and why does it matter?` FAQ
16. **Chunk 16**: `### How do I create a Litecoin Ordinal?` FAQ
17. **Chunk 17**: `### Is Litecoin Ordinals safe/secure/reliable?` FAQ
18. **Chunk 18**: `### What's the difference between Litecoin Ordinals and Bitcoin Ordinals?` FAQ
19. **Chunk 19**: `### How do Litecoin Ordinals integrate with other Litecoin features?` FAQ
20. **Chunk 20**: `## Summary` section
21. **Chunk 21**: `## Related Topics` section (includes citations)

## Example Chunk Structure

Each chunk looks like this:

```
Title: Litecoin Ordinals
Section: How Litecoin Ordinals Works
Subsection: Technical Specifications

**Litecoin Ordinals** rely on **Litecoin's** **Scrypt** hashing algorithm...
```

## Metadata Attached to Each Chunk

- `doc_title_hierarchical`: The main document title
- `section_title`: H2 heading (or H1 if treated as section)
- `subsection_title`: H3 heading
- `subsubsection_title`: H4 heading
- `chunk_type`: 'section' or 'text'
- `content_length`: Length of content without headers
- `chunk_index`: Sequential index (0-based)
- `payload_id`: Document ID from Payload CMS
- Plus all original metadata (author, published_date, etc.)

## Benefits of This Approach

1. **Semantic coherence**: Each chunk is a complete thought/paragraph, not arbitrarily split
2. **Context preservation**: Hierarchical headers provide context for better retrieval
3. **Better search**: Users can find specific sections (e.g., "Technical Specifications") easily
4. **No information loss**: Tables, lists, and multi-paragraph sections stay together

## Notes

- Tables are included as part of the paragraph they're in
- Lists (bullet points) are included in the same chunk as their section
- Empty lines between paragraphs don't create separate chunks - they're grouped together
- The horizontal rule (`---`) in your article creates a natural break, starting a new section

