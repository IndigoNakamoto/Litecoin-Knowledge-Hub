# Tech Stack: Litecoin RAG Chat

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
    *   `requests`: For making HTTP requests to Ghost Content API and external services.
    *   `tweepy`: For interacting with the Twitter (X) API.
    *   `GitPython`: For cloning and interacting with Git repositories (e.g., GitHub).
    *   `beautifulsoup4`: For parsing HTML and XML documents (e.g., web scraping).
    *   `lxml`: A fast XML and HTML parser, often used as a backend for BeautifulSoup.
    *   `python-frontmatter`: For parsing YAML front matter from legacy Markdown files during migration.
    *   `markdownify` or `html2text`: For converting Ghost HTML content to Markdown for RAG processing.
    *   **Ghost Integration Libraries:**
        *   Native HTTP requests via `requests` for Ghost Content API
        *   `jwt`: For Ghost Admin API authentication (if needed)
    *   **RAG Pipeline Specifics:**
        *   **Hierarchical Chunking:** Ghost HTML content converted to Markdown, then parsed hierarchically. For each chunk, its parent titles (e.g., "Title: Document Title\nSection: Section Name\nSubsection: Subsection Name") are prepended to the content before embedding. This provides rich contextual information directly into the vector.
        *   **Embedding `task_type`:**
            *   Knowledge base documents are embedded using `task_type='retrieval_document'`.
            *   User queries are embedded using `task_type='retrieval_query'`.
            *   This asymmetric approach is critical for optimal performance with the `text-embedding-004` model.

## Content Management System
*   **CMS Platform:** Ghost (self-hosted)
*   **CMS Database:** MySQL 8.0+ (Ghost requirement)
*   **Content Format:** Native Markdown support via Ghost editor
*   **Editorial Workflow:** Foundation-controlled (Contributors → Foundation review → Publish)
*   **Integration Method:** Ghost Content API + Webhooks for real-time synchronization
*   **Access Control:** Ghost's built-in role system (Owner, Administrator, Editor, Author, Contributor)

## Database Architecture
*   **Content Storage:** MySQL (Ghost CMS)
*   **Vector Storage:** MongoDB Atlas Vector Search (RAG pipeline)
*   **General Application Data:** MongoDB (if needed for additional features)
*   **ORM/ODM:** 
    *   Direct `pymongo` usage for MongoDB operations
    *   Ghost handles MySQL operations internally
    *   Pydantic models for data validation and serialization in FastAPI layer

## RAG Pipeline Components
*   **Data Sources:**
    *   **Primary:** Ghost CMS via Content API
    *   **Secondary:** Legacy Markdown files (during migration), GitHub, Web scraping
*   **Content Processing:**
    *   Ghost content fetched via Content API (HTML format)
    *   HTML converted to Markdown using `markdownify` or `html2text`
    *   Processed by `embedding_processor_ghost.py` for hierarchical chunking
    *   Metadata extracted from Ghost API (authors, tags, publish dates, etc.)
*   **Embedding Model:** Google Text Embedding 004 (`text-embedding-004`)
    *   Knowledge base documents: `task_type='retrieval_document'`
    *   User queries: `task_type='retrieval_query'`
*   **Vector Store:** MongoDB Atlas Vector Search
*   **Retriever:** Implemented via `VectorStoreManager` using similarity search (default k=3)
*   **Generator:** Langchain with `ChatGoogleGenerativeAI` (gemini-pro)
*   **Orchestration:** Langchain
*   **Synchronization:** Ghost webhooks trigger RAG pipeline updates

## Ghost CMS Integration Architecture
*   **Content Retrieval:**
    ```python
    # Ghost Content API integration pattern
    async def fetch_ghost_posts():
        response = await ghost_client.posts.browse({
            'include': 'authors,tags',
            'formats': ['html', 'plaintext'],
            'filter': 'status:published'
        })
        return response
    ```
*   **Webhook Processing:**
    ```python
    # Webhook handler for content synchronization
    async def process_ghost_webhook(payload):
        event_type = payload.get('event')  # post.published, post.updated, etc.
        if event_type in ['post.published', 'post.published.edited']:
            await sync_content_to_rag(payload['post'])
        elif event_type == 'post.deleted':
            await remove_from_rag(payload['post']['id'])
    ```
*   **Content Processing Pipeline:**
    ```
    Ghost Content API → HTML Content → Markdown Conversion → 
    Hierarchical Chunking → Embedding → MongoDB Vector Store
    ```

