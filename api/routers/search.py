"""
Search Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for full-text search across entities.

Endpoints:
- GET /api/v1/search - Global search with query params
- GET /api/v1/projects/{project_id}/search - Project-scoped search
- GET /api/v1/projects/{project_id}/search/advanced - Advanced boolean search
- GET /api/v1/search/fields - Get searchable fields
- GET /api/v1/search/syntax-help - Get advanced syntax documentation
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


class SyntaxHelpResponse(BaseModel):
    """Response model for syntax help documentation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "syntax": {
                    "operators": ["AND", "OR", "NOT"],
                    "wildcards": ["*", "?"],
                    "field_search": "field:value",
                    "phrase_search": "\"exact phrase\"",
                    "grouping": "(query1 OR query2) AND query3"
                },
                "examples": [
                    "email:john@example.com",
                    "name:John AND email:*@gmail.com"
                ]
            }
        }
    )

    syntax: dict[str, Any] = Field(..., description="Syntax reference")
    examples: list[dict[str, str]] = Field(
        default_factory=list,
        description="Query examples with descriptions"
    )
    operators: list[dict[str, str]] = Field(
        default_factory=list,
        description="Available operators"
    )
    wildcards: list[dict[str, str]] = Field(
        default_factory=list,
        description="Wildcard characters"
    )


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


@router.get(
    "/syntax-help",
    response_model=SyntaxHelpResponse,
    summary="Get advanced search syntax documentation",
    description="""
    Returns comprehensive documentation for the advanced boolean search syntax.

    This endpoint provides:
    - Available operators (AND, OR, NOT)
    - Wildcard characters (* and ?)
    - Field-specific search syntax
    - Phrase search syntax
    - Query grouping with parentheses
    - Real-world examples
    """,
    responses={
        200: {"description": "Syntax help returned successfully"},
    }
)
async def get_syntax_help():
    """
    Get documentation for advanced search syntax.

    Returns operators, wildcards, field syntax, and examples.
    """
    return SyntaxHelpResponse(
        syntax={
            "operators": {
                "AND": "Both conditions must match",
                "OR": "At least one condition must match",
                "NOT": "Negates the following condition"
            },
            "wildcards": {
                "*": "Matches any number of characters (including zero)",
                "?": "Matches exactly one character"
            },
            "field_search": "field:value - Search in a specific field",
            "phrase_search": '"exact phrase" - Search for exact phrase match',
            "grouping": "(query1 OR query2) AND query3 - Group queries with parentheses",
            "precedence": "NOT > AND > OR (from highest to lowest)"
        },
        examples=[
            {
                "query": "email:john@example.com",
                "description": "Find entities with exact email match"
            },
            {
                "query": "name:John AND email:*@gmail.com",
                "description": "Find John with any Gmail address"
            },
            {
                "query": '(tag:suspect OR tag:person_of_interest) AND NOT status:cleared',
                "description": "Complex boolean query with grouping"
            },
            {
                "query": '"John Smith"',
                "description": "Exact phrase match across all fields"
            },
            {
                "query": "phone:555* OR phone:777*",
                "description": "Multiple wildcard patterns with OR"
            },
            {
                "query": "name:J?hn",
                "description": "Single character wildcard (matches John, Jahn, etc.)"
            },
            {
                "query": "email:*@company.com AND NOT department:sales",
                "description": "Company emails excluding sales department"
            },
            {
                "query": '(name:"John Doe" OR name:"Jane Doe") AND city:Boston',
                "description": "Search for specific names in a city"
            }
        ],
        operators=[
            {
                "operator": "AND",
                "description": "Both conditions must be true",
                "example": "name:John AND city:Boston"
            },
            {
                "operator": "OR",
                "description": "At least one condition must be true",
                "example": "email:john@example.com OR phone:555-1234"
            },
            {
                "operator": "NOT",
                "description": "Negates the following condition",
                "example": "tag:customer AND NOT status:inactive"
            }
        ],
        wildcards=[
            {
                "character": "*",
                "description": "Matches zero or more characters",
                "example": "john* matches john, johnny, johnson"
            },
            {
                "character": "?",
                "description": "Matches exactly one character",
                "example": "j?hn matches john, jahn, jahn"
            }
        ]
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


@project_search_router.get(
    "/advanced",
    response_model=SearchResponse,
    summary="Advanced boolean search within a project",
    description="""
    Execute an advanced boolean search with operators, wildcards, and field-specific queries.

    Supports:
    - Boolean operators: AND, OR, NOT
    - Field-specific search: field:value
    - Phrase search: "exact phrase"
    - Wildcards: * (multiple chars), ? (single char)
    - Grouping: (query1 OR query2) AND query3

    See /api/v1/search/syntax-help for complete documentation.
    """,
    responses={
        200: {"description": "Search results returned successfully"},
        400: {"description": "Invalid query syntax"},
        404: {"description": "Project not found"},
    }
)
async def advanced_project_search(
    project_id: str,
    q: str = Query(
        ...,
        min_length=1,
        max_length=1000,
        description="Advanced search query with boolean operators",
        examples=[
            "email:john@example.com",
            "name:John AND email:*@gmail.com",
            '(tag:suspect OR tag:poi) AND NOT status:cleared'
        ]
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    highlight: bool = Query(True),
    search_service: SearchService = Depends(get_search_service_dep),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Execute an advanced boolean search within a specific project.

    - **project_id**: Project ID or safe_name to search in
    - **q**: Advanced query with boolean operators
    - **limit**: Max results per page (1-100, default 20)
    - **offset**: Skip N results for pagination
    - **highlight**: Generate highlighted snippets (default true)
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

    # Parse the query to validate syntax
    parsed = search_service.parse_advanced_query(q)
    if parsed.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query syntax: {parsed.error}"
        )

    # Create advanced search query
    query = SearchQuery(
        query=q,
        project_id=project_id,
        limit=limit,
        offset=offset,
        fuzzy=False,  # Disable fuzzy for advanced queries
        highlight=highlight,
        advanced=True  # Enable advanced parsing
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
