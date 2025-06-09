# Codebase Summary: Litecoin RAG Chat

## High-Level Directory Structure Overview
*   **Git Repository Root:** `Litecoin-RAG-Chat/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend, with rules correctly scoped for the monorepo structure (e.g., `frontend/node_modules/`).
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
*   `backend/`: Contains the FastAPI application.
    *   `data_ingestion/`: Contains modules for data loading, embedding, and vector store management.
    *   `utils/`: Contains utility scripts.
    *   `main.py`: Main FastAPI application file.
    *   `requirements.txt`: Python dependencies.
    *   `rag_pipeline.py`: Encapsulates Langchain-related logic for the RAG pipeline.
*   `cline_docs/`: Contains project documentation.
    *   `projectRoadmap.md`: High-level project vision, goals, and progress.
    *   `currentTask.md`: Details of current objectives and active tasks.
    *   `techStack.md`: Key technology choices and justifications.
    *   `codebaseSummary.md`: Overview of project structure and components.
    *   `task_archive.md`: Archive of completed tasks.
*   `knowledge_base/`: Contains the curated knowledge base.
    *   `articles/`: Subdirectory containing the curated markdown articles.
    *   `_template.md`: Template for new knowledge base articles.
    *   `index.md`: Master index of all knowledge base articles.
    *   `deep_research/`: Subdirectory for articles initiated by research tools (e.g., DeepSearch). These articles undergo the standard human curation and vetting process before being fully integrated.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `reference_docs/`: Contains documentation for frameworks, services, and APIs used in the project.
*   `user_instructions/`: Contains instructions for the user.

## Key Modules/Components & Their Responsibilities
*   `backend/rag_pipeline.py`: Contains the core logic for the RAG (Retrieval-Augmented Generation) pipeline. This includes orchestrating Langchain chains, using an updated prompt template, and ensuring user queries are embedded with `task_type='retrieval_query'`.
*   `backend/main.py`: The main entry point for the FastAPI backend, responsible for defining API endpoints and handling incoming requests.
*   `backend/data_ingestion/litecoin_docs_loader.py`: Responsible for loading raw text data from Markdown files or directories. It now utilizes the `python-frontmatter` library to accurately parse YAML front matter from these files, ensuring that metadata (like title, tags, custom fields) is correctly extracted and associated with the document content before further processing.
*   `backend/data_ingestion/embedding_processor.py`: Handles hierarchical chunking of Markdown documents (prepending titles/sections to content) and standard text splitting for other formats. It receives documents with pre-parsed front matter (from `litecoin_docs_loader.py`) and further processes this metadata, including converting `published_at` to `datetime` objects. Generates vector embeddings using Google Text Embedding 004 with `task_type='retrieval_document'` for knowledge base content.
*   `backend/data_ingestion/vector_store_manager.py`: Manages connections to MongoDB Atlas. Facilitates the insertion and retrieval of vector embeddings. Handles deletion of documents based on flattened metadata fields (as `langchain-mongodb` stores metadata at the root document level). Contains a `clear_all_documents()` method to empty a collection.
*   `backend/ingest_data.py`: A standalone script to orchestrate the data ingestion process, primarily focused on processing the **Curated Knowledge Base**.
*   `backend/utils/clear_litecoin_docs_collection.py`: A utility script to clear all documents from the `litecoin_docs` collection in MongoDB. It uses the `clear_all_documents` method from `VectorStoreManager`.
*   `backend/api_client/ingest_kb_articles.py`: A client script responsible for orchestrating the ingestion of the entire knowledge base. It interacts with the `/api/v1/sources` endpoints to ensure a clean and complete data ingestion process, including clearing the collection before starting.
*   `backend/data_models.py`: Contains core Pydantic data models for the application, such as `DataSource` and `DataSourceUpdate`.
*   `backend/api/v1/sources.py`: Contains the API router and CRUD endpoints for managing data sources. It uses FastAPI's dependency injection to handle database connections and ensures that deleting a data source also removes its associated embeddings from the vector store.
*   **AI-Integrated Knowledge Base CMS (Planned):** A new system to be developed, focusing on providing a user interface and backend APIs for collaborative content creation, editing, vetting, publishing, and archiving of knowledge base articles. This will integrate with AI capabilities for research and content assistance.

## Core Data Models & Entities
*   **`DataSource`**: A Pydantic model representing a data source for the RAG pipeline. It includes fields like `id`, `name`, `type`, `uri`, `status`, and timestamps.
*   **`DataSourceUpdate`**: A Pydantic model used for updating a `DataSource`, where all fields are optional.
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
*   **Planned CMS Data Flow (Conceptual):**
    ```mermaid
    graph TD
        A[User/AI Agent] --> B(CMS Frontend);
        B --> C(CMS Backend APIs);
        C --> D[Knowledge Base (MongoDB)];
        C --> E[AI Services: Google Deep Search, etc.];
        E --> C;
        C --> B;
        B --> A;
        C --> F[RAG Pipeline (Existing)];
        F --> G[Chatbot Frontend (Existing)];
        G --> A;
    ```

## API Endpoints Overview
*   **`POST /api/v1/chat`**:
    *   **Description**: Receives a user query and processes it through the RAG pipeline, incorporating conversational history for context-aware responses.
    *   **Request Body**: `{"query": "string", "chat_history": [{"role": "human" | "ai", "content": "string"}]}`
    *   **Response Body**: `{"answer": "string", "sources": [...]}`
*   **Data Source Management:**
    *   **`POST /api/v1/sources`**: Creates a new data source record.
    *   **`GET /api/v1/sources`**: Retrieves a list of all data source records.
    *   **`GET /api/v1/sources/{source_id}`**: Retrieves a single data source record by its ID.
    *   **`PUT /api/v1/sources/{source_id}`**: Updates an existing data source record using a partial update model.
    *   **`DELETE /api/v1/sources/{source_id}`**: Deletes a data source record and its associated vectorized data from the vector store.

## External Services & Dependencies
*   Google Text Embedding API (text-embedding-004)
*   Litecoin blockchain data sources (e.g., public APIs, nodes - specific sources to be identified)
*   Market data APIs for Litecoin (specific sources to be identified)
*   Community resources (e.g., forums, documentation sites - specific sources to be identified)
*   Existing YouTube video summarization project (as a data source/component)

## Authentication & Authorization Mechanisms
*   (Not yet applicable for MVP, to be defined if user accounts or personalized features are added)

## Recent Significant Changes
*   **Conversational Memory Implementation (6/9/2025)**:
    *   **Backend (`backend/data_models.py`, `backend/rag_pipeline.py`, `backend/main.py`):**
        *   Introduced `ChatMessage` and `ChatRequest` Pydantic models to handle structured chat history.
        *   Modified `RAGPipeline` to use Langchain's `create_history_aware_retriever` and `create_retrieval_chain` for context-aware question rephrasing and answer generation.
        *   Updated `/api/v1/chat` endpoint to accept `chat_history` and pass it to the RAG pipeline.
    *   **Frontend (`frontend/src/app/page.tsx`):**
        *   Updated `Message` interface to align `role` types (`human` | `ai`) with the backend.
        *   Modified `handleSendMessage` to construct and send `chat_history` with each query.
        *   Adjusted `Message` component rendering to map `human` | `ai` roles back to `user` | `assistant` for display.
*   Project Initialization (INIT-001) (6/5/2025) - Initial setup of documentation.
*   Project Reset & Re-Scaffold (6/5/2025) - Removed initial scaffold due to a Git submodule conflict. Re-scaffolded frontend and backend with a clean Git history, ensuring the monorepo is correctly tracked.
*   Metadata Ingestion Fix (M4-FAQ-001) (6/6/2025) - Resolved an issue where front matter from Markdown documents in `knowledge_base/` was not being correctly ingested. Updated `litecoin_docs_loader.py` to use the `python-frontmatter` library for robust parsing, ensuring all metadata is captured.
*   Data Source CRUD API (M4-DATASRC-001) (6/7/2025) - Implemented a full suite of CRUD API endpoints for managing data sources. This includes creating `DataSource` and `DataSourceUpdate` Pydantic models, using FastAPI's dependency injection for database connections, and ensuring that `PUT` and `DELETE` operations maintain data integrity by removing associated embeddings from the vector store.

## Links to other relevant documentation
*   `cline_docs/projectRoadmap.md`
*   `cline_docs/techStack.md`
*   `cline_docs/currentTask.md`
*   `cline_docs/task_archive.md`
