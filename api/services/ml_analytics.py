"""
ML Analytics Service for Basset Hound OSINT Platform.

This module provides machine learning-based analytics and insights including:
- Query suggestions based on history, patterns, and semantic similarity
- Search pattern detection and trending topic identification
- Entity insights with relationship suggestions
- Query similarity calculation using TF-IDF and edit distance
- Query clustering using simple algorithms
- Zero-result prediction based on historical patterns

Features:
- Lightweight ML implementation (no heavy dependencies)
- TF-IDF vectorization for text similarity
- N-gram analysis for pattern detection
- Simple clustering algorithms
- Frequency-based predictions
- Thread-safe operations
"""

import logging
import math
import re
import threading
import time
from collections import Counter, defaultdict, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ==================== Pydantic Models ====================


class SuggestionSource(str, Enum):
    """Source of a query suggestion."""
    HISTORY = "history"
    PATTERN = "pattern"
    SEMANTIC = "semantic"


class InsightType(str, Enum):
    """Types of entity insights."""
    RELATED_ENTITY = "related_entity"
    MISSING_RELATIONSHIP = "missing_relationship"
    DATA_QUALITY = "data_quality"
    SEARCH_FREQUENCY = "search_frequency"
    CONNECTION_STRENGTH = "connection_strength"


class PatternType(str, Enum):
    """Types of search patterns."""
    TRENDING = "trending"
    SEASONAL = "seasonal"
    COMMON = "common"
    DECLINING = "declining"
    ENTITY_TYPE = "entity_type"
    FILTER_COMBO = "filter_combo"


class QuerySuggestion(BaseModel):
    """Model for a query suggestion with confidence and source."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestion": "john doe email",
                "confidence": 0.85,
                "source": "history",
                "related_queries": ["john doe", "john doe phone"]
            }
        }
    )

    suggestion: str = Field(..., description="The suggested query string")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    source: SuggestionSource = Field(
        ..., description="Source of the suggestion"
    )
    related_queries: List[str] = Field(
        default_factory=list, description="Related query suggestions"
    )


class SearchPattern(BaseModel):
    """Model for a detected search pattern."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern_type": "trending",
                "description": "Rising interest in cryptocurrency-related searches",
                "frequency": 45,
                "examples": ["bitcoin wallet", "ethereum address"],
                "insight": "15% increase in crypto searches this week"
            }
        }
    )

    pattern_type: PatternType = Field(
        ..., description="Type of pattern detected"
    )
    description: str = Field(..., description="Human-readable pattern description")
    frequency: int = Field(..., ge=0, description="How often this pattern occurs")
    examples: List[str] = Field(
        default_factory=list, description="Example queries matching this pattern"
    )
    insight: str = Field(
        "", description="Actionable insight about this pattern"
    )


class EntityInsight(BaseModel):
    """Model for an entity-specific insight."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "person-123",
                "insight_type": "related_entity",
                "description": "Frequently searched together with 'Jane Smith'",
                "confidence": 0.78,
                "related_entities": ["person-456"],
                "recommended_actions": ["Review relationship", "Link entities"]
            }
        }
    )

    entity_id: str = Field(..., description="ID of the entity this insight is about")
    insight_type: InsightType = Field(..., description="Type of insight")
    description: str = Field(..., description="Human-readable insight description")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    related_entities: List[str] = Field(
        default_factory=list, description="Related entity IDs"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended actions based on this insight"
    )


# ==================== Internal Data Structures ====================


@dataclass
class QueryRecord:
    """Internal record for tracking query data."""
    query: str
    timestamp: datetime
    result_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    clicked_entities: List[str] = field(default_factory=list)
    project_id: Optional[str] = None


@dataclass
class TFIDFVector:
    """TF-IDF vector representation."""
    terms: Dict[str, float] = field(default_factory=dict)
    magnitude: float = 0.0


@dataclass
class TFIDFCacheEntry:
    """Cache entry for TF-IDF vectors with metadata for invalidation."""
    vector: TFIDFVector
    idf_snapshot: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class CacheStatistics:
    """Statistics for TF-IDF cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    evictions: int = 0
    idf_change_invalidations: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0
        self.idf_change_invalidations = 0


# ==================== ML Analytics Service ====================


