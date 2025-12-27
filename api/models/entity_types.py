"""
Entity Type Definitions for Multi-Entity Support (Phase 5).

This module provides the foundation for supporting multiple entity types
in Basset Hound, including Person, Organization, Device, Location, Event,
and Document. Each entity type has its own schema configuration defining
which fields and sections are relevant.

The system is designed for backwards compatibility - existing Person
entities continue to work exactly as before.
"""

from enum import Enum
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class EntityType(str, Enum):
    """
    Enumeration of supported entity types.

    These represent the fundamental categories of entities that can be
    tracked in Basset Hound for OSINT investigations and relationship
    management.
    """
    # Primary entity types
    PERSON = "person"
    ORGANIZATION = "organization"
    DEVICE = "device"
    LOCATION = "location"

    # Additional entity types for extended use cases
    EVENT = "event"
    DOCUMENT = "document"

    @classmethod
    def get_default(cls) -> "EntityType":
        """Return the default entity type (Person for backwards compatibility)."""
        return cls.PERSON

    @classmethod
    def get_all_values(cls) -> List[str]:
        """Return all entity type values as strings."""
        return [e.value for e in cls]

    @classmethod
    def from_string(cls, value: str) -> Optional["EntityType"]:
        """
        Convert a string to an EntityType, case-insensitive.
        Returns None if the value doesn't match any type.
        """
        if value is None:
            return None
        value_lower = value.lower().strip()
        for entity_type in cls:
            if entity_type.value == value_lower:
                return entity_type
        return None

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid entity type."""
        return cls.from_string(value) is not None


class EntityTypeConfig(BaseModel):
    """
    Configuration for an entity type.

    Defines the metadata and schema information for a specific entity type,
    including which sections and fields are available, display settings,
    and relationship constraints.
    """

    entity_type: EntityType = Field(
        ...,
        description="The entity type this configuration applies to"
    )
    display_name: str = Field(
        ...,
        description="Human-readable display name for the entity type",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of what this entity type represents",
        max_length=500
    )
    icon: str = Field(
        default="fa-circle",
        description="Font Awesome icon class for this entity type",
        max_length=50
    )
    color: Optional[str] = Field(
        default=None,
        description="CSS color for UI display (e.g., '#3498db')",
        pattern=r"^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$"
    )
    sections: List[str] = Field(
        default_factory=list,
        description="List of section IDs applicable to this entity type"
    )
    primary_name_field: str = Field(
        default="name",
        description="Field ID used as the primary display name"
    )
    primary_name_section: str = Field(
        default="core",
        description="Section ID containing the primary name field"
    )
    allowed_relationship_types: Optional[List[str]] = Field(
        default=None,
        description="Relationship types allowed for this entity type (None = all allowed)"
    )
    can_relate_to: Optional[List[str]] = Field(
        default=None,
        description="Entity types this type can form relationships with (None = all types)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "organization",
                "display_name": "Organization",
                "description": "Companies, groups, agencies, and other organizational entities",
                "icon": "fa-building",
                "color": "#2ecc71",
                "sections": ["org_identity", "org_contact", "org_structure"],
                "primary_name_field": "name",
                "primary_name_section": "org_identity"
            }
        }
    )


class FieldMapping(BaseModel):
    """
    Defines how fields map between entity types for cross-type operations.

    Used when converting entities between types or finding equivalent
    fields across different entity types.
    """

    source_type: EntityType = Field(..., description="Source entity type")
    source_section: str = Field(..., description="Source section ID")
    source_field: str = Field(..., description="Source field ID")
    target_type: EntityType = Field(..., description="Target entity type")
    target_section: str = Field(..., description="Target section ID")
    target_field: str = Field(..., description="Target field ID")
    transformation: Optional[str] = Field(
        default=None,
        description="Optional transformation to apply (e.g., 'lowercase', 'split_name')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_type": "person",
                "source_section": "employment",
                "source_field": "employer.company",
                "target_type": "organization",
                "target_section": "org_identity",
                "target_field": "name"
            }
        }
    )


class CrossTypeRelationship(BaseModel):
    """
    Defines a relationship pattern between different entity types.

    These patterns describe how entities of different types can be
    connected, with semantic meaning for the relationship.
    """

    source_type: EntityType = Field(..., description="Source entity type")
    target_type: EntityType = Field(..., description="Target entity type")
    relationship_name: str = Field(
        ...,
        description="Name of the relationship (e.g., 'EMPLOYED_BY', 'LOCATED_AT')",
        pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    inverse_name: Optional[str] = Field(
        default=None,
        description="Name of the inverse relationship (e.g., 'EMPLOYS')",
        pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the relationship"
    )
    is_symmetric: bool = Field(
        default=False,
        description="Whether the relationship is the same in both directions"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_type": "person",
                "target_type": "organization",
                "relationship_name": "EMPLOYED_BY",
                "inverse_name": "EMPLOYS",
                "description": "Person is employed by organization",
                "is_symmetric": False
            }
        }
    )


# =============================================================================
# DEFAULT ENTITY TYPE CONFIGURATIONS
# =============================================================================

# These configurations define the base settings for each entity type.
# They can be extended or overridden via data_config.yaml.

DEFAULT_ENTITY_TYPE_CONFIGS: Dict[EntityType, EntityTypeConfig] = {
    EntityType.PERSON: EntityTypeConfig(
        entity_type=EntityType.PERSON,
        display_name="Person",
        description="Individual people being investigated or tracked",
        icon="fa-user",
        color="#3498db",
        sections=[
            "profile_picture", "core", "contact", "social_major", "professional",
            "federated", "forums", "gaming", "international", "creator", "dating",
            "ecommerce", "financial", "technical", "devices", "employment",
            "credentials", "files", "file_metadata", "public_records",
            "breach_intelligence", "threat_presence", "infrastructure",
            "transportation", "radio_comms", "government_ids", "relationships",
            "Tagged People"
        ],
        primary_name_field="name",
        primary_name_section="core",
        can_relate_to=None  # Can relate to all types
    ),

    EntityType.ORGANIZATION: EntityTypeConfig(
        entity_type=EntityType.ORGANIZATION,
        display_name="Organization",
        description="Companies, groups, agencies, and other organizational entities",
        icon="fa-building",
        color="#2ecc71",
        sections=[
            "org_identity", "org_contact", "org_structure", "org_registration",
            "org_online_presence", "org_financial", "files", "Tagged People"
        ],
        primary_name_field="name",
        primary_name_section="org_identity",
        can_relate_to=None
    ),

    EntityType.DEVICE: EntityTypeConfig(
        entity_type=EntityType.DEVICE,
        display_name="Device",
        description="Phones, computers, IoT devices, and other hardware",
        icon="fa-mobile-alt",
        color="#e74c3c",
        sections=[
            "device_identity", "device_technical", "device_network",
            "device_location", "files", "Tagged People"
        ],
        primary_name_field="name",
        primary_name_section="device_identity",
        can_relate_to=[EntityType.PERSON.value, EntityType.ORGANIZATION.value, EntityType.LOCATION.value]
    ),

    EntityType.LOCATION: EntityTypeConfig(
        entity_type=EntityType.LOCATION,
        display_name="Location",
        description="Physical addresses, venues, regions, and geographic points",
        icon="fa-map-marker-alt",
        color="#9b59b6",
        sections=[
            "location_identity", "location_address", "location_coordinates",
            "location_metadata", "files", "Tagged People"
        ],
        primary_name_field="name",
        primary_name_section="location_identity",
        can_relate_to=None
    ),

    EntityType.EVENT: EntityTypeConfig(
        entity_type=EntityType.EVENT,
        display_name="Event",
        description="Incidents, meetings, transactions, and other time-bound occurrences",
        icon="fa-calendar-alt",
        color="#f39c12",
        sections=[
            "event_identity", "event_timing", "event_location",
            "event_participants", "files", "Tagged People"
        ],
        primary_name_field="name",
        primary_name_section="event_identity",
        can_relate_to=None
    ),

    EntityType.DOCUMENT: EntityTypeConfig(
        entity_type=EntityType.DOCUMENT,
        display_name="Document",
        description="Files, reports, evidence, and other document artifacts",
        icon="fa-file-alt",
        color="#1abc9c",
        sections=[
            "document_identity", "document_metadata", "document_content",
            "document_provenance", "files", "Tagged People"
        ],
        primary_name_field="title",
        primary_name_section="document_identity",
        can_relate_to=None
    ),
}


# =============================================================================
# DEFAULT CROSS-TYPE RELATIONSHIPS
# =============================================================================

DEFAULT_CROSS_TYPE_RELATIONSHIPS: List[CrossTypeRelationship] = [
    # Person <-> Organization
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.ORGANIZATION,
        relationship_name="EMPLOYED_BY",
        inverse_name="EMPLOYS",
        description="Person is/was employed by organization"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.ORGANIZATION,
        relationship_name="MEMBER_OF",
        inverse_name="HAS_MEMBER",
        description="Person is a member of organization"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.ORGANIZATION,
        relationship_name="FOUNDED",
        inverse_name="FOUNDED_BY",
        description="Person founded the organization"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.ORGANIZATION,
        relationship_name="OWNS",
        inverse_name="OWNED_BY",
        description="Person owns the organization"
    ),

    # Person <-> Device
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.DEVICE,
        relationship_name="OWNS_DEVICE",
        inverse_name="DEVICE_OWNED_BY",
        description="Person owns the device"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.DEVICE,
        relationship_name="USES",
        inverse_name="USED_BY",
        description="Person uses the device"
    ),

    # Person <-> Location
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.LOCATION,
        relationship_name="LIVES_AT",
        inverse_name="RESIDENCE_OF",
        description="Person lives at location"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.LOCATION,
        relationship_name="WORKS_AT",
        inverse_name="WORKPLACE_OF",
        description="Person works at location"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.LOCATION,
        relationship_name="VISITED",
        inverse_name="VISITED_BY",
        description="Person visited location"
    ),

    # Person <-> Event
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.EVENT,
        relationship_name="PARTICIPATED_IN",
        inverse_name="HAD_PARTICIPANT",
        description="Person participated in event"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.EVENT,
        relationship_name="ORGANIZED",
        inverse_name="ORGANIZED_BY",
        description="Person organized event"
    ),

    # Person <-> Document
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.DOCUMENT,
        relationship_name="AUTHORED",
        inverse_name="AUTHORED_BY",
        description="Person authored document"
    ),
    CrossTypeRelationship(
        source_type=EntityType.PERSON,
        target_type=EntityType.DOCUMENT,
        relationship_name="MENTIONED_IN",
        inverse_name="MENTIONS",
        description="Person is mentioned in document"
    ),

    # Organization <-> Location
    CrossTypeRelationship(
        source_type=EntityType.ORGANIZATION,
        target_type=EntityType.LOCATION,
        relationship_name="LOCATED_AT",
        inverse_name="LOCATION_OF",
        description="Organization is located at address"
    ),
    CrossTypeRelationship(
        source_type=EntityType.ORGANIZATION,
        target_type=EntityType.LOCATION,
        relationship_name="OPERATES_IN",
        inverse_name="OPERATING_AREA_OF",
        description="Organization operates in region"
    ),

    # Organization <-> Organization
    CrossTypeRelationship(
        source_type=EntityType.ORGANIZATION,
        target_type=EntityType.ORGANIZATION,
        relationship_name="SUBSIDIARY_OF",
        inverse_name="PARENT_OF",
        description="Organization is a subsidiary of another"
    ),
    CrossTypeRelationship(
        source_type=EntityType.ORGANIZATION,
        target_type=EntityType.ORGANIZATION,
        relationship_name="PARTNER_WITH",
        inverse_name="PARTNER_WITH",
        description="Organizations are partners",
        is_symmetric=True
    ),

    # Device <-> Location
    CrossTypeRelationship(
        source_type=EntityType.DEVICE,
        target_type=EntityType.LOCATION,
        relationship_name="LOCATED_AT",
        inverse_name="LOCATION_OF",
        description="Device is located at position"
    ),

    # Event <-> Location
    CrossTypeRelationship(
        source_type=EntityType.EVENT,
        target_type=EntityType.LOCATION,
        relationship_name="OCCURRED_AT",
        inverse_name="SITE_OF",
        description="Event occurred at location"
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_entity_type_config(entity_type: EntityType) -> EntityTypeConfig:
    """
    Get the configuration for a specific entity type.

    Returns the default configuration if no custom config exists.
    """
    return DEFAULT_ENTITY_TYPE_CONFIGS.get(entity_type)


def get_all_entity_type_configs() -> Dict[EntityType, EntityTypeConfig]:
    """Get all entity type configurations."""
    return DEFAULT_ENTITY_TYPE_CONFIGS.copy()


def get_cross_type_relationships(
    source_type: Optional[EntityType] = None,
    target_type: Optional[EntityType] = None
) -> List[CrossTypeRelationship]:
    """
    Get cross-type relationships, optionally filtered by source and/or target type.
    """
    relationships = DEFAULT_CROSS_TYPE_RELATIONSHIPS.copy()

    if source_type:
        relationships = [r for r in relationships if r.source_type == source_type]

    if target_type:
        relationships = [r for r in relationships if r.target_type == target_type]

    return relationships


def get_available_relationships_for_type(entity_type: EntityType) -> List[str]:
    """
    Get all relationship names available for a specific entity type.

    Includes both same-type relationships (from RelationshipType enum)
    and cross-type relationships.
    """
    from api.models.relationship import get_all_relationship_types

    relationships = set(get_all_relationship_types())

    # Add cross-type relationships where this type is the source
    for rel in DEFAULT_CROSS_TYPE_RELATIONSHIPS:
        if rel.source_type == entity_type:
            relationships.add(rel.relationship_name)
        if rel.target_type == entity_type and rel.inverse_name:
            relationships.add(rel.inverse_name)

    return sorted(list(relationships))


def can_entities_relate(
    source_type: EntityType,
    target_type: EntityType,
    relationship_name: Optional[str] = None
) -> bool:
    """
    Check if two entity types can form a relationship.

    Optionally checks if a specific relationship type is valid.
    """
    source_config = get_entity_type_config(source_type)

    if source_config is None:
        return False

    # Check if target type is allowed
    if source_config.can_relate_to is not None:
        if target_type.value not in source_config.can_relate_to:
            return False

    # Check if relationship type is valid (if specified)
    if relationship_name:
        allowed = source_config.allowed_relationship_types
        if allowed is not None and relationship_name not in allowed:
            return False

    return True


# =============================================================================
# ENTITY TYPE REGISTRY
# =============================================================================

class EntityTypeRegistry:
    """
    Registry for managing entity types and their configurations.

    This class provides a central point for registering, retrieving,
    and validating entity types. It supports dynamic registration
    of custom entity types from configuration.
    """

    def __init__(self):
        self._configs: Dict[EntityType, EntityTypeConfig] = DEFAULT_ENTITY_TYPE_CONFIGS.copy()
        self._cross_type_relationships: List[CrossTypeRelationship] = DEFAULT_CROSS_TYPE_RELATIONSHIPS.copy()

    def register_type(self, config: EntityTypeConfig) -> None:
        """Register or update an entity type configuration."""
        self._configs[config.entity_type] = config

    def get_config(self, entity_type: EntityType) -> Optional[EntityTypeConfig]:
        """Get the configuration for an entity type."""
        return self._configs.get(entity_type)

    def get_all_configs(self) -> Dict[EntityType, EntityTypeConfig]:
        """Get all registered entity type configurations."""
        return self._configs.copy()

    def get_all_types(self) -> List[EntityType]:
        """Get all registered entity types."""
        return list(self._configs.keys())

    def add_cross_type_relationship(self, relationship: CrossTypeRelationship) -> None:
        """Add a cross-type relationship definition."""
        self._cross_type_relationships.append(relationship)

    def get_cross_type_relationships(
        self,
        source_type: Optional[EntityType] = None,
        target_type: Optional[EntityType] = None
    ) -> List[CrossTypeRelationship]:
        """Get cross-type relationships, optionally filtered."""
        relationships = self._cross_type_relationships.copy()

        if source_type:
            relationships = [r for r in relationships if r.source_type == source_type]

        if target_type:
            relationships = [r for r in relationships if r.target_type == target_type]

        return relationships

    def is_type_registered(self, entity_type: EntityType) -> bool:
        """Check if an entity type is registered."""
        return entity_type in self._configs

    def get_sections_for_type(self, entity_type: EntityType) -> List[str]:
        """Get the list of section IDs for an entity type."""
        config = self.get_config(entity_type)
        return config.sections if config else []


# Global registry instance
_registry: Optional[EntityTypeRegistry] = None


def get_registry() -> EntityTypeRegistry:
    """Get the global entity type registry instance."""
    global _registry
    if _registry is None:
        _registry = EntityTypeRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry to defaults (useful for testing)."""
    global _registry
    _registry = None
