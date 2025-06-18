# Current Task: Litecoin Knowledge Hub

## Current Sprint/Iteration Goal
*   **Milestone 6: Strapi CMS Integration - Phase 1: Strapi Setup and Configuration**

## High-Priority Initiatives: Strapi CMS Integration

## Active Task(s):
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
    *   #### Status: In Progress
    *   #### Estimated Effort: 2-3 days
    *   #### Priority: High

## Recently Completed Tasks:
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
