"""
Tests for the Suggestion System - Phase 43.4.

Tests suggestion generation for entities and orphans, confidence grouping,
dismissed suggestions, and performance characteristics.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from api.services.suggestion_service import (
    SuggestionService,
    ConfidenceLevel,
    SuggestionMatch,
    ConfidenceGroup,
)
from api.services.matching_engine import MatchResult, MatchingEngine
from api.models.data_item import DataItem


class TestSuggestionMatch:
    """Test SuggestionMatch dataclass."""

    def test_suggestion_match_creation(self):
        """Test creating a SuggestionMatch."""
        match = SuggestionMatch(
            data_id="data_123",
            data_type="email",
            data_value="test@example.com",
            match_type="exact_hash",
            confidence_score=1.0,
            matched_entity_id="ent_456",
            matched_entity_name="John Doe"
        )

        assert match.data_id == "data_123"
        assert match.data_type == "email"
        assert match.confidence_score == 1.0
        assert match.matched_entity_name == "John Doe"

    def test_suggestion_match_to_dict(self):
        """Test converting SuggestionMatch to dictionary."""
        match = SuggestionMatch(
            data_id="data_123",
            data_type="email",
            data_value="test@example.com",
            match_type="exact_string",
            confidence_score=0.95,
            matched_entity_id="ent_456",
            matched_entity_name="John Doe"
        )

        result = match.to_dict()

        assert result["data_id"] == "data_123"
        assert result["data_type"] == "email"
        assert result["data_value"] == "test@example.com"
        assert result["match_type"] == "exact_string"
        assert result["confidence_score"] == 0.95
        assert result["matched_entity_id"] == "ent_456"
        assert result["matched_entity_name"] == "John Doe"

    def test_suggestion_match_with_orphan(self):
        """Test SuggestionMatch with orphan ID."""
        match = SuggestionMatch(
            data_id="data_123",
            data_type="email",
            data_value="test@example.com",
            match_type="partial_string",
            confidence_score=0.75,
            matched_orphan_id="orphan_789"
        )

        result = match.to_dict()
        assert result["matched_orphan_id"] == "orphan_789"
        assert "matched_entity_id" not in result


class TestConfidenceGroup:
    """Test ConfidenceGroup dataclass."""

    def test_confidence_group_creation(self):
        """Test creating a ConfidenceGroup."""
        matches = [
            SuggestionMatch(
                data_id="data_123",
                data_type="email",
                data_value="test@example.com",
                match_type="exact_hash",
                confidence_score=1.0,
                matched_entity_id="ent_456"
            )
        ]

        group = ConfidenceGroup(
            confidence=ConfidenceLevel.HIGH,
            matches=matches
        )

        assert group.confidence == ConfidenceLevel.HIGH
        assert len(group.matches) == 1

    def test_confidence_group_to_dict(self):
        """Test converting ConfidenceGroup to dictionary."""
        matches = [
            SuggestionMatch(
                data_id="data_123",
                data_type="email",
                data_value="test@example.com",
                match_type="exact_hash",
                confidence_score=1.0,
                matched_entity_id="ent_456"
            )
        ]

        group = ConfidenceGroup(
            confidence=ConfidenceLevel.HIGH,
            matches=matches
        )

        result = group.to_dict()

        assert result["confidence"] == "HIGH"
        assert len(result["matches"]) == 1
        assert result["matches"][0]["data_id"] == "data_123"


class TestSuggestionService:
    """Test SuggestionService main functionality."""

    @pytest.fixture
    def mock_neo4j_service(self):
        """Create mock Neo4j service."""
        service = MagicMock()
        service.connect = AsyncMock()
        service.close = AsyncMock()
        service.session = MagicMock()
        return service

    @pytest.fixture
    def mock_matching_engine(self):
        """Create mock MatchingEngine."""
        engine = MagicMock(spec=MatchingEngine)
        engine.__aenter__ = AsyncMock(return_value=engine)
        engine.__aexit__ = AsyncMock()
        engine.find_all_matches = AsyncMock()
        return engine

    @pytest.fixture
    def suggestion_service(self, mock_neo4j_service, mock_matching_engine):
        """Create SuggestionService with mocks."""
        return SuggestionService(
            neo4j_service=mock_neo4j_service,
            matching_engine=mock_matching_engine
        )

    def test_classify_confidence(self, suggestion_service):
        """Test confidence classification."""
        # HIGH: >= 0.9
        assert suggestion_service._classify_confidence(1.0) == ConfidenceLevel.HIGH
        assert suggestion_service._classify_confidence(0.95) == ConfidenceLevel.HIGH
        assert suggestion_service._classify_confidence(0.9) == ConfidenceLevel.HIGH

        # MEDIUM: 0.7-0.89
        assert suggestion_service._classify_confidence(0.85) == ConfidenceLevel.MEDIUM
        assert suggestion_service._classify_confidence(0.75) == ConfidenceLevel.MEDIUM
        assert suggestion_service._classify_confidence(0.7) == ConfidenceLevel.MEDIUM

        # LOW: 0.5-0.69
        assert suggestion_service._classify_confidence(0.65) == ConfidenceLevel.LOW
        assert suggestion_service._classify_confidence(0.55) == ConfidenceLevel.LOW
        assert suggestion_service._classify_confidence(0.5) == ConfidenceLevel.LOW

    def test_group_by_confidence(self, suggestion_service):
        """Test grouping matches by confidence level."""
        matches = [
            SuggestionMatch(
                data_id="data_1",
                data_type="email",
                data_value="test1@example.com",
                match_type="exact_hash",
                confidence_score=1.0,
                matched_entity_id="ent_1"
            ),
            SuggestionMatch(
                data_id="data_2",
                data_type="phone",
                data_value="+15551234567",
                match_type="exact_string",
                confidence_score=0.95,
                matched_entity_id="ent_2"
            ),
            SuggestionMatch(
                data_id="data_3",
                data_type="name",
                data_value="John Doe",
                match_type="partial_string",
                confidence_score=0.75,
                matched_entity_id="ent_3"
            ),
            SuggestionMatch(
                data_id="data_4",
                data_type="address",
                data_value="123 Main St",
                match_type="partial_string",
                confidence_score=0.55,
                matched_entity_id="ent_4"
            )
        ]

        groups = suggestion_service._group_by_confidence(matches)

        # Should have 3 groups: HIGH, MEDIUM, LOW
        assert len(groups) == 3
        assert groups[0].confidence == ConfidenceLevel.HIGH
        assert groups[1].confidence == ConfidenceLevel.MEDIUM
        assert groups[2].confidence == ConfidenceLevel.LOW

        # Check match counts
        assert len(groups[0].matches) == 2  # 1.0, 0.95
        assert len(groups[1].matches) == 1  # 0.75
        assert len(groups[2].matches) == 1  # 0.55

    def test_group_by_confidence_empty(self, suggestion_service):
        """Test grouping with no matches."""
        groups = suggestion_service._group_by_confidence([])
        assert groups == []

    def test_group_by_confidence_single_level(self, suggestion_service):
        """Test grouping with matches in single confidence level."""
        matches = [
            SuggestionMatch(
                data_id="data_1",
                data_type="email",
                data_value="test1@example.com",
                match_type="exact_hash",
                confidence_score=1.0,
                matched_entity_id="ent_1"
            ),
            SuggestionMatch(
                data_id="data_2",
                data_type="email",
                data_value="test2@example.com",
                match_type="exact_hash",
                confidence_score=0.95,
                matched_entity_id="ent_2"
            )
        ]

        groups = suggestion_service._group_by_confidence(matches)

        # Should have only HIGH group
        assert len(groups) == 1
        assert groups[0].confidence == ConfidenceLevel.HIGH
        assert len(groups[0].matches) == 2

    @pytest.mark.asyncio
    async def test_get_entity_name(self, suggestion_service, mock_neo4j_service):
        """Test getting entity name."""
        # Mock session and result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"name": "John Doe"})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        name = await suggestion_service._get_entity_name("ent_123")
        assert name == "John Doe"

    @pytest.mark.asyncio
    async def test_get_entity_name_not_found(self, suggestion_service, mock_neo4j_service):
        """Test getting entity name for non-existent entity."""
        # Mock session and result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        name = await suggestion_service._get_entity_name("ent_nonexistent")
        assert name is None

    @pytest.mark.asyncio
    async def test_get_dismissed_suggestions(self, suggestion_service, mock_neo4j_service):
        """Test getting dismissed suggestions."""
        # Mock session and result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {"data_id": "data_123"},
            {"data_id": "data_456"}
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        dismissed = await suggestion_service._get_dismissed_suggestions("ent_789")
        assert len(dismissed) == 2
        assert "data_123" in dismissed
        assert "data_456" in dismissed

    @pytest.mark.asyncio
    async def test_get_entity_suggestions(self, suggestion_service, mock_neo4j_service, mock_matching_engine):
        """Test getting entity suggestions."""
        # Mock data service to return data items
        with patch.object(suggestion_service.data_service, 'list_data_items', AsyncMock(return_value=[
            DataItem(
                id="data_001",
                type="email",
                value="test@example.com",
                normalized_value="test@example.com",
                created_at=datetime.now(),
                entity_id="ent_123"
            )
        ])):
            # Mock matching engine to return matches
            mock_matching_engine.find_all_matches.return_value = [
                (
                    MatchResult(
                        entity_id="ent_456",
                        data_id="data_002",
                        field_type="email",
                        field_value="test@example.com",
                        confidence=0.95,
                        match_type="exact_string",
                        similarity_score=1.0
                    ),
                    0.95,
                    "exact_string"
                )
            ]

            # Mock session for entity name and dismissed suggestions
            mock_session = AsyncMock()
            mock_result1 = AsyncMock()
            mock_result1.single = AsyncMock(return_value={"name": "Jane Smith"})
            mock_result2 = AsyncMock()
            mock_result2.data = AsyncMock(return_value=[])
            mock_session.run = AsyncMock(side_effect=[mock_result2, mock_result1])
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_neo4j_service.session.return_value = mock_session

            # Get suggestions
            result = await suggestion_service.get_entity_suggestions("ent_123")

            assert result["entity_id"] == "ent_123"
            assert len(result["suggestions"]) > 0
            assert result["suggestions"][0]["confidence"] == "HIGH"
            assert len(result["suggestions"][0]["matches"]) == 1
            assert result["suggestions"][0]["matches"][0]["matched_entity_name"] == "Jane Smith"

    @pytest.mark.asyncio
    async def test_get_entity_suggestions_no_data(self, suggestion_service):
        """Test getting suggestions for entity with no data."""
        with patch.object(suggestion_service.data_service, 'list_data_items', AsyncMock(return_value=[])):
            result = await suggestion_service.get_entity_suggestions("ent_empty")

            assert result["entity_id"] == "ent_empty"
            assert result["suggestions"] == []
            assert result["dismissed_count"] == 0

    @pytest.mark.asyncio
    async def test_get_entity_suggestions_filters_self(self, suggestion_service, mock_neo4j_service, mock_matching_engine):
        """Test that entity suggestions filter out matches to self."""
        with patch.object(suggestion_service.data_service, 'list_data_items', AsyncMock(return_value=[
            DataItem(
                id="data_001",
                type="email",
                value="test@example.com",
                normalized_value="test@example.com",
                created_at=datetime.now(),
                entity_id="ent_123"
            )
        ])):
            # Mock matching engine to return match to same entity
            mock_matching_engine.find_all_matches.return_value = [
                (
                    MatchResult(
                        entity_id="ent_123",  # Same entity
                        data_id="data_001",
                        field_type="email",
                        field_value="test@example.com",
                        confidence=1.0,
                        match_type="exact_hash",
                        similarity_score=1.0
                    ),
                    1.0,
                    "exact_hash"
                )
            ]

            # Mock session for dismissed suggestions
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.data = AsyncMock(return_value=[])
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_neo4j_service.session.return_value = mock_session

            result = await suggestion_service.get_entity_suggestions("ent_123")

            # Should have no suggestions since it filtered out self-match
            assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_get_orphan_suggestions(self, suggestion_service, mock_neo4j_service, mock_matching_engine):
        """Test getting suggestions for orphan data."""
        # Mock session for orphan data query
        mock_session = AsyncMock()
        mock_result1 = AsyncMock()
        mock_result1.single = AsyncMock(return_value={
            "value": "orphan@example.com",
            "type": "email",
            "id": "orphan_123"
        })
        mock_session.run = AsyncMock(return_value=mock_result1)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        # Mock matching engine
        mock_matching_engine.find_all_matches.return_value = [
            (
                MatchResult(
                    entity_id="ent_456",
                    data_id="data_002",
                    field_type="email",
                    field_value="orphan@example.com",
                    confidence=0.95,
                    match_type="exact_string",
                    similarity_score=1.0
                ),
                0.95,
                "exact_string"
            )
        ]

        # Mock entity name query
        with patch.object(suggestion_service, '_get_entity_name', AsyncMock(return_value="John Doe")):
            result = await suggestion_service.get_orphan_suggestions("orphan_123")

            assert result["orphan_id"] == "orphan_123"
            assert len(result["suggestions"]) > 0
            assert result["suggestions"][0]["confidence"] == "HIGH"
            assert result["suggestions"][0]["matches"][0]["matched_entity_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_get_orphan_suggestions_not_found(self, suggestion_service, mock_neo4j_service):
        """Test getting suggestions for non-existent orphan."""
        # Mock session for orphan data query
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        result = await suggestion_service.get_orphan_suggestions("orphan_nonexistent")

        assert result["orphan_id"] == "orphan_nonexistent"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_dismiss_suggestion(self, suggestion_service, mock_neo4j_service):
        """Test dismissing a suggestion."""
        # Mock session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"created": 1})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        success = await suggestion_service.dismiss_suggestion("ent_123", "data_456")
        assert success is True

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_invalid(self, suggestion_service, mock_neo4j_service):
        """Test dismissing suggestion with invalid IDs."""
        # Mock session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"created": 0})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        success = await suggestion_service.dismiss_suggestion("ent_invalid", "data_invalid")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_dismissed_suggestions_list(self, suggestion_service, mock_neo4j_service):
        """Test getting list of dismissed suggestions."""
        # Mock session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "data_id": "data_123",
                "data_type": "email",
                "data_value": "test1@example.com",
                "dismissed_at": "2026-01-09T12:00:00"
            },
            {
                "data_id": "data_456",
                "data_type": "phone",
                "data_value": "+15551234567",
                "dismissed_at": "2026-01-09T13:00:00"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_service.session.return_value = mock_session

        result = await suggestion_service.get_dismissed_suggestions_list("ent_789")

        assert result["entity_id"] == "ent_789"
        assert len(result["dismissed_suggestions"]) == 2
        assert result["count"] == 2
        assert result["dismissed_suggestions"][0]["data_id"] == "data_123"


class TestSuggestionSystemPerformance:
    """Test performance characteristics of suggestion system."""

    @pytest.mark.asyncio
    async def test_suggestion_performance_100_entities(self):
        """Test suggestion generation handles 100+ entities in <1s."""
        import time

        # Mock Neo4j service
        mock_neo4j = MagicMock()
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.close = AsyncMock()

        # Mock session for data items
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j.session.return_value = mock_session

        # Mock matching engine
        mock_matching_engine = MagicMock(spec=MatchingEngine)
        mock_matching_engine.__aenter__ = AsyncMock(return_value=mock_matching_engine)
        mock_matching_engine.__aexit__ = AsyncMock()

        # Generate 100 mock matches
        mock_matches = []
        for i in range(100):
            mock_matches.append((
                MatchResult(
                    entity_id=f"ent_{i}",
                    data_id=f"data_{i}",
                    field_type="email",
                    field_value=f"user{i}@example.com",
                    confidence=0.95,
                    match_type="exact_string",
                    similarity_score=1.0
                ),
                0.95,
                "exact_string"
            ))

        mock_matching_engine.find_all_matches = AsyncMock(return_value=mock_matches)

        # Create service
        service = SuggestionService(
            neo4j_service=mock_neo4j,
            matching_engine=mock_matching_engine
        )

        # Mock data service
        with patch.object(service.data_service, 'list_data_items', AsyncMock(return_value=[
            DataItem(
                id="data_001",
                type="email",
                value="test@example.com",
                normalized_value="test@example.com",
                created_at=datetime.now(),
                entity_id="ent_test"
            )
        ])):
            # Mock dismissed suggestions
            mock_result_dismissed = AsyncMock()
            mock_result_dismissed.data = AsyncMock(return_value=[])
            mock_session.run = AsyncMock(return_value=mock_result_dismissed)

            # Mock entity names
            mock_result_name = AsyncMock()
            mock_result_name.single = AsyncMock(return_value={"name": "Test Entity"})

            # Measure time
            start_time = time.time()

            result = await service.get_entity_suggestions("ent_test")

            elapsed_time = time.time() - start_time

            # Should complete in under 1 second
            assert elapsed_time < 1.0, f"Suggestion generation took {elapsed_time:.2f}s, expected <1s"

            print(f"Generated suggestions for 100 matches in: {elapsed_time*1000:.2f}ms")


class TestSuggestionSystemIntegration:
    """Integration tests for suggestion system."""

    @pytest.mark.asyncio
    async def test_confidence_grouping_integration(self):
        """Test end-to-end confidence grouping."""
        # Mock services
        mock_neo4j = MagicMock()
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.close = AsyncMock()

        mock_matching_engine = MagicMock(spec=MatchingEngine)
        mock_matching_engine.__aenter__ = AsyncMock(return_value=mock_matching_engine)
        mock_matching_engine.__aexit__ = AsyncMock()

        # Create matches with different confidence levels
        mock_matches = [
            # HIGH confidence
            (
                MatchResult(
                    entity_id="ent_1",
                    data_id="data_1",
                    field_type="email",
                    field_value="test1@example.com",
                    confidence=1.0,
                    match_type="exact_hash",
                    similarity_score=1.0
                ),
                1.0,
                "exact_hash"
            ),
            # MEDIUM confidence
            (
                MatchResult(
                    entity_id="ent_2",
                    data_id="data_2",
                    field_type="name",
                    field_value="John Doe",
                    confidence=0.75,
                    match_type="partial_string",
                    similarity_score=0.85
                ),
                0.75,
                "partial_string"
            ),
            # LOW confidence
            (
                MatchResult(
                    entity_id="ent_3",
                    data_id="data_3",
                    field_type="address",
                    field_value="123 Main St",
                    confidence=0.55,
                    match_type="partial_string",
                    similarity_score=0.65
                ),
                0.55,
                "partial_string"
            )
        ]

        mock_matching_engine.find_all_matches = AsyncMock(return_value=mock_matches)

        service = SuggestionService(
            neo4j_service=mock_neo4j,
            matching_engine=mock_matching_engine
        )

        # Mock data service and sessions
        with patch.object(service.data_service, 'list_data_items', AsyncMock(return_value=[
            DataItem(
                id="data_001",
                type="email",
                value="test@example.com",
                normalized_value="test@example.com",
                created_at=datetime.now(),
                entity_id="ent_test"
            )
        ])):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            # Mock dismissed suggestions
            mock_result_dismissed = AsyncMock()
            mock_result_dismissed.data = AsyncMock(return_value=[])

            # Mock entity names
            mock_result_name = AsyncMock()
            mock_result_name.single = AsyncMock(return_value={"name": "Test Entity"})

            mock_session.run = AsyncMock(side_effect=[mock_result_dismissed, mock_result_name, mock_result_name, mock_result_name])
            mock_neo4j.session.return_value = mock_session

            result = await service.get_entity_suggestions("ent_test")

            # Should have 3 confidence groups
            assert len(result["suggestions"]) == 3
            assert result["suggestions"][0]["confidence"] == "HIGH"
            assert result["suggestions"][1]["confidence"] == "MEDIUM"
            assert result["suggestions"][2]["confidence"] == "LOW"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
