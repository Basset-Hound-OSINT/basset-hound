"""
Audit Logging Service for Basset Hound

This module provides comprehensive audit logging for entity and project modifications.
It is part of Phase 14: Enterprise Features.

Features:
- Log CREATE, UPDATE, DELETE, LINK, UNLINK, VIEW actions
- Store timestamp, action, entity_type, entity_id, project_id, user_id, changes, ip_address
- In-memory storage with optional persistence interface
- Query methods for filtering logs by entity, project, action, and date range
- Thread-safe operations
- Singleton pattern for global access

Phase 14: Enterprise Features - Audit Logging
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Audit log action types."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LINK = "LINK"
    UNLINK = "UNLINK"
    VIEW = "VIEW"


class EntityType(str, Enum):
    """Types of entities that can be audited."""
    PROJECT = "PROJECT"
    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"
    FILE = "FILE"
    REPORT = "REPORT"
    TEMPLATE = "TEMPLATE"
    SCHEDULE = "SCHEDULE"


@dataclass
class AuditLogEntry:
    """
    Represents a single audit log entry.

    Attributes:
        id: Unique identifier for the log entry
        timestamp: ISO 8601 timestamp when the action occurred
        action: The type of action (CREATE, UPDATE, DELETE, etc.)
        entity_type: The type of entity affected
        entity_id: The unique identifier of the affected entity
        project_id: The project context (optional for global actions)
        user_id: The user who performed the action (optional)
        changes: JSON representation of what changed
        ip_address: IP address of the request origin (optional)
        metadata: Additional context information
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    action: AuditAction = AuditAction.VIEW
    entity_type: EntityType = EntityType.ENTITY
    entity_id: str = ""
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entry to a dictionary."""
        result = {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action.value if isinstance(self.action, AuditAction) else self.action,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else self.entity_type,
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "metadata": self.metadata,
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        """Create an AuditLogEntry from a dictionary."""
        # Handle action enum conversion
        action = data.get("action", AuditAction.VIEW)
        if isinstance(action, str):
            action = AuditAction(action)

        # Handle entity_type enum conversion
        entity_type = data.get("entity_type", EntityType.ENTITY)
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)

        return cls(
            id=data.get("id", str(uuid4())),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            action=action,
            entity_type=entity_type,
            entity_id=data.get("entity_id", ""),
            project_id=data.get("project_id"),
            user_id=data.get("user_id"),
            changes=data.get("changes"),
            ip_address=data.get("ip_address"),
            metadata=data.get("metadata"),
        )


class AuditPersistenceBackend(ABC):
    """Abstract base class for audit log persistence backends."""

    @abstractmethod
    async def save(self, entry: AuditLogEntry) -> bool:
        """Save an audit log entry."""
        pass

    @abstractmethod
    async def load_all(self) -> List[AuditLogEntry]:
        """Load all audit log entries."""
        pass

    @abstractmethod
    async def query(
        self,
        entity_id: Optional[str] = None,
        project_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """Query audit log entries with filters."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries. Returns count of deleted entries."""
        pass


