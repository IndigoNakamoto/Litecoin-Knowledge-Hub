import json
from typing import List, Dict, Any, Optional, Tuple

class StrapiEmbeddingProcessor:
    """
    Processes Strapi API responses to prepare them for embedding.
    
    This class is responsible for parsing the JSON structure of a Strapi rich text field,
    converting it into a clean text format, and applying a hierarchical chunking strategy
    to maintain contextual awareness.
    """

    def _parse_rich_text(self, content_json: List[Dict[str, Any]]) -> str:
        """
        Parses Strapi's rich text JSON into a plain text string.
        
        Args:
            content_json (List[Dict[str, Any]]): The JSON array from a Strapi rich text field.

        Returns:
            str: A string representation of the content.
        """
        texts = []
        for block in content_json:
            if block.get("type") == "paragraph":
                for child in block.get("children", []):
                    if "text" in child:
                        texts.append(child["text"])
        return "\\n".join(texts)

    def process_entry(self, entry: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Processes a single Strapi entry to extract its content and metadata.

        Args:
            entry (Dict[str, Any]): A dictionary representing a single Strapi entry,
                                    typically from the StrapiClient.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the processed text content
                                        and a dictionary of its metadata.
        """
        attributes = entry.get("attributes", {})
        
        # Extract and parse the rich text content
        content_json_str = attributes.get("content", "[]")
        try:
            # The content might be a stringified JSON, so we parse it.
            content_json = json.loads(content_json_str) if isinstance(content_json_str, str) else content_json_str
        except json.JSONDecodeError:
            content_json = []
            
        content_text = self._parse_rich_text(content_json)

        # Map metadata from Strapi to our RAG schema
        metadata = {
            "strapi_id": entry.get("id"),
            "source_type": "strapi",
            "title": attributes.get("title"),
            "slug": attributes.get("slug"),
            "author": attributes.get("author"),
            "tags": attributes.get("tags"),
            "published_at": attributes.get("publishedAt"),
            "created_at": attributes.get("createdAt"),
            "updated_at": attributes.get("updatedAt"),
        }
        
        # Filter out any None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return content_text, metadata

# Example usage (for testing purposes)
def main():
    processor = StrapiEmbeddingProcessor()

    # A sample Strapi entry structure
    sample_entry = {
        "id": 1,
        "attributes": {
            "title": "What is Litecoin?",
            "slug": "what-is-litecoin",
            "author": "Litecoin Foundation",
            "tags": "basics, crypto",
            "publishedAt": "2025-06-17T12:00:00.000Z",
            "createdAt": "2025-06-17T11:00:00.000Z",
            "updatedAt": "2025-06-17T13:00:00.000Z",
            "content": json.dumps([
                {"type": "paragraph", "children": [{"text": "Litecoin is a peer-to-peer cryptocurrency."}]},
                {"type": "paragraph", "children": [{"text": "It was created by Charlie Lee."}]}
            ])
        }
    }

    content, metadata = processor.process_entry(sample_entry)

    print("--- Processed Content ---")
    print(content)
    print("\\n--- Metadata ---")
    print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    main()
