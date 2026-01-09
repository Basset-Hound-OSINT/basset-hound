"""
Tests for Phase 43.5: Linking Actions.

Tests the LinkingService for:
- Data item linking
- Entity merging
- Relationship creation from suggestions
- Orphan linking
- Suggestion dismissal
- Audit trail creation
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.linking_service import LinkingService, LinkingAction
from api.models.data_item import DataItem
from api.models.relationship import RelationshipType, ConfidenceLevel


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j service."""
    neo4j = AsyncMock()
    session = AsyncMock()
    neo4j.session.return_value.__aenter__.return_value = session
    neo4j.session.return_value.__aexit__.return_value = None
    return neo4j


@pytest.fixture
def linking_service(mock_neo4j):
    """Create LinkingService with mock Neo4j."""
    return LinkingService(mock_neo4j)


class TestLinkDataItems:
    """Tests for linking DataItems together."""

    @pytest.mark.asyncio
    async def test_link_data_items_success(self, linking_service, mock_neo4j):
        """Test successfully linking two data items."""
        # Mock data service to return both data items
        with patch.object(linking_service.data_service, "get_data_item") as mock_get:
            mock_get.side_effect = [
                DataItem(
                    id="data_abc123",
                    type="email",
                    value="test@example.com",
                    normalized_value="test@example.com",
                ),
                DataItem(
                    id="data_xyz789",
                    type="email",
                    value="test@example.com",
                    normalized_value="test@example.com",
                ),
            ]

            # Mock Neo4j session
            session = mock_neo4j.session.return_value.__aenter__.return_value
            session.run.return_value.single.return_value = {"r1": {}, "r2": {}}

            result = await linking_service.link_data_items(
                data_id_1="data_abc123",
                data_id_2="data_xyz789",
                reason="Same email in different contexts",
                confidence=0.9,
            )

            assert result["success"] is True
            assert "action_id" in result
            assert result["linked_data_items"] == ["data_abc123", "data_xyz789"]
            assert result["reason"] == "Same email in different contexts"
            assert result["confidence"] == 0.9

            # Verify Neo4j calls were made
            assert session.run.call_count == 2  # One for link, one for audit

    @pytest.mark.asyncio
    async def test_link_data_items_no_reason(self, linking_service):
        """Test that linking requires a reason."""
        with pytest.raises(ValueError, match="Reason is required"):
            await linking_service.link_data_items(
                data_id_1="data_abc123",
                data_id_2="data_xyz789",
                reason="",
            )

    @pytest.mark.asyncio
    async def test_link_data_items_not_found(self, linking_service):
        """Test linking fails if data item doesn't exist."""
        with patch.object(linking_service.data_service, "get_data_item") as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError, match="DataItem not found"):
                await linking_service.link_data_items(
                    data_id_1="data_abc123",
                    data_id_2="data_xyz789",
                    reason="Test",
                )

    @pytest.mark.asyncio
    async def test_link_data_items_self_link(self, linking_service):
        """Test that self-linking is prevented."""
        with patch.object(linking_service.data_service, "get_data_item") as mock_get:
            mock_get.return_value = DataItem(
                id="data_abc123",
                type="email",
                value="test@example.com",
                normalized_value="test@example.com",
            )

            with pytest.raises(ValueError, match="Cannot link a data item to itself"):
                await linking_service.link_data_items(
                    data_id_1="data_abc123",
                    data_id_2="data_abc123",
                    reason="Test",
                )


