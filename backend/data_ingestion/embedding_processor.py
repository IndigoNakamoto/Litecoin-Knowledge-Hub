import os
import logging
import time
import datetime
from typing import List
import yaml # Added for frontmatter parsing
import re   # Added for regex-based heading parsing

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from data_models import PayloadWebhookDoc, PayloadArticleMetadata

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
    with prepended titles and section context, and then further splits these
    into smaller chunks using RecursiveCharacterTextSplitter.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100, **kwargs):
        """
        Initializes the MarkdownTextSplitter.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            **kwargs
        )

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
        if 'source' not in initial_metadata:
            initial_metadata['source'] = 'unknown_markdown_source'
            
        # First, parse hierarchically to get logical sections
        hierarchical_sections = parse_markdown_hierarchically(text, initial_metadata, self.recursive_splitter)
        
        # The parse_markdown_hierarchically function now returns already split documents
        return hierarchical_sections

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Splits a list of Documents, applying hierarchical Markdown parsing to each.
        """
        all_chunks = []
        for doc in documents:
            doc_metadata_copy = doc.metadata.copy() if doc.metadata else {}
            chunks_from_doc = self.split_text(doc.page_content, metadata=doc_metadata_copy)
            all_chunks.extend(chunks_from_doc)
        return all_chunks

# --- Configuration Constants ---
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_KWARGS = {"device": "cpu"}
ENCODE_KWARGS = {"normalize_embeddings": True}

# --- Custom Exception ---
class PayloadTooLargeError(Exception):
    """Custom exception for payload size errors."""
    pass

# --- Embedding Service ---
class EmbeddingService:
    """
    Handles generating embeddings using local sentence-transformers models.
    This eliminates API calls and avoids 504 errors.
    """
    def __init__(self, model_name=None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        logger.info(f"EmbeddingService initialized with local model: {self.model_name}")

    def get_embeddings_client(self):
        """
        Returns an instance of the Langchain HuggingFaceEmbeddings client.
        This is used for integration with Langchain's vector store functions.
        Uses local sentence-transformers model for document embeddings.
        """
        try:
            return HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs=EMBEDDING_MODEL_KWARGS,
                encode_kwargs=ENCODE_KWARGS
            )
        except Exception as e:
            logger.error(f"Failed to initialize local embedding model: {e}")
            raise


