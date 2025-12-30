"""
Timeline Visualization Service for Basset Hound OSINT Platform.

This module provides temporal graph visualization capabilities that show
how entities and relationships evolve over time. It integrates with the
existing TimelineService for event data, GraphVisualizationService for
graph snapshots, and AuditLogger for change tracking.

Features:
- Entity timeline visualization with event markers
- Relationship timeline tracking between entity pairs
- Project activity heatmap data for temporal analysis
- Temporal graph snapshots at specific points in time
- Entity evolution tracking (profile changes over time)
- Time period comparison for statistical analysis
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class TimelineGranularity(str, Enum):
    """Granularity levels for timeline aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TimelineEventType(str, Enum):
    """Types of events that can appear on a timeline."""
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_REMOVED = "relationship_removed"
    RELATIONSHIP_UPDATED = "relationship_updated"
    ENTITY_MERGED = "entity_merged"
    PROFILE_CHANGED = "profile_changed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class TimelineEvent(BaseModel):
    """
    A single event on a timeline.

    Represents a discrete change or action that occurred at a specific
    point in time, with associated metadata and details.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "event_type": "entity_updated",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {"field": "email", "old_value": "old@example.com", "new_value": "new@example.com"},
                "metadata": {"actor": "user123", "source": "manual"}
            }
        }
    )

    timestamp: datetime = Field(..., description="When the event occurred (ISO 8601)")
    event_type: str = Field(..., description="Type of the event")
    entity_id: str = Field(..., description="ID of the entity this event relates to")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier")


class ActivityHeatmapData(BaseModel):
    """
    Activity data for a single time bucket in a heatmap.

    Used for visualizing activity intensity over time periods.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-01-15",
                "count": 25,
                "entity_count": 10,
                "relationship_count": 15
            }
        }
    )

    date: str = Field(..., description="Date or time bucket identifier")
    count: int = Field(default=0, ge=0, description="Total number of events")
    entity_count: int = Field(default=0, ge=0, description="Number of entity-related events")
    relationship_count: int = Field(default=0, ge=0, description="Number of relationship-related events")
    event_types: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of events by type"
    )


class TemporalNode(BaseModel):
    """A node in a temporal graph snapshot."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Display label")
    entity_type: str = Field(default="Person", description="Entity type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties at this time")
    created_at: Optional[datetime] = Field(None, description="When the node was created")


class TemporalEdge(BaseModel):
    """An edge in a temporal graph snapshot."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship_type: str = Field(default="RELATED_TO", description="Type of relationship")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties at this time")
    created_at: Optional[datetime] = Field(None, description="When the edge was created")


class GraphStats(BaseModel):
    """Statistics about a graph at a point in time."""
    node_count: int = Field(default=0, ge=0, description="Number of nodes")
    edge_count: int = Field(default=0, ge=0, description="Number of edges")
    density: float = Field(default=0.0, ge=0.0, le=1.0, description="Graph density")
    avg_degree: float = Field(default=0.0, ge=0.0, description="Average node degree")
    isolated_nodes: int = Field(default=0, ge=0, description="Number of nodes with no connections")
    entity_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of entity types"
    )
    relationship_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of relationship types"
    )


class TemporalSnapshot(BaseModel):
    """
    A snapshot of the graph state at a specific point in time.

    Captures the complete state of nodes, edges, and computed statistics
    for a given timestamp.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "nodes": [],
                "edges": [],
                "stats": {"node_count": 50, "edge_count": 75}
            }
        }
    )

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Nodes at this time")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Edges at this time")
    stats: GraphStats = Field(default_factory=GraphStats, description="Graph statistics")


class EntityVersion(BaseModel):
    """A version of an entity's profile at a point in time."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "version_number": 3,
                "profile_snapshot": {"core": {"name": [{"first_name": "John", "last_name": "Doe"}]}},
                "changes": {"added": ["email"], "modified": ["name"], "removed": []}
            }
        }
    )

    timestamp: datetime = Field(..., description="When this version was created")
    version_number: int = Field(..., ge=1, description="Version sequence number")
    profile_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete profile at this version"
    )
    changes: Dict[str, List[str]] = Field(
        default_factory=lambda: {"added": [], "modified": [], "removed": []},
        description="Changes from previous version"
    )
    change_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed change information"
    )


