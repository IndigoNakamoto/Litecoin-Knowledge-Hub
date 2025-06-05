# Instructions to Run Development Servers

This document provides instructions to run the Next.js frontend and FastAPI backend development servers to verify the "Hello World" setups.

## Frontend (Next.js)

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

## Backend (FastAPI)

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
