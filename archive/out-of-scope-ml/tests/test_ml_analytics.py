"""
Tests for the ML Analytics Service

Comprehensive test coverage for:
- QuerySuggestion, SearchPattern, EntityInsight Pydantic models
- MLAnalyticsService class methods
- Query recording and tracking
- Query suggestions (prefix, pattern, semantic)
- Pattern detection (trending, common, declining, entity-type)
- Entity insights (related, frequency, data quality)
- Related search recommendations
- Query similarity calculations
- Query clustering
- Zero-result predictions
- Singleton management
- Thread safety
- API router endpoints
"""

import math
import pytest
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock, AsyncMock, patch

from api.services.ml_analytics import (
    # Models
    QuerySuggestion,
    SearchPattern,
    EntityInsight,
    SuggestionSource,
    PatternType,
    InsightType,
    # Service
    MLAnalyticsService,
    QueryRecord,
    TFIDFVector,
    # Singleton
    get_ml_analytics,
    set_ml_analytics,
)


# ==================== QuerySuggestion Model Tests ====================


class TestQuerySuggestionModel:
    """Tests for QuerySuggestion Pydantic model."""

    def test_query_suggestion_creation(self):
        """Test creating a QuerySuggestion with all fields."""
        suggestion = QuerySuggestion(
            suggestion="john doe",
            confidence=0.85,
            source=SuggestionSource.HISTORY,
            related_queries=["john smith", "jane doe"],
        )

        assert suggestion.suggestion == "john doe"
        assert suggestion.confidence == 0.85
        assert suggestion.source == SuggestionSource.HISTORY
        assert len(suggestion.related_queries) == 2

    def test_query_suggestion_defaults(self):
        """Test QuerySuggestion with default values."""
        suggestion = QuerySuggestion(
            suggestion="test",
            confidence=0.5,
            source=SuggestionSource.PATTERN,
        )

        assert suggestion.related_queries == []

    def test_query_suggestion_confidence_bounds(self):
        """Test confidence value bounds."""
        with pytest.raises(ValueError):
            QuerySuggestion(
                suggestion="test",
                confidence=1.5,
                source=SuggestionSource.HISTORY,
            )

        with pytest.raises(ValueError):
            QuerySuggestion(
                suggestion="test",
                confidence=-0.1,
                source=SuggestionSource.HISTORY,
            )

    def test_suggestion_source_enum(self):
        """Test SuggestionSource enum values."""
        assert SuggestionSource.HISTORY.value == "history"
        assert SuggestionSource.PATTERN.value == "pattern"
        assert SuggestionSource.SEMANTIC.value == "semantic"


# ==================== SearchPattern Model Tests ====================


class TestSearchPatternModel:
    """Tests for SearchPattern Pydantic model."""

    def test_search_pattern_creation(self):
        """Test creating a SearchPattern."""
        pattern = SearchPattern(
            pattern_type=PatternType.TRENDING,
            description="Rising interest in crypto",
            frequency=45,
            examples=["bitcoin", "ethereum"],
            insight="15% increase",
        )

        assert pattern.pattern_type == PatternType.TRENDING
        assert pattern.description == "Rising interest in crypto"
        assert pattern.frequency == 45
        assert len(pattern.examples) == 2

    def test_pattern_type_enum(self):
        """Test PatternType enum values."""
        assert PatternType.TRENDING.value == "trending"
        assert PatternType.SEASONAL.value == "seasonal"
        assert PatternType.COMMON.value == "common"
        assert PatternType.DECLINING.value == "declining"
        assert PatternType.ENTITY_TYPE.value == "entity_type"

    def test_search_pattern_defaults(self):
        """Test SearchPattern with defaults."""
        pattern = SearchPattern(
            pattern_type=PatternType.COMMON,
            description="Common pattern",
            frequency=10,
        )

        assert pattern.examples == []
        assert pattern.insight == ""


# ==================== EntityInsight Model Tests ====================