class EntityEvolution(BaseModel):
    """
    The complete evolution history of an entity over time.

    Tracks all versions of an entity's profile, showing how it
    changed over time.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_label": "John Doe",
                "versions": [],
                "total_versions": 5,
                "first_seen": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }
    )

    entity_id: str = Field(..., description="Entity identifier")
    entity_label: str = Field(..., description="Current display label")
    versions: List[EntityVersion] = Field(default_factory=list, description="Version history")
    total_versions: int = Field(default=0, ge=0, description="Total number of versions")
    first_seen: Optional[datetime] = Field(None, description="When entity was first created")
    last_updated: Optional[datetime] = Field(None, description="Most recent update timestamp")
    relationship_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of relationship changes"
    )


class PeriodStats(BaseModel):
    """Statistics for a time period."""
    start_date: datetime = Field(..., description="Period start")
    end_date: datetime = Field(..., description="Period end")
    total_events: int = Field(default=0, ge=0, description="Total events in period")
    entity_events: int = Field(default=0, ge=0, description="Entity-related events")
    relationship_events: int = Field(default=0, ge=0, description="Relationship-related events")
    new_entities: int = Field(default=0, ge=0, description="Entities created in period")
    new_relationships: int = Field(default=0, ge=0, description="Relationships created in period")
    active_entities: int = Field(default=0, ge=0, description="Entities with activity")
    event_type_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Events by type"
    )
    graph_stats: GraphStats = Field(
        default_factory=GraphStats,
        description="Graph statistics at period end"
    )


class StatsDifference(BaseModel):
    """Difference between two sets of statistics."""
    metric: str = Field(..., description="Metric name")
    period1_value: float = Field(..., description="Value in period 1")
    period2_value: float = Field(..., description="Value in period 2")
    absolute_change: float = Field(..., description="Absolute change (period2 - period1)")
    percent_change: Optional[float] = Field(
        None,
        description="Percentage change (None if period1 is 0)"
    )
    trend: str = Field(default="stable", description="Trend direction: increase, decrease, stable")


class PeriodComparison(BaseModel):
    """
    Comparison of graph statistics between two time periods.

    Useful for trend analysis and identifying changes in activity patterns.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period1_stats": {"start_date": "2024-01-01", "end_date": "2024-01-07"},
                "period2_stats": {"start_date": "2024-01-08", "end_date": "2024-01-14"},
                "differences": []
            }
        }
    )

    period1_stats: PeriodStats = Field(..., description="Statistics for first period")
    period2_stats: PeriodStats = Field(..., description="Statistics for second period")
    differences: List[StatsDifference] = Field(
        default_factory=list,
        description="Computed differences between periods"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of significant changes"
    )


