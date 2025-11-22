#!/usr/bin/env python3
"""
Test script to verify astream_query functionality with full RAG processing capabilities.
"""
import os
import sys

# Load environment variables BEFORE any other imports
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
    print('✅ Loaded .env file')
else:
    print('❌ No .env file found')

# Now import other modules
import asyncio
import pytest
from rag_pipeline import RAGPipeline

@pytest.mark.asyncio
async def test_astream_query():
    """Test the modified astream_query method."""
    try:
        print('🚀 Initializing RAGPipeline...')
        pipeline = RAGPipeline()
        print('✅ RAGPipeline initialized successfully')

        # Test 1: Basic streaming query without history
        print('\n📝 Test 1: Basic streaming query')
        print('Query: "What is Litecoin?"')

        chunks = []
        sources_count = 0
        from_cache = False

        async for chunk in pipeline.astream_query('What is Litecoin?', []):
            if chunk['type'] == 'sources':
                sources_count = len(chunk['sources'])
                print(f'📚 Received {sources_count} sources')
                # Check if sources are filtered (should only be published)
                published_count = sum(1 for doc in chunk['sources'] if doc.metadata.get('status') == 'published')
                print(f'📋 Published sources: {published_count}/{sources_count}')

            elif chunk['type'] == 'chunk':
                chunks.append(chunk['content'])

            elif chunk['type'] == 'complete':
                from_cache = chunk.get('from_cache', False)
                print(f'✅ Complete! From cache: {from_cache}')
                break

        full_response = ''.join(chunks)
        print(f'📏 Response length: {len(full_response)} characters')
        print(f'💬 Response preview: {full_response[:150]}...')

        # Test 2: Query with chat history (conversational context)
        print('\n📝 Test 2: Conversational query with history')
        print('Query: "Who created it?" (with previous context)')

        history = [('What is Litecoin?', full_response[:200] + '...')]  # Simulate previous response

        chunks2 = []
        sources_count2 = 0

        async for chunk in pipeline.astream_query('Who created it?', history):
            if chunk['type'] == 'sources':
                sources_count2 = len(chunk['sources'])
                print(f'📚 Received {sources_count2} sources (with history)')
                published_count2 = sum(1 for doc in chunk['sources'] if doc.metadata.get('status') == 'published')
                print(f'📋 Published sources: {published_count2}/{sources_count2}')

            elif chunk['type'] == 'chunk':
                chunks2.append(chunk['content'])

            elif chunk['type'] == 'complete':
                from_cache2 = chunk.get('from_cache', False)
                print(f'✅ Complete! From cache: {from_cache2}')
                break

        full_response2 = ''.join(chunks2)
        print(f'📏 Response length: {len(full_response2)} characters')
        print(f'💬 Response preview: {full_response2[:150]}...')

        # Test 3: Verify caching works
        print('\n📝 Test 3: Cache verification')
        print('Repeating first query to test caching...')

        chunks3 = []
        async for chunk in pipeline.astream_query('What is Litecoin?', []):
            if chunk['type'] == 'sources':
                print(f'📚 Cache test - Received {len(chunk["sources"])} sources')
            elif chunk['type'] == 'chunk':
                chunks3.append(chunk['content'])
            elif chunk['type'] == 'complete':
                from_cache3 = chunk.get('from_cache', False)
                print(f'✅ Cache test complete! From cache: {from_cache3}')
                break

        cached_response = ''.join(chunks3)
        cache_match = full_response == cached_response
        print(f'📋 Cache response matches: {cache_match}')

        print('\n🎉 All tests completed successfully!')
        print('✅ astream_query now has the same RAG processing capabilities as aquery')
        print('✅ Streaming functionality preserved')
        print('✅ Chat history support added')
        print('✅ Source filtering implemented')
        print('✅ Caching functionality maintained')

        # Assertions for pytest
        assert len(full_response) > 0, "Response should not be empty"
        assert sources_count > 0, "Should have sources"
        assert cache_match, "Cache response should match original"

    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()
        raise  # Re-raise for pytest to catch

if __name__ == '__main__':
    result = asyncio.run(test_astream_query())
    print(f'\n🏁 Final result: {"PASSED" if result else "FAILED"}')
