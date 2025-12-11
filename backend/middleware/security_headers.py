"""
FastAPI middleware for adding security headers to all responses.
"""

import os
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.
    
    Adds the following headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (production only)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    - Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
    """
    
    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        # Check if we're in production
        self.is_production = os.getenv("NODE_ENV") == "production" or os.getenv("ENVIRONMENT") == "production"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip security headers for excluded paths if needed
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Relaxed CSP for API functionality and Swagger UI
        # - default-src 'self': Allow loading resources from same origin
        # - frame-ancestors 'none': Prevent clickjacking (same as X-Frame-Options: DENY)
        # - script-src 'self' 'unsafe-inline': Allow inline scripts (needed for Swagger UI)
        # - style-src 'self' 'unsafe-inline': Allow inline styles (needed for Swagger UI)
        # - Removed sandbox: Allow JS execution
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        # Only add HSTS in production
        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
