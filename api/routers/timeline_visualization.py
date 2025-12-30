"""
Timeline Visualization Router for Basset Hound OSINT Platform.

This module provides API endpoints for temporal graph visualization,
allowing clients to view and analyze how entities and relationships
evolve over time.

Endpoints:
- GET /timeline/{project}/entity/{entity_id} - Entity timeline events
- GET /timeline/{project}/relationship/{entity1_id}/{entity2_id} - Relationship timeline
- GET /timeline/{project}/activity - Project activity heatmap
- GET /timeline/{project}/snapshot - Graph snapshot at timestamp
- GET /timeline/{project}/entity/{entity_id}/evolution - Entity evolution history
- POST /timeline/{project}/compare - Compare time periods
"""

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.timeline_visualization import (
    TimelineVisualizationService,
    TimelineEvent,
    TimelineGranularity,
    ActivityHeatmapData,
    TemporalSnapshot,
    EntityEvolution,
    PeriodComparison,
    TimePeriod,
    GraphStats,
    get_timeline_visualization_service,
)
from ..services.timeline_service import get_timeline_service, TimelineService
from ..services.audit_logger import get_audit_logger


# =============================================================================
# ROUTER SETUP
# =============================================================================


router = APIRouter(
    prefix="/timeline-viz/{project_safe_name}",
    tags=["timeline-visualization"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class TimelineEventResponse(BaseModel):
    """Response model for a single timeline event."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "event_type": "entity_updated",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {"field": "email", "old_value": "old@example.com"},
                "metadata": {"actor": "user123"},
                "event_id": "event-123"
            }
        }
    )

    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    event_type: str = Field(..., description="Type of event")
    entity_id: str = Field(..., description="Related entity ID")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    event_id: str = Field(..., description="Unique event identifier")


class EntityTimelineResponse(BaseModel):
    """Response model for entity timeline."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "events": [],
                "total_events": 0,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z"
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    entity_id: str = Field(..., description="Entity identifier")
    events: List[TimelineEventResponse] = Field(default_factory=list, description="Timeline events")
    total_events: int = Field(default=0, description="Total number of events")
    start_date: Optional[str] = Field(None, description="Filter start date")
    end_date: Optional[str] = Field(None, description="Filter end date")


class RelationshipTimelineResponse(BaseModel):
    """Response model for relationship timeline."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "entity1_id": "entity-1",
                "entity2_id": "entity-2",
                "events": [],
                "total_events": 0
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    entity1_id: str = Field(..., description="First entity identifier")
    entity2_id: str = Field(..., description="Second entity identifier")
    events: List[TimelineEventResponse] = Field(default_factory=list, description="Timeline events")
    total_events: int = Field(default=0, description="Total number of events")


class ActivityHeatmapResponse(BaseModel):
    """Response model for activity heatmap."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "granularity": "day",
                "data": [],
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "total_events": 150
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    granularity: str = Field(..., description="Time bucket granularity")
    data: List[dict[str, Any]] = Field(default_factory=list, description="Heatmap data")
    start_date: str = Field(..., description="Period start date")
    end_date: str = Field(..., description="Period end date")
    total_events: int = Field(default=0, description="Total events in period")


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "node_count": 50,
                "edge_count": 75,
                "density": 0.06,
                "avg_degree": 3.0,
                "isolated_nodes": 5
            }
        }
    )

    node_count: int = Field(default=0, description="Number of nodes")
    edge_count: int = Field(default=0, description="Number of edges")
    density: float = Field(default=0.0, description="Graph density")
    avg_degree: float = Field(default=0.0, description="Average node degree")
    isolated_nodes: int = Field(default=0, description="Isolated nodes count")
    entity_type_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Entity type distribution"
    )
    relationship_type_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Relationship type distribution"
    )


