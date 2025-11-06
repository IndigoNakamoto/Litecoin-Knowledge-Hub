"""
FastAPI middleware for collecting metrics and observability data.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from .metrics import (
    request_count_total,
    request_duration_seconds,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics for Prometheus.
    
    Tracks:
    - Request count by method, endpoint, and status code
    - Request duration by method, endpoint, and status code
    """
    
    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/metrics",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract endpoint (simplified path without query params)
        endpoint = request.url.path
        method = request.method
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            logger.error(f"Request failed: {e}", exc_info=True)
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        request_count_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()
        
        request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).observe(duration)
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.
    """
    
    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
        self.logger = logging.getLogger("http")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        self.logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "query_params": dict(request.query_params),
            },
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                f"Response: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                    "client_ip": client_ip,
                },
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": duration,
                    "error": str(e),
                    "client_ip": client_ip,
                },
                exc_info=True,
            )
            raise