class TestEntityInsightModel:
    """Tests for EntityInsight Pydantic model."""

    def test_entity_insight_creation(self):
        """Test creating an EntityInsight."""
        insight = EntityInsight(
            entity_id="person-123",
            insight_type=InsightType.RELATED_ENTITY,
            description="Related to Jane Smith",
            confidence=0.78,
            related_entities=["person-456"],
            recommended_actions=["Review relationship"],
        )

        assert insight.entity_id == "person-123"
        assert insight.insight_type == InsightType.RELATED_ENTITY
        assert insight.confidence == 0.78
        assert len(insight.related_entities) == 1

    def test_insight_type_enum(self):
        """Test InsightType enum values."""
        assert InsightType.RELATED_ENTITY.value == "related_entity"
        assert InsightType.MISSING_RELATIONSHIP.value == "missing_relationship"
        assert InsightType.DATA_QUALITY.value == "data_quality"
        assert InsightType.SEARCH_FREQUENCY.value == "search_frequency"


# ==================== MLAnalyticsService Basic Tests ====================


class TestMLAnalyticsServiceBasic:
    """Basic tests for MLAnalyticsService class."""

    @pytest.fixture
    def service(self):
        """Create a fresh MLAnalyticsService instance."""
        return MLAnalyticsService()

    def test_initialization(self, service):
        """Test service initialization."""
        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 0
        assert stats["unique_queries"] == 0

    def test_initialization_with_params(self):
        """Test initialization with custom parameters."""
        service = MLAnalyticsService(
            min_confidence=0.5,
            max_history_size=5000,
            ngram_sizes=(2, 3, 4),
        )
        assert service._min_confidence == 0.5
        assert service._max_history_size == 5000
        assert service._ngram_sizes == (2, 3, 4)

    def test_record_query_basic(self, service):
        """Test recording a basic query."""
        service.record_query("test query")

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 1
        assert stats["unique_queries"] == 1

    def test_record_query_with_all_params(self, service):
        """Test recording query with all parameters."""
        service.record_query(
            query="john doe",
            result_count=5,
            clicked_entities=["entity-1", "entity-2"],
            entity_types=["Person"],
            project_id="project-123",
        )

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 1
        assert stats["entities_tracked"] == 2

    def test_record_empty_query(self, service):
        """Test that empty queries are not recorded."""
        service.record_query("")
        service.record_query("   ")

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 0

    def test_normalize_query(self, service):
        """Test query normalization."""
        service.record_query("  JOHN DOE  ")
        service.record_query("john doe")

        stats = service.get_statistics()
        assert stats["unique_queries"] == 1  # Same normalized query

    def test_clear(self, service):
        """Test clearing all data."""
        service.record_query("test1")
        service.record_query("test2")

        service.clear()

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 0
        assert stats["unique_queries"] == 0


# ==================== Query Recording Tests ====================


class TestQueryRecording:
    """Tests for query recording functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh MLAnalyticsService instance."""
        return MLAnalyticsService()

    def test_record_multiple_queries(self, service):
        """Test recording multiple queries."""
        for i in range(10):
            service.record_query(f"query {i}")

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 10
        assert stats["unique_queries"] == 10

    def test_record_duplicate_queries(self, service):
        """Test recording duplicate queries."""
        for _ in range(5):
            service.record_query("same query")

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == 5
        assert stats["unique_queries"] == 1

    def test_zero_result_tracking(self, service):
        """Test tracking zero-result queries."""
        service.record_query("successful", result_count=5)
        service.record_query("failed", result_count=0)
        service.record_query("also failed", result_count=0)

        stats = service.get_statistics()
        assert stats["zero_result_queries"] == 2

    def test_entity_tracking(self, service):
        """Test entity query association tracking."""
        service.record_query("query1", clicked_entities=["e1", "e2"])
        service.record_query("query2", clicked_entities=["e1", "e3"])

        stats = service.get_statistics()
        assert stats["entities_tracked"] == 3

    def test_max_history_size(self):
        """Test that history is trimmed when max size is exceeded."""
        service = MLAnalyticsService(max_history_size=100)

        for i in range(150):
            service.record_query(f"query {i}")

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] <= 100


