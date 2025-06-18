# backend.data_ingestion.embedding_processor_strapi.py
import json
from typing import List, Dict, Any
from datetime import datetime
from langchain_core.documents import Document
from backend.strapi.rich_text_chunker import StrapiRichTextChunker
from backend.data_models import StrapiDocumentMetadata

class EmbeddingProcessorStrapi:
    """
    Processes a single Strapi article entry, chunks it using the StrapiRichTextChunker,
    and prepares it for embedding.
    """
    def __init__(self):
        self.chunker = StrapiRichTextChunker()

    def process_entry(self, entry: Dict[str, Any]) -> List[Document]:
        """
        Processes a single Strapi entry to extract its content, chunk it,
        and return a list of Documents.

        Args:
            entry (Dict[str, Any]): A dictionary representing a single Strapi entry.

        Returns:
            List[Document]: A list of Document objects, each representing a chunk
                            with its corresponding metadata.
        """
        # The StrapiRichTextChunker is designed to take the whole entry
        # and produce all necessary chunks and their initial metadata.
        documents = self.chunker.chunk_document(entry)

        # We can now iterate through the documents to add/enrich metadata
        # that is common to all chunks from this entry.
        attributes = entry.get("attributes", {})
        tags_str = attributes.get("Tags", "")
        tags_array = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        published_at_str = attributes.get("publishedAt")
        published_date = datetime.fromisoformat(published_at_str.replace('Z', '+00:00')) if published_at_str else None

        for doc in documents:
            # Combine the base metadata from the chunker with the article-level metadata
            combined_metadata = {
                **doc.metadata,
                "title": attributes.get("Title"),
                "slug": attributes.get("Slug"),
                "author": attributes.get("Author"),
                "tags": tags_str,
                "tags_array": tags_array,
                "published_date": published_date,
                "content_length": len(doc.page_content),
            }
            
            # Validate and structure the metadata using the Pydantic model
            validated_metadata = StrapiDocumentMetadata(**combined_metadata)
            doc.metadata = validated_metadata.dict()

        return documents

# Example usage (for testing purposes)
def main():
    processor = EmbeddingProcessorStrapi()

    # A sample Strapi entry structure
    sample_entry = {
        "id": 1,
        "attributes": {
            "Title": "What is Litecoin?",
            "Slug": "what-is-litecoin",
            "Author": "Litecoin Foundation",
            "Tags": "basics, crypto",
            "summary": "A brief introduction to Litecoin.",
            "publishedAt": "2025-06-17T12:00:00.000Z",
            "createdAt": "2025-06-17T11:00:00.000Z",
            "updatedAt": "2025-06-17T13:00:00.000Z",
            "content": [
                {"type": "heading", "level": 1, "children": [{"text": "The Basics"}]},
                {"type": "paragraph", "children": [{"text": "Litecoin is a peer-to-peer cryptocurrency."}]},
                {"type": "paragraph", "children": [{"text": "It was created by Charlie Lee."}]}
            ]
        }
    }

    documents = processor.process_entry(sample_entry)

    print(f"--- Found {len(documents)} documents ---")
    for i, doc in enumerate(documents):
        print(f"\\n--- Document {i+1} ---")
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {json.dumps(doc.metadata, indent=2)}")


if __name__ == "__main__":
    main()
