"""
Temporal Pattern Detection Service for Basset Hound.

Detects temporal patterns in relationship changes and entity activity.
Focuses on identifying trends, bursts, and cyclical patterns in graph evolution.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict


logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class PatternType(str, Enum):
    """Types of temporal patterns that can be detected."""
    BURST = "burst"           # Sudden spike in activity
    TREND = "trend"           # Gradual increase/decrease
    CYCLICAL = "cyclical"     # Repeating pattern
    ANOMALY = "anomaly"       # Unusual deviation from normal
    STABLE = "stable"         # Consistent activity level


class TrendDirection(str, Enum):
    """Direction of a detected trend."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class TimeWindow(str, Enum):
    """Time window sizes for analysis."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class ActivityBucket(BaseModel):
    """Activity count for a time bucket."""
    model_config = ConfigDict(frozen=True)

    start_time: datetime = Field(..., description="Start of the time bucket")
    end_time: datetime = Field(..., description="End of the time bucket")
    event_count: int = Field(default=0, ge=0, description="Number of events")
    entity_count: int = Field(default=0, ge=0, description="Unique entities involved")
    relationship_count: int = Field(default=0, ge=0, description="Relationships created/modified")


class BurstDetection(BaseModel):
    """A detected activity burst."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T12:00:00Z",
                "intensity": 3.5,
                "event_count": 150,
                "baseline_average": 42.8
            }
        }
    )

    start_time: datetime = Field(..., description="When the burst started")
    end_time: datetime = Field(..., description="When the burst ended")
    intensity: float = Field(..., ge=0, description="Intensity relative to baseline (e.g., 3.5x normal)")
    event_count: int = Field(..., ge=0, description="Total events during burst")
    baseline_average: float = Field(..., ge=0, description="Normal average for comparison")
    peak_time: Optional[datetime] = Field(None, description="Time of maximum activity")
    involved_entities: List[str] = Field(default_factory=list, description="Entity IDs with most activity")


class TrendAnalysis(BaseModel):
    """A detected trend in activity."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "direction": "increasing",
                "slope": 0.15,
                "start_value": 10,
                "end_value": 25,
                "confidence": 0.85
            }
        }
    )

    direction: TrendDirection = Field(..., description="Trend direction")
    slope: float = Field(..., description="Rate of change per time unit")
    start_value: float = Field(..., description="Activity level at start")
    end_value: float = Field(..., description="Activity level at end")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in trend detection")
    start_time: Optional[datetime] = Field(None, description="Trend start time")
    end_time: Optional[datetime] = Field(None, description="Trend end time")


class CyclicalPattern(BaseModel):
    """A detected cyclical/repeating pattern."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_days": 7.0,
                "period_description": "weekly",
                "peak_day": "Monday",
                "trough_day": "Saturday"
            }
        }
    )

    period_days: float = Field(..., gt=0, description="Period length in days")
    period_description: str = Field(..., description="Human-readable period (e.g., 'weekly')")
    amplitude: float = Field(default=0.0, description="Amplitude of oscillation")
    phase_offset: float = Field(default=0.0, description="Phase offset in days")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Confidence in pattern")
    peak_day: Optional[str] = Field(None, description="Day of week with highest activity")
    trough_day: Optional[str] = Field(None, description="Day of week with lowest activity")


class TemporalAnomaly(BaseModel):
    """A detected temporal anomaly."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2024-01-15T14:30:00Z",
                "anomaly_score": 0.92,
                "description": "Activity 4.2 standard deviations above normal"
            }
        }
    )

    timestamp: datetime = Field(..., description="When the anomaly occurred")
    anomaly_score: float = Field(..., ge=0, le=1, description="Anomaly score (0=normal, 1=extreme)")
    expected_value: float = Field(..., description="Expected activity level")
    actual_value: float = Field(..., description="Actual activity level")
    deviation: float = Field(..., description="Standard deviations from expected")
    description: str = Field(default="", description="Human-readable description")
    involved_entities: List[str] = Field(default_factory=list, description="Entities involved")


class EntityTemporalProfile(BaseModel):
    """Temporal activity profile for an entity."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "uuid",
                "first_activity": "2024-01-01T00:00:00Z",
                "last_activity": "2024-01-15T14:30:00Z",
                "total_events": 150
            }
        }
    )

    entity_id: str = Field(..., description="Entity identifier")
    first_activity: Optional[datetime] = Field(None, description="First recorded activity")
    last_activity: Optional[datetime] = Field(None, description="Most recent activity")
    total_events: int = Field(default=0, ge=0, description="Total event count")
    avg_events_per_day: float = Field(default=0.0, ge=0, description="Average daily activity")
    most_active_hour: Optional[int] = Field(None, ge=0, le=23, description="Hour with most activity")
    most_active_day: Optional[str] = Field(None, description="Day of week with most activity")
    activity_trend: Optional[TrendDirection] = Field(None, description="Recent activity trend")


