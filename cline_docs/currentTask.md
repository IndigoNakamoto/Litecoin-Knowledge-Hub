# Current Task: Litecoin Knowledge Hub

## Current Sprint/Iteration Goal
*   **Milestone 6: Strapi CMS Integration - Phase 1: Strapi Setup and Configuration**

## High-Priority Initiatives: Strapi CMS Integration

## Active Task(s):
*   ### Task ID: `STRAPI-INT-005`
    *   #### Name: Implement and Verify Hierarchical Chunking for Strapi Content
    *   #### Detailed Description & Business Context:
        The initial Strapi integration did not correctly chunk rich text content, leading to poor retrieval quality. This task involved implementing a sophisticated, hierarchical chunker to split Strapi articles into meaningful sections based on headings. This is critical for providing accurate, context-aware answers in the RAG pipeline.
    *   #### Acceptance Criteria:
        1.  Strapi rich text content is split into separate documents for each heading section.
        2.  Each document's content is prepended with its hierarchical heading structure (e.g., "H1 > H2").
        3.  Each document's metadata is enriched with `chunk_type`, `section_title`, `parent_headings`, and `heading_level`.
        4.  The `entry.publish` webhook event successfully triggers the new chunking logic.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 3
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Refactored `backend/strapi/rich_text_chunker.py` with a stateful algorithm to create hierarchical chunks.
        *   Updated `backend/strapi/webhook_handler.py` to use the new chunker and correctly merge metadata.
        *   Successfully verified the end-to-end `publish` event, confirming that articles are chunked and stored correctly in MongoDB.
    *   #### Estimated Effort: 1 day
    *   #### Priority: High

## Task Backlog:
*   ### Task ID: `STRAPI-INT-006`
    *   #### Name: Verify Strapi `update`, `unpublish`, and `delete` Webhook Events
    *   #### Detailed Description & Business Context:
        While the `publish` event has been confirmed to work with the new hierarchical chunker, the other critical content lifecycle events (`update`, `unpublish`, `delete`) have not been explicitly tested. This task is to ensure that all webhook events are handled correctly by the RAG pipeline, ensuring data integrity and consistency between the CMS and the vector store.
    *   #### Acceptance Criteria:
        1.  Updating an article in Strapi correctly deletes the old document chunks and creates new, updated chunks in the vector store.
        2.  Unpublishing an article in Strapi correctly deletes all associated document chunks from the vector store.
        3.  Deleting an article from Strapi correctly deletes all associated document chunks from the vector store.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 3
    *   #### Status: To Do
    *   #### Estimated Effort: 1 day
    *   #### Priority: High

*   ### Task ID: `RAG-OPT-001`
    *   #### Name: Implement Query Optimization and Hybrid Search
    *   #### Detailed Description & Business Context:
        Update the RAG retrieval logic to leverage the new structured chunks and rich metadata. This involves implementing hybrid search (a combination of vector search and metadata-based filtering) to improve the accuracy and relevance of retrieved documents. This is the final step to fully realize the benefits of the new chunking strategy.
    *   #### Acceptance Criteria:
        1.  The core retrieval function in `rag_pipeline.py` is updated to accept metadata filters.
        2.  The chat API is updated to intelligently construct filters based on the user's query.
        3.  Section-aware retrieval is implemented (e.g., prioritizing `title_summary` chunks for overview questions).
        4.  End-to-end tests validate that hybrid search improves retrieval relevance for a variety of query types.
    *   #### Link to projectRoadmap.md goal(s):
        *   Phase 2: User Experience & Accuracy Enhancements
    *   #### Status: To Do
    *   #### Estimated Effort: 3-4 days
    *   #### Priority: High

## Recently Completed Tasks:
*   ### Task ID: `STRAPI-INT-004`
    *   #### Name: Test and Verify Strapi Webhook Synchronization
    *   #### Detailed Description & Business Context:
        Thoroughly test the end-to-end synchronization process between Strapi CMS and the MongoDB vector store. This involves creating, updating, publishing, unpublishing, and deleting content in Strapi and verifying that the changes are accurately and promptly reflected in the vector database. This is a critical step to ensure data integrity for the RAG pipeline.
    *   #### Acceptance Criteria:
        1.  When an article is **published** in Strapi, its content is correctly chunked, embedded, and stored in MongoDB.
        2.  When a published article is **updated** in Strapi, the corresponding documents in MongoDB are updated.
        3.  When an article is **unpublished** in Strapi, its corresponding documents are deleted from MongoDB.
        4.  When an article is **deleted** from Strapi, its corresponding documents are deleted from MongoDB.
        5.  The webhook endpoint correctly validates the secret token and handles valid/invalid requests securely.
        6.  The entire process has minimal and acceptable latency.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 3
    *   #### Status: Done
    *   #### Notes on Completion:
        *   The initial testing and verification of the webhook synchronization is complete.
        *   As part of this task, the entire chunking and metadata strategy was overhauled to support more granular, structure-aware retrieval.
        *   Created `backend/strapi/rich_text_chunker.py` to handle intelligent chunking of Strapi's rich text format.
        *   Updated `backend/data_ingestion/embedding_processor_strapi.py` to use the new chunker and to enrich documents with a detailed metadata schema defined in `backend/data_models.py`.
        *   Updated `cline_docs/techStack.md` with the new, recommended MongoDB Vector Search index definitions.
        *   Updated `cline_docs/codebaseSummary.md` to reflect the new architecture.
    *   #### Estimated Effort: 2-3 days
    *   #### Priority: High
