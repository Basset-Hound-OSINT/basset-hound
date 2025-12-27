"""
Tests for the Timeline Analysis Service

Comprehensive test coverage for:
- TimelineEvent dataclass
- TimelineService class methods
- Event recording and retrieval
- Date and event type filtering
- Relationship history tracking
- Activity analysis
- Singleton management
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from api.services.timeline_service import (
    EventType,
    TimelineEvent,
    TimelineService,
    get_timeline_service,
    set_timeline_service,
)


# ==================== TimelineEvent Tests ====================


class TestTimelineEvent:
    """Tests for TimelineEvent dataclass."""

    def test_event_creation_with_defaults(self):
        """Test creating an event with default values."""
        event = TimelineEvent(
            entity_id="entity-123",
            project_id="project-456",
            event_type="CREATED"
        )

        assert event.entity_id == "entity-123"
        assert event.project_id == "project-456"
        assert event.event_type == "CREATED"
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.details == {}
        assert event.actor is None

    def test_event_creation_with_all_fields(self):
        """Test creating an event with all fields specified."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        details = {"field": "name", "old_value": None, "new_value": "John Doe"}

        event = TimelineEvent(
            event_id="custom-event-id",
            entity_id="entity-123",
            project_id="project-456",
            event_type="UPDATED",
            timestamp=timestamp,
            details=details,
            actor="user-789"
        )

        assert event.event_id == "custom-event-id"
        assert event.entity_id == "entity-123"
        assert event.project_id == "project-456"
        assert event.event_type == "UPDATED"
        assert event.timestamp == timestamp
        assert event.details == details
        assert event.actor == "user-789"

    def test_event_to_dict(self):
        """Test converting an event to a dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        event = TimelineEvent(
            event_id="event-123",
            entity_id="entity-456",
            project_id="project-789",
            event_type="CREATED",
            timestamp=timestamp,
            details={"key": "value"},
            actor="user-001"
        )

        result = event.to_dict()

        assert result["event_id"] == "event-123"
        assert result["entity_id"] == "entity-456"
        assert result["project_id"] == "project-789"
        assert result["event_type"] == "CREATED"
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert result["details"] == {"key": "value"}
        assert result["actor"] == "user-001"

    def test_event_from_dict(self):
        """Test creating an event from a dictionary."""
        data = {
            "event_id": "event-123",
            "entity_id": "entity-456",
            "project_id": "project-789",
            "event_type": "UPDATED",
            "timestamp": "2024-01-15T10:30:00",
            "details": {"field": "email"},
            "actor": "user-001"
        }

        event = TimelineEvent.from_dict(data)

        assert event.event_id == "event-123"
        assert event.entity_id == "entity-456"
        assert event.project_id == "project-789"
        assert event.event_type == "UPDATED"
        assert event.timestamp.year == 2024
        assert event.timestamp.month == 1
        assert event.timestamp.day == 15
        assert event.details == {"field": "email"}
        assert event.actor == "user-001"

    def test_event_from_dict_with_z_timestamp(self):
        """Test creating an event with Z-suffixed timestamp."""
        data = {
            "entity_id": "entity-456",
            "project_id": "project-789",
            "event_type": "CREATED",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        event = TimelineEvent.from_dict(data)

        assert event.timestamp is not None

    def test_event_from_dict_with_missing_fields(self):
        """Test creating an event from incomplete dictionary."""
        data = {}

        event = TimelineEvent.from_dict(data)

        assert event.event_id is not None  # Auto-generated
        assert event.entity_id == ""
        assert event.project_id == ""
        assert event.event_type == ""
        assert event.timestamp is not None  # Default to now
        assert event.details == {}
        assert event.actor is None

    def test_event_auto_generates_uuid(self):
        """Test that events auto-generate unique UUIDs."""
        event1 = TimelineEvent(
            entity_id="entity-1",
            project_id="project-1",
            event_type="CREATED"
        )
        event2 = TimelineEvent(
            entity_id="entity-1",
            project_id="project-1",
            event_type="CREATED"
        )

        assert event1.event_id != event2.event_id


# ==================== EventType Tests ====================


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """Test that all expected event types exist."""
        expected_types = [
            "CREATED",
            "UPDATED",
            "DELETED",
            "RELATIONSHIP_ADDED",
            "RELATIONSHIP_REMOVED",
            "RELATIONSHIP_UPDATED",
            "MERGED",
            "TAGGED",
            "UNTAGGED",
            "FILE_ADDED",
            "FILE_REMOVED",
            "REPORT_ADDED",
            "REPORT_REMOVED"
        ]

        for event_type in expected_types:
            assert hasattr(EventType, event_type)
            assert EventType[event_type].value == event_type

    def test_event_type_is_string_enum(self):
        """Test that EventType is a string enum."""
        assert EventType.CREATED == "CREATED"
        assert str(EventType.UPDATED) == "EventType.UPDATED"


# ==================== TimelineService Tests ====================


class TestTimelineService:
    """Tests for TimelineService class."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.run_query = MagicMock(return_value=[])
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a TimelineService with a mock handler."""
        return TimelineService(mock_handler)

    def test_service_initialization(self, service, mock_handler):
        """Test service initialization."""
        assert service._handler == mock_handler
        assert service._initialized is False

    def test_record_event(self, service, mock_handler):
        """Test recording a new timeline event."""
        event = service.record_event(
            project_id="project-123",
            entity_id="entity-456",
            event_type="CREATED",
            details={"field": "name"},
            actor="user-789"
        )

        assert event is not None
        assert event.project_id == "project-123"
        assert event.entity_id == "entity-456"
        assert event.event_type == "CREATED"
        assert event.details == {"field": "name"}
        assert event.actor == "user-789"
        assert event.event_id is not None
        assert event.timestamp is not None

        # Verify query was called
        mock_handler.run_query.assert_called_once()

    def test_record_event_without_details(self, service, mock_handler):
        """Test recording an event without details."""
        event = service.record_event(
            project_id="project-123",
            entity_id="entity-456",
            event_type="DELETED"
        )

        assert event.details == {}
        assert event.actor is None

    def test_record_event_handles_query_failure(self, service, mock_handler):
        """Test that record_event returns event even if query fails."""
        mock_handler.run_query.side_effect = Exception("Database error")

        event = service.record_event(
            project_id="project-123",
            entity_id="entity-456",
            event_type="CREATED"
        )

        # Event should still be returned
        assert event is not None
        assert event.project_id == "project-123"

    def test_get_entity_timeline(self, service, mock_handler):
        """Test getting timeline for an entity."""
        mock_handler.run_query.return_value = [
            {
                "te": {
                    "event_id": "event-1",
                    "entity_id": "entity-456",
                    "project_id": "project-123",
                    "event_type": "CREATED",
                    "timestamp": "2024-01-15T10:30:00",
                    "details": "{}",
                    "actor": None
                }
            }
        ]

        events = service.get_entity_timeline(
            project_id="project-123",
            entity_id="entity-456"
        )

        assert len(events) == 1
        assert events[0].event_id == "event-1"
        assert events[0].event_type == "CREATED"

    def test_get_entity_timeline_with_date_filters(self, service, mock_handler):
        """Test getting timeline with date filters."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        service.get_entity_timeline(
            project_id="project-123",
            entity_id="entity-456",
            start_date=start_date,
            end_date=end_date
        )

        # Verify query was called with date parameters
        call_args = mock_handler.run_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "start_date" in params
        assert "end_date" in params
        assert "datetime($start_date)" in query
        assert "datetime($end_date)" in query

    def test_get_entity_timeline_with_event_type_filter(self, service, mock_handler):
        """Test getting timeline with event type filter."""
        service.get_entity_timeline(
            project_id="project-123",
            entity_id="entity-456",
            event_types=["CREATED", "UPDATED"]
        )

        call_args = mock_handler.run_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "event_types" in params
        assert params["event_types"] == ["CREATED", "UPDATED"]
        assert "IN $event_types" in query

    def test_get_project_timeline(self, service, mock_handler):
        """Test getting timeline for a project."""
        mock_handler.run_query.return_value = [
            {
                "te": {
                    "event_id": "event-1",
                    "entity_id": "entity-1",
                    "project_id": "project-123",
                    "event_type": "CREATED",
                    "timestamp": "2024-01-15T10:30:00",
                    "details": "{}",
                    "actor": None
                }
            },
            {
                "te": {
                    "event_id": "event-2",
                    "entity_id": "entity-2",
                    "project_id": "project-123",
                    "event_type": "UPDATED",
                    "timestamp": "2024-01-15T11:30:00",
                    "details": "{}",
                    "actor": None
                }
            }
        ]

        events = service.get_project_timeline(
            project_id="project-123",
            limit=100
        )

        assert len(events) == 2

    def test_get_project_timeline_with_limit(self, service, mock_handler):
        """Test getting project timeline with limit."""
        service.get_project_timeline(
            project_id="project-123",
            limit=50
        )

        call_args = mock_handler.run_query.call_args
        params = call_args[0][1]

        assert params["limit"] == 50

    def test_get_relationship_history(self, service, mock_handler):
        """Test getting relationship history between two entities."""
        mock_handler.run_query.return_value = [
            {
                "te": {
                    "event_id": "event-1",
                    "entity_id": "entity-1",
                    "project_id": "project-123",
                    "event_type": "RELATIONSHIP_ADDED",
                    "timestamp": "2024-01-15T10:30:00",
                    "details": json.dumps({"target_entity": "entity-2"}),
                    "actor": None
                }
            }
        ]

        events = service.get_relationship_history(
            project_id="project-123",
            entity1_id="entity-1",
            entity2_id="entity-2"
        )

        assert len(events) == 1
        assert events[0].event_type == "RELATIONSHIP_ADDED"

    def test_analyze_activity(self, service, mock_handler):
        """Test activity analysis for an entity."""
        mock_handler.run_query.return_value = [
            {"event_type": "CREATED", "event_date": "2024-01-15", "timestamp": datetime(2024, 1, 15, 10, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-15", "timestamp": datetime(2024, 1, 15, 11, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-16", "timestamp": datetime(2024, 1, 16, 9, 0)},
        ]

        result = service.analyze_activity(
            project_id="project-123",
            entity_id="entity-456",
            days=30
        )

        assert result["total_events"] == 3
        assert result["events_by_type"]["CREATED"] == 1
        assert result["events_by_type"]["UPDATED"] == 2
        assert "2024-01-15" in result["events_by_day"]
        assert result["events_by_day"]["2024-01-15"] == 2
        assert result["analysis_period_days"] == 30

    def test_analyze_activity_empty_result(self, service, mock_handler):
        """Test activity analysis with no events."""
        mock_handler.run_query.return_value = []

        result = service.analyze_activity(
            project_id="project-123",
            entity_id="entity-456",
            days=30
        )

        assert result["total_events"] == 0
        assert result["events_by_type"] == {}
        assert result["events_by_day"] == {}
        assert result["most_active_day"] is None
        assert result["average_events_per_day"] == 0.0


# ==================== Async TimelineService Tests ====================


class TestTimelineServiceAsync:
    """Tests for async TimelineService methods."""

    @pytest.fixture
    def mock_async_handler(self):
        """Create a mock async Neo4j handler."""
        handler = MagicMock()

        # Create a mock session context manager
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create async context manager
        async_session_cm = MagicMock()
        async_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        async_session_cm.__aexit__ = AsyncMock(return_value=None)

        handler.session = MagicMock(return_value=async_session_cm)

        return handler, mock_session, mock_result

    @pytest.fixture
    def async_service(self, mock_async_handler):
        """Create a TimelineService with a mock async handler."""
        handler, _, _ = mock_async_handler
        return TimelineService(handler)

    @pytest.mark.asyncio
    async def test_initialize_async(self, mock_async_handler):
        """Test async initialization."""
        handler, mock_session, _ = mock_async_handler
        service = TimelineService(handler)

        await service.initialize()

        assert service._initialized is True
        # Should have called session.run to create indexes
        assert mock_session.run.call_count >= 1

    @pytest.mark.asyncio
    async def test_record_event_async(self, async_service, mock_async_handler):
        """Test async event recording."""
        event = await async_service.record_event_async(
            project_id="project-123",
            entity_id="entity-456",
            event_type="CREATED",
            details={"test": "value"},
            actor="user-1"
        )

        assert event is not None
        assert event.project_id == "project-123"
        assert event.entity_id == "entity-456"
        assert event.event_type == "CREATED"

    @pytest.mark.asyncio
    async def test_get_entity_timeline_async(self, async_service, mock_async_handler):
        """Test async entity timeline retrieval."""
        _, _, mock_result = mock_async_handler
        mock_result.data = AsyncMock(return_value=[
            {
                "te": {
                    "event_id": "event-1",
                    "entity_id": "entity-456",
                    "project_id": "project-123",
                    "event_type": "CREATED",
                    "timestamp": "2024-01-15T10:30:00",
                    "details": "{}",
                    "actor": None
                }
            }
        ])

        events = await async_service.get_entity_timeline_async(
            project_id="project-123",
            entity_id="entity-456"
        )

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_project_timeline_async(self, async_service, mock_async_handler):
        """Test async project timeline retrieval."""
        events = await async_service.get_project_timeline_async(
            project_id="project-123",
            limit=50
        )

        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_get_relationship_history_async(self, async_service, mock_async_handler):
        """Test async relationship history retrieval."""
        events = await async_service.get_relationship_history_async(
            project_id="project-123",
            entity1_id="entity-1",
            entity2_id="entity-2"
        )

        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_analyze_activity_async(self, async_service, mock_async_handler):
        """Test async activity analysis."""
        _, _, mock_result = mock_async_handler
        mock_result.data = AsyncMock(return_value=[
            {"event_type": "CREATED", "event_date": "2024-01-15", "timestamp": datetime(2024, 1, 15)},
        ])

        result = await async_service.analyze_activity_async(
            project_id="project-123",
            entity_id="entity-456",
            days=30
        )

        assert "total_events" in result
        assert "events_by_type" in result
        assert "analysis_period_days" in result


# ==================== Singleton Tests ====================


class TestTimelineServiceSingleton:
    """Tests for timeline service singleton management."""

    def test_get_timeline_service_requires_handler_first_call(self):
        """Test that first call requires a handler."""
        # Reset singleton
        set_timeline_service(None)

        with pytest.raises(ValueError, match="neo4j_handler is required"):
            get_timeline_service()

    def test_get_timeline_service_creates_singleton(self):
        """Test that get_timeline_service creates a singleton."""
        # Reset singleton
        set_timeline_service(None)

        handler = MagicMock()
        service1 = get_timeline_service(handler)
        service2 = get_timeline_service()

        assert service1 is service2

    def test_set_timeline_service(self):
        """Test setting the timeline service singleton."""
        handler = MagicMock()
        service = TimelineService(handler)

        set_timeline_service(service)
        retrieved = get_timeline_service()

        assert retrieved is service

    def test_set_timeline_service_to_none(self):
        """Test clearing the timeline service singleton."""
        handler = MagicMock()
        set_timeline_service(TimelineService(handler))
        set_timeline_service(None)

        with pytest.raises(ValueError):
            get_timeline_service()


# ==================== Edge Cases ====================


class TestTimelineServiceEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.run_query = MagicMock(return_value=[])
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a TimelineService with a mock handler."""
        return TimelineService(mock_handler)

    def test_record_event_with_complex_details(self, service, mock_handler):
        """Test recording event with complex nested details."""
        details = {
            "changes": {
                "profile": {
                    "core": {
                        "name": {"old": "John", "new": "Jane"},
                        "email": {"old": ["a@b.com"], "new": ["c@d.com"]}
                    }
                }
            },
            "metadata": {
                "source": "api",
                "version": 1
            }
        }

        event = service.record_event(
            project_id="project-123",
            entity_id="entity-456",
            event_type="UPDATED",
            details=details
        )

        assert event.details == details

    def test_parse_event_record_with_neo4j_datetime(self, service):
        """Test parsing record with Neo4j datetime object."""
        mock_datetime = MagicMock()
        mock_datetime.to_native.return_value = datetime(2024, 1, 15, 10, 30)

        record = {
            "event_id": "event-1",
            "entity_id": "entity-1",
            "project_id": "project-1",
            "event_type": "CREATED",
            "timestamp": mock_datetime,
            "details": "{}",
            "actor": None
        }

        event = service._parse_event_record(record)

        assert event.timestamp.year == 2024
        assert event.timestamp.month == 1
        assert event.timestamp.day == 15

    def test_parse_event_record_with_json_details(self, service):
        """Test parsing record with JSON string details."""
        record = {
            "event_id": "event-1",
            "entity_id": "entity-1",
            "project_id": "project-1",
            "event_type": "CREATED",
            "timestamp": "2024-01-15T10:30:00",
            "details": '{"key": "value", "nested": {"a": 1}}',
            "actor": None
        }

        event = service._parse_event_record(record)

        assert event.details == {"key": "value", "nested": {"a": 1}}

    def test_parse_event_record_with_invalid_json_details(self, service):
        """Test parsing record with invalid JSON details."""
        record = {
            "event_id": "event-1",
            "entity_id": "entity-1",
            "project_id": "project-1",
            "event_type": "CREATED",
            "timestamp": "2024-01-15T10:30:00",
            "details": "not valid json {",
            "actor": None
        }

        event = service._parse_event_record(record)

        assert event.details == {}

    def test_analyze_activity_with_zero_days(self, service, mock_handler):
        """Test activity analysis with zero days (edge case)."""
        result = service.analyze_activity(
            project_id="project-123",
            entity_id="entity-456",
            days=0  # Edge case - should handle gracefully
        )

        # Should not raise, should return valid result
        assert result["analysis_period_days"] == 0

    def test_get_timeline_empty_project(self, service, mock_handler):
        """Test getting timeline for project with no events."""
        mock_handler.run_query.return_value = []

        events = service.get_project_timeline(
            project_id="empty-project",
            limit=100
        )

        assert events == []

    def test_handler_without_run_query(self):
        """Test service behavior with handler lacking run_query method."""
        handler = MagicMock(spec=[])  # No methods
        service = TimelineService(handler)

        # Should not raise, just log warning
        event = service.record_event(
            project_id="project-123",
            entity_id="entity-456",
            event_type="CREATED"
        )

        assert event is not None


# ==================== Integration-like Tests ====================


class TestTimelineServiceIntegration:
    """Integration-like tests for timeline service workflows."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler with realistic behavior."""
        handler = MagicMock()
        handler.run_query = MagicMock(return_value=[])
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a TimelineService with a mock handler."""
        return TimelineService(mock_handler)

    def test_entity_lifecycle_timeline(self, service, mock_handler):
        """Test tracking an entity through its lifecycle."""
        entity_id = "entity-123"
        project_id = "project-456"

        # Create entity
        create_event = service.record_event(
            project_id=project_id,
            entity_id=entity_id,
            event_type="CREATED",
            details={"initial_data": {"name": "John Doe"}},
            actor="user-1"
        )

        # Update entity
        update_event = service.record_event(
            project_id=project_id,
            entity_id=entity_id,
            event_type="UPDATED",
            details={
                "field": "email",
                "old_value": None,
                "new_value": "john@example.com"
            },
            actor="user-1"
        )

        # Add relationship
        relationship_event = service.record_event(
            project_id=project_id,
            entity_id=entity_id,
            event_type="RELATIONSHIP_ADDED",
            details={
                "target_entity": "entity-789",
                "relationship_type": "KNOWS"
            },
            actor="user-2"
        )

        assert create_event.event_type == "CREATED"
        assert update_event.event_type == "UPDATED"
        assert relationship_event.event_type == "RELATIONSHIP_ADDED"

        # All events should have different IDs
        assert len({create_event.event_id, update_event.event_id, relationship_event.event_id}) == 3

    def test_relationship_tracking_workflow(self, service, mock_handler):
        """Test tracking relationships between entities."""
        project_id = "project-123"
        entity1_id = "entity-1"
        entity2_id = "entity-2"

        # Add relationship from entity1 to entity2
        add_event = service.record_event(
            project_id=project_id,
            entity_id=entity1_id,
            event_type="RELATIONSHIP_ADDED",
            details={
                "target_entity": entity2_id,
                "relationship_type": "TAGGED"
            }
        )

        # Update relationship
        update_event = service.record_event(
            project_id=project_id,
            entity_id=entity1_id,
            event_type="RELATIONSHIP_UPDATED",
            details={
                "target_entity": entity2_id,
                "old_type": "TAGGED",
                "new_type": "COLLEAGUE"
            }
        )

        # Remove relationship
        remove_event = service.record_event(
            project_id=project_id,
            entity_id=entity1_id,
            event_type="RELATIONSHIP_REMOVED",
            details={
                "target_entity": entity2_id,
                "relationship_type": "COLLEAGUE"
            }
        )

        assert add_event.event_type == "RELATIONSHIP_ADDED"
        assert update_event.event_type == "RELATIONSHIP_UPDATED"
        assert remove_event.event_type == "RELATIONSHIP_REMOVED"

    def test_activity_analysis_workflow(self, service, mock_handler):
        """Test activity analysis over time."""
        # Simulate activity data over multiple days
        mock_handler.run_query.return_value = [
            {"event_type": "CREATED", "event_date": "2024-01-10", "timestamp": datetime(2024, 1, 10, 9, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-10", "timestamp": datetime(2024, 1, 10, 10, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-11", "timestamp": datetime(2024, 1, 11, 9, 0)},
            {"event_type": "RELATIONSHIP_ADDED", "event_date": "2024-01-11", "timestamp": datetime(2024, 1, 11, 10, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-12", "timestamp": datetime(2024, 1, 12, 9, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-12", "timestamp": datetime(2024, 1, 12, 10, 0)},
            {"event_type": "UPDATED", "event_date": "2024-01-12", "timestamp": datetime(2024, 1, 12, 11, 0)},
        ]

        result = service.analyze_activity(
            project_id="project-123",
            entity_id="entity-456",
            days=30
        )

        assert result["total_events"] == 7
        assert result["events_by_type"]["CREATED"] == 1
        assert result["events_by_type"]["UPDATED"] == 5
        assert result["events_by_type"]["RELATIONSHIP_ADDED"] == 1
        assert result["most_active_day"] == "2024-01-12"  # 3 events
        assert result["first_event"] == "2024-01-10T09:00:00"
        assert result["last_event"] == "2024-01-12T11:00:00"


# ==================== API Router Tests ====================


class TestTimelineRouter:
    """Tests for the timeline router endpoints."""

    @pytest.fixture
    def mock_neo4j_handler(self):
        """Create a mock Neo4j handler for API tests."""
        handler = MagicMock()
        handler.get_project = MagicMock(return_value={
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project"
        })
        handler.get_person = MagicMock(return_value={
            "id": "entity-456",
            "created_at": "2024-01-15T10:30:00",
            "profile": {}
        })
        handler.run_query = MagicMock(return_value=[])
        return handler

    def test_timeline_router_import(self):
        """Test that timeline router can be imported."""
        from api.routers.timeline import router
        assert router is not None

    def test_timeline_models_import(self):
        """Test that all response models can be imported."""
        from api.routers.timeline import (
            TimelineEventResponse,
            TimelineListResponse,
            EntityTimelineResponse,
            RelationshipHistoryResponse,
            ActivityAnalysisResponse,
            RecordEventRequest,
            RecordEventResponse,
        )

        # Verify models have expected fields
        assert hasattr(TimelineEventResponse, "model_fields")
        assert hasattr(TimelineListResponse, "model_fields")
        assert hasattr(EntityTimelineResponse, "model_fields")
        assert hasattr(RelationshipHistoryResponse, "model_fields")
        assert hasattr(ActivityAnalysisResponse, "model_fields")
        assert hasattr(RecordEventRequest, "model_fields")
        assert hasattr(RecordEventResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.timeline import _parse_datetime, _event_to_response

        # Test datetime parsing
        assert _parse_datetime(None) is None
        assert _parse_datetime("2024-01-15T10:30:00") is not None
        assert _parse_datetime("invalid") is None

        # Test event to response conversion
        event = TimelineEvent(
            entity_id="entity-1",
            project_id="project-1",
            event_type="CREATED"
        )
        response = _event_to_response(event)
        assert response.entity_id == "entity-1"
        assert response.project_id == "project-1"
        assert response.event_type == "CREATED"
