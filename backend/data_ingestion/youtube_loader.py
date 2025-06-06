import requests
import os
import time
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

CITEIO_API_BASE_URL = os.getenv("CITEIO_API_BASE_URL", "http://localhost:8001") # Reason: Default to a common local development port for Citeio.

def load_youtube_data(youtube_url: str, poll_interval: int = 5, max_polls: int = 60) -> Dict:
    """
    Loads processed YouTube data (transcript, topics) from the Citeio API.
    It first submits the URL, then polls for status until processing is complete,
    and finally fetches the processed media data.

    Args:
        youtube_url: The URL of the YouTube video.
        poll_interval: Time in seconds to wait between status checks.
        max_polls: Maximum number of times to poll for status.

    Returns:
        A dictionary containing the processed data from Citeio,
        or an empty dictionary if an error occurs or processing fails.
    """
    # Step 1: Submit YouTube URL for processing
    submit_endpoint = f"{CITEIO_API_BASE_URL}/api/submit_youtube"
    try:
        print(f"Submitting YouTube URL: {youtube_url} to Citeio...")
        response = requests.post(submit_endpoint, json={"url": youtube_url})
        response.raise_for_status()
        submit_data = response.json()
        media_id = submit_data.get("media_id")
        if not media_id:
            print(f"Error: No media_id received from Citeio submission: {submit_data}")
            return {}
        print(f"YouTube URL submitted. Media ID: {media_id}. Initial status: {submit_data.get('status')}")
    except requests.exceptions.RequestException as e:
        print(f"Error submitting YouTube URL to Citeio API: {e}")
        return {}

    # Step 2: Poll for processing status
    status_endpoint = f"{CITEIO_API_BASE_URL}/api/file/{media_id}/status"
    for i in range(max_polls):
        try:
            response = requests.get(status_endpoint)
            response.raise_for_status()
            status_data = response.json()
            current_status = status_data.get("status")
            print(f"Polling status for {media_id}: {current_status} (Attempt {i+1}/{max_polls})")

            if current_status == "COMPLETED":
                print(f"Processing for {media_id} completed.")
                break
            elif current_status in ["FAILED", "ERROR"]: # Reason: Handle explicit failure states.
                print(f"Processing for {media_id} failed with status: {current_status}. Error: {status_data.get('error')}")
                return {}
            time.sleep(poll_interval)
        except requests.exceptions.RequestException as e:
            print(f"Error polling status for {media_id}: {e}")
            return {}
    else:
        print(f"Max polling attempts reached for {media_id}. Processing did not complete in time.")
        return {}

    # Step 3: Fetch processed media data
    get_source_endpoint = f"{CITEIO_API_BASE_URL}/api/file/{media_id}"
    try:
        print(f"Fetching processed data for {media_id}...")
        response = requests.get(get_source_endpoint)
        response.raise_for_status()
        processed_data = response.json().get("serialized_media", {}) # Reason: API returns 'serialized_media' key.
        print(f"Successfully fetched processed data for {media_id}.")
        return processed_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching processed data for {media_id}: {e}")
        return {}

if __name__ == "__main__":
    # Example usage (for testing purposes)
    # IMPORTANT: Replace with a real YouTube URL for actual testing.
    # This URL will be submitted to your running Citeio instance.
    sample_youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Rick Astley - Never Gonna Give You Up
    print(f"Attempting to load data for: {sample_youtube_url}")
    data = load_youtube_data(sample_youtube_url, poll_interval=5, max_polls=12) # Poll for up to 1 minute
    if data:
        print("\nSuccessfully loaded data from Citeio API.")
        print(f"Video Title: {data.get('title', 'N/A')}")
        print(f"Transcript snippet: {data.get('transcript', '')[:200]}...")
        if data.get('topics'):
            print(f"Number of topics: {len(data['topics'])}")
            print(f"First topic: {data['topics'][0].get('title', 'N/A')}")
        else:
            print("No topics found.")
    else:
        print("\nFailed to load data from Citeio API.")
