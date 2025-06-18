import asyncio
import os
from backend.strapi.client import StrapiClient

# This is the ID of the article you are trying to publish/update in the tests.
# Please update this ID to match an article that you know exists in your Strapi CMS.
TEST_ARTICLE_ID = 101 

async def main():
    """
    A simple script to test the StrapiClient's ability to fetch an article.
    """
    print("--- Strapi Client Debugger ---")
    
    # Check for environment variables
    api_url = os.getenv("STRAPI_API_URL")
    api_token = os.getenv("STRAPI_API_TOKEN") or os.getenv("STRAPI_FULL_ACCESS_TOKEN")

    if not api_url:
        print("ERROR: STRAPI_API_URL environment variable is not set.")
        return
    if not api_token:
        print("ERROR: STRAPI_API_TOKEN or STRAPI_FULL_ACCESS_TOKEN environment variable is not set.")
        return
        
    print(f"Attempting to connect to Strapi at: {api_url}")
    print(f"Using API Token: {api_token[:4]}...{api_token[-4:]}") # Print partial token for verification

    try:
        client = StrapiClient()
        print(f"\nStrapiClient initialized with base URL: {client.base_url}")
        print(f"Fetching article with ID: {TEST_ARTICLE_ID}...")
        
        # Add publicationState=preview to fetch drafts as well as published content
        params = {"populate": "*", "publicationState": "preview"}
        article = await client.get_entry("articles", TEST_ARTICLE_ID, params=params)
        
        if article:
            print("\n--- SUCCESS! ---")
            print("Successfully fetched article data:")
            print(article)
        else:
            print("\n--- FAILURE ---")
            print("Failed to fetch article. The client received a 'None' response.")
            print("This most likely means the Strapi API returned a 404 Not Found error.")
            print("Please verify the following:")
            print(f"1. An article with ID '{TEST_ARTICLE_ID}' actually exists.")
            print("2. The API Token has 'find' permissions for the 'Article' content type.")

    except Exception as e:
        print("\n--- AN ERROR OCCURRED ---")
        print(f"The test script failed with an exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure you run this from the root of the project, e.g.:
    # python -m backend.debug_strapi_client
    asyncio.run(main())
