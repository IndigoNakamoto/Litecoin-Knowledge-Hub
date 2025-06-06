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

## Database
*   **Type:** MongoDB
*   **Usage:**
    *   Vector storage and search for RAG.
    *   General application data (if needed).
*   **ORM/ODM:** (To be determined, e.g., Pydantic for FastAPI, `MongoEngine` or direct `pymongo` usage)

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
*   **Google Text Embedding 004:** Specified for generating text embeddings for the RAG system.
*   **MongoDB:** Chosen for its flexibility and capabilities for vector search, suitable for RAG applications.

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
