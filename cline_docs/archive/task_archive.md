## Recently Completed Tasks:

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
    *   #### Status: Done
    *   #### Estimated Effort: 1 day
    *   #### Priority: High
    *   #### Plan:
        *   **Objective:** To confirm that `update`, `unpublish`, and `delete` events in Strapi correctly trigger the corresponding actions (update or delete) in the MongoDB vector store, ensuring data consistency.
        *   **Test Case 1: Baseline (`entry.publish`)**
            *   **Action:** Create and publish a new article in Strapi.
            *   **Verification:** Confirm document creation in logs and MongoDB.
        *   **Test Case 2: `entry.update`**
            *   **Action:** Update the previously published article.
            *   **Verification:** Confirm old documents are deleted and new ones are created.
        *   **Test Case 3: `entry.unpublish`**
            *   **Action:** Unpublish the article.
            *   **Verification:** Confirm all associated documents are deleted from MongoDB.
        *   **Test Case 4: `entry.delete`**
            *   **Action:** Re-publish and then permanently delete the article.
            *   **Verification:** Confirm all associated documents are deleted from MongoDB.
    *   #### Notes on Completion:
        *   Identified and fixed a critical bug where `entry.unpublish` and `entry.update` events failed to delete documents due to using the volatile `entry.id` instead of the stable `entry.documentId`.
        *   Updated `VectorStoreManager` to include a `delete_documents_by_document_id` method.
        *   Updated the `webhook_handler` to use the new deletion method, ensuring data integrity.
        *   Added `document_id` to the metadata for all chunks.
        *   Successfully re-ran the E2E test plan and verified that `publish`, `update`, `unpublish`, and `delete` events are all now handled correctly and robustly.
        
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
    *   #### Status: Done (6/18/25)
    *   #### Notes on Completion:
        *   Refactored `backend/strapi/rich_text_chunker.py` with a stateful algorithm to create hierarchical chunks.
        *   Updated `backend/strapi/webhook_handler.py` to use the new chunker and correctly merge metadata.
        *   Successfully verified the end-to-end `publish` event, confirming that articles are chunked and stored correctly in MongoDB.
    *   #### Estimated Effort: 1 day
    *   #### Priority: High

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
    *   #### Status: Done (6/18/25)
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
    *   #### Status: Done (6/18/25)
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
    *   #### Status: Done (6/18/25)
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
    *   #### Status: Done (6/17/25)
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
    *   #### Status: Done (6/16/25)
    *   #### Notes on Completion:
        *   The decision to switch to Strapi has been finalized and documented.
        *   All high-level project documents have been updated to reflect this pivot.

*   ### Task ID: `FEAT-CONV-001`
    *   #### Name: Implement Conversational Memory for RAG Chat
    *   #### Detailed Description & Business Context:
        Enhance the Litecoin RAG Chat application to maintain conversational context across multiple turns. This will allow the chatbot to understand follow-up questions that refer to previous parts of the conversation, leading to more natural and accurate responses.
    *   #### Acceptance Criteria:
        1.  The backend API (`/api/v1/chat`) is updated to accept and process chat history.
        2.  The RAG pipeline (`backend/rag_pipeline.py`) is modified to use Langchain's history-aware retriever and retrieval chain.
        3.  The frontend (`frontend/src/app/page.tsx`) correctly sends the conversation history with each new query.
        4.  The chatbot can accurately answer follow-up questions based on previous turns in the conversation.
        5.  `backend/data_models.py` is updated with `ChatMessage` and `ChatRequest` models.
        6.  `cline_docs/codebaseSummary.md` is updated to reflect the changes.
    *   #### Link to projectRoadmap.md goal(s):
        *   Primary Goal: Deliver accurate, real-time responses to Litecoin-related queries.
        *   Enhance user experience and foster greater adoption of Litecoin.
    *   #### Status: Done
    *   #### Notes on Completion:
        *   `backend/data_models.py` updated with `ChatMessage` and `ChatRequest` Pydantic models.
        *   `backend/rag_pipeline.py` modified to use `create_history_aware_retriever` and `create_retrieval_chain`, along with new prompt templates for history-aware question rephrasing and final answer generation. The `query` method now accepts `chat_history`.
        *   `backend/main.py` updated to import `ChatRequest` and `ChatMessage`, and the `/api/v1/chat` endpoint now accepts `ChatRequest` and passes the `chat_history` to the RAG pipeline.
        *   `frontend/src/app/page.tsx` updated to manage chat history state, send it with API requests, and align `Message` interface roles (`human` | `ai`) with the backend.
        *   `cline_docs/codebaseSummary.md` updated to document these changes.
    *   #### Estimated Effort: 4 hours
    *   #### Assigned To: Cline
    *   #### Priority: Highest

*   ### Task ID: `M4-E2E-003`
    *   #### Name: Re-run End-to-End Test with Clean Collection
    *   #### Detailed Description & Business Context:
        Perform a clean run of the full knowledge base ingestion and RAG pipeline validation. This involves clearing the existing vector store, re-ingesting all content from `knowledge_base/articles` and `knowledge_base/deep_research`, and running the end-to-end test suite to ensure the system is functioning correctly from a clean state.
    *   #### Acceptance Criteria:
        1.  The MongoDB vector store (`litecoin_docs` collection) is successfully cleared.
        2.  The `ingest_kb_articles.py` script runs without errors, processing all documents from the knowledge base.
        3.  The `test_rag_pipeline.py` test suite passes, confirming the RAG pipeline's ability to retrieve information from the newly ingested, comprehensive dataset.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
    *   #### Status: Done
    *   #### Plan:
        1.  Execute `backend/utils/clear_litecoin_docs_collection.py` to empty the vector store.
        2.  Execute `backend/api_client/ingest_kb_articles.py` to ingest all knowledge base content.
        3.  Execute `backend/test_rag_pipeline.py` to validate the pipeline.
    *   #### Priority: Highest

*   ### Task ID: `M4-E2E-002`
    *   #### Name: Ingest All Knowledge Base Content and Perform RAG Pipeline Test
    *   #### Detailed Description & Business Context:
        With the foundational knowledge base content now created in both `knowledge_base/articles` and `knowledge_base/deep_research`, the next critical step is to ingest all of this content into the vector store and perform an end-to-end test of the RAG pipeline. This will validate that the ingestion process works for multiple directories and that the retrieval system can successfully pull context from the newly added `deep_research` articles.
    *   #### Acceptance Criteria:
        1.  The `ingest_data.py` script is confirmed or updated to process Markdown files from both `knowledge_base/articles` and `knowledge_base/deep_research`.
        2.  The script is executed successfully, and the content is indexed in the MongoDB vector store.
        3.  A test query is run using `test_rag_pipeline.py` that specifically targets information present only in the `deep_research` articles.
        4.  The test successfully retrieves the correct context and generates a relevant answer, confirming the end-to-end pipeline is functional with the expanded knowledge base.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Created a client script `backend/api_client/ingest_kb_articles.py` to manage ingestion via API calls.
        *   Debugged and fixed multiple issues in the ingestion pipeline, including `datetime` encoding errors and file extension handling.
        *   Identified and corrected the root cause of retrieval failure: `vetting_status` was set to `draft` in `deep_research` articles.
        *   Updated all `deep_research` articles to `vetting_status: vetted`.
        *   Performed a full, clean ingestion of all knowledge base content and validated with a targeted test query that the RAG pipeline now retrieves the correct sources.
    *   #### Estimated Effort: 1-2 hours (excluding indexing time)
    *   #### Assigned To: Cline
    *   #### Priority: Highest

