#!/usr/bin/env python3
"""
Script to clear the semantic cache.

This clears both Redis Stack vector cache (if enabled) and
legacy in-memory semantic cache (if enabled).

When the backend is running in Docker (via run-prod.sh), this script
will execute the clear command inside the backend container.

Usage:
    python scripts/clear-semantic-cache.py
"""

import sys
import os
import asyncio
import logging
import subprocess

# Add project root to path (same pattern as rag_pipeline.py)
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


async def clear_semantic_cache():
    """Clear all semantic caches."""
    # Check if backend is running in Docker
    container_name = find_backend_container()
    
    if container_name:
        logger.info(f"🔍 Backend container detected: {container_name}")
        logger.info("   Executing clear command inside container...")
        print("")
        
        try:
            # Execute the clear command inside the container
            # Use python3 to run the script inside the container
            result = subprocess.run(
                [
                    "docker", "exec", container_name,
                    "python3", "-c",
                    """
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

async def clear():
    USE_REDIS_CACHE = os.getenv('USE_REDIS_CACHE', 'false').lower() == 'true'
    cleared = []
    
    # Clear Redis Stack vector cache
    if USE_REDIS_CACHE:
        try:
            from rag_pipeline import _get_redis_vector_cache
            cache = _get_redis_vector_cache()
            if cache:
                stats = await cache.stats()
                entries = stats.get('entries', 0)
                await cache.clear()
                cleared.append(f'Redis Stack vector cache ({entries} entries)')
                print(f'✅ Cleared Redis Stack vector cache ({entries} entries)')
        except Exception as e:
            print(f'⚠️  Error clearing Redis cache: {e}')
    
    # Clear legacy semantic cache
    if not USE_REDIS_CACHE:
        try:
            from api.v1.sync.payload import _global_rag_pipeline
            if _global_rag_pipeline and hasattr(_global_rag_pipeline, 'semantic_cache') and _global_rag_pipeline.semantic_cache:
                stats = _global_rag_pipeline.semantic_cache.stats()
                entries = stats.get('size', 0)
                _global_rag_pipeline.semantic_cache.clear()
                cleared.append(f'Legacy semantic cache ({entries} entries)')
                print(f'✅ Cleared legacy semantic cache ({entries} entries)')
            else:
                print('ℹ️  Legacy semantic cache not available or not initialized')
        except Exception as e:
            print(f'⚠️  Error clearing legacy cache: {e}')
    
    if not cleared:
        print('ℹ️  No semantic cache was active to clear')
    return cleared

asyncio.run(clear())
"""
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Print output from container
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            if result.returncode == 0:
                print("\n✅ Semantic cache cleared successfully via Docker container!")
                return
            else:
                logger.warning(f"⚠️  Command exited with code {result.returncode}")
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout waiting for container command to complete")
        except Exception as e:
            logger.warning(f"⚠️  Error executing command in container: {e}")
        
        print("")
        logger.info("   Falling back to API endpoint method...")
        print("   You can also use: curl -X POST http://localhost:8000/api/v1/admin/cache/semantic/clear \\")
        print("                         -H 'Authorization: Bearer YOUR_ADMIN_TOKEN'")
        print("")
    
    # Fallback: Try to access cache directly (when running locally or if Docker method failed)
    USE_REDIS_CACHE = os.getenv("USE_REDIS_CACHE", "false").lower() == "true"
    
    # Change to backend directory and add it to path for relative imports
    backend_dir = os.path.join(project_root, 'backend')
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    
    cleared_caches = []
    
    # Clear Redis Stack vector cache (if enabled)
    if USE_REDIS_CACHE:
        try:
            # Import using same style as rag_pipeline.py (relative imports from backend/)
            from rag_pipeline import _get_redis_vector_cache
            redis_cache = _get_redis_vector_cache()
            if redis_cache:
                stats_before = await redis_cache.stats()
                entries_before = stats_before.get("entries", 0)
                cleared = await redis_cache.clear()
                if cleared:
                    cleared_caches.append(f"Redis Stack vector cache ({entries_before} entries)")
                    logger.info(f"✅ Cleared Redis Stack vector cache ({entries_before} entries)")
                else:
                    logger.warning("⚠️  Failed to clear Redis Stack vector cache")
            else:
                logger.info("ℹ️  Redis Stack vector cache not available")
        except Exception as e:
            logger.warning(f"⚠️  Error clearing Redis vector cache: {e}")
    else:
        logger.info("ℹ️  Redis Stack vector cache not enabled (USE_REDIS_CACHE=false)")
    
    # Clear legacy semantic cache (if enabled)
    # Note: Legacy semantic cache is in-memory and only exists in a running RAGPipeline instance
    # So we can only clear it if the backend is running (via global instance) or if we can create an instance
    if not USE_REDIS_CACHE:
        try:
            # Try to access via global RAG pipeline instance first (if backend is running)
            # Use absolute import style that matches rag_pipeline.py
            global_pipeline_cleared = False
            try:
                from backend.api.v1.sync.payload import _global_rag_pipeline
                if _global_rag_pipeline and hasattr(_global_rag_pipeline, "semantic_cache") and _global_rag_pipeline.semantic_cache:
                    stats_before = _global_rag_pipeline.semantic_cache.stats()
                    entries_before = stats_before.get("size", 0)
                    _global_rag_pipeline.semantic_cache.clear()
                    cleared_caches.append(f"Legacy semantic cache ({entries_before} entries)")
                    logger.info(f"✅ Cleared legacy semantic cache ({entries_before} entries)")
                    global_pipeline_cleared = True
            except ImportError:
                # Try relative import (when running from backend directory)
                try:
                    from api.v1.sync.payload import _global_rag_pipeline
                    if _global_rag_pipeline and hasattr(_global_rag_pipeline, "semantic_cache") and _global_rag_pipeline.semantic_cache:
                        stats_before = _global_rag_pipeline.semantic_cache.stats()
                        entries_before = stats_before.get("size", 0)
                        _global_rag_pipeline.semantic_cache.clear()
                        cleared_caches.append(f"Legacy semantic cache ({entries_before} entries)")
                        logger.info(f"✅ Cleared legacy semantic cache ({entries_before} entries)")
                        global_pipeline_cleared = True
                except ImportError:
                    pass  # Will try creating instance below
            
            # Only try creating instance if global pipeline didn't work
            if not global_pipeline_cleared:
                # If global pipeline not available, try creating a temporary RAGPipeline instance
                # This only works if all dependencies are installed and environment is configured
                try:
                    from rag_pipeline import RAGPipeline
                    logger.info("ℹ️  Global RAG pipeline not available, attempting to create temporary instance...")
                    # Create a minimal instance just to access semantic_cache
                    temp_pipeline = RAGPipeline()
                    if temp_pipeline.semantic_cache:
                        stats_before = temp_pipeline.semantic_cache.stats()
                        entries_before = stats_before.get("size", 0)
                        temp_pipeline.semantic_cache.clear()
                        cleared_caches.append(f"Legacy semantic cache ({entries_before} entries)")
                        logger.info(f"✅ Cleared legacy semantic cache ({entries_before} entries)")
                    else:
                        logger.info("ℹ️  Legacy semantic cache not initialized (Redis or Infinity embeddings enabled)")
                except ImportError as import_err:
                    logger.info(f"ℹ️  Cannot create RAGPipeline instance (missing dependencies).")
                    logger.info("   Note: Legacy semantic cache is in-memory and only exists when the backend is running.")
                    logger.info("   To clear it, use the admin API endpoint when the backend is running:")
                    logger.info("   curl -X POST http://localhost:8000/api/v1/admin/cache/semantic/clear \\")
                    logger.info("        -H 'Authorization: Bearer YOUR_ADMIN_TOKEN'")
                except Exception as create_err:
                    logger.warning(f"⚠️  Failed to create RAGPipeline instance: {create_err}")
                    logger.info("   Tip: Use the admin API endpoint when the backend is running to clear the cache.")
        except Exception as e:
            logger.warning(f"⚠️  Error clearing legacy semantic cache: {e}")
    else:
        logger.info("ℹ️  Legacy semantic cache not enabled (Redis Stack cache is active)")
    
    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    if cleared_caches:
        for cache_info in cleared_caches:
            print(f"  • {cache_info}")
        print("="*60)
        print("\n✅ Semantic cache cleared successfully!")
    else:
        print("  • No semantic cache was active to clear")
        print("="*60)
        print("\nℹ️  No cache to clear")


if __name__ == "__main__":
    print("🧹 Clearing semantic cache...")
    print("")
    asyncio.run(clear_semantic_cache())

