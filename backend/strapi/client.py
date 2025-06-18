import os
import httpx
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class StrapiClient:
    """
    An asynchronous client to interact with the Strapi REST API.
    """

    def __init__(self):
        """
        Initializes the StrapiClient, loading configuration from environment variables.
        """
        self.base_url = os.getenv("STRAPI_API_URL", "http://localhost:1337/api")
        self.api_token = os.getenv("STRAPI_FULL_ACCESS_TOKEN")

        if not self.api_token:
            raise ValueError("STRAPI_FULL_ACCESS_TOKEN environment variable not set.")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        A private helper method to make asynchronous HTTP requests.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            endpoint (str): The API endpoint to target (e.g., '/articles').
            **kwargs: Additional arguments to pass to httpx.request.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        
        Raises:
            httpx.HTTPStatusError: If the API returns an unsuccessful status code.
        """
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            return response.json()

    async def get_entries(self, collection_name: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetches a list of entries from a specified Strapi collection.

        Args:
            collection_name (str): The plural API ID of the collection (e.g., 'articles').
            params (Optional[Dict[str, Any]]): A dictionary of query parameters (e.g., for sorting, filtering, population).

        Returns:
            List[Dict[str, Any]]: A list of entry objects from the API.
        """
        endpoint = f"/{collection_name}"
        response_data = await self._request("GET", endpoint, params=params)
        return response_data.get("data", [])

    async def get_entry(self, collection_name: str, entry_id: int, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches a single entry from a specified Strapi collection by its ID.

        Args:
            collection_name (str): The plural API ID of the collection (e.g., 'articles').
            entry_id (int): The ID of the entry to retrieve.
            params (Optional[Dict[str, Any]]): A dictionary of query parameters.

        Returns:
            Optional[Dict[str, Any]]: The entry object, or None if not found.
        """
        endpoint = f"/{collection_name}/{entry_id}"
        try:
            response_data = await self._request("GET", endpoint, params=params)
            return response_data.get("data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches a single article by its ID, ensuring all relations are populated.

        Args:
            article_id (int): The ID of the article to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The article object, or None if not found.
        """
        return await self.get_entry("articles", article_id, params={"populate": "*"})

# Example usage (for testing purposes)
async def main():
    print("Initializing Strapi Client...")
    client = StrapiClient()
    print("Fetching articles...")
    try:
        articles = await client.get_entries("articles", params={"populate": "*"})
        if articles:
            print(f"Successfully fetched {len(articles)} articles.")
            # print("First article:", articles[0])
        else:
            print("No articles found. This may be expected if the CMS is empty.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the Strapi server is running and the API token is correct.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
