"""
Entity Type UI Service for Basset Hound OSINT Platform.

This service provides UI-specific configuration and metadata for entity types,
including icons, colors, form field definitions, cross-type relationship options,
and entity type statistics per project.

The service builds upon the core entity type definitions in api/models/entity_types.py
and provides enhanced UI-focused data for frontend rendering.
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from api.models.entity_types import (
    EntityType,
    EntityTypeConfig,
    CrossTypeRelationship,
    DEFAULT_ENTITY_TYPE_CONFIGS,
    DEFAULT_CROSS_TYPE_RELATIONSHIPS,
    get_entity_type_config,
    get_all_entity_type_configs,
    get_registry,
)
from api.models.entity_type_ui import (
    EntityTypeUIConfig,
    FieldUIConfig,
    FieldUIType,
    FieldValidation,
    SelectOption,
    SectionUIConfig,
    EntityTypeStats,
    ProjectEntityTypeStats,
    CrossTypeRelationshipOption,
    CrossTypeRelationships,
    EntityValidationResult,
    EntityTypeIconResponse,
)


logger = logging.getLogger("basset_hound.entity_type_ui")


# =============================================================================
# DEFAULT FIELD CONFIGURATIONS BY ENTITY TYPE
# =============================================================================

# Maps entity types to their default field configurations.
# These provide sensible defaults for common fields per entity type.

DEFAULT_PERSON_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="name",
        label="Full Name",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter full name",
        help_text="Primary name for identification",
        order=1,
        validation=FieldValidation(min_length=1, max_length=200)
    ),
    FieldUIConfig(
        id="first_name",
        label="First Name",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="First name",
        order=2
    ),
    FieldUIConfig(
        id="last_name",
        label="Last Name",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Last name",
        order=3
    ),
    FieldUIConfig(
        id="email",
        label="Email Address",
        type=FieldUIType.EMAIL,
        required=False,
        placeholder="email@example.com",
        validation=FieldValidation(
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            pattern_error="Please enter a valid email address"
        ),
        order=4
    ),
    FieldUIConfig(
        id="phone",
        label="Phone Number",
        type=FieldUIType.PHONE,
        required=False,
        placeholder="+1 (555) 123-4567",
        order=5
    ),
    FieldUIConfig(
        id="date_of_birth",
        label="Date of Birth",
        type=FieldUIType.DATE,
        required=False,
        order=6
    ),
    FieldUIConfig(
        id="occupation",
        label="Occupation",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Job title or profession",
        order=7
    ),
    FieldUIConfig(
        id="notes",
        label="Notes",
        type=FieldUIType.TEXTAREA,
        required=False,
        placeholder="Additional notes and observations",
        order=100
    ),
]

DEFAULT_ORGANIZATION_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="name",
        label="Organization Name",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter organization name",
        help_text="Legal or common name of the organization",
        order=1,
        validation=FieldValidation(min_length=1, max_length=300)
    ),
    FieldUIConfig(
        id="type",
        label="Organization Type",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="company", label="Company"),
            SelectOption(value="nonprofit", label="Non-Profit"),
            SelectOption(value="government", label="Government Agency"),
            SelectOption(value="educational", label="Educational Institution"),
            SelectOption(value="political", label="Political Organization"),
            SelectOption(value="religious", label="Religious Organization"),
            SelectOption(value="criminal", label="Criminal Organization"),
            SelectOption(value="other", label="Other"),
        ],
        order=2
    ),
    FieldUIConfig(
        id="industry",
        label="Industry",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Primary industry or sector",
        order=3
    ),
    FieldUIConfig(
        id="founded_date",
        label="Founded Date",
        type=FieldUIType.DATE,
        required=False,
        order=4
    ),
    FieldUIConfig(
        id="website",
        label="Website",
        type=FieldUIType.URL,
        required=False,
        placeholder="https://example.com",
        order=5
    ),
    FieldUIConfig(
        id="headquarters",
        label="Headquarters Location",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="City, Country",
        order=6
    ),
    FieldUIConfig(
        id="employee_count",
        label="Employee Count",
        type=FieldUIType.NUMBER,
        required=False,
        validation=FieldValidation(min_value=0),
        order=7
    ),
    FieldUIConfig(
        id="description",
        label="Description",
        type=FieldUIType.TEXTAREA,
        required=False,
        placeholder="Organization description",
        order=100
    ),
]

DEFAULT_DEVICE_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="name",
        label="Device Name",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter device name or identifier",
        order=1
    ),
    FieldUIConfig(
        id="type",
        label="Device Type",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="phone", label="Phone", icon="fa-mobile-alt"),
            SelectOption(value="computer", label="Computer", icon="fa-laptop"),
            SelectOption(value="tablet", label="Tablet", icon="fa-tablet-alt"),
            SelectOption(value="server", label="Server", icon="fa-server"),
            SelectOption(value="router", label="Router/Network Device", icon="fa-network-wired"),
            SelectOption(value="iot", label="IoT Device", icon="fa-microchip"),
            SelectOption(value="vehicle", label="Vehicle", icon="fa-car"),
            SelectOption(value="other", label="Other"),
        ],
        order=2
    ),
    FieldUIConfig(
        id="manufacturer",
        label="Manufacturer",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Device manufacturer",
        order=3
    ),
    FieldUIConfig(
        id="model",
        label="Model",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Device model",
        order=4
    ),
    FieldUIConfig(
        id="serial_number",
        label="Serial Number",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Serial number",
        order=5
    ),
    FieldUIConfig(
        id="mac_address",
        label="MAC Address",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="00:00:00:00:00:00",
        validation=FieldValidation(
            pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
            pattern_error="Enter a valid MAC address"
        ),
        order=6
    ),
    FieldUIConfig(
        id="ip_address",
        label="IP Address",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="192.168.1.1",
        order=7
    ),
    FieldUIConfig(
        id="imei",
        label="IMEI",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="15-digit IMEI number",
        order=8
    ),
    FieldUIConfig(
        id="notes",
        label="Notes",
        type=FieldUIType.TEXTAREA,
        required=False,
        order=100
    ),
]

DEFAULT_LOCATION_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="name",
        label="Location Name",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter location name",
        help_text="Descriptive name for the location",
        order=1
    ),
    FieldUIConfig(
        id="type",
        label="Location Type",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="address", label="Physical Address"),
            SelectOption(value="city", label="City"),
            SelectOption(value="region", label="Region/State"),
            SelectOption(value="country", label="Country"),
            SelectOption(value="coordinates", label="GPS Coordinates"),
            SelectOption(value="venue", label="Venue/Building"),
            SelectOption(value="poi", label="Point of Interest"),
        ],
        order=2
    ),
    FieldUIConfig(
        id="address",
        label="Street Address",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="123 Main St",
        order=3
    ),
    FieldUIConfig(
        id="city",
        label="City",
        type=FieldUIType.TEXT,
        required=False,
        order=4
    ),
    FieldUIConfig(
        id="state",
        label="State/Province",
        type=FieldUIType.TEXT,
        required=False,
        order=5
    ),
    FieldUIConfig(
        id="country",
        label="Country",
        type=FieldUIType.TEXT,
        required=False,
        order=6
    ),
    FieldUIConfig(
        id="postal_code",
        label="Postal Code",
        type=FieldUIType.TEXT,
        required=False,
        order=7
    ),
    FieldUIConfig(
        id="latitude",
        label="Latitude",
        type=FieldUIType.NUMBER,
        required=False,
        validation=FieldValidation(min_value=-90, max_value=90),
        order=8
    ),
    FieldUIConfig(
        id="longitude",
        label="Longitude",
        type=FieldUIType.NUMBER,
        required=False,
        validation=FieldValidation(min_value=-180, max_value=180),
        order=9
    ),
    FieldUIConfig(
        id="description",
        label="Description",
        type=FieldUIType.TEXTAREA,
        required=False,
        order=100
    ),
]

DEFAULT_EVENT_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="name",
        label="Event Name",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter event name",
        order=1
    ),
    FieldUIConfig(
        id="type",
        label="Event Type",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="meeting", label="Meeting"),
            SelectOption(value="incident", label="Incident"),
            SelectOption(value="transaction", label="Transaction"),
            SelectOption(value="communication", label="Communication"),
            SelectOption(value="travel", label="Travel"),
            SelectOption(value="crime", label="Criminal Activity"),
            SelectOption(value="social", label="Social Event"),
            SelectOption(value="other", label="Other"),
        ],
        order=2
    ),
    FieldUIConfig(
        id="start_datetime",
        label="Start Date/Time",
        type=FieldUIType.DATETIME,
        required=False,
        order=3
    ),
    FieldUIConfig(
        id="end_datetime",
        label="End Date/Time",
        type=FieldUIType.DATETIME,
        required=False,
        order=4
    ),
    FieldUIConfig(
        id="duration",
        label="Duration",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="e.g., 2 hours, 3 days",
        order=5
    ),
    FieldUIConfig(
        id="location",
        label="Location",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Where the event occurred",
        order=6
    ),
    FieldUIConfig(
        id="description",
        label="Description",
        type=FieldUIType.TEXTAREA,
        required=False,
        placeholder="Detailed description of the event",
        order=100
    ),
]

DEFAULT_DOCUMENT_FIELDS: List[FieldUIConfig] = [
    FieldUIConfig(
        id="title",
        label="Document Title",
        type=FieldUIType.TEXT,
        required=True,
        placeholder="Enter document title",
        order=1
    ),
    FieldUIConfig(
        id="type",
        label="Document Type",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="report", label="Report"),
            SelectOption(value="evidence", label="Evidence"),
            SelectOption(value="correspondence", label="Correspondence"),
            SelectOption(value="financial", label="Financial Document"),
            SelectOption(value="legal", label="Legal Document"),
            SelectOption(value="technical", label="Technical Document"),
            SelectOption(value="media", label="Media/Image"),
            SelectOption(value="other", label="Other"),
        ],
        order=2
    ),
    FieldUIConfig(
        id="author",
        label="Author",
        type=FieldUIType.TEXT,
        required=False,
        order=3
    ),
    FieldUIConfig(
        id="date_created",
        label="Date Created",
        type=FieldUIType.DATE,
        required=False,
        order=4
    ),
    FieldUIConfig(
        id="source",
        label="Source",
        type=FieldUIType.TEXT,
        required=False,
        placeholder="Where the document was obtained",
        order=5
    ),
    FieldUIConfig(
        id="classification",
        label="Classification",
        type=FieldUIType.SELECT,
        required=False,
        options=[
            SelectOption(value="public", label="Public"),
            SelectOption(value="internal", label="Internal"),
            SelectOption(value="confidential", label="Confidential"),
            SelectOption(value="restricted", label="Restricted"),
        ],
        order=6
    ),
    FieldUIConfig(
        id="file_path",
        label="File",
        type=FieldUIType.FILE,
        required=False,
        order=7
    ),
    FieldUIConfig(
        id="summary",
        label="Summary",
        type=FieldUIType.TEXTAREA,
        required=False,
        placeholder="Brief summary of document contents",
        order=100
    ),
]

# Mapping of entity types to their field configurations
ENTITY_TYPE_FIELDS: Dict[EntityType, List[FieldUIConfig]] = {
    EntityType.PERSON: DEFAULT_PERSON_FIELDS,
    EntityType.ORGANIZATION: DEFAULT_ORGANIZATION_FIELDS,
    EntityType.DEVICE: DEFAULT_DEVICE_FIELDS,
    EntityType.LOCATION: DEFAULT_LOCATION_FIELDS,
    EntityType.EVENT: DEFAULT_EVENT_FIELDS,
    EntityType.DOCUMENT: DEFAULT_DOCUMENT_FIELDS,
}


# =============================================================================
# ENTITY TYPE UI SERVICE
# =============================================================================

class EntityTypeUIService:
    """
    Service for entity type UI configuration and metadata.

    Provides methods to retrieve UI-specific configuration for entity types,
    including icons, colors, form fields, cross-type relationships, and
    per-project entity type statistics.
    """

    def __init__(self, neo4j_handler=None):
        """
        Initialize the Entity Type UI Service.

        Args:
            neo4j_handler: Optional Neo4j database handler for statistics queries.
                          If not provided, statistics methods will return empty results.
        """
        self.neo4j = neo4j_handler
        self._registry = get_registry()

    def get_entity_type_config(self, entity_type: str) -> Optional[EntityTypeUIConfig]:
        """
        Get the full UI configuration for an entity type.

        Args:
            entity_type: Entity type identifier (e.g., 'person', 'organization')

        Returns:
            EntityTypeUIConfig with complete UI configuration, or None if type not found.
        """
        # Convert string to EntityType enum
        entity_type_enum = EntityType.from_string(entity_type)
        if entity_type_enum is None:
            logger.warning(f"Unknown entity type: {entity_type}")
            return None

        # Get base configuration
        base_config = self._registry.get_config(entity_type_enum)
        if base_config is None:
            return None

        # Get fields for this type
        fields = self.get_entity_type_fields(entity_type)

        # Build sections from fields
        sections = self._build_sections_from_fields(entity_type_enum, fields)

        # Get plural label
        plural_label = self._get_plural_label(base_config.display_name)

        return EntityTypeUIConfig(
            type=entity_type_enum.value,
            icon=base_config.icon,
            color=base_config.color or "#6c757d",
            label=base_config.display_name,
            plural_label=plural_label,
            description=base_config.description,
            sections=sections,
            fields=fields,
            primary_name_field=base_config.primary_name_field,
            primary_name_section=base_config.primary_name_section,
            searchable_fields=self._get_searchable_fields(entity_type_enum),
            list_display_fields=self._get_list_display_fields(entity_type_enum),
        )

    def get_all_entity_type_configs(self) -> List[EntityTypeUIConfig]:
        """
        Get UI configurations for all entity types.

        Returns:
            List of EntityTypeUIConfig for all registered entity types.
        """
        configs = []
        for entity_type in EntityType:
            config = self.get_entity_type_config(entity_type.value)
            if config:
                configs.append(config)
        return configs

    def get_entity_type_icon(self, entity_type: str) -> Optional[EntityTypeIconResponse]:
        """
        Get the FontAwesome icon class for an entity type.

        Args:
            entity_type: Entity type identifier

        Returns:
            EntityTypeIconResponse with icon and color, or None if type not found.
        """
        entity_type_enum = EntityType.from_string(entity_type)
        if entity_type_enum is None:
            return None

        config = self._registry.get_config(entity_type_enum)
        if config is None:
            return None

        return EntityTypeIconResponse(
            type=entity_type_enum.value,
            icon=config.icon,
            color=config.color or "#6c757d"
        )

    def get_entity_type_color(self, entity_type: str) -> Optional[str]:
        """
        Get the theme color for an entity type.

        Args:
            entity_type: Entity type identifier

        Returns:
            CSS color string (e.g., '#3498db'), or None if type not found.
        """
        entity_type_enum = EntityType.from_string(entity_type)
        if entity_type_enum is None:
            return None

        config = self._registry.get_config(entity_type_enum)
        if config is None:
            return None

        return config.color or "#6c757d"

    def get_entity_type_fields(self, entity_type: str) -> List[FieldUIConfig]:
        """
        Get field definitions for an entity type's forms.

        Args:
            entity_type: Entity type identifier

        Returns:
            List of FieldUIConfig defining the form fields.
        """
        entity_type_enum = EntityType.from_string(entity_type)
        if entity_type_enum is None:
            return []

        fields = ENTITY_TYPE_FIELDS.get(entity_type_enum, [])
        return sorted(fields, key=lambda f: f.order)

    def get_cross_type_relationship_options(
        self,
        source_type: str,
        target_type: str
    ) -> CrossTypeRelationships:
        """
        Get valid relationship types between two entity types.

        Args:
            source_type: Source entity type identifier
            target_type: Target entity type identifier

        Returns:
            CrossTypeRelationships with valid relationship options.
        """
        source_enum = EntityType.from_string(source_type)
        target_enum = EntityType.from_string(target_type)

        if source_enum is None or target_enum is None:
            return CrossTypeRelationships(
                source_type=source_type,
                target_type=target_type,
                relationship_types=[],
                bidirectional=False
            )

        # Find matching cross-type relationships
        relationships: List[CrossTypeRelationshipOption] = []
        bidirectional = False

        for rel in DEFAULT_CROSS_TYPE_RELATIONSHIPS:
            # Check forward direction
            if rel.source_type == source_enum and rel.target_type == target_enum:
                relationships.append(CrossTypeRelationshipOption(
                    relationship_type=rel.relationship_name,
                    display_label=self._format_relationship_label(rel.relationship_name),
                    inverse_type=rel.inverse_name,
                    inverse_label=self._format_relationship_label(rel.inverse_name) if rel.inverse_name else None,
                    description=rel.description,
                    is_symmetric=rel.is_symmetric
                ))

            # Check reverse direction
            if rel.target_type == source_enum and rel.source_type == target_enum:
                bidirectional = True
                if rel.inverse_name:
                    relationships.append(CrossTypeRelationshipOption(
                        relationship_type=rel.inverse_name,
                        display_label=self._format_relationship_label(rel.inverse_name),
                        inverse_type=rel.relationship_name,
                        inverse_label=self._format_relationship_label(rel.relationship_name),
                        description=f"Inverse: {rel.description}" if rel.description else None,
                        is_symmetric=rel.is_symmetric
                    ))

        # Add generic relationships that work between any types
        generic_relationships = self._get_generic_relationships()
        relationships.extend(generic_relationships)

        return CrossTypeRelationships(
            source_type=source_type,
            target_type=target_type,
            relationship_types=relationships,
            bidirectional=bidirectional
        )

    def get_entity_type_statistics(
        self,
        project_id: str
    ) -> ProjectEntityTypeStats:
        """
        Get count of each entity type in a project.

        Args:
            project_id: Project safe name or ID

        Returns:
            ProjectEntityTypeStats with counts for each entity type.
        """
        if self.neo4j is None:
            logger.warning("Neo4j handler not available for statistics query")
            return ProjectEntityTypeStats(
                project_safe_name=project_id,
                total_entities=0,
                type_stats=[],
                dominant_type=None
            )

        try:
            # Query entities from Neo4j
            with self.neo4j.driver.session() as session:
                # Get all entities with their types
                query = """
                    MATCH (project:Project {safe_name: $project_id})
                          -[:HAS_PERSON]->(entity:Person)
                    RETURN entity.id AS id,
                           entity.profile AS profile,
                           entity.created_at AS created_at,
                           entity.entity_type AS entity_type
                    ORDER BY entity.created_at DESC
                """
                result = session.run(query, project_id=project_id)

                # Aggregate by type
                type_counts: Dict[str, int] = {}
                type_last_created: Dict[str, datetime] = {}
                total_entities = 0

                for record in result:
                    total_entities += 1

                    # Get entity type from record or profile
                    entity_type = record.get("entity_type")
                    if not entity_type:
                        profile = record.get("profile") or {}
                        entity_type = profile.get("entity_type", EntityType.PERSON.value)

                    # Normalize to lowercase
                    if isinstance(entity_type, str):
                        entity_type = entity_type.lower()
                    else:
                        entity_type = EntityType.PERSON.value

                    # Update counts
                    type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

                    # Track last created
                    created_at = record.get("created_at")
                    if created_at:
                        if isinstance(created_at, str):
                            try:
                                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                                if entity_type not in type_last_created or created_dt > type_last_created[entity_type]:
                                    type_last_created[entity_type] = created_dt
                            except ValueError:
                                pass

                # Build stats list
                type_stats: List[EntityTypeStats] = []
                dominant_type = None
                max_count = 0

                for entity_type in EntityType:
                    count = type_counts.get(entity_type.value, 0)
                    percentage = (count / total_entities * 100) if total_entities > 0 else 0.0

                    if count > max_count:
                        max_count = count
                        dominant_type = entity_type.value

                    type_stats.append(EntityTypeStats(
                        type=entity_type.value,
                        count=count,
                        percentage=round(percentage, 2),
                        last_created=type_last_created.get(entity_type.value)
                    ))

                return ProjectEntityTypeStats(
                    project_safe_name=project_id,
                    total_entities=total_entities,
                    type_stats=type_stats,
                    dominant_type=dominant_type
                )

        except Exception as e:
            logger.error(f"Error getting entity type statistics: {e}")
            return ProjectEntityTypeStats(
                project_safe_name=project_id,
                total_entities=0,
                type_stats=[],
                dominant_type=None
            )

    def validate_entity_for_type(
        self,
        entity_type: str,
        profile: Dict[str, Any]
    ) -> EntityValidationResult:
        """
        Validate profile data against an entity type's schema.

        Args:
            entity_type: Entity type identifier
            profile: Profile data dictionary to validate

        Returns:
            EntityValidationResult with validation status and any errors/warnings.
        """
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        missing_required: List[str] = []
        invalid_fields: List[str] = []

        # Get fields for this type
        fields = self.get_entity_type_fields(entity_type)
        if not fields:
            # Unknown entity type
            errors.append({
                "field": "_entity_type",
                "message": f"Unknown entity type: {entity_type}"
            })
            return EntityValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                missing_required=missing_required,
                invalid_fields=invalid_fields
            )

        # Flatten profile data for validation
        flat_profile = self._flatten_profile(profile)

        # Validate each field
        for field in fields:
            field_value = flat_profile.get(field.id)

            # Check required fields
            if field.required:
                if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                    errors.append({
                        "field": field.id,
                        "message": f"Required field '{field.label}' is empty"
                    })
                    missing_required.append(field.id)
                    continue

            # Skip validation if no value
            if field_value is None or field_value == "":
                continue

            # Type-specific validation
            validation_error = self._validate_field_value(field, field_value)
            if validation_error:
                errors.append({
                    "field": field.id,
                    "message": validation_error
                })
                invalid_fields.append(field.id)

            # Pattern validation
            if field.validation and field.validation.pattern:
                if isinstance(field_value, str):
                    if not re.match(field.validation.pattern, field_value):
                        error_msg = field.validation.pattern_error or f"Invalid format for {field.label}"
                        errors.append({
                            "field": field.id,
                            "message": error_msg
                        })
                        if field.id not in invalid_fields:
                            invalid_fields.append(field.id)

            # Length validation
            if field.validation:
                if isinstance(field_value, str):
                    if field.validation.min_length and len(field_value) < field.validation.min_length:
                        errors.append({
                            "field": field.id,
                            "message": f"{field.label} must be at least {field.validation.min_length} characters"
                        })
                        if field.id not in invalid_fields:
                            invalid_fields.append(field.id)
                    if field.validation.max_length and len(field_value) > field.validation.max_length:
                        errors.append({
                            "field": field.id,
                            "message": f"{field.label} must be at most {field.validation.max_length} characters"
                        })
                        if field.id not in invalid_fields:
                            invalid_fields.append(field.id)

                # Numeric range validation
                if isinstance(field_value, (int, float)):
                    if field.validation.min_value is not None and field_value < field.validation.min_value:
                        errors.append({
                            "field": field.id,
                            "message": f"{field.label} must be at least {field.validation.min_value}"
                        })
                        if field.id not in invalid_fields:
                            invalid_fields.append(field.id)
                    if field.validation.max_value is not None and field_value > field.validation.max_value:
                        errors.append({
                            "field": field.id,
                            "message": f"{field.label} must be at most {field.validation.max_value}"
                        })
                        if field.id not in invalid_fields:
                            invalid_fields.append(field.id)

        # Check for unknown fields (warnings only)
        known_field_ids = {f.id for f in fields}
        for field_id in flat_profile.keys():
            if field_id not in known_field_ids:
                warnings.append({
                    "field": field_id,
                    "message": f"Unknown field: {field_id}"
                })

        return EntityValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_required=missing_required,
            invalid_fields=invalid_fields
        )

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _get_plural_label(self, singular: str) -> str:
        """Get plural form of a label."""
        special_plurals = {
            "Person": "People",
            "person": "people",
        }
        if singular in special_plurals:
            return special_plurals[singular]

        # Simple pluralization rules
        if singular.endswith("y"):
            return singular[:-1] + "ies"
        elif singular.endswith(("s", "x", "z", "ch", "sh")):
            return singular + "es"
        else:
            return singular + "s"

    def _build_sections_from_fields(
        self,
        entity_type: EntityType,
        fields: List[FieldUIConfig]
    ) -> List[SectionUIConfig]:
        """Build section configurations from fields."""
        base_config = self._registry.get_config(entity_type)
        if not base_config:
            return []

        # Group fields into sections based on entity type
        section_map = self._get_section_mapping(entity_type)

        sections: List[SectionUIConfig] = []
        for section_id, section_info in section_map.items():
            section_fields = [f for f in fields if f.id in section_info.get("fields", [])]
            if not section_fields:
                # Include all fields in "core" section if no specific mapping
                if section_id == "core":
                    section_fields = fields

            sections.append(SectionUIConfig(
                id=section_id,
                label=section_info.get("label", section_id.title()),
                description=section_info.get("description"),
                icon=section_info.get("icon"),
                fields=section_fields,
                order=section_info.get("order", 0)
            ))

        return sorted(sections, key=lambda s: s.order)

    def _get_section_mapping(self, entity_type: EntityType) -> Dict[str, Dict[str, Any]]:
        """Get section definitions for an entity type."""
        section_maps = {
            EntityType.PERSON: {
                "core": {
                    "label": "Basic Information",
                    "description": "Core identity information",
                    "icon": "fa-user",
                    "fields": ["name", "first_name", "last_name", "date_of_birth"],
                    "order": 1
                },
                "contact": {
                    "label": "Contact Information",
                    "description": "Email, phone, and other contact details",
                    "icon": "fa-address-book",
                    "fields": ["email", "phone"],
                    "order": 2
                },
                "professional": {
                    "label": "Professional",
                    "description": "Employment and professional details",
                    "icon": "fa-briefcase",
                    "fields": ["occupation"],
                    "order": 3
                },
                "notes": {
                    "label": "Notes",
                    "description": "Additional notes and observations",
                    "icon": "fa-sticky-note",
                    "fields": ["notes"],
                    "order": 100
                }
            },
            EntityType.ORGANIZATION: {
                "core": {
                    "label": "Organization Identity",
                    "icon": "fa-building",
                    "fields": ["name", "type", "industry"],
                    "order": 1
                },
                "details": {
                    "label": "Organization Details",
                    "icon": "fa-info-circle",
                    "fields": ["founded_date", "headquarters", "employee_count", "website"],
                    "order": 2
                },
                "description": {
                    "label": "Description",
                    "icon": "fa-file-alt",
                    "fields": ["description"],
                    "order": 100
                }
            },
            EntityType.DEVICE: {
                "core": {
                    "label": "Device Identity",
                    "icon": "fa-mobile-alt",
                    "fields": ["name", "type", "manufacturer", "model"],
                    "order": 1
                },
                "technical": {
                    "label": "Technical Details",
                    "icon": "fa-cog",
                    "fields": ["serial_number", "mac_address", "ip_address", "imei"],
                    "order": 2
                },
                "notes": {
                    "label": "Notes",
                    "icon": "fa-sticky-note",
                    "fields": ["notes"],
                    "order": 100
                }
            },
            EntityType.LOCATION: {
                "core": {
                    "label": "Location Identity",
                    "icon": "fa-map-marker-alt",
                    "fields": ["name", "type"],
                    "order": 1
                },
                "address": {
                    "label": "Address",
                    "icon": "fa-map",
                    "fields": ["address", "city", "state", "country", "postal_code"],
                    "order": 2
                },
                "coordinates": {
                    "label": "Coordinates",
                    "icon": "fa-globe",
                    "fields": ["latitude", "longitude"],
                    "order": 3
                },
                "description": {
                    "label": "Description",
                    "icon": "fa-file-alt",
                    "fields": ["description"],
                    "order": 100
                }
            },
            EntityType.EVENT: {
                "core": {
                    "label": "Event Identity",
                    "icon": "fa-calendar-alt",
                    "fields": ["name", "type"],
                    "order": 1
                },
                "timing": {
                    "label": "Timing",
                    "icon": "fa-clock",
                    "fields": ["start_datetime", "end_datetime", "duration"],
                    "order": 2
                },
                "location": {
                    "label": "Location",
                    "icon": "fa-map-marker-alt",
                    "fields": ["location"],
                    "order": 3
                },
                "description": {
                    "label": "Description",
                    "icon": "fa-file-alt",
                    "fields": ["description"],
                    "order": 100
                }
            },
            EntityType.DOCUMENT: {
                "core": {
                    "label": "Document Identity",
                    "icon": "fa-file-alt",
                    "fields": ["title", "type", "classification"],
                    "order": 1
                },
                "metadata": {
                    "label": "Metadata",
                    "icon": "fa-info-circle",
                    "fields": ["author", "date_created", "source"],
                    "order": 2
                },
                "content": {
                    "label": "Content",
                    "icon": "fa-file",
                    "fields": ["file_path", "summary"],
                    "order": 3
                }
            }
        }
        return section_maps.get(entity_type, {"core": {"label": "Core", "order": 1}})

    def _get_searchable_fields(self, entity_type: EntityType) -> List[str]:
        """Get list of searchable field IDs for an entity type."""
        searchable_map = {
            EntityType.PERSON: ["name", "first_name", "last_name", "email", "phone"],
            EntityType.ORGANIZATION: ["name", "industry", "website"],
            EntityType.DEVICE: ["name", "serial_number", "mac_address", "ip_address", "imei"],
            EntityType.LOCATION: ["name", "address", "city", "country"],
            EntityType.EVENT: ["name", "location"],
            EntityType.DOCUMENT: ["title", "author", "source"],
        }
        return searchable_map.get(entity_type, ["name"])

    def _get_list_display_fields(self, entity_type: EntityType) -> List[str]:
        """Get fields to display in list views."""
        display_map = {
            EntityType.PERSON: ["name", "email", "occupation"],
            EntityType.ORGANIZATION: ["name", "type", "industry"],
            EntityType.DEVICE: ["name", "type", "manufacturer"],
            EntityType.LOCATION: ["name", "type", "city"],
            EntityType.EVENT: ["name", "type", "start_datetime"],
            EntityType.DOCUMENT: ["title", "type", "author"],
        }
        return display_map.get(entity_type, ["name"])

    def _format_relationship_label(self, relationship_type: str) -> str:
        """Format a relationship type as a human-readable label."""
        if not relationship_type:
            return ""
        # Replace underscores with spaces and title case
        return relationship_type.replace("_", " ").title()

    def _get_generic_relationships(self) -> List[CrossTypeRelationshipOption]:
        """Get generic relationship types that work between any entity types."""
        return [
            CrossTypeRelationshipOption(
                relationship_type="RELATED_TO",
                display_label="Related To",
                inverse_type="RELATED_TO",
                inverse_label="Related To",
                description="Generic relationship between entities",
                is_symmetric=True
            ),
            CrossTypeRelationshipOption(
                relationship_type="ASSOCIATED_WITH",
                display_label="Associated With",
                inverse_type="ASSOCIATED_WITH",
                inverse_label="Associated With",
                description="Association between entities",
                is_symmetric=True
            ),
            CrossTypeRelationshipOption(
                relationship_type="LINKED_TO",
                display_label="Linked To",
                inverse_type="LINKED_TO",
                inverse_label="Linked To",
                description="Link between entities",
                is_symmetric=True
            ),
        ]

    def _flatten_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten a nested profile structure for validation."""
        flat = {}
        for section_id, section_data in profile.items():
            if isinstance(section_data, dict):
                for field_id, field_value in section_data.items():
                    # Handle arrays by taking first value
                    if isinstance(field_value, list) and len(field_value) > 0:
                        field_value = field_value[0]
                    flat[field_id] = field_value
            else:
                flat[section_id] = section_data
        return flat

    def _validate_field_value(self, field: FieldUIConfig, value: Any) -> Optional[str]:
        """Validate a field value based on its type."""
        if field.type == FieldUIType.EMAIL:
            if isinstance(value, str):
                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, value):
                    return f"Invalid email format"

        elif field.type == FieldUIType.URL:
            if isinstance(value, str):
                url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
                if not re.match(url_pattern, value, re.IGNORECASE):
                    return f"Invalid URL format"

        elif field.type == FieldUIType.NUMBER:
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    return f"Must be a number"

        elif field.type == FieldUIType.DATE:
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    # Try other common formats
                    date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
                    valid = False
                    for fmt in date_formats:
                        try:
                            datetime.strptime(value, fmt)
                            valid = True
                            break
                        except ValueError:
                            continue
                    if not valid:
                        return f"Invalid date format"

        elif field.type == FieldUIType.DATETIME:
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid datetime format"

        return None


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

# Global service instance
_entity_type_ui_service: Optional[EntityTypeUIService] = None


def get_entity_type_ui_service(neo4j_handler=None) -> EntityTypeUIService:
    """
    Get the global EntityTypeUIService instance.

    Creates a new instance if one doesn't exist or if neo4j_handler is provided.

    Args:
        neo4j_handler: Optional Neo4j handler for database queries.

    Returns:
        EntityTypeUIService instance.
    """
    global _entity_type_ui_service

    if neo4j_handler is not None or _entity_type_ui_service is None:
        _entity_type_ui_service = EntityTypeUIService(neo4j_handler)

    return _entity_type_ui_service


def reset_entity_type_ui_service() -> None:
    """Reset the global service instance (useful for testing)."""
    global _entity_type_ui_service
    _entity_type_ui_service = None
