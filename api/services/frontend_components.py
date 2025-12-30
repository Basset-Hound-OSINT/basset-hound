"""
Frontend Component Specifications for Basset Hound OSINT Platform.

This module provides JSON specifications for frontend graph visualization
components that can be consumed by React, Vue, or vanilla JavaScript.

The specifications include:
- Component props and state definitions
- Event handlers and callbacks
- Styling and theming options
- D3.js/Cytoscape.js integration configs

These specs enable frontend developers to build consistent UI components
that integrate with the Basset Hound API.

Usage:
    from api.services.frontend_components import (
        get_graph_viewer_spec,
        get_entity_card_spec,
        get_timeline_viewer_spec,
        get_import_wizard_spec,
    )

    # Get React-style component spec
    spec = get_graph_viewer_spec(framework="react")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field


logger = logging.getLogger("basset_hound.frontend_components")


# =============================================================================
# ENUMS
# =============================================================================

class Framework(str, Enum):
    """Supported frontend frameworks."""
    REACT = "react"
    VUE = "vue"
    VANILLA = "vanilla"


class ComponentType(str, Enum):
    """Types of frontend components."""
    GRAPH_VIEWER = "graph_viewer"
    ENTITY_CARD = "entity_card"
    ENTITY_LIST = "entity_list"
    ENTITY_FORM = "entity_form"
    RELATIONSHIP_EDITOR = "relationship_editor"
    TIMELINE_VIEWER = "timeline_viewer"
    IMPORT_WIZARD = "import_wizard"
    SEARCH_BAR = "search_bar"
    FILTER_PANEL = "filter_panel"
    STATS_DASHBOARD = "stats_dashboard"


class EventType(str, Enum):
    """Frontend event types."""
    NODE_CLICK = "node_click"
    NODE_DOUBLE_CLICK = "node_double_click"
    NODE_HOVER = "node_hover"
    NODE_DRAG = "node_drag"
    EDGE_CLICK = "edge_click"
    EDGE_HOVER = "edge_hover"
    CANVAS_CLICK = "canvas_click"
    ZOOM_CHANGE = "zoom_change"
    LAYOUT_COMPLETE = "layout_complete"
    SELECTION_CHANGE = "selection_change"
    CONTEXT_MENU = "context_menu"


# =============================================================================
# PYDANTIC MODELS FOR COMPONENT SPECS
# =============================================================================

class PropDefinition(BaseModel):
    """Definition of a component prop."""
    name: str = Field(..., description="Prop name")
    type: str = Field(..., description="TypeScript/PropTypes type")
    required: bool = Field(default=False, description="Whether prop is required")
    default: Optional[Any] = Field(default=None, description="Default value")
    description: str = Field(default="", description="Prop description")
    options: Optional[List[Any]] = Field(default=None, description="Valid options for enum types")


class StateDefinition(BaseModel):
    """Definition of component state."""
    name: str = Field(..., description="State variable name")
    type: str = Field(..., description="TypeScript type")
    initial: Any = Field(default=None, description="Initial value")
    description: str = Field(default="", description="State description")


class EventDefinition(BaseModel):
    """Definition of a component event/callback."""
    name: str = Field(..., description="Event handler name")
    payload_type: str = Field(..., description="TypeScript type for event payload")
    description: str = Field(default="", description="Event description")
    example: Optional[Dict[str, Any]] = Field(default=None, description="Example payload")


class StyleDefinition(BaseModel):
    """CSS/styling definition."""
    class_name: str = Field(..., description="CSS class name")
    css_vars: Dict[str, str] = Field(default_factory=dict, description="CSS custom properties")
    description: str = Field(default="", description="Style description")


class APIEndpoint(BaseModel):
    """API endpoint used by component."""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="API path")
    description: str = Field(default="", description="Endpoint description")
    request_type: Optional[str] = Field(default=None, description="Request body type")
    response_type: str = Field(..., description="Response type")


class ComponentSpec(BaseModel):
    """Complete component specification."""
    name: str = Field(..., description="Component name")
    type: ComponentType = Field(..., description="Component type")
    description: str = Field(default="", description="Component description")
    props: List[PropDefinition] = Field(default_factory=list, description="Component props")
    state: List[StateDefinition] = Field(default_factory=list, description="Component state")
    events: List[EventDefinition] = Field(default_factory=list, description="Component events")
    styles: List[StyleDefinition] = Field(default_factory=list, description="Component styles")
    api_endpoints: List[APIEndpoint] = Field(default_factory=list, description="Used API endpoints")
    dependencies: List[str] = Field(default_factory=list, description="NPM dependencies")
    example_usage: str = Field(default="", description="Example code")
    framework: Framework = Field(default=Framework.REACT, description="Target framework")


# =============================================================================
# GRAPH VIEWER COMPONENT
# =============================================================================

def get_graph_viewer_spec(framework: Framework = Framework.REACT) -> ComponentSpec:
    """
    Get specification for the Graph Viewer component.

    The Graph Viewer displays entity-relationship graphs with:
    - Interactive node/edge visualization
    - Multiple layout algorithms
    - Zoom/pan controls
    - Node selection and highlighting
    - Context menus
    - Real-time updates via WebSocket
    """
    return ComponentSpec(
        name="GraphViewer",
        type=ComponentType.GRAPH_VIEWER,
        description="Interactive graph visualization component for entity relationships",
        framework=framework,
        props=[
            PropDefinition(
                name="projectId",
                type="string",
                required=True,
                description="Project ID to load graph from"
            ),
            PropDefinition(
                name="layout",
                type="'force_directed' | 'hierarchical' | 'circular' | 'radial' | 'grid'",
                required=False,
                default="force_directed",
                description="Graph layout algorithm",
                options=["force_directed", "hierarchical", "circular", "radial", "grid"]
            ),
            PropDefinition(
                name="width",
                type="number | string",
                required=False,
                default="100%",
                description="Component width"
            ),
            PropDefinition(
                name="height",
                type="number | string",
                required=False,
                default="600px",
                description="Component height"
            ),
            PropDefinition(
                name="showMinimap",
                type="boolean",
                required=False,
                default=True,
                description="Show navigation minimap"
            ),
            PropDefinition(
                name="showControls",
                type="boolean",
                required=False,
                default=True,
                description="Show zoom/layout controls"
            ),
            PropDefinition(
                name="enableSelection",
                type="boolean",
                required=False,
                default=True,
                description="Enable node selection"
            ),
            PropDefinition(
                name="enableDrag",
                type="boolean",
                required=False,
                default=True,
                description="Enable node dragging"
            ),
            PropDefinition(
                name="highlightedNodes",
                type="string[]",
                required=False,
                default=[],
                description="IDs of nodes to highlight"
            ),
            PropDefinition(
                name="selectedNodes",
                type="string[]",
                required=False,
                default=[],
                description="IDs of currently selected nodes"
            ),
            PropDefinition(
                name="filterEntityTypes",
                type="EntityType[]",
                required=False,
                default=[],
                description="Filter to show only specific entity types"
            ),
            PropDefinition(
                name="filterRelationshipTypes",
                type="string[]",
                required=False,
                default=[],
                description="Filter to show only specific relationship types"
            ),
            PropDefinition(
                name="theme",
                type="'light' | 'dark' | 'auto'",
                required=False,
                default="auto",
                description="Color theme"
            ),
            PropDefinition(
                name="realtimeUpdates",
                type="boolean",
                required=False,
                default=True,
                description="Enable WebSocket real-time updates"
            ),
        ],
        state=[
            StateDefinition(
                name="nodes",
                type="GraphNode[]",
                initial=[],
                description="Current graph nodes"
            ),
            StateDefinition(
                name="edges",
                type="GraphEdge[]",
                initial=[],
                description="Current graph edges"
            ),
            StateDefinition(
                name="loading",
                type="boolean",
                initial=True,
                description="Loading state"
            ),
            StateDefinition(
                name="error",
                type="Error | null",
                initial=None,
                description="Error state"
            ),
            StateDefinition(
                name="zoom",
                type="number",
                initial=1.0,
                description="Current zoom level"
            ),
            StateDefinition(
                name="pan",
                type="{ x: number, y: number }",
                initial={"x": 0, "y": 0},
                description="Current pan position"
            ),
            StateDefinition(
                name="hoveredNode",
                type="string | null",
                initial=None,
                description="ID of currently hovered node"
            ),
        ],
        events=[
            EventDefinition(
                name="onNodeClick",
                payload_type="{ node: GraphNode, event: MouseEvent }",
                description="Fired when a node is clicked",
                example={"node": {"id": "entity-1", "label": "John Doe", "type": "person"}}
            ),
            EventDefinition(
                name="onNodeDoubleClick",
                payload_type="{ node: GraphNode, event: MouseEvent }",
                description="Fired when a node is double-clicked"
            ),
            EventDefinition(
                name="onNodeHover",
                payload_type="{ node: GraphNode | null, event: MouseEvent }",
                description="Fired when hovering over a node"
            ),
            EventDefinition(
                name="onNodeDragEnd",
                payload_type="{ node: GraphNode, position: { x: number, y: number } }",
                description="Fired when node drag completes"
            ),
            EventDefinition(
                name="onEdgeClick",
                payload_type="{ edge: GraphEdge, event: MouseEvent }",
                description="Fired when an edge is clicked"
            ),
            EventDefinition(
                name="onSelectionChange",
                payload_type="{ selectedNodes: string[], selectedEdges: string[] }",
                description="Fired when selection changes"
            ),
            EventDefinition(
                name="onZoomChange",
                payload_type="{ zoom: number, pan: { x: number, y: number } }",
                description="Fired when zoom/pan changes"
            ),
            EventDefinition(
                name="onLayoutComplete",
                payload_type="{ layout: string, duration: number }",
                description="Fired when layout algorithm completes"
            ),
            EventDefinition(
                name="onContextMenu",
                payload_type="{ node?: GraphNode, edge?: GraphEdge, position: { x: number, y: number } }",
                description="Fired on right-click for context menu"
            ),
            EventDefinition(
                name="onError",
                payload_type="{ error: Error, context: string }",
                description="Fired when an error occurs"
            ),
        ],
        styles=[
            StyleDefinition(
                class_name="bh-graph-viewer",
                css_vars={
                    "--bh-node-person-color": "#4a90d9",
                    "--bh-node-organization-color": "#50c878",
                    "--bh-node-device-color": "#ff7f50",
                    "--bh-node-location-color": "#dda0dd",
                    "--bh-node-event-color": "#ffd700",
                    "--bh-node-document-color": "#d3d3d3",
                    "--bh-edge-color": "#888888",
                    "--bh-edge-highlight-color": "#ff6b6b",
                    "--bh-selection-color": "#007bff",
                    "--bh-background-color": "#ffffff",
                },
                description="Main graph viewer container"
            ),
            StyleDefinition(
                class_name="bh-graph-node",
                css_vars={
                    "--bh-node-size": "40px",
                    "--bh-node-border-width": "2px",
                    "--bh-node-font-size": "12px",
                },
                description="Graph node styling"
            ),
            StyleDefinition(
                class_name="bh-graph-controls",
                css_vars={},
                description="Zoom/layout control panel"
            ),
        ],
        api_endpoints=[
            APIEndpoint(
                method="GET",
                path="/visualization/{project}/graph",
                description="Fetch project graph data",
                response_type="VisualizationGraph"
            ),
            APIEndpoint(
                method="GET",
                path="/visualization/{project}/entity/{id}/neighborhood",
                description="Fetch entity neighborhood",
                response_type="VisualizationGraph"
            ),
            APIEndpoint(
                method="POST",
                path="/visualization/{project}/export",
                description="Export graph in various formats",
                request_type="ExportRequest",
                response_type="ExportResponse"
            ),
        ],
        dependencies=[
            "d3",
            "@types/d3",
            "d3-force",
            "d3-zoom",
            "d3-selection",
        ],
        example_usage="""
