"""
Timeline Analysis Router for Basset Hound.

Provides endpoints for tracking and analyzing relationship changes over time,
including entity timelines, project timelines, relationship history, and activity analysis.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.timeline_service import (
    EventType,
    TimelineEvent,
    TimelineService,
    get_timeline_service,
    set_timeline_service,
)


router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["timeline"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----


class TimelineEventResponse(BaseModel):
    """Schema for a timeline event response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_id": "550e8400-e29b-41d4-a716-446655440001",
                "project_id": "test_project",
                "event_type": "CREATED",
                "timestamp": "2024-01-15T10:30:00",
                "details": {"field": "name", "old_value": None, "new_value": "John Doe"},
                "actor": None
            }
        }
    )

    event_id: str = Field(..., description="Unique event identifier (UUID)")
    entity_id: str = Field(..., description="ID of the entity this event relates to")
    project_id: str = Field(..., description="ID of the project")
    event_type: str = Field(..., description="Type of event (CREATED, UPDATED, etc.)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of when the event occurred")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional event details")
    actor: Optional[str] = Field(None, description="Who made the change")


class TimelineListResponse(BaseModel):
    """Schema for a list of timeline events."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [],
                "count": 0,
                "project_id": "test_project"
            }
        }
    )

    events: list[TimelineEventResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of events returned")
    project_id: str = Field(..., description="Project ID")


class EntityTimelineResponse(BaseModel):
    """Schema for entity timeline response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [],
                "count": 0,
                "entity_id": "550e8400-e29b-41d4-a716-446655440001",
                "project_id": "test_project"
            }
        }
    )

    events: list[TimelineEventResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of events returned")
    entity_id: str = Field(..., description="Entity ID")
    project_id: str = Field(..., description="Project ID")


class RelationshipHistoryResponse(BaseModel):
    """Schema for relationship history response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [],
                "count": 0,
                "entity1_id": "550e8400-e29b-41d4-a716-446655440001",
                "entity2_id": "550e8400-e29b-41d4-a716-446655440002",
                "project_id": "test_project"
            }
        }
    )

    events: list[TimelineEventResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of events returned")
    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    project_id: str = Field(..., description="Project ID")


class ActivityAnalysisResponse(BaseModel):
    """Schema for activity analysis response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440001",
                "project_id": "test_project",
                "total_events": 25,
                "events_by_type": {"CREATED": 1, "UPDATED": 20, "RELATIONSHIP_ADDED": 4},
                "events_by_day": {"2024-01-15": 5, "2024-01-16": 10, "2024-01-17": 10},
                "most_active_day": "2024-01-16",
                "average_events_per_day": 0.83,
                "first_event": "2024-01-15T10:30:00",
                "last_event": "2024-01-17T18:45:00",
                "analysis_period_days": 30
            }
        }
    )

    entity_id: str = Field(..., description="Entity ID")
    project_id: str = Field(..., description="Project ID")
    total_events: int = Field(0, description="Total number of events in the period")
    events_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of events grouped by type"
    )
    events_by_day: dict[str, int] = Field(
        default_factory=dict,
        description="Count of events grouped by day"
    )
    most_active_day: Optional[str] = Field(None, description="Day with most activity")
    average_events_per_day: float = Field(0.0, description="Average events per day")
    first_event: Optional[str] = Field(None, description="Timestamp of first event")
    last_event: Optional[str] = Field(None, description="Timestamp of last event")
    analysis_period_days: int = Field(30, description="Number of days analyzed")