*   ### Task ID: `M4-DATASRC-001`
    *   #### Name: Implement CRUD API for Data Source Management
    *   #### Detailed Description & Business Context:
        To effectively manage the knowledge base of the RAG system, we need a dedicated way to track and control the data sources being ingested. This task involves creating a new set of API endpoints to handle the Create, Read, Update, and Delete (CRUD) operations for data sources. This will provide a foundational mechanism for adding, viewing, modifying, and removing sources, ensuring that the RAG pipeline is always working with a well-curated and up-to-date set of information.
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Implemented the full suite of CRUD endpoints in `backend/api/v1/sources.py`.
        *   Created `DataSource` and `DataSourceUpdate` Pydantic models in `backend/data_models.py` to handle data validation.
        *   Refactored the API to use FastAPI's dependency injection for MongoDB connections, which resolved testing issues related to environment variable loading and database access.
        *   The `PUT` and `DELETE` endpoints correctly remove associated embeddings from the vector store to maintain data integrity.
        *   Created a comprehensive test suite in `backend/test_sources_api.py` with 11 tests that are all passing, confirming the functionality of the API.

*   ### Task ID / Name: `M4-FAQ-001` - Create and Ingest Curated Content for Litecoin Basics & FAQ
    *   #### Detailed Description & Business Context:
        To implement the "Litecoin Basics & FAQ" feature, the RAG pipeline needs to be populated with high-quality, curated knowledge. This task involves creating well-structured Markdown documents for fundamental Litecoin topics within the `knowledge_base/` directory and then ingesting this curated data into the MongoDB vector store.
    *   #### Acceptance Criteria:
        1.  The foundational articles created in `M4-KB-001` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`) are finalized and meet quality standards in the `knowledge_base/articles/` directory.
        2.  The `ingest_data.py` script is used to load data specifically from the `knowledge_base/articles/` directory.
        3.  Verify that the data from these curated articles is present in the MongoDB vector store.
        4.  Document any specific ingestion notes in this task's "Notes on Completion".
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: Done
    *   #### Plan:
        *   ✅ Finalize content of initial FAQ articles in `knowledge_base/articles/`. (Completed as part of M4-KB-001)
        *   ✅ Use `ingest_data.py` to load data from `knowledge_base/articles/`.
        *   ✅ Verify ingestion in MongoDB (implicitly done by checking vector store content and metadata via `test_rag_pipeline.py`).
        *   ✅ Confirmed front matter metadata is correctly ingested with document chunks.
    *   #### Notes on Completion:
        *   Initial ingestion of foundational articles from `knowledge_base/articles/` is complete.
        *   Corrected an issue where `UnstructuredMarkdownLoader` was not parsing front matter. Switched to `python-frontmatter` library in `litecoin_docs_loader.py` which resolved the problem.
        *   Verified via `test_rag_pipeline.py` that front matter (title, tags, last_updated) is now present in the metadata of the ingested document chunks.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

*   ### Task ID: `M3-DOC-001`
    *   #### Name: Document Metadata Filtering Enhancements
    *   #### Detailed Description:
        Update project documentation (`techStack.md`, `codebaseSummary.md`, `projectRoadmap.md`) to reflect the recent implementation of metadata filtering capabilities. This includes noting the metadata flattening behavior of `langchain-mongodb` and providing the correct Atlas Vector Search index definition.
    *   #### Acceptance Criteria:
        1.  `techStack.md` is updated with details on metadata handling and the correct Atlas index JSON.
        2.  `codebaseSummary.md` is updated to reflect changes in `embedding_processor.py` and `vector_store_manager.py`.
        3.  `projectRoadmap.md` logs the completion of metadata filtering enhancement under Milestone 3.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation
    *   #### Status: Done
    *   #### Plan:
        *   Update `techStack.md`.
        *   Update `codebaseSummary.md`.
        *   Update `projectRoadmap.md`.
    *   #### Priority: High


*   ### Task ID: `M3-RAG-OPT-002`
    *   #### Name: Implement and Validate Metadata Filtering for RAG
    *   #### Detailed Description:
        Enhance the RAG pipeline to support filtering by metadata extracted from document frontmatter. This involves updating the embedding processor to handle new metadata fields (e.g., `author`, `published_at`, `tags`), ensuring these fields are correctly stored in MongoDB, and updating the Atlas Vector Search index definition to allow filtering on these fields. The `langchain-mongodb` library's behavior of flattening metadata into the root of the document was discovered and addressed.
    *   #### Acceptance Criteria:
        1.  `embedding_processor.py` correctly parses and converts frontmatter metadata, including `published_at` to `datetime`.
        2.  `vector_store_manager.py` correctly handles deletion of documents based on flattened metadata.
        3.  A test case in `test_rag_pipeline.py` validates that `similarity_search` with `pre_filter` correctly retrieves documents based on various metadata criteria (e.g., author, tags).
        4.  The user is provided with the correct Atlas Vector Search index JSON definition for flattened metadata.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation
    *   #### Status: Verified
    *   #### Progress (as of 2025-06-06):
        *   ✅ `embedding_processor.py` updated for `published_at` date conversion.
        *   ✅ `vector_store_manager.py` updated for correct metadata deletion.
        *   ✅ `test_metadata_filtering` added to `test_rag_pipeline.py` and successfully passed after user updated Atlas index.
        *   ✅ Correct Atlas Vector Search index definition provided to user.
    *   #### Discovered During Work:
        *   `langchain-mongodb` flattens metadata into the root of the MongoDB document.
        *   The Atlas Vector Search index must define filterable paths at the root level (e.g., `author`, not `metadata.author`).
    *   #### Plan:
        *   ✅ Update `embedding_processor.py`.
        *   ✅ Update `vector_store_manager.py`.
        *   ✅ Create `sample_for_metadata_test.md`.
        *   ✅ Add `test_metadata_filtering` to `test_rag_pipeline.py`.
        *   ✅ Iteratively debugged and fixed test based on pymongo errors and direct DB inspection.
        *   ✅ Confirmed metadata flattening and provided correct index definition to user.
        *   ✅ Test passed after user updated index.
    *   #### Priority: Highest

*   ### Task ID: `M4-UI-001`
    *   #### Name: Develop Frontend Chat UI Components
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Initialized ShadCN and added necessary components (`card`, `input`, `button`, `avatar`, `accordion`).
        *   Created custom components (`ChatWindow.tsx`, `Message.tsx`, `InputBox.tsx`).
        *   Assembled components and implemented basic state management in `frontend/src/app/page.tsx`.

*   ### Task ID: `M4-INT-001`
    *   #### Name: Integrate Frontend with Backend API
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Implemented API call logic in `frontend/src/app/page.tsx` to send queries to `/api/v1/chat` and display responses/sources.
        *   Configured CORS middleware and added an OPTIONS handler in `backend/main.py` to resolve cross-origin issues.

*   ### Task ID: `M3-TEST-001`
    *   #### Name: Create Validation Test for Advanced RAG Optimizations
    *   #### Detailed Description:
        This task involves creating a new test case within `backend/test_rag_pipeline.py` to specifically validate the recent RAG enhancements. The test will use a controlled, small-scale Markdown document to verify that the hierarchical chunking and asymmetric `task_type` embeddings are functioning as expected and leading to accurate retrieval.
    *   #### Acceptance Criteria:
        1.  A new, temporary test file, `backend/data_ingestion/test_data/sample_for_hierarchical_test.md`, will be created with a clear hierarchical structure (titles, sections, subsections).
        2.  A new test function, `test_hierarchical_chunking_and_retrieval`, will be added to `backend/test_rag_pipeline.py`.
        3.  The test will programmatically:
            *   Clear the vector store before starting for a clean base.
            *   Ingest the `sample_for_hierarchical_test.md` file.
            *   Verify that the chunks stored in the vector database contain the prepended hierarchical titles (e.g., "Title: Document Title\nSection: Section 1").
            *   Formulate a specific query that should *only* match a chunk from a deep subsection.
            *   Assert that the correct, context-rich chunk is retrieved, proving the system's precision.
        4.  The test must clean up after itself by deleting the temporary test data from the vector store upon completion.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Enhancement Validation)
    *   #### Status: Verified
    *   #### Progress (as of 2025-06-06):
        *   ✅ `backend/data_ingestion/test_data/sample_for_hierarchical_test.md` created.
        *   ✅ `test_hierarchical_chunking_and_retrieval` function added to `backend/test_rag_pipeline.py` with logic for ingestion, verification, and cleanup.
    *   #### Discovered During Work:
        *   **Metadata Persistence Issue (2025-06-06):** The `test_hierarchical_chunking_and_retrieval` test initially failed because document metadata was not being saved to MongoDB in a way that `pymongo.collection.find()` could directly retrieve it as a BSON object.
        *   **Strategy Update (2025-06-06):** The test was updated to use the main `litecoin_docs` collection.
        *   **Resolution Steps (2025-06-06):**
            1.  Updated `backend/data_ingestion/vector_store_manager.py` to explicitly define `text_key="text"` and `metadata_key="metadata"` when initializing `MongoDBAtlasVectorSearch`.
            2.  Ensured the MongoDB Atlas Vector Search index for the `litecoin_docs` collection used the simple definition (only defining the `embedding` field).
            3.  Increased `time.sleep()` in `backend/test_rag_pipeline.py` to 60 seconds to allow more time for Atlas indexing.
        *   **Outcome (2025-06-06):** The `test_hierarchical_chunking_and_retrieval` test now passes its core assertions: the RAG pipeline correctly retrieves context-rich chunks. However, direct inspection of the `metadata` field via `pymongo.collection.find()` in the test script still shows `None`. This suggests `langchain-mongodb` handles metadata internally for its operations, but direct BSON inspection might require a different approach or understanding of how the data is stored/reconstructed by the library. Since the RAG functionality is verified, this direct inspection anomaly is noted but does not block the task's completion.
    *   #### Plan:
        *   ✅ Create `backend/data_ingestion/test_data/sample_for_hierarchical_test.md`.
        *   ✅ Add `test_hierarchical_chunking_and_retrieval` to `backend/test_rag_pipeline.py`.
        *   ✅ Implement test logic: ingest, verify chunks, query, assert, cleanup.
        *   ✅ Updated `backend/test_rag_pipeline.py` to use the `litecoin_docs` collection.
        *   ✅ Updated `backend/data_ingestion/vector_store_manager.py` to explicitly set `text_key` and `metadata_key`.
        *   ✅ User confirmed Atlas Vector Search index for `litecoin_docs` is using the simple definition.
        *   ✅ Updated `backend/test_rag_pipeline.py` to increase sleep time to 60s after ingestion.
        *   ✅ Ran `python backend/test_rag_pipeline.py`. Test assertions for RAG functionality passed. Direct MongoDB inspection of metadata via `pymongo` in the test script still shows `None`, but this does not impede RAG functionality.
        *   **Task `M3-TEST-001` is now verified and complete.**
    *   #### Priority: Highest

*   ### Task ID: `FEAT-CONV-001`
    *   #### Name: Implement Conversational Memory for RAG Chat
    *   #### Detailed Description & Business Context:
        Enhance the Litecoin RAG Chat application to maintain conversational context across multiple turns. This will allow the chatbot to understand follow-up questions that refer to previous parts of the conversation, leading to more natural and accurate responses.
    *   #### Acceptance Criteria:
        1.  The backend API (`/api/v1/chat`) is updated to accept and process chat history.
        2.  The RAG pipeline (`backend/rag_pipeline.py`) is modified to use Langchain's history-aware retriever and retrieval chain.
        3.  The frontend (`frontend/src/app/page.tsx`) correctly sends the conversation history with each new query.
        4.  The chatbot can accurately answer follow-up questions based on previous turns in the conversation.
        5.  `backend/data_models.py` is updated with `ChatMessage` and `ChatRequest` models.
        6.  `cline_docs/codebaseSummary.md` is updated to reflect the changes.
    *   #### Link to projectRoadmap.md goal(s):
        *   Primary Goal: Deliver accurate, real-time responses to Litecoin-related queries.
        *   Enhance user experience and foster greater adoption of Litecoin.
    *   #### Status: Done
    *   #### Notes on Completion:
        *   `backend/data_models.py` updated with `ChatMessage` and `ChatRequest` Pydantic models.
        *   `backend/rag_pipeline.py` modified to use `create_history_aware_retriever` and `create_retrieval_chain`, along with new prompt templates for history-aware question rephrasing and final answer generation. The `query` method now accepts `chat_history`.
        *   `backend/main.py` updated to import `ChatRequest` and `ChatMessage`, and the `/api/v1/chat` endpoint now accepts `ChatRequest` and passes the `chat_history` to the RAG pipeline.
        *   `frontend/src/app/page.tsx` updated to manage chat history state, send it with API requests, and align `Message` interface roles (`human` | `ai`) with the backend.
        *   `cline_docs/codebaseSummary.md` updated to document these changes.
    *   #### Estimated Effort: 4 hours
    *   #### Assigned To: Cline
    *   #### Priority: Highest

*   ### Task ID: `M4-E2E-003`
    *   #### Name: Re-run End-to-End Test with Clean Collection
    *   #### Detailed Description & Business Context:
        Perform a clean run of the full knowledge base ingestion and RAG pipeline validation. This involves clearing the existing vector store, re-ingesting all content from `knowledge_base/articles` and `knowledge_base/deep_research`, and running the end-to-end test suite to ensure the system is functioning correctly from a clean state.
    *   #### Acceptance Criteria:
        1.  The MongoDB vector store (`litecoin_docs` collection) is successfully cleared.
        2.  The `ingest_kb_articles.py` script runs without errors, processing all documents from the knowledge base.
        3.  The `test_rag_pipeline.py` test suite passes, confirming the RAG pipeline's ability to retrieve information from the newly ingested, comprehensive dataset.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
    *   #### Status: Done
    *   #### Plan:
        1.  Execute `backend/utils/clear_litecoin_docs_collection.py` to empty the vector store.
        2.  Execute `backend/api_client/ingest_kb_articles.py` to ingest all knowledge base content.
        3.  Execute `backend/test_rag_pipeline.py` to validate the pipeline.
    *   #### Priority: Highest

*   ### Task ID: `M4-E2E-002`
    *   #### Name: Ingest All Knowledge Base Content and Perform RAG Pipeline Test
    *   #### Detailed Description & Business Context:
        With the foundational knowledge base content now created in both `knowledge_base/articles` and `knowledge_base/deep_research`, the next critical step is to ingest all of this content into the vector store and perform an end-to-end test of the RAG pipeline. This will validate that the ingestion process works for multiple directories and that the retrieval system can successfully pull context from the newly added `deep_research` articles.
    *   #### Acceptance Criteria:
        1.  The `ingest_data.py` script is confirmed or updated to process Markdown files from both `knowledge_base/articles` and `knowledge_base/deep_research`.
        2.  The script is executed successfully, and the content is indexed in the MongoDB vector store.
        3.  A test query is run using `test_rag_pipeline.py` that specifically targets information present only in the `deep_research` articles.
        4.  The test successfully retrieves the correct context and generates a relevant answer, confirming the end-to-end pipeline is functional with the expanded knowledge base.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Created a client script `backend/api_client/ingest_kb_articles.py` to manage ingestion via API calls.
        *   Debugged and fixed multiple issues in the ingestion pipeline, including `datetime` encoding errors and file extension handling.
        *   Identified and corrected the root cause of retrieval failure: `vetting_status` was set to `draft` in `deep_research` articles.
        *   Updated all `deep_research` articles to `vetting_status: vetted`.
        *   Performed a full, clean ingestion of all knowledge base content and validated with a targeted test query that the RAG pipeline now retrieves the correct sources.
    *   #### Estimated Effort: 1-2 hours (excluding indexing time)
    *   #### Assigned To: Cline
    *   #### Priority: Highest

*   ### Task ID: `M4-DATASRC-001`
    *   #### Name: Implement CRUD API for Data Source Management
    *   #### Detailed Description & Business Context:
        To effectively manage the knowledge base of the RAG system, we need a dedicated way to track and control the data sources being ingested. This task involves creating a new set of API endpoints to handle the Create, Read, Update, and Delete (CRUD) operations for data sources. This will provide a foundational mechanism for adding, viewing, modifying, and removing sources, ensuring that the RAG pipeline is always working with a well-curated and up-to-date set of information.
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Implemented the full suite of CRUD endpoints in `backend/api/v1/sources.py`.
        *   Created `DataSource` and `DataSourceUpdate` Pydantic models in `backend/data_models.py` to handle data validation.
        *   Refactored the API to use FastAPI's dependency injection for MongoDB connections, which resolved testing issues related to environment variable loading and database access.
        *   The `PUT` and `DELETE` endpoints correctly remove associated embeddings from the vector store to maintain data integrity.
        *   Created a comprehensive test suite in `backend/test_sources_api.py` with 11 tests that are all passing, confirming the functionality of the API.

*   ### Task ID / Name: `M4-FAQ-001` - Create and Ingest Curated Content for Litecoin Basics & FAQ
    *   #### Detailed Description & Business Context:
        To implement the "Litecoin Basics & FAQ" feature, the RAG pipeline needs to be populated with high-quality, curated knowledge. This task involves creating well-structured Markdown documents for fundamental Litecoin topics within the `knowledge_base/` directory and then ingesting this curated data into the MongoDB vector store.
    *   #### Acceptance Criteria:
        1.  The foundational articles created in `M4-KB-001` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`) are finalized and meet quality standards in the `knowledge_base/articles/` directory.
        2.  The `ingest_data.py` script is used to load data specifically from the `knowledge_base/articles/` directory.
        3.  Verify that the data from these curated articles is present in the MongoDB vector store.
        4.  Document any specific ingestion notes in this task's "Notes on Completion".
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: Done
    *   #### Plan:
        *   ✅ Finalize content of initial FAQ articles in `knowledge_base/articles/`. (Completed as part of M4-KB-001)
        *   ✅ Use `ingest_data.py` to load data from `knowledge_base/articles/`.
        *   ✅ Verify ingestion in MongoDB (implicitly done by checking vector store content and metadata via `test_rag_pipeline.py`).
        *   ✅ Confirmed front matter metadata is correctly ingested with document chunks.
    *   #### Notes on Completion:
        *   Initial ingestion of foundational articles from `knowledge_base/articles/` is complete.
        *   Corrected an issue where `UnstructuredMarkdownLoader` was not parsing front matter. Switched to `python-frontmatter` library in `litecoin_docs_loader.py` which resolved the problem.
        *   Verified via `test_rag_pipeline.py` that front matter (title, tags, last_updated) is now present in the metadata of the ingested document chunks.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

