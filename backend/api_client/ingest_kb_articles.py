import os
import requests
import subprocess
import time
import sys
from typing import Dict, Any

# Add backend to sys.path to allow direct import of utils
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.clear_litecoin_docs_collection import clear_collection

# Base URL for the FastAPI application
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BASE_URL = f"{BACKEND_BASE_URL}/api/v1"

def get_frontmatter(file_path: str) -> Dict[str, Any]:
    """
    Parses YAML frontmatter from a Markdown file.
    A simple implementation for demonstration.
    """
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines[0].strip() != '---':
                return {}
            
            frontmatter_lines = []
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                frontmatter_lines.append(line)
            
            frontmatter_str = "".join(frontmatter_lines)
            return yaml.safe_load(frontmatter_str)
    except (ImportError, yaml.YAMLError, IndexError, FileNotFoundError) as e:
        print(f"Could not parse frontmatter for {file_path}: {e}")
        return {}

def register_and_ingest_article(file_path: str):
    """
    Registers a new data source via the API and then triggers its ingestion.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}. Skipping.")
        return

    print(f"Processing file: {file_path}")
    
    # 1. Extract frontmatter to get the article title
    frontmatter = get_frontmatter(file_path)
    article_title = frontmatter.get("title", os.path.basename(file_path))

    # 2. Register the data source via the API
    source_data = {
        "name": article_title,
        "type": "markdown",
        "uri": file_path,
        "status": "pending" # Initial status
    }
    
    try:
        # Check if source already exists
        response = requests.get(f"{BASE_URL}/sources/")
        response.raise_for_status()
        existing_sources = response.json()
        
        source_exists = any(s['uri'] == file_path for s in existing_sources)

        if source_exists:
            print(f"Data source with URI '{file_path}' already exists. Skipping registration.")
        else:
            print(f"Registering new data source: {source_data['name']}")
            response = requests.post(f"{BASE_URL}/sources/", json=source_data)
            response.raise_for_status()
            created_source = response.json()
            print(f"Successfully registered data source with ID: {created_source['id']}")

        # 3. Trigger the ingestion process using the standalone script
        print(f"Triggering ingestion for: {file_path}")
        subprocess.run(
            ["python", "backend/ingest_data.py", "--source_type", "markdown", "--source_identifier", file_path],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Successfully triggered ingestion for {file_path}.")

    except requests.exceptions.RequestException as e:
        print(f"API Error for {file_path}: {e}")
        if e.response:
            print(f"Response body: {e.response.text}")
    except subprocess.CalledProcessError as e:
        print(f"Ingestion script error for {file_path}: {e.stdout}\n{e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred for {file_path}: {e}")


def main():
    """
    Scans knowledge base directories and processes each article.
    """
    # Add a delay to ensure the server is ready
    print("Waiting for server to start...")
    time.sleep(5)

    # Clear the collection before starting to ensure a fresh ingestion
    print("Clearing the 'litecoin_docs' collection before ingestion...")
    clear_collection()
    print("Collection cleared successfully.")

    source_directories = [
        "knowledge_base/articles",
        "knowledge_base/deep_research"
    ]
    
    for directory in source_directories:
        if os.path.isdir(directory):
            print(f"\nScanning directory: {directory}")
            for filename in os.listdir(directory):
                if filename.lower().endswith((".md", ".markdown")) and not filename.startswith("_"):
                    file_path = os.path.join(directory, filename)
                    register_and_ingest_article(file_path)
        else:
            print(f"Directory not found: {directory}")

if __name__ == "__main__":
    # Ensure PyYAML is installed
    try:
        import yaml
    except ImportError:
        print("PyYAML not found. Please install it: pip install PyYAML")
        exit(1)
    
    main()
