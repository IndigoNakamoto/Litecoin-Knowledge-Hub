# Litecoin Knowledge Hub

## Project Overview
The Litecoin RAG (Retrieval-Augmented Generation) Chatbot is an AI-powered conversational tool designed to serve the Litecoin community by providing real-time, accurate answers to a wide range of questions. Its core strength lies in retrieving information from a human-vetted, curated knowledge base managed by the Litecoin Foundation through Payload CMS. This ensures the information is not only accurate but also aligned with the Foundation's mission to combat misinformation and provide a single, trustworthy source for everything related to Litecoin. The chatbot aims to enhance user experience, foster greater adoption, and provide clear, reliable information about Litecoin's features, transaction management, development projects, and market insights.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin's features, transactions, or market trends.

## Project Status
The project has successfully completed the implementation of the core RAG pipeline, backend services, and is now actively migrating from Strapi CMS to Payload CMS. The current focus is on setting up Payload, defining content schemas, and integrating it with the RAG pipeline.

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

### Feature 6: Payload CMS Integration
A robust content management solution leveraging Payload CMS to ensure the quality, consistency, and accuracy of the Litecoin Knowledge Base. Payload provides superior database control and content-structuring flexibility, facilitating the creation, editing, and publishing of knowledge base articles with proper editorial workflows.

*   **Primary Goals:**
    *   Leverage Payload's flexible content types (collections) for optimal RAG pipeline compatibility.
    *   Implement foundation-controlled editorial workflows (Contributors create drafts, Foundation team publishes).
    *   Ensure seamless integration with existing RAG pipeline through the Payload REST/GraphQL API and `afterChange` hooks.
    *   Maintain content structure standards for hierarchical chunking.
*   **Current Status:** Migration in progress.

## Project Milestones
This project is organized into several key milestones. For detailed information on each milestone, please refer to the documents in the `cline_docs/milestones/` directory.

| Status | Milestone | Description |
| :---: | :--- | :--- |
| ✅ | [Milestone 1: Project Initialization](./cline_docs/milestones/milestone_1_project_initialization.md) | Initial project setup and core documentation. |
| ✅ | [Milestone 2: Basic Project Scaffold](./cline_docs/milestones/milestone_2_basic_project_scaffold.md) | Scaffolding for the Next.js frontend and FastAPI backend. |
| ✅ | [Milestone 3: Core RAG Pipeline](./cline_docs/milestones/milestone_3_core_rag_pipeline.md) | Implementation of the core data ingestion, retrieval, and generation pipeline. |
| ✅ | [Milestone 4: Backend & Knowledge Base Completion](./cline_docs/milestones/milestone_4_litecoin_basics_faq.md) | Full backend and data pipeline for MVP FAQ feature (Feature 1), including full knowledge base ingestion and advanced metadata filtering. |
| 📝 | [Milestone 5: Transaction & Block Explorer](./cline_docs/milestones/milestone_5_transaction_block_explorer.md) | MVP Feature 2: Feature for looking up transaction and block details. |
| 🟨 | [Milestone 6: AI-Integrated CMS (Payload CMS Integration)](./cline_docs/milestones/milestone_6_ai_integrated_cms.md) | MVP Feature 6: Integration with Payload CMS. Migration from Strapi in progress. |
| 📝 | [Milestone 7: Developer Documentation & Resources](./cline_docs/milestones/milestone_7_developer_documentation.md) | MVP Feature 4: Feature for providing access to developer resources. |
| 📝 | [Milestone 8: Testing, Refinement & Deployment](./cline_docs/milestones/milestone_8_testing_refinement_deployment.md) | Comprehensive testing, optimization, and deployment of all MVP features. |
| 📝 | [Milestone 9: Market Data & Insights](./cline_docs/milestones/milestone_9_market_data_insights.md) | MVP Feature 3: Feature for delivering real-time Litecoin market data. |

**Legend:**
*   ✅: Completed
*   🟨: In Progress
*   📝: Planned

## Technology Stack

*   **Frontend:**
    *   Framework: Next.js
    *   Styling: Tailwind CSS
    *   Language: TypeScript
*   **Backend:**
    *   Language: Python
    *   Framework: FastAPI
    *   RAG & LLM: Langchain (`langchain`, `langchain-core`, `langchain-community`), Google Text Embedding (`text-embedding-004`), `ChatGoogleGenerativeAI` (gemini-pro)
    *   Database Interaction: MongoDB (`pymongo`, `motor`)
    *   Payload Integration: Payload REST/GraphQL API, `afterChange` hook handling
    *   Data Handling: `python-frontmatter`
    *   Other Key Libraries: `requests`, `tweepy`, `GitPython`, `beautifulsoup4`, `lxml`