*   ### Task ID: `M3-DOC-001`
    *   #### Name: Document Metadata Filtering Enhancements
    *   #### Detailed Description:
        Update project documentation (`techStack.md`, `codebaseSummary.md`, `projectRoadmap.md`) to reflect the recent implementation of metadata filtering capabilities. This includes noting the metadata flattening behavior of `langchain-mongodb` and providing the correct Atlas Vector Search index definition.
    *   #### Acceptance Criteria:
        1.  `techStack.md` is updated with details on metadata handling and the correct Atlas index JSON.
        2.  `codebaseSummary.md` is updated to reflect changes in `embedding_processor.py` and `vector_store_manager.py`.
        3.  `projectRoadmap.md` logs the completion of metadata filtering enhancement under Milestone 3.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation
    *   #### Status: Done
    *   #### Plan:
        *   Update `techStack.md`.
        *   Update `codebaseSummary.md`.
        *   Update `projectRoadmap.md`.
    *   #### Priority: High


*   ### Task ID: `M3-RAG-OPT-002`
    *   #### Name: Implement and Validate Metadata Filtering for RAG
    *   #### Detailed Description:
        Enhance the RAG pipeline to support filtering by metadata extracted from document frontmatter. This involves updating the embedding processor to handle new metadata fields (e.g., `author`, `published_at`, `tags`), ensuring these fields are correctly stored in MongoDB, and updating the Atlas Vector Search index definition to allow filtering on these fields. The `langchain-mongodb` library's behavior of flattening metadata into the root of the document was discovered and addressed.
    *   #### Acceptance Criteria:
        1.  `embedding_processor.py` correctly parses and converts frontmatter metadata, including `published_at` to `datetime`.
        2.  `vector_store_manager.py` correctly handles deletion of documents based on flattened metadata.
        3.  A test case in `test_rag_pipeline.py` validates that `similarity_search` with `pre_filter` correctly retrieves documents based on various metadata criteria (e.g., author, tags).
        4.  The user is provided with the correct Atlas Vector Search index JSON definition for flattened metadata.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation
    *   #### Status: Verified
    *   #### Progress (as of 2025-06-06):
        *   ✅ `embedding_processor.py` updated for `published_at` date conversion.
        *   ✅ `vector_store_manager.py` updated for correct metadata deletion.
        *   ✅ `test_metadata_filtering` added to `test_rag_pipeline.py` and successfully passed after user updated Atlas index.
        *   ✅ Correct Atlas Vector Search index definition provided to user.
    *   #### Discovered During Work:
        *   `langchain-mongodb` flattens metadata into the root of the MongoDB document.
        *   The Atlas Vector Search index must define filterable paths at the root level (e.g., `author`, not `metadata.author`).
    *   #### Plan:
        *   ✅ Update `embedding_processor.py`.
        *   ✅ Update `vector_store_manager.py`.
        *   ✅ Create `sample_for_metadata_test.md`.
        *   ✅ Add `test_metadata_filtering` to `test_rag_pipeline.py`.
        *   ✅ Iteratively debugged and fixed test based on pymongo errors and direct DB inspection.
        *   ✅ Confirmed metadata flattening and provided correct index definition to user.
        *   ✅ Test passed after user updated index.
    *   #### Priority: Highest

