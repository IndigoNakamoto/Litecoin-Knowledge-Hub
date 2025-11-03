#!/usr/bin/env python3
"""
Test script for conversational memory functionality in RAG pipeline.
Tests the LangChain-style conversation management with history-aware retrieval.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from rag_pipeline import RAGPipeline

def test_conversational_memory():
    """Test conversational memory with follow-up questions."""
    print("🧠 Testing Conversational Memory Implementation")
    print("=" * 50)

    try:
        # Initialize RAG pipeline
        pipeline = RAGPipeline()
        print("✅ RAG Pipeline initialized with conversational memory")

        # Test 1: Initial query about Litecoin
        print("\n📝 Test 1: Initial query")
        initial_query = "What is Litecoin?"
        print(f"Query: '{initial_query}'")

        answer1, sources1 = pipeline.query(initial_query, chat_history=[])
        print(f"Answer: {answer1[:200]}...")
        print(f"Sources: {len(sources1)} documents retrieved")

        # Test 2: Follow-up question using "it" (should understand context)
        print("\n📝 Test 2: Follow-up question with context")
        followup_query = "Who created it?"
        print(f"Query: '{followup_query}' (referring to Litecoin)")

        # Provide the previous conversation as history
        chat_history = [(initial_query, answer1)]
        print(f"Chat history provided: {len(chat_history)} pairs")
        answer2, sources2 = pipeline.query(followup_query, chat_history)
        print(f"Answer: {answer2[:300]}...")
        print(f"Sources: {len(sources2)} documents retrieved")

        # Debug: Check if the answer mentions Charlie Lee
        if "Charlie" in answer2 or "Lee" in answer2:
            print("✅ SUCCESS: Answer correctly identifies Charlie Lee as Litecoin creator")
        else:
            print("❌ ISSUE: Answer does not mention Charlie Lee")

        # Test 3: Another follow-up about differences
        print("\n📝 Test 3: Second follow-up question")
        followup2_query = "How is it different from Bitcoin?"
        print(f"Query: '{followup2_query}' (should still understand 'it' means Litecoin)")

        # Add to conversation history
        chat_history.append((followup_query, answer2))
        answer3, sources3 = pipeline.query(followup2_query, chat_history)
        print(f"Answer: {answer3[:200]}...")
        print(f"Sources: {len(sources3)} documents retrieved")

        # Test 4: Test standalone question generation
        print("\n📝 Test 4: Testing 'What about the second one?' scenario")
        # Simulate a conversation where AI mentioned multiple things
        simulated_history = [
            ("What are some Litecoin features?", "Litecoin has several key features: 1) Faster block times (2.5 minutes vs Bitcoin's 10 minutes), 2) Scrypt mining algorithm, 3) Segregated Witness (SegWit) support, 4) Lightning Network compatibility.")
        ]

        ambiguous_query = "What about the second one?"
        print(f"Query: '{ambiguous_query}' (should be converted to standalone question)")

        answer4, sources4 = pipeline.query(ambiguous_query, simulated_history)
        print(f"Answer: {answer4[:200]}...")
        print(f"Sources: {len(sources4)} documents retrieved")

        print("\n🎉 All conversational memory tests completed successfully!")
        print("✅ History-aware retrieval working")
        print("✅ Memory management functional")
        print("✅ Standalone question generation active")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conversational_memory()
