#!/usr/bin/env python3
"""
Test script to query "blocktime" and capture detailed embedding and retrieval logs.
This helps diagnose vector embedding issues.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

# Setup logging to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_blocktime_query():
    """Test querying 'blocktime' and show detailed logs."""
    from dotenv import load_dotenv
    load_dotenv()
    
    from backend.rag_pipeline import RAGPipeline
    
    print("=" * 80)
    print("Testing 'blocktime' Query")
    print("=" * 80)
    
    # Initialize RAG pipeline
    print("\n1. Initializing RAG pipeline...")
    rag = RAGPipeline()
    print("   ✓ RAG pipeline initialized")
    
    # Check vector store info
    if hasattr(rag, 'vector_store_manager'):
        vsm = rag.vector_store_manager
        if hasattr(vsm, 'vector_store') and hasattr(vsm.vector_store, 'index'):
            vector_count = vsm.vector_store.index.ntotal
            print(f"   ✓ FAISS index has {vector_count} vectors")
            
            # Check dimension
            if hasattr(vsm.vector_store.index, 'd'):
                dimension = vsm.vector_store.index.d
                print(f"   ✓ Vector dimension: {dimension}")
    
    # Test the query
    print("\n2. Querying 'blocktime'...")
    query = "blocktime"
    
    try:
        answer, sources, metadata = await rag.aquery(query, [])
        
        print(f"\n3. Query Results:")
        print(f"   Query: '{query}'")
        print(f"   Answer length: {len(answer)} chars")
        print(f"   Sources found: {len(sources)}")
        print(f"   Cache hit: {metadata.get('cache_hit', False)}")
        print(f"   Duration: {metadata.get('duration_seconds', 0):.2f}s")
        
        print(f"\n4. Answer Preview:")
        print(f"   {answer[:200]}...")
        
        print(f"\n5. Top Sources:")
        for i, source in enumerate(sources[:3], 1):
            preview = source.page_content[:150].replace('\n', ' ')
            print(f"   {i}. {preview}...")
            if hasattr(source, 'metadata'):
                print(f"      Metadata: {source.metadata.get('doc_title', 'N/A')}")
        
        # Check if answer mentions blocktime
        if 'blocktime' in answer.lower() or 'block time' in answer.lower():
            print("\n   ✓ Answer mentions blocktime")
        else:
            print("\n   ⚠️  Answer does NOT mention blocktime - potential issue!")
        
        # Check if sources mention blocktime
        blocktime_in_sources = any(
            'blocktime' in s.page_content.lower() or 'block time' in s.page_content.lower()
            for s in sources
        )
        if blocktime_in_sources:
            print("   ✓ Sources contain blocktime information")
        else:
            print("   ⚠️  Sources do NOT contain blocktime information - retrieval issue!")
        
    except Exception as e:
        print(f"\n❌ Error during query: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_blocktime_query())