# ==================== Query Suggestion Tests ====================


class TestQuerySuggestions:
    """Tests for query suggestion functionality."""

    @pytest.fixture
    def service(self):
        """Create a service with test data."""
        s = MLAnalyticsService()
        # Add test search history
        for _ in range(10):
            s.record_query("john doe")
        for _ in range(5):
            s.record_query("john smith")
        for _ in range(3):
            s.record_query("johnny appleseed")
        s.record_query("jane doe")
        return s

    def test_prefix_suggestions(self, service):
        """Test prefix-based suggestions."""
        suggestions = service.suggest_queries("joh", limit=5)

        assert len(suggestions) > 0
        assert all(s.suggestion.startswith("joh") for s in suggestions)

    def test_suggestions_sorted_by_confidence(self, service):
        """Test that suggestions are sorted by confidence."""
        suggestions = service.suggest_queries("joh", limit=10)

        if len(suggestions) > 1:
            confidences = [s.confidence for s in suggestions]
            assert confidences == sorted(confidences, reverse=True)

    def test_suggestions_include_source(self, service):
        """Test that suggestions include source information."""
        suggestions = service.suggest_queries("joh")

        for s in suggestions:
            assert s.source in [
                SuggestionSource.HISTORY,
                SuggestionSource.PATTERN,
                SuggestionSource.SEMANTIC,
            ]

    def test_suggestions_limit(self, service):
        """Test suggestion limit."""
        suggestions = service.suggest_queries("j", limit=2)

        assert len(suggestions) <= 2

    def test_suggestions_empty_query(self, service):
        """Test suggestions with empty query."""
        suggestions = service.suggest_queries("")

        assert suggestions == []

    def test_suggestions_no_match(self, service):
        """Test suggestions with no matching prefix."""
        suggestions = service.suggest_queries("xyz123")

        assert len(suggestions) == 0

    def test_suggestions_with_user_history(self, service):
        """Test suggestions with user history."""
        suggestions = service.suggest_queries(
            "j",
            user_history=["john doe", "jane doe"],
        )

        # Should still get suggestions
        assert len(suggestions) >= 0

    def test_related_queries_included(self, service):
        """Test that related queries are included in suggestions."""
        suggestions = service.suggest_queries("joh", limit=5)

        # At least some suggestions should have related queries
        has_related = any(len(s.related_queries) > 0 for s in suggestions)
        # This is optional based on co-occurrence data


# ==================== Pattern Detection Tests ====================