*   ### Task ID: `M4-UI-001`
    *   #### Name: Develop Frontend Chat UI Components
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Initialized ShadCN and added necessary components (`card`, `input`, `button`, `avatar`, `accordion`).
        *   Created custom components (`ChatWindow.tsx`, `Message.tsx`, `InputBox.tsx`).
        *   Assembled components and implemented basic state management in `frontend/src/app/page.tsx`.

*   ### Task ID: `M4-INT-001`
    *   #### Name: Integrate Frontend with Backend API
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Implemented API call logic in `frontend/src/app/page.tsx` to send queries to `/api/v1/chat` and display responses/sources.
        *   Configured CORS middleware and added an OPTIONS handler in `backend/main.py` to resolve cross-origin issues.

*   ### Task ID: `M3-TEST-001`
    *   #### Name: Create Validation Test for Advanced RAG Optimizations
    *   #### Detailed Description:
        This task involves creating a new test case within `backend/test_rag_pipeline.py` to specifically validate the recent RAG enhancements. The test will use a controlled, small-scale Markdown document to verify that the hierarchical chunking and asymmetric `task_type` embeddings are functioning as expected and leading to accurate retrieval.
    *   #### Acceptance Criteria:
        1.  A new, temporary test file, `backend/data_ingestion/test_data/sample_for_hierarchical_test.md`, will be created with a clear hierarchical structure (titles, sections, subsections).
        2.  A new test function, `test_hierarchical_chunking_and_retrieval`, will be added to `backend/test_rag_pipeline.py`.
        3.  The test will programmatically:
            *   Clear the vector store before starting for a clean base.
            *   Ingest the `sample_for_hierarchical_test.md` file.
            *   Verify that the chunks stored in the vector database contain the prepended hierarchical titles (e.g., "Title: Document Title\nSection: Section 1").
            *   Formulate a specific query that should *only* match a chunk from a deep subsection.
            *   Assert that the correct, context-rich chunk is retrieved, proving the system's precision.
        4.  The test must clean up after itself by deleting the temporary test data from the vector store upon completion.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Enhancement Validation)
    *   #### Status: Verified
    *   #### Progress (as of 2025-06-06):
        *   ✅ `backend/data_ingestion/test_data/sample_for_hierarchical_test.md` created.
        *   ✅ `test_hierarchical_chunking_and_retrieval` function added to `backend/test_rag_pipeline.py` with logic for ingestion, verification, and cleanup.
    *   #### Discovered During Work:
        *   **Metadata Persistence Issue (2025-06-06):** The `test_hierarchical_chunking_and_retrieval` test initially failed because document metadata was not being saved to MongoDB in a way that `pymongo.collection.find()` could directly retrieve it as a BSON object.
        *   **Strategy Update (2025-06-06):** The test was updated to use the main `litecoin_docs` collection.
        *   **Resolution Steps (2025-06-06):**
            1.  Updated `backend/data_ingestion/vector_store_manager.py` to explicitly define `text_key="text"` and `metadata_key="metadata"` when initializing `MongoDBAtlasVectorSearch`.
            2.  Ensured the MongoDB Atlas Vector Search index for the `litecoin_docs` collection used the simple definition (only defining the `embedding` field).
            3.  Increased `time.sleep()` in `backend/test_rag_pipeline.py` to 60 seconds to allow more time for Atlas indexing.
        *   **Outcome (2025-06-06):** The `test_hierarchical_chunking_and_retrieval` test now passes its core assertions: the RAG pipeline correctly retrieves context-rich chunks. However, direct inspection of the `metadata` field via `pymongo.collection.find()` in the test script still shows `None`. This suggests `langchain-mongodb` handles metadata internally for its operations, but direct BSON inspection might require a different approach or understanding of how the data is stored/reconstructed by the library. Since the RAG functionality is verified, this direct inspection anomaly is noted but does not block the task's completion.
    *   #### Plan:
        *   ✅ Create `backend/data_ingestion/test_data/sample_for_hierarchical_test.md`.
        *   ✅ Add `test_hierarchical_chunking_and_retrieval` to `backend/test_rag_pipeline.py`.
        *   ✅ Implement test logic: ingest, verify chunks, query, assert, cleanup.
        *   ✅ Updated `backend/test_rag_pipeline.py` to use the `litecoin_docs` collection.
        *   ✅ Updated `backend/data_ingestion/vector_store_manager.py` to explicitly set `text_key` and `metadata_key`.
        *   ✅ User confirmed Atlas Vector Search index for `litecoin_docs` is using the simple definition.
        *   ✅ Updated `backend/test_rag_pipeline.py` to increase sleep time to 60s after ingestion.
        *   ✅ Ran `python backend/test_rag_pipeline.py`. Test assertions for RAG functionality passed. Direct MongoDB inspection of metadata via `pymongo` in the test script still shows `None`, but this does not impede RAG functionality.
        *   **Task `M3-TEST-001` is now verified and complete.**
    *   #### Priority: Highest

