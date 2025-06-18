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
    *   `requests`: For making HTTP requests to Strapi's REST API and other external services.
    *   `tweepy`: For interacting with the Twitter (X) API.
    *   `GitPython`: For cloning and interacting with Git repositories (e.g., GitHub).
    *   `beautifulsoup4`: For parsing HTML and XML documents (e.g., web scraping).
    *   `lxml`: A fast XML and HTML parser, often used as a backend for BeautifulSoup.
    *   `python-frontmatter`: For parsing YAML front matter from legacy Markdown files during migration to Strapi.
    *   **Strapi Integration Libraries:**
        *   Native HTTP requests via `requests` for the Strapi REST API.
    *   **RAG Pipeline Specifics:**
        *   **Hierarchical Chunking:** Strapi's structured JSON content (e.g., rich text editor blocks) will be parsed and converted to a Markdown-like format. For each chunk, its parent titles will be prepended to the content before embedding, preserving the hierarchical context.
        *   **Embedding `task_type`:**
            *   Knowledge base documents are embedded using `task_type='retrieval_document'`.
            *   User queries are embedded using `task_type='retrieval_query'`.
            *   This asymmetric approach is critical for optimal performance with the `text-embedding-004` model.

## Content Management System
*   **CMS Platform:** Strapi (self-hosted)
*   **CMS Database:** PostgreSQL (preferred) or MySQL
*   **Content Format:** Customizable content types with a rich text editor (JSON output).
*   **Editorial Workflow:** Foundation-controlled (Contributors → Foundation review → Publish)
*   **Integration Method:** Strapi REST API + Webhooks for real-time synchronization
*   **Access Control:** Strapi's built-in Role-Based Access Control (RBAC).

## Database Architecture
*   **Content Storage:** PostgreSQL or MySQL (for Strapi CMS)
*   **Vector Storage:** MongoDB Atlas Vector Search (RAG pipeline)
*   **General Application Data:** MongoDB (if needed for additional features)
*   **ORM/ODM:** 
    *   Direct `pymongo` usage for MongoDB operations
    *   Strapi handles its database operations internally.
    *   Pydantic models for data validation and serialization in FastAPI layer

## RAG Pipeline Components
*   **Data Sources:**
    *   **Primary:** Strapi CMS via REST API
    *   **Secondary:** Legacy Markdown files (during migration), GitHub, Web scraping
*   **Content Processing:**
    *   Strapi content fetched via REST API (JSON format)
    *   JSON content processed by `embedding_processor_strapi.py` to extract text and structure for hierarchical chunking.
    *   Metadata extracted from Strapi API (authors, tags, publish dates, etc.)
*   **Embedding Model:** Google Text Embedding 004 (`text-embedding-004`)
    *   Knowledge base documents: `task_type='retrieval_document'`
    *   User queries: `task_type='retrieval_query'`
*   **Vector Store:** MongoDB Atlas Vector Search
*   **Retriever:** Implemented via `VectorStoreManager` using similarity search (default k=3)
*   **Generator:** Langchain with `ChatGoogleGenerativeAI` (gemini-pro)
*   **Orchestration:** Langchain
*   **Synchronization:** Strapi webhooks trigger RAG pipeline updates

## Strapi CMS Integration Architecture
*   **Content Retrieval:**
    ```python
    # Strapi REST API integration pattern
    async def fetch_strapi_articles():
        response = await strapi_client.get('/api/articles', params={'populate': '*'})
        return response.json()['data']
    ```
*   **Webhook Processing:**
    ```python
    # Webhook handler for content synchronization
    async def process_strapi_webhook(payload):
        event = payload.get('event')  # e.g., 'entry.publish', 'entry.unpublish'
        model = payload.get('model')  # e.g., 'article'
        entry = payload.get('entry')

        if event == 'entry.publish':
            await sync_content_to_rag(entry)
        elif event == 'entry.unpublish':
            await remove_from_rag(entry['id'])
    ```
*   **Content Processing Pipeline:**
    ```
    Strapi REST API → JSON Content → Structured Text Conversion → 
    Hierarchical Chunking → Embedding → MongoDB Vector Store
    ```

