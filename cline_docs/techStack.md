# Tech Stack: Litecoin RAG Chat

## Frontend
*   **Framework:** Next.js
*   **Styling:** Tailwind CSS
*   **UI Libraries:** (To be determined, e.g., ShadCN if suitable)
*   **Language:** TypeScript (Preferred for Next.js projects, to be confirmed by user if an alternative is desired)
*   **Node.js Version:** 18.18.0 (managed via nvm, as confirmed by user)

## Backend
*   **Language:** Python
*   **Framework:** FastAPI
*   **Key Libraries:**
    *   Google Text Embedding (specifically `text-embedding-004`)
    *   Libraries for interacting with MongoDB (e.g., `pymongo`, `motor`)
    *   Libraries for RAG pipeline: Langchain (chosen - core packages: `langchain`, `langchain-core`, `langchain-community`)
    *   `requests`: For making HTTP requests to external APIs (e.g., Citeio for YouTube data).
    *   `tweepy`: For interacting with the Twitter (X) API.
    *   `GitPython`: For cloning and interacting with Git repositories (e.g., GitHub).
    *   `beautifulsoup4`: For parsing HTML and XML documents (e.g., web scraping).
    *   `lxml`: A fast XML and HTML parser, often used as a backend for BeautifulSoup.
    *   `python-frontmatter`: For robustly parsing YAML front matter from Markdown files, ensuring metadata like title, tags, and custom fields are correctly extracted.
    *   **RAG Pipeline Specifics:**
        *   **Hierarchical Chunking:** Markdown documents are parsed hierarchically. For each chunk, its parent titles (e.g., "Title: Document Title\nSection: Section Name\nSubsection: Subsection Name") are prepended to the content before embedding. This provides rich contextual information directly into the vector.
        *   **Embedding `task_type`:**
            *   Knowledge base documents are embedded using `task_type='retrieval_document'`.
            *   User queries are embedded using `task_type='retrieval_query'`.
            *   This asymmetric approach is critical for optimal performance with the `text-embedding-004` model.

## Database
*   **Type:** MongoDB
*   **Usage:**
    *   Vector storage and search for RAG.
    *   General application data (if needed).
*   **ORM/ODM:** Direct `pymongo` usage for database operations, combined with Pydantic models for data validation and serialization in the FastAPI layer.
*   **RAG Components:** (This seems like a good place for a dedicated RAG component breakdown)
    *   **Data Ingestion & Processing:**
        *   Markdown documents are loaded using `litecoin_docs_loader.py`, which utilizes the `python-frontmatter` library to parse YAML front matter and extract content. This ensures metadata (title, tags, custom fields) is accurately captured.
        *   The extracted content and metadata are then processed by `embedding_processor.py` for hierarchical chunking and embedding.
    *   **Embedding Model:** Google Text Embedding 004 (`text-embedding-004`) is used.
        *   Knowledge base documents: `task_type='retrieval_document'`.
        *   User queries: `task_type='retrieval_query'`.
    *   **Vector Store:** MongoDB Atlas Vector Search.
    *   **Retriever:** Implemented via `VectorStoreManager` using similarity search (default k=3).
    *   **Generator:** Langchain with `ChatGoogleGenerativeAI` (gemini-pro).
    *   **Orchestration:** Langchain.
