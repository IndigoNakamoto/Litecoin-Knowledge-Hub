import os
from typing import List
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

def process_and_embed_documents(docs: List[Document]) -> List[Document]:
    """
    Splits documents into chunks and generates embeddings.

    Args:
        docs: A list of documents to process.

    Returns:
        A list of documents with embeddings.
    """
    # Reason: Using RecursiveCharacterTextSplitter to break down documents
    # into smaller, semantically coherent chunks. This is important for
    # effective retrieval in a RAG system.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(docs)

    # Reason: Initializing the Google Generative AI Embeddings model.
    # This model will convert our text chunks into vector representations.
    # It requires the GOOGLE_API_KEY to be set in the environment.
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-004")

    # Note: The embedding process is handled by the vector store integration later.
    # This function now primarily focuses on splitting the text.
    # The actual embedding generation will happen when we add to the vector store.
    
    return split_docs

if __name__ == '__main__':
    from dotenv import load_dotenv
    from litecoin_docs_loader import load_litecoin_docs

    load_dotenv()

    # Example usage:
    file_path = "backend/data_ingestion/sample_litecoin_docs.md"
    documents = load_litecoin_docs(file_path)
    processed_docs = process_and_embed_documents(documents)
    
    print(f"Number of documents after splitting: {len(processed_docs)}")
    for doc in processed_docs:
        print(doc.page_content)
        print("-" * 20)
