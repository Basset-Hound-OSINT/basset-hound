"""
Pydantic models for Orphan Data management.

Orphan Data represents unlinked identifiers (phone numbers, emails, crypto addresses,
usernames, IP addresses, etc.) that haven't been tied to entities yet. This is critical
for OSINT work where data is collected before entity relationships are established.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class IdentifierType(str, Enum):
    """Enumeration of supported identifier types for orphan data."""
    EMAIL = "email"
    PHONE = "phone"
    CRYPTO_ADDRESS = "crypto_address"
    USERNAME = "username"
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    URL = "url"
    SOCIAL_MEDIA = "social_media"
    LICENSE_PLATE = "license_plate"
    PASSPORT = "passport"
    SSN = "ssn"
    ACCOUNT_NUMBER = "account_number"
    MAC_ADDRESS = "mac_address"
    IMEI = "imei"
    OTHER = "other"


class OrphanDataBase(BaseModel):
    """Base model for orphan data with common fields."""

    identifier_type: IdentifierType = Field(
        ...,
        description="Type of identifier (email, phone, crypto_address, etc.)"
    )
    identifier_value: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The actual identifier value"
    )
    source: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Where this identifier was found (URL, document name, etc.)"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Additional notes about this identifier"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing and filtering orphan data"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the identifier validity (0.0 to 1.0)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON field for additional metadata"
    )

    @field_validator("identifier_value")
    @classmethod
    def validate_identifier_value(cls, v: str) -> str:
        """Ensure identifier value is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("identifier_value cannot be empty")
        return v.strip()

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> list[str]:
        """Ensure tags is a list of strings."""
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("tags must be a list")
        # Filter out empty strings and convert to strings
        return [str(tag).strip() for tag in v if tag and str(tag).strip()]


class OrphanDataCreate(OrphanDataBase):
    """
    Model for creating new orphan data.

    The id and discovered_date will be auto-generated if not provided.
    """

    id: Optional[str] = Field(
        default=None,
        description="Optional custom orphan ID (UUID generated if not provided)",
        examples=["orphan-550e8400-e29b-41d4-a716-446655440000"]
    )
    discovered_date: Optional[str] = Field(
        default=None,
        description="Optional discovery timestamp (current time if not provided)",
        examples=["2024-01-15T10:30:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identifier_type": "email",
                "identifier_value": "john.unknown@example.com",
                "source": "https://leaked-data.com/dump123",
                "notes": "Found in data breach, unconfirmed owner",
                "tags": ["data-breach", "unverified"],
                "confidence_score": 0.6,
                "metadata": {
                    "breach_name": "Company XYZ 2024",
                    "breach_date": "2024-01-10",
                    "additional_info": "Email appears in password list"
                }
            }
        }
    )


