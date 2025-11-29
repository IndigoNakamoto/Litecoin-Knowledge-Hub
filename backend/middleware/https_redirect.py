"""
FastAPI middleware for redirecting HTTP requests to HTTPS in production.
This provides defense-in-depth when behind a reverse proxy (e.g., Cloudflare Tunnel).
"""

import os
import logging
from typing import Callable
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS in production.
    
    This middleware checks the X-Forwarded-Proto header (set by reverse proxies
    like Cloudflare) to detect HTTP requests and redirect them to HTTPS.
    
    Features:
    - Only redirects in production environment
    - Skips redirect for health check endpoints
    - Skips redirect for internal Docker network requests
    - Preserves query parameters and path
    """
    
    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/", "/health", "/health/live", "/health/ready", "/metrics"]
        # Check if we're in production
        self.is_production = (
            os.getenv("NODE_ENV") == "production" or 
            os.getenv("ENVIRONMENT") == "production"
        )
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only redirect in production
        if not self.is_production:
            return await call_next(request)
        
        # Skip redirect for excluded paths (health checks, metrics)
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Check if request is HTTP (via X-Forwarded-Proto header from reverse proxy)
        # Cloudflare Tunnel sets this header
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
        
        # Also check the scheme from the request URL (for direct connections)
        request_scheme = request.url.scheme.lower()
        
        # If either indicates HTTP, redirect to HTTPS
        if forwarded_proto == "http" or request_scheme == "http":
            # Build HTTPS URL
            # Get the host from X-Forwarded-Host (set by Cloudflare) or use request host
            host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.url.hostname
            
            # Construct HTTPS URL
            https_url = f"https://{host}{request.url.path}"
            
            # Preserve query parameters
            if request.url.query:
                https_url += f"?{request.url.query}"
            
            logger.info(f"Redirecting HTTP request to HTTPS: {request.url.path}")
            return RedirectResponse(url=https_url, status_code=301)
        
        # Request is already HTTPS, proceed normally
        return await call_next(request)

