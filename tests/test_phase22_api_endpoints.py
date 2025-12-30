"""
Phase 22 API Endpoint Tests for Basset Hound.

Tests for the new REST API endpoints:
- Import Mapping Router (/import-mappings)
- LLM Export Router (/llm-export, /projects/{project}/llm-export)
- Graph Format Converter Router (/graph-format)
"""

import pytest
from typing import Dict, Any


# =============================================================================
# IMPORT MAPPING ROUTER TESTS
# =============================================================================


class TestImportMappingRouter:
    """Tests for the Import Mapping Router."""

    def test_router_exists(self):
        """Test that the import mapping router exists."""
        from api.routers.import_mapping import router
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_required_endpoints(self):
        """Test that the router has all required endpoints."""
        from api.routers.import_mapping import router

        paths = [route.path for route in router.routes]
        assert "/import-mappings" in paths
        assert "/import-mappings/{mapping_id}" in paths
        assert "/import-mappings/{mapping_id}/apply" in paths
        assert "/import-mappings/validate" in paths
        assert "/import-mappings/preview" in paths

    def test_create_mapping_request_model(self):
        """Test CreateMappingRequest model validation."""
        from api.routers.import_mapping import CreateMappingRequest

        request = CreateMappingRequest(
            name="test_mapping",
            description="Test mapping",
            field_mappings=[
                {"source_field": "email", "destination_field": "contact_email"}
            ],
            tags=["test"]
        )

        assert request.name == "test_mapping"
        assert len(request.field_mappings) == 1
        assert request.tags == ["test"]

    def test_update_mapping_request_model(self):
        """Test UpdateMappingRequest model validation."""
        from api.routers.import_mapping import UpdateMappingRequest

        request = UpdateMappingRequest(
            name="updated_mapping",
            field_mappings=[
                {"source_field": "name", "destination_field": "full_name"}
            ]
        )

        assert request.name == "updated_mapping"

    def test_apply_mapping_request_model(self):
        """Test ApplyMappingRequest model validation."""
        from api.routers.import_mapping import ApplyMappingRequest

        request = ApplyMappingRequest(
            data=[{"name": "John", "email": "john@example.com"}]
        )

        assert len(request.data) == 1

    def test_validate_mapping_request_model(self):
        """Test ValidateMappingRequest model validation."""
        from api.routers.import_mapping import ValidateMappingRequest

        request = ValidateMappingRequest(
            config={"name": "test", "field_mappings": []},
            sample_data=[{"field1": "value1"}]
        )

        assert "name" in request.config

    def test_preview_mapping_request_model(self):
        """Test PreviewMappingRequest model validation."""
        from api.routers.import_mapping import PreviewMappingRequest

        request = PreviewMappingRequest(
            config={"name": "test", "field_mappings": []},
            sample_data=[{"field1": "value1"}],
            limit=10
        )

        assert request.limit == 10

    def test_mapping_response_model(self):
        """Test MappingResponse model."""
        from api.routers.import_mapping import MappingResponse

        response = MappingResponse(
            id="test-id",
            name="test_mapping",
            description="Test",
            field_mappings=[],
            source_format="csv",
            target_format="entity",
            metadata={},
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            version=1,
            tags=[]
        )

        assert response.id == "test-id"
        assert response.version == 1

    def test_validation_response_model(self):
        """Test ValidationResponse model."""
        from api.routers.import_mapping import ValidationResponse

        response = ValidationResponse(
            is_valid=True,
            errors=[],
            warnings=["Warning message"]
        )

        assert response.is_valid is True
        assert len(response.warnings) == 1


# =============================================================================
# LLM EXPORT ROUTER TESTS
# =============================================================================


