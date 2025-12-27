"""
Search Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for full-text search across entities.

Endpoints:
- GET /api/v1/search - Global search with query params
- GET /api/v1/projects/{project_id}/search - Project-scoped search
- GET /api/v1/search/fields - Get searchable fields
- POST /api/v1/projects/{project_id}/search/reindex - Rebuild search index
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler, get_app_config
from ..services.search_service import (
    SearchService,
    SearchQuery,
    SearchResult,
    get_search_service,
    set_search_service,
)


# ----- Pydantic Models -----

class SearchResultResponse(BaseModel):
    """Response model for a single search result."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "project-123",
                "entity_type": "Person",
                "score": 0.95,
                "highlights": {
                    "core.name": ["**John** Doe"],
                    "core.email": ["...contact **john**@example.com..."]
                },
                "matched_fields": ["core.name", "core.email"],
                "entity_data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": {"first_name": "John", "last_name": "Doe"}
                }
            }
        }
    )

    entity_id: str = Field(..., description="Unique entity identifier")
    project_id: str = Field(..., description="Project ID containing the entity")
    entity_type: str = Field(..., description="Type of entity (e.g., 'Person')")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    highlights: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Field -> matching snippets with highlights"
    )
    matched_fields: list[str] = Field(
        default_factory=list,
        description="List of fields that matched the query"
    )
    entity_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Basic entity information"
    )


class SearchResponse(BaseModel):
    """Response model for search results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "project-123",
                        "entity_type": "Person",
                        "score": 0.95,
                        "highlights": {"core.name": ["**John** Doe"]},
                        "matched_fields": ["core.name"],
                        "entity_data": {"id": "550e8400-e29b-41d4-a716-446655440000"}
                    }
                ],
                "total": 1,
                "query": "John",
                "limit": 20,
                "offset": 0
            }
        }
    )

    results: list[SearchResultResponse] = Field(
        default_factory=list,
        description="List of matching search results"
    )
    total: int = Field(0, ge=0, description="Total number of matching results")
    query: str = Field(..., description="The search query that was executed")
    limit: int = Field(20, ge=1, le=100, description="Maximum results returned")
    offset: int = Field(0, ge=0, description="Number of results skipped")


class SearchFieldsResponse(BaseModel):
    """Response model for searchable fields."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fields": [
                    "core.name",
                    "core.email",
                    "core.name.first_name",
                    "core.name.last_name",
                    "social.linkedin.url"
                ],
                "count": 5
            }
        }
    )

    fields: list[str] = Field(
        default_factory=list,
        description="List of searchable field paths"
    )
    count: int = Field(0, ge=0, description="Number of searchable fields")


