"""
Global exception handler middleware for sanitizing error messages and preventing information disclosure.
"""

import logging
import os
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Determine if we're in development mode
IS_DEVELOPMENT = os.getenv("NODE_ENV", "development") == "development"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message to prevent information disclosure.
    
    In production, returns generic error messages.
    In development/debug mode, returns detailed error messages.
    
    Args:
        error: The exception that occurred
    
    Returns:
        Sanitized error message string
    """
    if IS_DEVELOPMENT or DEBUG_MODE:
        # In development, provide more details for debugging
        return str(error)
    
    # In production, return generic error messages
    error_type = type(error).__name__
    
    # Handle specific error types with appropriate generic messages
    if "Connection" in error_type or "connection" in str(error).lower():
        return "Database connection error. Please try again later."
    elif "Authentication" in error_type or "auth" in str(error).lower():
        return "Authentication error occurred."
    elif "Permission" in error_type or "permission" in str(error).lower():
        return "Permission denied."
    elif "Validation" in error_type:
        return "Invalid input provided."
    elif "Timeout" in error_type:
        return "Request timeout. Please try again."
    else:
        return "An error occurred processing your request. Please try again."


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for FastAPI application.
    
    Args:
        request: FastAPI Request object
        exc: The exception that was raised
    
    Returns:
        JSONResponse with sanitized error message
    """
    # Log the full error with details server-side
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Handle HTTPException (includes our custom exceptions)
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail.get("error") if isinstance(exc.detail, dict) else "http_error",
                "message": exc.detail.get("message") if isinstance(exc.detail, dict) else sanitize_error_message(exc)
            }
        )
    
    # Handle validation errors
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Invalid request data provided"
            }
        )
    
    # Handle all other exceptions
    sanitized_message = sanitize_error_message(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": sanitized_message
        }
    )


class ErrorSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and sanitize exceptions before they reach the client.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch request and catch any exceptions, sanitizing error messages.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware/handler in the chain
        
        Returns:
            Response object
        """
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Let the exception handler process it
            return await exception_handler(request, exc)

