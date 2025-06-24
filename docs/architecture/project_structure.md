# Project Structure Overview

This document outlines the high-level directory and file structure of the Litecoin RAG Chat project.

## Root Level

- `README.md`: Project overview and setup instructions.
- `package.json`: Node.js project manifest for the root (likely for workspace management).
- `package-lock.json`: Exact versions of root-level Node.js dependencies.
- `backend/`: Contains the Python-based backend application (FastAPI, RAG pipeline).
- `frontend/`: Contains the Next.js-based frontend application.
- `payload_cms/`: Contains the Payload CMS application.
- `knowledge_base/`: Markdown files containing Litecoin knowledge.
- `cline_docs/`: Documentation related to the project's development and milestones.
- `user_instructions/`: Instructions for developers and users.

## `backend/`

- `main.py`: FastAPI application entry point.
- `rag_pipeline.py`: Core logic for the Retrieval-Augmented Generation pipeline.
- `ingest_data.py`: Script for ingesting data into the vector store.
- `requirements.txt`: Python package dependencies.
- `api/`: API endpoint definitions.
- `data_ingestion/`: Scripts and modules for loading data from various sources.
- `data_models.py`: Pydantic models for data validation and serialization.
- `dependencies.py`: FastAPI dependencies.
- `utils/`: Utility scripts.

### `backend/api/`

- `v1/`: Version 1 of the API.
- `v1/sources.py`: API endpoints for managing data sources.
- `v1/sync/payload.py`: API endpoint for syncing with Payload CMS.

## `frontend/`

- `next.config.ts`: Next.js configuration file.
- `package.json`: Frontend project manifest.
- `src/`: Source code for the frontend application.
- `public/`: Static assets.

### `frontend/src/`

- `app/`: Next.js App Router directory.
- `components/`: Reusable React components.
- `contexts/`: React contexts for state management.
- `lib/`: Library functions and utilities.
- `types/`: TypeScript type definitions.

## `payload_cms/`

- `payload.config.ts`: Main Payload CMS configuration file.
- `package.json`: Payload CMS project manifest.
- `src/`: Source code for the Payload CMS application.

### `payload_cms/src/`

- `collections/`: Definitions for Payload CMS collections (e.g., Articles, Users).
- `access/`: Access control functions for collections and fields.
- `app/`: Next.js app directory for Payload-specific pages.

## `knowledge_base/`

- `articles/`: Individual articles about Litecoin.
- `deep_research/`: In-depth research documents.
- `index.md`: Root index for the knowledge base.

## `cline_docs/`

- `milestones/`: Documentation for each project milestone.
- `projectRoadmap.md`: The overall project roadmap.
- `techStack.md`: A description of the technology stack.
- `codebaseSummary.md`: A summary of the codebase.
