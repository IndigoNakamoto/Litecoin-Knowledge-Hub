# Litecoin RAG Chat

## Project Overview
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin. Its core strength lies in retrieving relevant data from a **human-vetted, curated knowledge base**, ensuring high accuracy and reliability. It aims to solve the problem of misinformation and scattered resources by offering a centralized, trustworthy way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.

## Project Status
The project has successfully completed the **Core RAG Pipeline Implementation** (Milestone 3). The core RAG pipeline is now functional, capable of ingesting data from multiple sources, retrieving relevant information, and generating answers with source attribution.

The project is currently focused on **Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)**.

## Key Features

### Feature 1: Litecoin Basics & FAQ
Provides clear, concise answers to fundamental questions about Litecoin, its history, how it works, and common terminology. Caters especially to new users.

### Feature 2: Transaction & Block Explorer
Allows users to look up details of Litecoin transactions (e.g., status, confirmations, fees) using a transaction ID, and explore block information (e.g., height, timestamp, included transactions).

### Feature 3: Market Data & Insights
Delivers real-time Litecoin price information, market capitalization, trading volume, and basic chart data from reliable market APIs.

### Feature 4: Developer Documentation & Resources
Provides quick access to snippets from Litecoin developer documentation, links to key resources, and answers to common technical questions for developers building on Litecoin.

### Feature 5: Curated Knowledge Base
A continuously updated library of well-researched, clearly written articles and data covering all aspects of Litecoin. This content is explicitly structured for optimal machine retrieval and serves as the primary source for the chatbot's answers.

## Project Milestones
This project is organized into several key milestones. For detailed information on each milestone, please refer to the documents in the `cline_docs/milestones/` directory.

| Status | Milestone | Description |
| :---: | :--- | :--- |
| ✅ | [Milestone 1: Project Initialization](./cline_docs/milestones/milestone_1_project_initialization.md) | Initial project setup and core documentation. |
| ✅ | [Milestone 2: Basic Project Scaffold](./cline_docs/milestones/milestone_2_basic_project_scaffold.md) | Scaffolding for the Next.js frontend and FastAPI backend. |
| ✅ | [Milestone 3: Core RAG Pipeline](./cline_docs/milestones/milestone_3_core_rag_pipeline.md) | Implementation of the core data ingestion, retrieval, and generation pipeline. |
| ⏳ | [Milestone 4: Litecoin Basics & FAQ](./cline_docs/milestones/milestone_4_litecoin_basics_faq.md) | Implementing the first core feature for basic questions. |
| 📝 | [Milestone 5: Transaction & Block Explorer](./cline_docs/milestones/milestone_5_transaction_block_explorer.md) | Feature for looking up transaction and block details. |
| 📝 | [Milestone 6: Market Data & Insights](./cline_docs/milestones/milestone_6_market_data_insights.md) | Feature for delivering real-time market data. |
| 📝 | [Milestone 7: Developer Documentation](./cline_docs/milestones/milestone_7_developer_documentation.md) | Feature for providing access to developer resources. |
| 📝 | [Milestone 8: Testing, Refinement & Deployment](./cline_docs/milestones/milestone_8_testing_refinement_deployment.md) | Comprehensive testing, optimization, and deployment. |

**Legend:**
*   ✅: Completed
*   ⏳: In Progress
*   📝: Planned

## Technology Stack
*   **Frontend:** Next.js, Tailwind CSS
*   **Backend:** Python, FastAPI, Langchain (`langchain`, `langchain-core`, `langchain-community`), Google Text Embedding (`text-embedding-004`), MongoDB libraries (`pymongo`, `motor`), `requests`, `tweepy`, `GitPython`, `beautifulsoup4`, `lxml`
*   **Database:** MongoDB (for vector storage and general data)
*   **Deployment:** Vercel (for frontend)

