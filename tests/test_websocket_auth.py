"""
Tests for WebSocket Authentication (Phase 14: Enterprise Features)

Comprehensive test coverage for:
- WebSocketAuthenticator class
- WebSocketAuthResult dataclass
- API key authentication for WebSocket
- JWT token authentication for WebSocket
- Authentication rejection scenarios
- Connection with authentication metadata

Test Categories:
1. API Key Authentication Tests
2. JWT Token Authentication Tests
3. Authentication Rejection Tests
4. WebSocketAuthenticator Configuration Tests
5. Integration Tests with ConnectionManager
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.middleware.auth import (
    WebSocketAuthenticator,
    WebSocketAuthResult,
    WebSocketAuthError,
    AuthMethod,
    authenticate_websocket,
    extract_api_key_from_query,
    extract_api_key_from_header,
    extract_jwt_from_query,
    extract_jwt_from_header,
    validate_api_key_auth,
    validate_jwt_auth,
    default_authenticator,
    optional_authenticator,
    api_key_only_authenticator,
    jwt_only_authenticator,
    WS_AUTH_ENABLED,
)
from api.auth.jwt import create_access_token, TokenData
from api.auth.api_key import APIKey, APIKeyManager, FileBasedStorage
from api.auth.dependencies import User
from api.services.websocket_service import (
    ConnectionManager,
    WebSocketConnection,
    reset_websocket_services,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with configurable query params and headers."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {}
    ws.headers = {}
    return ws


@pytest.fixture
def mock_websocket_with_api_key(mock_websocket):
    """Create a mock WebSocket with API key in query params."""
    mock_websocket.query_params = {"api_key": "bh_test_api_key_12345678"}
    return mock_websocket


@pytest.fixture
def mock_websocket_with_jwt(mock_websocket):
    """Create a mock WebSocket with JWT in query params."""
    token = create_access_token({"sub": "testuser", "user_id": "user-123"})
    mock_websocket.query_params = {"token": token}
    return mock_websocket


@pytest.fixture
def mock_websocket_with_header_auth(mock_websocket):
    """Create a mock WebSocket with auth in headers."""
    token = create_access_token({"sub": "testuser", "user_id": "user-123"})
    mock_websocket.headers = {"authorization": f"Bearer {token}"}
    return mock_websocket


@pytest.fixture
def mock_websocket_with_api_key_header(mock_websocket):
    """Create a mock WebSocket with API key in headers."""
    mock_websocket.headers = {"x-api-key": "bh_test_api_key_12345678"}
    return mock_websocket


@pytest.fixture
def temp_api_key_storage(tmp_path):
    """Create a temporary API key storage for testing."""
    storage_path = tmp_path / "api_keys.json"
    return FileBasedStorage(str(storage_path))


@pytest.fixture
def api_key_manager(temp_api_key_storage):
    """Create an API key manager with temp storage."""
    return APIKeyManager(storage=temp_api_key_storage)


@pytest.fixture
def valid_api_key(api_key_manager):
    """Create a valid API key for testing."""
    raw_key, api_key = api_key_manager.create_api_key(
        name="Test Key",
        scopes=["read", "write"],
        created_by="test-user",
    )
    return raw_key, api_key


@pytest.fixture
def connection_manager():
    """Create a fresh connection manager."""
    reset_websocket_services()
    return ConnectionManager()


# ==================== Extraction Function Tests ====================


class TestExtractionFunctions:
    """Tests for credential extraction functions."""

    def test_extract_api_key_from_query(self, mock_websocket):
        """Test extracting API key from query parameters."""
        mock_websocket.query_params = {"api_key": "bh_test_key_123"}

        result = extract_api_key_from_query(mock_websocket)

        assert result == "bh_test_key_123"

    def test_extract_api_key_from_query_missing(self, mock_websocket):
        """Test extracting API key when not in query parameters."""
        mock_websocket.query_params = {}

        result = extract_api_key_from_query(mock_websocket)

        assert result is None

    def test_extract_api_key_from_header(self, mock_websocket):
        """Test extracting API key from headers."""
        mock_websocket.headers = {"x-api-key": "bh_test_key_456"}

        result = extract_api_key_from_header(mock_websocket)

        assert result == "bh_test_key_456"

    def test_extract_api_key_from_header_missing(self, mock_websocket):
        """Test extracting API key when not in headers."""
        mock_websocket.headers = {}

        result = extract_api_key_from_header(mock_websocket)

        assert result is None

    def test_extract_jwt_from_query(self, mock_websocket):
        """Test extracting JWT from query parameters."""
        mock_websocket.query_params = {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"}

        result = extract_jwt_from_query(mock_websocket)

        assert result == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"

    def test_extract_jwt_from_query_missing(self, mock_websocket):
        """Test extracting JWT when not in query parameters."""
        mock_websocket.query_params = {}

        result = extract_jwt_from_query(mock_websocket)

        assert result is None

    def test_extract_jwt_from_header_bearer(self, mock_websocket):
        """Test extracting JWT from Authorization header with Bearer prefix."""
        mock_websocket.headers = {"authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.test"}

        result = extract_jwt_from_header(mock_websocket)

        assert result == "eyJhbGciOiJIUzI1NiJ9.test"

    def test_extract_jwt_from_header_raw(self, mock_websocket):
        """Test extracting JWT from Authorization header without Bearer prefix."""
        mock_websocket.headers = {"authorization": "eyJhbGciOiJIUzI1NiJ9.test"}

        result = extract_jwt_from_header(mock_websocket)

        assert result == "eyJhbGciOiJIUzI1NiJ9.test"

    def test_extract_jwt_from_header_missing(self, mock_websocket):
        """Test extracting JWT when not in headers."""
        mock_websocket.headers = {}

        result = extract_jwt_from_header(mock_websocket)

        assert result is None


# ==================== WebSocketAuthResult Tests ====================


class TestWebSocketAuthResult:
    """Tests for WebSocketAuthResult dataclass."""

    def test_auth_result_authenticated(self):
        """Test creating an authenticated result."""
        user = User(
            user_id="user-123",
            username="testuser",
            scopes=["read", "write"],
            auth_type="jwt",
        )
        result = WebSocketAuthResult(
            authenticated=True,
            user=user,
            auth_method=AuthMethod.JWT,
        )

        assert result.authenticated is True
        assert result.user == user
        assert result.auth_method == AuthMethod.JWT
        assert result.error is None

    def test_auth_result_failed(self):
        """Test creating a failed authentication result."""
        result = WebSocketAuthResult(
            authenticated=False,
            auth_method=AuthMethod.API_KEY,
            error="Invalid API key",
            error_code="invalid_api_key",
        )

        assert result.authenticated is False
        assert result.user is None
        assert result.error == "Invalid API key"
        assert result.error_code == "invalid_api_key"

    def test_to_connection_metadata(self):
        """Test converting auth result to connection metadata."""
        user = User(
            user_id="user-123",
            username="testuser",
            scopes=["read"],
            auth_type="api_key",
            api_key_id="key-456",
        )
        result = WebSocketAuthResult(
            authenticated=True,
            user=user,
            auth_method=AuthMethod.API_KEY,
            metadata={"extra": "data"},
        )

        metadata = result.to_connection_metadata()

        assert metadata["authenticated"] is True
        assert metadata["auth_method"] == "api_key"
        assert metadata["user_id"] == "user-123"
        assert metadata["username"] == "testuser"
        assert metadata["scopes"] == ["read"]
        assert metadata["api_key_id"] == "key-456"
        assert metadata["extra"] == "data"
        assert "authenticated_at" in metadata


# ==================== JWT Authentication Tests ====================


class TestJWTAuthentication:
    """Tests for JWT token authentication."""

    def test_validate_jwt_auth_valid_token(self):
        """Test JWT authentication with valid token."""
        token = create_access_token(
            {"sub": "testuser", "user_id": "user-123"},
            scopes=["read", "write"],
        )

        result = validate_jwt_auth(token)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.JWT
        assert result.user is not None
        assert result.user.username == "testuser"
        assert result.user.user_id == "user-123"

    def test_validate_jwt_auth_invalid_token(self):
        """Test JWT authentication with invalid token."""
        result = validate_jwt_auth("invalid.token.here")

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.JWT
        assert result.error is not None
        assert "invalid" in result.error.lower() or "could not validate" in result.error.lower()

    def test_validate_jwt_auth_expired_token(self):
        """Test JWT authentication with expired token."""
        token = create_access_token(
            {"sub": "testuser", "user_id": "user-123"},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        result = validate_jwt_auth(token)

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.JWT

    @pytest.mark.asyncio
    async def test_authenticate_with_jwt_query_param(self, mock_websocket):
        """Test WebSocket authentication with JWT in query params."""
        token = create_access_token({"sub": "testuser", "user_id": "user-123"})
        mock_websocket.query_params = {"token": token}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.JWT

    @pytest.mark.asyncio
    async def test_authenticate_with_jwt_header(self, mock_websocket):
        """Test WebSocket authentication with JWT in header."""
        token = create_access_token({"sub": "testuser", "user_id": "user-123"})
        mock_websocket.headers = {"authorization": f"Bearer {token}"}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.JWT


# ==================== API Key Authentication Tests ====================


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_validate_api_key_auth_invalid_key(self):
        """Test API key authentication with invalid key."""
        result = validate_api_key_auth("bh_invalid_key_12345678")

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.API_KEY
        assert result.error is not None

    def test_validate_api_key_auth_invalid_format(self):
        """Test API key authentication with invalid format."""
        result = validate_api_key_auth("not_a_valid_key")

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.API_KEY

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_api_key(
        self, mock_websocket, api_key_manager, valid_api_key
    ):
        """Test WebSocket authentication with valid API key."""
        raw_key, api_key = valid_api_key
        mock_websocket.query_params = {"api_key": raw_key}

        with patch("api.middleware.auth.validate_api_key", return_value=api_key):
            result = validate_api_key_auth(raw_key)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.API_KEY
        assert result.user is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_api_key_header(
        self, mock_websocket, api_key_manager, valid_api_key
    ):
        """Test WebSocket authentication with API key in header."""
        raw_key, api_key = valid_api_key
        mock_websocket.headers = {"x-api-key": raw_key}
        mock_websocket.query_params = {}

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                with patch("api.middleware.auth.validate_api_key", return_value=api_key):
                    authenticator = WebSocketAuthenticator(require_auth=True, allow_jwt=False)
                    result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.API_KEY


# ==================== Authentication Rejection Tests ====================


class TestAuthenticationRejection:
    """Tests for authentication rejection scenarios."""

    @pytest.mark.asyncio
    async def test_reject_no_credentials(self, mock_websocket):
        """Test rejection when no credentials provided."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is False
        assert result.error is not None
        assert "required" in result.error.lower() or "provide" in result.error.lower()

    @pytest.mark.asyncio
    async def test_reject_invalid_jwt(self, mock_websocket):
        """Test rejection with invalid JWT token."""
        mock_websocket.query_params = {"token": "invalid.jwt.token"}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.JWT

    @pytest.mark.asyncio
    async def test_reject_invalid_api_key(self, mock_websocket):
        """Test rejection with invalid API key."""
        mock_websocket.query_params = {"api_key": "bh_invalid_key_12345678"}

        authenticator = WebSocketAuthenticator(require_auth=True, allow_jwt=False)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is False
        assert result.auth_method == AuthMethod.API_KEY

    @pytest.mark.asyncio
    async def test_allow_anonymous_when_not_required(self, mock_websocket):
        """Test allowing anonymous when auth not required."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        authenticator = WebSocketAuthenticator(require_auth=False, allow_anonymous=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is True
        assert result.user is not None
        assert result.user.auth_type == "anonymous"


# ==================== WebSocketAuthenticator Configuration Tests ====================


class TestWebSocketAuthenticatorConfig:
    """Tests for WebSocketAuthenticator configuration options."""

    @pytest.mark.asyncio
    async def test_auth_disabled_globally(self, mock_websocket):
        """Test that disabled auth allows all connections."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", False):
            result = await authenticator.authenticate(mock_websocket)

        assert result.authenticated is True
        assert result.auth_method == AuthMethod.DISABLED

    @pytest.mark.asyncio
    async def test_api_key_only_mode(self, mock_websocket):
        """Test authenticator in API key only mode."""
        token = create_access_token({"sub": "testuser", "user_id": "user-123"})
        mock_websocket.query_params = {"token": token}

        authenticator = WebSocketAuthenticator(
            require_auth=True,
            allow_api_key=True,
            allow_jwt=False,
        )

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        # Should fail because JWT is not allowed
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_jwt_only_mode(self, mock_websocket, valid_api_key):
        """Test authenticator in JWT only mode."""
        raw_key, _ = valid_api_key
        mock_websocket.query_params = {"api_key": raw_key}

        authenticator = WebSocketAuthenticator(
            require_auth=True,
            allow_api_key=False,
            allow_jwt=True,
        )

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate(mock_websocket)

        # Should fail because API key is not allowed
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_default_authenticator(self, mock_websocket):
        """Test default authenticator requires auth."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await default_authenticator.authenticate(mock_websocket)

        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_optional_authenticator(self, mock_websocket):
        """Test optional authenticator allows anonymous."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await optional_authenticator.authenticate(mock_websocket)

        assert result.authenticated is True


