"""
Search Analytics Service for Basset Hound OSINT Platform.

This module provides comprehensive search analytics tracking including:
- Recording search events with detailed metadata
- Tracking query statistics and aggregations
- Analyzing popular queries and trends
- Identifying zero-result and slow queries
- Computing search volume metrics by time
- Generating query suggestions and related queries
- Exporting analytics data in multiple formats

Features:
- Thread-safe in-memory storage with aggregation
- Time-based analysis helpers
- Project-scoped analytics support
- JSON and CSV export
"""

import csv
import io
import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ----- Pydantic Models -----


class SearchEvent(BaseModel):
    """
    Represents a single search event.

    Attributes:
        id: Unique identifier for the event
        query: The search query string
        project_id: Project ID the search was scoped to
        user_id: Optional user ID who performed the search
        timestamp: When the search occurred
        results_count: Number of results returned
        response_time_ms: Search execution time in milliseconds
        fields_searched: List of field names that were searched
        filters_applied: Dictionary of filters applied to the search
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "john doe",
                "project_id": "project-123",
                "user_id": "user-456",
                "timestamp": "2024-01-15T10:30:00",
                "results_count": 5,
                "response_time_ms": 150,
                "fields_searched": ["name", "email"],
                "filters_applied": {"entity_type": "Person"}
            }
        }
    )

    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str = Field(..., description="The search query string")
    project_id: str = Field(..., description="Project ID the search was scoped to")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results_count: int = Field(0, ge=0, description="Number of results returned")
    response_time_ms: int = Field(0, ge=0, description="Response time in milliseconds")
    fields_searched: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary representation."""
        return {
            "id": self.id,
            "query": self.query,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "results_count": self.results_count,
            "response_time_ms": self.response_time_ms,
            "fields_searched": self.fields_searched,
            "filters_applied": self.filters_applied,
        }


class QueryStats(BaseModel):
    """
    Aggregated statistics for a specific query.

    Attributes:
        query: The search query string
        total_searches: Total number of times this query was searched
        avg_results: Average number of results returned
        avg_response_time_ms: Average response time in milliseconds
        first_searched: Timestamp of first search
        last_searched: Timestamp of most recent search
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "total_searches": 42,
                "avg_results": 5.5,
                "avg_response_time_ms": 120.5,
                "first_searched": "2024-01-01T10:00:00",
                "last_searched": "2024-01-15T15:30:00"
            }
        }
    )

    query: str = Field(..., description="The search query string")
    total_searches: int = Field(0, ge=0, description="Total number of searches")
    avg_results: float = Field(0.0, ge=0, description="Average number of results")
    avg_response_time_ms: float = Field(0.0, ge=0, description="Average response time")
    first_searched: Optional[datetime] = Field(None, description="First search timestamp")
    last_searched: Optional[datetime] = Field(None, description="Last search timestamp")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "total_searches": self.total_searches,
            "avg_results": round(self.avg_results, 2),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "first_searched": self.first_searched.isoformat() if self.first_searched else None,
            "last_searched": self.last_searched.isoformat() if self.last_searched else None,
        }


class AnalyticsSummary(BaseModel):
    """
    Overall analytics summary.

    Attributes:
        total_searches: Total number of search events
        unique_queries: Number of unique query strings
        avg_response_time: Average response time across all searches
        top_queries: List of top N most popular queries
        searches_by_day: Search counts grouped by day
        searches_by_hour: Search counts grouped by hour of day
        zero_result_queries: Queries that returned no results
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_searches": 1000,
                "unique_queries": 150,
                "avg_response_time": 125.5,
                "top_queries": [],
                "searches_by_day": {"2024-01-15": 50},
                "searches_by_hour": {"10": 15},
                "zero_result_queries": []
            }
        }
    )

    total_searches: int = Field(0, ge=0, description="Total number of searches")
    unique_queries: int = Field(0, ge=0, description="Number of unique queries")
    avg_response_time: float = Field(0.0, ge=0, description="Average response time")
    top_queries: List[QueryStats] = Field(default_factory=list)
    searches_by_day: Dict[str, int] = Field(default_factory=dict)
    searches_by_hour: Dict[str, int] = Field(default_factory=dict)
    zero_result_queries: List[QueryStats] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_searches": self.total_searches,
            "unique_queries": self.unique_queries,
            "avg_response_time": round(self.avg_response_time, 2),
            "top_queries": [q.to_dict() for q in self.top_queries],
            "searches_by_day": self.searches_by_day,
            "searches_by_hour": self.searches_by_hour,
            "zero_result_queries": [q.to_dict() for q in self.zero_result_queries],
        }


