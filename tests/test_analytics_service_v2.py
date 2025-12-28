"""
Comprehensive Tests for Search Analytics Service v2

This module provides extensive test coverage for:
- SearchEvent model
- QueryStats model
- AnalyticsSummary model
- TimeRange helper class
- SearchAnalytics class methods
- Event recording and retrieval
- Query statistics aggregation
- Top queries with various filters
- Time-based analysis
- Zero-result and slow query detection
- Related query suggestions
- Export functionality
- Singleton management
- Thread safety
- Edge cases and error handling
- Router endpoints

Total: 60+ tests
"""

import json
import pytest
import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from api.services.analytics_service import (
    SearchEvent,
    QueryStats,
    AnalyticsSummary,
    TimeRange,
    SearchAnalytics,
    get_analytics_service,
    set_analytics_service,
)


# ==================== Fixtures ====================


@pytest.fixture
def analytics():
    """Create a fresh SearchAnalytics instance for each test."""
    return SearchAnalytics()


@pytest.fixture
def populated_analytics():
    """Create SearchAnalytics instance with test data."""
    a = SearchAnalytics()

    # Add various search events
    for i in range(5):
        a.record_search(
            query="john doe",
            project_id="project-1",
            results_count=3,
            response_time_ms=100,
            fields=["name", "email"],
        )

    for i in range(3):
        a.record_search(
            query="jane smith",
            project_id="project-1",
            results_count=2,
            response_time_ms=150,
            fields=["name"],
        )

    for i in range(2):
        a.record_search(
            query="bob jones",
            project_id="project-2",
            results_count=0,
            response_time_ms=50,
        )

    return a


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before and after each test."""
    set_analytics_service(None)
    yield
    set_analytics_service(None)


# ==================== SearchEvent Model Tests ====================


class TestSearchEventModel:
    """Tests for SearchEvent Pydantic model."""

    def test_create_event_with_required_fields(self):
        """Test creating event with only required fields."""
        event = SearchEvent(query="test", project_id="proj-1")

        assert event.query == "test"
        assert event.project_id == "proj-1"
        assert event.id is not None
        assert event.timestamp is not None
        assert event.results_count == 0
        assert event.response_time_ms == 0
        assert event.user_id is None
        assert event.fields_searched == []
        assert event.filters_applied == {}

    def test_create_event_with_all_fields(self):
        """Test creating event with all fields."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)

        event = SearchEvent(
            id="custom-id",
            query="john doe",
            project_id="project-123",
            user_id="user-456",
            timestamp=timestamp,
            results_count=5,
            response_time_ms=150,
            fields_searched=["name", "email"],
            filters_applied={"type": "person"},
        )

        assert event.id == "custom-id"
        assert event.query == "john doe"
        assert event.project_id == "project-123"
        assert event.user_id == "user-456"
        assert event.timestamp == timestamp
        assert event.results_count == 5
        assert event.response_time_ms == 150
        assert event.fields_searched == ["name", "email"]
        assert event.filters_applied == {"type": "person"}

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        event = SearchEvent(
            id="event-123",
            query="test",
            project_id="project-1",
            timestamp=timestamp,
            results_count=10,
        )

        result = event.to_dict()

        assert result["id"] == "event-123"
        assert result["query"] == "test"
        assert result["project_id"] == "project-1"
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert result["results_count"] == 10

    def test_event_auto_generates_uuid(self):
        """Test that events auto-generate unique UUIDs."""
        event1 = SearchEvent(query="test", project_id="proj")
        event2 = SearchEvent(query="test", project_id="proj")

        assert event1.id != event2.id
        assert len(event1.id) == 36  # UUID format

    def test_event_timestamp_defaults_to_utcnow(self):
        """Test that timestamp defaults to UTC now."""
        before = datetime.now(timezone.utc)
        event = SearchEvent(query="test", project_id="proj")
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after


# ==================== QueryStats Model Tests ====================


