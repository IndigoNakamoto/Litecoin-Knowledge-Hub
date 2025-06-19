# Current Task: Litecoin Knowledge Hub

## Current Sprint/Iteration Goal
*   **Milestone 6: AI-Integrated CMS (Transition to Payload CMS)**

## High-Priority Initiatives: CMS Migration & RAG Integration

## Active Task(s):
*   ### Task ID: `CMS-MIG-001`
    *   #### Name: Migrate CMS from Strapi to Payload CMS
    *   #### Detailed Description & Business Context:
        Due to user interface preferences, the project is transitioning from Strapi CMS to Payload CMS. This task involves a complete migration, including setting up Payload, defining content schemas, integrating it with the RAG pipeline's content ingestion, and updating the article generation and translation dashboard to interact with Payload's API. This ensures a more user-friendly content management experience while maintaining the integrity of the RAG system.
    *   #### Acceptance Criteria:
        1.  Payload CMS is successfully set up and configured with MongoDB.
        2.  Existing Strapi content types are accurately translated into Payload collections.
        3.  Payload's `afterChange` hooks are implemented to trigger the Content Sync Service.
        4.  The Content Sync Service successfully fetches and processes content from Payload CMS for embedding.
        5.  The Embedding Processor correctly parses and chunks content from Payload.
        6.  The Article Generation Dashboard can save original and translated drafts to Payload via its API.
        7.  The RAG pipeline accurately retrieves and generates responses based on content managed by Payload CMS.
        8.  All Strapi-related code and configurations are removed from the codebase.
        9.  Relevant `cline_docs` files (`projectRoadmap.md`, `techStack.md`, `codebaseSummary.md`, `README.md`) are updated to reflect the Payload CMS integration.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 6: AI-Integrated CMS
    *   #### Status: In Progress
    *   #### Estimated Effort: 5-7 days
    *   #### Priority: Critical

## Task Backlog:
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
## Task Backlog:

[View Task Archive](archive/task_archive.md)
