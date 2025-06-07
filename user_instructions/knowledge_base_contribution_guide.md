# Guide to Contributing to the Litecoin RAG Knowledge Base

## 1. The Philosophy: Why Curated Content Matters
The Litecoin RAG Chatbot aims to be the most reliable and accurate source of information for all things Litecoin. Its effectiveness is directly tied to the quality, clarity, and accuracy of the human-vetted articles stored in the `knowledge_base/` directory. This "content-first" strategy means that every piece of information the chatbot uses from this core set has been carefully researched, written, and structured for optimal understanding by both humans and our AI.

Our goal is to build a trusted resource. Your contributions are vital to achieving this.

## 2. The Golden Rule: Write for Clarity and Accuracy
All content contributed to the knowledge base must adhere to these core principles:

*   **Objectivity:** Present information factually and without bias. Avoid personal opinions, speculation, or promotional language. The aim is to educate, not to persuade towards a particular viewpoint beyond factual representation.
*   **Accuracy:** All statements, especially technical details and figures, must be thoroughly researched and verifiable. Where possible, cite or link to primary sources (e.g., official Litecoin documentation, Litecoin Improvement Proposals (LIPs), academic papers, or reputable technical analyses).
*   **Clarity:** Write for a broad audience, which includes both newcomers to Litecoin and experienced developers. Explain complex concepts in simple, accessible language without oversimplifying or sacrificing technical correctness. Define any jargon or specialized terms on their first use.
*   **Conciseness:** Be as clear and to the point as possible. While articles should be comprehensive, avoid unnecessary verbosity.

## 3. Structure of a Knowledge Base Article
To ensure consistency and optimal processing by our RAG pipeline, all articles must follow this structure:

*   **Filename:**
    *   Use lowercase letters.
    *   Separate words with hyphens (`-`).
    *   Example: `what-is-mweb.md`, `understanding-scrypt-algorithm.md`.
*   **Frontmatter (YAML):**
    *   Every article must begin with YAML frontmatter enclosed in triple-dashed lines (`---`).
    *   Required fields:
        *   `title`: The main title of the article (e.g., "Understanding Litecoin's MimbleWimble Extension Blocks (MWEB)").
        *   `tags`: A list of relevant keywords or categories (e.g., `["mweb", "privacy", "fungibility", "protocol"]`).
        *   `last_updated`: The date the article was last significantly revised, in `YYYY-MM-DD` format (e.g., `2025-06-06`).
    *   Example:
        ```yaml
        ---
        title: Understanding Litecoin's MimbleWimble Extension Blocks (MWEB)
        tags: ["mweb", "privacy", "fungibility", "protocol"]
        last_updated: 2025-06-06
        ---
        ```
*   **Headings:**
    *   Each article must have exactly one Level 1 Heading (`# Main Title`), which should match the `title` in the frontmatter.
    *   Use Level 2 Headings (`## Section`) and Level 3 Headings (`### Subsection`) to logically structure the content.
    *   Proper heading structure is crucial for the RAG system to effectively "chunk" the document for retrieval.

*   **Why This Structure is Critical for AI:**
    *   Our RAG (Retrieval-Augmented Generation) system relies heavily on this hierarchical structure (Frontmatter Title -> `# H1 Title` -> `## Section` -> `### Subsection` -> Paragraphs).
    *   When processing your article, the system "chunks" it into smaller pieces. Each chunk is then embedded (turned into a vector) with its hierarchical context prepended.
    *   For example, a paragraph under "### MWEB Details" within "## How MWEB Works" from an article titled "Litecoin Privacy Features" might be embedded as:
        ```
        Title: Litecoin Privacy Features
        Section: How MWEB Works
        Subsection: MWEB Details

        MWEB (MimbleWimble Extension Blocks) enhances privacy by...
        ```
    *   This rich contextual information in the vector allows the AI to perform much more accurate and relevant searches when a user asks a question. Following the `_template.md` and these structural guidelines directly improves the AI's ability to understand and use your content effectively.

## 4. Content Formatting and Style Guide
Adherence to these formatting guidelines ensures readability and consistent parsing:

*   **Markdown:** All articles must be written in standard Markdown.
*   **Links:**
    *   Use descriptive text for links, e.g., `[Litecoin Improvement Proposals](https://litecoin.info/index.php/LIPs)`.
    *   Avoid generic link text like "click here."
*   **Code Snippets:**
    *   Use backticks for inline code: `` `scrypt` ``.
    *   Use triple backticks for code blocks, specifying the language for syntax highlighting where appropriate:
        ```json
        {
          "example": "data"
        }
        ```
*   **Lists:**
    *   Use standard Markdown for bulleted (`*`, `-`, or `+`) and numbered (`1.`, `2.`) lists.
*   **Emphasis:**
    *   Use double asterisks (`**text**`) for strong emphasis or to highlight key terms.
    *   Use single asterisks (`*text*`) for light emphasis or when defining a term for the first time.
*   **Blockquotes:**
    *   Use `>` for blockquotes, for quoting external sources or highlighting important notes.
*   **Tables:**
    *   Use Markdown tables for structured data where appropriate.

## 5. Contribution Workflow
Follow these steps to contribute new content or update existing articles:

1.  **Identify a Need:** Determine if a new topic needs to be covered or an existing article requires updates/corrections. Check `cline_docs/currentTask.md` for content-related tasks.
2.  **Create/Locate File:**
    *   **New Article:** Create a new `.md` file in the `knowledge_base/` directory using the specified filename convention.
    *   **Existing Article:** Open the relevant file in `knowledge_base/`.
3.  **Use the Template:** For new articles, it's recommended to start by copying the content of `knowledge_base/_template.md` (if it exists and is up-to-date) or by ensuring you include the required frontmatter.
4.  **Write/Edit Content:**
    *   Adhere strictly to the structural, formatting, and style guidelines outlined in this document.
    *   Focus on accuracy, clarity, and objectivity.
    *   Cite sources where necessary.
5.  **Local Verification (Recommended):**
    *   If you have the project set up locally, navigate to the `backend/` directory.
    *   Activate your Python virtual environment.
    *   Run the ingestion script targeting the `knowledge_base` directory to ensure your new/updated article parses correctly:
        ```bash
        python ingest_data.py --source_type markdown --source_identifier ../knowledge_base
        ```
    *   Check for any errors in the console output.
6.  **Submit for Review:**
    *   Commit your changes with a clear commit message.
    *   Push your changes to your fork/branch.
    *   Open a Pull Request (PR) against the main project repository.
    *   In your PR description, briefly explain the purpose of your contribution and any specific areas reviewers should focus on.

Thank you for helping build a high-quality knowledge resource for the Litecoin community!