## Vector Search Configuration
*   **Metadata Handling:** Strapi API metadata (author, tags, publishedAt, etc.) mapped to MongoDB document fields for filtering.
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
          "path": "strapi_id"
        },
        {
          "type": "filter",
          "path": "slug"
        },
        {
          "type": "filter",
          "path": "author"
        },
        {
          "type": "filter",
          "path": "tags"
        },
        {
          "type": "filter",
          "path": "publishedAt"
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
*   **Strapi CMS Hosting:** Self-hosted (DigitalOcean, AWS EC2, Google Cloud Compute, etc.)
*   **Database Hosting:**
    *   MongoDB: MongoDB Atlas (cloud)
    *   PostgreSQL/MySQL: Co-located with Strapi CMS instance or as a managed service.
*   **CI/CD Tools:** TBD (GitHub Actions, GitLab CI, etc.)
*   **Containerization:** Docker (for Strapi CMS deployment consistency)
*   **Monitoring:** TBD (External services for comprehensive monitoring of the Strapi instance)

## Testing
*   **Frontend Frameworks:** TBD (Jest, React Testing Library, Cypress)
*   **Backend Frameworks:** TBD (Pytest)
*   **Integration Testing:** Strapi API integration tests, webhook delivery testing
*   **Content Pipeline Testing:** End-to-end testing of Strapi → RAG synchronization

## Build Tools & Package Managers
*   **Frontend:** npm (standard with Next.js)
*   **Backend:** pip with `requirements.txt`
*   **Strapi CMS:** `npx create-strapi-app` or Docker for installation and management

## Key Libraries & Justifications

### Core Framework Choices
*   **Next.js:** Chosen for robust React-based frontend development, SSR/SSG capabilities, and excellent Vercel integration.
*   **Tailwind CSS:** Chosen for utility-first CSS development, enabling rapid UI construction.
*   **Python/FastAPI:** Chosen for backend due to Python's strong AI/ML ecosystem and FastAPI's high performance and ease of use for building APIs.

### Strapi CMS Integration
*   **Strapi CMS:** Selected for its:
    *   **Superior Database Control:** Full ownership and optimization of the data layer.
    *   **Flexible Content Structuring:** Customizable content types are ideal for RAG.
    *   **Open-Source and Self-Hosted:** Aligns with project's control and ownership principles.
    *   **Built-in RBAC:** Enforces Foundation-controlled editorial workflows out-of-the-box.
    *   **REST API & Webhooks:** Robust mechanisms for integration with the RAG pipeline.
*   **PostgreSQL/MySQL:** Standard, powerful database options for Strapi.
*   **Strapi REST API:** Provides flexible and powerful ways to query content.
*   **JSON Content Processing:** Direct handling of structured JSON from Strapi is more robust than converting from HTML.

### RAG Pipeline Libraries
*   **Google Text Embedding 004:** Specified for generating text embeddings with critical `task_type` usage:
    *   `task_type='retrieval_document'` for stored Strapi content
    *   `task_type='retrieval_query'` for user queries
    *   Hierarchical chunking strategy maintained for optimal context preservation
*   **MongoDB Atlas Vector Search:** Chosen for vector storage and similarity search capabilities
*   **Langchain:** Core RAG orchestration framework
*   **`requests`:** Used to interact with the Strapi REST API.

### Content Processing
*   **`embedding_processor_strapi.py`:** New specialized processor for Strapi content:
    *   Handles Strapi REST API JSON responses.
    *   Parses structured JSON to extract text and create a hierarchical context.
    *   Maps Strapi metadata to the RAG pipeline metadata schema.
    *   Maintains hierarchical chunking for optimal retrieval.
*   **Webhook handlers:** Real-time synchronization between Strapi and the RAG pipeline.
*   **Strapi API client:** A module to handle communication with the Strapi API.

## Migration Strategy
*   **Phase 1:** Set up Strapi CMS infrastructure and define content types.
*   **Phase 2:** Develop `embedding_processor_strapi.py` and webhook handlers.
*   **Phase 3:** Establish Foundation editorial workflows in Strapi.
*   **Phase 4:** Deprecate any remaining legacy CMS components.

## Security Considerations
*   **Strapi CMS Security:**
    *   Regular Strapi version updates.
    *   Secure Strapi hosting configuration.
    *   SSL/TLS encryption for Strapi admin and API access.
    *   Strong authentication for Strapi admin accounts.
*   **API Security:**
    *   Secure management of Strapi API tokens.
    *   Webhook signature verification (if available/implemented).
    *   Rate limiting on API and webhook endpoints.
*   **Database Security:**
    *   Database access restricted to the Strapi instance.
    *   MongoDB Atlas security best practices
    *   Secure network configurations

## Performance Considerations
*   **Strapi CMS Performance:**
    *   Strapi instance sizing appropriate for content volume.
    *   Database optimization for the chosen database (PostgreSQL/MySQL).
    *   CDN integration for Strapi-served assets.
*   **RAG Pipeline Performance:**
    *   Efficient webhook processing to avoid blocking Strapi.
    *   Asynchronous content processing.
    *   Vector search optimization.
    *   Caching strategies for frequently accessed content.

## Operational Monitoring
*   **Strapi CMS Monitoring:**
    *   Strapi instance health monitoring.
    *   Database performance monitoring.
    *   Content publishing workflow monitoring.
*   **Integration Monitoring:**
    *   Webhook delivery success rates.
    *   Content synchronization lag monitoring.
    *   RAG pipeline processing times.
    *   Vector store update verification.

This revised tech stack reflects the strategic decision to leverage Strapi for content management, providing greater data control and flexibility for the RAG pipeline while establishing a mature, reliable foundation for the Litecoin knowledge base.
