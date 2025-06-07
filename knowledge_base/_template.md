---
# YAML Frontmatter: Provides critical metadata for search and organization.
# Ensure all fields are filled accurately.

title: "Your Article Title Here"  # The main, human-readable title of the article.
tags: ["tag1", "tag2", "relevant-keyword"] # A list of 3-5 relevant keywords. Helps with filtering and finding related content.
last_updated: "YYYY-MM-DD" # Date of the last significant revision. Use ISO 8601 format.
---

# Your Article Title Here
# IMPORTANT: This H1 heading MUST exactly match the 'title' field in the YAML frontmatter above.
# This is crucial for how our AI understands and categorizes the document.

*This introductory paragraph should provide a brief, high-level summary of the topic. It should clearly state what the reader will learn from this article and why it is important.*

## Core Concepts
*Start with the most fundamental aspects of the topic. Define key terms clearly and explain the basics before moving on to more complex details. Assume the reader has a general interest but may not be an expert.*

Explain the first core concept here. Use clear and simple language.

### Deeper Dive into a Concept
*Use subsections to elaborate on specific details of a core concept. This helps keep the main sections clean and easy to scan.*

Provide more detailed information here. You can use bullet points for clarity:
*   Point A: Explain a specific detail.
*   Point B: Explain another related detail.
*   Point C: Explain a third detail.

## How It Works
*This section should detail a process, mechanism, or technical workflow. Break it down into logical steps if possible.*

Provide a step-by-step explanation. For technical topics, consider using code blocks to illustrate your points:

```
# Example code snippet or command
# This helps make abstract concepts concrete.
def example_function():
    return "hello world"
```

## Importance and Implications
*Explain why this topic is important within the Litecoin ecosystem. Discuss its benefits, trade-offs, or impact on users, developers, or the network.*

Discuss the broader context and relevance here. This helps the reader understand not just *what* something is, but *why* it matters.

## Conclusion
*Summarize the key takeaways from the article. The reader should leave with a clear and confident understanding of the topic. Reiterate the most important points in a few sentences.*

---
*For more detailed guidelines on formatting and style, please refer to the [Knowledge Base Contribution Guide](../user_instructions/knowledge_base_contribution_guide.md).*

---
**A Note on Structure for AI Processing:**
Our AI system (RAG) processes this document by breaking it into "chunks" based on its structure (Title -> H1 -> H2 -> H3 -> Paragraphs).
When you follow this template:
1.  The **YAML frontmatter** provides high-level metadata.
2.  The **`# H1 Title`** (matching the YAML `title`) acts as the main identifier.
3.  **`## H2 Sections`** and **`### H3 Subsections`** create a clear hierarchy.
4.  **Paragraphs** under these headings form the content chunks.

The AI then prepends this hierarchy to each chunk (e.g., "Title: X\nSection: Y\nSubsection: Z\n\nParagraph content...").
This rich, structured context allows the AI to find and use your information much more accurately.
**Please adhere to this structure carefully.**
