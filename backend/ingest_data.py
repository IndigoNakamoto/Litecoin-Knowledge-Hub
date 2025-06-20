import os
import argparse
import asyncio
from dotenv import load_dotenv
from data_ingestion.litecoin_docs_loader import load_litecoin_docs
from data_ingestion.youtube_loader import load_youtube_data
from data_ingestion.twitter_loader import load_twitter_posts
from data_ingestion.github_loader import load_github_repo_data
from data_ingestion.web_article_loader import load_web_article_data
from data_ingestion.embedding_processor import process_documents
from data_ingestion.vector_store_manager import VectorStoreManager
from langchain_core.documents import Document
from strapi.client import StrapiClient
from data_ingestion.embedding_processor_strapi import StrapiEmbeddingProcessor

async def main(source_type: str, source_identifier: str):
    """
    Main function to run the data ingestion pipeline, acting as a source router.

    Args:
        source_type: The type of the data source (e.g., "markdown", "youtube", "twitter", "github", "web", "strapi").
        source_identifier: The identifier for the source (e.g., file path, URL, collection name).
    """
    load_dotenv()

    collection_name = "litecoin_docs" # Reason: Default collection name for all ingested data.
    db_name = "litecoin_rag_db"

    print(f"Starting data ingestion pipeline for source type: {source_type}, identifier: {source_identifier}...")

    documents = []
    if source_type == "markdown":
        print(f"Loading documents from markdown file: {source_identifier}...")
        documents = load_litecoin_docs(source_identifier)
    elif source_type == "youtube":
        print(f"Loading data from YouTube URL via Citeio: {source_identifier}...")
        youtube_data = load_youtube_data(source_identifier)
        if youtube_data:
            # Reason: Convert Citeio's output into a Langchain Document format.
            content = youtube_data.get("transcript", "")
            # Reason: Combine topics into content for better retrieval if available.
            if youtube_data.get("topics"):
                content += "\n\nTopics:\n" + "\n".join([f"- {t['title']}: {t['summary']}" for t in youtube_data['topics']])
            documents.append(Document(page_content=content, metadata={"source": source_identifier, "type": "youtube", "title": youtube_data.get("title", "YouTube Video")}))
    elif source_type == "twitter":
        print(f"Loading posts from Twitter handle(s): {source_identifier}...")
        # Reason: Assuming source_identifier can be a comma-separated string of handles.
        handles = [h.strip() for h in source_identifier.split(',')]
        twitter_posts = load_twitter_posts(handles=handles)
        for post in twitter_posts:
            documents.append(Document(page_content=post["text"], metadata={"source": post["source_handle"], "type": "twitter", "id": post["id"], "created_at": post["created_at"]}))
    elif source_type == "github":
        print(f"Loading data from GitHub repository: {source_identifier}...")
        github_docs = load_github_repo_data(source_identifier)
        for doc_data in github_docs:
            documents.append(Document(page_content=doc_data["content"], metadata=doc_data["metadata"]))
    elif source_type == "web":
        print(f"Loading data from web article: {source_identifier}...")
        article_data = load_web_article_data(source_identifier)
        if article_data:
            documents.append(Document(page_content=article_data["content"], metadata=article_data["metadata"]))
    elif source_type == "strapi":
        print(f"Loading data from Strapi collection: {source_identifier}...")
        strapi_client = StrapiClient()
        strapi_processor = StrapiEmbeddingProcessor()
        entries = await strapi_client.get_entries(source_identifier, params={"populate": "*"})
        for entry in entries:
            content, metadata = strapi_processor.process_entry(entry)
            documents.append(Document(page_content=content, metadata=metadata))
    else:
        print(f"Error: Unknown source type '{source_type}'. Supported types: markdown, youtube, twitter, github, web, strapi.")
        return

    if not documents:
        print("No documents loaded. Exiting ingestion pipeline.")
        return

    print(f"Loaded {len(documents)} document(s).")

    print("Splitting documents into smaller chunks...")
    processed_docs = process_documents(documents)
    print(f"Split documents into {len(processed_docs)} chunks.")

    print(f"Initializing VectorStoreManager for db: '{db_name}', collection: '{collection_name}'...")
    vector_store_manager = VectorStoreManager(db_name=db_name, collection_name=collection_name)

    print(f"Inserting documents into MongoDB collection '{collection_name}' in db '{db_name}'...")
    vector_store_manager.add_documents(processed_docs) # Corrected usage
    print("Data ingestion pipeline completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest data from various sources into MongoDB Atlas Vector Store.")
    parser.add_argument("--source_type", required=True, help="Type of the data source (e.g., markdown, youtube, twitter, github, web, strapi).")
    parser.add_argument("--source_identifier", required=True, help="Identifier for the source (e.g., file path, URL, collection name).")
    args = parser.parse_args()
    asyncio.run(main(args.source_type, args.source_identifier))