class TestMergeEntities:
    """Tests for entity merging."""

    @pytest.mark.asyncio
    async def test_merge_entities_success(self, linking_service, mock_neo4j):
        """Test successfully merging two entities."""
        session = mock_neo4j.session.return_value.__aenter__.return_value

        # Mock verification query
        session.run.return_value.single.side_effect = [
            {"id1": "ent_abc123", "id2": "ent_xyz789"},  # Verification
            {"data_moved": 5},  # Data move
            {"keep_profile": json.dumps({"core": {"name": [{"first_name": "John"}]}}),
             "discard_profile": json.dumps({"core": {"email": ["john@example.com"]}})},  # Profile merge
            None,  # Profile update
            {"relationships_moved": 3},  # Relationships
            None,  # Mark as merged
            None,  # Audit trail
        ]

        result = await linking_service.merge_entities(
            entity_id_1="ent_abc123",
            entity_id_2="ent_xyz789",
            keep_entity_id="ent_abc123",
            reason="Confirmed duplicate via manual review",
        )

        assert result["success"] is True
        assert result["kept_entity_id"] == "ent_abc123"
        assert result["merged_entity_id"] == "ent_xyz789"
        assert result["data_items_moved"] == 5
        assert result["relationships_moved"] == 3
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_merge_entities_no_reason(self, linking_service):
        """Test that merging requires a reason."""
        with pytest.raises(ValueError, match="Reason is required"):
            await linking_service.merge_entities(
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                keep_entity_id="ent_abc123",
                reason="",
            )

    @pytest.mark.asyncio
    async def test_merge_entities_invalid_keep_id(self, linking_service):
        """Test that keep_entity_id must be one of the two entities."""
        with pytest.raises(ValueError, match="keep_entity_id must be either"):
            await linking_service.merge_entities(
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                keep_entity_id="ent_invalid",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_merge_entities_not_found(self, linking_service, mock_neo4j):
        """Test merging fails if entity doesn't exist."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.return_value = None

        with pytest.raises(ValueError, match="One or both entities not found"):
            await linking_service.merge_entities(
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                keep_entity_id="ent_abc123",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_profile_merging(self, linking_service):
        """Test that profiles are merged correctly."""
        keep_profile = {
            "core": {
                "name": [{"first_name": "John", "last_name": "Doe"}],
                "email": ["john@example.com"],
            }
        }

        discard_profile = {
            "core": {
                "email": ["john.doe@example.com"],  # Additional email
                "phone": ["555-1234"],  # New field
            },
            "social": {
                "linkedin": ["linkedin.com/in/johndoe"],  # New section
            }
        }

        merged = linking_service._merge_profiles(keep_profile, discard_profile)

        # Keep profile values should be preserved
        assert merged["core"]["name"] == [{"first_name": "John", "last_name": "Doe"}]

        # Lists should be combined
        assert len(merged["core"]["email"]) == 2
        assert "john@example.com" in merged["core"]["email"]
        assert "john.doe@example.com" in merged["core"]["email"]

        # New fields should be added
        assert merged["core"]["phone"] == ["555-1234"]

        # New sections should be added
        assert "social" in merged
        assert merged["social"]["linkedin"] == ["linkedin.com/in/johndoe"]


class TestCreateRelationshipFromSuggestion:
    """Tests for creating relationships from suggestions."""

    @pytest.mark.asyncio
    async def test_create_relationship_success(self, linking_service, mock_neo4j):
        """Test successfully creating a relationship."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.side_effect = [
            {"id1": "ent_abc123", "id2": "ent_xyz789"},  # Verification
            {"r": {}},  # Relationship creation
            None,  # Audit trail
        ]

        result = await linking_service.create_relationship_from_suggestion(
            entity_id_1="ent_abc123",
            entity_id_2="ent_xyz789",
            relationship_type="WORKS_WITH",
            reason="Both listed at same company",
            confidence="high",
        )

        assert result["success"] is True
        assert result["source_entity_id"] == "ent_abc123"
        assert result["target_entity_id"] == "ent_xyz789"
        assert result["relationship_type"] == "WORKS_WITH"
        assert result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_create_symmetric_relationship(self, linking_service, mock_neo4j):
        """Test that symmetric relationships create inverse."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.side_effect = [
            {"id1": "ent_abc123", "id2": "ent_xyz789"},  # Verification
            {"r": {}},  # Relationship creation
            None,  # Inverse relationship (for symmetric)
            None,  # Audit trail
        ]

        result = await linking_service.create_relationship_from_suggestion(
            entity_id_1="ent_abc123",
            entity_id_2="ent_xyz789",
            relationship_type="WORKS_WITH",  # Symmetric
            reason="Colleagues",
        )

        assert result["is_symmetric"] is True
        # Should have created inverse relationship
        assert session.run.call_count == 4  # Verify + create + inverse + audit

    @pytest.mark.asyncio
    async def test_create_relationship_no_reason(self, linking_service):
        """Test that creating relationship requires a reason."""
        with pytest.raises(ValueError, match="Reason is required"):
            await linking_service.create_relationship_from_suggestion(
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                relationship_type="WORKS_WITH",
                reason="",
            )

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_type(self, linking_service):
        """Test that invalid relationship type is rejected."""
        with pytest.raises(ValueError, match="Invalid relationship type"):
            await linking_service.create_relationship_from_suggestion(
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                relationship_type="INVALID_TYPE",
                reason="Test",
            )


class TestLinkOrphanToEntity:
    """Tests for linking orphans to entities."""

    @pytest.mark.asyncio
    async def test_link_orphan_success(self, linking_service, mock_neo4j):
        """Test successfully linking orphan to entity."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.side_effect = [
            {"orphan_id": "orphan_abc123", "entity_id": "ent_xyz789"},  # Verification
            {"data_moved": 3},  # Data move
            None,  # Mark as resolved
            None,  # Audit trail
        ]

        result = await linking_service.link_orphan_to_entity(
            orphan_id="orphan_abc123",
            entity_id="ent_xyz789",
            reason="Orphan email matches entity email",
        )

        assert result["success"] is True
        assert result["orphan_id"] == "orphan_abc123"
        assert result["entity_id"] == "ent_xyz789"
        assert result["data_items_moved"] == 3

    @pytest.mark.asyncio
    async def test_link_orphan_no_reason(self, linking_service):
        """Test that linking orphan requires a reason."""
        with pytest.raises(ValueError, match="Reason is required"):
            await linking_service.link_orphan_to_entity(
                orphan_id="orphan_abc123",
                entity_id="ent_xyz789",
                reason="",
            )

    @pytest.mark.asyncio
    async def test_link_orphan_not_found(self, linking_service, mock_neo4j):
        """Test linking fails if orphan or entity doesn't exist."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.return_value = None

        with pytest.raises(ValueError, match="Orphan or entity not found"):
            await linking_service.link_orphan_to_entity(
                orphan_id="orphan_abc123",
                entity_id="ent_xyz789",
                reason="Test",
            )


class TestDismissSuggestion:
    """Tests for dismissing suggestions."""

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_success(self, linking_service, mock_neo4j):
        """Test successfully dismissing a suggestion."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.side_effect = [
            {"entity_id": "ent_abc123", "data_id": "data_xyz789"},  # Verification
            {"r": {}},  # Dismissal creation
            None,  # Audit trail
        ]

        result = await linking_service.dismiss_suggestion(
            entity_id="ent_abc123",
            data_id="data_xyz789",
            reason="Different person with same name",
        )

        assert result["success"] is True
        assert result["entity_id"] == "ent_abc123"
        assert result["data_id"] == "data_xyz789"
        assert result["reason"] == "Different person with same name"
        assert "dismissed_at" in result

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_no_reason(self, linking_service):
        """Test that dismissing requires a reason."""
        with pytest.raises(ValueError, match="Reason is required"):
            await linking_service.dismiss_suggestion(
                entity_id="ent_abc123",
                data_id="data_xyz789",
                reason="",
            )

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_not_found(self, linking_service, mock_neo4j):
        """Test dismissal fails if entity or data doesn't exist."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.single.return_value = None

        with pytest.raises(ValueError, match="Entity or data item not found"):
            await linking_service.dismiss_suggestion(
                entity_id="ent_abc123",
                data_id="data_xyz789",
                reason="Test",
            )


class TestAuditTrail:
    """Tests for audit trail functionality."""

    @pytest.mark.asyncio
    async def test_audit_trail_created(self, linking_service, mock_neo4j):
        """Test that audit trail is created for actions."""
        session = mock_neo4j.session.return_value.__aenter__.return_value

        await linking_service._create_audit_trail(
            action_id="test_action_123",
            action_type="test_action",
            created_by="test_user",
            reason="Test reason",
            details={"key": "value"},
            confidence=0.8,
        )

        # Verify Neo4j create call
        session.run.assert_called_once()
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "LinkingAction" in query
        assert call_args[1]["action_id"] == "test_action_123"
        assert call_args[1]["action_type"] == "test_action"
        assert call_args[1]["reason"] == "Test reason"

    @pytest.mark.asyncio
    async def test_get_linking_history(self, linking_service, mock_neo4j):
        """Test retrieving linking history."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.data.return_value = [
            {
                "a": {
                    "action_id": "action_1",
                    "action_type": "link_data_items",
                    "created_at": "2026-01-09T10:00:00",
                    "created_by": "user1",
                    "reason": "Test reason",
                    "details": json.dumps({"key": "value"}),
                    "confidence": 0.8,
                }
            }
        ]

        history = await linking_service.get_linking_history(limit=50)

        assert len(history) == 1
        assert history[0]["action_id"] == "action_1"
        assert history[0]["action_type"] == "link_data_items"
        assert history[0]["details"]["key"] == "value"  # JSON parsed

    @pytest.mark.asyncio
    async def test_get_linking_history_filtered(self, linking_service, mock_neo4j):
        """Test retrieving filtered linking history."""
        session = mock_neo4j.session.return_value.__aenter__.return_value
        session.run.return_value.data.return_value = []

        history = await linking_service.get_linking_history(
            entity_id="ent_abc123",
            action_type="merge_entities",
            limit=20,
        )

        # Verify query includes filters
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "WHERE" in query
        assert call_args[1]["entity_id"] == "ent_abc123"
        assert call_args[1]["action_type"] == "merge_entities"
        assert call_args[1]["limit"] == 20


