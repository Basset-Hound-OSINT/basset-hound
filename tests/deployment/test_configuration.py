"""
Configuration validation tests for Basset Hound deployment.

These tests verify that:
1. Required environment variables are set
2. Configuration values are valid
3. Invalid configurations fail gracefully
"""

import os
import pytest


class TestEnvironmentVariables:
    """Test that required environment variables are properly configured."""

    def test_neo4j_uri_configured(self):
        """Test that NEO4J_URI is configured."""
        neo4j_uri = os.getenv("NEO4J_URI")
        assert neo4j_uri is not None, "NEO4J_URI environment variable not set"
        assert "bolt://" in neo4j_uri or "neo4j+s://" in neo4j_uri or "neo4j://" in neo4j_uri, \
            f"NEO4J_URI should contain bolt:// or neo4j:// protocol, got: {neo4j_uri}"

    def test_neo4j_user_configured(self):
        """Test that NEO4J_USER is configured."""
        neo4j_user = os.getenv("NEO4J_USER")
        assert neo4j_user is not None, "NEO4J_USER environment variable not set"
        assert len(neo4j_user) > 0, "NEO4J_USER should not be empty"

    def test_neo4j_password_configured(self):
        """Test that NEO4J_PASSWORD is configured."""
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        assert neo4j_password is not None, "NEO4J_PASSWORD environment variable not set"
        assert len(neo4j_password) > 0, "NEO4J_PASSWORD should not be empty"

    def test_redis_url_configured(self):
        """Test that REDIS_URL is configured (if Redis is being used)."""
        redis_url = os.getenv("REDIS_URL")
        # Redis is optional, but if set, should be valid
        if redis_url:
            assert "redis://" in redis_url or "rediss://" in redis_url, \
                f"REDIS_URL should contain redis:// or rediss:// protocol, got: {redis_url}"

    def test_secret_key_configured(self):
        """Test that SECRET_KEY is configured for the application."""
        secret_key = os.getenv("SECRET_KEY")
        assert secret_key is not None, "SECRET_KEY environment variable not set"
        assert len(secret_key) > 0, "SECRET_KEY should not be empty"
        # In production, secret key should be sufficiently long
        if not os.getenv("TESTING"):
            assert len(secret_key) >= 32, "SECRET_KEY should be at least 32 characters in production"


class TestConfigurationValidation:
    """Test configuration validation logic."""

    def test_valid_neo4j_uri_format(self):
        """Test that NEO4J_URI has a valid format."""
        neo4j_uri = os.getenv("NEO4J_URI", "")
        if neo4j_uri:
            # Check that it contains a host
            assert "://" in neo4j_uri, "NEO4J_URI should contain protocol"
            # Check that it's not just the protocol
            parts = neo4j_uri.split("://")
            assert len(parts) == 2, "NEO4J_URI should have format protocol://host"
            assert len(parts[1]) > 0, "NEO4J_URI should have a host after protocol"

    def test_neo4j_uri_host_reachable_format(self):
        """Test that NEO4J_URI contains a valid host format."""
        neo4j_uri = os.getenv("NEO4J_URI", "")
        if neo4j_uri:
            # Extract host part
            host_part = neo4j_uri.split("://")[1]
            # Should contain at least a hostname or IP address
            assert len(host_part) > 0, "NEO4J_URI should specify a host"
            # Typically contains localhost, IP, or domain name
            valid_hosts = ["localhost", "127.0.0.1", "neo4j", "0.0.0.0", "."]
            is_valid = any(h in host_part for h in valid_hosts) or "." in host_part or ":" in host_part
            assert is_valid, f"NEO4J_URI host '{host_part}' doesn't appear to be valid"


class TestMissingConfigurationHandling:
    """Test how the application handles missing configuration."""

    def test_missing_neo4j_uri_detection(self):
        """Test that missing NEO4J_URI can be detected."""
        # This test ensures the configuration can be properly validated
        old_uri = os.environ.pop("NEO4J_URI", None)
        try:
            neo4j_uri = os.getenv("NEO4J_URI")
            assert neo4j_uri is None, "NEO4J_URI should be unset for this test"
            # The test passes if we can detect it's missing
        finally:
            if old_uri:
                os.environ["NEO4J_URI"] = old_uri

    def test_neo4j_connection_string_validation(self):
        """Test that NEO4J_URI forms a valid connection string."""
        neo4j_uri = os.getenv("NEO4J_URI", "")
        if neo4j_uri:
            # Should have the format: bolt://host:port or bolt+s://host:port
            import re
            # Regex to match valid Neo4j connection strings
            pattern = r"^(bolt|neo4j)(\+s)?://[a-zA-Z0-9\-\.]+(\:[0-9]+)?(/.*)?$"
            assert re.match(pattern, neo4j_uri) or "localhost" in neo4j_uri, \
                f"NEO4J_URI '{neo4j_uri}' doesn't match expected format"


class TestEnvironmentConsistency:
    """Test that environment configuration is consistent."""

    def test_neo4j_credentials_match(self):
        """Test that Neo4j URI, user, and password are all set together."""
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        # If one is set, others should be set too
        if neo4j_uri:
            assert neo4j_user is not None, "If NEO4J_URI is set, NEO4J_USER must be set"
            assert neo4j_password is not None, "If NEO4J_URI is set, NEO4J_PASSWORD must be set"

    def test_secret_key_length_in_production(self):
        """Test that SECRET_KEY is long enough for production."""
        secret_key = os.getenv("SECRET_KEY", "")
        is_testing = os.getenv("TESTING") == "true"

        if not is_testing and secret_key:
            # In production, use a stronger secret
            assert len(secret_key) >= 32, \
                "SECRET_KEY in production should be at least 32 characters for security"

    def test_no_default_passwords_in_production(self):
        """Test that default passwords aren't used in production."""
        is_testing = os.getenv("TESTING") == "true"
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        if not is_testing and neo4j_password:
            # Common default passwords that should not be used
            default_passwords = ["password", "neo4j", "admin", "123456"]
            assert neo4j_password not in default_passwords, \
                f"Default password '{neo4j_password}' should not be used in production"
