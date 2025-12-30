"""
Data Quality Service for Basset Hound OSINT Platform.

This module provides data quality scoring and assessment capabilities
for entities. It helps investigators understand the reliability and
completeness of their data.

Features:
- Completeness scoring (fields filled vs available)
- Freshness scoring (recency of updates)
- Confidence scoring (based on source reliability)
- Data quality reports per entity and project
- Quality-based recommendations

Usage:
    from api.services.data_quality import (
        DataQualityService,
        QualityScore,
        QualityDimension,
        get_data_quality_service,
    )

    service = get_data_quality_service()

    # Score an entity
    score = await service.score_entity(project_id, entity_id)
    print(f"Quality: {score.overall_score}/100")

    # Get project-wide quality report
    report = await service.get_project_quality_report(project_id)
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import re


class QualityDimension(str, Enum):
    """Dimensions of data quality assessment."""
    COMPLETENESS = "completeness"  # How many fields are filled
    FRESHNESS = "freshness"        # How recently updated
    ACCURACY = "accuracy"          # Corroboration across sources
    CONSISTENCY = "consistency"    # Format and value consistency
    UNIQUENESS = "uniqueness"      # Lack of duplicates
    VALIDITY = "validity"          # Values match expected formats


class DataSource(str, Enum):
    """Sources of data with default reliability scores."""
    MANUAL_ENTRY = "manual_entry"          # User entered
    MALTEGO = "maltego"                    # Maltego import
    SPIDERFOOT = "spiderfoot"              # SpiderFoot scan
    THEHARVESTER = "theharvester"          # TheHarvester discovery
    SHODAN = "shodan"                      # Shodan host data
    HIBP = "hibp"                          # Have I Been Pwned
    CSV_IMPORT = "csv_import"              # Generic CSV
    JSON_IMPORT = "json_import"            # Generic JSON
    API_ENRICHMENT = "api_enrichment"      # External API
    OSINT_TOOL = "osint_tool"              # Generic OSINT tool
    UNKNOWN = "unknown"                    # Unknown source


# Default source reliability scores (0.0 - 1.0)
SOURCE_RELIABILITY = {
    DataSource.MANUAL_ENTRY: 0.9,      # Human verified
    DataSource.MALTEGO: 0.8,           # Professional tool
    DataSource.SPIDERFOOT: 0.75,       # Automated OSINT
    DataSource.THEHARVESTER: 0.7,      # Email/domain discovery
    DataSource.SHODAN: 0.85,           # Network data
    DataSource.HIBP: 0.95,             # Breach data authority
    DataSource.CSV_IMPORT: 0.5,        # Unknown quality
    DataSource.JSON_IMPORT: 0.5,       # Unknown quality
    DataSource.API_ENRICHMENT: 0.7,    # Depends on API
    DataSource.OSINT_TOOL: 0.6,        # Generic tool
    DataSource.UNKNOWN: 0.3,           # Lowest confidence
}


@dataclass
class FieldQuality:
    """Quality assessment for a single field."""
    field_id: str
    field_name: str
    section_id: str
    has_value: bool
    value_type: str
    is_valid: bool = True
    validation_message: Optional[str] = None
    source: DataSource = DataSource.UNKNOWN
    source_reliability: float = 0.3
    last_updated: Optional[datetime] = None
    corroboration_count: int = 0  # How many sources confirm this value


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    dimension: QualityDimension
    score: float  # 0.0 - 100.0
    weight: float = 1.0
    details: str = ""
    field_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Complete quality assessment for an entity."""
    entity_id: str
    project_id: str
    overall_score: float  # 0.0 - 100.0
    grade: str  # A, B, C, D, F
    dimensions: Dict[QualityDimension, DimensionScore] = field(default_factory=dict)
    field_quality: List[FieldQuality] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "overall_score": round(self.overall_score, 2),
            "grade": self.grade,
            "dimensions": {
                dim.value: {
                    "score": round(score.score, 2),
                    "weight": score.weight,
                    "details": score.details,
                }
                for dim, score in self.dimensions.items()
            },
            "field_count": len(self.field_quality),
            "filled_fields": sum(1 for f in self.field_quality if f.has_value),
            "recommendations": self.recommendations,
            "issues": self.issues,
            "scored_at": self.scored_at.isoformat(),
        }


