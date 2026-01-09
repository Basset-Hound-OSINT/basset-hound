"""
Tests for the Matching Engine service.

Tests exact hash matching, exact string matching, partial matching,
confidence scoring, Unicode handling, and special characters.

Phase 43.3: Smart Suggestions & Data Matching System
"""

import asyncio
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.matching_engine import (
    MatchingEngine,
    MatchResult,
    StringNormalizer,
)


class TestStringNormalizer:
    """Test StringNormalizer utility class."""

    def test_normalize_email(self):
        """Test email normalization."""
        normalizer = StringNormalizer()

        # Basic normalization
        assert normalizer.normalize_email("User@EXAMPLE.COM") == "user@example.com"
        assert normalizer.normalize_email("  test@test.com  ") == "test@test.com"

        # Plus-addressing preserved
        assert normalizer.normalize_email("user+tag@example.com") == "user+tag@example.com"

        # Empty cases
        assert normalizer.normalize_email("") == ""
        assert normalizer.normalize_email(None) == ""

    def test_normalize_phone_basic(self):
        """Test basic phone normalization without libphonenumber."""
        normalizer = StringNormalizer()

        # Without libphonenumber, should strip non-digits and add +
        result = normalizer.normalize_phone_e164("(555) 123-4567")
        assert result == "+5551234567" or result == "5551234567"

        result = normalizer.normalize_phone_e164("555-123-4567")
        assert "5551234567" in result

    def test_normalize_address(self):
        """Test address normalization."""
        normalizer = StringNormalizer()

        # Basic normalization
        result = normalizer.normalize_address("123 Main Street, Apt 4B")
        assert "123" in result
        assert "main" in result
        assert "st" in result or "street" in result

        # Abbreviation expansion
        result = normalizer.normalize_address("456 Oak Avenue")
        assert "oak" in result
        assert "ave" in result or "avenue" in result

        # Punctuation removal
        result = normalizer.normalize_address("789 Elm St., Suite #100")
        assert "elm" in result
        assert "#" not in result

        # Unicode handling
        result = normalizer.normalize_address("Café Street 123")
        assert "cafe" in result

    def test_normalize_name(self):
        """Test name normalization."""
        normalizer = StringNormalizer()

        # Basic normalization
        assert normalizer.normalize_name("John Doe") == "john doe"
        assert normalizer.normalize_name("JANE SMITH") == "jane smith"

        # Middle initial removal
        assert normalizer.normalize_name("John A. Doe") == "john doe"
        assert normalizer.normalize_name("John A Doe") == "john doe"

        # Diacritic removal
        result = normalizer.normalize_name("José García")
        assert result == "jose garcia"

        # Special characters
        result = normalizer.normalize_name("O'Brien")
        assert "brien" in result

        # Hyphens preserved
        result = normalizer.normalize_name("Mary-Jane Watson")
        assert "mary-jane" in result or "mary jane" in result

    def test_calculate_hash(self):
        """Test hash calculation."""
        normalizer = StringNormalizer()

        # Known hash
        hash1 = normalizer.calculate_hash("test")
        expected = hashlib.sha256("test".encode('utf-8')).hexdigest()
        assert hash1 == expected

        # Same input = same hash
        hash2 = normalizer.calculate_hash("test")
        assert hash1 == hash2

        # Different input = different hash
        hash3 = normalizer.calculate_hash("test2")
        assert hash1 != hash3

        # Empty input
        assert normalizer.calculate_hash("") == ""
        assert normalizer.calculate_hash(None) == ""


