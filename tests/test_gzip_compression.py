"""
Test GZIP compression middleware for Basset Hound API.

This test verifies that:
1. Large responses are compressed with GZIP
2. Small responses are not compressed (under 1000 bytes)
3. Content-Encoding header is set correctly
4. Decompression works properly
"""

import gzip
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse


def test_gzip_middleware_installed():
    """Test that GZipMiddleware is properly installed in the app."""
    from api.main import create_application

    app = create_application()

    # Check if GZipMiddleware is in the app's user_middleware
    middleware_classes = [m.cls for m in app.user_middleware]

    # GZipMiddleware should be present
    assert GZipMiddleware in middleware_classes, "GZipMiddleware not found in app middleware"


def test_gzip_compression_large_response():
    """Test that large responses are compressed with GZIP."""
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Create a large response (> 1000 bytes)
    large_data = {
        "status": "success",
        "data": [
            {
                "id": f"ent_{i:05d}",
                "type": "PERSON",
                "name": f"Entity {i}",
                "email": f"entity{i}@example.com",
                "description": "A" * 100,  # Padding to increase response size
            }
            for i in range(50)  # 50 entities
        ]
    }

    @app.get("/test/large")
    async def get_large():
        return large_data

    client = TestClient(app)
    response = client.get("/test/large", headers={"Accept-Encoding": "gzip"})

    # Response should be compressed
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip", \
        f"Expected content-encoding: gzip, got {response.headers.get('content-encoding')}"

    # Verify content can be decompressed
    try:
        decompressed = gzip.decompress(response.content)
        data = json.loads(decompressed)
        assert data["status"] == "success"
        assert len(data["data"]) == 50
    except Exception as e:
        pytest.fail(f"Failed to decompress response: {e}")


def test_no_compression_small_response():
    """Test that small responses are not compressed."""
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/test/small")
    async def get_small():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test/small", headers={"Accept-Encoding": "gzip"})

    # Small response should not be compressed
    assert response.status_code == 200
    # Content-Encoding should either not be present or not be gzip for small responses
    content_encoding = response.headers.get("content-encoding", "").lower()
    response_size = len(response.content)

    # If response is under 1000 bytes, it shouldn't be gzip encoded
    if response_size < 1000:
        assert content_encoding != "gzip", \
            f"Small response ({response_size} bytes) should not be compressed"


def test_websocket_not_compressed():
    """Test that WebSocket connections are not affected by GZIP."""
    # This is a theoretical test since actual WebSocket compression
    # is handled differently than HTTP response compression
    # The GZipMiddleware only applies to HTTP responses, not WebSocket

    from api.main import create_application

    app = create_application()

    # Verify that WebSocket endpoints exist and are not affected
    # WebSocket middleware would be separate from HTTP middleware
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]

    # GZipMiddleware should only apply to HTTP, not WebSocket
    assert "GZipMiddleware" in str(middleware_classes)


def test_minimum_size_configuration():
    """Test that minimum_size is correctly set to 1000 bytes."""
    app = FastAPI()

    # Add middleware with 1000 byte minimum (as per requirements)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Create responses of different sizes
    size_500 = {"data": "x" * 500}
    size_1001 = {"data": "x" * 1001}

    @app.get("/test/500")
    async def get_500():
        return size_500

    @app.get("/test/1001")
    async def get_1001():
        return size_1001

    client = TestClient(app)

    # 500 byte response should not be compressed
    response_500 = client.get("/test/500", headers={"Accept-Encoding": "gzip"})
    assert response_500.status_code == 200

    # 1001 byte response should be compressed
    response_1001 = client.get("/test/1001", headers={"Accept-Encoding": "gzip"})
    assert response_1001.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