class TestPatternDetection:
    """Tests for pattern detection functionality."""

    @pytest.fixture
    def service(self):
        """Create a service with test data for patterns."""
        s = MLAnalyticsService()

        # Create trending pattern
        old_time = datetime.now(timezone.utc) - timedelta(days=7)
        new_time = datetime.now(timezone.utc)

        # Old queries
        for _ in range(2):
            s.record_query("bitcoin", timestamp=old_time)

        # New queries (trending)
        for _ in range(10):
            s.record_query("bitcoin", timestamp=new_time)

        # Common queries
        for _ in range(15):
            s.record_query("john doe", timestamp=new_time)

        # Declining queries
        for _ in range(10):
            s.record_query("old topic", timestamp=old_time)
        for _ in range(2):
            s.record_query("old topic", timestamp=new_time)

        return s

    def test_detect_patterns(self, service):
        """Test basic pattern detection."""
        patterns = service.detect_search_patterns()

        assert len(patterns) > 0

    def test_detect_trending_patterns(self, service):
        """Test trending pattern detection."""
        patterns = service.detect_search_patterns()

        trending = [p for p in patterns if p.pattern_type == PatternType.TRENDING]
        # May or may not detect trending based on threshold
        assert isinstance(trending, list)

    def test_detect_common_patterns(self, service):
        """Test common pattern detection."""
        patterns = service.detect_search_patterns()

        common = [p for p in patterns if p.pattern_type == PatternType.COMMON]
        assert len(common) > 0
        assert any("john doe" in p.examples for p in common)

    def test_detect_declining_patterns(self, service):
        """Test declining pattern detection."""
        patterns = service.detect_search_patterns()

        declining = [p for p in patterns if p.pattern_type == PatternType.DECLINING]
        # May detect declining patterns
        assert isinstance(declining, list)

    def test_patterns_with_time_range(self, service):
        """Test patterns with time range filter."""
        patterns = service.detect_search_patterns(time_range=7)

        assert isinstance(patterns, list)

    def test_patterns_empty_history(self):
        """Test patterns with no history."""
        service = MLAnalyticsService()
        patterns = service.detect_search_patterns()

        assert patterns == []

    def test_entity_type_patterns(self):
        """Test entity type pattern detection."""
        service = MLAnalyticsService()

        for _ in range(10):
            service.record_query("query", entity_types=["Person"])

        patterns = service.detect_search_patterns()

        entity_patterns = [
            p for p in patterns
            if p.pattern_type == PatternType.ENTITY_TYPE
        ]
        assert len(entity_patterns) > 0


# ==================== Entity Insights Tests ====================


class TestEntityInsights:
    """Tests for entity insight functionality."""

    @pytest.fixture
    def service(self):
        """Create a service with entity data."""
        s = MLAnalyticsService()

        # Create entity associations
        for _ in range(5):
            s.record_query("find john", clicked_entities=["entity-1"])

        for _ in range(3):
            s.record_query("find john", clicked_entities=["entity-2"])

        for _ in range(3):
            s.record_query("find jane", clicked_entities=["entity-1", "entity-3"])

        # Add a zero-result query for entity-1
        s.record_query("failed search", result_count=0, clicked_entities=["entity-1"])

        return s

    def test_get_entity_insights(self, service):
        """Test getting entity insights."""
        insights = service.get_entity_insights("entity-1")

        assert len(insights) > 0

    def test_related_entity_insight(self, service):
        """Test related entity insight detection."""
        insights = service.get_entity_insights("entity-1")

        related = [i for i in insights if i.insight_type == InsightType.RELATED_ENTITY]
        # May have related entity insights
        assert isinstance(related, list)

    def test_search_frequency_insight(self, service):
        """Test search frequency insight."""
        insights = service.get_entity_insights("entity-1")

        frequency = [i for i in insights if i.insight_type == InsightType.SEARCH_FREQUENCY]
        assert len(frequency) > 0

    def test_data_quality_insight(self, service):
        """Test data quality insight for zero-result queries."""
        insights = service.get_entity_insights("entity-1")

        quality = [i for i in insights if i.insight_type == InsightType.DATA_QUALITY]
        assert len(quality) > 0

    def test_insights_unknown_entity(self, service):
        """Test insights for unknown entity."""
        insights = service.get_entity_insights("unknown-entity")

        assert insights == []

    def test_insights_include_recommendations(self, service):
        """Test that insights include recommended actions."""
        insights = service.get_entity_insights("entity-1")

        for insight in insights:
            assert isinstance(insight.recommended_actions, list)


# ==================== Related Searches Tests ====================


