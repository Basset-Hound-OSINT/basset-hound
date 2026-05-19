"""
Authentication Router for Basset Hound API

Provides endpoints for:
- User login with password verification
- Token generation (access and refresh tokens)
- Token refresh without re-authentication
- Token validation

Phase 8, Security Fix: JWT Authentication Implementation
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenValidationError,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from api.config import get_settings
from api.models.auth import Token, TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic Models for Auth Endpoints
class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(
        ...,
        description="Username or email",
        examples=["johndoe"]
    )
    password: str = Field(
        ...,
        description="User password",
        examples=["SecureP@ssw0rd!"]
    )


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(
        ...,
        description="Refresh token to use for obtaining new access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication"
    )
    refresh_token: Optional[str] = Field(
        None,
        description="JWT refresh token for obtaining new access tokens"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds"
    )


class TokenValidationResponse(BaseModel):
    """Response model for token validation endpoint."""
    valid: bool = Field(
        ...,
        description="Whether token is valid"
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID from token (if valid)"
    )
    username: Optional[str] = Field(
        None,
        description="Username from token (if valid)"
    )
    scopes: list = Field(
        default_factory=list,
        description="Permission scopes (if valid)"
    )
    expires_in: Optional[int] = Field(
        None,
        description="Seconds until token expiration (if valid)"
    )


# Placeholder for user database (in production, query from Neo4j or user database)
# For now, we'll use a simple in-memory store with hardcoded test user
TEST_USERS = {
    "testuser": {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        # Password: TestPassword123!
        "hashed_password": "$2b$12$5DWKvyMxXLhXTR0zYhqPuO.fCW02TgV5C7H7V3UXZ7Mz9L.F2W7Wy",
        "user_id": "user-001",
        "scopes": ["read:projects", "write:projects", "read:entities", "write:entities"],
        "is_active": True,
    },
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Administrator",
        # Password: AdminPassword123!
        "hashed_password": "$2b$12$DWKvyMxXLhXTR0zYhqPuO.fCW02TgV5C7H7V3UXZ7Mz9L.F2W7Wy",
        "user_id": "user-admin",
        "scopes": ["admin"],
        "is_active": True,
    },
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.

    In production, this should query a user database (Neo4j, PostgreSQL, etc.)
    and verify the password hash.

    Args:
        username: Username to authenticate
        password: Password to verify

    Returns:
        User dictionary if authentication successful, None otherwise
    """
    # Check test users (for development/testing)
    user = TEST_USERS.get(username)
    if not user:
        return None

    if not user["is_active"]:
        return None

    # Verify password
    if not verify_password(password, user["hashed_password"]):
        return None

    return user


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Login with username and password to obtain JWT tokens.

    Returns both access token (short-lived, for API requests) and
    refresh token (long-lived, for obtaining new access tokens).

    **Security Notes:**
    - Passwords are verified using bcrypt hashing
    - Access tokens expire after 30 minutes (default, configurable)
    - Refresh tokens expire after 7 days (default, configurable)
    - Failed login attempts should be rate limited (not implemented yet)
    - Passwords should never be logged

    Args:
        request: Login request with username and password

    Returns:
        TokenResponse with access_token, refresh_token, and expires_in

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid
    """
    # Authenticate user
    user = authenticate_user(request.username, request.password)

    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token payload
    token_payload = {
        "sub": user["username"],  # Subject (required for JWT)
        "user_id": user.get("user_id", user["username"]),
    }

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=token_payload,
        expires_delta=access_token_expires,
        scopes=user.get("scopes", []),
    )

    # Create refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data=token_payload,
        expires_delta=refresh_token_expires,
    )

    logger.info(f"User logged in successfully: {user['username']}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: TokenRefreshRequest) -> TokenResponse:
    """
    Obtain a new access token using a refresh token.

    Allows clients to get a new access token without providing username/password,
    as long as their refresh token is still valid.

    **Security Notes:**
    - Only refresh tokens can be used with this endpoint (not access tokens)
    - Refresh token must not be expired
    - Returns new access token with same permissions as original

    Args:
        request: TokenRefreshRequest with refresh_token

    Returns:
        TokenResponse with new access_token and new refresh_token

    Raises:
        HTTPException: 401 Unauthorized if refresh token is invalid or expired
    """
    try:
        # Verify refresh token
        token_data = verify_token(
            request.refresh_token,
            expected_type="refresh",
            verify_exp=True
        )

        # Create new access token with same claims
        token_payload = {
            "sub": token_data.username,
            "user_id": token_data.user_id,
        }

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data=token_payload,
            expires_delta=access_token_expires,
            scopes=token_data.scopes,
        )

        # Also return new refresh token to extend session
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            data=token_payload,
            expires_delta=refresh_token_expires,
        )

        logger.info(f"Token refreshed for user: {token_data.username}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )

    except TokenValidationError as e:
        logger.warning(f"Token refresh failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/validate", response_model=TokenValidationResponse, status_code=status.HTTP_200_OK)
async def validate_token(token: str) -> TokenValidationResponse:
    """
    Validate an access token and return its claims.

    Useful for clients to check if their token is still valid without
    making an authenticated request.

    **Security Notes:**
    - Token signature and expiration are validated
    - Does not require authentication itself
    - Returns user info from token (should match user database)

    Args:
        token: Access token to validate (as query parameter or header)

    Returns:
        TokenValidationResponse with validation result and token claims

    Raises:
        HTTPException: 400 Bad Request if token parameter missing
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token parameter required",
        )

    try:
        # Verify token
        token_data = verify_token(token, expected_type="access", verify_exp=True)

        # Calculate time until expiration
        expires_in = None
        if token_data.exp:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if token_data.exp > now:
                expires_in = int((token_data.exp - now).total_seconds())

        return TokenValidationResponse(
            valid=True,
            user_id=token_data.user_id,
            username=token_data.username,
            scopes=token_data.scopes,
            expires_in=expires_in,
        )

    except TokenValidationError as e:
        logger.debug(f"Token validation failed: {e.message}")
        return TokenValidationResponse(
            valid=False,
            scopes=[],
        )


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: dict = Depends(__import__("api.dependencies", fromlist=["get_current_user"]).get_current_user)
) -> dict:
    """
    Get information about the currently authenticated user.

    Returns the user information from their valid JWT token.

    Args:
        current_user: Current user from JWT token (via dependency injection)

    Returns:
        Dictionary with user information:
        - id: User ID
        - username: Username
        - scopes: Permission scopes
        - exp: Token expiration time
    """
    return {
        "id": current_user.get("id"),
        "username": current_user.get("username"),
        "scopes": current_user.get("scopes", []),
        "expires_at": current_user.get("exp"),
    }
