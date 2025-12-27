"""
Pydantic models for Configuration schema management.

The configuration defines the dynamic profile schema including:
- Sections: Groups of related fields (e.g., "core", "social", "devices")
- Fields: Individual data fields with types and validation
- Components: Sub-fields for complex field types

This schema is defined in data_config.yaml and drives the profile editor UI.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Valid field types supported by the system
VALID_FIELD_TYPES = {
    "string",       # Plain text
    "email",        # Email address with validation
    "url",          # URL with validation
    "date",         # Date field
    "password",     # Password (hidden in UI)
    "comment",      # Multi-line text/notes
    "file",         # File upload
    "component",    # Complex field with sub-components
    "ip_address",   # IP address
}


class ConfigComponent(BaseModel):
    """
    Model for a field component (sub-field).

    Components are used for complex field types that have multiple
    related values, like a social media account with URL and username.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique component identifier within the field",
        examples=["url", "username", "email"]
    )
    type: str = Field(
        default="string",
        description="Component data type",
        examples=["string", "url", "email", "file", "comment"]
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable label (defaults to id if not provided)",
        examples=["Profile URL", "Username"]
    )
    multiple: bool = Field(
        default=False,
        description="Whether multiple values are allowed for this component"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure the component type is valid."""
        if v not in VALID_FIELD_TYPES:
            raise ValueError(
                f"Invalid component type '{v}'. Must be one of: {', '.join(sorted(VALID_FIELD_TYPES))}"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "url",
                "type": "url",
                "label": "Profile URL",
                "multiple": False
            }
        }
    )


class ConfigField(BaseModel):
    """
    Model for a profile field definition.

    Fields define individual data points that can be collected
    for each entity. They can be simple (string, email, etc.)
    or complex (with components for structured data).
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique field identifier within the section",
        examples=["name", "email", "linkedin", "ip address"]
    )
    type: str = Field(
        default="string",
        description="Field data type",
        examples=["string", "email", "url", "file", "component"]
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable label (defaults to id if not provided)",
        examples=["Full Name", "Email Address", "LinkedIn Profile"]
    )
    multiple: bool = Field(
        default=False,
        description="Whether multiple values are allowed for this field"
    )
    components: Optional[list[ConfigComponent]] = Field(
        default=None,
        description="Sub-components for complex field types"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure the field type is valid."""
        if v not in VALID_FIELD_TYPES:
            raise ValueError(
                f"Invalid field type '{v}'. Must be one of: {', '.join(sorted(VALID_FIELD_TYPES))}"
            )
        return v

    @field_validator("components")
    @classmethod
    def validate_components(cls, v: Optional[list], info) -> Optional[list]:
        """Validate components if present."""
        if v is None:
            return None

        # Check for duplicate component IDs
        ids = [comp.id for comp in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate component IDs found within field")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "linkedin",
                "type": "component",
                "label": "LinkedIn",
                "multiple": True,
                "components": [
                    {"id": "url", "type": "url", "label": "Profile URL"},
                    {"id": "username", "type": "string", "label": "Username"},
                    {"id": "email", "type": "email", "label": "Email", "multiple": True}
                ]
            }
        }
    )


class ConfigSection(BaseModel):
    """
    Model for a profile section definition.

    Sections group related fields together in the UI.
    Examples: Personal Information, Social Media, Devices, etc.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique section identifier",
        examples=["core", "social", "devices", "Profile Picture Section"]
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable section name (defaults to id if not provided)",
        examples=["Personal Information", "Social Media", "Devices"]
    )
    label: Optional[str] = Field(
        default=None,
        description="Alternative to 'name' - human-readable section label",
        examples=["Personal Information"]
    )
    fields: list[ConfigField] = Field(
        default_factory=list,
        description="List of fields in this section"
    )

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: list) -> list:
        """Validate fields within the section."""
        # Check for duplicate field IDs
        ids = [field.id for field in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate field IDs found within section")
        return v

    def get_display_name(self) -> str:
        """Get the display name for the section."""
        return self.name or self.label or self.id

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "core",
                "name": "Personal Information",
                "fields": [
                    {
                        "id": "name",
                        "type": "string",
                        "multiple": True,
                        "components": [
                            {"id": "first_name", "type": "string"},
                            {"id": "middle_name", "type": "string"},
                            {"id": "last_name", "type": "string"}
                        ]
                    },
                    {"id": "email", "type": "email", "multiple": True},
                    {"id": "date_of_birth", "type": "date", "multiple": True}
                ]
            }
        }
    )


class ConfigResponse(BaseModel):
    """
    Model for the complete configuration schema.

    This represents the entire data_config.yaml structure
    defining all sections and fields for entity profiles.
    """

    sections: list[ConfigSection] = Field(
        default_factory=list,
        description="List of profile sections"
    )

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, v: list) -> list:
        """Validate sections for uniqueness."""
        # Check for duplicate section IDs
        ids = [section.id for section in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate section IDs found in configuration")
        return v

    def get_section(self, section_id: str) -> Optional[ConfigSection]:
        """Get a section by its ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def get_field(self, section_id: str, field_id: str) -> Optional[ConfigField]:
        """Get a field by section and field ID."""
        section = self.get_section(section_id)
        if section:
            for field in section.fields:
                if field.id == field_id:
                    return field
        return None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sections": [
                    {
                        "id": "Profile Picture Section",
                        "name": "Profile Picture",
                        "fields": [
                            {"id": "profilepicturefile", "type": "file"}
                        ]
                    },
                    {
                        "id": "core",
                        "name": "Personal Information",
                        "fields": [
                            {
                                "id": "name",
                                "type": "string",
                                "multiple": True,
                                "components": [
                                    {"id": "first_name", "type": "string"},
                                    {"id": "last_name", "type": "string"}
                                ]
                            },
                            {"id": "email", "type": "email", "multiple": True}
                        ]
                    },
                    {
                        "id": "social",
                        "name": "Social Media",
                        "fields": [
                            {
                                "id": "linkedin",
                                "type": "component",
                                "multiple": True,
                                "components": [
                                    {"id": "url", "type": "url"},
                                    {"id": "username", "type": "string"}
                                ]
                            }
                        ]
                    },
                    {
                        "id": "devices",
                        "name": "Devices",
                        "fields": [
                            {"id": "ip address", "type": "ip_address", "multiple": True}
                        ]
                    }
                ]
            }
        }
    )


class ConfigUpdate(BaseModel):
    """
    Model for updating the configuration schema.

    Allows updating the entire configuration with validation.
    Changes are persisted to data_config.yaml.
    """

    sections: list[ConfigSection] = Field(
        ...,
        min_length=1,
        description="Complete list of profile sections (replaces existing)"
    )

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, v: list) -> list:
        """Validate sections for uniqueness."""
        ids = [section.id for section in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate section IDs found in configuration")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sections": [
                    {
                        "id": "core",
                        "name": "Personal Information",
                        "fields": [
                            {"id": "name", "type": "string"},
                            {"id": "email", "type": "email", "multiple": True}
                        ]
                    }
                ]
            }
        }
    )