class InMemoryAuditBackend(AuditPersistenceBackend):
    """
    In-memory implementation of the audit persistence backend.

    Suitable for development and testing. For production, consider
    implementing a database-backed persistence layer.
    """

    def __init__(self, max_entries: int = 10000):
        """
        Initialize the in-memory backend.

        Args:
            max_entries: Maximum number of entries to keep in memory.
                        Older entries are removed when limit is reached.
        """
        self._entries: List[AuditLogEntry] = []
        self._max_entries = max_entries
        self._lock = Lock()

    async def save(self, entry: AuditLogEntry) -> bool:
        """Save an audit log entry."""
        with self._lock:
            self._entries.append(entry)

            # Trim old entries if we exceed max
            if len(self._entries) > self._max_entries:
                # Remove oldest entries (first 10% of max)
                trim_count = self._max_entries // 10
                self._entries = self._entries[trim_count:]
                logger.debug(f"Trimmed {trim_count} old audit log entries")

            return True

    async def load_all(self) -> List[AuditLogEntry]:
        """Load all audit log entries."""
        with self._lock:
            return list(self._entries)

    async def query(
        self,
        entity_id: Optional[str] = None,
        project_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """Query audit log entries with filters."""
        with self._lock:
            results = []

            for entry in self._entries:
                # Apply filters
                if entity_id and entry.entity_id != entity_id:
                    continue
                if project_id and entry.project_id != project_id:
                    continue
                if action and entry.action != action:
                    continue
                if entity_type and entry.entity_type != entity_type:
                    continue
                if user_id and entry.user_id != user_id:
                    continue

                # Date filtering
                if start_date or end_date:
                    entry_time = datetime.fromisoformat(entry.timestamp.rstrip("Z"))

                    if start_date and entry_time < start_date:
                        continue
                    if end_date and entry_time > end_date:
                        continue

                results.append(entry)

            # Sort by timestamp descending (most recent first)
            results.sort(key=lambda x: x.timestamp, reverse=True)

            # Apply pagination
            return results[offset:offset + limit]

    async def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._entries)
            self._entries = []
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the audit log storage."""
        with self._lock:
            action_counts = {}
            entity_type_counts = {}

            for entry in self._entries:
                # Count by action
                action_key = entry.action.value if isinstance(entry.action, AuditAction) else entry.action
                action_counts[action_key] = action_counts.get(action_key, 0) + 1

                # Count by entity type
                type_key = entry.entity_type.value if isinstance(entry.entity_type, EntityType) else entry.entity_type
                entity_type_counts[type_key] = entity_type_counts.get(type_key, 0) + 1

            return {
                "total_entries": len(self._entries),
                "max_entries": self._max_entries,
                "action_counts": action_counts,
                "entity_type_counts": entity_type_counts,
            }


class AuditLogger:
    """
    Main audit logging service.

    Provides methods for logging various entity and project modifications
    with support for custom persistence backends.

    Example usage:
        audit = get_audit_logger()
        await audit.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            project_id="project-456",
            changes={"profile": {"name": "John Doe"}},
            user_id="user-789",
            ip_address="192.168.1.1"
        )
    """

    def __init__(
        self,
        backend: Optional[AuditPersistenceBackend] = None,
        enabled: bool = True,
        log_views: bool = False,
        max_entries: int = 10000,
    ):
        """
        Initialize the AuditLogger.

        Args:
            backend: Optional persistence backend. Defaults to InMemoryAuditBackend.
            enabled: Whether audit logging is enabled.
            log_views: Whether to log VIEW actions (can be noisy).
            max_entries: Maximum entries for in-memory backend.
        """
        self._backend = backend or InMemoryAuditBackend(max_entries=max_entries)
        self._enabled = enabled
        self._log_views = log_views
        self._listeners: List[Callable[[AuditLogEntry], None]] = []
        self._lock = Lock()

    @property
    def is_enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable audit logging."""
        self._enabled = True

    def disable(self) -> None:
        """Disable audit logging."""
        self._enabled = False

    def add_listener(self, listener: Callable[[AuditLogEntry], None]) -> None:
        """
        Add a listener that will be called for each new audit entry.

        Args:
            listener: A callable that takes an AuditLogEntry as argument.
        """
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[AuditLogEntry], None]) -> None:
        """Remove a previously added listener."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    async def _log_entry(self, entry: AuditLogEntry) -> Optional[AuditLogEntry]:
        """
        Internal method to log an entry.

        Returns the logged entry or None if logging is disabled.
        """
        if not self._enabled:
            return None

        # Skip VIEW actions if not configured to log them
        if entry.action == AuditAction.VIEW and not self._log_views:
            return None

        # Save to backend
        success = await self._backend.save(entry)

        if success:
            logger.debug(
                f"Audit log: {entry.action.value} {entry.entity_type.value} "
                f"{entry.entity_id} in project {entry.project_id}"
            )

            # Notify listeners
            with self._lock:
                listeners = list(self._listeners)

            for listener in listeners:
                try:
                    listener(entry)
                except Exception as e:
                    logger.error(f"Audit listener error: {e}")

            return entry

        return None

    async def log(
        self,
        action: AuditAction,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """
        Log an audit event.

        Args:
            action: The type of action being performed.
            entity_type: The type of entity being affected.
            entity_id: The unique identifier of the entity.
            project_id: The project context (optional).
            user_id: The user performing the action (optional).
            changes: Dictionary of changes made (optional).
            ip_address: The origin IP address (optional).
            metadata: Additional context (optional).

        Returns:
            The created AuditLogEntry or None if logging is disabled.
        """
        entry = AuditLogEntry(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            metadata=metadata,
        )

        return await self._log_entry(entry)

    # ==================== Convenience Methods ====================

    async def log_create(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a CREATE action."""
        return await self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            changes=changes,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_update(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an UPDATE action."""
        return await self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            changes=changes,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_delete(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a DELETE action."""
        return await self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            changes=changes,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_link(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a LINK action (creating a relationship)."""
        changes = {
            "target_entity_id": target_entity_id,
            "relationship_type": relationship_type,
        }
        return await self.log(
            action=AuditAction.LINK,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            changes=changes,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_unlink(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an UNLINK action (removing a relationship)."""
        changes = {
            "target_entity_id": target_entity_id,
            "relationship_type": relationship_type,
        }
        return await self.log(
            action=AuditAction.UNLINK,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            changes=changes,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_view(
        self,
        entity_type: EntityType,
        entity_id: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a VIEW action."""
        return await self.log(
            action=AuditAction.VIEW,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
        )

    # ==================== Query Methods ====================

    async def get_logs_by_entity(
        self,
        entity_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get audit logs for a specific entity.

        Args:
            entity_id: The entity ID to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching AuditLogEntry objects.
        """
        return await self._backend.query(
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )

    async def get_logs_by_project(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get audit logs for a specific project.

        Args:
            project_id: The project ID to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching AuditLogEntry objects.
        """
        return await self._backend.query(
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

    async def get_logs_by_action(
        self,
        action: AuditAction,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get audit logs for a specific action type.

        Args:
            action: The action type to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching AuditLogEntry objects.
        """
        return await self._backend.query(
            action=action,
            limit=limit,
            offset=offset,
        )

    async def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get audit logs within a date range.

        Args:
            start_date: The start of the date range.
            end_date: The end of the date range (defaults to now).
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching AuditLogEntry objects.
        """
        if end_date is None:
            end_date = datetime.utcnow()

        return await self._backend.query(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_logs(
        self,
        entity_id: Optional[str] = None,
        project_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get audit logs with flexible filtering.

        Args:
            entity_id: Filter by entity ID.
            project_id: Filter by project ID.
            action: Filter by action type.
            entity_type: Filter by entity type.
            user_id: Filter by user ID.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching AuditLogEntry objects.
        """
        return await self._backend.query(
            entity_id=entity_id,
            project_id=project_id,
            action=action,
            entity_type=entity_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_all_logs(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        Get all audit logs with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of AuditLogEntry objects.
        """
        return await self._backend.query(limit=limit, offset=offset)

    async def clear_logs(self) -> int:
        """
        Clear all audit logs.

        Returns:
            Number of entries cleared.
        """
        count = await self._backend.clear()
        logger.info(f"Cleared {count} audit log entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the audit logs.

        Returns:
            Dictionary with statistics.
        """
        if isinstance(self._backend, InMemoryAuditBackend):
            return self._backend.get_stats()

        return {
            "enabled": self._enabled,
            "log_views": self._log_views,
            "backend_type": type(self._backend).__name__,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the audit logger.

        Returns:
            Health status dictionary.
        """
        try:
            # Try to create and save a test entry
            test_entry = AuditLogEntry(
                action=AuditAction.VIEW,
                entity_type=EntityType.PROJECT,
                entity_id="health-check",
                metadata={"type": "health_check"},
            )

            # We don't actually save the health check, just verify the backend is accessible
            all_logs = await self._backend.query(limit=1)

            return {
                "status": "healthy",
                "enabled": self._enabled,
                "backend_type": type(self._backend).__name__,
                "has_entries": len(all_logs) > 0,
            }
        except Exception as e:
            logger.error(f"Audit logger health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# ==================== Singleton Instance ====================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(
    backend: Optional[AuditPersistenceBackend] = None,
    enabled: bool = True,
    log_views: bool = False,
    max_entries: int = 10000,
) -> AuditLogger:
    """
    Get or create the audit logger singleton.

    Args:
        backend: Optional persistence backend.
        enabled: Whether audit logging is enabled.
        log_views: Whether to log VIEW actions.
        max_entries: Maximum entries for in-memory backend.

    Returns:
        The AuditLogger instance.
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger(
            backend=backend,
            enabled=enabled,
            log_views=log_views,
            max_entries=max_entries,
        )

    return _audit_logger


def set_audit_logger(audit_logger: Optional[AuditLogger]) -> None:
    """
    Set the audit logger singleton.

    Args:
        audit_logger: The AuditLogger instance to use, or None to clear.
    """
    global _audit_logger
    _audit_logger = audit_logger


async def initialize_audit_logger(
    backend: Optional[AuditPersistenceBackend] = None,
    enabled: bool = True,
    log_views: bool = False,
    max_entries: int = 10000,
) -> AuditLogger:
    """
    Initialize and return the audit logger.

    This is a convenience function that gets the singleton and
    performs any necessary initialization.

    Args:
        backend: Optional persistence backend.
        enabled: Whether audit logging is enabled.
        log_views: Whether to log VIEW actions.
        max_entries: Maximum entries for in-memory backend.

    Returns:
        The initialized AuditLogger.
    """
    audit = get_audit_logger(
        backend=backend,
        enabled=enabled,
        log_views=log_views,
        max_entries=max_entries,
    )

    logger.info(f"Audit logger initialized (enabled={enabled}, log_views={log_views})")

    return audit
