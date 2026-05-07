"""
Real-Time Collaboration Service for Basset Hound

Implements multi-user real-time collaboration features including:
- WebSocket-based entity synchronization
- Concurrent edit detection with conflict resolution (last-write-wins)
- Activity feed tracking (new entities, relationships, updates)
- Presence indicators (active users, viewing entities, cursor positions)
- Offline queue handling and reconnection sync

Phase 8, Stream 6: Real-Time Collaboration Features
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from api.services.neo4j_service import AsyncNeo4jService

logger = logging.getLogger(__name__)


class ActivityAction(str, Enum):
    """Types of activities that can be tracked."""
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_DELETED = "relationship_deleted"
    ENTITY_MERGED = "entity_merged"
    BULK_IMPORT = "bulk_import"


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving edit conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"


@dataclass
class EditConflict:
    """Represents a conflict between concurrent edits."""
    entity_id: str
    user_1: str
    user_2: str
    timestamp_1: str
    timestamp_2: str
    changes_1: Dict[str, Any]
    changes_2: Dict[str, Any]
    resolved: bool = False
    resolution_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    conflict_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "conflict_id": self.conflict_id,
            "entity_id": self.entity_id,
            "user_1": self.user_1,
            "user_2": self.user_2,
            "timestamp_1": self.timestamp_1,
            "timestamp_2": self.timestamp_2,
            "changes_1": self.changes_1,
            "changes_2": self.changes_2,
            "resolved": self.resolved,
            "resolution_strategy": self.resolution_strategy.value,
        }


@dataclass
class ActivityEvent:
    """Represents an activity event in the project."""
    project_id: str
    action: ActivityAction
    entity_id: Optional[str] = None
    relationship_id: Optional[str] = None
    user: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    activity_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "activity_id": self.activity_id,
            "project_id": self.project_id,
            "action": self.action.value,
            "timestamp": self.timestamp,
        }
        if self.entity_id:
            result["entity_id"] = self.entity_id
        if self.relationship_id:
            result["relationship_id"] = self.relationship_id
        if self.user:
            result["user"] = self.user
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class PresenceIndicator:
    """Indicates a user's presence in a project."""
    project_id: str
    user: str
    viewing_entity_id: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    connection_id: str = field(default_factory=lambda: str(uuid4()))
    is_editing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "user": self.user,
            "project_id": self.project_id,
            "connection_id": self.connection_id,
            "last_activity": self.last_activity,
            "is_editing": self.is_editing,
        }
        if self.viewing_entity_id:
            result["viewing_entity_id"] = self.viewing_entity_id
        if self.cursor_position:
            result["cursor_position"] = self.cursor_position
        return result

    def is_active(self, timeout_seconds: int = 300) -> bool:
        """Check if the user is still active (within timeout)."""
        last_activity_dt = datetime.fromisoformat(self.last_activity)
        return (datetime.now(timezone.utc) - last_activity_dt).total_seconds() < timeout_seconds


@dataclass
class SyncUpdate:
    """Represents a sync update for an entity."""
    entity_id: str
    project_id: str
    operation: str  # "create", "update", "delete"
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user: Optional[str] = None
    version: int = 1
    update_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "update_id": self.update_id,
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "operation": self.operation,
            "data": self.data,
            "timestamp": self.timestamp,
            "version": self.version,
        }
        if self.user:
            result["user"] = self.user
        return result


