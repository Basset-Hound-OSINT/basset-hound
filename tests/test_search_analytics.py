"""
Tests for the Search Analytics Service

Comprehensive test coverage for:
- SearchEvent dataclass
- PopularQuery dataclass
- SearchAnalytics class methods
- Event recording and click tracking
- Popular queries calculation
- Zero result detection
- Volume aggregation
- CTR calculation
- Query suggestions
- Search trends
- Cleanup operations
- Export functionality
- Singleton management
- Thread safety
- API router endpoints
"""

import json
import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from api.services.search_analytics import (
    SearchEvent,
    PopularQuery,
    SearchAnalytics,
    get_search_analytics,
    set_search_analytics,
)


# ==================== SearchEvent Tests ====================


class TestSearchEvent:
    """Tests for SearchEvent dataclass."""

    def test_event_creation_with_defaults(self):
        """Test creating an event with default values."""
        event = SearchEvent(query="test query")

        assert event.query == "test query"
        assert event.id is not None
        assert event.timestamp is not None
        assert event.project_id is None
        assert event.user_id is None
        assert event.result_count == 0
        assert event.duration_ms == 0
        assert event.entity_types == []
        assert event.filters_used == {}
        assert event.clicked_results == []

    def test_event_creation_with_all_fields(self):
        """Test creating an event with all fields specified."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)

        event = SearchEvent(
            id="custom-id",
            query="john doe",
            project_id="project-123",
            user_id="user-456",
            timestamp=timestamp,
            result_count=5,
            duration_ms=150,
            entity_types=["Person", "Organization"],
            filters_used={"field": "email"},
            clicked_results=["entity-1", "entity-2"],
        )

        assert event.id == "custom-id"
        assert event.query == "john doe"
        assert event.project_id == "project-123"
        assert event.user_id == "user-456"
        assert event.timestamp == timestamp
        assert event.result_count == 5
        assert event.duration_ms == 150
        assert event.entity_types == ["Person", "Organization"]
        assert event.filters_used == {"field": "email"}
        assert event.clicked_results == ["entity-1", "entity-2"]

    def test_event_to_dict(self):
        """Test converting an event to a dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        event = SearchEvent(
            id="event-123",
            query="test",
            project_id="project-1",
            timestamp=timestamp,
            result_count=10,
        )

        result = event.to_dict()

        assert result["id"] == "event-123"
        assert result["query"] == "test"
        assert result["project_id"] == "project-1"
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert result["result_count"] == 10

    def test_event_from_dict(self):
        """Test creating an event from a dictionary."""
        data = {
            "id": "event-123",
            "query": "john doe",
            "project_id": "project-456",
            "user_id": "user-789",
            "timestamp": "2024-01-15T10:30:00",
            "result_count": 5,
            "duration_ms": 100,
            "entity_types": ["Person"],
            "filters_used": {"type": "email"},
            "clicked_results": ["e1", "e2"],
        }

        event = SearchEvent.from_dict(data)

        assert event.id == "event-123"
        assert event.query == "john doe"
        assert event.project_id == "project-456"
        assert event.user_id == "user-789"
        assert event.result_count == 5
        assert event.duration_ms == 100
        assert event.entity_types == ["Person"]
        assert event.filters_used == {"type": "email"}
        assert event.clicked_results == ["e1", "e2"]

    def test_event_from_dict_with_z_timestamp(self):
        """Test creating an event with Z-suffixed timestamp."""
        data = {
            "query": "test",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        event = SearchEvent.from_dict(data)
        assert event.timestamp is not None

    def test_event_from_dict_with_missing_fields(self):
        """Test creating an event from incomplete dictionary."""
        data = {}

        event = SearchEvent.from_dict(data)

        assert event.id is not None
        assert event.query == ""
        assert event.project_id is None
        assert event.result_count == 0

    def test_event_auto_generates_uuid(self):
        """Test that events auto-generate unique UUIDs."""
        event1 = SearchEvent(query="test")
        event2 = SearchEvent(query="test")

        assert event1.id != event2.id

    def test_event_timestamp_defaults_to_utcnow(self):
        """Test that timestamp defaults to UTC now."""
        before = datetime.utcnow()
        event = SearchEvent(query="test")
        after = datetime.utcnow()

        assert before <= event.timestamp <= after


# ==================== PopularQuery Tests ====================


class TestPopularQuery:
    """Tests for PopularQuery dataclass."""

    def test_popular_query_creation(self):
        """Test creating a PopularQuery."""
        last_searched = datetime(2024, 1, 15, 10, 30, 0)

        pq = PopularQuery(
            query="john doe",
            count=42,
            avg_results=5.5,
            last_searched=last_searched,
        )

        assert pq.query == "john doe"
        assert pq.count == 42
        assert pq.avg_results == 5.5
        assert pq.last_searched == last_searched

    def test_popular_query_to_dict(self):
        """Test converting PopularQuery to dictionary."""
        last_searched = datetime(2024, 1, 15, 10, 30, 0)
        pq = PopularQuery(
            query="test",
            count=10,
            avg_results=3.456,
            last_searched=last_searched,
        )

        result = pq.to_dict()

        assert result["query"] == "test"
        assert result["count"] == 10
        assert result["avg_results"] == 3.46  # Rounded to 2 decimal places
        assert result["last_searched"] == "2024-01-15T10:30:00"


# ==================== SearchAnalytics Basic Tests ====================


class TestSearchAnalyticsBasic:
    """Basic tests for SearchAnalytics class."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance."""
        return SearchAnalytics(retention_days=30)

    def test_initialization(self, analytics):
        """Test analytics service initialization."""
        assert analytics.retention_days == 30
        assert analytics.get_event_count() == 0

    def test_retention_days_property(self, analytics):
        """Test retention days getter and setter."""
        analytics.retention_days = 60
        assert analytics.retention_days == 60

        # Test minimum value
        analytics.retention_days = 0
        assert analytics.retention_days == 1

    def test_record_search_basic(self, analytics):
        """Test recording a basic search event."""
        event = analytics.record_search(query="test query")

        assert event is not None
        assert event.query == "test query"
        assert analytics.get_event_count() == 1

    def test_record_search_with_all_params(self, analytics):
        """Test recording search with all parameters."""
        event = analytics.record_search(
            query="John Doe",
            result_count=5,
            duration_ms=150,
            project_id="project-123",
            user_id="user-456",
            entity_types=["Person"],
            filters_used={"field": "email"},
        )

        assert event.query == "john doe"  # Normalized to lowercase
        assert event.result_count == 5
        assert event.duration_ms == 150
        assert event.project_id == "project-123"
        assert event.user_id == "user-456"
        assert event.entity_types == ["Person"]
        assert event.filters_used == {"field": "email"}

    def test_record_search_normalizes_query(self, analytics):
        """Test that queries are normalized (lowercase, trimmed)."""
        event = analytics.record_search(query="  JOHN DOE  ")
        assert event.query == "john doe"

    def test_get_event(self, analytics):
        """Test retrieving an event by ID."""
        event = analytics.record_search(query="test")
        retrieved = analytics.get_event(event.id)

        assert retrieved is not None
        assert retrieved.id == event.id

    def test_get_event_not_found(self, analytics):
        """Test retrieving a non-existent event."""
        retrieved = analytics.get_event("nonexistent-id")
        assert retrieved is None

    def test_clear_all_events(self, analytics):
        """Test clearing all events."""
        analytics.record_search(query="test1")
        analytics.record_search(query="test2")
        assert analytics.get_event_count() == 2

        cleared = analytics.clear_all_events()

        assert cleared == 2
        assert analytics.get_event_count() == 0


# ==================== Click Tracking Tests ====================


class TestClickTracking:
    """Tests for click tracking functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance."""
        return SearchAnalytics()

    def test_record_click(self, analytics):
        """Test recording a click on a search result."""
        event = analytics.record_search(query="test", result_count=5)

        success = analytics.record_click(event.id, "entity-123")

        assert success is True
        assert "entity-123" in event.clicked_results

    def test_record_click_multiple(self, analytics):
        """Test recording multiple clicks."""
        event = analytics.record_search(query="test", result_count=5)

        analytics.record_click(event.id, "entity-1")
        analytics.record_click(event.id, "entity-2")

        assert len(event.clicked_results) == 2
        assert "entity-1" in event.clicked_results
        assert "entity-2" in event.clicked_results

    def test_record_click_duplicate(self, analytics):
        """Test that duplicate clicks are not recorded."""
        event = analytics.record_search(query="test", result_count=5)

        analytics.record_click(event.id, "entity-1")
        analytics.record_click(event.id, "entity-1")

        assert len(event.clicked_results) == 1

    def test_record_click_event_not_found(self, analytics):
        """Test recording click for non-existent event."""
        success = analytics.record_click("nonexistent-id", "entity-123")
        assert success is False


# ==================== Popular Queries Tests ====================


class TestPopularQueries:
    """Tests for popular queries functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance with test data."""
        a = SearchAnalytics()
        # Add test search events
        for _ in range(5):
            a.record_search(query="john doe", result_count=3)
        for _ in range(3):
            a.record_search(query="jane smith", result_count=2)
        for _ in range(1):
            a.record_search(query="bob jones", result_count=1)
        return a

    def test_get_popular_queries(self, analytics):
        """Test getting popular queries."""
        popular = analytics.get_popular_queries(limit=10)

        assert len(popular) == 3
        assert popular[0].query == "john doe"
        assert popular[0].count == 5
        assert popular[1].query == "jane smith"
        assert popular[1].count == 3
        assert popular[2].query == "bob jones"
        assert popular[2].count == 1

    def test_get_popular_queries_limit(self, analytics):
        """Test limiting popular queries."""
        popular = analytics.get_popular_queries(limit=2)

        assert len(popular) == 2
        assert popular[0].query == "john doe"
        assert popular[1].query == "jane smith"

    def test_get_popular_queries_avg_results(self, analytics):
        """Test that average results is calculated correctly."""
        popular = analytics.get_popular_queries(limit=10)

        assert popular[0].avg_results == 3.0  # john doe
        assert popular[1].avg_results == 2.0  # jane smith
        assert popular[2].avg_results == 1.0  # bob jones

    def test_get_popular_queries_empty(self):
        """Test getting popular queries with no data."""
        analytics = SearchAnalytics()
        popular = analytics.get_popular_queries()

        assert popular == []

    def test_get_popular_queries_by_project(self):
        """Test filtering popular queries by project."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test1", project_id="project-a", result_count=1)
        analytics.record_search(query="test1", project_id="project-a", result_count=1)
        analytics.record_search(query="test2", project_id="project-b", result_count=1)

        popular = analytics.get_popular_queries(project_id="project-a")

        assert len(popular) == 1
        assert popular[0].query == "test1"
        assert popular[0].count == 2


# ==================== Zero Result Queries Tests ====================


class TestZeroResultQueries:
    """Tests for zero result queries functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance with test data."""
        a = SearchAnalytics()
        # Add events with results
        a.record_search(query="john doe", result_count=5)
        # Add zero result events
        for _ in range(3):
            a.record_search(query="asdfghjkl", result_count=0)
        for _ in range(2):
            a.record_search(query="qwertyuiop", result_count=0)
        return a

    def test_get_zero_result_queries(self, analytics):
        """Test getting zero result queries."""
        zero_results = analytics.get_zero_result_queries(limit=10)

        assert len(zero_results) == 2
        assert zero_results[0].query == "asdfghjkl"
        assert zero_results[0].count == 3
        assert zero_results[0].avg_results == 0.0
        assert zero_results[1].query == "qwertyuiop"
        assert zero_results[1].count == 2

    def test_get_zero_result_queries_limit(self, analytics):
        """Test limiting zero result queries."""
        zero_results = analytics.get_zero_result_queries(limit=1)

        assert len(zero_results) == 1
        assert zero_results[0].query == "asdfghjkl"

    def test_get_zero_result_queries_empty(self):
        """Test when there are no zero result queries."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test", result_count=5)

        zero_results = analytics.get_zero_result_queries()
        assert zero_results == []


