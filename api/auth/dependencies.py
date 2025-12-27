"""
FastAPI Authentication Dependencies

This module provides FastAPI dependency functions for authentication,
including JWT token validation and API key authentication.

Features:
- Optional authentication mode for development
- JWT bearer token authentication
- API key header authentication
- Combined authentication (JWT or API key)
"""

import os
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from .jwt import verify_token, TokenData, TokenValidationError
from .api_key import validate_api_key, APIKey


# Configuration
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() in ("true", "1", "yes")
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str, code: str = "authentication_error"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": detail, "code": code},
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str, code: str = "authorization_error"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": detail, "code": code},
        )


class User:
    """
    Represents an authenticated user.

    Can be populated from JWT token or API key.
    """
    def __init__(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        auth_type: str = "jwt",
        api_key_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.scopes = scopes or []
        self.auth_type = auth_type
        self.api_key_id = api_key_id

    def has_scope(self, scope: str) -> bool:
        """Check if user has a specific scope"""
        return scope in self.scopes or "*" in self.scopes

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if user has any of the specified scopes"""
        return any(self.has_scope(s) for s in scopes)

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if user has all of the specified scopes"""
        return all(self.has_scope(s) for s in scopes)

    @classmethod
    def from_token(cls, token_data: TokenData) -> "User":
        """Create a User from JWT token data"""
        return cls(
            user_id=token_data.user_id,
            username=token_data.username,
            scopes=token_data.scopes,
            auth_type="jwt",
        )

    @classmethod
    def from_api_key(cls, api_key: APIKey) -> "User":
        """Create a User from API key"""
        return cls(
            user_id=api_key.created_by,
            username=api_key.name,
            scopes=api_key.scopes,
            auth_type="api_key",
            api_key_id=api_key.id,
        )

    @classmethod
    def anonymous(cls) -> "User":
        """Create an anonymous user (for optional auth)"""
        return cls(
            user_id=None,
            username="anonymous",
            scopes=[],
            auth_type="anonymous",
        )


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> User:
    """
    FastAPI dependency to get the current authenticated user from JWT token.

    Raises:
        AuthenticationError: If authentication fails
    """
    if not AUTH_ENABLED:
        # Return a default user when auth is disabled
        return User(
            user_id="dev-user",
            username="developer",
            scopes=["*"],
            auth_type="disabled",
        )

    if not credentials:
        raise AuthenticationError(
            "Missing authentication credentials",
            code="missing_credentials"
        )

    try:
        token_data = verify_token(credentials.credentials)
        return User.from_token(token_data)
    except TokenValidationError as e:
        raise AuthenticationError(e.message, code=e.code)


async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current authenticated user.

    Returns None if no valid authentication is provided, instead of raising an error.
    """
    if not AUTH_ENABLED:
        return User(
            user_id="dev-user",
            username="developer",
            scopes=["*"],
            auth_type="disabled",
        )

    if not credentials:
        return User.anonymous()

    try:
        token_data = verify_token(credentials.credentials)
        return User.from_token(token_data)
    except TokenValidationError:
        return User.anonymous()


async def require_api_key(
    api_key: Annotated[Optional[str], Depends(api_key_header)],
) -> User:
    """
    FastAPI dependency to require API key authentication.

    Raises:
        AuthenticationError: If API key is missing or invalid
    """
    if not AUTH_ENABLED:
        return User(
            user_id="dev-user",
            username="developer",
            scopes=["*"],
            auth_type="disabled",
        )

    if not api_key:
        raise AuthenticationError(
            f"Missing API key in {API_KEY_HEADER_NAME} header",
            code="missing_api_key"
        )

    validated_key = validate_api_key(api_key)
    if not validated_key:
        raise AuthenticationError(
            "Invalid or expired API key",
            code="invalid_api_key"
        )

    return User.from_api_key(validated_key)


async def require_api_key_optional(
    api_key: Annotated[Optional[str], Depends(api_key_header)],
) -> Optional[User]:
    """
    FastAPI dependency to optionally validate API key.

    Returns None if no valid API key is provided.
    """
    if not AUTH_ENABLED:
        return User(
            user_id="dev-user",
            username="developer",
            scopes=["*"],
            auth_type="disabled",
        )

    if not api_key:
        return User.anonymous()

    validated_key = validate_api_key(api_key)
    if not validated_key:
        return User.anonymous()

    return User.from_api_key(validated_key)


async def get_current_user_or_api_key(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    api_key: Annotated[Optional[str], Depends(api_key_header)],
) -> User:
    """
    FastAPI dependency that accepts either JWT token or API key.

    Checks JWT token first, then falls back to API key.

    Raises:
        AuthenticationError: If neither valid JWT nor API key is provided
    """
    if not AUTH_ENABLED:
        return User(
            user_id="dev-user",
            username="developer",
            scopes=["*"],
            auth_type="disabled",
        )

    # Try JWT token first
    if credentials:
        try:
            token_data = verify_token(credentials.credentials)
            return User.from_token(token_data)
        except TokenValidationError:
            pass  # Fall through to try API key

    # Try API key
    if api_key:
        validated_key = validate_api_key(api_key)
        if validated_key:
            return User.from_api_key(validated_key)

    raise AuthenticationError(
        "Valid authentication required (JWT token or API key)",
        code="authentication_required"
    )


def require_scopes(*required_scopes: str):
    """
    Factory function to create a dependency that requires specific scopes.

    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: User = Depends(require_scopes("admin", "read"))):
            ...
    """
    async def scope_checker(
        user: Annotated[User, Depends(get_current_user_or_api_key)],
    ) -> User:
        if not user.has_all_scopes(list(required_scopes)):
            raise AuthorizationError(
                f"Required scopes: {', '.join(required_scopes)}",
                code="insufficient_scopes"
            )
        return user

    return scope_checker


def require_any_scope(*required_scopes: str):
    """
    Factory function to create a dependency that requires at least one of the specified scopes.

    Usage:
        @app.get("/data")
        async def data_endpoint(user: User = Depends(require_any_scope("read", "admin"))):
            ...
    """
    async def scope_checker(
        user: Annotated[User, Depends(get_current_user_or_api_key)],
    ) -> User:
        if not user.has_any_scope(list(required_scopes)):
            raise AuthorizationError(
                f"Required one of scopes: {', '.join(required_scopes)}",
                code="insufficient_scopes"
            )
        return user

    return scope_checker


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user_optional)]
APIKeyUser = Annotated[User, Depends(require_api_key)]
OptionalAPIKeyUser = Annotated[Optional[User], Depends(require_api_key_optional)]
AnyAuthUser = Annotated[User, Depends(get_current_user_or_api_key)]