class TemporalSnapshotResponse(BaseModel):
    """Response model for temporal graph snapshot."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "timestamp": "2024-01-15T10:30:00Z",
                "nodes": [],
                "edges": [],
                "stats": {"node_count": 50, "edge_count": 75}
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    timestamp: str = Field(..., description="Snapshot timestamp")
    nodes: List[dict[str, Any]] = Field(default_factory=list, description="Nodes at this time")
    edges: List[dict[str, Any]] = Field(default_factory=list, description="Edges at this time")
    stats: GraphStatsResponse = Field(default_factory=GraphStatsResponse, description="Graph statistics")


class EntityVersionResponse(BaseModel):
    """Response model for an entity version."""
    timestamp: str = Field(..., description="Version timestamp")
    version_number: int = Field(..., description="Version sequence number")
    profile_snapshot: dict[str, Any] = Field(default_factory=dict, description="Profile at this version")
    changes: dict[str, List[str]] = Field(
        default_factory=lambda: {"added": [], "modified": [], "removed": []},
        description="Changes from previous version"
    )
    change_details: dict[str, Any] = Field(default_factory=dict, description="Detailed changes")


class EntityEvolutionResponse(BaseModel):
    """Response model for entity evolution history."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_label": "John Doe",
                "versions": [],
                "total_versions": 5,
                "first_seen": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    entity_id: str = Field(..., description="Entity identifier")
    entity_label: str = Field(..., description="Current entity label")
    versions: List[EntityVersionResponse] = Field(default_factory=list, description="Version history")
    total_versions: int = Field(default=0, description="Total version count")
    first_seen: Optional[str] = Field(None, description="First creation timestamp")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    relationship_history: List[dict[str, Any]] = Field(
        default_factory=list,
        description="Relationship change history"
    )


class PeriodStatsResponse(BaseModel):
    """Response model for period statistics."""
    start_date: str = Field(..., description="Period start")
    end_date: str = Field(..., description="Period end")
    total_events: int = Field(default=0, description="Total events")
    entity_events: int = Field(default=0, description="Entity events")
    relationship_events: int = Field(default=0, description="Relationship events")
    new_entities: int = Field(default=0, description="New entities")
    new_relationships: int = Field(default=0, description="New relationships")
    active_entities: int = Field(default=0, description="Active entities")
    event_type_breakdown: dict[str, int] = Field(default_factory=dict, description="Events by type")
    graph_stats: GraphStatsResponse = Field(default_factory=GraphStatsResponse, description="Graph stats")


class StatsDifferenceResponse(BaseModel):
    """Response model for statistics difference."""
    metric: str = Field(..., description="Metric name")
    period1_value: float = Field(..., description="Period 1 value")
    period2_value: float = Field(..., description="Period 2 value")
    absolute_change: float = Field(..., description="Absolute change")
    percent_change: Optional[float] = Field(None, description="Percentage change")
    trend: str = Field(default="stable", description="Trend direction")


