"""
Analytics Router v2 for Basset Hound OSINT Platform.

Provides RESTful API endpoints for search analytics including:
- Recording search events
- Analytics summaries (global and per-project)
- Top queries and zero-result queries
- Slow query detection
- Time-based search analysis
- Popular fields tracking
- Query stats and suggestions
- Analytics export and cleanup

All endpoints are under /api/v1/analytics/
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict

from ..services.analytics_service import (
    SearchAnalytics,
    SearchEvent,
    QueryStats,
    AnalyticsSummary,
    TimeRange,
    get_analytics_service,
)


# ----- Request/Response Models -----


class RecordSearchRequest(BaseModel):
    """Request model for recording a search event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "project_id": "project-123",
                "results_count": 5,
                "response_time_ms": 150,
                "fields_searched": ["name", "email"],
                "filters_applied": {"entity_type": "Person"},
                "user_id": "user-456"
            }
        }
    )

    query: str = Field(..., min_length=1, description="The search query string")
    project_id: str = Field(..., min_length=1, description="Project ID")
    results_count: int = Field(0, ge=0, description="Number of results returned")
    response_time_ms: int = Field(0, ge=0, description="Response time in milliseconds")
    fields_searched: List[str] = Field(default_factory=list, description="Fields that were searched")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters applied")
    user_id: Optional[str] = Field(None, description="Optional user ID")


class RecordSearchResponse(BaseModel):
    """Response model for recording a search event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Search event recorded successfully"
            }
        }
    )

    success: bool = Field(..., description="Whether recording succeeded")
    event_id: str = Field(..., description="ID of the created event")
    message: str = Field(..., description="Status message")


class QueryStatsResponse(BaseModel):
    """Response model for query statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "total_searches": 42,
                "avg_results": 5.5,
                "avg_response_time_ms": 120.5,
                "first_searched": "2024-01-01T10:00:00",
                "last_searched": "2024-01-15T15:30:00"
            }
        }
    )

    query: str = Field(..., description="The search query string")
    total_searches: int = Field(..., description="Total number of searches")
    avg_results: float = Field(..., description="Average number of results")
    avg_response_time_ms: float = Field(..., description="Average response time")
    first_searched: Optional[str] = Field(None, description="First search timestamp")
    last_searched: Optional[str] = Field(None, description="Last search timestamp")


class TopQueriesResponse(BaseModel):
    """Response model for top queries list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queries": [],
                "total": 0,
                "project_id": None,
                "time_range": None
            }
        }
    )

    queries: List[QueryStatsResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    project_id: Optional[str] = Field(None)
    time_range: Optional[str] = Field(None)


class SearchEventResponse(BaseModel):
    """Response model for a search event."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "john doe",
                "project_id": "project-123",
                "user_id": None,
                "timestamp": "2024-01-15T10:30:00",
                "results_count": 5,
                "response_time_ms": 150,
                "fields_searched": ["name"],
                "filters_applied": {}
            }
        }
    )

    id: str = Field(...)
    query: str = Field(...)
    project_id: str = Field(...)
    user_id: Optional[str] = Field(None)
    timestamp: str = Field(...)
    results_count: int = Field(...)
    response_time_ms: int = Field(...)
    fields_searched: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class SlowQueriesResponse(BaseModel):
    """Response model for slow queries list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queries": [],
                "total": 0,
                "threshold_ms": 1000
            }
        }
    )

    queries: List[SearchEventResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    threshold_ms: int = Field(1000)


class SearchesByTimeResponse(BaseModel):
    """Response model for searches by time period."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "granularity": "day",
                "data": {"2024-01-15": 50},
                "total": 50
            }
        }
    )

    granularity: str = Field(...)
    data: Dict[str, int] = Field(default_factory=dict)
    total: int = Field(0, ge=0)


class PopularFieldsResponse(BaseModel):
    """Response model for popular fields."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fields": [{"field": "name", "count": 100}],
                "total": 1
            }
        }
    )

    fields: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(0, ge=0)


class RelatedQueriesResponse(BaseModel):
    """Response model for related queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "related": ["john smith", "jane doe"],
                "count": 2
            }
        }
    )

    query: str = Field(...)
    related: List[str] = Field(default_factory=list)
    count: int = Field(0, ge=0)


class SuggestionsResponse(BaseModel):
    """Response model for query suggestions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john",
                "suggestions": ["john doe", "john smith"],
                "count": 2
            }
        }
    )

    query: str = Field(...)
    suggestions: List[str] = Field(default_factory=list)
    count: int = Field(0, ge=0)


class ClearAnalyticsResponse(BaseModel):
    """Response model for clear analytics operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "events_cleared": 100,
                "message": "Analytics cleared successfully"
            }
        }
    )

    success: bool = Field(...)
    events_cleared: int = Field(0, ge=0)
    message: str = Field(...)