@dataclass
class ProjectQualityReport:
    """Quality report for an entire project."""
    project_id: str
    entity_count: int
    average_score: float
    grade_distribution: Dict[str, int]  # A, B, C, D, F counts
    dimension_averages: Dict[QualityDimension, float]
    top_issues: List[str]
    top_recommendations: List[str]
    low_quality_entities: List[str]  # Entity IDs with low scores
    high_quality_entities: List[str]  # Entity IDs with high scores
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "entity_count": self.entity_count,
            "average_score": round(self.average_score, 2),
            "grade_distribution": self.grade_distribution,
            "dimension_averages": {
                dim.value: round(score, 2)
                for dim, score in self.dimension_averages.items()
            },
            "top_issues": self.top_issues[:10],
            "top_recommendations": self.top_recommendations[:10],
            "low_quality_entities": self.low_quality_entities[:20],
            "high_quality_entities": self.high_quality_entities[:10],
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class QualityConfig:
    """Configuration for quality scoring."""
    # Dimension weights (must sum to 1.0)
    completeness_weight: float = 0.30
    freshness_weight: float = 0.20
    accuracy_weight: float = 0.20
    consistency_weight: float = 0.15
    uniqueness_weight: float = 0.10
    validity_weight: float = 0.05

    # Thresholds
    freshness_days_excellent: int = 7     # A grade for freshness
    freshness_days_good: int = 30         # B grade
    freshness_days_acceptable: int = 90   # C grade
    freshness_days_stale: int = 180       # D grade
    # Beyond stale is F

    # Minimum fields for completeness scoring
    min_required_fields: int = 3

    # Grade thresholds
    grade_a_threshold: float = 90.0
    grade_b_threshold: float = 80.0
    grade_c_threshold: float = 70.0
    grade_d_threshold: float = 60.0
    # Below D is F

    def get_weights_dict(self) -> Dict[QualityDimension, float]:
        """Get dimension weights as dictionary."""
        return {
            QualityDimension.COMPLETENESS: self.completeness_weight,
            QualityDimension.FRESHNESS: self.freshness_weight,
            QualityDimension.ACCURACY: self.accuracy_weight,
            QualityDimension.CONSISTENCY: self.consistency_weight,
            QualityDimension.UNIQUENESS: self.uniqueness_weight,
            QualityDimension.VALIDITY: self.validity_weight,
        }


# Validation patterns for common field types
VALIDATION_PATTERNS = {
    "email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    "phone": r"^[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]*$",
    "url": r"^https?://[^\s<>\"{}|\\^`\[\]]+$",
    "ip_address": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    "domain": r"^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}$",
    "username": r"^[a-zA-Z0-9_.-]{2,50}$",
    "date": r"^\d{4}-\d{2}-\d{2}$",
}


