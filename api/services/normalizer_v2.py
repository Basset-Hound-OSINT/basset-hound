"""
Conservative Data Normalization Service for Basset Hound OSINT Platform (v2).

This service provides conservative data normalization that:
1. ALWAYS preserves the original raw value
2. Only normalizes when transformations are UNAMBIGUOUS
3. Flags ambiguous data for human review
4. Supports hint fields for disambiguating ambiguous data

Key Principles:
- Never make assumptions that could corrupt data (e.g., assuming country codes)
- Store raw input alongside normalized forms
- Provide explicit confidence levels for normalizations
- Support optional hints to resolve ambiguity

Ambiguity Examples:
- Phone "(555) 123-4567" - Could be US (+1), UK, or any country
- Date "01/02/2024" - Could be Jan 2 or Feb 1 depending on locale
- Currency "$100" - Could be USD, CAD, AUD, etc.

Usage:
    from api.services.normalizer_v2 import get_normalizer_v2, ConservativeNormalizer

    normalizer = get_normalizer_v2()

    # Normalize with ambiguity detection
    result = normalizer.normalize_phone("(555) 123-4567")
    # result.is_ambiguous == True
    # result.ambiguity_reason == "No country code - could be any country"

    # Normalize with hint to resolve ambiguity
    result = normalizer.normalize_phone("(555) 123-4567", country_hint="US")
    # result.is_ambiguous == False
    # result.normalized == "+15551234567"
"""

import ipaddress
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, urlunparse

from api.models.orphan import IdentifierType


logger = logging.getLogger("basset_hound.normalizer_v2")


class AmbiguityLevel(Enum):
    """Level of ambiguity in normalized data."""
    NONE = "none"               # Unambiguous, safe to normalize
    LOW = "low"                 # Minor ambiguity, normalization likely correct
    MEDIUM = "medium"           # Moderate ambiguity, may need review
    HIGH = "high"               # Significant ambiguity, needs human review
    CRITICAL = "critical"       # Cannot normalize without additional info


class NormalizationConfidence(Enum):
    """Confidence level in the normalization result."""
    CERTAIN = "certain"         # 100% confident the normalization is correct
    HIGH = "high"               # Very likely correct (>90%)
    MEDIUM = "medium"           # Probably correct (60-90%)
    LOW = "low"                 # May be incorrect (<60%)
    UNKNOWN = "unknown"         # Cannot determine correctness


@dataclass
class NormalizedResultV2:
    """
    Result of a conservative normalization operation.

    Contains the original value, normalized value(s), ambiguity information,
    extracted components, and hints for resolution.

    Attributes:
        original: The original input value - NEVER modified.
        normalized: The normalized value (may be same as original if ambiguous).
        normalized_search: A search-friendly form (digits only, lowercase, etc.).
        is_valid: Whether the value passed validation for its type.
        is_ambiguous: Whether the normalization has ambiguity.
        ambiguity_level: The severity of ambiguity.
        ambiguity_reasons: List of reasons why the value is ambiguous.
        confidence: Confidence level in the normalization.
        components: Extracted parts of the identifier.
        alternative_forms: Other searchable forms of the identifier.
        hints_used: Any hints that were applied during normalization.
        hints_available: Hints that could resolve ambiguity.
        needs_review: Whether this data should be flagged for human review.
        errors: List of validation or normalization error messages.
    """
    original: str
    normalized: str
    normalized_search: str = ""
    is_valid: bool = True
    is_ambiguous: bool = False
    ambiguity_level: AmbiguityLevel = AmbiguityLevel.NONE
    ambiguity_reasons: List[str] = field(default_factory=list)
    confidence: NormalizationConfidence = NormalizationConfidence.CERTAIN
    components: Dict[str, Any] = field(default_factory=dict)
    alternative_forms: List[str] = field(default_factory=list)
    hints_used: Dict[str, Any] = field(default_factory=dict)
    hints_available: List[str] = field(default_factory=list)
    needs_review: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "original": self.original,
            "normalized": self.normalized,
            "normalized_search": self.normalized_search,
            "is_valid": self.is_valid,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_level": self.ambiguity_level.value,
            "ambiguity_reasons": self.ambiguity_reasons,
            "confidence": self.confidence.value,
            "components": self.components,
            "alternative_forms": self.alternative_forms,
            "hints_used": self.hints_used,
            "hints_available": self.hints_available,
            "needs_review": self.needs_review,
            "errors": self.errors,
        }


