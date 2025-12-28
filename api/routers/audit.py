"""
Audit Log Router for Basset Hound.

Provides endpoints for querying audit logs for entities and projects.
Part of Phase 14: Enterprise Features.

Endpoints:
- GET /projects/{project_id}/audit - Get audit logs for a project
- GET /entities/{entity_id}/audit - Get audit logs for an entity
- GET /audit - Get all audit logs (admin, with pagination)
- GET /audit/stats - Get audit log statistics
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..services.audit_logger import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
    EntityType,
    get_audit_logger,
)


# ==================== Pydantic Models ====================


class AuditLogResponse(BaseModel):
    """Schema for a single audit log entry response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "CREATE",
            "entity_type": "ENTITY",
            "entity_id": "entity-123",
            "project_id": "project-456",
            "user_id": "user-789",
            "changes": {"profile": {"name": "John Doe"}},
            "ip_address": "192.168.1.1",
            "metadata": None
        }
    })

    id: str = Field(..., description="Unique identifier for the audit log entry")
    timestamp: str = Field(..., description="ISO 8601 timestamp when the action occurred")
    action: str = Field(..., description="The type of action (CREATE, UPDATE, DELETE, LINK, UNLINK, VIEW)")
    entity_type: str = Field(..., description="The type of entity affected")
    entity_id: str = Field(..., description="The unique identifier of the affected entity")
    project_id: Optional[str] = Field(None, description="The project context")
    user_id: Optional[str] = Field(None, description="The user who performed the action")
    changes: Optional[Dict[str, Any]] = Field(None, description="JSON representation of what changed")
    ip_address: Optional[str] = Field(None, description="IP address of the request origin")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context information")


class AuditLogListResponse(BaseModel):
    """Schema for a list of audit log entries."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "logs": [],
            "total": 0,
            "limit": 100,
            "offset": 0
        }
    })

    logs: List[AuditLogResponse] = Field(default_factory=list, description="List of audit log entries")
    total: int = Field(0, description="Total number of matching entries")
    limit: int = Field(100, description="Maximum entries returned")
    offset: int = Field(0, description="Number of entries skipped")


class AuditStatsResponse(BaseModel):
    """Schema for audit log statistics."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_entries": 1000,
            "max_entries": 10000,
            "action_counts": {"CREATE": 100, "UPDATE": 500, "DELETE": 50},
            "entity_type_counts": {"ENTITY": 400, "PROJECT": 50}
        }
    })

    total_entries: int = Field(0, description="Total number of audit log entries")
    max_entries: int = Field(10000, description="Maximum entries allowed")
    action_counts: Dict[str, int] = Field(default_factory=dict, description="Count of entries by action type")
    entity_type_counts: Dict[str, int] = Field(default_factory=dict, description="Count of entries by entity type")


class AuditHealthResponse(BaseModel):
    """Schema for audit logger health check response."""
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    enabled: Optional[bool] = Field(None, description="Whether audit logging is enabled")
    backend_type: Optional[str] = Field(None, description="Type of backend in use")
    has_entries: Optional[bool] = Field(None, description="Whether there are any entries")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


# ==================== Dependency ====================


def get_audit_service() -> AuditLogger:
    """Dependency to get the audit logger service."""
    return get_audit_logger()


# ==================== Routers ====================

# Main audit router for global audit endpoints
router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    responses={
        500: {"description": "Internal server error"},
    },
)

# Project audit router
project_audit_router = APIRouter(
    prefix="/projects/{project_id}/audit",
    tags=["audit", "projects"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)

# Entity audit router
entity_audit_router = APIRouter(
    prefix="/entities/{entity_id}/audit",
    tags=["audit", "entities"],
    responses={
        404: {"description": "Entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ==================== Global Audit Endpoints ====================


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Get all audit logs",
    description="Retrieve all audit logs with optional filtering and pagination. Admin endpoint.",
    responses={
        200: {"description": "Audit logs retrieved successfully"},
    }
)
async def get_all_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type (CREATE, UPDATE, DELETE, LINK, UNLINK, VIEW)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (PROJECT, ENTITY, RELATIONSHIP, etc.)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO 8601 format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    audit_service: AuditLogger = Depends(get_audit_service),
):
    """
    Get all audit logs.

    This is an admin endpoint that returns all audit logs with optional filtering.
    Use query parameters to filter by action, entity type, user, and date range.

    - **action**: Filter by action type
    - **entity_type**: Filter by entity type
    - **user_id**: Filter by user ID
    - **start_date**: Filter from this date (ISO 8601)
    - **end_date**: Filter until this date (ISO 8601)
    - **limit**: Maximum number of results (1-1000)
    - **offset**: Pagination offset
    """
    try:
        # Parse action filter
        parsed_action = None
        if action:
            try:
                parsed_action = AuditAction(action.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action type: {action}. Valid values: {[a.value for a in AuditAction]}"
                )

        # Parse entity_type filter
        parsed_entity_type = None
        if entity_type:
            try:
                parsed_entity_type = EntityType(entity_type.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid entity type: {entity_type}. Valid values: {[e.value for e in EntityType]}"
                )

        # Parse date filters
        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format: {start_date}. Use ISO 8601 format."
                )

        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_date format: {end_date}. Use ISO 8601 format."
                )

        # Query logs
        logs = await audit_service.get_logs(
            action=parsed_action,
            entity_type=parsed_entity_type,
            user_id=user_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
        )

        # Convert to response format
        log_responses = [AuditLogResponse(**entry.to_dict()) for entry in logs]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),  # Note: This is the count of returned entries
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=AuditStatsResponse,
    summary="Get audit log statistics",
    description="Retrieve statistics about audit logs including counts by action and entity type.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
    }
)
async def get_audit_stats(
    audit_service: AuditLogger = Depends(get_audit_service),
):
    """
    Get audit log statistics.

    Returns aggregate statistics about the audit logs including:
    - Total number of entries
    - Maximum entries allowed
    - Count of entries by action type
    - Count of entries by entity type
    """
    try:
        stats = audit_service.get_stats()

        return AuditStatsResponse(
            total_entries=stats.get("total_entries", 0),
            max_entries=stats.get("max_entries", 10000),
            action_counts=stats.get("action_counts", {}),
            entity_type_counts=stats.get("entity_type_counts", {}),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit statistics: {str(e)}"
        )


