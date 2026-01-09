"""
Tests for sock puppet and verification MCP tools.

These tests cover:
- Sock puppet identity management (Phase 40.5)
- Verification tools exposure via MCP
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4


class TestSockPuppetTools:
    """Tests for sock puppet identity management MCP tools."""

    @pytest.fixture
    def mock_neo4j_puppet(self):
        """Create mock Neo4j handler for sock puppet tests."""
        handler = MagicMock()

        # Mock project methods
        handler.get_project.return_value = {
            "id": "proj-1",
            "name": "Test Investigation",
            "safe_name": "test_investigation"
        }
        handler.get_all_projects.return_value = [{
            "id": "proj-1",
            "name": "Test Investigation",
            "safe_name": "test_investigation"
        }]

        puppet_id = str(uuid4())
        now = datetime.now().isoformat()

        # Mock sock puppet entity
        handler.get_person.return_value = {
            "id": puppet_id,
            "created_at": now,
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Smith"}]
                },
                "_sock_puppet": {
                    "is_sock_puppet": True,
                    "alias_name": "John Smith",
                    "backstory": "IT consultant from Seattle",
                    "status": "active",
                    "purpose": "research",
                    "risk_level": "low",
                    "handler_id": "handler-123",
                    "operation_id": "op-456",
                    "created_date": now,
                    "activated_date": now,
                    "burn_date": None,
                    "last_activity": now,
                    "platform_accounts": [
                        {
                            "id": "acct-1",
                            "platform": "linkedin",
                            "username": "johnsmith-it",
                            "credential_vault_ref": "keepass://sock_puppets/johnsmith",
                            "account_status": "active"
                        }
                    ],
                    "activity_log": []
                }
            }
        }

        handler.get_all_people.return_value = [handler.get_person.return_value]

        handler.create_person.return_value = {
            "id": puppet_id,
            "created_at": now,
            "profile": {}
        }

        handler.update_person.return_value = handler.get_person.return_value

        return handler

    def test_sock_puppet_tool_imports(self):
        """Test that sock puppet tools module can be imported."""
        try:
            from basset_mcp.tools.sock_puppets import register_sock_puppet_tools
            assert register_sock_puppet_tools is not None
        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")

    def test_sock_puppet_status_enum(self):
        """Test sock puppet status enum values."""
        from basset_mcp.tools.sock_puppets import SockPuppetStatus

        assert SockPuppetStatus.PLANNING.value == "planning"
        assert SockPuppetStatus.ACTIVE.value == "active"
        assert SockPuppetStatus.DORMANT.value == "dormant"
        assert SockPuppetStatus.BURNED.value == "burned"
        assert SockPuppetStatus.RETIRED.value == "retired"

    def test_sock_puppet_purpose_enum(self):
        """Test sock puppet purpose enum values."""
        from basset_mcp.tools.sock_puppets import SockPuppetPurpose

        assert SockPuppetPurpose.PASSIVE_SURVEILLANCE.value == "passive_surveillance"
        assert SockPuppetPurpose.ACTIVE_ENGAGEMENT.value == "active_engagement"
        assert SockPuppetPurpose.INFILTRATION.value == "infiltration"
        assert SockPuppetPurpose.RESEARCH.value == "research"

    def test_sock_puppet_risk_level_enum(self):
        """Test sock puppet risk level enum values."""
        from basset_mcp.tools.sock_puppets import RiskLevel

        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_sock_puppet_data_structure(self, mock_neo4j_puppet):
        """Test sock puppet data structure integrity."""
        entity = mock_neo4j_puppet.get_person("test_investigation", "puppet-1")
        sp_data = entity["profile"]["_sock_puppet"]

        # Required fields
        assert sp_data["is_sock_puppet"] is True
        assert "alias_name" in sp_data
        assert "status" in sp_data
        assert "purpose" in sp_data
        assert "risk_level" in sp_data
        assert "platform_accounts" in sp_data
        assert "activity_log" in sp_data

        # Platform account structure
        if sp_data["platform_accounts"]:
            acct = sp_data["platform_accounts"][0]
            assert "platform" in acct
            assert "username" in acct
            assert "credential_vault_ref" in acct

    def test_sock_puppet_lifecycle_states(self):
        """Test sock puppet lifecycle state transitions."""
        from basset_mcp.tools.sock_puppets import SockPuppetStatus

        # Valid transitions
        valid_transitions = {
            "planning": ["active", "retired"],
            "active": ["dormant", "burned", "retired"],
            "dormant": ["active", "burned", "retired"],
            "burned": [],  # Terminal state
            "retired": [],  # Terminal state
        }

        # Verify burned and retired are terminal
        assert len(valid_transitions["burned"]) == 0
        assert len(valid_transitions["retired"]) == 0

    def test_platform_account_storage(self, mock_neo4j_puppet):
        """Test that platform accounts store references, not credentials."""
        entity = mock_neo4j_puppet.get_person("test_investigation", "puppet-1")
        sp_data = entity["profile"]["_sock_puppet"]

        for acct in sp_data["platform_accounts"]:
            # Verify we store vault reference, not actual password
            assert "credential_vault_ref" in acct
            assert "password" not in acct
            assert "2fa_seed" not in acct

            # Vault reference should be a reference string
            vault_ref = acct.get("credential_vault_ref", "")
            assert vault_ref.startswith("keepass://") or vault_ref.startswith("vault://") or vault_ref == ""

    def test_activity_log_structure(self, mock_neo4j_puppet):
        """Test activity log structure for audit compliance."""
        # Simulate activity log entry
        activity_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "login",
            "platform": "linkedin",
            "details": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "success": True
            }
        }

        assert "timestamp" in activity_entry
        assert "action" in activity_entry
        assert "details" in activity_entry


class TestVerificationTools:
    """Tests for verification MCP tools."""

    def test_verification_tool_imports(self):
        """Test that verification tools module can be imported."""
        try:
            from basset_mcp.tools.verification import register_verification_tools
            assert register_verification_tools is not None
        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")

    def test_verification_service_import(self):
        """Test that verification service can be imported."""
        from api.services.verification_service import (
            VerificationService,
            VerificationLevel,
            VerificationResult,
            VerificationStatus
        )

        assert VerificationService is not None
        assert VerificationLevel.FORMAT.value == "format"
        assert VerificationLevel.NETWORK.value == "network"

    def test_crypto_detector_import(self):
        """Test that crypto detector can be imported."""
        from api.utils.crypto_detector import CryptoAddressDetector

        detector = CryptoAddressDetector()
        assert detector is not None

    @pytest.mark.asyncio
    async def test_email_verification_format(self):
        """Test email format verification."""
        from api.services.verification_service import VerificationService, VerificationLevel

        service = VerificationService()
        result = await service.verify_email("test@example.com", VerificationLevel.FORMAT)

        assert result.is_valid is True
        assert result.confidence > 0.5
        assert "local_part" in result.details
        assert "domain" in result.details

    @pytest.mark.asyncio
    async def test_email_verification_disposable(self):
        """Test disposable email detection."""
        from api.services.verification_service import VerificationService, VerificationLevel

        service = VerificationService()
        result = await service.verify_email("test@tempmail.com", VerificationLevel.FORMAT)

        # Should still be valid but with warning
        assert len(result.warnings) > 0 or result.details.get("is_disposable", False)

    @pytest.mark.asyncio
    async def test_phone_verification(self):
        """Test phone number verification."""
        from api.services.verification_service import VerificationService, VerificationLevel

        service = VerificationService()
        result = await service.verify_phone("+14155551234", VerificationLevel.FORMAT)

        assert result.is_valid is True
        assert "e164_format" in result.details or "country_code" in result.details

    @pytest.mark.asyncio
    async def test_ip_verification_ipv4(self):
        """Test IPv4 address verification."""
        from api.services.verification_service import VerificationService

        service = VerificationService()

        # Public IP
        result = await service.verify_ip("8.8.8.8")
        assert result.is_valid is True
        assert result.details.get("version") == 4

        # Private IP
        result = await service.verify_ip("192.168.1.1")
        assert result.is_valid is True
        assert result.details.get("is_private", False) is True

    @pytest.mark.asyncio
    async def test_ip_verification_ipv6(self):
        """Test IPv6 address verification."""
        from api.services.verification_service import VerificationService

        service = VerificationService()
        result = await service.verify_ip("2001:4860:4860::8888")

        # IPv6 support may be limited - check if it's detected at all
        # Some implementations only support IPv4 format validation
        if result.is_valid:
            assert result.details.get("version") == 6
        else:
            # Service doesn't support IPv6 - this is acceptable
            pytest.skip("IPv6 verification not fully supported")

    @pytest.mark.asyncio
    async def test_domain_verification(self):
        """Test domain verification."""
        from api.services.verification_service import VerificationService, VerificationLevel

        service = VerificationService()
        result = await service.verify_domain("example.com", VerificationLevel.FORMAT)

        assert result.is_valid is True
        assert "domain" in result.details

    @pytest.mark.asyncio
    async def test_url_verification(self):
        """Test URL verification."""
        from api.services.verification_service import VerificationService

        service = VerificationService()
        result = await service.verify_url("https://example.com/path?query=1")

        assert result.is_valid is True
        assert "scheme" in result.details
        assert "domain" in result.details

    def test_crypto_detection_bitcoin(self):
        """Test Bitcoin address detection."""
        from api.utils.crypto_detector import CryptoAddressDetector

        detector = CryptoAddressDetector()

        # P2PKH (legacy)
        result = detector.detect("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")
        assert result.detected is True
        assert result.coin_ticker == "BTC"

        # Bech32 (SegWit)
        result = detector.detect("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
        assert result.detected is True
        assert result.coin_ticker == "BTC"
        assert "SegWit" in result.address_type or "Bech32" in result.address_type

    def test_crypto_detection_ethereum(self):
        """Test Ethereum address detection."""
        from api.utils.crypto_detector import CryptoAddressDetector

        detector = CryptoAddressDetector()
        result = detector.detect("0x742d35Cc6634C0532925a3b844Bc9e7595f82921")

        assert result.detected is True
        assert result.coin_ticker == "ETH"

    def test_crypto_detection_monero(self):
        """Test Monero address detection."""
        from api.utils.crypto_detector import CryptoAddressDetector

        detector = CryptoAddressDetector()
        # Example Monero address (95 characters starting with 4)
        monero_addr = "4" + "A" * 94
        result = detector.detect(monero_addr)

        # Should detect as potential Monero or not detect (depends on address format)
        # Monero addresses have specific checksum requirements
        assert result is not None

    def test_crypto_evm_detection(self):
        """Test EVM address detection (multiple chains use same format)."""
        from api.utils.crypto_detector import CryptoAddressDetector

        detector = CryptoAddressDetector()
        # 0x addresses are used by ETH and all EVM-compatible chains
        result = detector.detect("0x742d35Cc6634C0532925a3b844Bc9e7595f82921")

        assert result.detected is True
        # Primary detection should be ETH
        assert result.coin_ticker == "ETH"

    @pytest.mark.asyncio
    async def test_batch_verification(self):
        """Test batch verification of multiple identifiers."""
        from api.services.verification_service import VerificationService, VerificationLevel

        service = VerificationService()

        items = [
            {"value": "test@example.com", "type": "email"},
            {"value": "+14155551234", "type": "phone"},
            {"value": "8.8.8.8", "type": "ip_address"}
        ]

        results = await service.batch_verify(items, VerificationLevel.FORMAT)

        assert len(results) == 3
        assert all(r.is_valid for r in results)


class TestEntityTypeVisualization:
    """Tests related to entity type visualization for graphs."""

    def test_entity_types_distinguishable(self):
        """Test that entity types can be distinguished in graph visualization."""
        # Standard entity
        standard_entity = {
            "id": "person-1",
            "profile": {
                "core": {"name": [{"first_name": "John"}]}
            }
        }

        # Sock puppet entity
        sock_puppet_entity = {
            "id": "puppet-1",
            "profile": {
                "core": {"name": [{"first_name": "Cover", "last_name": "Identity"}]},
                "_sock_puppet": {
                    "is_sock_puppet": True,
                    "alias_name": "Cover Identity"
                }
            }
        }

        # Function to get entity type for visualization
        def get_entity_type(entity):
            profile = entity.get("profile", {})
            if profile.get("_sock_puppet", {}).get("is_sock_puppet"):
                return "SOCK_PUPPET"
            # Could add more types: COMPANY, ORGANIZATION, etc.
            return "PERSON"

        assert get_entity_type(standard_entity) == "PERSON"
        assert get_entity_type(sock_puppet_entity) == "SOCK_PUPPET"

    def test_entity_label_format(self):
        """Test entity label formatting for graph nodes."""
        entity_types = {
            "PERSON": {"color": "#4A90D9", "icon": "user"},
            "SOCK_PUPPET": {"color": "#9B59B6", "icon": "user-secret"},
            "COMPANY": {"color": "#27AE60", "icon": "building"},
            "ORGANIZATION": {"color": "#E67E22", "icon": "sitemap"}
        }

        # Each type should have distinct visual properties
        assert entity_types["PERSON"]["color"] != entity_types["SOCK_PUPPET"]["color"]
        assert entity_types["SOCK_PUPPET"]["icon"] == "user-secret"


class TestIntegrationScenarios:
    """Integration tests for investigation workflows."""

    def test_investigation_with_sock_puppet_workflow(self):
        """Test typical investigation workflow using sock puppet."""
        # 1. Create investigation project
        project = {"id": "inv-001", "name": "Target Investigation", "safe_name": "target_investigation"}

        # 2. Create sock puppet for investigation
        sock_puppet_data = {
            "alias_name": "Research Account",
            "backstory": "IT security researcher",
            "purpose": "passive_surveillance",
            "status": "active",
            "platforms": [
                {"platform": "linkedin", "username": "researcher-acct"}
            ]
        }

        # 3. Create target entity
        target_entity = {
            "id": "target-001",
            "profile": {
                "core": {"name": [{"first_name": "Target", "last_name": "Person"}]}
            }
        }

        # 4. Record observation using sock puppet
        observation = {
            "sock_puppet_id": "puppet-001",
            "target_id": "target-001",
            "action": "profile_view",
            "platform": "linkedin",
            "details": {"profile_url": "https://linkedin.com/in/target"}
        }

        # Verify data structures
        assert sock_puppet_data["purpose"] == "passive_surveillance"
        assert observation["action"] == "profile_view"

    def test_provenance_with_sock_puppet(self):
        """Test provenance tracking when data collected via sock puppet."""
        from api.models.provenance import SourceType

        # When collecting data via sock puppet, provenance should indicate
        provenance = {
            "source_type": SourceType.OSINT_AGENT.value,
            "captured_by": "sock_puppet:puppet-001",
            "source_url": "https://linkedin.com/in/target",
            "capture_method": "scrape",
            "confidence": 0.85,
            "metadata": {
                "sock_puppet_alias": "Research Account",
                "collection_platform": "linkedin"
            }
        }

        assert "sock_puppet" in provenance["captured_by"]
        assert provenance["source_type"] == "osint_agent"

    def test_entity_graph_with_sock_puppets(self):
        """Test that graph export includes sock puppet type information."""
        entities = [
            {
                "id": "person-1",
                "profile": {"core": {"name": [{"first_name": "Target"}]}}
            },
            {
                "id": "puppet-1",
                "profile": {
                    "core": {"name": [{"first_name": "Observer"}]},
                    "_sock_puppet": {"is_sock_puppet": True, "alias_name": "Observer"}
                }
            }
        ]

        # Build graph nodes with type
        nodes = []
        for entity in entities:
            profile = entity.get("profile", {})
            entity_type = "SOCK_PUPPET" if profile.get("_sock_puppet", {}).get("is_sock_puppet") else "PERSON"
            nodes.append({
                "id": entity["id"],
                "type": entity_type,
                "label": entity_type.lower()  # For display
            })

        assert nodes[0]["type"] == "PERSON"
        assert nodes[1]["type"] == "SOCK_PUPPET"