class TestHelperMethods:
    """Tests for helper methods."""

    def test_merge_lists(self, linking_service):
        """Test list merging removes duplicates."""
        list1 = ["a", "b", "c"]
        list2 = ["b", "c", "d"]

        merged = linking_service._merge_lists(list1, list2)

        assert len(merged) == 4
        assert merged == ["a", "b", "c", "d"]

    def test_merge_lists_with_dicts(self, linking_service):
        """Test list merging with dict objects."""
        list1 = [{"name": "John"}, {"name": "Jane"}]
        list2 = [{"name": "John"}, {"name": "Bob"}]

        merged = linking_service._merge_lists(list1, list2)

        assert len(merged) == 3
        # Should have John, Jane, Bob (John not duplicated)


class TestLinkingAction:
    """Tests for LinkingAction model."""

    def test_linking_action_to_dict(self):
        """Test LinkingAction serialization."""
        action = LinkingAction(
            action_id="test_123",
            action_type="link_data_items",
            created_at=datetime(2026, 1, 9, 10, 0, 0),
            created_by="test_user",
            reason="Test reason",
            details={"key": "value"},
            confidence=0.8,
        )

        result = action.to_dict()

        assert result["action_id"] == "test_123"
        assert result["action_type"] == "link_data_items"
        assert result["created_at"] == "2026-01-09T10:00:00"
        assert result["created_by"] == "test_user"
        assert result["reason"] == "Test reason"
        assert result["details"] == {"key": "value"}
        assert result["confidence"] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
