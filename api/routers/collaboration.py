"""
Real-Time Collaboration Router for Basset Hound

Provides REST API endpoints for real-time collaboration features:
- Entity synchronization
- Conflict detection and resolution
- Activity feed querying
- Presence indicators
- Offline queue management

Phase 8, Stream 6: Real-Time Collaboration Features
Phase 8, Security Fix: Activity Feed User Verification
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path, Query, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel

from api.services.collaboration_service import (
    get_collaboration_service,
    CollaborationService,
    ActivityAction,
    ConflictResolutionStrategy,
)
from api.auth.dependencies import CurrentUser, get_current_user
from api.services.audit_logger import get_audit_logger, AuditAction, EntityType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])


# ===== Pydantic Models =====

class EntityUpdateRequest(BaseModel):
    """Request to update an entity with sync."""
    entity_id: str
    operation: str  # "create", "update", "delete"
    data: Dict[str, Any]
    user: str


class ActivityFilterRequest(BaseModel):
    """Request to filter activity feed."""
    limit: int = 100
    user_filter: Optional[str] = None
    action_filter: Optional[str] = None
    entity_type_filter: Optional[str] = None


class PresenceUpdateRequest(BaseModel):
    """Request to update user presence."""
    user: str
    viewing_entity_id: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None
    is_editing: bool = False


class ConflictResolutionRequest(BaseModel):
    """Request to resolve a conflict."""
    conflict_id: str
    strategy: str = "last_write_wins"


# ===== Sync Endpoints =====

@router.post("/projects/{project_id}/sync/update", tags=["Sync"])
async def broadcast_entity_update(
    project_id: str,
    request: EntityUpdateRequest,
    current_user: CurrentUser,
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Broadcast an entity update to all connected clients.

    This endpoint handles real-time synchronization of entity changes across
    all connected WebSocket clients. Implements version tracking and conflict
    detection.

    Security: Validates that the user parameter matches the authenticated user.

    Args:
        project_id: Project ID
        request: Update request with entity data
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        Update confirmation with version number

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
    """
    try:
        # SECURITY FIX: Verify user identity
        if request.user != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.UPDATE,
                entity_type=EntityType.ENTITY,
                entity_id=request.entity_id,
                project_id=project_id,
                changes={
                    "verification_failure": "user_mismatch_on_sync",
                    "authenticated_user": current_user.user_id,
                    "requested_user": request.user,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "sync_update_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "sync_update_user_verification_failed",
                authenticated_user=current_user.user_id,
                requested_user=request.user,
                project_id=project_id,
                entity_id=request.entity_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot sync as another user",
            )

        update = await service.broadcast_entity_update(
            project_id=project_id,
            entity_id=request.entity_id,
            operation=request.operation,
            data=request.data,
            user=request.user,
        )

        logger.info(
            "entity_update_broadcast",
            project_id=project_id,
            entity_id=request.entity_id,
            user=request.user,
            operation=request.operation,
        )

        return {
            "success": True,
            "update_id": update.update_id,
            "entity_id": update.entity_id,
            "version": update.version,
            "timestamp": update.timestamp,
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_broadcast_update", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast entity update",
        )


