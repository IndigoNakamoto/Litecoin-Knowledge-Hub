import asyncio
import time
import logging
from dotenv import load_dotenv
from advanced_retrieval import AdvancedRetrievalPipeline
from data_ingestion.vector_store_manager import VectorStoreManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def benchmark_retrieval(pipeline: AdvancedRetrievalPipeline, query: str, iterations: int = 3) -> dict:
    """
    Benchmark retrieval performance for a given query.

    Args:
        pipeline: The retrieval pipeline to test
        query: Test query to run
        iterations: Number of times to run the query for averaging

    Returns:
        Dictionary with performance metrics
    """
    times = []

    for i in range(iterations):
        start_time = time.time()
        try:
            results = pipeline.retrieve(query, expand_query=True, rerank=True, top_k=5)
            end_time = time.time()
            elapsed = end_time - start_time
            times.append(elapsed)
            logger.info(f"Iteration {i+1}: {elapsed:.3f}s, retrieved {len(results)} documents")
        except Exception as e:
            logger.error(f"Iteration {i+1} failed: {e}")
            times.append(float('inf'))

    # Calculate statistics
    valid_times = [t for t in times if t != float('inf')]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        success_rate = len(valid_times) / iterations
    else:
        avg_time = min_time = max_time = float('inf')
        success_rate = 0.0

    return {
        'query': query,
        'iterations': iterations,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'success_rate': success_rate,
        'individual_times': times
    }

async def benchmark_retrieval_async(pipeline: AdvancedRetrievalPipeline, query: str, iterations: int = 3) -> dict:
    """
    Benchmark async retrieval performance for a given query.

    Args:
        pipeline: The retrieval pipeline to test
        query: Test query to run
        iterations: Number of times to run the query for averaging

    Returns:
        Dictionary with performance metrics
    """
    times = []

    for i in range(iterations):
        start_time = time.time()
        try:
            results = await pipeline.retrieve_async(query, expand_query=True, rerank=True, top_k=5)
            end_time = time.time()
            elapsed = end_time - start_time
            times.append(elapsed)
            logger.info(f"Async iteration {i+1}: {elapsed:.3f}s, retrieved {len(results)} documents")
        except Exception as e:
            logger.error(f"Async iteration {i+1} failed: {e}")
            times.append(float('inf'))

    # Calculate statistics
    valid_times = [t for t in times if t != float('inf')]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        success_rate = len(valid_times) / iterations
    else:
        avg_time = min_time = max_time = float('inf')
        success_rate = 0.0

    return {
        'query': query,
        'iterations': iterations,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'success_rate': success_rate,
        'individual_times': times
    }

def print_benchmark_results(results: dict, label: str):
    """Print formatted benchmark results."""
    print(f"\n=== {label} ===")
    print(f"Query: '{results['query']}'")
    print(f"Iterations: {results['iterations']}")
    print(f"Average time: {results['avg_time']:.3f}s")
    print(f"Min time: {results['min_time']:.3f}s")
    print(f"Max time: {results['max_time']:.3f}s")
    print(f"Success rate: {results['success_rate']*100:.1f}%")
    print(f"Individual times: {[f'{t:.3f}s' for t in results['individual_times']]}")

def main():
    """Main benchmark function."""
    # Load environment variables
    load_dotenv()

    # Initialize components
    try:
        vector_store_manager = VectorStoreManager()
        pipeline = AdvancedRetrievalPipeline(vector_store_manager)
        logger.info("Successfully initialized retrieval pipeline")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        return

    # Test queries
    test_queries = [
        "What is Litecoin?",
        "How does mining work?",
        "Where can I buy Litecoin?",
        "What are the advantages of Litecoin over Bitcoin?"
    ]

    print("Starting retrieval performance benchmark...")
    print("=" * 60)

    # Benchmark sync retrieval
    print("\nBENCHMARKING SYNCHRONOUS RETRIEVAL")
    for query in test_queries:
        results = benchmark_retrieval(pipeline, query, iterations=3)
        print_benchmark_results(results, f"Sync - {query}")

    # Benchmark async retrieval
    print("\nBENCHMARKING ASYNCHRONOUS RETRIEVAL")
    for query in test_queries:
        results = asyncio.run(benchmark_retrieval_async(pipeline, query, iterations=3))
        print_benchmark_results(results, f"Async - {query}")

    print("\n" + "=" * 60)
    print("Benchmark complete!")

if __name__ == "__main__":
    main()
