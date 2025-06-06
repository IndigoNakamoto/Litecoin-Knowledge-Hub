import requests
import json

# Define the URL of the FastAPI chat endpoint
API_URL = "http://127.0.0.1:8000/api/v1/chat"

# Define a sample query
SAMPLE_QUERY = "What is Litecoin?"

def run_test():
    """
    Sends a sample query to the RAG pipeline and prints the response.
    """
    print(f"Sending query to RAG pipeline: '{SAMPLE_QUERY}'")
    
    payload = {"query": SAMPLE_QUERY}
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        response_data = response.json()
        
        print("\n--- Answer from RAG Pipeline ---")
        print(response_data.get("answer", "N/A"))
        
        print("\n--- Sources ---")
        sources = response_data.get("sources", [])
        if sources:
            for i, source in enumerate(sources):
                print(f"\nSource {i+1}:")
                print(f"  Content: {source.get('page_content', 'N/A')[:200]}...") # Print first 200 chars
                print(f"  Metadata: {source.get('metadata', {})}")
        else:
            print("No sources provided.")
        print("\n--- End of Response ---")
        
    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to the API: {e}")
        print(f"Please ensure the FastAPI backend server is running on {API_URL.replace('/api/v1/chat', '')}")
    except json.JSONDecodeError:
        print("\nError: Could not decode JSON response from the server.")
        print(f"Raw response content: {response.text}")

if __name__ == "__main__":
    print("--- Starting RAG Pipeline Test Script ---")
    run_test()
    print("\n--- RAG Pipeline Test Script Finished ---")
