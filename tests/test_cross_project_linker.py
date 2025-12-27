"""
Tests for cross-project entity linking service.

These tests cover cross-project linking functionality:
- Creating and removing cross-project links
- Finding potential matches based on shared identifiers
- Getting all linked entities across projects
- Edge cases and error handling
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


def get_test_client(mock_handler):
    """Create a test client with mocked dependencies."""
    from api.main import app
    from api.dependencies import get_neo4j_handler

    app.dependency_overrides[get_neo4j_handler] = lambda: mock_handler
    return TestClient(app)


class TestCrossProjectLinkDataclass:
    """Tests for the CrossProjectLink dataclass."""

    def test_cross_project_link_creation(self):
        """Test creating a CrossProjectLink instance."""
        from api.services.cross_project_linker import CrossProjectLink

        link = CrossProjectLink(
            source_project_id="project_alpha",
            source_entity_id="entity-123",
            target_project_id="project_beta",
            target_entity_id="entity-456",
            link_type="SAME_PERSON",
            confidence=0.95,
            metadata={"notes": "Matched via email"}
        )

        assert link.source_project_id == "project_alpha"
        assert link.source_entity_id == "entity-123"
        assert link.target_project_id == "project_beta"
        assert link.target_entity_id == "entity-456"
        assert link.link_type == "SAME_PERSON"
        assert link.confidence == 0.95
        assert link.metadata == {"notes": "Matched via email"}
        assert isinstance(link.created_at, datetime)

    def test_cross_project_link_to_dict(self):
        """Test converting CrossProjectLink to dictionary."""
        from api.services.cross_project_linker import CrossProjectLink

        created_time = datetime(2024, 1, 15, 10, 30, 0)
        link = CrossProjectLink(
            source_project_id="project_alpha",
            source_entity_id="entity-123",
            target_project_id="project_beta",
            target_entity_id="entity-456",
            link_type="RELATED",
            confidence=0.8,
            created_at=created_time,
            metadata={"reason": "shared phone"}
        )

        result = link.to_dict()

        assert isinstance(result, dict)
        assert result["source_project_id"] == "project_alpha"
        assert result["source_entity_id"] == "entity-123"
        assert result["target_project_id"] == "project_beta"
        assert result["target_entity_id"] == "entity-456"
        assert result["link_type"] == "RELATED"
        assert result["confidence"] == 0.8
        assert result["created_at"] == "2024-01-15T10:30:00"
        assert result["metadata"] == {"reason": "shared phone"}

    def test_cross_project_link_from_dict(self):
        """Test creating CrossProjectLink from dictionary."""
        from api.services.cross_project_linker import CrossProjectLink

        data = {
            "source_project_id": "project_alpha",
            "source_entity_id": "entity-123",
            "target_project_id": "project_beta",
            "target_entity_id": "entity-456",
            "link_type": "ALIAS",
            "confidence": 0.9,
            "created_at": "2024-01-15T10:30:00",
            "metadata": {"alias_type": "username"}
        }

        link = CrossProjectLink.from_dict(data)

        assert link.source_project_id == "project_alpha"
        assert link.source_entity_id == "entity-123"
        assert link.link_type == "ALIAS"
        assert link.confidence == 0.9
        assert link.metadata == {"alias_type": "username"}

    def test_cross_project_link_default_values(self):
        """Test default values for CrossProjectLink."""
        from api.services.cross_project_linker import CrossProjectLink

        link = CrossProjectLink(
            source_project_id="p1",
            source_entity_id="e1",
            target_project_id="p2",
            target_entity_id="e2",
            link_type="RELATED"
        )

        assert link.confidence == 1.0
        assert link.metadata == {}
        assert isinstance(link.created_at, datetime)


class TestCrossProjectLinkerService:
    """Tests for the CrossProjectLinker service class."""

    @pytest.fixture
    def async_mock_neo4j_handler(self):
        """Create an async mock Neo4j handler."""
        handler = MagicMock()

        # Setup async mocks
        handler.get_person = AsyncMock()
        handler.get_all_people = AsyncMock()
        handler.get_all_projects = AsyncMock()
        handler.session = MagicMock()

        # Default return values
        handler.get_person.return_value = {
            "id": "entity-123",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                }
            }
        }

        handler.get_all_projects.return_value = [
            {"safe_name": "project_alpha", "name": "Project Alpha"},
            {"safe_name": "project_beta", "name": "Project Beta"},
            {"safe_name": "project_gamma", "name": "Project Gamma"}
        ]

        return handler

    @pytest.fixture
    def cross_project_linker(self, async_mock_neo4j_handler):
        """Create a CrossProjectLinker instance with mock handler."""
        from api.services.cross_project_linker import CrossProjectLinker
        linker = CrossProjectLinker(async_mock_neo4j_handler)
        return linker

    def test_valid_link_types(self, cross_project_linker):
        """Test that valid link types are properly defined."""
        valid_types = cross_project_linker.VALID_LINK_TYPES

        assert "SAME_PERSON" in valid_types
        assert "RELATED" in valid_types
        assert "ALIAS" in valid_types
        assert "ASSOCIATE" in valid_types
        assert "FAMILY" in valid_types
        assert "ORGANIZATION" in valid_types

    def test_normalize_email(self, cross_project_linker):
        """Test email normalization."""
        assert cross_project_linker._normalize_value("John.Doe@Example.COM", "email") == "john.doe@example.com"
        assert cross_project_linker._normalize_value("  TEST@test.com  ", "email") == "test@test.com"

    def test_normalize_phone(self, cross_project_linker):
        """Test phone number normalization."""
        assert cross_project_linker._normalize_value("+1 (555) 123-4567", "phone") == "+15551234567"
        assert cross_project_linker._normalize_value("555.123.4567", "phone") == "5551234567"

    def test_normalize_empty_values(self, cross_project_linker):
        """Test normalization of empty values."""
        assert cross_project_linker._normalize_value(None, "string") is None
        assert cross_project_linker._normalize_value("", "string") is None
        assert cross_project_linker._normalize_value("   ", "string") is None

    def test_normalize_complex_values(self, cross_project_linker):
        """Test that complex values (dict, list) return None."""
        assert cross_project_linker._normalize_value({"key": "value"}, "string") is None
        assert cross_project_linker._normalize_value(["a", "b"], "string") is None

    def test_extract_identifiers(self, cross_project_linker):
        """Test identifier extraction from entity profiles."""
        # Setup identifier paths
        cross_project_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True},
            {"path": "social.twitter.handle", "section_id": "social",
             "field_id": "twitter", "component_id": "handle", "field_type": "string", "multiple": True}
        ]

        entity = {
            "id": "entity-1",
            "profile": {
                "core": {
                    "email": ["john@example.com", "john.doe@work.com"]
                },
                "social": {
                    "twitter": [{"handle": "@johndoe"}]
                }
            }
        }

        identifiers = cross_project_linker._extract_identifiers(entity)

        assert "core.email" in identifiers
        assert len(identifiers["core.email"]) == 2
        assert "john@example.com" in identifiers["core.email"]

    @pytest.mark.asyncio
    async def test_link_entities_success(self, cross_project_linker, async_mock_neo4j_handler):
        """Test successful entity linking."""
        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        # Setup get_person to return different entities
        async_mock_neo4j_handler.get_person.side_effect = [
            {"id": "entity-123", "profile": {}},  # source
            {"id": "entity-456", "profile": {}}   # target
        ]

        link = await cross_project_linker.link_entities(
            source_project="project_alpha",
            source_entity="entity-123",
            target_project="project_beta",
            target_entity="entity-456",
            link_type="SAME_PERSON",
            confidence=0.95,
            metadata={"notes": "matched via email"}
        )

        assert link.source_project_id == "project_alpha"
        assert link.source_entity_id == "entity-123"
        assert link.target_project_id == "project_beta"
        assert link.target_entity_id == "entity-456"
        assert link.link_type == "SAME_PERSON"
        assert link.confidence == 0.95

    @pytest.mark.asyncio
    async def test_link_entities_invalid_type(self, cross_project_linker, async_mock_neo4j_handler):
        """Test linking with invalid link type raises error."""
        with pytest.raises(ValueError, match="Invalid link type"):
            await cross_project_linker.link_entities(
                source_project="project_alpha",
                source_entity="entity-123",
                target_project="project_beta",
                target_entity="entity-456",
                link_type="INVALID_TYPE"
            )

    @pytest.mark.asyncio
    async def test_link_entities_self_linking(self, cross_project_linker, async_mock_neo4j_handler):
        """Test that self-linking raises error."""
        async_mock_neo4j_handler.get_person.return_value = {"id": "entity-123", "profile": {}}

        with pytest.raises(ValueError, match="Cannot link an entity to itself"):
            await cross_project_linker.link_entities(
                source_project="project_alpha",
                source_entity="entity-123",
                target_project="project_alpha",
                target_entity="entity-123",
                link_type="SAME_PERSON"
            )

    @pytest.mark.asyncio
    async def test_link_entities_source_not_found(self, cross_project_linker, async_mock_neo4j_handler):
        """Test linking when source entity doesn't exist."""
        async_mock_neo4j_handler.get_person.return_value = None

        with pytest.raises(ValueError, match="Source entity.*not found"):
            await cross_project_linker.link_entities(
                source_project="project_alpha",
                source_entity="nonexistent",
                target_project="project_beta",
                target_entity="entity-456",
                link_type="RELATED"
            )

    @pytest.mark.asyncio
    async def test_link_entities_target_not_found(self, cross_project_linker, async_mock_neo4j_handler):
        """Test linking when target entity doesn't exist."""
        async_mock_neo4j_handler.get_person.side_effect = [
            {"id": "entity-123", "profile": {}},  # source exists
            None  # target doesn't exist
        ]

        with pytest.raises(ValueError, match="Target entity.*not found"):
            await cross_project_linker.link_entities(
                source_project="project_alpha",
                source_entity="entity-123",
                target_project="project_beta",
                target_entity="nonexistent",
                link_type="RELATED"
            )

    @pytest.mark.asyncio
    async def test_link_entities_confidence_clamped(self, cross_project_linker, async_mock_neo4j_handler):
        """Test that confidence is clamped to 0.0-1.0 range."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        async_mock_neo4j_handler.get_person.side_effect = [
            {"id": "entity-123", "profile": {}},
            {"id": "entity-456", "profile": {}}
        ]

        # Test confidence > 1.0
        link = await cross_project_linker.link_entities(
            source_project="project_alpha",
            source_entity="entity-123",
            target_project="project_beta",
            target_entity="entity-456",
            link_type="RELATED",
            confidence=1.5
        )
        assert link.confidence == 1.0

        # Reset for negative test
        async_mock_neo4j_handler.get_person.side_effect = [
            {"id": "entity-123", "profile": {}},
            {"id": "entity-456", "profile": {}}
        ]

        # Test confidence < 0.0
        link = await cross_project_linker.link_entities(
            source_project="project_alpha",
            source_entity="entity-123",
            target_project="project_beta",
            target_entity="entity-456",
            link_type="RELATED",
            confidence=-0.5
        )
        assert link.confidence == 0.0

    @pytest.mark.asyncio
    async def test_unlink_entities_success(self, cross_project_linker, async_mock_neo4j_handler):
        """Test successful entity unlinking."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted_count": 1})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        result = await cross_project_linker.unlink_entities(
            source_project="project_alpha",
            source_entity="entity-123",
            target_project="project_beta",
            target_entity="entity-456"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_unlink_entities_not_found(self, cross_project_linker, async_mock_neo4j_handler):
        """Test unlinking when link doesn't exist."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted_count": 0})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        result = await cross_project_linker.unlink_entities(
            source_project="project_alpha",
            source_entity="entity-123",
            target_project="project_beta",
            target_entity="entity-999"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cross_project_links(self, cross_project_linker, async_mock_neo4j_handler):
        """Test getting cross-project links for an entity."""
        mock_session = AsyncMock()

        # Mock outgoing links result
        outgoing_result = AsyncMock()
        outgoing_result.data = AsyncMock(return_value=[
            {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "SAME_PERSON",
                "confidence": 0.95,
                "created_at": "2024-01-15T10:30:00",
                "metadata": "{}"
            }
        ])

        # Mock incoming links result
        incoming_result = AsyncMock()
        incoming_result.data = AsyncMock(return_value=[
            {
                "source_project_id": "project_gamma",
                "source_entity_id": "entity-789",
                "target_project_id": "project_alpha",
                "target_entity_id": "entity-123",
                "link_type": "RELATED",
                "confidence": 0.7,
                "created_at": "2024-01-16T14:00:00",
                "metadata": "{}"
            }
        ])

        mock_session.run = AsyncMock(side_effect=[outgoing_result, incoming_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        links = await cross_project_linker.get_cross_project_links(
            project_id="project_alpha",
            entity_id="entity-123"
        )

        assert len(links) == 2
        assert links[0].link_type == "SAME_PERSON"
        assert links[1].link_type == "RELATED"

    @pytest.mark.asyncio
    async def test_find_potential_matches(self, cross_project_linker, async_mock_neo4j_handler):
        """Test finding potential matches across projects."""
        # Setup identifier paths
        cross_project_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        # Source entity
        source_entity = {
            "id": "entity-123",
            "profile": {
                "core": {"email": ["shared@example.com"]}
            }
        }

        # Target entities in different projects
        target_entities = [
            {
                "id": "entity-alpha-1",
                "profile": {"core": {"email": ["other@example.com"]}}
            },
            {
                "id": "entity-alpha-2",
                "profile": {"core": {"email": ["shared@example.com"]}}  # Match!
            }
        ]

        async_mock_neo4j_handler.get_person.return_value = source_entity
        async_mock_neo4j_handler.get_all_people.return_value = target_entities

        matches = await cross_project_linker.find_potential_matches(
            project_id="project_source",
            entity_id="entity-123",
            target_projects=["project_alpha"]
        )

        assert len(matches) == 1
        assert matches[0].target_entity_id == "entity-alpha-2"
        assert "matching_identifiers" in matches[0].metadata

    @pytest.mark.asyncio
    async def test_find_potential_matches_no_identifiers(self, cross_project_linker, async_mock_neo4j_handler):
        """Test finding matches when entity has no identifiers."""
        cross_project_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        # Source entity with no identifiers
        source_entity = {
            "id": "entity-123",
            "profile": {"core": {"name": "John Doe"}}  # No email
        }

        async_mock_neo4j_handler.get_person.return_value = source_entity

        matches = await cross_project_linker.find_potential_matches(
            project_id="project_source",
            entity_id="entity-123"
        )

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_find_potential_matches_entity_not_found(self, cross_project_linker, async_mock_neo4j_handler):
        """Test finding matches when source entity doesn't exist."""
        async_mock_neo4j_handler.get_person.return_value = None

        matches = await cross_project_linker.find_potential_matches(
            project_id="project_source",
            entity_id="nonexistent"
        )

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_get_all_linked_entities(self, cross_project_linker, async_mock_neo4j_handler):
        """Test getting all linked entities across projects."""
        # Setup mock session for get_cross_project_links
        mock_session = AsyncMock()

        outgoing_result = AsyncMock()
        outgoing_result.data = AsyncMock(return_value=[
            {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "SAME_PERSON",
                "confidence": 0.95,
                "created_at": "2024-01-15T10:30:00",
                "metadata": "{}"
            }
        ])

        incoming_result = AsyncMock()
        incoming_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(side_effect=[outgoing_result, incoming_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        async_mock_neo4j_handler.session.return_value = mock_session

        # Setup get_person to return entity data
        async_mock_neo4j_handler.get_person.return_value = {
            "id": "entity-456",
            "profile": {"core": {"name": [{"first_name": "Jane", "last_name": "Smith"}]}}
        }

        linked = await cross_project_linker.get_all_linked_entities(
            project_id="project_alpha",
            entity_id="entity-123"
        )

        assert len(linked) == 1
        assert linked[0]["project_id"] == "project_beta"
        assert linked[0]["entity_id"] == "entity-456"
        assert linked[0]["link_type"] == "SAME_PERSON"
        assert "entity_data" in linked[0]


class TestCrossProjectLinkerSingleton:
    """Tests for CrossProjectLinker singleton pattern."""

    def test_get_cross_project_linker_singleton(self):
        """Test get_cross_project_linker returns same instance."""
        from api.services.cross_project_linker import get_cross_project_linker
        import api.services.cross_project_linker as module

        # Reset singleton
        module._cross_project_linker_instance = None

        mock_handler = MagicMock()
        linker1 = get_cross_project_linker(mock_handler)
        linker2 = get_cross_project_linker()

        assert linker1 is linker2

    def test_get_cross_project_linker_updates_handler(self):
        """Test that passing a new handler updates the singleton."""
        from api.services.cross_project_linker import get_cross_project_linker
        import api.services.cross_project_linker as module

        # Reset singleton
        module._cross_project_linker_instance = None

        handler1 = MagicMock()
        linker = get_cross_project_linker(handler1)
        assert linker.neo4j_handler is handler1

        handler2 = MagicMock()
        linker = get_cross_project_linker(handler2)
        assert linker.neo4j_handler is handler2


class TestCrossProjectEndpoints:
    """Tests for cross-project linking API endpoints."""

    @pytest.fixture
    def mock_handler_for_endpoints(self, mock_neo4j_handler):
        """Extend mock handler for endpoint tests."""
        # Make handler async-compatible
        mock_neo4j_handler.get_person = AsyncMock(return_value={
            "id": "entity-123",
            "profile": {"core": {"name": [{"first_name": "John", "last_name": "Doe"}]}}
        })
        mock_neo4j_handler.get_all_projects = AsyncMock(return_value=[
            {"safe_name": "project_alpha"},
            {"safe_name": "project_beta"}
        ])
        mock_neo4j_handler.get_all_people = AsyncMock(return_value=[])

        # Setup mock session
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_neo4j_handler.session = MagicMock(return_value=mock_session)

        return mock_neo4j_handler

    def test_create_cross_project_link_endpoint(self, mock_handler_for_endpoints):
        """Test creating a cross-project link via API."""
        # Setup get_person to return entities
        mock_handler_for_endpoints.get_person = AsyncMock(side_effect=[
            {"id": "entity-123", "profile": {}},
            {"id": "entity-456", "profile": {}}
        ])

        client = get_test_client(mock_handler_for_endpoints)

        response = client.post(
            "/api/v1/cross-project/link",
            json={
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "SAME_PERSON",
                "confidence": 0.95,
                "metadata": {"notes": "Email match"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "link" in data

    def test_create_cross_project_link_invalid_type(self, mock_handler_for_endpoints):
        """Test creating a link with invalid type."""
        client = get_test_client(mock_handler_for_endpoints)

        response = client.post(
            "/api/v1/cross-project/link",
            json={
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "INVALID_TYPE",
                "confidence": 0.95
            }
        )

        assert response.status_code == 400
        assert "Invalid link type" in response.json()["detail"]

    def test_delete_cross_project_link_endpoint(self, mock_handler_for_endpoints):
        """Test deleting a cross-project link via API."""
        # Setup mock to indicate deletion success
        mock_session = mock_handler_for_endpoints.session()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted_count": 1})
        mock_session.run = AsyncMock(return_value=mock_result)

        client = get_test_client(mock_handler_for_endpoints)

        response = client.request(
            "DELETE",
            "/api/v1/cross-project/link",
            json={
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_entity_cross_links_endpoint(self, mock_handler_for_endpoints):
        """Test getting cross-project links for an entity."""
        # Setup mock to return links
        mock_session = mock_handler_for_endpoints.session()

        outgoing_result = AsyncMock()
        outgoing_result.data = AsyncMock(return_value=[])
        incoming_result = AsyncMock()
        incoming_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(side_effect=[outgoing_result, incoming_result])

        client = get_test_client(mock_handler_for_endpoints)

        response = client.get(
            "/api/v1/projects/project_alpha/entities/entity-123/cross-links"
        )

        assert response.status_code == 200
        data = response.json()
        assert "links" in data
        assert "count" in data

    def test_get_entity_cross_links_not_found(self, mock_handler_for_endpoints):
        """Test getting links for non-existent entity."""
        mock_handler_for_endpoints.get_person = AsyncMock(return_value=None)

        client = get_test_client(mock_handler_for_endpoints)

        response = client.get(
            "/api/v1/projects/project_alpha/entities/nonexistent/cross-links"
        )

        assert response.status_code == 404

    def test_find_potential_matches_endpoint(self, mock_handler_for_endpoints):
        """Test finding potential matches via API."""
        client = get_test_client(mock_handler_for_endpoints)

        response = client.get(
            "/api/v1/cross-project/find-matches/project_alpha/entity-123"
        )

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "count" in data

    def test_find_potential_matches_with_target_projects(self, mock_handler_for_endpoints):
        """Test finding matches with specified target projects."""
        client = get_test_client(mock_handler_for_endpoints)

        response = client.get(
            "/api/v1/cross-project/find-matches/project_alpha/entity-123",
            params={"target_projects": "project_beta,project_gamma"}
        )

        assert response.status_code == 200

    def test_get_all_linked_entities_endpoint(self, mock_handler_for_endpoints):
        """Test getting all linked entities via API."""
        # Setup mock to return empty links
        mock_session = mock_handler_for_endpoints.session()

        outgoing_result = AsyncMock()
        outgoing_result.data = AsyncMock(return_value=[])
        incoming_result = AsyncMock()
        incoming_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(side_effect=[outgoing_result, incoming_result])

        client = get_test_client(mock_handler_for_endpoints)

        response = client.get(
            "/api/v1/projects/project_alpha/entities/entity-123/cross-links/all-linked"
        )

        assert response.status_code == 200
        data = response.json()
        assert "linked_entities" in data
        assert "count" in data


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_record_to_link_invalid_data(self):
        """Test _record_to_link with invalid data."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        # Missing required fields
        result = linker._record_to_link({"partial": "data"})
        assert result is None

        # Invalid JSON in metadata
        result = linker._record_to_link({
            "source_project_id": "p1",
            "source_entity_id": "e1",
            "target_project_id": "p2",
            "target_entity_id": "e2",
            "metadata": "not{valid}json"
        })
        assert result is not None  # Should still work, treating metadata as empty

    def test_extract_identifiers_empty_profile(self):
        """Test identifier extraction with empty profile."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)
        linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        entity = {"id": "test", "profile": {}}
        identifiers = linker._extract_identifiers(entity)
        assert identifiers == {}

    def test_extract_identifiers_missing_section(self):
        """Test identifier extraction when section is missing."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)
        linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        entity = {"id": "test", "profile": {"other_section": {"field": "value"}}}
        identifiers = linker._extract_identifiers(entity)
        assert identifiers == {}

    @pytest.mark.asyncio
    async def test_link_entities_no_handler(self):
        """Test linking when handler is not configured."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        with pytest.raises(ValueError, match="Neo4j handler not configured"):
            await linker.link_entities(
                source_project="p1",
                source_entity="e1",
                target_project="p2",
                target_entity="e2",
                link_type="RELATED"
            )

    @pytest.mark.asyncio
    async def test_unlink_entities_no_handler(self):
        """Test unlinking when handler is not configured."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        result = await linker.unlink_entities(
            source_project="p1",
            source_entity="e1",
            target_project="p2",
            target_entity="e2"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cross_project_links_no_handler(self):
        """Test getting links when handler is not configured."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        result = await linker.get_cross_project_links(
            project_id="p1",
            entity_id="e1"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_potential_matches_no_handler(self):
        """Test finding matches when handler is not configured."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        result = await linker.find_potential_matches(
            project_id="p1",
            entity_id="e1"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_linked_entities_no_handler(self):
        """Test getting linked entities when handler is not configured."""
        from api.services.cross_project_linker import CrossProjectLinker

        linker = CrossProjectLinker(None)

        result = await linker.get_all_linked_entities(
            project_id="p1",
            entity_id="e1"
        )

        assert result == []