class CollaborationService:
    """
    Service for managing real-time collaboration features.

    Handles:
    - Entity synchronization across clients
    - Conflict detection and resolution
    - Activity feed management
    - Presence tracking
    - Offline queue management
    """

    def __init__(self):
        """Initialize the collaboration service."""
        self.neo4j = AsyncNeo4jService()
        # In-memory storage for active presence and conflicts
        self.presence: Dict[str, PresenceIndicator] = {}
        self.conflicts: Dict[str, EditConflict] = {}
        self.entity_locks: Dict[str, str] = {}  # entity_id -> user mapping
        self.offline_queue: Dict[str, List[SyncUpdate]] = {}  # user -> list of updates
        self.entity_versions: Dict[str, int] = {}  # entity_id -> version number

    async def initialize(self):
        """Initialize the Neo4j connection."""
        await self.neo4j.connect()

    async def close(self):
        """Close the Neo4j connection."""
        await self.neo4j.close()

    # ===== Real-Time Sync Layer =====

    async def broadcast_entity_update(
        self,
        project_id: str,
        entity_id: str,
        operation: str,
        data: Dict[str, Any],
        user: str,
    ) -> SyncUpdate:
        """
        Broadcast an entity update to all connected clients.

        Args:
            project_id: Project ID
            entity_id: Entity ID being updated
            operation: "create", "update", or "delete"
            data: Entity data
            user: User making the change

        Returns:
            SyncUpdate object with the broadcast information
        """
        current_version = self.entity_versions.get(entity_id, 0) + 1
        self.entity_versions[entity_id] = current_version

        update = SyncUpdate(
            entity_id=entity_id,
            project_id=project_id,
            operation=operation,
            data=data,
            user=user,
            version=current_version,
        )

        # Log the activity
        await self.log_activity(
            project_id=project_id,
            action=ActivityAction.ENTITY_CREATED if operation == "create" else ActivityAction.ENTITY_UPDATED,
            entity_id=entity_id,
            user=user,
            details={"operation": operation},
        )

        logger.info(
            f"broadcast_entity_update: entity_id={entity_id}, operation={operation}, version={current_version}, user={user}"
        )

        return update

    async def handle_offline_queue(self, user: str, project_id: str) -> List[SyncUpdate]:
        """
        Get pending updates from offline queue and sync on reconnection.

        Args:
            user: User reconnecting
            project_id: Project ID

        Returns:
            List of pending updates
        """
        queue_key = f"{user}:{project_id}"
        updates = self.offline_queue.get(queue_key, [])

        # Clear the queue after retrieval
        if queue_key in self.offline_queue:
            del self.offline_queue[queue_key]

        logger.info(
            f"offline_queue_synced: user={user}, project_id={project_id}, update_count={len(updates)}"
        )

        return updates

    async def queue_offline_update(
        self,
        user: str,
        project_id: str,
        entity_id: str,
        operation: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Queue an update for a user who is offline.

        Args:
            user: User ID
            project_id: Project ID
            entity_id: Entity ID
            operation: Operation type
            data: Update data
        """
        queue_key = f"{user}:{project_id}"
        if queue_key not in self.offline_queue:
            self.offline_queue[queue_key] = []

        update = SyncUpdate(
            entity_id=entity_id,
            project_id=project_id,
            operation=operation,
            data=data,
            user=user,
        )
        self.offline_queue[queue_key].append(update)

        logger.info(
            f"offline_update_queued: user={user}, project_id={project_id}, entity_id={entity_id}"
        )

    # ===== Concurrent Edit Detection & Conflict Resolution =====

    async def detect_concurrent_edit(
        self,
        entity_id: str,
        user: str,
        changes: Dict[str, Any],
    ) -> Optional[EditConflict]:
        """
        Detect if multiple users are editing the same entity.

        Args:
            entity_id: Entity ID
            user: Current user
            changes: Changes being made

        Returns:
            EditConflict if detected, None otherwise
        """
        if entity_id not in self.entity_locks:
            # Lock the entity for this user
            self.entity_locks[entity_id] = user
            return None

        # Check if locked by a different user
        lock_user = self.entity_locks[entity_id]
        if lock_user != user:
            # Concurrent edit detected - fetch the current state
            entity_data = await self._get_entity_data(entity_id)
            if entity_data:
                conflict = EditConflict(
                    entity_id=entity_id,
                    user_1=lock_user,
                    user_2=user,
                    timestamp_1=datetime.now(timezone.utc).isoformat(),
                    timestamp_2=datetime.now(timezone.utc).isoformat(),
                    changes_1={},  # Could be populated from lock info
                    changes_2=changes,
                )
                self.conflicts[conflict.conflict_id] = conflict
                logger.warning(
                    f"concurrent_edit_detected: entity_id={entity_id}, user_1={lock_user}, user_2={user}"
                )
                return conflict

        return None

    async def merge_concurrent_edits(
        self,
        conflict: EditConflict,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    ) -> Dict[str, Any]:
        """
        Merge updates from concurrent edits.

        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy

        Returns:
            Merged data
        """
        conflict.resolution_strategy = strategy
        merged_data = {}

        if strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Use timestamp to determine last write
            if conflict.timestamp_2 > conflict.timestamp_1:
                merged_data = conflict.changes_2
            else:
                merged_data = conflict.changes_1

        elif strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
            merged_data = conflict.changes_1

        elif strategy == ConflictResolutionStrategy.MERGE:
            # Merge non-conflicting changes
            merged_data = {**conflict.changes_1, **conflict.changes_2}

        conflict.resolved = True
        logger.info(
            f"conflict_resolved: conflict_id={conflict.conflict_id}, entity_id={conflict.entity_id}, strategy={strategy.value}"
        )

        return merged_data

    async def get_conflict(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Get conflict details by ID."""
        conflict = self.conflicts.get(conflict_id)
        if conflict:
            return conflict.to_dict()
        return None

    async def list_conflicts(self, project_id: str) -> List[Dict[str, Any]]:
        """List all active conflicts in a project."""
        return [
            c.to_dict()
            for c in self.conflicts.values()
            if not c.resolved
        ]

    # ===== Activity Feed =====

    async def log_activity(
        self,
        project_id: str,
        action: ActivityAction,
        entity_id: Optional[str] = None,
        relationship_id: Optional[str] = None,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ActivityEvent:
        """
        Log an activity event.

        Args:
            project_id: Project ID
            action: Activity action type
            entity_id: Entity ID (if applicable)
            relationship_id: Relationship ID (if applicable)
            user: User who triggered the activity
            details: Additional details

        Returns:
            ActivityEvent that was logged
        """
        activity = ActivityEvent(
            project_id=project_id,
            action=action,
            entity_id=entity_id,
            relationship_id=relationship_id,
            user=user,
            details=details or {},
        )

        # Store in Neo4j
        try:
            query = """
            CREATE (a:Activity {
                activity_id: $activity_id,
                project_id: $project_id,
                action: $action,
                entity_id: $entity_id,
                relationship_id: $relationship_id,
                user: $user,
                timestamp: $timestamp,
                details: $details
            })
            RETURN a
            """
            await self.neo4j.execute_query(
                query,
                activity_id=activity.activity_id,
                project_id=project_id,
                action=action.value,
                entity_id=entity_id,
                relationship_id=relationship_id,
                user=user,
                timestamp=activity.timestamp,
                details=json.dumps(activity.details),
            )
        except Exception as e:
            logger.error(f"failed_to_log_activity: {str(e)}")

        return activity

    async def get_activity_feed(
        self,
        project_id: str,
        limit: int = 100,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        entity_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get activity feed for a project.

        Args:
            project_id: Project ID
            limit: Maximum activities to return
            user_filter: Filter by user
            action_filter: Filter by action type
            entity_type_filter: Filter by entity type

        Returns:
            List of activity events
        """
        where_clauses = ["a.project_id = $project_id"]
        params = {"project_id": project_id}

        if user_filter:
            where_clauses.append("a.user = $user")
            params["user"] = user_filter

        if action_filter:
            where_clauses.append("a.action = $action")
            params["action"] = action_filter

        where_expr = " AND ".join(where_clauses)

        query = f"""
        MATCH (a:Activity)
        WHERE {where_expr}
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """
        params["limit"] = limit

        try:
            result = await self.neo4j.execute_query(query, **params)
            activities = []
            for record in result:
                activity_node = record[0]
                activity_data = dict(activity_node)
                activities.append(activity_data)
            return activities
        except Exception as e:
            logger.error(f"failed_to_get_activity_feed: {str(e)}")
            return []

    async def archive_old_activities(self, project_id: str, days: int = 30) -> int:
        """
        Archive activities older than specified days.

        Args:
            project_id: Project ID
            days: Archive activities older than this many days

        Returns:
            Number of activities archived
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = """
        MATCH (a:Activity {project_id: $project_id})
        WHERE a.timestamp < $cutoff_date
        SET a:ArchivedActivity
        RETURN count(a) as archived_count
        """

        try:
            result = await self.neo4j.execute_query(
                query,
                project_id=project_id,
                cutoff_date=cutoff_date,
            )
            if result:
                return result[0][0]
        except Exception as e:
            logger.error(f"failed_to_archive_activities: {str(e)}")

        return 0

    # ===== Presence Indicators =====

    async def update_presence(
        self,
        project_id: str,
        user: str,
        viewing_entity_id: Optional[str] = None,
        cursor_position: Optional[Dict[str, Any]] = None,
        is_editing: bool = False,
    ) -> PresenceIndicator:
        """
        Update user presence in a project.

        Args:
            project_id: Project ID
            user: User ID
            viewing_entity_id: Entity ID being viewed (optional)
            cursor_position: Cursor position info (optional)
            is_editing: Whether user is currently editing

        Returns:
            PresenceIndicator
        """
        presence_key = f"{project_id}:{user}"

        if presence_key in self.presence:
            indicator = self.presence[presence_key]
            indicator.last_activity = datetime.now(timezone.utc).isoformat()
            indicator.viewing_entity_id = viewing_entity_id
            indicator.cursor_position = cursor_position
            indicator.is_editing = is_editing
        else:
            indicator = PresenceIndicator(
                project_id=project_id,
                user=user,
                viewing_entity_id=viewing_entity_id,
                cursor_position=cursor_position,
                is_editing=is_editing,
            )
            self.presence[presence_key] = indicator

        return indicator

    async def get_active_users(
        self,
        project_id: str,
        timeout_seconds: int = 300,
    ) -> List[PresenceIndicator]:
        """
        Get all active users in a project.

        Args:
            project_id: Project ID
            timeout_seconds: User activity timeout

        Returns:
            List of active presence indicators
        """
        active_users = []
        for key, indicator in self.presence.items():
            if indicator.project_id == project_id and indicator.is_active(timeout_seconds):
                active_users.append(indicator)
        return active_users

    async def get_entity_viewers(self, entity_id: str) -> List[PresenceIndicator]:
        """
        Get all users currently viewing an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of presence indicators viewing this entity
        """
        viewers = []
        for indicator in self.presence.values():
            if indicator.viewing_entity_id == entity_id and indicator.is_active():
                viewers.append(indicator)
        return viewers

    async def remove_presence(self, project_id: str, user: str) -> bool:
        """
        Remove user presence (on disconnect).

        Args:
            project_id: Project ID
            user: User ID

        Returns:
            True if removed, False if not found
        """
        presence_key = f"{project_id}:{user}"
        if presence_key in self.presence:
            del self.presence[presence_key]
            logger.info(f"presence_removed: user={user}, project_id={project_id}")
            return True
        return False

    # ===== Helper Methods =====

    async def _get_entity_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity data from Neo4j."""
        query = """
        MATCH (e:Entity {entity_id: $entity_id})
        RETURN e
        """
        try:
            result = await self.neo4j.execute_query(query, entity_id=entity_id)
            if result:
                return dict(result[0][0])
        except Exception as e:
            logger.error(f"failed_to_get_entity_data: entity_id={entity_id}, error={str(e)}")
        return None

    async def release_entity_lock(self, entity_id: str, user: str) -> bool:
        """
        Release an entity lock held by a user.

        Args:
            entity_id: Entity ID
            user: User ID

        Returns:
            True if released, False if user didn't hold the lock
        """
        if self.entity_locks.get(entity_id) == user:
            del self.entity_locks[entity_id]
            logger.info(f"entity_lock_released: entity_id={entity_id}, user={user}")
            return True
        return False

    async def cleanup_stale_presence(self, timeout_seconds: int = 300) -> int:
        """
        Clean up stale presence indicators.

        Args:
            timeout_seconds: User activity timeout

        Returns:
            Number of stale indicators removed
        """
        stale_keys = [
            key
            for key, indicator in self.presence.items()
            if not indicator.is_active(timeout_seconds)
        ]

        for key in stale_keys:
            del self.presence[key]

        if stale_keys:
            logger.info(f"stale_presence_cleaned: count={len(stale_keys)}")

        return len(stale_keys)


# Global instance
_collaboration_service: Optional[CollaborationService] = None


def get_collaboration_service() -> CollaborationService:
    """Get or create the global collaboration service instance."""
    global _collaboration_service
    if _collaboration_service is None:
        _collaboration_service = CollaborationService()
    return _collaboration_service


async def initialize_collaboration_service():
    """Initialize the collaboration service."""
    service = get_collaboration_service()
    await service.initialize()
    return service
