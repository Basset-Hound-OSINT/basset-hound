"""
Orphan Data Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for managing orphan data - unlinked identifiers
that haven't been tied to entities yet (emails, phone numbers, crypto addresses, etc.).

Endpoints:
- POST /api/v1/projects/{project_id}/orphans - Create orphan
- GET /api/v1/projects/{project_id}/orphans - List/search orphans
- GET /api/v1/projects/{project_id}/orphans/{orphan_id} - Get by ID
- PUT /api/v1/projects/{project_id}/orphans/{orphan_id} - Update orphan
- DELETE /api/v1/projects/{project_id}/orphans/{orphan_id} - Delete orphan
- GET /api/v1/projects/{project_id}/orphans/{orphan_id}/suggestions - Get entity match suggestions
- POST /api/v1/projects/{project_id}/orphans/{orphan_id}/link - Link to entity
- POST /api/v1/projects/{project_id}/orphans/batch - Bulk import
- GET /api/v1/projects/{project_id}/orphans/duplicates - Find duplicates
- GET /api/v1/orphans/types - List identifier types
"""

from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..models.orphan import (
    IdentifierType,
    OrphanDataCreate,
    OrphanDataUpdate,
    OrphanDataResponse,
    OrphanDataList,
    OrphanLinkRequest,
    OrphanLinkResponse,
    DetachRequest,
    DetachResponse,
)


# ----- Additional Response Models -----

class EntitySuggestion(BaseModel):
    """Model for entity match suggestion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "entity-550e8400-e29b-41d4-a716-446655440000",
                "entity_name": "John Doe",
                "match_score": 0.85,
                "match_reason": "Email domain matches existing entity email",
                "matched_fields": ["email"],
                "entity_data": {
                    "id": "entity-550e8400-e29b-41d4-a716-446655440000",
                    "profile": {
                        "name": {"first_name": "John", "last_name": "Doe"},
                        "email": "john.doe@example.com"
                    }
                }
            }
        }
    )

    entity_id: str = Field(..., description="Entity ID")
    entity_name: str = Field(..., description="Display name of entity")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence score (0-1)")
    match_reason: str = Field(..., description="Explanation of why this entity was suggested")
    matched_fields: list[str] = Field(
        default_factory=list,
        description="Fields that matched"
    )
    entity_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Basic entity information"
    )


class EntitySuggestionsResponse(BaseModel):
    """Response model for entity match suggestions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orphan_id": "orphan-550e8400-e29b-41d4-a716-446655440000",
                "suggestions": [
                    {
                        "entity_id": "entity-123",
                        "entity_name": "John Doe",
                        "match_score": 0.85,
                        "match_reason": "Email domain matches",
                        "matched_fields": ["email"],
                        "entity_data": {}
                    }
                ],
                "total": 1
            }
        }
    )

    orphan_id: str = Field(..., description="Orphan data ID")
    suggestions: list[EntitySuggestion] = Field(
        default_factory=list,
        description="List of matching entity suggestions"
    )
    total: int = Field(0, ge=0, description="Total number of suggestions")


class BatchImportItem(BaseModel):
    """Model for a single item in batch import."""

    identifier_type: IdentifierType = Field(..., description="Type of identifier")
    identifier_value: str = Field(..., description="Identifier value")
    source: Optional[str] = Field(default=None, description="Source")
    notes: Optional[str] = Field(default=None, description="Notes")
    tags: list[str] = Field(default_factory=list, description="Tags")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