def parse_markdown_hierarchically(content: str, initial_metadata: dict, recursive_splitter: RecursiveCharacterTextSplitter) -> List[Document]:
    """
    Parses Markdown content hierarchically, creating chunks with prepended titles.
    Handles YAML frontmatter for legacy files and extracts metadata from Payload documents.
    Uses a recursive_splitter to further break down large paragraphs into smaller chunks.
    """
    chunks = []
    current_metadata = initial_metadata.copy()
    is_payload_doc = current_metadata.get('source') == 'payload'

    current_h1 = current_metadata.get("doc_title", "")
    current_h2 = ""
    current_h3 = ""
    current_h4 = ""

    if not is_payload_doc:
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_str = parts[1]
                    content_after_frontmatter = parts[2].lstrip()
                    parsed_frontmatter = yaml.safe_load(frontmatter_str)
                    if isinstance(parsed_frontmatter, dict):
                        if 'last_updated' in parsed_frontmatter:
                            last_updated_date = parsed_frontmatter['last_updated']
                            if isinstance(last_updated_date, str):
                                try:
                                    parsed_frontmatter['last_updated'] = datetime.datetime.fromisoformat(last_updated_date.replace('Z', '+00:00'))
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Could not parse 'last_updated' date string '{last_updated_date}' for source: {initial_metadata.get('source', 'Unknown')}. Error: {e}. Keeping as string.")
                            elif isinstance(last_updated_date, datetime.date) and not isinstance(last_updated_date, datetime.datetime):
                                parsed_frontmatter['last_updated'] = datetime.datetime.combine(last_updated_date, datetime.time.min)

                        current_metadata.update(parsed_frontmatter)
                        if "title" in parsed_frontmatter:
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

    def create_and_split_chunk(paragraph_lines_list, h1, h2, h3, h4, meta, splitter):
        if not paragraph_lines_list:
            return []
        
        text = "\n".join(paragraph_lines_list).strip()
        if not text:
            return []

        prepended_text_parts = []
        if h1: prepended_text_parts.append(f"Title: {h1}")
        if h2: prepended_text_parts.append(f"Section: {h2}")
        if h3: prepended_text_parts.append(f"Subsection: {h3}")
        if h4: prepended_text_parts.append(f"Sub-subsection: {h4}")
        
        prepended_header = "\n".join(prepended_text_parts)
        
        # Create a temporary document for the current section/paragraph
        temp_doc_content = text
        temp_doc_metadata = meta.copy()
        if h1: temp_doc_metadata['doc_title_hierarchical'] = h1
        if h2: temp_doc_metadata['section_title'] = h2
        if h3: temp_doc_metadata['subsection_title'] = h3
        if h4: temp_doc_metadata['subsubsection_title'] = h4
        temp_doc_metadata['chunk_type'] = 'section' if h2 or h3 or h4 else 'text'

        # Use the recursive splitter to break down the section/paragraph into smaller chunks
        split_docs = splitter.create_documents([temp_doc_content], metadatas=[temp_doc_metadata])
        
        final_chunks = []
        for i, split_doc in enumerate(split_docs):
            # Prepend hierarchical header to each split chunk
            final_page_content = f"{prepended_header}\n\n{split_doc.page_content}" if prepended_header else split_doc.page_content
            
            chunk_metadata = split_doc.metadata.copy()
            chunk_metadata['content_length'] = len(split_doc.page_content)
            chunk_metadata['sub_chunk_index'] = i # Index for sub-chunks within a hierarchical section

            for key, value in chunk_metadata.items():
                if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                    logger.debug(f"Converting datetime.date to datetime.datetime for key '{key}' in source: {chunk_metadata.get('source', 'Unknown')}")
                    chunk_metadata[key] = datetime.datetime.combine(value, datetime.time.min)
            
            final_chunks.append(Document(page_content=final_page_content, metadata=chunk_metadata))
        
        return final_chunks

    for line_number, line in enumerate(lines):
        h1_match = re.match(r"^#\s+(.*)", line)
        h2_match = re.match(r"^##\s+(.*)", line)
        h3_match = re.match(r"^###\s+(.*)", line)
        h4_match = re.match(r"^####\s+(.*)", line)

        if h1_match and not is_payload_doc:
            if current_paragraph_lines:
                chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
                current_paragraph_lines = []
            current_h1 = h1_match.group(1).strip()
            current_h2, current_h3, current_h4 = "", "", ""
        elif h1_match and is_payload_doc:
            if current_paragraph_lines:
                chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
                current_paragraph_lines = []
            current_h2 = h1_match.group(1).strip()
            current_h3, current_h4 = "", ""
        elif h2_match:
            if current_paragraph_lines:
                chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
                current_paragraph_lines = []
            current_h2 = h2_match.group(1).strip()
            current_h3, current_h4 = "", ""
        elif h3_match:
            if current_paragraph_lines:
                chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
                current_paragraph_lines = []
            current_h3 = h3_match.group(1).strip()
            current_h4 = ""
        elif h4_match:
            if current_paragraph_lines:
                chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
                current_paragraph_lines = []
            current_h4 = h4_match.group(1).strip()
        elif line.strip() or (not line.strip() and current_paragraph_lines and line_number < len(lines) -1 and lines[line_number+1].strip()):
            current_paragraph_lines.append(line)
        elif current_paragraph_lines:
            chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
            current_paragraph_lines = []

    if current_paragraph_lines:
        chunks.extend(create_and_split_chunk(current_paragraph_lines, current_h1, current_h2, current_h3, current_h4, current_metadata, recursive_splitter))
    
    if not chunks and content.strip():
        page_content = content.strip()
        prepended_text_parts = []
        if current_h1: prepended_text_parts.append(f"Title: {current_h1}")
        prepended_header = "\n".join(prepended_text_parts)
        final_page_content = f"{prepended_header}\n\n{page_content}" if prepended_header else page_content
        
        final_metadata = current_metadata.copy()
        if current_h1: final_metadata['doc_title_hierarchical'] = current_h1
        final_metadata['content_length'] = len(page_content)
        final_metadata['chunk_type'] = 'title_summary'
        
        # Use recursive splitter for the single chunk if no headings were found
        single_chunk_docs = recursive_splitter.create_documents([final_page_content], metadatas=[final_metadata])
        chunks.extend(single_chunk_docs)

    elif not chunks and not content.strip():
        logger.info(f"No content to chunk for source: {initial_metadata.get('source', 'Unknown')}")

    for i, chunk in enumerate(chunks):
        chunk.metadata['chunk_index'] = i
        chunk.metadata['is_title_chunk'] = (i == 0 and chunk.metadata.get('chunk_type') == 'title_summary')

    return chunks

def process_payload_documents(payload_docs: List[PayloadWebhookDoc]) -> List[Document]:
    """
    Processes a list of documents from Payload, converting them into Langchain Documents
    and then splitting them hierarchically.
    """
    all_chunks = []
    markdown_splitter = MarkdownTextSplitter()

    for payload_doc in payload_docs:
        published_date_dt = None
        if payload_doc.publishedDate:
            try:
                published_date_dt = datetime.datetime.fromisoformat(payload_doc.publishedDate.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse 'publishedDate' string '{payload_doc.publishedDate}' for Payload doc ID {payload_doc.id}. Skipping date.")

        initial_metadata = {
            "payload_id": payload_doc.id,
            "source": "payload",
            "content_type": "article",
            "doc_title": payload_doc.title,
            "author": payload_doc.author,
            "categories": payload_doc.category or [],
            "status": payload_doc.status,
            "published_date": published_date_dt,
            "slug": payload_doc.slug,
            "locale": "en"
        }
        
        langchain_doc = Document(
            page_content=payload_doc.markdown,
            metadata=initial_metadata
        )
        
        hierarchical_chunks = markdown_splitter.split_documents([langchain_doc])
        all_chunks.extend(hierarchical_chunks)
        
    logger.info(f"Processed {len(payload_docs)} Payload document(s) into {len(all_chunks)} chunks.")
    return all_chunks


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
    markdown_splitter = MarkdownTextSplitter()

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
    Initializes and returns the local embedding service client.
    """
    service = EmbeddingService()
    return service.get_embeddings_client()


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example'))


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
    
    try:
        embeddings_client = get_embedding_client()
        print(f"\nSuccessfully initialized embeddings client for model: {embeddings_client.model}")
    except ValueError as e:
        print(f"\nError initializing embedding client: {e}")
        print("Ensure GOOGLE_API_KEY is set in your .env.example file.")
