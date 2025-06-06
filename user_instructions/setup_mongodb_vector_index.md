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
    *   Paste the following JSON configuration into the editor. This configuration tells MongoDB how to index the vector embeddings.

    ```json
    {
      "fields": [
        {
          "type": "vector",
          "path": "embedding",
          "numDimensions": 768,
          "similarity": "cosine"
        }
      ]
    }
    ```

    *   **Explanation of the configuration:**
        *   `"type": "vector"`: Specifies that this is a vector field.
        *   `"path": "embedding"`: This must match the field name where Langchain stores the vector embeddings. By default, `langchain-mongodb` uses the field name `embedding`.
        *   `"numDimensions": 768`: This is the number of dimensions for the `text-embedding-004` model from Google. **This must be exact.**
        *   `"similarity": "cosine"`: Specifies the similarity metric to use for vector comparisons. Cosine similarity is a standard choice for this type of embedding.

5.  **Review and Create:**
    *   Click **Next**.
    *   Review the index configuration and click **Create Search Index**.

The index will now start building. This may take a few minutes. You can monitor the status in the Atlas UI. Once the index is active, you can proceed to run the data ingestion script.
