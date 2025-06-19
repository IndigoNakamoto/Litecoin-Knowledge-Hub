# Tech Stack: Litecoin Knowledge Hub

## Frontend
*   **Framework:** Next.js
*   **Styling:** Tailwind CSS
*   **UI Libraries:** ShadCN (for consistent application UI components)
*   **Language:** TypeScript (Preferred for Next.js projects, to be confirmed by user if an alternative is desired)
*   **Node.js Version:** 18.18.0 (managed via nvm, as confirmed by user)

## Backend
*   **Language:** Python
*   **Framework:** FastAPI
*   **Key Libraries:**
    *   Google Text Embedding (specifically `text-embedding-004`)
    *   Libraries for interacting with MongoDB (e.g., `pymongo`, `motor`)
    *   Libraries for RAG pipeline: Langchain (chosen - core packages: `langchain`, `langchain-core`, `langchain-community`)
    *   `requests`: For making HTTP requests to Payload's REST/GraphQL API and other external services.
    *   `tweepy`: For interacting with the Twitter (X) API.
    *   `GitPython`: For cloning and interacting with Git repositories (e.g., GitHub).
    *   `beautifulsoup4`: For parsing HTML and XML documents (e.g., web scraping).
    *   `lxml`: A fast XML and HTML parser, often used as a backend for BeautifulSoup.
    *   `python-frontmatter`: For parsing YAML front matter from legacy Markdown files during migration to Payload.
    *   **Payload Integration Libraries:**
        *   Native HTTP requests via `requests` for the Payload REST/GraphQL API.
    *   **RAG Pipeline Specifics:**
        *   **Hierarchical Chunking:** Payload's structured JSON content (e.g., rich text editor blocks) will be parsed and converted to a Markdown-like format. For each chunk, its parent titles will be prepended to the content before embedding, preserving the hierarchical context.
        *   **Embedding `task_type`:**
            *   Knowledge base documents are embedded using `task_type='retrieval_document'`.
            *   User queries are embedded using `task_type='retrieval_query'`.
            *   This asymmetric approach is critical for optimal performance with the `text-embedding-004` model.

## Content Management System
*   **CMS Platform:** Payload (self-hosted)
*   **CMS Database:** MongoDB
*   **Content Format:** Customizable content types (collections) with a rich text editor (JSON output).
*   **Editorial Workflow:** Foundation-controlled (Contributors → Foundation review → Publish)
*   **Integration Method:** Payload REST/GraphQL API + `afterChange` hooks for real-time synchronization
*   **Access Control:** Payload's built-in Role-Based Access Control (RBAC).

## Database Architecture
*   **Content Storage:** MongoDB (for Payload CMS)
*   **Vector Storage:** MongoDB Atlas Vector Search (RAG pipeline)
*   **General Application Data:** MongoDB (if needed for additional features)
*   **ORM/ODM:** 
    *   Direct `pymongo` usage for MongoDB operations
    *   Payload handles its database operations internally.
    *   Pydantic models for data validation and serialization in FastAPI layer

## RAG Pipeline Components
*   **Data Sources:**
    *   **Primary:** Payload CMS via REST/GraphQL API
    *   **Secondary:** Legacy Markdown files (during migration), GitHub, Web scraping
*   **Content Processing:**
    *   Payload content fetched via REST/GraphQL API (JSON format)
    *   JSON content processed by `embedding_processor.py` to extract text and structure for hierarchical chunking.
    *   Metadata extracted from Payload API (authors, tags, publish dates, etc.)
*   **Embedding Model:** Google Text Embedding 004 (`text-embedding-004`)
    *   Knowledge base documents: `task_type='retrieval_document'`
    *   User queries: `task_type='retrieval_query'`
*   **Vector Store:** MongoDB Atlas Vector Search
*   **Retriever:** Implemented via `VectorStoreManager` using similarity search (default k=3)
*   **Generator:** Langchain with `ChatGoogleGenerativeAI` (gemini-pro)
*   **Orchestration:** Langchain
*   **Synchronization:** Payload `afterChange` hooks trigger RAG pipeline updates

