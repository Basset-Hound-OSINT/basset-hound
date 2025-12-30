"""
Saved Search Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for managing and executing saved searches.

Endpoints:
- POST /api/v1/saved-searches - Create a new saved search
- GET /api/v1/saved-searches - List saved searches
- GET /api/v1/saved-searches/{search_id} - Get a specific saved search
- PUT /api/v1/saved-searches/{search_id} - Update a saved search
- DELETE /api/v1/saved-searches/{search_id} - Delete a saved search
- POST /api/v1/saved-searches/{search_id}/execute - Execute a saved search
- POST /api/v1/saved-searches/{search_id}/duplicate - Duplicate a saved search
- POST /api/v1/saved-searches/{search_id}/toggle-favorite - Toggle favorite status
- GET /api/v1/saved-searches/favorites - Get favorite searches
- GET /api/v1/saved-searches/recent - Get recently executed searches
- GET /api/v1/saved-searches/popular - Get most popular searches
- GET /api/v1/saved-searches/tags - Get all tags with counts
- GET /api/v1/saved-searches/by-category/{category} - Get searches by category
- GET /api/v1/saved-searches/by-tag/{tag} - Get searches by tag
- GET /api/v1/projects/{project_id}/saved-searches - Project-scoped saved searches
"""

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler, get_app_config
from ..services.search_service import (
    SearchService,
    SearchResult,
    get_search_service,
)
from ..services.saved_search import (
    SavedSearchService,
    SavedSearchConfig,
    SavedSearch,
    SearchScope,
    SearchCategory,
    SearchListFilter,
    SearchExecutionResult,
    get_saved_search_service,
)


# ----- Pydantic Models -----

class CreateSavedSearchRequest(BaseModel):
    """Request model for creating a saved search."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "High-Risk Entities",
                "description": "Find entities with risk indicators",
                "query": "tag:high-risk OR tag:suspicious",
                "scope": "project",
                "project_id": "project-123",
                "is_advanced": True,
                "entity_types": ["Person"],
                "fields": ["core.name", "core.email"],
                "limit": 50,
                "fuzzy": True,
                "highlight": True,
                "tags": ["risk", "monitoring"],
                "category": "risk",
                "is_favorite": False,
                "icon": "alert",
                "color": "#ff5722"
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    description: str = Field("", max_length=500, description="Optional description")
    scope: str = Field("project", description="Scope: global, project, or user")
    project_id: Optional[str] = Field(None, description="Project ID for project-scoped")
    user_id: Optional[str] = Field(None, description="User ID for user-scoped")
    is_advanced: bool = Field(False, description="Use advanced boolean parsing")
    entity_types: Optional[List[str]] = Field(None, description="Entity type filter")
    fields: Optional[List[str]] = Field(None, description="Fields to search")
    limit: int = Field(20, ge=1, le=100, description="Default result limit")
    fuzzy: bool = Field(True, description="Enable fuzzy matching")
    highlight: bool = Field(True, description="Generate highlights")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    category: str = Field("general", description="Category for organization")
    is_favorite: bool = Field(False, description="Mark as favorite")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="Color for UI display")


class UpdateSavedSearchRequest(BaseModel):
    """Request model for updating a saved search."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Search Name",
                "description": "Updated description",
                "query": "tag:updated-query",
                "tags": ["updated", "tags"]
            }
        }
    )

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    query: Optional[str] = Field(None, min_length=1, max_length=1000)
    description: Optional[str] = Field(None, max_length=500)
    scope: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)
    user_id: Optional[str] = Field(None)
    is_advanced: Optional[bool] = Field(None)
    entity_types: Optional[List[str]] = Field(None)
    fields: Optional[List[str]] = Field(None)
    limit: Optional[int] = Field(None, ge=1, le=100)
    fuzzy: Optional[bool] = Field(None)
    highlight: Optional[bool] = Field(None)
    tags: Optional[List[str]] = Field(None)
    category: Optional[str] = Field(None)
    is_favorite: Optional[bool] = Field(None)
    icon: Optional[str] = Field(None)
    color: Optional[str] = Field(None)


