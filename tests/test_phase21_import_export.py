"""
Phase 21: Import/Export Flexibility Tests

Tests for:
- Custom import mapping service
- LLM-optimized export service
- Graph format converters
"""

import json
from datetime import datetime, timezone

import pytest


# =============================================================================
# IMPORT MAPPING SERVICE TESTS
# =============================================================================


class TestTransformationType:
    """Test TransformationType enum."""

    def test_transformation_types_exist(self):
        """Test that all transformation types are defined."""
        from api.services.import_mapping import TransformationType

        assert TransformationType.DIRECT == "direct"
        assert TransformationType.LOWERCASE == "lowercase"
        assert TransformationType.UPPERCASE == "uppercase"
        assert TransformationType.TRIM == "trim"
        assert TransformationType.REGEX_EXTRACT == "regex_extract"
        assert TransformationType.SPLIT == "split"
        assert TransformationType.JOIN == "join"
        assert TransformationType.DEFAULT == "default"
        assert TransformationType.TEMPLATE == "template"


class TestFieldMapping:
    """Test FieldMapping model."""

    def test_field_mapping_creation(self):
        """Test creating a field mapping."""
        from api.services.import_mapping import FieldMapping, TransformationType

        mapping = FieldMapping(
            source_field="email_address",
            destination_field="email",
            transformations=[TransformationType.LOWERCASE, TransformationType.TRIM],
            description="Email field mapping"
        )

        assert mapping.source_field == "email_address"
        assert mapping.destination_field == "email"
        assert len(mapping.transformations) == 2

    def test_field_mapping_with_options(self):
        """Test field mapping with transformation options."""
        from api.services.import_mapping import (
            FieldMapping,
            TransformationType,
            TransformationOptions,
        )

        options = TransformationOptions(
            pattern=r"(\w+)@(\w+\.com)",
            delimiter=",",
            default_value="unknown"
        )

        mapping = FieldMapping(
            source_field="data",
            destination_field="parsed_data",
            transformations=[TransformationType.REGEX_EXTRACT],
            options=options
        )

        assert mapping.options.pattern == r"(\w+)@(\w+\.com)"