## Project Structure
*   **Git Repository Root:** `Litecoin-RAG-Chat/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend.
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
*   `backend/`: Contains the FastAPI application.
    *   `data_ingestion/`: Contains modules for data loading, embedding, and vector store management.
    *   `main.py`: Main FastAPI application file.
    *   `requirements.txt`: Python dependencies.
    *   `rag_pipeline.py`: Encapsulates Langchain-related logic for the RAG pipeline.
*   `cline_docs/`: Contains project documentation.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `user_instructions/`: Contains instructions for the user.
*   `knowledge_base/`: Contains the curated, human-vetted articles that form the primary source of truth for the RAG system.

## Content-First Approach
This project emphasizes a **content-first strategy**. The accuracy and reliability of the chatbot are directly tied to the quality of the information in its `knowledge_base/`. This directory houses meticulously researched, well-structured Markdown articles covering various Litecoin topics. These articles are the "golden source" for the RAG pipeline.

While the system can ingest data from other sources (web, GitHub, etc.), the primary focus for high-quality, trusted answers will always be the content within `knowledge_base/`.

## Getting Started

### Prerequisites
*   **Node.js:** Version 18.18.0 or newer (managed via nvm is recommended).
*   **npm:** Node package manager (comes with Node.js).
*   **Python:** Version 3.x.
*   **pip:** Python package installer (comes with Python).
*   **Virtual Environment:** Recommended for Python projects.

### Running Development Servers

This document provides instructions to run the Next.js frontend and FastAPI backend development servers to verify the "Hello World" setups.

#### Frontend (Next.js)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The Next.js development server should start, typically on `http://localhost:3000`.

3.  **Verify:**
    Open your web browser and go to `http://localhost:3000`. You should see the default Next.js "Welcome" page.

    **Note on Node.js Version:** During the `create-next-app` process, warnings related to your Node.js version (v18.17.0) were observed, as some dependencies expected v18.18.0 or newer. While the scaffolding was successful, consider upgrading Node.js to the latest LTS version (>=18.18.0) at your convenience to prevent potential issues later.

#### Backend (FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment (recommended):**
    *   Create the environment:
        ```bash
        python3 -m venv venv
        ```
    *   Activate the environment:
        *   On macOS/Linux:
            ```bash
            source venv/bin/activate
            ```
        *   On Windows:
            ```bash
            .\venv\Scripts\activate
            ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the development server:**
    ```bash
    uvicorn main:app --reload
    ```
    The FastAPI development server should start, typically on `http://localhost:8000`.

5.  **Verify:**
    Open your web browser or a tool like Postman and go to `http://localhost:8000/`. You should see a JSON response:
    ```json
    {"message":"Hello World"}
    ```

### Running Data Ingestion