import { GraphViewer } from '@basset-hound/components';

function InvestigationView() {
  const handleNodeClick = ({ node }) => {
    console.log('Clicked entity:', node.id);
    // Navigate to entity detail page
  };

  const handleSelectionChange = ({ selectedNodes }) => {
    // Update selection state for bulk operations
  };

  return (
    <GraphViewer
      projectId="my-investigation"
      layout="force_directed"
      height="80vh"
      showMinimap={true}
      showControls={true}
      onNodeClick={handleNodeClick}
      onSelectionChange={handleSelectionChange}
      realtimeUpdates={true}
    />
  );
}
"""
    )


# =============================================================================
# ENTITY CARD COMPONENT
# =============================================================================

def get_entity_card_spec(framework: Framework = Framework.REACT) -> ComponentSpec:
    """
    Get specification for the Entity Card component.

    The Entity Card displays a summary of an entity with:
    - Type-specific icon and color
    - Key profile information
    - Relationship count
    - Quick actions
    """
    return ComponentSpec(
        name="EntityCard",
        type=ComponentType.ENTITY_CARD,
        description="Compact entity summary card with key information",
        framework=framework,
        props=[
            PropDefinition(
                name="entity",
                type="Entity",
                required=True,
                description="Entity object to display"
            ),
            PropDefinition(
                name="variant",
                type="'compact' | 'standard' | 'detailed'",
                required=False,
                default="standard",
                description="Card size variant"
            ),
            PropDefinition(
                name="showRelationships",
                type="boolean",
                required=False,
                default=True,
                description="Show relationship count"
            ),
            PropDefinition(
                name="showActions",
                type="boolean",
                required=False,
                default=True,
                description="Show action buttons"
            ),
            PropDefinition(
                name="selectable",
                type="boolean",
                required=False,
                default=False,
                description="Enable selection checkbox"
            ),
            PropDefinition(
                name="selected",
                type="boolean",
                required=False,
                default=False,
                description="Current selection state"
            ),
            PropDefinition(
                name="highlighted",
                type="boolean",
                required=False,
                default=False,
                description="Highlight the card"
            ),
        ],
        events=[
            EventDefinition(
                name="onClick",
                payload_type="{ entity: Entity, event: MouseEvent }",
                description="Fired when card is clicked"
            ),
            EventDefinition(
                name="onEdit",
                payload_type="{ entity: Entity }",
                description="Fired when edit action is triggered"
            ),
            EventDefinition(
                name="onDelete",
                payload_type="{ entity: Entity }",
                description="Fired when delete action is triggered"
            ),
            EventDefinition(
                name="onSelect",
                payload_type="{ entity: Entity, selected: boolean }",
                description="Fired when selection changes"
            ),
            EventDefinition(
                name="onViewGraph",
                payload_type="{ entity: Entity }",
                description="Fired when view in graph is triggered"
            ),
        ],
        styles=[
            StyleDefinition(
                class_name="bh-entity-card",
                css_vars={
                    "--bh-card-border-radius": "8px",
                    "--bh-card-shadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "--bh-card-padding": "16px",
                },
                description="Entity card container"
            ),
        ],
        api_endpoints=[
            APIEndpoint(
                method="GET",
                path="/projects/{project}/entities/{id}",
                description="Fetch entity details",
                response_type="Entity"
            ),
            APIEndpoint(
                method="DELETE",
                path="/projects/{project}/entities/{id}",
                description="Delete entity",
                response_type="{ success: boolean }"
            ),
        ],
        dependencies=[],
        example_usage="""
import { EntityCard } from '@basset-hound/components';

function EntityList({ entities }) {
  return (
    <div className="entity-grid">
      {entities.map(entity => (
        <EntityCard
          key={entity.id}
          entity={entity}
          variant="standard"
          showRelationships={true}
          onClick={({ entity }) => navigate(`/entity/${entity.id}`)}
          onEdit={({ entity }) => openEditModal(entity)}
        />
      ))}
    </div>
  );
}
"""
    )


# =============================================================================
# TIMELINE VIEWER COMPONENT
# =============================================================================

def get_timeline_viewer_spec(framework: Framework = Framework.REACT) -> ComponentSpec:
    """
    Get specification for the Timeline Viewer component.

    The Timeline Viewer displays temporal data with:
    - Chronological event display
    - Zoomable time axis
    - Event filtering
    - Entity tracking over time
    """
    return ComponentSpec(
        name="TimelineViewer",
        type=ComponentType.TIMELINE_VIEWER,
        description="Temporal visualization of entity and relationship events",
        framework=framework,
        props=[
            PropDefinition(
                name="projectId",
                type="string",
                required=True,
                description="Project ID to load timeline from"
            ),
            PropDefinition(
                name="entityId",
                type="string",
                required=False,
                description="Optional entity ID to filter timeline"
            ),
            PropDefinition(
                name="startDate",
                type="Date | string",
                required=False,
                description="Start date for timeline range"
            ),
            PropDefinition(
                name="endDate",
                type="Date | string",
                required=False,
                description="End date for timeline range"
            ),
            PropDefinition(
                name="granularity",
                type="'hour' | 'day' | 'week' | 'month'",
                required=False,
                default="day",
                description="Time granularity for grouping"
            ),
            PropDefinition(
                name="eventTypes",
                type="string[]",
                required=False,
                default=[],
                description="Filter by event types"
            ),
            PropDefinition(
                name="height",
                type="number | string",
                required=False,
                default="400px",
                description="Component height"
            ),
            PropDefinition(
                name="showHeatmap",
                type="boolean",
                required=False,
                default=True,
                description="Show activity heatmap"
            ),
        ],
        state=[
            StateDefinition(
                name="events",
                type="TimelineEvent[]",
                initial=[],
                description="Timeline events"
            ),
            StateDefinition(
                name="loading",
                type="boolean",
                initial=True,
                description="Loading state"
            ),
            StateDefinition(
                name="visibleRange",
                type="{ start: Date, end: Date }",
                initial=None,
                description="Currently visible time range"
            ),
        ],
        events=[
            EventDefinition(
                name="onEventClick",
                payload_type="{ event: TimelineEvent }",
                description="Fired when a timeline event is clicked"
            ),
            EventDefinition(
                name="onRangeChange",
                payload_type="{ start: Date, end: Date }",
                description="Fired when visible range changes"
            ),
            EventDefinition(
                name="onEntityClick",
                payload_type="{ entityId: string }",
                description="Fired when an entity in the timeline is clicked"
            ),
        ],
        api_endpoints=[
            APIEndpoint(
                method="GET",
                path="/timeline/{project}/entity/{id}",
                description="Fetch entity timeline",
                response_type="TimelineEvent[]"
            ),
            APIEndpoint(
                method="GET",
                path="/timeline/{project}/activity",
                description="Fetch project activity heatmap",
                response_type="ActivityHeatmapData[]"
            ),
        ],
        dependencies=[
            "d3",
            "d3-time",
            "d3-scale",
        ],
        example_usage="""
import { TimelineViewer } from '@basset-hound/components';

function EntityHistory({ projectId, entityId }) {
  return (
    <TimelineViewer
      projectId={projectId}
      entityId={entityId}
      granularity="day"
      showHeatmap={true}
      onEventClick={({ event }) => {
        console.log('Event:', event);
      }}
    />
  );
}
"""
    )


# =============================================================================
# IMPORT WIZARD COMPONENT
# =============================================================================

def get_import_wizard_spec(framework: Framework = Framework.REACT) -> ComponentSpec:
    """
    Get specification for the Import Wizard component.

    The Import Wizard provides:
    - Multi-step import flow
    - Format detection
    - Field mapping
    - Preview and validation
    - Progress tracking
    """
    return ComponentSpec(
        name="ImportWizard",
        type=ComponentType.IMPORT_WIZARD,
        description="Multi-step wizard for importing data from OSINT tools",
        framework=framework,
        props=[
            PropDefinition(
                name="projectId",
                type="string",
                required=True,
                description="Target project for import"
            ),
            PropDefinition(
                name="supportedFormats",
                type="ImportFormat[]",
                required=False,
                default=["maltego", "spiderfoot", "theharvester", "shodan", "hibp", "csv", "json"],
                description="List of supported import formats"
            ),
            PropDefinition(
                name="maxFileSize",
                type="number",
                required=False,
                default=52428800,  # 50MB
                description="Maximum file size in bytes"
            ),
            PropDefinition(
                name="dryRunByDefault",
                type="boolean",
                required=False,
                default=True,
                description="Enable dry-run validation by default"
            ),
        ],
        state=[
            StateDefinition(
                name="step",
                type="'upload' | 'format' | 'mapping' | 'preview' | 'importing' | 'complete'",
                initial="upload",
                description="Current wizard step"
            ),
            StateDefinition(
                name="file",
                type="File | null",
                initial=None,
                description="Uploaded file"
            ),
            StateDefinition(
                name="detectedFormat",
                type="ImportFormat | null",
                initial=None,
                description="Auto-detected format"
            ),
            StateDefinition(
                name="fieldMapping",
                type="Record<string, string>",
                initial={},
                description="Field mapping configuration"
            ),
            StateDefinition(
                name="previewData",
                type="ImportPreview | null",
                initial=None,
                description="Preview of import results"
            ),
            StateDefinition(
                name="progress",
                type="{ percent: number, message: string }",
                initial={"percent": 0, "message": ""},
                description="Import progress"
            ),
            StateDefinition(
                name="result",
                type="ImportResult | null",
                initial=None,
                description="Final import result"
            ),
        ],
        events=[
            EventDefinition(
                name="onComplete",
                payload_type="{ result: ImportResult }",
                description="Fired when import completes successfully"
            ),
            EventDefinition(
                name="onError",
                payload_type="{ error: Error, step: string }",
                description="Fired when an error occurs"
            ),
            EventDefinition(
                name="onCancel",
                payload_type="{}",
                description="Fired when user cancels import"
            ),
            EventDefinition(
                name="onStepChange",
                payload_type="{ step: string, prevStep: string }",
                description="Fired when wizard step changes"
            ),
        ],
        api_endpoints=[
            APIEndpoint(
                method="GET",
                path="/import/formats",
                description="Get supported import formats",
                response_type="ImportFormat[]"
            ),
            APIEndpoint(
                method="POST",
                path="/import/{project}/validate",
                description="Validate import without importing",
                request_type="ImportRequest",
                response_type="ImportResult"
            ),
            APIEndpoint(
                method="POST",
                path="/import/{project}/{format}",
                description="Execute import",
                request_type="FormData",
                response_type="ImportResult"
            ),
        ],
        dependencies=[
            "react-dropzone",
        ],
        example_usage="""
import { ImportWizard } from '@basset-hound/components';

function ImportPage({ projectId }) {
  const handleComplete = ({ result }) => {
    toast.success(`Imported ${result.entities_created} entities!`);
    navigate(`/project/${projectId}`);
  };

  return (
    <ImportWizard
      projectId={projectId}
      dryRunByDefault={true}
      onComplete={handleComplete}
      onError={({ error }) => toast.error(error.message)}
    />
  );
}
"""
    )


# =============================================================================
# SEARCH BAR COMPONENT
# =============================================================================

def get_search_bar_spec(framework: Framework = Framework.REACT) -> ComponentSpec:
    """
    Get specification for the Search Bar component.
    """
    return ComponentSpec(
        name="SearchBar",
        type=ComponentType.SEARCH_BAR,
        description="Advanced search bar with autocomplete and filters",
        framework=framework,
        props=[
            PropDefinition(
                name="projectId",
                type="string",
                required=False,
                description="Scope search to specific project"
            ),
            PropDefinition(
                name="placeholder",
                type="string",
                required=False,
                default="Search entities...",
                description="Placeholder text"
            ),
            PropDefinition(
                name="showFilters",
                type="boolean",
                required=False,
                default=True,
                description="Show filter dropdown"
            ),
            PropDefinition(
                name="showSuggestions",
                type="boolean",
                required=False,
                default=True,
                description="Show autocomplete suggestions"
            ),
            PropDefinition(
                name="debounceMs",
                type="number",
                required=False,
                default=300,
                description="Debounce delay for search"
            ),
        ],
        events=[
            EventDefinition(
                name="onSearch",
                payload_type="{ query: string, filters: SearchFilters }",
                description="Fired when search is executed"
            ),
            EventDefinition(
                name="onSuggestionSelect",
                payload_type="{ suggestion: SearchSuggestion }",
                description="Fired when a suggestion is selected"
            ),
            EventDefinition(
                name="onFilterChange",
                payload_type="{ filters: SearchFilters }",
                description="Fired when filters change"
            ),
        ],
        api_endpoints=[
            APIEndpoint(
                method="GET",
                path="/search",
                description="Execute search",
                response_type="SearchResult[]"
            ),
            APIEndpoint(
                method="GET",
                path="/ml/suggest",
                description="Get search suggestions",
                response_type="SearchSuggestion[]"
            ),
        ],
        dependencies=[],
        example_usage="""
import { SearchBar } from '@basset-hound/components';

function Header() {
  return (
    <SearchBar
      showFilters={true}
      showSuggestions={true}
      onSearch={({ query, filters }) => {
        // Handle search
      }}
    />
  );
}
"""
    )


# =============================================================================
# SERVICE FUNCTIONS
# =============================================================================

def get_all_component_specs(framework: Framework = Framework.REACT) -> Dict[str, ComponentSpec]:
    """
    Get all component specifications.

    Returns:
        Dictionary mapping component names to their specifications
    """
    return {
        "GraphViewer": get_graph_viewer_spec(framework),
        "EntityCard": get_entity_card_spec(framework),
        "TimelineViewer": get_timeline_viewer_spec(framework),
        "ImportWizard": get_import_wizard_spec(framework),
        "SearchBar": get_search_bar_spec(framework),
    }


def get_component_spec(
    component_type: ComponentType,
    framework: Framework = Framework.REACT
) -> Optional[ComponentSpec]:
    """
    Get specification for a specific component type.

    Args:
        component_type: Type of component
        framework: Target frontend framework

    Returns:
        ComponentSpec or None if not found
    """
    spec_map = {
        ComponentType.GRAPH_VIEWER: get_graph_viewer_spec,
        ComponentType.ENTITY_CARD: get_entity_card_spec,
        ComponentType.TIMELINE_VIEWER: get_timeline_viewer_spec,
        ComponentType.IMPORT_WIZARD: get_import_wizard_spec,
        ComponentType.SEARCH_BAR: get_search_bar_spec,
    }

    spec_func = spec_map.get(component_type)
    if spec_func:
        return spec_func(framework)
    return None


def generate_typescript_types() -> str:
    """
    Generate TypeScript type definitions for all components.

    Returns:
        TypeScript type definitions as a string
    """
    return """
