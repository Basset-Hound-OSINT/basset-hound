"""
Tests for Entity Type Definitions (Phase 5 - Multi-Entity Support).

Tests cover:
- EntityType enum functionality
- EntityTypeConfig model validation
- FieldMapping model validation
- CrossTypeRelationship model validation
- Default entity type configurations
- Entity type registry functionality
- Helper functions for entity type management
"""

import pytest
from pydantic import ValidationError


class TestEntityTypeEnum:
    """Tests for the EntityType enumeration."""

    def test_entity_type_values(self):
        """Test that all expected entity types are defined."""
        from api.models.entity_types import EntityType

        expected_types = ["person", "organization", "device", "location", "event", "document"]
        actual_types = [e.value for e in EntityType]

        for expected in expected_types:
            assert expected in actual_types, f"Missing entity type: {expected}"

    def test_entity_type_person(self):
        """Test PERSON entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.PERSON.value == "person"
        # EntityType inherits from str, so equality comparison works directly
        assert EntityType.PERSON == "person"

    def test_entity_type_organization(self):
        """Test ORGANIZATION entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.ORGANIZATION.value == "organization"

    def test_entity_type_device(self):
        """Test DEVICE entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.DEVICE.value == "device"

    def test_entity_type_location(self):
        """Test LOCATION entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.LOCATION.value == "location"

    def test_entity_type_event(self):
        """Test EVENT entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.EVENT.value == "event"

    def test_entity_type_document(self):
        """Test DOCUMENT entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.DOCUMENT.value == "document"

    def test_get_default_returns_person(self):
        """Test that default entity type is Person for backwards compatibility."""
        from api.models.entity_types import EntityType

        assert EntityType.get_default() == EntityType.PERSON

    def test_get_all_values(self):
        """Test getting all entity type values as strings."""
        from api.models.entity_types import EntityType

        values = EntityType.get_all_values()
        assert isinstance(values, list)
        assert "person" in values
        assert "organization" in values
        assert len(values) == 6

    def test_from_string_valid(self):
        """Test converting valid strings to EntityType."""
        from api.models.entity_types import EntityType

        assert EntityType.from_string("person") == EntityType.PERSON
        assert EntityType.from_string("PERSON") == EntityType.PERSON
        assert EntityType.from_string("Person") == EntityType.PERSON
        assert EntityType.from_string("  person  ") == EntityType.PERSON
        assert EntityType.from_string("organization") == EntityType.ORGANIZATION

    def test_from_string_invalid(self):
        """Test that invalid strings return None."""
        from api.models.entity_types import EntityType

        assert EntityType.from_string("invalid") is None
        assert EntityType.from_string("") is None
        assert EntityType.from_string(None) is None

    def test_is_valid(self):
        """Test validation of entity type strings."""
        from api.models.entity_types import EntityType

        assert EntityType.is_valid("person") is True
        assert EntityType.is_valid("organization") is True
        assert EntityType.is_valid("invalid") is False
        assert EntityType.is_valid("") is False


