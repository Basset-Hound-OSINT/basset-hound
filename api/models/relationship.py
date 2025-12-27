"""
Pydantic models for Relationship (Tagging) management.

Relationships represent connections between entities, including:
- Direct tags: One person tagged as related to another
- Transitive relationships: Indirect connections through shared tags
- Named relationship types: WORKS_WITH, KNOWS, FAMILY, etc.
- Relationship properties: confidence, source, notes, timestamp

These are stored in the entity's profile under the "Tagged People" section.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class RelationshipType(str, Enum):
    """
    Enumeration of named relationship types between entities.

    These types describe the nature of the connection between two people
    in an OSINT investigation context.
    """
    # Generic relationships
    RELATED_TO = "RELATED_TO"
    KNOWS = "KNOWS"

    # Professional relationships
    WORKS_WITH = "WORKS_WITH"
    BUSINESS_PARTNER = "BUSINESS_PARTNER"
    REPORTS_TO = "REPORTS_TO"
    MANAGES = "MANAGES"
    COLLEAGUE = "COLLEAGUE"
    CLIENT = "CLIENT"
    EMPLOYER = "EMPLOYER"
    EMPLOYEE = "EMPLOYEE"

    # Family relationships
    FAMILY = "FAMILY"
    MARRIED_TO = "MARRIED_TO"
    PARENT_OF = "PARENT_OF"
    CHILD_OF = "CHILD_OF"
    SIBLING_OF = "SIBLING_OF"
    SPOUSE = "SPOUSE"

    # Social relationships
    FRIEND = "FRIEND"
    ACQUAINTANCE = "ACQUAINTANCE"
    NEIGHBOR = "NEIGHBOR"

    # Organizational relationships
    MEMBER_OF = "MEMBER_OF"
    AFFILIATED_WITH = "AFFILIATED_WITH"

    # Adversarial/investigative relationships
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    SUSPECTED_ASSOCIATE = "SUSPECTED_ASSOCIATE"
    ALIAS_OF = "ALIAS_OF"

    # Communication relationships
    COMMUNICATES_WITH = "COMMUNICATES_WITH"
    CONTACTED = "CONTACTED"

    @classmethod
    def get_inverse(cls, rel_type: "RelationshipType") -> Optional["RelationshipType"]:
        """
        Get the inverse relationship type for bidirectional relationships.

        For example, PARENT_OF -> CHILD_OF, MANAGES -> REPORTS_TO.
        Returns None for symmetric relationships or if no inverse exists.
        """
        inverse_map = {
            cls.PARENT_OF: cls.CHILD_OF,
            cls.CHILD_OF: cls.PARENT_OF,
            cls.MANAGES: cls.REPORTS_TO,
            cls.REPORTS_TO: cls.MANAGES,
            cls.EMPLOYER: cls.EMPLOYEE,
            cls.EMPLOYEE: cls.EMPLOYER,
        }
        return inverse_map.get(rel_type)

    @classmethod
    def is_symmetric(cls, rel_type: "RelationshipType") -> bool:
        """
        Check if a relationship type is symmetric (same in both directions).

        For example, MARRIED_TO, SIBLING_OF, WORKS_WITH are symmetric.
        """
        symmetric_types = {
            cls.RELATED_TO,
            cls.KNOWS,
            cls.WORKS_WITH,
            cls.BUSINESS_PARTNER,
            cls.COLLEAGUE,
            cls.FAMILY,
            cls.MARRIED_TO,
            cls.SIBLING_OF,
            cls.SPOUSE,
            cls.FRIEND,
            cls.ACQUAINTANCE,
            cls.NEIGHBOR,
            cls.COMMUNICATES_WITH,
            cls.ASSOCIATED_WITH,
        }
        return rel_type in symmetric_types


class ConfidenceLevel(str, Enum):
    """
    Confidence level for relationship assertions.

    Indicates how confident we are that the relationship exists.
    """
    CONFIRMED = "confirmed"      # Verified through multiple sources
    HIGH = "high"                # Strong evidence
    MEDIUM = "medium"            # Some evidence
    LOW = "low"                  # Weak evidence or speculation
    UNVERIFIED = "unverified"    # Not yet verified


class RelationshipProperties(BaseModel):
    """
    Extended properties for a relationship between entities.

    These properties provide additional context about the relationship,
    including confidence level, source attribution, and notes.
    """

    relationship_type: RelationshipType = Field(
        default=RelationshipType.RELATED_TO,
        description="The type of relationship between entities"
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.UNVERIFIED,
        description="Confidence level in this relationship"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the relationship information (e.g., 'LinkedIn', 'public records')",
        max_length=500
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the relationship",
        max_length=2000
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When this relationship was established or discovered"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="When the relationship began (if known)"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="When the relationship ended (if applicable)"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this relationship is currently active"
    )
    verified_by: Optional[str] = Field(
        default=None,
        description="Who verified this relationship",
        max_length=200
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="When this relationship was verified"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relationship_type": "WORKS_WITH",
                "confidence": "high",
                "source": "LinkedIn profile",
                "notes": "Both listed as employees at Acme Corp",
                "timestamp": "2024-01-15T10:30:00Z",
                "is_active": True
            }
        }
    )


class RelationshipCreate(BaseModel):
    """
    Model for creating/updating relationships between entities.

    Sets the complete list of tagged entities and transitive relationships
    for a given entity. This replaces any existing tags.
    """

    tagged_ids: list[str] = Field(
        default_factory=list,
        description="List of entity IDs directly tagged/related to this entity",
        examples=[["uuid-person-1", "uuid-person-2"]]
    )
    transitive_relationships: list[str] = Field(
        default_factory=list,
        description="List of entity IDs transitively related (through shared connections)",
        examples=[["uuid-person-3"]]
    )
    relationship_types: Optional[Dict[str, RelationshipType]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship types"
    )
    relationship_properties: Optional[Dict[str, RelationshipProperties]] = Field(
        default=None,
        description="Mapping of entity IDs to full relationship properties"
    )

    @field_validator("tagged_ids", "transitive_relationships", mode="before")
    @classmethod
    def ensure_list(cls, v) -> list[str]:
        """Ensure the value is a list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if not isinstance(v, list):
            raise ValueError("Must be a list of entity IDs")
        return [str(item) for item in v]

    @field_validator("tagged_ids", "transitive_relationships")
    @classmethod
    def validate_unique_ids(cls, v: list[str]) -> list[str]:
        """Ensure all IDs are unique within each list."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate entity IDs are not allowed")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tagged_ids": [
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002"
                ],
                "transitive_relationships": [
                    "550e8400-e29b-41d4-a716-446655440003"
                ],
                "relationship_types": {
                    "550e8400-e29b-41d4-a716-446655440001": "WORKS_WITH",
                    "550e8400-e29b-41d4-a716-446655440002": "FRIEND"
                },
                "relationship_properties": {
                    "550e8400-e29b-41d4-a716-446655440001": {
                        "relationship_type": "WORKS_WITH",
                        "confidence": "high",
                        "source": "LinkedIn"
                    }
                }
            }
        }
    )


class NamedRelationshipCreate(BaseModel):
    """
    Model for creating a single named relationship with full properties.

    Used for the tag_entity endpoint to create a relationship with a
    specific type and properties.
    """

    relationship_type: RelationshipType = Field(
        default=RelationshipType.RELATED_TO,
        description="The type of relationship to create"
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.UNVERIFIED,
        description="Confidence level in this relationship"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the relationship information",
        max_length=500
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the relationship",
        max_length=2000
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether to create the inverse relationship on the target entity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relationship_type": "WORKS_WITH",
                "confidence": "high",
                "source": "Company website",
                "notes": "Both listed on the leadership team page",
                "bidirectional": True
            }
        }
    )


class RelationshipInfo(BaseModel):
    """
    Schema for relationship information with full details.
    """
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(
        default=RelationshipType.RELATED_TO,
        description="Type of relationship"
    )
    confidence: Optional[ConfidenceLevel] = Field(
        default=None,
        description="Confidence level"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of relationship info"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Notes about the relationship"
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When relationship was created/discovered"
    )
    is_transitive: bool = Field(
        default=False,
        description="Whether this is a transitive relationship"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "source_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_id": "550e8400-e29b-41d4-a716-446655440001",
                "relationship_type": "WORKS_WITH",
                "confidence": "high",
                "source": "LinkedIn",
                "notes": "Colleagues at same company",
                "timestamp": "2024-01-15T10:30:00Z",
                "is_transitive": False
            }
        }
    )


class RelationshipResponse(BaseModel):
    """
    Model for relationship data returned by the API.

    Shows all direct and transitive relationships for an entity,
    with optional entity details for each related person.
    """

    entity_id: str = Field(
        ...,
        description="ID of the entity whose relationships are being returned",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    tagged_ids: list[str] = Field(
        default_factory=list,
        description="List of directly tagged entity IDs"
    )
    transitive_relationships: list[str] = Field(
        default_factory=list,
        description="List of transitively related entity IDs"
    )
    relationship_types: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship type names"
    )
    relationship_details: Optional[Dict[str, RelationshipInfo]] = Field(
        default=None,
        description="Mapping of entity IDs to full relationship details"
    )
    tagged_entities: Optional[list[dict]] = Field(
        default=None,
        description="Optional: Full entity data for each tagged person"
    )
    transitive_entities: Optional[list[dict]] = Field(
        default=None,
        description="Optional: Full entity data for each transitive relationship"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "tagged_ids": [
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002"
                ],
                "transitive_relationships": [
                    "550e8400-e29b-41d4-a716-446655440003"
                ],
                "relationship_types": {
                    "550e8400-e29b-41d4-a716-446655440001": "WORKS_WITH",
                    "550e8400-e29b-41d4-a716-446655440002": "FRIEND"
                },
                "tagged_entities": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "profile": {"core": {"name": [{"first_name": "Jane", "last_name": "Smith"}]}}
                    }
                ],
                "transitive_entities": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440003",
                        "profile": {"core": {"name": [{"first_name": "Bob", "last_name": "Wilson"}]}}
                    }
                ]
            }
        }
    )


class RelationshipListResponse(BaseModel):
    """Schema for list of relationships with full details."""
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    count: int = Field(0, description="Total number of relationships")
    relationship_type_counts: Optional[Dict[str, int]] = Field(
        default=None,
        description="Count of relationships by type"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relationships": [
                    {
                        "source_id": "uuid-1",
                        "target_id": "uuid-2",
                        "relationship_type": "WORKS_WITH",
                        "confidence": "high"
                    }
                ],
                "count": 1,
                "relationship_type_counts": {
                    "WORKS_WITH": 5,
                    "FRIEND": 3,
                    "FAMILY": 2
                }
            }
        }
    )


class RelationshipBulkUpdate(BaseModel):
    """
    Model for bulk updating relationships across multiple entities.

    Allows setting relationships for multiple entities in a single request.
    """

    updates: list[dict] = Field(
        ...,
        min_length=1,
        description="List of relationship updates, each containing entity_id and relationships"
    )

    @field_validator("updates")
    @classmethod
    def validate_updates(cls, v: list[dict]) -> list[dict]:
        """Ensure each update has required fields."""
        for update in v:
            if "entity_id" not in update:
                raise ValueError("Each update must contain an entity_id")
            if "tagged_ids" not in update and "transitive_relationships" not in update:
                raise ValueError(
                    "Each update must contain at least one of: tagged_ids, transitive_relationships"
                )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "updates": [
                    {
                        "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                        "tagged_ids": ["550e8400-e29b-41d4-a716-446655440001"],
                        "transitive_relationships": [],
                        "relationship_types": {
                            "550e8400-e29b-41d4-a716-446655440001": "WORKS_WITH"
                        }
                    },
                    {
                        "entity_id": "550e8400-e29b-41d4-a716-446655440001",
                        "tagged_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                        "transitive_relationships": [],
                        "relationship_types": {
                            "550e8400-e29b-41d4-a716-446655440000": "WORKS_WITH"
                        }
                    }
                ]
            }
        }
    )


# Utility functions for relationship handling

def get_all_relationship_types() -> List[str]:
    """Return a list of all valid relationship type names."""
    return [rt.value for rt in RelationshipType]


def get_relationship_type_categories() -> Dict[str, List[str]]:
    """Return relationship types organized by category."""
    return {
        "generic": [
            RelationshipType.RELATED_TO.value,
            RelationshipType.KNOWS.value,
        ],
        "professional": [
            RelationshipType.WORKS_WITH.value,
            RelationshipType.BUSINESS_PARTNER.value,
            RelationshipType.REPORTS_TO.value,
            RelationshipType.MANAGES.value,
            RelationshipType.COLLEAGUE.value,
            RelationshipType.CLIENT.value,
            RelationshipType.EMPLOYER.value,
            RelationshipType.EMPLOYEE.value,
        ],
        "family": [
            RelationshipType.FAMILY.value,
            RelationshipType.MARRIED_TO.value,
            RelationshipType.PARENT_OF.value,
            RelationshipType.CHILD_OF.value,
            RelationshipType.SIBLING_OF.value,
            RelationshipType.SPOUSE.value,
        ],
        "social": [
            RelationshipType.FRIEND.value,
            RelationshipType.ACQUAINTANCE.value,
            RelationshipType.NEIGHBOR.value,
        ],
        "organizational": [
            RelationshipType.MEMBER_OF.value,
            RelationshipType.AFFILIATED_WITH.value,
        ],
        "investigative": [
            RelationshipType.ASSOCIATED_WITH.value,
            RelationshipType.SUSPECTED_ASSOCIATE.value,
            RelationshipType.ALIAS_OF.value,
        ],
        "communication": [
            RelationshipType.COMMUNICATES_WITH.value,
            RelationshipType.CONTACTED.value,
        ],
    }
