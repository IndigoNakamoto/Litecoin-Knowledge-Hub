# **Requirements & Plan: AI-Integrated Knowledge Base CMS**

## 1. Overview & Goals

## **1. Overview & Goals**

This document outlines the requirements, features, and technical architecture for the Content Management System (CMS) for the Litecoin Knowledge Base. This system is a foundational component of our content strategy, designed to ensure the quality, consistency, and accuracy of the information served to our users. This plan is informed by the detailed analysis in `cline_docs/cms_research.md`.

**Primary Goals:**
-   **Enforce Content Structure:** Ensure all knowledge base articles strictly adhere to the predefined template (`knowledge_base/_template.md`), including both frontmatter metadata and the main body structure.
-   **Streamline Content Creation:** Provide a user-friendly and efficient editor for both human and AI content creators.
-   **Ensure Data Integrity:** Use schema-driven validation to guarantee that all content is well-formed and accurate before being saved.
-   **Seamless Integration:** The editor must integrate smoothly into the existing Next.js frontend and produce output compatible with the backend ingestion pipeline.

*   **Enforce Content Structure:** Ensure all articles strictly adhere to a predefined format. This is the most critical technical requirement, as the backend `embedding_processor.py` relies on this predictable structure for its hierarchical chunking strategy. Deviations would corrupt vector context and severely degrade RAG pipeline accuracy.
*   **Streamline Content Creation:** Provide a user-friendly, intuitive, and efficient editor for content creators to encourage the production of high-quality articles.
*   **Ensure Data Integrity:** Use schema-driven validation to guarantee all content is well-formed before being saved, protecting the entire downstream system from data corruption.
*   **Seamless Integration:** The editor must integrate smoothly into the existing Next.js frontend and produce output compatible with the backend, ensuring visual consistency and a compatible data format (`.md` with YAML frontmatter).

## **2. High-Level Architecture & Technology Choices**

The CMS editor will be a new feature within the frontend application, functioning as a single-page application composed of two primary parts managed by a single form state controller.

```mermaid
graph TD
    A[React Hook Form Provider] --> B{Frontmatter Form (React Hook Form + Zod)};
    A --> C{Main Content Editor (Tiptap)};

    subgraph "Article Editor Page"
        direction LR
        B --> E[Metadata Fields: Title, Tags, etc.];
        C --> F[Structured Rich-Text Editor];
    end

    A --> G[Submit Button];
    G --> H{Unified Form State};
    H --> I[Generate .md File Output];
    I --> J[Save/Export to knowledge_base/articles];

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
```

*   **Form Management:** **React Hook Form with Zod** is the selected solution.
    *   **Reasoning:** While `Auto-Form` is excellent for simple forms, the potential for increasing complexity in article metadata (e.g., conditional fields, repeatable groups) requires the greater flexibility, performance, and fine-grained control offered by React Hook Form. This choice is more robust and future-proof.
*   **Rich Text Editor:** **Tiptap** is the selected editor core.
    *   **Reasoning:** Tiptap's schema-driven nature is superior for enforcing the strict, non-editable structural templates required for our knowledge base. Its ability to declaratively define a document's structure (e.g., `content: 'title_heading summary_paragraph detail_section+'`) and create non-editable `atom: true` nodes is critical for maintaining consistency and is a key differentiator identified in research.
*   **UI Components:** **ShadCN** will be used for all UI elements to ensure a consistent look and feel.
*   **Backend Framework:** **FastAPI** will be used for its performance, Python ecosystem, and native support for asynchronous operations.

## **3. Core Features & Technical Implementation**

### **Feature 1: Schema-Driven Frontmatter Form**

*   **Description:** A validated form for all metadata fields, providing real-time feedback.
*   **Technology:**
    *   **Schema:** A Zod schema (`articleSchema.ts`) will define the data model and validation rules.
    *   **Form Management:** **React Hook Form** will build the form, connected to the Zod schema via `@hookform/resolvers/zod`.
    *   **UI Components (ShadCN):** Standard inputs, textareas, date pickers, and select components will be used.

### **Feature 2: Structured Rich-Text Editor**

*   **Description:** A rich-text editor that forces content to follow the standard article structure.
*   **Technology:**
    *   **Editor Core:** **Tiptap**.
    *   **Structural Enforcement:** A custom Tiptap schema will enforce the required document structure and define non-editable `atom: true` nodes for fixed headings or instructional blocks.
    *   **Toolbar:** The editor's toolbar will be intentionally limited to basic formatting to maintain a clean, uniform look across all articles.

## **4. Data and Asset Management Strategy**

### **4.1. Primary Data Store**