*   **Content Management:**
    *   CMS: Payload (self-hosted)
    *   Database: MongoDB
    *   Content Format: JSON
*   **Database:**
    *   Vector Storage: MongoDB Atlas Vector Search
    *   Content Storage: MongoDB (Payload CMS)
    *   General Data: MongoDB
*   **Deployment:**
    *   Frontend: Vercel
    *   Backend: TBD (e.g., Vercel Functions, Google Cloud Run, AWS Lambda)
    *   Payload CMS: Self-hosted (TBD platform)
*   **Testing:**
    *   Frontend: TBD (e.g., Jest, React Testing Library, Cypress)
    *   Backend: TBD (e.g., Pytest)
*   **Version Control:** Git (hosted on GitHub/GitLab - TBD)

For more details, see `cline_docs/techStack.md`.

## Project Structure
*   **Git Repository Root:** `Litecoin-Knowledge-Hub/`
*   `frontend/`: Next.js application.
    *   `src/app/`: Main application routes and pages.
    *   `src/components/`: Reusable React components.
    *   `src/lib/`: Utility libraries and configurations.
*   `backend/`: FastAPI application.
    *   `payload-cms/`: Contains the self-hosted Payload CMS application. This is the content authoring and management system.
    *   `payload_integration/`: Payload CMS integration modules.
    *   `data_ingestion/`: Modules for data loading, embedding, vector store management.
    *   `api/v1/`: API version 1 routers (chat, sources, sync).
    *   `main.py`: Main FastAPI application.
    *   `rag_pipeline.py`: Core RAG logic.
*   `knowledge_base/`:
*   `cline_docs/`: Project documentation.
*   `cline_agent_workspace/`: Cline's operational files.
*   `user_instructions/`: User-facing guides.
*   `reference_docs/`: Third-party documentation.

For a detailed overview, see `cline_docs/codebaseSummary.md`.

## Architecture Overview

The project utilizes a Next.js frontend, Python/FastAPI backend, and Payload CMS for content management. The architecture is centered around a **content-first RAG pipeline** with Payload CMS serving as the authoritative content source.

```mermaid
flowchart TD
    %% -------------------
    %% Node Definitions
    %% -------------------

    subgraph "User Interface"
        style UI fill:#D5E8D4,stroke:#82B366,color:#333,stroke-width:2px
        U("fa:fa-user User"):::uiStyle
        FE("fa:fa-window-maximize Next.js Frontend"):::uiStyle
    end

    subgraph "Application Backend (FastAPI)"
        style Backend fill:#DAE8FC,stroke:#6C8EBF,color:#333,stroke-width:2px
        API("fa:fa-cloud FastAPI Backend"):::backendStyle
        RAG("fa:fa-brain Langchain RAG Orchestrator"):::backendStyle
        LLM("fa:fa-robot LLM (e.g., Gemini Pro)"):::backendStyle
    end

    subgraph "Content Ingestion & Processing"
        style Ingestion fill:#FFE6CC,stroke:#D79B00,color:#333,stroke-width:2px
        SYNC("fa:fa-sync-alt Content Sync Service"):::ingestionStyle
        PROC("fa:fa-cogs Embedding Processor"):::ingestionStyle
        CHUNK("fa:fa-vector-square Hierarchical Chunking & Embedding"):::ingestionStyle
    end

    subgraph "Content Management System (Payload)"
        style CMS fill:#E6E0F8,stroke:#A094C4,color:#333,stroke-width:2px
        AUTHORS("fa:fa-users Foundation Team & Contributors"):::cmsStyle
        ADMIN("fa:fa-desktop Payload Admin Panel"):::cmsStyle
        PAYLOAD_DB("fa:fa-database Payload DB (MongoDB)"):::cmsStyle
        HOOK("fa:fa-bell Payload 'afterChange' Hook"):::cmsStyle
        PAYLOAD_API("fa:fa-code Payload REST/GraphQL API"):::cmsStyle
    end

    subgraph "Data Stores"
        style Storage fill:#F8CECC,stroke:#B85450,color:#333,stroke-width:2px
        VDB("fa:fa-layer-group Vector Store (MongoDB Atlas)"):::storageStyle
    end

    %% -------------------
    %% Connection Definitions
    %% -------------------

    %% Flow 1: Content Ingestion & Indexing
    AUTHORS -- "Create/Publish Content" --> ADMIN
    ADMIN -- "Saves to" --> PAYLOAD_DB
    ADMIN -- "On Publish/Update" --> HOOK
    HOOK -- "Triggers Sync Service" --> SYNC
    SYNC -- "Fetches full content via" --> PAYLOAD_API
    PAYLOAD_API -- "Returns Content" --> SYNC
    SYNC -- "Sends to Processor" --> PROC
    PROC -- "Parses & Chunks" --> CHUNK
    CHUNK -- "Embeds (text-embedding-004) & Stores" --> VDB

    %% Flow 2: User Query & RAG
    U -- "Submits Query" --> FE
    FE -- "Sends API Request" --> API
    API -- "Forwards to" --> RAG
    RAG -- "1 Embeds Query & Performs Vector Search" --> VDB
    VDB -- "2 Returns Relevant Context" --> RAG
    RAG -- "3 Constructs Prompt w/ Context" --> LLM
    LLM -- "4 Generates Response" --> RAG
    RAG -- "5 Returns Structured Answer" --> API
    API -- "Streams Response" --> FE
    FE -- "Displays Answer" --> U


    %% -------------------
    %% Class-Based Styling
    %% -------------------
    classDef uiStyle fill:#D5E8D4,stroke:#333,color:#333
    classDef backendStyle fill:#DAE8FC,stroke:#333,color:#333
    classDef ingestionStyle fill:#FFE6CC,stroke:#333,color:#333
    classDef cmsStyle fill:#E6E0F8,stroke:#333,color:#333
    classDef storageStyle fill:#F8CECC,stroke:#333,color:#333
```