class ExecuteSearchRequest(BaseModel):
    """Request model for executing a saved search with overrides."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "override:query",
                "project_id": "different-project",
                "limit": 10,
                "offset": 0
            }
        }
    )

    query: Optional[str] = Field(None, description="Override the saved query")
    project_id: Optional[str] = Field(None, description="Override the project")
    entity_types: Optional[List[str]] = Field(None, description="Override entity types")
    fields: Optional[List[str]] = Field(None, description="Override fields")
    limit: Optional[int] = Field(None, ge=1, le=100, description="Override limit")
    offset: int = Field(0, ge=0, description="Pagination offset")
    fuzzy: Optional[bool] = Field(None, description="Override fuzzy setting")
    highlight: Optional[bool] = Field(None, description="Override highlight setting")


class DuplicateSearchRequest(BaseModel):
    """Request model for duplicating a saved search."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_name": "Copy of High-Risk Entities"
            }
        }
    )

    new_name: Optional[str] = Field(None, min_length=1, max_length=100)


class SavedSearchResponse(BaseModel):
    """Response model for a saved search."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "High-Risk Entities",
                "description": "Find entities with risk indicators",
                "query": "tag:high-risk OR tag:suspicious",
                "scope": "project",
                "project_id": "project-123",
                "is_advanced": True,
                "entity_types": ["Person"],
                "fields": ["core.name", "core.email"],
                "limit": 50,
                "fuzzy": True,
                "highlight": True,
                "tags": ["risk", "monitoring"],
                "category": "risk",
                "is_favorite": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "last_executed_at": "2024-01-15T11:00:00Z",
                "execution_count": 5
            }
        }
    )

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description")
    query: str = Field(..., description="Search query")
    scope: str = Field(..., description="Scope: global, project, or user")
    project_id: Optional[str] = Field(None, description="Project ID")
    user_id: Optional[str] = Field(None, description="User ID")
    is_advanced: bool = Field(..., description="Uses advanced boolean parsing")
    entity_types: Optional[List[str]] = Field(None, description="Entity type filter")
    fields: Optional[List[str]] = Field(None, description="Fields to search")
    limit: int = Field(..., description="Default result limit")
    fuzzy: bool = Field(..., description="Fuzzy matching enabled")
    highlight: bool = Field(..., description="Highlights enabled")
    tags: List[str] = Field(..., description="Organization tags")
    category: str = Field(..., description="Category")
    is_favorite: bool = Field(..., description="Is favorite")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="UI color")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_executed_at: Optional[str] = Field(None, description="Last execution time")
    execution_count: int = Field(..., description="Execution count")
    created_by: Optional[str] = Field(None, description="Creator user ID")


class SavedSearchListResponse(BaseModel):
    """Response model for a list of saved searches."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "searches": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "High-Risk Entities",
                        "description": "Find entities with risk indicators",
                        "query": "tag:high-risk",
                        "scope": "project",
                        "category": "risk",
                        "is_favorite": True,
                        "execution_count": 5
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0
            }
        }
    )

    searches: List[SavedSearchResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="Total number of searches")
    limit: int = Field(50, description="Page size")
    offset: int = Field(0, description="Page offset")


class SearchResultItemResponse(BaseModel):
    """Response model for a single search result."""

    entity_id: str = Field(..., description="Entity ID")
    project_id: str = Field(..., description="Project ID")
    entity_type: str = Field(..., description="Entity type")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    highlights: dict[str, list[str]] = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)
    entity_data: dict[str, Any] = Field(default_factory=dict)


class ExecutionResultResponse(BaseModel):
    """Response model for search execution results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search_id": "550e8400-e29b-41d4-a716-446655440000",
                "search_name": "High-Risk Entities",
                "results": [],
                "total_count": 10,
                "execution_time_ms": 45.5,
                "executed_at": "2024-01-15T11:00:00Z",
                "query_used": "tag:high-risk OR tag:suspicious"
            }
        }
    )

    search_id: str = Field(..., description="Saved search ID")
    search_name: str = Field(..., description="Search name")
    results: List[SearchResultItemResponse] = Field(default_factory=list)
    total_count: int = Field(0, ge=0, description="Total matching results")
    execution_time_ms: float = Field(..., description="Execution time in ms")
    executed_at: str = Field(..., description="Execution timestamp")
    query_used: str = Field(..., description="Query that was executed")


class TagCountResponse(BaseModel):
    """Response model for tag counts."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tags": [
                    {"tag": "risk", "count": 5},
                    {"tag": "monitoring", "count": 3},
                    {"tag": "investigation", "count": 2}
                ],
                "total_unique_tags": 3
            }
        }
    )

    tags: List[dict] = Field(default_factory=list, description="Tags with counts")
    total_unique_tags: int = Field(0, ge=0, description="Number of unique tags")


