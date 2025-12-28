"""
Timeline Analysis Service for Basset Hound

This module provides timeline tracking and analysis for entity relationship changes.
It records events such as entity creation, updates, relationship additions/removals,
and merges, storing them in Neo4j for historical analysis.

Features:
- Event recording with automatic timestamp and UUID generation
- Entity timeline retrieval with date filtering and event type filtering
- Project-wide timeline with pagination
- Relationship history between two entities
- Activity analysis with statistics
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Timeline event types."""
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    RELATIONSHIP_ADDED = "RELATIONSHIP_ADDED"
    RELATIONSHIP_REMOVED = "RELATIONSHIP_REMOVED"
    RELATIONSHIP_UPDATED = "RELATIONSHIP_UPDATED"
    MERGED = "MERGED"
    TAGGED = "TAGGED"
    UNTAGGED = "UNTAGGED"
    FILE_ADDED = "FILE_ADDED"
    FILE_REMOVED = "FILE_REMOVED"
    REPORT_ADDED = "REPORT_ADDED"
    REPORT_REMOVED = "REPORT_REMOVED"


@dataclass
class TimelineEvent:
    """
    Represents a single timeline event.

    Attributes:
        event_id: Unique identifier for the event (auto-generated UUID)
        entity_id: ID of the entity this event relates to
        project_id: ID of the project containing the entity
        event_type: Type of event (CREATED, UPDATED, etc.)
        timestamp: When the event occurred
        details: Additional event details (field changes, relationship info, etc.)
        actor: Who made the change (for future authentication integration)
    """
    entity_id: str
    project_id: str
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    actor: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary representation."""
        return {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "details": self.details,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineEvent":
        """Create a TimelineEvent from a dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            event_id=data.get("event_id", str(uuid4())),
            entity_id=data.get("entity_id", ""),
            project_id=data.get("project_id", ""),
            event_type=data.get("event_type", ""),
            timestamp=timestamp,
            details=data.get("details", {}),
            actor=data.get("actor"),
        )


