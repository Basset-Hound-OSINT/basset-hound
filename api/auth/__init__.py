"""
Basset Hound Authentication Module

This module provides JWT token authentication and API key authentication
for the Basset Hound application.

Features:
- JWT token creation and validation with configurable expiry
- API key authentication for programmatic access
- Optional authentication mode for development
- Password hashing using passlib
- FastAPI dependencies for protected routes
"""

from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    TokenData,
    Token,
)

from .api_key import (
    APIKeyManager,
    create_api_key,
    validate_api_key,
    revoke_api_key,
    list_api_keys,
)

from .dependencies import (
    get_current_user,
    get_current_user_optional,
    require_api_key,
    require_api_key_optional,
    get_current_user_or_api_key,
    User,
    CurrentUser,
    OptionalUser,
    APIKeyUser,
    AnyAuthUser,
    require_scopes,
    require_any_scope,
    AUTH_ENABLED,
)

from .routes import router as auth_router

__all__ = [
    # JWT functions
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_password_hash",
    "verify_password",
    "TokenData",
    "Token",
    # API key functions
    "APIKeyManager",
    "create_api_key",
    "validate_api_key",
    "revoke_api_key",
    "list_api_keys",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_api_key",
    "require_api_key_optional",
    "get_current_user_or_api_key",
    "User",
    "CurrentUser",
    "OptionalUser",
    "APIKeyUser",
    "AnyAuthUser",
    "require_scopes",
    "require_any_scope",
    "AUTH_ENABLED",
    # Router
    "auth_router",
]