*   ### Task ID: `STRAPI-INT-003`
    *   #### Name: Synchronization Mechanism
    *   #### Detailed Description & Business Context:
        Implement a real-time synchronization mechanism between Strapi and the RAG vector store. This will be achieved by using Strapi's webhooks to notify the RAG pipeline of content changes and implementing corresponding webhook endpoints in the FastAPI backend to process these notifications.
    *   #### Acceptance Criteria:
        1.  Strapi webhooks are configured to fire on content creation, update, and deletion events.
        2.  A FastAPI endpoint (e.g., `/api/v1/sync/strapi`) is implemented to receive and process these webhooks.
        3.  End-to-end synchronization is tested and confirmed to have minimal lag.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 3
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Created `backend/api/v1/sync/strapi.py` to define the secure webhook endpoint.
        *   Implemented `backend/strapi/webhook_handler.py` to process `publish`, `update`, and `unpublish` events.
        *   Added `delete_documents_by_strapi_id` to `VectorStoreManager` for content removal.
        *   Updated `backend/data_models.py` with webhook payload validation models.
        *   Registered the new router in `main.py` and added the secret to `.env.example`.
    *   #### Estimated Effort: 4-6 days
    *   #### Priority: High

*   ### Task ID: `STRAPI-INT-002`
    *   #### Name: Content API Integration
    *   #### Detailed Description & Business Context:
        Develop the backend components to enable seamless content retrieval from Strapi for the RAG pipeline. This involves creating a Python client to communicate with Strapi's REST API, building a content processor to handle Strapi's JSON format, and mapping Strapi metadata to the RAG pipeline's schema.
    *   #### Acceptance Criteria:
        1.  A Python client for the Strapi REST API is implemented.
        2.  An `embedding_processor_strapi.py` is created to process Strapi JSON content.
        3.  Strapi metadata is correctly mapped to the RAG pipeline's metadata schema.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 2
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Created `backend/strapi/client.py` with a `StrapiClient` to handle async requests.
        *   Created `backend/data_ingestion/embedding_processor_strapi.py` to parse Strapi's rich text JSON.
        *   Updated `backend/data_models.py` with Pydantic models for Strapi articles.
        *   Updated `backend/ingest_data.py` to support the new `strapi` source type.
        *   Successfully tested the end-to-end ingestion pipeline for Strapi content.
    *   #### Estimated Effort: 5-7 days
    *   #### Priority: High

*   ### Task ID: `STRAPI-INT-001`
    *   #### Name: Strapi Setup and Configuration
    *   #### Detailed Description & Business Context:
        Establish a self-hosted Strapi instance tailored to our content management needs. This includes provisioning the necessary infrastructure, defining the content models that will structure our knowledge base, and configuring role-based access control (RBAC) to enforce the Foundation's editorial workflow.
    *   #### Acceptance Criteria:
        1.  A Strapi instance is provisioned and running on a secure hosting platform.
        2.  Content types (e.g., FAQs, Articles, Documentation) are defined in Strapi.
        3.  RBAC is configured for Contributor, Editor, and Administrator roles.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 1
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Successfully initialized the Strapi application in `backend/cms` using `npx create-strapi-app`.
        *   The application is running with a default SQLite database for local development.
        *   The first administrative user has been created.
    *   #### Estimated Effort: 3-5 days
    *   #### Priority: High

*   ### Task ID: `CMS-PIVOT-001`
    *   #### Name: CMS Strategy Pivot to Strapi
    *   #### Detailed Description & Business Context:
        After a comparative analysis of Ghost and Strapi, a strategic decision was made to pivot to Strapi. This decision was driven by Strapi's superior database control, flexible content structuring, and open-source nature, which better align with the project's long-term RAG and data governance goals.
    *   #### Acceptance Criteria:
        1.  Complete comparative analysis of Ghost vs. Strapi.
        2.  Design a new integration architecture for Strapi using its REST API and webhooks.
        3.  Define hosting and infrastructure requirements for a self-hosted Strapi instance.
        4.  Update core project documentation (`projectRoadmap.md`, `techStack.md`, etc.) to reflect the new CMS direction.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration
    *   #### Status: Done
    *   #### Notes on Completion:
        *   The decision to switch to Strapi has been finalized and documented.
        *   All high-level project documents have been updated to reflect this pivot.

## Task Backlog:

[View Task Archive](task_archive.md)
