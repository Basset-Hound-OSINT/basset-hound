"""
Graph Format Converter Router for Basset Hound.

Provides REST API endpoints for converting graph data between different formats
including GraphML, GEXF, JSON Graph, Cytoscape, D3, DOT, Pajek, and Adjacency List.
Supports format detection, validation, and bidirectional conversion.
"""

from typing import Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, status, Body
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..services.graph_format_converter import (
    GraphFormat,
    GraphFormatConverter,
    ConversionOptions,
    ConversionResult,
    FormatValidationResult,
    FormatDetectionResult,
    get_graph_format_converter,
    EdgeDirection,
)


router = APIRouter(
    prefix="",
    tags=["graph-format"],
    responses={
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class ConvertRequest(BaseModel):
    """Request schema for graph format conversion."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": '<?xml version="1.0"?><graphml>...</graphml>',
            "source_format": "graphml",
            "target_format": "d3",
            "options": {
                "include_properties": True,
                "pretty_print": True,
                "edge_direction": "preserve"
            }
        }
    })

    data: str = Field(..., description="Graph data in source format", min_length=1)
    source_format: GraphFormat = Field(..., description="Source graph format")
    target_format: GraphFormat = Field(..., description="Target graph format")
    options: Optional[ConversionOptions] = Field(
        None,
        description="Conversion options (optional)"
    )


class DetectFormatRequest(BaseModel):
    """Request schema for format detection."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": '{"nodes": [{"id": "1"}], "edges": []}'
        }
    })

    data: str = Field(..., description="Graph data to analyze", min_length=1)


class ValidateFormatRequest(BaseModel):
    """Request schema for format validation."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": '<?xml version="1.0"?><graphml>...</graphml>',
            "format": "graphml"
        }
    })

    data: str = Field(..., description="Graph data to validate", min_length=1)
    format: GraphFormat = Field(..., description="Expected format")


class FormatInfo(BaseModel):
    """Information about a graph format."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "format": "graphml",
            "name": "GraphML",
            "description": "XML-based graph format widely supported",
            "extensions": [".graphml", ".xml"],
            "mime_types": ["application/xml", "text/xml"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": True
        }
    })

    format: str = Field(..., description="Format identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Format description")
    extensions: list[str] = Field(..., description="Common file extensions")
    mime_types: list[str] = Field(..., description="MIME types")
    supports_properties: bool = Field(..., description="Supports node/edge properties")
    supports_directed: bool = Field(..., description="Supports directed graphs")
    supports_metadata: bool = Field(..., description="Supports graph metadata")


class FormatsListResponse(BaseModel):
    """Response schema for listing all formats."""
    formats: list[FormatInfo] = Field(..., description="List of supported formats")


class FormatDetailsResponse(FormatInfo):
    """Extended format information with examples and conversion capabilities."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "format": "graphml",
            "name": "GraphML",
            "description": "XML-based graph format",
            "extensions": [".graphml"],
            "mime_types": ["application/xml"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": True,
            "can_convert_to": ["gexf", "d3", "cytoscape", "dot"],
            "can_convert_from": ["gexf", "json_graph", "cytoscape", "d3"],
            "example_snippet": "<?xml version=\"1.0\"?>\\n<graphml>..."
        }
    })

    can_convert_to: list[str] = Field(
        default_factory=list,
        description="Formats this can convert to"
    )
    can_convert_from: list[str] = Field(
        default_factory=list,
        description="Formats this can convert from"
    )
    example_snippet: Optional[str] = Field(
        None,
        description="Example data snippet"
    )


# ----- Helper Functions -----

def _get_format_metadata() -> dict[str, dict[str, Any]]:
    """Get metadata for all supported formats."""
    return {
        "graphml": {
            "name": "GraphML",
            "description": "XML-based graph format with wide tool support. Standard format for graph visualization tools.",
            "extensions": [".graphml", ".xml"],
            "mime_types": ["application/xml", "text/xml"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": True,
            "example_snippet": '<?xml version="1.0"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n  <graph edgedefault="directed">\n    <node id="n1"/>\n    <edge source="n1" target="n2"/>\n  </graph>\n</graphml>'
        },
        "gexf": {
            "name": "GEXF",
            "description": "Graph Exchange XML Format. Used by Gephi and supports dynamic/temporal graphs.",
            "extensions": [".gexf", ".xml"],
            "mime_types": ["application/xml", "text/xml"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": True,
            "example_snippet": '<?xml version="1.0"?>\n<gexf xmlns="http://www.gexf.net/1.2draft">\n  <graph defaultedgetype="directed">\n    <nodes>\n      <node id="1" label="Node 1"/>\n    </nodes>\n  </graph>\n</gexf>'
        },
        "json_graph": {
            "name": "JSON Graph Format",
            "description": "Generic JSON-based graph format with nodes and edges arrays. Simple and flexible.",
            "extensions": [".json"],
            "mime_types": ["application/json"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": True,
            "example_snippet": '{\n  "graph": {\n    "directed": true,\n    "nodes": [{"id": "1", "label": "Node 1"}],\n    "edges": [{"source": "1", "target": "2"}]\n  }\n}'
        },
        "cytoscape": {
            "name": "Cytoscape.js",
            "description": "JSON format for Cytoscape.js graph visualization library. Popular for web applications.",
            "extensions": [".json"],
            "mime_types": ["application/json"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": False,
            "example_snippet": '{\n  "elements": {\n    "nodes": [{"data": {"id": "1", "label": "Node 1"}}],\n    "edges": [{"data": {"source": "1", "target": "2"}}]\n  }\n}'
        },
        "d3": {
            "name": "D3.js Force Layout",
            "description": "JSON format for D3.js force-directed graphs. Uses 'nodes' and 'links' arrays.",
            "extensions": [".json"],
            "mime_types": ["application/json"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": False,
            "example_snippet": '{\n  "nodes": [{"id": "1", "name": "Node 1"}],\n  "links": [{"source": "1", "target": "2"}]\n}'
        },
        "dot": {
            "name": "Graphviz DOT",
            "description": "Text-based graph format for Graphviz. Widely supported for graph layout and visualization.",
            "extensions": [".dot", ".gv"],
            "mime_types": ["text/vnd.graphviz", "text/plain"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": False,
            "example_snippet": 'digraph G {\n  n1 [label="Node 1"];\n  n1 -> n2 [label="edge"];\n}'
        },
        "pajek": {
            "name": "Pajek NET",
            "description": "Network format for Pajek network analysis tool. Supports large-scale network analysis.",
            "extensions": [".net", ".paj"],
            "mime_types": ["text/plain"],
            "supports_properties": True,
            "supports_directed": True,
            "supports_metadata": False,
            "example_snippet": '*Vertices 2\n1 "Node 1"\n2 "Node 2"\n*Arcs\n1 2 1'
        },
        "adjacency_list": {
            "name": "Adjacency List",
            "description": "Simple text format listing each node and its adjacent nodes. Compact and easy to parse.",
            "extensions": [".txt", ".adjlist"],
            "mime_types": ["text/plain"],
            "supports_properties": False,
            "supports_directed": True,
            "supports_metadata": False,
            "example_snippet": 'n1: n2 n3\nn2: n3\nn3:'
        }
    }


def _format_to_info(format_key: str, metadata: dict) -> FormatInfo:
    """Convert format metadata to FormatInfo model."""
    return FormatInfo(
        format=format_key,
        name=metadata["name"],
        description=metadata["description"],
        extensions=metadata["extensions"],
        mime_types=metadata["mime_types"],
        supports_properties=metadata["supports_properties"],
        supports_directed=metadata["supports_directed"],
        supports_metadata=metadata["supports_metadata"]
    )


def _format_to_details(format_key: str, metadata: dict, all_formats: list[str]) -> FormatDetailsResponse:
    """Convert format metadata to detailed FormatDetailsResponse."""
    # All formats can convert to/from each other
    other_formats = [f for f in all_formats if f != format_key]

    return FormatDetailsResponse(
        format=format_key,
        name=metadata["name"],
        description=metadata["description"],
        extensions=metadata["extensions"],
        mime_types=metadata["mime_types"],
        supports_properties=metadata["supports_properties"],
        supports_directed=metadata["supports_directed"],
        supports_metadata=metadata["supports_metadata"],
        can_convert_to=other_formats,
        can_convert_from=other_formats,
        example_snippet=metadata.get("example_snippet")
    )


def _get_media_type_for_format(format: GraphFormat) -> str:
    """Get appropriate media type for a graph format."""
    media_types = {
        GraphFormat.GRAPHML: "application/xml",
        GraphFormat.GEXF: "application/xml",
        GraphFormat.JSON_GRAPH: "application/json",
        GraphFormat.CYTOSCAPE: "application/json",
        GraphFormat.D3: "application/json",
        GraphFormat.DOT: "text/plain",
        GraphFormat.PAJEK: "text/plain",
        GraphFormat.ADJACENCY_LIST: "text/plain",
    }
    return media_types.get(format, "text/plain")


def _get_filename_for_format(format: GraphFormat, base_name: str = "graph") -> str:
    """Get appropriate filename for a graph format."""
    extensions = {
        GraphFormat.GRAPHML: ".graphml",
        GraphFormat.GEXF: ".gexf",
        GraphFormat.JSON_GRAPH: ".json",
        GraphFormat.CYTOSCAPE: ".json",
        GraphFormat.D3: ".json",
        GraphFormat.DOT: ".dot",
        GraphFormat.PAJEK: ".net",
        GraphFormat.ADJACENCY_LIST: ".txt",
    }
    return f"{base_name}{extensions.get(format, '.txt')}"


# ----- Endpoints -----

@router.post(
    "/graph-format/convert",
    response_model=ConversionResult,
    summary="Convert graph between formats",
    description="Convert graph data from one format to another with optional conversion options.",
    responses={
        200: {"description": "Conversion completed successfully"},
        400: {"description": "Invalid input data or format"},
        500: {"description": "Conversion failed"},
    }
)
async def convert_graph_format(request: ConvertRequest = Body(...)):
    """
    Convert graph data between different formats.

    Supports bidirectional conversion between all supported formats:
    - GraphML (XML-based, widely supported)
    - GEXF (XML-based, used by Gephi)
    - JSON Graph (generic JSON format)
    - Cytoscape.js (web visualization)
    - D3.js (force-directed layout)
    - DOT (Graphviz format)
    - Pajek NET (network analysis)
    - Adjacency List (simple text format)

    Conversion options allow control over:
    - Property inclusion
    - Edge directionality
    - Metadata handling
    - Output formatting
    - Node ID prefixing
    - Property filtering and mapping

    **Parameters:**
    - **data**: Graph data in source format
    - **source_format**: Source format identifier
    - **target_format**: Target format identifier
    - **options**: Optional conversion configuration
    """
    try:
        converter = get_graph_format_converter()
        result = converter.convert(
            data=request.data,
            source_format=request.source_format,
            target_format=request.target_format,
            options=request.options
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Conversion failed"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversion error: {str(e)}"
        )


@router.post(
    "/graph-format/convert-raw",
    summary="Convert and return raw data",
    description="Convert graph format and return the raw converted data as a downloadable file.",
    responses={
        200: {
            "description": "Converted graph data",
            "content": {
                "application/json": {},
                "application/xml": {},
                "text/plain": {}
            }
        },
        400: {"description": "Invalid input data or format"},
        500: {"description": "Conversion failed"},
    }
)
async def convert_graph_format_raw(request: ConvertRequest = Body(...)):
    """
    Convert graph format and return raw data as downloadable file.

    Same as `/convert` but returns the converted data directly with
    appropriate Content-Type and Content-Disposition headers for download.

    **Parameters:**
    - **data**: Graph data in source format
    - **source_format**: Source format identifier
    - **target_format**: Target format identifier
    - **options**: Optional conversion configuration
    """
    try:
        converter = get_graph_format_converter()
        result = converter.convert(
            data=request.data,
            source_format=request.source_format,
            target_format=request.target_format,
            options=request.options
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Conversion failed"
            )

        media_type = _get_media_type_for_format(request.target_format)
        filename = _get_filename_for_format(request.target_format)

        return Response(
            content=result.data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversion error: {str(e)}"
        )


@router.post(
    "/graph-format/detect",
    response_model=FormatDetectionResult,
    summary="Auto-detect graph format",
    description="Automatically detect the format of graph data using heuristics.",
    responses={
        200: {"description": "Format detection completed"},
        400: {"description": "Invalid input data"},
        500: {"description": "Detection failed"},
    }
)
async def detect_graph_format(request: DetectFormatRequest = Body(...)):
    """
    Auto-detect the format of graph data.

    Uses pattern matching and structural analysis to identify the format:
    - XML structure detection (GraphML, GEXF)
    - JSON schema analysis (D3, Cytoscape, JSON Graph)
    - Text pattern matching (DOT, Pajek, Adjacency List)

    Returns the most likely format along with confidence score and
    alternative format candidates.

    **Parameters:**
    - **data**: Graph data to analyze
    """
    try:
        converter = get_graph_format_converter()
        result = converter.detect_format(data=request.data)

        if not result.detected_format and result.confidence == 0.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not detect graph format from provided data"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Format detection error: {str(e)}"
        )


@router.post(
    "/graph-format/validate",
    response_model=FormatValidationResult,
    summary="Validate graph data format",
    description="Validate graph data against a specific format specification.",
    responses={
        200: {"description": "Validation completed"},
        400: {"description": "Invalid input data"},
        500: {"description": "Validation failed"},
    }
)
async def validate_graph_format(request: ValidateFormatRequest = Body(...)):
    """
    Validate graph data against a format specification.

    Checks:
    - Format syntax correctness
    - Node and edge structure validity
    - Reference integrity (edges reference existing nodes)
    - Required field presence

    Returns validation status, error list, and basic graph statistics.

    **Parameters:**
    - **data**: Graph data to validate
    - **format**: Expected format
    """
    try:
        converter = get_graph_format_converter()
        result = converter.validate_format(
            data=request.data,
            format=request.format
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.get(
    "/graph-format/formats",
    response_model=FormatsListResponse,
    summary="List all supported formats",
    description="Get a list of all supported graph formats with their capabilities.",
    responses={
        200: {"description": "Format list retrieved successfully"},
    }
)
async def list_graph_formats():
    """
    List all supported graph formats.

    Returns information about each format including:
    - Name and description
    - File extensions
    - MIME types
    - Feature support (properties, directed graphs, metadata)

    Useful for building format selection UIs and understanding capabilities.
    """
    try:
        metadata = _get_format_metadata()
        formats = [
            _format_to_info(format_key, meta)
            for format_key, meta in metadata.items()
        ]

        return FormatsListResponse(formats=formats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list formats: {str(e)}"
        )


@router.get(
    "/graph-format/formats/{format}",
    response_model=FormatDetailsResponse,
    summary="Get format details",
    description="Get detailed information about a specific graph format.",
    responses={
        200: {"description": "Format details retrieved successfully"},
        404: {"description": "Format not found"},
    }
)
async def get_format_details(format: GraphFormat):
    """
    Get detailed information about a specific format.

    Returns extended information including:
    - Basic format metadata
    - Conversion capabilities (can convert to/from)
    - Example code snippet
    - Feature support details

    **Parameters:**
    - **format**: Format identifier
    """
    try:
        metadata = _get_format_metadata()
        format_key = format.value

        if format_key not in metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Format '{format_key}' not found"
            )

        all_formats = list(metadata.keys())
        details = _format_to_details(format_key, metadata[format_key], all_formats)

        return details

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get format details: {str(e)}"
        )
