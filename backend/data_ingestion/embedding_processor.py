import os
import logging
import time
from typing import List

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError, InvalidArgument
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Setup Logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# --- Configuration Constants ---
DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
MAX_RETRIES = 5
BACKOFF_FACTOR = 2

# --- Custom Exception ---
class PayloadTooLargeError(Exception):
    """Custom exception for payload size errors."""
    pass

# --- Embedding Service ---
class EmbeddingService:
    """
    Handles generating embeddings using Google's Generative AI with robust error handling.
    """
    def __init__(self, api_key=None, model_name=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        logger.info(f"EmbeddingService initialized with model: {self.model_name}")

    def get_embeddings_client(self):
        """
        Returns an instance of the Langchain GoogleGenerativeAIEmbeddings client.
        This is used for integration with Langchain's vector store functions.
        """
        return GoogleGenerativeAIEmbeddings(model=f"models/{self.model_name}")


def process_documents(docs: List[Document]) -> List[Document]:
    """
    Splits documents into smaller chunks for processing.

    Args:
        docs: A list of documents to process.

    Returns:
        A list of split documents.
    """
    # Reason: Using RecursiveCharacterTextSplitter to break down documents
    # into smaller, semantically coherent chunks for effective retrieval.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(docs)
    logger.info(f"Split {len(docs)} document(s) into {len(split_docs)} chunks.")
    return split_docs

# This function is kept for compatibility with how vector_store_manager expects to get the embeddings client.
def get_embedding_client():
    """
    Initializes and returns the embedding service client.
    """
    service = EmbeddingService()
    return service.get_embeddings_client()


if __name__ == '__main__':
    from dotenv import load_dotenv
    from litecoin_docs_loader import load_litecoin_docs

    load_dotenv()

    # Example usage:
    file_path = "sample_litecoin_docs.md"
    documents = load_litecoin_docs(file_path)
    processed_docs = process_documents(documents)
    
    print(f"Number of documents after splitting: {len(processed_docs)}")
    
    # Example of getting the client
    embeddings_client = get_embedding_client()
    print(f"Successfully initialized embeddings client for model: {embeddings_client.model}")
