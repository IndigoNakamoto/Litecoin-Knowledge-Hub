# Codebase Summary: Litecoin RAG Chat

## High-Level Directory Structure Overview
*   **Git Repository Root:** `Litecoin-RAG-Chat/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend, with rules correctly scoped for the monorepo structure (e.g., `frontend/node_modules/`).
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
*   `backend/`: Contains the FastAPI application.
    *   `data_ingestion/`: Contains modules for data loading, embedding, and vector store management.
    *   `main.py`: Main FastAPI application file.
    *   `requirements.txt`: Python dependencies.
    *   `rag_pipeline.py`: Encapsulates Langchain-related logic for the RAG pipeline.
*   `cline_docs/`: Contains project documentation.
    *   `projectRoadmap.md`: High-level project vision, goals, and progress.
    *   `currentTask.md`: Details of current objectives and active tasks.
    *   `techStack.md`: Key technology choices and justifications.
    *   `codebaseSummary.md`: Overview of project structure and components.
    *   `task_archive.md`: Archive of completed tasks.
*   `knowledge_base/`: Contains the curated knowledge base articles.
    *   `_template.md`: Template for new knowledge base articles.
    *   `index.md`: Master index of all knowledge base articles.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `reference_docs/`: Contains documentation for frameworks, services, and APIs used in the project.
*   `user_instructions/`: Contains instructions for the user.

## Key Modules/Components & Their Responsibilities
*   `backend/rag_pipeline.py`: Contains the core logic for the RAG (Retrieval-Augmented Generation) pipeline. This includes orchestrating Langchain chains, using an updated prompt template, and ensuring user queries are embedded with `task_type='retrieval_query'`.
*   `backend/main.py`: The main entry point for the FastAPI backend, responsible for defining API endpoints and handling incoming requests.
*   `backend/data_ingestion/litecoin_docs_loader.py`: Responsible for loading raw text data from various Litecoin-related sources.
*   `backend/data_ingestion/embedding_processor.py`: Handles hierarchical chunking of Markdown documents (prepending titles/sections to content) and standard text splitting for other formats. Generates vector embeddings using Google Text Embedding 004 with `task_type='retrieval_document'` for knowledge base content.
*   `backend/data_ingestion/vector_store_manager.py`: Manages connections to MongoDB Atlas and facilitates the insertion and retrieval of vector embeddings.
*   `backend/ingest_data.py`: A standalone script to orchestrate the data ingestion process, primarily focused on processing the **Curated Knowledge Base**.
*   `backend/data_models.py`: (Planned) Will contain core Pydantic data models for the application, such as the `DataSource` model.
*   `backend/api/v1/sources.py`: (Planned) Will contain the API router and endpoints for managing data sources.

## Core Data Models & Entities
*   **`DataSource`** (Planned): A Pydantic model to represent a data source for the RAG pipeline. It will include fields like `name`, `type`, `uri`, and `status`.
*   (Other models for Litecoin data, user queries, etc., will be defined as needed.)

## Critical Data Flow Diagrams
*   The following diagram illustrates the content-first RAG pipeline:
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

## API Endpoints Overview
*   **`POST /api/v1/chat`**:
    *   **Description**: Receives a user query and processes it through the RAG pipeline.
    *   **Request Body**: `{"query": "string"}`
    *   **Response Body**: `{"answer": "string", "sources": [...]}`
*   **Data Source Management (Planned):**
    *   **`POST /api/v1/sources`**: Creates a new data source.
    *   **`GET /api/v1/sources`**: Retrieves a list of all data sources.
    *   **`GET /api/v1/sources/{source_id}`**: Retrieves a single data source.
    *   **`PUT /api/v1/sources/{source_id}`**: Updates a data source.
    *   **`DELETE /api/v1/sources/{source_id}`**: Deletes a data source and its associated vectorized data.

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
*   `cline_docs/task_archive.md`