class FavoriteToggleResponse(BaseModel):
    """Response for toggle favorite operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search_id": "550e8400-e29b-41d4-a716-446655440000",
                "is_favorite": True
            }
        }
    )

    search_id: str = Field(..., description="Search ID")
    is_favorite: bool = Field(..., description="New favorite status")


# ----- Helper Functions -----

def saved_search_to_response(search: SavedSearch) -> SavedSearchResponse:
    """Convert SavedSearch to response model."""
    return SavedSearchResponse(
        id=search.id,
        name=search.config.name,
        description=search.config.description,
        query=search.config.query,
        scope=search.config.scope.value,
        project_id=search.config.project_id,
        user_id=search.config.user_id,
        is_advanced=search.config.is_advanced,
        entity_types=search.config.entity_types,
        fields=search.config.fields,
        limit=search.config.limit,
        fuzzy=search.config.fuzzy,
        highlight=search.config.highlight,
        tags=search.config.tags,
        category=search.config.category.value,
        is_favorite=search.config.is_favorite,
        icon=search.config.icon,
        color=search.config.color,
        created_at=search.created_at.isoformat(),
        updated_at=search.updated_at.isoformat(),
        last_executed_at=search.last_executed_at.isoformat() if search.last_executed_at else None,
        execution_count=search.execution_count,
        created_by=search.created_by,
    )


def execution_result_to_response(result: SearchExecutionResult) -> ExecutionResultResponse:
    """Convert SearchExecutionResult to response model."""
    return ExecutionResultResponse(
        search_id=result.search_id,
        search_name=result.search_name,
        results=[
            SearchResultItemResponse(
                entity_id=r.entity_id,
                project_id=r.project_id,
                entity_type=r.entity_type,
                score=r.score,
                highlights=r.highlights,
                matched_fields=r.matched_fields,
                entity_data=r.entity_data,
            )
            for r in result.results
        ],
        total_count=result.total_count,
        execution_time_ms=result.execution_time_ms,
        executed_at=result.executed_at.isoformat(),
        query_used=result.query_used,
    )


# ----- Dependencies -----

def get_saved_search_service_dep(
    neo4j_handler=Depends(get_neo4j_handler),
    config=Depends(get_app_config)
) -> SavedSearchService:
    """Dependency to get SavedSearchService instance."""
    try:
        search_service = get_search_service(neo4j_handler, config)
        return get_saved_search_service(search_service, neo4j_handler)
    except Exception:
        return get_saved_search_service()


# ----- Routers -----

router = APIRouter(
    prefix="/saved-searches",
    tags=["saved-searches"],
    responses={
        500: {"description": "Internal server error"},
    },
)

project_saved_search_router = APIRouter(
    prefix="/projects/{project_id}/saved-searches",
    tags=["saved-searches"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Global Saved Search Endpoints -----

@router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new saved search",
    description="Create a new saved search configuration.",
    responses={
        201: {"description": "Saved search created successfully"},
        400: {"description": "Invalid request data"},
    }
)
async def create_saved_search(
    request: CreateSavedSearchRequest,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """
    Create a new saved search.

    - **name**: Display name for the search
    - **query**: The search query string
    - **scope**: Where this search is available (global, project, user)
    - **project_id**: Required if scope is "project"
    - **is_advanced**: Whether to use advanced boolean query parsing
    """
    try:
        # Validate scope and required fields
        scope = SearchScope(request.scope)
        category = SearchCategory(request.category)

        config = SavedSearchConfig(
            name=request.name,
            description=request.description,
            query=request.query,
            scope=scope,
            project_id=request.project_id,
            user_id=request.user_id,
            is_advanced=request.is_advanced,
            entity_types=request.entity_types,
            fields=request.fields,
            limit=request.limit,
            fuzzy=request.fuzzy,
            highlight=request.highlight,
            tags=request.tags,
            category=category,
            is_favorite=request.is_favorite,
            icon=request.icon,
            color=request.color,
        )

        search_id = await service.create_search(config)
        search = await service.get_search(search_id)

        if not search:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create saved search"
            )

        return saved_search_to_response(search)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "",
    response_model=SavedSearchListResponse,
    summary="List saved searches",
    description="List saved searches with optional filtering.",
    responses={
        200: {"description": "List of saved searches"},
    }
)
async def list_saved_searches(
    scope: Optional[str] = Query(None, description="Filter by scope"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    is_favorite: Optional[bool] = Query(None, description="Filter favorites"),
    name_contains: Optional[str] = Query(None, description="Search in name/description"),
    include_global: bool = Query(True, description="Include global searches"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """
    List saved searches with optional filters.

    - **scope**: Filter by scope (global, project, user)
    - **project_id**: Filter by project
    - **category**: Filter by category
    - **tags**: Comma-separated list of tags to filter by
    - **is_favorite**: Filter favorites only
    - **name_contains**: Search in name and description
    """
    filter_options = SearchListFilter(
        scope=SearchScope(scope) if scope else None,
        project_id=project_id,
        user_id=user_id,
        category=SearchCategory(category) if category else None,
        tags=tags.split(",") if tags else None,
        is_favorite=is_favorite,
        name_contains=name_contains,
        include_global=include_global,
    )

    searches, total = await service.list_searches(filter_options, offset, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/favorites",
    response_model=SavedSearchListResponse,
    summary="Get favorite saved searches",
    description="Get all saved searches marked as favorites.",
)
async def get_favorite_searches(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get favorite saved searches."""
    searches = await service.get_favorites(project_id, user_id, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=limit,
        offset=0,
    )


