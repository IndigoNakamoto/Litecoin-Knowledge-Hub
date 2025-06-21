import logging
from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class PayloadEmbeddingProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def process(self, payload_data: Dict[str, Any]) -> List[Document]:
        """
        Processes the rich text data from Payload CMS and returns a list of Document objects.
        """
        documents = []
        try:
            logger.info(f"Processing payload data for document ID: {payload_data.get('id')}")
            # Extract the content from the payload data
            content = payload_data.get("content", {})
            
            if not content:
                logger.warning(f"Document ID {payload_data.get('id')} has no 'content' field. Skipping.")
                return documents

            text = self._extract_text_from_richtext(content)
            logger.debug(f"Extracted text from rich text field: {text[:500]}...") # Log first 500 chars

            if not text.strip():
                logger.warning(f"Extracted text for document ID {payload_data.get('id')} is empty. Skipping.")
                return documents

            chunks = self.text_splitter.split_text(text)
            logger.info(f"Split text into {len(chunks)} chunks.")

            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": "payload",
                    "id": payload_data.get("id"),
                    "title": payload_data.get("title"),
                    "chunk_number": i + 1,
                    "total_chunks": len(chunks),
                }
                documents.append(Document(page_content=chunk, metadata=metadata))
            
            logger.info(f"Successfully created {len(documents)} Document objects.")

        except Exception as e:
            logger.error(f"Error processing payload data for ID {payload_data.get('id')}: {e}", exc_info=True)
        
        return documents

    def _extract_text_from_richtext(self, content: Dict[str, Any]) -> str:
        """
        Extracts the text from Payload's rich text JSON format.
        """
        text = []
        if "root" in content and "children" in content["root"]:
            for node in content["root"]["children"]:
                self._traverse_node(node, text)
        return "".join(text)

    def _traverse_node(self, node: Dict[str, Any], text: List[str]):
        """
        Recursively traverses the rich text JSON and extracts text.
        """
        if "type" in node and node["type"] == "text":
            text.append(node.get("text", ""))
        if "children" in node:
            for child in node["children"]:
                self._traverse_node(child, text)
        if node.get("type") in ["heading", "paragraph", "list"]:
            text.append("\n")