# ==================== Search Volume Tests ====================


class TestSearchVolume:
    """Tests for search volume functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance with test data."""
        a = SearchAnalytics()

        # Add events on different days
        base_date = datetime(2024, 1, 15, 10, 0, 0)

        # Day 1: 3 searches
        for i in range(3):
            event = a.record_search(query=f"query{i}")
            event.timestamp = base_date

        # Day 2: 5 searches
        day2 = base_date + timedelta(days=1)
        for i in range(5):
            event = a.record_search(query=f"query{i}")
            event.timestamp = day2

        return a

    def test_get_search_volume_by_day(self, analytics):
        """Test getting search volume by day."""
        volume = analytics.get_search_volume(granularity="day")

        assert "2024-01-15" in volume
        assert "2024-01-16" in volume
        assert volume["2024-01-15"] == 3
        assert volume["2024-01-16"] == 5

    def test_get_search_volume_by_hour(self):
        """Test getting search volume by hour."""
        analytics = SearchAnalytics()
        base_time = datetime(2024, 1, 15, 10, 0, 0)

        for i in range(3):
            event = analytics.record_search(query="test")
            event.timestamp = base_time

        hour2 = base_time.replace(hour=11)
        for i in range(2):
            event = analytics.record_search(query="test")
            event.timestamp = hour2

        volume = analytics.get_search_volume(granularity="hour")

        assert "2024-01-15 10:00" in volume
        assert "2024-01-15 11:00" in volume
        assert volume["2024-01-15 10:00"] == 3
        assert volume["2024-01-15 11:00"] == 2

    def test_get_search_volume_by_week(self):
        """Test getting search volume by week."""
        analytics = SearchAnalytics()

        # Week 3 of 2024
        week3 = datetime(2024, 1, 15, 10, 0, 0)
        for i in range(4):
            event = analytics.record_search(query="test")
            event.timestamp = week3

        volume = analytics.get_search_volume(granularity="week")

        assert "2024-W03" in volume
        assert volume["2024-W03"] == 4

    def test_get_search_volume_empty(self):
        """Test getting volume with no data."""
        analytics = SearchAnalytics()
        volume = analytics.get_search_volume()

        assert volume == {}