class AnalyticsSummaryResponse(BaseModel):
    """Response model for analytics summary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_searches": 1000,
                "unique_queries": 150,
                "avg_response_time": 125.5,
                "top_queries": [],
                "searches_by_day": {},
                "searches_by_hour": {},
                "zero_result_queries": []
            }
        }
    )

    total_searches: int = Field(0, ge=0)
    unique_queries: int = Field(0, ge=0)
    avg_response_time: float = Field(0.0, ge=0)
    top_queries: List[QueryStatsResponse] = Field(default_factory=list)
    searches_by_day: Dict[str, int] = Field(default_factory=dict)
    searches_by_hour: Dict[str, int] = Field(default_factory=dict)
    zero_result_queries: List[QueryStatsResponse] = Field(default_factory=list)


# ----- Helper Functions -----


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string, returning None on failure."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_time_range(
    start_date: Optional[str],
    end_date: Optional[str],
    last_days: Optional[int],
    last_hours: Optional[int],
) -> Optional[TimeRange]:
    """Parse time range from various inputs."""
    if last_days is not None:
        return TimeRange.last_days(last_days)
    if last_hours is not None:
        return TimeRange.last_hours(last_hours)

    start = _parse_datetime(start_date)
    end = _parse_datetime(end_date)

    if start or end:
        return TimeRange(start=start, end=end)

    return None


def _query_stats_to_response(stats: QueryStats) -> QueryStatsResponse:
    """Convert QueryStats to response model."""
    return QueryStatsResponse(
        query=stats.query,
        total_searches=stats.total_searches,
        avg_results=round(stats.avg_results, 2),
        avg_response_time_ms=round(stats.avg_response_time_ms, 2),
        first_searched=stats.first_searched.isoformat() if stats.first_searched else None,
        last_searched=stats.last_searched.isoformat() if stats.last_searched else None,
    )


def _search_event_to_response(event: SearchEvent) -> SearchEventResponse:
    """Convert SearchEvent to response model."""
    return SearchEventResponse(
        id=event.id,
        query=event.query,
        project_id=event.project_id,
        user_id=event.user_id,
        timestamp=event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
        results_count=event.results_count,
        response_time_ms=event.response_time_ms,
        fields_searched=event.fields_searched,
        filters_applied=event.filters_applied,
    )


# ----- Dependency -----


def get_analytics() -> SearchAnalytics:
    """Dependency to get the SearchAnalytics instance."""
    return get_analytics_service()


# ----- Router -----


router = APIRouter(
    prefix="/analytics",
    tags=["analytics-v2"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Endpoints -----


@router.post(
    "/search",
    response_model=RecordSearchResponse,
    summary="Record a search event",
    description="Record a new search event for analytics tracking.",
    responses={
        200: {"description": "Event recorded successfully"},
    }
)
async def record_search(
    request: RecordSearchRequest,
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Record a search event.

    - **query**: The search query string (required)
    - **project_id**: Project ID (required)
    - **results_count**: Number of results returned
    - **response_time_ms**: Response time in milliseconds
    - **fields_searched**: Fields that were searched
    - **filters_applied**: Filters applied to the search
    - **user_id**: Optional user ID
    """
    try:
        event = analytics.record_search(
            query=request.query,
            project_id=request.project_id,
            results_count=request.results_count,
            response_time_ms=request.response_time_ms,
            fields=request.fields_searched,
            filters=request.filters_applied,
            user_id=request.user_id,
        )

        return RecordSearchResponse(
            success=True,
            event_id=event.id,
            message="Search event recorded successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record event: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get analytics summary",
    description="Get a comprehensive analytics summary.",
    responses={
        200: {"description": "Summary returned successfully"},
    }
)
async def get_summary(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    last_days: Optional[int] = Query(None, ge=1, description="Last N days"),
    last_hours: Optional[int] = Query(None, ge=1, description="Last N hours"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get a comprehensive analytics summary.

    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **last_days**: Get data from last N days
    - **last_hours**: Get data from last N hours
    """
    try:
        time_range = _parse_time_range(start_date, end_date, last_days, last_hours)
        summary = analytics.get_summary(time_range=time_range)

        return AnalyticsSummaryResponse(
            total_searches=summary.total_searches,
            unique_queries=summary.unique_queries,
            avg_response_time=round(summary.avg_response_time, 2),
            top_queries=[_query_stats_to_response(q) for q in summary.top_queries],
            searches_by_day=summary.searches_by_day,
            searches_by_hour=summary.searches_by_hour,
            zero_result_queries=[_query_stats_to_response(q) for q in summary.zero_result_queries],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get(
    "/top-queries",
    response_model=TopQueriesResponse,
    summary="Get top queries",
    description="Get the most frequently searched queries.",
    responses={
        200: {"description": "Top queries returned successfully"},
    }
)
async def get_top_queries(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    last_days: Optional[int] = Query(None, ge=1, description="Last N days"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get the most frequently searched queries.

    - **project_id**: Optional project ID filter
    - **limit**: Maximum number of queries (1-100)
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **last_days**: Get data from last N days
    """
    try:
        time_range = _parse_time_range(start_date, end_date, last_days, None)
        top = analytics.get_top_queries(
            project_id=project_id,
            limit=limit,
            time_range=time_range,
        )

        return TopQueriesResponse(
            queries=[_query_stats_to_response(q) for q in top],
            total=len(top),
            project_id=project_id,
            time_range=f"last_{last_days}_days" if last_days else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top queries: {str(e)}"
        )


@router.get(
    "/zero-results",
    response_model=TopQueriesResponse,
    summary="Get zero-result queries",
    description="Get queries that returned no results.",
    responses={
        200: {"description": "Zero-result queries returned successfully"},
    }
)
async def get_zero_result_queries(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get queries that returned no results.

    - **project_id**: Optional project ID filter
    - **limit**: Maximum number of queries (1-100)
    """
    try:
        zero_results = analytics.get_zero_result_queries(
            project_id=project_id,
            limit=limit,
        )

        return TopQueriesResponse(
            queries=[_query_stats_to_response(q) for q in zero_results],
            total=len(zero_results),
            project_id=project_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get zero-result queries: {str(e)}"
        )


@router.get(
    "/slow-queries",
    response_model=SlowQueriesResponse,
    summary="Get slow queries",
    description="Get queries that exceeded the response time threshold.",
    responses={
        200: {"description": "Slow queries returned successfully"},
    }
)
async def get_slow_queries(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    threshold_ms: int = Query(1000, ge=1, description="Response time threshold in ms"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get queries that exceeded the response time threshold.

    - **project_id**: Optional project ID filter
    - **threshold_ms**: Response time threshold in milliseconds
    - **limit**: Maximum number of queries (1-100)
    """
    try:
        slow = analytics.get_slow_queries(
            project_id=project_id,
            threshold_ms=threshold_ms,
            limit=limit,
        )

        return SlowQueriesResponse(
            queries=[_search_event_to_response(e) for e in slow],
            total=len(slow),
            threshold_ms=threshold_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get slow queries: {str(e)}"
        )


@router.get(
    "/by-time",
    response_model=SearchesByTimeResponse,
    summary="Get searches by time period",
    description="Get search counts aggregated by time period.",
    responses={
        200: {"description": "Data returned successfully"},
    }
)
async def get_searches_by_time(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    granularity: str = Query("day", description="Time granularity: hour, day, or week"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    last_days: Optional[int] = Query(None, ge=1, description="Last N days"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get search counts aggregated by time period.

    - **project_id**: Optional project ID filter
    - **granularity**: Time granularity (hour, day, week)
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **last_days**: Get data from last N days
    """
    if granularity not in ("hour", "day", "week"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Granularity must be 'hour', 'day', or 'week'"
        )

    try:
        time_range = _parse_time_range(start_date, end_date, last_days, None)
        data = analytics.get_searches_by_timeframe(
            project_id=project_id,
            granularity=granularity,
            time_range=time_range,
        )

        return SearchesByTimeResponse(
            granularity=granularity,
            data=data,
            total=sum(data.values()),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get searches by time: {str(e)}"
        )


@router.get(
    "/popular-fields",
    response_model=PopularFieldsResponse,
    summary="Get most searched fields",
    description="Get the most frequently searched fields.",
    responses={
        200: {"description": "Popular fields returned successfully"},
    }
)
async def get_popular_fields(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of fields"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get the most frequently searched fields.

    - **project_id**: Optional project ID filter
    - **limit**: Maximum number of fields (1-100)
    """
    try:
        fields = analytics.get_popular_fields(
            project_id=project_id,
            limit=limit,
        )

        return PopularFieldsResponse(
            fields=[{"field": f, "count": c} for f, c in fields],
            total=len(fields),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular fields: {str(e)}"
        )


@router.get(
    "/query/{query}/stats",
    response_model=QueryStatsResponse,
    summary="Get stats for specific query",
    description="Get aggregated statistics for a specific query.",
    responses={
        200: {"description": "Query stats returned successfully"},
        404: {"description": "Query not found"},
    }
)
async def get_query_stats(
    query: str = Path(..., description="The query to get stats for"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get aggregated statistics for a specific query.

    - **query**: The query string to get stats for
    """
    try:
        stats = analytics.get_query_stats(query)

        if stats is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No searches found for query '{query}'"
            )

        return _query_stats_to_response(stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query stats: {str(e)}"
        )


@router.get(
    "/query/{query}/related",
    response_model=RelatedQueriesResponse,
    summary="Get related queries",
    description="Get queries that are similar to the given query.",
    responses={
        200: {"description": "Related queries returned successfully"},
    }
)
async def get_related_queries(
    query: str = Path(..., description="The query to find related queries for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of related queries"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get queries that are similar to the given query.

    - **query**: The query to find related queries for
    - **limit**: Maximum number of related queries (1-20)
    """
    try:
        related = analytics.get_related_queries(query, limit=limit)

        return RelatedQueriesResponse(
            query=query.strip().lower(),
            related=related,
            count=len(related),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related queries: {str(e)}"
        )


@router.get(
    "/query/{query}/suggestions",
    response_model=SuggestionsResponse,
    summary="Get improvement suggestions",
    description="Get improved query suggestions based on successful similar queries.",
    responses={
        200: {"description": "Suggestions returned successfully"},
    }
)
async def get_query_suggestions(
    query: str = Path(..., description="The query to get suggestions for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get improved query suggestions based on successful similar queries.

    - **query**: The query to get suggestions for
    - **limit**: Maximum number of suggestions (1-20)
    """
    try:
        suggestions = analytics.suggest_query_improvements(query, limit=limit)

        return SuggestionsResponse(
            query=query.strip().lower(),
            suggestions=suggestions,
            count=len(suggestions),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.delete(
    "",
    response_model=ClearAnalyticsResponse,
    summary="Clear analytics data",
    description="Clear analytics data (admin operation).",
    responses={
        200: {"description": "Analytics cleared successfully"},
    }
)
async def clear_analytics(
    project_id: Optional[str] = Query(None, description="Clear only this project's data"),
    before_date: Optional[str] = Query(None, description="Clear data before this date (ISO format)"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Clear analytics data.

    - **project_id**: Optional project ID to clear data for
    - **before_date**: Optional date before which to clear data
    """
    try:
        before = _parse_datetime(before_date)
        cleared = analytics.clear_analytics(
            project_id=project_id,
            before_date=before,
        )

        return ClearAnalyticsResponse(
            success=True,
            events_cleared=cleared,
            message=f"Cleared {cleared} analytics events",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear analytics: {str(e)}"
        )


@router.get(
    "/export",
    summary="Export analytics data",
    description="Export analytics data in JSON or CSV format.",
    responses={
        200: {"description": "Export successful"},
    }
)
async def export_analytics(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    format: str = Query("json", description="Export format: json or csv"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Export analytics data.

    - **project_id**: Optional project ID filter
    - **format**: Export format (json or csv)
    """
    if format.lower() not in ("json", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'json' or 'csv'"
        )

    try:
        data = analytics.export_analytics(
            project_id=project_id,
            format=format.lower(),
        )

        if format.lower() == "csv":
            return PlainTextResponse(
                content=data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=analytics.csv"}
            )
        else:
            return PlainTextResponse(
                content=data,
                media_type="application/json",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export analytics: {str(e)}"
        )


# ----- Project-specific Analytics -----


project_router = APIRouter(
    prefix="/projects/{project_id}/analytics",
    tags=["analytics-v2"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


@project_router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get project-specific analytics summary",
    description="Get analytics summary for a specific project.",
    responses={
        200: {"description": "Summary returned successfully"},
    }
)
async def get_project_summary(
    project_id: str = Path(..., description="Project ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    last_days: Optional[int] = Query(None, ge=1, description="Last N days"),
    analytics: SearchAnalytics = Depends(get_analytics),
):
    """
    Get analytics summary for a specific project.

    - **project_id**: Project ID
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **last_days**: Get data from last N days
    """
    try:
        time_range = _parse_time_range(start_date, end_date, last_days, None)
        summary = analytics.get_summary(
            project_id=project_id,
            time_range=time_range,
        )

        return AnalyticsSummaryResponse(
            total_searches=summary.total_searches,
            unique_queries=summary.unique_queries,
            avg_response_time=round(summary.avg_response_time, 2),
            top_queries=[_query_stats_to_response(q) for q in summary.top_queries],
            searches_by_day=summary.searches_by_day,
            searches_by_hour=summary.searches_by_hour,
            zero_result_queries=[_query_stats_to_response(q) for q in summary.zero_result_queries],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project summary: {str(e)}"
        )
