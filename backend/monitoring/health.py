"""
Health check module for monitoring service dependencies and status.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from backend.data_ingestion.vector_store_manager import VectorStoreManager

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthChecker:
    """
    Comprehensive health checker for all service dependencies.
    """
    
    def __init__(self):
        self.vector_store_manager = None
        self._last_check_time = None
        self._last_check_result = None
    
    def check_vector_store(self) -> Dict[str, Any]:
        """Check vector store health and return status."""
        try:
            if self.vector_store_manager is None:
                self.vector_store_manager = VectorStoreManager()
            
            start_time = time.time()
            mongodb_available = self.vector_store_manager.mongodb_available
            
            # Get document counts
            total_count = 0
            published_count = 0
            draft_count = 0
            
            if mongodb_available:
                total_count = self.vector_store_manager.collection.count_documents({})
                published_count = self.vector_store_manager.collection.count_documents({
                    "metadata.status": "published"
                })
                draft_count = self.vector_store_manager.collection.count_documents({
                    "metadata.status": "draft"
                })
            
            check_duration = time.time() - start_time
            
            return {
                "status": HealthStatus.HEALTHY if mongodb_available else HealthStatus.UNHEALTHY,
                "mongodb_available": mongodb_available,
                "document_counts": {
                    "total": total_count,
                    "published": published_count,
                    "draft": draft_count,
                },
                "check_duration_seconds": check_duration,
            }
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}", exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "mongodb_available": False,
            }
    
    def check_llm_connection(self) -> Dict[str, Any]:
        """Check LLM API connection health."""
        try:
            import os
            google_api_key = os.getenv("GOOGLE_API_KEY")
            
            if not google_api_key:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "error": "GOOGLE_API_KEY not configured",
                }
            
            # Simple check - verify key is present and not empty
            if len(google_api_key) < 10:  # Basic validation
                return {
                    "status": HealthStatus.DEGRADED,
                    "error": "GOOGLE_API_KEY appears invalid",
                }
            
            return {
                "status": HealthStatus.HEALTHY,
                "api_key_configured": True,
            }
        except Exception as e:
            logger.error(f"LLM health check failed: {e}", exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
            }
    
    def check_cache(self) -> Dict[str, Any]:
        """Check cache health and statistics."""
        try:
            from backend.cache_utils import query_cache
            
            cache_stats = query_cache.stats()
            
            return {
                "status": HealthStatus.HEALTHY,
                "cache_size": cache_stats.get("size", 0),
                "cache_max_size": cache_stats.get("max_size", 1000),
                "cache_utilization": cache_stats.get("size", 0) / cache_stats.get("max_size", 1000),
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}", exc_info=True)
            return {
                "status": HealthStatus.DEGRADED,
                "error": str(e),
            }
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all services.
        
        Returns:
            Dictionary with health status of all components
        """
        start_time = time.time()
        
        vector_store_health = self.check_vector_store()
        llm_health = self.check_llm_connection()
        cache_health = self.check_cache()
        
        # Determine overall health status
        all_healthy = all(
            service["status"] == HealthStatus.HEALTHY
            for service in [vector_store_health, llm_health]
        )
        
        any_unhealthy = any(
            service["status"] == HealthStatus.UNHEALTHY
            for service in [vector_store_health, llm_health]
        )
        
        if any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        elif not all_healthy:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        total_duration = time.time() - start_time
        
        result = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_seconds": total_duration,
            "services": {
                "vector_store": vector_store_health,
                "llm": llm_health,
                "cache": cache_health,
            },
        }
        
        self._last_check_time = datetime.utcnow()
        self._last_check_result = result
        
        return result
    
    def get_liveness(self) -> Dict[str, Any]:
        """
        Simple liveness check - returns healthy if the service is running.
        """
        return {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_readiness(self) -> Dict[str, Any]:
        """
        Readiness check - returns healthy if the service is ready to accept traffic.
        """
        # Quick check of critical dependencies
        vector_store_health = self.check_vector_store()
        llm_health = self.check_llm_connection()
        
        ready = (
            vector_store_health["status"] != HealthStatus.UNHEALTHY
            and llm_health["status"] != HealthStatus.UNHEALTHY
        )
        
        return {
            "status": HealthStatus.HEALTHY.value if ready else HealthStatus.UNHEALTHY.value,
            "timestamp": datetime.utcnow().isoformat(),
            "ready": ready,
        }


# Global health checker instance
_health_checker = HealthChecker()


def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status."""
    return _health_checker.get_comprehensive_health()


def get_liveness() -> Dict[str, Any]:
    """Get liveness status."""
    return _health_checker.get_liveness()


def get_readiness() -> Dict[str, Any]:
    """Get readiness status."""
    return _health_checker.get_readiness()

