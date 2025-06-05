# Litecoin RAG Chat

## Project Overview
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from trusted open-source sources. It aims to solve the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This will enhance user experience and foster greater adoption of Litecoin.

**Target Users/Audience:** Litecoin users (novice and experienced), Cryptocurrency enthusiasts, Developers building on Litecoin, Potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.

## Key Features

### Feature 1: Litecoin Basics & FAQ
Provides clear, concise answers to fundamental questions about Litecoin, its history, how it works, and common terminology. Caters especially to new users.

### Feature 2: Transaction & Block Explorer
Allows users to look up details of Litecoin transactions (e.g., status, confirmations, fees) using a transaction ID, and explore block information (e.g., height, timestamp, included transactions).

### Feature 3: Market Data & Insights
Delivers real-time Litecoin price information, market capitalization, trading volume, and basic chart data from reliable market APIs.

### Feature 4: Developer Documentation & Resources
Provides quick access to snippets from Litecoin developer documentation, links to key resources, and answers to common technical questions for developers building on Litecoin.

## Technology Stack
*   **Frontend:** Next.js, Tailwind CSS
*   **Backend:** Python, FastAPI, Langchain (core packages: `langchain`, `langchain-core`, `langchain-community`), Google Text Embedding (specifically `text-embedding-004`)
*   **Database:** MongoDB (for vector storage and general data)
*   **Deployment:** Vercel (for frontend)

## Project Structure
*   **Git Repository Root:** `Litecoin-RAG-Chat/` (This is the root of the monorepo and the Git repository.)
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore for both frontend and backend.
*   `frontend/`: Contains the Next.js application.
    *   `src/`: Main source code for the Next.js application (using App Router).
*   `backend/`: Contains the FastAPI application.
    *   `main.py`: Main FastAPI application file.
    *   `requirements.txt`: Python dependencies.
*   `cline_docs/`: Contains project documentation.
*   `cline_agent_workspace/`: Contains agent's operational files.
*   `user_instructions/`: Contains instructions for the user.

## Getting Started

### Prerequisites
*   **Node.js:** Version 18.18.0 or newer (managed via nvm is recommended).
*   **npm:** Node package manager (comes with Node.js).
*   **Python:** Version 3.x.
*   **pip:** Python package installer (comes with Python).
*   **Virtual Environment:** Recommended for Python projects.

### Running Development Servers

This document provides instructions to run the Next.js frontend and FastAPI backend development servers to verify the "Hello World" setups.

#### Frontend (Next.js)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The Next.js development server should start, typically on `http://localhost:3000`.

3.  **Verify:**
    Open your web browser and go to `http://localhost:3000`. You should see the default Next.js "Welcome" page.

    **Note on Node.js Version:** During the `create-next-app` process, warnings related to your Node.js version (v18.17.0) were observed, as some dependencies expected v18.18.0 or newer. While the scaffolding was successful, consider upgrading Node.js to the latest LTS version (>=18.18.0) at your convenience to prevent potential issues later.

#### Backend (FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment (recommended):**
    *   Create the environment:
        ```bash
        python3 -m venv venv
        ```
    *   Activate the environment:
        *   On macOS/Linux:
            ```bash
            source venv/bin/activate
            ```
        *   On Windows:
            ```bash
            .\venv\Scripts\activate
            ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the development server:**
    ```bash
    uvicorn main:app --reload
    ```
    The FastAPI development server should start, typically on `http://localhost:8000`.

5.  **Verify:**
    Open your web browser or a tool like Postman and go to `http://localhost:8000/`. You should see a JSON response:
    ```json
    {"message":"Hello World"}
    ```

If you encounter any issues, please check the terminal output for error messages.

## Documentation
The project's core documentation is maintained in the `cline_docs/` directory:
*   `projectRoadmap.md`: High-level project vision, goals, architecture, and major milestones.
*   `currentTask.md`: Details active tasks, backlog, progress, and Cline's immediate plan.
*   `techStack.md`: Documents all technology choices, frameworks, tools, and their rationale.
*   `codebaseSummary.md`: Provides an overview of the project's structure, key components, data flow, and dependencies.

## Contributing
(Contribution guidelines will be added here.)

## License
(License information will be added here.)
