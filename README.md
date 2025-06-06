# Litecoin RAG Chat

## Project Overview
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from verified sources. It aims to solve the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.

## Project Status
The project is currently in the **Core RAG Pipeline Implementation** phase (Milestone 3). The multi-source data ingestion framework and the core retrieval mechanism have been successfully implemented and tested. We are now focusing on the generation component.

## Key Features

### Feature 1: Litecoin Basics & FAQ
Provides clear, concise answers to fundamental questions about Litecoin, its history, how it works, and common terminology. Caters especially to new users.

### Feature 2: Transaction & Block Explorer
Allows users to look up details of Litecoin transactions (e.g., status, confirmations, fees) using a transaction ID, and explore block information (e.g., height, timestamp, included transactions).

### Feature 3: Market Data & Insights
Delivers real-time Litecoin price information, market capitalization, trading volume, and basic chart data from reliable market APIs.

### Feature 4: Developer Documentation & Resources
Provides quick access to snippets from Litecoin developer documentation, links to key resources, and answers to common technical questions for developers building on Litecoin.

## Project Milestones
This project is organized into several key milestones. For detailed information on each milestone, please refer to the documents in the `cline_docs/milestones/` directory.

| Status | Milestone | Description |
| :---: | :--- | :--- |
| ✅ | [Milestone 1: Project Initialization](./cline_docs/milestones/milestone_1_project_initialization.md) | Initial project setup and core documentation. |
| ✅ | [Milestone 2: Basic Project Scaffold](./cline_docs/milestones/milestone_2_basic_project_scaffold.md) | Scaffolding for the Next.js frontend and FastAPI backend. |
| ⏳ | [Milestone 3: Core RAG Pipeline](./cline_docs/milestones/milestone_3_core_rag_pipeline.md) | Implementation of the core data ingestion, retrieval, and generation pipeline. |
| 📝 | [Milestone 4: Litecoin Basics & FAQ](./cline_docs/milestones/milestone_4_litecoin_basics_faq.md) | Implementing the first core feature for basic questions. |
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
