"""
Unit tests for `api.services.normalizer_v2`.

Scope:
    Pure unit coverage of the ConservativeNormalizer v2 public surface. Verifies
    the documented intent of each public entry point (per the module docstring):
        - ALWAYS preserves the original raw value
        - Only normalizes when transformations are UNAMBIGUOUS
        - Flags ambiguous inputs (phones without country code, ambiguous dates,
          ambiguous currency symbols) for human review
        - Honors hint kwargs to resolve ambiguity

Tests are pure: no I/O, no DB, no network, no fixtures from conftest required.
Each public method gets a happy path plus one or two edge cases. The singleton
helpers (`get_normalizer_v2`, `reset_normalizer_v2`) and `NormalizedResultV2`
serialization are also covered.

Run (collection only — do not execute side-effects in this work zone):
    python3 -m pytest tests/test_normalizer_v2.py --collect-only
"""

import os
import sys

import pytest

# Make `api` importable when running tests from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.normalizer_v2 import (  # noqa: E402
    AmbiguityLevel,
    ConservativeNormalizer,
    NormalizationConfidence,
    NormalizedResultV2,
    get_normalizer_v2,
    reset_normalizer_v2,
)


@pytest.fixture
def normalizer():
    """Fresh ConservativeNormalizer instance per test (no shared state)."""
    return ConservativeNormalizer()


# ---------------------------------------------------------------------------
# NormalizedResultV2 dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizedResultV2:
    """The result dataclass and its serialization."""

    def test_defaults_are_safe(self):
        result = NormalizedResultV2(original="raw", normalized="raw")
        assert result.original == "raw"
        assert result.normalized == "raw"
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.ambiguity_level == AmbiguityLevel.NONE
        assert result.confidence == NormalizationConfidence.CERTAIN
        assert result.ambiguity_reasons == []
        assert result.components == {}
        assert result.alternative_forms == []
        assert result.hints_used == {}
        assert result.hints_available == []
        assert result.needs_review is False
        assert result.errors == []

    def test_to_dict_serializes_enums_as_values(self):
        result = NormalizedResultV2(
            original="x",
            normalized="x",
            ambiguity_level=AmbiguityLevel.HIGH,
            confidence=NormalizationConfidence.LOW,
        )
        d = result.to_dict()
        assert d["ambiguity_level"] == "high"
        assert d["confidence"] == "low"
        # Required keys present
        for key in (
            "original",
            "normalized",
            "normalized_search",
            "is_valid",
            "is_ambiguous",
            "ambiguity_level",
            "ambiguity_reasons",
            "confidence",
            "components",
            "alternative_forms",
            "hints_used",
            "hints_available",
            "needs_review",
            "errors",
        ):
            assert key in d


# ---------------------------------------------------------------------------
# Phone normalization — the canonical ambiguity test
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizePhone:
    """Phone normalization NEVER assumes a country code."""

    def test_empty_phone_invalid(self, normalizer):
        result = normalizer.normalize_phone("")
        assert result.is_valid is False
        assert "Empty" in result.errors[0]

    def test_whitespace_only_invalid(self, normalizer):
        result = normalizer.normalize_phone("   ")
        assert result.is_valid is False

    def test_no_digits_invalid(self, normalizer):
        result = normalizer.normalize_phone("abc-def")
        assert result.is_valid is False
        assert any("No digits" in e for e in result.errors)

    def test_no_country_code_is_ambiguous(self, normalizer):
        result = normalizer.normalize_phone("(555) 123-4567")
        assert result.normalized == "5551234567"
        assert result.is_ambiguous is True
        assert result.ambiguity_level == AmbiguityLevel.HIGH
        assert result.confidence == NormalizationConfidence.LOW
        assert result.needs_review is True
        assert result.components["has_country_code"] is False
        assert "country_hint" in result.hints_available

    def test_explicit_plus_country_code(self, normalizer):
        result = normalizer.normalize_phone("+1-555-123-4567")
        assert result.normalized == "+15551234567"
        assert result.is_valid is True
        assert result.components["has_country_code"] is True
        assert result.components.get("country_code") == "1"

    def test_country_hint_resolves_ambiguity(self, normalizer):
        result = normalizer.normalize_phone("(555) 123-4567", country_hint="US")
        assert result.normalized == "+15551234567"
        assert result.is_ambiguous is False
        assert result.ambiguity_level == AmbiguityLevel.NONE
        assert result.hints_used.get("country_hint") == "US"

    def test_invalid_country_hint_flagged(self, normalizer):
        result = normalizer.normalize_phone("5551234567", country_hint="ZZ")
        assert result.is_ambiguous is True
        assert result.confidence == NormalizationConfidence.LOW
        assert any("Unknown country hint" in r for r in result.ambiguity_reasons)

    @pytest.mark.parametrize(
        "phone,expected_digits",
        [
            ("(555) 123-4567", "5551234567"),
            ("555.123.4567", "5551234567"),
            ("555 123 4567", "5551234567"),
            ("555-123-4567", "5551234567"),
        ],
    )
    def test_various_separators(self, normalizer, phone, expected_digits):
        result = normalizer.normalize_phone(phone)
        assert result.normalized == expected_digits

    @pytest.mark.parametrize(
        "phone,is_valid",
        [
            ("123456", False),  # too short (<7)
            ("12345678901234567", False),  # too long (>15)
            ("5551234", True),  # exactly 7
        ],
    )
    def test_length_validation(self, normalizer, phone, is_valid):
        result = normalizer.normalize_phone(phone)
        assert result.is_valid is is_valid