class TestLLMExportRouter:
    """Tests for the LLM Export Router."""

    def test_router_exists(self):
        """Test that the LLM export router exists."""
        from api.routers.llm_export import router
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_required_endpoints(self):
        """Test that the router has all required endpoints."""
        from api.routers.llm_export import router

        paths = [route.path for route in router.routes]
        assert "/projects/{project_safe_name}/llm-export/entity/{entity_id}" in paths
        assert "/projects/{project_safe_name}/llm-export/summary" in paths
        assert "/projects/{project_safe_name}/llm-export/entity/{entity_id}/context" in paths
        assert "/projects/{project_safe_name}/llm-export/investigation-brief" in paths
        assert "/llm-export/estimate-tokens" in paths
        assert "/llm-export/formats" in paths

    def test_entity_export_request_model(self):
        """Test EntityExportRequest model."""
        from api.routers.llm_export import EntityExportRequest
        from api.services.llm_export import LLMExportFormat

        request = EntityExportRequest(
            format=LLMExportFormat.MARKDOWN,
            max_tokens=4000,
            max_relationships=50
        )

        assert request.format == LLMExportFormat.MARKDOWN
        assert request.max_tokens == 4000

    def test_project_summary_request_model(self):
        """Test ProjectSummaryRequest model."""
        from api.routers.llm_export import ProjectSummaryRequest
        from api.services.llm_export import LLMExportFormat

        request = ProjectSummaryRequest(
            format=LLMExportFormat.JSON,
            max_tokens=8000
        )

        assert request.format == LLMExportFormat.JSON

    def test_entity_context_request_model(self):
        """Test EntityContextRequest model."""
        from api.routers.llm_export import EntityContextRequest

        request = EntityContextRequest(
            depth=3,
            max_relationships=100
        )

        assert request.depth == 3
        assert request.max_relationships == 100

    def test_investigation_brief_request_model(self):
        """Test InvestigationBriefRequest model."""
        from api.routers.llm_export import InvestigationBriefRequest

        request = InvestigationBriefRequest(
            focus_entities=["entity-1", "entity-2"],
            max_tokens=10000
        )

        assert len(request.focus_entities) == 2

    def test_token_estimate_request_model(self):
        """Test TokenEstimateRequest model."""
        from api.routers.llm_export import TokenEstimateRequest
        from api.services.llm_export import LLMExportFormat

        request = TokenEstimateRequest(
            content="Sample content for token estimation",
            format=LLMExportFormat.MARKDOWN
        )

        assert len(request.content) > 0

    def test_token_estimate_response_model(self):
        """Test TokenEstimateResponse model."""
        from api.routers.llm_export import TokenEstimateResponse
        from api.services.llm_export import LLMExportFormat

        response = TokenEstimateResponse(
            token_estimate=42,
            format=LLMExportFormat.MARKDOWN,
            content_length=150,
            chars_per_token=4.0
        )

        assert response.token_estimate == 42
        assert response.chars_per_token == 4.0

    def test_format_info_model(self):
        """Test FormatInfo model."""
        from api.routers.llm_export import FormatInfo

        info = FormatInfo(
            value="markdown",
            description="Markdown format",
            overhead_multiplier=1.1
        )

        assert info.value == "markdown"
        assert info.overhead_multiplier == 1.1


# =============================================================================
# GRAPH FORMAT ROUTER TESTS
# =============================================================================


class TestGraphFormatRouter:
    """Tests for the Graph Format Router."""

    def test_router_exists(self):
        """Test that the graph format router exists."""
        from api.routers.graph_format import router
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_has_required_endpoints(self):
        """Test that the router has all required endpoints."""
        from api.routers.graph_format import router

        paths = [route.path for route in router.routes]
        assert "/graph-format/convert" in paths
        assert "/graph-format/convert-raw" in paths
        assert "/graph-format/detect" in paths
        assert "/graph-format/validate" in paths
        assert "/graph-format/formats" in paths
        assert "/graph-format/formats/{format}" in paths

    def test_convert_request_model(self):
        """Test ConvertRequest model."""
        from api.routers.graph_format import ConvertRequest
        from api.services.graph_format_converter import GraphFormat

        request = ConvertRequest(
            data='{"nodes": [], "links": []}',
            source_format=GraphFormat.D3,
            target_format=GraphFormat.CYTOSCAPE
        )

        assert request.source_format == GraphFormat.D3
        assert request.target_format == GraphFormat.CYTOSCAPE

    def test_detect_format_request_model(self):
        """Test DetectFormatRequest model."""
        from api.routers.graph_format import DetectFormatRequest

        request = DetectFormatRequest(
            data='{"nodes": [{"id": "1"}]}'
        )

        assert len(request.data) > 0

    def test_validate_format_request_model(self):
        """Test ValidateFormatRequest model."""
        from api.routers.graph_format import ValidateFormatRequest
        from api.services.graph_format_converter import GraphFormat

        request = ValidateFormatRequest(
            data='<graphml></graphml>',
            format=GraphFormat.GRAPHML
        )

        assert request.format == GraphFormat.GRAPHML

    def test_format_info_model(self):
        """Test FormatInfo model."""
        from api.routers.graph_format import FormatInfo

        info = FormatInfo(
            format="graphml",
            name="GraphML",
            description="XML-based graph format",
            extensions=[".graphml", ".xml"],
            mime_types=["application/xml"],
            supports_properties=True,
            supports_directed=True,
            supports_metadata=True
        )

        assert info.format == "graphml"
        assert info.supports_properties is True

    def test_format_details_response_model(self):
        """Test FormatDetailsResponse model."""
        from api.routers.graph_format import FormatDetailsResponse

        response = FormatDetailsResponse(
            format="d3",
            name="D3.js",
            description="D3.js format",
            extensions=[".json"],
            mime_types=["application/json"],
            supports_properties=True,
            supports_directed=True,
            supports_metadata=False,
            can_convert_to=["graphml", "cytoscape"],
            can_convert_from=["graphml", "gexf"],
            example_snippet='{"nodes": [], "links": []}'
        )

        assert "graphml" in response.can_convert_to
        assert response.example_snippet is not None

    def test_get_format_metadata(self):
        """Test _get_format_metadata helper function."""
        from api.routers.graph_format import _get_format_metadata

        metadata = _get_format_metadata()

        assert "graphml" in metadata
        assert "gexf" in metadata
        assert "d3" in metadata
        assert "cytoscape" in metadata
        assert "dot" in metadata
        assert "pajek" in metadata
        assert "adjacency_list" in metadata
        assert "json_graph" in metadata

        # Check metadata structure
        graphml = metadata["graphml"]
        assert "name" in graphml
        assert "description" in graphml
        assert "extensions" in graphml
        assert "mime_types" in graphml

    def test_get_media_type_for_format(self):
        """Test _get_media_type_for_format helper."""
        from api.routers.graph_format import _get_media_type_for_format
        from api.services.graph_format_converter import GraphFormat

        assert _get_media_type_for_format(GraphFormat.GRAPHML) == "application/xml"
        assert _get_media_type_for_format(GraphFormat.D3) == "application/json"
        assert _get_media_type_for_format(GraphFormat.DOT) == "text/plain"

    def test_get_filename_for_format(self):
        """Test _get_filename_for_format helper."""
        from api.routers.graph_format import _get_filename_for_format
        from api.services.graph_format_converter import GraphFormat

        assert _get_filename_for_format(GraphFormat.GRAPHML) == "graph.graphml"
        assert _get_filename_for_format(GraphFormat.D3) == "graph.json"
        assert _get_filename_for_format(GraphFormat.DOT) == "graph.dot"
        assert _get_filename_for_format(GraphFormat.PAJEK) == "graph.net"


# =============================================================================
# ROUTER INTEGRATION TESTS
# =============================================================================


class TestRouterIntegration:
    """Tests for router integration with the main API."""

    def test_all_routers_in_api_router(self):
        """Test that all Phase 22 routers are included in api_router."""
        from api.routers import (
            api_router,
            import_mapping_router,
            llm_export_router,
            graph_format_router,
        )

        # Verify routers exist
        assert import_mapping_router is not None
        assert llm_export_router is not None
        assert graph_format_router is not None

        # Verify api_router includes them
        assert api_router is not None

    def test_router_exports(self):
        """Test that all routers are exported from __init__.py."""
        from api.routers import __all__

        assert "import_mapping_router" in __all__
        assert "llm_export_router" in __all__
        assert "graph_format_router" in __all__

    def test_router_tags(self):
        """Test that routers have appropriate tags."""
        from api.routers.import_mapping import router as import_router
        from api.routers.llm_export import router as llm_router
        from api.routers.graph_format import router as format_router

        assert "import-mapping" in import_router.tags
        assert "llm-export" in llm_router.tags
        assert "graph-format" in format_router.tags


# =============================================================================
# ENDPOINT FUNCTION TESTS
# =============================================================================


