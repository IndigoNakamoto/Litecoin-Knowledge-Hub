#!/usr/bin/env python3
"""
Script to show semantic cache statistics.

This displays statistics for both Redis Stack vector cache (if enabled) and
legacy in-memory semantic cache (if enabled).

When the backend is running in Docker (via run-prod.sh), this script
will execute the stats command inside the backend container.

Usage:
    python scripts/semantic-cache-stats.py
"""

import sys
import os
import asyncio
import logging
import subprocess

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_backend_container():
    """Find the backend Docker container name."""
    try:
        # Check for production container
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=litecoin-backend", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            containers = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
            # Prefer production container
            for container in containers:
                if 'litecoin-backend' in container and 'prod' in container:
                    return container
            return containers[0] if containers else None
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


async def get_semantic_cache_stats():
    """Get semantic cache statistics."""
    # Check if backend is running in Docker
    container_name = find_backend_container()
    
    if container_name:
        logger.info(f"🔍 Backend container detected: {container_name}")
        logger.info("   Fetching stats from container...")
        print("")
        
        try:
            # Execute the stats command inside the container
            result = subprocess.run(
                [
                    "docker", "exec", container_name,
                    "python3", "-c",
                    """
import asyncio
import sys
import os
import json
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

async def get_stats():
    USE_REDIS_CACHE = os.getenv('USE_REDIS_CACHE', 'false').lower() == 'true'
    stats = {}
    
    # Get Redis Stack vector cache stats
    if USE_REDIS_CACHE:
        try:
            from rag_pipeline import _get_redis_vector_cache
            cache = _get_redis_vector_cache()
            if cache:
                redis_stats = await cache.stats()
                stats['redis_vector_cache'] = {
                    'entries': redis_stats.get('entries', 0),
                    'indexed_docs': redis_stats.get('indexed_docs', 0),
                    'memory_bytes': redis_stats.get('memory_bytes', 0),
                    'threshold': redis_stats.get('threshold', 0),
                    'dimension': redis_stats.get('dimension', 0)
                }
        except Exception as e:
            stats['redis_vector_cache'] = {'error': str(e)}
    
    # Get legacy semantic cache stats
    if not USE_REDIS_CACHE:
        try:
            from api.v1.sync.payload import _global_rag_pipeline
            if _global_rag_pipeline and hasattr(_global_rag_pipeline, 'semantic_cache') and _global_rag_pipeline.semantic_cache:
                legacy_stats = _global_rag_pipeline.semantic_cache.stats()
                stats['legacy_semantic_cache'] = {
                    'size': legacy_stats.get('size', 0),
                    'total': legacy_stats.get('total', 0),
                    'threshold': legacy_stats.get('threshold', 0),
                    'ttl_seconds': legacy_stats.get('ttl_seconds', 0),
                    'max_size': legacy_stats.get('max_size', 0)
                }
            else:
                stats['legacy_semantic_cache'] = {'status': 'not_initialized'}
        except Exception as e:
            stats['legacy_semantic_cache'] = {'error': str(e)}
    
    print(json.dumps(stats))
    return stats

asyncio.run(get_stats())
"""
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    import json
                    stats = json.loads(result.stdout.strip())
                    print_semantic_cache_stats(stats, USE_REDIS_CACHE=os.getenv("USE_REDIS_CACHE", "false").lower() == "true")
                    return
                except json.JSONDecodeError:
                    # Output might not be JSON, print it directly
                    print(result.stdout)
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)
                    return
            else:
                if result.stderr:
                    logger.warning(f"⚠️  Error: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout waiting for container command to complete")
        except Exception as e:
            logger.warning(f"⚠️  Error executing command in container: {e}")
        
        print("")
        logger.info("   Falling back to local method...")
        print("")
    
    # Fallback: Try to access stats directly (when running locally or if Docker method failed)
    USE_REDIS_CACHE = os.getenv("USE_REDIS_CACHE", "false").lower() == "true"
    
    # Change to backend directory and add it to path for relative imports
    backend_dir = os.path.join(project_root, 'backend')
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    
    stats = {}
    
    # Get Redis Stack vector cache stats
    if USE_REDIS_CACHE:
        try:
            from rag_pipeline import _get_redis_vector_cache
            redis_cache = _get_redis_vector_cache()
            if redis_cache:
                redis_stats = await redis_cache.stats()
                stats['redis_vector_cache'] = {
                    'entries': redis_stats.get('entries', 0),
                    'indexed_docs': redis_stats.get('indexed_docs', 0),
                    'memory_bytes': redis_stats.get('memory_bytes', 0),
                    'threshold': redis_stats.get('threshold', 0),
                    'dimension': redis_stats.get('dimension', 0)
                }
        except Exception as e:
            stats['redis_vector_cache'] = {'error': str(e)}
    else:
        stats['redis_vector_cache'] = {'status': 'disabled'}
    
    # Get legacy semantic cache stats
    if not USE_REDIS_CACHE:
        try:
            # Try to access via global RAG pipeline instance
            try:
                from backend.api.v1.sync.payload import _global_rag_pipeline
            except ImportError:
                from api.v1.sync.payload import _global_rag_pipeline
            
            if _global_rag_pipeline and hasattr(_global_rag_pipeline, "semantic_cache") and _global_rag_pipeline.semantic_cache:
                legacy_stats = _global_rag_pipeline.semantic_cache.stats()
                stats['legacy_semantic_cache'] = {
                    'size': legacy_stats.get('size', 0),
                    'total': legacy_stats.get('total', 0),
                    'threshold': legacy_stats.get('threshold', 0),
                    'ttl_seconds': legacy_stats.get('ttl_seconds', 0),
                    'max_size': legacy_stats.get('max_size', 0)
                }
            else:
                stats['legacy_semantic_cache'] = {'status': 'not_initialized'}
        except Exception as e:
            stats['legacy_semantic_cache'] = {'error': str(e)}
    else:
        stats['legacy_semantic_cache'] = {'status': 'disabled'}
    
    print_semantic_cache_stats(stats, USE_REDIS_CACHE)


def print_semantic_cache_stats(stats, USE_REDIS_CACHE):
    """Print formatted cache statistics."""
    print("=" * 70)
    print("Semantic Cache Statistics")
    print("=" * 70)
    print("")
    
    # Redis Stack Vector Cache
    if 'redis_vector_cache' in stats:
        redis_stats = stats['redis_vector_cache']
        if 'error' in redis_stats:
            print("❌ Redis Stack Vector Cache: Error")
            print(f"   {redis_stats['error']}")
        elif 'status' in redis_stats:
            print(f"ℹ️  Redis Stack Vector Cache: {redis_stats['status'].title()}")
        else:
            entries = redis_stats.get('entries', 0)
            indexed = redis_stats.get('indexed_docs', 0)
            memory_mb = redis_stats.get('memory_bytes', 0) / (1024 * 1024)
            threshold = redis_stats.get('threshold', 0)
            dimension = redis_stats.get('dimension', 0)
            
            print("📊 Redis Stack Vector Cache:")
            print(f"   Entries: {entries:,}")
            print(f"   Indexed Documents: {indexed:,}")
            print(f"   Memory Usage: {memory_mb:.2f} MB")
            print(f"   Similarity Threshold: {threshold}")
            print(f"   Vector Dimension: {dimension}")
    
    print("")
    
    # Legacy Semantic Cache
    if 'legacy_semantic_cache' in stats:
        legacy_stats = stats['legacy_semantic_cache']
        if 'error' in legacy_stats:
            print("❌ Legacy Semantic Cache: Error")
            print(f"   {legacy_stats['error']}")
        elif 'status' in legacy_stats:
            if legacy_stats['status'] == 'not_initialized':
                print("ℹ️  Legacy Semantic Cache: Not Initialized")
                print("   (Backend may not be running or Redis cache is enabled)")
            else:
                print(f"ℹ️  Legacy Semantic Cache: {legacy_stats['status'].title()}")
        else:
            size = legacy_stats.get('size', 0)
            total = legacy_stats.get('total', 0)
            threshold = legacy_stats.get('threshold', 0)
            ttl_hours = legacy_stats.get('ttl_seconds', 0) / 3600
            max_size = legacy_stats.get('max_size', 0)
            
            print("📊 Legacy Semantic Cache:")
            print(f"   Active Entries: {size:,}")
            print(f"   Total Entries: {total:,}")
            print(f"   Max Size: {max_size:,}")
            print(f"   Similarity Threshold: {threshold}")
            print(f"   TTL: {ttl_hours:.1f} hours")
    
    print("")
    print("=" * 70)
    
    # Summary
    total_entries = 0
    if 'redis_vector_cache' in stats and 'entries' in stats['redis_vector_cache']:
        total_entries += stats['redis_vector_cache']['entries']
    if 'legacy_semantic_cache' in stats and 'size' in stats['legacy_semantic_cache']:
        total_entries += stats['legacy_semantic_cache']['size']
    
    if total_entries > 0:
        print(f"\n✅ Total cached entries: {total_entries:,}")
    else:
        print("\nℹ️  No cached entries found")


if __name__ == "__main__":
    print("📊 Fetching semantic cache statistics...")
    print("")
    asyncio.run(get_semantic_cache_stats())


