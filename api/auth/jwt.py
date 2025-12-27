"""
JWT Token Authentication Module

This module handles JWT token creation, validation, and password hashing
for the Basset Hound authentication system.

Uses:
- python-jose for JWT encoding/decoding
- passlib for secure password hashing
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


# Configuration - can be overridden via environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data model"""
    username: Optional[str] = None
    user_id: Optional[str] = None
    scopes: list[str] = []
    token_type: str = "access"
    exp: Optional[datetime] = None


class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class TokenValidationError(Exception):
    """Custom exception for token validation errors"""
    def __init__(self, message: str, code: str = "invalid_token"):
        self.message = message
        self.code = code
        super().__init__(self.message)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[list[str]] = None,
) -> str:
    """
    Create a new JWT access token.

    Args:
        data: Dictionary containing token payload data (must include 'sub' for subject)
        expires_delta: Optional custom expiration time delta
        scopes: Optional list of permission scopes

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })

    if scopes:
        to_encode["scopes"] = scopes

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT refresh token.

    Refresh tokens have a longer expiration time and can be used
    to obtain new access tokens without re-authentication.

    Args:
        data: Dictionary containing token payload data (must include 'sub' for subject)
        expires_delta: Optional custom expiration time delta

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(
    token: str,
    expected_type: str = "access",
    verify_exp: bool = True,
) -> TokenData:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify
        expected_type: Expected token type ('access' or 'refresh')
        verify_exp: Whether to verify token expiration

    Returns:
        TokenData object with decoded token information

    Raises:
        TokenValidationError: If token is invalid or expired
    """
    try:
        options = {"verify_exp": verify_exp}
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options=options)

        # Verify token type
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise TokenValidationError(
                f"Invalid token type. Expected {expected_type}, got {token_type}",
                code="invalid_token_type"
            )

        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        scopes: list = payload.get("scopes", [])
        exp = payload.get("exp")

        if username is None and user_id is None:
            raise TokenValidationError(
                "Token missing subject identifier",
                code="missing_subject"
            )

        # Convert exp timestamp to datetime if present
        exp_datetime = None
        if exp:
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        return TokenData(
            username=username,
            user_id=user_id,
            scopes=scopes,
            token_type=token_type,
            exp=exp_datetime,
        )

    except JWTError as e:
        raise TokenValidationError(
            f"Could not validate credentials: {str(e)}",
            code="invalid_token"
        )


def decode_token_unsafe(token: str) -> dict:
    """
    Decode a JWT token without verification.

    WARNING: This should only be used for debugging or inspecting tokens.
    Never trust the data from this function for authentication.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary with decoded token payload
    """
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": False, "verify_exp": False}
        )
    except JWTError:
        return {}


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: JWT token string

    Returns:
        Datetime of token expiration, or None if token is invalid
    """
    try:
        payload = decode_token_unsafe(token)
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.

    Args:
        token: JWT token string

    Returns:
        True if token is expired or invalid, False otherwise
    """
    exp = get_token_expiry(token)
    if exp is None:
        return True
    return datetime.now(timezone.utc) > exp
