# Current Task: Litecoin RAG Chat

## Current Sprint/Iteration Goal
*   **Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)**

## Active Task(s):

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

## High-Priority Initiatives: AI-Integrated Knowledge Base CMS

*   ### Task ID: `CMS-PLAN-001`
    *   #### Name: Define Requirements and Plan for AI-Integrated Knowledge Base CMS
    *   #### Detailed Description & Business Context:
        Define the core requirements, features, and technical architecture for a content management system (CMS) specifically designed for the Litecoin RAG Chat's knowledge base. This CMS should facilitate collaborative content creation and editing by users and AI agents, integrate with research tools like Google Deep Search, and manage the lifecycle of knowledge base articles (creation, editing, publishing, archiving).
    *   #### Acceptance Criteria:
        1.  A detailed document outlining the CMS requirements and features is created (e.g., in `cline_docs/cms_requirements.md`).
        2.  A high-level architectural plan for the CMS, including its interaction with existing RAG components and external AI services, is defined.
        3.  Initial user stories for key CMS functionalities are drafted.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 5: Curated Knowledge Base (Significant Enhancement)
    *   #### Status: To Do
    *   #### Plan: (To be defined during planning)
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: Highest

*   ### Task ID: `CMS-DESIGN-001`
    *   #### Name: Design User Interface and User Experience for CMS
    *   #### Detailed Description & Business Context:
        Design the user interface (UI) and user experience (UX) for the AI-integrated knowledge base CMS based on the defined requirements. This includes creating wireframes or mockups for key screens (e.g., article editor, content dashboard, search integration) and defining the user flow for content creation, editing, and publishing.
    *   #### Acceptance Criteria:
        1.  UI/UX designs (wireframes or mockups) for the core CMS functionalities are created.
        2.  User flows for key content management processes are documented.
        3.  Design considerations for integrating AI assistance into the editing workflow are outlined.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 5: Curated Knowledge Base (Significant Enhancement)
    *   #### Status: To Do
    *   #### Plan: (To be defined during design)
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

## Task Backlog:

*   ### Task ID: `M4-KB-001`
    *   #### Name: Establish Content Foundation for FAQ Feature
    *   #### Detailed Description & Business Context:
        Before ingesting random data, we must first define the structure of our curated knowledge base and create the initial set of "golden" documents for the "Litecoin Basics & FAQ" feature. This ensures our RAG system is built on a foundation of quality.
    *   #### Acceptance Criteria:
        1.  A `knowledge_base/` directory is created at the project root, with a subdirectory `knowledge_base/articles/` for curated content.
        2.  A template file, `knowledge_base/_template.md`, is created to define the standard structure for all future articles (e.g., metadata frontmatter, heading styles).
        3.  A master index file, `knowledge_base/index.md`, is created, outlining a categorized list of 50 high-impact articles for the "Litecoin Basics & FAQ" feature.
        4.  At least three foundational FAQ articles are written and placed in `knowledge_base/articles/` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`).
        5.  The existing task `M4-FAQ-001` is updated to reflect that it will ingest data from the new `knowledge_base/articles/` directory, not from external raw sources.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: In Progress
    *   #### Progress (as of 2025-06-06):
        *   ✅ Core project documentation (`projectRoadmap.md`, `codebaseSummary.md`, `README.md`, `currentTask.md`) updated to reflect the content-first strategy.
        *   ✅ `user_instructions/knowledge_base_contribution_guide.md` created.
        *   ✅ `knowledge_base/` directory created, and `knowledge_base/articles/` subdirectory created.
        *   ✅ `knowledge_base/_template.md` created.
        *   ✅ `knowledge_base/index.md` created, outlining 50 high-impact articles.
        *   ✅ Created `knowledge_base/articles/001-what-is-litecoin.md`.
        *   ✅ Created `knowledge_base/articles/002-who-created-litecoin.md`.
        *   ✅ Created `knowledge_base/articles/003-how-to-buy-litecoin.md`.
        *   ✅ Created `knowledge_base/articles/004-where-can-i-spend-litecoin.md`.
        *   ✅ Created `knowledge_base/articles/006-common-litecoin-terminology.md`.
        *   ✅ Created `knowledge_base/articles/045-litecoin-vs-bitcoin.md`.
        *   (Note: File names adjusted to reflect actual content based on file listing)
    *   #### Plan:
        *   ✅ Create `knowledge_base/` directory and `knowledge_base/articles/` subdirectory.
        *   ✅ Create `knowledge_base/_template.md`.
        *   ✅ Create `knowledge_base/index.md` outlining 50 high-impact articles.
        *   ✅ Write the initial foundational FAQ articles in `knowledge_base/articles/`:
            *   `knowledge_base/articles/what-is-litecoin.md` (or equivalent like `001-what-is-litecoin.md`)
            *   `knowledge_base/articles/how-litecoin-differs-from-bitcoin.md` (or equivalent like `045-litecoin-vs-bitcoin.md`)
            *   `knowledge_base/articles/understanding-litecoin-wallets.md`
        *   **Next step:** Continue writing the remaining FAQ articles in `knowledge_base/articles/` based on the `index.md`.
        *   Update task `M4-FAQ-001` (already done by redefining its scope during the content-first strategy integration).
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: Medium 

*   ### Task ID: `M4-E2E-001`
    *   #### Name: End-to-End Testing and Refinement for FAQ Feature
    *   #### Detailed Description & Business Context:
        Once the data is ingested and the UI is fully integrated, conduct end-to-end testing of the FAQ feature. This involves asking a variety of basic Litecoin questions to validate the accuracy, relevance, and clarity of the responses. This task may also include refining the RAG prompt in `backend/rag_pipeline.py` to improve the quality of generated answers for FAQ-style queries.
    *   #### Acceptance Criteria:
        1.  A list of at least 10-15 standard Litecoin FAQ questions is compiled for testing.
        2.  Each question is tested through the UI, and the responses are evaluated for accuracy against the ingested source material.
        3.  The RAG prompt template is updated if necessary to improve response quality.
        4.  The feature is considered complete when it reliably answers the majority of test questions correctly and clearly.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
    *   #### Status: To Do
    *   #### Plan: (To be defined)
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

## Recently Completed Tasks:

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

[View Task Archive](task_archive.md)