class OrphanDataUpdate(BaseModel):
    """
    Model for updating existing orphan data.

    Supports partial updates - only provided fields will be modified.
    """

    identifier_type: Optional[IdentifierType] = Field(
        default=None,
        description="Updated identifier type"
    )
    identifier_value: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="Updated identifier value"
    )
    source: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated source"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Updated notes"
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Updated tags list"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Updated confidence score"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated metadata"
    )

    @field_validator("identifier_value")
    @classmethod
    def validate_identifier_value(cls, v: Optional[str]) -> Optional[str]:
        """Ensure identifier value is not empty after stripping if provided."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("identifier_value cannot be empty")
        return v.strip()

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> Optional[list[str]]:
        """Ensure tags is a list of strings if provided."""
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("tags must be a list")
        return [str(tag).strip() for tag in v if tag and str(tag).strip()]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": "Verified email belongs to John Doe",
                "tags": ["verified", "linked"],
                "confidence_score": 0.95
            }
        }
    )


class OrphanDataResponse(BaseModel):
    """
    Model for orphan data returned by the API.

    Contains the complete orphan data record including all fields and metadata.
    """

    id: str = Field(
        ...,
        description="Unique orphan data identifier",
        examples=["orphan-550e8400-e29b-41d4-a716-446655440000"]
    )
    project_id: str = Field(
        ...,
        description="Project ID this orphan data belongs to",
        examples=["project-123"]
    )
    identifier_type: IdentifierType = Field(
        ...,
        description="Type of identifier"
    )
    identifier_value: str = Field(
        ...,
        description="The actual identifier value"
    )
    source: Optional[str] = Field(
        default=None,
        description="Where this identifier was found"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score (0.0 to 1.0)"
    )
    discovered_date: str = Field(
        ...,
        description="When this orphan data was discovered",
        examples=["2024-01-15T10:30:00"]
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    linked_entity_id: Optional[str] = Field(
        default=None,
        description="ID of linked entity if this orphan was linked"
    )
    linked_at: Optional[str] = Field(
        default=None,
        description="When this orphan was linked to an entity"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "orphan-550e8400-e29b-41d4-a716-446655440000",
                "project_id": "project-123",
                "identifier_type": "email",
                "identifier_value": "john.unknown@example.com",
                "source": "https://leaked-data.com/dump123",
                "notes": "Found in data breach, verified owner",
                "tags": ["data-breach", "verified", "linked"],
                "confidence_score": 0.95,
                "discovered_date": "2024-01-15T10:30:00",
                "metadata": {
                    "breach_name": "Company XYZ 2024",
                    "breach_date": "2024-01-10"
                },
                "linked_entity_id": "entity-123",
                "linked_at": "2024-01-16T14:30:00"
            }
        }
    )


class OrphanDataList(BaseModel):
    """
    Model for a list of orphan data records.

    Used for listing orphan data with optional pagination.
    """

    orphans: list[OrphanDataResponse] = Field(
        default_factory=list,
        description="List of orphan data records"
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of orphan data records"
    )
    project_id: str = Field(
        ...,
        description="Project ID",
        examples=["project-123"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orphans": [
                    {
                        "id": "orphan-550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "project-123",
                        "identifier_type": "email",
                        "identifier_value": "john.unknown@example.com",
                        "source": "data breach",
                        "tags": ["unverified"],
                        "confidence_score": 0.6,
                        "discovered_date": "2024-01-15T10:30:00",
                        "metadata": {}
                    }
                ],
                "total": 1,
                "project_id": "project-123"
            }
        }
    )


class OrphanLinkRequest(BaseModel):
    """
    Model for linking orphan data to an entity.
    """

    entity_id: str = Field(
        ...,
        description="ID of the entity to link this orphan data to",
        examples=["entity-550e8400-e29b-41d4-a716-446655440000"]
    )
    merge_to_entity: bool = Field(
        default=True,
        description="Whether to merge orphan data into entity profile"
    )
    delete_orphan: bool = Field(
        default=False,
        description="Whether to delete orphan data after linking"
    )
    target_field: Optional[str] = Field(
        default=None,
        description="Target field in entity profile (auto-detected if not provided)",
        examples=["email", "phone", "username"]
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notes about this linking operation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "entity-550e8400-e29b-41d4-a716-446655440000",
                "merge_to_entity": True,
                "delete_orphan": False,
                "target_field": "email",
                "notes": "Verified this email belongs to John Doe"
            }
        }
    )


class OrphanLinkResponse(BaseModel):
    """
    Model for orphan data linking operation response.
    """

    success: bool = Field(
        ...,
        description="Whether the linking operation succeeded"
    )
    orphan_id: str = Field(
        ...,
        description="ID of the orphan data that was linked"
    )
    entity_id: str = Field(
        ...,
        description="ID of the entity it was linked to"
    )
    merged: bool = Field(
        ...,
        description="Whether data was merged into entity profile"
    )
    deleted: bool = Field(
        ...,
        description="Whether orphan data was deleted after linking"
    )
    message: str = Field(
        ...,
        description="Status message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "orphan_id": "orphan-550e8400-e29b-41d4-a716-446655440000",
                "entity_id": "entity-123",
                "merged": True,
                "deleted": False,
                "message": "Orphan data successfully linked and merged to entity"
            }
        }
    )