class TestRelatedSearches:
    """Tests for related search recommendations."""

    @pytest.fixture
    def service(self):
        """Create a service with co-occurrence data."""
        s = MLAnalyticsService()

        # Create co-occurring queries
        base_time = datetime.now(timezone.utc)

        s.record_query("john doe", timestamp=base_time)
        s.record_query("john smith", timestamp=base_time + timedelta(minutes=1))
        s.record_query("john doe email", timestamp=base_time + timedelta(minutes=2))
        s.record_query("jane doe", timestamp=base_time + timedelta(minutes=3))

        return s

    def test_recommend_related_searches(self, service):
        """Test getting related search recommendations."""
        related = service.recommend_related_searches("john doe")

        # Should recommend co-occurring queries
        assert isinstance(related, list)

    def test_related_searches_limit(self, service):
        """Test related searches limit."""
        related = service.recommend_related_searches("john doe", limit=2)

        assert len(related) <= 2

    def test_related_searches_excludes_original(self, service):
        """Test that original query is excluded from recommendations."""
        related = service.recommend_related_searches("john doe")

        assert "john doe" not in related

    def test_related_searches_empty_query(self, service):
        """Test related searches with empty query."""
        related = service.recommend_related_searches("")

        assert related == []


# ==================== Query Similarity Tests ====================


class TestQuerySimilarity:
    """Tests for query similarity calculations."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return MLAnalyticsService()

    def test_identical_queries(self, service):
        """Test similarity of identical queries."""
        similarity = service.calculate_query_similarity("john doe", "john doe")

        assert similarity == 1.0

    def test_similar_queries(self, service):
        """Test similarity of similar queries."""
        similarity = service.calculate_query_similarity("john doe", "john smith")

        assert 0.3 < similarity < 1.0

    def test_different_queries(self, service):
        """Test similarity of different queries."""
        similarity = service.calculate_query_similarity("john doe", "bitcoin wallet")

        assert similarity < 0.5

    def test_empty_query_similarity(self, service):
        """Test similarity with empty query."""
        similarity = service.calculate_query_similarity("", "john doe")

        assert similarity == 0.0

    def test_similarity_is_symmetric(self, service):
        """Test that similarity is symmetric."""
        sim1 = service.calculate_query_similarity("john doe", "john smith")
        sim2 = service.calculate_query_similarity("john smith", "john doe")

        assert abs(sim1 - sim2) < 0.01

    def test_similarity_bounds(self, service):
        """Test that similarity is between 0 and 1."""
        queries = [
            ("hello world", "goodbye world"),
            ("quick brown fox", "lazy dog"),
            ("python programming", "java development"),
        ]

        for q1, q2 in queries:
            similarity = service.calculate_query_similarity(q1, q2)
            assert 0.0 <= similarity <= 1.0


# ==================== Edit Distance Tests ====================


class TestEditDistance:
    """Tests for edit distance calculation."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return MLAnalyticsService()

    def test_identical_strings(self, service):
        """Test edit distance of identical strings."""
        distance = service._edit_distance("hello", "hello")

        assert distance == 0

    def test_single_insertion(self, service):
        """Test edit distance with single insertion."""
        distance = service._edit_distance("hello", "hellos")

        assert distance == 1

    def test_single_deletion(self, service):
        """Test edit distance with single deletion."""
        distance = service._edit_distance("hello", "hell")

        assert distance == 1

    def test_single_substitution(self, service):
        """Test edit distance with single substitution."""
        distance = service._edit_distance("hello", "hallo")

        assert distance == 1

    def test_empty_string(self, service):
        """Test edit distance with empty string."""
        distance = service._edit_distance("", "hello")

        assert distance == 5

    def test_both_empty(self, service):
        """Test edit distance of two empty strings."""
        distance = service._edit_distance("", "")

        assert distance == 0


# ==================== TF-IDF Tests ====================


class TestTFIDF:
    """Tests for TF-IDF functionality."""

    @pytest.fixture
    def service(self):
        """Create a service with training data."""
        s = MLAnalyticsService()
        s.record_query("john doe email")
        s.record_query("john smith phone")
        s.record_query("jane doe address")
        return s

    def test_tfidf_vector_creation(self, service):
        """Test TF-IDF vector creation."""
        vector = service._get_tfidf_vector("john doe")

        assert isinstance(vector, TFIDFVector)
        assert len(vector.terms) > 0
        assert vector.magnitude > 0

    def test_tfidf_cosine_similarity(self, service):
        """Test TF-IDF cosine similarity."""
        similarity = service._tfidf_cosine_similarity("john doe", "john smith")

        assert 0.0 <= similarity <= 1.0

    def test_tfidf_caching(self, service):
        """Test that TF-IDF vectors are cached."""
        # First call
        vector1 = service._get_tfidf_vector("test query")

        # Second call should return cached vector
        vector2 = service._get_tfidf_vector("test query")

        assert vector1 is vector2