# ---------------------------------------------------------------------------
# Email normalization — unambiguous
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeEmail:
    """Email normalization is documented as unambiguous (lowercase safe)."""

    def test_empty_email_invalid(self, normalizer):
        result = normalizer.normalize_email("")
        assert result.is_valid is False

    def test_lowercase_normalization(self, normalizer):
        result = normalizer.normalize_email("User@EXAMPLE.COM")
        assert result.normalized == "user@example.com"
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.ambiguity_level == AmbiguityLevel.NONE
        assert result.confidence == NormalizationConfidence.CERTAIN

    def test_missing_at_symbol(self, normalizer):
        result = normalizer.normalize_email("nope.example.com")
        assert result.is_valid is False
        assert any("missing @" in e.lower() for e in result.errors)

    def test_multiple_at_symbols(self, normalizer):
        result = normalizer.normalize_email("a@b@c.com")
        assert result.is_valid is False
        assert any("multiple @" in e.lower() for e in result.errors)

    def test_plus_addressing_produces_alternative_form(self, normalizer):
        result = normalizer.normalize_email("user+work@example.com")
        assert result.is_valid is True
        assert result.components["base_user"] == "user"
        assert result.components["tag"] == "work"
        assert "user@example.com" in result.alternative_forms

    def test_gmail_dotless_canonical(self, normalizer):
        result = normalizer.normalize_email("first.last+tag@gmail.com")
        assert result.is_valid is True
        # Gmail strips dots in the user part for the alternative/canonical form
        assert "firstlast@gmail.com" in result.alternative_forms
        assert result.components.get("gmail_canonical") == "firstlast@gmail.com"

    def test_domain_missing_tld(self, normalizer):
        result = normalizer.normalize_email("user@nohost")
        assert result.is_valid is False


# ---------------------------------------------------------------------------
# Username normalization — unambiguous
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeUsername:
    def test_empty_username_invalid(self, normalizer):
        result = normalizer.normalize_username("")
        assert result.is_valid is False

    def test_strips_leading_at_and_lowercases(self, normalizer):
        result = normalizer.normalize_username("@JohnDoe")
        assert result.normalized == "johndoe"
        assert result.components.get("original_had_at") is True

    def test_preserves_internal_chars(self, normalizer):
        result = normalizer.normalize_username("User_Name123")
        assert result.normalized == "user_name123"
        assert result.is_valid is True

    def test_trims_whitespace(self, normalizer):
        result = normalizer.normalize_username("  @Foo  ")
        assert result.normalized == "foo"
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# Domain normalization — unambiguous
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeDomain:
    def test_empty_domain_invalid(self, normalizer):
        result = normalizer.normalize_domain("")
        assert result.is_valid is False

    def test_strips_protocol_www_and_lowercases(self, normalizer):
        result = normalizer.normalize_domain("HTTPS://WWW.Example.COM/path")
        assert result.normalized == "example.com"
        assert result.is_valid is True

    def test_extracts_components(self, normalizer):
        result = normalizer.normalize_domain("sub.foo.example.com")
        assert result.components["tld"] == "com"
        assert result.components["main_domain"] == "example.com"
        assert result.components["subdomain"] == "sub.foo"

    def test_missing_tld_invalid(self, normalizer):
        result = normalizer.normalize_domain("localhost")
        assert result.is_valid is False


# ---------------------------------------------------------------------------
# URL normalization — mostly unambiguous (domain lowercased, path preserved)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeURL:
    def test_empty_url_invalid(self, normalizer):
        result = normalizer.normalize_url("")
        assert result.is_valid is False

    def test_domain_lowercase_path_case_preserved(self, normalizer):
        result = normalizer.normalize_url("HTTP://WWW.Example.COM/Path/Page")
        assert result.normalized == "http://example.com/Path/Page"
        assert result.is_valid is True

    def test_adds_https_when_scheme_missing(self, normalizer):
        result = normalizer.normalize_url("example.com/foo")
        assert result.normalized.startswith("https://")
        assert result.components.get("domain") == "example.com"

    def test_extracts_components(self, normalizer):
        result = normalizer.normalize_url(
            "https://api.example.com:8443/users/Jane?tab=x#frag"
        )
        assert result.is_valid is True
        assert result.components["scheme"] == "https"
        assert result.components["domain"] == "api.example.com"
        assert result.components["port"] == "8443"
        assert result.components["query"] == "tab=x"
        assert result.components["fragment"] == "frag"


# ---------------------------------------------------------------------------
# IP normalization — unambiguous
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeIP:
    def test_empty_ip_invalid(self, normalizer):
        result = normalizer.normalize_ip("")
        assert result.is_valid is False

    def test_ipv4_strips_leading_zeros(self, normalizer):
        result = normalizer.normalize_ip("192.168.001.001")
        assert result.normalized == "192.168.1.1"
        assert result.is_valid is True
        assert result.components["version"] == 4
        assert result.components["is_private"] is True

    def test_ipv6_loopback_expanded(self, normalizer):
        result = normalizer.normalize_ip("::1")
        assert result.is_valid is True
        assert result.components["version"] == 6
        assert result.normalized == "0000:0000:0000:0000:0000:0000:0000:0001"
        assert result.components["is_loopback"] is True

    def test_invalid_ip_flagged(self, normalizer):
        result = normalizer.normalize_ip("999.999.999.999")
        assert result.is_valid is False
        assert result.errors  # non-empty


# ---------------------------------------------------------------------------
# Crypto address normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeCrypto:
    def test_empty_crypto_invalid(self, normalizer):
        result = normalizer.normalize_crypto("")
        assert result.is_valid is False

    def test_ethereum_detected(self, normalizer):
        addr = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        result = normalizer.normalize_crypto(addr)
        assert result.is_valid is True
        assert result.components.get("crypto_type") == "ethereum"
        # Case is preserved for ETH (checksum sensitive)
        assert result.normalized == addr

    def test_bitcoin_legacy_detected(self, normalizer):
        result = normalizer.normalize_crypto("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert result.is_valid is True
        assert result.components.get("crypto_type") == "bitcoin"

    def test_whitespace_trimmed_case_preserved(self, normalizer):
        addr = "  0x742d35Cc6634C0532925a3b844Bc454e4438f44e  "
        result = normalizer.normalize_crypto(addr)
        assert result.normalized == addr.strip()

    def test_unrecognized_format_short(self, normalizer):
        result = normalizer.normalize_crypto("short")
        assert result.is_valid is False
        assert result.components.get("crypto_type") == "unknown"


# ---------------------------------------------------------------------------
# MAC address normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeMACAddress:
    def test_empty_mac_invalid(self, normalizer):
        result = normalizer.normalize_mac_address("")
        assert result.is_valid is False

    @pytest.mark.parametrize(
        "raw",
        [
            "00-1A-2B-3C-4D-5E",
            "00:1A:2B:3C:4D:5E",
            "001A.2B3C.4D5E",
            "001A2B3C4D5E",
        ],
    )
    def test_canonical_colon_lowercase(self, normalizer, raw):
        result = normalizer.normalize_mac_address(raw)
        assert result.normalized == "00:1a:2b:3c:4d:5e"
        assert result.is_valid is True

    def test_components_oui_nic_split(self, normalizer):
        result = normalizer.normalize_mac_address("00:1a:2b:3c:4d:5e")
        assert result.components["oui"] == "00:1a:2b"
        assert result.components["nic"] == "3c:4d:5e"

    def test_wrong_length_flagged(self, normalizer):
        result = normalizer.normalize_mac_address("00:1A:2B:3C:4D")
        assert result.is_valid is False
        assert any("Invalid MAC" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Date normalization — highly ambiguous without hint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeDate:
    def test_empty_date_invalid(self, normalizer):
        result = normalizer.normalize_date("")
        assert result.is_valid is False

    def test_iso_8601_unambiguous(self, normalizer):
        result = normalizer.normalize_date("2024-01-02")
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.normalized == "2024-01-02"
        assert result.confidence == NormalizationConfidence.CERTAIN
        assert result.components["format_detected"] == "ISO 8601"

    def test_ambiguous_us_eu_flagged(self, normalizer):
        result = normalizer.normalize_date("01/02/2024")
        assert result.is_ambiguous is True
        assert result.ambiguity_level == AmbiguityLevel.HIGH
        assert result.needs_review is True
        # Both interpretations stored
        interps = result.components.get("possible_interpretations", [])
        assert "2024-01-02" in interps
        assert "2024-02-01" in interps

    def test_format_hint_mdy(self, normalizer):
        result = normalizer.normalize_date("01/02/2024", format_hint="MDY")
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.normalized == "2024-01-02"
        assert result.hints_used.get("format_hint") == "MDY"

    def test_format_hint_dmy(self, normalizer):
        result = normalizer.normalize_date("01/02/2024", format_hint="DMY")
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.normalized == "2024-02-01"

    def test_part_over_12_resolves_unambiguously(self, normalizer):
        # 13 cannot be a month -> must be day -> DMY
        result = normalizer.normalize_date("13/05/2024")
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert result.normalized == "2024-05-13"

    def test_unparseable_date(self, normalizer):
        result = normalizer.normalize_date("not-a-date")
        assert result.is_valid is False
        assert result.ambiguity_level == AmbiguityLevel.CRITICAL


# ---------------------------------------------------------------------------
# Currency normalization — ambiguous symbols
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeCurrency:
    def test_empty_currency_invalid(self, normalizer):
        result = normalizer.normalize_currency("")
        assert result.is_valid is False

    def test_dollar_symbol_ambiguous(self, normalizer):
        result = normalizer.normalize_currency("$100")
        assert result.is_ambiguous is True
        assert result.ambiguity_level == AmbiguityLevel.HIGH
        assert result.needs_review is True
        assert any("could be" in r for r in result.ambiguity_reasons)

    def test_euro_symbol_unambiguous(self, normalizer):
        result = normalizer.normalize_currency("€99.50")
        assert result.is_valid is True
        assert result.is_ambiguous is False
        assert "EUR" in result.normalized
        assert result.components.get("currency") == "EUR"

    def test_currency_hint_resolves_dollar(self, normalizer):
        result = normalizer.normalize_currency("$100", currency_hint="CAD")
        assert result.is_ambiguous is False
        assert "CAD" in result.normalized
        assert result.hints_used.get("currency_hint") == "CAD"

    def test_no_numeric_value(self, normalizer):
        result = normalizer.normalize_currency("$$$")
        assert result.is_valid is False


# ---------------------------------------------------------------------------
# Main `normalize()` dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeDispatcher:
    def test_routes_string_type_to_phone(self, normalizer):
        result = normalizer.normalize("(555) 123-4567", "phone")
        assert result.normalized == "5551234567"

    def test_routes_enum_type_to_email(self, normalizer):
        from api.models.orphan import IdentifierType

        result = normalizer.normalize("User@EXAMPLE.COM", IdentifierType.EMAIL)
        assert result.normalized == "user@example.com"

    def test_passes_hints_through(self, normalizer):
        result = normalizer.normalize(
            "(555) 123-4567", "phone", country_hint="US"
        )
        assert result.normalized == "+15551234567"
        assert result.is_ambiguous is False

    def test_unknown_type_basic_trim(self, normalizer):
        result = normalizer.normalize("  some value  ", "unknown_type")
        assert result.normalized == "some value"
        assert result.is_valid is True
        assert result.components.get("type") == "unknown_type"

    def test_empty_value(self, normalizer):
        result = normalizer.normalize("", "phone")
        assert result.is_valid is False
        assert result.errors


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSingletonHelpers:
    def test_get_normalizer_v2_returns_same_instance(self):
        reset_normalizer_v2()
        a = get_normalizer_v2()
        b = get_normalizer_v2()
        assert a is b
        assert isinstance(a, ConservativeNormalizer)

    def test_reset_normalizer_v2_clears_singleton(self):
        a = get_normalizer_v2()
        reset_normalizer_v2()
        b = get_normalizer_v2()
        assert a is not b
