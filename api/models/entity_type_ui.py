"""
Pydantic Models for Entity Type UI Configuration.

This module provides data models for entity type UI configuration,
including field definitions, type configurations, statistics, and
cross-type relationship options for the Basset Hound OSINT platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class FieldUIType(str, Enum):
    """
    Enumeration of supported UI field types.

    These define how fields should be rendered in forms and display views.
    """
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    NUMBER = "number"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    TAGS = "tags"
    FILE = "file"
    IMAGE = "image"
    LOCATION = "location"
    CURRENCY = "currency"
    PASSWORD = "password"
    HIDDEN = "hidden"


class FieldValidation(BaseModel):
    """
    Validation rules for a form field.

    Defines constraints that must be satisfied for field values.
    """

    min_length: Optional[int] = Field(
        default=None,
        description="Minimum string length",
        ge=0
    )
    max_length: Optional[int] = Field(
        default=None,
        description="Maximum string length",
        ge=0
    )
    min_value: Optional[float] = Field(
        default=None,
        description="Minimum numeric value"
    )
    max_value: Optional[float] = Field(
        default=None,
        description="Maximum numeric value"
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern for validation",
        max_length=500
    )
    pattern_error: Optional[str] = Field(
        default=None,
        description="Custom error message for pattern validation",
        max_length=200
    )
    allowed_extensions: Optional[List[str]] = Field(
        default=None,
        description="Allowed file extensions (for file/image fields)"
    )
    max_file_size: Optional[int] = Field(
        default=None,
        description="Maximum file size in bytes",
        ge=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[a-zA-Z\s]+$",
                "pattern_error": "Name must contain only letters and spaces"
            }
        }
    )


class SelectOption(BaseModel):
    """
    Option for select/multiselect fields.
    """

    value: str = Field(..., description="Option value")
    label: str = Field(..., description="Display label")
    description: Optional[str] = Field(
        default=None,
        description="Optional description/tooltip"
    )
    icon: Optional[str] = Field(
        default=None,
        description="Optional FontAwesome icon class"
    )
    disabled: bool = Field(
        default=False,
        description="Whether option is disabled"
    )


class FieldUIConfig(BaseModel):
    """
    UI configuration for a single form field.

    Defines how a field should be rendered, validated, and displayed
    in the user interface.
    """

    id: str = Field(
        ...,
        description="Unique field identifier",
        min_length=1,
        max_length=100
    )
    label: str = Field(
        ...,
        description="Display label for the field",
        min_length=1,
        max_length=100
    )
    type: FieldUIType = Field(
        default=FieldUIType.TEXT,
        description="UI component type for the field"
    )
    required: bool = Field(
        default=False,
        description="Whether the field is required"
    )
    placeholder: Optional[str] = Field(
        default=None,
        description="Placeholder text for input fields",
        max_length=200
    )
    help_text: Optional[str] = Field(
        default=None,
        description="Help text displayed below the field",
        max_length=500
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value for the field"
    )
    options: Optional[List[SelectOption]] = Field(
        default=None,
        description="Options for select/multiselect fields"
    )
    validation: Optional[FieldValidation] = Field(
        default=None,
        description="Validation rules for the field"
    )
    readonly: bool = Field(
        default=False,
        description="Whether the field is read-only"
    )
    hidden: bool = Field(
        default=False,
        description="Whether the field is hidden in forms"
    )
    order: int = Field(
        default=0,
        description="Display order within section",
        ge=0
    )
    width: Optional[str] = Field(
        default=None,
        description="CSS width (e.g., '50%', '200px')"
    )
    depends_on: Optional[str] = Field(
        default=None,
        description="Field ID this field depends on for visibility"
    )
    depends_value: Optional[Any] = Field(
        default=None,
        description="Value that triggers visibility"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "email",
                "label": "Email Address",
                "type": "email",
                "required": True,
                "placeholder": "Enter email address",
                "help_text": "Primary contact email",
                "validation": {
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    "pattern_error": "Please enter a valid email address"
                }
            }
        }
    )


class SectionUIConfig(BaseModel):
    """
    UI configuration for a form section.

    Sections group related fields together in the UI.
    """

    id: str = Field(
        ...,
        description="Unique section identifier",
        min_length=1,
        max_length=100
    )
    label: str = Field(
        ...,
        description="Display label for the section",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        default=None,
        description="Section description/help text",
        max_length=500
    )
    icon: Optional[str] = Field(
        default=None,
        description="FontAwesome icon class",
        max_length=50
    )
    fields: List[FieldUIConfig] = Field(
        default_factory=list,
        description="Fields within this section"
    )
    collapsible: bool = Field(
        default=True,
        description="Whether section can be collapsed"
    )
    collapsed_by_default: bool = Field(
        default=False,
        description="Whether section starts collapsed"
    )
    order: int = Field(
        default=0,
        description="Display order among sections",
        ge=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "contact",
                "label": "Contact Information",
                "description": "Email, phone, and other contact details",
                "icon": "fa-address-book",
                "collapsible": True,
                "collapsed_by_default": False,
                "order": 2
            }
        }
    )


class EntityTypeUIConfig(BaseModel):
    """
    Complete UI configuration for an entity type.

    Defines the visual representation, form fields, and behavior
    for a specific entity type in the Basset Hound UI.
    """

    type: str = Field(
        ...,
        description="Entity type identifier (e.g., 'person', 'organization')",
        min_length=1,
        max_length=50
    )
    icon: str = Field(
        default="fa-circle",
        description="FontAwesome icon class for the entity type",
        max_length=50
    )
    color: str = Field(
        default="#6c757d",
        description="Theme color for the entity type (CSS color)",
        pattern=r"^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$"
    )
    label: str = Field(
        ...,
        description="Singular display name",
        min_length=1,
        max_length=50
    )
    plural_label: str = Field(
        ...,
        description="Plural display name",
        min_length=1,
        max_length=50
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the entity type",
        max_length=500
    )
    sections: List[SectionUIConfig] = Field(
        default_factory=list,
        description="Form sections with their fields"
    )
    fields: List[FieldUIConfig] = Field(
        default_factory=list,
        description="Flat list of all fields (convenience accessor)"
    )
    primary_name_field: str = Field(
        default="name",
        description="Field used as the primary display name"
    )
    primary_name_section: str = Field(
        default="core",
        description="Section containing the primary name field"
    )
    searchable_fields: List[str] = Field(
        default_factory=list,
        description="Field IDs included in search"
    )
    list_display_fields: List[str] = Field(
        default_factory=list,
        description="Field IDs shown in list views"
    )
    badge_field: Optional[str] = Field(
        default=None,
        description="Field ID used for badge/chip display"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "person",
                "icon": "fa-user",
                "color": "#3498db",
                "label": "Person",
                "plural_label": "People",
                "description": "Individual people being investigated",
                "primary_name_field": "name",
                "primary_name_section": "core",
                "searchable_fields": ["name", "email", "phone"],
                "list_display_fields": ["name", "email", "created_at"]
            }
        }
    )


class EntityTypeStats(BaseModel):
    """
    Statistics for an entity type within a project.

    Provides counts and metadata about entities of a specific type.
    """

    type: str = Field(
        ...,
        description="Entity type identifier"
    )
    count: int = Field(
        default=0,
        description="Total count of entities of this type",
        ge=0
    )
    percentage: float = Field(
        default=0.0,
        description="Percentage of total entities in project",
        ge=0.0,
        le=100.0
    )
    last_created: Optional[datetime] = Field(
        default=None,
        description="Timestamp of most recently created entity"
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        description="Timestamp of most recently updated entity"
    )
    has_orphans: bool = Field(
        default=False,
        description="Whether there are entities without relationships"
    )
    orphan_count: int = Field(
        default=0,
        description="Count of entities without relationships",
        ge=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "person",
                "count": 150,
                "percentage": 65.2,
                "last_created": "2024-01-15T10:30:00",
                "last_updated": "2024-01-16T14:00:00",
                "has_orphans": True,
                "orphan_count": 12
            }
        }
    )


class ProjectEntityTypeStats(BaseModel):
    """
    Complete entity type statistics for a project.
    """

    project_safe_name: str = Field(
        ...,
        description="Project identifier"
    )
    total_entities: int = Field(
        default=0,
        description="Total entities across all types",
        ge=0
    )
    type_stats: List[EntityTypeStats] = Field(
        default_factory=list,
        description="Statistics per entity type"
    )
    dominant_type: Optional[str] = Field(
        default=None,
        description="Entity type with highest count"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_safe_name": "operation_sunrise",
                "total_entities": 230,
                "dominant_type": "person",
                "type_stats": [
                    {"type": "person", "count": 150, "percentage": 65.2},
                    {"type": "organization", "count": 50, "percentage": 21.7},
                    {"type": "location", "count": 30, "percentage": 13.1}
                ]
            }
        }
    )


class CrossTypeRelationshipOption(BaseModel):
    """
    A valid relationship type between two entity types.

    Defines how entities of different types can be connected.
    """

    relationship_type: str = Field(
        ...,
        description="Relationship type name (e.g., 'EMPLOYED_BY')"
    )
    display_label: str = Field(
        ...,
        description="Human-readable label"
    )
    inverse_type: Optional[str] = Field(
        default=None,
        description="Inverse relationship type (if any)"
    )
    inverse_label: Optional[str] = Field(
        default=None,
        description="Human-readable label for inverse"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the relationship"
    )
    is_symmetric: bool = Field(
        default=False,
        description="Whether relationship is symmetric"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relationship_type": "EMPLOYED_BY",
                "display_label": "Employed By",
                "inverse_type": "EMPLOYS",
                "inverse_label": "Employs",
                "description": "Person is employed by organization",
                "is_symmetric": False
            }
        }
    )


class CrossTypeRelationships(BaseModel):
    """
    Valid relationship types between a source and target entity type.
    """

    source_type: str = Field(
        ...,
        description="Source entity type"
    )
    target_type: str = Field(
        ...,
        description="Target entity type"
    )
    relationship_types: List[CrossTypeRelationshipOption] = Field(
        default_factory=list,
        description="Valid relationship types"
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether relationships can go both directions"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_type": "person",
                "target_type": "organization",
                "bidirectional": True,
                "relationship_types": [
                    {
                        "relationship_type": "EMPLOYED_BY",
                        "display_label": "Employed By",
                        "inverse_type": "EMPLOYS",
                        "inverse_label": "Employs"
                    },
                    {
                        "relationship_type": "FOUNDED",
                        "display_label": "Founded",
                        "inverse_type": "FOUNDED_BY",
                        "inverse_label": "Founded By"
                    }
                ]
            }
        }
    )


class EntityValidationResult(BaseModel):
    """
    Result of validating entity data against its type schema.
    """

    valid: bool = Field(
        ...,
        description="Whether the entity data is valid"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    missing_required: List[str] = Field(
        default_factory=list,
        description="List of missing required field IDs"
    )
    invalid_fields: List[str] = Field(
        default_factory=list,
        description="List of field IDs with invalid values"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "valid": False,
                "errors": [
                    {"field": "email", "message": "Invalid email format"},
                    {"field": "name", "message": "Required field is empty"}
                ],
                "warnings": [
                    {"field": "phone", "message": "Phone number format may not be recognized"}
                ],
                "missing_required": ["name"],
                "invalid_fields": ["email"]
            }
        }
    )


class EntityTypeIconResponse(BaseModel):
    """
    Response model for entity type icon endpoint.
    """

    type: str = Field(..., description="Entity type identifier")
    icon: str = Field(..., description="FontAwesome icon class")
    color: str = Field(..., description="Theme color for the type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "person",
                "icon": "fa-user",
                "color": "#3498db"
            }
        }
    )


class EntityTypeListResponse(BaseModel):
    """
    Response model for listing all entity types.
    """

    entity_types: List[EntityTypeUIConfig] = Field(
        default_factory=list,
        description="List of all entity type configurations"
    )
    total: int = Field(
        default=0,
        description="Total number of entity types",
        ge=0
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 6,
                "entity_types": [
                    {
                        "type": "person",
                        "icon": "fa-user",
                        "color": "#3498db",
                        "label": "Person",
                        "plural_label": "People"
                    }
                ]
            }
        }
    )