# ==================== Average Results Tests ====================


class TestAverageResults:
    """Tests for average results calculation."""

    def test_get_avg_results_per_query(self):
        """Test calculating average results per query."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test1", result_count=10)
        analytics.record_search(query="test2", result_count=20)
        analytics.record_search(query="test3", result_count=30)

        avg = analytics.get_avg_results_per_query()

        assert avg == 20.0

    def test_get_avg_results_with_zeros(self):
        """Test average results including zero-result searches."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test1", result_count=10)
        analytics.record_search(query="test2", result_count=0)

        avg = analytics.get_avg_results_per_query()

        assert avg == 5.0

    def test_get_avg_results_empty(self):
        """Test average results with no data."""
        analytics = SearchAnalytics()
        avg = analytics.get_avg_results_per_query()

        assert avg == 0.0


# ==================== Click-Through Rate Tests ====================


class TestClickThroughRate:
    """Tests for CTR calculation."""

    def test_get_ctr(self):
        """Test calculating click-through rate."""
        analytics = SearchAnalytics()

        # 4 searches, 2 with clicks
        event1 = analytics.record_search(query="test1")
        analytics.record_click(event1.id, "entity-1")

        event2 = analytics.record_search(query="test2")
        analytics.record_click(event2.id, "entity-2")

        analytics.record_search(query="test3")
        analytics.record_search(query="test4")

        ctr = analytics.get_click_through_rate()

        assert ctr == 0.5  # 2/4 = 0.5

    def test_get_ctr_all_clicks(self):
        """Test CTR when all searches have clicks."""
        analytics = SearchAnalytics()

        for i in range(3):
            event = analytics.record_search(query=f"test{i}")
            analytics.record_click(event.id, f"entity-{i}")

        ctr = analytics.get_click_through_rate()

        assert ctr == 1.0

    def test_get_ctr_no_clicks(self):
        """Test CTR when no searches have clicks."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test1")
        analytics.record_search(query="test2")

        ctr = analytics.get_click_through_rate()

        assert ctr == 0.0

    def test_get_ctr_empty(self):
        """Test CTR with no data."""
        analytics = SearchAnalytics()
        ctr = analytics.get_click_through_rate()

        assert ctr == 0.0


# ==================== Query Suggestions Tests ====================


class TestQuerySuggestions:
    """Tests for query suggestions functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance with test data."""
        a = SearchAnalytics()
        # Add searches with similar prefixes
        for _ in range(5):
            a.record_search(query="john doe")
        for _ in range(3):
            a.record_search(query="john smith")
        for _ in range(2):
            a.record_search(query="johnny")
        a.record_search(query="jane doe")
        return a

    def test_get_query_suggestions(self, analytics):
        """Test getting query suggestions."""
        suggestions = analytics.get_query_suggestions(prefix="joh", limit=5)

        assert len(suggestions) == 3
        assert suggestions[0] == "john doe"  # Most popular
        assert suggestions[1] == "john smith"
        assert suggestions[2] == "johnny"

    def test_get_query_suggestions_limit(self, analytics):
        """Test limiting suggestions."""
        suggestions = analytics.get_query_suggestions(prefix="joh", limit=2)

        assert len(suggestions) == 2

    def test_get_query_suggestions_no_match(self, analytics):
        """Test suggestions with no matches."""
        suggestions = analytics.get_query_suggestions(prefix="xyz")

        assert suggestions == []

    def test_get_query_suggestions_empty_prefix(self, analytics):
        """Test suggestions with empty prefix."""
        suggestions = analytics.get_query_suggestions(prefix="")

        assert suggestions == []


# ==================== Search Trends Tests ====================


class TestSearchTrends:
    """Tests for search trends functionality."""

    def test_get_search_trends(self):
        """Test getting search trends for a query."""
        analytics = SearchAnalytics()

        base_date = datetime(2024, 1, 15, 10, 0, 0)

        # Day 1: 3 searches for "john doe"
        for _ in range(3):
            event = analytics.record_search(query="john doe")
            event.timestamp = base_date

        # Day 2: 5 searches for "john doe"
        day2 = base_date + timedelta(days=1)
        for _ in range(5):
            event = analytics.record_search(query="john doe")
            event.timestamp = day2

        # Other query (should not appear)
        event = analytics.record_search(query="jane smith")
        event.timestamp = base_date

        trends = analytics.get_search_trends(query="john doe", granularity="day")

        assert len(trends) == 2
        assert trends["2024-01-15"] == 3
        assert trends["2024-01-16"] == 5

    def test_get_search_trends_no_data(self):
        """Test getting trends for non-existent query."""
        analytics = SearchAnalytics()
        analytics.record_search(query="test")

        trends = analytics.get_search_trends(query="nonexistent")

        assert trends == {}


# ==================== Cleanup Tests ====================


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_old_events(self):
        """Test cleaning up old events."""
        analytics = SearchAnalytics(retention_days=7)

        # Add an old event
        old_event = analytics.record_search(query="old")
        old_event.timestamp = datetime.utcnow() - timedelta(days=10)

        # Add a recent event
        analytics.record_search(query="new")

        removed = analytics.cleanup_old_events()

        assert removed == 1
        assert analytics.get_event_count() == 1

    def test_cleanup_custom_retention(self):
        """Test cleanup with custom retention period."""
        analytics = SearchAnalytics(retention_days=30)

        # Add event 5 days old
        event = analytics.record_search(query="test")
        event.timestamp = datetime.utcnow() - timedelta(days=5)

        # Cleanup with 3 day retention
        removed = analytics.cleanup_old_events(older_than_days=3)

        assert removed == 1
        assert analytics.get_event_count() == 0

    def test_cleanup_preserves_recent_events(self):
        """Test that cleanup preserves recent events."""
        analytics = SearchAnalytics(retention_days=30)

        # Add recent events
        for i in range(5):
            analytics.record_search(query=f"test{i}")

        removed = analytics.cleanup_old_events()

        assert removed == 0
        assert analytics.get_event_count() == 5


# ==================== Export Tests ====================


class TestExport:
    """Tests for export functionality."""

    @pytest.fixture
    def analytics(self):
        """Create a fresh SearchAnalytics instance with test data."""
        a = SearchAnalytics()
        a.record_search(query="test1", result_count=5)
        a.record_search(query="test2", result_count=0)
        event = a.record_search(query="test1", result_count=3)
        a.record_click(event.id, "entity-1")
        return a

    def test_export_analytics(self, analytics):
        """Test exporting analytics data."""
        export = analytics.export_analytics()

        assert "generated_at" in export
        assert "filters" in export
        assert "summary" in export
        assert "popular_queries" in export
        assert "zero_result_queries" in export
        assert "volume_by_day" in export

    def test_export_analytics_summary(self, analytics):
        """Test export summary data."""
        export = analytics.export_analytics()
        summary = export["summary"]

        assert summary["total_searches"] == 3
        assert summary["unique_queries"] == 2
        assert "avg_results_per_query" in summary
        assert "click_through_rate" in summary

    def test_export_with_events(self, analytics):
        """Test export including raw events."""
        export = analytics.export_analytics(include_events=True)

        assert "events" in export
        assert len(export["events"]) == 3


# ==================== Date Range Filtering Tests ====================


class TestDateRangeFiltering:
    """Tests for date range filtering across methods."""

    @pytest.fixture
    def analytics(self):
        """Create analytics with events spanning multiple days."""
        a = SearchAnalytics()

        # Past events
        past = datetime(2024, 1, 10, 10, 0, 0)
        for i in range(3):
            event = a.record_search(query="old query")
            event.timestamp = past

        # Recent events
        recent = datetime(2024, 1, 15, 10, 0, 0)
        for i in range(5):
            event = a.record_search(query="new query")
            event.timestamp = recent

        return a

    def test_popular_queries_date_filter(self, analytics):
        """Test date filtering on popular queries."""
        start_date = datetime(2024, 1, 14, 0, 0, 0)

        popular = analytics.get_popular_queries(start_date=start_date)

        assert len(popular) == 1
        assert popular[0].query == "new query"
        assert popular[0].count == 5

    def test_volume_date_filter(self, analytics):
        """Test date filtering on volume."""
        end_date = datetime(2024, 1, 12, 0, 0, 0)

        volume = analytics.get_search_volume(end_date=end_date)

        assert "2024-01-10" in volume
        assert "2024-01-15" not in volume

    def test_ctr_date_filter(self, analytics):
        """Test date filtering on CTR."""
        # Add click to recent event
        event = analytics.record_search(query="clicked")
        event.timestamp = datetime(2024, 1, 15, 11, 0, 0)
        analytics.record_click(event.id, "entity-1")

        start_date = datetime(2024, 1, 14, 0, 0, 0)
        ctr = analytics.get_click_through_rate(start_date=start_date)

        # Should only consider events after start_date
        # 6 events (5 "new query" + 1 "clicked"), 1 with click
        assert ctr == pytest.approx(1/6, rel=0.01)


# ==================== Singleton Tests ====================


class TestSingleton:
    """Tests for singleton management."""

    def test_get_search_analytics_creates_singleton(self):
        """Test that get_search_analytics creates a singleton."""
        set_search_analytics(None)

        service1 = get_search_analytics()
        service2 = get_search_analytics()

        assert service1 is service2

    def test_set_search_analytics(self):
        """Test setting the singleton."""
        custom = SearchAnalytics(retention_days=60)
        set_search_analytics(custom)

        retrieved = get_search_analytics()

        assert retrieved is custom
        assert retrieved.retention_days == 60

    def test_set_search_analytics_to_none(self):
        """Test clearing the singleton."""
        set_search_analytics(SearchAnalytics())
        set_search_analytics(None)

        # Next call should create new instance
        new_service = get_search_analytics()
        assert new_service is not None


# ==================== Thread Safety Tests ====================


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_record_search(self):
        """Test concurrent search recording."""
        analytics = SearchAnalytics()
        num_threads = 10
        searches_per_thread = 100

        def record_searches():
            for i in range(searches_per_thread):
                analytics.record_search(query=f"query-{threading.current_thread().name}-{i}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_searches)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert analytics.get_event_count() == num_threads * searches_per_thread

    def test_concurrent_click_recording(self):
        """Test concurrent click recording."""
        analytics = SearchAnalytics()
        event = analytics.record_search(query="test", result_count=100)
        num_threads = 10
        clicks_per_thread = 10

        def record_clicks(thread_id):
            for i in range(clicks_per_thread):
                analytics.record_click(event.id, f"entity-{thread_id}-{i}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_clicks, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All unique clicks should be recorded
        assert len(event.clicked_results) == num_threads * clicks_per_thread


# ==================== Edge Cases Tests ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query(self):
        """Test recording search with empty query."""
        analytics = SearchAnalytics()
        event = analytics.record_search(query="")

        assert event.query == ""

    def test_whitespace_query(self):
        """Test recording search with whitespace query."""
        analytics = SearchAnalytics()
        event = analytics.record_search(query="   ")

        assert event.query == ""

    def test_special_characters_in_query(self):
        """Test recording search with special characters."""
        analytics = SearchAnalytics()
        event = analytics.record_search(query="email:test@example.com")

        assert event.query == "email:test@example.com"

    def test_large_result_count(self):
        """Test recording search with large result count."""
        analytics = SearchAnalytics()
        event = analytics.record_search(query="test", result_count=1000000)

        assert event.result_count == 1000000

    def test_negative_duration(self):
        """Test that negative duration is accepted (edge case)."""
        analytics = SearchAnalytics()
        # Negative duration shouldn't break anything
        event = analytics.record_search(query="test", duration_ms=-100)

        assert event.duration_ms == -100


# ==================== Router Tests ====================


class TestAnalyticsRouter:
    """Tests for the analytics router endpoints."""

    def test_router_import(self):
        """Test that router can be imported."""
        from api.routers.analytics import router, project_analytics_router
        assert router is not None
        assert project_analytics_router is not None

    def test_response_models_import(self):
        """Test that all response models can be imported."""
        from api.routers.analytics import (
            PopularQueryResponse,
            PopularQueriesResponse,
            SearchVolumeResponse,
            CTRResponse,
            QuerySuggestionsResponse,
            SearchTrendsResponse,
            ProjectAnalyticsResponse,
            CleanupResponse,
            RecordSearchRequest,
            RecordSearchResponse,
            RecordClickRequest,
            RecordClickResponse,
            ExportAnalyticsResponse,
        )

        # Verify models have expected fields
        assert hasattr(PopularQueryResponse, "model_fields")
        assert hasattr(PopularQueriesResponse, "model_fields")
        assert hasattr(SearchVolumeResponse, "model_fields")
        assert hasattr(CTRResponse, "model_fields")
        assert hasattr(QuerySuggestionsResponse, "model_fields")
        assert hasattr(SearchTrendsResponse, "model_fields")
        assert hasattr(ProjectAnalyticsResponse, "model_fields")
        assert hasattr(CleanupResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.analytics import _parse_datetime, _popular_query_to_response

        # Test datetime parsing
        assert _parse_datetime(None) is None
        assert _parse_datetime("2024-01-15T10:30:00") is not None
        assert _parse_datetime("invalid") is None

        # Test popular query conversion
        pq = PopularQuery(
            query="test",
            count=10,
            avg_results=5.0,
            last_searched=datetime(2024, 1, 15)
        )
        response = _popular_query_to_response(pq)
        assert response.query == "test"
        assert response.count == 10


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration-like tests for complete workflows."""

    def test_complete_search_workflow(self):
        """Test a complete search analytics workflow."""
        analytics = SearchAnalytics(retention_days=30)

        # Record multiple searches
        for i in range(10):
            event = analytics.record_search(
                query="john doe",
                result_count=5,
                duration_ms=100 + i * 10,
                project_id="project-1"
            )
            # Record clicks on some searches
            if i % 2 == 0:
                analytics.record_click(event.id, f"entity-{i}")

        # Verify popular queries
        popular = analytics.get_popular_queries(limit=1)
        assert popular[0].query == "john doe"
        assert popular[0].count == 10
        assert popular[0].avg_results == 5.0

        # Verify CTR
        ctr = analytics.get_click_through_rate()
        assert ctr == 0.5  # 5 out of 10 searches had clicks

        # Verify volume
        volume = analytics.get_search_volume()
        total = sum(volume.values())
        assert total == 10

        # Verify export
        export = analytics.export_analytics(include_events=True)
        assert export["summary"]["total_searches"] == 10
        assert len(export["events"]) == 10

    def test_project_isolation(self):
        """Test that project filtering properly isolates data."""
        analytics = SearchAnalytics()

        # Add searches for different projects
        for i in range(5):
            analytics.record_search(query="test", project_id="project-a", result_count=i)

        for i in range(3):
            analytics.record_search(query="test", project_id="project-b", result_count=i)

        # Verify project A
        popular_a = analytics.get_popular_queries(project_id="project-a")
        assert popular_a[0].count == 5

        # Verify project B
        popular_b = analytics.get_popular_queries(project_id="project-b")
        assert popular_b[0].count == 3

        # Verify global
        popular_all = analytics.get_popular_queries()
        assert popular_all[0].count == 8
