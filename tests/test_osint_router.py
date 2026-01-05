"""
Comprehensive tests for the OSINT Router.

Tests cover:
- Data ingestion with provenance
- Investigation job creation
- HTML extraction endpoint
- Capabilities endpoint
- Statistics endpoint
- Error handling
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.routers.osint import router
from api.models.provenance import SourceType, CaptureMethod


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create a test FastAPI app with the OSINT router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Ingest Endpoint Tests
# =============================================================================


class TestIngestEndpoint:
    """Tests for POST /osint/ingest endpoint."""

    def test_ingest_single_identifier(self, client):
        """Test ingesting a single identifier."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "source_url": "https://example.com/contact",
            "source_title": "Contact Page",
            "captured_by": "test-client",
            "identifiers": [
                {
                    "identifier_type": "email",
                    "identifier_value": "test@example.com",
                    "confidence": 0.9,
                }
            ],
            "verify_before_ingest": True,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == "test-project"
        assert data["total_count"] == 1
        assert data["ingested_count"] == 1

    def test_ingest_multiple_identifiers(self, client):
        """Test ingesting multiple identifiers."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [
                {"identifier_type": "email", "identifier_value": "user1@example.com"},
                {"identifier_type": "email", "identifier_value": "user2@example.com"},
                {"identifier_type": "phone", "identifier_value": "+12025551234"},
            ],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["results"]) == 3

    def test_ingest_with_invalid_identifier(self, client):
        """Test ingesting with an invalid identifier that gets blocked."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [
                {"identifier_type": "email", "identifier_value": "not_an_email"},
            ],
            "verify_before_ingest": True,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["blocked_count"] == 1
        assert data["results"][0]["status"] == "blocked"

    def test_ingest_force_invalid_identifier(self, client):
        """Test force ingesting an invalid identifier."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [
                {
                    "identifier_type": "email",
                    "identifier_value": "not_an_email",
                    "force_ingest": True,
                },
            ],
            "verify_before_ingest": True,
        })

        assert response.status_code == 200
        data = response.json()
        # Force ingest bypasses verification
        assert data["ingested_count"] == 1

    def test_ingest_without_verification(self, client):
        """Test ingesting without verification."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [
                {"identifier_type": "email", "identifier_value": "any_value"},
            ],
            "verify_before_ingest": False,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["ingested_count"] == 1

    def test_ingest_with_context(self, client):
        """Test ingesting with context information."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "source_url": "https://example.com",
            "source_title": "Example Page",
            "source_type": "website",
            "capture_method": "auto_detected",
            "captured_by": "autofill-extension",
            "identifiers": [
                {
                    "identifier_type": "email",
                    "identifier_value": "contact@example.com",
                    "context": "Found in footer",
                    "element_selector": ".footer-email",
                },
            ],
            "metadata": {"session_id": "abc123"},
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_ingest_empty_identifiers(self, client):
        """Test that empty identifiers list is rejected."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [],
        })

        # FastAPI validation should reject this
        assert response.status_code == 422

    def test_ingest_response_includes_timestamps(self, client):
        """Test that ingest response includes timestamp."""
        response = client.post("/api/v1/osint/ingest", json={
            "project_id": "test-project",
            "captured_by": "test-client",
            "identifiers": [
                {"identifier_type": "email", "identifier_value": "test@example.com"},
            ],
        })

        assert response.status_code == 200
        data = response.json()
        assert "ingested_at" in data


# =============================================================================
# Investigate Endpoint Tests
# =============================================================================


class TestInvestigateEndpoint:
    """Tests for POST /osint/investigate endpoint."""

    def test_start_investigation(self, client):
        """Test starting an OSINT investigation."""
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            "target": "https://example.com",
            "investigation_type": "web_osint",
        })

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["project_id"] == "test-project"
        assert data["target"] == "https://example.com"

    def test_investigation_with_options(self, client):
        """Test investigation with all options."""
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            "target": "https://example.com",
            "investigation_type": "web_osint",
            "depth": 3,
            "extract_types": ["email", "phone", "crypto_address"],
            "verify_results": True,
            "auto_link": True,
            "agent_id": "test-agent",
            "timeout_seconds": 600,
            "metadata": {"priority": "high"},
        })

        assert response.status_code == 200
        data = response.json()
        assert data["investigation_type"] == "web_osint"

    def test_investigation_depth_limits(self, client):
        """Test that investigation depth is limited."""
        # Depth > 5 should be rejected
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            "target": "https://example.com",
            "depth": 10,
        })

        assert response.status_code == 422  # Validation error

    def test_investigation_timeout_limits(self, client):
        """Test that timeout is within limits."""
        # Timeout > 3600 should be rejected
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            "target": "https://example.com",
            "timeout_seconds": 7200,
        })

        assert response.status_code == 422

    def test_investigation_includes_estimated_duration(self, client):
        """Test that response includes estimated duration."""
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            "target": "https://example.com",
            "depth": 2,
        })

        assert response.status_code == 200
        data = response.json()
        assert "estimated_duration_seconds" in data


# =============================================================================
# Extract Endpoint Tests
# =============================================================================


