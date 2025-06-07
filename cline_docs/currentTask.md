# Current Task: Litecoin RAG Chat

## Current Sprint/Iteration Goal
*   **Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)**

## Active Task(s):

*   ### Task ID: `M4-KB-001`
    *   #### Name: Establish Content Foundation for FAQ Feature
    *   #### Detailed Description & Business Context:
        Before ingesting random data, we must first define the structure of our curated knowledge base and create the initial set of "golden" documents for the "Litecoin Basics & FAQ" feature. This ensures our RAG system is built on a foundation of quality.
    *   #### Acceptance Criteria:
        1.  A new directory, `knowledge_base/`, is created at the project root.
        2.  A template file, `knowledge_base/_template.md`, is created to define the standard structure for all future articles (e.g., metadata frontmatter, heading styles).
        3.  At least three foundational FAQ articles are written and placed in `knowledge_base/` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`).
        4.  The existing task `M4-FAQ-001` is updated to reflect that it will ingest data from the new `knowledge_base/` directory, not from external raw sources.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: In Progress
    *   #### Progress (as of 2025-06-06):
        *   ✅ Core project documentation (`projectRoadmap.md`, `codebaseSummary.md`, `README.md`, `currentTask.md`) updated to reflect the content-first strategy.
        *   ✅ `user_instructions/knowledge_base_contribution_guide.md` created.
        *   ✅ `knowledge_base/` directory created.
        *   ✅ `knowledge_base/_template.md` created.
    *   #### Plan:
        *   ✅ Create `knowledge_base/` directory.
        *   ✅ Create `knowledge_base/_template.md`.
        *   Write initial three FAQ articles in `knowledge_base/` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`).
        *   Update task `M4-FAQ-001` (already done by redefining its scope during the content-first strategy integration).
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: Highest

*   ### Task ID: `M4-DATASRC-001`
    *   #### Name: Implement CRUD API for Data Source Management
    *   #### Detailed Description & Business Context:
        To effectively manage the knowledge base of the RAG system, we need a dedicated way to track and control the data sources being ingested. This task involves creating a new set of API endpoints to handle the Create, Read, Update, and Delete (CRUD) operations for data sources. This will provide a foundational mechanism for adding, viewing, modifying, and removing sources, ensuring that the RAG pipeline is always working with a well-curated and up-to-date set of information.
    *   #### Acceptance Criteria:
        1.  A `DataSource` Pydantic model is defined in a new `backend/data_models.py` file.
        2.  A new MongoDB collection named `data_sources` is used to store the source records.
        3.  A new API router is created at `backend/api/v1/sources.py`.
        4.  The following API endpoints are implemented and functional:
            *   `POST /api/v1/sources`: Creates a new data source record.
            *   `GET /api/v1/sources`: Retrieves all data source records.
            *   `GET /api/v1/sources/{source_id}`: Retrieves a single data source record.
            *   `PUT /api/v1/sources/{source_id}`: Updates an existing data source record.
            *   `DELETE /api/v1/sources/{source_id}`: Deletes a data source record.
        5.  Crucially, the `DELETE` endpoint must also remove all associated document chunks from the `litecoin_docs` vector store to prevent data orphans.
        6.  The new router is correctly integrated into the main FastAPI application in `backend/main.py`.
        7.  A new test file, `backend/test_sources_api.py`, is created with tests for each CRUD endpoint.
    *   #### Link to projectRoadmap.md goal(s):
        *   This is a foundational task that supports all major feature milestones by ensuring data integrity and manageability.
    *   #### Status: To Do
    *   #### Plan:
        *   **Phase 1: Backend Data Model & API Endpoints**
            1.  **Define the `DataSource` Model:**
                *   Create `backend/data_models.py`.
                *   Define a `DataSource` Pydantic model with fields: `name` (str), `type` (str, e.g., 'web', 'github', 'markdown'), `uri` (str, unique identifier), `status` (str, e.g., 'active', 'inactive'), `created_at` (datetime), `updated_at` (datetime).
            2.  **Create a Dedicated API Router for Sources:**
                *   Create `backend/api/v1/sources.py`.
            3.  **Implement CRUD API Endpoints in `backend/api/v1/sources.py`:**
                *   `POST /api/v1/sources`: Create a new data source record in a new MongoDB collection `data_sources`.
                *   `GET /api/v1/sources`: Retrieve all data source records.
                *   `GET /api/v1/sources/{source_id}`: Retrieve a single data source by ID.
                *   `PUT /api/v1/sources/{source_id}`: Update an existing data source.
                *   `DELETE /api/v1/sources/{source_id}`: Delete a data source record.
            4.  **Integrate Router into `backend/main.py`:**
                *   Include the `sources` router in the main FastAPI application.
        *   **Phase 2: Ensuring Data Integrity on Deletion**
            1.  **Link Source Deletion to Vector Store:**
                *   Modify the `DELETE /api/v1/sources/{source_id}` endpoint to remove all associated document chunks from the `litecoin_docs` vector store (MongoDB collection) based on metadata (source identifier).
        *   **Phase 3: Documentation & Testing**
            1.  **Update Project Documentation:** (Already partially done by adding this task and updating codebaseSummary.md)
                *   Ensure `cline_docs/codebaseSummary.md` accurately reflects the new files, models, and endpoints upon completion.
            2.  **Create API Tests:**
                *   Create `backend/test_sources_api.py` with Pytest tests for all CRUD endpoints, including validation of data integrity on deletion.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