class RecordEventRequest(BaseModel):
    """Schema for recording a new timeline event."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "UPDATED",
                "details": {"field": "email", "old_value": "old@example.com", "new_value": "new@example.com"},
                "actor": "user123"
            }
        }
    )

    event_type: str = Field(..., description="Type of event")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")
    actor: Optional[str] = Field(None, description="Who made the change")


class RecordEventResponse(BaseModel):
    """Schema for record event response."""
    success: bool = True
    event: TimelineEventResponse


# ----- Helper Functions -----


def _get_timeline_service(neo4j_handler) -> TimelineService:
    """Get or create the timeline service with the provided handler."""
    try:
        return get_timeline_service(neo4j_handler)
    except ValueError:
        # First call, create the service
        service = TimelineService(neo4j_handler)
        set_timeline_service(service)
        return service


def _event_to_response(event: TimelineEvent) -> TimelineEventResponse:
    """Convert a TimelineEvent to a response model."""
    return TimelineEventResponse(
        event_id=event.event_id,
        entity_id=event.entity_id,
        project_id=event.project_id,
        event_type=event.event_type,
        timestamp=event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
        details=event.details,
        actor=event.actor,
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ----- Endpoints -----


@router.get(
    "/timeline",
    response_model=TimelineListResponse,
    summary="Get project timeline",
    description="Get recent timeline events for a project.",
    responses={
        200: {"description": "Timeline events retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_project_timeline(
    project_id: str,
    start_date: Optional[str] = Query(
        None,
        description="Filter events after this date (ISO 8601 format)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter events before this date (ISO 8601 format)"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of events to return"
    ),
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Get the project timeline.

    Returns all timeline events for the project, ordered by timestamp descending.
    Supports date filtering and pagination via limit.

    - **project_id**: The project identifier
    - **start_date**: Optional filter for events after this date
    - **end_date**: Optional filter for events before this date
    - **limit**: Maximum events to return (1-1000, default: 100)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    try:
        service = _get_timeline_service(neo4j_handler)
        events = service.get_project_timeline(
            project_id=project_id,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
            limit=limit,
        )

        return TimelineListResponse(
            events=[_event_to_response(e) for e in events],
            count=len(events),
            project_id=project_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project timeline: {str(e)}"
        )


@router.get(
    "/entities/{entity_id}/timeline",
    response_model=EntityTimelineResponse,
    summary="Get entity timeline",
    description="Get timeline events for a specific entity.",
    responses={
        200: {"description": "Entity timeline retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_timeline(
    project_id: str,
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
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Get the entity timeline.

    Returns all timeline events for the specified entity, ordered by
    timestamp descending. Supports date and event type filtering.

    - **project_id**: The project identifier
    - **entity_id**: The entity identifier
    - **start_date**: Optional filter for events after this date
    - **end_date**: Optional filter for events before this date
    - **event_types**: Optional comma-separated list of event types to include
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    # Verify entity exists
    entity = neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        service = _get_timeline_service(neo4j_handler)

        # Parse event types
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(",")]

        events = service.get_entity_timeline(
            project_id=project_id,
            entity_id=entity_id,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
            event_types=event_type_list,
        )

        return EntityTimelineResponse(
            events=[_event_to_response(e) for e in events],
            count=len(events),
            entity_id=entity_id,
            project_id=project_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity timeline: {str(e)}"
        )


@router.get(
    "/relationships/{entity1_id}/{entity2_id}/history",
    response_model=RelationshipHistoryResponse,
    summary="Get relationship history",
    description="Get the history of relationship changes between two entities.",
    responses={
        200: {"description": "Relationship history retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_relationship_history(
    project_id: str,
    entity1_id: str,
    entity2_id: str,
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Get the relationship history between two entities.

    Returns all timeline events related to the relationship between
    the two specified entities, including additions, removals, and updates.

    - **project_id**: The project identifier
    - **entity1_id**: The first entity identifier
    - **entity2_id**: The second entity identifier
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    # Verify entities exist
    entity1 = neo4j_handler.get_person(project_id, entity1_id)
    if not entity1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity1_id}' not found in project '{project_id}'"
        )

    entity2 = neo4j_handler.get_person(project_id, entity2_id)
    if not entity2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity2_id}' not found in project '{project_id}'"
        )

    try:
        service = _get_timeline_service(neo4j_handler)
        events = service.get_relationship_history(
            project_id=project_id,
            entity1_id=entity1_id,
            entity2_id=entity2_id,
        )

        return RelationshipHistoryResponse(
            events=[_event_to_response(e) for e in events],
            count=len(events),
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            project_id=project_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relationship history: {str(e)}"
        )


@router.get(
    "/entities/{entity_id}/activity",
    response_model=ActivityAnalysisResponse,
    summary="Get entity activity analysis",
    description="Analyze activity for an entity over a specified period.",
    responses={
        200: {"description": "Activity analysis retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_activity(
    project_id: str,
    entity_id: str,
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to analyze"
    ),
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Get activity analysis for an entity.

    Analyzes the entity's activity over the specified period, providing
    statistics on event frequency, types, and patterns.

    - **project_id**: The project identifier
    - **entity_id**: The entity identifier
    - **days**: Number of days to analyze (1-365, default: 30)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    # Verify entity exists
    entity = neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        service = _get_timeline_service(neo4j_handler)
        analysis = service.analyze_activity(
            project_id=project_id,
            entity_id=entity_id,
            days=days,
        )

        return ActivityAnalysisResponse(
            entity_id=entity_id,
            project_id=project_id,
            total_events=analysis.get("total_events", 0),
            events_by_type=analysis.get("events_by_type", {}),
            events_by_day=analysis.get("events_by_day", {}),
            most_active_day=analysis.get("most_active_day"),
            average_events_per_day=analysis.get("average_events_per_day", 0.0),
            first_event=analysis.get("first_event"),
            last_event=analysis.get("last_event"),
            analysis_period_days=analysis.get("analysis_period_days", days),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze entity activity: {str(e)}"
        )


@router.post(
    "/entities/{entity_id}/timeline",
    response_model=RecordEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a timeline event",
    description="Record a new timeline event for an entity.",
    responses={
        201: {"description": "Event recorded successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def record_timeline_event(
    project_id: str,
    entity_id: str,
    event_data: RecordEventRequest,
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Record a new timeline event.

    Creates a new timeline event for the specified entity. This is typically
    called automatically by the system when entities are modified.

    - **project_id**: The project identifier
    - **entity_id**: The entity identifier
    - **event_data**: Event details including type, details, and optional actor
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    # Verify entity exists
    entity = neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        service = _get_timeline_service(neo4j_handler)
        event = service.record_event(
            project_id=project_id,
            entity_id=entity_id,
            event_type=event_data.event_type,
            details=event_data.details,
            actor=event_data.actor,
        )

        return RecordEventResponse(
            success=True,
            event=_event_to_response(event),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record timeline event: {str(e)}"
        )