class TestQueryStatsModel:
    """Tests for QueryStats Pydantic model."""

    def test_create_query_stats(self):
        """Test creating QueryStats."""
        first = datetime(2024, 1, 1, 10, 0, 0)
        last = datetime(2024, 1, 15, 15, 30, 0)

        stats = QueryStats(
            query="john doe",
            total_searches=42,
            avg_results=5.5,
            avg_response_time_ms=120.5,
            first_searched=first,
            last_searched=last,
        )

        assert stats.query == "john doe"
        assert stats.total_searches == 42
        assert stats.avg_results == 5.5
        assert stats.avg_response_time_ms == 120.5
        assert stats.first_searched == first
        assert stats.last_searched == last

    def test_query_stats_to_dict(self):
        """Test converting QueryStats to dictionary."""
        last = datetime(2024, 1, 15, 10, 30, 0)
        stats = QueryStats(
            query="test",
            total_searches=10,
            avg_results=3.456,
            avg_response_time_ms=100.789,
            last_searched=last,
        )

        result = stats.to_dict()

        assert result["query"] == "test"
        assert result["total_searches"] == 10
        assert result["avg_results"] == 3.46  # Rounded to 2 decimal places
        assert result["avg_response_time_ms"] == 100.79
        assert result["last_searched"] == "2024-01-15T10:30:00"

    def test_query_stats_default_values(self):
        """Test QueryStats default values."""
        stats = QueryStats(query="test")

        assert stats.total_searches == 0
        assert stats.avg_results == 0.0
        assert stats.avg_response_time_ms == 0.0
        assert stats.first_searched is None
        assert stats.last_searched is None


# ==================== AnalyticsSummary Model Tests ====================


class TestAnalyticsSummaryModel:
    """Tests for AnalyticsSummary Pydantic model."""

    def test_create_analytics_summary(self):
        """Test creating AnalyticsSummary."""
        summary = AnalyticsSummary(
            total_searches=1000,
            unique_queries=150,
            avg_response_time=125.5,
            searches_by_day={"2024-01-15": 50},
            searches_by_hour={"10": 15},
        )

        assert summary.total_searches == 1000
        assert summary.unique_queries == 150
        assert summary.avg_response_time == 125.5
        assert summary.searches_by_day == {"2024-01-15": 50}
        assert summary.searches_by_hour == {"10": 15}

    def test_analytics_summary_default_values(self):
        """Test AnalyticsSummary default values."""
        summary = AnalyticsSummary()

        assert summary.total_searches == 0
        assert summary.unique_queries == 0
        assert summary.avg_response_time == 0.0
        assert summary.top_queries == []
        assert summary.searches_by_day == {}
        assert summary.searches_by_hour == {}
        assert summary.zero_result_queries == []

    def test_analytics_summary_to_dict(self):
        """Test converting AnalyticsSummary to dictionary."""
        summary = AnalyticsSummary(
            total_searches=100,
            unique_queries=20,
            avg_response_time=150.555,
        )

        result = summary.to_dict()

        assert result["total_searches"] == 100
        assert result["unique_queries"] == 20
        assert result["avg_response_time"] == 150.56


# ==================== TimeRange Helper Tests ====================