@router.get(
    "/health",
    response_model=AuditHealthResponse,
    summary="Health check for audit logger",
    description="Check the health status of the audit logging service.",
    responses={
        200: {"description": "Health check completed"},
    }
)
async def audit_health_check(
    audit_service: AuditLogger = Depends(get_audit_service),
):
    """
    Perform a health check on the audit logger.

    Returns the current health status of the audit logging service
    including whether it's enabled and the backend type.
    """
    try:
        health = await audit_service.health_check()
        return AuditHealthResponse(**health)

    except Exception as e:
        return AuditHealthResponse(
            status="unhealthy",
            error=str(e),
        )


# ==================== Project Audit Endpoints ====================


@project_audit_router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Get audit logs for a project",
    description="Retrieve all audit logs associated with a specific project.",
    responses={
        200: {"description": "Project audit logs retrieved successfully"},
    }
)
async def get_project_audit_logs(
    project_id: str,
    action: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    audit_service: AuditLogger = Depends(get_audit_service),
):
    """
    Get audit logs for a specific project.

    Returns all audit log entries associated with the given project ID.

    - **project_id**: The project ID to filter by
    - **action**: Optional filter by action type
    - **entity_type**: Optional filter by entity type
    - **start_date**: Optional filter from this date (ISO 8601)
    - **end_date**: Optional filter until this date (ISO 8601)
    - **limit**: Maximum number of results (1-1000)
    - **offset**: Pagination offset
    """
    try:
        # Parse optional filters
        parsed_action = None
        if action:
            try:
                parsed_action = AuditAction(action.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action type: {action}"
                )

        parsed_entity_type = None
        if entity_type:
            try:
                parsed_entity_type = EntityType(entity_type.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid entity type: {entity_type}"
                )

        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format: {start_date}"
                )

        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_date format: {end_date}"
                )

        # Query logs for the project
        logs = await audit_service.get_logs(
            project_id=project_id,
            action=parsed_action,
            entity_type=parsed_entity_type,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
        )

        log_responses = [AuditLogResponse(**entry.to_dict()) for entry in logs]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project audit logs: {str(e)}"
        )


# ==================== Entity Audit Endpoints ====================


@entity_audit_router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Get audit logs for an entity",
    description="Retrieve all audit logs associated with a specific entity.",
    responses={
        200: {"description": "Entity audit logs retrieved successfully"},
    }
)
async def get_entity_audit_logs(
    entity_id: str,
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    audit_service: AuditLogger = Depends(get_audit_service),
):
    """
    Get audit logs for a specific entity.

    Returns all audit log entries associated with the given entity ID.

    - **entity_id**: The entity ID to filter by
    - **action**: Optional filter by action type
    - **start_date**: Optional filter from this date (ISO 8601)
    - **end_date**: Optional filter until this date (ISO 8601)
    - **limit**: Maximum number of results (1-1000)
    - **offset**: Pagination offset
    """
    try:
        # Parse optional filters
        parsed_action = None
        if action:
            try:
                parsed_action = AuditAction(action.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action type: {action}"
                )

        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format: {start_date}"
                )

        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.rstrip("Z"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_date format: {end_date}"
                )

        # Query logs for the entity
        logs = await audit_service.get_logs(
            entity_id=entity_id,
            action=parsed_action,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
        )

        log_responses = [AuditLogResponse(**entry.to_dict()) for entry in logs]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity audit logs: {str(e)}"
        )