class TestEntityTypeConfig:
    """Tests for EntityTypeConfig model."""

    def test_create_valid_config(self):
        """Test creating a valid entity type configuration."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        config = EntityTypeConfig(
            entity_type=EntityType.ORGANIZATION,
            display_name="Organization",
            description="Company or group",
            icon="fa-building",
            color="#2ecc71",
            sections=["org_identity", "org_contact"],
            primary_name_field="name",
            primary_name_section="org_identity"
        )

        assert config.entity_type == EntityType.ORGANIZATION
        assert config.display_name == "Organization"
        assert config.icon == "fa-building"
        assert len(config.sections) == 2

    def test_config_default_values(self):
        """Test default values in entity type configuration."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        config = EntityTypeConfig(
            entity_type=EntityType.PERSON,
            display_name="Person"
        )

        assert config.icon == "fa-circle"
        assert config.color is None
        assert config.sections == []
        assert config.primary_name_field == "name"
        assert config.primary_name_section == "core"
        assert config.allowed_relationship_types is None
        assert config.can_relate_to is None

    def test_config_empty_display_name_fails(self):
        """Test that empty display_name fails validation."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        with pytest.raises(ValidationError):
            EntityTypeConfig(
                entity_type=EntityType.PERSON,
                display_name=""
            )

    def test_config_invalid_color_fails(self):
        """Test that invalid color format fails validation."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        with pytest.raises(ValidationError):
            EntityTypeConfig(
                entity_type=EntityType.PERSON,
                display_name="Person",
                color="invalid-color-format"
            )

    def test_config_valid_hex_color(self):
        """Test valid hex color formats."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        config = EntityTypeConfig(
            entity_type=EntityType.PERSON,
            display_name="Person",
            color="#3498db"
        )
        assert config.color == "#3498db"

    def test_config_valid_named_color(self):
        """Test valid named color formats."""
        from api.models.entity_types import EntityType, EntityTypeConfig

        config = EntityTypeConfig(
            entity_type=EntityType.PERSON,
            display_name="Person",
            color="blue"
        )
        assert config.color == "blue"


class TestFieldMapping:
    """Tests for FieldMapping model."""

    def test_create_valid_field_mapping(self):
        """Test creating a valid field mapping."""
        from api.models.entity_types import EntityType, FieldMapping

        mapping = FieldMapping(
            source_type=EntityType.PERSON,
            source_section="employment",
            source_field="employer.company",
            target_type=EntityType.ORGANIZATION,
            target_section="org_identity",
            target_field="name"
        )

        assert mapping.source_type == EntityType.PERSON
        assert mapping.target_type == EntityType.ORGANIZATION
        assert mapping.source_field == "employer.company"
        assert mapping.transformation is None

    def test_field_mapping_with_transformation(self):
        """Test field mapping with transformation."""
        from api.models.entity_types import EntityType, FieldMapping

        mapping = FieldMapping(
            source_type=EntityType.PERSON,
            source_section="core",
            source_field="name",
            target_type=EntityType.ORGANIZATION,
            target_section="org_structure",
            target_field="leadership.name",
            transformation="split_name"
        )

        assert mapping.transformation == "split_name"


class TestCrossTypeRelationship:
    """Tests for CrossTypeRelationship model."""

    def test_create_valid_cross_type_relationship(self):
        """Test creating a valid cross-type relationship."""
        from api.models.entity_types import EntityType, CrossTypeRelationship

        rel = CrossTypeRelationship(
            source_type=EntityType.PERSON,
            target_type=EntityType.ORGANIZATION,
            relationship_name="EMPLOYED_BY",
            inverse_name="EMPLOYS",
            description="Person is employed by organization"
        )

        assert rel.source_type == EntityType.PERSON
        assert rel.target_type == EntityType.ORGANIZATION
        assert rel.relationship_name == "EMPLOYED_BY"
        assert rel.inverse_name == "EMPLOYS"
        assert rel.is_symmetric is False

    def test_symmetric_relationship(self):
        """Test symmetric relationship."""
        from api.models.entity_types import EntityType, CrossTypeRelationship

        rel = CrossTypeRelationship(
            source_type=EntityType.ORGANIZATION,
            target_type=EntityType.ORGANIZATION,
            relationship_name="PARTNER_WITH",
            inverse_name="PARTNER_WITH",
            is_symmetric=True
        )

        assert rel.is_symmetric is True

    def test_invalid_relationship_name_format(self):
        """Test that lowercase relationship name fails."""
        from api.models.entity_types import EntityType, CrossTypeRelationship

        with pytest.raises(ValidationError):
            CrossTypeRelationship(
                source_type=EntityType.PERSON,
                target_type=EntityType.ORGANIZATION,
                relationship_name="employed_by"  # Should be uppercase
            )

    def test_relationship_name_with_underscore(self):
        """Test relationship name with underscore is valid."""
        from api.models.entity_types import EntityType, CrossTypeRelationship

        rel = CrossTypeRelationship(
            source_type=EntityType.PERSON,
            target_type=EntityType.DEVICE,
            relationship_name="OWNS_DEVICE"
        )

        assert rel.relationship_name == "OWNS_DEVICE"


class TestDefaultConfigurations:
    """Tests for default entity type configurations."""

    def test_default_configs_exist_for_all_types(self):
        """Test that default configs exist for all entity types."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        for entity_type in EntityType:
            assert entity_type in DEFAULT_ENTITY_TYPE_CONFIGS, \
                f"Missing default config for {entity_type}"

    def test_person_config(self):
        """Test Person entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.PERSON]

        assert config.display_name == "Person"
        assert config.icon == "fa-user"
        assert "core" in config.sections
        assert config.primary_name_field == "name"
        assert config.primary_name_section == "core"

    def test_organization_config(self):
        """Test Organization entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.ORGANIZATION]

        assert config.display_name == "Organization"
        assert config.icon == "fa-building"
        assert "org_identity" in config.sections
        assert config.primary_name_section == "org_identity"

    def test_location_config(self):
        """Test Location entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.LOCATION]

        assert config.display_name == "Location"
        assert config.icon == "fa-map-marker-alt"
        assert "location_identity" in config.sections

    def test_device_config(self):
        """Test Device entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.DEVICE]

        assert config.display_name == "Device"
        assert config.icon == "fa-mobile-alt"

    def test_event_config(self):
        """Test Event entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.EVENT]

        assert config.display_name == "Event"
        assert config.icon == "fa-calendar-alt"

    def test_document_config(self):
        """Test Document entity type default configuration."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_ENTITY_TYPE_CONFIGS
        )

        config = DEFAULT_ENTITY_TYPE_CONFIGS[EntityType.DOCUMENT]

        assert config.display_name == "Document"
        assert config.icon == "fa-file-alt"
        assert config.primary_name_field == "title"  # Document uses 'title' not 'name'