# Country code registry for phone number normalization
COUNTRY_CODES = {
    # North America
    "US": "1", "CA": "1", "MX": "52",
    # Europe
    "UK": "44", "GB": "44", "DE": "49", "FR": "33", "IT": "39", "ES": "34",
    "NL": "31", "BE": "32", "CH": "41", "AT": "43", "PL": "48", "SE": "46",
    "NO": "47", "DK": "45", "FI": "358", "IE": "353", "PT": "351", "GR": "30",
    "CZ": "420", "RO": "40", "HU": "36", "UA": "380", "RU": "7",
    # Asia Pacific
    "CN": "86", "JP": "81", "KR": "82", "IN": "91", "AU": "61", "NZ": "64",
    "SG": "65", "HK": "852", "TW": "886", "TH": "66", "MY": "60", "ID": "62",
    "PH": "63", "VN": "84",
    # Middle East
    "AE": "971", "SA": "966", "IL": "972", "TR": "90",
    # Africa
    "ZA": "27", "NG": "234", "EG": "20", "KE": "254",
    # South America
    "BR": "55", "AR": "54", "CL": "56", "CO": "57", "PE": "51",
}

# Reverse lookup: code to countries (some codes shared like 1 for US/CA)
CODE_TO_COUNTRIES = {}
for country, code in COUNTRY_CODES.items():
    if code not in CODE_TO_COUNTRIES:
        CODE_TO_COUNTRIES[code] = []
    CODE_TO_COUNTRIES[code].append(country)


# Currency symbols and their ambiguity
CURRENCY_SYMBOLS = {
    "$": ["USD", "CAD", "AUD", "NZD", "SGD", "HKD", "MXN", "ARS", "CLP"],  # Highly ambiguous
    "€": ["EUR"],  # Unambiguous
    "£": ["GBP"],  # Unambiguous
    "¥": ["JPY", "CNY"],  # Ambiguous (Japan vs China)
    "₹": ["INR"],  # Unambiguous
    "₩": ["KRW"],  # Unambiguous
    "₽": ["RUB"],  # Unambiguous
    "฿": ["THB", "BTC"],  # Ambiguous (Thai Baht vs Bitcoin)
    "₿": ["BTC"],  # Unambiguous (Bitcoin)
    "R$": ["BRL"],  # Unambiguous
    "kr": ["SEK", "NOK", "DKK"],  # Ambiguous (Scandinavian)
    "CHF": ["CHF"],  # Unambiguous
}