class TimePeriod(BaseModel):
    """A time period specification for comparison."""
    start_date: datetime = Field(..., description="Period start (inclusive)")
    end_date: datetime = Field(..., description="Period end (inclusive)")

    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        """Validate that end_date is after start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


# =============================================================================
# TIMELINE VISUALIZATION SERVICE
# =============================================================================


class TimelineVisualizationService:
    """
    Timeline Visualization Service for Basset Hound OSINT Platform.

    Provides temporal graph visualization capabilities including:
    - Entity timeline events
    - Relationship timeline tracking
    - Activity heatmaps
    - Temporal graph snapshots
    - Entity evolution history
    - Time period comparisons

    This service integrates with:
    - TimelineService for event data
    - GraphVisualizationService for graph snapshots
    - AuditLogger for change tracking
    """

    def __init__(
        self,
        neo4j_handler=None,
        timeline_service=None,
        graph_visualization_service=None,
        audit_logger=None
    ):
        """
        Initialize the Timeline Visualization Service.

        Args:
            neo4j_handler: Neo4j database handler for direct queries
            timeline_service: TimelineService instance for event data
            graph_visualization_service: GraphVisualizationService for snapshots
            audit_logger: AuditLogger instance for change tracking
        """
        self.neo4j_handler = neo4j_handler
        self.timeline_service = timeline_service
        self.graph_visualization_service = graph_visualization_service
        self.audit_logger = audit_logger

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse various datetime formats into a datetime object."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Handle ISO format with Z suffix
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try parsing without timezone
                    return datetime.fromisoformat(value)
                except ValueError:
                    return None
        if hasattr(value, 'to_native'):
            # Neo4j datetime
            return value.to_native()
        return None

    def _extract_entity_label(self, entity: Dict[str, Any]) -> str:
        """Extract a display label from an entity."""
        if not entity:
            return "Unknown"

        entity_id = entity.get("id", "")
        profile = entity.get("profile", {})

        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except json.JSONDecodeError:
                profile = {}

        # Try profile section
        if "profile" in profile:
            profile_section = profile["profile"]
            first_name = profile_section.get("first_name", "")
            last_name = profile_section.get("last_name", "")
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            if "full_name" in profile_section:
                return profile_section["full_name"]
            if "name" in profile_section:
                return profile_section["name"]

        # Try core section
        if "core" in profile:
            core = profile["core"]
            names = core.get("name", [])
            if names and isinstance(names, list) and len(names) > 0:
                name_obj = names[0]
                if isinstance(name_obj, dict):
                    first = name_obj.get("first_name", "")
                    last = name_obj.get("last_name", "")
                    if first or last:
                        return f"{first} {last}".strip()

        return f"Entity {entity_id[:8]}" if entity_id else "Unknown"

    async def get_entity_timeline(
        self,
        project_id: str,
        entity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None
    ) -> List[TimelineEvent]:
        """
        Get timeline events for a specific entity.

        Retrieves all events related to an entity within the specified
        time range, including creation, updates, relationship changes,
        and other tracked events.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier
            start_date: Optional start of time range filter
            end_date: Optional end of time range filter
            event_types: Optional list of event types to filter by

        Returns:
            List of TimelineEvent objects ordered by timestamp descending
        """
        events = []

        # Get events from TimelineService if available
        if self.timeline_service:
            try:
                if hasattr(self.timeline_service, 'get_entity_timeline_async'):
                    raw_events = await self.timeline_service.get_entity_timeline_async(
                        project_id=project_id,
                        entity_id=entity_id,
                        start_date=start_date,
                        end_date=end_date,
                        event_types=event_types
                    )
                else:
                    raw_events = self.timeline_service.get_entity_timeline(
                        project_id=project_id,
                        entity_id=entity_id,
                        start_date=start_date,
                        end_date=end_date,
                        event_types=event_types
                    )

                for raw_event in raw_events:
                    timestamp = self._parse_datetime(raw_event.timestamp)
                    if timestamp:
                        events.append(TimelineEvent(
                            timestamp=timestamp,
                            event_type=raw_event.event_type,
                            entity_id=raw_event.entity_id,
                            details=raw_event.details or {},
                            metadata={"actor": raw_event.actor} if raw_event.actor else {},
                            event_id=raw_event.event_id
                        ))
            except Exception as e:
                logger.error(f"Failed to get timeline events from TimelineService: {e}")

        # Get events from AuditLogger if available
        if self.audit_logger:
            try:
                audit_logs = await self.audit_logger.get_logs(
                    entity_id=entity_id,
                    project_id=project_id,
                    start_date=start_date,
                    end_date=end_date
                )

                for log in audit_logs:
                    timestamp = self._parse_datetime(log.timestamp)
                    if timestamp:
                        # Map audit action to timeline event type
                        event_type_map = {
                            "CREATE": TimelineEventType.ENTITY_CREATED.value,
                            "UPDATE": TimelineEventType.ENTITY_UPDATED.value,
                            "DELETE": TimelineEventType.ENTITY_DELETED.value,
                            "LINK": TimelineEventType.RELATIONSHIP_ADDED.value,
                            "UNLINK": TimelineEventType.RELATIONSHIP_REMOVED.value,
                        }
                        event_type = event_type_map.get(
                            log.action.value if hasattr(log.action, 'value') else log.action,
                            "unknown"
                        )

                        # Filter by event types if specified
                        if event_types and event_type not in event_types:
                            continue

                        events.append(TimelineEvent(
                            timestamp=timestamp,
                            event_type=event_type,
                            entity_id=entity_id,
                            details=log.changes or {},
                            metadata=log.metadata or {},
                            event_id=log.id
                        ))
            except Exception as e:
                logger.error(f"Failed to get audit logs: {e}")

        # Sort by timestamp descending and deduplicate
        seen_ids = set()
        unique_events = []
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True):
            if event.event_id not in seen_ids:
                seen_ids.add(event.event_id)
                unique_events.append(event)

        return unique_events

    async def get_relationship_timeline(
        self,
        project_id: str,
        entity1_id: str,
        entity2_id: str
    ) -> List[TimelineEvent]:
        """
        Get timeline of relationship changes between two entities.

        Tracks all events related to the relationship between two specific
        entities, including when it was created, modified, or removed.

        Args:
            project_id: Project identifier
            entity1_id: First entity identifier
            entity2_id: Second entity identifier

        Returns:
            List of TimelineEvent objects related to the relationship
        """
        events = []

        # Get events from TimelineService if available
        if self.timeline_service:
            try:
                if hasattr(self.timeline_service, 'get_relationship_history_async'):
                    raw_events = await self.timeline_service.get_relationship_history_async(
                        project_id=project_id,
                        entity1_id=entity1_id,
                        entity2_id=entity2_id
                    )
                else:
                    raw_events = self.timeline_service.get_relationship_history(
                        project_id=project_id,
                        entity1_id=entity1_id,
                        entity2_id=entity2_id
                    )

                for raw_event in raw_events:
                    timestamp = self._parse_datetime(raw_event.timestamp)
                    if timestamp:
                        events.append(TimelineEvent(
                            timestamp=timestamp,
                            event_type=raw_event.event_type,
                            entity_id=raw_event.entity_id,
                            details={
                                **raw_event.details,
                                "entity1_id": entity1_id,
                                "entity2_id": entity2_id
                            },
                            metadata={"actor": raw_event.actor} if raw_event.actor else {},
                            event_id=raw_event.event_id
                        ))
            except Exception as e:
                logger.error(f"Failed to get relationship history from TimelineService: {e}")

        # Also check audit logs for relationship events
        if self.audit_logger:
            try:
                # Get logs for both entities
                for entity_id in [entity1_id, entity2_id]:
                    audit_logs = await self.audit_logger.get_logs(
                        entity_id=entity_id,
                        project_id=project_id
                    )

                    for log in audit_logs:
                        # Check if this log relates to the relationship
                        changes = log.changes or {}
                        target_id = changes.get("target_entity_id")

                        if target_id in [entity1_id, entity2_id]:
                            timestamp = self._parse_datetime(log.timestamp)
                            if timestamp:
                                events.append(TimelineEvent(
                                    timestamp=timestamp,
                                    event_type=log.action.value if hasattr(log.action, 'value') else str(log.action),
                                    entity_id=entity_id,
                                    details={
                                        **changes,
                                        "entity1_id": entity1_id,
                                        "entity2_id": entity2_id
                                    },
                                    metadata=log.metadata or {},
                                    event_id=log.id
                                ))
            except Exception as e:
                logger.error(f"Failed to get audit logs for relationship: {e}")

        # Sort and deduplicate
        seen_ids = set()
        unique_events = []
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True):
            if event.event_id not in seen_ids:
                seen_ids.add(event.event_id)
                unique_events.append(event)

        return unique_events

    async def get_project_activity_timeline(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimelineGranularity = TimelineGranularity.DAY
    ) -> List[ActivityHeatmapData]:
        """
        Get activity heatmap data for a project.

        Aggregates events into time buckets based on the specified granularity,
        providing data suitable for heatmap visualization.

        Args:
            project_id: Project identifier
            start_date: Start of time range (defaults to 30 days ago)
            end_date: End of time range (defaults to now)
            granularity: Time bucket granularity (hour, day, week, month)

        Returns:
            List of ActivityHeatmapData objects for each time bucket
        """
        # Set default date range
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Initialize buckets based on granularity
        buckets: Dict[str, Dict[str, Any]] = {}

        def get_bucket_key(dt: datetime) -> str:
            """Get the bucket key for a datetime based on granularity."""
            if granularity == TimelineGranularity.HOUR:
                return dt.strftime("%Y-%m-%d %H:00")
            elif granularity == TimelineGranularity.DAY:
                return dt.strftime("%Y-%m-%d")
            elif granularity == TimelineGranularity.WEEK:
                # ISO week
                return dt.strftime("%Y-W%W")
            elif granularity == TimelineGranularity.MONTH:
                return dt.strftime("%Y-%m")
            return dt.strftime("%Y-%m-%d")

        # Generate all bucket keys in the range
        current = start_date
        while current <= end_date:
            key = get_bucket_key(current)
            if key not in buckets:
                buckets[key] = {
                    "count": 0,
                    "entity_count": 0,
                    "relationship_count": 0,
                    "event_types": defaultdict(int)
                }

            # Advance based on granularity
            if granularity == TimelineGranularity.HOUR:
                current += timedelta(hours=1)
            elif granularity == TimelineGranularity.DAY:
                current += timedelta(days=1)
            elif granularity == TimelineGranularity.WEEK:
                current += timedelta(weeks=1)
            elif granularity == TimelineGranularity.MONTH:
                # Approximate month advancement
                current += timedelta(days=30)

        # Collect events from TimelineService
        if self.timeline_service:
            try:
                if hasattr(self.timeline_service, 'get_project_timeline_async'):
                    raw_events = await self.timeline_service.get_project_timeline_async(
                        project_id=project_id,
                        start_date=start_date,
                        end_date=end_date,
                        limit=10000  # Get all events in range
                    )
                else:
                    raw_events = self.timeline_service.get_project_timeline(
                        project_id=project_id,
                        start_date=start_date,
                        end_date=end_date,
                        limit=10000
                    )

                for event in raw_events:
                    timestamp = self._parse_datetime(event.timestamp)
                    if timestamp and start_date <= timestamp <= end_date:
                        key = get_bucket_key(timestamp)
                        if key in buckets:
                            buckets[key]["count"] += 1
                            buckets[key]["event_types"][event.event_type] += 1

                            # Categorize as entity or relationship event
                            if "RELATIONSHIP" in event.event_type.upper():
                                buckets[key]["relationship_count"] += 1
                            else:
                                buckets[key]["entity_count"] += 1
            except Exception as e:
                logger.error(f"Failed to get project timeline: {e}")

        # Also include audit log data
        if self.audit_logger:
            try:
                audit_logs = await self.audit_logger.get_logs(
                    project_id=project_id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000
                )

                for log in audit_logs:
                    timestamp = self._parse_datetime(log.timestamp)
                    if timestamp and start_date <= timestamp <= end_date:
                        key = get_bucket_key(timestamp)
                        if key in buckets:
                            buckets[key]["count"] += 1
                            action = log.action.value if hasattr(log.action, 'value') else str(log.action)
                            buckets[key]["event_types"][action] += 1

                            if action in ("LINK", "UNLINK"):
                                buckets[key]["relationship_count"] += 1
                            else:
                                buckets[key]["entity_count"] += 1
            except Exception as e:
                logger.error(f"Failed to get audit logs: {e}")

        # Convert to ActivityHeatmapData objects
        result = []
        for date_key in sorted(buckets.keys()):
            bucket = buckets[date_key]
            result.append(ActivityHeatmapData(
                date=date_key,
                count=bucket["count"],
                entity_count=bucket["entity_count"],
                relationship_count=bucket["relationship_count"],
                event_types=dict(bucket["event_types"])
            ))

        return result

    async def get_temporal_graph_snapshot(
        self,
        project_id: str,
        timestamp: datetime
    ) -> TemporalSnapshot:
        """
        Get the graph state at a specific point in time.

        Reconstructs the graph as it existed at the specified timestamp,
        including only entities and relationships that existed at that time.

        Args:
            project_id: Project identifier
            timestamp: Point in time for the snapshot

        Returns:
            TemporalSnapshot with nodes, edges, and statistics
        """
        nodes = []
        edges = []

        # Get graph data from Neo4j if available
        if self.neo4j_handler:
            try:
                # Get all entities
                all_entities = self.neo4j_handler.get_all_people(project_id) or []

                entity_ids = set()
                for entity in all_entities:
                    if not entity or not entity.get("id"):
                        continue

                    # Check if entity existed at the given timestamp
                    created_at = self._parse_datetime(entity.get("created_at"))
                    if created_at and created_at > timestamp:
                        continue  # Entity didn't exist yet

                    entity_id = entity["id"]
                    entity_ids.add(entity_id)

                    nodes.append({
                        "id": entity_id,
                        "label": self._extract_entity_label(entity),
                        "entity_type": "Person",
                        "properties": entity.get("profile", {}),
                        "created_at": entity.get("created_at")
                    })

                # Get relationships/tags
                edge_index = 0
                for entity in all_entities:
                    if not entity:
                        continue

                    entity_id = entity.get("id")
                    if entity_id not in entity_ids:
                        continue

                    profile = entity.get("profile", {})
                    if isinstance(profile, str):
                        try:
                            profile = json.loads(profile)
                        except json.JSONDecodeError:
                            profile = {}

                    tagged_section = profile.get("Tagged People", {})
                    tagged_ids = tagged_section.get("tagged_people", []) or []
                    if not isinstance(tagged_ids, list):
                        tagged_ids = [tagged_ids] if tagged_ids else []

                    relationship_types = tagged_section.get("relationship_types", {}) or {}

                    for target_id in tagged_ids:
                        if target_id in entity_ids:
                            edges.append({
                                "id": f"edge_{edge_index}",
                                "source": entity_id,
                                "target": target_id,
                                "relationship_type": relationship_types.get(target_id, "RELATED_TO"),
                                "properties": {},
                                "created_at": None
                            })
                            edge_index += 1

            except Exception as e:
                logger.error(f"Failed to get graph data for snapshot: {e}")

        # Calculate statistics
        stats = self._calculate_graph_stats(nodes, edges)

        return TemporalSnapshot(
            timestamp=timestamp,
            nodes=nodes,
            edges=edges,
            stats=stats
        )

    def _calculate_graph_stats(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> GraphStats:
        """Calculate graph statistics from nodes and edges."""
        n = len(nodes)
        m = len(edges)

        if n == 0:
            return GraphStats()

        # Calculate degrees
        degrees = {node["id"]: 0 for node in nodes}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in degrees:
                degrees[source] += 1
            if target in degrees:
                degrees[target] += 1

        degree_values = list(degrees.values())
        avg_degree = sum(degree_values) / n if n > 0 else 0.0
        isolated_nodes = sum(1 for d in degree_values if d == 0)

        # Calculate density
        max_edges = n * (n - 1) / 2 if n > 1 else 1
        density = m / max_edges if max_edges > 0 else 0.0

        # Entity type distribution
        entity_types: Dict[str, int] = defaultdict(int)
        for node in nodes:
            entity_types[node.get("entity_type", "Person")] += 1

        # Relationship type distribution
        relationship_types: Dict[str, int] = defaultdict(int)
        for edge in edges:
            relationship_types[edge.get("relationship_type", "RELATED_TO")] += 1

        return GraphStats(
            node_count=n,
            edge_count=m,
            density=round(density, 4),
            avg_degree=round(avg_degree, 2),
            isolated_nodes=isolated_nodes,
            entity_type_distribution=dict(entity_types),
            relationship_type_distribution=dict(relationship_types)
        )

    async def get_entity_evolution(
        self,
        project_id: str,
        entity_id: str
    ) -> EntityEvolution:
        """
        Get the evolution history of an entity's profile over time.

        Tracks all changes to an entity's profile, creating a version
        history that shows how the entity evolved.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier

        Returns:
            EntityEvolution with version history and change details
        """
        versions: List[EntityVersion] = []
        entity_label = "Unknown"
        first_seen = None
        last_updated = None
        relationship_history = []

        # Get current entity state
        if self.neo4j_handler:
            try:
                entity = self.neo4j_handler.get_person(project_id, entity_id)
                if entity:
                    entity_label = self._extract_entity_label(entity)
                    first_seen = self._parse_datetime(entity.get("created_at"))
                    last_updated = self._parse_datetime(entity.get("updated_at"))

                    # Create current version
                    current_profile = entity.get("profile", {})
                    if isinstance(current_profile, str):
                        try:
                            current_profile = json.loads(current_profile)
                        except json.JSONDecodeError:
                            current_profile = {}

                    if last_updated:
                        versions.append(EntityVersion(
                            timestamp=last_updated,
                            version_number=1,  # Will be renumbered
                            profile_snapshot=current_profile,
                            changes={"added": [], "modified": [], "removed": []},
                            change_details={}
                        ))
            except Exception as e:
                logger.error(f"Failed to get current entity state: {e}")

        # Get historical changes from timeline events
        events = await self.get_entity_timeline(project_id, entity_id)

        version_number = len(versions)
        for event in events:
            if event.event_type in [
                TimelineEventType.ENTITY_CREATED.value,
                TimelineEventType.ENTITY_UPDATED.value,
                TimelineEventType.PROFILE_CHANGED.value,
                "CREATED",
                "UPDATED"
            ]:
                version_number += 1

                # Extract change details
                changes = {
                    "added": event.details.get("added_fields", []),
                    "modified": event.details.get("modified_fields", []),
                    "removed": event.details.get("removed_fields", [])
                }

                # Track first seen
                if first_seen is None or event.timestamp < first_seen:
                    first_seen = event.timestamp

                versions.append(EntityVersion(
                    timestamp=event.timestamp,
                    version_number=version_number,
                    profile_snapshot=event.details.get("profile_snapshot", {}),
                    changes=changes,
                    change_details=event.details
                ))

            elif event.event_type in [
                TimelineEventType.RELATIONSHIP_ADDED.value,
                TimelineEventType.RELATIONSHIP_REMOVED.value,
                TimelineEventType.RELATIONSHIP_UPDATED.value,
                "RELATIONSHIP_ADDED",
                "RELATIONSHIP_REMOVED",
                "RELATIONSHIP_UPDATED",
                "LINK",
                "UNLINK"
            ]:
                relationship_history.append({
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "details": event.details
                })

        # Sort versions by timestamp and renumber
        versions.sort(key=lambda v: v.timestamp)
        for i, version in enumerate(versions, 1):
            version.version_number = i

        return EntityEvolution(
            entity_id=entity_id,
            entity_label=entity_label,
            versions=versions,
            total_versions=len(versions),
            first_seen=first_seen,
            last_updated=last_updated,
            relationship_history=relationship_history
        )

    async def compare_time_periods(
        self,
        project_id: str,
        period1: TimePeriod,
        period2: TimePeriod
    ) -> PeriodComparison:
        """
        Compare graph statistics between two time periods.

        Useful for trend analysis and identifying changes in activity
        patterns, entity growth, and relationship changes.

        Args:
            project_id: Project identifier
            period1: First time period to compare
            period2: Second time period to compare

        Returns:
            PeriodComparison with statistics and differences
        """
        # Get statistics for period 1
        period1_stats = await self._get_period_stats(
            project_id,
            period1.start_date,
            period1.end_date
        )

        # Get statistics for period 2
        period2_stats = await self._get_period_stats(
            project_id,
            period2.start_date,
            period2.end_date
        )

        # Calculate differences
        differences = []
        metrics_to_compare = [
            ("total_events", period1_stats.total_events, period2_stats.total_events),
            ("entity_events", period1_stats.entity_events, period2_stats.entity_events),
            ("relationship_events", period1_stats.relationship_events, period2_stats.relationship_events),
            ("new_entities", period1_stats.new_entities, period2_stats.new_entities),
            ("new_relationships", period1_stats.new_relationships, period2_stats.new_relationships),
            ("active_entities", period1_stats.active_entities, period2_stats.active_entities),
            ("node_count", period1_stats.graph_stats.node_count, period2_stats.graph_stats.node_count),
            ("edge_count", period1_stats.graph_stats.edge_count, period2_stats.graph_stats.edge_count),
            ("density", period1_stats.graph_stats.density, period2_stats.graph_stats.density),
            ("avg_degree", period1_stats.graph_stats.avg_degree, period2_stats.graph_stats.avg_degree),
        ]

        for metric, val1, val2 in metrics_to_compare:
            absolute_change = val2 - val1

            if val1 != 0:
                percent_change = ((val2 - val1) / val1) * 100
            else:
                percent_change = None

            if absolute_change > 0:
                trend = "increase"
            elif absolute_change < 0:
                trend = "decrease"
            else:
                trend = "stable"

            differences.append(StatsDifference(
                metric=metric,
                period1_value=float(val1),
                period2_value=float(val2),
                absolute_change=float(absolute_change),
                percent_change=round(percent_change, 2) if percent_change is not None else None,
                trend=trend
            ))

        # Generate summary
        summary = {
            "overall_trend": "growth" if period2_stats.total_events > period1_stats.total_events else "decline",
            "entity_trend": "growth" if period2_stats.entity_events > period1_stats.entity_events else "decline",
            "relationship_trend": "growth" if period2_stats.relationship_events > period1_stats.relationship_events else "decline",
            "most_increased_metric": max(differences, key=lambda d: d.absolute_change).metric,
            "most_decreased_metric": min(differences, key=lambda d: d.absolute_change).metric,
        }

        return PeriodComparison(
            period1_stats=period1_stats,
            period2_stats=period2_stats,
            differences=differences,
            summary=summary
        )

    async def _get_period_stats(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> PeriodStats:
        """Get statistics for a specific time period."""
        total_events = 0
        entity_events = 0
        relationship_events = 0
        new_entities = 0
        new_relationships = 0
        active_entity_ids: set = set()
        event_type_breakdown: Dict[str, int] = defaultdict(int)

        # Collect events from timeline service
        if self.timeline_service:
            try:
                if hasattr(self.timeline_service, 'get_project_timeline_async'):
                    events = await self.timeline_service.get_project_timeline_async(
                        project_id=project_id,
                        start_date=start_date,
                        end_date=end_date,
                        limit=10000
                    )
                else:
                    events = self.timeline_service.get_project_timeline(
                        project_id=project_id,
                        start_date=start_date,
                        end_date=end_date,
                        limit=10000
                    )

                for event in events:
                    total_events += 1
                    event_type_breakdown[event.event_type] += 1
                    active_entity_ids.add(event.entity_id)

                    if "RELATIONSHIP" in event.event_type.upper():
                        relationship_events += 1
                        if "ADDED" in event.event_type.upper():
                            new_relationships += 1
                    else:
                        entity_events += 1
                        if "CREATED" in event.event_type.upper():
                            new_entities += 1
            except Exception as e:
                logger.error(f"Failed to get period stats from timeline: {e}")

        # Get graph snapshot at end of period for graph stats
        snapshot = await self.get_temporal_graph_snapshot(project_id, end_date)

        return PeriodStats(
            start_date=start_date,
            end_date=end_date,
            total_events=total_events,
            entity_events=entity_events,
            relationship_events=relationship_events,
            new_entities=new_entities,
            new_relationships=new_relationships,
            active_entities=len(active_entity_ids),
            event_type_breakdown=dict(event_type_breakdown),
            graph_stats=snapshot.stats
        )


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================


_timeline_visualization_service: Optional[TimelineVisualizationService] = None


def get_timeline_visualization_service(
    neo4j_handler=None,
    timeline_service=None,
    graph_visualization_service=None,
    audit_logger=None
) -> TimelineVisualizationService:
    """
    Get or create the TimelineVisualizationService singleton.

    Args:
        neo4j_handler: Optional Neo4j database handler
        timeline_service: Optional TimelineService instance
        graph_visualization_service: Optional GraphVisualizationService instance
        audit_logger: Optional AuditLogger instance

    Returns:
        TimelineVisualizationService instance
    """
    global _timeline_visualization_service

    if _timeline_visualization_service is None:
        _timeline_visualization_service = TimelineVisualizationService(
            neo4j_handler=neo4j_handler,
            timeline_service=timeline_service,
            graph_visualization_service=graph_visualization_service,
            audit_logger=audit_logger
        )
    else:
        # Update handlers if provided
        if neo4j_handler is not None:
            _timeline_visualization_service.neo4j_handler = neo4j_handler
        if timeline_service is not None:
            _timeline_visualization_service.timeline_service = timeline_service
        if graph_visualization_service is not None:
            _timeline_visualization_service.graph_visualization_service = graph_visualization_service
        if audit_logger is not None:
            _timeline_visualization_service.audit_logger = audit_logger

    return _timeline_visualization_service


def set_timeline_visualization_service(
    service: Optional[TimelineVisualizationService]
) -> None:
    """
    Set the timeline visualization service singleton.

    Useful for testing or replacing with a custom implementation.

    Args:
        service: TimelineVisualizationService instance or None to clear
    """
    global _timeline_visualization_service
    _timeline_visualization_service = service
