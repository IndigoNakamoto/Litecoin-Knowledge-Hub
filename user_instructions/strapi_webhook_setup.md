# How to Configure Strapi Webhooks for Local Development

This guide explains how to test the Strapi webhook integration on a local development machine by exposing your local FastAPI server to the internet using `ngrok`.

## Prerequisites
*   You have `ngrok` installed. If not, download it from [ngrok.com/download](https://ngrok.com/download).
*   Your FastAPI and Strapi development servers are ready to be started.

## Step 1: Start the Development Servers

You will need three separate terminal windows.

### Terminal 1: Start the FastAPI Backend Server
1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Activate your Python virtual environment if you have one.
3.  Start the FastAPI server using `uvicorn`. It will automatically reload when code changes.
    ```bash
    uvicorn main:app --reload
    ```
    Keep this terminal open to monitor for webhook activity.

### Terminal 2: Start the Strapi CMS Server
1.  Navigate to the Strapi directory:
    ```bash
    cd backend/cms
    ```
2.  Start the Strapi development server:
    ```bash
    npm run develop
    ```
    This will launch the Strapi admin panel, typically at `http://localhost:1337/admin`.

## Step 2: Expose Your FastAPI Server with ngrok

### Terminal 3: Start ngrok
1.  In a new terminal, run the following command to create a public tunnel to your local FastAPI server, which runs on port 8000 by default.
    ```bash
    ngrok http 8000
    ```
2.  `ngrok` will display a session status screen. Look for the line that starts with `Forwarding` and **copy the HTTPS URL**. It will look something like `https://<random-characters>.ngrok-free.app`.

## Step 3: Configure the Webhook in Strapi

1.  Open the Strapi admin panel in your browser (usually `http://localhost:1337/admin`).
2.  Navigate to **Settings** -> **Webhooks**.
3.  Click **"Add new webhook"**.
4.  **Name:** Give it a descriptive name, like `RAG Sync`.
5.  **URL:** Paste the `ngrok` HTTPS URL you copied and append the specific endpoint path: `/api/v1/sync/strapi`.
    *   Example: `https://<random-characters>.ngrok-free.app/api/v1/sync/strapi`
6.  **Events:** Under "Events," check the boxes for all **Entry** events:
    *   `entry.create`
    *   `entry.update`
    *   `entry.delete`
    *   `entry.publish`
    *   `entry.unpublish`
7.  Click **Save**.

## Step 4: Test the Integration

You are now ready to test the webhook.

1.  In the Strapi admin panel, go to **Content Manager** -> **Article**.
2.  Create a new entry, fill in the details, **Save**, and then **Publish** it.
3.  Check your FastAPI server terminal (Terminal 1) for log output indicating that a webhook was received and processed. You can also check the `ngrok` terminal (Terminal 3) to see if a `POST /api/v1/sync/strapi` request was logged.