## Vector Search Configuration
*   **Metadata Handling:** Ghost API metadata (authors, tags, published_at, etc.) mapped to MongoDB document fields for filtering
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
          "path": "ghost_id"
        },
        {
          "type": "filter",
          "path": "ghost_slug"
        },
        {
          "type": "filter",
          "path": "authors"
        },
        {
          "type": "filter",
          "path": "tags"
        },
        {
          "type": "filter",
          "path": "published_at"
        },
        {
          "type": "filter",
          "path": "source_type"
        }
      ]
    }
    ```

## DevOps & Infrastructure
*   **Frontend Deployment:** Vercel
*   **Backend Deployment:** TBD (Vercel Functions, Google Cloud Run, AWS Lambda, etc.)
*   **Ghost CMS Hosting:** Self-hosted (DigitalOcean, AWS EC2, Google Cloud Compute, etc.)
*   **Database Hosting:**
    *   MongoDB: MongoDB Atlas (cloud)
    *   MySQL: Co-located with Ghost CMS instance
*   **CI/CD Tools:** TBD (GitHub Actions, GitLab CI, etc.)
*   **Containerization:** Docker (for Ghost CMS deployment consistency)
*   **Monitoring:** TBD (Ghost has basic built-in monitoring, external services for comprehensive monitoring)

## Testing
*   **Frontend Frameworks:** TBD (Jest, React Testing Library, Cypress)
*   **Backend Frameworks:** TBD (Pytest)
*   **Integration Testing:** Ghost API integration tests, webhook delivery testing
*   **Content Pipeline Testing:** End-to-end testing of Ghost → RAG synchronization

## Build Tools & Package Managers
*   **Frontend:** npm (standard with Next.js)
*   **Backend:** pip with `requirements.txt`
*   **Ghost CMS:** Ghost-CLI for installation and management

## Key Libraries & Justifications

### Core Framework Choices
*   **Next.js:** Chosen for robust React-based frontend development, SSR/SSG capabilities, and excellent Vercel integration.
*   **Tailwind CSS:** Chosen for utility-first CSS development, enabling rapid UI construction.
*   **Python/FastAPI:** Chosen for backend due to Python's strong AI/ML ecosystem and FastAPI's high performance and ease of use for building APIs.

### Ghost CMS Integration
*   **Ghost CMS:** Selected for its:
    *   **Native Markdown support:** Perfect alignment with existing RAG pipeline requirements
    *   **Foundation-friendly RBAC:** Contributors create drafts, Foundation controls publishing
    *   **Robust Content API:** Comprehensive access to content and metadata
    *   **Professional editorial interface:** Streamlined content creation and management
    *   **Webhook system:** Real-time synchronization capabilities
    *   **Enterprise reliability:** Mature, battle-tested platform used by major organizations
*   **MySQL (Ghost requirement):** Accepted as necessary for Ghost CMS, maintains separation from MongoDB vector storage
*   **Ghost Content API:** Provides rich JSON responses with content, metadata, and relationships
*   **HTML-to-Markdown conversion:** Necessary bridge between Ghost's HTML output and RAG pipeline's Markdown processing

### RAG Pipeline Libraries
*   **Google Text Embedding 004:** Specified for generating text embeddings with critical `task_type` usage:
    *   `task_type='retrieval_document'` for stored Ghost content
    *   `task_type='retrieval_query'` for user queries
    *   Hierarchical chunking strategy maintained for optimal context preservation
*   **MongoDB Atlas Vector Search:** Chosen for vector storage and similarity search capabilities
*   **Langchain:** Core RAG orchestration framework
*   **markdownify/html2text:** Bridge libraries for converting Ghost HTML to Markdown

### Content Processing
*   **`embedding_processor_ghost.py`:** New specialized processor for Ghost content:
    *   Handles Ghost Content API JSON responses
    *   Converts HTML to Markdown while preserving structure
    *   Maps Ghost metadata to RAG pipeline metadata schema
    *   Maintains hierarchical chunking for optimal retrieval
*   **Webhook handlers:** Real-time synchronization between Ghost and RAG pipeline
*   **Ghost API clients:** Robust integration with Ghost's REST API

## Migration Strategy from Custom CMS
*   **Phase 1:** Set up Ghost CMS infrastructure and Content API integration
*   **Phase 2:** Develop `embedding_processor_ghost.py` and webhook handlers
*   **Phase 3:** Migrate existing `knowledge_base/` Markdown content to Ghost
*   **Phase 4:** Establish Foundation editorial workflows in Ghost
*   **Phase 5:** Deprecate custom CMS components and redirect development focus

## Security Considerations
*   **Ghost CMS Security:**
    *   Regular Ghost version updates
    *   Secure Ghost hosting configuration
    *   SSL/TLS encryption for Ghost admin and API access
    *   Strong authentication for Ghost admin accounts
*   **API Security:**
    *   Ghost Content API key management
    *   Webhook signature verification
    *   Rate limiting on webhook endpoints
*   **Database Security:**
    *   MySQL access restricted to Ghost instance
    *   MongoDB Atlas security best practices
    *   Secure network configurations

## Performance Considerations
*   **Ghost CMS Performance:**
    *   Ghost instance sizing appropriate for content volume
    *   Database optimization for Ghost MySQL instance
    *   CDN integration for Ghost-served content (if public-facing)
*   **RAG Pipeline Performance:**
    *   Efficient webhook processing to avoid blocking Ghost
    *   Asynchronous content processing
    *   Vector search optimization
    *   Caching strategies for frequently accessed content

## Operational Monitoring
*   **Ghost CMS Monitoring:**
    *   Ghost instance health monitoring
    *   MySQL database performance monitoring
    *   Content publishing workflow monitoring
*   **Integration Monitoring:**
    *   Webhook delivery success rates
    *   Content synchronization lag monitoring
    *   RAG pipeline processing times
    *   Vector store update verification

This revised tech stack reflects the strategic decision to leverage Ghost CMS for content management while maintaining the existing RAG pipeline architecture, providing a mature, reliable foundation for the Litecoin knowledge base with optimal integration characteristics.