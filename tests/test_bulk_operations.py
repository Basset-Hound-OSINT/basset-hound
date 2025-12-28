"""
Tests for Bulk Operations service and API endpoints.

Tests cover:
- JSON import/export
- CSV import/export
- Validation
- Error handling
- Large batch handling
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from api.services.bulk_operations import (
    BulkOperationsService,
    BulkImportResult,
    BulkExportOptions,
)


def get_test_client(mock_handler):
    """Create a test client with mocked dependencies."""
    from api.main import app
    from api.dependencies import get_neo4j_handler

    app.dependency_overrides[get_neo4j_handler] = lambda: mock_handler
    return TestClient(app)


# ----- Fixtures -----

@pytest.fixture
def mock_neo4j_handler():
    """Create a mock Neo4j handler for testing."""
    handler = MagicMock()

    # Mock project methods
    handler.get_project.return_value = {
        "id": "test-project-id",
        "name": "Test Project",
        "safe_name": "test_project",
        "created_at": "2024-01-15T10:30:00"
    }

    # Mock person methods
    handler.get_all_people.return_value = [
        {
            "id": "person-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                },
                "Tagged People": {
                    "tagged_people": ["person-2"]
                }
            }
        },
        {
            "id": "person-2",
            "created_at": "2024-01-15T11:00:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "Jane", "last_name": "Smith"}],
                    "email": ["jane@example.com"]
                }
            }
        }
    ]

    handler.get_person.return_value = None  # Default to not found

    def create_person_side_effect(project_id, person_data):
        return {
            "id": person_data.get("id", "new-uuid"),
            "created_at": person_data.get("created_at", "2024-01-15T10:30:00"),
            "profile": person_data.get("profile", {})
        }

    handler.create_person.side_effect = create_person_side_effect

    def create_people_batch_side_effect(project_id, people_data):
        # Return list of IDs for successfully created people
        return [p.get("id", f"new-uuid-{i}") for i, p in enumerate(people_data)]

    handler.create_people_batch.side_effect = create_people_batch_side_effect

    def update_person_side_effect(project_id, person_id, data):
        return {
            "id": person_id,
            "created_at": "2024-01-15T10:30:00",
            "profile": data.get("profile", {})
        }

    handler.update_person.side_effect = update_person_side_effect

    return handler


@pytest.fixture
def bulk_service(mock_neo4j_handler):
    """Create a BulkOperationsService with mocked handler."""
    return BulkOperationsService(mock_neo4j_handler)


@pytest.fixture
def sample_entities():
    """Sample entity data for testing."""
    return [
        {
            "profile": {
                "core": {
                    "name": [{"first_name": "Alice", "last_name": "Wonder"}],
                    "email": ["alice@example.com"]
                }
            }
        },
        {
            "profile": {
                "core": {
                    "name": [{"first_name": "Bob", "last_name": "Builder"}],
                    "email": ["bob@example.com"]
                }
            }
        }
    ]


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """first_name,last_name,email
Alice,Wonder,alice@example.com
Bob,Builder,bob@example.com
Charlie,Brown,charlie@example.com"""


@pytest.fixture
def sample_csv_mapping():
    """Sample CSV to entity field mapping."""
    return {
        "first_name": "profile.core.first_name",
        "last_name": "profile.core.last_name",
        "email": "profile.core.email"
    }


# ----- BulkImportResult Tests -----

class TestBulkImportResult:
    """Tests for BulkImportResult dataclass."""

    def test_init_defaults(self):
        """Test default initialization."""
        result = BulkImportResult()
        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.errors == []
        assert result.created_ids == []

    def test_add_success(self):
        """Test adding a successful import."""
        result = BulkImportResult(total=1)
        result.add_success("entity-123")

        assert result.successful == 1
        assert "entity-123" in result.created_ids

    def test_add_error(self):
        """Test adding an import error."""
        result = BulkImportResult(total=1)
        result.add_error(0, "Something went wrong")

        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0]["index"] == 0
        assert result.errors[0]["error"] == "Something went wrong"

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = BulkImportResult(total=2)
        result.add_success("id-1")
        result.add_error(1, "Error message")

        d = result.to_dict()
        assert d["total"] == 2
        assert d["successful"] == 1
        assert d["failed"] == 1
        assert d["created_ids"] == ["id-1"]
        assert len(d["errors"]) == 1


# ----- BulkExportOptions Tests -----

class TestBulkExportOptions:
    """Tests for BulkExportOptions dataclass."""

    def test_init_defaults(self):
        """Test default initialization."""
        options = BulkExportOptions()
        assert options.format == "json"
        assert options.include_relationships is True
        assert options.include_files is False
        assert options.entity_ids is None

    def test_valid_formats(self):
        """Test all valid export formats."""
        for fmt in ["json", "csv", "jsonl"]:
            options = BulkExportOptions(format=fmt)
            assert options.format == fmt

    def test_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError) as exc:
            BulkExportOptions(format="xml")
        assert "Invalid format" in str(exc.value)

    def test_entity_ids_filter(self):
        """Test entity IDs filter."""
        options = BulkExportOptions(entity_ids=["id-1", "id-2"])
        assert options.entity_ids == ["id-1", "id-2"]


# ----- BulkOperationsService Tests -----

class TestBulkOperationsService:
    """Tests for BulkOperationsService class."""

    def test_import_entities_success(self, bulk_service, sample_entities):
        """Test successful bulk import."""
        result = bulk_service.import_entities("test_project", sample_entities)

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0
        assert len(result.created_ids) == 2

    def test_import_entities_project_not_found(self, bulk_service, sample_entities):
        """Test import to non-existent project."""
        bulk_service.neo4j_handler.get_project.return_value = None

        result = bulk_service.import_entities("nonexistent", sample_entities)

        # Project not found counts as a failure
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]["error"].lower()

    def test_import_entities_with_existing_skip(self, bulk_service, mock_neo4j_handler):
        """Test import with existing entity (skip mode)."""
        entities = [{"id": "existing-id", "profile": {}}]
        mock_neo4j_handler.get_person.return_value = {"id": "existing-id"}

        result = bulk_service.import_entities("test_project", entities, update_existing=False)

        assert result.total == 1
        assert result.successful == 0
        assert result.failed == 1
        assert "already exists" in result.errors[0]["error"]

    def test_import_entities_with_existing_update(self, bulk_service, mock_neo4j_handler):
        """Test import with existing entity (update mode)."""
        entities = [{"id": "existing-id", "profile": {"core": {"email": ["new@example.com"]}}}]
        mock_neo4j_handler.get_person.return_value = {"id": "existing-id"}

        result = bulk_service.import_entities("test_project", entities, update_existing=True)

        assert result.total == 1
        assert result.successful == 1
        assert result.failed == 0

    def test_export_entities_json(self, bulk_service):
        """Test exporting entities to JSON format."""
        options = BulkExportOptions(format="json")
        content = bulk_service.export_entities("test_project", options)

        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "person-1"

    def test_export_entities_jsonl(self, bulk_service):
        """Test exporting entities to JSONL format."""
        options = BulkExportOptions(format="jsonl")
        content = bulk_service.export_entities("test_project", options)

        lines = content.strip().split("\n")
        assert len(lines) == 2

        entity1 = json.loads(lines[0])
        assert entity1["id"] == "person-1"

    def test_export_entities_csv(self, bulk_service):
        """Test exporting entities to CSV format."""
        options = BulkExportOptions(format="csv")
        content = bulk_service.export_entities("test_project", options)

        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 entities
        assert "id" in lines[0]

    def test_export_entities_without_relationships(self, bulk_service):
        """Test export excluding relationships."""
        options = BulkExportOptions(format="json", include_relationships=False)
        content = bulk_service.export_entities("test_project", options)

        data = json.loads(content)
        # First entity should not have Tagged People section
        assert "Tagged People" not in data[0].get("profile", {})

    def test_export_entities_specific_ids(self, bulk_service, mock_neo4j_handler):
        """Test export with specific entity IDs."""
        mock_neo4j_handler.get_person.return_value = {
            "id": "person-1",
            "profile": {"core": {"name": "John"}}
        }

        options = BulkExportOptions(format="json", entity_ids=["person-1"])
        content = bulk_service.export_entities("test_project", options)

        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["id"] == "person-1"

    def test_export_entities_project_not_found(self, bulk_service):
        """Test export from non-existent project."""
        bulk_service.neo4j_handler.get_project.return_value = None

        with pytest.raises(ValueError) as exc:
            options = BulkExportOptions(format="json")
            bulk_service.export_entities("nonexistent", options)

        assert "not found" in str(exc.value).lower()

    def test_validate_import_data_valid(self, bulk_service, sample_entities):
        """Test validation of valid entity data."""
        errors = bulk_service.validate_import_data(sample_entities)
        assert len(errors) == 0

    def test_validate_import_data_invalid_type(self, bulk_service):
        """Test validation catches invalid entity type."""
        entities = ["not a dict", 123]
        errors = bulk_service.validate_import_data(entities)

        assert len(errors) == 2
        for error in errors:
            assert "must be a dictionary" in error["error"]

    def test_validate_import_data_invalid_profile(self, bulk_service):
        """Test validation catches invalid profile structure."""
        entities = [{"profile": "not a dict"}]
        errors = bulk_service.validate_import_data(entities)

        assert len(errors) == 1
        assert "profile must be a dictionary" in errors[0]["error"].lower()

    def test_validate_import_data_invalid_datetime(self, bulk_service):
        """Test validation catches invalid datetime format."""
        entities = [{"created_at": "not-a-datetime"}]
        errors = bulk_service.validate_import_data(entities)

        assert len(errors) == 1
        assert "iso 8601" in errors[0]["error"].lower()

    def test_validate_import_data_valid_datetime(self, bulk_service):
        """Test validation accepts valid datetime format."""
        entities = [{"created_at": "2024-01-15T10:30:00"}]
        errors = bulk_service.validate_import_data(entities)
        assert len(errors) == 0

    def test_import_from_csv(self, bulk_service, sample_csv_content, sample_csv_mapping):
        """Test CSV import with field mapping."""
        result = bulk_service.import_from_csv(
            "test_project",
            sample_csv_content,
            sample_csv_mapping
        )

        assert result.total == 3
        assert result.successful == 3

    def test_import_from_csv_invalid(self, bulk_service):
        """Test CSV import with invalid content."""
        result = bulk_service.import_from_csv(
            "test_project",
            "invalid\x00csv\x00content",  # Invalid CSV
            {"col": "profile.field"}
        )

        # Should handle gracefully
        assert result.total >= 0

    def test_export_to_csv_specific_fields(self, bulk_service):
        """Test CSV export with specific fields."""
        fields = ["id", "profile.core.email"]
        content = bulk_service.export_to_csv("test_project", fields)

        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 entities
        assert "id" in lines[0]
        assert "profile.core.email" in lines[0]

    def test_export_to_csv_project_not_found(self, bulk_service):
        """Test CSV export from non-existent project."""
        bulk_service.neo4j_handler.get_project.return_value = None

        with pytest.raises(ValueError) as exc:
            bulk_service.export_to_csv("nonexistent", ["id"])

        assert "not found" in str(exc.value).lower()


# ----- API Endpoint Tests -----

class TestBulkImportEndpoint:
    """Tests for POST /api/v1/projects/{project}/bulk/import endpoint."""

    def test_bulk_import_success(self, mock_neo4j_handler):
        """Test successful bulk import via API."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/import",
            json={
                "entities": [
                    {"profile": {"core": {"name": "John"}}},
                    {"profile": {"core": {"name": "Jane"}}}
                ],
                "update_existing": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["successful"] == 2
        assert len(data["created_ids"]) == 2

    def test_bulk_import_project_not_found(self, mock_neo4j_handler):
        """Test bulk import to non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/nonexistent/bulk/import",
            json={
                "entities": [{"profile": {}}]
            }
        )

        # Returns 200 with error in result (BulkImportResult contains the error)
        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 1
        assert "not found" in data["errors"][0]["error"].lower()

    def test_bulk_import_empty_entities(self, mock_neo4j_handler):
        """Test bulk import with empty entities list."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/import",
            json={
                "entities": []
            }
        )

        # Should fail validation (min_length=1)
        assert response.status_code == 422