class PeriodComparisonResponse(BaseModel):
    """Response model for period comparison."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "period1_stats": {},
                "period2_stats": {},
                "differences": [],
                "summary": {}
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    period1_stats: PeriodStatsResponse = Field(..., description="Period 1 statistics")
    period2_stats: PeriodStatsResponse = Field(..., description="Period 2 statistics")
    differences: List[StatsDifferenceResponse] = Field(
        default_factory=list,
        description="Statistical differences"
    )
    summary: dict[str, Any] = Field(default_factory=dict, description="Summary analysis")


class ComparePeriodsRequest(BaseModel):
    """Request model for comparing time periods."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period1": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-07T23:59:59Z"
                },
                "period2": {
                    "start_date": "2024-01-08T00:00:00Z",
                    "end_date": "2024-01-14T23:59:59Z"
                }
            }
        }
    )

    period1: dict[str, str] = Field(
        ...,
        description="First period with start_date and end_date"
    )
    period2: dict[str, str] = Field(
        ...,
        description="Second period with start_date and end_date"
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string."""
    if value is None:
        return None
    try:
        # Handle ISO format with Z suffix
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


def _get_service(neo4j_handler) -> TimelineVisualizationService:
    """Get the timeline visualization service with dependencies."""
    # Get or create timeline service
    try:
        timeline_service = get_timeline_service(neo4j_handler)
    except (ValueError, RuntimeError):
        from ..services.timeline_service import TimelineService, set_timeline_service
        timeline_service = TimelineService(neo4j_handler)
        set_timeline_service(timeline_service)

    # Get audit logger
    try:
        audit_logger = get_audit_logger()
    except Exception:
        audit_logger = None

    # Get timeline visualization service
    return get_timeline_visualization_service(
        neo4j_handler=neo4j_handler,
        timeline_service=timeline_service,
        audit_logger=audit_logger
    )


def _event_to_response(event: TimelineEvent) -> TimelineEventResponse:
    """Convert a TimelineEvent to a response model."""
    return TimelineEventResponse(
        timestamp=event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
        event_type=event.event_type,
        entity_id=event.entity_id,
        details=event.details,
        metadata=event.metadata,
        event_id=event.event_id
    )


def _graph_stats_to_response(stats: GraphStats) -> GraphStatsResponse:
    """Convert GraphStats to response model."""
    return GraphStatsResponse(
        node_count=stats.node_count,
        edge_count=stats.edge_count,
        density=stats.density,
        avg_degree=stats.avg_degree,
        isolated_nodes=stats.isolated_nodes,
        entity_type_distribution=stats.entity_type_distribution,
        relationship_type_distribution=stats.relationship_type_distribution
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/entity/{entity_id}",
    response_model=EntityTimelineResponse,
    summary="Get entity timeline",
    description="Retrieve timeline events for a specific entity showing its history.",
    responses={
        200: {"description": "Entity timeline retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_timeline(
    project_safe_name: str,
    entity_id: str,
    start_date: Optional[str] = Query(
        None,
        description="Filter events after this date (ISO 8601 format)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter events before this date (ISO 8601 format)"
    ),
    event_types: Optional[str] = Query(
        None,
        description="Comma-separated list of event types to filter"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get timeline events for a specific entity.

    Returns all events related to an entity including creation, updates,
    relationship changes, and other tracked events. Events are ordered
    by timestamp descending (most recent first).

    - **project_safe_name**: URL-safe project identifier
    - **entity_id**: Entity identifier
    - **start_date**: Optional start date filter (ISO 8601)
    - **end_date**: Optional end date filter (ISO 8601)
    - **event_types**: Optional comma-separated event type filter
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entity exists
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        service = _get_service(neo4j_handler)

        # Parse event types filter
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(",")]

        events = await service.get_entity_timeline(
            project_id=project_safe_name,
            entity_id=entity_id,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
            event_types=event_type_list
        )

        return EntityTimelineResponse(
            project_id=project_safe_name,
            entity_id=entity_id,
            events=[_event_to_response(e) for e in events],
            total_events=len(events),
            start_date=start_date,
            end_date=end_date
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity timeline: {str(e)}"
        )


@router.get(
    "/relationship/{entity1_id}/{entity2_id}",
    response_model=RelationshipTimelineResponse,
    summary="Get relationship timeline",
    description="Track relationship changes between two entities over time.",
    responses={
        200: {"description": "Relationship timeline retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_relationship_timeline(
    project_safe_name: str,
    entity1_id: str,
    entity2_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the timeline of relationship changes between two entities.

    Returns all events related to the relationship between the two
    specified entities, including when it was created, modified, or removed.

    - **project_safe_name**: URL-safe project identifier
    - **entity1_id**: First entity identifier
    - **entity2_id**: Second entity identifier
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entities exist
    entity1 = neo4j_handler.get_person(project_safe_name, entity1_id)
    if not entity1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity1_id}' not found in project '{project_safe_name}'"
        )

    entity2 = neo4j_handler.get_person(project_safe_name, entity2_id)
    if not entity2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity2_id}' not found in project '{project_safe_name}'"
        )

    try:
        service = _get_service(neo4j_handler)

        events = await service.get_relationship_timeline(
            project_id=project_safe_name,
            entity1_id=entity1_id,
            entity2_id=entity2_id
        )

        return RelationshipTimelineResponse(
            project_id=project_safe_name,
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            events=[_event_to_response(e) for e in events],
            total_events=len(events)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relationship timeline: {str(e)}"
        )


@router.get(
    "/activity",
    response_model=ActivityHeatmapResponse,
    summary="Get project activity heatmap",
    description="Get activity heatmap data for visualizing project activity over time.",
    responses={
        200: {"description": "Activity heatmap data retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_project_activity_timeline(
    project_safe_name: str,
    start_date: Optional[str] = Query(
        None,
        description="Start date for activity analysis (ISO 8601)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date for activity analysis (ISO 8601)"
    ),
    granularity: str = Query(
        "day",
        description="Time bucket granularity: hour, day, week, month"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get activity heatmap data for a project.

    Returns aggregated event counts in time buckets suitable for
    heatmap visualization. Useful for identifying activity patterns
    and busy periods.

    - **project_safe_name**: URL-safe project identifier
    - **start_date**: Start of analysis period (default: 30 days ago)
    - **end_date**: End of analysis period (default: now)
    - **granularity**: Time bucket size (hour, day, week, month)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Validate granularity
    try:
        granularity_enum = TimelineGranularity(granularity.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid granularity '{granularity}'. Must be one of: hour, day, week, month"
        )

    try:
        service = _get_service(neo4j_handler)

        # Parse dates
        parsed_start = _parse_datetime(start_date)
        parsed_end = _parse_datetime(end_date)

        # Set defaults
        if parsed_end is None:
            parsed_end = datetime.now(timezone.utc)
        if parsed_start is None:
            parsed_start = parsed_end - timedelta(days=30)

        heatmap_data = await service.get_project_activity_timeline(
            project_id=project_safe_name,
            start_date=parsed_start,
            end_date=parsed_end,
            granularity=granularity_enum
        )

        # Calculate total events
        total_events = sum(d.count for d in heatmap_data)

        return ActivityHeatmapResponse(
            project_id=project_safe_name,
            granularity=granularity,
            data=[{
                "date": d.date,
                "count": d.count,
                "entity_count": d.entity_count,
                "relationship_count": d.relationship_count,
                "event_types": d.event_types
            } for d in heatmap_data],
            start_date=parsed_start.isoformat(),
            end_date=parsed_end.isoformat(),
            total_events=total_events
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity heatmap: {str(e)}"
        )


@router.get(
    "/snapshot",
    response_model=TemporalSnapshotResponse,
    summary="Get temporal graph snapshot",
    description="Get the graph state at a specific point in time.",
    responses={
        200: {"description": "Graph snapshot retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_temporal_graph_snapshot(
    project_safe_name: str,
    timestamp: str = Query(
        ...,
        description="Timestamp for snapshot (ISO 8601 format)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get a snapshot of the graph at a specific point in time.

    Reconstructs the graph state as it existed at the given timestamp,
    including only entities and relationships that existed at that time.

    - **project_safe_name**: URL-safe project identifier
    - **timestamp**: Point in time for the snapshot (ISO 8601)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Parse timestamp
    parsed_timestamp = _parse_datetime(timestamp)
    if parsed_timestamp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format. Use ISO 8601 format."
        )

    try:
        service = _get_service(neo4j_handler)

        snapshot = await service.get_temporal_graph_snapshot(
            project_id=project_safe_name,
            timestamp=parsed_timestamp
        )

        return TemporalSnapshotResponse(
            project_id=project_safe_name,
            timestamp=snapshot.timestamp.isoformat(),
            nodes=snapshot.nodes,
            edges=snapshot.edges,
            stats=_graph_stats_to_response(snapshot.stats)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph snapshot: {str(e)}"
        )


@router.get(
    "/entity/{entity_id}/evolution",
    response_model=EntityEvolutionResponse,
    summary="Get entity evolution history",
    description="Track how an entity's profile changed over time.",
    responses={
        200: {"description": "Entity evolution retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_evolution(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the evolution history of an entity's profile.

    Returns all versions of an entity's profile showing how it
    changed over time, including what fields were added, modified,
    or removed in each version.

    - **project_safe_name**: URL-safe project identifier
    - **entity_id**: Entity identifier
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entity exists
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        service = _get_service(neo4j_handler)

        evolution = await service.get_entity_evolution(
            project_id=project_safe_name,
            entity_id=entity_id
        )

        return EntityEvolutionResponse(
            project_id=project_safe_name,
            entity_id=evolution.entity_id,
            entity_label=evolution.entity_label,
            versions=[
                EntityVersionResponse(
                    timestamp=v.timestamp.isoformat() if isinstance(v.timestamp, datetime) else str(v.timestamp),
                    version_number=v.version_number,
                    profile_snapshot=v.profile_snapshot,
                    changes=v.changes,
                    change_details=v.change_details
                )
                for v in evolution.versions
            ],
            total_versions=evolution.total_versions,
            first_seen=evolution.first_seen.isoformat() if evolution.first_seen else None,
            last_updated=evolution.last_updated.isoformat() if evolution.last_updated else None,
            relationship_history=evolution.relationship_history
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity evolution: {str(e)}"
        )


@router.post(
    "/compare",
    response_model=PeriodComparisonResponse,
    summary="Compare time periods",
    description="Compare graph statistics between two time periods.",
    responses={
        200: {"description": "Period comparison completed successfully"},
        400: {"description": "Invalid period specification"},
        404: {"description": "Project not found"},
    }
)
async def compare_time_periods(
    project_safe_name: str,
    request: ComparePeriodsRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Compare graph statistics between two time periods.

    Useful for trend analysis and identifying changes in activity
    patterns, entity growth, and relationship changes over time.

    - **project_safe_name**: URL-safe project identifier
    - **period1**: First period (start_date, end_date in ISO 8601)
    - **period2**: Second period (start_date, end_date in ISO 8601)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Parse period 1
    period1_start = _parse_datetime(request.period1.get("start_date"))
    period1_end = _parse_datetime(request.period1.get("end_date"))
    if period1_start is None or period1_end is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period1 dates. Use ISO 8601 format."
        )

    # Parse period 2
    period2_start = _parse_datetime(request.period2.get("start_date"))
    period2_end = _parse_datetime(request.period2.get("end_date"))
    if period2_start is None or period2_end is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period2 dates. Use ISO 8601 format."
        )

    # Validate date ranges
    if period1_start >= period1_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period 1 end_date must be after start_date"
        )
    if period2_start >= period2_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period 2 end_date must be after start_date"
        )

    try:
        service = _get_service(neo4j_handler)

        comparison = await service.compare_time_periods(
            project_id=project_safe_name,
            period1=TimePeriod(start_date=period1_start, end_date=period1_end),
            period2=TimePeriod(start_date=period2_start, end_date=period2_end)
        )

        # Convert period stats
        def period_stats_to_response(stats) -> PeriodStatsResponse:
            return PeriodStatsResponse(
                start_date=stats.start_date.isoformat() if isinstance(stats.start_date, datetime) else str(stats.start_date),
                end_date=stats.end_date.isoformat() if isinstance(stats.end_date, datetime) else str(stats.end_date),
                total_events=stats.total_events,
                entity_events=stats.entity_events,
                relationship_events=stats.relationship_events,
                new_entities=stats.new_entities,
                new_relationships=stats.new_relationships,
                active_entities=stats.active_entities,
                event_type_breakdown=stats.event_type_breakdown,
                graph_stats=_graph_stats_to_response(stats.graph_stats)
            )

        return PeriodComparisonResponse(
            project_id=project_safe_name,
            period1_stats=period_stats_to_response(comparison.period1_stats),
            period2_stats=period_stats_to_response(comparison.period2_stats),
            differences=[
                StatsDifferenceResponse(
                    metric=d.metric,
                    period1_value=d.period1_value,
                    period2_value=d.period2_value,
                    absolute_change=d.absolute_change,
                    percent_change=d.percent_change,
                    trend=d.trend
                )
                for d in comparison.differences
            ],
            summary=comparison.summary
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare time periods: {str(e)}"
        )