class TestExtractEndpoint:
    """Tests for POST /osint/extract endpoint."""

    def test_extract_emails_from_html(self, client):
        """Test extracting emails from HTML content."""
        html = """
        <html>
        <body>
            <p>Contact us at info@example.com or support@example.com</p>
        </body>
        </html>
        """
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["email"],
            "verify": True,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] >= 2
        emails = [i["identifier_value"] for i in data["identifiers"]]
        assert "info@example.com" in emails
        assert "support@example.com" in emails

    def test_extract_phones_from_html(self, client):
        """Test extracting phone numbers from HTML content."""
        html = """
        <html>
        <body>
            <p>Call us: (555) 123-4567 or 555-987-6543</p>
        </body>
        </html>
        """
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["phone"],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] >= 1

    def test_extract_crypto_addresses(self, client):
        """Test extracting cryptocurrency addresses."""
        html = """
        <html>
        <body>
            <p>BTC: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2</p>
            <p>ETH: 0x742d35Cc6634C0532925a3b844Bc9e7595f9E9E9</p>
        </body>
        </html>
        """
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["crypto_address"],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] >= 1

    def test_extract_multiple_types(self, client):
        """Test extracting multiple identifier types."""
        html = """
        <html>
        <body>
            <p>Email: contact@example.com</p>
            <p>Phone: (555) 123-4567</p>
            <p>Twitter: @exampleuser</p>
        </body>
        </html>
        """
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["email", "phone", "username"],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] >= 2

    def test_extract_with_verification(self, client):
        """Test that verification adds details to results."""
        html = "<p>Valid email: test@gmail.com</p>"
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["email"],
            "verify": True,
        })

        assert response.status_code == 200
        data = response.json()
        if data["extracted_count"] > 0:
            first = data["identifiers"][0]
            assert "is_valid" in first or "verification_details" in first

    def test_extract_includes_context(self, client):
        """Test that extraction includes surrounding context."""
        html = "<p>For support, email support@example.com immediately.</p>"
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["email"],
        })

        assert response.status_code == 200
        data = response.json()
        if data["extracted_count"] > 0:
            assert data["identifiers"][0].get("context") is not None

    def test_extract_empty_html(self, client):
        """Test extraction from empty HTML."""
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": "",
            "extract_types": ["email"],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] == 0

    def test_extract_deduplicates_results(self, client):
        """Test that duplicate values are deduplicated."""
        html = """
        <p>Email: test@example.com</p>
        <p>Also: test@example.com</p>
        <p>Contact: test@example.com</p>
        """
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            "html": html,
            "extract_types": ["email"],
        })

        assert response.status_code == 200
        data = response.json()
        # Should only have one unique email
        emails = [i["identifier_value"] for i in data["identifiers"]]
        assert emails.count("test@example.com") == 1


# =============================================================================
# Capabilities Endpoint Tests
# =============================================================================


class TestCapabilitiesEndpoint:
    """Tests for GET /osint/capabilities endpoint."""

    def test_get_capabilities(self, client):
        """Test getting OSINT capabilities."""
        response = client.get("/api/v1/osint/capabilities")

        assert response.status_code == 200
        data = response.json()

        assert "identifier_types" in data
        assert "investigation_types" in data
        assert "verification_levels" in data
        assert "source_types" in data
        assert "capture_methods" in data

    def test_capabilities_include_identifier_types(self, client):
        """Test that capabilities include all identifier types."""
        response = client.get("/api/v1/osint/capabilities")
        data = response.json()

        expected_types = ["email", "phone", "crypto_address", "domain"]
        for t in expected_types:
            assert t in data["identifier_types"]

    def test_capabilities_include_investigation_types(self, client):
        """Test that capabilities include investigation types."""
        response = client.get("/api/v1/osint/capabilities")
        data = response.json()

        assert len(data["investigation_types"]) > 0
        for inv_type in data["investigation_types"]:
            assert "type" in inv_type
            assert "description" in inv_type

    def test_capabilities_include_limits(self, client):
        """Test that capabilities include limits."""
        response = client.get("/api/v1/osint/capabilities")
        data = response.json()

        assert "max_identifiers_per_request" in data
        assert "max_investigation_depth" in data


# =============================================================================
# Stats Endpoint Tests
# =============================================================================


class TestStatsEndpoint:
    """Tests for GET /osint/stats endpoint."""

    def test_get_stats(self, client):
        """Test getting OSINT statistics."""
        response = client.get("/api/v1/osint/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_ingestions" in data
        assert "ingestions_by_type" in data
        assert "verification_success_rate" in data

    def test_get_stats_with_project_filter(self, client):
        """Test getting stats filtered by project."""
        response = client.get("/api/v1/osint/stats", params={"project_id": "test-project"})

        assert response.status_code == 200
        data = response.json()
        assert data["project_filter"] == "test-project"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in OSINT router."""

    def test_ingest_missing_required_fields(self, client):
        """Test that missing required fields return 422."""
        response = client.post("/api/v1/osint/ingest", json={
            # Missing project_id and identifiers
        })

        assert response.status_code == 422

    def test_investigate_missing_target(self, client):
        """Test that missing target returns 422."""
        response = client.post("/api/v1/osint/investigate", json={
            "project_id": "test-project",
            # Missing target
        })

        assert response.status_code == 422

    def test_extract_missing_html(self, client):
        """Test that missing HTML returns 422."""
        response = client.post("/api/v1/osint/extract", json={
            "url": "https://example.com",
            # Missing html
        })

        assert response.status_code == 422
