"""
Tests for the Data Normalization Service.

Tests cover phone, email, username, domain, URL, IP, crypto address, and MAC address
normalization functionality.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPhoneNormalization:
    """Tests for phone number normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_basic_phone_normalization(self, normalizer):
        """Test basic phone number with parentheses and dashes."""
        result = normalizer.normalize_phone("(555) 123-4567")
        assert result.normalized == "5551234567"
        assert result.is_valid
        assert result.components.get("has_country_code") is False

    def test_phone_with_country_code(self, normalizer):
        """Test phone with country code."""
        result = normalizer.normalize_phone("+1-555-123-4567")
        assert result.normalized == "+15551234567"
        assert result.is_valid
        assert result.components.get("has_country_code") is True
        assert result.components.get("country_code") == "1"

    def test_phone_dots_separator(self, normalizer):
        """Test phone with dots as separator."""
        result = normalizer.normalize_phone("555.123.4567")
        assert result.normalized == "5551234567"
        assert result.is_valid

    def test_phone_spaces(self, normalizer):
        """Test phone with spaces."""
        result = normalizer.normalize_phone("555 123 4567")
        assert result.normalized == "5551234567"
        assert result.is_valid

    def test_phone_too_short(self, normalizer):
        """Test that short phone numbers are flagged."""
        result = normalizer.normalize_phone("123456")
        assert not result.is_valid
        assert "too short" in result.errors[0].lower()

    def test_phone_empty(self, normalizer):
        """Test empty phone number."""
        result = normalizer.normalize_phone("")
        assert not result.is_valid
        assert result.normalized == ""


class TestEmailNormalization:
    """Tests for email normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_basic_email_lowercase(self, normalizer):
        """Test email gets lowercased."""
        result = normalizer.normalize_email("User@EXAMPLE.COM")
        assert result.normalized == "user@example.com"
        assert result.is_valid
        assert result.components.get("user") == "user"
        assert result.components.get("domain") == "example.com"

    def test_email_plus_addressing(self, normalizer):
        """Test Gmail-style plus addressing."""
        result = normalizer.normalize_email("service+support@gmail.com")
        assert result.normalized == "service+support@gmail.com"
        assert result.is_valid
        assert result.components.get("user") == "service"
        assert result.components.get("tag") == "support"
        assert result.components.get("domain") == "gmail.com"
        # Alternative form should contain base email
        assert "service@gmail.com" in result.alternative_forms

    def test_email_multiple_plus_signs(self, normalizer):
        """Test email with multiple plus signs."""
        result = normalizer.normalize_email("user+tag1+tag2@example.com")
        assert result.normalized == "user+tag1+tag2@example.com"
        assert result.is_valid
        assert result.components.get("user") == "user"
        assert result.components.get("tag") == "tag1+tag2"

    def test_email_missing_at(self, normalizer):
        """Test email without @ symbol."""
        result = normalizer.normalize_email("userexample.com")
        assert not result.is_valid
        assert "missing @" in result.errors[0].lower()

    def test_email_empty(self, normalizer):
        """Test empty email."""
        result = normalizer.normalize_email("")
        assert not result.is_valid


class TestUsernameNormalization:
    """Tests for username normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_username_at_symbol_removal(self, normalizer):
        """Test @ symbol is removed from username."""
        result = normalizer.normalize_username("@JohnDoe")
        assert result.normalized == "johndoe"
        assert result.is_valid
        assert result.components.get("original_had_at") is True

    def test_username_lowercase(self, normalizer):
        """Test username is lowercased."""
        result = normalizer.normalize_username("User_Name123")
        assert result.normalized == "user_name123"
        assert result.is_valid

    def test_username_whitespace_trim(self, normalizer):
        """Test whitespace is trimmed."""
        result = normalizer.normalize_username("  @User_Name  ")
        assert result.normalized == "user_name"
        assert result.is_valid

    def test_username_empty(self, normalizer):
        """Test empty username."""
        result = normalizer.normalize_username("")
        assert not result.is_valid


class TestDomainNormalization:
    """Tests for domain normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_domain_protocol_removal(self, normalizer):
        """Test protocol is removed."""
        result = normalizer.normalize_domain("https://WWW.Example.COM/")
        assert result.normalized == "example.com"
        assert result.is_valid

    def test_domain_www_removal(self, normalizer):
        """Test www. is removed."""
        result = normalizer.normalize_domain("www.example.com")
        assert result.normalized == "example.com"
        assert result.is_valid

    def test_domain_lowercase(self, normalizer):
        """Test domain is lowercased."""
        result = normalizer.normalize_domain("EXAMPLE.COM")
        assert result.normalized == "example.com"
        assert result.is_valid

    def test_domain_subdomain(self, normalizer):
        """Test subdomain is preserved."""
        result = normalizer.normalize_domain("sub.domain.example.com")
        assert result.normalized == "sub.domain.example.com"
        assert result.is_valid
        assert result.components.get("subdomain") == "sub.domain"


class TestURLNormalization:
    """Tests for URL normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_url_domain_lowercase_path_preserved(self, normalizer):
        """Test domain is lowercased but path case is preserved."""
        result = normalizer.normalize_url("HTTP://WWW.Example.COM/Path/Page")
        assert result.normalized == "http://example.com/Path/Page"
        assert result.is_valid

    def test_url_trailing_slash_removal(self, normalizer):
        """Test trailing slashes are removed from path."""
        result = normalizer.normalize_url("https://example.com/path/")
        assert result.normalized == "https://example.com/path"
        assert result.is_valid

    def test_url_components_extracted(self, normalizer):
        """Test URL components are extracted."""
        result = normalizer.normalize_url("https://api.github.com/users/JohnDoe?tab=repos")
        assert result.is_valid
        assert result.components.get("scheme") == "https"
        assert result.components.get("domain") == "api.github.com"
        assert result.components.get("path") == "/users/JohnDoe"
        assert result.components.get("query") == "tab=repos"


