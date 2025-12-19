# Litecoin Knowledge Hub - Article Template Guide

> **Purpose**: This guide defines the optimal structure for LLM-generated articles to maximize retrieval quality in the RAG pipeline.

---

## How This System Works

```
Payload CMS Article → Lexical → Markdown → Hierarchical Chunking → Vector Embeddings → RAG Retrieval
```

Each **paragraph** under a heading becomes a separate semantic chunk with prepended context:

```
Title: [Article Title]
Section: [H1/H2 Heading]
Subsection: [H3 Heading]

[Paragraph content...]
```

---

## Canonical Terminology

Always use these official terms for consistency:

| Canonical Term | Never Use |
|----------------|-----------|
| **MWEB** | MimbleWimble, extension blocks, privacy feature |
| **LitVM** | Litecoin Virtual Machine, ZK-rollup |
| **Scrypt** | script, scrypt algorithm |
| **Lightning** | Lightning Network, LN |
| **Halving** | halvening, reward reduction |
| **Creator** or **Charlie Lee** | founder, developer |
| **Litecoin** or **LTC** | litecoin (lowercase in technical context) |

---

## Article Template

```markdown
# Overview

[1-2 sentence high-impact definition. Start with the subject name, not a pronoun. Use canonical terminology. This chunk has highest retrieval weight for "what is X" queries.]

**Key Points:**
* [Standalone fact 1 - include the subject name]
* [Standalone fact 2 - specific numbers/dates when possible]
* [Standalone fact 3 - differentiating characteristic]

## Background

[Context paragraph 1: Origin story, creation date, creator. Always name the subject explicitly.]

[Context paragraph 2: Problem it solves, motivation. Each paragraph = separate retrievable chunk.]

[Context paragraph 3: Evolution or adoption history with specific dates/milestones.]

## How [Topic] Works

[Technical explanation paragraph 1: The "what" - describe the mechanism at a high level. Bold key terms like **Scrypt** or **MWEB**.]

[Technical explanation paragraph 2: The "how" - describe the process or workflow. Use numbered steps if applicable.]

### Technical Specifications

[Deeper technical content: algorithms, parameters, protocols. Include specific values.]

| Specification | Value |
|--------------|-------|
| [Param 1] | [Value] |
| [Param 2] | [Value] |

### Security Model

[Security explanation. Reference **Proof of Work**, **84 million LTC** max supply, or other security properties as relevant.]

## Use Cases

[Use case paragraph 1: Who uses this and why. Be specific about user types.]

[Use case paragraph 2: Different application or user segment.]

### For Everyday Users

[User-focused explanation in accessible language. Avoid jargon.]

### For Developers

[Developer-focused explanation with technical accuracy. Can include code concepts.]

### For Businesses

[Business/merchant-focused explanation with practical benefits.]

## Comparison with [Related Concept]

[Comparative analysis paragraph. Explicitly state both subjects being compared.]

| Aspect | **Litecoin** | **[Other]** |
|--------|-------------|-------------|
| [Feature 1] | [LTC value] | [Other value] |
| [Feature 2] | [LTC value] | [Other value] |
| [Feature 3] | [LTC value] | [Other value] |

## History & Timeline

[Introductory sentence about the historical development of this topic.]

* **[YYYY-MM-DD]**: [Event description with context]
* **[YYYY-MM-DD]**: [Event description with context]
* **[YYYY-MM-DD]**: [Event description with context]

## Frequently Asked Questions

### What is [topic] and why does it matter?

[Direct 2-3 sentence answer. Restate the question's subject in the answer.]

### How do I [common action related to topic]?

[Step-by-step or explanatory answer. Be specific and actionable.]

### Is [topic] safe/secure/reliable?

[Confidence-building answer with factual basis.]

### What's the difference between [topic] and [related thing]?

[Clear differentiation with specific contrasts.]

## Summary

[2-3 sentence recap hitting the main keywords. Reinforces core concepts for both semantic embedding and BM25 keyword matching. Mention the canonical terms one more time.]

## Related Topics

* [[Related Article 1]]
* [[Related Article 2]]
* [[Related Article 3]]
```

---

## Writing Guidelines

### ✅ DO

1. **Start paragraphs with the subject name**
   - ✅ "**Litecoin** uses the Scrypt hashing algorithm..."
   - ❌ "It uses the Scrypt hashing algorithm..."

2. **Make each paragraph self-contained**
   - Each paragraph becomes a separate chunk
   - Should make sense without reading previous paragraphs

3. **Use 2-4 sentences per paragraph**
   - Too short = weak semantic signal
   - Too long = diluted relevance

4. **Bold canonical terms on first use in each section**
   - `**MWEB**`, `**Scrypt**`, `**Lightning**`

5. **Include specific numbers and dates**
   - "Created on October 7, 2011" not "Created in 2011"
   - "2.5 minute block time" not "faster block time"

6. **Use heading hierarchy properly**
   - H1 (`#`) = Major sections (Overview, Background, etc.)
   - H2 (`##`) = Main topics within sections
   - H3 (`###`) = Subtopics (Technical Details, For Users, etc.)