# ==================== Integration Tests with ConnectionManager ====================


class TestConnectionManagerIntegration:
    """Integration tests for authenticated connections with ConnectionManager."""

    @pytest.mark.asyncio
    async def test_connect_with_auth_info(self, connection_manager, mock_websocket):
        """Test connecting with authentication information."""
        connection = await connection_manager.connect(
            mock_websocket,
            connection_id="test-conn",
            authenticated=True,
            user_id="user-123",
            username="testuser",
            auth_method="jwt",
            scopes=["read", "write"],
        )

        assert connection.authenticated is True
        assert connection.user_id == "user-123"
        assert connection.username == "testuser"
        assert connection.auth_method == "jwt"
        assert "read" in connection.scopes
        assert "write" in connection.scopes

    @pytest.mark.asyncio
    async def test_connect_without_auth_info(self, connection_manager, mock_websocket):
        """Test connecting without authentication information."""
        connection = await connection_manager.connect(
            mock_websocket,
            connection_id="test-conn",
        )

        assert connection.authenticated is False
        assert connection.user_id is None
        assert connection.username is None

    @pytest.mark.asyncio
    async def test_get_authenticated_connections(self, connection_manager):
        """Test getting only authenticated connections."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        ws3 = MagicMock()
        ws3.accept = AsyncMock()
        ws3.send_text = AsyncMock()

        # Connect with mixed auth states
        await connection_manager.connect(
            ws1, connection_id="auth-1", authenticated=True, user_id="user-1"
        )
        await connection_manager.connect(
            ws2, connection_id="unauth-1", authenticated=False
        )
        await connection_manager.connect(
            ws3, connection_id="auth-2", authenticated=True, user_id="user-2"
        )

        auth_ids = connection_manager.get_authenticated_connection_ids()

        assert len(auth_ids) == 2
        assert "auth-1" in auth_ids
        assert "auth-2" in auth_ids
        assert "unauth-1" not in auth_ids

    @pytest.mark.asyncio
    async def test_get_connections_by_user_id(self, connection_manager):
        """Test getting connections for a specific user."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        ws3 = MagicMock()
        ws3.accept = AsyncMock()
        ws3.send_text = AsyncMock()

        # Connect same user from multiple devices
        await connection_manager.connect(
            ws1, connection_id="conn-1", authenticated=True, user_id="user-123"
        )
        await connection_manager.connect(
            ws2, connection_id="conn-2", authenticated=True, user_id="user-123"
        )
        await connection_manager.connect(
            ws3, connection_id="conn-3", authenticated=True, user_id="user-456"
        )

        user_conns = connection_manager.get_connections_by_user_id("user-123")

        assert len(user_conns) == 2
        assert "conn-1" in user_conns
        assert "conn-2" in user_conns
        assert "conn-3" not in user_conns

    @pytest.mark.asyncio
    async def test_get_connections_with_scope(self, connection_manager):
        """Test getting connections with a specific scope."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await connection_manager.connect(
            ws1, connection_id="admin-conn",
            authenticated=True, user_id="admin", scopes=["admin", "read"]
        )
        await connection_manager.connect(
            ws2, connection_id="user-conn",
            authenticated=True, user_id="user", scopes=["read"]
        )

        admin_conns = connection_manager.get_connections_with_scope("admin")
        read_conns = connection_manager.get_connections_with_scope("read")

        assert len(admin_conns) == 1
        assert "admin-conn" in admin_conns

        assert len(read_conns) == 2

    @pytest.mark.asyncio
    async def test_connection_has_scope(self, connection_manager, mock_websocket):
        """Test connection scope checking."""
        connection = await connection_manager.connect(
            mock_websocket,
            connection_id="test-conn",
            authenticated=True,
            scopes=["read", "write"],
        )

        assert connection.has_scope("read") is True
        assert connection.has_scope("write") is True
        assert connection.has_scope("admin") is False

    @pytest.mark.asyncio
    async def test_connection_wildcard_scope(self, connection_manager, mock_websocket):
        """Test connection with wildcard scope."""
        connection = await connection_manager.connect(
            mock_websocket,
            connection_id="test-conn",
            authenticated=True,
            scopes=["*"],
        )

        assert connection.has_scope("read") is True
        assert connection.has_scope("admin") is True
        assert connection.has_scope("anything") is True

    @pytest.mark.asyncio
    async def test_connection_confirmation_includes_auth_info(self, mock_websocket):
        """Test that connection confirmation message includes auth info."""
        manager = ConnectionManager()

        connection = await manager.connect(
            mock_websocket,
            connection_id="test-conn",
            authenticated=True,
            user_id="user-123",
            username="testuser",
        )

        # Check that send_text was called with auth info
        calls = mock_websocket.send_text.call_args_list
        assert len(calls) > 0

        # Parse the last sent message
        import json
        last_message = json.loads(calls[-1][0][0])
        assert last_message["type"] == "connected"
        assert last_message["data"]["authenticated"] is True
        assert last_message["data"]["user_id"] == "user-123"
        assert last_message["data"]["username"] == "testuser"


# ==================== WebSocketConnection Auth Methods Tests ====================


class TestWebSocketConnectionAuthMethods:
    """Tests for WebSocketConnection authentication methods."""

    def test_is_authenticated_true(self):
        """Test is_authenticated returns true when authenticated."""
        ws = MagicMock()
        connection = WebSocketConnection(
            connection_id="test",
            websocket=ws,
            authenticated=True,
            user_id="user-123",
        )

        assert connection.is_authenticated() is True

    def test_is_authenticated_false_no_user_id(self):
        """Test is_authenticated returns false without user_id."""
        ws = MagicMock()
        connection = WebSocketConnection(
            connection_id="test",
            websocket=ws,
            authenticated=True,
            user_id=None,
        )

        assert connection.is_authenticated() is False

    def test_is_authenticated_false_not_authenticated(self):
        """Test is_authenticated returns false when not authenticated."""
        ws = MagicMock()
        connection = WebSocketConnection(
            connection_id="test",
            websocket=ws,
            authenticated=False,
            user_id="user-123",
        )

        assert connection.is_authenticated() is False

    def test_get_auth_info(self):
        """Test getting auth info dictionary."""
        ws = MagicMock()
        connection = WebSocketConnection(
            connection_id="test",
            websocket=ws,
            authenticated=True,
            user_id="user-123",
            username="testuser",
            auth_method="jwt",
            scopes=["read", "write"],
        )

        auth_info = connection.get_auth_info()

        assert auth_info["authenticated"] is True
        assert auth_info["user_id"] == "user-123"
        assert auth_info["username"] == "testuser"
        assert auth_info["auth_method"] == "jwt"
        assert auth_info["scopes"] == ["read", "write"]

    def test_has_any_scope(self):
        """Test has_any_scope method."""
        ws = MagicMock()
        connection = WebSocketConnection(
            connection_id="test",
            websocket=ws,
            scopes=["read"],
        )

        assert connection.has_any_scope(["read", "write"]) is True
        assert connection.has_any_scope(["write", "admin"]) is False


# ==================== Convenience Function Tests ====================


class TestConvenienceFunctions:
    """Tests for convenience authentication functions."""

    @pytest.mark.asyncio
    async def test_authenticate_websocket_function(self, mock_websocket):
        """Test the authenticate_websocket convenience function."""
        token = create_access_token({"sub": "testuser", "user_id": "user-123"})
        mock_websocket.query_params = {"token": token}

        result = await authenticate_websocket(
            mock_websocket,
            require_auth=True,
            allow_jwt=True,
        )

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_websocket_optional(self, mock_websocket):
        """Test authenticate_websocket with optional auth."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticate_websocket(
                    mock_websocket,
                    require_auth=False,
                )

        # Without allow_anonymous, should fail even when not required
        assert result.authenticated is False