## Content-First Approach with Payload CMS
This project emphasizes a **content-first strategy** powered by Payload CMS. The accuracy and reliability of the chatbot are directly tied to the quality of the information managed through Payload's editorial workflow. Payload CMS provides:

*   **Foundation-controlled editorial workflow**: Contributors create drafts, Foundation team reviews and publishes.
*   **Flexible Content Types (Collections)**: Customizable content structures are ideal for RAG.
*   **Robust REST/GraphQL API**: Comprehensive access to content and metadata.
*   **`afterChange` hook system**: Real-time synchronization with the RAG pipeline.
*   **Professional Admin Panel**: A powerful interface for content management.

The Payload CMS serves as the "golden source" for the RAG pipeline, providing greater data control and flexibility.

## Getting Started

### Prerequisites
*   **Node.js:** Version 18.18.0 or newer (managed via nvm is recommended).
*   **npm:** Node package manager (comes with Node.js).
*   **Python:** Version 3.x.
*   **pip:** Python package installer (comes with Python).
*   **Virtual Environment:** Recommended for Python projects.
*   **Payload CMS:** Self-hosted Payload instance with REST/GraphQL API access.
*   **MongoDB:** Database for Payload CMS.

### Running Development Servers

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
    Open your web browser and go to `http://localhost:3000`. You should see the Litecoin RAG Chat interface.

#### Backend (FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # .\venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    ```bash
    cp .env.example .env
    # Edit .env with your Payload API URL, tokens, and other credentials
    ```

5.  **Run the development server:**
    ```bash
    uvicorn main:app --reload
    ```
    The FastAPI development server should start, typically on `http://localhost:8000`.

### Payload CMS Setup

1.  **Install Payload CMS** following the official documentation.
2.  **Configure API Tokens** in Payload Admin → Settings → API Tokens (or similar).
3.  **Set up `afterChange` hooks** for content synchronization with the RAG pipeline.
4.  **Configure user roles** (Contributors for community, Editors/Admins for Foundation).

### Running Data Ingestion from Payload

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Run Payload content ingestion:**
    ```bash
    python ingest_data.py --source-type payload
    ```

3.  **Verify:**
    Confirm content is processed and vectors are stored in MongoDB Atlas.

## Security Considerations
*   Input validation for all user queries and API inputs.
*   Protection against common web vulnerabilities (OWASP Top 10).
*   Secure handling of API keys and credentials (not hardcoded).
*   Payload CMS authentication and authorization for content management.
*   `afterChange` hook security for Payload-to-RAG synchronization.

## Documentation
The project's core documentation is maintained in the `cline_docs/` directory:
*   `projectRoadmap.md`: High-level project vision, goals, architecture, and major milestones.
*   `currentTask.md`: Details active tasks, backlog, progress, and immediate development plan.
*   `techStack.md`: Documents all technology choices, frameworks, tools, and their rationale.
*   `codebaseSummary.md`: Provides an overview of the project's structure, key components, data flow, and dependencies.

## Contributing
This project thrives on community contributions to its knowledge base through Payload CMS. The Litecoin Foundation maintains editorial control while enabling community participation.

### Content Contribution Process
1.  **Request Contributor Access**: Contact the Litecoin Foundation for Payload CMS contributor credentials.
2.  **Create Draft Content**: Use Payload's rich text editor to create well-structured articles.
3.  **Foundation Review**: The Foundation team reviews and publishes approved content.
4.  **Automatic Sync**: Published content automatically updates the RAG pipeline.

For detailed guidelines on content structure and submission, see the Payload CMS editorial guidelines (to be provided by Foundation team).

## License
(To be determined - e.g., MIT License)