@router.get(
    "/recent",
    response_model=SavedSearchListResponse,
    summary="Get recently executed searches",
    description="Get saved searches sorted by last execution time.",
)
async def get_recent_searches(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get recently executed saved searches."""
    searches = await service.get_recent(project_id, user_id, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=limit,
        offset=0,
    )


@router.get(
    "/popular",
    response_model=SavedSearchListResponse,
    summary="Get most popular searches",
    description="Get saved searches sorted by execution count.",
)
async def get_popular_searches(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get most frequently executed saved searches."""
    searches = await service.get_popular(project_id, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=limit,
        offset=0,
    )


@router.get(
    "/tags",
    response_model=TagCountResponse,
    summary="Get all tags with counts",
    description="Get all unique tags used in saved searches with usage counts.",
)
async def get_all_tags(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get all unique tags with their usage counts."""
    tag_counts = await service.get_all_tags(project_id)

    return TagCountResponse(
        tags=[{"tag": tag, "count": count} for tag, count in tag_counts],
        total_unique_tags=len(tag_counts),
    )


@router.get(
    "/by-category/{category}",
    response_model=SavedSearchListResponse,
    summary="Get searches by category",
    description="Get all saved searches in a specific category.",
)
async def get_searches_by_category(
    category: str,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get saved searches by category."""
    try:
        cat = SearchCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}"
        )

    searches = await service.get_by_category(cat, project_id)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=100,
        offset=0,
    )


