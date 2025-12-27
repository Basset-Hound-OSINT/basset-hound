"""
Pydantic models for Project management.

Projects are the top-level containers for investigations, containing
people/entities and their associated data, files, and relationships.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class ProjectBase(BaseModel):
    """Base model for project data with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable project name",
        examples=["Operation Sunrise", "Background Check - John Doe"]
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure project name is not empty after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty or whitespace only")
        return stripped


class ProjectCreate(ProjectBase):
    """
    Model for creating a new project.

    The safe_name will be auto-generated from the name if not provided.
    The safe_name is used as a URL-safe identifier for the project.
    """

    safe_name: Optional[str] = Field(
        default=None,
        pattern=r"^[a-z0-9_]+$",
        max_length=255,
        description="URL-safe project identifier (auto-generated if not provided)",
        examples=["operation_sunrise", "background_check_john_doe"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Operation Sunrise",
                "safe_name": "operation_sunrise"
            }
        }
    )

    @field_validator("safe_name", mode="before")
    @classmethod
    def generate_safe_name(cls, v: Optional[str], info) -> Optional[str]:
        """
        Validate or generate a URL-safe name.

        If safe_name is provided, validate it matches the pattern.
        If not provided, it will be None and generated server-side from name.
        """
        if v is not None:
            v = v.strip().lower()
            if not re.match(r"^[a-z0-9_]+$", v):
                raise ValueError(
                    "safe_name must contain only lowercase letters, numbers, and underscores"
                )
        return v


class ProjectResponse(BaseModel):
    """
    Model for project data returned by the API.

    Contains all project metadata including creation timestamp
    and the auto-generated ID.
    """

    id: str = Field(
        ...,
        description="Unique project identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    name: str = Field(
        ...,
        description="Human-readable project name",
        examples=["Operation Sunrise"]
    )
    safe_name: str = Field(
        ...,
        description="URL-safe project identifier",
        examples=["operation_sunrise"]
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the project was created",
        examples=["2024-01-15T10:30:00Z"]
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Project start date (defaults to creation time)",
        examples=["2024-01-15T10:30:00Z"]
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Operation Sunrise",
                "safe_name": "operation_sunrise",
                "created_at": "2024-01-15T10:30:00Z",
                "start_date": "2024-01-15T10:30:00Z"
            }
        }
    )


class ProjectList(BaseModel):
    """
    Model for a paginated list of projects.

    Used for listing all projects with optional pagination support.
    """

    projects: list[ProjectResponse] = Field(
        default_factory=list,
        description="List of project summaries"
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of projects"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "projects": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Operation Sunrise",
                        "safe_name": "operation_sunrise",
                        "created_at": "2024-01-15T10:30:00Z",
                        "start_date": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )
