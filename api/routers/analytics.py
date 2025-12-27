"""
Search Analytics Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for search analytics including:
- Popular queries tracking
- Zero-result query detection
- Search volume metrics
- Click-through rate analysis
- Query suggestions
- Search trends over time
- Project-specific analytics

Endpoints:
- GET /api/v1/analytics/search/popular - Popular queries
- GET /api/v1/analytics/search/zero-results - Zero result queries
- GET /api/v1/analytics/search/volume - Search volume stats
- GET /api/v1/analytics/search/ctr - Click-through rate
- GET /api/v1/analytics/search/suggestions - Query suggestions
- GET /api/v1/analytics/search/trends - Query trends
- GET /api/v1/analytics/search/export - Export analytics data
- GET /api/v1/projects/{project}/analytics/search - Project-specific analytics
- POST /api/v1/analytics/search/cleanup - Trigger cleanup
- POST /api/v1/analytics/search/event - Record a search event
- POST /api/v1/analytics/search/click - Record a result click
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..services.search_analytics import (
    SearchAnalytics,
    SearchEvent,
    PopularQuery,
    get_search_analytics,
)


# ----- Pydantic Models -----


class PopularQueryResponse(BaseModel):
    """Response model for a popular query."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "count": 42,
                "avg_results": 5.5,
                "last_searched": "2024-01-15T10:30:00"
            }
        }
    )

    query: str = Field(..., description="The search query string")
    count: int = Field(..., ge=0, description="Number of times this query was searched")
    avg_results: float = Field(..., ge=0, description="Average number of results returned")
    last_searched: str = Field(..., description="Timestamp of most recent search")


class PopularQueriesResponse(BaseModel):
    """Response model for list of popular queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queries": [
                    {"query": "john doe", "count": 42, "avg_results": 5.5, "last_searched": "2024-01-15T10:30:00"}
                ],
                "total": 1
            }
        }
    )

    queries: List[PopularQueryResponse] = Field(default_factory=list, description="List of popular queries")
    total: int = Field(0, ge=0, description="Total number of queries returned")


class SearchVolumeResponse(BaseModel):
    """Response model for search volume data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "granularity": "day",
                "volume": {
                    "2024-01-14": 15,
                    "2024-01-15": 23
                },
                "total_searches": 38
            }
        }
    )

    granularity: str = Field(..., description="Time granularity (hour, day, week)")
    volume: Dict[str, int] = Field(default_factory=dict, description="Search counts by time period")
    total_searches: int = Field(0, ge=0, description="Total number of searches")


class CTRResponse(BaseModel):
    """Response model for click-through rate."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "click_through_rate": 0.35,
                "searches_with_clicks": 35,
                "total_searches": 100
            }
        }
    )

    click_through_rate: float = Field(..., ge=0, le=1, description="CTR as decimal (0-1)")
    searches_with_clicks: int = Field(0, ge=0, description="Number of searches with at least one click")
    total_searches: int = Field(0, ge=0, description="Total number of searches")


class QuerySuggestionsResponse(BaseModel):
    """Response model for query suggestions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prefix": "joh",
                "suggestions": ["john doe", "john smith", "johnny"],
                "count": 3
            }
        }
    )

    prefix: str = Field(..., description="The prefix used for suggestions")
    suggestions: List[str] = Field(default_factory=list, description="Suggested query completions")
    count: int = Field(0, ge=0, description="Number of suggestions returned")


class SearchTrendsResponse(BaseModel):
    """Response model for search trends."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "granularity": "day",
                "trends": {
                    "2024-01-14": 5,
                    "2024-01-15": 8
                },
                "total_for_query": 13
            }
        }
    )

    query: str = Field(..., description="The query being analyzed")
    granularity: str = Field(..., description="Time granularity (hour, day, week)")
    trends: Dict[str, int] = Field(default_factory=dict, description="Search counts by time period")
    total_for_query: int = Field(0, ge=0, description="Total searches for this query")


class ProjectAnalyticsResponse(BaseModel):
    """Response model for project-specific analytics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "total_searches": 150,
                "unique_queries": 45,
                "avg_results_per_query": 3.5,
                "click_through_rate": 0.28,
                "popular_queries": [],
                "zero_result_queries": []
            }
        }
    )

    project_id: str = Field(..., description="Project identifier")
    total_searches: int = Field(0, ge=0, description="Total searches in project")
    unique_queries: int = Field(0, ge=0, description="Number of unique queries")
    avg_results_per_query: float = Field(0, ge=0, description="Average results per search")
    click_through_rate: float = Field(0, ge=0, le=1, description="CTR for project")
    popular_queries: List[PopularQueryResponse] = Field(default_factory=list, description="Top popular queries")
    zero_result_queries: List[PopularQueryResponse] = Field(default_factory=list, description="Top zero-result queries")


