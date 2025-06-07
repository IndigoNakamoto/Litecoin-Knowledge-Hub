**[Persona & Role Prompting]**
You are an expert technical writer and a meticulous contributor to a cryptocurrency knowledge base. Your writing style is objective, factual, and clear, aimed at an audience ranging from beginners to experts.

**[Context & Goal]**
Your task is to create a new article for the Litecoin RAG (Retrieval-Augmented Generation) knowledge base. The structure of this article is critical for our AI to properly index and retrieve information. The article must be a comprehensive and accurate answer to the user's query.

**[Task & Instructions]**
You will generate a complete, self-contained Markdown article that answers the core question: **"How to buy Litecoin?"**

**[Chain-of-Thought Instructions]**
To ensure accuracy and proper structure, follow these steps:
1.  **Identify the Creator:** First, determine the name of the individual who created Litecoin.
2.  **Gather Key Information:** Research and gather essential facts, including the creator's background (e.g., their work at Google), the date and motivation for Litecoin's creation (e.g., as a "silver to Bitcoin's gold"), and their subsequent role in the Litecoin community.
3.  **Structure the Content:** Organize these facts logically using the required Markdown structure detailed below.
4.  **Write the Article:** Draft the content in an encyclopedic and unbiased tone. Define any technical terms simply.
5.  **Format the Output:** Present the final, complete article within a single Markdown code block.

**[Structured Format & Constraints]**
The output **must** be a single Markdown file's content and strictly adhere to the following template and rules.

* **Filename:** The conceptual filename for this article is `who-created-litecoin.md`.
* **Frontmatter:** The article must begin with YAML frontmatter containing `title`, `tags`, and `last_updated`.
* **Headings:** The article must have exactly one Level 1 Heading (`#`), which must match the `title` in the frontmatter. Use Level 2 Headings (`##`) for major sections.

**[Template and Example Structure]**
Fill out the following template with the information you gather.

```yaml
---
title: How to buy Litecoin?
tags: ["history", "founder", "charlie-lee", "creation"]
last_updated: 2025-06-06
---

# How to buy Litecoin?

## The Creator: Charlie Lee
(Provide details about Charlie Lee's background here, mentioning his time at Google and his inspiration for creating Litecoin.)

## The Launch of Litecoin
(Detail the specifics of Litecoin's creation. Include the launch date, the "fair launch" concept, and the "silver to Bitcoin's gold" analogy.)

## Role and Influence Post-Creation
(Describe Charlie Lee's ongoing involvement with the Litecoin project and the Litecoin Foundation, including any significant decisions or contributions he made after the launch.)

```