class TestIPNormalization:
    """Tests for IP address normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_ipv4_leading_zeros_removed(self, normalizer):
        """Test IPv4 leading zeros are removed."""
        result = normalizer.normalize_ip("192.168.001.001")
        assert result.normalized == "192.168.1.1"
        assert result.is_valid
        assert result.components.get("version") == 4

    def test_ipv4_private(self, normalizer):
        """Test private IP detection."""
        result = normalizer.normalize_ip("192.168.1.1")
        assert result.is_valid
        assert result.components.get("is_private") is True

    def test_ipv6_expansion(self, normalizer):
        """Test IPv6 is expanded."""
        result = normalizer.normalize_ip("::1")
        assert result.is_valid
        assert result.components.get("version") == 6
        assert "0000:0000:0000:0000:0000:0000:0000:0001" == result.normalized

    def test_ip_invalid(self, normalizer):
        """Test invalid IP address."""
        result = normalizer.normalize_ip("999.999.999.999")
        assert not result.is_valid


class TestCryptoNormalization:
    """Tests for cryptocurrency address normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_ethereum_address(self, normalizer):
        """Test Ethereum address detection."""
        result = normalizer.normalize_crypto("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        assert result.is_valid
        assert result.components.get("crypto_type") == "ethereum"

    def test_bitcoin_legacy_address(self, normalizer):
        """Test Bitcoin legacy address detection."""
        result = normalizer.normalize_crypto("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert result.is_valid
        assert result.components.get("crypto_type") == "bitcoin"

    def test_crypto_whitespace_trimmed(self, normalizer):
        """Test whitespace is trimmed but case preserved."""
        address = "  0x742d35Cc6634C0532925a3b844Bc454e4438f44e  "
        result = normalizer.normalize_crypto(address)
        assert result.normalized == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


class TestMACAddressNormalization:
    """Tests for MAC address normalization."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_mac_dash_to_colon(self, normalizer):
        """Test MAC with dashes converted to colons."""
        result = normalizer.normalize_mac_address("00-1A-2B-3C-4D-5E")
        assert result.normalized == "00:1a:2b:3c:4d:5e"
        assert result.is_valid

    def test_mac_uppercase_to_lowercase(self, normalizer):
        """Test MAC is lowercased."""
        result = normalizer.normalize_mac_address("00:1A:2B:3C:4D:5E")
        assert result.normalized == "00:1a:2b:3c:4d:5e"
        assert result.is_valid

    def test_mac_plain_hex(self, normalizer):
        """Test MAC as plain hex string."""
        result = normalizer.normalize_mac_address("001A2B3C4D5E")
        assert result.normalized == "00:1a:2b:3c:4d:5e"
        assert result.is_valid

    def test_mac_components(self, normalizer):
        """Test MAC address components."""
        result = normalizer.normalize_mac_address("00:1a:2b:3c:4d:5e")
        assert result.is_valid
        assert result.components.get("oui") == "00:1a:2b"


class TestGenericNormalization:
    """Tests for the generic normalize() method."""

    @pytest.fixture
    def normalizer(self):
        from api.services.normalizer import DataNormalizer
        return DataNormalizer()

    def test_normalize_with_string_type(self, normalizer):
        """Test normalize with string type."""
        result = normalizer.normalize("(555) 123-4567", "phone")
        assert result.normalized == "5551234567"

    def test_normalize_with_enum_type(self, normalizer):
        """Test normalize with IdentifierType enum."""
        from api.models.orphan import IdentifierType
        result = normalizer.normalize("User@EXAMPLE.COM", IdentifierType.EMAIL)
        assert result.normalized == "user@example.com"

    def test_normalize_unknown_type(self, normalizer):
        """Test normalize with unknown type does basic trimming."""
        result = normalizer.normalize("  some value  ", "unknown_type")
        assert result.normalized == "some value"
        assert result.is_valid

    def test_normalize_empty_value(self, normalizer):
        """Test normalize with empty value."""
        result = normalizer.normalize("", "phone")
        assert not result.is_valid


class TestGetNormalizer:
    """Tests for the get_normalizer factory function."""

    def test_get_normalizer_singleton(self):
        """Test get_normalizer returns singleton instance."""
        from api.services.normalizer import get_normalizer
        normalizer1 = get_normalizer()
        normalizer2 = get_normalizer()
        assert normalizer1 is normalizer2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
