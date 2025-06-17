# Codebase Summary: Litecoin RAG Chat

## High-Level Directory Structure Overview
*   **Git Repository Root:** `Litecoin-Knowledge-Hub/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend, with rules correctly scoped for the monorepo structure.
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
        *   `app/`: Application routes and pages.
            *   `page.tsx`: Main chat interface.
            *   `login/page.tsx`: Authentication page.
        *   `components/`: Reusable React components for the chat interface.
        *   `contexts/`: React contexts for state management.
        *   `lib/`: Utility libraries and configurations.
*   `backend/`: Contains the FastAPI application.
    *   `strapi/`: Directory for Strapi CMS integration modules.
        *   `client.py`: Strapi REST API client implementation.
        *   `webhook_handler.py`: Strapi webhook processing logic.
    *   `data_ingestion/`: Contains modules for data loading, embedding, and vector store management.
        *   `embedding_processor_strapi.py`: Strapi-specific content processor for JSON parsing and hierarchical chunking.
    *   `api/v1/`: API version 1 routers.
        *   `chat.py`: Chat endpoint for RAG queries.
        *   `sources.py`: Data source management endpoints.
        *   `sync/`: Synchronization endpoints.
            *   `strapi.py`: Strapi webhook endpoints for content synchronization.
    *   `utils/`: Contains utility scripts.
    *   `main.py`: Main FastAPI application file.
    *   `rag_pipeline.py`: Encapsulates Langchain-related logic for the RAG pipeline.
*   `cline_docs/`: Contains project documentation.
    *   `projectRoadmap.md`: High-level project vision, goals, and progress.
    *   `currentTask.md`: Details of current objectives and active tasks.
    *   `techStack.md`: Key technology choices and justifications.
    *   `codebaseSummary.md`: Overview of project structure and components.
    *   `task_archive.md`: Archive of completed tasks.
*   `knowledge_base/`: Contains the legacy curated knowledge base (to be migrated to Strapi CMS).
    *   `articles/`: Subdirectory containing the curated markdown articles.
    *   `_template.md`: Template for knowledge base articles.
    *   `index.md`: Master index of all knowledge base articles.
    *   `deep_research/`: Subdirectory for deep research articles.
*   `strapi_setup/`: Directory for Strapi CMS related configurations and scripts.
    *   `migration/`: Scripts for migrating legacy content to Strapi.
    *   `config/`: Strapi CMS configuration files and templates.
    *   `backups/`: Strapi content backups and exports.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `reference_docs/`: Contains documentation for frameworks, services, and APIs used in the project.
*   `user_instructions/`: Contains instructions for the user.

## Key Modules/Components & Their Responsibilities

### Core RAG Pipeline Components
*   `backend/rag_pipeline.py`: Contains the core logic for the RAG (Retrieval-Augmented Generation) pipeline. This includes orchestrating Langchain chains, using an updated prompt template, and ensuring user queries are embedded with `task_type='retrieval_query'`.
*   `backend/main.py`: The main entry point for the FastAPI backend, responsible for defining API endpoints and handling incoming requests.
*   `backend/data_ingestion/embedding_processor.py`: Handles hierarchical chunking of Markdown documents (prepending titles/sections to content) and standard text splitting for other formats. Generates vector embeddings using Google Text Embedding 004 with `task_type='retrieval_document'` for knowledge base content.
*   `backend/data_ingestion/vector_store_manager.py`: Manages connections to MongoDB Atlas. Facilitates the insertion and retrieval of vector embeddings. Handles deletion of documents based on flattened metadata fields.

### Strapi CMS Integration Components
*   `backend/strapi/client.py`: Strapi REST API client for fetching content collections, handling authentication, and managing API requests.
*   `backend/strapi/webhook_handler.py`: Processes Strapi webhook events (e.g., entry.publish, entry.unpublish) and triggers the appropriate RAG pipeline updates.
*   `backend/data_ingestion/embedding_processor_strapi.py`: Specialized processor for Strapi content that parses JSON, extracts text, performs hierarchical chunking, and maps Strapi metadata to the RAG pipeline's schema.
*   `backend/api/v1/sync/strapi.py`: FastAPI router containing the Strapi webhook endpoint for real-time content synchronization.

### Legacy Components (To be Modified/Removed)
*   `backend/data_ingestion/litecoin_docs_loader.py`: Legacy loader for Markdown files. Will be used by the migration script but deprecated for direct ingestion.
*   `backend/cms/`: Directory containing a deprecated custom CMS implementation. This will be removed.

### Utility and Support Components
*   `backend/ingest_data.py`: A standalone script to orchestrate the data ingestion process, to be updated to support Strapi as a content source.
*   `backend/utils/clear_litecoin_docs_collection.py`: A utility script to clear all documents from collections in MongoDB.
*   `backend/data_models.py`: Contains core Pydantic data models for the application, to be updated with models for Strapi integration.
*   `backend/api/v1/sources.py`: Contains the API router and CRUD endpoints for managing data sources, to be updated to include Strapi as a source type.

## Core Data Models & Entities
*   **`DataSource`**: A Pydantic model representing a data source for the RAG pipeline. To be updated to include Strapi as a source type.
*   **`StrapiArticle`**: New Pydantic model representing a Strapi content type with all relevant metadata fields.
*   **`StrapiWebhookPayload`**: Model for handling Strapi webhook payloads with event type and entry data.

## Critical Data Flow Diagrams

### Strapi CMS Integration Data Flow
```mermaid
graph TD
    A[Strapi CMS] -->|REST API| B[Strapi Client]
    A -->|Webhooks| C[Webhook Handler]
    B -->|Fetch Content (JSON)| D[embedding_processor_strapi.py]
    C -->|Trigger Sync| D
    D -->|Parse & Chunk| E[Vector Embeddings]
    E -->|Store| F[MongoDB Vector Store]
    G[User Query] -->|Chat API| H[RAG Pipeline]
    H -->|Vector Search| F
    F -->|Retrieved Context| H
    H -->|Generated Answer| I[User Response]
```

### Legacy Knowledge Base Integration Flow (for reference)
```mermaid
graph TD
    A[Legacy Markdown Files] -->|Migration Script| B[Strapi CMS]
    B -->|Standard Flow| C[Strapi Integration Pipeline]
    C -->|Processed Content| D[RAG Vector Store]
```

## API Endpoints Overview

### Chat & Core Functionality
*   **`POST /api/v1/chat`**:
    *   **Description**: Receives a user query and processes it through the RAG pipeline, incorporating conversational history for context-aware responses.
    *   **Request Body**: `{"query": "string", "chat_history": [{"role": "human" | "ai", "content": "string"}]}`
    *   **Response Body**: `{"answer": "string", "sources": [...]}`

### Data Source Management
*   **`POST /api/v1/sources`**: Creates a new data source record (to be updated for Strapi support).
*   **`GET /api/v1/sources`**:
