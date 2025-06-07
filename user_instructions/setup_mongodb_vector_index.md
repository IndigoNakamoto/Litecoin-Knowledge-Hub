# How to Set Up MongoDB Atlas Vector Search Index

This guide provides the steps to create the necessary vector search index in your MongoDB Atlas cluster. This index is required for the data ingestion script (`ingest_data.py`) to function correctly.

The RAG pipeline uses a collection named `litecoin_docs` within a database named `litecoin_rag_db`.

## Prerequisites
- A MongoDB Atlas account with a running cluster.
- The `mongosh` command-line tool or access to the Atlas UI.

## Steps to Create the Vector Search Index

1.  **Navigate to Your Collection:**
    *   Log in to your MongoDB Atlas account.
    *   Navigate to the "Database" section and select the cluster where you want to store the data.
    *   Click on "Browse Collections".
    *   If the `litecoin_rag_db` database and `litecoin_docs` collection do not exist, they will be created automatically when you run the ingestion script for the first time. However, you need to create the index *before* running the script. You can create the database and collection manually if you prefer.

2.  **Create the Search Index:**
    *   In the Atlas UI, select the `litecoin_rag_db` database and then the `litecoin_docs` collection.
    *   Click on the **Search** tab.
    *   Click on **Create Search Index**.

3.  **Select the Index Creation Method:**
    *   Choose the **Atlas Vector Search** option.
    *   Click **Next**.

4.  **Configure the Index:**
    *   You will be presented with a JSON editor to define the index.
    *   Give your index a name (e.g., `vector_index`).
    *   Paste the following JSON configuration into the editor. This configuration tells MongoDB how to index the vector embeddings and ensures other fields like `text` and `metadata` are also stored and indexed.

    ```json
    {
      "name": "vector_index", // Or your preferred index name, ensure it matches MONGO_VECTOR_INDEX_NAME
      "dynamic": true,       // IMPORTANT: Allows fields not explicitly defined (like 'text' and 'metadata') to be indexed.
      "fields": [
        {
          "type": "vector",
          "path": "embedding", // Default path for Langchain embeddings
          "numDimensions": 768, // Must match your embedding model's dimensions (e.g., 768 for text-embedding-004)
          "similarity": "cosine"
        },
        // Optional: Explicitly define metadata fields if you need to perform specific queries/sorts on them.
        // If "dynamic": true is set, these are not strictly necessary for storage but can optimize searching on these fields.
        // Example:
        // {
        //   "type": "document", // Represents the 'metadata' field which is an object
        //   "path": "metadata",
        //   "dynamic": true    // Allows all sub-fields within 'metadata' to be indexed
        // },
        // {
        //   "type": "string",
        //   "path": "metadata.source", // Example for a specific metadata sub-field
        //   "analyzer": "lucene.standard" // Choose an appropriate analyzer
        // }
      ]
    }
    ```

    *   **Explanation of the configuration:**
        *   `"name"`: The name for your search index.
        *   `"dynamic": true`: This is crucial. It tells Atlas Search to automatically index fields that are not explicitly defined in the `fields` array. This ensures that `text` (page content) and `metadata` (document metadata) are stored and can be retrieved.
        *   `"type": "vector"`: Specifies that this is a vector field.