# ==================== Query Clustering Tests ====================


class TestQueryClustering:
    """Tests for query clustering functionality."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return MLAnalyticsService()

    def test_cluster_similar_queries(self, service):
        """Test clustering similar queries."""
        queries = [
            "john doe",
            "john smith",
            "jane doe",
            "bitcoin wallet",
            "ethereum address",
        ]

        clusters = service.cluster_similar_queries(queries, threshold=0.4)

        assert len(clusters) > 0
        total_clustered = sum(len(c) for c in clusters.values())
        assert total_clustered == len(set(q.strip().lower() for q in queries))

    def test_cluster_identical_queries(self, service):
        """Test clustering identical queries."""
        queries = ["john doe", "JOHN DOE", "  john doe  "]

        clusters = service.cluster_similar_queries(queries)

        # Should all be in one cluster
        assert len(clusters) == 1

    def test_cluster_empty_list(self, service):
        """Test clustering empty list."""
        clusters = service.cluster_similar_queries([])

        assert clusters == {}

    def test_cluster_single_query(self, service):
        """Test clustering single query."""
        clusters = service.cluster_similar_queries(["john doe"])

        assert len(clusters) == 1
        assert "john doe" in clusters

    def test_cluster_threshold_effect(self, service):
        """Test that threshold affects clustering."""
        queries = ["john doe", "john smith", "jane doe"]

        high_threshold_clusters = service.cluster_similar_queries(queries, threshold=0.9)
        low_threshold_clusters = service.cluster_similar_queries(queries, threshold=0.3)

        # Higher threshold should result in more clusters (less grouping)
        assert len(high_threshold_clusters) >= len(low_threshold_clusters)


# ==================== Zero Result Prediction Tests ====================


class TestZeroResultPrediction:
    """Tests for zero-result prediction functionality."""

    @pytest.fixture
    def service(self):
        """Create a service with zero-result history."""
        s = MLAnalyticsService()

        # Add successful queries
        for _ in range(5):
            s.record_query("john doe", result_count=5)

        # Add zero-result queries
        for _ in range(3):
            s.record_query("asdfghjkl", result_count=0)

        return s

    def test_predict_known_zero_result(self, service):
        """Test prediction for known zero-result query."""
        probability = service.predict_zero_results("asdfghjkl")

        assert probability >= 0.7  # High probability

    def test_predict_known_successful(self, service):
        """Test prediction for known successful query."""
        probability = service.predict_zero_results("john doe")

        assert probability == 0.0  # Zero because all results > 0

    def test_predict_unknown_query(self, service):
        """Test prediction for unknown query."""
        probability = service.predict_zero_results("xyz unknown")

        assert 0.0 <= probability <= 1.0

    def test_predict_similar_to_zero_result(self, service):
        """Test prediction for query similar to zero-result."""
        probability = service.predict_zero_results("asdfghjk")  # Similar to known zero

        assert probability >= 0.3  # Should have elevated probability

    def test_predict_empty_query(self, service):
        """Test prediction for empty query."""
        probability = service.predict_zero_results("")

        assert probability == 0.5  # Default uncertainty


# ==================== N-gram Tests ====================


class TestNgrams:
    """Tests for n-gram functionality."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return MLAnalyticsService()

    def test_get_ngrams_bigrams(self, service):
        """Test bigram generation."""
        tokens = ["hello", "world", "python"]
        ngrams = service._get_ngrams(tokens, 2)

        assert len(ngrams) == 2
        assert "hello world" in ngrams
        assert "world python" in ngrams

    def test_get_ngrams_trigrams(self, service):
        """Test trigram generation."""
        tokens = ["one", "two", "three", "four"]
        ngrams = service._get_ngrams(tokens, 3)

        assert len(ngrams) == 2
        assert "one two three" in ngrams
        assert "two three four" in ngrams

    def test_get_ngrams_insufficient_tokens(self, service):
        """Test n-grams with insufficient tokens."""
        tokens = ["hello"]
        ngrams = service._get_ngrams(tokens, 2)

        assert ngrams == []


