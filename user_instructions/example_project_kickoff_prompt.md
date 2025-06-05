# Initiate New Project: Litecoin RAG Chat

Hi Cline,

We are initiating a new project called **Litecoin RAG Chat**. Your primary directive is to assist in its development, strictly following your custom instructions (the "Unified Cline Super-Prompt").

Please begin by processing this initial information to populate the `cline_docs` for this new project. After your initial processing and `cline_docs` setup, present your `session_summary.md` for review, including your plan for the first *actual* development task.

## 1. Project Vision & Core Goal (for `projectRoadmap.md`)
*   **Brief Description:**  
A RAG (Retrieval-Augmented Generation) Chatbot for Litecoin users is an AI-powered conversational tool that provides real-time, accurate answers about Litecoin by retrieving relevant data from trusted open-source sources. It solves the problem of misinformation and scattered resources by offering a centralized, reliable way for users to access Litecoin-related information, such as transactions, wallet management, and market insights. This enhances user experience and fosters greater adoption of Litecoin.
*   **Primary Goal(s):** 
Deliver accurate, real-time responses to Litecoin-related queries using open-source data like blockchain records, market APIs, and community resources.  
Simplify user access to Litecoin information, reducing reliance on fragmented or unverified sources.  
Increase user engagement and trust in the Litecoin ecosystem through reliable, conversational support.
*   **Target Users/Audience:** 
Litecoin users (novice and experienced), cryptocurrency enthusiasts, developers building on Litecoin, and potential adopters seeking reliable information about Litecoin’s features, transactions, or market trends.  
*   **Success Metrics (if known):** 
Achieve an average user engagement of 10,000 queries per week within 6 months of launch.  
Process at least 1,000 unique transaction-related queries per day with 95% accuracy.  
Attain a user satisfaction rating of 4.5/5 based on post-interaction surveys.

## 2. Initial Technical Considerations (for `techStack.md`)
*   **Preferred Frontend Technologies (if any):** Next.js, tailwind, ...
*   **Preferred Backend Technologies (if any):** Python, FastAPI, google text embedding, mongodb search for vector, ...
*   **Preferred Database (if any):** Mongo
*   **Deployment Environment (if known):** Vercel
*   **Key Non-Functional Requirements:** [e.g., "Must be highly scalable to 100 users," "Requires response times under 3000 ms," "High security for sensitive data," "Mobile-first design."]
*   **Any existing code, libraries, or services to integrate?** I have another project that takes youtube videos, summarizes them, creates a timeseries list of topics. For each topic is the start time, title, summary, transcript slice. Each topic gets embedded using google text embedding 004. Their is also a NextJS frontend that integrates with youtube and provides a UI to navigate the video find the clip or topic.

## 3. Core Features - Initial Thoughts (for `projectRoadmap.md`)
*(List 2-4 high-level features you envision for the MVP or first phase.)*
*   **Feature 1:** [Name of Feature 1] - [Brief description of what it does and for whom.]
*   **Feature 2:** [Name of Feature 2] - [Brief description.]
*   **(Optional) Feature 3:** [Name of Feature 3] - [Brief description.]

## 4. First Task Definition (for `currentTask.md`)
*   **Task ID / Name:** `INIT-001` - Project Initialization and Documentation Setup
*   **Detailed Description & Business Context:** Based on the information provided in this "Initiate New Project" prompt, your task is to:
    1.  Thoroughly review and internalize your custom instructions.
    2.  Perform your "Pre-Task Analysis & Planning" thinking step.
    3.  Populate the initial versions of all four `cline_docs` files (`projectRoadmap.md`, `currentTask.md`, `techStack.md`, `codebaseSummary.md`) with the information provided and any reasonable defaults or placeholders where information is missing.
    4.  For `currentTask.md`, detail this `INIT-001` task and then define and plan the *next logical development task* (e.g., "Scaffold initial project structure," "Create 'Hello World' application," "Set up basic CI/CD pipeline").
*   **Acceptance Criteria for `INIT-001`:**
    *   All four `cline_docs` files are created/populated in the project's `cline_docs` directory.
    *   `projectRoadmap.md` reflects the initial vision, goals, and features.
    *   `techStack.md` outlines initial technology considerations and areas needing decisions.
    *   `currentTask.md` details `INIT-001` as "In Progress" or "Done" (once you present the summary) and clearly defines the *next* development task with its own plan.
    *   `codebaseSummary.md` is created (can be minimal, e.g., stating "Initial project setup, codebase not yet established").
    *   You have presented your `session_summary.md` detailing your analysis, actions, and proposed `cline_docs` content for review.

Please proceed. I am ready for your questions and your initial `session_summary.md`.