class CleanupResponse(BaseModel):
    """Response model for cleanup operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "events_removed": 150,
                "events_remaining": 350,
                "message": "Cleanup completed successfully"
            }
        }
    )

    success: bool = Field(..., description="Whether cleanup succeeded")
    events_removed: int = Field(0, ge=0, description="Number of events removed")
    events_remaining: int = Field(0, ge=0, description="Number of events remaining")
    message: str = Field(..., description="Status message")


class RecordSearchRequest(BaseModel):
    """Request model for recording a search event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "result_count": 5,
                "duration_ms": 150,
                "project_id": "project-123",
                "entity_types": ["Person"],
                "filters_used": {"field": "email"}
            }
        }
    )

    query: str = Field(..., min_length=1, description="The search query string")
    result_count: int = Field(0, ge=0, description="Number of results returned")
    duration_ms: int = Field(0, ge=0, description="Search duration in milliseconds")
    project_id: Optional[str] = Field(None, description="Optional project ID")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    entity_types: List[str] = Field(default_factory=list, description="Entity types searched")
    filters_used: Dict[str, Any] = Field(default_factory=dict, description="Filters applied")


class RecordSearchResponse(BaseModel):
    """Response model for recording a search event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Search event recorded"
            }
        }
    )

    success: bool = Field(..., description="Whether recording succeeded")
    event_id: str = Field(..., description="ID of the created event")
    message: str = Field(..., description="Status message")


class RecordClickRequest(BaseModel):
    """Request model for recording a click on a search result."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_id": "entity-123"
            }
        }
    )

    event_id: str = Field(..., description="ID of the search event")
    entity_id: str = Field(..., description="ID of the clicked entity")


class RecordClickResponse(BaseModel):
    """Response model for recording a click."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Click recorded"
            }
        }
    )

    success: bool = Field(..., description="Whether recording succeeded")
    message: str = Field(..., description="Status message")


class ExportAnalyticsResponse(BaseModel):
    """Response model for exporting analytics data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "generated_at": "2024-01-15T10:30:00",
                "filters": {},
                "summary": {},
                "popular_queries": [],
                "zero_result_queries": [],
                "volume_by_day": {}
            }
        }
    )

    generated_at: str = Field(..., description="When the export was generated")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters applied")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Analytics summary")
    popular_queries: List[Dict[str, Any]] = Field(default_factory=list, description="Popular queries")
    zero_result_queries: List[Dict[str, Any]] = Field(default_factory=list, description="Zero-result queries")
    volume_by_day: Dict[str, int] = Field(default_factory=dict, description="Volume by day")
    events: Optional[List[Dict[str, Any]]] = Field(None, description="Raw events if requested")


# ----- Dependency -----


def get_analytics_service() -> SearchAnalytics:
    """
    Dependency to get the SearchAnalytics instance.

    Returns the singleton SearchAnalytics service.
    """
    return get_search_analytics()


# ----- Helper Functions -----


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string, returning None on failure."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _popular_query_to_response(pq: PopularQuery) -> PopularQueryResponse:
    """Convert PopularQuery to response model."""
    return PopularQueryResponse(
        query=pq.query,
        count=pq.count,
        avg_results=pq.avg_results,
        last_searched=pq.last_searched.isoformat() if isinstance(pq.last_searched, datetime) else str(pq.last_searched),
    )


# ----- Routers -----


router = APIRouter(
    prefix="/analytics/search",
    tags=["analytics"],
    responses={
        500: {"description": "Internal server error"},
    },
)