class MLAnalyticsService:
    """
    Machine learning-based analytics service for search optimization.

    This service provides intelligent query suggestions, pattern detection,
    entity insights, and predictive capabilities using lightweight ML techniques.

    Usage:
        service = MLAnalyticsService()

        # Add query data for training
        service.record_query("john doe", result_count=5, clicked=["entity-1"])

        # Get suggestions
        suggestions = service.suggest_queries("joh", limit=5)

        # Detect patterns
        patterns = service.detect_search_patterns(days=7)

        # Get entity insights
        insights = service.get_entity_insights("entity-123", "project-1")
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        max_history_size: int = 10000,
        ngram_sizes: Tuple[int, ...] = (2, 3),
        max_cache_size: int = 1000,
        idf_change_threshold: float = 0.1,
        cache_ttl_seconds: Optional[float] = 3600.0,
        max_cooccurrence_entries: int = 5000,
        max_entity_queries: int = 2000,
    ):
        """
        Initialize the ML Analytics service.

        Args:
            min_confidence: Minimum confidence threshold for suggestions
            max_history_size: Maximum number of queries to store in history
            ngram_sizes: Tuple of n-gram sizes to use for pattern analysis
            max_cache_size: Maximum number of TF-IDF vectors to cache (LRU eviction)
            idf_change_threshold: Threshold for IDF change that triggers cache invalidation (0.1 = 10%)
            cache_ttl_seconds: Time-to-live for cache entries in seconds (None = no expiration)
            max_cooccurrence_entries: Maximum number of query co-occurrence entries (LRU eviction)
            max_entity_queries: Maximum number of entity query associations (LRU eviction)
        """
        self._query_history: List[QueryRecord] = []
        self._query_counts: Counter = Counter()
        # Use OrderedDict for LRU behavior on co-occurrence data
        self._cooccurrence: OrderedDict[str, Counter] = OrderedDict()
        # Use OrderedDict for LRU behavior on entity queries
        self._entity_queries: OrderedDict[str, List[str]] = OrderedDict()
        self._zero_result_queries: Set[str] = set()
        # Use OrderedDict for LRU cache behavior
        self._tfidf_cache: OrderedDict[str, TFIDFCacheEntry] = OrderedDict()
        self._idf: Dict[str, float] = {}
        self._idf_last_updated: float = time.time()
        self._idf_snapshot_at_last_update: Dict[str, float] = {}
        self._document_count: int = 0
        self._term_document_counts: Counter = Counter()
        self._ngram_counts: Dict[int, Counter] = {n: Counter() for n in ngram_sizes}

        self._min_confidence = min_confidence
        self._max_history_size = max_history_size
        self._ngram_sizes = ngram_sizes
        self._max_cache_size = max_cache_size
        self._idf_change_threshold = idf_change_threshold
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_cooccurrence_entries = max_cooccurrence_entries
        self._max_entity_queries = max_entity_queries
        self._cache_stats = CacheStatistics()
        self._lock = threading.RLock()

    # ==================== Data Recording ====================

    def record_query(
        self,
        query: str,
        result_count: int = 0,
        clicked_entities: Optional[List[str]] = None,
        entity_types: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a search query for ML analysis.

        Args:
            query: The search query string
            result_count: Number of results returned
            clicked_entities: List of entity IDs clicked from results
            entity_types: Entity types searched
            project_id: Optional project ID
            timestamp: Optional timestamp (defaults to now)
        """
        if not query or not query.strip():
            return

        normalized = self._normalize_query(query)
        if not normalized:
            return

        record = QueryRecord(
            query=normalized,
            timestamp=timestamp or datetime.now(timezone.utc),
            result_count=result_count,
            entity_types=entity_types or [],
            clicked_entities=clicked_entities or [],
            project_id=project_id,
        )

        with self._lock:
            # Add to history
            self._query_history.append(record)

            # Trim history if needed
            if len(self._query_history) > self._max_history_size:
                self._query_history = self._query_history[-self._max_history_size:]

            # Update counts
            self._query_counts[normalized] += 1

            # Track zero results
            if result_count == 0:
                self._zero_result_queries.add(normalized)

            # Track entity associations
            for entity_id in clicked_entities or []:
                if entity_id not in self._entity_queries:
                    self._entity_queries[entity_id] = []
                self._entity_queries[entity_id].append(normalized)
                self._entity_queries.move_to_end(entity_id)  # Mark as recently used
            self._enforce_entity_queries_limit()

            # Update n-grams
            tokens = self._tokenize(normalized)
            for n in self._ngram_sizes:
                for ngram in self._get_ngrams(tokens, n):
                    self._ngram_counts[n][ngram] += 1

            # Update TF-IDF components (this also handles cache invalidation for changed IDF terms)
            self._update_idf(tokens)

            # Invalidate TF-IDF cache for this specific query (since it was just recorded)
            if normalized in self._tfidf_cache:
                del self._tfidf_cache[normalized]
                self._cache_stats.invalidations += 1

            # Track query co-occurrence (queries within same session)
            self._update_cooccurrence(normalized)

    def _update_cooccurrence(self, query: str, window_minutes: int = 30) -> None:
        """Update query co-occurrence based on temporal proximity."""
        if len(self._query_history) < 2:
            return

        current_time = self._query_history[-1].timestamp
        window_start = current_time - timedelta(minutes=window_minutes)

        # Find queries in the same time window
        for record in reversed(self._query_history[:-1]):
            if record.timestamp < window_start:
                break
            if record.query != query:
                if query not in self._cooccurrence:
                    self._cooccurrence[query] = Counter()
                if record.query not in self._cooccurrence:
                    self._cooccurrence[record.query] = Counter()
                self._cooccurrence[query][record.query] += 1
                self._cooccurrence[record.query][query] += 1
                # Mark as recently used
                self._cooccurrence.move_to_end(query)
                self._cooccurrence.move_to_end(record.query)

        # Enforce limit after updates
        self._enforce_cooccurrence_limit()

    def _update_idf(self, tokens: List[str]) -> None:
        """Update IDF values with new document and handle cache invalidation."""
        self._document_count += 1
        seen_terms = set(tokens)
        significantly_changed_terms: Set[str] = set()

        for term in seen_terms:
            self._term_document_counts[term] += 1

        # Recalculate IDF for affected terms and track significant changes
        for term in seen_terms:
            old_idf = self._idf.get(term, 0.0)
            df = self._term_document_counts[term]
            new_idf = math.log(self._document_count / (1 + df)) + 1
            self._idf[term] = new_idf

            # Check if IDF changed significantly
            if old_idf > 0:
                change_ratio = abs(new_idf - old_idf) / old_idf
                if change_ratio > self._idf_change_threshold:
                    significantly_changed_terms.add(term)

        # Invalidate cache entries that use significantly changed terms
        if significantly_changed_terms:
            self._invalidate_cache_for_terms(significantly_changed_terms)

        self._idf_last_updated = time.time()

    def _invalidate_cache_for_terms(self, terms: Set[str]) -> None:
        """Invalidate cache entries that contain any of the specified terms."""
        keys_to_remove = []
        for query, entry in self._tfidf_cache.items():
            # Check if any of the terms in this entry's vector have changed
            entry_terms = set(entry.vector.terms.keys())
            if entry_terms & terms:
                keys_to_remove.append(query)

        for key in keys_to_remove:
            del self._tfidf_cache[key]
            self._cache_stats.idf_change_invalidations += 1

    # ==================== Query Suggestions ====================

    def suggest_queries(
        self,
        partial_query: str,
        user_history: Optional[List[str]] = None,
        limit: int = 10,
        project_id: Optional[str] = None,
    ) -> List[QuerySuggestion]:
        """
        Generate query suggestions based on partial input.

        Combines prefix matching, historical patterns, and semantic similarity
        to provide intelligent suggestions.

        Args:
            partial_query: The partial query string to complete
            user_history: Optional list of user's previous queries
            limit: Maximum number of suggestions to return
            project_id: Optional project ID for scoping

        Returns:
            List of QuerySuggestion objects sorted by confidence
        """
        if not partial_query or not partial_query.strip():
            return []

        normalized = self._normalize_query(partial_query)
        if not normalized:
            return []

        suggestions: Dict[str, QuerySuggestion] = {}

        with self._lock:
            # 1. Prefix-based suggestions from history
            prefix_suggestions = self._get_prefix_suggestions(
                normalized, project_id
            )
            for query, confidence in prefix_suggestions:
                if query not in suggestions:
                    suggestions[query] = QuerySuggestion(
                        suggestion=query,
                        confidence=confidence,
                        source=SuggestionSource.HISTORY,
                        related_queries=self._get_related_queries(query, limit=3),
                    )

            # 2. Pattern-based suggestions (from n-grams)
            pattern_suggestions = self._get_pattern_suggestions(
                normalized, project_id
            )
            for query, confidence in pattern_suggestions:
                if query not in suggestions:
                    suggestions[query] = QuerySuggestion(
                        suggestion=query,
                        confidence=confidence * 0.9,  # Slightly lower weight
                        source=SuggestionSource.PATTERN,
                        related_queries=self._get_related_queries(query, limit=3),
                    )

            # 3. Semantic similarity suggestions (TF-IDF based)
            if user_history:
                semantic_suggestions = self._get_semantic_suggestions(
                    normalized, user_history, project_id
                )
                for query, confidence in semantic_suggestions:
                    if query not in suggestions:
                        suggestions[query] = QuerySuggestion(
                            suggestion=query,
                            confidence=confidence * 0.85,  # Lower weight for semantic
                            source=SuggestionSource.SEMANTIC,
                            related_queries=self._get_related_queries(query, limit=3),
                        )

        # Sort by confidence and limit
        sorted_suggestions = sorted(
            suggestions.values(),
            key=lambda x: x.confidence,
            reverse=True,
        )

        # Filter by minimum confidence
        filtered = [
            s for s in sorted_suggestions
            if s.confidence >= self._min_confidence
        ]

        return filtered[:limit]

    def _get_prefix_suggestions(
        self,
        prefix: str,
        project_id: Optional[str],
    ) -> List[Tuple[str, float]]:
        """Get suggestions based on prefix matching."""
        suggestions = []
        max_count = max(self._query_counts.values()) if self._query_counts else 1

        for query, count in self._query_counts.most_common():
            if query.startswith(prefix) and query != prefix:
                # Calculate confidence based on frequency
                confidence = min(1.0, (count / max_count) * 0.8 + 0.2)
                suggestions.append((query, confidence))

            if len(suggestions) >= 20:
                break

        return suggestions

    def _get_pattern_suggestions(
        self,
        partial: str,
        project_id: Optional[str],
    ) -> List[Tuple[str, float]]:
        """Get suggestions based on n-gram patterns."""
        suggestions = []
        tokens = self._tokenize(partial)

        if not tokens:
            return suggestions

        # Look for queries that share n-grams
        matching_queries: Counter = Counter()

        for n in self._ngram_sizes:
            partial_ngrams = set(self._get_ngrams(tokens, n))

            for query, count in self._query_counts.items():
                if query.startswith(partial):
                    continue  # Skip prefix matches (already covered)

                query_tokens = self._tokenize(query)
                query_ngrams = set(self._get_ngrams(query_tokens, n))

                # Calculate n-gram overlap
                overlap = len(partial_ngrams & query_ngrams)
                if overlap > 0:
                    matching_queries[query] += overlap * count

        max_score = max(matching_queries.values()) if matching_queries else 1

        for query, score in matching_queries.most_common(10):
            confidence = min(1.0, score / max_score)
            suggestions.append((query, confidence))

        return suggestions

    def _get_semantic_suggestions(
        self,
        partial: str,
        user_history: List[str],
        project_id: Optional[str],
    ) -> List[Tuple[str, float]]:
        """Get suggestions based on semantic similarity to user history."""
        suggestions = []

        # Get similar queries from history
        for hist_query in user_history[-10:]:  # Use last 10 queries
            normalized_hist = self._normalize_query(hist_query)

            # Find queries co-occurring with history queries
            if normalized_hist in self._cooccurrence:
                for coquery, count in self._cooccurrence[normalized_hist].most_common(5):
                    if coquery.startswith(partial) or partial in coquery:
                        similarity = self.calculate_query_similarity(partial, coquery)
                        if similarity > 0.3:
                            suggestions.append((coquery, similarity))

        # Deduplicate
        seen = set()
        unique_suggestions = []
        for query, conf in suggestions:
            if query not in seen:
                seen.add(query)
                unique_suggestions.append((query, conf))

        return unique_suggestions[:10]

    def _get_related_queries(self, query: str, limit: int = 5) -> List[str]:
        """Get queries related to the given query."""
        related = []

        if query in self._cooccurrence:
            for coquery, _ in self._cooccurrence[query].most_common(limit):
                related.append(coquery)

        return related

    # ==================== Pattern Detection ====================

    def detect_search_patterns(
        self,
        time_range: Optional[int] = None,
        project_id: Optional[str] = None,
    ) -> List[SearchPattern]:
        """
        Detect common search patterns from query history.

        Identifies trending topics, seasonal patterns, and common query types.

        Args:
            time_range: Number of days to analyze (None = all time)
            project_id: Optional project ID for scoping

        Returns:
            List of SearchPattern objects
        """
        patterns = []

        with self._lock:
            # Filter history by time range
            cutoff = None
            if time_range:
                cutoff = datetime.now(timezone.utc) - timedelta(days=time_range)

            filtered_history = [
                r for r in self._query_history
                if (cutoff is None or r.timestamp >= cutoff) and
                   (project_id is None or r.project_id == project_id)
            ]

            if not filtered_history:
                return patterns

            # 1. Detect trending patterns
            trending = self._detect_trending_patterns(filtered_history)
            patterns.extend(trending)

            # 2. Detect common query patterns
            common = self._detect_common_patterns(filtered_history)
            patterns.extend(common)

            # 3. Detect entity type patterns
            entity_patterns = self._detect_entity_type_patterns(filtered_history)
            patterns.extend(entity_patterns)

            # 4. Detect declining patterns
            declining = self._detect_declining_patterns(filtered_history)
            patterns.extend(declining)

        return patterns

    def _detect_trending_patterns(
        self,
        history: List[QueryRecord],
    ) -> List[SearchPattern]:
        """Detect trending search topics."""
        patterns = []

        if len(history) < 10:
            return patterns

        # Split history into two halves
        mid = len(history) // 2
        first_half = history[:mid]
        second_half = history[mid:]

        first_counts = Counter(r.query for r in first_half)
        second_counts = Counter(r.query for r in second_half)

        # Find queries that increased significantly
        for query, count in second_counts.most_common(20):
            first_count = first_counts.get(query, 0)
            if first_count > 0:
                growth = (count - first_count) / first_count
            else:
                growth = count  # New query

            if growth > 0.5 and count >= 3:  # 50% growth, at least 3 occurrences
                patterns.append(SearchPattern(
                    pattern_type=PatternType.TRENDING,
                    description=f"Rising interest in '{query}'",
                    frequency=count,
                    examples=[query],
                    insight=f"{int(growth * 100)}% increase in searches",
                ))

        return patterns[:5]  # Top 5 trending

    def _detect_common_patterns(
        self,
        history: List[QueryRecord],
    ) -> List[SearchPattern]:
        """Detect commonly used search patterns."""
        patterns = []

        query_counts = Counter(r.query for r in history)
        total_queries = len(history)

        for query, count in query_counts.most_common(10):
            if count >= 3:  # At least 3 occurrences
                percentage = (count / total_queries) * 100
                patterns.append(SearchPattern(
                    pattern_type=PatternType.COMMON,
                    description=f"Frequently searched: '{query}'",
                    frequency=count,
                    examples=[query],
                    insight=f"Represents {percentage:.1f}% of all searches",
                ))

        return patterns[:5]  # Top 5 common

    def _detect_entity_type_patterns(
        self,
        history: List[QueryRecord],
    ) -> List[SearchPattern]:
        """Detect patterns in entity type searches."""
        patterns = []

        type_counts = Counter()
        type_examples: Dict[str, List[str]] = defaultdict(list)

        for record in history:
            for entity_type in record.entity_types:
                type_counts[entity_type] += 1
                if len(type_examples[entity_type]) < 3:
                    type_examples[entity_type].append(record.query)

        for entity_type, count in type_counts.most_common(5):
            if count >= 3:
                patterns.append(SearchPattern(
                    pattern_type=PatternType.ENTITY_TYPE,
                    description=f"Searches focused on '{entity_type}' entities",
                    frequency=count,
                    examples=type_examples[entity_type],
                    insight=f"Consider optimizing {entity_type} search performance",
                ))

        return patterns

    def _detect_declining_patterns(
        self,
        history: List[QueryRecord],
    ) -> List[SearchPattern]:
        """Detect declining search topics."""
        patterns = []

        if len(history) < 10:
            return patterns

        mid = len(history) // 2
        first_half = history[:mid]
        second_half = history[mid:]

        first_counts = Counter(r.query for r in first_half)
        second_counts = Counter(r.query for r in second_half)

        for query, first_count in first_counts.most_common(20):
            if first_count < 3:
                continue

            second_count = second_counts.get(query, 0)
            if second_count < first_count * 0.5:  # 50% or more decline
                decline = ((first_count - second_count) / first_count) * 100
                patterns.append(SearchPattern(
                    pattern_type=PatternType.DECLINING,
                    description=f"Declining interest in '{query}'",
                    frequency=second_count,
                    examples=[query],
                    insight=f"{int(decline)}% decrease in searches",
                ))

        return patterns[:3]  # Top 3 declining

    # ==================== Entity Insights ====================

    def get_entity_insights(
        self,
        entity_id: str,
        project_id: Optional[str] = None,
    ) -> List[EntityInsight]:
        """
        Generate insights about an entity based on search behavior.

        Args:
            entity_id: The entity ID to analyze
            project_id: Optional project ID for context

        Returns:
            List of EntityInsight objects
        """
        insights = []

        with self._lock:
            # Get queries associated with this entity
            entity_queries = self._entity_queries.get(entity_id, [])

            if not entity_queries:
                return insights

            # 1. Find co-searched entities
            co_entities: Counter = Counter()
            for query in entity_queries:
                # Find other entities searched with similar queries
                for other_id, other_queries in self._entity_queries.items():
                    if other_id != entity_id:
                        overlap = len(set(entity_queries) & set(other_queries))
                        if overlap > 0:
                            co_entities[other_id] += overlap

            for other_id, overlap_count in co_entities.most_common(3):
                confidence = min(1.0, overlap_count / len(entity_queries))
                if confidence >= 0.3:
                    insights.append(EntityInsight(
                        entity_id=entity_id,
                        insight_type=InsightType.RELATED_ENTITY,
                        description=f"Frequently searched together with entity {other_id}",
                        confidence=confidence,
                        related_entities=[other_id],
                        recommended_actions=[
                            "Review potential relationship",
                            "Consider linking entities",
                        ],
                    ))

            # 2. Search frequency insight
            query_count = len(entity_queries)
            if query_count >= 5:
                insights.append(EntityInsight(
                    entity_id=entity_id,
                    insight_type=InsightType.SEARCH_FREQUENCY,
                    description=f"High search activity ({query_count} searches)",
                    confidence=min(1.0, query_count / 20),
                    related_entities=[],
                    recommended_actions=[
                        "Entity may be of high interest",
                        "Review data completeness",
                    ],
                ))

            # 3. Check for zero-result queries
            zero_result_queries = [
                q for q in entity_queries
                if q in self._zero_result_queries
            ]
            if zero_result_queries:
                insights.append(EntityInsight(
                    entity_id=entity_id,
                    insight_type=InsightType.DATA_QUALITY,
                    description=f"{len(zero_result_queries)} searches returned no results",
                    confidence=min(1.0, len(zero_result_queries) / len(entity_queries)),
                    related_entities=[],
                    recommended_actions=[
                        "Verify entity data is complete",
                        "Check for spelling/naming issues",
                    ],
                ))

        return insights

    # ==================== Related Search Recommendations ====================

    def recommend_related_searches(
        self,
        query: str,
        results: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> List[str]:
        """
        Suggest follow-up searches based on query and results.

        Args:
            query: The original search query
            results: Optional list of search results
            limit: Maximum number of recommendations

        Returns:
            List of recommended search queries
        """
        recommendations = []
        normalized = self._normalize_query(query)

        with self._lock:
            # 1. Get co-occurring queries
            if normalized in self._cooccurrence:
                for coquery, _ in self._cooccurrence[normalized].most_common(limit * 2):
                    if coquery != normalized:
                        recommendations.append(coquery)

            # 2. Add variations based on common terms
            tokens = self._tokenize(normalized)
            for token in tokens:
                if len(token) >= 3:
                    for other_query in self._query_counts:
                        if token in other_query and other_query != normalized:
                            if other_query not in recommendations:
                                recommendations.append(other_query)
                        if len(recommendations) >= limit * 3:
                            break

            # 3. If we have results, suggest refinements based on entity types
            if results:
                entity_types = set()
                for result in results[:10]:
                    if "entity_type" in result:
                        entity_types.add(result["entity_type"])

                for et in entity_types:
                    refined = f"{normalized} {et.lower()}"
                    if refined not in recommendations:
                        recommendations.append(refined)

        # Deduplicate and limit
        seen = set()
        unique = []
        for rec in recommendations:
            if rec not in seen and rec != normalized:
                seen.add(rec)
                unique.append(rec)
        return unique[:limit]

    # ==================== Query Similarity ====================

    def calculate_query_similarity(
        self,
        query1: str,
        query2: str,
    ) -> float:
        """
        Calculate similarity between two queries.

        Uses a combination of Jaccard similarity, edit distance,
        and TF-IDF cosine similarity.

        Args:
            query1: First query string
            query2: Second query string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not query1 or not query2:
            return 0.0

        q1 = self._normalize_query(query1)
        q2 = self._normalize_query(query2)

        if q1 == q2:
            return 1.0

        # 1. Jaccard similarity on tokens
        tokens1 = set(self._tokenize(q1))
        tokens2 = set(self._tokenize(q2))

        if not tokens1 or not tokens2:
            return 0.0

        jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)

        # 2. Normalized edit distance
        edit_sim = 1.0 - (self._edit_distance(q1, q2) / max(len(q1), len(q2)))

        # 3. TF-IDF cosine similarity
        tfidf_sim = self._tfidf_cosine_similarity(q1, q2)

        # Weighted combination
        weights = (0.3, 0.3, 0.4)  # jaccard, edit, tfidf
        combined = (
            weights[0] * jaccard +
            weights[1] * edit_sim +
            weights[2] * tfidf_sim
        )

        return min(1.0, max(0.0, combined))

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance."""
        m, n = len(s1), len(s2)

        if m == 0:
            return n
        if n == 0:
            return m

        # Use space-optimized version
        prev = list(range(n + 1))
        curr = [0] * (n + 1)

        for i in range(1, m + 1):
            curr[0] = i
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    curr[j] = prev[j - 1]
                else:
                    curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
            prev, curr = curr, prev

        return prev[n]

    def _tfidf_cosine_similarity(self, q1: str, q2: str) -> float:
        """Calculate TF-IDF cosine similarity."""
        vec1 = self._get_tfidf_vector(q1)
        vec2 = self._get_tfidf_vector(q2)

        if vec1.magnitude == 0 or vec2.magnitude == 0:
            return 0.0

        # Calculate dot product
        dot_product = sum(
            vec1.terms.get(term, 0) * vec2.terms.get(term, 0)
            for term in set(vec1.terms) | set(vec2.terms)
        )

        return dot_product / (vec1.magnitude * vec2.magnitude)

    def _get_tfidf_vector(self, query: str) -> TFIDFVector:
        """Get or compute TF-IDF vector for a query with LRU caching."""
        current_time = time.time()

        # Check if entry exists in cache
        if query in self._tfidf_cache:
            entry = self._tfidf_cache[query]

            # Check TTL expiration
            if self._cache_ttl_seconds is not None:
                age = current_time - entry.created_at
                if age > self._cache_ttl_seconds:
                    # Entry expired, remove and recompute
                    del self._tfidf_cache[query]
                    self._cache_stats.invalidations += 1
                else:
                    # Valid cache hit - move to end for LRU
                    self._tfidf_cache.move_to_end(query)
                    entry.last_accessed = current_time
                    entry.access_count += 1
                    self._cache_stats.hits += 1
                    return entry.vector
            else:
                # No TTL, just use the cached entry
                self._tfidf_cache.move_to_end(query)
                entry.last_accessed = current_time
                entry.access_count += 1
                self._cache_stats.hits += 1
                return entry.vector

        # Cache miss
        self._cache_stats.misses += 1

        # Compute the TF-IDF vector
        tokens = self._tokenize(query)
        term_counts = Counter(tokens)

        vector = TFIDFVector()

        # Capture current IDF values for the terms in this query
        idf_snapshot = {}
        for term, count in term_counts.items():
            # TF: log(1 + count)
            tf = math.log(1 + count)
            # IDF: from stored values or default
            idf = self._idf.get(term, 1.0)
            idf_snapshot[term] = idf
            vector.terms[term] = tf * idf

        # Calculate magnitude
        vector.magnitude = math.sqrt(sum(v ** 2 for v in vector.terms.values()))

        # Create cache entry with metadata
        entry = TFIDFCacheEntry(
            vector=vector,
            idf_snapshot=idf_snapshot,
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
        )

        # Evict LRU entries if cache is full
        self._evict_lru_entries()

        # Add to cache
        self._tfidf_cache[query] = entry
        return vector

    def _evict_lru_entries(self) -> None:
        """Evict least recently used entries if cache exceeds max size."""
        while len(self._tfidf_cache) >= self._max_cache_size:
            # Remove the oldest entry (first item in OrderedDict)
            oldest_key = next(iter(self._tfidf_cache))
            del self._tfidf_cache[oldest_key]
            self._cache_stats.evictions += 1

    def _enforce_cooccurrence_limit(self) -> None:
        """Evict oldest co-occurrence entries when limit is exceeded (LRU eviction)."""
        while len(self._cooccurrence) > self._max_cooccurrence_entries:
            oldest_key = next(iter(self._cooccurrence))
            del self._cooccurrence[oldest_key]
            logger.debug(f"LRU evicted co-occurrence entry: {oldest_key}")

    def _enforce_entity_queries_limit(self) -> None:
        """Evict oldest entity query associations when limit is exceeded (LRU eviction)."""
        while len(self._entity_queries) > self._max_entity_queries:
            oldest_key = next(iter(self._entity_queries))
            del self._entity_queries[oldest_key]
            logger.debug(f"LRU evicted entity queries entry: {oldest_key}")

    # ==================== Memory Management ====================

    def get_tfidf_cache_size(self) -> int:
        """Get current size of TF-IDF cache."""
        with self._lock:
            return len(self._tfidf_cache)

    def get_tfidf_cache_capacity(self) -> int:
        """Get maximum TF-IDF cache capacity."""
        return self._max_cache_size

    def get_cooccurrence_size(self) -> int:
        """Get current number of co-occurrence entries."""
        with self._lock:
            return len(self._cooccurrence)

    def get_cooccurrence_capacity(self) -> int:
        """Get maximum co-occurrence entries capacity."""
        return self._max_cooccurrence_entries

    def get_entity_queries_size(self) -> int:
        """Get current number of entity query associations."""
        with self._lock:
            return len(self._entity_queries)

    def get_entity_queries_capacity(self) -> int:
        """Get maximum entity queries capacity."""
        return self._max_entity_queries

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for this service."""
        with self._lock:
            return {
                "query_history_count": len(self._query_history),
                "query_history_capacity": self._max_history_size,
                "query_history_usage_percent": (len(self._query_history) / self._max_history_size * 100) if self._max_history_size > 0 else 0,
                "tfidf_cache_count": len(self._tfidf_cache),
                "tfidf_cache_capacity": self._max_cache_size,
                "tfidf_cache_usage_percent": (len(self._tfidf_cache) / self._max_cache_size * 100) if self._max_cache_size > 0 else 0,
                "cooccurrence_count": len(self._cooccurrence),
                "cooccurrence_capacity": self._max_cooccurrence_entries,
                "cooccurrence_usage_percent": (len(self._cooccurrence) / self._max_cooccurrence_entries * 100) if self._max_cooccurrence_entries > 0 else 0,
                "entity_queries_count": len(self._entity_queries),
                "entity_queries_capacity": self._max_entity_queries,
                "entity_queries_usage_percent": (len(self._entity_queries) / self._max_entity_queries * 100) if self._max_entity_queries > 0 else 0,
                "unique_queries": len(self._query_counts),
                "zero_result_queries": len(self._zero_result_queries),
                "vocabulary_size": len(self._idf),
            }

    # ==================== Query Clustering ====================

    def cluster_similar_queries(
        self,
        queries: List[str],
        threshold: float = 0.6,
    ) -> Dict[str, List[str]]:
        """
        Group similar queries together using simple clustering.

        Uses a greedy approach based on similarity threshold.

        Args:
            queries: List of queries to cluster
            threshold: Similarity threshold for clustering (0-1)

        Returns:
            Dict mapping cluster representative to list of similar queries
        """
        if not queries:
            return {}

        normalized = [self._normalize_query(q) for q in queries if q]
        unique_queries = list(set(normalized))

        if len(unique_queries) <= 1:
            if unique_queries:
                return {unique_queries[0]: unique_queries}
            return {}

        clusters: Dict[str, List[str]] = {}
        assigned: Set[str] = set()

        for query in unique_queries:
            if query in assigned:
                continue

            # Start new cluster
            cluster = [query]
            assigned.add(query)

            # Find similar queries
            for other in unique_queries:
                if other in assigned:
                    continue

                similarity = self.calculate_query_similarity(query, other)
                if similarity >= threshold:
                    cluster.append(other)
                    assigned.add(other)

            clusters[query] = cluster

        return clusters

    # ==================== Zero-Result Prediction ====================

    def predict_zero_results(
        self,
        query: str,
    ) -> float:
        """
        Predict likelihood of zero results for a query.

        Based on:
        - Historical zero-result patterns
        - Query similarity to known zero-result queries
        - Token-level analysis

        Args:
            query: Query to analyze

        Returns:
            Probability of zero results (0.0 to 1.0)
        """
        if not query:
            return 0.5

        normalized = self._normalize_query(query)

        with self._lock:
            # 1. Check if exact query has zero results history
            if normalized in self._zero_result_queries:
                return 0.9

            # 2. Check if query was successful before
            if normalized in self._query_counts:
                history = [
                    r for r in self._query_history
                    if r.query == normalized
                ]
                if history:
                    zero_count = sum(1 for r in history if r.result_count == 0)
                    return zero_count / len(history)

            # 3. Check similarity to known zero-result queries
            if self._zero_result_queries:
                max_similarity = 0.0
                for zero_query in list(self._zero_result_queries)[:100]:
                    similarity = self.calculate_query_similarity(normalized, zero_query)
                    max_similarity = max(max_similarity, similarity)

                if max_similarity > 0.8:
                    return 0.7 * max_similarity

            # 4. Check for unusual tokens (not in any successful query)
            tokens = set(self._tokenize(normalized))
            successful_queries = [
                r.query for r in self._query_history
                if r.result_count > 0
            ]
            all_successful_tokens = set()
            for sq in successful_queries:
                all_successful_tokens.update(self._tokenize(sq))

            if all_successful_tokens:
                novel_tokens = tokens - all_successful_tokens
                if len(novel_tokens) == len(tokens):
                    return 0.6  # All tokens are novel

        return 0.3  # Default uncertainty

    # ==================== Utility Methods ====================

    def _normalize_query(self, query: str) -> str:
        """Normalize a query string."""
        if not query:
            return ""
        return query.strip().lower()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        if not text:
            return []
        # Split on whitespace and remove punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return [t for t in tokens if len(t) >= 2]

    def _get_ngrams(self, tokens: List[str], n: int) -> List[str]:
        """Get n-grams from token list."""
        if len(tokens) < n:
            return []
        return [
            " ".join(tokens[i:i + n])
            for i in range(len(tokens) - n + 1)
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics including cache performance metrics."""
        with self._lock:
            return {
                "total_queries_recorded": len(self._query_history),
                "unique_queries": len(self._query_counts),
                "zero_result_queries": len(self._zero_result_queries),
                "entities_tracked": len(self._entity_queries),
                "vocabulary_size": len(self._idf),
                "ngram_counts": {n: len(c) for n, c in self._ngram_counts.items()},
                "cache": self.get_cache_statistics(),
            }

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get detailed TF-IDF cache statistics.

        Returns:
            Dict containing cache performance metrics including:
            - size: Current number of cached entries
            - max_size: Maximum cache capacity
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Percentage of requests served from cache
            - evictions: Number of LRU evictions
            - invalidations: Number of TTL-based invalidations
            - idf_change_invalidations: Number of IDF-change based invalidations
        """
        with self._lock:
            return {
                "size": len(self._tfidf_cache),
                "max_size": self._max_cache_size,
                "hits": self._cache_stats.hits,
                "misses": self._cache_stats.misses,
                "hit_rate": self._cache_stats.hit_rate,
                "evictions": self._cache_stats.evictions,
                "invalidations": self._cache_stats.invalidations,
                "idf_change_invalidations": self._cache_stats.idf_change_invalidations,
                "ttl_seconds": self._cache_ttl_seconds,
                "idf_change_threshold": self._idf_change_threshold,
            }

    def clear_tfidf_cache(self) -> int:
        """
        Manually clear all TF-IDF cache entries.

        Returns:
            Number of cache entries that were cleared
        """
        with self._lock:
            count = len(self._tfidf_cache)
            self._tfidf_cache.clear()
            self._cache_stats.invalidations += count
            logger.info(f"Cleared {count} TF-IDF cache entries")
            return count

    def reset_cache_statistics(self) -> None:
        """Reset all cache statistics counters to zero."""
        with self._lock:
            self._cache_stats.reset()
            logger.info("Reset TF-IDF cache statistics")

    def invalidate_cache_entries_older_than(self, seconds: float) -> int:
        """
        Invalidate cache entries older than the specified age.

        Args:
            seconds: Maximum age in seconds for cache entries to keep

        Returns:
            Number of cache entries that were invalidated
        """
        with self._lock:
            current_time = time.time()
            keys_to_remove = []

            for query, entry in self._tfidf_cache.items():
                age = current_time - entry.created_at
                if age > seconds:
                    keys_to_remove.append(query)

            for key in keys_to_remove:
                del self._tfidf_cache[key]
                self._cache_stats.invalidations += 1

            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} TF-IDF cache entries older than {seconds}s")

            return len(keys_to_remove)

    def set_cache_ttl(self, ttl_seconds: Optional[float]) -> None:
        """
        Update the cache TTL setting.

        Args:
            ttl_seconds: New TTL in seconds, or None to disable TTL expiration
        """
        with self._lock:
            self._cache_ttl_seconds = ttl_seconds
            logger.info(f"Updated TF-IDF cache TTL to {ttl_seconds}s")

    def set_max_cache_size(self, max_size: int) -> None:
        """
        Update the maximum cache size.

        If the new size is smaller than the current cache size,
        excess entries will be evicted using LRU policy.

        Args:
            max_size: New maximum cache size
        """
        with self._lock:
            self._max_cache_size = max_size
            # Evict excess entries if needed
            while len(self._tfidf_cache) > self._max_cache_size:
                oldest_key = next(iter(self._tfidf_cache))
                del self._tfidf_cache[oldest_key]
                self._cache_stats.evictions += 1
            logger.info(f"Updated TF-IDF cache max size to {max_size}")

    def set_idf_change_threshold(self, threshold: float) -> None:
        """
        Update the IDF change threshold for cache invalidation.

        Args:
            threshold: New threshold (0.0 to 1.0, e.g., 0.1 = 10% change)
        """
        with self._lock:
            self._idf_change_threshold = max(0.0, min(1.0, threshold))
            logger.info(f"Updated IDF change threshold to {self._idf_change_threshold}")

    def clear(self) -> None:
        """Clear all stored data including cache and statistics."""
        with self._lock:
            self._query_history.clear()
            self._query_counts.clear()
            self._cooccurrence.clear()
            self._entity_queries.clear()
            self._zero_result_queries.clear()
            self._tfidf_cache.clear()
            self._idf.clear()
            self._idf_last_updated = time.time()
            self._idf_snapshot_at_last_update.clear()
            self._document_count = 0
            self._term_document_counts.clear()
            self._cache_stats.reset()
            for n in self._ngram_sizes:
                self._ngram_counts[n].clear()


# ==================== Singleton Management ====================


_ml_analytics_instance: Optional[MLAnalyticsService] = None
_ml_analytics_lock = threading.Lock()


def get_ml_analytics() -> MLAnalyticsService:
    """
    Get or create the MLAnalyticsService singleton instance.

    Returns:
        MLAnalyticsService instance
    """
    global _ml_analytics_instance

    with _ml_analytics_lock:
        if _ml_analytics_instance is None:
            _ml_analytics_instance = MLAnalyticsService()

    return _ml_analytics_instance


def set_ml_analytics(service: Optional[MLAnalyticsService]) -> None:
    """
    Set the global MLAnalyticsService instance.

    Args:
        service: MLAnalyticsService instance or None to clear
    """
    global _ml_analytics_instance

    with _ml_analytics_lock:
        _ml_analytics_instance = service
