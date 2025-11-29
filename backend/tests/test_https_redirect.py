"""
Tests for HTTPS redirect middleware.
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from fastapi.responses import RedirectResponse
from backend.middleware.https_redirect import HTTPSRedirectMiddleware


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    app = Mock()
    return app


@pytest.fixture
def middleware_production(mock_app):
    """Create middleware instance in production mode."""
    with patch.dict(os.environ, {"NODE_ENV": "production"}):
        middleware = HTTPSRedirectMiddleware(mock_app)
        yield middleware


@pytest.fixture
def middleware_development(mock_app):
    """Create middleware instance in development mode."""
    with patch.dict(os.environ, {"NODE_ENV": "development"}):
        middleware = HTTPSRedirectMiddleware(mock_app)
        yield middleware


@pytest.mark.asyncio
async def test_https_redirect_in_production_with_http_header(middleware_production):
    """Test that HTTP requests are redirected to HTTPS in production."""
    # Create a mock request with X-Forwarded-Proto: http
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    request.url.scheme = "http"
    request.url.hostname = "api.lite.space"
    request.url.query = ""
    request.headers = {"X-Forwarded-Proto": "http", "Host": "api.lite.space"}
    
    # Mock call_next
    call_next = AsyncMock(return_value=Mock())
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should return a redirect
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 301
    assert response.headers["location"] == "https://api.lite.space/api/v1/chat/stream"
    
    # Should not call next
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_no_redirect_in_development(middleware_development):
    """Test that no redirect happens in development mode."""
    # Create a mock request with HTTP
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    request.url.scheme = "http"
    request.headers = {"X-Forwarded-Proto": "http"}
    
    # Mock call_next
    mock_response = Mock()
    call_next = AsyncMock(return_value=mock_response)
    
    # Call middleware
    response = await middleware_development.dispatch(request, call_next)
    
    # Should not redirect, just pass through
    assert response == mock_response
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_no_redirect_for_https_in_production(middleware_production):
    """Test that HTTPS requests are not redirected in production."""
    # Create a mock request with HTTPS
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    request.url.scheme = "https"
    request.headers = {"X-Forwarded-Proto": "https"}
    
    # Mock call_next
    mock_response = Mock()
    call_next = AsyncMock(return_value=mock_response)
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should not redirect
    assert response == mock_response
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_no_redirect_for_health_endpoints(middleware_production):
    """Test that health check endpoints are not redirected."""
    # Create a mock request for health endpoint
    request = Mock(spec=Request)
    request.url.path = "/health"
    request.url.scheme = "http"
    request.headers = {"X-Forwarded-Proto": "http"}
    
    # Mock call_next
    mock_response = Mock()
    call_next = AsyncMock(return_value=mock_response)
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should not redirect health checks
    assert response == mock_response
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_redirect_preserves_query_parameters(middleware_production):
    """Test that query parameters are preserved in redirect."""
    # Create a mock request with query parameters
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    request.url.scheme = "http"
    request.url.query = "param1=value1&param2=value2"
    request.url.hostname = "api.lite.space"
    request.headers = {"X-Forwarded-Proto": "http", "Host": "api.lite.space"}
    
    # Mock call_next
    call_next = AsyncMock(return_value=Mock())
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should redirect with query parameters
    assert isinstance(response, RedirectResponse)
    assert "param1=value1&param2=value2" in response.headers["location"]


@pytest.mark.asyncio
async def test_redirect_uses_forwarded_host(middleware_production):
    """Test that redirect uses X-Forwarded-Host header if available."""
    # Create a mock request with X-Forwarded-Host
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/stream"
    request.url.scheme = "http"
    request.url.query = ""
    request.url.hostname = "internal-host"
    request.headers = {
        "X-Forwarded-Proto": "http",
        "X-Forwarded-Host": "api.lite.space",
        "Host": "internal-host"
    }
    
    # Mock call_next
    call_next = AsyncMock(return_value=Mock())
    
    # Call middleware
    response = await middleware_production.dispatch(request, call_next)
    
    # Should redirect to X-Forwarded-Host
    assert isinstance(response, RedirectResponse)
    assert "api.lite.space" in response.headers["location"]
    assert "internal-host" not in response.headers["location"]

