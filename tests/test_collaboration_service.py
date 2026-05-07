"""
Tests for Real-Time Collaboration Service

Tests:
- Entity synchronization (broadcast)
- Offline queue handling
- Concurrent edit detection
- Conflict resolution (last-write-wins, merge)
- Activity feed logging and retrieval
- Presence indicators
- Entity lock management

Phase 8, Stream 6: Real-Time Collaboration Features
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.collaboration_service import (
    CollaborationService,
    ActivityAction,
    ConflictResolutionStrategy,
    EditConflict,
    ActivityEvent,
    PresenceIndicator,
    SyncUpdate,
)


@pytest.fixture
def service():
    """Create a collaboration service instance for testing."""
    service = CollaborationService()
    service.neo4j = AsyncMock()
    return service


@pytest.fixture
async def initialized_service(service):
    """Create an initialized collaboration service."""
    await service.initialize()
    return service


class TestRealTimeSyncLayer:
    """Tests for real-time sync layer."""

    @pytest.mark.asyncio
    async def test_broadcast_entity_update(self, service):
        """Test broadcasting an entity update."""
        update = await service.broadcast_entity_update(
            project_id="proj1",
            entity_id="entity1",
            operation="update",
            data={"name": "John Doe"},
            user="user1",
        )

        assert update.entity_id == "entity1"
        assert update.operation == "update"
        assert update.data == {"name": "John Doe"}
        assert update.user == "user1"
        assert update.version == 1

    @pytest.mark.asyncio
    async def test_broadcast_increments_version(self, service):
        """Test that version increments with each update."""
        await service.broadcast_entity_update(
            project_id="proj1",
            entity_id="entity1",
            operation="create",
            data={"name": "John"},
            user="user1",
        )

        update2 = await service.broadcast_entity_update(
            project_id="proj1",
            entity_id="entity1",
            operation="update",
            data={"name": "Jane"},
            user="user1",
        )

        assert update2.version == 2

    @pytest.mark.asyncio
    async def test_offline_queue_management(self, service):
        """Test offline queue handling."""
        await service.queue_offline_update(
            user="user1",
            project_id="proj1",
            entity_id="entity1",
            operation="update",
            data={"name": "Updated"},
        )

        updates = await service.handle_offline_queue("user1", "proj1")
        assert len(updates) == 1
        assert updates[0].entity_id == "entity1"

    @pytest.mark.asyncio
    async def test_offline_queue_clears_after_retrieval(self, service):
        """Test that offline queue clears after retrieval."""
        await service.queue_offline_update(
            user="user1",
            project_id="proj1",
            entity_id="entity1",
            operation="update",
            data={"name": "Updated"},
        )

        await service.handle_offline_queue("user1", "proj1")
        updates = await service.handle_offline_queue("user1", "proj1")

        assert len(updates) == 0

    @pytest.mark.asyncio
    async def test_multiple_offline_updates(self, service):
        """Test queuing multiple offline updates."""
        for i in range(3):
            await service.queue_offline_update(
                user="user1",
                project_id="proj1",
                entity_id=f"entity{i}",
                operation="update",
                data={"index": i},
            )

        updates = await service.handle_offline_queue("user1", "proj1")
        assert len(updates) == 3


class TestConcurrentEditDetection:
    """Tests for concurrent edit detection and conflict resolution."""

    @pytest.mark.asyncio
    async def test_detect_concurrent_edit(self, service):
        """Test detecting concurrent edits."""
        # Mock the _get_entity_data method
        service._get_entity_data = AsyncMock(return_value={"entity_id": "entity1", "name": "Original"})

        # Lock entity for user1
        conflict1 = await service.detect_concurrent_edit(
            entity_id="entity1",
            user="user1",
            changes={"name": "John"},
        )
        assert conflict1 is None  # First user gets no conflict

        # User2 edits same entity
        conflict2 = await service.detect_concurrent_edit(
            entity_id="entity1",
            user="user2",
            changes={"name": "Jane"},
        )
        assert conflict2 is not None
        assert conflict2.user_1 == "user1"
        assert conflict2.user_2 == "user2"

    @pytest.mark.asyncio
    async def test_last_write_wins_resolution(self, service):
        """Test last-write-wins conflict resolution."""
        conflict = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            changes_1={"name": "John"},
            changes_2={"name": "Jane"},
        )

        merged = await service.merge_concurrent_edits(
            conflict,
            ConflictResolutionStrategy.LAST_WRITE_WINS,
        )

        assert merged == {"name": "Jane"}
        assert conflict.resolved

    @pytest.mark.asyncio
    async def test_first_write_wins_resolution(self, service):
        """Test first-write-wins conflict resolution."""
        conflict = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            changes_1={"name": "John"},
            changes_2={"name": "Jane"},
        )

        merged = await service.merge_concurrent_edits(
            conflict,
            ConflictResolutionStrategy.FIRST_WRITE_WINS,
        )

        assert merged == {"name": "John"}
        assert conflict.resolved

    @pytest.mark.asyncio
    async def test_merge_resolution(self, service):
        """Test merge conflict resolution."""
        conflict = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=datetime.now(timezone.utc).isoformat(),
            changes_1={"name": "John", "email": "john@example.com"},
            changes_2={"phone": "123-456-7890"},
        )

        merged = await service.merge_concurrent_edits(
            conflict,
            ConflictResolutionStrategy.MERGE,
        )

        assert merged == {
            "name": "John",
            "email": "john@example.com",
            "phone": "123-456-7890",
        }

    @pytest.mark.asyncio
    async def test_get_conflict_by_id(self, service):
        """Test retrieving a conflict by ID."""
        conflict = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=datetime.now(timezone.utc).isoformat(),
            changes_1={"name": "John"},
            changes_2={"name": "Jane"},
        )
        service.conflicts[conflict.conflict_id] = conflict

        retrieved = await service.get_conflict(conflict.conflict_id)
        assert retrieved is not None
        assert retrieved["entity_id"] == "entity1"

    @pytest.mark.asyncio
    async def test_list_unresolved_conflicts(self, service):
        """Test listing unresolved conflicts."""
        conflict1 = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=datetime.now(timezone.utc).isoformat(),
            changes_1={"name": "John"},
            changes_2={"name": "Jane"},
        )
        conflict2 = EditConflict(
            entity_id="entity2",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=datetime.now(timezone.utc).isoformat(),
            changes_1={"email": "a@example.com"},
            changes_2={"email": "b@example.com"},
            resolved=True,
        )

        service.conflicts[conflict1.conflict_id] = conflict1
        service.conflicts[conflict2.conflict_id] = conflict2

        conflicts = await service.list_conflicts("proj1")
        assert len(conflicts) == 1
        assert conflicts[0]["entity_id"] == "entity1"


class TestActivityFeed:
    """Tests for activity feed functionality."""

    @pytest.mark.asyncio
    async def test_log_activity_event(self, service):
        """Test logging an activity event."""
        activity = await service.log_activity(
            project_id="proj1",
            action=ActivityAction.ENTITY_CREATED,
            entity_id="entity1",
            user="user1",
            details={"source": "import"},
        )

        assert activity.project_id == "proj1"
        assert activity.action == ActivityAction.ENTITY_CREATED
        assert activity.entity_id == "entity1"
        assert activity.user == "user1"

    @pytest.mark.asyncio
    async def test_get_activity_feed(self, service):
        """Test retrieving activity feed."""
        service.neo4j.execute_query = AsyncMock(return_value=[
            [MagicMock(spec=dict,
                      **{
                          "__getitem__": lambda self, key: {
                              "activity_id": "act1",
                              "action": "entity_created",
                              "entity_id": "entity1",
                              "user": "user1",
                              "timestamp": datetime.now(timezone.utc).isoformat(),
                          }.get(key)
                      })]
        ])

        activities = await service.get_activity_feed("proj1", limit=10)
        assert service.neo4j.execute_query.called

    @pytest.mark.asyncio
    async def test_archive_old_activities(self, service):
        """Test archiving old activities."""
        service.neo4j.execute_query = AsyncMock(return_value=[[5]])

        archived_count = await service.archive_old_activities("proj1", days=30)
        assert archived_count == 5


class TestPresenceIndicators:
    """Tests for presence indicators."""

    @pytest.mark.asyncio
    async def test_update_presence(self, service):
        """Test updating user presence."""
        indicator = await service.update_presence(
            project_id="proj1",
            user="user1",
            viewing_entity_id="entity1",
            is_editing=True,
        )

        assert indicator.project_id == "proj1"
        assert indicator.user == "user1"
        assert indicator.viewing_entity_id == "entity1"
        assert indicator.is_editing is True

    @pytest.mark.asyncio
    async def test_get_active_users(self, service):
        """Test getting active users in a project."""
        indicator1 = await service.update_presence("proj1", "user1")
        indicator2 = await service.update_presence("proj1", "user2")

        active_users = await service.get_active_users("proj1")
        assert len(active_users) == 2

    @pytest.mark.asyncio
    async def test_get_entity_viewers(self, service):
        """Test getting users viewing an entity."""
        await service.update_presence("proj1", "user1", viewing_entity_id="entity1")
        await service.update_presence("proj1", "user2", viewing_entity_id="entity1")

        viewers = await service.get_entity_viewers("entity1")
        assert len(viewers) == 2

    @pytest.mark.asyncio
    async def test_remove_presence(self, service):
        """Test removing user presence."""
        await service.update_presence("proj1", "user1")
        removed = await service.remove_presence("proj1", "user1")

        assert removed is True
        active_users = await service.get_active_users("proj1")
        assert len(active_users) == 0

    @pytest.mark.asyncio
    async def test_presence_timeout(self, service):
        """Test presence timeout."""
        # Create a stale presence indicator
        indicator = PresenceIndicator(
            project_id="proj1",
            user="user1",
            last_activity=(datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat(),
        )
        service.presence["proj1:user1"] = indicator

        # Add an active user
        await service.update_presence("proj1", "user2")

        # Only active user should be returned
        active_users = await service.get_active_users("proj1", timeout_seconds=300)
        assert len(active_users) == 1
        assert active_users[0].user == "user2"

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence(self, service):
        """Test cleaning up stale presence indicators."""
        # Add stale presence
        stale = PresenceIndicator(
            project_id="proj1",
            user="user1",
            last_activity=(datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat(),
        )
        service.presence["proj1:user1"] = stale

        # Add active presence
        await service.update_presence("proj1", "user2")

        cleaned = await service.cleanup_stale_presence(timeout_seconds=300)
        assert cleaned == 1


class TestPresenceIndicatorModels:
    """Tests for presence indicator model."""

    def test_presence_is_active(self):
        """Test presence is_active check."""
        # Create active presence
        active = PresenceIndicator(
            project_id="proj1",
            user="user1",
            last_activity=datetime.now(timezone.utc).isoformat(),
        )
        assert active.is_active(timeout_seconds=300)

        # Create stale presence
        stale = PresenceIndicator(
            project_id="proj1",
            user="user2",
            last_activity=(datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat(),
        )
        assert not stale.is_active(timeout_seconds=300)

    def test_presence_to_dict(self):
        """Test presence to_dict serialization."""
        indicator = PresenceIndicator(
            project_id="proj1",
            user="user1",
            viewing_entity_id="entity1",
            is_editing=True,
        )

        data = indicator.to_dict()
        assert data["user"] == "user1"
        assert data["project_id"] == "proj1"
        assert data["viewing_entity_id"] == "entity1"
        assert data["is_editing"] is True


class TestDataModels:
    """Tests for data model serialization."""

    def test_edit_conflict_to_dict(self):
        """Test conflict serialization."""
        conflict = EditConflict(
            entity_id="entity1",
            user_1="user1",
            user_2="user2",
            timestamp_1=datetime.now(timezone.utc).isoformat(),
            timestamp_2=datetime.now(timezone.utc).isoformat(),
            changes_1={"name": "John"},
            changes_2={"name": "Jane"},
        )

        data = conflict.to_dict()
        assert data["entity_id"] == "entity1"
        assert data["user_1"] == "user1"
        assert data["user_2"] == "user2"

    def test_activity_event_to_dict(self):
        """Test activity event serialization."""
        activity = ActivityEvent(
            project_id="proj1",
            action=ActivityAction.ENTITY_CREATED,
            entity_id="entity1",
            user="user1",
        )

        data = activity.to_dict()
        assert data["project_id"] == "proj1"
        assert data["action"] == "entity_created"
        assert data["entity_id"] == "entity1"

    def test_sync_update_to_dict(self):
        """Test sync update serialization."""
        update = SyncUpdate(
            entity_id="entity1",
            project_id="proj1",
            operation="update",
            data={"name": "John"},
            user="user1",
        )

        data = update.to_dict()
        assert data["entity_id"] == "entity1"
        assert data["operation"] == "update"
        assert data["data"] == {"name": "John"}


class TestEntityLocking:
    """Tests for entity locking mechanism."""

    @pytest.mark.asyncio
    async def test_release_entity_lock(self, service):
        """Test releasing an entity lock."""
        service.entity_locks["entity1"] = "user1"

        released = await service.release_entity_lock("entity1", "user1")
        assert released is True
        assert "entity1" not in service.entity_locks

    @pytest.mark.asyncio
    async def test_release_lock_by_wrong_user(self, service):
        """Test that wrong user cannot release lock."""
        service.entity_locks["entity1"] = "user1"

        released = await service.release_entity_lock("entity1", "user2")
        assert released is False
        assert service.entity_locks["entity1"] == "user1"