7. **Include an FAQ section**
   - Direct Q&A has highest semantic match to user queries
   - Each Q&A pair becomes a highly retrievable chunk

### ❌ DON'T

1. **Start with pronouns**
   - ❌ "It was created by Charlie Lee..."
   - ❌ "This technology enables..."

2. **Use vague language**
   - ❌ "very fast" → ✅ "2.5 minute block time"
   - ❌ "low fees" → ✅ "average fee of $0.01"

3. **Bury key terms mid-paragraph**
   - Put important terms in the first sentence of each paragraph

4. **Create wall-of-text paragraphs**
   - Break into digestible 2-4 sentence paragraphs

5. **Use non-canonical terminology**
   - Always use the standard terms from the terminology table

---

## Example: Well-Structured Article

```markdown
# Overview

**MWEB** (MimbleWimble Extension Blocks) is **Litecoin's** privacy and scalability upgrade activated on May 19, 2022. It enables confidential transactions where amounts are hidden from public view while maintaining full blockchain security.

**Key Points:**
* **MWEB** hides transaction amounts using cryptographic commitments
* Users can opt-in to privacy by sending to MWEB addresses
* The upgrade maintains **Litecoin's** fungibility without sacrificing auditability

## Background

**MWEB** was proposed by **Charlie Lee** in 2019 as a solution to **Litecoin's** transparency limitations. Traditional blockchain transactions expose exact amounts to anyone viewing the ledger, which can compromise user privacy in commercial settings.

Development was led by David Burkett, a cryptographer specializing in MimbleWimble implementations. The feature underwent extensive testing on testnet before the mainnet activation at block height 2,257,920.

## How MWEB Works

**MWEB** creates a parallel transaction layer called an "extension block" that runs alongside the main **Litecoin** blockchain. When users send **LTC** to an MWEB address, their coins enter this confidential layer where amounts are encrypted using Pedersen commitments.

The protocol uses cut-through to aggregate transactions, meaning intermediate transaction data can be pruned. This improves scalability by reducing the data nodes must store while maintaining cryptographic proof that no coins were created or destroyed.

### Technical Specifications

| Specification | Value |
|--------------|-------|
| Activation Block | 2,257,920 |
| Activation Date | May 19, 2022 |
| Cryptographic Scheme | Pedersen Commitments |
| Address Prefix | ltcmweb1 |

### Security Model

**MWEB** maintains the same **Proof of Work** security as standard **Litecoin** transactions. The extension block is validated by all full nodes, and any attempt to inflate the **84 million LTC** supply would be detected and rejected.

## Frequently Asked Questions

### What is MWEB and why does it matter?

**MWEB** is **Litecoin's** privacy upgrade that hides transaction amounts. It matters because it gives users the option to keep their financial activity private, similar to cash transactions in the physical world.

### How do I use MWEB for private transactions?

To use **MWEB**, you need a compatible wallet like Litecoin Core or Litewallet. Simply send **LTC** to an MWEB address (starting with ltcmweb1), and your transaction amount will be hidden on the blockchain.

## Summary

**MWEB** represents **Litecoin's** most significant upgrade since its creation, bringing confidential transactions to one of the oldest cryptocurrencies. By using MimbleWimble cryptography in extension blocks, **MWEB** provides optional privacy while preserving **Litecoin's** core properties of security, speed, and low fees.
```

---

## Payload CMS Field Mapping

| Template Element | Payload Field | Notes |
|-----------------|---------------|-------|
| Article title | `title` | Becomes `doc_title` in chunks |
| All markdown content | `content` (rich text) | Converted to markdown automatically |
| Publication date | `publishedDate` | Set when publishing |
| Topic categories | `category` | Select relevant categories |
| Article state | `status` | `draft` → `published` |

---

## Chunk Metadata Generated

When processed, each paragraph generates metadata:

```json
{
  "payload_id": "article-uuid",
  "source": "payload",
  "doc_title": "MWEB - Litecoin's Privacy Upgrade",
  "section_title": "How MWEB Works",
  "subsection_title": "Technical Specifications",
  "status": "published",
  "categories": ["technology", "privacy"],
  "chunk_type": "section",
  "chunk_index": 5
}
```

This metadata enables filtered retrieval and source attribution in responses.

---

## LLM Prompt for Article Generation

When using an LLM to generate articles from research, use this system prompt:

```
You are a technical writer for the Litecoin Knowledge Hub. Generate a comprehensive article following these rules:

1. Use ONLY these canonical terms: MWEB, LitVM, Scrypt, Lightning, Halving, Creator/Charlie Lee
2. Start every paragraph with the subject name, never pronouns
3. Write 2-4 sentences per paragraph
4. Bold canonical terms on first use in each section
5. Include specific numbers, dates, and technical values
6. Structure with: Overview, Background, How It Works, Use Cases, FAQ, Summary
7. Each paragraph must be self-contained and understandable alone
8. Include a table of technical specifications where applicable
9. Write 3-5 FAQ questions with direct answers

Research to incorporate:
[INSERT RESEARCH HERE]
```

---

*Last updated: December 2024*

