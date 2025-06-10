# Litecoin RAG Chat

## Project Overview
The Litecoin RAG (Retrieval-Augmented Generation) Chatbot is an AI-powered conversational tool designed to serve the Litecoin community by providing real-time, accurate answers to a wide range of questions. Its core strength lies in retrieving information from a human-vetted, curated knowledge base managed by the Litecoin Foundation. This ensures the information is not only accurate but also aligned with the Foundation's mission to combat misinformation and provide a single, trustworthy source for everything related to Litecoin. The chatbot aims to enhance user experience, foster greater adoption, and provide clear, reliable information about Litecoin's features, transaction management, development projects, and market insights.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.

## Project Status
The project has successfully completed:
*   **Core RAG Pipeline Implementation** (Milestone 3).
*   **Backend & Knowledge Base Completion** (Milestone 4).
*   **AI-Integrated Knowledge Base CMS Development - Phase 1: Core Setup & Basic Content Management (`CMS-IMP-001`)** (Milestone 6, Phase 1).

The project is currently focused on **Milestone 6: AI-Integrated Knowledge Base CMS Development - Phase 2: Semantic Search Implementation (`CMS-IMP-002`)**.

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

### Feature 6: AI-Integrated Knowledge Base CMS
A foundational component of the content strategy, this Content Management System (CMS) is designed to ensure the quality, consistency, and accuracy of the Litecoin Knowledge Base. It facilitates the creation, editing, vetting, publishing, and archiving of knowledge base articles, integrating AI assistance to streamline workflows.
*   **Primary Goals:**
    *   Enforce strict content structure for optimal RAG pipeline performance.
    *   Provide a user-friendly editor (Tiptap with React Hook Form).
    *   Ensure data integrity with schema-driven validation (Zod).
    *   Seamlessly integrate with the Next.js frontend and backend ingestion pipeline.
*   **Current Status:** Phase 1 (Core Setup & Basic Content Management) is complete. Phase 2 (Semantic Search Implementation) is in progress.

## Project Milestones
This project is organized into several key milestones. For detailed information on each milestone, please refer to the documents in the `cline_docs/milestones/` directory.

| Status | Milestone | Description |
| :---: | :--- | :--- |
| ✅ | [Milestone 1: Project Initialization](./cline_docs/milestones/milestone_1_project_initialization.md) | Initial project setup and core documentation. |
| ✅ | [Milestone 2: Basic Project Scaffold](./cline_docs/milestones/milestone_2_basic_project_scaffold.md) | Scaffolding for the Next.js frontend and FastAPI backend. |
| ✅ | [Milestone 3: Core RAG Pipeline](./cline_docs/milestones/milestone_3_core_rag_pipeline.md) | Implementation of the core data ingestion, retrieval, and generation pipeline. |
| ✅ | [Milestone 4: Backend & Knowledge Base Completion](./cline_docs/milestones/milestone_4_litecoin_basics_faq.md) | Full backend and data pipeline for MVP FAQ feature, including full knowledge base ingestion and advanced metadata filtering. |
| 📝 | [Milestone 5: Transaction & Block Explorer](./cline_docs/milestones/milestone_5_transaction_block_explorer.md) | Feature for looking up transaction and block details. |
| 🟨 | [Milestone 6: AI-Integrated Knowledge Base CMS Development](./cline_docs/milestones/milestone_6_market_data_insights.md) | Development of the CMS. Phase 1 (Core Setup & Basic Content Management) ✅. Phase 2 (Semantic Search & RAG Sync) ⏳. Phase 3 (Refinement & Advanced Features) 📝. |
| 📝 | [Milestone 7: Developer Documentation](./cline_docs/milestones/milestone_7_developer_documentation.md) | Feature for providing access to developer resources. |
| 📝 | [Milestone 8: Testing, Refinement & Deployment](./cline_docs/milestones/milestone_8_testing_refinement_deployment.md) | Comprehensive testing, optimization, and deployment. |

**Legend:**
*   ✅: Completed
*   🟨: In Progress
*   📝: Planned

## Technology Stack

*   **Frontend:**
    *   Framework: Next.js
    *   Styling: Tailwind CSS
    *   UI Libraries: ShadCN
    *   Form Management (CMS): React Hook Form with Zod
    *   Rich Text Editor (CMS): Tiptap
    *   Language: TypeScript
