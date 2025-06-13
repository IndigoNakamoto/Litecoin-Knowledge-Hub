# Current Task: Litecoin RAG Chat

## Current Sprint/Iteration Goal
*   **Milestone 6: AI-Integrated Knowledge Base CMS Development - Phase 3: Refinement & Advanced Features (`CMS-IMP-003`)**

## High-Priority Initiatives: AI-Integrated Knowledge Base CMS

## Recently Completed Tasks:

*   ### Task ID: `CMS-IMP-001`
    *   #### Name: CMS Implementation - Phase 1: Core Setup & Basic Content Management
    *   #### Detailed Description & Business Context:
        Implement the foundational elements of the AI-Integrated Knowledge Base CMS. This phase focuses on setting up the core technologies, developing basic CRUD (Create, Read, Update, Delete) functionality for articles, and implementing initial authentication and role-based access control. This aligns with Phase 1 of the CMS Implementation Roadmap defined in `cline_docs/cms_requirements.md`.
    *   #### Acceptance Criteria:
        1.  Selected frontend technologies (Tiptap, React Hook Form with Zod, ShadCN) are integrated into the Next.js application.
        2.  Basic article CRUD API endpoints (`/api/v1/articles`) are developed in the FastAPI backend, capable of creating, reading, updating, and deleting article data in MongoDB.
        3.  Frontend components for article creation/editing (including frontmatter form and Tiptap editor) are developed and connected to the backend API.
        4.  Initial JWT-based authentication is implemented for CMS access.
        5.  Basic user roles (e.g., Writer, Editor) are defined and enforced for core CMS actions.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: AI-Integrated Knowledge Base CMS
        *   Milestone 6: AI-Integrated Knowledge Base CMS Development - Phase 1
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Backend API with MongoDB integration for articles is complete.
        *   JWT authentication is implemented and protects relevant endpoints.
        *   Frontend login page and article editor are connected to the backend.

*   ### Task ID: `CMS-IMP-002`
    *   #### Name: CMS Implementation - Phase 2: Semantic Search Implementation
    *   #### Detailed Description & Business Context:
        Integrate semantic search capabilities within the CMS, allowing users to efficiently find and manage articles. This involves connecting to MongoDB Atlas Vector Search, implementing or adapting the content ingestion pipeline for CMS-managed articles, and building the necessary UI and API components. This aligns with Phase 2 of the CMS Implementation Roadmap.
    *   #### Acceptance Criteria:
        1.  MongoDB Atlas Vector Search is integrated for articles created/managed via the CMS.
        2.  The asynchronous content ingestion pipeline (chunking, embedding) is adapted or implemented for CMS articles.
        3.  A search interface is built into the CMS frontend.
        4.  Backend API supports search queries over CMS articles.
        5.  The solution for search index consistency (e.g., polling) is implemented for critical updates.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: AI-Integrated Knowledge Base CMS
        *   Milestone 6: AI-Integrated Knowledge Base CMS Development - Phase 2
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Backend:
            *   Created `/api/v1/articles/search` endpoint in `backend/cms/articles/router.py`.
            *   Implemented `search_articles` in `backend/cms/articles/crud.py` using MongoDB Atlas Vector Search.
            *   Modified `create_article` and `update_article` in `backend/cms/articles/crud.py` to generate and store `content_embedding` for articles.
            *   Created RAG synchronization webhook `/api/v1/sync/rag` in `backend/cms/sync/router.py`.
            *   Integrated webhook call into `update_article` in `backend/cms/articles/crud.py` to trigger on relevant `vetting_status` changes.
            *   Implemented logic within the RAG sync webhook to add/delete documents from the RAG vector store using `VectorStoreManager`.
        *   Frontend:
            *   Added search input and results display to `frontend/src/app/(cms)/dashboard/page.tsx`.
            *   Connected frontend search UI to the `/api/v1/articles/search` endpoint, handling API calls and displaying results.
    *   #### Plan:
        1.  **Backend Tasks (FastAPI):**
            *   **Semantic Search Endpoint:** Create a new endpoint (e.g., `/api/v1/articles/search`) that embeds a search query and uses MongoDB Atlas Vector Search to find similar articles within the CMS content (including drafts). - ✅ Done
            *   **Content Ingestion for Search:** Modify the article save logic to trigger an asynchronous task that embeds the article's content and updates a dedicated CMS search index in MongoDB. - ✅ Done (Integrated into save logic directly)
            *   **RAG Synchronization Service:** Implement a webhook endpoint (e.g., `/api/v1/sync/rag`). When an article's `vetting_status` changes to 'vetted' (or a vetted article is updated/archived), the CMS backend will call this webhook to trigger the RAG ingestion pipeline (add/update/remove) for that specific article. - ✅ Done
        2.  **Frontend Tasks (Next.js):**
            *   **Search UI:** Add a search bar and results display to the CMS dashboard page, connected to the new search API endpoint. - ✅ Done
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High
    