class BatchImportRequest(BaseModel):
    """Model for batch import request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orphans": [
                    {
                        "identifier_type": "email",
                        "identifier_value": "user1@example.com",
                        "source": "data breach",
                        "tags": ["breach-2024"],
                        "confidence_score": 0.8
                    },
                    {
                        "identifier_type": "phone",
                        "identifier_value": "+1-555-0100",
                        "source": "public record",
                        "tags": ["verified"]
                    }
                ],
                "skip_duplicates": True
            }
        }
    )

    orphans: list[BatchImportItem] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of orphan data to import (max 1000)"
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Skip orphans with duplicate identifier values"
    )


class BatchImportResponse(BaseModel):
    """Response model for batch import."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "imported_count": 45,
                "skipped_count": 5,
                "failed_count": 0,
                "total_submitted": 50,
                "errors": [],
                "message": "Successfully imported 45 orphan data records"
            }
        }
    )

    success: bool = Field(..., description="Whether the operation succeeded")
    imported_count: int = Field(0, ge=0, description="Number of records successfully imported")
    skipped_count: int = Field(0, ge=0, description="Number of duplicates skipped")
    failed_count: int = Field(0, ge=0, description="Number of records that failed")
    total_submitted: int = Field(..., ge=0, description="Total records submitted")
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages for failed imports"
    )
    message: str = Field(..., description="Summary message")


class DuplicateGroup(BaseModel):
    """Model for a group of duplicate orphan data."""

    identifier_value: str = Field(..., description="The duplicated identifier value")
    identifier_type: IdentifierType = Field(..., description="Type of identifier")
    count: int = Field(..., ge=2, description="Number of duplicates")
    orphan_ids: list[str] = Field(..., description="IDs of duplicate orphan records")
    orphans: list[OrphanDataResponse] = Field(
        default_factory=list,
        description="Full orphan data records"
    )


class DuplicatesResponse(BaseModel):
    """Response model for duplicate detection."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "duplicates": [
                    {
                        "identifier_value": "john@example.com",
                        "identifier_type": "email",
                        "count": 3,
                        "orphan_ids": ["orphan-1", "orphan-2", "orphan-3"],
                        "orphans": []
                    }
                ],
                "total_groups": 1,
                "total_duplicates": 3,
                "project_id": "project-123"
            }
        }
    )

    duplicates: list[DuplicateGroup] = Field(
        default_factory=list,
        description="List of duplicate groups"
    )
    total_groups: int = Field(0, ge=0, description="Number of duplicate groups found")
    total_duplicates: int = Field(0, ge=0, description="Total number of duplicate records")
    project_id: str = Field(..., description="Project ID")


class IdentifierTypeInfo(BaseModel):
    """Model for identifier type information."""

    type: IdentifierType = Field(..., description="Identifier type enum value")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Description of this identifier type")
    examples: list[str] = Field(default_factory=list, description="Example values")


class IdentifierTypesResponse(BaseModel):
    """Response model for identifier types list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "types": [
                    {
                        "type": "email",
                        "name": "Email Address",
                        "description": "Email address identifier",
                        "examples": ["user@example.com", "name.surname@company.org"]
                    }
                ],
                "count": 15
            }
        }
    )

    types: list[IdentifierTypeInfo] = Field(
        default_factory=list,
        description="List of supported identifier types"
    )
    count: int = Field(0, ge=0, description="Number of identifier types")


# ----- Router Configuration -----