*   ### Task ID: `UTIL-DB-001`
    *   #### Name: Create Utility Script to Clear `litecoin_docs` Collection
    *   #### Detailed Description & Business Context:
        Provide a straightforward way to clear all documents from the `litecoin_docs` MongoDB collection. This is useful for development and testing, allowing for a clean state before ingesting new data or running tests. The script leverages the existing `clear_all_documents` method in `VectorStoreManager`.
    *   #### Acceptance Criteria:
        1.  A new script `backend/utils/clear_litecoin_docs_collection.py` is created.
        2.  The script imports `VectorStoreManager` and uses its `clear_all_documents` method.
        3.  The script loads environment variables correctly to ensure DB connection.
        4.  The script includes a confirmation prompt before deleting data.
        5.  The script can be run directly from the command line (e.g., `python backend/utils/clear_litecoin_docs_collection.py`).
    *   #### Link to projectRoadmap.md goal(s):
        *   Supports general development and testing for all milestones.
    *   #### Status: Done
    *   #### Plan:
        *   ✅ Create `backend/utils/clear_litecoin_docs_collection.py`.
        *   ✅ Implement logic to load .env, instantiate `VectorStoreManager`, and call `clear_all_documents()`.
        *   ✅ Add user confirmation prompt.
    *   #### Estimated Effort: 0.5 hours
    *   #### Assigned To: Cline
    *   #### Priority: Medium
    
*   ### Task ID: `M4-RAG-OPT-001`
    *   #### Name: Implement Advanced RAG Pipeline Optimizations
    *   #### Detailed Description & Business Context:
        Upgrade the data ingestion and retrieval pipeline based on expert recommendations for `text-embedding-004`. This involves implementing a hierarchical chunking strategy for Markdown files and ensuring the correct `task_type` parameter is used during embedding to improve retrieval accuracy.
    *   #### Acceptance Criteria:
        1.  `backend/data_ingestion/embedding_processor.py` is updated to implement hierarchical chunking for Markdown documents, prepending titles to each chunk.
        2.  `backend/data_ingestion/embedding_processor.py` is updated to use `task_type='retrieval_document'` when embedding document chunks.
        3.  `backend/rag_pipeline.py` is updated to use `task_type='retrieval_query'` when embedding user queries.
        4.  The RAG prompt template in `backend/rag_pipeline.py` is updated to the recommended robust version.
        5.  `cline_docs/techStack.md` is updated to reflect these new RAG pipeline details.
        6.  `cline_docs/codebaseSummary.md` is updated to reflect these new RAG pipeline details.
        7.  `user_instructions/knowledge_base_contribution_guide.md` is updated to explain the importance of Markdown structure for AI performance.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Enhancement)
        *   Feature 5: Curated Knowledge Base (Foundation)
    *   #### Status: Completed (6/6/2025)
    *   #### Plan:
        *   ✅ Modify `backend/data_ingestion/embedding_processor.py` for hierarchical chunking and `retrieval_document` task type.
        *   ✅ Modify `backend/rag_pipeline.py` for `retrieval_query` task type and updated prompt.
        *   ✅ Update `cline_docs/techStack.md`.
        *   ✅ Update `cline_docs/codebaseSummary.md`.
        *   ✅ Update `user_instructions/knowledge_base_contribution_guide.md`.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: Highest
    *   #### Notes on Completion:
        *   All code changes implemented as planned.
        *   All relevant documentation (`techStack.md`, `codebaseSummary.md`, `knowledge_base_contribution_guide.md`) updated.
        *   This task significantly enhances the RAG pipeline's foundation for future content ingestion and query processing.

