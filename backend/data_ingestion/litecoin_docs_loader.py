import os # Reason: To check if path is directory and list files
import frontmatter # Reason: To correctly parse YAML frontmatter from Markdown files
from typing import List
from langchain_core.documents import Document
# UnstructuredMarkdownLoader might not be needed if frontmatter library handles content well enough
# from langchain_community.document_loaders import UnstructuredMarkdownLoader 

def load_litecoin_docs(path_or_dir: str) -> List[Document]:
    """
    Loads Litecoin documentation from a markdown file or a directory of markdown files.
    If a directory is provided, it will be walked recursively.
    Files in a subdirectory named 'deep_research' will only be loaded if their
    frontmatter metadata 'vetting_status' is 'vetted'.

    Args:
        path_or_dir: The path to the markdown file or a root directory to search for .md files.

    Returns:
        A list of documents.
    """
    all_docs: List[Document] = []
    if os.path.isdir(path_or_dir):
        print(f"'{path_or_dir}' is a directory. Loading all .md files within it recursively...")
        for dirpath, dirnames, filenames in os.walk(path_or_dir):
            # Skip hidden directories (e.g., .git, .vscode)
            # To prune search into hidden directories, you could modify dirnames:
            # dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            
            # Check if current dirpath itself is hidden to avoid processing its files
            path_parts = dirpath.split(os.sep)
            if any(part.startswith('.') for part in path_parts if part): # ensure part is not empty string
                # print(f"  Skipping hidden/config directory: {dirpath}") # Optional: for debugging
                continue

            current_dir_name = os.path.basename(dirpath)
            is_deep_research_subdir = current_dir_name == "deep_research"

            for filename in filenames:
                if filename.endswith(".md") and not filename.startswith("_"): # Reason: Ignore templates like _template.md
                    file_path = os.path.join(dirpath, filename)
                    # print(f"  Processing markdown file: {file_path}") # Verbose, can be enabled for debugging
                    try:
                        post = frontmatter.load(file_path)
                        doc_metadata = post.metadata
                        doc_metadata['source'] = file_path # Ensure source is always present
                        
                        if is_deep_research_subdir:
                            vetting_status = doc_metadata.get('vetting_status')
                            if vetting_status != 'vetted':
                                print(f"    INFO: Skipping '{file_path}' from 'deep_research' as its vetting_status is '{vetting_status}' (not 'vetted').")
                                continue # Skip this file

                        all_docs.append(Document(page_content=post.content, metadata=doc_metadata))
                        
                    except Exception as e:
                        print(f"    ERROR: Error loading file {file_path} with frontmatter library: {e}")
    elif os.path.isfile(path_or_dir) and path_or_dir.endswith(".md"):
        print(f"Loading single markdown file: {path_or_dir}")
        try:
            post = frontmatter.load(path_or_dir)
            doc_metadata = post.metadata
            doc_metadata['source'] = path_or_dir

            # Check vetting status if this single file is in a 'deep_research' directory
            # Get the absolute path to handle relative paths correctly
            abs_file_path = os.path.abspath(path_or_dir)
            parent_dir_name = os.path.basename(os.path.dirname(abs_file_path))

            if parent_dir_name == "deep_research":
                vetting_status = doc_metadata.get('vetting_status')
                if vetting_status != 'vetted':
                    print(f"    INFO: Skipping '{path_or_dir}' from 'deep_research' as its vetting_status is '{vetting_status}' (not 'vetted').")
                    return [] # Return empty list for this single skipped file
            
            all_docs.append(Document(page_content=post.content, metadata=doc_metadata))
        except Exception as e:
            print(f"    ERROR: Error loading file {path_or_dir} with frontmatter library: {e}")
    else:
        print(f"Error: '{path_or_dir}' is not a valid .md file or directory. No documents loaded.")

    return all_docs

