#!/usr/bin/env python3
"""
Check if any documents in MongoDB contain "blocktime" or related terms.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

load_dotenv()

from pymongo import MongoClient
import re

def check_blocktime_documents():
    """Check MongoDB for documents containing blocktime."""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("❌ MONGO_URI not set")
        return
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client["litecoin_rag_db"]
        collection = db["litecoin_docs"]
        
        # Search for documents containing "blocktime" (case-insensitive)
        search_terms = ["blocktime", "block time", "block-time", "2.5 minutes", "2.5 min"]
        
        print("=" * 80)
        print("Searching for documents containing blocktime-related terms...")
        print("=" * 80)
        
        found_docs = []
        
        for term in search_terms:
            # Use regex for case-insensitive search
            pattern = re.compile(term, re.IGNORECASE)
            docs = list(collection.find({
                "$or": [
                    {"text": pattern},
                    {"metadata.doc_title": pattern},
                    {"metadata.title": pattern}
                ]
            }).limit(10))
            
            if docs:
                print(f"\n✅ Found {len(docs)} documents containing '{term}':")
                for i, doc in enumerate(docs[:5], 1):  # Show first 5
                    text_preview = doc.get("text", "")[:200].replace('\n', ' ')
                    title = doc.get("metadata", {}).get("doc_title") or doc.get("metadata", {}).get("title", "N/A")
                    payload_id = doc.get("metadata", {}).get("payload_id", "N/A")
                    print(f"\n  {i}. Title: {title}")
                    print(f"     Payload ID: {payload_id}")
                    print(f"     Preview: {text_preview}...")
                found_docs.extend(docs)
        
        # Also check total document count
        total_docs = collection.count_documents({})
        published_docs = collection.count_documents({"metadata.status": "published"})
        
        print("\n" + "=" * 80)
        print("Summary:")
        print("=" * 80)
        print(f"Total documents in MongoDB: {total_docs}")
        print(f"Published documents: {published_docs}")
        print(f"Documents containing 'blocktime': {len(set(d.get('_id') for d in found_docs))}")
        
        if not found_docs:
            print("\n⚠️  No documents found containing 'blocktime' or related terms!")
            print("   This explains why the query returns irrelevant results.")
            print("   You may need to add content about Litecoin's blocktime to your knowledge base.")
        else:
            print(f"\n✅ Found {len(set(d.get('_id') for d in found_docs))} unique documents about blocktime")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_blocktime_documents()