class ReindexResponse(BaseModel):
    """Response model for reindex operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "indexed_count": 42,
                "project_id": "project-123",
                "message": "Successfully indexed 42 entities"
            }
        }
    )

    success: bool = Field(..., description="Whether the operation succeeded")
    indexed_count: int = Field(0, ge=0, description="Number of entities indexed")
    project_id: str = Field(..., description="Project that was reindexed")
    message: str = Field(..., description="Status message")


# ----- Dependency -----

def get_search_service_dep(
    neo4j_handler=Depends(get_neo4j_handler),
    config=Depends(get_app_config)
) -> SearchService:
    """
    Dependency to get the SearchService instance.

    Creates or returns the singleton SearchService.
    """
    try:
        return get_search_service(neo4j_handler, config)
    except Exception:
        # Create a new instance if singleton fails
        return SearchService(neo4j_handler, config)


# ----- Routers -----

# Global search router
router = APIRouter(
    prefix="/search",
    tags=["search"],
    responses={
        500: {"description": "Internal server error"},
    },
)

# Project-scoped search router
project_search_router = APIRouter(
    prefix="/projects/{project_id}/search",
    tags=["search"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Global Search Endpoints -----

@router.get(
    "",
    response_model=SearchResponse,
    summary="Global search across all projects",
    description="""
    Search for entities across all projects.

    Supports:
    - Full-text search with relevance scoring
    - Fuzzy matching for typos and variations
    - Field-specific search with the 'fields' parameter
    - Pagination with limit and offset
    - Highlighted snippets showing matched text
    """,
    responses={
        200: {"description": "Search results returned successfully"},
        400: {"description": "Invalid search parameters"},
    }
)
async def global_search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="Search query text",
        examples=["John Doe", "email:john@example.com"]
    ),
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated entity types to filter (e.g., 'Person')",
        examples=["Person"]
    ),
    fields: Optional[str] = Query(
        None,
        description="Comma-separated field paths to search (e.g., 'core.name,core.email')",
        examples=["core.name,core.email"]
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip for pagination"
    ),
    fuzzy: bool = Query(
        True,
        description="Enable fuzzy matching for typo tolerance"
    ),
    highlight: bool = Query(
        True,
        description="Include highlighted snippets in results"
    ),
    search_service: SearchService = Depends(get_search_service_dep)
):
    """
    Execute a global search across all projects.

    - **q**: Required search query text
    - **entity_types**: Optional filter by entity type
    - **fields**: Optional specific fields to search
    - **limit**: Max results per page (1-100, default 20)
    - **offset**: Skip N results for pagination
    - **fuzzy**: Enable fuzzy matching (default true)
    - **highlight**: Generate highlighted snippets (default true)
    """
    # Parse comma-separated parameters
    entity_type_list = None
    if entity_types:
        entity_type_list = [t.strip() for t in entity_types.split(",") if t.strip()]

    field_list = None
    if fields:
        field_list = [f.strip() for f in fields.split(",") if f.strip()]

    # Create search query
    query = SearchQuery(
        query=q,
        project_id=None,  # Global search
        entity_types=entity_type_list,
        fields=field_list,
        limit=limit,
        offset=offset,
        fuzzy=fuzzy,
        highlight=highlight,
    )

    try:
        results, total = await search_service.search(query)

        return SearchResponse(
            results=[
                SearchResultResponse(
                    entity_id=r.entity_id,
                    project_id=r.project_id,
                    entity_type=r.entity_type,
                    score=r.score,
                    highlights=r.highlights,
                    matched_fields=r.matched_fields,
                    entity_data=r.entity_data,
                )
                for r in results
            ],
            total=total,
            query=q,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/fields",
    response_model=SearchFieldsResponse,
    summary="Get searchable fields",
    description="Returns a list of field paths that are searchable based on the configuration.",
    responses={
        200: {"description": "Searchable fields returned successfully"},
    }
)
async def get_searchable_fields(
    search_service: SearchService = Depends(get_search_service_dep)
):
    """
    Get the list of searchable fields from the configuration.

    Returns field paths in the format 'section.field' or 'section.field.component'.
    """
    try:
        fields = search_service.get_searchable_fields()
        return SearchFieldsResponse(
            fields=fields,
            count=len(fields),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get searchable fields: {str(e)}"
        )


# ----- Project-Scoped Search Endpoints -----

@project_search_router.get(
    "",
    response_model=SearchResponse,
    summary="Search within a project",
    description="""
    Search for entities within a specific project.

    Same features as global search but scoped to the specified project.
    """,
    responses={
        200: {"description": "Search results returned successfully"},
        404: {"description": "Project not found"},
    }
)
async def project_search(
    project_id: str,
    q: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="Search query text"
    ),
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated entity types to filter"
    ),
    fields: Optional[str] = Query(
        None,
        description="Comma-separated field paths to search"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    fuzzy: bool = Query(True),
    highlight: bool = Query(True),
    search_service: SearchService = Depends(get_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Execute a search within a specific project.

    - **project_id**: Project ID or safe_name to search in
    - **q**: Required search query text
    - Other parameters same as global search
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_id)
    if not project:
        # Try to find by ID
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

    # Parse parameters
    entity_type_list = None
    if entity_types:
        entity_type_list = [t.strip() for t in entity_types.split(",") if t.strip()]

    field_list = None
    if fields:
        field_list = [f.strip() for f in fields.split(",") if f.strip()]

    # Create search query scoped to project
    query = SearchQuery(
        query=q,
        project_id=project_id,
        entity_types=entity_type_list,
        fields=field_list,
        limit=limit,
        offset=offset,
        fuzzy=fuzzy,
        highlight=highlight,
    )

    try:
        results, total = await search_service.search(query)

        return SearchResponse(
            results=[
                SearchResultResponse(
                    entity_id=r.entity_id,
                    project_id=r.project_id,
                    entity_type=r.entity_type,
                    score=r.score,
                    highlights=r.highlights,
                    matched_fields=r.matched_fields,
                    entity_data=r.entity_data,
                )
                for r in results
            ],
            total=total,
            query=q,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@project_search_router.post(
    "/reindex",
    response_model=ReindexResponse,
    summary="Rebuild search index for project",
    description="""
    Rebuilds the full-text search index for all entities in the specified project.

    This operation:
    1. Iterates through all entities in the project
    2. Extracts searchable text from each entity's profile
    3. Updates the search index entries

    Use this after bulk imports or when search results seem incorrect.
    """,
    responses={
        200: {"description": "Reindex completed successfully"},
        404: {"description": "Project not found"},
    }
)
async def reindex_project(
    project_id: str,
    search_service: SearchService = Depends(get_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Rebuild the search index for a project.

    - **project_id**: Project ID or safe_name to reindex
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
        indexed_count = await search_service.build_search_index(project_id)

        return ReindexResponse(
            success=True,
            indexed_count=indexed_count,
            project_id=project_id,
            message=f"Successfully indexed {indexed_count} entities"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}"
        )


# ----- Entity-Scoped Search -----

@project_search_router.get(
    "/entity/{entity_id}",
    response_model=SearchResponse,
    summary="Search within a specific entity",
    description="Search for text within a specific entity's profile data.",
    responses={
        200: {"description": "Search results returned successfully"},
        404: {"description": "Entity or project not found"},
    }
)
async def search_in_entity(
    project_id: str,
    entity_id: str,
    q: str = Query(..., min_length=1, max_length=500, description="Search query text"),
    search_service: SearchService = Depends(get_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Search within a specific entity's data.

    - **project_id**: Project ID or safe_name
    - **entity_id**: Entity ID to search within
    - **q**: Search query text
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

    project_safe_name = project.get("safe_name", project_id)

    # Verify entity exists
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        results = await search_service.search_entity(project_id, entity_id, q)

        return SearchResponse(
            results=[
                SearchResultResponse(
                    entity_id=r.entity_id,
                    project_id=r.project_id,
                    entity_type=r.entity_type,
                    score=r.score,
                    highlights=r.highlights,
                    matched_fields=r.matched_fields,
                    entity_data=r.entity_data,
                )
                for r in results
            ],
            total=len(results),
            query=q,
            limit=1,
            offset=0,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
