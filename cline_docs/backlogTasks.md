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