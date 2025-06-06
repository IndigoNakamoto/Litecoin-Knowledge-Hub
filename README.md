# Litecoin RAG Chat

## Project Overview
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from trusted open-source sources. It aims to solve the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.

## Project Status
The project is currently in the **Core RAG Pipeline Implementation** phase (Milestone 3). We are actively working on `RAG-001: Implement Data Ingestion and MongoDB Vector Store Setup`, which is a critical step towards building our knowledge base for the RAG chatbot.

## Key Features

### Feature 1: Litecoin Basics & FAQ
Provides clear, concise answers to fundamental questions about Litecoin, its history, how it works, and common terminology. Caters especially to new users.

### Feature 2: Transaction & Block Explorer
Allows users to look up details of Litecoin transactions (e.g., status, confirmations, fees) using a transaction ID, and explore block information (e.g., height, timestamp, included transactions).

### Feature 3: Market Data & Insights
Delivers real-time Litecoin price information, market capitalization, trading volume, and basic chart data from reliable market APIs.

### Feature 4: Developer Documentation & Resources
Provides quick access to snippets from Litecoin developer documentation, links to key resources, and answers to common technical questions for developers building on Litecoin.

## Milestones

### Completed Milestones

#### Milestone 1: Project Initialization & Documentation Setup
*   **Description:** This milestone covered the initial setup of the project, including defining the project scope, objectives, key features, and setting up the core documentation structure in `cline_docs`.
*   **Key Tasks:** Define Project Scope & Objectives, Outline Key Features & User Stories, Establish Architectural Overview & Patterns, Document Core Technology Decisions, Identify Significant Constraints, Define High-Level Security Requirements, Set up `cline_docs` with `projectRoadmap.md`, `currentTask.md`, `techStack.md`, and `codebaseSummary.md`.
*   **Status:** Completed (6/5/2025)
*   **Dependencies:** None
*   **Estimated Time:** 3 hours

#### Milestone 2: Basic Project Scaffold
*   **Description:** This milestone involved setting up the basic project structure for both the frontend (Next.js) and backend (Python/FastAPI) components. This included initializing the applications, setting up basic configurations, and ensuring they can run.
*   **Key Tasks:** Initialize Next.js frontend application, Initialize FastAPI backend application, Set up basic folder structures for both frontend and backend, Configure basic dependencies, Ensure both frontend and backend servers can start.
*   **Status:** Completed (6/5/2025)
*   **Dependencies:** Milestone 1
*   **Estimated Time:** 4 hours

### In Progress Milestones

#### Milestone 3: Core RAG Pipeline Implementation
*   **Description:** This milestone focuses on building the foundational Retrieval-Augmented Generation (RAG) pipeline. This includes setting up the Langchain framework, integrating with MongoDB Atlas for vector search, configuring the Google Text Embedding model, and implementing the initial data ingestion process.
*   **Key Tasks:** Set up Langchain project structure, Integrate Google Text Embedding 004 model, Configure MongoDB Atlas Vector Search for vector storage and retrieval, Develop initial data ingestion scripts for basic text data, Implement the core retrieval mechanism, Set up the LLM integration for generation.
*   **Status:** In Progress (Initial Langchain setup completed)
*   **Dependencies:** Milestone 1, Milestone 2
*   **Estimated Time:** 40 hours (1 hour so far)

### Upcoming Milestones

#### Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
*   **Description:** This milestone focuses on implementing the first core feature: providing answers to fundamental questions about Litecoin. This involves developing the frontend chat interface, integrating it with the RAG backend, and ensuring the RAG pipeline can accurately retrieve and generate responses for basic Litecoin queries. It also includes the curation and ingestion of relevant FAQ data.
*   **Key Tasks:** Develop the frontend chat UI components, Integrate frontend with the FastAPI backend for query submission and response display, Identify and curate reliable open-source data for Litecoin basics and FAQs, Implement data ingestion for FAQ content into the vector store, Refine RAG pipeline for accurate retrieval and generation of FAQ answers.
*   **Status:** Planned
*   **Dependencies:** Milestone 3
*   **Estimated Time:** 30 hours

