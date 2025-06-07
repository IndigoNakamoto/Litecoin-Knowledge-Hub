# Project Roadmap: Litecoin RAG Chat

## Project Scope & Objectives
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from verified sources. It aims to solve the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.
*   Establish and maintain a canonical, human-vetted knowledge base that serves as the single source of truth for the RAG pipeline, ensuring the highest level of accuracy and clarity.

## Strategic Value Proposition: Specialist vs. Generalist AI

This project's value is not in competing with general-purpose AI models like ChatGPT or Grok, but in providing a specialized, high-accuracy information utility for the Litecoin ecosystem. Generalist models, while powerful, are not suitable for tasks requiring real-time, verifiable data from trusted sources.

Our RAG-based approach provides a distinct advantage by:

1.  **Ensuring Data Accuracy:** We retrieve information from a curated set of live data sources (e.g., blockchain APIs, market data, official documentation), mitigating the risk of AI "hallucinations."
2.  **Providing Real-Time Information:** Unlike the static knowledge of general models, our system can query live data for features like transaction lookups and current market prices.
3.  **Delivering Verifiable Trust:** Our responses are grounded in specific, trusted data sources, providing a level of reliability that is essential for financial and technical queries.

This focus on specialized, real-time, and accurate data is the core differentiator that makes the Litecoin RAG Chat a valuable and necessary tool for its target audience.

## Key Features & User Stories
*   **Primary Goal(s):**
    *   Deliver accurate, real-time responses to Litecoin-related queries using open-source data like blockchain records, market APIs, and community resources.
    *   Simplify user access to Litecoin information, reducing reliance on fragmented or unverified sources.
    *   Increase user engagement and trust in the Litecoin ecosystem through reliable, conversational support.
*   **Target Users/Audience:**
    *   Litecoin users (novice and experienced)
    *   Cryptocurrency enthusiasts
    *   Developers building on Litecoin
    *   Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.
*   **Core Features (MVP/Phase 1):**
    *   **Feature 1: Litecoin Basics & FAQ**
        *   Description: Provides clear, concise answers to fundamental questions about Litecoin, its history, how it works, and common terminology. Caters especially to new users.
        *   Example Queries: "What is Litecoin?", "How is Litecoin different from Bitcoin?", "How do I get a Litecoin wallet?"
    *   **Feature 2: Transaction & Block Explorer**
        *   Description: Allows users to look up details of Litecoin transactions (e.g., status, confirmations, fees) using a transaction ID, and explore block information (e.g., height, timestamp, included transactions). Useful for all users, including developers.
        *   Example Queries: "Check status of transaction [TXID]", "What was in block [Block Height]?", "How many confirmations does transaction [TXID] have?"
    *   **Feature 3: Market Data & Insights**
        *   Description: Delivers real-time Litecoin price information, market capitalization, trading volume, and basic chart data from reliable market APIs.
        *   Example Queries: "What's the current price of Litecoin?", "Show me Litecoin's market cap.", "Litecoin price trend last 7 days."
    *   **Feature 4: Developer Documentation & Resources**
        *   Description: Provides quick access to snippets from Litecoin developer documentation, links to key resources, and answers to common technical questions for developers building on Litecoin.
        *   Example Queries: "How to use Litecoin RPC call [method_name]?", "Link to Litecoin improvement proposals (LIPs).", "What are common Litecoin scripting opcodes?"
    *   **Feature 5: Curated Knowledge Base**
        *   Description: A continuously updated library of well-researched, clearly written articles and data covering all aspects of Litecoin. This content is explicitly structured for optimal machine retrieval and serves as the primary source for the chatbot's answers.

## Architectural Overview & Patterns
*   The project utilizes a Next.js frontend and a Python/FastAPI backend. The architecture is centered around a **content-first RAG pipeline**, where a curated knowledge base is ingested to provide context for the LLM, ensuring responses are grounded in verified information. A microservices-oriented architectural approach is being considered for the RAG capabilities, with further details to be fleshed out as development progresses.

## Core Technology Decisions
*   (Summary, see `techStack.md` for details)
    *   Frontend: Next.js, Tailwind CSS
    *   Backend: Python, FastAPI
    *   Database: MongoDB (for vector search and general data)
    *   Embedding: Google Text Embedding 004
    *   Deployment: Vercel

## Significant Constraints
*   Reliance on open-source data quality and availability.
*   Need for robust security for any user-specific data (if applicable in later phases).
*   Scalability to handle target user engagement.

## High-Level Security Requirements & Standards
*   Input validation for all user queries.
*   Protection against common web vulnerabilities (OWASP Top 10).
*   Secure handling of API keys for external services.
*   (Further details as features involving sensitive data are defined)

## Major Milestones & Tentative Timelines
*   **Milestone 1:** Project Initialization & Documentation Setup (Completed)
*   **Milestone 2:** Basic Project Scaffold (Next.js Frontend, FastAPI Backend) (Completed)
*   **Milestone 3:** Core RAG Pipeline Implementation (Data Ingestion, Embedding, Retrieval, Generation) (Completed)
*   **Milestone 4:** MVP Feature 1 Implementation (Litecoin Basics & FAQ) (Current)
*   **Milestone 5:** MVP Feature 2 Implementation (Transaction & Block Explorer)
*   (Timelines to be determined)

## Success Metrics
*   Achieve an average user engagement of 10,000 queries per week within 6 months of launch.
*   Process at least 1,000 unique transaction-related queries per day with 95% accuracy.
*   Attain a user satisfaction rating of 4.5/5 based on post-interaction surveys.

## Completion Criteria
*   (For the project/major phases - to be defined)

## Log of Completed Major Milestones/Phases
*   **Milestone 1: Project Initialization & Documentation Setup** - Completed 6/5/2025
    *   Initial `cline_docs` created and populated.
*   **Milestone 2: Basic Project Scaffold (Next.js Frontend, FastAPI Backend)** - Completed 6/5/2025
    *   Frontend (Next.js) and Backend (FastAPI) directory structures established.
    *   Basic "Hello World" functionality confirmed for both.
*   **Milestone 3: Core RAG Pipeline Implementation** - Completed 6/6/2025
    *   **Data Ingestion Framework:** Implemented and tested multi-source data loaders (Markdown, GitHub, Web).
    *   **Embedding:** Integrated Google Text Embedding 004.
    *   **Vector Store:** Set up and integrated MongoDB Atlas Vector Search.
    *   **Retrieval:** Implemented document retrieval based on similarity search.
    *   **Generation:** Integrated Langchain with `ChatGoogleGenerativeAI` (gemini-pro) to generate answers from retrieved context.
    *   **API:** `/api/v1/chat` endpoint created and functional, returning both the generated answer and source documents for transparency.
    *   **Testing:** Standalone test script (`backend/test_rag_pipeline.py`) created to validate the end-to-end pipeline.
    *   The core RAG pipeline is now functional and capable of ingesting data, retrieving relevant chunks, and generating answers with source attribution.