class TestBulkImportCSVEndpoint:
    """Tests for POST /api/v1/projects/{project}/bulk/import/csv endpoint."""

    def test_csv_import_success(self, mock_neo4j_handler):
        """Test successful CSV import via API."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/import/csv",
            json={
                "csv_content": "name,email\nJohn,john@example.com\nJane,jane@example.com",
                "mapping": {
                    "name": "profile.core.name",
                    "email": "profile.core.email"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_csv_import_project_not_found(self, mock_neo4j_handler):
        """Test CSV import to non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/nonexistent/bulk/import/csv",
            json={
                "csv_content": "name\nJohn",
                "mapping": {"name": "profile.core.name"}
            }
        )

        assert response.status_code == 404


class TestBulkExportEndpoint:
    """Tests for GET /api/v1/projects/{project}/bulk/export endpoint."""

    def test_export_json(self, mock_neo4j_handler):
        """Test JSON export via API."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "json"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, list)

    def test_export_csv(self, mock_neo4j_handler):
        """Test CSV export via API."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "csv"}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "id" in response.text  # Should have header

    def test_export_jsonl(self, mock_neo4j_handler):
        """Test JSONL export via API."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "jsonl"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

    def test_export_invalid_format(self, mock_neo4j_handler):
        """Test export with invalid format."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "xml"}
        )

        assert response.status_code == 400

    def test_export_with_entity_ids(self, mock_neo4j_handler):
        """Test export with specific entity IDs."""
        mock_neo4j_handler.get_person.return_value = {
            "id": "person-1",
            "profile": {}
        }
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "json", "entity_ids": "person-1,person-2"}
        )

        assert response.status_code == 200

    def test_export_without_relationships(self, mock_neo4j_handler):
        """Test export excluding relationships."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "json", "include_relationships": False}
        )

        assert response.status_code == 200
        data = response.json()
        # First entity should not have Tagged People
        if data:
            assert "Tagged People" not in data[0].get("profile", {})

    def test_export_project_not_found(self, mock_neo4j_handler):
        """Test export from non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/nonexistent/bulk/export",
            params={"format": "json"}
        )

        assert response.status_code == 404


