# Large Documents Analysis

## Documents Over 8,000 Characters

The following documents exceed 8,000 characters and are truncated to 8,000 chars during re-indexing with BGE-M3 to prevent memory issues:

| Rank | Length (chars) | Document Title |
|------|---------------|----------------|
| 1 | 36,725 | **Blockchain** |
| 2 | 24,654 | **Proof of work** |
| 3 | 20,474 | **Fork (blockchain)** |
| 4 | 14,082 | **SegWit** |
| 5 | 11,852 | **Why Litecoin?** |
| 6 | 9,243 | **LitVM: Litecoin's Zero-Knowledge Omnichain – Revolutionizing Payments, DeFi, and Web3 Interoperability** |
| 7 | 8,807 | **Keys and Addresses** |
| 8 | 8,679 | **What are the implications of Scrypt vs SHA-256? How does merged mining with Dogecoin enhance security?** |
| 9 | 8,060 | **How Litecoin Works** |

## Statistics

- **Total documents**: 511
- **Average length**: 1,830 chars
- **Documents over 8,000 chars**: 9 (1.8%)
- **Documents over 10,000 chars**: 5 (1.0%)
- **Documents over 20,000 chars**: 3 (0.6%)

## Truncation Policy

During re-indexing with BGE-M3, documents exceeding **8,000 characters** are automatically truncated to prevent:
- MPS memory buffer overflow (30GB+ buffer size errors)
- Model timeout issues
- Excessive processing time

The truncation preserves the first 8,000 characters, which typically contains the most important content (title, introduction, key concepts).

## Impact on Retrieval

Documents are truncated at **indexing time**, not at query time. This means:
- ✅ Full document content is available in MongoDB
- ✅ Embeddings are generated from first 8,000 chars
- ✅ Retrieval may miss content beyond 8,000 chars
- ⚠️ Very long documents (20K+ chars) may have reduced retrieval quality

## Recommendations

1. **For very long documents**: Consider splitting into multiple chunks (e.g., by section)
2. **For glossary/reference documents**: Current truncation is acceptable (key terms are usually at the start)
3. **Monitoring**: Track retrieval quality for queries about topics in truncated sections

## Example: "Blockchain" Document

The "Blockchain" document is 36,725 characters. It's truncated to 8,000 chars (about 22% of original content). This is likely a glossary-style document where key definitions appear early, so truncation impact should be minimal.