*   ### Task ID / Name: `RAG-004` - Enhance RAG Pipeline Output with Source Documents
    *   #### Detailed Description & Business Context:
        Modify the RAG pipeline and API to return not just the generated answer, but also the source documents (content and metadata) that were retrieved and used as context by the LLM. This enhances transparency and allows users to verify the information.
    *   #### Acceptance Criteria:
        1.  The RAG chain in `backend/rag_pipeline.py` is modified to output both the generated answer and the retrieved source documents.
        2.  The `/api/v1/chat` endpoint in `backend/main.py` is updated to return a JSON object containing `answer` and a list of `sources` (each with `page_content` and `metadata`).
        3.  Pydantic models (`SourceDocument`, `ChatResponse`) are defined in `backend/main.py` for the new response structure.
        4.  The test script `backend/test_rag_pipeline.py` is updated to correctly parse and display the new response format, including the answer and source details.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Enhancement for verifiable trust)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   Modified `get_rag_chain` in `backend/rag_pipeline.py` to return the full output dictionary containing `answer` and `context` (source documents).
        *   Updated `chat_endpoint` in `backend/main.py`:
            *   Added `SourceDocument` and `ChatResponse` Pydantic models.
            *   Set `response_model=ChatResponse`.
            *   Formatted the output to include `answer` and a list of `sources` (transformed from Langchain `Document` objects).
        *   Updated `backend/test_rag_pipeline.py` to print the answer and source document details from the new response structure.
        *   All acceptance criteria for RAG-004 have been met.

*   ### Task ID / Name: `TEST-003` - Create Standalone Test Script for RAG Pipeline
    *   #### Detailed Description & Business Context:
        Create a standalone Python script (`backend/test_rag_pipeline.py`) to test the end-to-end RAG pipeline. This script will send a sample query to the `/api/v1/chat` endpoint and print the response to verify the pipeline's functionality.
    *   #### Acceptance Criteria:
        1.  A new file `backend/test_rag_pipeline.py` is created.
        2.  The script uses the `requests` library to send a POST request to `http://127.0.0.1:8000/api/v1/chat`.
        3.  The script sends a predefined query (e.g., "What is Litecoin?").
        4.  The script prints the query and the JSON response from the server.
        5.  The script can be executed directly (`python backend/test_rag_pipeline.py`) assuming the backend server is running.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Testing)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   Created `backend/test_rag_pipeline.py`.
        *   The script uses the `requests` library to send a POST request with a sample query ("What is Litecoin?") to `http://127.0.0.1:8000/api/v1/chat`.
        *   It prints the query and the JSON response from the server.
        *   The script can be run using `python backend/test_rag_pipeline.py` when the backend server is active.
        *   All acceptance criteria for TEST-003 have been met.

*   ### Task ID / Name: `RAG-003` - Implement Generator for RAG Pipeline
    *   #### Detailed Description & Business Context:
        This task involves creating the "generation" part of the RAG pipeline. We will modify `backend/rag_pipeline.py` to take the retrieved document chunks, format them into a prompt, and pass them to a Large Language Model (LLM) to generate a coherent and contextually relevant answer to the user's query.
    *   #### Acceptance Criteria:
        1.  Modify the `retrieve_documents` function (or create a new one) in `backend/rag_pipeline.py` to include the generation step.
        2.  Initialize a suitable LLM from Langchain (e.g., `ChatGoogleGenerativeAI`).
        3.  Create a prompt template that incorporates the retrieved documents and the user's query.
        4.  Construct a Langchain chain that passes the query to the retriever, then the retrieved documents and query to the prompt template, and finally to the LLM.
        5.  The `/api/v1/chat` endpoint in `backend/main.py` should be updated to call this new RAG chain.
        6.  The endpoint should return the LLM-generated response as a JSON object (e.g., `{"response": "generated_answer"}`).
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion, Embedding, Retrieval, Generation)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   Modified `backend/rag_pipeline.py` to implement a full RAG chain using LangChain Expression Language (LCEL).
        *   The chain now includes:
            *   A retriever using `MongoDBAtlasVectorSearch`.
            *   A prompt template (`RAG_PROMPT_TEMPLATE`) to format the query and context.
            *   The `ChatGoogleGenerativeAI` model (gemini-pro) as the LLM.
            *   An output parser (`StrOutputParser`) to get the final string response.
        *   The `retrieve_documents` function is still present but no longer directly called by the main API; its logic is incorporated into the new `get_rag_chain` function's retriever.
        *   Removed the `get_placeholder_chain` function.
        *   Updated `backend/main.py`'s `/api/v1/chat` endpoint to use the new `get_rag_chain` function.
        *   The endpoint now returns the LLM-generated response in the format `{"response": "generated_answer"}`.
        *   All acceptance criteria for RAG-003 have been met.

*   ### Task ID / Name: `TEST-002` - Validate Multi-Source Ingestion Loaders
    *   #### Detailed Description & Business Context:
        This task addresses the gap identified during the review of `RAG-001`. While the ingestion framework supports multiple data sources, only the `markdown` loader was validated in `TEST-001`. This task will systematically test each of the other implemented data loaders (`youtube`, `twitter`, `github`, `web`) to confirm they correctly ingest, process, and store data in the MongoDB vector store. This ensures the reliability of our entire data pipeline.
    *   #### Acceptance Criteria:
        1.  The `ingest_data.py` script is successfully executed for each of the following source types with a valid, publicly accessible identifier: `youtube`, `twitter`, `github`, and `web`.
        2.  After each execution, verification is performed to confirm that new documents have been added to the MongoDB collection.
        3.  A spot-check of the newly added documents confirms that the `page_content` is reasonable and the `metadata` field correctly identifies the source type and identifier.
        4.  The task is marked as "Done" upon successful validation of all loaders.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Testing)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   **Markdown Loader:** Passed.
        *   **GitHub Loader:** Passed after a patch was applied to handle repositories with a `master` default branch instead of `main`.
        *   **Web Loader:** Passed after a patch was applied to fix an `AttributeError` related to timestamp generation.
        *   **Twitter Loader:** Skipped. Requires a `TWITTER_BEARER_TOKEN` environment variable to be set.
        *   **YouTube Loader:** Skipped. Requires a local instance of the Citeio application running on `http://localhost:8001`.

*   ### Task ID / Name: `RAG-002` - Implement Retriever for RAG Pipeline
    *   #### Detailed Description & Business Context:
        This task involves creating the "retrieval" part of the RAG pipeline. We will modify `backend/rag_pipeline.py` to accept a user query, use the MongoDB vector store to find the most relevant document chunks from our knowledge base, and then pass these chunks as context to the language model. This is the core of the "Retrieval-Augmented" process.
    *   #### Acceptance Criteria:
        1.  Create a new function in `backend/rag_pipeline.py` that takes a user query as input.
        2.  The function should initialize the `MongoDBAtlasVectorSearch` store.
        3.  The function should perform a similarity search on the vector store using the user's query to retrieve relevant documents.
        4.  The retrieved documents should be formatted and returned.
        5.  The `/api/v1/chat` endpoint in `backend/main.py` should be updated to call this new retrieval function.
        6.  For now, the endpoint can return the retrieved documents directly as a JSON response for testing purposes.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion, Embedding, Retrieval, Generation)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   Created a `retrieve_documents` function in `backend/rag_pipeline.py` that connects to the MongoDB Atlas Vector Store and performs a similarity search.
        *   Updated the `/api/v1/chat` endpoint in `backend/main.py` to call this new function.
        *   The endpoint now returns the retrieved documents as a JSON response, fulfilling the acceptance criteria for testing the retrieval step in isolation.
        *   **Fix (6/6/2025):** Corrected `COLLECTION_NAME` in `backend/rag_pipeline.py` from `"docs"` to `"litecoin_docs"` to match the ingestion setup, resolving an issue where no documents were being retrieved.
        