// Auto-generated TypeScript types for Basset Hound components
// Generated by api/services/frontend_components.py

export type EntityType = 'person' | 'organization' | 'device' | 'location' | 'event' | 'document';

export type LayoutAlgorithm = 'force_directed' | 'hierarchical' | 'circular' | 'radial' | 'grid';

export type ExportFormat = 'd3_json' | 'cytoscape_json' | 'graphml' | 'dot';

export interface GraphNode {
  id: string;
  label: string;
  entityType: EntityType;
  position: { x: number; y: number };
  properties: Record<string, any>;
  centrality?: number;
  degree?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationshipType: string;
  properties: Record<string, any>;
  weight?: number;
}

export interface VisualizationGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout: LayoutAlgorithm;
  bounds: { minX: number; minY: number; maxX: number; maxY: number };
  metadata: Record<string, any>;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  eventType: string;
  entityId?: string;
  details: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface ImportResult {
  success: boolean;
  totalRecords: number;
  entitiesCreated: number;
  orphansCreated: number;
  relationshipsCreated: number;
  skipped: number;
  errors: Array<{ index: number; message: string }>;
  warnings: Array<{ index: number; field: string; message: string }>;
  dryRun: boolean;
  sourceTool: string;
}

export interface SearchFilters {
  entityTypes?: EntityType[];
  relationshipTypes?: string[];
  dateRange?: { start: string; end: string };
  fields?: string[];
}

export interface SearchResult {
  entityId: string;
  projectId: string;
  entityType: EntityType;
  displayName: string;
  matches: Array<{ field: string; value: string; highlight: string }>;
  score: number;
}
"""


# =============================================================================
# API ROUTER SUPPORT
# =============================================================================

_component_specs_cache: Dict[str, ComponentSpec] = {}


def get_cached_specs(framework: Framework = Framework.REACT) -> Dict[str, ComponentSpec]:
    """Get cached component specifications."""
    cache_key = framework.value
    if cache_key not in _component_specs_cache:
        _component_specs_cache[cache_key] = get_all_component_specs(framework)
    return _component_specs_cache[cache_key]


def clear_specs_cache() -> None:
    """Clear the component specs cache."""
    global _component_specs_cache
    _component_specs_cache = {}
