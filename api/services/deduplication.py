"""
Entity Deduplication Service for Basset Hound OSINT Platform.

This module provides intelligent duplicate detection and resolution
capabilities for entities. It helps investigators consolidate data
from multiple sources and maintain a clean entity database.

Features:
- Multiple matching strategies (exact, fuzzy, phonetic)
- Confidence scoring for potential matches
- Merge suggestions with field-level conflict resolution
- Batch deduplication operations
- Audit trail for merge operations

Usage:
    from api.services.deduplication import (
        DeduplicationService,
        DuplicateCandidate,
        MergeStrategy,
        get_deduplication_service,
    )

    service = get_deduplication_service()

    # Find duplicates for an entity
    candidates = await service.find_duplicates(project_id, entity_id)

    # Merge entities
    result = await service.merge_entities(
        project_id=project_id,
        primary_id=entity_id,
        duplicate_ids=["dup1", "dup2"],
        strategy=MergeStrategy.KEEP_PRIMARY,
    )
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import re
import uuid


class MatchType(str, Enum):
    """Types of matching strategies."""
    EXACT = "exact"              # Exact string match
    CASE_INSENSITIVE = "case_insensitive"  # Case-insensitive match
    FUZZY = "fuzzy"              # Fuzzy string matching
    PHONETIC = "phonetic"        # Sounds-alike matching
    NORMALIZED = "normalized"     # Normalized format matching
    PARTIAL = "partial"          # Partial string match
    TOKEN_SET = "token_set"      # Token set ratio matching


class MergeStrategy(str, Enum):
    """Strategies for merging duplicate entities."""
    KEEP_PRIMARY = "keep_primary"        # Keep primary entity values
    KEEP_DUPLICATE = "keep_duplicate"    # Keep duplicate entity values
    KEEP_NEWEST = "keep_newest"          # Keep most recently updated values
    KEEP_OLDEST = "keep_oldest"          # Keep oldest values
    KEEP_LONGEST = "keep_longest"        # Keep longest string values
    KEEP_ALL = "keep_all"                # Merge as array (for multi-value fields)
    MANUAL = "manual"                    # Require manual selection


class FieldConflictResolution(str, Enum):
    """Resolution for individual field conflicts."""
    USE_PRIMARY = "use_primary"
    USE_DUPLICATE = "use_duplicate"
    USE_COMBINED = "use_combined"    # Combine values
    USE_CUSTOM = "use_custom"        # Custom value provided
    SKIP = "skip"                    # Don't update field


@dataclass
class MatchResult:
    """Result of comparing two field values."""
    field_id: str
    field_name: str
    match_type: MatchType
    similarity: float  # 0.0 - 1.0
    primary_value: Any
    duplicate_value: Any
    is_match: bool
    details: str = ""


@dataclass
class DuplicateCandidate:
    """A potential duplicate entity."""
    entity_id: str
    entity_name: str
    confidence: float  # 0.0 - 1.0
    match_reasons: List[str]
    field_matches: List[MatchResult]
    suggested_action: str  # "merge", "review", "ignore"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "confidence": round(self.confidence, 3),
            "match_reasons": self.match_reasons,
            "field_matches": [
                {
                    "field_id": m.field_id,
                    "field_name": m.field_name,
                    "match_type": m.match_type.value,
                    "similarity": round(m.similarity, 3),
                    "primary_value": m.primary_value,
                    "duplicate_value": m.duplicate_value,
                    "is_match": m.is_match,
                }
                for m in self.field_matches
            ],
            "suggested_action": self.suggested_action,
            "metadata": self.metadata,
        }


@dataclass
class FieldConflict:
    """A conflict between field values during merge."""
    field_id: str
    field_name: str
    primary_value: Any
    duplicate_value: Any
    values_from_all: List[Any]  # Values from all entities being merged
    suggested_resolution: FieldConflictResolution
    resolved_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field_id": self.field_id,
            "field_name": self.field_name,
            "primary_value": self.primary_value,
            "duplicate_value": self.duplicate_value,
            "values_from_all": self.values_from_all,
            "suggested_resolution": self.suggested_resolution.value,
            "resolved_value": self.resolved_value,
        }


@dataclass
class MergePreview:
    """Preview of a merge operation before execution."""
    primary_id: str
    duplicate_ids: List[str]
    strategy: MergeStrategy
    conflicts: List[FieldConflict]
    merged_profile: Dict[str, Any]
    relationships_to_transfer: int
    files_to_transfer: int
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_id": self.primary_id,
            "duplicate_ids": self.duplicate_ids,
            "strategy": self.strategy.value,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "merged_profile": self.merged_profile,
            "relationships_to_transfer": self.relationships_to_transfer,
            "files_to_transfer": self.files_to_transfer,
            "warnings": self.warnings,
        }


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_entity_id: str
    deleted_entity_ids: List[str]
    relationships_transferred: int
    files_transferred: int
    conflicts_resolved: int
    warnings: List[str]
    merge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    merged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "merge_id": self.merge_id,
            "merged_entity_id": self.merged_entity_id,
            "deleted_entity_ids": self.deleted_entity_ids,
            "relationships_transferred": self.relationships_transferred,
            "files_transferred": self.files_transferred,
            "conflicts_resolved": self.conflicts_resolved,
            "warnings": self.warnings,
            "merged_at": self.merged_at.isoformat(),
        }


@dataclass
class DeduplicationConfig:
    """Configuration for deduplication behavior."""
    # Matching thresholds
    exact_match_weight: float = 1.0
    fuzzy_match_threshold: float = 0.85
    phonetic_match_weight: float = 0.9

    # Confidence thresholds
    auto_merge_threshold: float = 0.95  # Auto-merge above this
    review_threshold: float = 0.70      # Suggest review above this
    ignore_threshold: float = 0.50      # Ignore below this

    # Field weights for scoring
    field_weights: Dict[str, float] = field(default_factory=lambda: {
        "email": 3.0,
        "phone": 2.5,
        "username": 2.0,
        "name": 1.5,
        "social_media": 2.0,
        "crypto_address": 3.5,
        "ip_address": 2.0,
    })

    # Fields to use for matching
    identifier_fields: List[str] = field(default_factory=lambda: [
        "email", "phone", "username", "social_media",
        "crypto_address", "ip_address", "domain",
    ])


@dataclass
class DeduplicationReport:
    """Report of deduplication analysis for a project."""
    project_id: str
    total_entities: int
    duplicate_groups: int
    total_duplicates: int
    high_confidence_matches: int  # >= 0.95
    medium_confidence_matches: int  # 0.70 - 0.95
    low_confidence_matches: int  # 0.50 - 0.70
    top_duplicate_fields: Dict[str, int]  # field -> count of matches
    estimated_reduction: float  # Percentage of entities that could be merged
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "total_entities": self.total_entities,
            "duplicate_groups": self.duplicate_groups,
            "total_duplicates": self.total_duplicates,
            "high_confidence_matches": self.high_confidence_matches,
            "medium_confidence_matches": self.medium_confidence_matches,
            "low_confidence_matches": self.low_confidence_matches,
            "top_duplicate_fields": self.top_duplicate_fields,
            "estimated_reduction": round(self.estimated_reduction, 2),
            "generated_at": self.generated_at.isoformat(),
        }


class DeduplicationService:
    """
    Service for detecting and resolving duplicate entities.

    Provides intelligent duplicate detection using multiple matching
    strategies and supports various merge operations with full
    audit trail.
    """

    def __init__(self, config: Optional[DeduplicationConfig] = None):
        """
        Initialize the deduplication service.

        Args:
            config: Deduplication configuration
        """
        self._lock = threading.RLock()
        self._config = config or DeduplicationConfig()

        # Cache for duplicate candidates
        self._candidate_cache: OrderedDict[str, List[DuplicateCandidate]] = OrderedDict()
        self._max_cache_entries = 1000

        # Merge history for audit
        self._merge_history: OrderedDict[str, MergeResult] = OrderedDict()
        self._max_history_entries = 500

    async def find_duplicates(
        self,
        project_id: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        candidate_entities: List[Dict[str, Any]],
        match_types: Optional[List[MatchType]] = None,
    ) -> List[DuplicateCandidate]:
        """
        Find potential duplicates for an entity.

        Args:
            project_id: Project ID
            entity_id: Entity to find duplicates for
            entity_data: Entity profile data
            candidate_entities: List of entities to compare against
            match_types: Matching strategies to use

        Returns:
            List of duplicate candidates sorted by confidence
        """
        if match_types is None:
            match_types = [
                MatchType.EXACT,
                MatchType.CASE_INSENSITIVE,
                MatchType.FUZZY,
                MatchType.PHONETIC,
            ]

        candidates: List[DuplicateCandidate] = []

        for candidate in candidate_entities:
            candidate_id = candidate.get("id", "")
            if candidate_id == entity_id:
                continue

            # Compare entities
            result = await self._compare_entities(
                entity_data,
                candidate.get("profile", candidate),
                match_types,
            )

            if result["confidence"] >= self._config.ignore_threshold:
                # Determine suggested action
                if result["confidence"] >= self._config.auto_merge_threshold:
                    suggested_action = "merge"
                elif result["confidence"] >= self._config.review_threshold:
                    suggested_action = "review"
                else:
                    suggested_action = "ignore"

                candidates.append(DuplicateCandidate(
                    entity_id=candidate_id,
                    entity_name=candidate.get("name", candidate.get("profile", {}).get("name", "Unknown")),
                    confidence=result["confidence"],
                    match_reasons=result["reasons"],
                    field_matches=result["matches"],
                    suggested_action=suggested_action,
                    metadata={
                        "project_id": project_id,
                        "compared_at": datetime.now(timezone.utc).isoformat(),
                    },
                ))

        # Sort by confidence descending
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        # Cache results
        cache_key = f"{project_id}:{entity_id}"
        with self._lock:
            while len(self._candidate_cache) >= self._max_cache_entries:
                self._candidate_cache.popitem(last=False)
            self._candidate_cache[cache_key] = candidates

        return candidates

    async def find_all_duplicates(
        self,
        project_id: str,
        entities: List[Dict[str, Any]],
        match_types: Optional[List[MatchType]] = None,
    ) -> Dict[str, List[DuplicateCandidate]]:
        """
        Find all duplicates in a set of entities.

        Args:
            project_id: Project ID
            entities: All entities to check
            match_types: Matching strategies to use

        Returns:
            Dictionary mapping entity_id to its duplicate candidates
        """
        all_duplicates: Dict[str, List[DuplicateCandidate]] = {}

        for i, entity in enumerate(entities):
            entity_id = entity.get("id", str(i))
            # Compare against remaining entities to avoid duplicate comparisons
            remaining = entities[i+1:]

            candidates = await self.find_duplicates(
                project_id=project_id,
                entity_id=entity_id,
                entity_data=entity.get("profile", entity),
                candidate_entities=remaining,
                match_types=match_types,
            )

            if candidates:
                all_duplicates[entity_id] = candidates

        return all_duplicates

    async def preview_merge(
        self,
        project_id: str,
        primary_entity: Dict[str, Any],
        duplicate_entities: List[Dict[str, Any]],
        strategy: MergeStrategy = MergeStrategy.KEEP_PRIMARY,
        custom_resolutions: Optional[Dict[str, FieldConflictResolution]] = None,
    ) -> MergePreview:
        """
        Preview a merge operation without executing it.

        Args:
            project_id: Project ID
            primary_entity: Primary entity to merge into
            duplicate_entities: Entities to merge from
            strategy: Merge strategy
            custom_resolutions: Custom field resolutions

        Returns:
            Preview of the merge operation
        """
        custom_resolutions = custom_resolutions or {}
        conflicts: List[FieldConflict] = []
        warnings: List[str] = []
        merged_profile: Dict[str, Any] = {}

        primary_profile = primary_entity.get("profile", primary_entity)
        primary_id = primary_entity.get("id", "primary")

        # Collect all field values
        all_values: Dict[str, List[Tuple[str, Any]]] = {}  # field -> [(entity_id, value)]

        # Add primary values
        for key, value in primary_profile.items():
            if key not in all_values:
                all_values[key] = []
            all_values[key].append((primary_id, value))

        # Add duplicate values
        for dup in duplicate_entities:
            dup_id = dup.get("id", "duplicate")
            dup_profile = dup.get("profile", dup)
            for key, value in dup_profile.items():
                if key not in all_values:
                    all_values[key] = []
                all_values[key].append((dup_id, value))

        # Resolve each field
        for field_id, values in all_values.items():
            # Get unique non-empty values
            unique_values = []
            seen = set()
            for entity_id, val in values:
                val_str = str(val) if val is not None else ""
                if val_str and val_str not in seen:
                    unique_values.append((entity_id, val))
                    seen.add(val_str)

            if len(unique_values) <= 1:
                # No conflict - use the value
                merged_profile[field_id] = values[0][1] if values else None
            else:
                # Conflict - need resolution
                primary_val = None
                duplicate_val = None
                for entity_id, val in values:
                    if entity_id == primary_id and primary_val is None:
                        primary_val = val
                    elif entity_id != primary_id and duplicate_val is None:
                        duplicate_val = val

                # Determine resolution
                if field_id in custom_resolutions:
                    resolution = custom_resolutions[field_id]
                else:
                    resolution = self._suggest_resolution(
                        field_id, primary_val, duplicate_val, strategy
                    )

                # Apply resolution
                resolved_value = self._resolve_conflict(
                    primary_val, duplicate_val,
                    [v for _, v in unique_values],
                    resolution, strategy
                )

                conflicts.append(FieldConflict(
                    field_id=field_id,
                    field_name=field_id,  # Would get from schema
                    primary_value=primary_val,
                    duplicate_value=duplicate_val,
                    values_from_all=[v for _, v in unique_values],
                    suggested_resolution=resolution,
                    resolved_value=resolved_value,
                ))

                merged_profile[field_id] = resolved_value

        # Count relationships and files to transfer (placeholders)
        relationships_to_transfer = len(duplicate_entities) * 5  # Estimate
        files_to_transfer = len(duplicate_entities) * 2  # Estimate

        # Generate warnings
        if len(duplicate_entities) > 5:
            warnings.append(f"Merging {len(duplicate_entities)} entities may take time")
        if len(conflicts) > 10:
            warnings.append(f"{len(conflicts)} field conflicts need resolution")

        return MergePreview(
            primary_id=primary_id,
            duplicate_ids=[d.get("id", "unknown") for d in duplicate_entities],
            strategy=strategy,
            conflicts=conflicts,
            merged_profile=merged_profile,
            relationships_to_transfer=relationships_to_transfer,
            files_to_transfer=files_to_transfer,
            warnings=warnings,
        )

    async def merge_entities(
        self,
        project_id: str,
        primary_entity: Dict[str, Any],
        duplicate_entities: List[Dict[str, Any]],
        strategy: MergeStrategy = MergeStrategy.KEEP_PRIMARY,
        custom_resolutions: Optional[Dict[str, Any]] = None,
    ) -> MergeResult:
        """
        Merge duplicate entities into primary entity.

        Note: This service doesn't directly modify the database.
        The caller is responsible for applying the merged profile
        and deleting duplicates.

        Args:
            project_id: Project ID
            primary_entity: Primary entity to merge into
            duplicate_entities: Entities to merge from
            strategy: Merge strategy
            custom_resolutions: Custom field resolutions

        Returns:
            Merge result with merged profile
        """
        # Get preview first
        preview = await self.preview_merge(
            project_id=project_id,
            primary_entity=primary_entity,
            duplicate_entities=duplicate_entities,
            strategy=strategy,
            custom_resolutions=custom_resolutions,
        )

        primary_id = primary_entity.get("id", "primary")
        duplicate_ids = [d.get("id", "unknown") for d in duplicate_entities]

        result = MergeResult(
            success=True,
            merged_entity_id=primary_id,
            deleted_entity_ids=duplicate_ids,
            relationships_transferred=preview.relationships_to_transfer,
            files_transferred=preview.files_to_transfer,
            conflicts_resolved=len(preview.conflicts),
            warnings=preview.warnings,
        )

        # Store in history
        with self._lock:
            while len(self._merge_history) >= self._max_history_entries:
                self._merge_history.popitem(last=False)
            self._merge_history[result.merge_id] = result

        return result

    async def get_merge_history(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MergeResult]:
        """
        Get merge operation history.

        Args:
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of merge results
        """
        with self._lock:
            results = list(self._merge_history.values())
            results.sort(key=lambda x: x.merged_at, reverse=True)
            return results[:limit]

    async def undo_merge(self, merge_id: str) -> bool:
        """
        Check if a merge can be undone.

        Note: Actual undo would require stored backup data.

        Args:
            merge_id: Merge operation ID

        Returns:
            True if undo is possible
        """
        with self._lock:
            return merge_id in self._merge_history

    async def generate_report(
        self,
        project_id: str,
        entities: List[Dict[str, Any]],
    ) -> DeduplicationReport:
        """
        Generate deduplication report for a project.

        Args:
            project_id: Project ID
            entities: All entities in project

        Returns:
            Deduplication analysis report
        """
        # Find all duplicates
        all_duplicates = await self.find_all_duplicates(project_id, entities)

        # Count statistics
        total_entities = len(entities)
        duplicate_groups = len(all_duplicates)
        total_duplicates = sum(len(dups) for dups in all_duplicates.values())

        high_conf = 0
        medium_conf = 0
        low_conf = 0
        field_counts: Dict[str, int] = {}

        for entity_id, candidates in all_duplicates.items():
            for candidate in candidates:
                if candidate.confidence >= 0.95:
                    high_conf += 1
                elif candidate.confidence >= 0.70:
                    medium_conf += 1
                else:
                    low_conf += 1

                # Count matching fields
                for match in candidate.field_matches:
                    if match.is_match:
                        field_counts[match.field_id] = field_counts.get(match.field_id, 0) + 1

        # Sort fields by count
        top_fields = dict(sorted(
            field_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])

        # Estimate reduction
        if total_entities > 0:
            estimated_reduction = (total_duplicates / total_entities) * 100
        else:
            estimated_reduction = 0.0

        return DeduplicationReport(
            project_id=project_id,
            total_entities=total_entities,
            duplicate_groups=duplicate_groups,
            total_duplicates=total_duplicates,
            high_confidence_matches=high_conf,
            medium_confidence_matches=medium_conf,
            low_confidence_matches=low_conf,
            top_duplicate_fields=top_fields,
            estimated_reduction=estimated_reduction,
        )

    async def _compare_entities(
        self,
        entity1: Dict[str, Any],
        entity2: Dict[str, Any],
        match_types: List[MatchType],
    ) -> Dict[str, Any]:
        """
        Compare two entities and calculate similarity.

        Returns:
            Dict with confidence, reasons, and field matches
        """
        matches: List[MatchResult] = []
        reasons: List[str] = []
        total_weight = 0.0
        weighted_similarity = 0.0

        # Get identifier fields from config
        identifier_fields = self._config.identifier_fields

        # Compare each identifier field
        for field_id in identifier_fields:
            val1 = self._get_field_value(entity1, field_id)
            val2 = self._get_field_value(entity2, field_id)

            if val1 is None or val2 is None:
                continue

            if val1 == "" or val2 == "":
                continue

            # Get field weight
            weight = self._config.field_weights.get(field_id, 1.0)

            # Try each match type
            best_similarity = 0.0
            best_match_type = MatchType.EXACT
            is_match = False

            for match_type in match_types:
                similarity = self._calculate_similarity(
                    str(val1), str(val2), match_type
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_type = match_type

            # Determine if it's a match
            if best_match_type == MatchType.EXACT and best_similarity == 1.0:
                is_match = True
                reasons.append(f"Exact match on {field_id}")
            elif best_similarity >= self._config.fuzzy_match_threshold:
                is_match = True
                reasons.append(f"Similar {field_id} ({best_similarity:.0%})")

            matches.append(MatchResult(
                field_id=field_id,
                field_name=field_id,
                match_type=best_match_type,
                similarity=best_similarity,
                primary_value=val1,
                duplicate_value=val2,
                is_match=is_match,
            ))

            if is_match:
                total_weight += weight
                weighted_similarity += weight * best_similarity

        # Calculate overall confidence
        if total_weight > 0:
            confidence = weighted_similarity / total_weight
        else:
            confidence = 0.0

        return {
            "confidence": confidence,
            "reasons": reasons,
            "matches": matches,
        }

    def _get_field_value(self, entity: Dict[str, Any], field_id: str) -> Any:
        """Get field value from entity, handling nested paths."""
        # Handle list fields (e.g., emails, phones)
        if field_id in entity:
            val = entity[field_id]
            if isinstance(val, list) and len(val) > 0:
                return val[0] if isinstance(val[0], str) else str(val[0])
            return val

        # Handle nested paths
        keys = field_id.split(".")
        value = entity
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _calculate_similarity(
        self,
        str1: str,
        str2: str,
        match_type: MatchType,
    ) -> float:
        """Calculate similarity between two strings using specified method."""
        if not str1 or not str2:
            return 0.0

        if match_type == MatchType.EXACT:
            return 1.0 if str1 == str2 else 0.0

        elif match_type == MatchType.CASE_INSENSITIVE:
            return 1.0 if str1.lower() == str2.lower() else 0.0

        elif match_type == MatchType.NORMALIZED:
            norm1 = self._normalize_string(str1)
            norm2 = self._normalize_string(str2)
            return 1.0 if norm1 == norm2 else 0.0

        elif match_type == MatchType.FUZZY:
            return self._levenshtein_similarity(str1.lower(), str2.lower())

        elif match_type == MatchType.PHONETIC:
            return self._phonetic_similarity(str1, str2)

        elif match_type == MatchType.PARTIAL:
            s1, s2 = str1.lower(), str2.lower()
            if s1 in s2 or s2 in s1:
                return min(len(s1), len(s2)) / max(len(s1), len(s2))
            return 0.0

        elif match_type == MatchType.TOKEN_SET:
            return self._token_set_ratio(str1, str2)

        return 0.0

    def _normalize_string(self, s: str) -> str:
        """Normalize a string for comparison."""
        # Remove non-alphanumeric, lowercase
        return re.sub(r"[^a-z0-9]", "", s.lower())

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity (1 - normalized distance)."""
        if not s1 or not s2:
            return 0.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0

        # Create distance matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )

        distance = matrix[len1][len2]
        max_len = max(len1, len2)
        return 1.0 - (distance / max_len)

    def _phonetic_similarity(self, s1: str, s2: str) -> float:
        """Calculate phonetic similarity using simple Soundex-like approach."""
        def simple_phonetic(s: str) -> str:
            """Simple phonetic encoding."""
            if not s:
                return ""
            s = s.upper()
            # Keep first letter
            code = s[0]
            # Map consonants
            mapping = {
                "B": "1", "F": "1", "P": "1", "V": "1",
                "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
                "D": "3", "T": "3",
                "L": "4",
                "M": "5", "N": "5",
                "R": "6",
            }
            prev = ""
            for c in s[1:]:
                if c in mapping:
                    if mapping[c] != prev:
                        code += mapping[c]
                        prev = mapping[c]
                else:
                    prev = ""
            return code[:4].ljust(4, "0")

        code1 = simple_phonetic(s1)
        code2 = simple_phonetic(s2)

        if code1 == code2:
            return 1.0

        # Partial match
        matching = sum(1 for a, b in zip(code1, code2) if a == b)
        return matching / 4.0

    def _token_set_ratio(self, s1: str, s2: str) -> float:
        """Calculate token set ratio similarity."""
        tokens1 = set(s1.lower().split())
        tokens2 = set(s2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _suggest_resolution(
        self,
        field_id: str,
        primary_val: Any,
        duplicate_val: Any,
        strategy: MergeStrategy,
    ) -> FieldConflictResolution:
        """Suggest resolution for a field conflict."""
        if strategy == MergeStrategy.KEEP_PRIMARY:
            return FieldConflictResolution.USE_PRIMARY
        elif strategy == MergeStrategy.KEEP_DUPLICATE:
            return FieldConflictResolution.USE_DUPLICATE
        elif strategy == MergeStrategy.KEEP_LONGEST:
            if len(str(primary_val or "")) >= len(str(duplicate_val or "")):
                return FieldConflictResolution.USE_PRIMARY
            return FieldConflictResolution.USE_DUPLICATE
        elif strategy == MergeStrategy.KEEP_ALL:
            return FieldConflictResolution.USE_COMBINED
        else:
            return FieldConflictResolution.USE_PRIMARY

    def _resolve_conflict(
        self,
        primary_val: Any,
        duplicate_val: Any,
        all_values: List[Any],
        resolution: FieldConflictResolution,
        strategy: MergeStrategy,
    ) -> Any:
        """Resolve a field conflict based on resolution strategy."""
        if resolution == FieldConflictResolution.USE_PRIMARY:
            return primary_val
        elif resolution == FieldConflictResolution.USE_DUPLICATE:
            return duplicate_val
        elif resolution == FieldConflictResolution.USE_COMBINED:
            # Combine unique values
            unique = []
            seen = set()
            for val in all_values:
                val_str = str(val) if val is not None else ""
                if val_str and val_str not in seen:
                    unique.append(val)
                    seen.add(val_str)
            return unique if len(unique) > 1 else (unique[0] if unique else None)
        else:
            return primary_val

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        with self._lock:
            return {
                "cached_candidates": len(self._candidate_cache),
                "merge_history_count": len(self._merge_history),
                "config": {
                    "auto_merge_threshold": self._config.auto_merge_threshold,
                    "review_threshold": self._config.review_threshold,
                    "ignore_threshold": self._config.ignore_threshold,
                    "fuzzy_match_threshold": self._config.fuzzy_match_threshold,
                },
            }

    def clear_cache(self) -> int:
        """Clear the candidate cache."""
        with self._lock:
            count = len(self._candidate_cache)
            self._candidate_cache.clear()
            return count


# Module-level singleton
_deduplication_service: Optional[DeduplicationService] = None


def get_deduplication_service(
    config: Optional[DeduplicationConfig] = None,
) -> DeduplicationService:
    """
    Get or create the DeduplicationService singleton.

    Args:
        config: Optional deduplication configuration

    Returns:
        DeduplicationService instance
    """
    global _deduplication_service

    if _deduplication_service is None:
        _deduplication_service = DeduplicationService(config)

    return _deduplication_service


def set_deduplication_service(service: Optional[DeduplicationService]) -> None:
    """Set the global DeduplicationService instance."""
    global _deduplication_service
    _deduplication_service = service


def reset_deduplication_service() -> None:
    """Reset the singleton instance."""
    global _deduplication_service
    _deduplication_service = None