# ==================== Error Handling Tests ====================


class TestErrorHandling:
    """Tests for error handling in authentication."""

    def test_websocket_auth_error(self):
        """Test WebSocketAuthError exception."""
        error = WebSocketAuthError(
            message="Invalid credentials",
            code="invalid_credentials",
            close_code=1008,
        )

        assert error.message == "Invalid credentials"
        assert error.code == "invalid_credentials"
        assert error.close_code == 1008
        assert str(error) == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_authenticate_and_accept_success(self, mock_websocket):
        """Test authenticate_and_accept with successful auth."""
        token = create_access_token({"sub": "testuser", "user_id": "user-123"})
        mock_websocket.query_params = {"token": token}

        authenticator = WebSocketAuthenticator(require_auth=True)
        result = await authenticator.authenticate_and_accept(mock_websocket)

        assert result is not None
        assert result.authenticated is True
        mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_and_accept_failure(self, mock_websocket):
        """Test authenticate_and_accept with failed auth."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        authenticator = WebSocketAuthenticator(require_auth=True)

        with patch("api.middleware.auth.WS_AUTH_ENABLED", True):
            with patch("api.middleware.auth.AUTH_ENABLED", True):
                result = await authenticator.authenticate_and_accept(mock_websocket)

        assert result is None
        mock_websocket.close.assert_called_once()