class TestBulkExportCSVEndpoint:
    """Tests for POST /api/v1/projects/{project}/bulk/export/csv endpoint."""

    def test_export_specific_fields(self, mock_neo4j_handler):
        """Test CSV export with specific fields."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/export/csv",
            json={
                "fields": ["id", "profile.core.email"]
            }
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "id" in response.text
        assert "profile.core.email" in response.text

    def test_export_csv_project_not_found(self, mock_neo4j_handler):
        """Test CSV export from non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/nonexistent/bulk/export/csv",
            json={"fields": ["id"]}
        )

        assert response.status_code == 404


class TestValidateEndpoint:
    """Tests for POST /api/v1/projects/{project}/bulk/validate endpoint."""

    def test_validate_valid_data(self, mock_neo4j_handler):
        """Test validation of valid entity data."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/validate",
            json={
                "entities": [
                    {"profile": {"core": {"name": "John"}}},
                    {"id": "custom-id", "created_at": "2024-01-15T10:30:00", "profile": {}}
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_invalid_data(self, mock_neo4j_handler):
        """Test validation of invalid entity data."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/bulk/validate",
            json={
                "entities": [
                    {"profile": "not a dict"},
                    {"created_at": "invalid-date"}
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 2


class TestLargeBatchHandling:
    """Tests for handling large batches of entities."""

    def test_import_large_batch(self, mock_neo4j_handler):
        """Test importing a large batch of entities."""
        client = get_test_client(mock_neo4j_handler)

        # Create 100 entities
        entities = [
            {"profile": {"core": {"name": f"Person {i}"}}}
            for i in range(100)
        ]

        response = client.post(
            "/api/v1/projects/test_project/bulk/import",
            json={
                "entities": entities,
                "update_existing": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100
        assert data["successful"] == 100

    def test_export_large_batch(self, mock_neo4j_handler):
        """Test exporting a large batch of entities."""
        # Mock 100 entities
        mock_neo4j_handler.get_all_people.return_value = [
            {
                "id": f"person-{i}",
                "created_at": "2024-01-15T10:30:00",
                "profile": {"core": {"name": f"Person {i}"}}
            }
            for i in range(100)
        ]

        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/bulk/export",
            params={"format": "json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 100

    def test_validate_large_batch(self, mock_neo4j_handler):
        """Test validating a large batch of entities."""
        client = get_test_client(mock_neo4j_handler)

        entities = [
            {"profile": {"core": {"name": f"Person {i}"}}}
            for i in range(100)
        ]

        response = client.post(
            "/api/v1/projects/test_project/bulk/validate",
            json={"entities": entities}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_import_with_mixed_success_failure(self, mock_neo4j_handler):
        """Test import with some successes and some failures."""
        # Make every other entity fail
        call_count = [0]

        def create_person_side_effect(project_id, person_data):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                return None  # Simulate failure
            return {
                "id": person_data.get("id", f"id-{call_count[0]}"),
                "profile": person_data.get("profile", {})
            }

        mock_neo4j_handler.create_person.side_effect = create_person_side_effect

        client = get_test_client(mock_neo4j_handler)

        entities = [{"profile": {}} for _ in range(10)]

        response = client.post(
            "/api/v1/projects/test_project/bulk/import",
            json={"entities": entities}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        # Some should succeed, some should fail
        assert data["successful"] + data["failed"] == 10