*   **Database:** **MongoDB** will be used as the primary data store.
*   **Metadata:** Article metadata will be stored directly within the main article document in MongoDB. To ensure performance, **indexes must be created on all frequently queried metadata fields** (e.g., `tags`, `category`, `vetting_status`).

### **4.2. Large Asset Handling**

*   **Strategy:** For large binary assets (images > 1MB, videos, PDFs), a dedicated **cloud storage solution (e.g., AWS S3, Google Cloud Storage)** is required.
*   **Implementation:** The MongoDB database will store metadata about these assets, including a URL pointing to the file in cloud storage. This approach is more cost-effective, scalable, and performant for asset delivery than using GridFS.

## **5. User Roles and Permissions**

*   **Writer:** Can create, edit, and delete their own draft articles.
*   **Editor:** Has all Writer permissions, plus the ability to view, edit, and delete any article. This is the only role that can change `vetting_status` to `in_review` or `vetted`.
*   **Administrator:** Has full system access, including all Editor permissions and user management.
*   **Implementation:** A **JWT-based authentication** and a comprehensive **Role-Based Access Control (RBAC)** system will be implemented in the FastAPI backend.

## **6. Backend & RAG Pipeline Integration Plan**

### **6.1. Core Article CRUD API**

*   **API Router:** A new router at `/api/v1/articles` will handle all CRUD operations.
*   **Asynchronous Operations:** All I/O-bound tasks (database queries, file system access, calls to embedding models) **must be handled asynchronously** using FastAPI's `async/await` capabilities to ensure high performance and responsiveness.
*   **File Handling:** The API will use the `python-frontmatter` library for parsing and serializing `.md` files.

### **6.2. Embedding and Search Strategy**

*   **Embedding Model:**
    *   **Initial Choice:** The project will start with **Google's `text-embedding-004`**, being mindful of its 2048-token input limit and potential rate limits on the free tier.
    *   **Future Flexibility:** The system architecture **must be designed to support batch re-embedding** of all content. This is critical to allow for future upgrades to more performant or cost-effective models without being locked into the initial choice.
*   **Chunking Strategy:**
    *   A well-defined and **intelligent chunking strategy is required** for processing long articles before embedding. This strategy should leverage the semantic structure provided by the Tiptap editor's output to create meaningful chunks, which is crucial for search relevance.
*   **Search Index Consistency:**
    *   The system **must address the "eventual consistency" of the Atlas Vector Search index**. There is a natural delay between when data is updated in MongoDB and when it's reflected in the search index.
    *   **Solution:** For critical updates, a mechanism such as **polling the search index** must be implemented to verify that the update is live before confirming the action to the user or proceeding with tasks that depend on the new data.

### **6.3. RAG Pipeline Quality Gate**

*   **Filtering:** The core query method in `rag_pipeline.py` **must** be permanently modified to add a `pre_filter` to the vector search, retrieving **only** documents where `vetting_status` is `'vetted'`. This is the final and most important gatekeeper for content quality.
*   **Vector Index Requirement:** This filtering is critically dependent on the MongoDB Atlas Vector Search index being configured to allow filtering on the `vetting_status` field.

## **7. Proposed File Structure (within frontend/)**

(No changes from previous version)

frontend/
└── src/
    ├── app/
    │   └── (cms)/
    │       ├── dashboard/
    │       │   └── page.tsx
    │       └── editor/
    │           ├── [id]/
    │           │   └── page.tsx
    │           └── new/
    │               └── page.tsx
    ├── components/
    │   └── cms/
    │       ├── ArticleEditor.tsx
    │       ├── FrontmatterForm.tsx
    │       └── TiptapEditor.tsx
    └── lib/
        ├── zod/
        │   └── articleSchema.ts
        └── markdown/
            └── utils.ts

## **8. Implementation Roadmap**

An iterative development approach is required.

1.  **Phase 1: Core Setup & Basic Content Management:**
    *   Implement technology choices: Tiptap, React Hook Form, FastAPI, MongoDB.
    *   Develop basic article CRUD functionality.
    *   Implement initial JWT authentication and basic roles.
2.  **Phase 2: Semantic Search Implementation:**
    *   Integrate MongoDB Atlas Vector Search.
    *   Implement the asynchronous content ingestion pipeline, including the chunking strategy and embedding generation.
    *   Build the search UI and API.
    *   **Critically, implement the solution for search index consistency.**
3.  **Phase 3: Refinement & Advanced Features:**
    *   Implement the full, granular RBAC system tied to content workflows.
    *   Develop advanced Tiptap features (custom blocks, template enforcement).
    *   Implement the cloud storage solution for large assets.
    *   Conduct performance testing and optimization.