class TestImportMappingConfig:
    """Test ImportMappingConfig model."""

    def test_config_creation(self):
        """Test creating a mapping configuration."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        config = ImportMappingConfig(
            name="CSV Email Import",
            description="Maps CSV email exports",
            field_mappings=[
                FieldMapping(
                    source_field="Email",
                    destination_field="email",
                    transformations=[TransformationType.LOWERCASE]
                )
            ],
            source_format="CSV",
            target_format="Basset Hound Entity"
        )

        assert config.name == "CSV Email Import"
        assert len(config.field_mappings) == 1
        assert config.id is not None  # Auto-generated


class TestTransformationEngine:
    """Test TransformationEngine class."""

    def test_direct_transformation(self):
        """Test direct value copy."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationType,
        )

        engine = TransformationEngine()
        result = engine.apply_transformation(
            "Hello World",
            TransformationType.DIRECT,
            None
        )

        assert result == "Hello World"

    def test_lowercase_transformation(self):
        """Test lowercase transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationType,
        )

        engine = TransformationEngine()
        result = engine.apply_transformation(
            "HELLO WORLD",
            TransformationType.LOWERCASE,
            None
        )

        assert result == "hello world"

    def test_uppercase_transformation(self):
        """Test uppercase transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationType,
        )

        engine = TransformationEngine()
        result = engine.apply_transformation(
            "hello world",
            TransformationType.UPPERCASE,
            None
        )

        assert result == "HELLO WORLD"

    def test_trim_transformation(self):
        """Test trim whitespace transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationType,
        )

        engine = TransformationEngine()
        result = engine.apply_transformation(
            "  hello world  ",
            TransformationType.TRIM,
            None
        )

        assert result == "hello world"

    def test_split_transformation(self):
        """Test split string transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationOptions,
            TransformationType,
        )

        engine = TransformationEngine()
        options = TransformationOptions(delimiter=",")
        result = engine.apply_transformation(
            "a,b,c",
            TransformationType.SPLIT,
            options
        )

        assert result == ["a", "b", "c"]

    def test_join_transformation(self):
        """Test join array transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationOptions,
            TransformationType,
        )

        engine = TransformationEngine()
        options = TransformationOptions(delimiter="; ")
        result = engine.apply_transformation(
            ["a", "b", "c"],
            TransformationType.JOIN,
            options
        )

        assert result == "a; b; c"

    def test_default_transformation(self):
        """Test default value transformation."""
        from api.services.import_mapping import (
            TransformationEngine,
            TransformationOptions,
            TransformationType,
        )

        engine = TransformationEngine()
        options = TransformationOptions(default_value="N/A")

        # Empty string should use default
        result = engine.apply_transformation(
            "",
            TransformationType.DEFAULT,
            options
        )
        assert result == "N/A"

        # Non-empty should keep value
        result = engine.apply_transformation(
            "hello",
            TransformationType.DEFAULT,
            options
        )
        assert result == "hello"


class TestImportMappingService:
    """Test ImportMappingService class."""

    @pytest.fixture
    def service(self):
        """Create a mapping service for testing."""
        from api.services.import_mapping import (
            ImportMappingService,
            reset_import_mapping_service,
        )

        reset_import_mapping_service()
        return ImportMappingService()

    def test_create_mapping(self, service):
        """Test creating a new mapping."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        config = ImportMappingConfig(
            name="Test Mapping",
            field_mappings=[
                FieldMapping(
                    source_field="src",
                    destination_field="dst",
                    transformations=[TransformationType.DIRECT]
                )
            ]
        )

        result = service.create_mapping(config)

        assert result.name == "Test Mapping"
        assert result.id is not None

    def test_get_mapping(self, service):
        """Test getting a mapping by ID."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        config = ImportMappingConfig(
            name="Get Test",
            field_mappings=[
                FieldMapping(
                    source_field="a",
                    destination_field="b",
                    transformations=[TransformationType.DIRECT]
                )
            ]
        )

        created = service.create_mapping(config)
        retrieved = service.get_mapping(created.id)

        assert retrieved is not None
        assert retrieved.name == "Get Test"

    def test_list_mappings(self, service):
        """Test listing all mappings."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        # Create multiple mappings
        for i in range(3):
            config = ImportMappingConfig(
                name=f"Mapping {i}",
                field_mappings=[
                    FieldMapping(
                        source_field="a",
                        destination_field="b",
                        transformations=[TransformationType.DIRECT]
                    )
                ]
            )
            service.create_mapping(config)

        mappings = service.list_mappings()
        assert len(mappings) >= 3

    def test_delete_mapping(self, service):
        """Test deleting a mapping."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        config = ImportMappingConfig(
            name="Delete Test",
            field_mappings=[
                FieldMapping(
                    source_field="a",
                    destination_field="b",
                    transformations=[TransformationType.DIRECT]
                )
            ]
        )

        created = service.create_mapping(config)
        result = service.delete_mapping(created.id)

        assert result is True
        assert service.get_mapping(created.id) is None

    def test_apply_mapping(self, service):
        """Test applying a mapping to data."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        config = ImportMappingConfig(
            name="Apply Test",
            field_mappings=[
                FieldMapping(
                    source_field="EMAIL",
                    destination_field="email",
                    transformations=[TransformationType.LOWERCASE, TransformationType.TRIM]
                )
            ]
        )

        created = service.create_mapping(config)
        data = {"EMAIL": "  TEST@EXAMPLE.COM  "}

        result = service.apply_mapping(data, created.id)

        assert result is not None
        assert result["email"] == "test@example.com"

    def test_validate_mapping(self, service):
        """Test validating a mapping configuration."""
        from api.services.import_mapping import (
            FieldMapping,
            ImportMappingConfig,
            TransformationType,
        )

        # Valid config
        valid_config = ImportMappingConfig(
            name="Valid Config",
            field_mappings=[
                FieldMapping(
                    source_field="a",
                    destination_field="b",
                    transformations=[TransformationType.DIRECT]
                )
            ]
        )

        result = service.validate_mapping(valid_config)
        assert result.is_valid is True


# =============================================================================
# LLM EXPORT SERVICE TESTS
# =============================================================================


class TestLLMExportFormat:
    """Test LLMExportFormat enum."""

    def test_export_formats_exist(self):
        """Test that all export formats are defined."""
        from api.services.llm_export import LLMExportFormat

        assert LLMExportFormat.MARKDOWN == "markdown"
        assert LLMExportFormat.JSON == "json"
        assert LLMExportFormat.YAML == "yaml"
        assert LLMExportFormat.PLAIN_TEXT == "plain_text"
        assert LLMExportFormat.XML == "xml"


class TestExportContext:
    """Test ExportContext model."""

    def test_export_context_defaults(self):
        """Test default export context values."""
        from api.services.llm_export import ExportContext

        context = ExportContext()

        assert context.include_entities is True
        assert context.include_relationships is True
        assert context.include_timeline is False
        assert context.include_orphan_data is False


