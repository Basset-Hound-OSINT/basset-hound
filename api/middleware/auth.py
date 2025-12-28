"""
WebSocket Authentication Middleware

This module provides authentication functionality for WebSocket connections,
supporting both API key and JWT token authentication methods.

Features:
- API key authentication via query parameter or header
- JWT token authentication via query parameter or header
- Connection validation before accepting WebSocket
- Authenticated user info storage with connection metadata

Phase 14: Enterprise Features
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union

from fastapi import WebSocket, status

from api.auth.jwt import verify_token, TokenData, TokenValidationError
from api.auth.api_key import validate_api_key, APIKey
from api.auth.dependencies import User, AUTH_ENABLED

logger = logging.getLogger(__name__)


# Configuration
WS_AUTH_ENABLED = os.getenv("WS_AUTH_ENABLED", "true").lower() in ("true", "1", "yes")
API_KEY_QUERY_PARAM = os.getenv("WS_API_KEY_QUERY_PARAM", "api_key")
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
JWT_QUERY_PARAM = os.getenv("WS_JWT_QUERY_PARAM", "token")
JWT_HEADER_NAME = os.getenv("WS_JWT_HEADER_NAME", "Authorization")


class AuthMethod(str, Enum):
    """Authentication methods supported for WebSocket connections."""
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    DISABLED = "disabled"


class WebSocketAuthError(Exception):
    """
    Custom exception for WebSocket authentication errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        close_code: WebSocket close code to use when rejecting connection
    """
    def __init__(
        self,
        message: str,
        code: str = "authentication_error",
        close_code: int = status.WS_1008_POLICY_VIOLATION
    ):
        self.message = message
        self.code = code
        self.close_code = close_code
        super().__init__(self.message)


@dataclass
class WebSocketAuthResult:
    """
    Result of WebSocket authentication attempt.

    Attributes:
        authenticated: Whether authentication was successful
        user: The authenticated user (if successful)
        auth_method: The authentication method used
        error: Error message if authentication failed
        error_code: Error code if authentication failed
        metadata: Additional metadata about the authentication
    """
    authenticated: bool
    user: Optional[User] = None
    auth_method: AuthMethod = AuthMethod.NONE
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_connection_metadata(self) -> Dict[str, Any]:
        """
        Convert auth result to metadata suitable for storing with connection.

        Returns:
            Dictionary of authentication metadata for connection
        """
        result = {
            "authenticated": self.authenticated,
            "auth_method": self.auth_method.value,
            "authenticated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.user:
            result.update({
                "user_id": self.user.user_id,
                "username": self.user.username,
                "scopes": self.user.scopes,
                "api_key_id": self.user.api_key_id,
            })

        result.update(self.metadata)
        return result


def extract_api_key_from_query(websocket: WebSocket) -> Optional[str]:
    """
    Extract API key from WebSocket query parameters.

    Args:
        websocket: The WebSocket connection

    Returns:
        The API key if found, None otherwise
    """
    return websocket.query_params.get(API_KEY_QUERY_PARAM)


def extract_api_key_from_header(websocket: WebSocket) -> Optional[str]:
    """
    Extract API key from WebSocket headers.

    Args:
        websocket: The WebSocket connection

    Returns:
        The API key if found, None otherwise
    """
    return websocket.headers.get(API_KEY_HEADER_NAME.lower())


def extract_jwt_from_query(websocket: WebSocket) -> Optional[str]:
    """
    Extract JWT token from WebSocket query parameters.

    Args:
        websocket: The WebSocket connection

    Returns:
        The JWT token if found, None otherwise
    """
    return websocket.query_params.get(JWT_QUERY_PARAM)


def extract_jwt_from_header(websocket: WebSocket) -> Optional[str]:
    """
    Extract JWT token from WebSocket Authorization header.

    Supports both "Bearer <token>" and raw token formats.

    Args:
        websocket: The WebSocket connection

    Returns:
        The JWT token if found, None otherwise
    """
    auth_header = websocket.headers.get(JWT_HEADER_NAME.lower())
    if not auth_header:
        return None

    # Handle "Bearer <token>" format
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    # Handle raw token format
    return auth_header.strip()


def validate_api_key_auth(api_key: str) -> WebSocketAuthResult:
    """
    Validate an API key and return authentication result.

    Args:
        api_key: The API key to validate

    Returns:
        WebSocketAuthResult with authentication status
    """
    validated_key = validate_api_key(api_key)

    if not validated_key:
        logger.warning("WebSocket connection rejected: invalid API key")
        return WebSocketAuthResult(
            authenticated=False,
            auth_method=AuthMethod.API_KEY,
            error="Invalid or expired API key",
            error_code="invalid_api_key",
        )

    user = User.from_api_key(validated_key)
    logger.info(f"WebSocket authenticated via API key: {validated_key.key_prefix}...")

    return WebSocketAuthResult(
        authenticated=True,
        user=user,
        auth_method=AuthMethod.API_KEY,
        metadata={
            "api_key_prefix": validated_key.key_prefix,
            "api_key_name": validated_key.name,
        },
    )


def validate_jwt_auth(token: str) -> WebSocketAuthResult:
    """
    Validate a JWT token and return authentication result.

    Args:
        token: The JWT token to validate

    Returns:
        WebSocketAuthResult with authentication status
    """
    try:
        token_data = verify_token(token)
        user = User.from_token(token_data)

        logger.info(f"WebSocket authenticated via JWT for user: {user.username}")

        return WebSocketAuthResult(
            authenticated=True,
            user=user,
            auth_method=AuthMethod.JWT,
            metadata={
                "token_type": "access",
            },
        )
    except TokenValidationError as e:
        logger.warning(f"WebSocket connection rejected: {e.message}")
        return WebSocketAuthResult(
            authenticated=False,
            auth_method=AuthMethod.JWT,
            error=e.message,
            error_code=e.code,
        )


class WebSocketAuthenticator:
    """
    WebSocket authenticator that supports multiple authentication methods.

    This class provides a unified interface for authenticating WebSocket
    connections using either API keys or JWT tokens.

    Features:
    - Configurable authentication requirements
    - Support for credentials in query params or headers
    - Detailed authentication results for connection metadata
    - Graceful handling of disabled authentication

    Example usage:
        authenticator = WebSocketAuthenticator(require_auth=True)
        result = await authenticator.authenticate(websocket)

        if not result.authenticated:
            await websocket.close(code=1008)
            return

        # Use result.user for authenticated user info
    """

    def __init__(
        self,
        require_auth: bool = True,
        allow_api_key: bool = True,
        allow_jwt: bool = True,
        allow_anonymous: bool = False,
    ):
        """
        Initialize the WebSocket authenticator.

        Args:
            require_auth: Whether authentication is required
            allow_api_key: Whether to allow API key authentication
            allow_jwt: Whether to allow JWT authentication
            allow_anonymous: Whether to allow anonymous connections when auth not required
        """
        self.require_auth = require_auth
        self.allow_api_key = allow_api_key
        self.allow_jwt = allow_jwt
        self.allow_anonymous = allow_anonymous

    async def authenticate(self, websocket: WebSocket) -> WebSocketAuthResult:
        """
        Authenticate a WebSocket connection.

        Attempts authentication in the following order:
        1. JWT token (query param, then header)
        2. API key (query param, then header)
        3. Anonymous (if allowed)

        Args:
            websocket: The WebSocket connection to authenticate

        Returns:
            WebSocketAuthResult with authentication status and user info
        """
        # Check if authentication is globally disabled
        if not WS_AUTH_ENABLED or not AUTH_ENABLED:
            logger.debug("WebSocket authentication disabled, allowing connection")
            return WebSocketAuthResult(
                authenticated=True,
                user=User(
                    user_id="dev-user",
                    username="developer",
                    scopes=["*"],
                    auth_type="disabled",
                ),
                auth_method=AuthMethod.DISABLED,
            )

        # Try JWT authentication
        if self.allow_jwt:
            jwt_token = extract_jwt_from_query(websocket) or extract_jwt_from_header(websocket)
            if jwt_token:
                result = validate_jwt_auth(jwt_token)
                if result.authenticated:
                    return result
                # If JWT was provided but invalid, don't try other methods
                if self.require_auth:
                    return result

        # Try API key authentication
        if self.allow_api_key:
            api_key = extract_api_key_from_query(websocket) or extract_api_key_from_header(websocket)
            if api_key:
                result = validate_api_key_auth(api_key)
                if result.authenticated:
                    return result
                # If API key was provided but invalid, don't try other methods
                if self.require_auth:
                    return result

        # No credentials provided
        if self.require_auth:
            logger.warning("WebSocket connection rejected: no credentials provided")
            return WebSocketAuthResult(
                authenticated=False,
                auth_method=AuthMethod.NONE,
                error="Authentication required. Provide API key or JWT token.",
                error_code="missing_credentials",
            )

        # Allow anonymous connection
        if self.allow_anonymous:
            logger.debug("WebSocket connection accepted: anonymous")
            return WebSocketAuthResult(
                authenticated=True,
                user=User.anonymous(),
                auth_method=AuthMethod.NONE,
            )

        return WebSocketAuthResult(
            authenticated=False,
            auth_method=AuthMethod.NONE,
            error="Authentication required",
            error_code="authentication_required",
        )

    async def authenticate_and_accept(
        self,
        websocket: WebSocket,
    ) -> Optional[WebSocketAuthResult]:
        """
        Authenticate a WebSocket connection and accept or reject it.

        This is a convenience method that combines authentication with
        connection acceptance/rejection.

        Args:
            websocket: The WebSocket connection to authenticate

        Returns:
            WebSocketAuthResult if authentication succeeded, None if rejected
        """
        result = await self.authenticate(websocket)

        if not result.authenticated:
            # Reject the connection
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=result.error or "Authentication failed"
            )
            return None

        return result


async def authenticate_websocket(
    websocket: WebSocket,
    require_auth: bool = True,
    allow_api_key: bool = True,
    allow_jwt: bool = True,
) -> WebSocketAuthResult:
    """
    Convenience function to authenticate a WebSocket connection.

    Args:
        websocket: The WebSocket connection to authenticate
        require_auth: Whether authentication is required
        allow_api_key: Whether to allow API key authentication
        allow_jwt: Whether to allow JWT authentication

    Returns:
        WebSocketAuthResult with authentication status
    """
    authenticator = WebSocketAuthenticator(
        require_auth=require_auth,
        allow_api_key=allow_api_key,
        allow_jwt=allow_jwt,
    )
    return await authenticator.authenticate(websocket)


# Pre-configured authenticators for common use cases
default_authenticator = WebSocketAuthenticator(require_auth=True)
optional_authenticator = WebSocketAuthenticator(require_auth=False, allow_anonymous=True)
api_key_only_authenticator = WebSocketAuthenticator(require_auth=True, allow_jwt=False)
jwt_only_authenticator = WebSocketAuthenticator(require_auth=True, allow_api_key=False)
