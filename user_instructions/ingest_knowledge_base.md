# How to Ingest the Knowledge Base

This document outlines the process for performing a clean ingestion of the knowledge base into the MongoDB vector store. This is necessary when you add new articles, update existing ones, or need to ensure the vector store is in a consistent state.

The process involves two main scripts that should be run in order from the project's root directory:

1.  **Clear the Existing Collection:** This step ensures you are starting with a fresh, empty vector store, preventing any duplicate or outdated data from interfering with the new ingestion.
    *   **Script:** `backend/utils/clear_litecoin_docs_collection.py`
    *   **What it does:** This utility script connects to your MongoDB Atlas instance and completely clears all documents from the `litecoin_docs` collection.
    *   **Command:**
        ```bash
        python backend/utils/clear_litecoin_docs_collection.py
        ```

2.  **Ingest All Knowledge Base Articles:** This script orchestrates the ingestion of all content from the `knowledge_base/` directory (including both `articles` and `deep_research`) by making calls to the backend API.
    *   **Script:** `backend/api_client/ingest_kb_articles.py`
    *   **What it does:** It systematically reads the content, processes it through the RAG pipeline (hierarchical chunking, embedding), and populates the vector store.
    *   **Command:**
        ```bash
        python backend/api_client/ingest_kb_articles.py
        ```

### **Summary of Steps**

To perform a full, clean ingestion of the knowledge base, execute the following commands sequentially from the project's root directory (`Litecoin-RAG-Chat/`):

```bash
python backend/utils/clear_litecoin_docs_collection.py
python backend/api_client/ingest_kb_articles.py
```

This two-step process ensures data integrity and is the standard procedure for updating the knowledge base.
