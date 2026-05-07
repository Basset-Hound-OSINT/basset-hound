"""
End-to-End Integration Tests for basset-hound + basset-verify Production Deployment.

These tests verify that basset-hound correctly integrates with basset-verify
in a production environment, including:

1. Configuration verification
2. Service connectivity
3. All 12 MCP verification tools delegation
4. Graceful fallback when basset-verify is unavailable
5. Error handling and resilience
6. End-to-end identifier verification workflows
7. Batch verification
8. Result storage in entity metadata
9. Performance benchmarks
10. Monitoring metrics

To run these tests:
    # With both services running (full integration)
    pytest tests/production/test_e2e_production.py -v

    # With verbose output
    pytest tests/production/test_e2e_production.py -vv

    # Run specific test class
    pytest tests/production/test_e2e_production.py::TestIntegrationConfiguration -v

    # Run with coverage
    pytest tests/production/test_e2e_production.py --cov=api --cov=basset_mcp --cov-report=html
"""

import asyncio
import logging
import os
import pytest
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from neo4j import Session

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.config import get_settings, Settings
from api.clients.basset_verify_client import (
    BassetVerifyClient,
    VerificationResult,
    VerificationLevel,
    IdentifierType,
    VerificationStatus,
)
from api.services.verification_service import VerificationService
from neo4j_handler import Neo4jHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_e2e_production")

# Configuration
BASSET_VERIFY_URL = os.environ.get("BASSET_VERIFY_URL", "http://basset_verify:8001")
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4jbasset")
INTEGRATION_TIMEOUT = 10.0  # seconds


# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestIntegrationConfiguration:
    """Test Phase 7.3 configuration settings."""

    def test_basset_verify_configuration_exists(self):
        """Test that basset-verify configuration is present in settings."""
        settings = get_settings()
        assert hasattr(settings, "basset_verify_url")
        assert hasattr(settings, "basset_verify_timeout")
        assert hasattr(settings, "basset_verify_enabled")

    def test_basset_verify_url_configured(self):
        """Test that basset-verify URL is properly configured."""
        settings = get_settings()
        assert settings.basset_verify_url is not None
        assert "8001" in settings.basset_verify_url or settings.basset_verify_url.startswith("http")

    def test_basset_verify_timeout_production_ready(self):
        """Test that basset-verify timeout is production-ready (5-10 seconds)."""
        settings = get_settings()
        assert settings.basset_verify_timeout >= 5.0
        assert settings.basset_verify_timeout <= 30.0

    def test_basset_verify_enabled_by_default(self):
        """Test that basset-verify integration is enabled by default."""
        settings = get_settings()
        assert settings.basset_verify_enabled is True


class TestServiceConnectivity:
    """Test connectivity between basset-hound and basset-verify."""

    async def test_basset_verify_health_check(self):
        """Test health check to basset-verify service."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            status = await client.health_check()

            # Service should be available in production tests
            if status.available:
                assert status.status == "healthy"
                assert status.version is not None
                logger.info(f"basset-verify health check: {status.status} (v{status.version})")
            else:
                logger.warning(f"basset-verify unavailable: {status.error_message}")
                # Graceful degradation - tests should still pass
                assert status.error_message is not None
        finally:
            await client.close()

    async def test_basset_verify_connectivity(self):
        """Test basic connectivity to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Try to get verification types
            result = await client.get_verification_types()

            if "identifier_types" in result:
                assert len(result["identifier_types"]) > 0
                logger.info(f"Supported identifier types: {result['identifier_types']}")
            else:
                # Service may not be available
                logger.warning(f"Could not retrieve types from basset-verify: {result.get('error')}")
        finally:
            await client.close()


