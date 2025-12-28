"""
Basset Hound Middleware Module

This module provides middleware components for the Basset Hound application,
including WebSocket authentication and request processing.

Phase 14: Enterprise Features
"""

from .auth import (
    WebSocketAuthenticator,
    WebSocketAuthResult,
    WebSocketAuthError,
    authenticate_websocket,
    extract_api_key_from_query,
    extract_api_key_from_header,
    extract_jwt_from_query,
    extract_jwt_from_header,
)

__all__ = [
    "WebSocketAuthenticator",
    "WebSocketAuthResult",
    "WebSocketAuthError",
    "authenticate_websocket",
    "extract_api_key_from_query",
    "extract_api_key_from_header",
    "extract_jwt_from_query",
    "extract_jwt_from_header",
]
