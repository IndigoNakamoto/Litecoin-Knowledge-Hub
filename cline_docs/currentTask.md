# Current Task: Litecoin Knowledge Hub

## Current Sprint/Iteration Goal
*   **Milestone 6: Strapi CMS Integration - Phase 1: Strapi Setup and Configuration**

## High-Priority Initiatives: Strapi CMS Integration

## Recently Completed Tasks:

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
    *   #### Status: To Do
    *   #### Estimated Effort: 5-7 days
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
    *   #### Status: To Do
    *   #### Estimated Effort: 4-6 days
    *   #### Priority: High

*   ### Task ID: `STRAPI-INT-004`
    *   #### Name: Content Migration
    *   #### Detailed Description & Business Context:
        Transfer the existing knowledge base content from the legacy Markdown files in `knowledge_base/` to the new Strapi CMS. This requires a migration script that can parse the Markdown files and use the Strapi API to create corresponding entries.
    *   #### Acceptance Criteria:
        1.  A migration script is developed to import content from Markdown files into Strapi.
        2.  Metadata (title, tags, authors) and content structure are preserved during migration.
        3.  All migrated content is validated for accuracy in the Strapi admin panel.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: Strapi CMS Integration
        *   Milestone 6: Strapi CMS Integration - Phase 4
    *   #### Status: To Do
    *   #### Estimated Effort: 3-4 days
    *   #### Priority: Medium

## Legacy Tasks (Deprecated):

*   ### Task ID: `GHOST-INT-*` - DEPRECATED
    *   #### Name: All Ghost CMS Integration Tasks
    *   #### Status: Deprecated
    *   #### Notes: All tasks related to the Ghost CMS integration (`GHOST-INT-001` through `GHOST-INT-004`) are now obsolete due to the strategic pivot to Strapi CMS.

[View Task Archive](task_archive.md)
