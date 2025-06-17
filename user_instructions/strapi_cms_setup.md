# How to Set Up and Run the Strapi CMS

This guide provides the steps to start the local Strapi development server and create the initial administrator account.

## Prerequisites

-   Node.js (version specified in `cline_docs/techStack.md`)
-   `npm` or a compatible package manager

## Step-by-Step Instructions

1.  **Navigate to the CMS Directory:**
    Open your terminal and navigate to the Strapi application's root directory.

    ```bash
    cd backend/cms
    ```

2.  **Install Dependencies (if needed):**
    The `create-strapi-app` command should have already installed the necessary dependencies. However, if you encounter any issues, you can run the installation manually:

    ```bash
    npm install
    ```

3.  **Start the Development Server:**
    Run the following command to start the Strapi application in development mode. This will also watch for file changes and automatically restart the server.

    ```bash
    npm run develop
    ```

4.  **Create the Administrator Account:**
    Once the server is running, it will provide a URL to the admin panel (usually `http://localhost:1337/admin`). Open this URL in your web browser.

    -   You will be prompted with a registration form to create the first administrator account for the CMS.
    -   Fill out the required details (name, email, password) and complete the registration.

5.  **Access the Admin Panel:**
    After creating your account, you will be logged in and redirected to the Strapi admin dashboard. You can now begin creating content types, defining roles, and managing content.

## Configuring Webhooks for RAG Synchronization

To ensure that the RAG pipeline stays synchronized with the content in Strapi, you need to configure webhooks. These webhooks will notify the backend whenever content is created, updated, or deleted.

1.  **Navigate to Webhooks Settings:**
    In the Strapi admin panel, go to `Settings` -> `Webhooks`.

2.  **Create a New Webhook:**
    Click the "Add new webhook" button.

3.  **Configure the Webhook:**
    -   **Name:** Give the webhook a descriptive name, such as `RAG Sync`.
    -   **URL:** Enter the URL of the backend's webhook receiver endpoint. For local development, this will typically be `http://localhost:8000/api/v1/sync/strapi`.
    -   **Headers:** Add a new header for security.
        -   **Key:** `X-Strapi-Webhook-Secret`
        -   **Value:** The secret token you defined in your backend's `.env` file for the `STRAPI_WEBHOOK_SECRET` variable. This must be a strong, unguessable string.

4.  **Select Events:**
    Choose the events that will trigger this webhook. For complete synchronization, select the following events under the "Entry" section:
    -   `entry.create`
    -   `entry.update`
    -   `entry.delete`
    -   `entry.publish`
    -   `entry.unpublish`

5.  **Save the Webhook:**
    Click the "Save" button to create the webhook.

Now, whenever you perform one of the selected actions on an entry (like publishing an article), Strapi will send a notification to your backend, and the RAG pipeline's knowledge base will be updated automatically.
