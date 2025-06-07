import os
import logging
import time
import datetime
from typing import List
import yaml # Added for frontmatter parsing
import re   # Added for regex-based heading parsing

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError, InvalidArgument
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Setup Logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Reverted to INFO
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# --- Custom Text Splitter for Markdown ---
class MarkdownTextSplitter:
    """
    A text splitter that processes Markdown content hierarchically.
    It uses the parse_markdown_hierarchically function to create Document chunks
    with prepended titles and section context.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100, **kwargs):
        """
        Initializes the MarkdownTextSplitter.
        Note: chunk_size and chunk_overlap are kept for interface compatibility
        but the primary splitting logic is based on Markdown structure.
        """
        self.chunk_size = chunk_size # Not directly used by parse_markdown_hierarchically in the same way
        self.chunk_overlap = chunk_overlap # Not directly used
        # kwargs can be used to pass other parameters if needed in the future

    def split_text(self, text: str, metadata: dict = None) -> List[Document]:
        """
        Splits Markdown text into a list of Document objects.

        Args:
            text: The Markdown content to split.
            metadata: Optional initial metadata to associate with the created documents.
                      This metadata can be augmented by the parsing process.

        Returns:
            A list of Document objects, where each document is a chunk
            with prepended hierarchical context.
        """
        initial_metadata = metadata or {}
        # Ensure 'source' is in metadata if not provided, as parse_markdown_hierarchically might use it for logging
        if 'source' not in initial_metadata:
            initial_metadata['source'] = 'unknown_markdown_source'
            
        # parse_markdown_hierarchically expects initial_metadata to be a dictionary
        return parse_markdown_hierarchically(text, initial_metadata)

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Splits a list of Documents, applying hierarchical Markdown parsing to each.
        """
        all_chunks = []
        for doc in documents:
            # Pass a copy of the document's metadata to avoid modification issues
            # and to ensure each call to split_text gets the original doc's metadata.
            doc_metadata_copy = doc.metadata.copy() if doc.metadata else {}
            chunks_from_doc = self.split_text(doc.page_content, metadata=doc_metadata_copy)
            all_chunks.extend(chunks_from_doc)
        return all_chunks

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
        It's configured for document retrieval.
        """
        # Reason: Setting task_type to 'retrieval_document' for embedding knowledge base documents,
        # as recommended for text-embedding-004.
        return GoogleGenerativeAIEmbeddings(
            model=f"models/{self.model_name}",
            task_type="retrieval_document"
        )


def parse_markdown_hierarchically(content: str, initial_metadata: dict) -> List[Document]:
    """
    Parses Markdown content hierarchically, creating chunks with prepended titles.
    Handles YAML frontmatter and basic Markdown headings (#, ##, ###, ####).
    """
    chunks = []
    current_metadata = initial_metadata.copy()
    # Initialize titles from metadata if present, otherwise empty
    current_h1 = current_metadata.get("title", "") # Often set from filename or frontmatter
    current_h2 = ""
    current_h3 = ""
    current_h4 = "" # Added support for H4

    # Try to parse YAML frontmatter
    try:
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                content_after_frontmatter = parts[2].lstrip()
                parsed_frontmatter = yaml.safe_load(frontmatter_str)
                if isinstance(parsed_frontmatter, dict):
                    # Reason: Convert published_at to datetime for proper BSON type in MongoDB, enabling date-based queries.
                    if 'published_at' in parsed_frontmatter:
                        pub_date = parsed_frontmatter['published_at']
                        if isinstance(pub_date, str):
                            try:
                                # Attempt to parse ISO format string into a datetime object
                                parsed_frontmatter['published_at'] = datetime.datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Could not parse 'published_at' date string '{pub_date}' for source: {initial_metadata.get('source', 'Unknown')}. Error: {e}. Keeping as string.")
                        elif isinstance(pub_date, datetime.date) and not isinstance(pub_date, datetime.datetime):
                            # Reason: Convert datetime.date to datetime.datetime to prevent BSON encoding errors.
                            parsed_frontmatter['published_at'] = datetime.datetime.combine(pub_date, datetime.time.min)

                    current_metadata.update(parsed_frontmatter)
                    if "title" in parsed_frontmatter: # Frontmatter title overrides
                        current_h1 = parsed_frontmatter["title"]
                    content = content_after_frontmatter
                else:
                    logger.warning(f"Parsed frontmatter is not a dictionary for source: {initial_metadata.get('source', 'Unknown')}. Skipping.")
            else:
                logger.debug(f"No valid YAML frontmatter block found for source: {initial_metadata.get('source', 'Unknown')}")
    except yaml.YAMLError as e:
        logger.warning(f"Could not parse YAML frontmatter for {initial_metadata.get('source', 'Unknown')}: {e}")
    except Exception as e:
        logger.warning(f"Error processing frontmatter for {initial_metadata.get('source', 'Unknown')}: {e}")

    lines = content.splitlines()
    current_paragraph_lines = []

    def create_chunk(paragraph_lines_list, h1, h2, h3, h4, meta):
        if not paragraph_lines_list:
            return None
        
        text = "\n".join(paragraph_lines_list).strip()
        if not text:
            return None

        prepended_text_parts = []
        if h1: prepended_text_parts.append(f"Title: {h1}")
        if h2: prepended_text_parts.append(f"Section: {h2}")
        if h3: prepended_text_parts.append(f"Subsection: {h3}")
        if h4: prepended_text_parts.append(f"Sub-subsection: {h4}") # Added H4 to prefix
        
        prepended_header = "\n".join(prepended_text_parts)
        page_content = f"{prepended_header}\n\n{text}" if prepended_header else text
        
        chunk_metadata = meta.copy()
        if h1: chunk_metadata['doc_title'] = h1
        if h2: chunk_metadata['section_title'] = h2
        if h3: chunk_metadata['subsection_title'] = h3
        if h4: chunk_metadata['subsubsection_title'] = h4 # Added H4 to metadata
        
        # Final check to convert any date objects to datetime objects before creating the Document
        for key, value in chunk_metadata.items():
            if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                logger.debug(f"Converting datetime.date to datetime.datetime for key '{key}' in source: {chunk_metadata.get('source', 'Unknown')}")
                chunk_metadata[key] = datetime.datetime.combine(value, datetime.time.min)

        return Document(page_content=page_content, metadata=chunk_metadata)

    for line_number, line in enumerate(lines):
        h1_match = re.match(r"^#\s+(.*)", line)
        h2_match = re.match(r"^##\s+(.*)", line)
        h3_match = re.match(r"^###\s+(.*)", line)
        h4_match = re.match(r"^####\s+(.*)", line) # Added H4 parsing

        if h1_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h1 = h1_match.group(1).strip()
            current_h2, current_h3, current_h4 = "", "", ""
        elif h2_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h2 = h2_match.group(1).strip()
            current_h3, current_h4 = "", ""
        elif h3_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h3 = h3_match.group(1).strip()
            current_h4 = ""
        elif h4_match: # Added H4 handling
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h4 = h4_match.group(1).strip()
        elif line.strip() or (not line.strip() and current_paragraph_lines and line_number < len(lines) -1 and lines[line_number+1].strip()):
            current_paragraph_lines.append(line)
        elif current_paragraph_lines:
            chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
            if chunk: chunks.append(chunk)
            current_paragraph_lines = []

    if current_paragraph_lines: # Process any remaining lines
        chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata)
        if chunk: chunks.append(chunk)
    
    if not chunks and content.strip(): # If no headings were found but content exists
        page_content = content.strip()
        prepended_text_parts = []
        if current_h1: prepended_text_parts.append(f"Title: {current_h1}")
        prepended_header = "\n".join(prepended_text_parts)
        final_page_content = f"{prepended_header}\n\n{page_content}" if prepended_header else page_content
        
        final_metadata = current_metadata.copy()
        if current_h1: final_metadata['doc_title'] = current_h1
        chunks.append(Document(page_content=final_page_content, metadata=final_metadata))
    elif not chunks and not content.strip():
        logger.info(f"No content to chunk for source: {initial_metadata.get('source', 'Unknown')}")

    return chunks

def process_documents(docs: List[Document]) -> List[Document]:
    """
    Splits documents into smaller, hierarchically structured chunks for processing.
    Optimized for Markdown content by prepending titles/sections.
    Falls back to RecursiveCharacterTextSplitter for non-Markdown content.

    Args:
        docs: A list of documents to process.

    Returns:
        A list of split documents (chunks).
    """
    all_chunks = []
    markdown_splitter = MarkdownTextSplitter() # Use the class here

    for doc_idx, doc in enumerate(docs):
        source_identifier = doc.metadata.get('source', f'doc_index_{doc_idx}')
        
        is_markdown_like = False
        if doc.page_content:
            first_few_lines = doc.page_content.splitlines()[:20]
            if any("---" in line for line in first_few_lines[:5]):
                 is_markdown_like = True
            if not is_markdown_like and any(line.strip().startswith("#") for line in first_few_lines):
                 is_markdown_like = True
        
        if not is_markdown_like and 'source' in doc.metadata and isinstance(doc.metadata['source'], str) \
           and doc.metadata['source'].lower().endswith(('.md', '.markdown')):
            is_markdown_like = True

        if is_markdown_like:
            logger.info(f"Processing document '{source_identifier}' with MarkdownTextSplitter.")
            # The MarkdownTextSplitter's split_documents method expects a list of Documents
            # and handles metadata copying internally per document.
            hierarchical_chunks = markdown_splitter.split_documents([doc]) 
            all_chunks.extend(hierarchical_chunks)
        else:
            logger.info(f"Processing document '{source_identifier}' with RecursiveCharacterTextSplitter (not identified as Markdown).")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            split_docs_from_current = text_splitter.split_documents([doc])
            all_chunks.extend(split_docs_from_current)

    logger.info(f"Processed {len(docs)} original document(s) into {len(all_chunks)} chunks.")
    return all_chunks

# This function is kept for compatibility with how vector_store_manager expects to get the embeddings client.
def get_embedding_client():
    """
    Initializes and returns the embedding service client.
    """
    service = EmbeddingService()
    return service.get_embeddings_client()


if __name__ == '__main__':
    from dotenv import load_dotenv
    # Assuming litecoin_docs_loader is in the same directory or accessible via PYTHONPATH
    # from litecoin_docs_loader import load_litecoin_docs # This might cause issues if not structured for direct run

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example'))


    # Example usage:
    # Create a dummy markdown document for testing
    sample_md_content = """---
title: Test Document
author: Cline
---
# Main Title from Content

This is the first paragraph.

## Section One

Some text in section one.

### Subsection A

Details for subsection A.

## Section Two

Text for section two.
"""
    sample_doc = Document(page_content=sample_md_content, metadata={"source": "sample_test.md"})
    
    processed_docs = process_documents([sample_doc])
    
    print(f"Number of documents after splitting: {len(processed_docs)}")
    for i, p_doc in enumerate(processed_docs):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Content:\n{p_doc.page_content}")
        print(f"Metadata: {p_doc.metadata}")
    
    # Example of getting the client
    try:
        embeddings_client = get_embedding_client()
        print(f"\nSuccessfully initialized embeddings client for model: {embeddings_client.model}")
    except ValueError as e:
        print(f"\nError initializing embedding client: {e}")
        print("Ensure GOOGLE_API_KEY is set in your .env.example file.")
