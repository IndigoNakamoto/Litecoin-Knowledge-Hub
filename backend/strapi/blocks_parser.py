"""
Comprehensive handler for all Strapi rich text block types
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_text_from_strapi_blocks(content_blocks: List[Dict[str, Any]]) -> str:
    """
    Extract plain text from Strapi's rich text blocks format.
    
    Handles all common Strapi block types:
    - Paragraphs
    - Headings (h1-h6)
    - Lists (ordered/unordered)
    - Quotes
    - Code blocks
    - Images (alt text)
    - Links
    - Text formatting (bold, italic, etc.)
    """
    if not content_blocks:
        return ""
    
    text_parts = []
    
    try:
        for block in content_blocks:
            if not isinstance(block, dict):
                continue
                
            block_type = block.get('type', '')
            block_text = extract_text_from_block(block, block_type)
            
            if block_text:
                text_parts.append(block_text)
    
    except Exception as e:
        logger.warning(f"Error parsing Strapi blocks: {str(e)}")
        # Fallback: try to extract any text recursively
        return extract_text_recursive(content_blocks)
    
    return '\n\n'.join(text_parts).strip()

def extract_text_from_block(block: Dict[str, Any], block_type: str) -> str:
    """Extract text from a single block based on its type"""
    
    if block_type == 'paragraph':
        return extract_children_text(block.get('children', []))
    
    elif block_type in ['heading-1', 'heading-2', 'heading-3', 'heading-4', 'heading-5', 'heading-6']:
        heading_text = extract_children_text(block.get('children', []))
        # Add heading markers for better context
        level = block_type.split('-')[1]
        return f"{'#' * int(level)} {heading_text}"
    
    elif block_type == 'quote':
        quote_text = extract_children_text(block.get('children', []))
        return f"> {quote_text}"
    
    elif block_type == 'code':
        code_text = extract_children_text(block.get('children', []))
        language = block.get('language', '')
        return f"```{language}\n{code_text}\n```"
    
    elif block_type in ['list', 'list-ordered', 'list-unordered']:
        return extract_list_text(block)
    
    elif block_type == 'list-item':
        item_text = extract_children_text(block.get('children', []))
        return f"• {item_text}"
    
    elif block_type == 'image':
        return extract_image_text(block)
    
    elif block_type == 'link':
        link_text = extract_children_text(block.get('children', []))
        url = block.get('url', '')
        return f"{link_text} ({url})" if url else link_text
    
    elif block_type == 'divider':
        return "---"
    
    elif block_type == 'table':
        return extract_table_text(block)
    
    else:
        # Unknown block type - try to extract any text
        logger.debug(f"Unknown block type: {block_type}")
        return extract_children_text(block.get('children', []))

def extract_children_text(children: List[Dict[str, Any]]) -> str:
    """Extract text from children elements (recursive)"""
    if not children:
        return ""
    
    text_parts = []
    
    for child in children:
        if not isinstance(child, dict):
            continue
            
        child_type = child.get('type', '')
        
        if child_type == 'text':
            text = child.get('text', '')
            if text:
                # Apply formatting if present
                formatted_text = apply_text_formatting(text, child)
                text_parts.append(formatted_text)
        
        elif child_type == 'link':
            link_text = extract_children_text(child.get('children', []))
            url = child.get('url', '')
            formatted_link = f"{link_text} ({url})" if url else link_text
            text_parts.append(formatted_link)
        
        elif child_type in ['strong', 'emphasis', 'code', 'strikethrough']:
            # Handle inline formatting elements
            inner_text = extract_children_text(child.get('children', []))
            if child_type == 'strong':
                text_parts.append(f"**{inner_text}**")
            elif child_type == 'emphasis':
                text_parts.append(f"*{inner_text}*")
            elif child_type == 'code':
                text_parts.append(f"`{inner_text}`")
            elif child_type == 'strikethrough':
                text_parts.append(f"~~{inner_text}~~")
            else:
                text_parts.append(inner_text)
        
        else:
            # Try to extract text from any other child types
            if 'children' in child:
                nested_text = extract_children_text(child['children'])
                if nested_text:
                    text_parts.append(nested_text)
            elif 'text' in child:
                text_parts.append(str(child['text']))
    
    return ''.join(text_parts)

def apply_text_formatting(text: str, child: Dict[str, Any]) -> str:
    """Apply text formatting based on child properties"""
    formatted_text = text
    
    # Check for formatting properties
    if child.get('bold') or child.get('strong'):
        formatted_text = f"**{formatted_text}**"
    
    if child.get('italic') or child.get('emphasis'):
        formatted_text = f"*{formatted_text}*"
    
    if child.get('underline'):
        formatted_text = f"__{formatted_text}__"
    
    if child.get('strikethrough'):
        formatted_text = f"~~{formatted_text}~~"
    
    if child.get('code'):
        formatted_text = f"`{formatted_text}`"
    
    return formatted_text

def extract_list_text(list_block: Dict[str, Any]) -> str:
    """Extract text from list blocks"""
    children = list_block.get('children', [])
    list_items = []
    
    list_type = list_block.get('type', 'list')
    is_ordered = 'ordered' in list_type
    
    for i, child in enumerate(children, 1):
        if isinstance(child, dict):
            if child.get('type') == 'list-item':
                item_text = extract_children_text(child.get('children', []))
                if is_ordered:
                    list_items.append(f"{i}. {item_text}")
                else:
                    list_items.append(f"• {item_text}")
            else:
                # Handle nested content
                item_text = extract_text_from_block(child, child.get('type', ''))
                if item_text:
                    if is_ordered:
                        list_items.append(f"{i}. {item_text}")
                    else:
                        list_items.append(f"• {item_text}")
    
    return '\n'.join(list_items)

def extract_image_text(image_block: Dict[str, Any]) -> str:
    """Extract descriptive text from image blocks"""
    image_info = []
    
    # Get image details
    image = image_block.get('image', {})
    if isinstance(image, dict):
        alt_text = image.get('alternativeText', '')
        caption = image.get('caption', '')
        name = image.get('name', '')
        
        if alt_text:
            image_info.append(f"Image: {alt_text}")
        elif caption:
            image_info.append(f"Image: {caption}")
        elif name:
            image_info.append(f"Image: {name}")
        else:
            image_info.append("Image")
    
    return ' '.join(image_info)

def extract_table_text(table_block: Dict[str, Any]) -> str:
    """Extract text from table blocks"""
    try:
        rows = table_block.get('children', [])
        table_text = []
        
        for row in rows:
            if isinstance(row, dict) and row.get('type') == 'table-row':
                cells = row.get('children', [])
                row_text = []
                
                for cell in cells:
                    if isinstance(cell, dict) and cell.get('type') in ['table-cell', 'table-header']:
                        cell_text = extract_children_text(cell.get('children', []))
                        row_text.append(cell_text)
                
                if row_text:
                    table_text.append(' | '.join(row_text))
        
        return '\n'.join(table_text)
    
    except Exception as e:
        logger.warning(f"Error extracting table text: {str(e)}")
        return "Table content"

def extract_text_recursive(data: Any) -> str:
    """
    Fallback function to recursively extract any text from complex structures
    """
    text_parts = []
    
    try:
        if isinstance(data, dict):
            # Look for text fields
            if 'text' in data and data['text']:
                text_parts.append(str(data['text']))
            
            # Recursively process other fields
            for key, value in data.items():
                if key != 'text':  # Avoid duplicating text we already found
                    nested_text = extract_text_recursive(value)
                    if nested_text:
                        text_parts.append(nested_text)
        
        elif isinstance(data, list):
            for item in data:
                nested_text = extract_text_recursive(item)
                if nested_text:
                    text_parts.append(nested_text)
        
        elif isinstance(data, str) and data.strip():
            text_parts.append(data)
    
    except Exception as e:
        logger.warning(f"Error in recursive text extraction: {str(e)}")
    
    return ' '.join(text_parts)

# Test function with various block types
def test_comprehensive_blocks():
    """Test the comprehensive block handler with various content types"""
    
    test_content = [
        {
            "type": "heading-1",
            "children": [{"type": "text", "text": "Complete Guide to Litecoin"}]
        },
        {
            "type": "paragraph",
            "children": [
                {"type": "text", "text": "Litecoin is a "},
                {"type": "text", "text": "peer-to-peer cryptocurrency", "bold": True},
                {"type": "text", "text": " created by "},
                {"type": "text", "text": "Charlie Lee", "italic": True},
                {"type": "text", "text": " in 2011."}
            ]
        },
        {
            "type": "quote",
            "children": [
                {"type": "text", "text": "Litecoin is the silver to Bitcoin's gold."}
            ]
        },
        {
            "type": "list",
            "children": [
                {
                    "type": "list-item",
                    "children": [{"type": "text", "text": "Faster transaction times"}]
                },
                {
                    "type": "list-item",
                    "children": [{"type": "text", "text": "Lower transaction fees"}]
                },
                {
                    "type": "list-item", 
                    "children": [{"type": "text", "text": "Scrypt mining algorithm"}]
                }
            ]
        },
        {
            "type": "code",
            "language": "bash",
            "children": [
                {"type": "text", "text": "litecoin-cli getblockchaininfo"}
            ]
        },
        {
            "type": "image",
            "image": {
                "alternativeText": "Litecoin logo and network visualization",
                "caption": "The Litecoin network structure"
            }
        }
    ]
    
    print("🧪 Testing Comprehensive Block Types")
    print("=" * 50)
    
    result = extract_text_from_strapi_blocks(test_content)
    print("Extracted text:")
    print(result)
    print("\n" + "=" * 50)
    
    return result

if __name__ == "__main__":
    test_comprehensive_blocks()