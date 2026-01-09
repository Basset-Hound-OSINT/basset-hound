"""
Suggestion Service for Phase 43.4: Suggestion System.

Provides on-demand suggestion computation for "Suggested Tags" on entity profiles.
Shows matching DataItems from other entities and suggests entities for orphan data.

Key Features:
- get_entity_suggestions: Find matching DataItems from other entities
- get_orphan_suggestions: Find entities that match orphan data
- Confidence-based ranking (HIGH/MEDIUM/LOW)
- Dismissed suggestions tracking
- Read-only suggestions (no automatic linking)

Phase 43.4: Smart Suggestions & Data Matching System
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from api.services.matching_engine import MatchingEngine, MatchResult
from api.services.data_service import DataService
from api.services.neo4j_service import AsyncNeo4jService

logger = logging.getLogger("basset_hound.suggestion_service")


class ConfidenceLevel(str, Enum):
    """Confidence levels for suggestions."""
    HIGH = "HIGH"      # 0.9-1.0
    MEDIUM = "MEDIUM"  # 0.7-0.89
    LOW = "LOW"        # 0.5-0.69


@dataclass
class SuggestionMatch:
    """
    Represents a single suggestion match.

    Attributes:
        data_id: ID of the data item that matched
        data_type: Type of data (email, phone, etc.)
        data_value: The actual value
        match_type: Type of match (exact_hash, exact_string, partial_string)
        confidence_score: Confidence score (0.5-1.0)
        matched_entity_id: ID of entity containing matching data
        matched_entity_name: Name of entity containing matching data
        matched_orphan_id: ID of orphan containing matching data (if applicable)
    """
    data_id: str
    data_type: str
    data_value: str
    match_type: str
    confidence_score: float
    matched_entity_id: Optional[str] = None
    matched_entity_name: Optional[str] = None
    matched_orphan_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "data_id": self.data_id,
            "data_type": self.data_type,
            "data_value": self.data_value,
            "match_type": self.match_type,
            "confidence_score": self.confidence_score
        }

        if self.matched_entity_id:
            result["matched_entity_id"] = self.matched_entity_id
            result["matched_entity_name"] = self.matched_entity_name

        if self.matched_orphan_id:
            result["matched_orphan_id"] = self.matched_orphan_id

        return result


@dataclass
class ConfidenceGroup:
    """
    Group of suggestions at a specific confidence level.

    Attributes:
        confidence: Confidence level (HIGH, MEDIUM, LOW)
        matches: List of suggestion matches at this confidence level
    """
    confidence: ConfidenceLevel
    matches: List[SuggestionMatch]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence": self.confidence.value,
            "matches": [match.to_dict() for match in self.matches]
        }


class SuggestionService:
    """
    Service for generating on-demand suggestions for entities and orphans.

    This service provides intelligent suggestions based on matching data:
    - For entities: Suggests other entities with matching data
    - For orphans: Suggests entities to link orphan data to
    - Confidence-based grouping (HIGH/MEDIUM/LOW)
    - Dismissed suggestions tracking

    Usage:
        async with SuggestionService() as service:
            suggestions = await service.get_entity_suggestions("ent_abc123")
            orphan_suggestions = await service.get_orphan_suggestions("orphan_xyz")
    """

    def __init__(
        self,
        neo4j_service: Optional[AsyncNeo4jService] = None,
        matching_engine: Optional[MatchingEngine] = None
    ):
        """
        Initialize the suggestion service.

        Args:
            neo4j_service: Optional Neo4j service instance
            matching_engine: Optional MatchingEngine instance
        """
        self.neo4j_service = neo4j_service or AsyncNeo4jService()
        self._owns_neo4j = neo4j_service is None
        self.matching_engine = matching_engine or MatchingEngine(self.neo4j_service)
        self._owns_matching_engine = matching_engine is None
        self.data_service = DataService(self.neo4j_service)

    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_neo4j:
            await self.neo4j_service.connect()
        if self._owns_matching_engine:
            await self.matching_engine.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owns_matching_engine:
            await self.matching_engine.__aexit__(exc_type, exc_val, exc_tb)
        if self._owns_neo4j:
            await self.neo4j_service.close()

    def _classify_confidence(self, score: float) -> ConfidenceLevel:
        """
        Classify a confidence score into HIGH/MEDIUM/LOW.

        Args:
            score: Confidence score (0.0-1.0)

        Returns:
            ConfidenceLevel enum
        """
        if score >= 0.9:
            return ConfidenceLevel.HIGH
        elif score >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _group_by_confidence(self, matches: List[SuggestionMatch]) -> List[ConfidenceGroup]:
        """
        Group matches by confidence level.

        Args:
            matches: List of suggestion matches

        Returns:
            List of ConfidenceGroup objects sorted by confidence (HIGH to LOW)
        """
        groups: Dict[ConfidenceLevel, List[SuggestionMatch]] = {
            ConfidenceLevel.HIGH: [],
            ConfidenceLevel.MEDIUM: [],
            ConfidenceLevel.LOW: []
        }

        for match in matches:
            level = self._classify_confidence(match.confidence_score)
            groups[level].append(match)

        # Return groups in order: HIGH, MEDIUM, LOW
        result = []
        for level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]:
            if groups[level]:
                result.append(ConfidenceGroup(confidence=level, matches=groups[level]))

        return result

    async def _get_entity_name(self, entity_id: str) -> Optional[str]:
        """
        Get entity name by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity name or None if not found
        """
        try:
            async with self.neo4j_service.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})
                    RETURN p.name as name
                    """,
                    entity_id=entity_id
                )
                record = await result.single()
                return record["name"] if record else None
        except Exception as e:
            logger.error(f"Error getting entity name: {e}")
            return None

    async def _get_dismissed_suggestions(self, entity_id: str) -> List[str]:
        """
        Get list of dismissed suggestion IDs for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of dismissed suggestion IDs
        """
        try:
            async with self.neo4j_service.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})-[:DISMISSED_SUGGESTION]->(d:DataItem)
                    RETURN d.id as data_id
                    """,
                    entity_id=entity_id
                )
                records = await result.data()
                return [record["data_id"] for record in records]
        except Exception as e:
            logger.error(f"Error getting dismissed suggestions: {e}")
            return []

    async def get_entity_suggestions(
        self,
        entity_id: str,
        include_partial: bool = True,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get suggestions for an entity based on matching data.

        Finds DataItems from other entities that match this entity's data.
        Useful for finding potential relationships and duplicates.

        Args:
            entity_id: Entity ID to get suggestions for
            include_partial: Whether to include partial matches
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Dictionary with entity_id, suggestions grouped by confidence, and dismissed_count
        """
        try:
            # Get all data items for this entity
            entity_data = await self.data_service.list_data_items(entity_id=entity_id)

            if not entity_data:
                return {
                    "entity_id": entity_id,
                    "suggestions": [],
                    "dismissed_count": 0
                }

            # Get dismissed suggestions
            dismissed_ids = await self._get_dismissed_suggestions(entity_id)

            # Find matches for each data item
            all_matches: List[SuggestionMatch] = []
            seen_data_ids = set()

            for data_item in entity_data:
                # Find all matches for this data item
                matches = await self.matching_engine.find_all_matches(
                    value=str(data_item.value),
                    field_type=data_item.type,
                    include_partial=include_partial,
                    partial_threshold=min_confidence
                )

                for match_result, confidence, match_type in matches:
                    # Skip if it's the same entity or dismissed
                    if match_result.entity_id == entity_id:
                        continue

                    if match_result.data_id in dismissed_ids:
                        continue

                    # Skip if we've already seen this data item
                    if match_result.data_id and match_result.data_id in seen_data_ids:
                        continue

                    # Skip if below minimum confidence
                    if confidence < min_confidence:
                        continue

                    # Get entity name if it's an entity match
                    entity_name = None
                    orphan_id = None

                    if match_result.entity_id.startswith("ent_") or match_result.entity_id.startswith("person_"):
                        entity_name = await self._get_entity_name(match_result.entity_id)
                    elif match_result.entity_id.startswith("orphan_"):
                        orphan_id = match_result.entity_id

                    suggestion = SuggestionMatch(
                        data_id=match_result.data_id or match_result.entity_id,
                        data_type=match_result.field_type,
                        data_value=match_result.field_value,
                        match_type=match_result.match_type,
                        confidence_score=confidence,
                        matched_entity_id=match_result.entity_id if entity_name else None,
                        matched_entity_name=entity_name,
                        matched_orphan_id=orphan_id
                    )

                    all_matches.append(suggestion)
                    if match_result.data_id:
                        seen_data_ids.add(match_result.data_id)

            # Group by confidence
            confidence_groups = self._group_by_confidence(all_matches)

            return {
                "entity_id": entity_id,
                "suggestions": [group.to_dict() for group in confidence_groups],
                "dismissed_count": len(dismissed_ids)
            }

        except Exception as e:
            logger.error(f"Error getting entity suggestions: {e}")
            return {
                "entity_id": entity_id,
                "error": str(e),
                "suggestions": [],
                "dismissed_count": 0
            }

    async def get_orphan_suggestions(
        self,
        orphan_id: str,
        include_partial: bool = True,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get entity suggestions for orphan data.

        Finds entities that match the orphan's data. Useful for linking
        orphan data to existing entities.

        Args:
            orphan_id: Orphan ID to get suggestions for
            include_partial: Whether to include partial matches
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Dictionary with orphan_id, suggestions grouped by confidence
        """
        try:
            # Get orphan data
            async with self.neo4j_service.session() as session:
                result = await session.run(
                    """
                    MATCH (o:OrphanData {id: $orphan_id})
                    RETURN o.identifier_value as value,
                           o.identifier_type as type,
                           o.id as id
                    """,
                    orphan_id=orphan_id
                )
                record = await result.single()

                if not record:
                    return {
                        "orphan_id": orphan_id,
                        "error": "Orphan not found",
                        "suggestions": []
                    }

                orphan_value = record["value"]
                orphan_type = record["type"]

            # Find matches
            matches = await self.matching_engine.find_all_matches(
                value=str(orphan_value),
                field_type=orphan_type,
                include_partial=include_partial,
                partial_threshold=min_confidence
            )

            # Convert to suggestions
            all_matches: List[SuggestionMatch] = []
            seen_entity_ids = set()

            for match_result, confidence, match_type in matches:
                # Skip if we've already suggested this entity
                if match_result.entity_id in seen_entity_ids:
                    continue

                # Skip if below minimum confidence
                if confidence < min_confidence:
                    continue

                # Only suggest entities, not other orphans
                if match_result.entity_id.startswith("orphan_"):
                    continue

                # Get entity name
                entity_name = await self._get_entity_name(match_result.entity_id)

                suggestion = SuggestionMatch(
                    data_id=match_result.data_id or match_result.entity_id,
                    data_type=match_result.field_type,
                    data_value=match_result.field_value,
                    match_type=match_result.match_type,
                    confidence_score=confidence,
                    matched_entity_id=match_result.entity_id,
                    matched_entity_name=entity_name
                )

                all_matches.append(suggestion)
                seen_entity_ids.add(match_result.entity_id)

            # Group by confidence
            confidence_groups = self._group_by_confidence(all_matches)

            return {
                "orphan_id": orphan_id,
                "suggestions": [group.to_dict() for group in confidence_groups]
            }

        except Exception as e:
            logger.error(f"Error getting orphan suggestions: {e}")
            return {
                "orphan_id": orphan_id,
                "error": str(e),
                "suggestions": []
            }

    async def dismiss_suggestion(
        self,
        entity_id: str,
        data_id: str
    ) -> bool:
        """
        Mark a suggestion as dismissed for an entity.

        Creates a DISMISSED_SUGGESTION relationship between the entity
        and the data item so it won't appear in future suggestions.

        Args:
            entity_id: Entity ID
            data_id: Data ID to dismiss

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.neo4j_service.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})
                    MATCH (d:DataItem {id: $data_id})
                    MERGE (p)-[r:DISMISSED_SUGGESTION {
                        dismissed_at: datetime()
                    }]->(d)
                    RETURN count(r) as created
                    """,
                    entity_id=entity_id,
                    data_id=data_id
                )
                record = await result.single()
                return record is not None and record["created"] > 0
        except Exception as e:
            logger.error(f"Error dismissing suggestion: {e}")
            return False

    async def get_dismissed_suggestions_list(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """
        Get list of all dismissed suggestions for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Dictionary with entity_id and list of dismissed suggestions
        """
        try:
            async with self.neo4j_service.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})-[r:DISMISSED_SUGGESTION]->(d:DataItem)
                    RETURN d.id as data_id,
                           d.type as data_type,
                           d.value as data_value,
                           r.dismissed_at as dismissed_at
                    ORDER BY r.dismissed_at DESC
                    """,
                    entity_id=entity_id
                )
                records = await result.data()

                dismissed = []
                for record in records:
                    dismissed.append({
                        "data_id": record["data_id"],
                        "data_type": record["data_type"],
                        "data_value": str(record["data_value"]),
                        "dismissed_at": record["dismissed_at"]
                    })

                return {
                    "entity_id": entity_id,
                    "dismissed_suggestions": dismissed,
                    "count": len(dismissed)
                }
        except Exception as e:
            logger.error(f"Error getting dismissed suggestions list: {e}")
            return {
                "entity_id": entity_id,
                "error": str(e),
                "dismissed_suggestions": [],
                "count": 0
            }


# Module-level singleton
_suggestion_service_instance: Optional[SuggestionService] = None


async def get_suggestion_service() -> SuggestionService:
    """
    Get or create the singleton SuggestionService instance.

    Returns:
        SuggestionService instance
    """
    global _suggestion_service_instance

    if _suggestion_service_instance is None:
        _suggestion_service_instance = SuggestionService()
        await _suggestion_service_instance.__aenter__()

    return _suggestion_service_instance
