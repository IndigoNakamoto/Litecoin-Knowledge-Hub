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

