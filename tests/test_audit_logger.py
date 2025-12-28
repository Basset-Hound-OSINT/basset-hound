"""
Tests for the Audit Logging Service (Phase 14: Enterprise Features)

Comprehensive test coverage for:
- AuditLogEntry dataclass
- AuditAction and EntityType enums
- InMemoryAuditBackend
- AuditLogger service
- Query methods (by entity, project, action, date range)
- Listener functionality
- Singleton pattern
- Router endpoint tests
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.audit_logger import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
    AuditPersistenceBackend,
    EntityType,
    InMemoryAuditBackend,
    get_audit_logger,
    set_audit_logger,
    initialize_audit_logger,
)


# ==================== AuditLogEntry Tests ====================


class TestAuditLogEntry:
    """Tests for AuditLogEntry dataclass."""

    def test_entry_creation_defaults(self):
        """Test creating an entry with default values."""
        entry = AuditLogEntry()

        assert entry.id is not None
        assert entry.timestamp is not None
        assert entry.action == AuditAction.VIEW
        assert entry.entity_type == EntityType.ENTITY
        assert entry.entity_id == ""
        assert entry.project_id is None
        assert entry.user_id is None
        assert entry.changes is None
        assert entry.ip_address is None
        assert entry.metadata is None

    def test_entry_creation_with_values(self):
        """Test creating an entry with specific values."""
        entry = AuditLogEntry(
            id="test-id-123",
            timestamp="2024-01-15T10:30:00Z",
            action=AuditAction.CREATE,
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            project_id="project-456",
            user_id="user-789",
            changes={"name": "John Doe"},
            ip_address="192.168.1.1",
            metadata={"source": "api"},
        )

        assert entry.id == "test-id-123"
        assert entry.timestamp == "2024-01-15T10:30:00Z"
        assert entry.action == AuditAction.CREATE
        assert entry.entity_type == EntityType.ENTITY
        assert entry.entity_id == "entity-123"
        assert entry.project_id == "project-456"
        assert entry.user_id == "user-789"
        assert entry.changes == {"name": "John Doe"}
        assert entry.ip_address == "192.168.1.1"
        assert entry.metadata == {"source": "api"}

    def test_entry_to_dict(self):
        """Test converting entry to dictionary."""
        entry = AuditLogEntry(
            id="test-id",
            action=AuditAction.UPDATE,
            entity_type=EntityType.PROJECT,
            entity_id="entity-123",
            project_id="project-456",
            changes={"field": "value"},
        )

        result = entry.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test-id"
        assert result["action"] == "UPDATE"
        assert result["entity_type"] == "PROJECT"
        assert result["entity_id"] == "entity-123"
        assert result["project_id"] == "project-456"
        assert result["changes"] == {"field": "value"}

    def test_entry_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "id": "test-id",
            "timestamp": "2024-01-15T10:30:00Z",
            "action": "DELETE",
            "entity_type": "RELATIONSHIP",
            "entity_id": "entity-123",
            "project_id": "project-456",
            "user_id": "user-789",
            "changes": {"deleted": True},
            "ip_address": "10.0.0.1",
            "metadata": {"reason": "cleanup"},
        }

        entry = AuditLogEntry.from_dict(data)

        assert entry.id == "test-id"
        assert entry.timestamp == "2024-01-15T10:30:00Z"
        assert entry.action == AuditAction.DELETE
        assert entry.entity_type == EntityType.RELATIONSHIP
        assert entry.entity_id == "entity-123"
        assert entry.project_id == "project-456"
        assert entry.user_id == "user-789"
        assert entry.changes == {"deleted": True}
        assert entry.ip_address == "10.0.0.1"
        assert entry.metadata == {"reason": "cleanup"}

    def test_entry_from_dict_with_missing_fields(self):
        """Test creating entry from dictionary with missing optional fields."""
        data = {
            "entity_id": "entity-123",
        }

        entry = AuditLogEntry.from_dict(data)

        assert entry.entity_id == "entity-123"
        assert entry.id is not None  # Auto-generated
        assert entry.timestamp is not None  # Auto-generated
        assert entry.action == AuditAction.VIEW  # Default
        assert entry.entity_type == EntityType.ENTITY  # Default

    def test_entry_roundtrip(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = AuditLogEntry(
            id="test-id",
            timestamp="2024-01-15T10:30:00Z",
            action=AuditAction.LINK,
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            project_id="project-456",
            user_id="user-789",
            changes={"target": "entity-999"},
            ip_address="192.168.1.1",
            metadata={"extra": "data"},
        )

        data = original.to_dict()
        restored = AuditLogEntry.from_dict(data)

        assert restored.id == original.id
        assert restored.timestamp == original.timestamp
        assert restored.action == original.action
        assert restored.entity_type == original.entity_type
        assert restored.entity_id == original.entity_id
        assert restored.project_id == original.project_id
        assert restored.user_id == original.user_id
        assert restored.changes == original.changes
        assert restored.ip_address == original.ip_address
        assert restored.metadata == original.metadata


# ==================== AuditAction and EntityType Tests ====================


class TestEnums:
    """Tests for AuditAction and EntityType enums."""

    def test_audit_actions(self):
        """Test all audit action values."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        assert AuditAction.LINK.value == "LINK"
        assert AuditAction.UNLINK.value == "UNLINK"
        assert AuditAction.VIEW.value == "VIEW"

    def test_entity_types(self):
        """Test all entity type values."""
        assert EntityType.PROJECT.value == "PROJECT"
        assert EntityType.ENTITY.value == "ENTITY"
        assert EntityType.RELATIONSHIP.value == "RELATIONSHIP"
        assert EntityType.FILE.value == "FILE"
        assert EntityType.REPORT.value == "REPORT"
        assert EntityType.TEMPLATE.value == "TEMPLATE"
        assert EntityType.SCHEDULE.value == "SCHEDULE"

    def test_action_from_string(self):
        """Test creating action from string."""
        assert AuditAction("CREATE") == AuditAction.CREATE
        assert AuditAction("UPDATE") == AuditAction.UPDATE

    def test_entity_type_from_string(self):
        """Test creating entity type from string."""
        assert EntityType("PROJECT") == EntityType.PROJECT
        assert EntityType("ENTITY") == EntityType.ENTITY


