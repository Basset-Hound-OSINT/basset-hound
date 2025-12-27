"""
Pydantic models for Authentication and User management.

Provides models for JWT token-based authentication including:
- Token generation and validation
- User registration and login
- User profile management

Note: This is a foundation for future authentication implementation.
The current Basset Hound application does not have authentication enabled.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator, SecretStr
import re


class Token(BaseModel):
    """
    Model for JWT access token response.

    Returned after successful authentication.
    """

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"]
    )
    expires_in: Optional[int] = Field(
        default=None,
        description="Token expiration time in seconds",
        examples=[3600]
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="Optional refresh token for obtaining new access tokens"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNzA1MzM2MDAwfQ.signature",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    )


class TokenData(BaseModel):
    """
    Model for decoded JWT token payload.

    Contains the claims extracted from a validated JWT token.
    """

    sub: Optional[str] = Field(
        default=None,
        description="Subject (user ID or username)",
        examples=["user123", "admin@example.com"]
    )
    username: Optional[str] = Field(
        default=None,
        description="Username from the token"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User's unique identifier"
    )
    exp: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp"
    )
    iat: Optional[datetime] = Field(
        default=None,
        description="Token issued-at timestamp"
    )
    scopes: list[str] = Field(
        default_factory=list,
        description="List of permission scopes granted to the token",
        examples=[["read:projects", "write:entities"]]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sub": "user123",
                "username": "johndoe",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "exp": "2024-01-16T10:30:00Z",
                "iat": "2024-01-15T10:30:00Z",
                "scopes": ["read:projects", "write:entities"]
            }
        }
    )


class UserBase(BaseModel):
    """Base model for user data with common fields."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique username (alphanumeric, underscores, hyphens)",
        examples=["johndoe", "admin_user"]
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["john.doe@example.com"]
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's full display name",
        examples=["John Doe"]
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format and reserved words."""
        v = v.strip()

        # Check length after stripping
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")

        # Check for reserved usernames
        reserved = {"admin", "root", "system", "api", "null", "undefined"}
        if v.lower() in reserved:
            raise ValueError(f"Username '{v}' is reserved")

        return v


class UserCreate(UserBase):
    """
    Model for user registration.

    Requires password with strength validation.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 chars, requires complexity)",
        examples=["SecureP@ssw0rd!"]
    )
    confirm_password: Optional[str] = Field(
        default=None,
        description="Password confirmation (must match password)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure confirm_password matches password if provided."""
        if v is not None and "password" in info.data:
            if v != info.data["password"]:
                raise ValueError("Passwords do not match")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "password": "SecureP@ssw0rd!",
                "confirm_password": "SecureP@ssw0rd!"
            }
        }
    )


class UserLogin(BaseModel):
    """
    Model for user login request.

    Accepts either username or email for authentication.
    """

    username: Optional[str] = Field(
        default=None,
        description="Username (alternative to email)"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Email address (alternative to username)"
    )
    password: str = Field(
        ...,
        description="User password"
    )

    @field_validator("password", mode="before")
    @classmethod
    def check_credentials_provided(cls, v: str, info) -> str:
        """Ensure at least username or email is provided."""
        data = info.data
        if not data.get("username") and not data.get("email"):
            raise ValueError("Either username or email must be provided")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "password": "SecureP@ssw0rd!"
            }
        }
    )


class User(UserBase):
    """
    Model for user data returned by the API.

    Contains user profile information without sensitive data like password.
    """

    id: str = Field(
        ...,
        description="Unique user identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active"
    )
    is_superuser: bool = Field(
        default=False,
        description="Whether the user has superuser privileges"
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the user account was created"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="When the user last logged in"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-16T08:00:00Z"
            }
        }
    )


class UserUpdate(BaseModel):
    """
    Model for updating user profile.

    All fields are optional - only provided fields will be updated.
    """

    email: Optional[EmailStr] = Field(
        default=None,
        description="New email address"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="New display name"
    )
    current_password: Optional[str] = Field(
        default=None,
        description="Current password (required when changing password)"
    )
    new_password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: Optional[str], info) -> Optional[str]:
        """Validate new password if provided."""
        if v is None:
            return None

        # If changing password, current_password must be provided
        if "current_password" in info.data and not info.data.get("current_password"):
            raise ValueError("Current password is required to set a new password")

        # Apply same strength requirements as UserCreate
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new.email@example.com",
                "full_name": "John Q. Doe"
            }
        }
    )


class PasswordReset(BaseModel):
    """
    Model for password reset request.
    """

    email: EmailStr = Field(
        ...,
        description="Email address associated with the account"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com"
            }
        }
    )


class PasswordResetConfirm(BaseModel):
    """
    Model for confirming password reset with token.
    """

    token: str = Field(
        ...,
        description="Password reset token received via email"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Apply password strength requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset-token-123456",
                "new_password": "NewSecureP@ssw0rd!"
            }
        }
    )
