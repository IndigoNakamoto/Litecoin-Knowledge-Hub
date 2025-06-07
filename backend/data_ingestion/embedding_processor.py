import os
import logging
import time
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
    Handles YAML frontmatter and basic Markdown headings (#, ##, ###).
    """
    chunks = []
    # Reason: Use a copy of metadata to avoid modification issues across chunks.
    current_metadata = initial_metadata.copy()
    current_h1 = current_metadata.get("title", "")
    current_h2 = ""
    current_h3 = ""

    # Try to parse YAML frontmatter
    try:
        if content.startswith("---"):
            # Reason: Correctly split frontmatter from main content.
            parts = content.split("---", 2) # maxsplit=2 to get ---frontmatter---content
            if len(parts) >= 3: # Ensure we have frontmatter and content parts
                frontmatter_str = parts[1]
                content_after_frontmatter = parts[2].lstrip()
                parsed_frontmatter = yaml.safe_load(frontmatter_str)
                if isinstance(parsed_frontmatter, dict):
                    current_metadata.update(parsed_frontmatter)
                    # Reason: Prioritize title from frontmatter if available.
                    if "title" in parsed_frontmatter and (not current_h1 or current_h1 == initial_metadata.get("source")): # if current_h1 was just filename
                        current_h1 = parsed_frontmatter["title"]
                    content = content_after_frontmatter
                else:
                    logger.warning(f"Parsed frontmatter is not a dictionary for source: {initial_metadata.get('source', 'Unknown')}. Skipping frontmatter.")
            else: # Only one "---" or content starts with "---" but no second "---"
                logger.debug(f"No valid YAML frontmatter block found for source: {initial_metadata.get('source', 'Unknown')}")

    except yaml.YAMLError as e:
        logger.warning(f"Could not parse YAML frontmatter for {initial_metadata.get('source', 'Unknown')}: {e}")
    except Exception as e: # pylint: disable=broad-except
        logger.warning(f"Error processing frontmatter for {initial_metadata.get('source', 'Unknown')}: {e}")

    lines = content.splitlines()
    current_paragraph_lines = []

    def create_chunk(paragraph_lines_list, h1, h2, h3, meta):
        if not paragraph_lines_list:
            return None
        
        text = "\n".join(paragraph_lines_list).strip()
        if not text:
            return None

        prepended_text_parts = []
        # Reason: Prepend hierarchical context (Title, Section, Subsection) to the chunk.
        if h1: prepended_text_parts.append(f"Title: {h1}")
        if h2: prepended_text_parts.append(f"Section: {h2}")
        if h3: prepended_text_parts.append(f"Subsection: {h3}")
        
        prepended_header = "\n".join(prepended_text_parts)
        
        page_content = f"{prepended_header}\n\n{text}" if prepended_header else text
        
        chunk_metadata = meta.copy()
        if h1: chunk_metadata['doc_title'] = h1 # Use 'doc_title' to avoid conflict if 'title' is in frontmatter for a specific chunk
        if h2: chunk_metadata['section_title'] = h2
        if h3: chunk_metadata['subsection_title'] = h3
        
        return Document(page_content=page_content, metadata=chunk_metadata)

    for line_number, line in enumerate(lines):
        h1_match = re.match(r"^#\s+(.*)", line)
        h2_match = re.match(r"^##\s+(.*)", line)
        h3_match = re.match(r"^###\s+(.*)", line)

        # Reason: Process headings to establish hierarchical context for subsequent text.
        if h1_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h1 = h1_match.group(1).strip()
            current_h2 = "" 
            current_h3 = ""
        elif h2_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h2 = h2_match.group(1).strip()
            current_h3 = ""
        elif h3_match:
            if current_paragraph_lines:
                chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_metadata)
                if chunk: chunks.append(chunk)
                current_paragraph_lines = []
            current_h3 = h3_match.group(1).strip()
        elif line.strip() or (not line.strip() and current_paragraph_lines and line_number < len(lines) -1 and lines[line_number+1].strip()):
            # Accumulate non-empty lines. Also accumulate empty lines if they are between non-empty lines (preserve paragraph structure).
            current_paragraph_lines.append(line)
        elif current_paragraph_lines: # End of a paragraph block (multiple empty lines or end of content)
            chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_metadata)
            if chunk: chunks.append(chunk)
            current_paragraph_lines = []

    if current_paragraph_lines:
        chunk = create_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_metadata)
        if chunk: chunks.append(chunk)
    
    if not chunks and content.strip():
        # Reason: Ensure at least one chunk is created if content exists but no Markdown structure was parsed.
        page_content = content.strip()
        prepended_text_parts = []
        if current_h1: prepended_text_parts.append(f"Title: {current_h1}") # From metadata or parsed H1
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
    for doc_idx, doc in enumerate(docs):
        source_identifier = doc.metadata.get('source', f'doc_index_{doc_idx}')
        
        # Reason: Heuristic to determine if content is Markdown.
        # This allows applying specialized Markdown parsing or falling back to generic splitting.
        # Checking for '---' (frontmatter) or '#' (headings) in the first few lines.
        is_markdown_like = False
        if doc.page_content:
            first_few_lines = doc.page_content.splitlines()[:20]
            if any("---" in line for line in first_few_lines[:5]): # Check for frontmatter early
                 is_markdown_like = True
            if not is_markdown_like and any(line.strip().startswith("#") for line in first_few_lines):
                 is_markdown_like = True
        
        # Also consider file extension if available in metadata
        if not is_markdown_like and 'source' in doc.metadata and isinstance(doc.metadata['source'], str) \
           and doc.metadata['source'].lower().endswith(('.md', '.markdown')):
            is_markdown_like = True

        if is_markdown_like:
            logger.info(f"Processing document '{source_identifier}' with hierarchical Markdown chunker.")
            # Reason: Pass a copy of metadata to avoid cross-contamination between documents if parse_markdown_hierarchically modifies it.
            hierarchical_chunks = parse_markdown_hierarchically(doc.page_content, doc.metadata.copy())
            all_chunks.extend(hierarchical_chunks)
        else:
            logger.info(f"Processing document '{source_identifier}' with RecursiveCharacterTextSplitter (not identified as Markdown).")
            # Reason: Using RecursiveCharacterTextSplitter as a fallback for non-Markdown documents
            # to ensure they are still chunked for effective retrieval.
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            # Reason: Split one document at a time to maintain metadata association.
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
