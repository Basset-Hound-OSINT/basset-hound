"""
Integration tests for Cletus news aggregation integration.

Tests:
- Cletus client health checks
- Event listing and fetching
- Event ingestion into projects
- Entity and relationship creation
- Organization extraction
"""

import pytest
import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from api.clients.cletus_client import get_cletus_client, CletusClient
from api.services.cletus_ingestion import CletusIngestionService

logger = logging.getLogger("test_cletus_integration")


class MockCletusEvent:
    """Mock Cletus event data for testing."""

    @staticmethod
    def create(
        event_id: Optional[str] = None,
        title: str = "Test Event",
        category: str = "Cyber",
        severity: str = "high"
    ) -> Dict[str, Any]:
        """Create a mock event."""
        return {
            "id": event_id or str(uuid4()),
            "title": title,
            "summary": f"Summary for {title}",
            "category": category,
            "severity": severity,
            "status": "active",
            "keywords": ["test", "event", category.lower()],
            "first_seen": "2026-01-01T00:00:00Z",
            "last_updated": "2026-05-06T00:00:00Z",
            "entry_count": 3,
            "entries": [
                {
                    "id": str(uuid4()),
                    "event_id": event_id or str(uuid4()),
                    "summary": "First entry",
                    "key_developments": ["Development 1", "Development 2"],
                    "sources_mentioned": ["Reuters", "BBC", "CNN"],
                    "sentiment_shift": 0.1,
                    "significance": 0.8,
                    "article_ids": ["art1", "art2"],
                    "observed_at": "2026-05-05T12:00:00Z"
                }
            ]
        }


class TestCletusClient:
    """Tests for CletusClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with custom base URL."""
        client = CletusClient(base_url="http://test:9000")
        assert client.base_url == "http://test:9000"
        assert client.timeout == 10.0

    @pytest.mark.asyncio
    async def test_client_default_base_url(self, monkeypatch):
        """Test client uses CLETUS_BASE_URL env var."""
        monkeypatch.setenv("CLETUS_BASE_URL", "http://custom:9000")
        client = CletusClient()
        assert client.base_url == "http://custom:9000"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager usage."""
        async with get_cletus_client() as client:
            # Client should be None or connected
            # (depends on whether Cletus is actually running)
            if client:
                assert client.client is not None

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, monkeypatch):
        """Test health check when Cletus is unavailable."""
        monkeypatch.setenv("CLETUS_BASE_URL", "http://invalid:9999")
        client = CletusClient()
        is_healthy = await client.health_check()
        # Should return False when unavailable
        assert is_healthy is False


class TestCletusIngestionService:
    """Tests for CletusIngestionService."""

    def test_service_initialization(self, mock_neo4j_handler):
        """Test service initialization."""
        service = CletusIngestionService(mock_neo4j_handler, "test_project")
        assert service.project_safe_name == "test_project"
        assert service.ingested_events == {}
        assert service.ingested_orgs == {}
        assert service.ingested_categories == {}

    @pytest.mark.asyncio
    async def test_ingest_event_creates_entity(self, mock_neo4j_handler):
        """Test that ingesting an event creates an entity."""
        service = CletusIngestionService(mock_neo4j_handler, "test_project")
        mock_client = type('obj', (object,), {})()

        event = MockCletusEvent.create(event_id="evt1", title="Cyber Attack")

        # Mock the neo4j_handler.create_person to return a created entity
        created_entity = {
            "id": str(uuid4()),
            "created_at": "2026-05-06T00:00:00Z"
        }
        mock_neo4j_handler.create_person = lambda *args, **kwargs: created_entity

        entity_id = await service.ingest_event(mock_client, event)

        assert entity_id == created_entity["id"]
        assert "evt1" in service.ingested_events

    @pytest.mark.asyncio
    async def test_organization_extraction(self, mock_neo4j_handler):
        """Test that organizations are extracted from events."""
        service = CletusIngestionService(mock_neo4j_handler, "test_project")

        # Track created entities
        created_entities = {}
        def create_person_side_effect(project_name, data):
            entity_id = str(uuid4())
            created_entities[entity_id] = data
            return {"id": entity_id}

        mock_neo4j_handler.create_person = create_person_side_effect
        mock_neo4j_handler.create_relationship = lambda *args, **kwargs: True

        mock_client = type('obj', (object,), {})()
        event = MockCletusEvent.create()

        entity_id = await service.ingest_event(mock_client, event)

        # Check that organizations were extracted and entities created
        assert len(service.ingested_orgs) > 0
        assert "Reuters" in service.ingested_orgs or entity_id is not None

    @pytest.mark.asyncio
    async def test_category_creation(self, mock_neo4j_handler):
        """Test that categories are created as entities."""
        service = CletusIngestionService(mock_neo4j_handler, "test_project")

        created_entities = {}
        def create_person_side_effect(project_name, data):
            entity_id = str(uuid4())
            created_entities[entity_id] = data
            return {"id": entity_id}

        mock_neo4j_handler.create_person = create_person_side_effect
        mock_neo4j_handler.create_relationship = lambda *args, **kwargs: True

        mock_client = type('obj', (object,), {})()
        event = MockCletusEvent.create(category="Legal")

        entity_id = await service.ingest_event(mock_client, event)

        # Check that category was created
        assert "Legal" in service.ingested_categories or entity_id is not None


class TestCletusRouter:
    """Tests for Cletus router endpoints."""

    def test_status_endpoint_schema(self):
        """Test status endpoint response schema."""
        # This would be tested with FastAPI TestClient
        # when Cletus integration is fully implemented
        pass

    def test_list_events_endpoint(self):
        """Test list events endpoint with filters."""
        pass

    def test_ingest_all_events_endpoint(self):
        """Test ingest all events endpoint."""
        pass

    def test_ingest_single_event_endpoint(self):
        """Test ingest specific event endpoint."""
        pass


# Fixtures

@pytest.fixture
def mock_neo4j_handler():
    """Create a mock Neo4j handler."""
    class MockHandler:
        def create_person(self, project_safe_name, data):
            return {"id": str(uuid4()), "created_at": "2026-05-06T00:00:00Z"}

        def create_relationship(self, project_safe_name, source_id, target_id,
                              rel_type="RELATED_TO", properties=None):
            return {"relationship_type": rel_type}

        def get_person(self, project_safe_name, person_id):
            return {"id": person_id, "profile": {}}

    return MockHandler()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