class TimelineService:
    """
    Service for managing timeline events in Neo4j.

    Provides methods for recording, retrieving, and analyzing timeline events
    for entities within OSINT investigation projects.
    """

    def __init__(self, neo4j_handler):
        """
        Initialize the timeline service.

        Args:
            neo4j_handler: Neo4j database handler instance
        """
        self._handler = neo4j_handler
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the timeline service, creating necessary indexes."""
        if self._initialized:
            return

        try:
            # Create indexes for timeline events if using async handler
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    # Create index for TimelineEvent nodes
                    await session.run(
                        "CREATE INDEX IF NOT EXISTS FOR (te:TimelineEvent) ON (te.event_id)"
                    )
                    await session.run(
                        "CREATE INDEX IF NOT EXISTS FOR (te:TimelineEvent) ON (te.timestamp)"
                    )
                    await session.run(
                        "CREATE INDEX IF NOT EXISTS FOR (te:TimelineEvent) ON (te.entity_id)"
                    )
                    await session.run(
                        "CREATE INDEX IF NOT EXISTS FOR (te:TimelineEvent) ON (te.project_id)"
                    )
            self._initialized = True
            logger.info("Timeline service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize timeline service: {e}")
            # Don't raise - service can still work without indexes

    def _ensure_sync_handler(self):
        """Ensure we have a sync handler for sync operations."""
        if not hasattr(self._handler, 'run_query'):
            raise RuntimeError("Timeline service requires a Neo4j handler with run_query method")

    def record_event(
        self,
        project_id: str,
        entity_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> TimelineEvent:
        """
        Record a new timeline event.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            event_type: Type of event (e.g., CREATED, UPDATED)
            details: Additional event details
            actor: Who made the change

        Returns:
            The created TimelineEvent
        """
        event = TimelineEvent(
            entity_id=entity_id,
            project_id=project_id,
            event_type=event_type,
            details=details or {},
            actor=actor,
        )

        # Store in Neo4j
        query = """
        MATCH (entity:Person {id: $entity_id})
        CREATE (te:TimelineEvent {
            event_id: $event_id,
            entity_id: $entity_id,
            project_id: $project_id,
            event_type: $event_type,
            timestamp: datetime($timestamp),
            details: $details_json,
            actor: $actor
        })
        CREATE (entity)-[:HAS_TIMELINE_EVENT]->(te)
        RETURN te
        """

        import json
        params = {
            "entity_id": entity_id,
            "event_id": event.event_id,
            "project_id": project_id,
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "details_json": json.dumps(details or {}),
            "actor": actor,
        }

        try:
            if hasattr(self._handler, 'run_query'):
                self._handler.run_query(query, params)
            else:
                # Fallback for handlers without run_query
                logger.warning("Handler does not have run_query method, event not persisted")
        except Exception as e:
            logger.error(f"Failed to record timeline event: {e}")
            # Return the event even if persistence fails - caller can retry

        return event

    async def record_event_async(
        self,
        project_id: str,
        entity_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> TimelineEvent:
        """
        Record a new timeline event asynchronously.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            event_type: Type of event (e.g., CREATED, UPDATED)
            details: Additional event details
            actor: Who made the change

        Returns:
            The created TimelineEvent
        """
        event = TimelineEvent(
            entity_id=entity_id,
            project_id=project_id,
            event_type=event_type,
            details=details or {},
            actor=actor,
        )

        query = """
        MATCH (entity:Person {id: $entity_id})
        CREATE (te:TimelineEvent {
            event_id: $event_id,
            entity_id: $entity_id,
            project_id: $project_id,
            event_type: $event_type,
            timestamp: datetime($timestamp),
            details: $details_json,
            actor: $actor
        })
        CREATE (entity)-[:HAS_TIMELINE_EVENT]->(te)
        RETURN te
        """

        import json
        params = {
            "entity_id": entity_id,
            "event_id": event.event_id,
            "project_id": project_id,
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "details_json": json.dumps(details or {}),
            "actor": actor,
        }

        try:
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    await session.run(query, params)
            elif hasattr(self._handler, '_execute_query'):
                await self._handler._execute_query(query, params, fetch_all=False)
        except Exception as e:
            logger.error(f"Failed to record timeline event: {e}")

        return event

    def get_entity_timeline(
        self,
        project_id: str,
        entity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
    ) -> List[TimelineEvent]:
        """
        Get timeline events for a specific entity.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            start_date: Optional start date filter
            end_date: Optional end date filter
            event_types: Optional list of event types to filter by

        Returns:
            List of TimelineEvent objects ordered by timestamp descending
        """
        # Build query with optional filters
        query_parts = [
            "MATCH (entity:Person {id: $entity_id})-[:HAS_TIMELINE_EVENT]->(te:TimelineEvent)",
            "WHERE te.project_id = $project_id"
        ]
        params = {
            "entity_id": entity_id,
            "project_id": project_id,
        }

        if start_date:
            query_parts.append("AND te.timestamp >= datetime($start_date)")
            params["start_date"] = start_date.isoformat()

        if end_date:
            query_parts.append("AND te.timestamp <= datetime($end_date)")
            params["end_date"] = end_date.isoformat()

        if event_types:
            query_parts.append("AND te.event_type IN $event_types")
            params["event_types"] = event_types

        query_parts.append("RETURN te ORDER BY te.timestamp DESC")
        query = " ".join(query_parts)

        events = []
        try:
            if hasattr(self._handler, 'run_query'):
                results = self._handler.run_query(query, params)
                for record in results:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get entity timeline: {e}")

        return events

    async def get_entity_timeline_async(
        self,
        project_id: str,
        entity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
    ) -> List[TimelineEvent]:
        """
        Get timeline events for a specific entity asynchronously.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            start_date: Optional start date filter
            end_date: Optional end date filter
            event_types: Optional list of event types to filter by

        Returns:
            List of TimelineEvent objects ordered by timestamp descending
        """
        query_parts = [
            "MATCH (entity:Person {id: $entity_id})-[:HAS_TIMELINE_EVENT]->(te:TimelineEvent)",
            "WHERE te.project_id = $project_id"
        ]
        params = {
            "entity_id": entity_id,
            "project_id": project_id,
        }

        if start_date:
            query_parts.append("AND te.timestamp >= datetime($start_date)")
            params["start_date"] = start_date.isoformat()

        if end_date:
            query_parts.append("AND te.timestamp <= datetime($end_date)")
            params["end_date"] = end_date.isoformat()

        if event_types:
            query_parts.append("AND te.event_type IN $event_types")
            params["event_types"] = event_types

        query_parts.append("RETURN te ORDER BY te.timestamp DESC")
        query = " ".join(query_parts)

        events = []
        try:
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    result = await session.run(query, params)
                    records = await result.data()
                    for record in records:
                        events.append(self._parse_event_record(record["te"]))
            elif hasattr(self._handler, '_execute_query'):
                results = await self._handler._execute_query(query, params)
                for record in results or []:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get entity timeline: {e}")

        return events

    def get_project_timeline(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """
        Get recent timeline events for a project.

        Args:
            project_id: ID of the project
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of events to return (default 100)

        Returns:
            List of TimelineEvent objects ordered by timestamp descending
        """
        query_parts = [
            "MATCH (te:TimelineEvent)",
            "WHERE te.project_id = $project_id"
        ]
        params = {
            "project_id": project_id,
            "limit": limit,
        }

        if start_date:
            query_parts.append("AND te.timestamp >= datetime($start_date)")
            params["start_date"] = start_date.isoformat()

        if end_date:
            query_parts.append("AND te.timestamp <= datetime($end_date)")
            params["end_date"] = end_date.isoformat()

        query_parts.append("RETURN te ORDER BY te.timestamp DESC LIMIT $limit")
        query = " ".join(query_parts)

        events = []
        try:
            if hasattr(self._handler, 'run_query'):
                results = self._handler.run_query(query, params)
                for record in results:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get project timeline: {e}")

        return events

    async def get_project_timeline_async(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """
        Get recent timeline events for a project asynchronously.

        Args:
            project_id: ID of the project
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of events to return (default 100)

        Returns:
            List of TimelineEvent objects ordered by timestamp descending
        """
        query_parts = [
            "MATCH (te:TimelineEvent)",
            "WHERE te.project_id = $project_id"
        ]
        params = {
            "project_id": project_id,
            "limit": limit,
        }

        if start_date:
            query_parts.append("AND te.timestamp >= datetime($start_date)")
            params["start_date"] = start_date.isoformat()

        if end_date:
            query_parts.append("AND te.timestamp <= datetime($end_date)")
            params["end_date"] = end_date.isoformat()

        query_parts.append("RETURN te ORDER BY te.timestamp DESC LIMIT $limit")
        query = " ".join(query_parts)

        events = []
        try:
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    result = await session.run(query, params)
                    records = await result.data()
                    for record in records:
                        events.append(self._parse_event_record(record["te"]))
            elif hasattr(self._handler, '_execute_query'):
                results = await self._handler._execute_query(query, params)
                for record in results or []:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get project timeline: {e}")

        return events

    def get_relationship_history(
        self,
        project_id: str,
        entity1_id: str,
        entity2_id: str,
    ) -> List[TimelineEvent]:
        """
        Get the history of relationship changes between two entities.

        Args:
            project_id: ID of the project
            entity1_id: ID of the first entity
            entity2_id: ID of the second entity

        Returns:
            List of TimelineEvent objects related to the relationship
        """
        query = """
        MATCH (te:TimelineEvent)
        WHERE te.project_id = $project_id
        AND te.event_type IN ['RELATIONSHIP_ADDED', 'RELATIONSHIP_REMOVED', 'RELATIONSHIP_UPDATED', 'TAGGED', 'UNTAGGED']
        AND (
            (te.entity_id = $entity1_id AND te.details CONTAINS $entity2_id)
            OR (te.entity_id = $entity2_id AND te.details CONTAINS $entity1_id)
        )
        RETURN te ORDER BY te.timestamp DESC
        """
        params = {
            "project_id": project_id,
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        }

        events = []
        try:
            if hasattr(self._handler, 'run_query'):
                results = self._handler.run_query(query, params)
                for record in results:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get relationship history: {e}")

        return events

    async def get_relationship_history_async(
        self,
        project_id: str,
        entity1_id: str,
        entity2_id: str,
    ) -> List[TimelineEvent]:
        """
        Get the history of relationship changes between two entities asynchronously.

        Args:
            project_id: ID of the project
            entity1_id: ID of the first entity
            entity2_id: ID of the second entity

        Returns:
            List of TimelineEvent objects related to the relationship
        """
        query = """
        MATCH (te:TimelineEvent)
        WHERE te.project_id = $project_id
        AND te.event_type IN ['RELATIONSHIP_ADDED', 'RELATIONSHIP_REMOVED', 'RELATIONSHIP_UPDATED', 'TAGGED', 'UNTAGGED']
        AND (
            (te.entity_id = $entity1_id AND te.details CONTAINS $entity2_id)
            OR (te.entity_id = $entity2_id AND te.details CONTAINS $entity1_id)
        )
        RETURN te ORDER BY te.timestamp DESC
        """
        params = {
            "project_id": project_id,
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
        }

        events = []
        try:
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    result = await session.run(query, params)
                    records = await result.data()
                    for record in records:
                        events.append(self._parse_event_record(record["te"]))
            elif hasattr(self._handler, '_execute_query'):
                results = await self._handler._execute_query(query, params)
                for record in results or []:
                    events.append(self._parse_event_record(record["te"]))
        except Exception as e:
            logger.error(f"Failed to get relationship history: {e}")

        return events

    def analyze_activity(
        self,
        project_id: str,
        entity_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze activity for an entity over a specified period.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            days: Number of days to analyze (default 30)

        Returns:
            Dictionary containing activity statistics:
            - total_events: Total number of events
            - events_by_type: Count of events by type
            - events_by_day: Count of events per day
            - most_active_day: Day with most activity
            - average_events_per_day: Average events per day
            - first_event: Timestamp of first event
            - last_event: Timestamp of last event
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        query = """
        MATCH (entity:Person {id: $entity_id})-[:HAS_TIMELINE_EVENT]->(te:TimelineEvent)
        WHERE te.project_id = $project_id
        AND te.timestamp >= datetime($start_date)
        AND te.timestamp <= datetime($end_date)
        RETURN te.event_type AS event_type,
               date(te.timestamp) AS event_date,
               te.timestamp AS timestamp
        ORDER BY te.timestamp
        """
        params = {
            "entity_id": entity_id,
            "project_id": project_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        events_by_type: Dict[str, int] = {}
        events_by_day: Dict[str, int] = {}
        timestamps: List[datetime] = []

        try:
            if hasattr(self._handler, 'run_query'):
                results = self._handler.run_query(query, params)
                for record in results:
                    event_type = record.get("event_type", "UNKNOWN")
                    event_date = record.get("event_date")
                    timestamp = record.get("timestamp")

                    events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

                    if event_date:
                        date_str = str(event_date)
                        events_by_day[date_str] = events_by_day.get(date_str, 0) + 1

                    if timestamp:
                        if hasattr(timestamp, 'to_native'):
                            timestamps.append(timestamp.to_native())
                        elif isinstance(timestamp, datetime):
                            timestamps.append(timestamp)
        except Exception as e:
            logger.error(f"Failed to analyze activity: {e}")

        total_events = sum(events_by_type.values())
        most_active_day = max(events_by_day.items(), key=lambda x: x[1])[0] if events_by_day else None
        average_events_per_day = total_events / days if days > 0 else 0

        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_day": events_by_day,
            "most_active_day": most_active_day,
            "average_events_per_day": round(average_events_per_day, 2),
            "first_event": timestamps[0].isoformat() if timestamps else None,
            "last_event": timestamps[-1].isoformat() if timestamps else None,
            "analysis_period_days": days,
        }

    async def analyze_activity_async(
        self,
        project_id: str,
        entity_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze activity for an entity over a specified period asynchronously.

        Args:
            project_id: ID of the project
            entity_id: ID of the entity
            days: Number of days to analyze (default 30)

        Returns:
            Dictionary containing activity statistics
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        query = """
        MATCH (entity:Person {id: $entity_id})-[:HAS_TIMELINE_EVENT]->(te:TimelineEvent)
        WHERE te.project_id = $project_id
        AND te.timestamp >= datetime($start_date)
        AND te.timestamp <= datetime($end_date)
        RETURN te.event_type AS event_type,
               date(te.timestamp) AS event_date,
               te.timestamp AS timestamp
        ORDER BY te.timestamp
        """
        params = {
            "entity_id": entity_id,
            "project_id": project_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        events_by_type: Dict[str, int] = {}
        events_by_day: Dict[str, int] = {}
        timestamps: List[datetime] = []

        try:
            if hasattr(self._handler, 'session'):
                async with self._handler.session() as session:
                    result = await session.run(query, params)
                    records = await result.data()
                    for record in records:
                        event_type = record.get("event_type", "UNKNOWN")
                        event_date = record.get("event_date")
                        timestamp = record.get("timestamp")

                        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

                        if event_date:
                            date_str = str(event_date)
                            events_by_day[date_str] = events_by_day.get(date_str, 0) + 1

                        if timestamp:
                            if hasattr(timestamp, 'to_native'):
                                timestamps.append(timestamp.to_native())
                            elif isinstance(timestamp, datetime):
                                timestamps.append(timestamp)
            elif hasattr(self._handler, '_execute_query'):
                results = await self._handler._execute_query(query, params)
                for record in results or []:
                    event_type = record.get("event_type", "UNKNOWN")
                    event_date = record.get("event_date")
                    timestamp = record.get("timestamp")

                    events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

                    if event_date:
                        date_str = str(event_date)
                        events_by_day[date_str] = events_by_day.get(date_str, 0) + 1

                    if timestamp:
                        if hasattr(timestamp, 'to_native'):
                            timestamps.append(timestamp.to_native())
                        elif isinstance(timestamp, datetime):
                            timestamps.append(timestamp)
        except Exception as e:
            logger.error(f"Failed to analyze activity: {e}")

        total_events = sum(events_by_type.values())
        most_active_day = max(events_by_day.items(), key=lambda x: x[1])[0] if events_by_day else None
        average_events_per_day = total_events / days if days > 0 else 0

        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_day": events_by_day,
            "most_active_day": most_active_day,
            "average_events_per_day": round(average_events_per_day, 2),
            "first_event": timestamps[0].isoformat() if timestamps else None,
            "last_event": timestamps[-1].isoformat() if timestamps else None,
            "analysis_period_days": days,
        }

    def _parse_event_record(self, record: Dict[str, Any]) -> TimelineEvent:
        """Parse a Neo4j record into a TimelineEvent."""
        import json

        details = record.get("details") or record.get("details_json") or "{}"
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except json.JSONDecodeError:
                details = {}

        timestamp = record.get("timestamp")
        if hasattr(timestamp, 'to_native'):
            timestamp = timestamp.to_native()
        elif hasattr(timestamp, 'iso_format'):
            timestamp = datetime.fromisoformat(timestamp.iso_format())
        elif isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return TimelineEvent(
            event_id=record.get("event_id", str(uuid4())),
            entity_id=record.get("entity_id", ""),
            project_id=record.get("project_id", ""),
            event_type=record.get("event_type", ""),
            timestamp=timestamp,
            details=details,
            actor=record.get("actor"),
        )


# Singleton instance management
_timeline_service: Optional[TimelineService] = None


def get_timeline_service(neo4j_handler=None) -> TimelineService:
    """
    Get or create the timeline service singleton.

    Args:
        neo4j_handler: Neo4j handler instance (required on first call)

    Returns:
        TimelineService instance
    """
    global _timeline_service

    if _timeline_service is None:
        if neo4j_handler is None:
            raise ValueError("neo4j_handler is required on first call to get_timeline_service")
        _timeline_service = TimelineService(neo4j_handler)

    return _timeline_service


def set_timeline_service(service: Optional[TimelineService]) -> None:
    """Set the timeline service singleton (for testing)."""
    global _timeline_service
    _timeline_service = service
