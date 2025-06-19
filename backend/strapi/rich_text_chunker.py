# backend/strapi/rich_text_chunker.py
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

class StrapiRichTextChunker:
    """
    A chunker that intelligently splits Strapi's rich text JSON content
    into structured documents based on headings, lists, and other elements.
    """

    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size

    def chunk_document(self, article_data: Dict[str, Any]) -> List[Document]:
        """
        Chunks a single Strapi article into multiple documents based on heading structure.
        """
        chunks = []
        strapi_id = article_data['id']
        title = article_data['attributes']['title']
        summary = article_data['attributes'].get('summary', '')

        # Create a document for the title and summary
        title_summary_content = f"Title: {title}\nSummary: {summary}"
        chunks.append(Document(
            page_content=title_summary_content.strip(),
            metadata={
                "strapi_id": strapi_id,
                "chunk_type": "title_summary",
                "section_title": title,
                "parent_headings": [],
                "heading_level": 0,
                "chunk_index": 0
            }
        ))

        content_blocks = article_data['attributes'].get('content', [])
        if not content_blocks:
            return chunks

        current_chunk_blocks: List[Dict[str, Any]] = []
        heading_hierarchy: List[str] = []

        for block in content_blocks:
            if block.get('type') == 'heading':
                # If we find a heading and there's content in the current chunk,
                # finalize the previous chunk.
                if current_chunk_blocks:
                    doc = self._create_document_from_blocks(
                        strapi_id, len(chunks), current_chunk_blocks, heading_hierarchy
                    )
                    chunks.append(doc)
                    current_chunk_blocks = []

                # Update heading hierarchy
                level = block.get('level', 1)
                heading_text = self._get_text_from_children(block.get('children', []))
                
                # Trim the hierarchy to the parent level of the current heading
                heading_hierarchy = heading_hierarchy[:level - 1]
                heading_hierarchy.append(heading_text)
                
                current_chunk_blocks.append(block)
            else:
                # If there's no heading hierarchy, this content belongs to the intro
                if not heading_hierarchy:
                     # If there is no heading, create a default one.
                    heading_hierarchy.append(title)

                current_chunk_blocks.append(block)

        # Add the last remaining chunk
        if current_chunk_blocks:
            doc = self._create_document_from_blocks(
                strapi_id, len(chunks), current_chunk_blocks, heading_hierarchy
            )
            chunks.append(doc)

        return chunks

    def _create_document_from_blocks(
        self,
        strapi_id: int,
        chunk_index: int,
        blocks: List[Dict[str, Any]],
        heading_hierarchy: List[str],
    ) -> Document:
        """Helper function to create a Document object from a list of blocks."""
        content_markdown = self._blocks_to_markdown(blocks)

        # Prepend hierarchical context to the content for better retrieval
        context_prefix = " > ".join(heading_hierarchy)
        page_content = f"{context_prefix}\n\n{content_markdown}"

        # Create rich metadata for filtering and context
        metadata = {
            "strapi_id": strapi_id,
            "chunk_type": "section",
            "section_title": heading_hierarchy[-1] if heading_hierarchy else "Introduction",
            "parent_headings": heading_hierarchy[:-1],
            "heading_level": len(heading_hierarchy),
            "chunk_index": chunk_index,
        }
        
        return Document(page_content=page_content.strip(), metadata=metadata)

    def _blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """
        Converts Strapi's rich text JSON to a Markdown-like string.
        """
        markdown_lines = []
        for block in blocks:
            if block['type'] == 'heading':
                level = block.get('level', 1)
                markdown_lines.append(f"{'#' * level} {self._get_text_from_children(block['children'])}")
            elif block['type'] == 'paragraph':
                markdown_lines.append(self._get_text_from_children(block['children']))
            elif block['type'] == 'list':
                list_char = '* ' if block.get('format') == 'unordered' else '1. '
                for item in block['children']:
                    markdown_lines.append(f"{list_char}{self._get_text_from_children(item['children'])}")
        return "\n\n".join(markdown_lines)

    def _get_text_from_children(self, children: List[Dict[str, Any]]) -> str:
        """
        Recursively extracts and formats text from the 'children' array of a block,
        handling different node types like text and links.
        """
        text_parts = []
        for child in children:
            node_type = child.get('type')

            if node_type == 'link':
                # For links, recursively process children to get the link text
                link_text = self._get_text_from_children(child.get('children', []))
                link_url = child.get('url', '')
                text_parts.append(f"[{link_text}]({link_url})")
            elif 'text' in child:
                # For text nodes, get the text and apply formatting
                text = child['text']
                if child.get('bold'):
                    text = f"**{text}**"
                if child.get('italic'):
                    text = f"*{text}*"
                text_parts.append(text)
                
        return "".join(text_parts)