class ConservativeNormalizer:
    """
    Conservative normalizer that preserves raw data and flags ambiguity.

    Key differences from v1:
    - Never assumes country codes for phone numbers
    - Never assumes date formats
    - Never assumes currency types
    - Flags ambiguous data for review
    - Supports hint fields to resolve ambiguity
    """

    # Email regex pattern for validation
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Known cryptocurrency address patterns
    CRYPTO_PATTERNS = {
        "bitcoin": re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$'),
        "bitcoin_bech32": re.compile(r'^bc1[a-zA-HJ-NP-Z0-9]{25,90}$'),
        "bitcoin_taproot": re.compile(r'^bc1p[a-zA-HJ-NP-Z0-9]{58}$'),
        "ethereum": re.compile(r'^0x[a-fA-F0-9]{40}$'),
        "litecoin": re.compile(r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$'),
        "litecoin_bech32": re.compile(r'^ltc1[a-zA-HJ-NP-Z0-9]{25,90}$'),
        "ripple": re.compile(r'^r[0-9a-zA-Z]{24,34}$'),
        "monero": re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$'),
        "dogecoin": re.compile(r'^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$'),
        "cardano": re.compile(r'^addr1[a-zA-Z0-9]{50,}$'),
        "solana": re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'),
    }

    # MAC address pattern
    MAC_PATTERN = re.compile(
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|'
        r'^([0-9A-Fa-f]{4}\.){2}([0-9A-Fa-f]{4})$|'
        r'^[0-9A-Fa-f]{12}$'
    )

    def __init__(self):
        """Initialize the ConservativeNormalizer."""
        # Map identifier types to their normalization methods
        self._normalizers: Dict[str, Callable] = {
            IdentifierType.PHONE.value: self.normalize_phone,
            IdentifierType.EMAIL.value: self.normalize_email,
            IdentifierType.USERNAME.value: self.normalize_username,
            IdentifierType.DOMAIN.value: self.normalize_domain,
            IdentifierType.URL.value: self.normalize_url,
            IdentifierType.IP_ADDRESS.value: self.normalize_ip,
            IdentifierType.CRYPTO_ADDRESS.value: self.normalize_crypto,
            IdentifierType.SOCIAL_MEDIA.value: self.normalize_username,
            IdentifierType.MAC_ADDRESS.value: self.normalize_mac_address,
        }

    def normalize(
        self,
        value: str,
        identifier_type: Union[str, IdentifierType],
        **hints: Any
    ) -> NormalizedResultV2:
        """
        Main entry point for normalization - routes to appropriate normalizer.

        Args:
            value: The identifier value to normalize.
            identifier_type: The type of identifier.
            **hints: Optional hints to resolve ambiguity (e.g., country_hint="US").

        Returns:
            NormalizedResultV2 with normalization results and ambiguity info.
        """
        if not value:
            return NormalizedResultV2(
                original="",
                normalized="",
                is_valid=False,
                errors=["Empty value provided"]
            )

        # Convert enum to string if needed
        type_str = identifier_type.value if isinstance(identifier_type, IdentifierType) else str(identifier_type)

        # Get the appropriate normalizer
        normalizer_func = self._normalizers.get(type_str)

        if normalizer_func:
            try:
                return normalizer_func(value, **hints)
            except Exception as e:
                logger.error(f"Normalization error for {type_str}: {e}")
                return NormalizedResultV2(
                    original=value,
                    normalized=value.strip(),
                    is_valid=False,
                    errors=[f"Normalization failed: {str(e)}"]
                )

        # Default: basic trimming for unknown types
        trimmed = value.strip()
        return NormalizedResultV2(
            original=value,
            normalized=trimmed,
            normalized_search=trimmed.lower(),
            is_valid=bool(trimmed),
            components={"type": type_str}
        )

    def normalize_phone(
        self,
        phone: str,
        country_hint: Optional[str] = None,
        **kwargs
    ) -> NormalizedResultV2:
        """
        Normalize a phone number CONSERVATIVELY.

        Key principle: NEVER assume a country code if not explicitly provided.

        Args:
            phone: The phone number to normalize.
            country_hint: ISO country code (e.g., "US", "UK", "DE") to resolve ambiguity.

        Returns:
            NormalizedResultV2 with normalization and ambiguity info.
        """
        original = phone
        errors = []
        components = {}
        ambiguity_reasons = []
        hints_used = {}
        hints_available = ["country_hint"]

        if not phone or not phone.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty phone number"]
            )

        phone = phone.strip()

        # Check if starts with + (explicit country code)
        has_explicit_country_code = phone.startswith('+')

        # Extract all digits
        digits = re.sub(r'\D', '', phone)

        if not digits:
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["No digits found in phone number"]
            )

        # Validate length (typical phone numbers are 7-15 digits)
        is_valid = 7 <= len(digits) <= 15
        if not is_valid:
            if len(digits) < 7:
                errors.append("Phone number too short (minimum 7 digits)")
            else:
                errors.append("Phone number too long (maximum 15 digits)")

        # CONSERVATIVE NORMALIZATION
        if has_explicit_country_code:
            # Country code is explicit - safe to normalize
            normalized = '+' + digits
            normalized_search = digits  # Digits only for search

            # Try to identify the country from the code
            if len(digits) >= 10:
                # Check common country codes
                for code_len in [3, 2, 1]:
                    potential_code = digits[:code_len]
                    if potential_code in CODE_TO_COUNTRIES:
                        countries = CODE_TO_COUNTRIES[potential_code]
                        components['country_code'] = potential_code
                        components['local_number'] = digits[code_len:]
                        components['possible_countries'] = countries
                        if len(countries) > 1:
                            ambiguity_reasons.append(
                                f"Country code +{potential_code} is shared by: {', '.join(countries)}"
                            )
                        break

            components['has_country_code'] = True
            ambiguity_level = AmbiguityLevel.LOW if ambiguity_reasons else AmbiguityLevel.NONE
            confidence = NormalizationConfidence.HIGH

        elif country_hint:
            # Country hint provided - use it to normalize
            country_hint = country_hint.upper()
            if country_hint in COUNTRY_CODES:
                country_code = COUNTRY_CODES[country_hint]
                normalized = f"+{country_code}{digits}"
                normalized_search = digits
                components['country_code'] = country_code
                components['local_number'] = digits
                components['country_hint_applied'] = country_hint
                components['has_country_code'] = True
                hints_used['country_hint'] = country_hint
                ambiguity_level = AmbiguityLevel.NONE
                confidence = NormalizationConfidence.HIGH
            else:
                # Invalid hint - don't normalize
                normalized = digits
                normalized_search = digits
                ambiguity_reasons.append(f"Unknown country hint: {country_hint}")
                ambiguity_level = AmbiguityLevel.HIGH
                confidence = NormalizationConfidence.LOW
                components['has_country_code'] = False
        else:
            # NO COUNTRY CODE - DO NOT ASSUME!
            # Store digits only, flag as ambiguous
            normalized = digits  # Just the digits, no + prefix
            normalized_search = digits
            components['has_country_code'] = False
            components['local_number'] = digits
            ambiguity_reasons.append(
                "No country code provided - cannot determine country. "
                "Use country_hint to specify (e.g., country_hint='US' for +1)"
            )
            ambiguity_level = AmbiguityLevel.HIGH
            confidence = NormalizationConfidence.LOW

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized_search,
            is_valid=is_valid,
            is_ambiguous=bool(ambiguity_reasons),
            ambiguity_level=ambiguity_level,
            ambiguity_reasons=ambiguity_reasons,
            confidence=confidence,
            components=components,
            hints_used=hints_used,
            hints_available=hints_available,
            needs_review=ambiguity_level in [AmbiguityLevel.HIGH, AmbiguityLevel.CRITICAL],
            errors=errors
        )

    def normalize_email(self, email: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize an email address.

        Email normalization is UNAMBIGUOUS - safe to lowercase.

        Args:
            email: The email address to normalize.

        Returns:
            NormalizedResultV2 with normalized email.
        """
        original = email
        errors = []
        components = {}
        alternative_forms = []

        if not email or not email.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty email address"]
            )

        email = email.strip()

        # Lowercase is SAFE for email (RFC 5321 says local part is case-insensitive)
        normalized = email.lower()
        normalized_search = normalized

        # Validate basic format
        if '@' not in normalized:
            return NormalizedResultV2(
                original=original,
                normalized=normalized,
                normalized_search=normalized_search,
                is_valid=False,
                errors=["Invalid email format: missing @ symbol"]
            )

        parts = normalized.split('@')
        if len(parts) != 2:
            return NormalizedResultV2(
                original=original,
                normalized=normalized,
                normalized_search=normalized_search,
                is_valid=False,
                errors=["Invalid email format: multiple @ symbols"]
            )

        user_part, domain_part = parts

        if not user_part:
            errors.append("Invalid email format: empty user part")
        if not domain_part:
            errors.append("Invalid email format: empty domain part")
        if not errors and '.' not in domain_part:
            errors.append("Invalid email format: domain missing TLD")

        # Extract components
        components['domain'] = domain_part
        components['user'] = user_part

        # Handle plus-addressing (user+tag@domain.com)
        if '+' in user_part:
            plus_parts = user_part.split('+', 1)
            base_user = plus_parts[0]
            tag = plus_parts[1] if len(plus_parts) > 1 else ""

            components['base_user'] = base_user
            components['tag'] = tag

            # Add base email as alternative form for searching
            base_email = f"{base_user}@{domain_part}"
            alternative_forms.append(base_email)

        # Gmail dot handling - gmail ignores dots in the user part
        if domain_part in ['gmail.com', 'googlemail.com']:
            dotless_user = user_part.replace('.', '').split('+')[0]
            dotless_email = f"{dotless_user}@{domain_part}"
            if dotless_email != normalized and dotless_email not in alternative_forms:
                alternative_forms.append(dotless_email)
                components['gmail_canonical'] = dotless_email

        # Validate with regex
        is_valid = bool(self.EMAIL_PATTERN.match(normalized)) and not errors

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized_search,
            is_valid=is_valid,
            is_ambiguous=False,  # Email normalization is unambiguous
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            alternative_forms=alternative_forms,
            errors=errors
        )

    def normalize_username(self, username: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize a username/handle.

        Username normalization is UNAMBIGUOUS - safe to lowercase and remove @.

        Args:
            username: The username to normalize.

        Returns:
            NormalizedResultV2 with normalized username.
        """
        original = username
        errors = []

        if not username or not username.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty username"]
            )

        # Trim whitespace
        normalized = username.strip()

        # Remove leading @ symbols
        normalized = normalized.lstrip('@')

        # Lowercase
        normalized_lower = normalized.lower()

        # Validate
        is_valid = len(normalized) >= 1

        if not is_valid:
            errors.append("Username is empty after normalization")

        components = {
            'original_had_at': username.strip().startswith('@'),
            'length': len(normalized),
            'case_preserved': normalized,  # Keep original case for display
        }

        return NormalizedResultV2(
            original=original,
            normalized=normalized_lower,
            normalized_search=normalized_lower,
            is_valid=is_valid,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_domain(self, domain: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize a domain name.

        Domain normalization is UNAMBIGUOUS - safe to lowercase.

        Args:
            domain: The domain to normalize.

        Returns:
            NormalizedResultV2 with normalized domain.
        """
        original = domain
        errors = []

        if not domain or not domain.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty domain"]
            )

        normalized = domain.strip()

        # Remove protocol prefixes (case-insensitive)
        normalized = re.sub(r'^https?://', '', normalized, flags=re.IGNORECASE)

        # Remove www. prefix (case-insensitive)
        normalized = re.sub(r'^www\.', '', normalized, flags=re.IGNORECASE)

        # Remove trailing slashes and paths
        normalized = normalized.split('/')[0]

        # Remove any port number
        normalized = normalized.split(':')[0]

        # Lowercase
        normalized = normalized.lower()

        # Validate domain format
        is_valid = True
        if not normalized:
            is_valid = False
            errors.append("Empty domain after normalization")
        elif '.' not in normalized:
            is_valid = False
            errors.append("Invalid domain format: no TLD")
        else:
            if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', normalized):
                if len(normalized) == 1:
                    is_valid = False
                    errors.append("Domain too short")
                elif not re.match(r'^[a-z0-9.-]+$', normalized):
                    is_valid = False
                    errors.append("Invalid characters in domain")

        # Extract components
        parts = normalized.split('.') if normalized else []
        components = {
            'full_domain': normalized,
            'tld': parts[-1] if parts else "",
            'subdomain': '.'.join(parts[:-2]) if len(parts) > 2 else "",
            'main_domain': '.'.join(parts[-2:]) if len(parts) >= 2 else normalized,
        }

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized,
            is_valid=is_valid,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_url(self, url: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize a URL.

        URL normalization is MOSTLY unambiguous - domain is lowercased,
        but path case is preserved (paths can be case-sensitive).

        Args:
            url: The URL to normalize.

        Returns:
            NormalizedResultV2 with normalized URL.
        """
        original = url
        errors = []

        if not url or not url.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty URL"]
            )

        url = url.strip()

        # Add scheme if missing
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
            url = 'https://' + url

        try:
            parsed = urlparse(url)

            # Lowercase the scheme
            scheme = parsed.scheme.lower()

            # Lowercase the netloc (domain + port)
            netloc = parsed.netloc.lower()

            # Remove www. prefix from domain
            if netloc.startswith('www.'):
                netloc = netloc[4:]

            # Preserve path case but remove trailing slashes
            path = parsed.path.rstrip('/')

            # Keep query and fragment as-is
            query = parsed.query
            fragment = parsed.fragment

            # Reconstruct URL
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                '',
                query,
                fragment
            ))

            # Extract components
            components = {
                'scheme': scheme,
                'domain': netloc.split(':')[0],
                'port': netloc.split(':')[1] if ':' in netloc else None,
                'path': path,
                'query': query,
                'fragment': fragment,
            }

            # Create search-friendly version (domain only)
            normalized_search = netloc.split(':')[0]

            is_valid = bool(netloc)
            if not is_valid:
                errors.append("Invalid URL: no domain found")

        except Exception as e:
            normalized = url.lower()
            normalized_search = url.lower()
            is_valid = False
            errors.append(f"URL parsing error: {str(e)}")
            components = {}

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized_search,
            is_valid=is_valid,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_ip(self, ip: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize an IP address.

        IP normalization is UNAMBIGUOUS.

        Args:
            ip: The IP address to normalize.

        Returns:
            NormalizedResultV2 with normalized IP address.
        """
        original = ip
        errors = []

        if not ip or not ip.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty IP address"]
            )

        ip = ip.strip()

        # Pre-process to remove leading zeros from IPv4 octets
        if '.' in ip and ':' not in ip:
            try:
                octets = ip.split('.')
                if len(octets) == 4:
                    cleaned_octets = [str(int(o)) for o in octets]
                    ip = '.'.join(cleaned_octets)
            except ValueError:
                pass

        try:
            ip_obj = ipaddress.ip_address(ip)

            if ip_obj.version == 4:
                normalized = str(ip_obj)
                components = {
                    'version': 4,
                    'octets': normalized.split('.'),
                    'is_private': ip_obj.is_private,
                    'is_loopback': ip_obj.is_loopback,
                    'is_multicast': ip_obj.is_multicast,
                }
            else:
                full_ipv6 = ip_obj.exploded.lower()
                normalized = full_ipv6
                components = {
                    'version': 6,
                    'segments': full_ipv6.split(':'),
                    'compressed': str(ip_obj),
                    'is_private': ip_obj.is_private,
                    'is_loopback': ip_obj.is_loopback,
                    'is_multicast': ip_obj.is_multicast,
                }

            is_valid = True
            normalized_search = normalized

        except ValueError as e:
            normalized = ip.lower()
            normalized_search = normalized
            is_valid = False
            errors.append(f"Invalid IP address: {str(e)}")
            components = {}

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized_search,
            is_valid=is_valid,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_crypto(self, address: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize a cryptocurrency address.

        Crypto normalization is UNAMBIGUOUS - preserves case (checksum sensitive).

        Args:
            address: The cryptocurrency address to normalize.

        Returns:
            NormalizedResultV2 with normalized address.
        """
        original = address
        errors = []
        components = {}

        if not address or not address.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty cryptocurrency address"]
            )

        # Trim whitespace only - preserve case
        normalized = address.strip()

        # Detect cryptocurrency type
        crypto_type = None
        is_valid = False

        for ctype, pattern in self.CRYPTO_PATTERNS.items():
            if pattern.match(normalized):
                crypto_type = ctype
                is_valid = True
                break

        if crypto_type:
            components['crypto_type'] = crypto_type
            type_mapping = {
                'bitcoin': 'Bitcoin (Legacy)',
                'bitcoin_bech32': 'Bitcoin (Bech32/SegWit)',
                'bitcoin_taproot': 'Bitcoin (Taproot)',
                'ethereum': 'Ethereum',
                'litecoin': 'Litecoin (Legacy)',
                'litecoin_bech32': 'Litecoin (Bech32)',
                'ripple': 'Ripple/XRP',
                'monero': 'Monero',
                'dogecoin': 'Dogecoin',
                'cardano': 'Cardano',
                'solana': 'Solana',
            }
            components['crypto_name'] = type_mapping.get(crypto_type, crypto_type)
        else:
            is_valid = len(normalized) >= 20
            if not is_valid:
                errors.append("Unrecognized cryptocurrency address format")
            components['crypto_type'] = 'unknown'

        components['length'] = len(normalized)

        # Normalized search is lowercase for non-checksummed addresses
        if crypto_type in ['bitcoin', 'litecoin', 'dogecoin', 'ripple']:
            # These are case-insensitive for searching but case-sensitive for validation
            normalized_search = normalized.lower()
        else:
            normalized_search = normalized

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=normalized_search,
            is_valid=is_valid,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_mac_address(self, mac: str, **kwargs) -> NormalizedResultV2:
        """
        Normalize a MAC address.

        MAC normalization is UNAMBIGUOUS.

        Args:
            mac: The MAC address to normalize.

        Returns:
            NormalizedResultV2 with normalized MAC address.
        """
        original = mac
        errors = []

        if not mac or not mac.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty MAC address"]
            )

        mac = mac.strip()

        # Remove all separators and get hex digits
        hex_only = re.sub(r'[^0-9A-Fa-f]', '', mac)

        if len(hex_only) != 12:
            return NormalizedResultV2(
                original=original,
                normalized=mac.lower(),
                normalized_search=hex_only.lower(),
                is_valid=False,
                errors=[f"Invalid MAC address length: expected 12 hex digits, got {len(hex_only)}"]
            )

        # Format as colon-separated lowercase
        hex_lower = hex_only.lower()
        normalized = ':'.join(hex_lower[i:i+2] for i in range(0, 12, 2))

        components = {
            'oui': normalized[:8],  # First 3 octets (OUI - Organizationally Unique Identifier)
            'nic': normalized[9:],  # Last 3 octets (NIC - Network Interface Controller)
        }

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=hex_lower,
            is_valid=True,
            is_ambiguous=False,
            ambiguity_level=AmbiguityLevel.NONE,
            confidence=NormalizationConfidence.CERTAIN,
            components=components,
            errors=errors
        )

    def normalize_date(
        self,
        date_str: str,
        format_hint: Optional[str] = None,
        **kwargs
    ) -> NormalizedResultV2:
        """
        Normalize a date string CONSERVATIVELY.

        Dates are HIGHLY AMBIGUOUS without format hints:
        - "01/02/2024" could be Jan 2 (US) or Feb 1 (EU)
        - "2024-01-02" is unambiguous (ISO 8601)

        Args:
            date_str: The date string to normalize.
            format_hint: Date format hint (e.g., "MDY", "DMY", "YMD", or strftime format).

        Returns:
            NormalizedResultV2 with normalization and ambiguity info.
        """
        original = date_str
        errors = []
        ambiguity_reasons = []
        hints_used = {}
        hints_available = ["format_hint"]
        components = {}

        if not date_str or not date_str.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty date string"]
            )

        date_str = date_str.strip()

        # Check for ISO 8601 format (unambiguous)
        iso_patterns = [
            (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
            (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '%Y-%m-%dT%H:%M:%S'),
        ]

        for pattern, fmt in iso_patterns:
            if re.match(pattern, date_str):
                try:
                    parsed = datetime.strptime(date_str[:19], fmt)
                    normalized = parsed.strftime('%Y-%m-%d')
                    return NormalizedResultV2(
                        original=original,
                        normalized=normalized,
                        normalized_search=normalized,
                        is_valid=True,
                        is_ambiguous=False,
                        ambiguity_level=AmbiguityLevel.NONE,
                        confidence=NormalizationConfidence.CERTAIN,
                        components={
                            'year': parsed.year,
                            'month': parsed.month,
                            'day': parsed.day,
                            'format_detected': 'ISO 8601',
                        }
                    )
                except ValueError:
                    pass

        # Check for ambiguous formats
        ambiguous_patterns = [
            r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$',  # MM/DD/YYYY or DD/MM/YYYY
        ]

        for pattern in ambiguous_patterns:
            match = re.match(pattern, date_str)
            if match:
                part1, part2, year = match.groups()
                part1, part2 = int(part1), int(part2)

                # If year is 2 digits, expand it
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year

                # Check if format is determinable
                if part1 > 12:
                    # Must be DD/MM/YYYY (part1 is day)
                    day, month = part1, part2
                    confidence = NormalizationConfidence.HIGH
                    ambiguity_level = AmbiguityLevel.NONE
                elif part2 > 12:
                    # Must be MM/DD/YYYY (part2 is day)
                    month, day = part1, part2
                    confidence = NormalizationConfidence.HIGH
                    ambiguity_level = AmbiguityLevel.NONE
                else:
                    # AMBIGUOUS - both parts could be month or day
                    if format_hint:
                        hints_used['format_hint'] = format_hint
                        if format_hint.upper() in ['MDY', 'US']:
                            month, day = part1, part2
                            confidence = NormalizationConfidence.HIGH
                            ambiguity_level = AmbiguityLevel.NONE
                        elif format_hint.upper() in ['DMY', 'EU', 'UK']:
                            day, month = part1, part2
                            confidence = NormalizationConfidence.HIGH
                            ambiguity_level = AmbiguityLevel.NONE
                        else:
                            # Unknown hint
                            month, day = part1, part2  # Default to MDY
                            ambiguity_reasons.append(f"Unknown format hint: {format_hint}")
                            confidence = NormalizationConfidence.LOW
                            ambiguity_level = AmbiguityLevel.HIGH
                    else:
                        # No hint - flag as ambiguous, don't assume
                        ambiguity_reasons.append(
                            f"Date '{date_str}' is ambiguous: could be "
                            f"{part1:02d}/{part2:02d}/{year} (MM/DD/YYYY) or "
                            f"{part2:02d}/{part1:02d}/{year} (DD/MM/YYYY). "
                            "Use format_hint='MDY' or format_hint='DMY' to specify."
                        )
                        # Store as-is, don't try to parse
                        return NormalizedResultV2(
                            original=original,
                            normalized=date_str,  # Keep original
                            normalized_search=date_str,
                            is_valid=True,  # Valid format, just ambiguous
                            is_ambiguous=True,
                            ambiguity_level=AmbiguityLevel.HIGH,
                            ambiguity_reasons=ambiguity_reasons,
                            confidence=NormalizationConfidence.LOW,
                            components={
                                'part1': part1,
                                'part2': part2,
                                'year': year,
                                'possible_interpretations': [
                                    f"{year}-{part1:02d}-{part2:02d}",  # MDY
                                    f"{year}-{part2:02d}-{part1:02d}",  # DMY
                                ],
                            },
                            hints_available=hints_available,
                            needs_review=True
                        )

                # Try to create a valid date
                try:
                    parsed = datetime(int(year), month, day)
                    normalized = parsed.strftime('%Y-%m-%d')
                    return NormalizedResultV2(
                        original=original,
                        normalized=normalized,
                        normalized_search=normalized,
                        is_valid=True,
                        is_ambiguous=bool(ambiguity_reasons),
                        ambiguity_level=ambiguity_level,
                        ambiguity_reasons=ambiguity_reasons,
                        confidence=confidence,
                        components={
                            'year': parsed.year,
                            'month': parsed.month,
                            'day': parsed.day,
                        },
                        hints_used=hints_used,
                        hints_available=hints_available
                    )
                except ValueError as e:
                    errors.append(f"Invalid date: {e}")

        # Could not parse
        return NormalizedResultV2(
            original=original,
            normalized=date_str,
            normalized_search=date_str,
            is_valid=False,
            is_ambiguous=True,
            ambiguity_level=AmbiguityLevel.CRITICAL,
            ambiguity_reasons=["Could not parse date format"],
            confidence=NormalizationConfidence.UNKNOWN,
            hints_available=hints_available,
            errors=errors
        )

    def normalize_currency(
        self,
        amount_str: str,
        currency_hint: Optional[str] = None,
        **kwargs
    ) -> NormalizedResultV2:
        """
        Normalize a currency amount CONSERVATIVELY.

        Currency symbols are often AMBIGUOUS:
        - "$100" could be USD, CAD, AUD, etc.
        - "£100" is unambiguous (GBP)

        Args:
            amount_str: The currency amount string.
            currency_hint: ISO currency code hint (e.g., "USD", "CAD").

        Returns:
            NormalizedResultV2 with normalization and ambiguity info.
        """
        original = amount_str
        errors = []
        ambiguity_reasons = []
        hints_used = {}
        hints_available = ["currency_hint"]
        components = {}

        if not amount_str or not amount_str.strip():
            return NormalizedResultV2(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty currency string"]
            )

        amount_str = amount_str.strip()

        # Extract numeric value
        numeric_match = re.search(r'[\d,]+\.?\d*', amount_str)
        if not numeric_match:
            return NormalizedResultV2(
                original=original,
                normalized=amount_str,
                is_valid=False,
                errors=["No numeric value found"]
            )

        numeric_str = numeric_match.group().replace(',', '')
        try:
            amount = float(numeric_str)
        except ValueError:
            return NormalizedResultV2(
                original=original,
                normalized=amount_str,
                is_valid=False,
                errors=["Invalid numeric format"]
            )

        # Detect currency symbol
        symbol_match = re.search(r'^([^\d\s.,]+)|([^\d\s.,]+)$', amount_str)
        symbol = symbol_match.group().strip() if symbol_match else None

        if symbol and symbol in CURRENCY_SYMBOLS:
            possible_currencies = CURRENCY_SYMBOLS[symbol]
            if len(possible_currencies) == 1:
                # Unambiguous
                currency = possible_currencies[0]
                confidence = NormalizationConfidence.CERTAIN
                ambiguity_level = AmbiguityLevel.NONE
            else:
                # Ambiguous symbol
                if currency_hint and currency_hint.upper() in possible_currencies:
                    currency = currency_hint.upper()
                    hints_used['currency_hint'] = currency_hint
                    confidence = NormalizationConfidence.HIGH
                    ambiguity_level = AmbiguityLevel.NONE
                else:
                    ambiguity_reasons.append(
                        f"Symbol '{symbol}' could be: {', '.join(possible_currencies)}. "
                        f"Use currency_hint to specify (e.g., currency_hint='USD')"
                    )
                    currency = None
                    confidence = NormalizationConfidence.LOW
                    ambiguity_level = AmbiguityLevel.HIGH
        elif currency_hint:
            currency = currency_hint.upper()
            hints_used['currency_hint'] = currency_hint
            confidence = NormalizationConfidence.HIGH
            ambiguity_level = AmbiguityLevel.NONE
        else:
            currency = None
            ambiguity_reasons.append("No currency symbol or hint provided")
            confidence = NormalizationConfidence.LOW
            ambiguity_level = AmbiguityLevel.HIGH

        components['amount'] = amount
        components['symbol'] = symbol
        if currency:
            components['currency'] = currency

        # Normalized form
        if currency:
            normalized = f"{amount:.2f} {currency}"
        else:
            normalized = f"{amount:.2f}"

        return NormalizedResultV2(
            original=original,
            normalized=normalized,
            normalized_search=str(amount),
            is_valid=True,
            is_ambiguous=bool(ambiguity_reasons),
            ambiguity_level=ambiguity_level,
            ambiguity_reasons=ambiguity_reasons,
            confidence=confidence,
            components=components,
            hints_used=hints_used,
            hints_available=hints_available,
            needs_review=ambiguity_level in [AmbiguityLevel.HIGH, AmbiguityLevel.CRITICAL]
        )


# Module-level singleton
_normalizer_v2_instance: Optional[ConservativeNormalizer] = None


def get_normalizer_v2() -> ConservativeNormalizer:
    """
    Get or create the singleton ConservativeNormalizer instance.

    Returns:
        ConservativeNormalizer instance.
    """
    global _normalizer_v2_instance
    if _normalizer_v2_instance is None:
        _normalizer_v2_instance = ConservativeNormalizer()
    return _normalizer_v2_instance


def reset_normalizer_v2() -> None:
    """Reset the singleton instance (for testing)."""
    global _normalizer_v2_instance
    _normalizer_v2_instance = None