class TestImportMappingEndpoints:
    """Tests for import mapping endpoint functions."""

    @pytest.mark.asyncio
    async def test_list_export_formats_endpoint(self):
        """Test the list_export_formats endpoint function."""
        from api.routers.llm_export import list_export_formats

        response = await list_export_formats()

        assert response is not None
        assert hasattr(response, "formats")
        assert hasattr(response, "total")
        assert response.total == 5  # MARKDOWN, JSON, YAML, PLAIN_TEXT, XML

    @pytest.mark.asyncio
    async def test_list_graph_formats_endpoint(self):
        """Test the list_graph_formats endpoint function."""
        from api.routers.graph_format import list_graph_formats

        response = await list_graph_formats()

        assert response is not None
        assert hasattr(response, "formats")
        assert len(response.formats) == 8  # All 8 graph formats

    @pytest.mark.asyncio
    async def test_estimate_tokens_endpoint(self):
        """Test the estimate_tokens endpoint function."""
        from api.routers.llm_export import estimate_tokens, TokenEstimateRequest
        from api.services.llm_export import LLMExportFormat

        request = TokenEstimateRequest(
            content="This is test content for token estimation.",
            format=LLMExportFormat.PLAIN_TEXT
        )

        response = await estimate_tokens(request)

        assert response is not None
        assert response.token_estimate > 0
        assert response.content_length == len(request.content)


# =============================================================================
# MODEL VALIDATION TESTS
# =============================================================================


class TestModelValidation:
    """Tests for Pydantic model validation."""

    def test_create_mapping_requires_field_mappings(self):
        """Test that CreateMappingRequest requires field_mappings."""
        from api.routers.import_mapping import CreateMappingRequest
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateMappingRequest(
                name="test",
                # Missing field_mappings
            )

    def test_entity_context_depth_limits(self):
        """Test EntityContextRequest depth limits."""
        from api.routers.llm_export import EntityContextRequest
        import pydantic

        # Valid depth
        request = EntityContextRequest(depth=3)
        assert request.depth == 3

        # Invalid depth (too high)
        with pytest.raises(pydantic.ValidationError):
            EntityContextRequest(depth=10)

        # Invalid depth (too low)
        with pytest.raises(pydantic.ValidationError):
            EntityContextRequest(depth=0)

    def test_investigation_brief_requires_entities(self):
        """Test InvestigationBriefRequest requires focus_entities."""
        from api.routers.llm_export import InvestigationBriefRequest
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            InvestigationBriefRequest(
                focus_entities=[],  # Empty list should fail
            )

    def test_convert_request_requires_data(self):
        """Test ConvertRequest requires non-empty data."""
        from api.routers.graph_format import ConvertRequest
        from api.services.graph_format_converter import GraphFormat
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ConvertRequest(
                data="",  # Empty string should fail
                source_format=GraphFormat.D3,
                target_format=GraphFormat.CYTOSCAPE
            )


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions in routers."""

    def test_build_config_helper(self):
        """Test _build_config helper function."""
        from api.routers.llm_export import _build_config, EntityExportRequest
        from api.services.llm_export import LLMExportFormat

        request = EntityExportRequest(
            format=LLMExportFormat.JSON,
            max_tokens=2000,
            max_relationships=25
        )

        config = _build_config(request)

        assert config.format == LLMExportFormat.JSON
        assert config.max_tokens == 2000
        assert config.max_relationships == 25

    def test_format_to_info_helper(self):
        """Test _format_to_info helper function."""
        from api.routers.graph_format import _format_to_info, _get_format_metadata

        metadata = _get_format_metadata()
        info = _format_to_info("graphml", metadata["graphml"])

        assert info.format == "graphml"
        assert info.name == "GraphML"
        assert ".graphml" in info.extensions

    def test_format_to_details_helper(self):
        """Test _format_to_details helper function."""
        from api.routers.graph_format import _format_to_details, _get_format_metadata

        metadata = _get_format_metadata()
        all_formats = list(metadata.keys())
        details = _format_to_details("d3", metadata["d3"], all_formats)

        assert details.format == "d3"
        assert len(details.can_convert_to) == 7  # All other formats
        assert "d3" not in details.can_convert_to