## Payload CMS Integration Architecture
*   **Content Retrieval:**
    ```python
    # Payload REST/GraphQL API integration pattern
    async def fetch_payload_articles():
        # Example: Fetch articles from Payload
        response = await payload_client.get('/api/articles', params={'depth': 2})
        return response.json()['docs']
    ```
*   **Webhook Processing (Conceptual `afterChange` hook handler):**
    ```python
    # Conceptual `afterChange` hook handler for content synchronization
    # This logic would typically reside within the Payload CMS itself or a dedicated service
    # triggered by the hook.
    async def process_payload_after_change(doc, collection_name):
        if collection_name == 'articles' and doc['status'] == 'published':
            await sync_content_to_rag(doc)
        elif collection_name == 'articles' and doc['status'] == 'draft':
            await remove_from_rag(doc['id']) # Or update if content changed in draft
    ```
*   **Content Processing Pipeline:**
    ```
    Payload REST/GraphQL API → JSON Content → Structured Text Conversion → 
    Hierarchical Chunking → Embedding → MongoDB Vector Store
    ```

## Vector Search Configuration
*   **Metadata Handling:** Payload API metadata (author, tags, publishedAt, etc.) mapped to MongoDB document fields for filtering.
*   **Atlas Vector Search Index Definition:**
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
          "path": "payload_id"
        },
        {
          "type": "filter",
          "path": "chunk_type"
        },
        {
          "type": "filter",
          "path": "content_type"
        },
        {
          "type": "filter",
          "path": "author"
        },
        {
          "type": "filter",
          "path": "tags_array"
        },
        {
          "type": "filter",
          "path": "published_date"
        }
      ]
    }
    ```

*   **Recommended Metadata Indexes for Filtering:**
    ```javascript
    // Vector Search Index (defined above)

    // Metadata Indexes for Filtering
    db.litecoin_docs.createIndex({"payload_id": 1})
    db.litecoin_docs.createIndex({"chunk_type": 1, "content_type": 1})
    db.litecoin_docs.createIndex({"author": 1})
    db.litecoin_docs.createIndex({"tags_array": 1})
    db.litecoin_docs.createIndex({"published_date": -1})
    db.litecoin_docs.createIndex({"title": "text", "section_title": "text"})
    ```

## DevOps & Infrastructure
*   **Frontend Deployment:** Vercel
*   **Backend Deployment:** TBD (Vercel Functions, Google Cloud Run, AWS Lambda, etc.)
*   **Payload CMS Hosting:** Self-hosted (DigitalOcean, AWS EC2, Google Cloud Compute, etc.)
*   **Database Hosting:**
    *   MongoDB: MongoDB Atlas (cloud)
*   **CI/CD Tools:** TBD (GitHub Actions, GitLab CI, etc.)
*   **Containerization:** Docker (for Payload CMS deployment consistency)
*   **Monitoring:** TBD (External services for comprehensive monitoring of the Payload instance)

## Testing
*   **Frontend Frameworks:** TBD (Jest, React Testing Library, Cypress)
*   **Backend Frameworks:** TBD (Pytest)
*   **Integration Testing:** Payload API integration tests, `afterChange` hook delivery testing
*   **Content Pipeline Testing:** End-to-end testing of Payload → RAG synchronization

## Build Tools & Package Managers
*   **Frontend:** npm (standard with Next.js)
*   **Backend:** pip with `requirements.txt`
*   **Payload CMS:** npm/yarn for installation and management

## Key Libraries & Justifications

### Core Framework Choices
*   **Next.js:** Chosen for robust React-based frontend development, SSR/SSG capabilities, and excellent Vercel integration.
*   **Tailwind CSS:** Chosen for utility-first CSS development, enabling rapid UI construction.
*   **Python/FastAPI:** Chosen for backend due to Python's strong AI/ML ecosystem and FastAPI's high performance and ease of use for building APIs.

### Payload CMS Integration
*   **Payload CMS:** Selected for its:
    *   **Superior Developer Experience:** Modern Node.js/TypeScript framework with a great admin UI.
    *   **Direct MongoDB Integration:** Aligns perfectly with our existing MongoDB Atlas setup.
    *   **Flexible Content Structuring:** Customizable collections are ideal for RAG.
    *   **Open-Source and Self-Hosted:** Aligns with project's control and ownership principles.
    *   **Built-in RBAC:** Enforces Foundation-controlled editorial workflows out-of-the-box.
    *   **REST/GraphQL API & `afterChange` hooks:** Robust mechanisms for integration with the RAG pipeline.
*   **MongoDB:** Native database for Payload, simplifying the stack.
*   **Payload REST/GraphQL API:** Provides flexible and powerful ways to query content.
*   **JSON Content Processing:** Direct handling of structured JSON from Payload is robust.

### RAG Pipeline Libraries
*   **Google Text Embedding 004:** Specified for generating text embeddings with critical `task_type` usage:
    *   `task_type='retrieval_document'` for stored Payload content
    *   `task_type='retrieval_query'` for user queries
    *   Hierarchical chunking strategy maintained for optimal context preservation
*   **MongoDB Atlas Vector Search:** Chosen for vector storage and similarity search capabilities
*   **Langchain:** Core RAG orchestration framework
*   **`requests`:** Used to interact with the Payload REST/GraphQL API.

### Content Processing
*   **`embedding_processor.py` (adapted):** Will be adapted to handle Payload content:
    *   Handles Payload REST/GraphQL API JSON responses.
    *   Parses structured JSON to extract text and create a hierarchical context.
    *   Maps Payload metadata to the RAG pipeline metadata schema.
    *   Maintains hierarchical chunking for optimal retrieval.
*   **`afterChange` hook handlers:** Real-time synchronization between Payload and the RAG pipeline.
*   **Payload API client:** A module to handle communication with the Payload API.

## Migration Strategy
*   **Phase 1:** Set up Payload CMS infrastructure and define content types (collections).
*   **Phase 2:** Develop/adapt `embedding_processor.py` and `afterChange` hook handlers.
*   **Phase 3:** Establish Foundation editorial workflows in Payload.
*   **Phase 4:** Deprecate any remaining legacy CMS components.

## Security Considerations
*   **Payload CMS Security:**
    *   Regular Payload version updates.
    *   Secure Payload hosting configuration.
    *   SSL/TLS encryption for Payload admin and API access.
    *   Strong authentication for Payload admin accounts.
*   **API Security:**
    *   Secure management of Payload API tokens.
    *   `afterChange` hook signature verification (if available/implemented).
    *   Rate limiting on API and `afterChange` hook endpoints.
*   **Database Security:**
    *   Database access restricted to the Payload instance.
    *   MongoDB Atlas security best practices
    *   Secure network configurations

## Performance Considerations
*   **Payload CMS Performance:**
    *   Payload instance sizing appropriate for content volume.
    *   Database optimization for MongoDB.
    *   CDN integration for Payload-served assets.
*   **RAG Pipeline Performance:**
    *   Efficient `afterChange` hook processing to avoid blocking Payload.
    *   Asynchronous content processing.
    *   Vector search optimization.
    *   Caching strategies for frequently accessed content.

## Operational Monitoring
*   **Payload CMS Monitoring:**
    *   Payload instance health monitoring.
    *   Database performance monitoring.
    *   Content publishing workflow monitoring.
*   **Integration Monitoring:**
    *   `afterChange` hook delivery success rates.
    *   Content synchronization lag monitoring.
    *   RAG pipeline processing times.
    *   Vector store update verification.

This revised tech stack reflects the strategic decision to leverage Payload for content management, providing greater data control and flexibility for the RAG pipeline while establishing a mature, reliable foundation for the Litecoin knowledge base.