@router.post("/users/{user_id}/sync/reconnect", tags=["Sync"])
async def sync_on_reconnection(
    user_id: str,
    current_user: CurrentUser,
    project_id: str = Query(..., description="Project ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Sync offline queue when user reconnects.

    Retrieves all pending updates from the offline queue and synchronizes them
    with the newly reconnected client.

    Security: Validates that user_id in path matches authenticated user.

    Args:
        user_id: User ID
        project_id: Project ID
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        List of pending updates

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
    """
    try:
        # SECURITY FIX: Verify that path user_id matches authenticated user
        if user_id != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.VIEW,
                entity_type=EntityType.ENTITY,
                entity_id="offline_queue",
                project_id=project_id,
                changes={
                    "verification_failure": "user_id_mismatch_in_reconnect",
                    "authenticated_user": current_user.user_id,
                    "path_user_id": user_id,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "reconnection_sync_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "reconnection_sync_user_verification_failed",
                authenticated_user=current_user.user_id,
                path_user_id=user_id,
                project_id=project_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot sync for another user",
            )

        updates = await service.handle_offline_queue(user_id, project_id)

        logger.info(
            "reconnection_sync_completed",
            user_id=user_id,
            project_id=project_id,
            update_count=len(updates),
        )

        return {
            "success": True,
            "updates": [u.to_dict() for u in updates],
            "count": len(updates),
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_sync_on_reconnection", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync on reconnection",
        )


@router.post("/users/{user_id}/queue/offline", tags=["Sync"])
async def queue_offline_update(
    user_id: str,
    request: EntityUpdateRequest,
    current_user: CurrentUser,
    project_id: str = Query(..., description="Project ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Queue an update for an offline user.

    Used when a user is offline and sends updates. The updates are queued
    and will be synced when they reconnect.

    Security: Validates that user_id in path matches authenticated user.

    Args:
        user_id: User ID
        project_id: Project ID
        request: Update request
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        Confirmation of queued update

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
    """
    try:
        # SECURITY FIX: Verify that path user_id matches authenticated user
        if user_id != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.UPDATE,
                entity_type=EntityType.ENTITY,
                entity_id=request.entity_id,
                project_id=project_id,
                changes={
                    "verification_failure": "user_id_mismatch_in_path",
                    "authenticated_user": current_user.user_id,
                    "path_user_id": user_id,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "offline_queue_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "offline_queue_user_verification_failed",
                authenticated_user=current_user.user_id,
                path_user_id=user_id,
                project_id=project_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot queue updates for another user",
            )

        await service.queue_offline_update(
            user=user_id,
            project_id=project_id,
            entity_id=request.entity_id,
            operation=request.operation,
            data=request.data,
        )

        logger.info(
            "offline_update_queued",
            user_id=user_id,
            project_id=project_id,
            entity_id=request.entity_id,
        )

        return {
            "success": True,
            "queued": True,
            "message": f"Update queued for user {user_id}",
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_queue_offline_update", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue offline update",
        )


# ===== Conflict Detection & Resolution Endpoints =====

@router.post("/projects/{project_id}/conflicts/detect", tags=["Conflicts"])
async def detect_concurrent_edit(
    project_id: str,
    request: EntityUpdateRequest,
    current_user: CurrentUser,
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Detect if multiple users are editing the same entity.

    Checks for concurrent edits and returns conflict information if detected.

    Security: Validates that the user parameter matches the authenticated user.

    Args:
        project_id: Project ID
        request: Update request
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        Conflict details if detected, else empty

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
    """
    try:
        # SECURITY FIX: Verify user identity
        if request.user != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.UPDATE,
                entity_type=EntityType.ENTITY,
                entity_id=request.entity_id,
                project_id=project_id,
                changes={
                    "verification_failure": "user_mismatch_on_conflict_detect",
                    "authenticated_user": current_user.user_id,
                    "requested_user": request.user,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "conflict_detect_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "conflict_detect_user_verification_failed",
                authenticated_user=current_user.user_id,
                requested_user=request.user,
                project_id=project_id,
                entity_id=request.entity_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot detect conflicts as another user",
            )

        conflict = await service.detect_concurrent_edit(
            entity_id=request.entity_id,
            user=request.user,
            changes=request.data,
        )

        if conflict:
            logger.info(
                "concurrent_edit_conflict_detected",
                project_id=project_id,
                entity_id=request.entity_id,
                user=request.user,
                conflict_id=conflict.conflict_id,
            )
            return {
                "success": True,
                "conflict_detected": True,
                "conflict": conflict.to_dict(),
            }
        else:
            return {
                "success": True,
                "conflict_detected": False,
            }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_detect_conflict", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect conflict",
        )


@router.post("/projects/{project_id}/conflicts/resolve", tags=["Conflicts"])
async def resolve_conflict(
    project_id: str,
    request: ConflictResolutionRequest,
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Resolve a conflict using specified strategy.

    Supports multiple resolution strategies:
    - last_write_wins: Use the most recent change
    - first_write_wins: Keep the first change
    - merge: Merge non-conflicting changes

    Args:
        project_id: Project ID
        request: Resolution request
        service: Collaboration service instance

    Returns:
        Resolved data and strategy used
    """
    try:
        conflict = service.conflicts.get(request.conflict_id)
        if not conflict:
            return {
                "success": False,
                "error": "Conflict not found",
            }

        strategy = ConflictResolutionStrategy(request.strategy)
        merged_data = await service.merge_concurrent_edits(conflict, strategy)

        return {
            "success": True,
            "conflict_id": request.conflict_id,
            "merged_data": merged_data,
            "strategy": request.strategy,
        }
    except Exception as e:
        logger.error("failed_to_resolve_conflict", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/projects/{project_id}/conflicts", tags=["Conflicts"])
async def list_conflicts(
    project_id: str = Path(..., description="Project ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    List all active conflicts in a project.

    Args:
        project_id: Project ID
        service: Collaboration service instance

    Returns:
        List of active conflicts
    """
    try:
        conflicts = await service.list_conflicts(project_id)

        return {
            "success": True,
            "conflicts": conflicts,
            "count": len(conflicts),
        }
    except Exception as e:
        logger.error("failed_to_list_conflicts", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/conflicts/{conflict_id}", tags=["Conflicts"])
async def get_conflict(
    conflict_id: str = Path(..., description="Conflict ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Get details about a specific conflict.

    Args:
        conflict_id: Conflict ID
        service: Collaboration service instance

    Returns:
        Conflict details
    """
    try:
        conflict = await service.get_conflict(conflict_id)

        if conflict:
            return {
                "success": True,
                "conflict": conflict,
            }
        else:
            return {
                "success": False,
                "error": "Conflict not found",
            }
    except Exception as e:
        logger.error("failed_to_get_conflict", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


# ===== Activity Feed Endpoints =====

@router.post("/projects/{project_id}/activity/log", tags=["Activity"])
async def log_activity(
    project_id: str,
    current_user: CurrentUser,
    action: str = Query(..., description="Activity action"),
    entity_id: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    details: Optional[Dict[str, Any]] = None,
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Log an activity event.

    Security: Validates that the user parameter matches the authenticated user.
    Prevents audit trail forgery by ensuring users can only log activities as themselves.

    Args:
        project_id: Project ID
        action: Activity action type
        entity_id: Entity ID (optional)
        user: User who triggered activity
        details: Additional details
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        Activity event that was logged

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
        HTTPException: If invalid action type (400 Bad Request)
    """
    try:
        # SECURITY FIX: Verify that the user parameter matches the authenticated user
        # This prevents users from logging activities as other users (audit trail forgery)
        if user and user != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.UPDATE,
                entity_type=EntityType.ENTITY,
                entity_id=entity_id or "unknown",
                project_id=project_id,
                changes={
                    "verification_failure": "user_mismatch",
                    "authenticated_user": current_user.user_id,
                    "requested_user": user,
                    "action": action,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "activity_feed_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "activity_feed_user_verification_failed",
                authenticated_user=current_user.user_id,
                requested_user=user,
                project_id=project_id,
                action=action,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot log activity as another user",
            )

        # Use authenticated user ID if no user provided
        activity_user = user or current_user.user_id

        activity_action = ActivityAction(action)
        activity = await service.log_activity(
            project_id=project_id,
            action=activity_action,
            entity_id=entity_id,
            user=activity_user,
            details=details or {},
        )

        logger.info(
            "activity_logged",
            project_id=project_id,
            user=activity_user,
            action=action,
            entity_id=entity_id,
        )

        return {
            "success": True,
            "activity": activity.to_dict(),
        }
    except ValueError as e:
        logger.warning(
            "invalid_activity_action",
            action=action,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}",
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_log_activity", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log activity",
        )


@router.get("/projects/{project_id}/activity/feed", tags=["Activity"])
async def get_activity_feed(
    project_id: str = Path(..., description="Project ID"),
    limit: int = Query(100, ge=1, le=1000),
    user_filter: Optional[str] = Query(None),
    action_filter: Optional[str] = Query(None),
    entity_type_filter: Optional[str] = Query(None),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Get activity feed for a project.

    Supports filtering by:
    - user: Specific user who triggered activities
    - action: Activity action type
    - entity_type: Type of entity involved

    Args:
        project_id: Project ID
        limit: Maximum activities to return (1-1000, default 100)
        user_filter: Filter by user
        action_filter: Filter by action type
        entity_type_filter: Filter by entity type
        service: Collaboration service instance

    Returns:
        List of activity events
    """
    try:
        activities = await service.get_activity_feed(
            project_id=project_id,
            limit=limit,
            user_filter=user_filter,
            action_filter=action_filter,
            entity_type_filter=entity_type_filter,
        )

        return {
            "success": True,
            "activities": activities,
            "count": len(activities),
        }
    except Exception as e:
        logger.error("failed_to_get_activity_feed", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/projects/{project_id}/activity/archive", tags=["Activity"])
async def archive_activities(
    project_id: str = Path(..., description="Project ID"),
    days: int = Query(30, ge=1),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Archive old activities in a project.

    Activities older than the specified number of days will be marked as archived.

    Args:
        project_id: Project ID
        days: Archive activities older than this many days
        service: Collaboration service instance

    Returns:
        Number of activities archived
    """
    try:
        archived_count = await service.archive_old_activities(project_id, days)

        return {
            "success": True,
            "archived_count": archived_count,
            "days": days,
        }
    except Exception as e:
        logger.error("failed_to_archive_activities", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


# ===== Presence Indicator Endpoints =====

@router.post("/projects/{project_id}/presence/update", tags=["Presence"])
async def update_presence(
    project_id: str,
    current_user: CurrentUser,
    request: PresenceUpdateRequest,
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Update user presence in a project.

    Tracks which users are active, what entities they're viewing, and if they're editing.

    Security: Validates that the user parameter matches the authenticated user.

    Args:
        project_id: Project ID
        request: Presence update request
        current_user: Authenticated user from JWT/API key
        service: Collaboration service instance

    Returns:
        Updated presence indicator

    Raises:
        HTTPException: If user verification fails (403 Forbidden)
    """
    try:
        # SECURITY FIX: Verify that request user matches authenticated user
        if request.user != current_user.user_id:
            audit_logger = get_audit_logger()
            await audit_logger.log(
                action=AuditAction.UPDATE,
                entity_type=EntityType.ENTITY,
                entity_id=request.viewing_entity_id or "unknown",
                project_id=project_id,
                changes={
                    "verification_failure": "user_mismatch_on_presence_update",
                    "authenticated_user": current_user.user_id,
                    "requested_user": request.user,
                },
                metadata={
                    "security_event": True,
                    "verification_type": "presence_update_user_verification",
                    "severity": "medium",
                }
            )
            logger.warning(
                "presence_update_user_verification_failed",
                authenticated_user=current_user.user_id,
                requested_user=request.user,
                project_id=project_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User verification failed: cannot update presence for another user",
            )

        indicator = await service.update_presence(
            project_id=project_id,
            user=request.user,
            viewing_entity_id=request.viewing_entity_id,
            cursor_position=request.cursor_position,
            is_editing=request.is_editing,
        )

        logger.debug(
            "presence_updated",
            project_id=project_id,
            user=request.user,
            viewing_entity_id=request.viewing_entity_id,
            is_editing=request.is_editing,
        )

        return {
            "success": True,
            "presence": indicator.to_dict(),
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("failed_to_update_presence", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update presence",
        )


@router.get("/projects/{project_id}/presence/active-users", tags=["Presence"])
async def get_active_users(
    project_id: str = Path(..., description="Project ID"),
    timeout_seconds: int = Query(300, ge=1),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Get all active users in a project.

    Returns users who have been active within the specified timeout period.

    Args:
        project_id: Project ID
        timeout_seconds: User activity timeout (default 300s)
        service: Collaboration service instance

    Returns:
        List of active users with their presence info
    """
    try:
        users = await service.get_active_users(project_id, timeout_seconds)

        return {
            "success": True,
            "active_users": [u.to_dict() for u in users],
            "count": len(users),
        }
    except Exception as e:
        logger.error("failed_to_get_active_users", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/entities/{entity_id}/presence/viewers", tags=["Presence"])
async def get_entity_viewers(
    entity_id: str = Path(..., description="Entity ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Get all users currently viewing an entity.

    Shows "edited by X" indicators and helps prevent conflicts.

    Args:
        entity_id: Entity ID
        service: Collaboration service instance

    Returns:
        List of users viewing this entity
    """
    try:
        viewers = await service.get_entity_viewers(entity_id)

        return {
            "success": True,
            "viewers": [v.to_dict() for v in viewers],
            "count": len(viewers),
        }
    except Exception as e:
        logger.error("failed_to_get_entity_viewers", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/projects/{project_id}/presence/remove", tags=["Presence"])
async def remove_presence(
    project_id: str = Path(..., description="Project ID"),
    user: str = Query(..., description="User ID"),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Remove user presence (on disconnect).

    Called when a user disconnects from the project.

    Args:
        project_id: Project ID
        user: User ID
        service: Collaboration service instance

    Returns:
        Confirmation of removal
    """
    try:
        removed = await service.remove_presence(project_id, user)

        return {
            "success": True,
            "removed": removed,
            "user": user,
            "project_id": project_id,
        }
    except Exception as e:
        logger.error("failed_to_remove_presence", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/projects/{project_id}/presence/cleanup", tags=["Presence"])
async def cleanup_stale_presence(
    project_id: str = Path(..., description="Project ID"),
    timeout_seconds: int = Query(300, ge=1),
    service: CollaborationService = Depends(get_collaboration_service),
) -> Dict[str, Any]:
    """
    Clean up stale presence indicators.

    Removes presence indicators for users who haven't been active within the timeout period.

    Args:
        project_id: Project ID
        timeout_seconds: Activity timeout (default 300s)
        service: Collaboration service instance

    Returns:
        Number of stale indicators removed
    """
    try:
        removed_count = await service.cleanup_stale_presence(timeout_seconds)

        return {
            "success": True,
            "removed_count": removed_count,
            "timeout_seconds": timeout_seconds,
        }
    except Exception as e:
        logger.error("failed_to_cleanup_presence", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


# ===== WebSocket Endpoint =====

@router.websocket("/ws/projects/{project_id}")
async def websocket_collaboration_endpoint(
    websocket: WebSocket,
    project_id: str,
    user: str = Query(..., description="User ID"),
    service: CollaborationService = Depends(get_collaboration_service),
):
    """
    WebSocket endpoint for real-time collaboration.

    Handles real-time updates, presence changes, and activity broadcasts.

    Security: The user parameter is passed as query parameter. For WebSocket connections,
    authentication should be handled at the connection level by the client providing
    valid JWT token. This endpoint trusts the user parameter but logs all activities
    for audit purposes.

    Args:
        websocket: WebSocket connection
        project_id: Project ID
        user: User ID
        service: Collaboration service instance

    Note:
        WebSocket authentication in FastAPI is limited by the protocol.
        For production: Implement token validation before accepting the connection
        or use custom authentication middleware.
    """
    await websocket.accept()
    logger.info("collaboration_websocket_connected", project_id=project_id, user=user)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "presence":
                # Update presence
                indicator = await service.update_presence(
                    project_id=project_id,
                    user=user,
                    viewing_entity_id=data.get("viewing_entity_id"),
                    cursor_position=data.get("cursor_position"),
                    is_editing=data.get("is_editing", False),
                )
                await websocket.send_json({
                    "type": "presence_updated",
                    "presence": indicator.to_dict(),
                })

            elif message_type == "sync":
                # Broadcast entity update
                try:
                    update = await service.broadcast_entity_update(
                        project_id=project_id,
                        entity_id=data.get("entity_id"),
                        operation=data.get("operation"),
                        data=data.get("data"),
                        user=user,
                    )
                    await websocket.send_json({
                        "type": "sync_confirmed",
                        "update": update.to_dict(),
                    })
                except Exception as sync_error:
                    logger.error("websocket_sync_error", error=str(sync_error))
                    await websocket.send_json({
                        "type": "error",
                        "error": "Failed to broadcast sync",
                    })

            elif message_type == "activity":
                # Log activity
                try:
                    activity_action = ActivityAction(data.get("action"))
                    activity = await service.log_activity(
                        project_id=project_id,
                        action=activity_action,
                        entity_id=data.get("entity_id"),
                        user=user,
                        details=data.get("details"),
                    )
                    await websocket.send_json({
                        "type": "activity_logged",
                        "activity": activity.to_dict(),
                    })
                except ValueError:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Invalid action: {data.get('action')}",
                    })
                except Exception as activity_error:
                    logger.error("websocket_activity_error", error=str(activity_error))
                    await websocket.send_json({
                        "type": "error",
                        "error": "Failed to log activity",
                    })

            elif message_type == "ping":
                # Respond to ping with graceful error handling
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception as ping_error:
                    logger.warning("failed_to_send_pong", error=str(ping_error))

            elif message_type == "pong":
                # Client responding to our heartbeat
                logger.debug("pong_received_from_client", user=user)

    except WebSocketDisconnect:
        # Remove presence on disconnect
        await service.remove_presence(project_id, user)
        logger.info("collaboration_websocket_disconnected", project_id=project_id, user=user)

    except Exception as e:
        logger.error("collaboration_websocket_error", error=str(e), exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": "Internal server error",
            })
        except Exception:
            pass
