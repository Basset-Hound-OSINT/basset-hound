"""
Search Analytics Service for Basset Hound OSINT Platform.

This module provides comprehensive search analytics tracking including:
- Recording search events with detailed metadata
- Tracking user clicks on search results
- Analyzing popular queries and trends
- Identifying zero-result queries for search improvement
- Computing click-through rates and search volume metrics
- Generating query suggestions based on history

Features:
- Thread-safe in-memory storage with configurable retention
- Efficient statistics calculation for large event counts
- Date range filtering for all analytics
- Project-scoped analytics support
- JSON export of analytics data
"""

import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class SearchEvent:
    """
    Represents a single search event.

    Attributes:
        id: Unique identifier for the event (auto-generated UUID)
        query: The search query string
        project_id: Optional project ID if search was scoped
        user_id: Optional user ID who performed the search
        timestamp: When the search occurred
        result_count: Number of results returned
        duration_ms: Search execution time in milliseconds
        entity_types: List of entity types searched or filtered
        filters_used: Dictionary of filters applied to the search
        clicked_results: List of entity IDs that were clicked from results
    """
    query: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    result_count: int = 0
    duration_ms: int = 0
    entity_types: List[str] = field(default_factory=list)
    filters_used: Dict[str, Any] = field(default_factory=dict)
    clicked_results: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary representation."""
        return {
            "id": self.id,
            "query": self.query,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "result_count": self.result_count,
            "duration_ms": self.duration_ms,
            "entity_types": self.entity_types,
            "filters_used": self.filters_used,
            "clicked_results": self.clicked_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchEvent":
        """Create a SearchEvent from a dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            id=data.get("id", str(uuid4())),
            query=data.get("query", ""),
            project_id=data.get("project_id"),
            user_id=data.get("user_id"),
            timestamp=timestamp,
            result_count=data.get("result_count", 0),
            duration_ms=data.get("duration_ms", 0),
            entity_types=data.get("entity_types", []),
            filters_used=data.get("filters_used", {}),
            clicked_results=data.get("clicked_results", []),
        )


@dataclass
class PopularQuery:
    """
    Represents aggregated data for a popular query.

    Attributes:
        query: The search query string
        count: Number of times this query was searched
        avg_results: Average number of results returned
        last_searched: Timestamp of most recent search
    """
    query: str
    count: int
    avg_results: float
    last_searched: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "count": self.count,
            "avg_results": round(self.avg_results, 2),
            "last_searched": self.last_searched.isoformat() if isinstance(self.last_searched, datetime) else self.last_searched,
        }


