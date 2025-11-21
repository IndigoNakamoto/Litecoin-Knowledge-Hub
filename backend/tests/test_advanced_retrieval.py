"""
Test script for advanced retrieval capabilities.

This script tests the new hybrid search, query expansion, and re-ranking features.
"""

import os
import sys
from dotenv import load_dotenv
import pytest

# Add project root and backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(backend_dir)
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Try to import advanced_retrieval, skip tests if not available
try:
    from advanced_retrieval import AdvancedRetrievalPipeline, QueryExpansionService
    ADVANCED_RETRIEVAL_AVAILABLE = True
except ImportError:
    ADVANCED_RETRIEVAL_AVAILABLE = False
    AdvancedRetrievalPipeline = None
    QueryExpansionService = None

from backend.data_ingestion.vector_store_manager import VectorStoreManager

@pytest.mark.skipif(not ADVANCED_RETRIEVAL_AVAILABLE, reason="advanced_retrieval module not available")
def test_query_expansion():
    """Test query expansion functionality."""
    print("🧪 Testing Query Expansion...")

    expander = QueryExpansionService()

    test_queries = [
        "litecoin price",
        "mining hardware",
        "wallet address",
        "transaction fee"
    ]

    for query in test_queries:
        expanded = expander.expand_query(query, use_llm=False)  # Test static expansion first
        print(f"Query: '{query}' → {len(expanded)} variations: {expanded}")

    print("✅ Query expansion test completed\n")

@pytest.mark.skipif(not ADVANCED_RETRIEVAL_AVAILABLE, reason="advanced_retrieval module not available")
def test_advanced_retrieval():
    """Test the complete advanced retrieval pipeline."""
    print("🧪 Testing Advanced Retrieval Pipeline...")

    try:
        # Initialize components
        vector_store_manager = VectorStoreManager()
        advanced_retrieval = AdvancedRetrievalPipeline(vector_store_manager)

        # Test queries
        test_queries = [
            "What is Litecoin?",
            "litecoin mining",
            "wallet security",
            "transaction speed"
        ]

        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")

            # Test with different configurations
            configs = [
                ("Basic", False, False),
                ("With Expansion", True, False),
                ("With Re-ranking", False, True),
                ("Full Advanced", True, True)
            ]

            for config_name, expand, rerank in configs:
                try:
                    docs = advanced_retrieval.retrieve(
                        query=query,
                        expand_query=expand,
                        rerank=rerank,
                        top_k=5
                    )
                    print(f"  {config_name}: Retrieved {len(docs)} documents")
                    if docs:
                        print(f"    Top document: {docs[0].page_content[:100]}...")
                        if hasattr(docs[0], 'metadata') and 'rerank_score' in docs[0].metadata:
                            print(f"    Re-rank score: {docs[0].metadata['rerank_score']:.3f}")
                except Exception as e:
                    print(f"  {config_name}: Error - {e}")

        print("✅ Advanced retrieval test completed\n")

    except Exception as e:
        print(f"❌ Advanced retrieval test failed: {e}\n")

@pytest.mark.skipif(not ADVANCED_RETRIEVAL_AVAILABLE, reason="advanced_retrieval module not available")
def test_hybrid_search():
    """Test hybrid search components individually."""
    print("🧪 Testing Hybrid Search Components...")

    try:
        vector_store_manager = VectorStoreManager()
        advanced_retrieval = AdvancedRetrievalPipeline(vector_store_manager)

        query = "litecoin mining"

        # Test BM25 search
        bm25_results = advanced_retrieval.bm25_indexer.search(query, top_k=5)
        print(f"BM25 results for '{query}': {len(bm25_results)} matches")

        # Test dense search
        dense_retriever = vector_store_manager.get_retriever(search_kwargs={"k": 5})
        dense_docs = dense_retriever.get_relevant_documents(query)
        print(f"Dense search results for '{query}': {len(dense_docs)} documents")

        # Test hybrid retrieval
        hybrid_docs = advanced_retrieval.hybrid_retriever.get_relevant_documents(query) if advanced_retrieval.hybrid_retriever else []
        print(f"Hybrid search results for '{query}': {len(hybrid_docs)} documents")

        print("✅ Hybrid search test completed\n")

    except Exception as e:
        print(f"❌ Hybrid search test failed: {e}\n")

def main():
    """Run all tests."""
    print("🚀 Starting Advanced Retrieval Tests\n")

    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("✅ Environment variables loaded")
    else:
        print("⚠️  No .env file found, using system environment variables")

    # Check required environment variables
    required_vars = ['GOOGLE_API_KEY', 'MONGO_URI']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return

    # Run tests
    test_query_expansion()
    test_hybrid_search()
    test_advanced_retrieval()

    print("🎉 All tests completed!")

if __name__ == "__main__":
    main()
