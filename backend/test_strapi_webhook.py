"""
Test with the exact payload from your Strapi webhook logs
"""

import json
from datetime import datetime
from typing import List, Dict, Any

# Your actual payload from the logs
real_payload = {
    "event": "entry.publish",
    "createdAt": "2025-06-18T13:14:07.344Z",
    "model": "article",
    "uid": "api::article.article",
    "entry": {
        "id": 132,
        "documentId": "lupjhok168tg6a0ec2gi975t",
        "Title": "test432",
        "Summary": "test432",
        "Content": [{"type": "paragraph", "children": [{"type": "text", "text": "test432"}]}],
        "Author": "test432",
        "Slug": "test432",
        "Tags": "test432",
        "Published": "2025-06-18T07:00:00.000Z",
        "createdAt": "2025-06-18T13:14:07.329Z",
        "updatedAt": "2025-06-18T13:14:07.329Z",
        "publishedAt": "2025-06-18T13:14:07.334Z",
        "locale": "en"
    }
}

def extract_text_from_blocks(content_blocks) -> str:
    """Extract text from Strapi blocks with better formatting"""
    if not content_blocks:
        return ""
    
    text_parts = []
    
    for block in content_blocks:
        if isinstance(block, dict):
            block_type = block.get('type', '')
            children = block.get('children', [])
            
            if block_type == 'heading-1':
                heading_text = extract_children_text(children)
                text_parts.append(f"# {heading_text}")
            elif block_type in ['paragraph', 'heading-2', 'heading-3', 'heading-4', 'heading-5', 'heading-6']:
                text_parts.append(extract_children_text(children))
            elif block_type == 'list':
                list_items = []
                for child in children:
                    if isinstance(child, dict) and child.get('type') == 'list-item':
                        item_text = extract_children_text(child.get('children', []))
                        list_items.append(f"• {item_text}")
                text_parts.append('\n'.join(list_items))
    
    return '\n\n'.join(text_parts)

def extract_children_text(children):
    """Extract text from children, preserving formatting"""
    text_parts = []
    for child in children:
        if isinstance(child, dict) and child.get('type') == 'text':
            text = child.get('text', '')
            if text:
                # Apply basic formatting
                if child.get('bold'):
                    text = f"**{text}**"
                if child.get('italic'):
                    text = f"*{text}*"
                text_parts.append(text)
    return ''.join(text_parts)

def test_payload_processing():
    """Test processing the real payload"""
    
    print("🔍 Testing Real Payload Processing")
    print("=" * 50)
    
    # Extract entry data
    entry_data = real_payload['entry']
    
    print(f"📋 Entry Fields:")
    for key, value in entry_data.items():
        print(f"   {key}: {value} (type: {type(value).__name__})")
    
    print(f"\n📝 Content Blocks:")
    content_blocks = entry_data['Content']
    print(f"   Raw: {content_blocks}")
    
    # Extract text
    extracted_text = extract_text_from_blocks(content_blocks)
    print(f"   Extracted text: '{extracted_text}'")
    
    # Build full content for embedding
    content_parts = []
    
    if entry_data.get('Title'):
        content_parts.append(f"Title: {entry_data['Title']}")
    
    if entry_data.get('Summary'):
        content_parts.append(f"Summary: {entry_data['Summary']}")
    
    if extracted_text:
        content_parts.append(f"Content: {extracted_text}")
    
    if entry_data.get('Author'):
        content_parts.append(f"Author: {entry_data['Author']}")
    
    if entry_data.get('Tags'):
        content_parts.append(f"Tags: {entry_data['Tags']}")
    
    embedding_content = "\n\n".join(content_parts)
    
    print(f"\n📄 Final Embedding Content:")
    print(f"'{embedding_content}'")
    
    # Build metadata
    metadata = {
        'strapi_id': entry_data['id'],
        'document_id': entry_data.get('documentId'),
        'source': 'strapi',
        'content_type': 'article',
        'title': entry_data.get('Title', ''),
        'summary': entry_data.get('Summary', ''),
        'author': entry_data.get('Author', ''),
        'slug': entry_data.get('Slug', ''),
        'tags': entry_data.get('Tags', ''),
        'locale': entry_data.get('locale', ''),
        'published_date': entry_data.get('Published'),
        'created_at': entry_data.get('createdAt'),
        'updated_at': entry_data.get('updatedAt'),
        'published_at': entry_data.get('publishedAt'),
    }
    
    print(f"\n🏷️  Metadata:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    
    print(f"\n✅ Processing completed successfully!")
    return embedding_content, metadata

# Test with more complex content blocks
def test_complex_content():
    """Test with more complex rich text content"""
    
    complex_content = [
        {
            "type": "heading-1",
            "children": [{"type": "text", "text": "Introduction to Litecoin"}]
        },
        {
            "type": "paragraph", 
            "children": [
                {"type": "text", "text": "Litecoin is a "},
                {"type": "text", "text": "cryptocurrency", "bold": True},
                {"type": "text", "text": " created by Charlie Lee."}
            ]
        },
        {
            "type": "list",
            "children": [
                {
                    "type": "list-item",
                    "children": [{"type": "text", "text": "Fast transactions"}]
                },
                {
                    "type": "list-item", 
                    "children": [{"type": "text", "text": "Low fees"}]
                }
            ]
        }
    ]
    
    print(f"\n🧪 Testing Complex Content:")
    print(f"Raw: {complex_content}")
    
    extracted = extract_text_from_blocks(complex_content)
    print(f"Extracted: '{extracted}'")

if __name__ == "__main__":
    # Test with your real payload
    test_payload_processing()
    
    # Test with complex content
    test_complex_content()