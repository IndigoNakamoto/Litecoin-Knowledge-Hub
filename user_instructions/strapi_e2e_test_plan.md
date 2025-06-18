# End-to-End Test Plan: Strapi Webhook Integration

This document provides a complete plan for testing the Strapi webhook integration with the FastAPI backend. It covers the initial setup, a step-by-step guide for each CRUD operation, and the expected outcomes.

## I. Setup Instructions

### Prerequisites
*   You have `ngrok` installed. If not, download it from [ngrok.com/download](https://ngrok.com/download).
*   Your FastAPI and Strapi development servers are ready to be started.

### Step 1: Start the Development Servers (3 Terminals)

**Terminal 1: FastAPI Backend Server**
1.  Navigate to the `backend` directory: `cd backend`
2.  Activate your Python virtual environment.
3.  Start the server: `uvicorn main:app --reload`
4.  **Keep this terminal visible to monitor logs.**

**Terminal 2: Strapi CMS Server**
1.  Navigate to the Strapi directory: `cd backend/cms`
2.  Start the server: `npm run develop`

**Terminal 3: ngrok Tunnel**
1.  In a new terminal, expose your local FastAPI server (port 8000):
    ```bash
    ngrok http 8000
    ```
2.  From the `ngrok` output, **copy the HTTPS `Forwarding` URL**.

### Step 2: Configure the Strapi Webhook

1.  Open the Strapi admin panel (usually `http://localhost:1337/admin`).
2.  Navigate to **Settings** -> **Webhooks**.
3.  Click **"Add new webhook"**.
4.  **Name:** `RAG Sync`
5.  **URL:** Paste your `ngrok` HTTPS URL and append the endpoint path: `/api/v1/sync/strapi`.
    *   *Example:* `https://<random-characters>.ngrok-free.app/api/v1/sync/strapi`
6.  **Events:** Check the boxes for all **Entry** events (`create`, `update`, `delete`, `publish`, `unpublish`).
7.  **Save** the webhook.

---

## II. End-to-End Testing Procedure

Follow these steps sequentially. After each action in the Strapi UI, copy the logs from the FastAPI Server Terminal and provide them for analysis.

### Test Case 1: Create & Publish a New Article

**Action:**
1.  In the Strapi UI, go to **Content Manager** -> **Article**.
2.  Click **"Create new entry"**.
3.  Enter a `title`, `slug`, and some `content`.
4.  Click **Save**.
5.  Click **Publish**.

**Expected Outcome (FastAPI Logs):**
*   A log message indicating a `POST` request to `/api/v1/sync/strapi`.
*   A log message showing "Received Strapi webhook for event: entry.publish".
*   Logs indicating that the article content is being processed, chunked, and embedded.
*   A final log confirming that the documents have been successfully added to the vector store.

### Test Case 2: Update a Published Article

**Action:**
1.  In the Strapi UI, open the article you just published.
2.  Make a change to the `content` field.
3.  Click **Save**. (This automatically triggers the `entry.update` webhook for published content).

**Expected Outcome (FastAPI Logs):**
*   A log message indicating a `POST` request to `/api/v1/sync/strapi`.
*   A log message showing "Received Strapi webhook for event: entry.update".
*   Logs showing that the existing documents for the article are being deleted.
*   Logs showing that the updated content is being processed and re-embedded.
*   A final log confirming the new documents have been added to the vector store.

### Test Case 3: Unpublish an Article

**Action:**
1.  In the Strapi UI, open the article you have been testing.
2.  Click the **Unpublish** button.

**Expected Outcome (FastAPI Logs):**
*   A log message indicating a `POST` request to `/api/v1/sync/strapi`.
*   A log message showing "Received Strapi webhook for event: entry.unpublish".
*   Logs indicating that documents with the corresponding `strapi_id` are being deleted from the vector store.
*   A final log confirming the successful deletion.

### Test Case 4: Delete an Article

**Action:**
1.  First, re-publish the article so it exists in the vector store again. Wait for the `entry.publish` logs to confirm it's been added.
2.  From the **Article** list view in the Content Manager, click the trash can icon to delete the article.

**Expected Outcome (FastAPI Logs):**
*   A log message indicating a `POST` request to `/api/v1/sync/strapi`.
*   A log message showing "Received Strapi webhook for event: entry.delete".
*   Logs indicating that documents with the corresponding `strapi_id` are being deleted from the vector store.
*   A final log confirming the successful deletion.

---

Please begin with **Part I: Setup Instructions**. Once you are set up, proceed to **Part II, Test Case 1** and paste the logs when ready.