## Task Backlog:

*   ### Task ID / Name: `M4-FAQ-001` - Create and Ingest Curated Content for Litecoin Basics & FAQ
    *   #### Detailed Description & Business Context:
        To implement the "Litecoin Basics & FAQ" feature, the RAG pipeline needs to be populated with high-quality, curated knowledge. This task involves creating well-structured Markdown documents for fundamental Litecoin topics within the `knowledge_base/` directory and then ingesting this curated data into the MongoDB vector store.
    *   #### Acceptance Criteria:
        1.  The foundational articles created in `M4-KB-001` (e.g., `what-is-litecoin.md`, `how-litecoin-differs-from-bitcoin.md`, `understanding-litecoin-wallets.md`) are finalized and meet quality standards.
        2.  The `ingest_data.py` script is used to load data specifically from the `knowledge_base/` directory.
        3.  Verify that the data from these curated articles is present in the MongoDB vector store.
        4.  Document any specific ingestion notes in this task's "Notes on Completion".
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
        *   Feature 5: Curated Knowledge Base
    *   #### Status: To Do
    *   #### Plan:
        *   Finalize content of initial FAQ articles in `knowledge_base/`.
        *   Use `ingest_data.py` to load data from `knowledge_base/`.
        *   Verify ingestion in MongoDB.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High
    
*   ### Task ID: `M4-UI-001`
    *   #### Name: Develop Frontend Chat UI Components
    *   #### Detailed Description & Business Context:
        Create the necessary React components in the Next.js frontend to build the user-facing chat interface. This includes the main chat window, a text input area for user queries, a submission button, and a display area for both the user's questions and the AI's responses (including source documents).
    *   #### Acceptance Criteria:
        1.  A reusable `ChatWindow` component is created.
        2.  An `InputBox` component allows users to type and submit questions.
        3.  A `Message` component is created to display questions and answers distinctly.
        4.  The UI is styled using Tailwind CSS to be clean and user-friendly.
        5.  The component state is managed appropriately (e.g., storing the conversation history).
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
    *   #### Status: To Do
    *   #### Plan: (To be defined)
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

*   ### Task ID: `M4-INT-001`
    *   #### Name: Integrate Frontend with Backend API
    *   #### Detailed Description & Business Context:
        Connect the frontend chat interface to the backend `/api/v1/chat` endpoint. This involves handling user input submission, making a POST request to the backend with the query, and then processing and displaying the JSON response (`answer` and `sources`) in the UI.
    *   #### Acceptance Criteria:
        1.  Submitting a query in the frontend triggers a POST request to `http://localhost:8000/api/v1/chat`.
        2.  The `answer` from the API response is displayed in the chat interface.
        3.  The `sources` from the API response are displayed alongside the answer, showing the origin of the information.
        4.  Loading and error states are handled gracefully in the UI.
    *   #### Link to projectRoadmap.md goal(s):
        *   Milestone 4: MVP Feature 1 Implementation (Litecoin Basics & FAQ)
    *   #### Status: To Do
    *   #### Plan: (To be defined)
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

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

[View Task Archive](task_archive.md)