class TestLLMExportConfig:
    """Test LLMExportConfig model."""

    def test_config_defaults(self):
        """Test default configuration values."""
        from api.services.llm_export import LLMExportConfig, LLMExportFormat

        config = LLMExportConfig()

        assert config.format == LLMExportFormat.MARKDOWN
        assert config.max_tokens is None  # Default is unlimited (None)
        assert config.max_field_length == 500

    def test_config_custom(self):
        """Test custom configuration."""
        from api.services.llm_export import LLMExportConfig, LLMExportFormat

        config = LLMExportConfig(
            format=LLMExportFormat.JSON,
            max_tokens=8000,
            max_relationships=50
        )

        assert config.format == LLMExportFormat.JSON
        assert config.max_tokens == 8000
        assert config.max_relationships == 50


class TestLLMExportResult:
    """Test LLMExportResult model."""

    def test_result_creation(self):
        """Test creating an export result."""
        from api.services.llm_export import LLMExportFormat, LLMExportResult

        result = LLMExportResult(
            content="# Entity Report\n\nContent here...",
            format=LLMExportFormat.MARKDOWN,
            token_estimate=150,
            truncated=False,
            metadata={"entity_count": 1}
        )

        assert result.content.startswith("# Entity Report")
        assert result.token_estimate == 150
        assert result.truncated is False


class TestLLMExportService:
    """Test LLMExportService class."""

    def test_service_instantiation(self):
        """Test creating LLM export service."""
        from api.services.llm_export import LLMExportService

        # LLMExportService requires neo4j_handler (can be None for testing)
        service = LLMExportService(neo4j_handler=None)
        assert service is not None

    def test_estimate_tokens(self):
        """Test token estimation using TokenEstimator."""
        from api.services.llm_export import TokenEstimator, LLMExportFormat

        # Short text
        estimate = TokenEstimator.estimate("Hello world", LLMExportFormat.PLAIN_TEXT)
        assert estimate > 0
        assert estimate < 10

        # Longer text
        long_text = "This is a longer piece of text. " * 100
        estimate = TokenEstimator.estimate(long_text, LLMExportFormat.PLAIN_TEXT)
        assert estimate > 100


# =============================================================================
# GRAPH FORMAT CONVERTER TESTS
# =============================================================================


class TestGraphFormat:
    """Test GraphFormat enum."""

    def test_graph_formats_exist(self):
        """Test that all graph formats are defined."""
        from api.services.graph_format_converter import GraphFormat

        assert GraphFormat.GRAPHML == "graphml"
        assert GraphFormat.GEXF == "gexf"
        assert GraphFormat.JSON_GRAPH == "json_graph"
        assert GraphFormat.CYTOSCAPE == "cytoscape"
        assert GraphFormat.D3 == "d3"
        assert GraphFormat.DOT == "dot"
        assert GraphFormat.PAJEK == "pajek"
        assert GraphFormat.ADJACENCY_LIST == "adjacency_list"


class TestConversionOptions:
    """Test ConversionOptions model."""

    def test_options_defaults(self):
        """Test default conversion options."""
        from api.services.graph_format_converter import ConversionOptions

        options = ConversionOptions()

        assert options.include_properties is True
        assert options.include_metadata is True
        assert options.pretty_print is True

    def test_options_custom(self):
        """Test custom conversion options."""
        from api.services.graph_format_converter import (
            ConversionOptions,
            EdgeDirection,
        )

        options = ConversionOptions(
            include_properties=False,
            edge_direction=EdgeDirection.UNDIRECTED,
            node_id_prefix="n_"
        )

        assert options.include_properties is False
        assert options.edge_direction == EdgeDirection.UNDIRECTED
        assert options.node_id_prefix == "n_"


class TestInternalGraph:
    """Test internal graph representation."""

    def test_internal_node(self):
        """Test InternalNode dataclass."""
        from api.services.graph_format_converter import InternalNode

        node = InternalNode(
            id="node1",
            label="Test Node",
            properties={"type": "person", "name": "John"}
        )

        assert node.id == "node1"
        assert node.label == "Test Node"
        assert node.properties["name"] == "John"

    def test_internal_edge(self):
        """Test InternalEdge dataclass."""
        from api.services.graph_format_converter import InternalEdge

        edge = InternalEdge(
            source="node1",
            target="node2",
            label="KNOWS",
            properties={"since": "2020"},
            directed=True
        )

        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.label == "KNOWS"
        assert edge.directed is True

    def test_internal_graph(self):
        """Test InternalGraph dataclass."""
        from api.services.graph_format_converter import (
            InternalEdge,
            InternalGraph,
            InternalNode,
        )

        graph = InternalGraph(
            nodes=[
                InternalNode(id="n1", label="Node 1"),
                InternalNode(id="n2", label="Node 2"),
            ],
            edges=[
                InternalEdge(source="n1", target="n2", label="connects"),
            ],
            metadata={"name": "Test Graph"},
            directed=True
        )

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.directed is True