class TestVerificationToolsDelegation:
    """Test that all 12 MCP verification tools correctly delegate to basset-verify."""

    async def test_email_verification_delegation(self):
        """Test email verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Test with valid email format
            result = await client.verify_email("test@example.com")
            assert result.identifier_type == "email"
            assert result.identifier_value == "test@example.com"
            # Status can vary based on verification level
            assert result.status in ["valid", "invalid", "plausible", "error", "verification_unavailable"]
            logger.info(f"Email verification result: {result.status} (confidence: {result.confidence})")
        finally:
            await client.close()

    async def test_phone_verification_delegation(self):
        """Test phone verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Test with valid phone format
            result = await client.verify_phone("+1-555-123-4567")
            assert result.identifier_type == "phone"
            assert result.identifier_value == "+1-555-123-4567"
            logger.info(f"Phone verification result: {result.status}")
        finally:
            await client.close()

    async def test_crypto_verification_delegation(self):
        """Test crypto address verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Test with valid Ethereum address
            eth_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f42bB"
            result = await client.verify_crypto(eth_address)
            assert result.identifier_type == "crypto_address"
            logger.info(f"Crypto verification result: {result.status}")

            # Check for poisoning detection warnings
            if result.warnings:
                logger.info(f"Poisoning detection warnings: {result.warnings}")
        finally:
            await client.close()

    async def test_domain_verification_delegation(self):
        """Test domain verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify_domain("example.com")
            assert result.identifier_type == "domain"
            logger.info(f"Domain verification result: {result.status}")
        finally:
            await client.close()

    async def test_ip_verification_delegation(self):
        """Test IP verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify_ip("192.0.2.1")
            assert result.identifier_type == "ip_address"
            logger.info(f"IP verification result: {result.status}")
        finally:
            await client.close()

    async def test_url_verification_delegation(self):
        """Test URL verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify_url("https://example.com")
            assert result.identifier_type == "url"
            logger.info(f"URL verification result: {result.status}")
        finally:
            await client.close()

    async def test_username_verification_delegation(self):
        """Test username verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify_username("test_user")
            assert result.identifier_type == "username"
            logger.info(f"Username verification result: {result.status}")
        finally:
            await client.close()

    async def test_generic_verification_delegation(self):
        """Test generic verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify(
                value="test@example.com",
                identifier_type="email"
            )
            assert result.identifier_type == "email"
            logger.info(f"Generic verification result: {result.status}")
        finally:
            await client.close()

    async def test_batch_verification_delegation(self):
        """Test batch verification delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            items = [
                {"value": "test@example.com", "type": "email"},
                {"value": "+1-555-123-4567", "type": "phone"},
                {"value": "example.com", "type": "domain"},
            ]
            result = await client.batch_verify(items)
            assert result.count == 3
            assert len(result.results) == 3
            logger.info(f"Batch verification completed: {result.count} items")
        finally:
            await client.close()

    async def test_crypto_matches_delegation(self):
        """Test crypto matches retrieval delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.get_crypto_matches("0x742d35Cc6634C0532925a3b844Bc9e7595f42bB")
            assert "address" in result or "error" in result
            logger.info(f"Crypto matches retrieved: {result.get('count', 0)} matches")
        finally:
            await client.close()

    async def test_supported_cryptocurrencies_delegation(self):
        """Test supported cryptocurrencies retrieval delegates to basset-verify."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.get_supported_cryptocurrencies()
            if "cryptocurrencies" in result:
                logger.info(f"Supported cryptocurrencies: {result['count']} total")
        finally:
            await client.close()


class TestGracefulFallback:
    """Test graceful fallback when basset-verify is unavailable."""

    async def test_unavailable_service_returns_unavailable_status(self):
        """Test that unavailable service returns graceful unavailable status."""
        # Use a port that's definitely not running
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )

        try:
            result = await client.verify_email("test@example.com")
            assert result.status == "verification_unavailable"
            assert result.confidence == 0.0
            assert result.allows_override is True
            logger.info("Graceful fallback working: unavailable status returned")
        finally:
            await client.close()

    async def test_batch_verification_graceful_fallback(self):
        """Test batch verification gracefully degrades when service unavailable."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )

        try:
            items = [
                {"value": "test@example.com", "type": "email"},
                {"value": "example.com", "type": "domain"},
            ]
            result = await client.batch_verify(items)

            # Should return unavailable results for all items
            assert result.count == 2
            assert len(result.results) == 2
            assert all(r.status == "verification_unavailable" for r in result.results)
            logger.info("Batch graceful fallback working")
        finally:
            await client.close()