*   **Backend:**
    *   Language: Python
    *   Framework: FastAPI
    *   RAG & LLM: Langchain (`langchain`, `langchain-core`, `langchain-community`), Google Text Embedding (`text-embedding-004`), `ChatGoogleGenerativeAI` (gemini-pro)
    *   Database Interaction: MongoDB (`pymongo`, `motor`)
    *   Authentication (CMS): `fastapi-users`, `jose`, `passlib`
    *   Data Handling: `python-frontmatter`
    *   Other Key Libraries: `requests`, `tweepy`, `GitPython`, `beautifulsoup4`, `lxml`
*   **Database:**
    *   Type: MongoDB
    *   Usage: Vector storage (MongoDB Atlas Vector Search), general application data, CMS content.
*   **Deployment:**
    *   Frontend: Vercel
    *   Backend: TBD (e.g., Vercel Functions, Google Cloud Run, AWS Lambda)
*   **Testing:**
    *   Frontend: TBD (e.g., Jest, React Testing Library, Cypress)
    *   Backend: TBD (e.g., Pytest)
*   **Version Control:** Git (hosted on GitHub/GitLab - TBD)

For more details, see `cline_docs/techStack.md`.

## Project Structure
*   **Git Repository Root:** `Litecoin-RAG-Chat/`
*   `frontend/`: Next.js application.
    *   `src/app/(cms)/`: CMS-specific routes (dashboard, editor).
    *   `src/components/cms/`: CMS-specific React components (`ArticleEditor.tsx`, `FrontmatterForm.tsx`, `TiptapEditor.tsx`).
    *   `src/lib/zod/articleSchema.ts`: Zod schema for CMS article validation.
    *   `src/contexts/AuthContext.tsx`: Manages JWT tokens for CMS authentication.
*   `backend/`: FastAPI application.
    *   `cms/`: Modules for CMS backend (articles, users, auth).
    *   `data_ingestion/`: Modules for data loading, embedding, vector store management.
    *   `api/v1/`: API version 1 routers (chat, sources, articles).
    *   `main.py`: Main FastAPI application.
    *   `rag_pipeline.py`: Core RAG logic.
*   `knowledge_base/`: Curated Markdown articles.
    *   `articles/`
    *   `deep_research/`
    *   `_template.md`
*   `cline_docs/`: Project documentation.
*   `cline_agent_workspace/`: Cline's operational files.
*   `user_instructions/`: User-facing guides.
*   `reference_docs/`: Third-party documentation.

For a detailed overview, see `cline_docs/codebaseSummary.md`.

## Architecture Overview

The project utilizes a Next.js frontend and a Python/FastAPI backend. The architecture is centered around a **content-first RAG pipeline**, where a curated knowledge base is ingested to provide context for the LLM, ensuring responses are grounded in verified information.

```mermaid
graph TD
    A[Raw Data Sources: GitHub, Docs, Articles] -->|Research & Synthesis| B(Human Curation & Writing);
    B -->|Structured for AI| C[Curated Knowledge Base: 'Golden' Articles in Markdown];
    C -->|ingest_data.py| D[RAG Pipeline: Hierarchical Chunking (Markdown) / Text Splitting & Embedding with 'retrieval_document' task_type];
    D --> E[MongoDB Vector Store];
    F[User Query] -->|Embed with 'retrieval_query' task_type| G[API Backend];
    G -->|Similarity Search| E;
    E -->|Retrieve Context| G;
    G -->|Generate Answer| H[LLM];
    H --> G;
    G --> I[Chatbot Response];
end
```

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

This document provides instructions to run the Next.js frontend and FastAPI backend development servers to access the functional chat interface.

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
    Open your web browser and go to `http://localhost:3001`. You should see the Litecoin RAG Chat interface.

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

## Security Considerations
*   Input validation for all user queries and API inputs.
*   Protection against common web vulnerabilities (OWASP Top 10).
*   Secure handling of API keys and credentials (not hardcoded).
*   Authentication and authorization for CMS functionalities.

## Documentation
The project's core documentation is maintained in the `cline_docs/` directory:
*   `projectRoadmap.md`: High-level project vision, goals, architecture, and major milestones.
*   `currentTask.md`: Details active tasks, backlog, progress, and Cline's immediate plan.
*   `techStack.md`: Documents all technology choices, frameworks, tools, and their rationale.
*   `codebaseSummary.md`: Provides an overview of the project's structure, key components, data flow, and dependencies.

## Contributing
This project thrives on community contributions, especially to its core knowledge base. To ensure quality and consistency, we have a structured contribution process.

For detailed instructions on how to contribute articles to the knowledge base, including topic selection, article structure, frontmatter requirements, and the submission process, please see the **[Knowledge Base Contribution Guide](./user_instructions/knowledge_base_contribution_guide.md)**.

## License
(To be determined - e.g., MIT License)