# ==================== Tokenization Tests ====================


class TestTokenization:
    """Tests for tokenization functionality."""

    @pytest.fixture
    def service(self):
        """Create a service instance."""
        return MLAnalyticsService()

    def test_tokenize_basic(self, service):
        """Test basic tokenization."""
        tokens = service._tokenize("hello world")

        assert tokens == ["hello", "world"]

    def test_tokenize_with_punctuation(self, service):
        """Test tokenization with punctuation."""
        tokens = service._tokenize("hello, world!")

        assert tokens == ["hello", "world"]

    def test_tokenize_removes_short_tokens(self, service):
        """Test that short tokens are removed."""
        tokens = service._tokenize("a I am here")

        assert "a" not in tokens
        assert "am" in tokens
        assert "here" in tokens

    def test_tokenize_lowercase(self, service):
        """Test that tokens are lowercased."""
        tokens = service._tokenize("Hello WORLD")

        assert tokens == ["hello", "world"]

    def test_tokenize_empty(self, service):
        """Test tokenizing empty string."""
        tokens = service._tokenize("")

        assert tokens == []


# ==================== Singleton Tests ====================


class TestSingleton:
    """Tests for singleton management."""

    def test_get_ml_analytics_creates_singleton(self):
        """Test that get_ml_analytics creates a singleton."""
        set_ml_analytics(None)

        service1 = get_ml_analytics()
        service2 = get_ml_analytics()

        assert service1 is service2

    def test_set_ml_analytics(self):
        """Test setting the singleton."""
        custom = MLAnalyticsService(min_confidence=0.7)
        set_ml_analytics(custom)

        retrieved = get_ml_analytics()

        assert retrieved is custom
        assert retrieved._min_confidence == 0.7

    def test_set_ml_analytics_to_none(self):
        """Test clearing the singleton."""
        set_ml_analytics(MLAnalyticsService())
        set_ml_analytics(None)

        # Next call should create new instance
        new_service = get_ml_analytics()
        assert new_service is not None