class TestMatchingEngine:
    """Test MatchingEngine main functionality."""

    @pytest.fixture
    def mock_neo4j_service(self):
        """Create mock Neo4j service."""
        service = MagicMock()
        service.connect = AsyncMock()
        service.close = AsyncMock()
        service._driver = MagicMock()
        return service

    @pytest.fixture
    def matching_engine(self, mock_neo4j_service):
        """Create MatchingEngine with mock Neo4j."""
        return MatchingEngine(neo4j_service=mock_neo4j_service)

    @pytest.mark.asyncio
    async def test_find_exact_hash_matches(self, matching_engine, mock_neo4j_service):
        """Test exact hash matching."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-123",
                "data_id": "data-456",
                "field_type": "file.document",
                "field_value": {"hash": "abc123", "filename": "test.pdf"}
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test hash matching
        matches = await matching_engine.find_exact_hash_matches("abc123")

        assert len(matches) == 1
        assert matches[0].entity_id == "entity-123"
        assert matches[0].confidence == 1.0
        assert matches[0].match_type == "exact_hash"

    @pytest.mark.asyncio
    async def test_find_exact_string_matches_email(self, matching_engine, mock_neo4j_service):
        """Test exact string matching for emails."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-456",
                "data_id": "data-789",
                "field_type": "email",
                "field_value": "test@example.com",
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test exact matching
        matches = await matching_engine.find_exact_string_matches(
            "test@example.com",
            "email"
        )

        assert len(matches) == 1
        assert matches[0].entity_id == "entity-456"
        assert matches[0].confidence == 0.95
        assert matches[0].match_type == "exact_string"

    @pytest.mark.asyncio
    async def test_find_partial_matches_names(self, matching_engine, mock_neo4j_service):
        """Test partial matching for names."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-001",
                "data_id": "data-001",
                "field_type": "name",
                "field_value": "John Doe",
                "source": "entity"
            },
            {
                "entity_id": "entity-002",
                "data_id": "data-002",
                "field_type": "name",
                "field_value": "Jon Doe",
                "source": "entity"
            },
            {
                "entity_id": "entity-003",
                "data_id": "data-003",
                "field_type": "name",
                "field_value": "Jane Smith",
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test partial matching
        matches = await matching_engine.find_partial_matches(
            "John Doe",
            "name",
            threshold=0.7
        )

        # Should match "John Doe" and "Jon Doe" but not "Jane Smith"
        assert len(matches) >= 1

        # First match should be highest similarity
        assert matches[0][1] >= 0.7

        # Check match types
        for match, similarity in matches:
            assert match.match_type == "partial_string"
            assert 0.5 <= match.confidence <= 0.9

    @pytest.mark.asyncio
    async def test_find_partial_matches_addresses(self, matching_engine, mock_neo4j_service):
        """Test partial matching for addresses."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-101",
                "data_id": "data-101",
                "field_type": "address",
                "field_value": "123 Main Street, Apt 4B",
                "source": "entity"
            },
            {
                "entity_id": "entity-102",
                "data_id": "data-102",
                "field_type": "address",
                "field_value": "123 Main St #4B",
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test partial matching with token-based comparison
        matches = await matching_engine.find_partial_matches(
            "123 Main Street Apt 4B",
            "address",
            threshold=0.7
        )

        assert len(matches) >= 1

        # Both addresses should match with high similarity
        for match, similarity in matches:
            assert similarity >= 0.7
            assert match.match_type == "partial_string"

    def test_confidence_scoring(self, matching_engine):
        """Test confidence score calculation."""
        # Test different similarity ranges
        assert matching_engine._calculate_confidence(0.95) == 0.9
        assert matching_engine._calculate_confidence(0.90) == 0.9

        # 0.85 should be between 0.7 and 0.9
        conf_85 = matching_engine._calculate_confidence(0.85)
        assert 0.7 <= conf_85 <= 0.9

        # 0.75 should be between 0.5 and 0.7
        conf_75 = matching_engine._calculate_confidence(0.75)
        assert 0.5 <= conf_75 <= 0.7

        # 0.70 should be exactly 0.5
        assert matching_engine._calculate_confidence(0.70) == 0.5

    @pytest.mark.asyncio
    async def test_find_all_matches(self, matching_engine, mock_neo4j_service):
        """Test finding all matches for a value."""
        # Mock Neo4j responses for both exact and partial matching
        mock_session = AsyncMock()

        # First call: exact matches
        mock_result1 = AsyncMock()
        mock_result1.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-200",
                "data_id": "data-200",
                "field_type": "email",
                "field_value": "test@example.com",
                "source": "entity"
            }
        ])

        # Second call: partial matches
        mock_result2 = AsyncMock()
        mock_result2.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-201",
                "data_id": "data-201",
                "field_type": "email",
                "field_value": "test@example.org",
                "source": "entity"
            }
        ])

        # Set up session to return different results per call
        mock_session.run = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test finding all matches
        matches = await matching_engine.find_all_matches(
            "test@example.com",
            "email",
            include_partial=True
        )

        # Should have at least exact match
        assert len(matches) >= 1

        # First match should have highest confidence
        if len(matches) > 1:
            assert matches[0][1] >= matches[1][1]

    @pytest.mark.asyncio
    async def test_unicode_handling(self, matching_engine, mock_neo4j_service):
        """Test matching with Unicode characters."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-300",
                "data_id": "data-300",
                "field_type": "name",
                "field_value": "José García",
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test matching with and without diacritics
        matches = await matching_engine.find_partial_matches(
            "Jose Garcia",
            "name",
            threshold=0.7
        )

        # Should match despite different diacritics
        assert len(matches) >= 1

    @pytest.mark.asyncio
    async def test_special_characters(self, matching_engine, mock_neo4j_service):
        """Test matching with special characters."""
        # Mock Neo4j response
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-400",
                "data_id": "data-400",
                "field_type": "name",
                "field_value": "O'Brien",
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test matching with special characters
        matches = await matching_engine.find_partial_matches(
            "OBrien",
            "name",
            threshold=0.7
        )

        # Should match despite different punctuation
        assert len(matches) >= 1

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, matching_engine):
        """Test handling of empty inputs."""
        # Empty hash
        matches = await matching_engine.find_exact_hash_matches("")
        assert matches == []

        # Empty string match
        matches = await matching_engine.find_exact_string_matches("", "email")
        assert matches == []

        # Empty partial match
        matches = await matching_engine.find_partial_matches("", "name")
        assert matches == []

    @pytest.mark.asyncio
    async def test_threshold_filtering(self, matching_engine, mock_neo4j_service):
        """Test that threshold properly filters results."""
        # Mock Neo4j response with varying similarity matches
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "entity_id": "entity-501",
                "data_id": "data-501",
                "field_type": "name",
                "field_value": "John Doe",
                "source": "entity"
            },
            {
                "entity_id": "entity-502",
                "data_id": "data-502",
                "field_type": "name",
                "field_value": "Jane Smith",  # Very different
                "source": "entity"
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        # Test with high threshold - should filter out dissimilar matches
        matches = await matching_engine.find_partial_matches(
            "John Doe",
            "name",
            threshold=0.9
        )

        # Should only match very similar names
        for match, similarity in matches:
            assert similarity >= 0.9

    def test_match_result_to_dict(self):
        """Test MatchResult serialization."""
        match = MatchResult(
            entity_id="entity-123",
            data_id="data-456",
            field_type="email",
            field_value="test@example.com",
            confidence=0.95,
            match_type="exact_string",
            similarity_score=1.0
        )

        result = match.to_dict()

        assert result["entity_id"] == "entity-123"
        assert result["data_id"] == "data-456"
        assert result["field_type"] == "email"
        assert result["field_value"] == "test@example.com"
        assert result["confidence"] == 0.95
        assert result["match_type"] == "exact_string"
        assert result["similarity_score"] == 1.0


class TestMatchingEnginePerformance:
    """Test performance characteristics of matching engine."""

    @pytest.mark.asyncio
    async def test_batch_matching_performance(self, mock_neo4j_service=None):
        """Test matching performance with 100 items."""
        import time

        if mock_neo4j_service is None:
            mock_neo4j_service = MagicMock()
            mock_neo4j_service.connect = AsyncMock()
            mock_neo4j_service.close = AsyncMock()
            mock_neo4j_service._driver = MagicMock()

        # Mock response with 100 items
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Generate 100 mock data items
        mock_data = []
        for i in range(100):
            mock_data.append({
                "entity_id": f"entity-{i}",
                "data_id": f"data-{i}",
                "field_type": "email",
                "field_value": f"user{i}@example.com",
                "source": "entity"
            })

        mock_result.data = AsyncMock(return_value=mock_data)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_neo4j_service._driver.session.return_value.__aenter__.return_value = mock_session

        matching_engine = MatchingEngine(neo4j_service=mock_neo4j_service)

        # Measure time to find matches
        start_time = time.time()

        matches = await matching_engine.find_exact_string_matches(
            "test@example.com",
            "email"
        )

        elapsed_time = time.time() - start_time

        # Should complete in under 500ms for 100 items
        assert elapsed_time < 0.5, f"Matching took {elapsed_time*1000:.2f}ms, expected <500ms"

        print(f"Matching 100 items took: {elapsed_time*1000:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
