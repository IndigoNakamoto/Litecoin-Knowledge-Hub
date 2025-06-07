import os # Reason: To check if path is directory and list files
import frontmatter # Reason: To correctly parse YAML frontmatter from Markdown files
from typing import List
from langchain_core.documents import Document
# UnstructuredMarkdownLoader might not be needed if frontmatter library handles content well enough
# from langchain_community.document_loaders import UnstructuredMarkdownLoader 

def load_litecoin_docs(path_or_dir: str) -> List[Document]:
    """
    Loads Litecoin documentation from a markdown file or a directory of markdown files.

    Args:
        path_or_dir: The path to the markdown file or a directory containing .md files.

    Returns:
        A list of documents.
    """
    all_docs: List[Document] = []
    if os.path.isdir(path_or_dir):
        print(f"'{path_or_dir}' is a directory. Loading all .md files within it...")
        for filename in os.listdir(path_or_dir):
            if filename.endswith(".md") and not filename.startswith("_"): # Reason: Ignore templates like _template.md
                file_path = os.path.join(path_or_dir, filename)
                print(f"  Loading markdown file: {file_path}")
                try:
                    post = frontmatter.load(file_path)
                    doc_metadata = post.metadata
                    doc_metadata['source'] = file_path # Ensure source is always present
                    
                    # Create a Langchain Document directly
                    # The content is post.content
                    # The metadata is post.metadata (which includes frontmatter)
                    # UnstructuredMarkdownLoader might still be useful if we want its specific
                    # content cleaning/chunking for the main body, but for now, let's use raw content.
                    # If UnstructuredMarkdownLoader is used, it should be on post.content,
                    # and its output metadata should be merged with post.metadata.
                    
                    # For now, creating a single Document per file with all its content.
                    # The splitting into smaller chunks will happen in embedding_processor.py
                    all_docs.append(Document(page_content=post.content, metadata=doc_metadata))
                    
                except Exception as e:
                    print(f"    Error loading file {file_path} with frontmatter library: {e}")
    elif os.path.isfile(path_or_dir) and path_or_dir.endswith(".md"):
        print(f"Loading markdown file: {path_or_dir}")
        try:
            post = frontmatter.load(path_or_dir)
            doc_metadata = post.metadata
            doc_metadata['source'] = path_or_dir

            all_docs.append(Document(page_content=post.content, metadata=doc_metadata))
        except Exception as e:
            print(f"    Error loading file {path_or_dir} with frontmatter library: {e}")
    else:
        print(f"Error: '{path_or_dir}' is not a valid .md file or directory. No documents loaded.")

    return all_docs

if __name__ == '__main__':
    # Example usage for a single file:
    # file_path_example = "backend/data_ingestion/sample_litecoin_docs.md"
    # documents_single = load_litecoin_docs(file_path_example)
    # print(f"\nLoaded {len(documents_single)} documents from single file '{file_path_example}'.")
    # for doc in documents_single:
    #     print(doc.page_content[:100] + "...")
    #     print("-" * 20)

    # Example usage for a directory:
    # Determine the correct path to knowledge_base whether script is run from root or data_ingestion
    kb_path = "knowledge_base/"
    if not os.path.exists(kb_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(script_dir, "..", "..", "knowledge_base")
        kb_path = os.path.normpath(kb_path)


    print(f"\nAttempting to load from directory: {os.path.abspath(kb_path)}")
    if os.path.exists(kb_path):
        documents_from_dir = load_litecoin_docs(kb_path)
        print(f"\nLoaded {len(documents_from_dir)} documents from directory '{kb_path}'.")
        for i, doc in enumerate(documents_from_dir):
            print(f"\n--- Document {i+1} (Source: {doc.metadata.get('source', 'N/A')}) ---")
            print(doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content)
    else:
        print(f"Directory '{kb_path}' not found. Skipping directory loading example.")
    
    # Test with a non-existent path
    print("\nAttempting to load from non-existent path:")
    non_existent_docs = load_litecoin_docs("non_existent_path.md")
    print(f"Loaded {len(non_existent_docs)} documents from non_existent_path.md")