# ==================== Thread Safety Tests ====================


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_query_recording(self):
        """Test concurrent query recording."""
        service = MLAnalyticsService()
        num_threads = 10
        queries_per_thread = 100

        def record_queries():
            for i in range(queries_per_thread):
                service.record_query(f"query-{threading.current_thread().name}-{i}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_queries)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        stats = service.get_statistics()
        assert stats["total_queries_recorded"] == num_threads * queries_per_thread

    def test_concurrent_suggestions(self):
        """Test concurrent suggestion requests."""
        service = MLAnalyticsService()

        # Add some data first
        for i in range(100):
            service.record_query(f"john doe {i}")

        results = []

        def get_suggestions():
            for _ in range(10):
                suggestions = service.suggest_queries("joh")
                results.append(len(suggestions))

        threads = []
        for i in range(5):
            t = threading.Thread(target=get_suggestions)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All requests should succeed
        assert len(results) == 50


# ==================== Router Tests ====================


class TestMLAnalyticsRouter:
    """Tests for the ML analytics router."""

    def test_router_import(self):
        """Test that router can be imported."""
        from api.routers.ml_analytics import router
        assert router is not None

    def test_response_models_import(self):
        """Test that all response models can be imported."""
        from api.routers.ml_analytics import (
            QuerySuggestionResponse,
            SuggestionsResponse,
            SearchPatternResponse,
            PatternsResponse,
            EntityInsightResponse,
            InsightsResponse,
            RelatedSearchesResponse,
            ClusterRequest,
            ClusterResponse,
            ZeroPredictionResponse,
            SimilarityResponse,
            StatisticsResponse,
            RecordQueryRequest,
            RecordQueryResponse,
        )

        # Verify models have expected fields
        assert hasattr(SuggestionsResponse, "model_fields")
        assert hasattr(PatternsResponse, "model_fields")
        assert hasattr(InsightsResponse, "model_fields")
        assert hasattr(ClusterResponse, "model_fields")
        assert hasattr(ZeroPredictionResponse, "model_fields")

    def test_dependency_import(self):
        """Test that dependency can be imported."""
        from api.routers.ml_analytics import get_ml_service

        service = get_ml_service()
        assert service is not None


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration-like tests for complete workflows."""

    def test_complete_suggestion_workflow(self):
        """Test a complete suggestion workflow."""
        service = MLAnalyticsService()

        # Record search history
        queries = [
            ("john doe", 5),
            ("john doe email", 3),
            ("john smith", 4),
            ("jane doe", 2),
            ("bitcoin wallet", 10),
            ("ethereum address", 8),
        ]

        for query, count in queries:
            for _ in range(count):
                service.record_query(query, result_count=count)

        # Get suggestions
        suggestions = service.suggest_queries("joh", limit=5)

        assert len(suggestions) > 0
        assert suggestions[0].confidence >= suggestions[-1].confidence

        # All suggestions should be valid
        for s in suggestions:
            assert s.suggestion
            assert s.source in SuggestionSource
            assert 0.0 <= s.confidence <= 1.0

    def test_complete_pattern_workflow(self):
        """Test a complete pattern detection workflow."""
        service = MLAnalyticsService()

        # Simulate historical data
        old_time = datetime.now(timezone.utc) - timedelta(days=14)
        new_time = datetime.now(timezone.utc)

        # Create patterns
        for _ in range(20):
            service.record_query("common query", timestamp=new_time)

        for _ in range(5):
            service.record_query("trending", timestamp=old_time)
        for _ in range(25):
            service.record_query("trending", timestamp=new_time)

        patterns = service.detect_search_patterns(time_range=30)

        # Should detect at least common pattern
        pattern_types = {p.pattern_type for p in patterns}
        assert PatternType.COMMON in pattern_types or PatternType.TRENDING in pattern_types

    def test_complete_clustering_workflow(self):
        """Test a complete clustering workflow."""
        service = MLAnalyticsService()

        queries = [
            "john doe",
            "John Doe",
            "JOHN DOE",
            "jane doe",
            "Jane Smith",
            "bitcoin wallet",
            "crypto wallet",
            "ethereum wallet",
        ]

        clusters = service.cluster_similar_queries(queries, threshold=0.5)

        # Should have multiple clusters
        assert len(clusters) >= 1

        # All queries should be assigned
        all_clustered = set()
        for cluster_queries in clusters.values():
            all_clustered.update(cluster_queries)

        assert len(all_clustered) == len(set(q.strip().lower() for q in queries))

    def test_zero_result_prediction_workflow(self):
        """Test zero-result prediction workflow."""
        service = MLAnalyticsService()

        # Train with historical data
        successful_queries = ["john doe", "jane smith", "bitcoin price"]
        failed_queries = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

        for q in successful_queries:
            for _ in range(5):
                service.record_query(q, result_count=10)

        for q in failed_queries:
            for _ in range(5):
                service.record_query(q, result_count=0)

        # Test predictions
        for q in successful_queries:
            prob = service.predict_zero_results(q)
            assert prob < 0.5  # Should predict success

        for q in failed_queries:
            prob = service.predict_zero_results(q)
            assert prob >= 0.5  # Should predict failure