class TestGraphFormatConverter:
    """Test GraphFormatConverter class."""

    @pytest.fixture
    def converter(self):
        """Create a converter for testing."""
        from api.services.graph_format_converter import (
            GraphFormatConverter,
            reset_graph_format_converter,
        )

        reset_graph_format_converter()
        return GraphFormatConverter()

    def test_converter_instantiation(self, converter):
        """Test creating the converter."""
        assert converter is not None

    def test_detect_json_format(self, converter):
        """Test detecting JSON graph format."""
        from api.services.graph_format_converter import GraphFormat

        json_data = json.dumps({
            "nodes": [{"id": "n1"}],
            "edges": [{"source": "n1", "target": "n2"}]
        })

        result = converter.detect_format(json_data)

        # Should detect as some JSON format
        assert result.detected_format in [
            GraphFormat.JSON_GRAPH,
            GraphFormat.D3,
            GraphFormat.CYTOSCAPE
        ]
        assert result.confidence > 0.5

    def test_detect_graphml_format(self, converter):
        """Test detecting GraphML format."""
        from api.services.graph_format_converter import GraphFormat

        graphml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <graphml xmlns="http://graphml.graphdrawing.org/xmlns">
            <graph id="G" edgedefault="directed">
                <node id="n0"/>
                <node id="n1"/>
                <edge source="n0" target="n1"/>
            </graph>
        </graphml>"""

        result = converter.detect_format(graphml_data)

        assert result.detected_format == GraphFormat.GRAPHML
        assert result.confidence > 0.8

    def test_convert_json_to_d3(self, converter):
        """Test converting JSON graph to D3 format."""
        from api.services.graph_format_converter import GraphFormat

        json_data = json.dumps({
            "nodes": [{"id": "n1", "label": "Node 1"}, {"id": "n2", "label": "Node 2"}],
            "edges": [{"source": "n1", "target": "n2"}]
        })

        result = converter.convert(
            json_data,
            GraphFormat.JSON_GRAPH,
            GraphFormat.D3
        )

        assert result.success is True
        assert result.node_count == 2
        assert result.edge_count == 1


class TestConversionResult:
    """Test ConversionResult model."""

    def test_successful_result(self):
        """Test creating a successful conversion result."""
        from api.services.graph_format_converter import (
            ConversionResult,
            GraphFormat,
        )

        result = ConversionResult(
            success=True,
            data='{"nodes": [], "links": []}',
            source_format=GraphFormat.JSON_GRAPH,
            target_format=GraphFormat.D3,
            node_count=5,
            edge_count=3,
            warnings=[],
            metadata={"converted_at": "2024-01-01"}
        )

        assert result.success is True
        assert result.node_count == 5
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed conversion result."""
        from api.services.graph_format_converter import (
            ConversionResult,
            GraphFormat,
        )

        result = ConversionResult(
            success=False,
            data="",  # data is a required string field, use empty string for errors
            source_format=GraphFormat.GRAPHML,
            target_format=GraphFormat.D3,
            node_count=0,
            edge_count=0,
            error="Invalid GraphML format"
        )

        assert result.success is False
        assert result.error == "Invalid GraphML format"


# =============================================================================
# EXPORTS TESTS
# =============================================================================


class TestServicesExports:
    """Test that Phase 21 services export correctly."""

    def test_import_mapping_exports(self):
        """Test import mapping service exports."""
        from api.services import (
            FieldMapping,
            ImportMappingConfig,
            ImportMappingService,
            MappingPreviewResult,
            MappingValidationResult,
            TransformationEngine,
            TransformationOptions,
            TransformationType,
            get_import_mapping_service,
            reset_import_mapping_service,
        )

        assert ImportMappingService is not None
        assert TransformationType is not None
        assert FieldMapping is not None

    def test_llm_export_exports(self):
        """Test LLM export service exports."""
        from api.services import (
            ExportContext,
            LLMExportConfig,
            LLMExportFormat,
            LLMExportResult,
            LLMExportService,
            get_llm_export_service,
            reset_llm_export_service,
            set_llm_export_service,
        )

        assert LLMExportService is not None
        assert LLMExportFormat is not None
        assert ExportContext is not None

    def test_graph_format_converter_exports(self):
        """Test graph format converter exports."""
        from api.services import (
            ConversionOptions,
            ConversionResult,
            ConversionWarning,
            EdgeDirection,
            FormatDetectionResult,
            FormatValidationResult,
            GraphFormat,
            GraphFormatConverter,
            InternalEdge,
            InternalGraph,
            InternalNode,
            get_graph_format_converter,
            reset_graph_format_converter,
            set_graph_format_converter,
        )

        assert GraphFormatConverter is not None
        assert GraphFormat is not None
        assert InternalGraph is not None