class SearchAnalytics:
    """
    Service for tracking and analyzing search behavior.

    Provides methods for recording search events, tracking clicks,
    and computing various analytics metrics with thread-safety.

    Usage:
        analytics = SearchAnalytics(retention_days=30)

        # Record a search
        event = analytics.record_search(
            query="John Doe",
            result_count=5,
            duration_ms=150
        )

        # Record a click on a result
        analytics.record_click(event.id, "entity-123")

        # Get popular queries
        popular = analytics.get_popular_queries(limit=10)

        # Get click-through rate
        ctr = analytics.get_click_through_rate()
    """

    def __init__(self, retention_days: int = 30):
        """
        Initialize the search analytics service.

        Args:
            retention_days: Number of days to retain events (default 30)
        """
        self._events: List[SearchEvent] = []
        self._events_by_id: Dict[str, SearchEvent] = {}
        self._retention_days = retention_days
        self._lock = threading.RLock()

    @property
    def retention_days(self) -> int:
        """Get the retention period in days."""
        return self._retention_days

    @retention_days.setter
    def retention_days(self, value: int) -> None:
        """Set the retention period in days."""
        with self._lock:
            self._retention_days = max(1, value)

    def record_search(
        self,
        query: str,
        result_count: int = 0,
        duration_ms: int = 0,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        filters_used: Optional[Dict[str, Any]] = None,
    ) -> SearchEvent:
        """
        Record a new search event.

        Args:
            query: The search query string
            result_count: Number of results returned
            duration_ms: Search execution time in milliseconds
            project_id: Optional project ID if search was scoped
            user_id: Optional user ID who performed the search
            entity_types: Optional list of entity types searched
            filters_used: Optional dictionary of filters applied

        Returns:
            The created SearchEvent
        """
        event = SearchEvent(
            query=query.strip().lower() if query else "",
            result_count=result_count,
            duration_ms=duration_ms,
            project_id=project_id,
            user_id=user_id,
            entity_types=entity_types or [],
            filters_used=filters_used or {},
        )

        with self._lock:
            self._events.append(event)
            self._events_by_id[event.id] = event

        logger.debug(f"Recorded search event: query='{query}', results={result_count}")
        return event

    def record_click(self, event_id: str, entity_id: str) -> bool:
        """
        Record a click on a search result.

        Args:
            event_id: ID of the search event
            entity_id: ID of the entity that was clicked

        Returns:
            True if click was recorded, False if event not found
        """
        with self._lock:
            event = self._events_by_id.get(event_id)
            if event:
                if entity_id not in event.clicked_results:
                    event.clicked_results.append(entity_id)
                logger.debug(f"Recorded click: event={event_id}, entity={entity_id}")
                return True
            return False

    def get_popular_queries(
        self,
        limit: int = 10,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PopularQuery]:
        """
        Get the most popular search queries.

        Args:
            limit: Maximum number of queries to return
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            List of PopularQuery objects sorted by count descending
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            # Aggregate by query
            query_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "total_results": 0, "last_searched": None}
            )

            for event in filtered:
                if not event.query:
                    continue
                data = query_data[event.query]
                data["count"] += 1
                data["total_results"] += event.result_count
                if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                    data["last_searched"] = event.timestamp

            # Convert to PopularQuery objects
            popular = []
            for query, data in query_data.items():
                avg_results = data["total_results"] / data["count"] if data["count"] > 0 else 0
                popular.append(PopularQuery(
                    query=query,
                    count=data["count"],
                    avg_results=avg_results,
                    last_searched=data["last_searched"],
                ))

            # Sort by count descending
            popular.sort(key=lambda x: (-x.count, x.query))
            return popular[:limit]

    def get_zero_result_queries(
        self,
        limit: int = 10,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PopularQuery]:
        """
        Get queries that returned zero results.

        Args:
            limit: Maximum number of queries to return
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            List of PopularQuery objects for zero-result queries
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            # Aggregate zero-result queries
            query_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "last_searched": None}
            )

            for event in filtered:
                if not event.query or event.result_count > 0:
                    continue
                data = query_data[event.query]
                data["count"] += 1
                if data["last_searched"] is None or event.timestamp > data["last_searched"]:
                    data["last_searched"] = event.timestamp

            # Convert to PopularQuery objects
            zero_results = []
            for query, data in query_data.items():
                zero_results.append(PopularQuery(
                    query=query,
                    count=data["count"],
                    avg_results=0.0,
                    last_searched=data["last_searched"],
                ))

            # Sort by count descending
            zero_results.sort(key=lambda x: (-x.count, x.query))
            return zero_results[:limit]

    def get_search_volume(
        self,
        granularity: str = "day",
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Get search volume aggregated by time period.

        Args:
            granularity: Time granularity - "hour", "day", or "week"
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dictionary mapping time periods to search counts
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            volume: Dict[str, int] = defaultdict(int)

            for event in filtered:
                if granularity == "hour":
                    key = event.timestamp.strftime("%Y-%m-%d %H:00")
                elif granularity == "week":
                    # Get ISO week
                    year, week, _ = event.timestamp.isocalendar()
                    key = f"{year}-W{week:02d}"
                else:  # day
                    key = event.timestamp.strftime("%Y-%m-%d")

                volume[key] += 1

            # Sort by key (date/time)
            return dict(sorted(volume.items()))

    def get_avg_results_per_query(
        self,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """
        Get the average number of results per search query.

        Args:
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Average result count across all searches
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            if not filtered:
                return 0.0

            total_results = sum(event.result_count for event in filtered)
            return round(total_results / len(filtered), 2)

    def get_click_through_rate(
        self,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """
        Get the click-through rate (ratio of searches with clicks to total searches).

        Args:
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            CTR as a decimal (0.0 to 1.0)
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            if not filtered:
                return 0.0

            searches_with_clicks = sum(1 for event in filtered if event.clicked_results)
            return round(searches_with_clicks / len(filtered), 4)

    def get_query_suggestions(
        self,
        prefix: str,
        limit: int = 5,
        project_id: Optional[str] = None,
    ) -> List[str]:
        """
        Get query suggestions based on search history.

        Args:
            prefix: Query prefix to match
            limit: Maximum number of suggestions
            project_id: Optional project ID to filter by

        Returns:
            List of suggested query strings
        """
        if not prefix:
            return []

        prefix_lower = prefix.strip().lower()

        with self._lock:
            filtered = self._filter_events(project_id, None, None)

            # Count matching queries
            query_counts: Dict[str, int] = defaultdict(int)
            for event in filtered:
                if event.query and event.query.startswith(prefix_lower):
                    query_counts[event.query] += 1

            # Sort by count and return top suggestions
            sorted_queries = sorted(
                query_counts.items(),
                key=lambda x: (-x[1], x[0])
            )
            return [query for query, _ in sorted_queries[:limit]]

    def get_search_trends(
        self,
        query: str,
        granularity: str = "day",
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Get search volume trends for a specific query over time.

        Args:
            query: The query to analyze
            granularity: Time granularity - "hour", "day", or "week"
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dictionary mapping time periods to search counts for the query
        """
        query_lower = query.strip().lower() if query else ""

        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            trends: Dict[str, int] = defaultdict(int)

            for event in filtered:
                if event.query != query_lower:
                    continue

                if granularity == "hour":
                    key = event.timestamp.strftime("%Y-%m-%d %H:00")
                elif granularity == "week":
                    year, week, _ = event.timestamp.isocalendar()
                    key = f"{year}-W{week:02d}"
                else:  # day
                    key = event.timestamp.strftime("%Y-%m-%d")

                trends[key] += 1

            return dict(sorted(trends.items()))

    def cleanup_old_events(self, older_than_days: Optional[int] = None) -> int:
        """
        Remove events older than the retention period.

        Args:
            older_than_days: Custom retention period (uses default if None)

        Returns:
            Number of events removed
        """
        days = older_than_days if older_than_days is not None else self._retention_days
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self._lock:
            initial_count = len(self._events)

            # Filter out old events
            self._events = [e for e in self._events if e.timestamp >= cutoff]

            # Rebuild the ID index
            self._events_by_id = {e.id: e for e in self._events}

            removed = initial_count - len(self._events)
            logger.info(f"Cleaned up {removed} old search events")
            return removed

    def export_analytics(
        self,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_events: bool = False,
    ) -> Dict[str, Any]:
        """
        Export analytics data as a dictionary (JSON-serializable).

        Args:
            project_id: Optional project ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            include_events: Whether to include raw event data

        Returns:
            Dictionary containing analytics summary and optionally events
        """
        with self._lock:
            filtered = self._filter_events(project_id, start_date, end_date)

            export = {
                "generated_at": datetime.utcnow().isoformat(),
                "filters": {
                    "project_id": project_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
                "summary": {
                    "total_searches": len(filtered),
                    "unique_queries": len(set(e.query for e in filtered if e.query)),
                    "avg_results_per_query": self.get_avg_results_per_query(project_id, start_date, end_date),
                    "click_through_rate": self.get_click_through_rate(project_id, start_date, end_date),
                    "zero_result_query_count": len([e for e in filtered if e.result_count == 0]),
                },
                "popular_queries": [q.to_dict() for q in self.get_popular_queries(10, project_id, start_date, end_date)],
                "zero_result_queries": [q.to_dict() for q in self.get_zero_result_queries(10, project_id, start_date, end_date)],
                "volume_by_day": self.get_search_volume("day", project_id, start_date, end_date),
            }

            if include_events:
                export["events"] = [e.to_dict() for e in filtered]

            return export

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

    def clear_all_events(self) -> int:
        """
        Clear all stored events (for testing/admin purposes).

        Returns:
            Number of events cleared
        """
        with self._lock:
            count = len(self._events)
            self._events.clear()
            self._events_by_id.clear()
            return count

    def _filter_events(
        self,
        project_id: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[SearchEvent]:
        """
        Filter events by project and date range.

        Must be called within a lock context.

        Args:
            project_id: Optional project ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Filtered list of events
        """
        filtered = self._events

        if project_id is not None:
            filtered = [e for e in filtered if e.project_id == project_id]

        if start_date is not None:
            filtered = [e for e in filtered if e.timestamp >= start_date]

        if end_date is not None:
            filtered = [e for e in filtered if e.timestamp <= end_date]

        return filtered


# Singleton instance management
_search_analytics_instance: Optional[SearchAnalytics] = None
_analytics_lock = threading.Lock()


def get_search_analytics(retention_days: int = 30) -> SearchAnalytics:
    """
    Get or create the SearchAnalytics singleton instance.

    Args:
        retention_days: Retention period for first initialization

    Returns:
        SearchAnalytics instance
    """
    global _search_analytics_instance

    with _analytics_lock:
        if _search_analytics_instance is None:
            _search_analytics_instance = SearchAnalytics(retention_days)

    return _search_analytics_instance


def set_search_analytics(service: Optional[SearchAnalytics]) -> None:
    """
    Set the global SearchAnalytics instance.

    Args:
        service: SearchAnalytics instance or None to clear
    """
    global _search_analytics_instance

    with _analytics_lock:
        _search_analytics_instance = service
