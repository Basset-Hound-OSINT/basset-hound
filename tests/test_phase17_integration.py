"""
Phase 17 Integration Tests: Frontend Integration & UI Enhancements

Tests for:
- Timeline Visualization Service
- Entity Type UI Service
- Frontend Components API
- WebSocket enhancements for real-time updates
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock


class TestTimelineVisualizationService:
    """Tests for TimelineVisualizationService."""

    def test_service_import(self):
        """Test that the service can be imported."""
        from api.services.timeline_visualization import (
            TimelineVisualizationService,
            TimelineEvent,
            TimelineGranularity,
            TimelineEventType,
            ActivityHeatmapData,
            TemporalSnapshot,
            EntityEvolution,
            EntityVersion,
            PeriodComparison,
            PeriodStats,
            TimePeriod,
            GraphStats,
        )

        assert TimelineVisualizationService is not None
        assert TimelineEvent is not None
        assert TimelineGranularity is not None
        assert TimelineEventType is not None

    def test_timeline_event_model(self):
        """Test TimelineEvent Pydantic model."""
        from api.services.timeline_visualization import TimelineEvent

        now = datetime.now(timezone.utc)
        event = TimelineEvent(
            timestamp=now,
            event_type="entity_created",
            entity_id="test-entity-123",
            details={"field": "name", "value": "John"},
            metadata={"actor": "user-1"}
        )

        assert event.timestamp == now
        assert event.event_type == "entity_created"
        assert event.entity_id == "test-entity-123"
        assert event.details["field"] == "name"
        assert event.event_id is not None

    def test_timeline_granularity_enum(self):
        """Test TimelineGranularity enum values."""
        from api.services.timeline_visualization import TimelineGranularity

        assert TimelineGranularity.HOUR.value == "hour"
        assert TimelineGranularity.DAY.value == "day"
        assert TimelineGranularity.WEEK.value == "week"
        assert TimelineGranularity.MONTH.value == "month"

    def test_timeline_event_type_enum(self):
        """Test TimelineEventType enum values."""
        from api.services.timeline_visualization import TimelineEventType

        assert TimelineEventType.ENTITY_CREATED.value == "entity_created"
        assert TimelineEventType.ENTITY_UPDATED.value == "entity_updated"
        assert TimelineEventType.ENTITY_DELETED.value == "entity_deleted"
        assert TimelineEventType.RELATIONSHIP_ADDED.value == "relationship_added"
        assert TimelineEventType.RELATIONSHIP_REMOVED.value == "relationship_removed"

    def test_activity_heatmap_data_model(self):
        """Test ActivityHeatmapData Pydantic model."""
        from api.services.timeline_visualization import ActivityHeatmapData

        data = ActivityHeatmapData(
            date="2024-01-15",
            count=25,
            entity_count=10,
            relationship_count=15,
            event_types={"create": 10, "update": 15}
        )

        assert data.date == "2024-01-15"
        assert data.count == 25
        assert data.entity_count == 10
        assert data.relationship_count == 15

    def test_temporal_snapshot_model(self):
        """Test TemporalSnapshot Pydantic model."""
        from api.services.timeline_visualization import TemporalSnapshot, GraphStats

        now = datetime.now(timezone.utc)
        snapshot = TemporalSnapshot(
            timestamp=now,
            nodes=[{"id": "n1", "label": "Node 1"}],
            edges=[{"id": "e1", "source": "n1", "target": "n2"}],
            stats=GraphStats(node_count=2, edge_count=1)
        )

        assert snapshot.timestamp == now
        assert len(snapshot.nodes) == 1
        assert len(snapshot.edges) == 1
        assert snapshot.stats.node_count == 2

    def test_entity_evolution_model(self):
        """Test EntityEvolution Pydantic model."""
        from api.services.timeline_visualization import EntityEvolution, EntityVersion

        now = datetime.now(timezone.utc)
        version = EntityVersion(
            timestamp=now,
            version_number=1,
            profile_snapshot={"name": "John Doe"},
            changes={"added": ["name"], "modified": [], "removed": []}
        )

        evolution = EntityEvolution(
            entity_id="test-123",
            entity_label="John Doe",
            versions=[version],
            total_versions=1,
            first_seen=now,
            last_updated=now
        )

        assert evolution.entity_id == "test-123"
        assert evolution.total_versions == 1
        assert len(evolution.versions) == 1

    def test_period_comparison_model(self):
        """Test PeriodComparison Pydantic model."""
        from api.services.timeline_visualization import (
            PeriodComparison,
            PeriodStats,
            StatsDifference,
            GraphStats
        )

        now = datetime.now(timezone.utc)
        start1 = now - timedelta(days=14)
        end1 = now - timedelta(days=7)
        start2 = now - timedelta(days=7)
        end2 = now

        period1 = PeriodStats(
            start_date=start1,
            end_date=end1,
            total_events=100,
            entity_events=60,
            relationship_events=40
        )

        period2 = PeriodStats(
            start_date=start2,
            end_date=end2,
            total_events=150,
            entity_events=90,
            relationship_events=60
        )

        comparison = PeriodComparison(
            period1_stats=period1,
            period2_stats=period2,
            differences=[
                StatsDifference(
                    metric="total_events",
                    period1_value=100,
                    period2_value=150,
                    absolute_change=50,
                    percent_change=50.0,
                    trend="increase"
                )
            ]
        )

        assert len(comparison.differences) == 1
        assert comparison.differences[0].trend == "increase"

    def test_time_period_validation(self):
        """Test TimePeriod validation."""
        from api.services.timeline_visualization import TimePeriod

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)

        # Valid period
        period = TimePeriod(start_date=start, end_date=now)
        assert period.start_date == start
        assert period.end_date == now

    def test_service_initialization(self):
        """Test service initialization."""
        from api.services.timeline_visualization import TimelineVisualizationService

        mock_neo4j = MagicMock()
        mock_timeline = MagicMock()
        mock_graph = MagicMock()
        mock_audit = MagicMock()

        service = TimelineVisualizationService(
            neo4j_handler=mock_neo4j,
            timeline_service=mock_timeline,
            graph_visualization_service=mock_graph,
            audit_logger=mock_audit
        )

        assert service.neo4j_handler is mock_neo4j
        assert service.timeline_service is mock_timeline
        assert service.graph_visualization_service is mock_graph
        assert service.audit_logger is mock_audit


class TestEntityTypeUIService:
    """Tests for Entity Type UI Service."""

    def test_service_import(self):
        """Test that the service can be imported."""
        from api.services.entity_type_ui import (
            EntityTypeUIService,
            get_entity_type_ui_service,
            reset_entity_type_ui_service,
        )

        assert EntityTypeUIService is not None
        assert get_entity_type_ui_service is not None

    def test_models_import(self):
        """Test that models can be imported."""
        from api.models.entity_type_ui import (
            FieldUIType,
            FieldValidation,
            SelectOption,
            FieldUIConfig,
            SectionUIConfig,
            EntityTypeUIConfig,
            EntityTypeStats,
            ProjectEntityTypeStats,
            CrossTypeRelationships,
            EntityValidationResult,
            EntityTypeIconResponse,
            EntityTypeListResponse,
        )

        assert FieldUIType is not None
        assert EntityTypeUIConfig is not None
        assert EntityValidationResult is not None

    def test_field_ui_type_enum(self):
        """Test FieldUIType enum values."""
        from api.models.entity_type_ui import FieldUIType

        assert FieldUIType.TEXT.value == "text"
        assert FieldUIType.TEXTAREA.value == "textarea"
        assert FieldUIType.EMAIL.value == "email"
        assert FieldUIType.URL.value == "url"
        assert FieldUIType.DATE.value == "date"
        assert FieldUIType.SELECT.value == "select"
        assert FieldUIType.MULTISELECT.value == "multiselect"

    def test_field_validation_model(self):
        """Test FieldValidation Pydantic model."""
        from api.models.entity_type_ui import FieldValidation

        validation = FieldValidation(
            min_length=1,
            max_length=100,
            pattern=r"^[a-zA-Z]+$",
            pattern_error="Only letters allowed"
        )

        assert validation.min_length == 1
        assert validation.max_length == 100
        assert validation.pattern == r"^[a-zA-Z]+$"

    def test_field_ui_config_model(self):
        """Test FieldUIConfig Pydantic model."""
        from api.models.entity_type_ui import FieldUIConfig, FieldUIType

        field = FieldUIConfig(
            id="email",
            label="Email Address",
            type=FieldUIType.EMAIL,
            required=True,
            placeholder="Enter email",
            order=1
        )

        assert field.id == "email"
        assert field.label == "Email Address"
        assert field.type == FieldUIType.EMAIL
        assert field.required is True

    def test_section_ui_config_model(self):
        """Test SectionUIConfig Pydantic model."""
        from api.models.entity_type_ui import SectionUIConfig, FieldUIConfig

        section = SectionUIConfig(
            id="contact",
            label="Contact Information",
            description="Contact details",
            icon="fa-address-book",
            collapsible=True,
            order=2
        )

        assert section.id == "contact"
        assert section.label == "Contact Information"
        assert section.collapsible is True

    def test_entity_type_ui_config_model(self):
        """Test EntityTypeUIConfig Pydantic model."""
        from api.models.entity_type_ui import EntityTypeUIConfig

        config = EntityTypeUIConfig(
            type="person",
            icon="fa-user",
            color="#3498db",
            label="Person",
            plural_label="People",
            description="Individual people in investigation"
        )

        assert config.type == "person"
        assert config.icon == "fa-user"
        assert config.color == "#3498db"
        assert config.label == "Person"
        assert config.plural_label == "People"

    def test_entity_type_stats_model(self):
        """Test EntityTypeStats Pydantic model."""
        from api.models.entity_type_ui import EntityTypeStats
        from datetime import datetime

        now = datetime.now()
        stats = EntityTypeStats(
            type="person",
            count=150,
            percentage=65.2,
            last_created=now,
            has_orphans=True,
            orphan_count=12
        )

        assert stats.type == "person"
        assert stats.count == 150
        assert stats.percentage == 65.2
        assert stats.has_orphans is True
        assert stats.orphan_count == 12

    def test_cross_type_relationships_model(self):
        """Test CrossTypeRelationships Pydantic model."""
        from api.models.entity_type_ui import (
            CrossTypeRelationships,
            CrossTypeRelationshipOption
        )

        relationship = CrossTypeRelationshipOption(
            relationship_type="EMPLOYED_BY",
            display_label="Employed By",
            inverse_type="EMPLOYS",
            inverse_label="Employs",
            is_symmetric=False
        )

        relationships = CrossTypeRelationships(
            source_type="person",
            target_type="organization",
            relationship_types=[relationship],
            bidirectional=True
        )

        assert relationships.source_type == "person"
        assert relationships.target_type == "organization"
        assert len(relationships.relationship_types) == 1
        assert relationships.bidirectional is True

    def test_entity_validation_result_model(self):
        """Test EntityValidationResult Pydantic model."""
        from api.models.entity_type_ui import EntityValidationResult

        # Valid result
        valid_result = EntityValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            missing_required=[],
            invalid_fields=[]
        )
        assert valid_result.valid is True

        # Invalid result
        invalid_result = EntityValidationResult(
            valid=False,
            errors=[{"field": "email", "message": "Invalid format"}],
            warnings=[],
            missing_required=["name"],
            invalid_fields=["email"]
        )
        assert invalid_result.valid is False
        assert len(invalid_result.errors) == 1
        assert "name" in invalid_result.missing_required


class TestFrontendComponentsAPI:
    """Tests for Frontend Components API."""

    def test_service_import(self):
        """Test that the service can be imported."""
        from api.services.frontend_components import (
            ComponentSpec,
            ComponentType,
            Framework,
            PropDefinition,
            StateDefinition,
            EventDefinition,
            StyleDefinition,
            get_all_component_specs,
            get_component_spec,
            generate_typescript_types,
            get_graph_viewer_spec,
            get_entity_card_spec,
            get_timeline_viewer_spec,
            get_import_wizard_spec,
            get_search_bar_spec,
        )

        assert ComponentSpec is not None
        assert ComponentType is not None
        assert Framework is not None

    def test_framework_enum(self):
        """Test Framework enum values."""
        from api.services.frontend_components import Framework

        assert Framework.REACT.value == "react"
        assert Framework.VUE.value == "vue"
        assert Framework.VANILLA.value == "vanilla"

    def test_component_type_enum(self):
        """Test ComponentType enum values."""
        from api.services.frontend_components import ComponentType

        assert ComponentType.GRAPH_VIEWER.value == "graph_viewer"
        assert ComponentType.ENTITY_CARD.value == "entity_card"
        assert ComponentType.TIMELINE_VIEWER.value == "timeline_viewer"
        assert ComponentType.IMPORT_WIZARD.value == "import_wizard"
        assert ComponentType.SEARCH_BAR.value == "search_bar"

    def test_prop_definition_model(self):
        """Test PropDefinition Pydantic model."""
        from api.services.frontend_components import PropDefinition

        prop = PropDefinition(
            name="layout",
            type="string",
            required=False,
            default="force",
            description="Graph layout algorithm"
        )

        assert prop.name == "layout"
        assert prop.type == "string"
        assert prop.default == "force"

    def test_event_definition_model(self):
        """Test EventDefinition Pydantic model."""
        from api.services.frontend_components import EventDefinition

        event = EventDefinition(
            name="onNodeClick",
            payload_type="{ nodeId: string, data: NodeData }",
            description="Fired when node is clicked"
        )

        assert event.name == "onNodeClick"
        assert "nodeId" in event.payload_type

    def test_get_all_component_specs(self):
        """Test get_all_component_specs returns all components."""
        from api.services.frontend_components import (
            get_all_component_specs,
            Framework,
            ComponentType
        )

        specs = get_all_component_specs(Framework.REACT)

        # Should have at least the 5 main components
        assert len(specs) >= 5

        # Check by component name (specs are keyed by name, not ComponentType)
        spec_names = list(specs.keys())
        assert "GraphViewer" in spec_names
        assert "EntityCard" in spec_names
        assert "TimelineViewer" in spec_names
        assert "ImportWizard" in spec_names
        assert "SearchBar" in spec_names

    def test_get_graph_viewer_spec(self):
        """Test get_graph_viewer_spec returns valid spec."""
        from api.services.frontend_components import (
            get_graph_viewer_spec,
            Framework
        )

        spec = get_graph_viewer_spec(Framework.REACT)

        assert spec.name == "GraphViewer"
        assert len(spec.props) > 0
        assert len(spec.state) > 0
        assert len(spec.events) > 0
        assert len(spec.dependencies) > 0
        assert "d3" in spec.dependencies

    def test_get_entity_card_spec(self):
        """Test get_entity_card_spec returns valid spec."""
        from api.services.frontend_components import (
            get_entity_card_spec,
            Framework
        )

        spec = get_entity_card_spec(Framework.REACT)

        assert spec.name == "EntityCard"
        assert len(spec.props) > 0

    def test_get_timeline_viewer_spec(self):
        """Test get_timeline_viewer_spec returns valid spec."""
        from api.services.frontend_components import (
            get_timeline_viewer_spec,
            Framework
        )

        spec = get_timeline_viewer_spec(Framework.REACT)

        assert spec.name == "TimelineViewer"
        assert len(spec.props) > 0
        assert any(d.startswith("d3") for d in spec.dependencies)

    def test_get_import_wizard_spec(self):
        """Test get_import_wizard_spec returns valid spec."""
        from api.services.frontend_components import (
            get_import_wizard_spec,
            Framework
        )

        spec = get_import_wizard_spec(Framework.REACT)

        assert spec.name == "ImportWizard"
        assert len(spec.props) > 0

    def test_get_search_bar_spec(self):
        """Test get_search_bar_spec returns valid spec."""
        from api.services.frontend_components import (
            get_search_bar_spec,
            Framework
        )

        spec = get_search_bar_spec(Framework.REACT)

        assert spec.name == "SearchBar"
        assert len(spec.props) > 0

    def test_generate_typescript_types(self):
        """Test generate_typescript_types returns TypeScript code."""
        from api.services.frontend_components import generate_typescript_types

        ts_code = generate_typescript_types()

        assert isinstance(ts_code, str)
        assert "interface" in ts_code or "type" in ts_code
        assert len(ts_code) > 0


class TestTimelineVisualizationRouter:
    """Tests for Timeline Visualization Router."""

    def test_router_import(self):
        """Test that the router can be imported."""
        from api.routers.timeline_visualization import router

        assert router is not None
        assert router.prefix == "/timeline-viz/{project_safe_name}"

    def test_response_models_import(self):
        """Test that response models can be imported."""
        from api.routers.timeline_visualization import (
            TimelineEventResponse,
            EntityTimelineResponse,
            RelationshipTimelineResponse,
            ActivityHeatmapResponse,
            TemporalSnapshotResponse,
            EntityEvolutionResponse,
            PeriodComparisonResponse,
            ComparePeriodsRequest,
        )

        assert TimelineEventResponse is not None
        assert EntityTimelineResponse is not None
        assert TemporalSnapshotResponse is not None

    def test_timeline_event_response_model(self):
        """Test TimelineEventResponse Pydantic model."""
        from api.routers.timeline_visualization import TimelineEventResponse

        response = TimelineEventResponse(
            timestamp="2024-01-15T10:30:00Z",
            event_type="entity_updated",
            entity_id="test-123",
            details={"field": "name"},
            metadata={"actor": "user-1"},
            event_id="event-456"
        )

        assert response.timestamp == "2024-01-15T10:30:00Z"
        assert response.event_type == "entity_updated"
        assert response.entity_id == "test-123"


class TestEntityTypesRouter:
    """Tests for Entity Types Router."""

    def test_router_import(self):
        """Test that routers can be imported."""
        from api.routers.entity_types import (
            router,
            project_entity_types_router
        )

        assert router is not None
        assert project_entity_types_router is not None
        assert router.prefix == "/entity-types"

    def test_response_models_import(self):
        """Test that response models can be imported."""
        from api.routers.entity_types import (
            EntityValidationRequest,
            ColorResponse,
            FieldsResponse,
        )

        assert EntityValidationRequest is not None
        assert ColorResponse is not None
        assert FieldsResponse is not None


class TestFrontendComponentsRouter:
    """Tests for Frontend Components Router."""

    def test_router_import(self):
        """Test that the router can be imported."""
        from api.routers.frontend_components import router

        assert router is not None
        assert router.prefix == "/frontend"

    def test_routes_registered(self):
        """Test that expected routes are registered."""
        from api.routers.frontend_components import router

        routes = [r.path for r in router.routes]

        # Routes include the prefix /frontend
        assert "/frontend/components" in routes
        assert "/frontend/components/{component_type}" in routes
        assert "/frontend/typescript" in routes
        assert "/frontend/css-variables" in routes
        assert "/frontend/dependencies" in routes
        assert "/frontend/frameworks" in routes


class TestServicesExports:
    """Tests for services module exports."""

    def test_timeline_visualization_exports(self):
        """Test that timeline visualization is properly exported."""
        from api.services import (
            TimelineVisualizationService,
            TimelineGranularity,
            TimelineEventType,
            ActivityHeatmapData,
            TemporalSnapshot,
            EntityEvolution,
            EntityVersion,
            PeriodComparison,
            PeriodStats,
            TimePeriod,
            GraphStats,
            get_timeline_visualization_service,
            set_timeline_visualization_service,
        )

        assert TimelineVisualizationService is not None
        assert get_timeline_visualization_service is not None

    def test_entity_type_ui_exports(self):
        """Test that entity type UI service is properly exported."""
        from api.services import (
            EntityTypeUIService,
            get_entity_type_ui_service,
            reset_entity_type_ui_service,
        )

        assert EntityTypeUIService is not None
        assert get_entity_type_ui_service is not None


class TestRoutersExports:
    """Tests for routers module exports."""

    def test_timeline_visualization_router_exported(self):
        """Test that timeline visualization router is exported."""
        from api.routers import timeline_visualization_router

        assert timeline_visualization_router is not None

    def test_entity_types_router_exported(self):
        """Test that entity types routers are exported."""
        from api.routers import (
            entity_types_router,
            project_entity_types_router
        )

        assert entity_types_router is not None
        assert project_entity_types_router is not None

    def test_frontend_components_router_exported(self):
        """Test that frontend components router is exported."""
        from api.routers import frontend_components_router

        assert frontend_components_router is not None

    def test_api_router_includes_phase17(self):
        """Test that api_router includes Phase 17 routers."""
        from api.routers import api_router

        # Check that the routers are included by looking at routes
        all_routes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)

        # Timeline visualization routes should be present
        assert any('/timeline-viz' in r for r in all_routes)

        # Entity types routes should be present
        assert any('/entity-types' in r for r in all_routes)

        # Frontend routes should be present
        assert any('/frontend' in r for r in all_routes)


class TestWebSocketEnhancements:
    """Tests for WebSocket enhancements for real-time updates."""

    def test_notification_types_import(self):
        """Test that enhanced notification types can be imported."""
        from api.services.websocket_service import NotificationType

        # Check original types exist
        assert NotificationType.ENTITY_CREATED is not None
        assert NotificationType.ENTITY_UPDATED is not None
        assert NotificationType.ENTITY_DELETED is not None

        # Check new graph update types
        assert hasattr(NotificationType, 'GRAPH_NODE_ADDED')
        assert hasattr(NotificationType, 'GRAPH_NODE_UPDATED')
        assert hasattr(NotificationType, 'GRAPH_NODE_DELETED')
        assert hasattr(NotificationType, 'GRAPH_EDGE_ADDED')
        assert hasattr(NotificationType, 'GRAPH_EDGE_UPDATED')
        assert hasattr(NotificationType, 'GRAPH_EDGE_DELETED')

    def test_graph_update_notification_types(self):
        """Test graph update notification type values."""
        from api.services.websocket_service import NotificationType

        assert NotificationType.GRAPH_NODE_ADDED.value == "graph_node_added"
        assert NotificationType.GRAPH_NODE_UPDATED.value == "graph_node_updated"
        assert NotificationType.GRAPH_NODE_DELETED.value == "graph_node_deleted"
        assert NotificationType.GRAPH_EDGE_ADDED.value == "graph_edge_added"
        assert NotificationType.GRAPH_EDGE_UPDATED.value == "graph_edge_updated"
        assert NotificationType.GRAPH_EDGE_DELETED.value == "graph_edge_deleted"

    def test_layout_and_cluster_notification_types(self):
        """Test layout and cluster notification type values."""
        from api.services.websocket_service import NotificationType

        assert hasattr(NotificationType, 'GRAPH_LAYOUT_CHANGED')
        assert hasattr(NotificationType, 'GRAPH_CLUSTER_DETECTED')
        assert NotificationType.GRAPH_LAYOUT_CHANGED.value == "graph_layout_changed"
        assert NotificationType.GRAPH_CLUSTER_DETECTED.value == "graph_cluster_detected"

    def test_import_notification_types(self):
        """Test import progress notification types."""
        from api.services.websocket_service import NotificationType

        assert hasattr(NotificationType, 'IMPORT_PROGRESS')
        assert hasattr(NotificationType, 'IMPORT_COMPLETE')
        assert NotificationType.IMPORT_PROGRESS.value == "import_progress"
        assert NotificationType.IMPORT_COMPLETE.value == "import_complete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