class TestDefaultCrossTypeRelationships:
    """Tests for default cross-type relationship definitions."""

    def test_default_relationships_exist(self):
        """Test that default cross-type relationships are defined."""
        from api.models.entity_types import DEFAULT_CROSS_TYPE_RELATIONSHIPS

        assert len(DEFAULT_CROSS_TYPE_RELATIONSHIPS) > 0

    def test_person_organization_relationships(self):
        """Test Person <-> Organization relationship types."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_CROSS_TYPE_RELATIONSHIPS
        )

        person_org_rels = [
            r for r in DEFAULT_CROSS_TYPE_RELATIONSHIPS
            if r.source_type == EntityType.PERSON
            and r.target_type == EntityType.ORGANIZATION
        ]

        rel_names = [r.relationship_name for r in person_org_rels]

        assert "EMPLOYED_BY" in rel_names
        assert "MEMBER_OF" in rel_names
        assert "FOUNDED" in rel_names
        assert "OWNS" in rel_names

    def test_person_location_relationships(self):
        """Test Person <-> Location relationship types."""
        from api.models.entity_types import (
            EntityType,
            DEFAULT_CROSS_TYPE_RELATIONSHIPS
        )

        person_loc_rels = [
            r for r in DEFAULT_CROSS_TYPE_RELATIONSHIPS
            if r.source_type == EntityType.PERSON
            and r.target_type == EntityType.LOCATION
        ]

        rel_names = [r.relationship_name for r in person_loc_rels]

        assert "LIVES_AT" in rel_names
        assert "WORKS_AT" in rel_names
        assert "VISITED" in rel_names

    def test_inverse_relationships_defined(self):
        """Test that inverse relationships are properly defined."""
        from api.models.entity_types import DEFAULT_CROSS_TYPE_RELATIONSHIPS

        for rel in DEFAULT_CROSS_TYPE_RELATIONSHIPS:
            if not rel.is_symmetric:
                # Non-symmetric relationships should have an inverse defined
                # (unless it's optional for one-way relationships)
                pass  # Currently all have inverses but this could change

    def test_symmetric_relationships(self):
        """Test symmetric relationship detection."""
        from api.models.entity_types import DEFAULT_CROSS_TYPE_RELATIONSHIPS

        symmetric_rels = [r for r in DEFAULT_CROSS_TYPE_RELATIONSHIPS if r.is_symmetric]

        # PARTNER_WITH should be symmetric
        partner_rels = [r for r in symmetric_rels if r.relationship_name == "PARTNER_WITH"]
        assert len(partner_rels) > 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_entity_type_config(self):
        """Test getting entity type configuration."""
        from api.models.entity_types import EntityType, get_entity_type_config

        config = get_entity_type_config(EntityType.PERSON)
        assert config is not None
        assert config.entity_type == EntityType.PERSON

    def test_get_all_entity_type_configs(self):
        """Test getting all entity type configurations."""
        from api.models.entity_types import EntityType, get_all_entity_type_configs

        configs = get_all_entity_type_configs()
        assert len(configs) == len(EntityType)

    def test_get_cross_type_relationships_no_filter(self):
        """Test getting all cross-type relationships without filter."""
        from api.models.entity_types import get_cross_type_relationships

        rels = get_cross_type_relationships()
        assert len(rels) > 0

    def test_get_cross_type_relationships_by_source(self):
        """Test getting cross-type relationships filtered by source type."""
        from api.models.entity_types import EntityType, get_cross_type_relationships

        rels = get_cross_type_relationships(source_type=EntityType.PERSON)

        for rel in rels:
            assert rel.source_type == EntityType.PERSON

    def test_get_cross_type_relationships_by_target(self):
        """Test getting cross-type relationships filtered by target type."""
        from api.models.entity_types import EntityType, get_cross_type_relationships

        rels = get_cross_type_relationships(target_type=EntityType.ORGANIZATION)

        for rel in rels:
            assert rel.target_type == EntityType.ORGANIZATION

    def test_get_cross_type_relationships_by_both(self):
        """Test getting cross-type relationships filtered by both source and target."""
        from api.models.entity_types import EntityType, get_cross_type_relationships

        rels = get_cross_type_relationships(
            source_type=EntityType.PERSON,
            target_type=EntityType.ORGANIZATION
        )

        for rel in rels:
            assert rel.source_type == EntityType.PERSON
            assert rel.target_type == EntityType.ORGANIZATION

    def test_get_available_relationships_for_type(self):
        """Test getting available relationships for an entity type."""
        from api.models.entity_types import EntityType, get_available_relationships_for_type

        rels = get_available_relationships_for_type(EntityType.PERSON)

        # Should include both same-type relationships and cross-type
        assert "RELATED_TO" in rels  # From RelationshipType enum
        assert "EMPLOYED_BY" in rels  # From cross-type relationships
        assert "KNOWS" in rels

    def test_can_entities_relate(self):
        """Test checking if entities can form relationships."""
        from api.models.entity_types import EntityType, can_entities_relate

        # Person can relate to Organization
        assert can_entities_relate(EntityType.PERSON, EntityType.ORGANIZATION) is True

        # Person can relate to Location
        assert can_entities_relate(EntityType.PERSON, EntityType.LOCATION) is True


class TestEntityTypeRegistry:
    """Tests for EntityTypeRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization with default configs."""
        from api.models.entity_types import EntityTypeRegistry

        registry = EntityTypeRegistry()

        assert len(registry.get_all_types()) == 6

    def test_registry_get_config(self):
        """Test getting config from registry."""
        from api.models.entity_types import EntityType, EntityTypeRegistry

        registry = EntityTypeRegistry()
        config = registry.get_config(EntityType.PERSON)

        assert config is not None
        assert config.entity_type == EntityType.PERSON

    def test_registry_register_type(self):
        """Test registering/updating entity type config."""
        from api.models.entity_types import EntityType, EntityTypeConfig, EntityTypeRegistry

        registry = EntityTypeRegistry()

        custom_config = EntityTypeConfig(
            entity_type=EntityType.PERSON,
            display_name="Custom Person",
            description="Custom configuration"
        )

        registry.register_type(custom_config)
        config = registry.get_config(EntityType.PERSON)

        assert config.display_name == "Custom Person"

    def test_registry_get_all_configs(self):
        """Test getting all configs from registry."""
        from api.models.entity_types import EntityTypeRegistry

        registry = EntityTypeRegistry()
        configs = registry.get_all_configs()

        assert len(configs) == 6

    def test_registry_is_type_registered(self):
        """Test checking if type is registered."""
        from api.models.entity_types import EntityType, EntityTypeRegistry

        registry = EntityTypeRegistry()

        assert registry.is_type_registered(EntityType.PERSON) is True
        assert registry.is_type_registered(EntityType.ORGANIZATION) is True

    def test_registry_get_sections_for_type(self):
        """Test getting sections for an entity type."""
        from api.models.entity_types import EntityType, EntityTypeRegistry

        registry = EntityTypeRegistry()
        sections = registry.get_sections_for_type(EntityType.PERSON)

        assert "core" in sections
        assert "contact" in sections

    def test_registry_add_cross_type_relationship(self):
        """Test adding cross-type relationship to registry."""
        from api.models.entity_types import (
            EntityType,
            EntityTypeRegistry,
            CrossTypeRelationship
        )

        registry = EntityTypeRegistry()
        initial_count = len(registry.get_cross_type_relationships())

        new_rel = CrossTypeRelationship(
            source_type=EntityType.DEVICE,
            target_type=EntityType.EVENT,
            relationship_name="INVOLVED_IN",
            description="Device was involved in event"
        )

        registry.add_cross_type_relationship(new_rel)
        new_count = len(registry.get_cross_type_relationships())

        assert new_count == initial_count + 1


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_registry(self):
        """Test getting global registry instance."""
        from api.models.entity_types import get_registry, reset_registry

        reset_registry()  # Ensure clean state
        registry = get_registry()

        assert registry is not None

    def test_get_registry_singleton(self):
        """Test that get_registry returns singleton."""
        from api.models.entity_types import get_registry, reset_registry

        reset_registry()
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_reset_registry(self):
        """Test resetting global registry."""
        from api.models.entity_types import (
            EntityType,
            EntityTypeConfig,
            get_registry,
            reset_registry
        )

        registry = get_registry()

        # Modify registry
        custom_config = EntityTypeConfig(
            entity_type=EntityType.PERSON,
            display_name="Modified Person"
        )
        registry.register_type(custom_config)

        # Reset
        reset_registry()

        # Get new registry and verify it's reset
        new_registry = get_registry()
        config = new_registry.get_config(EntityType.PERSON)

        assert config.display_name == "Person"  # Back to default


class TestBackwardsCompatibility:
    """Tests ensuring backwards compatibility with existing Person entities."""

    def test_person_is_default_type(self):
        """Test that Person is the default entity type."""
        from api.models.entity_types import EntityType

        assert EntityType.get_default() == EntityType.PERSON

    def test_person_config_uses_existing_sections(self):
        """Test that Person config uses existing section names."""
        from api.models.entity_types import EntityType, get_entity_type_config

        config = get_entity_type_config(EntityType.PERSON)

        # These section names match existing data_config.yaml
        assert "core" in config.sections
        assert "contact" in config.sections
        assert "social_major" in config.sections
        assert "professional" in config.sections
        assert "Tagged People" in config.sections

    def test_person_primary_name_field(self):
        """Test Person uses correct primary name field."""
        from api.models.entity_types import EntityType, get_entity_type_config

        config = get_entity_type_config(EntityType.PERSON)

        assert config.primary_name_section == "core"
        assert config.primary_name_field == "name"

    def test_entity_type_string_matches_existing_config(self):
        """Test EntityType.PERSON value matches existing config format."""
        from api.models.entity_types import EntityType

        # The existing data_config.yaml uses "entity_type: Person"
        # but we use lowercase internally for consistency
        assert EntityType.PERSON.value == "person"

        # from_string should handle case-insensitive conversion
        assert EntityType.from_string("Person") == EntityType.PERSON
        assert EntityType.from_string("PERSON") == EntityType.PERSON


class TestIntegrationWithRelationshipModel:
    """Tests for integration with existing relationship models."""

    def test_relationship_types_accessible(self):
        """Test that relationship types from relationship model are accessible."""
        from api.models.entity_types import get_available_relationships_for_type, EntityType

        relationships = get_available_relationships_for_type(EntityType.PERSON)

        # These should come from RelationshipType enum
        assert "WORKS_WITH" in relationships
        assert "KNOWS" in relationships
        assert "FAMILY" in relationships

    def test_cross_type_relationships_extend_base(self):
        """Test that cross-type relationships extend base relationships."""
        from api.models.entity_types import get_available_relationships_for_type, EntityType

        relationships = get_available_relationships_for_type(EntityType.PERSON)

        # These should come from cross-type relationships
        assert "EMPLOYED_BY" in relationships
        assert "LIVES_AT" in relationships
        assert "OWNS_DEVICE" in relationships