@router.get(
    "/by-tag/{tag}",
    response_model=SavedSearchListResponse,
    summary="Get searches by tag",
    description="Get all saved searches with a specific tag.",
)
async def get_searches_by_tag(
    tag: str,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get saved searches by tag."""
    searches = await service.get_by_tags([tag], project_id)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=100,
        offset=0,
    )


@router.get(
    "/search",
    response_model=SavedSearchListResponse,
    summary="Search saved searches",
    description="Search through saved search names and descriptions.",
)
async def search_saved_searches(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Search through saved search names and descriptions."""
    searches = await service.search_saved_searches(q, project_id, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=len(searches),
        limit=limit,
        offset=0,
    )


@router.get(
    "/{search_id}",
    response_model=SavedSearchResponse,
    summary="Get a saved search",
    description="Get a specific saved search by ID.",
    responses={
        200: {"description": "Saved search found"},
        404: {"description": "Saved search not found"},
    }
)
async def get_saved_search(
    search_id: str,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Get a saved search by ID."""
    search = await service.get_search(search_id)

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search '{search_id}' not found"
        )

    return saved_search_to_response(search)


@router.put(
    "/{search_id}",
    response_model=SavedSearchResponse,
    summary="Update a saved search",
    description="Update an existing saved search.",
    responses={
        200: {"description": "Saved search updated"},
        404: {"description": "Saved search not found"},
    }
)
async def update_saved_search(
    search_id: str,
    request: UpdateSavedSearchRequest,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Update a saved search."""
    # Build updates dict from non-None fields
    updates = {}
    for field_name in request.model_fields:
        value = getattr(request, field_name)
        if value is not None:
            updates[field_name] = value

    search = await service.update_search(search_id, updates)

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search '{search_id}' not found"
        )

    return saved_search_to_response(search)


@router.delete(
    "/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved search",
    description="Delete a saved search by ID.",
    responses={
        204: {"description": "Saved search deleted"},
        404: {"description": "Saved search not found"},
    }
)
async def delete_saved_search(
    search_id: str,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Delete a saved search."""
    deleted = await service.delete_search(search_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search '{search_id}' not found"
        )

    return None


@router.post(
    "/{search_id}/execute",
    response_model=ExecutionResultResponse,
    summary="Execute a saved search",
    description="Execute a saved search with optional parameter overrides.",
    responses={
        200: {"description": "Search executed successfully"},
        404: {"description": "Saved search not found"},
    }
)
async def execute_saved_search(
    search_id: str,
    request: Optional[ExecuteSearchRequest] = None,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """
    Execute a saved search.

    Optionally override search parameters for this execution only.
    """
    # Build overrides dict
    overrides = {}
    if request:
        for field_name in request.model_fields:
            value = getattr(request, field_name)
            if value is not None:
                overrides[field_name] = value

    try:
        result = await service.execute_search(search_id, overrides or None)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved search '{search_id}' not found"
            )

        return execution_result_to_response(result)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{search_id}/duplicate",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a saved search",
    description="Create a copy of an existing saved search.",
    responses={
        201: {"description": "Duplicate created successfully"},
        404: {"description": "Original saved search not found"},
    }
)
async def duplicate_saved_search(
    search_id: str,
    request: Optional[DuplicateSearchRequest] = None,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Create a duplicate of a saved search."""
    new_name = request.new_name if request else None
    new_id = await service.duplicate_search(search_id, new_name)

    if not new_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search '{search_id}' not found"
        )

    new_search = await service.get_search(new_id)
    return saved_search_to_response(new_search)


@router.post(
    "/{search_id}/toggle-favorite",
    response_model=FavoriteToggleResponse,
    summary="Toggle favorite status",
    description="Toggle the favorite status of a saved search.",
    responses={
        200: {"description": "Favorite status toggled"},
        404: {"description": "Saved search not found"},
    }
)
async def toggle_favorite(
    search_id: str,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
):
    """Toggle the favorite status of a saved search."""
    new_status = await service.toggle_favorite(search_id)

    if new_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search '{search_id}' not found"
        )

    return FavoriteToggleResponse(
        search_id=search_id,
        is_favorite=new_status,
    )


# ----- Project-Scoped Endpoints -----

@project_saved_search_router.get(
    "",
    response_model=SavedSearchListResponse,
    summary="List project saved searches",
    description="List saved searches for a specific project.",
)
async def list_project_saved_searches(
    project_id: str,
    include_global: bool = Query(True, description="Include global searches"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    is_favorite: Optional[bool] = Query(None, description="Filter favorites"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: SavedSearchService = Depends(get_saved_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler),
):
    """List saved searches for a project."""
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

    filter_options = SearchListFilter(
        project_id=project_id,
        category=SearchCategory(category) if category else None,
        tags=tags.split(",") if tags else None,
        is_favorite=is_favorite,
        include_global=include_global,
    )

    searches, total = await service.list_searches(filter_options, offset, limit)

    return SavedSearchListResponse(
        searches=[saved_search_to_response(s) for s in searches],
        total=total,
        limit=limit,
        offset=offset,
    )


@project_saved_search_router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project saved search",
    description="Create a saved search scoped to a specific project.",
)
async def create_project_saved_search(
    project_id: str,
    request: CreateSavedSearchRequest,
    service: SavedSearchService = Depends(get_saved_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler),
):
    """Create a saved search for a specific project."""
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
        category = SearchCategory(request.category)

        config = SavedSearchConfig(
            name=request.name,
            description=request.description,
            query=request.query,
            scope=SearchScope.PROJECT,
            project_id=project_id,
            user_id=request.user_id,
            is_advanced=request.is_advanced,
            entity_types=request.entity_types,
            fields=request.fields,
            limit=request.limit,
            fuzzy=request.fuzzy,
            highlight=request.highlight,
            tags=request.tags,
            category=category,
            is_favorite=request.is_favorite,
            icon=request.icon,
            color=request.color,
        )

        search_id = await service.create_search(config)
        search = await service.get_search(search_id)

        if not search:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create saved search"
            )

        return saved_search_to_response(search)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