router = APIRouter(
    prefix="/projects/{project_id}/orphans",
    tags=["orphans"],
    responses={
        404: {"description": "Project or orphan data not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)

# Global router for non-project-specific endpoints
global_router = APIRouter(
    prefix="/orphans",
    tags=["orphans"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Helper Functions -----

def _verify_project_exists(neo4j_handler, project_id: str) -> dict:
    """
    Verify that a project exists.

    Args:
        neo4j_handler: Neo4j handler instance
        project_id: Project ID or safe_name

    Returns:
        Project data dictionary

    Raises:
        HTTPException: If project not found
    """
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

    return project


# NOTE: The following endpoints are placeholders that demonstrate the API structure.
# A full implementation would require an OrphanService class to be created in
# api/services/orphan_service.py with methods for CRUD operations, linking, etc.
# For now, these endpoints show proper request/response handling patterns.


# ----- CRUD Endpoints -----

@router.post(
    "",
    response_model=OrphanDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create orphan data",
    description="""
    Create a new orphan data record.

    Orphan data represents unlinked identifiers that haven't been tied to entities yet.
    This is useful for OSINT work where data is collected before entity relationships
    are established.

    The system will auto-generate an ID and timestamp if not provided.
    """,
    responses={
        201: {"description": "Orphan data created successfully"},
        404: {"description": "Project not found"},
        422: {"description": "Invalid orphan data"},
    }
)
async def create_orphan(
    project_id: str,
    orphan: OrphanDataCreate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a new orphan data record.

    - **project_id**: Project ID or safe_name
    - **orphan**: Orphan data details
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # result = await service.create_orphan(project_id, orphan)
        # return result

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending. Please implement OrphanService in api/services/orphan_service.py"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create orphan data: {str(e)}"
        )


@router.get(
    "",
    response_model=OrphanDataList,
    summary="List and search orphan data",
    description="""
    List or search orphan data in a project with filtering and pagination.

    Supports filtering by:
    - Identifier type (email, phone, crypto_address, etc.)
    - Tags
    - Date range (discovered_date)
    - Link status (linked vs unlinked)

    Results are paginated with limit/offset parameters.
    """,
    responses={
        200: {"description": "Orphan data list returned successfully"},
        404: {"description": "Project not found"},
    }
)
async def list_orphans(
    project_id: str,
    identifier_type: Optional[IdentifierType] = Query(
        None,
        description="Filter by identifier type"
    ),
    tags: Optional[str] = Query(
        None,
        description="Comma-separated tags to filter by (OR logic)"
    ),
    date_from: Optional[str] = Query(
        None,
        description="Filter orphans discovered on or after this date (ISO 8601)",
        examples=["2024-01-01T00:00:00"]
    ),
    date_to: Optional[str] = Query(
        None,
        description="Filter orphans discovered on or before this date (ISO 8601)",
        examples=["2024-12-31T23:59:59"]
    ),
    linked_only: Optional[bool] = Query(
        None,
        description="Filter by link status: true=linked, false=unlinked, null=all"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of results (1-1000)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip for pagination"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List and search orphan data with filtering.

    - **project_id**: Project ID or safe_name
    - **identifier_type**: Filter by type (optional)
    - **tags**: Comma-separated tags (optional)
    - **date_from**: Start date filter (optional)
    - **date_to**: End date filter (optional)
    - **linked_only**: Filter by link status (optional)
    - **limit**: Max results (default 100)
    - **offset**: Pagination offset (default 0)
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # orphans, total = await service.list_orphans(
        #     project_id=project_id,
        #     identifier_type=identifier_type,
        #     tags=tag_list,
        #     date_from=date_from,
        #     date_to=date_to,
        #     linked_only=linked_only,
        #     limit=limit,
        #     offset=offset
        # )
        # return OrphanDataList(orphans=orphans, total=total, project_id=project_id)

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list orphan data: {str(e)}"
        )


@router.get(
    "/{orphan_id}",
    response_model=OrphanDataResponse,
    summary="Get orphan data by ID",
    description="Retrieve a specific orphan data record by its ID.",
    responses={
        200: {"description": "Orphan data returned successfully"},
        404: {"description": "Orphan data or project not found"},
    }
)
async def get_orphan(
    project_id: str,
    orphan_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get a specific orphan data record.

    - **project_id**: Project ID or safe_name
    - **orphan_id**: Orphan data ID
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # orphan = await service.get_orphan(project_id, orphan_id)
        #
        # if not orphan:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Orphan data '{orphan_id}' not found in project '{project_id}'"
        #     )
        #
        # return orphan

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orphan data: {str(e)}"
        )


@router.put(
    "/{orphan_id}",
    response_model=OrphanDataResponse,
    summary="Update orphan data",
    description="""
    Update an existing orphan data record.

    Supports partial updates - only provided fields will be modified.
    All fields are optional in the update payload.
    """,
    responses={
        200: {"description": "Orphan data updated successfully"},
        404: {"description": "Orphan data or project not found"},
        422: {"description": "Invalid update data"},
    }
)
async def update_orphan(
    project_id: str,
    orphan_id: str,
    orphan_update: OrphanDataUpdate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update an orphan data record.

    - **project_id**: Project ID or safe_name
    - **orphan_id**: Orphan data ID
    - **orphan_update**: Fields to update
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # orphan = await service.update_orphan(project_id, orphan_id, orphan_update)
        #
        # if not orphan:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Orphan data '{orphan_id}' not found in project '{project_id}'"
        #     )
        #
        # return orphan

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update orphan data: {str(e)}"
        )


@router.delete(
    "/{orphan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete orphan data",
    description="Delete an orphan data record permanently.",
    responses={
        204: {"description": "Orphan data deleted successfully"},
        404: {"description": "Orphan data or project not found"},
    }
)
async def delete_orphan(
    project_id: str,
    orphan_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete an orphan data record.

    - **project_id**: Project ID or safe_name
    - **orphan_id**: Orphan data ID to delete
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # success = await service.delete_orphan(project_id, orphan_id)
        #
        # if not success:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"Orphan data '{orphan_id}' not found in project '{project_id}'"
        #     )
        #
        # return None  # 204 No Content

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete orphan data: {str(e)}"
        )


# ----- Linking Endpoints -----

@router.get(
    "/{orphan_id}/suggestions",
    response_model=EntitySuggestionsResponse,
    summary="Get entity match suggestions",
    description="""
    Get entity match suggestions for an orphan data record.

    The system analyzes the orphan data and suggests entities that might match
    based on similar identifiers, shared attributes, or other heuristics.

    Suggestions are ranked by confidence score.
    """,
    responses={
        200: {"description": "Suggestions returned successfully"},
        404: {"description": "Orphan data or project not found"},
    }
)
async def get_entity_suggestions(
    project_id: str,
    orphan_id: str,
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of suggestions to return"
    ),
    min_score: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum match score threshold (0-1)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get entity match suggestions for orphan data.

    - **project_id**: Project ID or safe_name
    - **orphan_id**: Orphan data ID
    - **limit**: Max suggestions to return (default 10)
    - **min_score**: Minimum confidence score (default 0.5)
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # suggestions = await service.get_entity_suggestions(
        #     project_id=project_id,
        #     orphan_id=orphan_id,
        #     limit=limit,
        #     min_score=min_score
        # )
        #
        # return EntitySuggestionsResponse(
        #     orphan_id=orphan_id,
        #     suggestions=suggestions,
        #     total=len(suggestions)
        # )

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity suggestions: {str(e)}"
        )


@router.post(
    "/{orphan_id}/link",
    response_model=OrphanLinkResponse,
    summary="Link orphan data to entity",
    description="""
    Link an orphan data record to an entity.

    This operation can:
    1. Create a relationship between the orphan and entity
    2. Optionally merge the orphan data into the entity's profile
    3. Optionally delete the orphan record after linking

    The target field in the entity profile can be auto-detected based on
    the identifier type, or explicitly specified.
    """,
    responses={
        200: {"description": "Orphan data linked successfully"},
        404: {"description": "Orphan data, entity, or project not found"},
        422: {"description": "Invalid link request"},
    }
)
async def link_orphan_to_entity(
    project_id: str,
    orphan_id: str,
    link_request: OrphanLinkRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Link orphan data to an entity.

    - **project_id**: Project ID or safe_name
    - **orphan_id**: Orphan data ID
    - **link_request**: Link configuration
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # result = await service.link_orphan_to_entity(
        #     project_id=project_id,
        #     orphan_id=orphan_id,
        #     link_request=link_request
        # )
        #
        # return result

        # Import and use orphan service
        from ..services.orphan_service import get_orphan_service
        service = get_orphan_service(neo4j_handler)
        result = service.link_to_entity(
            project_id=project_id,
            orphan_id=orphan_id,
            entity_id=link_request.entity_id,
            merge=link_request.merge_to_entity,
            delete=link_request.delete_orphan
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link orphan data: {str(e)}"
        )


@router.post(
    "/detach",
    response_model=DetachResponse,
    summary="Detach data from entity to orphan",
    description="""
    Detach a field value from an entity and convert it to orphan data.

    This enables "soft delete" functionality - data is never truly lost,
    just moved from an entity to orphan status. This supports bidirectional
    data flow between entities and orphan data.

    Options:
    - **keep_in_entity**: If true, copies the value to orphan but keeps it in entity
    - **reason**: Optional explanation for the detachment

    The orphan record will contain metadata about its origin for provenance tracking.
    """,
    responses={
        200: {"description": "Data successfully detached and converted to orphan"},
        400: {"description": "Detach operation failed"},
        404: {"description": "Entity or project not found"},
        422: {"description": "Invalid detach request"},
    }
)
async def detach_from_entity(
    project_id: str,
    detach_request: DetachRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Detach data from an entity and convert to orphan.

    - **project_id**: Project ID or safe_name
    - **detach_request**: Detach configuration including entity_id, field_path, field_value
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        from ..services.orphan_service import get_orphan_service
        service = get_orphan_service(neo4j_handler)
        result = service.detach_from_entity(project_id, detach_request)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detach data: {str(e)}"
        )


# ----- Bulk & Utility Endpoints -----

@router.post(
    "/batch",
    response_model=BatchImportResponse,
    summary="Bulk import orphan data",
    description="""
    Import multiple orphan data records in a single request.

    Supports up to 1000 records per request. The operation can:
    - Skip duplicates (based on identifier_value)
    - Continue on errors (best-effort import)
    - Return detailed statistics about import results

    This is useful for importing data from external sources or bulk uploads.
    """,
    responses={
        200: {"description": "Batch import completed"},
        404: {"description": "Project not found"},
        422: {"description": "Invalid batch data"},
    }
)
async def batch_import_orphans(
    project_id: str,
    batch_request: BatchImportRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Bulk import orphan data records.

    - **project_id**: Project ID or safe_name
    - **batch_request**: Batch import configuration with orphan data list
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # result = await service.batch_import(project_id, batch_request)
        #
        # return result

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch import orphan data: {str(e)}"
        )


@router.get(
    "/duplicates",
    response_model=DuplicatesResponse,
    summary="Find duplicate orphan data",
    description="""
    Find orphan data records with duplicate identifier values.

    This helps identify:
    - Multiple imports of the same identifier
    - Potential data quality issues
    - Records that could be merged

    Results are grouped by identifier value and type.
    """,
    responses={
        200: {"description": "Duplicates found and returned"},
        404: {"description": "Project not found"},
    }
)
async def find_duplicates(
    project_id: str,
    identifier_type: Optional[IdentifierType] = Query(
        None,
        description="Filter duplicates by identifier type"
    ),
    min_count: int = Query(
        2,
        ge=2,
        le=100,
        description="Minimum number of duplicates to include in results"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find duplicate orphan data records.

    - **project_id**: Project ID or safe_name
    - **identifier_type**: Filter by type (optional)
    - **min_count**: Minimum duplicates to report (default 2)
    """
    # Verify project exists
    project = _verify_project_exists(neo4j_handler, project_id)

    try:
        # TODO: Implement orphan service
        # from ..services.orphan_service import get_orphan_service
        # service = get_orphan_service(neo4j_handler)
        # duplicates = await service.find_duplicates(
        #     project_id=project_id,
        #     identifier_type=identifier_type,
        #     min_count=min_count
        # )
        #
        # return DuplicatesResponse(
        #     duplicates=duplicates,
        #     total_groups=len(duplicates),
        #     total_duplicates=sum(d.count for d in duplicates),
        #     project_id=project_id
        # )

        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Orphan service implementation pending"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find duplicates: {str(e)}"
        )


# ----- Global Endpoints (Non-Project-Specific) -----

@global_router.get(
    "/types",
    response_model=IdentifierTypesResponse,
    summary="List identifier types",
    description="""
    Get a list of all supported identifier types for orphan data.

    This endpoint returns metadata about each identifier type including:
    - Type enum value
    - Human-readable name
    - Description
    - Example values

    Useful for building UI forms and validation.
    """,
    responses={
        200: {"description": "Identifier types returned successfully"},
    }
)
async def list_identifier_types():
    """
    Get list of supported identifier types.

    Returns metadata for all available identifier types.
    """
    try:
        # Define identifier type metadata
        type_metadata = {
            IdentifierType.EMAIL: {
                "name": "Email Address",
                "description": "Email address identifier",
                "examples": ["user@example.com", "name.surname@company.org"]
            },
            IdentifierType.PHONE: {
                "name": "Phone Number",
                "description": "Phone number in any format",
                "examples": ["+1-555-0100", "(555) 123-4567", "+44 20 7123 4567"]
            },
            IdentifierType.CRYPTO_ADDRESS: {
                "name": "Cryptocurrency Address",
                "description": "Blockchain wallet address",
                "examples": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"]
            },
            IdentifierType.USERNAME: {
                "name": "Username",
                "description": "Username or handle from any platform",
                "examples": ["@john_doe", "user123", "alice_smith"]
            },
            IdentifierType.IP_ADDRESS: {
                "name": "IP Address",
                "description": "IPv4 or IPv6 address",
                "examples": ["192.168.1.1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"]
            },
            IdentifierType.DOMAIN: {
                "name": "Domain Name",
                "description": "Domain or hostname",
                "examples": ["example.com", "subdomain.example.org", "website.co.uk"]
            },
            IdentifierType.URL: {
                "name": "URL",
                "description": "Full URL or web address",
                "examples": ["https://example.com/page", "http://subdomain.site.org/path?query=value"]
            },
            IdentifierType.SOCIAL_MEDIA: {
                "name": "Social Media Profile",
                "description": "Social media profile URL or handle",
                "examples": ["https://twitter.com/username", "https://linkedin.com/in/profile"]
            },
            IdentifierType.LICENSE_PLATE: {
                "name": "License Plate",
                "description": "Vehicle license plate number",
                "examples": ["ABC-1234", "XYZ 789", "AB12 CDE"]
            },
            IdentifierType.PASSPORT: {
                "name": "Passport Number",
                "description": "Passport identification number",
                "examples": ["X1234567", "AB1234567"]
            },
            IdentifierType.SSN: {
                "name": "Social Security Number",
                "description": "Social Security Number or national ID",
                "examples": ["123-45-6789"]
            },
            IdentifierType.ACCOUNT_NUMBER: {
                "name": "Account Number",
                "description": "Bank account or other account number",
                "examples": ["1234567890", "ACCT-98765432"]
            },
            IdentifierType.MAC_ADDRESS: {
                "name": "MAC Address",
                "description": "Network device MAC address",
                "examples": ["00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E"]
            },
            IdentifierType.IMEI: {
                "name": "IMEI Number",
                "description": "Mobile device IMEI number",
                "examples": ["123456789012345", "12-345678-901234-5"]
            },
            IdentifierType.OTHER: {
                "name": "Other",
                "description": "Other identifier type not listed above",
                "examples": ["custom-id-123"]
            },
        }

        types = []
        for identifier_type in IdentifierType:
            metadata = type_metadata.get(identifier_type, {
                "name": identifier_type.value.replace("_", " ").title(),
                "description": f"{identifier_type.value} identifier",
                "examples": []
            })

            types.append(IdentifierTypeInfo(
                type=identifier_type,
                name=metadata["name"],
                description=metadata["description"],
                examples=metadata["examples"]
            ))

        return IdentifierTypesResponse(
            types=types,
            count=len(types)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve identifier types: {str(e)}"
        )