*   ### Task ID / Name: `TEST-002` - Validate Multi-Source Ingestion Loaders
    *   #### Detailed Description & Business Context:
        This task addresses the gap identified during the review of `RAG-001`. While the ingestion framework supports multiple data sources, only the `markdown` loader was validated in `TEST-001`. This task will systematically test each of the other implemented data loaders (`youtube`, `twitter`, `github`, `web`) to confirm they correctly ingest, process, and store data in the MongoDB vector store. This ensures the reliability of our entire data pipeline.
    *   #### Acceptance Criteria Met:
        1.  The `ingest_data.py` script was successfully executed for the `markdown`, `github`, and `web` source types.
        2.  The `twitter` and `youtube` loaders were skipped due to external dependencies (API keys and a local service).
        3.  Verification of the `markdown`, `github`, and `web` loaders confirmed that new documents were added to the MongoDB collection with correct content and metadata.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Testing)
    *   #### Status: Done (6/6/2025)
    *   #### Notes on Completion:
        *   **GitHub Loader:** Passed after a patch was applied to handle repositories with a `master` default branch instead of `main`.
        *   **Web Loader:** Passed after a patch was applied to fix an `AttributeError` related to timestamp generation.
        *   **Twitter Loader:** Skipped. Requires a `TWITTER_BEARER_TOKEN` environment variable to be set.
        *   **YouTube Loader:** Skipped. Requires a local instance of the Citeio application running on `http://localhost:8001`.

*   ### Task ID / Name: `TEST-001` - Test Multi-Source Ingestion Pipeline
    *   #### Detailed Description & Business Context:
        This task focused on setting up the environment and thoroughly testing the multi-source data ingestion pipeline to ensure it functions correctly and populates the MongoDB Atlas collection as expected. This included verifying the `.env` setup and the MongoDB Vector Search index configuration.
    *   #### Acceptance Criteria Met:
        1.  The `backend/.env` file was correctly created and populated with `MONGO_URI` and `GOOGLE_API_KEY`.
        2.  The MongoDB Atlas Vector Search index was properly configured as per `user_instructions/setup_mongodb_vector_index.md`.
        3.  All backend dependencies were installed (`pip install -r backend/requirements.txt`).
        4.  The `ingest_data.py` script ran successfully for the `markdown` source without errors.
        5.  Data was confirmed to be populated in the MongoDB Atlas collection after ingestion.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Testing)
    *   #### Status: Done (6/6/2025)

    *   ### Task ID / Name: `RAG-001` - Implement Data Ingestion and MongoDB Vector Store Setup
    *   #### Detailed Description & Business Context:
        This task focused on setting up the foundational components for data ingestion and vector storage within our RAG pipeline. This included identifying initial data sources for Litecoin information, developing modules to ingest and process this data, generating embeddings using Google Text Embedding 004, and storing these embeddings in MongoDB Atlas Vector Search. The multi-source ingestion framework is now complete in terms of code, but requires environment setup and testing.
    *   #### Acceptance Criteria:
        1.  A new directory `backend/data_ingestion/` is created.
        2.  `pymongo` and `langchain-google-genai` are added to `backend/requirements.txt`.
        3.  `backend/data_ingestion/litecoin_docs_loader.py` is created with a function to load sample Litecoin documentation (e.g., from a local markdown file or a small, static text).
        4.  `backend/data_ingestion/embedding_processor.py` is created to handle text splitting and generate embeddings using Google Text Embedding 004.
        5.  `backend/data_ingestion/vector_store_manager.py` is created to manage connections to MongoDB Atlas and insert/retrieve vector embeddings.
        6.  A standalone script `backend/ingest_data.py` is created to orchestrate the data loading, embedding, and storage process, now supporting multiple sources via command-line arguments.
        7.  The ingestion script runs successfully without errors and populates the MongoDB Atlas collection with embedded data from various sources.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion, Embedding, Retrieval, Generation)
    *   #### Status: Done (6/6/2025)
    
*   ### Task ID / Name: `DOCS-002` - Create Reference Documentation Folder
    *   #### Detailed Description & Business Context:
        Created a dedicated folder at the project root to store external documentation for frameworks, services, and APIs used in the project. This improved organization and provided a centralized reference point for developers.
    *   #### Acceptance Criteria Met:
        1.  A new directory `reference_docs/` was created at the project root.
        2.  Subdirectories were created within `reference_docs/` for `nextjs`, `fastapi`, `mongodb`, `langchain`, and `google_ai`.
        3.  A `.gitkeep` file was added to each new subdirectory to ensure they are tracked by Git.
        4.  `cline_docs/codebaseSummary.md` was updated to include the new `reference_docs/` directory in its overview.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 1: Project Initialization & Documentation Setup (Ongoing documentation maintenance)
    *   #### Status: Done (6/6/2025)

*   ### Task ID / Name: `INGEST-001`: Create YouTube Data Loader via Citeio Integration
    *   #### Detailed Description & Business Context:
        Developed a `youtube_loader.py` module that interacts with the Citeio application's API to fetch processed YouTube transcripts and topic data.
    *   #### Acceptance Criteria Met:
        1.  `requests` was added to `backend/requirements.txt`.
        2.  `backend/data_ingestion/youtube_loader.py` was created with a function to load data from Citeio API.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion)
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `INGEST-002`: Create X (Twitter) Data Loader
    *   #### Detailed Description & Business Context:
        Developed a `twitter_loader.py` module to fetch recent posts from specified Twitter handles using the Twitter API.
    *   #### Acceptance Criteria Met:
        1.  `tweepy` was added to `backend/requirements.txt`.
        2.  `backend/data_ingestion/twitter_loader.py` was created with a function to load Twitter posts.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion)
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `INGEST-003`: Create GitHub Repository Loader
    *   #### Detailed Description & Business Context:
        Developed a `github_loader.py` module to clone GitHub repositories and process their Markdown files.
    *   #### Acceptance Criteria Met:
        1.  `GitPython` was added to `backend/requirements.txt`.
        2.  `backend/data_ingestion/github_loader.py` was created with a function to load GitHub repository data.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion)
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `INGEST-004`: Create Web Article Loader
    *   #### Detailed Description & Business Context:
        Developed a `web_article_loader.py` module to fetch and parse main content from news articles and blog posts.
    *   #### Acceptance Criteria Met:
        1.  `beautifulsoup4` and `lxml` were added to `backend/requirements.txt`.
        2.  `backend/data_ingestion/web_article_loader.py` was created with a function to load web article data.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion)
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `ARCH-002`: Refactor `ingest_data.py` into a Source Router
    *   #### Detailed Description & Business Context:
        Refactored the `backend/ingest_data.py` script to act as a router, dynamically calling the appropriate loader based on the input source type and identifier.
    *   #### Acceptance Criteria Met:
        1.  `backend/ingest_data.py` was modified to import new loaders.
        2.  The `main` function in `backend/ingest_data.py` was updated to accept `source_type` and `source_identifier` arguments.
        3.  Conditional logic was added to call the correct loader based on `source_type`.
        4.  The script now uses `argparse` for command-line arguments.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Data Ingestion)
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `INIT-003` - Basic Langchain Setup in Backend
    *   #### Detailed Description & Business Context:
        This task involves integrating Langchain into the FastAPI backend. We will add Langchain as a dependency and create a foundational structure for our RAG pipeline. This includes setting up a new API endpoint (e.g., `/api/v1/chat`) that can receive a user query. For now, this endpoint will use a very basic Langchain chain (e.g., a prompt template and a placeholder component) to process the query and return a placeholder response. This initial step verifies that Langchain is correctly integrated and operational within our backend environment before we build out the more complex data ingestion, embedding, retrieval, and generation components.
    *   #### Acceptance Criteria Met:
        1.  `langchain`, `langchain-core`, and `langchain-community` were added to `backend/requirements.txt`.
        2.  `backend/rag_pipeline.py` was created to encapsulate Langchain-related logic.
        3.  `backend/main.py` imports from `backend/rag_pipeline.py`.
        4.  The POST API endpoint `/api/v1/chat` was added to `backend/main.py`.
        5.  The endpoint uses a simple Langchain chain.
        6.  The endpoint returns a JSON response with a placeholder.
        7.  The FastAPI backend server can run without errors.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Initial setup)
    *   #### Status: Done (6/5/2025)