class DataQualityService:
    """
    Service for assessing and reporting on data quality.

    Provides scoring across multiple dimensions:
    - Completeness: How many fields are filled
    - Freshness: How recently the data was updated
    - Accuracy: Corroboration across multiple sources
    - Consistency: Format and value consistency
    - Uniqueness: Lack of duplicate data
    - Validity: Values match expected formats
    """

    def __init__(self, config: Optional[QualityConfig] = None):
        """
        Initialize the data quality service.

        Args:
            config: Quality scoring configuration
        """
        self._lock = threading.RLock()
        self._config = config or QualityConfig()
        self._cache: Dict[str, QualityScore] = {}  # entity_id -> score
        self._cache_ttl = 300  # 5 minutes
        self._source_reliability = dict(SOURCE_RELIABILITY)

        # Schema cache (would be populated from data_config.yaml)
        self._schema_cache: Dict[str, List[Dict[str, Any]]] = {}

    def set_source_reliability(
        self,
        source: DataSource,
        reliability: float
    ) -> None:
        """
        Set custom reliability score for a data source.

        Args:
            source: Data source
            reliability: Reliability score (0.0 - 1.0)
        """
        if not 0.0 <= reliability <= 1.0:
            raise ValueError("Reliability must be between 0.0 and 1.0")
        with self._lock:
            self._source_reliability[source] = reliability

    def get_source_reliability(self, source: DataSource) -> float:
        """Get reliability score for a data source."""
        with self._lock:
            return self._source_reliability.get(source, 0.3)

    async def score_entity(
        self,
        project_id: str,
        entity_id: str,
        entity_data: Optional[Dict[str, Any]] = None,
        schema: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityScore:
        """
        Calculate quality score for an entity.

        Args:
            project_id: Project ID
            entity_id: Entity ID
            entity_data: Entity profile data (if not provided, returns default score)
            schema: Field schema for the entity type
            metadata: Optional metadata (source, timestamps, etc.)

        Returns:
            Complete quality score
        """
        # Initialize field quality list
        field_quality: List[FieldQuality] = []
        dimension_scores: Dict[QualityDimension, DimensionScore] = {}
        recommendations: List[str] = []
        issues: List[str] = []

        # Handle empty data
        if not entity_data:
            entity_data = {}

        # Get or use default schema
        if not schema:
            schema = self._get_default_schema()

        # Extract metadata
        source = DataSource.UNKNOWN
        last_updated = None
        if metadata:
            source_str = metadata.get("source", "unknown")
            try:
                source = DataSource(source_str)
            except ValueError:
                source = DataSource.UNKNOWN

            updated_str = metadata.get("updated_at") or metadata.get("last_updated")
            if updated_str:
                if isinstance(updated_str, datetime):
                    last_updated = updated_str
                elif isinstance(updated_str, str):
                    try:
                        last_updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

        # Analyze each field from schema
        for section in schema:
            section_id = section.get("id", "unknown")
            fields = section.get("fields", [])

            for field_def in fields:
                field_id = field_def.get("id", "unknown")
                field_name = field_def.get("label", field_id)
                field_type = field_def.get("type", "string")

                # Check if field has value
                value = self._get_nested_value(entity_data, field_id)
                has_value = value is not None and value != "" and value != []

                # Validate value format
                is_valid = True
                validation_msg = None
                if has_value:
                    is_valid, validation_msg = self._validate_field(
                        value, field_type, field_def
                    )

                field_quality.append(FieldQuality(
                    field_id=field_id,
                    field_name=field_name,
                    section_id=section_id,
                    has_value=has_value,
                    value_type=field_type,
                    is_valid=is_valid,
                    validation_message=validation_msg,
                    source=source,
                    source_reliability=self.get_source_reliability(source),
                    last_updated=last_updated,
                    corroboration_count=1 if has_value else 0,
                ))

        # Calculate dimension scores
        dimension_scores[QualityDimension.COMPLETENESS] = self._score_completeness(
            field_quality, schema
        )
        dimension_scores[QualityDimension.FRESHNESS] = self._score_freshness(
            last_updated
        )
        dimension_scores[QualityDimension.ACCURACY] = self._score_accuracy(
            field_quality, source
        )
        dimension_scores[QualityDimension.CONSISTENCY] = self._score_consistency(
            field_quality, entity_data
        )
        dimension_scores[QualityDimension.UNIQUENESS] = self._score_uniqueness(
            entity_id
        )
        dimension_scores[QualityDimension.VALIDITY] = self._score_validity(
            field_quality
        )

        # Calculate overall score
        weights = self._config.get_weights_dict()
        overall_score = sum(
            dimension_scores[dim].score * weights[dim]
            for dim in QualityDimension
        )

        # Determine grade
        grade = self._calculate_grade(overall_score)

        # Generate recommendations and issues
        recommendations, issues = self._generate_recommendations(
            dimension_scores, field_quality, overall_score
        )

        score = QualityScore(
            entity_id=entity_id,
            project_id=project_id,
            overall_score=overall_score,
            grade=grade,
            dimensions=dimension_scores,
            field_quality=field_quality,
            recommendations=recommendations,
            issues=issues,
        )

        # Cache the score
        with self._lock:
            self._cache[entity_id] = score

        return score

    async def score_entities_batch(
        self,
        project_id: str,
        entities: List[Dict[str, Any]],
        schema: Optional[List[Dict[str, Any]]] = None,
    ) -> List[QualityScore]:
        """
        Score multiple entities in batch.

        Args:
            project_id: Project ID
            entities: List of entity data dicts (must include 'id' key)
            schema: Optional schema for all entities

        Returns:
            List of quality scores
        """
        scores = []
        for entity in entities:
            entity_id = entity.get("id", str(len(scores)))
            entity_data = entity.get("profile", entity)
            metadata = entity.get("metadata", {})

            score = await self.score_entity(
                project_id=project_id,
                entity_id=entity_id,
                entity_data=entity_data,
                schema=schema,
                metadata=metadata,
            )
            scores.append(score)

        return scores

    async def get_project_quality_report(
        self,
        project_id: str,
        entity_scores: Optional[List[QualityScore]] = None,
    ) -> ProjectQualityReport:
        """
        Generate quality report for an entire project.

        Args:
            project_id: Project ID
            entity_scores: Pre-computed entity scores (if available)

        Returns:
            Project quality report
        """
        if not entity_scores:
            entity_scores = []

        entity_count = len(entity_scores)
        if entity_count == 0:
            return ProjectQualityReport(
                project_id=project_id,
                entity_count=0,
                average_score=0.0,
                grade_distribution={"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                dimension_averages={dim: 0.0 for dim in QualityDimension},
                top_issues=[],
                top_recommendations=["Add entities to the project"],
                low_quality_entities=[],
                high_quality_entities=[],
            )

        # Calculate averages
        total_score = sum(s.overall_score for s in entity_scores)
        average_score = total_score / entity_count

        # Grade distribution
        grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for score in entity_scores:
            grade_dist[score.grade] = grade_dist.get(score.grade, 0) + 1

        # Dimension averages
        dim_totals: Dict[QualityDimension, float] = {dim: 0.0 for dim in QualityDimension}
        for score in entity_scores:
            for dim, dim_score in score.dimensions.items():
                dim_totals[dim] += dim_score.score
        dim_averages = {dim: total / entity_count for dim, total in dim_totals.items()}

        # Collect issues and recommendations
        all_issues: Dict[str, int] = {}
        all_recommendations: Dict[str, int] = {}
        for score in entity_scores:
            for issue in score.issues:
                all_issues[issue] = all_issues.get(issue, 0) + 1
            for rec in score.recommendations:
                all_recommendations[rec] = all_recommendations.get(rec, 0) + 1

        # Sort by frequency
        top_issues = sorted(all_issues.keys(), key=lambda x: all_issues[x], reverse=True)[:10]
        top_recs = sorted(all_recommendations.keys(), key=lambda x: all_recommendations[x], reverse=True)[:10]

        # Find low and high quality entities
        sorted_by_score = sorted(entity_scores, key=lambda x: x.overall_score)
        low_quality = [s.entity_id for s in sorted_by_score[:20] if s.overall_score < 60]
        high_quality = [s.entity_id for s in sorted_by_score[-10:] if s.overall_score >= 80]

        return ProjectQualityReport(
            project_id=project_id,
            entity_count=entity_count,
            average_score=average_score,
            grade_distribution=grade_dist,
            dimension_averages=dim_averages,
            top_issues=top_issues,
            top_recommendations=top_recs,
            low_quality_entities=low_quality,
            high_quality_entities=high_quality,
        )

    async def compare_quality(
        self,
        score1: QualityScore,
        score2: QualityScore,
    ) -> Dict[str, Any]:
        """
        Compare quality between two entities.

        Args:
            score1: First entity's quality score
            score2: Second entity's quality score

        Returns:
            Comparison results
        """
        comparison = {
            "entity1": {
                "id": score1.entity_id,
                "overall_score": score1.overall_score,
                "grade": score1.grade,
            },
            "entity2": {
                "id": score2.entity_id,
                "overall_score": score2.overall_score,
                "grade": score2.grade,
            },
            "difference": score1.overall_score - score2.overall_score,
            "better_entity": score1.entity_id if score1.overall_score > score2.overall_score else score2.entity_id,
            "dimension_comparison": {},
        }

        for dim in QualityDimension:
            s1 = score1.dimensions.get(dim, DimensionScore(dim, 0.0))
            s2 = score2.dimensions.get(dim, DimensionScore(dim, 0.0))
            comparison["dimension_comparison"][dim.value] = {
                "entity1_score": s1.score,
                "entity2_score": s2.score,
                "difference": s1.score - s2.score,
                "winner": score1.entity_id if s1.score > s2.score else score2.entity_id,
            }

        return comparison

    async def get_quality_trends(
        self,
        project_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get quality trends over time (placeholder for future implementation).

        Args:
            project_id: Project ID
            days: Number of days to analyze

        Returns:
            Trend data
        """
        # Placeholder - would track scores over time
        return {
            "project_id": project_id,
            "period_days": days,
            "trend": "stable",
            "message": "Quality trend tracking not yet implemented",
        }

    def _get_default_schema(self) -> List[Dict[str, Any]]:
        """Get default schema for scoring."""
        return [
            {
                "id": "basic",
                "fields": [
                    {"id": "name", "label": "Name", "type": "string"},
                    {"id": "email", "label": "Email", "type": "email"},
                    {"id": "phone", "label": "Phone", "type": "phone"},
                    {"id": "username", "label": "Username", "type": "string"},
                ]
            }
        ]

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value

    def _validate_field(
        self,
        value: Any,
        field_type: str,
        field_def: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a field value against its type.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None or value == "":
            return True, None

        # Convert to string for pattern matching
        str_value = str(value) if not isinstance(value, str) else value

        # Check against known patterns
        pattern = VALIDATION_PATTERNS.get(field_type)
        if pattern:
            if not re.match(pattern, str_value):
                return False, f"Invalid {field_type} format"

        # Check custom pattern from field definition
        custom_pattern = field_def.get("pattern")
        if custom_pattern:
            try:
                if not re.match(custom_pattern, str_value):
                    return False, f"Value does not match required pattern"
            except re.error:
                pass  # Invalid regex, skip validation

        return True, None

    def _score_completeness(
        self,
        field_quality: List[FieldQuality],
        schema: List[Dict[str, Any]],
    ) -> DimensionScore:
        """Score completeness dimension."""
        if not field_quality:
            return DimensionScore(
                dimension=QualityDimension.COMPLETENESS,
                score=0.0,
                details="No fields to assess",
            )

        total_fields = len(field_quality)
        filled_fields = sum(1 for f in field_quality if f.has_value)

        if total_fields == 0:
            score = 0.0
        else:
            score = (filled_fields / total_fields) * 100

        return DimensionScore(
            dimension=QualityDimension.COMPLETENESS,
            score=score,
            details=f"{filled_fields}/{total_fields} fields filled",
            field_scores={f.field_id: 100.0 if f.has_value else 0.0 for f in field_quality},
        )

    def _score_freshness(self, last_updated: Optional[datetime]) -> DimensionScore:
        """Score freshness dimension."""
        if not last_updated:
            return DimensionScore(
                dimension=QualityDimension.FRESHNESS,
                score=50.0,  # Unknown freshness gets middle score
                details="Update timestamp not available",
            )

        now = datetime.now(timezone.utc)
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        age_days = (now - last_updated).days

        if age_days <= self._config.freshness_days_excellent:
            score = 100.0
            details = f"Updated {age_days} days ago (excellent)"
        elif age_days <= self._config.freshness_days_good:
            score = 80.0
            details = f"Updated {age_days} days ago (good)"
        elif age_days <= self._config.freshness_days_acceptable:
            score = 60.0
            details = f"Updated {age_days} days ago (acceptable)"
        elif age_days <= self._config.freshness_days_stale:
            score = 40.0
            details = f"Updated {age_days} days ago (stale)"
        else:
            score = 20.0
            details = f"Updated {age_days} days ago (very stale)"

        return DimensionScore(
            dimension=QualityDimension.FRESHNESS,
            score=score,
            details=details,
        )

    def _score_accuracy(
        self,
        field_quality: List[FieldQuality],
        source: DataSource,
    ) -> DimensionScore:
        """Score accuracy dimension based on source reliability."""
        reliability = self.get_source_reliability(source)
        score = reliability * 100

        return DimensionScore(
            dimension=QualityDimension.ACCURACY,
            score=score,
            details=f"Source: {source.value} (reliability: {reliability:.0%})",
        )

    def _score_consistency(
        self,
        field_quality: List[FieldQuality],
        entity_data: Dict[str, Any],
    ) -> DimensionScore:
        """Score consistency dimension."""
        # Check for consistency issues
        issues = []

        # Check for mixed case in names
        name = entity_data.get("name", "")
        if name and not (name.istitle() or name.isupper() or name.islower()):
            # Inconsistent casing is OK, this is just a simple check
            pass

        # Check for duplicate field values
        values = []
        for f in field_quality:
            if f.has_value:
                val = self._get_nested_value(entity_data, f.field_id)
                if val and str(val) in values:
                    issues.append(f"Duplicate value in {f.field_name}")
                elif val:
                    values.append(str(val))

        # Score based on issues found
        if len(issues) == 0:
            score = 100.0
        else:
            score = max(0.0, 100.0 - (len(issues) * 20))

        return DimensionScore(
            dimension=QualityDimension.CONSISTENCY,
            score=score,
            details=f"{len(issues)} consistency issues found" if issues else "No consistency issues",
        )

    def _score_uniqueness(self, entity_id: str) -> DimensionScore:
        """
        Score uniqueness dimension.

        Note: This would integrate with deduplication service in practice.
        """
        # Placeholder - assumes entity is unique
        return DimensionScore(
            dimension=QualityDimension.UNIQUENESS,
            score=100.0,
            details="Uniqueness check not performed",
        )

    def _score_validity(self, field_quality: List[FieldQuality]) -> DimensionScore:
        """Score validity dimension based on field validation."""
        if not field_quality:
            return DimensionScore(
                dimension=QualityDimension.VALIDITY,
                score=100.0,
                details="No fields to validate",
            )

        fields_with_values = [f for f in field_quality if f.has_value]
        if not fields_with_values:
            return DimensionScore(
                dimension=QualityDimension.VALIDITY,
                score=100.0,
                details="No values to validate",
            )

        valid_count = sum(1 for f in fields_with_values if f.is_valid)
        score = (valid_count / len(fields_with_values)) * 100

        invalid_fields = [f.field_name for f in fields_with_values if not f.is_valid]

        return DimensionScore(
            dimension=QualityDimension.VALIDITY,
            score=score,
            details=f"{valid_count}/{len(fields_with_values)} values valid" +
                    (f" (invalid: {', '.join(invalid_fields)})" if invalid_fields else ""),
            field_scores={f.field_id: 100.0 if f.is_valid else 0.0 for f in fields_with_values},
        )

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= self._config.grade_a_threshold:
            return "A"
        elif score >= self._config.grade_b_threshold:
            return "B"
        elif score >= self._config.grade_c_threshold:
            return "C"
        elif score >= self._config.grade_d_threshold:
            return "D"
        else:
            return "F"

    def _generate_recommendations(
        self,
        dimension_scores: Dict[QualityDimension, DimensionScore],
        field_quality: List[FieldQuality],
        overall_score: float,
    ) -> Tuple[List[str], List[str]]:
        """Generate recommendations and issues based on scores."""
        recommendations = []
        issues = []

        # Completeness recommendations
        completeness = dimension_scores.get(QualityDimension.COMPLETENESS)
        if completeness and completeness.score < 50:
            empty_fields = [f.field_name for f in field_quality if not f.has_value][:5]
            recommendations.append(f"Fill in missing fields: {', '.join(empty_fields)}")
            issues.append("Many fields are empty")

        # Freshness recommendations
        freshness = dimension_scores.get(QualityDimension.FRESHNESS)
        if freshness and freshness.score < 50:
            recommendations.append("Update entity data to improve freshness")
            issues.append("Data may be outdated")

        # Accuracy recommendations
        accuracy = dimension_scores.get(QualityDimension.ACCURACY)
        if accuracy and accuracy.score < 50:
            recommendations.append("Verify data from a more reliable source")
            issues.append("Data source has low reliability")

        # Validity recommendations
        validity = dimension_scores.get(QualityDimension.VALIDITY)
        if validity and validity.score < 80:
            invalid_fields = [f.field_name for f in field_quality if not f.is_valid][:3]
            if invalid_fields:
                recommendations.append(f"Fix invalid values in: {', '.join(invalid_fields)}")
                issues.append("Some field values have invalid formats")

        # Overall recommendations
        if overall_score < 50:
            recommendations.append("Consider reviewing and enriching this entity")
        elif overall_score < 70:
            recommendations.append("Entity quality could be improved with additional data")

        return recommendations, issues

    def clear_cache(self) -> int:
        """Clear the score cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_cached_score(self, entity_id: str) -> Optional[QualityScore]:
        """Get cached score for an entity."""
        with self._lock:
            return self._cache.get(entity_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        with self._lock:
            return {
                "cached_scores": len(self._cache),
                "cache_ttl_seconds": self._cache_ttl,
                "config": {
                    "completeness_weight": self._config.completeness_weight,
                    "freshness_weight": self._config.freshness_weight,
                    "accuracy_weight": self._config.accuracy_weight,
                    "consistency_weight": self._config.consistency_weight,
                    "uniqueness_weight": self._config.uniqueness_weight,
                    "validity_weight": self._config.validity_weight,
                },
            }


# Module-level singleton
_data_quality_service: Optional[DataQualityService] = None


def get_data_quality_service(
    config: Optional[QualityConfig] = None,
) -> DataQualityService:
    """
    Get or create the DataQualityService singleton.

    Args:
        config: Optional quality configuration

    Returns:
        DataQualityService instance
    """
    global _data_quality_service

    if _data_quality_service is None:
        _data_quality_service = DataQualityService(config)

    return _data_quality_service


def set_data_quality_service(service: Optional[DataQualityService]) -> None:
    """Set the global DataQualityService instance."""
    global _data_quality_service
    _data_quality_service = service


def reset_data_quality_service() -> None:
    """Reset the singleton instance."""
    global _data_quality_service
    _data_quality_service = None
