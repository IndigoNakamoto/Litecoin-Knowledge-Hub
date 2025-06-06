import requests
from bs4 import BeautifulSoup
from typing import Dict

def load_web_article_data(url: str) -> Dict:
    """
    Fetches a web article, extracts its main content, and returns it.

    Args:
        url: The URL of the web article.

    Returns:
        A dictionary containing the extracted text content and metadata,
        or an empty dictionary if an error occurs.
    """
    try:
        response = requests.get(url, timeout=10) # Reason: Set a timeout for the request.
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'lxml')

        # Reason: Attempt to find the main content of the article.
        # This is a heuristic and might need refinement for different websites.
        article_text = ""
        # Common tags for main content: article, main, div with specific classes/ids
        main_content_tags = ['article', 'main', 'div', 'p']
        for tag_name in main_content_tags:
            found_tag = soup.find(tag_name)
            if found_tag:
                article_text = found_tag.get_text(separator='\n', strip=True)
                if article_text: # Reason: If content is found, break.
                    break
        
        if not article_text: # Fallback if specific tags don't yield content
            article_text = soup.get_text(separator='\n', strip=True)

        # Reason: Extract title for metadata.
        title = soup.find('title').get_text(strip=True) if soup.find('title') else "No Title"

        return {
            "content": article_text,
            "metadata": {
                "source_url": url,
                "title": title,
                "retrieval_date": requests.utils.time.strftime("%Y-%m-%dT%H:%M:%SZ", requests.utils.time.gmtime())
            }
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching web article from {url}: {e}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while processing {url}: {e}")
        return {}

if __name__ == "__main__":
    # Example usage (for testing purposes)
    sample_article_url = "https://litecoin.com/en/news/litecoin-halving-2023-everything-you-need-to-know" # Reason: A relevant Litecoin news article.
    print(f"Attempting to load data from: {sample_article_url}")
    article_data = load_web_article_data(sample_article_url)
    if article_data:
        print("Successfully loaded web article data.")
        print(f"Title: {article_data['metadata'].get('title')}")
        print(f"Content snippet: {article_data['content'][:500]}...") # Reason: Print snippet for brevity.
    else:
        print("Failed to load web article data.")