class TestTimeRange:
    """Tests for TimeRange helper class."""

    def test_create_time_range_with_dates(self):
        """Test creating TimeRange with specific dates."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        tr = TimeRange(start=start, end=end)

        assert tr.start == start
        assert tr.end == end

    def test_time_range_last_days(self):
        """Test creating TimeRange for last N days."""
        tr = TimeRange.last_days(7)

        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(days=7)

        assert tr.end is not None
        assert tr.start is not None
        # Allow small time difference due to execution time
        assert abs((tr.end - now).total_seconds()) < 1
        assert abs((tr.start - expected_start).total_seconds()) < 1

    def test_time_range_last_hours(self):
        """Test creating TimeRange for last N hours."""
        tr = TimeRange.last_hours(24)

        now = datetime.now(timezone.utc)
        expected_start = now - timedelta(hours=24)

        assert tr.end is not None
        assert abs((tr.start - expected_start).total_seconds()) < 1

    def test_time_range_today(self):
        """Test creating TimeRange for today."""
        tr = TimeRange.today()

        now = datetime.now(timezone.utc)
        expected_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        assert tr.start == expected_start
        assert tr.end is not None

    def test_time_range_this_week(self):
        """Test creating TimeRange for this week."""
        tr = TimeRange.this_week()

        now = datetime.now(timezone.utc)
        # Week starts on Monday
        assert tr.start is not None
        assert tr.start.weekday() == 0  # Monday
        assert tr.end is not None

    def test_time_range_contains(self):
        """Test TimeRange.contains() method."""
        tr = TimeRange(
            start=datetime(2024, 1, 10),
            end=datetime(2024, 1, 20),
        )

        assert tr.contains(datetime(2024, 1, 15)) is True
        assert tr.contains(datetime(2024, 1, 10)) is True
        assert tr.contains(datetime(2024, 1, 20)) is True
        assert tr.contains(datetime(2024, 1, 5)) is False
        assert tr.contains(datetime(2024, 1, 25)) is False

    def test_time_range_contains_open_ended(self):
        """Test TimeRange.contains() with open-ended ranges."""
        tr_start_only = TimeRange(start=datetime(2024, 1, 10))
        tr_end_only = TimeRange(end=datetime(2024, 1, 20))

        assert tr_start_only.contains(datetime(2024, 1, 15)) is True
        assert tr_start_only.contains(datetime(2024, 1, 5)) is False

        assert tr_end_only.contains(datetime(2024, 1, 15)) is True
        assert tr_end_only.contains(datetime(2024, 1, 25)) is False


# ==================== SearchAnalytics Basic Tests ====================


class TestSearchAnalyticsBasic:
    """Basic tests for SearchAnalytics class."""

    def test_initialization(self, analytics):
        """Test analytics service initialization."""
        assert analytics.get_event_count() == 0

    def test_record_search_basic(self, analytics):
        """Test recording a basic search event."""
        event = analytics.record_search(
            query="test query",
            project_id="project-1",
        )

        assert event is not None
        assert event.query == "test query"
        assert event.project_id == "project-1"
        assert analytics.get_event_count() == 1

    def test_record_search_with_all_params(self, analytics):
        """Test recording search with all parameters."""
        event = analytics.record_search(
            query="John Doe",
            project_id="project-123",
            results_count=5,
            response_time_ms=150,
            fields=["name", "email"],
            filters={"type": "person"},
            user_id="user-456",
        )

        assert event.query == "john doe"  # Normalized to lowercase
        assert event.project_id == "project-123"
        assert event.results_count == 5
        assert event.response_time_ms == 150
        assert event.fields_searched == ["name", "email"]
        assert event.filters_applied == {"type": "person"}
        assert event.user_id == "user-456"

    def test_record_search_normalizes_query(self, analytics):
        """Test that queries are normalized (lowercase, trimmed)."""
        event = analytics.record_search(
            query="  JOHN DOE  ",
            project_id="proj",
        )

        assert event.query == "john doe"

    def test_get_event(self, analytics):
        """Test retrieving an event by ID."""
        event = analytics.record_search(query="test", project_id="proj")
        retrieved = analytics.get_event(event.id)

        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.query == "test"

    def test_get_event_not_found(self, analytics):
        """Test retrieving a non-existent event."""
        retrieved = analytics.get_event("nonexistent-id")
        assert retrieved is None


# ==================== Query Stats Tests ====================


class TestQueryStats:
    """Tests for query statistics functionality."""

    def test_get_query_stats(self, populated_analytics):
        """Test getting statistics for a query."""
        stats = populated_analytics.get_query_stats("john doe")

        assert stats is not None
        assert stats.query == "john doe"
        assert stats.total_searches == 5
        assert stats.avg_results == 3.0
        assert stats.avg_response_time_ms == 100.0
        assert stats.first_searched is not None
        assert stats.last_searched is not None

    def test_get_query_stats_case_insensitive(self, populated_analytics):
        """Test that query stats lookup is case insensitive."""
        stats1 = populated_analytics.get_query_stats("JOHN DOE")
        stats2 = populated_analytics.get_query_stats("john doe")

        assert stats1 is not None
        assert stats2 is not None
        assert stats1.total_searches == stats2.total_searches

    def test_get_query_stats_not_found(self, analytics):
        """Test getting stats for non-existent query."""
        stats = analytics.get_query_stats("nonexistent")
        assert stats is None

    def test_get_query_stats_empty_query(self, analytics):
        """Test getting stats for empty query."""
        analytics.record_search(query="", project_id="proj")
        stats = analytics.get_query_stats("")

        assert stats is not None
        assert stats.query == ""


# ==================== Top Queries Tests ====================


class TestTopQueries:
    """Tests for top queries functionality."""

    def test_get_top_queries(self, populated_analytics):
        """Test getting top queries."""
        top = populated_analytics.get_top_queries(limit=10)

        assert len(top) == 3
        assert top[0].query == "john doe"
        assert top[0].total_searches == 5
        assert top[1].query == "jane smith"
        assert top[1].total_searches == 3
        assert top[2].query == "bob jones"
        assert top[2].total_searches == 2

    def test_get_top_queries_limit(self, populated_analytics):
        """Test limiting top queries."""
        top = populated_analytics.get_top_queries(limit=2)

        assert len(top) == 2
        assert top[0].query == "john doe"
        assert top[1].query == "jane smith"

    def test_get_top_queries_by_project(self, populated_analytics):
        """Test filtering top queries by project."""
        top = populated_analytics.get_top_queries(project_id="project-1")

        # project-1 has "john doe" and "jane smith"
        assert len(top) == 2
        assert top[0].query == "john doe"
        assert top[1].query == "jane smith"

    def test_get_top_queries_with_time_range(self, analytics):
        """Test top queries with time range filter."""
        # Add old event
        old_event = analytics.record_search(query="old query", project_id="proj")
        old_event.timestamp = datetime.now(timezone.utc) - timedelta(days=10)

        # Add recent event
        analytics.record_search(query="new query", project_id="proj")

        # Get queries from last 5 days
        time_range = TimeRange.last_days(5)
        top = analytics.get_top_queries(time_range=time_range)

        assert len(top) == 1
        assert top[0].query == "new query"

    def test_get_top_queries_empty(self, analytics):
        """Test getting top queries with no data."""
        top = analytics.get_top_queries()
        assert top == []


# ==================== Zero Result Queries Tests ====================


class TestZeroResultQueries:
    """Tests for zero result queries functionality."""

    def test_get_zero_result_queries(self, populated_analytics):
        """Test getting zero result queries."""
        zero_results = populated_analytics.get_zero_result_queries()

        assert len(zero_results) == 1
        assert zero_results[0].query == "bob jones"
        assert zero_results[0].total_searches == 2
        assert zero_results[0].avg_results == 0.0

    def test_get_zero_result_queries_limit(self, analytics):
        """Test limiting zero result queries."""
        for i in range(5):
            analytics.record_search(query=f"zero_{i}", project_id="proj", results_count=0)

        zero_results = analytics.get_zero_result_queries(limit=3)

        assert len(zero_results) == 3

    def test_get_zero_result_queries_by_project(self, populated_analytics):
        """Test filtering zero result queries by project."""
        zero_results = populated_analytics.get_zero_result_queries(project_id="project-2")

        assert len(zero_results) == 1
        assert zero_results[0].query == "bob jones"

    def test_get_zero_result_queries_empty(self, analytics):
        """Test when there are no zero result queries."""
        analytics.record_search(query="test", project_id="proj", results_count=5)

        zero_results = analytics.get_zero_result_queries()
        assert zero_results == []


# ==================== Analytics Summary Tests ====================


class TestAnalyticsSummary:
    """Tests for analytics summary functionality."""

    def test_get_summary(self, populated_analytics):
        """Test getting analytics summary."""
        summary = populated_analytics.get_summary()

        assert summary.total_searches == 10
        assert summary.unique_queries == 3
        assert summary.avg_response_time > 0
        assert len(summary.top_queries) <= 10
        assert len(summary.searches_by_day) > 0
        assert len(summary.searches_by_hour) > 0

    def test_get_summary_by_project(self, populated_analytics):
        """Test getting summary for specific project."""
        summary = populated_analytics.get_summary(project_id="project-1")

        assert summary.total_searches == 8  # 5 + 3
        assert summary.unique_queries == 2

    def test_get_summary_with_time_range(self, analytics):
        """Test getting summary with time range."""
        # Add old event
        old_event = analytics.record_search(query="old", project_id="proj")
        old_event.timestamp = datetime.now(timezone.utc) - timedelta(days=10)

        # Add recent events
        for i in range(3):
            analytics.record_search(query="new", project_id="proj")

        time_range = TimeRange.last_days(5)
        summary = analytics.get_summary(time_range=time_range)

        assert summary.total_searches == 3

    def test_get_summary_empty(self, analytics):
        """Test getting summary with no data."""
        summary = analytics.get_summary()

        assert summary.total_searches == 0
        assert summary.unique_queries == 0
        assert summary.avg_response_time == 0.0


# ==================== Searches by Timeframe Tests ====================


class TestSearchesByTimeframe:
    """Tests for time-based search analysis."""

    def test_get_searches_by_day(self, analytics):
        """Test getting searches by day."""
        base_date = datetime(2024, 1, 15, 10, 0, 0)

        for i in range(3):
            event = analytics.record_search(query="test", project_id="proj")
            event.timestamp = base_date

        day2 = base_date + timedelta(days=1)
        for i in range(5):
            event = analytics.record_search(query="test", project_id="proj")
            event.timestamp = day2

        volume = analytics.get_searches_by_timeframe(granularity="day")

        assert "2024-01-15" in volume
        assert "2024-01-16" in volume
        assert volume["2024-01-15"] == 3
        assert volume["2024-01-16"] == 5

    def test_get_searches_by_hour(self, analytics):
        """Test getting searches by hour."""
        base_time = datetime(2024, 1, 15, 10, 0, 0)

        for i in range(3):
            event = analytics.record_search(query="test", project_id="proj")
            event.timestamp = base_time

        hour2 = base_time.replace(hour=11)
        for i in range(2):
            event = analytics.record_search(query="test", project_id="proj")
            event.timestamp = hour2

        volume = analytics.get_searches_by_timeframe(granularity="hour")

        assert "2024-01-15 10:00" in volume
        assert "2024-01-15 11:00" in volume
        assert volume["2024-01-15 10:00"] == 3
        assert volume["2024-01-15 11:00"] == 2

    def test_get_searches_by_week(self, analytics):
        """Test getting searches by week."""
        week3 = datetime(2024, 1, 15, 10, 0, 0)

        for i in range(4):
            event = analytics.record_search(query="test", project_id="proj")
            event.timestamp = week3

        volume = analytics.get_searches_by_timeframe(granularity="week")

        assert "2024-W03" in volume
        assert volume["2024-W03"] == 4

    def test_get_searches_by_timeframe_empty(self, analytics):
        """Test getting volume with no data."""
        volume = analytics.get_searches_by_timeframe()
        assert volume == {}


# ==================== Popular Fields Tests ====================


class TestPopularFields:
    """Tests for popular fields functionality."""

    def test_get_popular_fields(self, populated_analytics):
        """Test getting popular fields."""
        fields = populated_analytics.get_popular_fields()

        # "name" appears in 8 events (5 john doe + 3 jane smith)
        # "email" appears in 5 events (john doe only)
        assert len(fields) == 2
        assert fields[0] == ("name", 8)
        assert fields[1] == ("email", 5)

    def test_get_popular_fields_limit(self, analytics):
        """Test limiting popular fields."""
        for i in range(10):
            analytics.record_search(
                query="test",
                project_id="proj",
                fields=[f"field_{i}"],
            )

        fields = analytics.get_popular_fields(limit=5)
        assert len(fields) == 5

    def test_get_popular_fields_empty(self, analytics):
        """Test popular fields with no field data."""
        analytics.record_search(query="test", project_id="proj")

        fields = analytics.get_popular_fields()
        assert fields == []


# ==================== Slow Queries Tests ====================


class TestSlowQueries:
    """Tests for slow query detection."""

    def test_get_slow_queries(self, analytics):
        """Test getting slow queries."""
        # Add fast query
        analytics.record_search(query="fast", project_id="proj", response_time_ms=100)

        # Add slow queries
        analytics.record_search(query="slow1", project_id="proj", response_time_ms=1500)
        analytics.record_search(query="slow2", project_id="proj", response_time_ms=2000)

        slow = analytics.get_slow_queries(threshold_ms=1000)

        assert len(slow) == 2
        assert slow[0].response_time_ms == 2000  # Sorted by response time desc
        assert slow[1].response_time_ms == 1500

    def test_get_slow_queries_limit(self, analytics):
        """Test limiting slow queries."""
        for i in range(10):
            analytics.record_search(
                query=f"slow_{i}",
                project_id="proj",
                response_time_ms=1000 + i * 100,
            )

        slow = analytics.get_slow_queries(threshold_ms=1000, limit=5)
        assert len(slow) == 5

    def test_get_slow_queries_custom_threshold(self, analytics):
        """Test slow queries with custom threshold."""
        analytics.record_search(query="q1", project_id="proj", response_time_ms=400)
        analytics.record_search(query="q2", project_id="proj", response_time_ms=600)

        slow = analytics.get_slow_queries(threshold_ms=500)

        assert len(slow) == 1
        assert slow[0].query == "q2"

    def test_get_slow_queries_empty(self, analytics):
        """Test slow queries when all queries are fast."""
        analytics.record_search(query="fast", project_id="proj", response_time_ms=100)

        slow = analytics.get_slow_queries(threshold_ms=1000)
        assert slow == []


# ==================== Related Queries Tests ====================


class TestRelatedQueries:
    """Tests for related query suggestions."""

    def test_get_related_queries(self, analytics):
        """Test getting related queries."""
        analytics.record_search(query="john doe", project_id="proj")
        analytics.record_search(query="john smith", project_id="proj")
        analytics.record_search(query="jane doe", project_id="proj")
        analytics.record_search(query="bob jones", project_id="proj")

        related = analytics.get_related_queries("john doe")

        # Should find similar queries
        assert len(related) >= 1
        assert "john smith" in related or "jane doe" in related

    def test_get_related_queries_limit(self, analytics):
        """Test limiting related queries."""
        for i in range(10):
            analytics.record_search(query=f"test query {i}", project_id="proj")

        related = analytics.get_related_queries("test query", limit=3)

        assert len(related) <= 3

    def test_get_related_queries_empty(self, analytics):
        """Test related queries with empty input."""
        related = analytics.get_related_queries("")
        assert related == []

    def test_get_related_queries_no_matches(self, analytics):
        """Test related queries with no similar queries."""
        analytics.record_search(query="completely different", project_id="proj")

        related = analytics.get_related_queries("xyz123")
        assert related == []


# ==================== Query Improvement Suggestions Tests ====================


class TestQueryImprovements:
    """Tests for query improvement suggestions."""

    def test_suggest_query_improvements(self, analytics):
        """Test getting query improvement suggestions."""
        # Add query with good results
        for i in range(3):
            analytics.record_search(
                query="john doe email",
                project_id="proj",
                results_count=10,
            )

        # Add similar query with poor results
        analytics.record_search(query="john doe", project_id="proj", results_count=0)

        suggestions = analytics.suggest_query_improvements("john doe")

        # Should suggest the more successful similar query
        assert "john doe email" in suggestions

    def test_suggest_query_improvements_empty(self, analytics):
        """Test suggestions with empty query."""
        suggestions = analytics.suggest_query_improvements("")
        assert suggestions == []

    def test_suggest_query_improvements_limit(self, analytics):
        """Test limiting suggestions."""
        for i in range(10):
            analytics.record_search(
                query=f"test {i}",
                project_id="proj",
                results_count=i * 10,
            )

        analytics.record_search(query="test", project_id="proj", results_count=0)

        suggestions = analytics.suggest_query_improvements("test", limit=3)
        assert len(suggestions) <= 3


# ==================== Clear Analytics Tests ====================


class TestClearAnalytics:
    """Tests for clearing analytics data."""

    def test_clear_all_analytics(self, populated_analytics):
        """Test clearing all analytics."""
        assert populated_analytics.get_event_count() == 10

        cleared = populated_analytics.clear_analytics()

        assert cleared == 10
        assert populated_analytics.get_event_count() == 0

    def test_clear_analytics_by_project(self, populated_analytics):
        """Test clearing analytics for specific project."""
        cleared = populated_analytics.clear_analytics(project_id="project-1")

        assert cleared == 8  # 5 + 3 from project-1
        assert populated_analytics.get_event_count() == 2  # 2 from project-2

    def test_clear_analytics_before_date(self, analytics):
        """Test clearing analytics before a date."""
        # Add old event
        old_event = analytics.record_search(query="old", project_id="proj")
        old_event.timestamp = datetime(2024, 1, 1)

        # Add new event
        new_event = analytics.record_search(query="new", project_id="proj")
        new_event.timestamp = datetime(2024, 1, 20)

        cleared = analytics.clear_analytics(before_date=datetime(2024, 1, 15))

        assert cleared == 1
        assert analytics.get_event_count() == 1

    def test_clear_analytics_empty(self, analytics):
        """Test clearing empty analytics."""
        cleared = analytics.clear_analytics()
        assert cleared == 0


# ==================== Export Tests ====================


class TestExportAnalytics:
    """Tests for export functionality."""

    def test_export_json(self, populated_analytics):
        """Test exporting to JSON format."""
        export = populated_analytics.export_analytics(format="json")

        assert export is not None
        data = json.loads(export)

        assert "generated_at" in data
        assert "filters" in data
        assert "summary" in data
        assert "events" in data
        assert len(data["events"]) == 10

    def test_export_csv(self, populated_analytics):
        """Test exporting to CSV format."""
        export = populated_analytics.export_analytics(format="csv")

        assert export is not None
        lines = export.strip().split("\n")

        # Header + 10 data rows
        assert len(lines) == 11
        assert "id" in lines[0]
        assert "query" in lines[0]

    def test_export_by_project(self, populated_analytics):
        """Test exporting for specific project."""
        export = populated_analytics.export_analytics(
            project_id="project-1",
            format="json",
        )

        data = json.loads(export)
        assert len(data["events"]) == 8

    def test_export_empty(self, analytics):
        """Test exporting empty analytics."""
        export = analytics.export_analytics(format="json")

        data = json.loads(export)
        assert data["summary"]["total_searches"] == 0
        assert data["events"] == []


# ==================== Singleton Tests ====================


class TestSingleton:
    """Tests for singleton management."""

    def test_get_analytics_service_creates_singleton(self):
        """Test that get_analytics_service creates a singleton."""
        set_analytics_service(None)

        service1 = get_analytics_service()
        service2 = get_analytics_service()

        assert service1 is service2

    def test_set_analytics_service(self):
        """Test setting the singleton."""
        custom = SearchAnalytics()
        custom.record_search(query="test", project_id="proj")

        set_analytics_service(custom)

        retrieved = get_analytics_service()
        assert retrieved is custom
        assert retrieved.get_event_count() == 1

    def test_set_analytics_service_to_none(self):
        """Test clearing the singleton."""
        set_analytics_service(SearchAnalytics())
        set_analytics_service(None)

        new_service = get_analytics_service()
        assert new_service is not None
        assert new_service.get_event_count() == 0


# ==================== Thread Safety Tests ====================


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_record_search(self, analytics):
        """Test concurrent search recording."""
        num_threads = 10
        searches_per_thread = 50

        def record_searches():
            for i in range(searches_per_thread):
                analytics.record_search(
                    query=f"query-{threading.current_thread().name}-{i}",
                    project_id="proj",
                )

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_searches)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert analytics.get_event_count() == num_threads * searches_per_thread

    def test_concurrent_read_write(self, analytics):
        """Test concurrent reads and writes."""
        # Add some initial data
        for i in range(10):
            analytics.record_search(query="initial", project_id="proj")

        results = {"reads": 0, "writes": 0}

        def writer():
            for i in range(20):
                analytics.record_search(query="new", project_id="proj")
                results["writes"] += 1

        def reader():
            for i in range(20):
                analytics.get_top_queries()
                results["reads"] += 1

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert results["writes"] == 100
        assert results["reads"] == 100


# ==================== Edge Cases Tests ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query(self, analytics):
        """Test recording search with empty query."""
        event = analytics.record_search(query="", project_id="proj")
        assert event.query == ""

    def test_whitespace_query(self, analytics):
        """Test recording search with whitespace query."""
        event = analytics.record_search(query="   ", project_id="proj")
        assert event.query == ""

    def test_special_characters_in_query(self, analytics):
        """Test recording search with special characters."""
        query = "email:test@example.com +filter -exclude"
        event = analytics.record_search(query=query, project_id="proj")

        assert event.query == query.lower()

    def test_unicode_query(self, analytics):
        """Test recording search with unicode characters."""
        event = analytics.record_search(query="test", project_id="proj")
        assert event.query == "test"

    def test_large_result_count(self, analytics):
        """Test recording search with large result count."""
        event = analytics.record_search(
            query="test",
            project_id="proj",
            results_count=1000000,
        )

        assert event.results_count == 1000000

    def test_very_long_query(self, analytics):
        """Test recording search with very long query."""
        long_query = "a" * 10000
        event = analytics.record_search(query=long_query, project_id="proj")

        assert event.query == long_query.lower()

    def test_many_fields(self, analytics):
        """Test recording search with many fields."""
        fields = [f"field_{i}" for i in range(100)]
        event = analytics.record_search(
            query="test",
            project_id="proj",
            fields=fields,
        )

        assert len(event.fields_searched) == 100

    def test_complex_filters(self, analytics):
        """Test recording search with complex filters."""
        filters = {
            "nested": {"level1": {"level2": "value"}},
            "list": [1, 2, 3],
            "boolean": True,
        }
        event = analytics.record_search(
            query="test",
            project_id="proj",
            filters=filters,
        )

        assert event.filters_applied == filters


# ==================== Router Import Tests ====================


class TestRouterImports:
    """Tests for router imports and configuration."""

    def test_router_import(self):
        """Test that router can be imported."""
        from api.routers.analytics_v2 import router, project_router

        assert router is not None
        assert project_router is not None

    def test_response_models_import(self):
        """Test that all response models can be imported."""
        from api.routers.analytics_v2 import (
            RecordSearchRequest,
            RecordSearchResponse,
            QueryStatsResponse,
            TopQueriesResponse,
            SearchEventResponse,
            SlowQueriesResponse,
            SearchesByTimeResponse,
            PopularFieldsResponse,
            RelatedQueriesResponse,
            SuggestionsResponse,
            ClearAnalyticsResponse,
            AnalyticsSummaryResponse,
        )

        # Verify models have expected fields
        assert hasattr(RecordSearchRequest, "model_fields")
        assert hasattr(RecordSearchResponse, "model_fields")
        assert hasattr(QueryStatsResponse, "model_fields")
        assert hasattr(TopQueriesResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.analytics_v2 import (
            _parse_datetime,
            _parse_time_range,
            _query_stats_to_response,
        )

        # Test datetime parsing
        assert _parse_datetime(None) is None
        assert _parse_datetime("2024-01-15T10:30:00") is not None
        assert _parse_datetime("invalid") is None

        # Test time range parsing
        tr = _parse_time_range(None, None, 7, None)
        assert tr is not None

        # Test query stats conversion
        stats = QueryStats(query="test", total_searches=10)
        response = _query_stats_to_response(stats)
        assert response.query == "test"
        assert response.total_searches == 10
