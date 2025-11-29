"""
Tests for HSTS header in security headers middleware.
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from backend.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    app = Mock()
    return app


@pytest.fixture
def middleware_production(mock_app):
    """Create middleware instance in production mode."""
    with patch.dict(os.environ, {"NODE_ENV": "production"}):
        middleware = SecurityHeadersMiddleware(mock_app)
        yield middleware


@pytest.fixture
def middleware_development(mock_app):
    """Create middleware instance in development mode."""
    with patch.dict(os.environ, {"NODE_ENV": "development"}):
        middleware = SecurityHeadersMiddleware(mock_app)
        yield middleware


@pytest.mark.asyncio
async def test_hsts_header_in_production(middleware_production):
    """Test that HSTS header is added in production."""
    # Create a mock request
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    
    # Create a mock response
    mock_response = Mock()
    mock_response.headers = {}
    
    # Mock call_next
    call_next = AsyncMock(return_value=mock_response)
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should add HSTS header
    assert "Strict-Transport-Security" in response.headers
    hsts_value = response.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts_value
    assert "includeSubDomains" in hsts_value
    
    # Should also add other security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers


@pytest.mark.asyncio
async def test_no_hsts_header_in_development(middleware_development):
    """Test that HSTS header is NOT added in development."""
    # Create a mock request
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    
    # Create a mock response
    mock_response = Mock()
    mock_response.headers = {}
    
    # Mock call_next
    call_next = AsyncMock(return_value=mock_response)
    
    # Call middleware
    response = await middleware_development.dispatch(request, call_next)
    
    # Should NOT add HSTS header in development
    assert "Strict-Transport-Security" not in response.headers
    
    # Should still add other security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers

