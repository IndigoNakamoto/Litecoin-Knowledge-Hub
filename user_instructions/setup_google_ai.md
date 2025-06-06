# How to Set Up Your Google AI API Key

This guide provides the steps to obtain and configure your Google AI API key, which is essential for the project's embedding generation using Google Text Embedding 004 and for utilizing Google's Language Models (LLMs) in the RAG pipeline.

## Prerequisites
- A Google account.

## Steps to Get Your API Key

1.  **Navigate to Google AI Studio:**
    *   Open your web browser and go to [Google AI Studio](https://aistudio.google.com/).
    *   Sign in with your Google account if prompted.

2.  **Create a New API Key:**
    *   Once in Google AI Studio, look for the "Get API key" or "Create API key" option. This is typically found in the left-hand navigation menu under "API key" or "Develop" -> "API keys".
    *   Click on "Create API key in new project" or "Create API key" if you already have a project.

3.  **Copy Your API Key:**
    *   After the key is generated, it will be displayed on the screen. Copy this key immediately.
    *   **Important:** Google AI Studio usually only shows the full API key once. Make sure to copy it and store it securely.

## How to Use the API Key in Your Project

1.  **Create a `.env` file:**
    *   Navigate to the `backend/` directory in your project.
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```

2.  **Add Your API Key to `.env`:**
    *   Open the newly created `.env` file in a text editor.
    *   Locate the line that corresponds to the Google API key and paste your copied key:
        ```
        GOOGLE_API_KEY="YOUR_COPIED_API_KEY_HERE"
        ```
    *   Replace `"YOUR_COPIED_API_KEY_HERE"` with the actual API key you obtained from Google AI Studio.

## Security Note
*   **Never commit your `.env` file to version control (e.g., Git).** The `.gitignore` file in the `backend/` directory should already prevent this, but always double-check. This file contains sensitive credentials that should not be exposed publicly.