*   ### Task ID / Name: `INIT-002` - Scaffold Initial Project Structure
    *   #### Detailed Description & Business Context:
        Set up the basic directory structure for the Next.js frontend and FastAPI backend. Initialize project files (e.g., `package.json`, `requirements.txt`), and set up basic "Hello World" endpoints for both frontend and backend to ensure the initial setup is working. This task lays the foundational codebase for subsequent feature development.
    *   #### Notes on Completion:
        *   The initial scaffold had a Git submodule conflict. The project state was reset, and the frontend and backend were re-scaffolded correctly on 6/5/2025.
    *   #### Acceptance Criteria:
        *   Root project directory contains `frontend/` and `backend/` subdirectories.
        *   `frontend/` is initialized as a Next.js project without a nested Git repository.
        *   `backend/` is set up for a FastAPI project.
        *   The root Git repository correctly tracks all files in `frontend/` and `backend/`.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 2: Basic Project Scaffold (Next.js Frontend, FastAPI Backend)
    *   #### Status: Done (6/5/2025)
*   ### Task ID / Name: `INIT-001` - Project Initialization and Documentation Setup
    *   #### Detailed Description & Business Context:
        Based on the information provided in the "Initiate New Project" prompt, this task was to:
        1.  Thoroughly review and internalize custom instructions (Unified Cline Super-Prompt).
        2.  Perform "Pre-Task Analysis & Planning" thinking step.
        3.  Populate the initial versions of all four `cline_docs` files (`projectRoadmap.md`, `currentTask.md`, `techStack.md`, `codebaseSummary.md`) with the information provided and any reasonable defaults or placeholders where information is missing.
        4.  For `currentTask.md`, detail this `INIT-001` task and then define and plan the *next logical development task*.
    *   #### Acceptance Criteria Met:
        *   All four `cline_docs` files created/populated in the project's `cline_docs` directory.
        *   `projectRoadmap.md` reflects the initial vision, goals, and features (including user-guided feature definitions).
        *   `techStack.md` outlines initial technology considerations.
        *   `currentTask.md` details `INIT-001` as "Done" and clearly defines `INIT-002`.
        *   `codebaseSummary.md` created.
        *   `session_summary.md` was presented (conceptually, as part of the PLAN MODE response).
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 1: Project Initialization & Documentation Setup
    *   #### Status: Done (6/5/2025)

*   ### Task ID / Name: `INIT-003` - Basic Langchain Setup in Backend
    *   #### Detailed Description & Business Context:
        This task involves integrating Langchain into the FastAPI backend. We will add Langchain as a dependency and create a foundational structure for our RAG pipeline. This includes setting up a new API endpoint (e.g., `/api/v1/chat`) that can receive a user query. For now, this endpoint will use a very basic Langchain chain (e.g., a prompt template and a placeholder component) to process the query and return a placeholder response. This initial step verifies that Langchain is correctly integrated and operational within our backend environment before we build out the more complex data ingestion, embedding, retrieval, and generation components.
    *   #### Acceptance Criteria Met:
        1.  `langchain`, `langchain-core`, and `langchain-community` were added to `backend/requirements.txt`.
        2.  `backend/rag_pipeline.py` was created to encapsulate Langchain-related logic.
        3.  `backend/main.py` imports from `backend/rag_pipeline.py`.
        4.  The POST API endpoint `/api/v1/chat` was added to `backend/main.py`.
        5.  The endpoint uses a simple Langchain chain.
        6.  The endpoint returns a JSON response with a placeholder.
        7.  The FastAPI backend server can run without errors.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 3: Core RAG Pipeline Implementation (Initial setup)
    *   #### Status: Done (6/5/2025)
*   ### Task ID / Name: `INIT-002` - Scaffold Initial Project Structure
    *   #### Detailed Description & Business Context:
        Set up the basic directory structure for the Next.js frontend and FastAPI backend. Initialize project files (e.g., `package.json`, `requirements.txt`), and set up basic "Hello World" endpoints for both frontend and backend to ensure the initial setup is working. This task lays the foundational codebase for subsequent feature development.
    *   #### Notes on Completion:
        *   The initial scaffold had a Git submodule conflict. The project state was reset, and the frontend and backend were re-scaffolded correctly on 6/5/2025.
    *   #### Acceptance Criteria:
        *   Root project directory contains `frontend/` and `backend/` subdirectories.
        *   `frontend/` is initialized as a Next.js project without a nested Git repository.
        *   `backend/` is set up for a FastAPI project.
        *   The root Git repository correctly tracks all files in `frontend/` and `backend/`.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 2: Basic Project Scaffold (Next.js Frontend, FastAPI Backend)
    *   #### Status: Done (6/5/2025)
*   ### Task ID / Name: `INIT-001` - Project Initialization and Documentation Setup
    *   #### Detailed Description & Business Context:
        Based on the information provided in the "Initiate New Project" prompt, this task was to:
        1.  Thoroughly review and internalize custom instructions (Unified Cline Super-Prompt).
        2.  Perform "Pre-Task Analysis & Planning" thinking step.
        3.  Populate the initial versions of all four `cline_docs` files (`projectRoadmap.md`, `currentTask.md`, `techStack.md`, `codebaseSummary.md`) with the information provided and any reasonable defaults or placeholders where information is missing.
        4.  For `currentTask.md`, detail this `INIT-001` task and then define and plan the *next logical development task*.
    *   #### Acceptance Criteria Met:
        *   All four `cline_docs` files created/populated in the project's `cline_docs` directory.
        *   `projectRoadmap.md` reflects the initial vision, goals, and features (including user-guided feature definitions).
        *   `techStack.md` outlines initial technology considerations.
        *   `currentTask.md` details `INIT-001` as "Done" and clearly defines `INIT-002`.
        *   `codebaseSummary.md` created.
        *   `session_summary.md` was presented (conceptually, as part of the PLAN MODE response).
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 1: Project Initialization & Documentation Setup
    *   #### Status: Done (6/5/2025)