#### Milestone 5: MVP Feature 2 Implementation (Transaction & Block Explorer)
*   **Description:** This milestone focuses on implementing the transaction and block explorer feature. This involves integrating the RAG system with Litecoin blockchain explorers or direct node APIs to retrieve and display detailed information about transactions and blocks. This will require robust data parsing and formatting to present complex blockchain data in an understandable way.
*   **Key Tasks:** Research and select reliable Litecoin blockchain explorer APIs or consider direct node interaction, Implement backend logic to fetch transaction details by ID (status, confirmations, fees), Implement backend logic to fetch block information by height (timestamp, included transactions), Integrate fetched blockchain data into the RAG pipeline for contextual answers, Develop frontend components to display transaction and block information clearly, Implement input validation for transaction IDs and block heights.
*   **Status:** Planned
*   **Dependencies:** Milestone 3, Milestone 4
*   **Estimated Time:** 50 hours

#### Milestone 6: MVP Feature 3 Implementation (Market Data & Insights)
*   **Description:** This milestone focuses on implementing the market data and insights feature. This involves integrating the RAG system with reliable cryptocurrency market data APIs to retrieve real-time Litecoin price, market capitalization, and trading volume. The goal is to present this dynamic data clearly and concisely to users.
*   **Key Tasks:** Research and select reliable cryptocurrency market data APIs (e.g., CoinGecko, CoinMarketCap), Implement backend logic to fetch real-time Litecoin price, Implement backend logic to fetch Litecoin market capitalization and trading volume, Integrate fetched market data into the RAG pipeline for contextual answers, Develop frontend components to display market data effectively, Consider basic chart data integration if feasible within the estimated time.
*   **Status:** Planned
*   **Dependencies:** Milestone 3, Milestone 4
*   **Estimated Time:** 35 hours

#### Milestone 7: MVP Feature 4 Implementation (Developer Documentation & Resources)
*   **Description:** This milestone focuses on implementing the developer documentation and resources feature. This involves ingesting relevant Litecoin developer documentation into the RAG system, creating a searchable index, and enabling the system to provide accurate code snippets, links to key resources, and answers to common technical questions for developers.
*   **Key Tasks:** Identify and curate official Litecoin developer documentation and key resources (e.g., GitHub repos, LIPs), Implement data ingestion for developer documentation, potentially handling various formats (Markdown, PDF, etc.), Optimize embedding and retrieval for technical content, including code snippets, Refine RAG pipeline to accurately answer developer-centric queries, Develop frontend components to display technical answers and links clearly.
*   **Status:** Planned
*   **Dependencies:** Milestone 3, Milestone 4
*   **Estimated Time:** 45 hours

#### Milestone 8: Testing, Refinement & Deployment
*   **Description:** This final MVP milestone focuses on ensuring the quality, performance, and deployability of the Litecoin RAG Chat. It includes comprehensive testing across all implemented features, bug fixing, performance optimizations, security audits, and setting up the continuous integration/continuous deployment (CI/CD) pipeline for production deployment.
*   **Key Tasks:** Develop and execute unit tests for backend and frontend components, Develop and execute integration tests for the RAG pipeline and API endpoints, Develop and execute end-to-end tests for user flows, Conduct thorough bug fixing and issue resolution, Perform performance profiling and optimization for the RAG pipeline and API, Conduct security audits and implement necessary fixes (e.g., input validation, API key management), Set up CI/CD pipelines for automated testing and deployment, Prepare deployment configurations for Vercel (frontend) and a suitable platform for FastAPI (backend), Finalize documentation and user guides.
*   **Status:** Planned
*   **Dependencies:** Milestone 3, Milestone 4, Milestone 5, Milestone 6, Milestone 7
*   **Estimated Time:** 60 hours

## Technology Stack
*   **Frontend:** Next.js, Tailwind CSS
*   **Backend:** Python, FastAPI, Langchain (`langchain`, `langchain-core`, `langchain-community`), Google Text Embedding (`text-embedding-004`), MongoDB libraries (`pymongo`, `motor`)
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

If you encounter any issues, please check the terminal output for error messages.

## Documentation
The project's core documentation is maintained in the `cline_docs/` directory:
*   `projectRoadmap.md`: High-level project vision, goals, architecture, and major milestones.
*   `currentTask.md`: Details active tasks, backlog, progress, and Cline's immediate plan.
*   `techStack.md`: Documents all technology choices, frameworks, tools, and their rationale.
*   `codebaseSummary.md`: Provides an overview of the project's structure, key components, data flow, and dependencies.

## Contributing
(Contribution guidelines will be added here.)

## License
(License information will be added here.)
