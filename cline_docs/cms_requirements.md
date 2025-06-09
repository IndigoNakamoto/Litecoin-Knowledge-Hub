# Requirements & Plan: AI-Integrated Knowledge Base CMS

## 1. Overview & Goals

This document outlines the requirements, features, and technical architecture for the AI-Integrated Content Management System (CMS) for the Litecoin RAG Chat.

**Primary Goals:**
-   **Enforce Content Structure:** Ensure all knowledge base articles strictly adhere to the predefined template (`knowledge_base/_template.md`), including both frontmatter metadata and the main body structure.
-   **Streamline Content Creation:** Provide a user-friendly and efficient editor for both human and AI content creators.
-   **Ensure Data Integrity:** Use schema-driven validation to guarantee that all content is well-formed and accurate before being saved.
-   **Seamless Integration:** The editor must integrate smoothly into the existing Next.js frontend and produce output compatible with the backend ingestion pipeline.

## 2. High-Level Architecture

The CMS editor will be a new feature within the existing `frontend` application. It will be composed of two primary, integrated parts managed by a single form state controller.

```mermaid
graph TD
    A[React Hook Form Provider] --> B{Frontmatter Form (Auto-Form + ShadCN)};
    A --> C{Main Content Editor (Plate.js + ShadCN)};

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

-   **Form Management:** `react-hook-form` will manage the overall form state, validation, and submission.
-   **Frontmatter:** `Auto-Form` will generate a form from a Zod schema for the article's metadata.
-   **Main Content:** `Plate.js` will serve as the rich-text editor, configured with a schema to enforce the required article structure.
-   **UI Components:** `ShadCN` will be used for all UI elements (inputs, buttons, layout) to ensure visual consistency with the rest of the application.

## 3. Core Features & Technical Implementation

### Feature 1: Schema-Driven Frontmatter Form

-   **Description:** A validated form for all metadata fields defined in `knowledge_base/_template.md`.
-   **Technology:**
    -   **Schema:** A `Zod` schema will be created to define the data types, required fields, and validation rules for the frontmatter.
    -   **Form Generation:** `Auto-Form` will use the Zod schema to automatically render the form fields.
    -   **UI Components (ShadCN):**
        -   `Input`: For `title`, `id`, `category`, `author`, `source`, `relevance_score`.
        -   `Textarea`: For `summary`.
        -   `Tag Input`: A custom or third-party component (e.g., "Emblor") for `tags`.
        -   `Date Picker`: For `last_updated`.
        -   `Select`: For `language`, `vetting_status`.

### Feature 2: Structured Rich-Text Editor

-   **Description:** A rich-text editor that forces content to follow the standard article structure (e.g., "Core Concepts," "How It Works").
-   **Technology:**
    -   **Editor Core:** `Plate.js`. Plate is a rich-text editor framework for Slate.js, designed for simplicity and efficiency. It provides a robust plugin system, headless primitives, and pre-built components using shadcn/ui, making it an ideal choice for our structured and design-consistent editor.
    -   **Structural Enforcement:** The "Forced Layout" plugin for Plate.js will be configured with a schema that mirrors the required sections of a knowledge base article.
    -   **Styling:** The editor and its toolbar will be styled using ShadCN components and Tailwind CSS.
    -   **Customization:** The toolbar will be customized to only allow formatting options that align with the contribution guide (e.g., headings, bold, lists, links).

## 4. Initial User Stories

-   **As a Content Creator,** I want to be presented with a structured form so that I can easily fill in all the required metadata for a new article without missing any fields.
-   **As a Content Creator,** I want the editor to guide me through creating the standard sections of an article in the correct order so that I don't have to remember the exact structure.
-   **As a System Administrator,** I want all submitted articles to be automatically validated against a schema so that the integrity and consistency of the knowledge base are maintained.
-   **As an AI Agent,** I want to interact with a predictable, schema-driven interface so that I can programmatically create and edit articles that are guaranteed to be in the correct format.

## 5. User Roles and Permissions

-   **Writer:**
    -   Can create and save drafts of knowledge base articles.
    -   Cannot directly publish or modify existing published articles.
-   **Editor:**
    -   Has all the permissions of a Writer.
    -   Can submit and publish new drafts to the knowledge base.
    -   Can update existing knowledge base articles, effectively changing the live responses provided to users.

## 6. Proposed File Structure (within `frontend/`)

```
frontend/
└── src/
    ├── app/
    │   └── (cms)/                # Route group for CMS pages
    │       └── editor/
    │           ├── [id]/         # Route for editing an existing article
    │           │   └── page.tsx
    │           └── new/          # Route for creating a new article
    │               └── page.tsx
    ├── components/
    │   └── cms/                  # New directory for CMS-specific components
    │       ├── ArticleEditor.tsx # The main editor component wrapping form/plate
    │       ├── FrontmatterForm.tsx # The frontmatter form component
    │       └── PlateEditor.tsx   # The configured Plate.js editor component
    └── lib/
        └── zod/
            └── articleSchema.ts  # Zod schema for article frontmatter
```

## 7. Next Steps & Implementation Plan

1.  **Setup:** Install necessary dependencies (`zod`, `react-hook-form`, `cmdk`, `plate-ui`, etc.).
2.  **Schema Definition:** Create the Zod schema in `frontend/src/lib/zod/articleSchema.ts`.
3.  **Component Development:** Build the individual components (`FrontmatterForm.tsx`, `PlateEditor.tsx`).
4.  **Integration:** Assemble the components in `ArticleEditor.tsx` and wrap them with `react-hook-form`.
5.  **Page Creation:** Create the routes and pages under `frontend/src/app/(cms)/`.