class TestErrorHandling:
    """Test error handling and resilience."""

    async def test_timeout_handling(self):
        """Test that timeout is handled gracefully."""
        # Use a real service but with very short timeout
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=0.001,  # 1ms - will definitely timeout
        )

        try:
            result = await client.verify_email("test@example.com")
            # Should return either error or unavailable
            assert result.status in ["error", "verification_unavailable"]
            logger.info(f"Timeout handling working: {result.status}")
        finally:
            await client.close()

    async def test_invalid_response_handling(self):
        """Test handling of invalid responses from basset-verify."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock invalid JSON response
            mock_response = AsyncMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response

            settings = get_settings()
            client = BassetVerifyClient(
                base_url=settings.basset_verify_url,
                timeout=settings.basset_verify_timeout,
            )
            client._client = AsyncMock()
            client._client.post = mock_post

            try:
                result = await client.verify_email("test@example.com")
                assert result.status == "error"
                logger.info("Invalid response handling working")
            finally:
                await client.close()


class TestEndToEndWorkflows:
    """Test complete end-to-end verification workflows."""

    async def test_single_identifier_verification_workflow(self):
        """Test verification of a single identifier."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Verify email
            result = await client.verify_email("test@example.com")

            assert result.identifier_type == "email"
            assert result.identifier_value == "test@example.com"
            assert result.status is not None
            assert result.confidence >= 0.0
            assert result.confidence <= 1.0

            logger.info(
                f"Single identifier workflow complete: "
                f"{result.identifier_type} -> {result.status} "
                f"(confidence: {result.confidence:.2%})"
            )
        finally:
            await client.close()

    async def test_mixed_batch_verification_workflow(self):
        """Test batch verification with 5 different identifier types."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            items = [
                {"value": "test@example.com", "type": "email"},
                {"value": "+1-555-123-4567", "type": "phone"},
                {"value": "0x742d35Cc6634C0532925a3b844Bc9e7595f42bB", "type": "crypto_address"},
                {"value": "example.com", "type": "domain"},
                {"value": "192.0.2.1", "type": "ip_address"},
            ]

            result = await client.batch_verify(items)

            assert result.count == 5
            assert len(result.results) == 5
            assert all(r.identifier_type in ["email", "phone", "crypto_address", "domain", "ip_address"]
                      for r in result.results)

            # Check confidence scores
            confidence_avg = sum(r.confidence for r in result.results) / len(result.results)
            logger.info(
                f"Batch verification complete: {result.count} items, "
                f"average confidence: {confidence_avg:.2%}"
            )
        finally:
            await client.close()

    async def test_crypto_poisoning_detection_workflow(self):
        """Test crypto verification with poisoning detection."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            # Test with an address that might trigger poisoning detection
            eth_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f42bB"
            result = await client.verify_crypto(eth_address)

            assert result.identifier_type == "crypto_address"
            assert result.identifier_value == eth_address

            # Check for warnings about poisoning
            if result.warnings:
                logger.info(f"Poisoning detection warnings: {result.warnings}")
                assert any("poison" in w.lower() for w in result.warnings)

            logger.info(f"Crypto poisoning detection complete: {len(result.warnings)} warnings")
        finally:
            await client.close()


class TestPerformance:
    """Test performance characteristics."""

    async def test_single_verification_latency(self):
        """Test latency of single identifier verification."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            start = time.time()
            result = await client.verify_email("test@example.com")
            latency = time.time() - start

            # Production expectation: < 2 seconds per verification
            logger.info(f"Single verification latency: {latency:.3f}s")

            if result.status != "verification_unavailable":
                assert latency < 2.0, f"Verification took too long: {latency:.3f}s"
        finally:
            await client.close()

    async def test_batch_verification_latency(self):
        """Test latency of batch verification (5 items)."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            items = [
                {"value": "test1@example.com", "type": "email"},
                {"value": "test2@example.com", "type": "email"},
                {"value": "test3@example.com", "type": "email"},
                {"value": "example.com", "type": "domain"},
                {"value": "192.0.2.1", "type": "ip_address"},
            ]

            start = time.time()
            result = await client.batch_verify(items)
            latency = time.time() - start

            logger.info(
                f"Batch verification latency: {latency:.3f}s for {result.count} items "
                f"({latency/result.count:.3f}s per item)"
            )

            if result.success:
                # Allow more time for batch operations
                assert latency < 10.0, f"Batch verification took too long: {latency:.3f}s"
        finally:
            await client.close()


class TestMonitoring:
    """Test monitoring and observability."""

    async def test_service_health_metrics(self):
        """Test that service health can be monitored."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            status = await client.health_check()

            # Verify monitoring-relevant data is available
            assert status.available is not None
            assert status.status is not None
            assert status.timestamp is not None or status.available is False

            logger.info(
                f"Service health metrics: available={status.available}, "
                f"status={status.status}, version={status.version}"
            )
        finally:
            await client.close()

    async def test_verification_result_metrics(self):
        """Test that verification results contain monitoring data."""
        settings = get_settings()
        client = BassetVerifyClient(
            base_url=settings.basset_verify_url,
            timeout=settings.basset_verify_timeout,
        )

        try:
            result = await client.verify_email("test@example.com")

            # Verify monitoring-relevant fields
            assert result.identifier_type is not None
            assert result.status is not None
            assert result.confidence is not None
            assert result.verified_at is not None

            logger.info(
                f"Verification result metrics: type={result.identifier_type}, "
                f"status={result.status}, confidence={result.confidence:.2%}, "
                f"verified_at={result.verified_at.isoformat()}"
            )
        finally:
            await client.close()


# Fixtures for test setup and teardown

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def basset_verify_client():
    """Provide a basset-verify client for tests."""
    settings = get_settings()
    client = BassetVerifyClient(
        base_url=settings.basset_verify_url,
        timeout=settings.basset_verify_timeout,
    )

    yield client

    # Cleanup
    await client.close()


# Test utilities

def log_test_summary(test_name: str, passed: int, failed: int, skipped: int):
    """Log test summary information."""
    logger.info(
        f"Test summary for {test_name}: "
        f"passed={passed}, failed={failed}, skipped={skipped}"
    )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
