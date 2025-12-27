"""
Pydantic models for Entity (Person) management.

Entities represent people or organizations being investigated.
They contain profile data organized into sections and fields
as defined by the configuration schema.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProfileData(BaseModel):
    """
    Dynamic profile data model.

    Profile data is organized by section_id -> field_id -> value.
    The structure is determined by the data_config.yaml schema.

    Example structure:
    {
        "core": {
            "name": [{"first_name": "John", "last_name": "Doe"}],
            "email": ["john@example.com"],
            "date_of_birth": ["1990-01-15"]
        },
        "social": {
            "linkedin": [{"url": "https://linkedin.com/in/johndoe", "username": "johndoe"}]
        }
    }
    """

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "core": {
                    "name": [{"first_name": "John", "middle_name": "", "last_name": "Doe"}],
                    "email": ["john.doe@example.com"],
                    "date_of_birth": ["1990-01-15"]
                },
                "social": {
                    "linkedin": [{
                        "url": "https://linkedin.com/in/johndoe",
                        "username": "johndoe"
                    }]
                }
            }
        }
    )


class EntityBase(BaseModel):
    """Base model for entity data with common fields."""

    profile: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Profile data organized by section_id -> field_id -> value"
    )

    @field_validator("profile", mode="before")
    @classmethod
    def validate_profile(cls, v: Any) -> dict[str, dict[str, Any]]:
        """Ensure profile is a properly structured dictionary."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("profile must be a dictionary")
        return v


class EntityCreate(EntityBase):
    """
    Model for creating a new entity/person.

    The id and created_at will be auto-generated if not provided.
    Profile data should match the schema defined in data_config.yaml.
    """

    id: Optional[str] = Field(
        default=None,
        description="Optional custom entity ID (UUID generated if not provided)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Optional creation timestamp (current time if not provided)",
        examples=["2024-01-15T10:30:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john.doe@example.com"]
                    },
                    "social": {
                        "linkedin": [{
                            "url": "https://linkedin.com/in/johndoe",
                            "username": "johndoe"
                        }]
                    }
                }
            }
        }
    )


class EntityUpdate(BaseModel):
    """
    Model for updating an existing entity/person.

    Supports partial updates - only provided fields will be modified.
    Profile data is merged with existing data at the section/field level.
    """

    profile: Optional[dict[str, dict[str, Any]]] = Field(
        default=None,
        description="Profile data to update (merged with existing data)"
    )

    @field_validator("profile", mode="before")
    @classmethod
    def validate_profile(cls, v: Any) -> Optional[dict[str, dict[str, Any]]]:
        """Ensure profile is a properly structured dictionary if provided."""
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("profile must be a dictionary")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "core": {
                        "email": ["newemail@example.com", "alternate@example.com"]
                    }
                }
            }
        }
    )


class EntityResponse(BaseModel):
    """
    Model for entity data returned by the API.

    Contains the complete entity record including all profile data,
    file references, and metadata.
    """

    id: str = Field(
        ...,
        description="Unique entity identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Timestamp when the entity was created",
        examples=["2024-01-15T10:30:00"]
    )
    profile: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Complete profile data organized by section and field"
    )
    reports: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="List of associated report references"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john.doe@example.com"],
                        "date_of_birth": ["1990-01-15"]
                    },
                    "social": {
                        "linkedin": [{
                            "url": "https://linkedin.com/in/johndoe",
                            "username": "johndoe"
                        }]
                    },
                    "Tagged People": {
                        "tagged_people": ["other-person-uuid-1", "other-person-uuid-2"],
                        "transitive_relationships": ["transitive-person-uuid-1"]
                    }
                },
                "reports": [
                    {"name": "initial_report.md", "created_at": "2024-01-16T14:00:00"}
                ]
            }
        }
    )


class EntityList(BaseModel):
    """
    Model for a list of entities.

    Used for listing all entities in a project with optional pagination.
    """

    entities: list[EntityResponse] = Field(
        default_factory=list,
        description="List of entity records"
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of entities in the project"
    )
    project_safe_name: str = Field(
        ...,
        description="Safe name of the containing project",
        examples=["operation_sunrise"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entities": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-15T10:30:00",
                        "profile": {
                            "core": {
                                "name": [{"first_name": "John", "last_name": "Doe"}]
                            }
                        }
                    }
                ],
                "total": 1,
                "project_safe_name": "operation_sunrise"
            }
        }
    )
