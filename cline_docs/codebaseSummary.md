# Codebase Summary: Litecoin RAG Chat

## High-Level Directory Structure Overview
*   **Git Repository Root:** `Litecoin-RAG-Chat/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend, with rules correctly scoped for the monorepo structure (e.g., `frontend/node_modules/`).
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
*   `backend/`: Contains the FastAPI application.
    *   `main.py`: Main FastAPI application file.
    *   `requirements.txt`: Python dependencies.
    *   `rag_pipeline.py`: Encapsulates Langchain-related logic for the RAG pipeline.
*   `cline_docs/`: Contains project documentation.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `user_instructions/`: Contains instructions for the user.

## Key Modules/Components & Their Responsibilities
*   `backend/rag_pipeline.py`: Contains the core logic for the RAG (Retrieval-Augmented Generation) pipeline, including the definition and orchestration of Langchain chains.
*   `backend/main.py`: The main entry point for the FastAPI backend, responsible for defining API endpoints and handling incoming requests.

## Core Data Models & Entities
*   (Not yet established - will likely include models for Litecoin data, user queries, RAG sources, etc.)

## Critical Data Flow Diagrams
*   (Not yet established - will involve user query -> RAG system -> LLM -> response. Mermaid syntax will be preferred for diagrams when defined.)

## API Endpoints Overview
*   **`POST /api/v1/chat`**:
    *   **Description**: Receives a user query and processes it through the RAG pipeline.
    *   **Request Body**: `{"query": "string"}`
    *   **Response Body**: `{"response": "string"}`

## External Services & Dependencies
*   Google Text Embedding API (text-embedding-004)
*   Litecoin blockchain data sources (e.g., public APIs, nodes - specific sources to be identified)
*   Market data APIs for Litecoin (specific sources to be identified)
*   Community resources (e.g., forums, documentation sites - specific sources to be identified)
*   Existing YouTube video summarization project (as a data source/component)

## Authentication & Authorization Mechanisms
*   (Not yet applicable for MVP, to be defined if user accounts or personalized features are added)

## Recent Significant Changes
*   Project Initialization (INIT-001) (6/5/2025) - Initial setup of documentation.
*   Project Reset & Re-Scaffold (6/5/2025) - Removed initial scaffold due to a Git submodule conflict. Re-scaffolded frontend and backend with a clean Git history, ensuring the monorepo is correctly tracked.

## Links to other relevant documentation
*   `cline_docs/projectRoadmap.md`
*   `cline_docs/techStack.md`
*   `cline_docs/currentTask.md`