# ----- TimeRange helper -----


@dataclass
class TimeRange:
    """
    Represents a time range for filtering analytics data.

    Attributes:
        start: Start datetime (inclusive)
        end: End datetime (inclusive)
    """
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    @classmethod
    def last_days(cls, days: int) -> "TimeRange":
        """Create a TimeRange for the last N days."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return cls(start=start, end=end)

    @classmethod
    def last_hours(cls, hours: int) -> "TimeRange":
        """Create a TimeRange for the last N hours."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        return cls(start=start, end=end)

    @classmethod
    def today(cls) -> "TimeRange":
        """Create a TimeRange for today."""
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return cls(start=start, end=now)

    @classmethod
    def this_week(cls) -> "TimeRange":
        """Create a TimeRange for the current week."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        return cls(start=start, end=now)

    def contains(self, dt: datetime) -> bool:
        """Check if a datetime falls within this range."""
        if self.start and dt < self.start:
            return False
        if self.end and dt > self.end:
            return False
        return True


# ----- SearchAnalytics Service -----


class SearchAnalytics:
    """
    Service for tracking and analyzing search behavior.

    Provides methods for recording search events, computing statistics,
    and generating analytics reports with thread-safety.

    Usage:
        analytics = SearchAnalytics()

        # Record a search
        event = analytics.record_search(
            query="John Doe",
            project_id="project-123",
            results_count=5,
            response_time_ms=150
        )

        # Get query statistics
        stats = analytics.get_query_stats("john doe")

        # Get analytics summary
        summary = analytics.get_summary(project_id="project-123")

        # Get top queries
        top = analytics.get_top_queries(limit=10)
    """

    def __init__(self):
        """Initialize the search analytics service."""
        self._events: List[SearchEvent] = []
        self._events_by_id: Dict[str, SearchEvent] = {}
        self._lock = threading.RLock()

    def record_search(
        self,
        query: str,
        project_id: str,
        results_count: int = 0,
        response_time_ms: int = 0,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> SearchEvent:
        """
        Record a new search event.

        Args:
            query: The search query string
            project_id: Project ID the search was scoped to
            results_count: Number of results returned
            response_time_ms: Search execution time in milliseconds
            fields: Optional list of fields that were searched
            filters: Optional dictionary of filters applied
            user_id: Optional user ID who performed the search

        Returns:
            The created SearchEvent
        """
        normalized_query = query.strip().lower() if query else ""

        event = SearchEvent(
            query=normalized_query,
            project_id=project_id,
            user_id=user_id,
            results_count=results_count,
            response_time_ms=response_time_ms,
            fields_searched=fields or [],
            filters_applied=filters or {},
        )

        with self._lock:
            self._events.append(event)
            self._events_by_id[event.id] = event

        logger.debug(f"Recorded search event: query='{query}', project={project_id}, results={results_count}")
        return event

    def get_query_stats(self, query: str) -> Optional[QueryStats]:
        """
        Get aggregated statistics for a specific query.

        Args:
            query: The query string to get stats for

        Returns:
            QueryStats object or None if no searches found
        """
        normalized_query = query.strip().lower() if query else ""

        with self._lock:
            matching_events = [e for e in self._events if e.query == normalized_query]

            if not matching_events:
                return None

            total_results = sum(e.results_count for e in matching_events)
            total_response_time = sum(e.response_time_ms for e in matching_events)
            count = len(matching_events)

            # Sort by timestamp to get first and last
            sorted_events = sorted(matching_events, key=lambda e: e.timestamp)

            return QueryStats(
                query=normalized_query,
                total_searches=count,
                avg_results=total_results / count if count > 0 else 0.0,
                avg_response_time_ms=total_response_time / count if count > 0 else 0.0,
                first_searched=sorted_events[0].timestamp if sorted_events else None,
                last_searched=sorted_events[-1].timestamp if sorted_events else None,
            )

    def get_top_queries(
        self,
        project_id: Optional[str] = None,
        limit: int = 10,
        time_range: Optional[TimeRange] = None,
    ) -> List[QueryStats]:
        """
        Get the most frequently searched queries.

        Args:
            project_id: Optional project ID to filter by
            limit: Maximum number of queries to return
            time_range: Optional time range to filter by

        Returns:
            List of QueryStats sorted by total_searches descending
        """
        with self._lock:
            filtered = self._filter_events(project_id, time_range)

            # Aggregate by query
            query_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "count": 0,
                    "total_results": 0,
                    "total_response_time": 0,
                    "first_searched": None,
                    "last_searched": None,
                }
            )

            for event in filtered:
                if not event.query:
                    continue
                data = query_data[event.query]
                data["count"] += 1
                data["total_results"] += event.results_count
                data["total_response_time"] += event.response_time_ms

                if data["first_searched"] is None or event.timestamp < data["first_searched"]:
                    data["first_searched"] = event.timestamp
                if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                    data["last_searched"] = event.timestamp

            # Convert to QueryStats objects
            stats_list = []
            for query, data in query_data.items():
                count = data["count"]
                stats_list.append(QueryStats(
                    query=query,
                    total_searches=count,
                    avg_results=data["total_results"] / count if count > 0 else 0.0,
                    avg_response_time_ms=data["total_response_time"] / count if count > 0 else 0.0,
                    first_searched=data["first_searched"],
                    last_searched=data["last_searched"],
                ))

            # Sort by total_searches descending, then by query alphabetically
            stats_list.sort(key=lambda x: (-x.total_searches, x.query))
            return stats_list[:limit]

    def get_zero_result_queries(
        self,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[QueryStats]:
        """
        Get queries that returned zero results.

        Args:
            project_id: Optional project ID to filter by
            limit: Maximum number of queries to return

        Returns:
            List of QueryStats for queries with zero results
        """
        with self._lock:
            filtered = self._filter_events(project_id, None)

            # Filter to only zero-result events
            zero_result_events = [e for e in filtered if e.results_count == 0]

            # Aggregate by query
            query_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "count": 0,
                    "total_response_time": 0,
                    "first_searched": None,
                    "last_searched": None,
                }
            )

            for event in zero_result_events:
                if not event.query:
                    continue
                data = query_data[event.query]
                data["count"] += 1
                data["total_response_time"] += event.response_time_ms

                if data["first_searched"] is None or event.timestamp < data["first_searched"]:
                    data["first_searched"] = event.timestamp
                if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                    data["last_searched"] = event.timestamp

            # Convert to QueryStats objects
            stats_list = []
            for query, data in query_data.items():
                count = data["count"]
                stats_list.append(QueryStats(
                    query=query,
                    total_searches=count,
                    avg_results=0.0,
                    avg_response_time_ms=data["total_response_time"] / count if count > 0 else 0.0,
                    first_searched=data["first_searched"],
                    last_searched=data["last_searched"],
                ))

            # Sort by total_searches descending
            stats_list.sort(key=lambda x: (-x.total_searches, x.query))
            return stats_list[:limit]

    def get_summary(
        self,
        project_id: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
    ) -> AnalyticsSummary:
        """
        Get a comprehensive analytics summary.

        Args:
            project_id: Optional project ID to filter by
            time_range: Optional time range to filter by

        Returns:
            AnalyticsSummary object
        """
        with self._lock:
            filtered = self._filter_events(project_id, time_range)

            if not filtered:
                return AnalyticsSummary()

            # Calculate basic metrics
            total_searches = len(filtered)
            unique_queries = len(set(e.query for e in filtered if e.query))
            total_response_time = sum(e.response_time_ms for e in filtered)
            avg_response_time = total_response_time / total_searches if total_searches > 0 else 0.0

            # Calculate searches by day
            searches_by_day: Dict[str, int] = defaultdict(int)
            for event in filtered:
                day_key = event.timestamp.strftime("%Y-%m-%d")
                searches_by_day[day_key] += 1

            # Calculate searches by hour
            searches_by_hour: Dict[str, int] = defaultdict(int)
            for event in filtered:
                hour_key = str(event.timestamp.hour)
                searches_by_hour[hour_key] += 1

            # Get top queries (calling within lock context)
            top_queries = self._get_top_queries_internal(filtered, 10)

            # Get zero result queries (calling within lock context)
            zero_result_queries = self._get_zero_result_queries_internal(filtered, 10)

            return AnalyticsSummary(
                total_searches=total_searches,
                unique_queries=unique_queries,
                avg_response_time=avg_response_time,
                top_queries=top_queries,
                searches_by_day=dict(sorted(searches_by_day.items())),
                searches_by_hour=dict(sorted(searches_by_hour.items(), key=lambda x: int(x[0]))),
                zero_result_queries=zero_result_queries,
            )

    def get_searches_by_timeframe(
        self,
        project_id: Optional[str] = None,
        granularity: str = "day",
        time_range: Optional[TimeRange] = None,
    ) -> Dict[str, int]:
        """
        Get search counts aggregated by time period.

        Args:
            project_id: Optional project ID to filter by
            granularity: Time granularity - "hour", "day", or "week"
            time_range: Optional time range to filter by

        Returns:
            Dictionary mapping time periods to search counts
        """
        with self._lock:
            filtered = self._filter_events(project_id, time_range)

            volume: Dict[str, int] = defaultdict(int)

            for event in filtered:
                if granularity == "hour":
                    key = event.timestamp.strftime("%Y-%m-%d %H:00")
                elif granularity == "week":
                    year, week, _ = event.timestamp.isocalendar()
                    key = f"{year}-W{week:02d}"
                else:  # day
                    key = event.timestamp.strftime("%Y-%m-%d")

                volume[key] += 1

            return dict(sorted(volume.items()))

    def get_popular_fields(
        self,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Tuple[str, int]]:
        """
        Get the most frequently searched fields.

        Args:
            project_id: Optional project ID to filter by
            limit: Maximum number of fields to return

        Returns:
            List of (field_name, count) tuples sorted by count descending
        """
        with self._lock:
            filtered = self._filter_events(project_id, None)

            field_counts: Dict[str, int] = defaultdict(int)

            for event in filtered:
                for field_name in event.fields_searched:
                    field_counts[field_name] += 1

            # Sort by count descending
            sorted_fields = sorted(field_counts.items(), key=lambda x: (-x[1], x[0]))
            return sorted_fields[:limit]

    def get_slow_queries(
        self,
        project_id: Optional[str] = None,
        threshold_ms: int = 1000,
        limit: int = 10,
    ) -> List[SearchEvent]:
        """
        Get search events that exceeded the response time threshold.

        Args:
            project_id: Optional project ID to filter by
            threshold_ms: Response time threshold in milliseconds
            limit: Maximum number of events to return

        Returns:
            List of SearchEvent objects for slow queries
        """
        with self._lock:
            filtered = self._filter_events(project_id, None)

            slow_events = [e for e in filtered if e.response_time_ms >= threshold_ms]

            # Sort by response time descending
            slow_events.sort(key=lambda x: -x.response_time_ms)
            return slow_events[:limit]

    def get_related_queries(
        self,
        query: str,
        limit: int = 5,
    ) -> List[str]:
        """
        Get queries that are similar to the given query.

        Uses string similarity to find related queries that users have searched.

        Args:
            query: The query to find related queries for
            limit: Maximum number of related queries to return

        Returns:
            List of related query strings
        """
        if not query:
            return []

        normalized_query = query.strip().lower()

        with self._lock:
            # Get all unique queries
            all_queries = set(e.query for e in self._events if e.query and e.query != normalized_query)

            if not all_queries:
                return []

            # Calculate similarity scores
            similarities: List[Tuple[str, float]] = []
            for other_query in all_queries:
                score = self._calculate_similarity(normalized_query, other_query)
                if score >= 0.4:  # Minimum similarity threshold
                    similarities.append((other_query, score))

            # Sort by similarity descending
            similarities.sort(key=lambda x: -x[1])

            return [q for q, _ in similarities[:limit]]

    def suggest_query_improvements(
        self,
        query: str,
        limit: int = 5,
    ) -> List[str]:
        """
        Suggest improved versions of a query based on successful similar queries.

        Finds similar queries that returned more results and suggests them.

        Args:
            query: The query to suggest improvements for
            limit: Maximum number of suggestions to return

        Returns:
            List of suggested query strings
        """
        if not query:
            return []

        normalized_query = query.strip().lower()

        with self._lock:
            # Get query stats for the input query
            input_stats = self._get_query_stats_internal(normalized_query)
            input_avg_results = input_stats.avg_results if input_stats else 0.0

            # Find similar queries with better results
            query_stats_map: Dict[str, Tuple[float, float]] = {}  # query -> (similarity, avg_results)

            for event in self._events:
                if not event.query or event.query == normalized_query:
                    continue

                if event.query not in query_stats_map:
                    other_stats = self._get_query_stats_internal(event.query)
                    if other_stats and other_stats.avg_results > input_avg_results:
                        similarity = self._calculate_similarity(normalized_query, event.query)
                        if similarity >= 0.3:
                            query_stats_map[event.query] = (similarity, other_stats.avg_results)

            # Sort by similarity * avg_results (weighted combination)
            suggestions = [
                (q, sim * avg)
                for q, (sim, avg) in query_stats_map.items()
            ]
            suggestions.sort(key=lambda x: -x[1])

            return [q for q, _ in suggestions[:limit]]

    def clear_analytics(
        self,
        project_id: Optional[str] = None,
        before_date: Optional[datetime] = None,
    ) -> int:
        """
        Clear analytics data.

        Args:
            project_id: Optional project ID to clear data for (all if None)
            before_date: Optional date before which to clear data

        Returns:
            Number of events cleared
        """
        with self._lock:
            initial_count = len(self._events)

            if project_id is None and before_date is None:
                # Clear all
                self._events.clear()
                self._events_by_id.clear()
                return initial_count

            # Filter out events to remove
            events_to_keep = []
            for event in self._events:
                keep = True

                if project_id is not None and event.project_id == project_id:
                    keep = False
                elif before_date is not None and event.timestamp < before_date:
                    keep = False

                if keep:
                    events_to_keep.append(event)

            removed = initial_count - len(events_to_keep)
            self._events = events_to_keep
            self._events_by_id = {e.id: e for e in events_to_keep}

            logger.info(f"Cleared {removed} analytics events")
            return removed

    def export_analytics(
        self,
        project_id: Optional[str] = None,
        format: str = "json",
    ) -> str:
        """
        Export analytics data.

        Args:
            project_id: Optional project ID to filter by
            format: Export format - "json" or "csv"

        Returns:
            Exported data as a string
        """
        with self._lock:
            filtered = self._filter_events(project_id, None)

            if format.lower() == "csv":
                return self._export_to_csv(filtered)
            else:
                return self._export_to_json(filtered, project_id)

    def get_event(self, event_id: str) -> Optional[SearchEvent]:
        """
        Get a specific search event by ID.

        Args:
            event_id: The event ID

        Returns:
            The SearchEvent or None if not found
        """
        with self._lock:
            return self._events_by_id.get(event_id)

    def get_event_count(self) -> int:
        """Get the total number of stored events."""
        with self._lock:
            return len(self._events)

    # ----- Internal Helper Methods -----

    def _filter_events(
        self,
        project_id: Optional[str],
        time_range: Optional[TimeRange],
    ) -> List[SearchEvent]:
        """
        Filter events by project and time range.

        Must be called within a lock context.

        Args:
            project_id: Optional project ID filter
            time_range: Optional time range filter

        Returns:
            Filtered list of events
        """
        filtered = self._events

        if project_id is not None:
            filtered = [e for e in filtered if e.project_id == project_id]

        if time_range is not None:
            filtered = [e for e in filtered if time_range.contains(e.timestamp)]

        return filtered

    def _get_query_stats_internal(self, query: str) -> Optional[QueryStats]:
        """
        Internal method to get query stats (caller must hold lock).

        Args:
            query: The normalized query string

        Returns:
            QueryStats or None
        """
        matching_events = [e for e in self._events if e.query == query]

        if not matching_events:
            return None

        total_results = sum(e.results_count for e in matching_events)
        total_response_time = sum(e.response_time_ms for e in matching_events)
        count = len(matching_events)

        sorted_events = sorted(matching_events, key=lambda e: e.timestamp)

        return QueryStats(
            query=query,
            total_searches=count,
            avg_results=total_results / count if count > 0 else 0.0,
            avg_response_time_ms=total_response_time / count if count > 0 else 0.0,
            first_searched=sorted_events[0].timestamp if sorted_events else None,
            last_searched=sorted_events[-1].timestamp if sorted_events else None,
        )

    def _get_top_queries_internal(
        self,
        events: List[SearchEvent],
        limit: int,
    ) -> List[QueryStats]:
        """
        Internal method to get top queries from a list of events.

        Must be called within a lock context.

        Args:
            events: List of events to analyze
            limit: Maximum number of queries to return

        Returns:
            List of QueryStats
        """
        query_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_results": 0,
                "total_response_time": 0,
                "first_searched": None,
                "last_searched": None,
            }
        )

        for event in events:
            if not event.query:
                continue
            data = query_data[event.query]
            data["count"] += 1
            data["total_results"] += event.results_count
            data["total_response_time"] += event.response_time_ms

            if data["first_searched"] is None or event.timestamp < data["first_searched"]:
                data["first_searched"] = event.timestamp
            if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                data["last_searched"] = event.timestamp

        stats_list = []
        for query, data in query_data.items():
            count = data["count"]
            stats_list.append(QueryStats(
                query=query,
                total_searches=count,
                avg_results=data["total_results"] / count if count > 0 else 0.0,
                avg_response_time_ms=data["total_response_time"] / count if count > 0 else 0.0,
                first_searched=data["first_searched"],
                last_searched=data["last_searched"],
            ))

        stats_list.sort(key=lambda x: (-x.total_searches, x.query))
        return stats_list[:limit]

    def _get_zero_result_queries_internal(
        self,
        events: List[SearchEvent],
        limit: int,
    ) -> List[QueryStats]:
        """
        Internal method to get zero-result queries from a list of events.

        Must be called within a lock context.

        Args:
            events: List of events to analyze
            limit: Maximum number of queries to return

        Returns:
            List of QueryStats
        """
        zero_result_events = [e for e in events if e.results_count == 0]

        query_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_response_time": 0,
                "first_searched": None,
                "last_searched": None,
            }
        )

        for event in zero_result_events:
            if not event.query:
                continue
            data = query_data[event.query]
            data["count"] += 1
            data["total_response_time"] += event.response_time_ms

            if data["first_searched"] is None or event.timestamp < data["first_searched"]:
                data["first_searched"] = event.timestamp
            if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                data["last_searched"] = event.timestamp

        stats_list = []
        for query, data in query_data.items():
            count = data["count"]
            stats_list.append(QueryStats(
                query=query,
                total_searches=count,
                avg_results=0.0,
                avg_response_time_ms=data["total_response_time"] / count if count > 0 else 0.0,
                first_searched=data["first_searched"],
                last_searched=data["last_searched"],
            ))

        stats_list.sort(key=lambda x: (-x.total_searches, x.query))
        return stats_list[:limit]

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity using SequenceMatcher.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1, str2).ratio()

    def _export_to_json(
        self,
        events: List[SearchEvent],
        project_id: Optional[str],
    ) -> str:
        """
        Export events to JSON format.

        Args:
            events: List of events to export
            project_id: Project ID filter that was applied

        Returns:
            JSON string
        """
        # Get summary for the filtered events
        summary_data = {
            "total_searches": len(events),
            "unique_queries": len(set(e.query for e in events if e.query)),
        }

        if events:
            total_response_time = sum(e.response_time_ms for e in events)
            summary_data["avg_response_time"] = round(total_response_time / len(events), 2)
        else:
            summary_data["avg_response_time"] = 0.0

        export_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "project_id": project_id,
            },
            "summary": summary_data,
            "events": [e.to_dict() for e in events],
        }

        return json.dumps(export_data, indent=2, default=str)

    def _export_to_csv(self, events: List[SearchEvent]) -> str:
        """
        Export events to CSV format.

        Args:
            events: List of events to export

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "id",
            "query",
            "project_id",
            "user_id",
            "timestamp",
            "results_count",
            "response_time_ms",
            "fields_searched",
            "filters_applied",
        ])

        # Write data rows
        for event in events:
            writer.writerow([
                event.id,
                event.query,
                event.project_id,
                event.user_id or "",
                event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp,
                event.results_count,
                event.response_time_ms,
                ",".join(event.fields_searched),
                json.dumps(event.filters_applied),
            ])

        return output.getvalue()


# ----- Singleton Instance Management -----


_analytics_instance: Optional[SearchAnalytics] = None
_instance_lock = threading.Lock()


def get_analytics_service() -> SearchAnalytics:
    """
    Get or create the SearchAnalytics singleton instance.

    Returns:
        SearchAnalytics instance
    """
    global _analytics_instance

    with _instance_lock:
        if _analytics_instance is None:
            _analytics_instance = SearchAnalytics()

    return _analytics_instance


def set_analytics_service(service: Optional[SearchAnalytics]) -> None:
    """
    Set the global SearchAnalytics instance.

    Args:
        service: SearchAnalytics instance or None to clear
    """
    global _analytics_instance

    with _instance_lock:
        _analytics_instance = service