## Task Backlog:

*   ### Task ID: `CMS-IMP-003`
    *   #### Name: CMS Implementation - Phase 3: Refinement & Advanced Features
    *   #### Detailed Description & Business Context:
        Implement advanced features and refinements for the CMS, including a full Role-Based Access Control (RBAC) system, advanced Tiptap editor capabilities, and cloud storage for large assets. This aligns with Phase 3 of the CMS Implementation Roadmap.
    *   #### Acceptance Criteria:
        1.  A granular RBAC system tied to content workflows (draft, review, vetted) is implemented.
        2.  Advanced Tiptap features (e.g., custom non-editable blocks, template enforcement) are developed.
        3.  A cloud storage solution (e.g., S3, GCS) is integrated for handling large binary assets, with MongoDB storing asset metadata and URLs.
        4.  Performance testing and optimization of the CMS are conducted.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: AI-Integrated Knowledge Base CMS
        *   Milestone 6: AI-Integrated Knowledge Base CMS Development - Phase 3
    *   #### Status: To Do
    *   #### Plan:
        1.  **Backend Tasks (FastAPI):**
            *   **Granular RBAC:** Expand the authentication system into a full RBAC system with FastAPI dependencies to check permissions based on user role and content status (e.g., only an 'Editor' can move an article to 'vetted').
            *   **Cloud Asset Storage:** Integrate with a cloud storage provider (e.g., AWS S3 or GCS). Create API endpoints for generating pre-signed URLs for client uploads and managing asset metadata in MongoDB.
            *   **AI Integration:** Develop a new set of API endpoints to act as a secure proxy for external AI services (e.g., Google's Generative AI) for tasks like summarization or rephrasing.
        2.  **Frontend Tasks (Next.js):**
            *   **Advanced Tiptap Editor:** Enhance the Tiptap schema to include custom nodes and non-editable blocks (`atom: true`) to strictly enforce the `knowledge_base/_template.md` structure.
            *   **Asset Management UI:** Develop UI components for uploading images/videos and inserting them into the Tiptap editor.
            *   **AI-Assisted Authoring:** Integrate Tiptap's AI extensions, connecting them to the backend AI proxy endpoints to provide in-editor assistance.
    *   #### Estimated Effort: (To be determined)
    *   #### Assigned To: (To be determined)
    *   #### Priority: High

*   ### Task ID: `CMS-PLAN-001`
    *   #### Name: Define Requirements and Plan for AI-Integrated Knowledge Base CMS
    *   #### Detailed Description & Business Context:
        Define the core requirements, features, and technical architecture for a content management system (CMS) specifically designed for the Litecoin RAG Chat's knowledge base. This CMS should facilitate collaborative content creation and editing by users and AI agents, integrate with research tools like Google Deep Search, and manage the lifecycle of knowledge base articles (creation, editing, publishing, archiving).
    *   #### Acceptance Criteria:
        1.  A detailed document outlining the CMS requirements and features is created (e.g., in `cline_docs/cms_requirements.md`).
        2.  A high-level architectural plan for the CMS, including its interaction with existing RAG components and external AI services, is defined.
        3.  Initial user stories for key CMS functionalities are drafted.
    *   #### Link to projectRoadmap.md goal(s):
        *   Feature 6: AI-Integrated Knowledge Base CMS
    *   #### Status: Done
    *   #### Notes on Completion:
        *   Detailed requirements, architecture, and implementation roadmap defined in `cline_docs/cms_requirements.md`.
        *   Core project documents (`projectRoadmap.md`, `techStack.md`, `codebaseSummary.md`) updated to reflect CMS plans.
    *   #### Estimated Effort: 4 hours (Planning)
    *   #### Assigned To: Cline
    *   #### Priority: Highest


[View Task Archive](task_archive.md)