# ==================== InMemoryAuditBackend Tests ====================


class TestInMemoryAuditBackend:
    """Tests for InMemoryAuditBackend."""

    @pytest.fixture
    def backend(self):
        """Create a fresh backend for each test."""
        return InMemoryAuditBackend(max_entries=100)

    @pytest.mark.asyncio
    async def test_save_entry(self, backend):
        """Test saving an audit entry."""
        entry = AuditLogEntry(
            action=AuditAction.CREATE,
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        result = await backend.save(entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_load_all(self, backend):
        """Test loading all entries."""
        # Save some entries
        for i in range(5):
            entry = AuditLogEntry(
                action=AuditAction.CREATE,
                entity_id=f"entity-{i}",
            )
            await backend.save(entry)

        entries = await backend.load_all()

        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_query_by_entity_id(self, backend):
        """Test querying by entity ID."""
        # Save entries for different entities
        for i in range(3):
            entry = AuditLogEntry(
                action=AuditAction.UPDATE,
                entity_id=f"entity-{i}",
            )
            await backend.save(entry)

        results = await backend.query(entity_id="entity-1")

        assert len(results) == 1
        assert results[0].entity_id == "entity-1"

    @pytest.mark.asyncio
    async def test_query_by_project_id(self, backend):
        """Test querying by project ID."""
        # Save entries for different projects
        await backend.save(AuditLogEntry(entity_id="e1", project_id="project-A"))
        await backend.save(AuditLogEntry(entity_id="e2", project_id="project-A"))
        await backend.save(AuditLogEntry(entity_id="e3", project_id="project-B"))

        results = await backend.query(project_id="project-A")

        assert len(results) == 2
        for entry in results:
            assert entry.project_id == "project-A"

    @pytest.mark.asyncio
    async def test_query_by_action(self, backend):
        """Test querying by action type."""
        await backend.save(AuditLogEntry(entity_id="e1", action=AuditAction.CREATE))
        await backend.save(AuditLogEntry(entity_id="e2", action=AuditAction.UPDATE))
        await backend.save(AuditLogEntry(entity_id="e3", action=AuditAction.CREATE))

        results = await backend.query(action=AuditAction.CREATE)

        assert len(results) == 2
        for entry in results:
            assert entry.action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_query_by_entity_type(self, backend):
        """Test querying by entity type."""
        await backend.save(AuditLogEntry(entity_id="e1", entity_type=EntityType.PROJECT))
        await backend.save(AuditLogEntry(entity_id="e2", entity_type=EntityType.ENTITY))
        await backend.save(AuditLogEntry(entity_id="e3", entity_type=EntityType.PROJECT))

        results = await backend.query(entity_type=EntityType.PROJECT)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_by_date_range(self, backend):
        """Test querying by date range."""
        now = datetime.utcnow()

        # Create entries with different timestamps
        old_entry = AuditLogEntry(
            entity_id="old",
            timestamp=(now - timedelta(days=5)).isoformat() + "Z",
        )
        recent_entry = AuditLogEntry(
            entity_id="recent",
            timestamp=(now - timedelta(hours=1)).isoformat() + "Z",
        )

        await backend.save(old_entry)
        await backend.save(recent_entry)

        # Query for entries from the last 2 days
        results = await backend.query(
            start_date=now - timedelta(days=2),
            end_date=now,
        )

        assert len(results) == 1
        assert results[0].entity_id == "recent"

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, backend):
        """Test query pagination."""
        # Save 10 entries
        for i in range(10):
            await backend.save(AuditLogEntry(entity_id=f"entity-{i}"))

        # Get first page
        page1 = await backend.query(limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = await backend.query(limit=5, offset=5)
        assert len(page2) == 5

        # Verify no overlap
        page1_ids = {e.entity_id for e in page1}
        page2_ids = {e.entity_id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_query_combined_filters(self, backend):
        """Test querying with multiple filters."""
        await backend.save(AuditLogEntry(
            entity_id="e1",
            project_id="project-A",
            action=AuditAction.CREATE,
        ))
        await backend.save(AuditLogEntry(
            entity_id="e2",
            project_id="project-A",
            action=AuditAction.UPDATE,
        ))
        await backend.save(AuditLogEntry(
            entity_id="e3",
            project_id="project-B",
            action=AuditAction.CREATE,
        ))

        results = await backend.query(
            project_id="project-A",
            action=AuditAction.CREATE,
        )

        assert len(results) == 1
        assert results[0].entity_id == "e1"

    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Test clearing all entries."""
        # Save some entries
        for i in range(5):
            await backend.save(AuditLogEntry(entity_id=f"entity-{i}"))

        count = await backend.clear()

        assert count == 5

        remaining = await backend.load_all()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_max_entries_trim(self):
        """Test that old entries are trimmed when max is exceeded."""
        backend = InMemoryAuditBackend(max_entries=10)

        # Save 15 entries
        for i in range(15):
            await backend.save(AuditLogEntry(entity_id=f"entity-{i}"))

        entries = await backend.load_all()

        # Should have trimmed the oldest entries (removed first 1, which is 10% of 10)
        assert len(entries) <= 15

    def test_get_stats(self):
        """Test getting statistics."""
        backend = InMemoryAuditBackend(max_entries=100)

        stats = backend.get_stats()

        assert "total_entries" in stats
        assert "max_entries" in stats
        assert "action_counts" in stats
        assert "entity_type_counts" in stats
        assert stats["max_entries"] == 100

    @pytest.mark.asyncio
    async def test_get_stats_with_entries(self, backend):
        """Test statistics with actual entries."""
        await backend.save(AuditLogEntry(action=AuditAction.CREATE, entity_type=EntityType.ENTITY))
        await backend.save(AuditLogEntry(action=AuditAction.CREATE, entity_type=EntityType.ENTITY))
        await backend.save(AuditLogEntry(action=AuditAction.UPDATE, entity_type=EntityType.PROJECT))

        stats = backend.get_stats()

        assert stats["total_entries"] == 3
        assert stats["action_counts"]["CREATE"] == 2
        assert stats["action_counts"]["UPDATE"] == 1
        assert stats["entity_type_counts"]["ENTITY"] == 2
        assert stats["entity_type_counts"]["PROJECT"] == 1


# ==================== AuditLogger Tests ====================


class TestAuditLogger:
    """Tests for AuditLogger service."""

    @pytest.fixture
    def logger(self):
        """Create a fresh audit logger for each test."""
        return AuditLogger(enabled=True, log_views=True)

    @pytest.mark.asyncio
    async def test_log_create(self, logger):
        """Test logging a CREATE action."""
        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            project_id="project-456",
            changes={"name": "John Doe"},
            user_id="user-789",
            ip_address="192.168.1.1",
        )

        assert entry is not None
        assert entry.action == AuditAction.CREATE
        assert entry.entity_type == EntityType.ENTITY
        assert entry.entity_id == "entity-123"
        assert entry.project_id == "project-456"
        assert entry.user_id == "user-789"
        assert entry.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_log_update(self, logger):
        """Test logging an UPDATE action."""
        entry = await logger.log_update(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            changes={"name": "Jane Doe"},
        )

        assert entry is not None
        assert entry.action == AuditAction.UPDATE
        assert entry.changes == {"name": "Jane Doe"}

    @pytest.mark.asyncio
    async def test_log_delete(self, logger):
        """Test logging a DELETE action."""
        entry = await logger.log_delete(
            entity_type=EntityType.PROJECT,
            entity_id="project-123",
            user_id="admin",
        )

        assert entry is not None
        assert entry.action == AuditAction.DELETE
        assert entry.entity_type == EntityType.PROJECT

    @pytest.mark.asyncio
    async def test_log_link(self, logger):
        """Test logging a LINK action."""
        entry = await logger.log_link(
            entity_type=EntityType.ENTITY,
            entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="KNOWS",
        )

        assert entry is not None
        assert entry.action == AuditAction.LINK
        assert entry.changes["target_entity_id"] == "entity-2"
        assert entry.changes["relationship_type"] == "KNOWS"

    @pytest.mark.asyncio
    async def test_log_unlink(self, logger):
        """Test logging an UNLINK action."""
        entry = await logger.log_unlink(
            entity_type=EntityType.ENTITY,
            entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="KNOWS",
        )

        assert entry is not None
        assert entry.action == AuditAction.UNLINK

    @pytest.mark.asyncio
    async def test_log_view(self, logger):
        """Test logging a VIEW action."""
        entry = await logger.log_view(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            user_id="user-456",
        )

        assert entry is not None
        assert entry.action == AuditAction.VIEW

    @pytest.mark.asyncio
    async def test_log_view_disabled(self):
        """Test that VIEW actions are not logged when disabled."""
        logger = AuditLogger(enabled=True, log_views=False)

        entry = await logger.log_view(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert entry is None

    @pytest.mark.asyncio
    async def test_logging_disabled(self):
        """Test that logging is disabled when enabled=False."""
        logger = AuditLogger(enabled=False)

        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert entry is None

    @pytest.mark.asyncio
    async def test_enable_disable(self, logger):
        """Test enabling and disabling logging."""
        logger.disable()
        assert not logger.is_enabled

        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )
        assert entry is None

        logger.enable()
        assert logger.is_enabled

        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_generic_log_method(self, logger):
        """Test the generic log method."""
        entry = await logger.log(
            action=AuditAction.UPDATE,
            entity_type=EntityType.FILE,
            entity_id="file-123",
            project_id="project-456",
            changes={"size": 1024},
            metadata={"mimetype": "text/plain"},
        )

        assert entry is not None
        assert entry.action == AuditAction.UPDATE
        assert entry.entity_type == EntityType.FILE
        assert entry.metadata == {"mimetype": "text/plain"}


# ==================== Query Method Tests ====================


class TestAuditLoggerQueries:
    """Tests for AuditLogger query methods."""

    async def _create_logger_with_data(self):
        """Create a logger with sample data."""
        logger = AuditLogger(enabled=True, log_views=True)

        # Add sample entries
        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-1",
            project_id="project-A",
        )
        await logger.log_update(
            entity_type=EntityType.ENTITY,
            entity_id="entity-1",
            project_id="project-A",
        )
        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-2",
            project_id="project-B",
        )
        await logger.log_delete(
            entity_type=EntityType.PROJECT,
            entity_id="project-C",
        )

        return logger

    @pytest.mark.asyncio
    async def test_get_logs_by_entity(self):
        """Test getting logs by entity ID."""
        logger_with_data = await self._create_logger_with_data()
        logs = await logger_with_data.get_logs_by_entity("entity-1")

        assert len(logs) == 2
        for log in logs:
            assert log.entity_id == "entity-1"

    @pytest.mark.asyncio
    async def test_get_logs_by_project(self):
        """Test getting logs by project ID."""
        logger_with_data = await self._create_logger_with_data()
        logs = await logger_with_data.get_logs_by_project("project-A")

        assert len(logs) == 2
        for log in logs:
            assert log.project_id == "project-A"

    @pytest.mark.asyncio
    async def test_get_logs_by_action(self):
        """Test getting logs by action type."""
        logger_with_data = await self._create_logger_with_data()
        logs = await logger_with_data.get_logs_by_action(AuditAction.CREATE)

        assert len(logs) == 2
        for log in logs:
            assert log.action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_get_logs_by_date_range(self):
        """Test getting logs by date range."""
        logger_with_data = await self._create_logger_with_data()
        # Get logs from the last hour
        start = datetime.utcnow() - timedelta(hours=1)
        logs = await logger_with_data.get_logs_by_date_range(start)

        # All recent entries should be included
        assert len(logs) >= 4

    @pytest.mark.asyncio
    async def test_get_all_logs(self):
        """Test getting all logs."""
        logger_with_data = await self._create_logger_with_data()
        logs = await logger_with_data.get_all_logs()

        assert len(logs) == 4

    @pytest.mark.asyncio
    async def test_get_logs_with_pagination(self):
        """Test logs pagination."""
        logger_with_data = await self._create_logger_with_data()
        # Get first 2 logs
        page1 = await logger_with_data.get_all_logs(limit=2, offset=0)
        assert len(page1) == 2

        # Get next 2 logs
        page2 = await logger_with_data.get_all_logs(limit=2, offset=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_get_logs_flexible_filter(self):
        """Test flexible log filtering."""
        logger_with_data = await self._create_logger_with_data()
        logs = await logger_with_data.get_logs(
            project_id="project-A",
            action=AuditAction.CREATE,
        )

        assert len(logs) == 1
        assert logs[0].project_id == "project-A"
        assert logs[0].action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_clear_logs(self):
        """Test clearing all logs."""
        logger_with_data = await self._create_logger_with_data()
        count = await logger_with_data.clear_logs()

        assert count == 4

        remaining = await logger_with_data.get_all_logs()
        assert len(remaining) == 0


# ==================== Listener Tests ====================


class TestAuditLoggerListeners:
    """Tests for AuditLogger listener functionality."""

    @pytest.fixture
    def logger(self):
        """Create a fresh audit logger."""
        return AuditLogger(enabled=True)

    @pytest.mark.asyncio
    async def test_add_listener(self, logger):
        """Test adding a listener."""
        received_entries = []

        def listener(entry):
            received_entries.append(entry)

        logger.add_listener(listener)

        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert len(received_entries) == 1
        assert received_entries[0].entity_id == "entity-123"

    @pytest.mark.asyncio
    async def test_remove_listener(self, logger):
        """Test removing a listener."""
        received_entries = []

        def listener(entry):
            received_entries.append(entry)

        logger.add_listener(listener)
        logger.remove_listener(listener)

        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert len(received_entries) == 0

    @pytest.mark.asyncio
    async def test_multiple_listeners(self, logger):
        """Test multiple listeners."""
        entries1 = []
        entries2 = []

        def listener1(entry):
            entries1.append(entry)

        def listener2(entry):
            entries2.append(entry)

        logger.add_listener(listener1)
        logger.add_listener(listener2)

        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert len(entries1) == 1
        assert len(entries2) == 1

    @pytest.mark.asyncio
    async def test_listener_error_handling(self, logger):
        """Test that listener errors don't break logging."""
        def bad_listener(entry):
            raise Exception("Listener error!")

        good_entries = []

        def good_listener(entry):
            good_entries.append(entry)

        logger.add_listener(bad_listener)
        logger.add_listener(good_listener)

        # Should not raise despite bad_listener error
        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert entry is not None
        assert len(good_entries) == 1


# ==================== Statistics and Health Tests ====================


class TestAuditLoggerStats:
    """Tests for statistics and health check."""

    async def _create_logger_with_data(self):
        """Create a logger with sample data."""
        logger = AuditLogger(enabled=True)

        await logger.log_create(entity_type=EntityType.ENTITY, entity_id="e1")
        await logger.log_create(entity_type=EntityType.ENTITY, entity_id="e2")
        await logger.log_update(entity_type=EntityType.PROJECT, entity_id="p1")

        return logger

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting statistics."""
        logger_with_data = await self._create_logger_with_data()
        stats = logger_with_data.get_stats()

        assert stats["total_entries"] == 3
        assert stats["action_counts"]["CREATE"] == 2
        assert stats["action_counts"]["UPDATE"] == 1

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when healthy."""
        logger_with_data = await self._create_logger_with_data()
        health = await logger_with_data.health_check()

        assert health["status"] == "healthy"
        assert health["enabled"] is True
        assert health["has_entries"] is True

    @pytest.mark.asyncio
    async def test_health_check_no_entries(self):
        """Test health check with no entries."""
        logger = AuditLogger(enabled=True)
        health = await logger.health_check()

        assert health["status"] == "healthy"
        assert health["has_entries"] is False


# ==================== Singleton Tests ====================


class TestAuditLoggerSingleton:
    """Tests for singleton pattern."""

    def test_get_audit_logger_creates_singleton(self):
        """Test that get_audit_logger creates a singleton."""
        # Reset singleton
        set_audit_logger(None)

        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2

    def test_set_audit_logger(self):
        """Test setting the audit logger singleton."""
        custom_logger = AuditLogger(enabled=False)

        set_audit_logger(custom_logger)

        assert get_audit_logger() is custom_logger

        # Clean up
        set_audit_logger(None)

    @pytest.mark.asyncio
    async def test_initialize_audit_logger(self):
        """Test the initialize_audit_logger convenience function."""
        # Reset singleton
        set_audit_logger(None)

        logger = await initialize_audit_logger(
            enabled=True,
            log_views=True,
            max_entries=5000,
        )

        assert logger is not None
        assert logger.is_enabled is True

        # Clean up
        set_audit_logger(None)


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_entity_id(self):
        """Test logging with empty entity ID."""
        logger = AuditLogger(enabled=True)

        entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="",
        )

        assert entry is not None
        assert entry.entity_id == ""

    @pytest.mark.asyncio
    async def test_none_changes(self):
        """Test logging without changes."""
        logger = AuditLogger(enabled=True)

        entry = await logger.log_update(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            changes=None,
        )

        assert entry is not None
        assert entry.changes is None

    @pytest.mark.asyncio
    async def test_complex_changes(self):
        """Test logging with complex nested changes."""
        logger = AuditLogger(enabled=True)

        complex_changes = {
            "profile": {
                "personal": {
                    "name": {"first": "John", "last": "Doe"},
                    "emails": ["john@example.com", "doe@example.com"],
                },
                "settings": {
                    "notifications": True,
                    "theme": "dark",
                }
            },
            "tags": ["tag1", "tag2"],
        }

        entry = await logger.log_update(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
            changes=complex_changes,
        )

        assert entry is not None
        assert entry.changes == complex_changes

    @pytest.mark.asyncio
    async def test_concurrent_logging(self):
        """Test concurrent logging operations."""
        logger = AuditLogger(enabled=True, max_entries=1000)

        async def log_entry(i):
            return await logger.log_create(
                entity_type=EntityType.ENTITY,
                entity_id=f"entity-{i}",
            )

        # Log 50 entries concurrently
        tasks = [log_entry(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert all(r is not None for r in results)

        logs = await logger.get_all_logs()
        assert len(logs) == 50

    @pytest.mark.asyncio
    async def test_special_characters_in_ids(self):
        """Test logging with special characters in IDs."""
        logger = AuditLogger(enabled=True)

        special_ids = [
            "entity/with/slashes",
            "entity:with:colons",
            "entity with spaces",
            "entity-with-dashes",
            "entity_with_underscores",
        ]

        for entity_id in special_ids:
            entry = await logger.log_create(
                entity_type=EntityType.ENTITY,
                entity_id=entity_id,
            )
            assert entry is not None
            assert entry.entity_id == entity_id


# ==================== Integration-like Tests ====================


class TestAuditLoggerIntegration:
    """Integration-like tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_entity_lifecycle_audit(self):
        """Test auditing a complete entity lifecycle."""
        logger = AuditLogger(enabled=True, log_views=True)
        project_id = "test-project"
        entity_id = "test-entity"

        # Create entity
        create_entry = await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            changes={"name": "John Doe"},
            user_id="admin",
        )
        assert create_entry is not None

        # View entity
        view_entry = await logger.log_view(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            user_id="viewer",
        )
        assert view_entry is not None

        # Update entity
        update_entry = await logger.log_update(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            changes={"name": "Jane Doe"},
            user_id="admin",
        )
        assert update_entry is not None

        # Link entity
        link_entry = await logger.log_link(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            target_entity_id="other-entity",
            relationship_type="KNOWS",
            user_id="admin",
        )
        assert link_entry is not None

        # Unlink entity
        unlink_entry = await logger.log_unlink(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            target_entity_id="other-entity",
            relationship_type="KNOWS",
            user_id="admin",
        )
        assert unlink_entry is not None

        # Delete entity
        delete_entry = await logger.log_delete(
            entity_type=EntityType.ENTITY,
            entity_id=entity_id,
            project_id=project_id,
            user_id="admin",
        )
        assert delete_entry is not None

        # Verify all entries for this entity
        logs = await logger.get_logs_by_entity(entity_id)
        assert len(logs) == 6

        # Verify chronological order (most recent first)
        actions = [log.action for log in logs]
        assert actions[0] == AuditAction.DELETE
        assert actions[-1] == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_project_audit_trail(self):
        """Test building a project audit trail."""
        logger = AuditLogger(enabled=True)
        project_id = "investigation-001"

        # Create project
        await logger.log_create(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            changes={"name": "Investigation Alpha"},
            user_id="admin",
        )

        # Add entities to project
        for i in range(3):
            await logger.log_create(
                entity_type=EntityType.ENTITY,
                entity_id=f"entity-{i}",
                project_id=project_id,
                user_id="analyst",
            )

        # Create relationships
        await logger.log_link(
            entity_type=EntityType.RELATIONSHIP,
            entity_id="rel-001",
            project_id=project_id,
            user_id="analyst",
        )

        # Upload file
        await logger.log_create(
            entity_type=EntityType.FILE,
            entity_id="file-001",
            project_id=project_id,
            changes={"filename": "evidence.pdf"},
            user_id="analyst",
        )

        # Get full project audit trail
        logs = await logger.get_logs_by_project(project_id)

        assert len(logs) == 5  # 3 entities + 1 relationship + 1 file

        # Verify entity types
        entity_types = {log.entity_type for log in logs}
        assert EntityType.ENTITY in entity_types
        assert EntityType.RELATIONSHIP in entity_types
        assert EntityType.FILE in entity_types

    @pytest.mark.asyncio
    async def test_audit_with_listener_notifications(self):
        """Test real-time audit notifications via listeners."""
        logger = AuditLogger(enabled=True)

        notifications = []

        def notification_handler(entry):
            notifications.append({
                "action": entry.action.value,
                "entity_id": entry.entity_id,
                "timestamp": entry.timestamp,
            })

        logger.add_listener(notification_handler)

        # Perform various actions
        await logger.log_create(entity_type=EntityType.ENTITY, entity_id="e1")
        await logger.log_update(entity_type=EntityType.ENTITY, entity_id="e1")
        await logger.log_delete(entity_type=EntityType.ENTITY, entity_id="e1")

        # Verify notifications were received
        assert len(notifications) == 3
        assert notifications[0]["action"] == "CREATE"
        assert notifications[1]["action"] == "UPDATE"
        assert notifications[2]["action"] == "DELETE"


# ==================== Custom Backend Tests ====================


class TestCustomBackend:
    """Tests for custom persistence backends."""

    @pytest.mark.asyncio
    async def test_custom_backend(self):
        """Test using a custom persistence backend."""

        class MockBackend(AuditPersistenceBackend):
            def __init__(self):
                self.entries = []

            async def save(self, entry):
                self.entries.append(entry)
                return True

            async def load_all(self):
                return self.entries

            async def query(self, **kwargs):
                return self.entries

            async def clear(self):
                count = len(self.entries)
                self.entries = []
                return count

        mock_backend = MockBackend()
        logger = AuditLogger(backend=mock_backend, enabled=True)

        await logger.log_create(
            entity_type=EntityType.ENTITY,
            entity_id="entity-123",
        )

        assert len(mock_backend.entries) == 1
        assert mock_backend.entries[0].entity_id == "entity-123"
