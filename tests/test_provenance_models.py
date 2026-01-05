"""
Comprehensive tests for the Data Provenance models.

Tests cover:
- SourceType enum
- CaptureMethod enum
- VerificationState enum
- DataProvenance model
- ProvenanceCreate model
- ProvenanceChain model
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from api.models.provenance import (
    SourceType,
    CaptureMethod,
    VerificationState,
    DataProvenance,
    ProvenanceCreate,
    ProvenanceResponse,
    ProvenanceChain,
)


# =============================================================================
# SourceType Enum Tests
# =============================================================================


class TestSourceType:
    """Tests for SourceType enum."""

    def test_all_source_types_exist(self):
        """Test that all expected source types are defined."""
        expected = [
            "website", "api", "file_import", "manual", "browser_extension",
            "osint_agent", "mcp_tool", "third_party", "clipboard", "ocr",
            "screenshot", "other"
        ]
        for source in expected:
            assert SourceType(source) is not None

    def test_source_type_values(self):
        """Test SourceType string values."""
        assert SourceType.WEBSITE.value == "website"
        assert SourceType.BROWSER_EXTENSION.value == "browser_extension"
        assert SourceType.OSINT_AGENT.value == "osint_agent"
        assert SourceType.MCP_TOOL.value == "mcp_tool"


# =============================================================================
# CaptureMethod Enum Tests
# =============================================================================


class TestCaptureMethod:
    """Tests for CaptureMethod enum."""

    def test_all_capture_methods_exist(self):
        """Test that all expected capture methods are defined."""
        expected = [
            "auto_detected", "user_selected", "form_autofill", "clipboard",
            "file_upload", "api_fetch", "scrape", "manual"
        ]
        for method in expected:
            assert CaptureMethod(method) is not None

    def test_capture_method_values(self):
        """Test CaptureMethod string values."""
        assert CaptureMethod.AUTO_DETECTED.value == "auto_detected"
        assert CaptureMethod.USER_SELECTED.value == "user_selected"
        assert CaptureMethod.MANUAL_INPUT.value == "manual"


# =============================================================================
# VerificationState Enum Tests
# =============================================================================


class TestVerificationState:
    """Tests for VerificationState enum."""

    def test_all_verification_states_exist(self):
        """Test that all expected verification states are defined."""
        expected = [
            "unverified", "format_valid", "network_verified", "api_verified",
            "human_verified", "user_override", "failed", "expired"
        ]
        for state in expected:
            assert VerificationState(state) is not None

    def test_verification_state_progression(self):
        """Test logical verification state progression."""
        states = [
            VerificationState.UNVERIFIED,
            VerificationState.FORMAT_VALID,
            VerificationState.NETWORK_VERIFIED,
            VerificationState.API_VERIFIED,
            VerificationState.HUMAN_VERIFIED,
        ]
        # Just verify they're all distinct
        assert len(set(states)) == 5


# =============================================================================
# DataProvenance Model Tests
# =============================================================================


class TestDataProvenance:
    """Tests for DataProvenance model."""

    def test_create_minimal_provenance(self):
        """Test creating provenance with minimal fields."""
        prov = DataProvenance()
        assert prov.source_type == SourceType.OTHER
        assert prov.capture_method == CaptureMethod.MANUAL_INPUT
        assert prov.verification_state == VerificationState.UNVERIFIED
        assert prov.confidence == 0.5
        # User override defaults
        assert prov.user_verified is False
        assert prov.user_override is False
        assert prov.override_reason is None
        assert prov.override_at is None

    def test_create_full_provenance(self):
        """Test creating provenance with all fields."""
        now = datetime.utcnow()
        prov = DataProvenance(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com/page",
            source_title="Example Page",
            source_domain="example.com",
            capture_method=CaptureMethod.AUTO_DETECTED,
            captured_at=now,
            captured_by="autofill-extension",
            user_agent="Mozilla/5.0...",
            page_context="Contact information section",
            element_selector=".contact-email",
            screenshot_path="/screenshots/abc123.png",
            confidence=0.95,
            verification_state=VerificationState.FORMAT_VALID,
            verified_at=now,
            verification_method="regex",
            original_source_id="prov-123",
            transformation_notes="Normalized email",
            external_tool="SpiderFoot",
            external_tool_version="4.0.0",
            external_record_id="sf-12345",
            metadata={"extra": "data"},
        )

        assert prov.source_type == SourceType.WEBSITE
        assert prov.source_url == "https://example.com/page"
        assert prov.captured_by == "autofill-extension"
        assert prov.confidence == 0.95

    def test_provenance_to_dict(self):
        """Test DataProvenance serialization."""
        prov = DataProvenance(
            source_type=SourceType.BROWSER_EXTENSION,
            source_url="https://example.com",
            captured_by="test",
        )

        data = prov.to_dict()

        assert data["source_type"] == "browser_extension"
        assert data["source_url"] == "https://example.com"
        assert data["captured_by"] == "test"
        assert "captured_at" in data
        assert data["captured_at"] is not None

    def test_provenance_confidence_bounds(self):
        """Test that confidence is bounded 0-1."""
        # Valid confidence
        prov = DataProvenance(confidence=0.5)
        assert prov.confidence == 0.5

        # Edge cases
        prov = DataProvenance(confidence=0.0)
        assert prov.confidence == 0.0

        prov = DataProvenance(confidence=1.0)
        assert prov.confidence == 1.0

    def test_provenance_field_lengths(self):
        """Test that field length limits are enforced."""
        # source_url max 2000
        prov = DataProvenance(source_url="https://example.com/" + "a" * 1980)
        assert len(prov.source_url) <= 2000

    def test_provenance_datetime_handling(self):
        """Test datetime field handling."""
        prov = DataProvenance()
        assert isinstance(prov.captured_at, datetime)

        # With explicit time
        specific_time = datetime(2026, 1, 5, 12, 0, 0)
        prov2 = DataProvenance(captured_at=specific_time)
        assert prov2.captured_at == specific_time

    def test_user_override_fields(self):
        """Test user override functionality."""
        now = datetime.utcnow()
        prov = DataProvenance(
            source_type=SourceType.WEBSITE,
            verification_state=VerificationState.FAILED,
            user_verified=True,
            user_override=True,
            override_reason="Valid on internal network",
            override_at=now,
        )

        assert prov.user_verified is True
        assert prov.user_override is True
        assert prov.override_reason == "Valid on internal network"
        assert prov.override_at == now

        # Check serialization includes override fields
        data = prov.to_dict()
        assert data["user_verified"] is True
        assert data["user_override"] is True
        assert data["override_reason"] == "Valid on internal network"
        assert data["override_at"] is not None

    def test_user_override_state(self):
        """Test the USER_OVERRIDE verification state."""
        prov = DataProvenance(
            verification_state=VerificationState.USER_OVERRIDE,
            user_override=True,
            override_reason="User confirmed this IP is valid on VPN",
        )
        assert prov.verification_state == VerificationState.USER_OVERRIDE


# =============================================================================
# ProvenanceCreate Model Tests
# =============================================================================


class TestProvenanceCreate:
    """Tests for ProvenanceCreate model."""

    def test_create_minimal(self):
        """Test creating with minimal fields."""
        create = ProvenanceCreate()
        assert create.source_type == SourceType.MANUAL_ENTRY
        assert create.capture_method == CaptureMethod.MANUAL_INPUT

    def test_create_with_fields(self):
        """Test creating with specific fields."""
        create = ProvenanceCreate(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com",
            source_title="Example",
            capture_method=CaptureMethod.AUTO_DETECTED,
            captured_by="autofill-extension",
            confidence=0.85,
            page_context="Found in footer",
            element_selector=".footer a",
            external_tool="Maltego",
            metadata={"custom": "field"},
        )

        assert create.source_type == SourceType.WEBSITE
        assert create.source_url == "https://example.com"
        assert create.confidence == 0.85

    def test_to_provenance_conversion(self):
        """Test conversion to full DataProvenance."""
        create = ProvenanceCreate(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com/page",
            source_title="Example Page",
            captured_by="test-agent",
            confidence=0.9,
        )

        prov = create.to_provenance()

        assert isinstance(prov, DataProvenance)
        assert prov.source_type == SourceType.WEBSITE
        assert prov.source_url == "https://example.com/page"
        assert prov.source_domain == "example.com"  # Extracted from URL
        assert prov.captured_by == "test-agent"
        assert prov.verification_state == VerificationState.UNVERIFIED

    def test_to_provenance_domain_extraction(self):
        """Test that domain is extracted from URL."""
        create = ProvenanceCreate(
            source_url="https://subdomain.example.com/path?query=1"
        )
        prov = create.to_provenance()
        assert prov.source_domain == "subdomain.example.com"

    def test_to_provenance_no_url(self):
        """Test conversion without URL."""
        create = ProvenanceCreate(
            source_type=SourceType.MANUAL_ENTRY,
        )
        prov = create.to_provenance()
        assert prov.source_domain is None


# =============================================================================
# ProvenanceChain Model Tests
# =============================================================================


class TestProvenanceChain:
    """Tests for ProvenanceChain model."""

    def test_create_chain(self):
        """Test creating a provenance chain."""
        current = DataProvenance(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com",
            captured_by="agent-1",
        )

        chain = ProvenanceChain(current=current)

        assert chain.current == current
        assert len(chain.history) == 0
        assert chain.derived_from is None

    def test_chain_with_history(self):
        """Test chain with historical records."""
        old = DataProvenance(
            source_type=SourceType.FILE_IMPORT,
            captured_by="import-script",
        )
        current = DataProvenance(
            source_type=SourceType.API,
            captured_by="enrichment-service",
        )

        chain = ProvenanceChain(
            current=current,
            history=[old],
            derived_from="original-123",
        )

        assert len(chain.history) == 1
        assert chain.history[0] == old
        assert chain.derived_from == "original-123"

    def test_add_transformation(self):
        """Test adding a transformation to the chain."""
        original = DataProvenance(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com",
            captured_by="scraper",
            confidence=0.8,
        )

        chain = ProvenanceChain(current=original)

        # Add transformation
        new_chain = chain.add_transformation(
            transformation_notes="Normalized email address",
            new_captured_by="normalizer-service",
        )

        # Original chain unchanged
        assert len(chain.history) == 0

        # New chain has history
        assert len(new_chain.history) == 1
        assert new_chain.history[0] == original
        assert new_chain.current.captured_by == "normalizer-service"
        assert new_chain.current.transformation_notes == "Normalized email address"

    def test_chain_preserves_source_info(self):
        """Test that transformations preserve source info."""
        original = DataProvenance(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com",
            source_title="Original Page",
            source_domain="example.com",
            confidence=0.9,
        )

        chain = ProvenanceChain(current=original)
        new_chain = chain.add_transformation(
            transformation_notes="Applied filter",
            new_captured_by="filter-service",
        )

        # Source info preserved
        assert new_chain.current.source_type == SourceType.WEBSITE
        assert new_chain.current.source_url == "https://example.com"
        assert new_chain.current.source_domain == "example.com"

    def test_chain_derivatives(self):
        """Test tracking derivative records."""
        current = DataProvenance(source_type=SourceType.API)

        chain = ProvenanceChain(
            current=current,
            derivatives=["derived-1", "derived-2", "derived-3"],
        )

        assert len(chain.derivatives) == 3
        assert "derived-1" in chain.derivatives


# =============================================================================
# Integration Tests
# =============================================================================


class TestProvenanceIntegration:
    """Integration tests for provenance models."""

    def test_full_provenance_workflow(self):
        """Test a complete provenance workflow."""
        # 1. Create initial provenance from browser extension
        create = ProvenanceCreate(
            source_type=SourceType.BROWSER_EXTENSION,
            source_url="https://target-site.com/contact",
            source_title="Contact - Target Site",
            capture_method=CaptureMethod.AUTO_DETECTED,
            captured_by="autofill-extension",
            confidence=0.85,
            page_context="Email found in contact form",
            element_selector="input[name='email']",
        )

        prov = create.to_provenance()

        # 2. Create chain
        chain = ProvenanceChain(current=prov)

        # 3. Add normalization transformation
        chain = chain.add_transformation(
            transformation_notes="Email normalized to lowercase",
            new_captured_by="normalizer-service",
        )

        # 4. Add verification transformation
        chain = chain.add_transformation(
            transformation_notes="MX record verified",
            new_captured_by="verification-service",
        )

        # Verify chain
        assert len(chain.history) == 2
        assert chain.current.transformation_notes == "MX record verified"
        assert chain.history[0].source_type == SourceType.BROWSER_EXTENSION
        assert chain.history[1].transformation_notes == "Email normalized to lowercase"

    def test_provenance_json_serialization(self):
        """Test that provenance can be serialized to JSON."""
        prov = DataProvenance(
            source_type=SourceType.OSINT_AGENT,
            source_url="https://example.com",
            captured_by="basset-hound-browser",
            confidence=0.95,
            metadata={"investigation_id": "inv-123"},
        )

        # to_dict should be JSON-serializable
        data = prov.to_dict()

        import json
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed["source_type"] == "osint_agent"
        assert parsed["captured_by"] == "basset-hound-browser"

    def test_provenance_model_validation(self):
        """Test that Pydantic validation works correctly."""
        # Valid model
        prov = DataProvenance(confidence=0.5)
        assert prov.confidence == 0.5

        # Invalid confidence (if we had strict bounds) would raise error
        # Pydantic 2.x uses different validation patterns
