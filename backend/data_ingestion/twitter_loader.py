import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

# Reason: Twitter API credentials from environment variables
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Reason: List of trusted Litecoin-related Twitter handles
TRUSTED_TWITTER_HANDLES = [
    "litecoin",
    "SatoshiLite", # Charlie Lee, creator of Litecoin
    "LTCFoundation", # Litecoin Foundation
    # Add more trusted handles as needed
]

def load_twitter_posts(handles: list = None, count: int = 10) -> list:
    """
    Fetches recent tweets from specified Twitter handles.

    Args:
        handles: A list of Twitter handles to fetch posts from. Defaults to TRUSTED_TWITTER_HANDLES.
        count: The number of recent tweets to fetch per handle.

    Returns:
        A list of dictionaries, where each dictionary represents a tweet
        with relevant information (e.g., text, author, timestamp).
    """
    if not TWITTER_BEARER_TOKEN:
        print("Error: TWITTER_BEARER_TOKEN not found in environment variables.")
        return []

    client = tweepy.Client(TWITTER_BEARER_TOKEN)
    all_tweets = []
    handles_to_fetch = handles if handles is not None else TRUSTED_TWITTER_HANDLES

    for handle in handles_to_fetch:
        try:
            # Get user ID from handle
            user_response = client.get_user(username=handle)
            if not user_response.data:
                print(f"Warning: User '{handle}' not found.")
                continue
            user_id = user_response.data.id

            # Fetch recent tweets
            # Reason: Using exclude_replies and exclude_retweets to get original content.
            tweets_response = client.get_users_tweets(
                id=user_id,
                tweet_fields=["created_at", "text", "author_id"],
                max_results=count,
                exclude=["replies", "retweets"]
            )

            if tweets_response.data:
                for tweet in tweets_response.data:
                    all_tweets.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "author_id": tweet.author_id,
                        "created_at": tweet.created_at.isoformat(),
                        "source_handle": handle # Reason: Add source handle for traceability.
                    })
        except tweepy.TweepyException as e:
            print(f"Error fetching tweets for {handle}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {handle}: {e}")

    return all_tweets

if __name__ == "__main__":
    # Example usage (for testing purposes)
    print("Attempting to load Twitter posts...")
    posts = load_twitter_posts(count=5) # Fetch 5 recent posts from each trusted handle
    if posts:
        print(f"Successfully loaded {len(posts)} Twitter posts.")
        for i, post in enumerate(posts):
            print(f"\n--- Post {i+1} ---")
            print(f"Handle: {post.get('source_handle')}")
            print(f"Text: {post.get('text')[:150]}...") # Reason: Print snippet to avoid overwhelming console.
            print(f"Created At: {post.get('created_at')}")
    else:
        print("Failed to load Twitter posts or no posts found.")
