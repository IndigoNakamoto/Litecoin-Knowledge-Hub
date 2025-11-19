"""
Monitoring and observability module for Litecoin Knowledge Hub.

This module provides:
- Prometheus metrics for application monitoring
- Structured logging
- Health check endpoints
- LLM observability integration
- RAG pipeline metrics
"""

from .metrics import (
    setup_metrics,
    get_metrics_registry,
    generate_metrics_response,
    request_duration_seconds,
    request_count_total,
    rag_query_duration_seconds,
    rag_cache_hits_total,
    rag_cache_misses_total,
    suggested_question_cache_hits_total,
    suggested_question_cache_misses_total,
    suggested_question_cache_lookup_duration_seconds,
    suggested_question_cache_size,
    suggested_question_cache_refresh_duration_seconds,
    suggested_question_cache_refresh_errors_total,
    llm_tokens_total,
    llm_requests_total,
    llm_cost_usd_total,
    vector_store_documents_total,
    webhook_processing_duration_seconds,
    webhook_processing_total,
)

from .middleware import MetricsMiddleware
from .health import HealthChecker, get_health_status, get_liveness, get_readiness
from .logging_config import setup_logging, get_logger

__all__ = [
    "setup_metrics",
    "get_metrics_registry",
    "generate_metrics_response",
    "request_duration_seconds",
    "request_count_total",
    "rag_query_duration_seconds",
    "rag_cache_hits_total",
    "rag_cache_misses_total",
    "suggested_question_cache_hits_total",
    "suggested_question_cache_misses_total",
    "suggested_question_cache_lookup_duration_seconds",
    "suggested_question_cache_size",
    "suggested_question_cache_refresh_duration_seconds",
    "suggested_question_cache_refresh_errors_total",
    "llm_tokens_total",
    "llm_requests_total",
    "llm_cost_usd_total",
    "vector_store_documents_total",
    "webhook_processing_duration_seconds",
    "webhook_processing_total",
    "MetricsMiddleware",
    "HealthChecker",
    "get_health_status",
    "get_liveness",
    "get_readiness",
    "setup_logging",
    "get_logger",
]