*   **Vector Search Specifics:**
    *   **Metadata Handling:** When using `langchain-mongodb` (`MongoDBAtlasVectorSearch`), metadata from Langchain `Document` objects (e.g., parsed from Markdown frontmatter) is **flattened** into the root of the MongoDB document. It is *not* stored in a nested `metadata` sub-document. For example, `Document(page_content="...", metadata={"author": "Cline"})` will result in a MongoDB document like `{"text": "...", "embedding": [...], "author": "Cline"}`.
    *   **Atlas Vector Search Index Definition:** To enable filtering on these flattened metadata fields, the Atlas Vector Search index must define filterable paths at the root level.
        *   **Correct Index Definition Example (as of 2025-06-06):**
            ```json
            {
              "fields": [
                {
                  "type": "vector",
                  "path": "embedding",
                  "numDimensions": 768,
                  "similarity": "cosine"
                },
                {
                  "type": "filter",
                  "path": "author"
                },
                {
                  "type": "filter",
                  "path": "published_at"
                },
                {
                  "type": "filter",
                  "path": "tags"
                }
              ]
            }
            ```
        *   Note: The `text_key` (default "text") and `embedding_key` (default "embedding") in `MongoDBAtlasVectorSearch` refer to the fields where the document content and vector embeddings are stored, respectively. The `metadata_key` parameter in `MongoDBAtlasVectorSearch` does *not* cause metadata to be nested under that key in the stored document; metadata is always flattened.

## DevOps & Infrastructure
*   **Deployment Environment:** Vercel (primarily for frontend, backend deployment strategy TBD - could be Vercel Functions, or separate service like Google Cloud Run, AWS Lambda, etc.)
*   **CI/CD Tools:** (To be determined, e.g., GitHub Actions)
*   **Containerization:** (To be determined, e.g., Docker, if needed for backend deployment)

## Testing
*   **Frontend Frameworks:** (To be determined, e.g., Jest, React Testing Library, Cypress)
*   **Backend Frameworks:** (To be determined, e.g., Pytest)

## Build Tools & Package Managers
*   **Frontend:** npm / yarn / pnpm (To be decided, `npm` is a common default with `create-next-app`)
*   **Backend:** pip (standard), potentially with `venv` or a manager like Poetry/PDM (To be decided)

## Key Libraries & Justifications
*   **Next.js:** Chosen for its robust features for React-based frontend development, SSR/SSG capabilities, and good integration with Vercel.
*   **Tailwind CSS:** Chosen for utility-first CSS development, enabling rapid UI construction.
*   **Python/FastAPI:** Chosen for backend due to Python's strong AI/ML ecosystem and FastAPI's high performance and ease of use for building APIs.
*   **Google Text Embedding 004:** Specified for generating text embeddings for the RAG system. Critical for its performance is the use of `task_type='retrieval_document'` for stored content and `task_type='retrieval_query'` for user queries, along with a hierarchical chunking strategy for source documents.
*   **MongoDB:** Chosen for its flexibility and capabilities for vector search, suitable for RAG applications.
*   **`python-frontmatter`**: Added to ensure reliable parsing of YAML front matter from Markdown source files, as the default Langchain loaders did not consistently extract all necessary metadata for the project's specific file structure. This is crucial for populating document chunks with accurate `title`, `tags`, `last_updated`, etc.

## Version Control System & Branching Strategy
*   **VCS:** Git (assumed, hosted on GitHub/GitLab/etc. - To be confirmed)
*   **Branching Strategy:** (To be determined, e.g., GitFlow, GitHub Flow)

## Coding Style Guides & Linters
*   **Frontend:** ESLint, Prettier (common with Next.js, often set up by `create-next-app`)
*   **Backend:** Black, Flake8 / Ruff (common in Python)

## Key Non-Functional Requirements
*   Highly scalable to support target user base (10,000 queries/week).
*   Response times under 3000 ms for typical queries.
*   High security for any sensitive data (if handled) and robust against common vulnerabilities.
*   Mobile-first design considerations for the frontend.
*   Accuracy of 95% for transaction-related queries.

## Existing Code, Libraries, or Services to Integrate
*   An existing project that processes YouTube videos:
    *   Summarizes them.
    *   Creates a timeseries list of topics (start time, title, summary, transcript slice).
    *   Embeds topics using Google Text Embedding 004.
    *   Has a Next.js frontend for YouTube integration and UI.
    *   **Integration Plan:** This existing system will likely serve as a data source or a component for the RAG system. The embeddings and topic data can be ingested into the Litecoin RAG Chat's knowledge base. The Next.js frontend components might be reusable or serve as inspiration. Details of integration need to be explored in a dedicated task.