if __name__ == '__main__':
    # Determine the correct path to knowledge_base whether script is run from root or data_ingestion
    # This allows the script to be run from the project root or from backend/data_ingestion
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(current_script_path, "..", ".."))
    # Path for loading main articles for testing purposes
    kb_articles_path_from_root = os.path.join(project_root, "knowledge_base", "articles")
    # Path for creating dummy deep_research files, relative to knowledge_base
    kb_root_path_for_deep_research_test = os.path.join(project_root, "knowledge_base")


    print(f"Project root determined as: {project_root}")
    print(f"Knowledge base articles path for testing determined as: {kb_articles_path_from_root}")

    # Create dummy files for testing the vetting_status logic
    deep_research_path = os.path.join(kb_root_path_for_deep_research_test, "deep_research")
    if not os.path.exists(deep_research_path):
        os.makedirs(deep_research_path)

    vetted_file_content = """---
title: Vetted Deep Research Article
tags: ["test", "vetted"]
last_updated: "2025-01-01"
source_type: deepsearch_generated
original_deepsearch_query: "test query for vetted"
vetting_status: vetted
vetter_name: "TestVetter"
vetting_date: "2025-01-01"
---
This is a vetted article from deep_research.
"""
    draft_file_content = """---
title: Draft Deep Research Article
tags: ["test", "draft"]
last_updated: "2025-01-01"
source_type: deepsearch_generated
original_deepsearch_query: "test query for draft"
vetting_status: draft
---
This is a draft article from deep_research and should be skipped.
"""
    vetted_file_path = os.path.join(deep_research_path, "_test_vetted_article.md")
    draft_file_path = os.path.join(deep_research_path, "_test_draft_article.md")

    with open(vetted_file_path, "w") as f:
        f.write(vetted_file_content)
    with open(draft_file_path, "w") as f:
        f.write(draft_file_content)

    print(f"\nAttempting to load articles from directory: {os.path.abspath(kb_articles_path_from_root)}")
    if os.path.exists(kb_articles_path_from_root):
        documents_from_dir = load_litecoin_docs(kb_articles_path_from_root)
        print(f"\n--- Summary of Loaded Articles ({len(documents_from_dir)} total) ---")
        for i, doc in enumerate(documents_from_dir):
            print(f"  Doc {i+1}: Source: {doc.metadata.get('source', 'N/A')}, Title: {doc.metadata.get('title', 'N/A')}, Vetting: {doc.metadata.get('vetting_status', 'N/A')}")
            # print(f"    Content: {doc.page_content[:80] + '...' if len(doc.page_content) > 80 else doc.page_content}")
        
        # Test loading a single vetted file from deep_research
        print(f"\nAttempting to load single vetted file: {vetted_file_path}")
        single_vetted_doc = load_litecoin_docs(vetted_file_path)
        print(f"  Loaded {len(single_vetted_doc)} doc(s). Title: {single_vetted_doc[0].metadata.get('title') if single_vetted_doc else 'N/A'}")

        # Test loading a single draft file from deep_research (should be skipped)
        print(f"\nAttempting to load single draft file: {draft_file_path}")
        single_draft_doc = load_litecoin_docs(draft_file_path)
        print(f"  Loaded {len(single_draft_doc)} doc(s). Should be 0.")

    else:
        print(f"Articles directory '{kb_articles_path_from_root}' not found. Skipping articles loading example.")
    
    # Clean up dummy files
    if os.path.exists(vetted_file_path):
        os.remove(vetted_file_path)
    if os.path.exists(draft_file_path):
        os.remove(draft_file_path)
    # Potentially remove deep_research_path if it was created and is empty, but be careful
    # For now, let's leave it if it was created by user.

    # Test with a non-existent path
    print("\nAttempting to load from non-existent path:")
    non_existent_docs = load_litecoin_docs("non_existent_path.md")
    print(f"Loaded {len(non_existent_docs)} documents from non_existent_path.md")
