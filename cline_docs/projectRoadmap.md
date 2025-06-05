# Project Roadmap: Litecoin RAG Chat

## Project Scope & Objectives
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from trusted open-source sources. It aims to solve the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.

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

## Architectural Overview & Patterns
*   The project utilizes a Next.js frontend and a Python/FastAPI backend. A microservices-oriented architectural approach is being considered for the RAG capabilities, with further details to be fleshed out as development progresses.

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
*   **Milestone 1:** Project Initialization & Documentation Setup (Current)
*   **Milestone 2:** Basic Project Scaffold (Next.js Frontend, FastAPI Backend)
*   **Milestone 3:** Core RAG Pipeline Implementation (Data Ingestion, Embedding, Retrieval, Generation)
*   **Milestone 4:** MVP Feature 1 Implementation (Litecoin Basics & FAQ)
*   **Milestone 5:** MVP Feature 2 Implementation (Transaction & Block Explorer)
*   (Timelines to be determined)

## Success Metrics
*   Achieve an average user engagement of 10,000 queries per week within 6 months of launch.
*   Process at least 1,000 unique transaction-related queries per day with 95% accuracy.
*   Attain a user satisfaction rating of 4.5/5 based on post-interaction surveys.

## Completion Criteria
*   (For the project/major phases - to be defined)

## Log of Completed Major Milestones/Phases
*   Milestone 1: Project Initialization & Documentation Setup - Completed 6/5/2025
*   Milestone 2: Basic Project Scaffold (Next.js Frontend, FastAPI Backend) - Completed 6/5/2025
