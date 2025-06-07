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
    *   The specific fields required in the frontmatter are defined in the template file `knowledge_base/_template.md`. Please refer to this template for the standard set of metadata fields such as `title`, `id`, `category`, `tags`, `summary`, `last_updated`, `author`, `source`, `language`, and `relevance_score`.
    *   Ensure all fields specified in `knowledge_base/_template.md` are included and correctly formatted.
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

## 5. Using DeepSearch (or similar AI tools) for Initial Drafts
To accelerate content creation, especially for comprehensive topics, AI-powered research tools like DeepSearch can be used to generate initial drafts. However, these drafts **must** undergo a rigorous human vetting and curation process before being considered part of the canonical knowledge base.

*   **Directory:** Articles initiated via DeepSearch should be placed in the `knowledge_base/deep_research/` subdirectory.
*   **Prompt Engineering:**
    *   Craft precise prompts to guide the AI. For example:
        *   **For FAQs (Feature 1):** "Generate concise, beginner-friendly answers to common Litecoin questions (e.g., ‘What is Litecoin?’, ‘How to set up a wallet?’) using simple language, sourced from Litecoin Foundation, CoinMarketCap, and X sentiment."
        *   **For Knowledge Base Articles (Feature 5):** "Create a structured article on Litecoin’s history, technical features, and recent developments, with sections for ‘Introduction,’ ‘Key Features,’ and ‘Updates,’ sourced from official docs, blockchain data, and recent X posts."
    *   Instruct the AI to focus on Litecoin-specific information and avoid general crypto content unless for direct comparison.
*   **Initial Output:** Save the raw output from DeepSearch as a Markdown file in `knowledge_base/deep_research/`.
*   **Mandatory Frontmatter for DeepSearch Drafts:**
    *   Articles originating from DeepSearch must include all standard frontmatter fields as defined in `knowledge_base/_template.md`.
    *   In addition, they **must** include specific fields to track their origin and vetting status. These additional fields are defined in the `knowledge_base/deep_research/_template_deepsearch.md` template. Please refer to this template for fields such as `source_type`, `original_deepsearch_query`, `vetting_status`, `vetter_name`, and `vetting_date`.
    *   Ensure all fields specified in both `knowledge_base/_template.md` (for common fields) and `knowledge_base/deep_research/_template_deepsearch.md` (for DeepSearch-specific fields) are included and correctly formatted.
*   **Human Vetting and Curation Process (CRITICAL):**
    1.  **Selection:** Pick a `draft` article from `knowledge_base/deep_research/`.
    2.  **Verification:** Thoroughly cross-check all facts, figures, and technical details against trusted primary sources (e.g., litecoin.org, official GitHub, reputable exchanges/market data sites).
    3.  **Correction & Enhancement:**
        *   Correct any inaccuracies, outdated information, or misleading statements.
        *   Fill content gaps. Research and add information that the AI might have missed, especially for niche or highly technical topics.
        *   Rewrite sections for clarity, conciseness, and appropriate tone (beginner-friendly for FAQs, technically sound for deeper articles).
        *   Ensure objectivity and remove any AI-generated biases or speculative content.
    4.  **Structuring for RAG:**
        *   Ensure the article adheres to the heading structure (`# H1`, `## H2`, `### H3`) outlined in Section 3.
        *   Format content for optimal readability and machine parsing (lists, code blocks, etc.).
    5.  **Metadata Update:**
        *   Change `vetting_status` to `vetted`.
        *   Fill in `vetter_name` with your name/identifier.
        *   Set `vetting_date` to the current date (`YYYY-MM-DD`).
        *   Update `last_updated` to the current date.
        *   Ensure `title` and `tags` are accurate and comprehensive.
    6.  **Final Review:** Read through the entire article one last time to catch any errors.
*   **Conditional Ingestion:** Only articles with `vetting_status: vetted` will be processed by the main data ingestion pipeline. This ensures that no unverified AI-generated content reaches the chatbot.

## 6. General Contribution Workflow
Follow these steps to contribute new manually-written content or update existing articles:

1.  **Identify a Need:** Determine if a new topic needs to be covered or an existing article requires updates/corrections. Check `cline_docs/currentTask.md` for content-related tasks.
2.  **Create/Locate File:**
    *   **New Article:** Create a new `.md` file in the `knowledge_base/` directory using the specified filename convention.
    *   **Existing Article:** Open the relevant file in `knowledge_base/`.
3.  **Use the Template:**
    *   For new, manually-written articles, start by copying the content of `knowledge_base/_template.md`. This ensures you include all required frontmatter fields and follow the standard article structure.
    *   For articles initiated by DeepSearch, use `knowledge_base/deep_research/_template_deepsearch.md` as your starting point, or ensure your generated file's frontmatter aligns with it.
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
    *   Commit your changes with a clear commit message (e.g., "feat(kb): add vetted article on MWEB via deepsearch" or "fix(kb): correct details in what-is-litecoin.md").
    *   Push your changes to your fork/branch.
    *   Open a Pull Request (PR) against the main project repository.
    *   In your PR description, briefly explain the purpose of your contribution and any specific areas reviewers should focus on. If it's a DeepSearch-originated article, mention this.

Thank you for helping build a high-quality knowledge resource for the Litecoin community!
