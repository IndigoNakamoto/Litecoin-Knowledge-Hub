import os
import tempfile
import shutil
from git import Repo, GitCommandError
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict

def load_github_repo_data(repo_url: str) -> List[Dict]:
    """
    Clones a GitHub repository, processes its Markdown files, and returns their content.
    It tries to clone the 'main' branch first, and falls back to 'master' if 'main' is not found.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        A list of dictionaries, where each dictionary contains the content
        and metadata of a processed Markdown file.
    """
    temp_dir = None
    documents = []
    branches_to_try = ["main", "master"]
    
    try:
        # Reason: Create a temporary directory to clone the repository into.
        temp_dir = tempfile.mkdtemp()
        
        cloned_successfully = False
        for branch in branches_to_try:
            try:
                print(f"Attempting to clone branch '{branch}' from {repo_url} into {temp_dir}...")
                Repo.clone_from(repo_url, temp_dir, branch=branch)
                print(f"Repository cloned successfully from branch '{branch}'.")
                cloned_successfully = True
                break # Exit the loop on successful clone
            except GitCommandError as e:
                print(f"Could not clone branch '{branch}': {e}. Trying next branch...")
                # Clean up the directory for the next attempt
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                temp_dir = tempfile.mkdtemp()

        if not cloned_successfully:
            print(f"Error: Could not clone from any of the default branches: {branches_to_try}")
            return []

        # Reason: Walk through the cloned repository and load Markdown files.
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        # Reason: Use TextLoader for simple text files like Markdown.
                        loader = TextLoader(file_path)
                        docs = loader.load()
                        for doc in docs:
                            # Reason: Add source metadata for traceability.
                            doc.metadata["source"] = repo_url
                            doc.metadata["file_path"] = os.path.relpath(file_path, temp_dir)
                            documents.append({"content": doc.page_content, "metadata": doc.metadata})
                    except Exception as e:
                        print(f"Error loading file {file_path}: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Reason: Clean up the temporary directory after processing.
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
    return documents

if __name__ == "__main__":
    # Example usage (for testing purposes)
    sample_repo_url = "https://github.com/litecoin-project/litecoin.git" # Reason: Official Litecoin GitHub repo for testing.
    print(f"Attempting to load data from: {sample_repo_url}")
    repo_data = load_github_repo_data(sample_repo_url)
    if repo_data:
        print(f"Successfully loaded {len(repo_data)} Markdown documents from GitHub.")
        for i, doc in enumerate(repo_data[:2]): # Reason: Print only first 2 for brevity.
            print(f"\n--- Document {i+1} ---")
            print(f"File Path: {doc['metadata'].get('file_path')}")
            print(f"Content snippet: {doc['content'][:200]}...")
    else:
        print("Failed to load data from GitHub repository or no Markdown files found.")
