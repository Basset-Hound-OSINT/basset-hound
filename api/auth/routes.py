"""
Authentication Routes

FastAPI router providing authentication endpoints for:
- User login and token generation
- Token refresh
- API key management
- User information
"""

import os
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
    Token,
    TokenData,
    TokenValidationError,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .api_key import (
    create_api_key,
    revoke_api_key,
    list_api_keys,
    APIKey,
)
from .dependencies import (
    get_current_user,
    get_current_user_optional,
    User,
    CurrentUser,
    AnyAuthUser,
    AUTH_ENABLED,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with username and password"""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Token response containing access and refresh tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Valid refresh token")


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key"""
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    description: Optional[str] = Field(None, max_length=500, description="Key description")
    scopes: List[str] = Field(default=[], description="Permission scopes")
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Days until expiration (1-365)"
    )


class APIKeyResponse(BaseModel):
    """Response containing API key details"""
    id: str
    name: str
    key_prefix: str
    created_at: str
    expires_at: Optional[str] = None
    status: str
    scopes: List[str]
    description: Optional[str] = None
    # Only included when key is first created
    raw_key: Optional[str] = None


class APIKeyCreateResponse(BaseModel):
    """Response after creating an API key"""
    message: str
    api_key: APIKeyResponse
    warning: str = "Store the raw_key securely - it will not be shown again"


class UserInfoResponse(BaseModel):
    """Current user information response"""
    user_id: Optional[str]
    username: Optional[str]
    scopes: List[str]
    auth_type: str
    auth_enabled: bool


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


# ============================================================================
# Simple User Store (for development/demo - replace with database in production)
# ============================================================================

# In production, this should be replaced with a proper user database
# For now, we use a simple in-memory store with environment variable support
_DEMO_USERS = {
    "admin": {
        "user_id": "admin-001",
        "username": "admin",
        "password_hash": get_password_hash(os.getenv("ADMIN_PASSWORD", "admin")),
        "scopes": ["*"],
    },
    "user": {
        "user_id": "user-001",
        "username": "user",
        "password_hash": get_password_hash(os.getenv("USER_PASSWORD", "user")),
        "scopes": ["read", "write"],
    },
}


def get_user_by_username(username: str) -> Optional[dict]:
    """Get a user by username from the user store"""
    return _DEMO_USERS.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate a user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login and get access token",
    description="Authenticate with username and password to receive JWT tokens.",
)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT tokens.

    Returns:
        - access_token: Short-lived token for API access
        - refresh_token: Long-lived token for obtaining new access tokens
        - expires_in: Seconds until access token expires
    """
    if not AUTH_ENABLED:
        # When auth is disabled, return a dummy token
        return TokenResponse(
            access_token=create_access_token({"sub": "dev-user", "user_id": "dev-001"}),
            refresh_token=create_refresh_token({"sub": "dev-user", "user_id": "dev-001"}),
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    token_data = {
        "sub": user["username"],
        "user_id": user["user_id"],
    }

    access_token = create_access_token(
        data=token_data,
        scopes=user.get("scopes", []),
    )
    refresh_token = create_refresh_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to obtain a new access token.",
)
async def refresh_token(request: RefreshRequest):
    """
    Refresh an access token using a valid refresh token.

    The refresh token must be valid and not expired.
    Returns a new access token with the same permissions.
    """
    if not AUTH_ENABLED:
        return TokenResponse(
            access_token=create_access_token({"sub": "dev-user", "user_id": "dev-001"}),
            refresh_token=request.refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    try:
        # Verify the refresh token
        token_data = verify_token(request.refresh_token, expected_type="refresh")
    except TokenValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e.message}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user to include scopes
    user = get_user_by_username(token_data.username) if token_data.username else None
    scopes = user.get("scopes", []) if user else token_data.scopes

    # Create new access token
    new_token_data = {
        "sub": token_data.username,
        "user_id": token_data.user_id,
    }

    new_access_token = create_access_token(
        data=new_token_data,
        scopes=scopes,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="Get current user info",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(user: AnyAuthUser):
    """
    Get information about the current authenticated user.

    Works with both JWT tokens and API keys.
    """
    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        scopes=user.scopes,
        auth_type=user.auth_type,
        auth_enabled=AUTH_ENABLED,
    )


@router.get(
    "/status",
    summary="Get authentication status",
    description="Check if authentication is enabled and get configuration info.",
)
async def auth_status():
    """
    Get the current authentication configuration status.

    Returns whether auth is enabled and available authentication methods.
    """
    return {
        "auth_enabled": AUTH_ENABLED,
        "methods": {
            "jwt": True,
            "api_key": True,
        },
        "token_expiry_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
    }


# ============================================================================
# API Key Management Endpoints
# ============================================================================

@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Generate a new API key for programmatic access.",
)
async def create_new_api_key(
    request: APIKeyCreateRequest,
    user: AnyAuthUser,
):
    """
    Create a new API key.

    The raw key is only returned once - store it securely.
    API keys can be used for programmatic access via the X-API-Key header.
    """
    raw_key, api_key = create_api_key(
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
        created_by=user.user_id,
        description=request.description,
    )

    return APIKeyCreateResponse(
        message="API key created successfully",
        api_key=APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            status=api_key.status,
            scopes=api_key.scopes,
            description=api_key.description,
            raw_key=raw_key,  # Only returned on creation
        ),
    )


@router.get(
    "/api-keys",
    response_model=List[APIKeyResponse],
    summary="List API keys",
    description="List all API keys (optionally including revoked ones).",
)
async def list_user_api_keys(
    user: AnyAuthUser,
    include_revoked: bool = False,
):
    """
    List API keys created by the current user.

    Note: The raw key values are never returned after creation.
    """
    keys = list_api_keys(
        include_revoked=include_revoked,
        created_by=user.user_id,
    )

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            created_at=key.created_at,
            expires_at=key.expires_at,
            status=key.status,
            scopes=key.scopes,
            description=key.description,
        )
        for key in keys
    ]


@router.delete(
    "/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="Revoke an API key",
    description="Revoke an API key so it can no longer be used.",
)
async def revoke_user_api_key(
    key_id: str,
    user: AnyAuthUser,
):
    """
    Revoke an API key.

    The key will be marked as revoked and can no longer be used for authentication.
    """
    # In production, verify the key belongs to the user
    success = revoke_api_key(key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return MessageResponse(
        message="API key revoked successfully",
        success=True,
    )


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.post(
    "/hash-password",
    summary="Hash a password (utility)",
    description="Utility endpoint to generate a password hash. For development use only.",
    include_in_schema=AUTH_ENABLED,  # Hide in production docs
)
async def hash_password_utility(
    password: str = Body(..., embed=True),
):
    """
    Generate a bcrypt hash of a password.

    This is a utility endpoint for development/setup purposes.
    In production, this should be protected or disabled.
    """
    if AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled when authentication is enabled",
        )

    return {
        "password_hash": get_password_hash(password),
    }


@router.post(
    "/verify-password",
    summary="Verify a password (utility)",
    description="Utility endpoint to verify a password against a hash. For development use only.",
    include_in_schema=AUTH_ENABLED,
)
async def verify_password_utility(
    password: str = Body(...),
    password_hash: str = Body(...),
):
    """
    Verify a password against a bcrypt hash.

    This is a utility endpoint for development/setup purposes.
    """
    if AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled when authentication is enabled",
        )

    is_valid = verify_password(password, password_hash)
    return {
        "valid": is_valid,
    }