project_analytics_router = APIRouter(
    prefix="/projects/{project_id}/analytics/search",
    tags=["analytics"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Analytics Endpoints -----


@router.get(
    "/popular",
    response_model=PopularQueriesResponse,
    summary="Get popular search queries",
    description="Returns the most frequently searched queries, sorted by search count.",
    responses={
        200: {"description": "Popular queries returned successfully"},
    }
)
async def get_popular_queries(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries to return"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get the most popular search queries.

    - **limit**: Maximum number of queries (1-100, default 10)
    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    try:
        popular = analytics.get_popular_queries(
            limit=limit,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
        )

        return PopularQueriesResponse(
            queries=[_popular_query_to_response(pq) for pq in popular],
            total=len(popular),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular queries: {str(e)}"
        )


@router.get(
    "/zero-results",
    response_model=PopularQueriesResponse,
    summary="Get zero-result queries",
    description="Returns queries that returned no results, useful for improving search quality.",
    responses={
        200: {"description": "Zero-result queries returned successfully"},
    }
)
async def get_zero_result_queries(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries to return"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get queries that returned zero results.

    - **limit**: Maximum number of queries (1-100, default 10)
    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    try:
        zero_results = analytics.get_zero_result_queries(
            limit=limit,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
        )

        return PopularQueriesResponse(
            queries=[_popular_query_to_response(pq) for pq in zero_results],
            total=len(zero_results),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get zero-result queries: {str(e)}"
        )


@router.get(
    "/volume",
    response_model=SearchVolumeResponse,
    summary="Get search volume",
    description="Returns search counts aggregated by time period (hour, day, or week).",
    responses={
        200: {"description": "Search volume returned successfully"},
    }
)
async def get_search_volume(
    granularity: str = Query("day", description="Time granularity: hour, day, or week"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get search volume aggregated by time period.

    - **granularity**: Time granularity - "hour", "day", or "week" (default "day")
    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    if granularity not in ("hour", "day", "week"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granularity must be 'hour', 'day', or 'week'"
        )

    try:
        volume = analytics.get_search_volume(
            granularity=granularity,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
        )

        return SearchVolumeResponse(
            granularity=granularity,
            volume=volume,
            total_searches=sum(volume.values()),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search volume: {str(e)}"
        )


@router.get(
    "/ctr",
    response_model=CTRResponse,
    summary="Get click-through rate",
    description="Returns the ratio of searches that resulted in at least one click.",
    responses={
        200: {"description": "CTR returned successfully"},
    }
)
async def get_click_through_rate(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get the click-through rate for searches.

    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    try:
        start = _parse_datetime(start_date)
        end = _parse_datetime(end_date)

        ctr = analytics.get_click_through_rate(
            start_date=start,
            end_date=end,
        )

        # Get additional stats for context
        export = analytics.export_analytics(
            start_date=start,
            end_date=end,
        )
        total_searches = export["summary"]["total_searches"]
        searches_with_clicks = int(ctr * total_searches) if total_searches > 0 else 0

        return CTRResponse(
            click_through_rate=ctr,
            searches_with_clicks=searches_with_clicks,
            total_searches=total_searches,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get CTR: {str(e)}"
        )


@router.get(
    "/suggestions",
    response_model=QuerySuggestionsResponse,
    summary="Get query suggestions",
    description="Returns query suggestions based on search history matching the given prefix.",
    responses={
        200: {"description": "Suggestions returned successfully"},
    }
)
async def get_query_suggestions(
    prefix: str = Query(..., min_length=1, description="Query prefix to match"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get query suggestions based on search history.

    - **prefix**: Query prefix to match (required)
    - **limit**: Maximum number of suggestions (1-20, default 5)
    """
    try:
        suggestions = analytics.get_query_suggestions(
            prefix=prefix,
            limit=limit,
        )

        return QuerySuggestionsResponse(
            prefix=prefix,
            suggestions=suggestions,
            count=len(suggestions),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get(
    "/trends",
    response_model=SearchTrendsResponse,
    summary="Get search trends",
    description="Returns search volume trends for a specific query over time.",
    responses={
        200: {"description": "Trends returned successfully"},
    }
)
async def get_search_trends(
    query: str = Query(..., min_length=1, description="Query to analyze"),
    granularity: str = Query("day", description="Time granularity: hour, day, or week"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Get search trends for a specific query.

    - **query**: The query to analyze (required)
    - **granularity**: Time granularity - "hour", "day", or "week" (default "day")
    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    if granularity not in ("hour", "day", "week"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granularity must be 'hour', 'day', or 'week'"
        )

    try:
        trends = analytics.get_search_trends(
            query=query,
            granularity=granularity,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
        )

        return SearchTrendsResponse(
            query=query.strip().lower(),
            granularity=granularity,
            trends=trends,
            total_for_query=sum(trends.values()),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trends: {str(e)}"
        )


@router.get(
    "/export",
    response_model=ExportAnalyticsResponse,
    summary="Export analytics data",
    description="Export complete analytics data as JSON.",
    responses={
        200: {"description": "Export successful"},
    }
)
async def export_analytics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    include_events: bool = Query(False, description="Include raw event data"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Export analytics data as JSON.

    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    - **include_events**: Whether to include raw event data (default false)
    """
    try:
        export = analytics.export_analytics(
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
            include_events=include_events,
        )

        return ExportAnalyticsResponse(**export)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export analytics: {str(e)}"
        )


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    summary="Cleanup old events",
    description="Remove search events older than the retention period.",
    responses={
        200: {"description": "Cleanup completed successfully"},
    }
)
async def cleanup_old_events(
    older_than_days: Optional[int] = Query(None, ge=1, description="Custom retention period in days"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Cleanup old search events.

    - **older_than_days**: Custom retention period (uses service default if not specified)
    """
    try:
        count_before = analytics.get_event_count()
        removed = analytics.cleanup_old_events(older_than_days)
        count_after = analytics.get_event_count()

        return CleanupResponse(
            success=True,
            events_removed=removed,
            events_remaining=count_after,
            message=f"Cleanup completed successfully. Removed {removed} events.",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.post(
    "/event",
    response_model=RecordSearchResponse,
    summary="Record a search event",
    description="Record a new search event for analytics tracking.",
    responses={
        200: {"description": "Event recorded successfully"},
    }
)
async def record_search_event(
    request: RecordSearchRequest,
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Record a search event.

    - **query**: The search query string (required)
    - **result_count**: Number of results returned
    - **duration_ms**: Search duration in milliseconds
    - **project_id**: Optional project ID
    - **user_id**: Optional user ID
    - **entity_types**: Entity types searched
    - **filters_used**: Filters applied
    """
    try:
        event = analytics.record_search(
            query=request.query,
            result_count=request.result_count,
            duration_ms=request.duration_ms,
            project_id=request.project_id,
            user_id=request.user_id,
            entity_types=request.entity_types,
            filters_used=request.filters_used,
        )

        return RecordSearchResponse(
            success=True,
            event_id=event.id,
            message="Search event recorded",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record event: {str(e)}"
        )


@router.post(
    "/click",
    response_model=RecordClickResponse,
    summary="Record a result click",
    description="Record a click on a search result for CTR tracking.",
    responses={
        200: {"description": "Click recorded successfully"},
        404: {"description": "Search event not found"},
    }
)
async def record_click(
    request: RecordClickRequest,
    analytics: SearchAnalytics = Depends(get_analytics_service),
):
    """
    Record a click on a search result.

    - **event_id**: ID of the search event
    - **entity_id**: ID of the clicked entity
    """
    try:
        success = analytics.record_click(
            event_id=request.event_id,
            entity_id=request.entity_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Search event '{request.event_id}' not found"
            )

        return RecordClickResponse(
            success=True,
            message="Click recorded",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record click: {str(e)}"
        )


# ----- Project-Specific Analytics -----


@project_analytics_router.get(
    "",
    response_model=ProjectAnalyticsResponse,
    summary="Get project-specific analytics",
    description="Returns comprehensive search analytics for a specific project.",
    responses={
        200: {"description": "Analytics returned successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_project_analytics(
    project_id: str,
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics_service),
    neo4j_handler=Depends(get_neo4j_handler),
):
    """
    Get comprehensive analytics for a specific project.

    - **project_id**: Project ID or safe_name
    - **start_date**: Optional start date for filtering
    - **end_date**: Optional end date for filtering
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        all_projects = neo4j_handler.get_all_projects()
        project = next(
            (p for p in all_projects if p.get("id") == project_id),
            None
        )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    try:
        start = _parse_datetime(start_date)
        end = _parse_datetime(end_date)

        # Get project-specific analytics
        export = analytics.export_analytics(
            project_id=project_id,
            start_date=start,
            end_date=end,
        )

        popular = analytics.get_popular_queries(
            limit=5,
            project_id=project_id,
            start_date=start,
            end_date=end,
        )

        zero_results = analytics.get_zero_result_queries(
            limit=5,
            project_id=project_id,
            start_date=start,
            end_date=end,
        )

        return ProjectAnalyticsResponse(
            project_id=project_id,
            total_searches=export["summary"]["total_searches"],
            unique_queries=export["summary"]["unique_queries"],
            avg_results_per_query=export["summary"]["avg_results_per_query"],
            click_through_rate=export["summary"]["click_through_rate"],
            popular_queries=[_popular_query_to_response(pq) for pq in popular],
            zero_result_queries=[_popular_query_to_response(pq) for pq in zero_results],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project analytics: {str(e)}"
        )
