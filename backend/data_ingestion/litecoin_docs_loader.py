from langchain_community.document_loaders import UnstructuredMarkdownLoader
from typing import List
from langchain_core.documents import Document

def load_litecoin_docs(file_path: str) -> List[Document]:
    """
    Loads Litecoin documentation from a markdown file.

    Args:
        file_path: The path to the markdown file.

    Returns:
        A list of documents.
    """
    # Reason: Using UnstructuredMarkdownLoader to parse the markdown file.
    # This loader is suitable for our sample documentation.
    loader = UnstructuredMarkdownLoader(file_path)
    docs = loader.load()
    return docs

if __name__ == '__main__':
    # Example usage:
    file_path = "backend/data_ingestion/sample_litecoin_docs.md"
    documents = load_litecoin_docs(file_path)
    for doc in documents:
        print(doc.page_content)
        print("-" * 20)