class RelationshipTemporalPattern(BaseModel):
    """Temporal pattern for relationship between two entities."""
    entity1_id: str = Field(..., description="First entity")
    entity2_id: str = Field(..., description="Second entity")
    first_interaction: Optional[datetime] = Field(None, description="First recorded interaction")
    last_interaction: Optional[datetime] = Field(None, description="Most recent interaction")
    interaction_count: int = Field(default=0, ge=0, description="Total interactions")
    avg_interval_days: Optional[float] = Field(None, description="Average days between interactions")
    relationship_age_days: float = Field(default=0.0, description="Days since first interaction")
    is_active: bool = Field(default=True, description="Whether relationship is currently active")


class TemporalPatternReport(BaseModel):
    """Complete temporal pattern analysis report."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-project",
                "analysis_window_days": 30,
                "total_events_analyzed": 5000
            }
        }
    )

    project_id: str = Field(..., description="Project analyzed")
    analysis_start: datetime = Field(..., description="Start of analysis window")
    analysis_end: datetime = Field(..., description="End of analysis window")
    analysis_window_days: int = Field(..., description="Window size in days")
    total_events_analyzed: int = Field(default=0, ge=0, description="Events analyzed")

    # Pattern detections
    bursts: List[BurstDetection] = Field(default_factory=list, description="Detected bursts")
    trend: Optional[TrendAnalysis] = Field(None, description="Overall trend")
    cyclical_patterns: List[CyclicalPattern] = Field(default_factory=list, description="Cyclical patterns")
    anomalies: List[TemporalAnomaly] = Field(default_factory=list, description="Anomalies detected")

    # Summary statistics
    avg_daily_events: float = Field(default=0.0, description="Average events per day")
    peak_day: Optional[str] = Field(None, description="Day with highest activity")
    quietest_day: Optional[str] = Field(None, description="Day with lowest activity")


# =============================================================================
# TEMPORAL PATTERNS SERVICE
# =============================================================================


class TemporalPatternsService:
    """
    Detects temporal patterns in graph activity.

    Features:
    - Burst detection using sliding window analysis
    - Trend detection using linear regression
    - Cyclical pattern detection using frequency analysis
    - Anomaly detection using statistical thresholds
    """

    def __init__(
        self,
        neo4j_handler=None,
        timeline_service=None,
        burst_threshold: float = 2.0,
        anomaly_threshold: float = 3.0
    ):
        """
        Initialize the service.

        Args:
            neo4j_handler: Neo4j database handler
            timeline_service: Timeline service for event data
            burst_threshold: Standard deviations above mean to detect burst
            anomaly_threshold: Standard deviations for anomaly detection
        """
        self.neo4j_handler = neo4j_handler
        self.timeline_service = timeline_service
        self.burst_threshold = burst_threshold
        self.anomaly_threshold = anomaly_threshold

    def _get_activity_buckets(
        self,
        events: List[Dict[str, Any]],
        window: TimeWindow,
        start_time: datetime,
        end_time: datetime
    ) -> List[ActivityBucket]:
        """Aggregate events into time buckets."""
        # Determine bucket size
        if window == TimeWindow.HOUR:
            bucket_delta = timedelta(hours=1)
        elif window == TimeWindow.DAY:
            bucket_delta = timedelta(days=1)
        elif window == TimeWindow.WEEK:
            bucket_delta = timedelta(weeks=1)
        else:  # MONTH
            bucket_delta = timedelta(days=30)

        # Initialize buckets
        buckets = []
        current = start_time
        while current < end_time:
            bucket_end = min(current + bucket_delta, end_time)
            buckets.append({
                "start_time": current,
                "end_time": bucket_end,
                "event_count": 0,
                "entities": set(),
                "relationships": 0
            })
            current = bucket_end

        # Aggregate events into buckets
        for event in events:
            event_time = event.get("timestamp")
            if event_time is None:
                continue

            if isinstance(event_time, str):
                try:
                    event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                except ValueError:
                    continue

            for bucket in buckets:
                if bucket["start_time"] <= event_time < bucket["end_time"]:
                    bucket["event_count"] += 1
                    if entity_id := event.get("entity_id"):
                        bucket["entities"].add(entity_id)
                    if "relationship" in event.get("event_type", "").lower():
                        bucket["relationships"] += 1
                    break

        # Convert to Pydantic models
        return [
            ActivityBucket(
                start_time=b["start_time"],
                end_time=b["end_time"],
                event_count=b["event_count"],
                entity_count=len(b["entities"]),
                relationship_count=b["relationships"]
            )
            for b in buckets
        ]

    def detect_bursts(
        self,
        buckets: List[ActivityBucket],
        threshold: Optional[float] = None
    ) -> List[BurstDetection]:
        """
        Detect activity bursts in time series data.

        Uses statistical threshold detection:
        - Calculate mean and standard deviation
        - Flag periods with activity > mean + threshold * std
        """
        if not buckets or len(buckets) < 3:
            return []

        threshold = threshold or self.burst_threshold
        counts = [b.event_count for b in buckets]

        # Calculate baseline statistics
        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return []  # No variation

        burst_threshold = mean_count + threshold * std_dev

        # Find burst periods
        bursts = []
        in_burst = False
        burst_start = None
        burst_events = 0
        burst_peak_time = None
        burst_peak_count = 0

        for bucket in buckets:
            if bucket.event_count > burst_threshold:
                if not in_burst:
                    in_burst = True
                    burst_start = bucket.start_time
                    burst_events = 0
                    burst_peak_count = 0

                burst_events += bucket.event_count
                if bucket.event_count > burst_peak_count:
                    burst_peak_count = bucket.event_count
                    burst_peak_time = bucket.start_time
            else:
                if in_burst:
                    # End of burst
                    bursts.append(BurstDetection(
                        start_time=burst_start,
                        end_time=bucket.start_time,
                        intensity=burst_events / max(mean_count * ((bucket.start_time - burst_start).total_seconds() / 3600), 1),
                        event_count=burst_events,
                        baseline_average=mean_count,
                        peak_time=burst_peak_time
                    ))
                    in_burst = False

        # Handle burst extending to end
        if in_burst and burst_start:
            bursts.append(BurstDetection(
                start_time=burst_start,
                end_time=buckets[-1].end_time,
                intensity=burst_events / max(mean_count, 1),
                event_count=burst_events,
                baseline_average=mean_count,
                peak_time=burst_peak_time
            ))

        return bursts

    def detect_trend(
        self,
        buckets: List[ActivityBucket]
    ) -> Optional[TrendAnalysis]:
        """
        Detect overall trend using simple linear regression.
        """
        if not buckets or len(buckets) < 3:
            return None

        counts = [b.event_count for b in buckets]
        n = len(counts)

        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(counts) / n

        numerator = sum((i - x_mean) * (counts[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Calculate R-squared for confidence
        ss_tot = sum((y - y_mean) ** 2 for y in counts)
        if ss_tot == 0:
            r_squared = 0
        else:
            y_pred = [y_mean + slope * (i - x_mean) for i in range(n)]
            ss_res = sum((counts[i] - y_pred[i]) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot)

        # Determine direction
        if abs(slope) < 0.01:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        return TrendAnalysis(
            direction=direction,
            slope=slope,
            start_value=counts[0] if counts else 0,
            end_value=counts[-1] if counts else 0,
            confidence=max(0, min(1, r_squared)),
            start_time=buckets[0].start_time if buckets else None,
            end_time=buckets[-1].end_time if buckets else None
        )

    def detect_cyclical_patterns(
        self,
        buckets: List[ActivityBucket],
        window: TimeWindow
    ) -> List[CyclicalPattern]:
        """
        Detect cyclical patterns (e.g., weekly, monthly cycles).

        Uses simple day-of-week analysis for now.
        """
        if not buckets or window != TimeWindow.DAY:
            return []

        # Aggregate by day of week
        day_counts = defaultdict(list)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for bucket in buckets:
            day_idx = bucket.start_time.weekday()
            day_counts[day_idx].append(bucket.event_count)

        if len(day_counts) < 7:
            return []  # Not enough data for weekly pattern

        # Calculate average for each day
        day_averages = {}
        for day_idx, counts in day_counts.items():
            day_averages[day_idx] = sum(counts) / len(counts) if counts else 0

        # Check for significant variation
        avg_values = list(day_averages.values())
        overall_avg = sum(avg_values) / len(avg_values) if avg_values else 0
        variance = sum((v - overall_avg) ** 2 for v in avg_values) / len(avg_values) if avg_values else 0
        std_dev = variance ** 0.5

        # If variation is significant, report weekly pattern
        if std_dev > overall_avg * 0.1:  # At least 10% variation
            peak_day_idx = max(day_averages, key=day_averages.get)
            trough_day_idx = min(day_averages, key=day_averages.get)

            max_val = day_averages[peak_day_idx]
            min_val = day_averages[trough_day_idx]

            return [CyclicalPattern(
                period_days=7.0,
                period_description="weekly",
                amplitude=(max_val - min_val) / 2 if max_val > min_val else 0,
                confidence=min(1.0, std_dev / overall_avg) if overall_avg > 0 else 0,
                peak_day=day_names[peak_day_idx],
                trough_day=day_names[trough_day_idx]
            )]

        return []

    def detect_anomalies(
        self,
        buckets: List[ActivityBucket],
        threshold: Optional[float] = None
    ) -> List[TemporalAnomaly]:
        """
        Detect anomalous activity periods.

        Uses statistical threshold: |value - mean| > threshold * std_dev
        """
        if not buckets or len(buckets) < 5:
            return []

        threshold = threshold or self.anomaly_threshold
        counts = [b.event_count for b in buckets]

        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return []

        anomalies = []
        for bucket in buckets:
            deviation = abs(bucket.event_count - mean_count) / std_dev

            if deviation > threshold:
                anomaly_score = min(1.0, deviation / (2 * threshold))
                direction = "above" if bucket.event_count > mean_count else "below"

                anomalies.append(TemporalAnomaly(
                    timestamp=bucket.start_time,
                    anomaly_score=anomaly_score,
                    expected_value=mean_count,
                    actual_value=bucket.event_count,
                    deviation=deviation,
                    description=f"Activity {deviation:.1f} standard deviations {direction} normal"
                ))

        return anomalies

    def get_entity_temporal_profile(
        self,
        project_id: str,
        entity_id: str,
        events: List[Dict[str, Any]]
    ) -> EntityTemporalProfile:
        """
        Build a temporal profile for an entity.
        """
        entity_events = [e for e in events if e.get("entity_id") == entity_id]

        if not entity_events:
            return EntityTemporalProfile(
                entity_id=entity_id,
                total_events=0
            )

        # Parse timestamps
        timestamps = []
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for event in entity_events:
            ts = event.get("timestamp")
            if ts is None:
                continue

            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue

            timestamps.append(ts)
            hour_counts[ts.hour] += 1
            day_counts[ts.weekday()] += 1

        if not timestamps:
            return EntityTemporalProfile(
                entity_id=entity_id,
                total_events=len(entity_events)
            )

        first_activity = min(timestamps)
        last_activity = max(timestamps)
        days_span = max(1, (last_activity - first_activity).days)

        # Find most active hour and day
        most_active_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
        most_active_day_idx = max(day_counts, key=day_counts.get) if day_counts else None
        most_active_day = day_names[most_active_day_idx] if most_active_day_idx is not None else None

        # Simple trend detection
        if len(timestamps) >= 10:
            mid_point = len(timestamps) // 2
            first_half = timestamps[:mid_point]
            second_half = timestamps[mid_point:]

            first_rate = len(first_half) / max(1, (first_half[-1] - first_half[0]).days)
            second_rate = len(second_half) / max(1, (second_half[-1] - second_half[0]).days)

            if second_rate > first_rate * 1.2:
                trend = TrendDirection.INCREASING
            elif second_rate < first_rate * 0.8:
                trend = TrendDirection.DECREASING
            else:
                trend = TrendDirection.STABLE
        else:
            trend = None

        return EntityTemporalProfile(
            entity_id=entity_id,
            first_activity=first_activity,
            last_activity=last_activity,
            total_events=len(entity_events),
            avg_events_per_day=len(entity_events) / days_span,
            most_active_hour=most_active_hour,
            most_active_day=most_active_day,
            activity_trend=trend
        )

    async def analyze_project_patterns(
        self,
        project_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        window: TimeWindow = TimeWindow.DAY
    ) -> TemporalPatternReport:
        """
        Analyze temporal patterns for a project.

        Args:
            project_id: Project to analyze
            start_time: Start of analysis window (default: 30 days ago)
            end_time: End of analysis window (default: now)
            window: Time bucket size for analysis

        Returns:
            TemporalPatternReport with detected patterns
        """
        # Set default time range
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=30)

        days = (end_time - start_time).days

        # Get events from timeline service
        events = []
        if self.timeline_service:
            try:
                raw_events = await self.timeline_service.get_project_timeline_async(
                    project_id=project_id,
                    start_date=start_time,
                    end_date=end_time,
                    limit=50000
                )
                events = [
                    {
                        "timestamp": e.timestamp,
                        "entity_id": e.entity_id,
                        "event_type": e.event_type
                    }
                    for e in raw_events
                ]
            except Exception as e:
                logger.error(f"Failed to get timeline events: {e}")

        # Create activity buckets
        buckets = self._get_activity_buckets(events, window, start_time, end_time)

        # Detect patterns
        bursts = self.detect_bursts(buckets)
        trend = self.detect_trend(buckets)
        cyclical = self.detect_cyclical_patterns(buckets, window)
        anomalies = self.detect_anomalies(buckets)

        # Calculate summary statistics
        total_events = sum(b.event_count for b in buckets)
        avg_daily = total_events / max(1, days)

        # Find peak and quietest days
        day_counts = defaultdict(int)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for bucket in buckets:
            if window == TimeWindow.DAY:
                day_idx = bucket.start_time.weekday()
                day_counts[day_idx] += bucket.event_count

        peak_day = None
        quietest_day = None
        if day_counts:
            peak_day_idx = max(day_counts, key=day_counts.get)
            quietest_day_idx = min(day_counts, key=day_counts.get)
            peak_day = day_names[peak_day_idx]
            quietest_day = day_names[quietest_day_idx]

        return TemporalPatternReport(
            project_id=project_id,
            analysis_start=start_time,
            analysis_end=end_time,
            analysis_window_days=days,
            total_events_analyzed=total_events,
            bursts=bursts,
            trend=trend,
            cyclical_patterns=cyclical,
            anomalies=anomalies,
            avg_daily_events=avg_daily,
            peak_day=peak_day,
            quietest_day=quietest_day
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_temporal_patterns_service: Optional[TemporalPatternsService] = None


def get_temporal_patterns_service() -> TemporalPatternsService:
    """Get the singleton TemporalPatternsService instance."""
    global _temporal_patterns_service
    if _temporal_patterns_service is None:
        _temporal_patterns_service = TemporalPatternsService()
    return _temporal_patterns_service


def set_temporal_patterns_service(
    neo4j_handler=None,
    timeline_service=None
) -> TemporalPatternsService:
    """Set up the TemporalPatternsService with dependencies."""
    global _temporal_patterns_service
    _temporal_patterns_service = TemporalPatternsService(
        neo4j_handler=neo4j_handler,
        timeline_service=timeline_service
    )
    return _temporal_patterns_service
