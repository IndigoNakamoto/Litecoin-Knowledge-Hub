# Strapi CMS Integration Diagram (Webhook-Only CRUD)

This document provides a detailed architectural diagram of how the Strapi CMS is integrated into the RAG (Retrieval-Augmented Generation) pipeline, using a webhook-only model for all data synchronization (CRUD operations).

```mermaid
flowchart TD
    %% Nodes - User / Content Team
    A("fa:fa-user Content Editor")

    %% Nodes - Strapi CMS (Headless)
    B("fa:fa-laptop-code Admin UI")
    C("fa:fa-database Strapi Database")
    D("fa:fa-bell Webhook Emitter")

    %% Nodes - RAG Backend (FastAPI Application)
    E("fa:fa-cloud-download-alt /api/v1/sync/strapi (Webhook Endpoint)")
    F("fa:fa-cogs WebhookHandler")
    G("fa:fa-brain EmbeddingProcessorStrapi")
    H("fa:fa-vector-square VectorStoreManager")

    %% Nodes - Data Storage
    I("fa:fa-cloud-upload-alt MongoDB Atlas Vector Store")

    %% Define connections and data flows

    %% Flow: Real-Time CRUD Synchronization (Event-Driven)
    A -- "Performs Action: (Publish, Update, Unpublish, Delete)" --> B
    B -- "Saves Content" --> C
    C -- "Triggers Event on" --> D
    D -- "Fires Webhook:(POST with JSON Payload)" --> E
    E -- "Validates & Forwards Payload to" --> F
    F -- "Processes Event <br> (e.g., 'entry.publish', 'entry.update')" --> G
    G -- "Parses, Chunks, & Embeds Content" --> H
    F -- "Processes Event <br> (e.g., 'entry.unpublish', 'entry.delete')" --> H
    H -- "Upserts or Deletes <br> Vector Embeddings in MongoDB" --> I

    %% Styling
    classDef user fill:#fff2cc,stroke:#ffd966,stroke-width:2px;
    classDef cms fill:#e6f3ff,stroke:#a8caff,stroke-width:2px;
    classDef backend fill:#e2f0d9,stroke:#a9d18e,stroke-width:2px;
    classDef storage fill:#fbe5d6,stroke:#f4b183,stroke-width:2px;

    class A user;
    class B,C,D cms;
    class E,F,G,H backend;
    class I storage;

    %% Adjusting styles to be more inline with the example's aesthetic (e.g., fill and stroke for clarity)
    style A fill:#FFD966,stroke:#FFD966,color:#333;
    style B fill:#A8CAFF,stroke:#A8CAFF,color:#333;
    style C fill:#A8CAFF,stroke:#A8CAFF,color:#333;
    style D fill:#A8CAFF,stroke:#A8CAFF,color:#333;
    style E fill:#A9D18E,stroke:#A9D18E,color:#333;
    style F fill:#A9D18E,stroke:#A9D18E,color:#333;
    style G fill:#A9D18E,stroke:#A9D18E,color:#333;
    style H fill:#A9D18E,stroke:#A9D18E,color:#333;
    style I fill:#F4B183,stroke:#F4B183,color:#333;
```

### Diagram Explanation:

This diagram illustrates a purely event-driven architecture for synchronizing content between Strapi CMS and the RAG pipeline's vector store. All Create, Read, Update, and Delete (CRUD) operations are handled in real-time via webhooks.

**Real-Time CRUD Synchronization Flow (Steps 1-6):**

1.  **Action in CMS**: The entire process begins when a content editor performs an action in the **Strapi Admin UI**, such as publishing a new article (**Create**), modifying an existing one (**Update**), or unpublishing/deleting an article (**Delete**).
2.  **Webhook Event**: Strapi's **Webhook Emitter** detects the change and sends a POST request with a JSON payload to the FastAPI backend's `/api/v1/sync/strapi` endpoint. The payload contains details about the event (`entry.publish`, `entry.update`, `entry.unpublish`, `entry.delete`) and the content entry itself.
3.  **Webhook Handling**: The `WebhookHandler` in the backend receives and validates the payload.
4.  **Event Routing**:
    *   For **Create/Update** events (`entry.publish`, `entry.update`), the handler passes the content to the `EmbeddingProcessorStrapi`.
    *   For **Delete** events (`entry.unpublish`, `entry.delete`), the handler directly instructs the `VectorStoreManager` to remove the content.
5.  **Processing & Embedding**: For create/update events, the `EmbeddingProcessorStrapi` parses the rich text JSON, performs hierarchical chunking, and generates vector embeddings.
6.  **Database Operation**: The `VectorStoreManager` performs the final action on the **MongoDB Atlas Vector Store**:
    *   It **upserts** (updates or inserts) the new vector embeddings for create/update events.
    *   It **deletes** the corresponding vector embeddings for delete events.

This streamlined, webhook-only architecture ensures that the vector store is always an exact, real-time reflection of the published content in Strapi, making the system highly reliable and efficient.