The `ingest_data.py` script has been refactored to support multiple data sources. You can specify the source type and identifier using command-line arguments.

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Activate your virtual environment** (if you haven't already):
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```

3.  **Ensure MongoDB Atlas Vector Search index is set up** as per `user_instructions/setup_mongodb_vector_index.md`.

4.  **Run the ingestion script with desired source:**

    *   **Litecoin Docs (Sample):**
        ```bash
        python ingest_data.py --source_type litecoin_docs --source_identifier data_ingestion/sample_litecoin_docs.md
        ```
    *   **YouTube (via Citeio API):**
        ```bash
        python ingest_data.py --source_type youtube --source_identifier "https://www.youtube.com/watch?v=your_video_id"
        ```
        (Replace `your_video_id` with an actual YouTube video ID)
    *   **Twitter (X) Posts:**
        ```bash
        python ingest_data.py --source_type twitter --source_identifier "litecoin,satoshi"
        ```
        (Replace `litecoin,satoshi` with comma-separated Twitter handles)
    *   **GitHub Repository (Markdown files):**
        ```bash
        python ingest_data.py --source_type github --source_identifier "https://github.com/litecoin-project/litecoin"
        ```
        (Replace with a valid GitHub repository URL)
    *   **Web Article:**
        ```bash
        python ingest_data.py --source_type web_article --source_identifier "https://litecoin.com/en/"
        ```
        (Replace with a valid web article URL)

5.  **Verify:**
    Confirm the script runs successfully and data is populated in your MongoDB Atlas collection.

    **Prioritizing Curated Content:**
    For the highest quality results, especially for the "Litecoin Basics & FAQ" feature, prioritize ingesting content from the `knowledge_base/` directory:
    ```bash
    python ingest_data.py --source_type markdown --source_identifier ../knowledge_base
    ```
    (This assumes you are in the `backend/` directory. Adjust the path if necessary.)

If you encounter any issues, please check the terminal output for error messages.

## Documentation
The project's core documentation is maintained in the `cline_docs/` directory:
*   `projectRoadmap.md`: High-level project vision, goals, architecture, and major milestones.
*   `currentTask.md`: Details active tasks, backlog, progress, and Cline's immediate plan.
*   `techStack.md`: Documents all technology choices, frameworks, tools, and their rationale.
*   `codebaseSummary.md`: Provides an overview of the project's structure, key components, data flow, and dependencies.

## Contributing

### How to Contribute to the Knowledge Base

The Litecoin RAG Chat aims to be the most reliable and accurate source of information for Litecoin. This is achieved through a "content-first" strategy, where all information in the `knowledge_base/` directory is human-vetted and structured for optimal AI processing.

**1. Core Principles for Content:**
*   **Objectivity:** Present factual information without bias.
*   **Accuracy:** All statements must be thoroughly researched and verifiable, citing primary sources where possible.
*   **Clarity:** Write for a broad audience, explaining complex concepts simply without sacrificing technical correctness. Define jargon on first use.
*   **Conciseness:** Be clear and to the point, avoiding unnecessary verbosity.

**2. Article Structure:**
All articles must adhere to a strict structure for consistency and optimal RAG pipeline processing:
*   **Filename:** Use lowercase, hyphen-separated words (e.g., `what-is-mweb.md`).
*   **Frontmatter (YAML):** Every article must begin with YAML frontmatter enclosed in `---`. Refer to `knowledge_base/_template.md` for required fields (`title`, `id`, `category`, `tags`, `summary`, `last_updated`, `author`, `source`, `language`, `relevance_score`).
*   **Headings:**
    *   Exactly one Level 1 Heading (`# Main Title`), matching the `title` in frontmatter.
    *   Use Level 2 (`## Section`) and Level 3 (`### Subsection`) headings for logical content structure. This hierarchical structure is crucial for the AI's contextual understanding during retrieval.

**3. Content Formatting and Style:**
*   **Markdown:** Use standard Markdown.
*   **Links:** Use descriptive text (e.g., `[Litecoin Improvement Proposals](URL)`).
*   **Code Snippets:** Use backticks (`` `inline code` ``) and triple backticks for code blocks (```language\ncode\n```).
*   **Lists, Emphasis, Blockquotes, Tables:** Use standard Markdown syntax.

**4. Using AI Tools (e.g., DeepSearch) for Initial Drafts:**
AI tools can accelerate content creation, but drafts **must** undergo rigorous human vetting.
*   **Placement:** Place AI-initiated drafts in `knowledge_base/deep_research/`.
*   **Prompt Engineering:** Craft precise prompts to guide the AI.
*   **Mandatory Frontmatter:** Include all standard frontmatter fields from `knowledge_base/_template.md` and additional DeepSearch-specific fields from `knowledge_base/deep_research/_template_deepsearch.md` (e.g., `source_type`, `original_deepsearch_query`, `vetting_status`, `vetter_name`, `vetting_date`).
*   **Human Vetting Process (CRITICAL):**
    1.  **Selection:** Pick a `draft` article.
    2.  **Verification:** Cross-check all facts against trusted primary sources.
    3.  **Correction & Enhancement:** Correct inaccuracies, fill gaps, rewrite for clarity, and ensure objectivity.
    4.  **Structuring for RAG:** Ensure adherence to heading structure and formatting.
    5.  **Metadata Update:** Change `vetting_status` to `vetted`, fill `vetter_name`, `vetting_date`, and update `last_updated`.
*   **Conditional Ingestion:** Only articles with `vetting_status: vetted` are processed by the main data ingestion pipeline.

**5. General Contribution Workflow:**
1.  **Identify a Need:** Determine new topics or updates needed. Consult `knowledge_base/index.md` for a categorized list of articles to write and fill out.
2.  **Create/Locate File:** Create a new `.md` file in `knowledge_base/articles/` or `knowledge_base/deep_research/` (depending on origin) or open an existing one.
3.  **Use the Template:** Copy `knowledge_base/_template.md` for new articles, or ensure DeepSearch drafts align with `knowledge_base/deep_research/_template_deepsearch.md`.
4.  **Write/Edit Content:** Adhere to all guidelines.
5.  **Local Verification (Recommended):** Run `python ingest_data.py --source_type markdown --source_identifier ../knowledge_base` from `backend/` to check for parsing errors.
6.  **Submit for Review:** Commit changes with a clear message, push to your branch, and open a Pull Request (PR) against the main repository. Explain your contribution in the PR description.

This detailed process ensures the knowledge base remains a high-quality, reliable resource for the Litecoin RAG Chat.
## License
(License information will be added here.)
