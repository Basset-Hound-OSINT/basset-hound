"""
Data Normalization Service for Basset Hound OSINT Platform.

This service standardizes data formats for identifiers (phone numbers, emails,
usernames, domains, URLs, IP addresses, crypto addresses) before storage in the
database. Normalization ensures consistent formats for easier searching and
matching across the platform.

Features:
- Phone number normalization with country code extraction
- Email normalization with plus-addressing handling
- Username, domain, and URL normalization
- IPv4 and IPv6 address normalization
- Crypto address validation and formatting
- Stores both original and normalized versions
- Extracts components for structured queries

Usage:
    from api.services.normalizer import get_normalizer, DataNormalizer

    normalizer = get_normalizer()

    # Normalize a phone number
    result = normalizer.normalize_phone("(555) 123-4567")
    # result.normalized == "5551234567"

    # Normalize any identifier by type
    result = normalizer.normalize("user@EXAMPLE.COM", "email")
    # result.normalized == "user@example.com"

    # Use with IdentifierType enum
    from api.models.orphan import IdentifierType
    result = normalizer.normalize("@JohnDoe", IdentifierType.USERNAME)
    # result.normalized == "johndoe"
"""

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse, urlunparse

from api.models.orphan import IdentifierType


logger = logging.getLogger("basset_hound.normalizer")


@dataclass
class NormalizedResult:
    """
    Result of a normalization operation.

    Contains the original value, normalized value, validation status,
    extracted components, and alternative searchable forms.

    Attributes:
        original: The original input value before normalization.
        normalized: The normalized/standardized value for storage and search.
        is_valid: Whether the value passed validation for its type.
        components: Extracted parts of the identifier (varies by type).
                   For phone: country_code, local_number
                   For email: user, domain, tag (if plus-addressing)
                   For URL: scheme, domain, path, query, fragment
                   For IP: version (4 or 6), octets/segments
        alternative_forms: Other searchable forms of the identifier.
                          For email with plus-addressing: base email without tag.
        errors: List of validation or normalization error messages.
    """
    original: str
    normalized: str
    is_valid: bool
    components: Dict[str, Any] = field(default_factory=dict)
    alternative_forms: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "original": self.original,
            "normalized": self.normalized,
            "is_valid": self.is_valid,
            "components": self.components,
            "alternative_forms": self.alternative_forms,
            "errors": self.errors,
        }


class DataNormalizer:
    """
    Service for normalizing identifier data in the OSINT platform.

    Provides normalization methods for various identifier types including
    phone numbers, emails, usernames, domains, URLs, IP addresses, and
    cryptocurrency addresses. Each normalizer extracts relevant components
    and validates the format.

    Usage:
        normalizer = DataNormalizer()

        # Normalize using type-specific method
        result = normalizer.normalize_phone("+1 (555) 123-4567")
        print(result.normalized)  # "+15551234567"
        print(result.components)  # {"country_code": "1", "local_number": "5551234567"}

        # Normalize using generic method with type
        result = normalizer.normalize("user@example.com", "email")

        # Normalize using IdentifierType enum
        result = normalizer.normalize("@JohnDoe", IdentifierType.USERNAME)
    """

    # Common TLDs for basic domain validation
    COMMON_TLDS = {
        "com", "org", "net", "edu", "gov", "mil", "int",
        "co", "io", "ai", "app", "dev", "info", "biz",
        "us", "uk", "ca", "au", "de", "fr", "jp", "cn", "ru", "br",
    }

    # Email regex pattern for validation
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Known cryptocurrency address patterns
    CRYPTO_PATTERNS = {
        "bitcoin": re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$'),
        "bitcoin_bech32": re.compile(r'^bc1[a-zA-HJ-NP-Z0-9]{25,90}$'),
        "ethereum": re.compile(r'^0x[a-fA-F0-9]{40}$'),
        "litecoin": re.compile(r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$'),
        "litecoin_bech32": re.compile(r'^ltc1[a-zA-HJ-NP-Z0-9]{25,90}$'),
        "ripple": re.compile(r'^r[0-9a-zA-Z]{24,34}$'),
        "monero": re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$'),
        "dogecoin": re.compile(r'^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$'),
    }

    # MAC address pattern
    MAC_PATTERN = re.compile(
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|'
        r'^([0-9A-Fa-f]{4}\.){2}([0-9A-Fa-f]{4})$|'
        r'^[0-9A-Fa-f]{12}$'
    )

    def __init__(self):
        """Initialize the DataNormalizer with method mappings."""
        # Map identifier types to their normalization methods
        self._normalizers: Dict[str, Callable[[str], NormalizedResult]] = {
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
        identifier_type: Union[str, IdentifierType]
    ) -> NormalizedResult:
        """
        Main entry point for normalization - routes to appropriate normalizer.

        Normalizes the given value based on its identifier type. If no specific
        normalizer exists for the type, returns the value with basic trimming.

        Args:
            value: The identifier value to normalize.
            identifier_type: The type of identifier (string or IdentifierType enum).

        Returns:
            NormalizedResult containing the normalized value and metadata.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize("(555) 123-4567", "phone")
            >>> result.normalized
            '5551234567'

            >>> result = normalizer.normalize("User@EXAMPLE.COM", IdentifierType.EMAIL)
            >>> result.normalized
            'user@example.com'
        """
        if not value:
            return NormalizedResult(
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
                return normalizer_func(value)
            except Exception as e:
                logger.error(f"Normalization error for {type_str}: {e}")
                return NormalizedResult(
                    original=value,
                    normalized=value.strip(),
                    is_valid=False,
                    errors=[f"Normalization failed: {str(e)}"]
                )

        # Default: basic trimming for unknown types
        trimmed = value.strip()
        return NormalizedResult(
            original=value,
            normalized=trimmed,
            is_valid=bool(trimmed),
            components={"type": type_str}
        )

    def normalize_phone(self, phone: str) -> NormalizedResult:
        """
        Normalize a phone number.

        Removes all non-digit characters except a leading '+' for country code.
        Extracts country code if present.

        Args:
            phone: The phone number to normalize.

        Returns:
            NormalizedResult with normalized phone and extracted components.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_phone("(555) 123-4567")
            >>> result.normalized
            '5551234567'

            >>> result = normalizer.normalize_phone("+1-555-123-4567")
            >>> result.normalized
            '+15551234567'
            >>> result.components
            {'country_code': '1', 'local_number': '5551234567', 'has_country_code': True}
        """
        original = phone
        errors = []
        components = {}

        if not phone or not phone.strip():
            return NormalizedResult(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty phone number"]
            )

        phone = phone.strip()

        # Check if starts with + (country code indicator)
        has_plus = phone.startswith('+')

        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        if not digits:
            return NormalizedResult(
                original=original,
                normalized="",
                is_valid=False,
                errors=["No digits found in phone number"]
            )

        # Build normalized number
        if has_plus:
            normalized = '+' + digits
            components['has_country_code'] = True

            # Extract country code
            if len(digits) >= 10:
                if digits.startswith('1') and len(digits) == 11:
                    components['country_code'] = '1'
                    components['local_number'] = digits[1:]
                elif len(digits) >= 11:
                    if digits.startswith('1'):
                        components['country_code'] = '1'
                        components['local_number'] = digits[1:]
                    else:
                        components['country_code'] = digits[:2]
                        components['local_number'] = digits[2:]
                else:
                    components['local_number'] = digits
            else:
                components['local_number'] = digits
        else:
            normalized = digits
            components['has_country_code'] = False
            components['local_number'] = digits

        # Validate length (typical phone numbers are 7-15 digits)
        is_valid = 7 <= len(digits) <= 15
        if not is_valid:
            if len(digits) < 7:
                errors.append("Phone number too short (minimum 7 digits)")
            else:
                errors.append("Phone number too long (maximum 15 digits)")

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_email(self, email: str) -> NormalizedResult:
        """
        Normalize an email address.

        Lowercases the entire email. Handles Gmail-style plus-addressing
        by storing both the original and the base email (without the tag).

        Args:
            email: The email address to normalize.

        Returns:
            NormalizedResult with normalized email and extracted components.
            For plus-addressed emails, alternative_forms contains the base email.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_email("User@EXAMPLE.COM")
            >>> result.normalized
            'user@example.com'

            >>> result = normalizer.normalize_email("service+support@gmail.com")
            >>> result.normalized
            'service+support@gmail.com'
            >>> result.alternative_forms
            ['service@gmail.com']
        """
        original = email
        errors = []
        components = {}
        alternative_forms = []

        if not email or not email.strip():
            return NormalizedResult(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty email address"]
            )

        email = email.strip()

        # Lowercase the entire email
        normalized = email.lower()

        # Validate basic format
        if '@' not in normalized:
            return NormalizedResult(
                original=original,
                normalized=normalized,
                is_valid=False,
                errors=["Invalid email format: missing @ symbol"]
            )

        parts = normalized.split('@')
        if len(parts) != 2:
            return NormalizedResult(
                original=original,
                normalized=normalized,
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

        # Handle plus-addressing (user+tag@domain.com)
        if '+' in user_part:
            plus_parts = user_part.split('+', 1)
            base_user = plus_parts[0]
            tag = plus_parts[1] if len(plus_parts) > 1 else ""

            components['user'] = base_user
            components['tag'] = tag
            components['base_user'] = base_user
            components['full_user'] = user_part

            # Add base email as alternative form
            base_email = f"{base_user}@{domain_part}"
            alternative_forms.append(base_email)
        else:
            components['user'] = user_part

        # Validate with regex
        is_valid = bool(self.EMAIL_PATTERN.match(normalized)) and not errors

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            alternative_forms=alternative_forms,
            errors=errors
        )

    def normalize_username(self, username: str) -> NormalizedResult:
        """
        Normalize a username/handle.

        Lowercases the username, removes leading @ symbols, and trims whitespace.

        Args:
            username: The username to normalize.

        Returns:
            NormalizedResult with normalized username.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_username("@JohnDoe")
            >>> result.normalized
            'johndoe'
        """
        original = username
        errors = []

        if not username or not username.strip():
            return NormalizedResult(
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
        normalized = normalized.lower()

        # Validate
        is_valid = len(normalized) >= 1

        if not is_valid:
            errors.append("Username is empty after normalization")

        components = {
            'original_had_at': username.strip().startswith('@'),
            'length': len(normalized)
        }

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_domain(self, domain: str) -> NormalizedResult:
        """
        Normalize a domain name.

        Lowercases the domain, removes http://, https://, and www. prefixes,
        and removes trailing slashes.

        Args:
            domain: The domain to normalize.

        Returns:
            NormalizedResult with normalized domain.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_domain("https://WWW.Example.COM/")
            >>> result.normalized
            'example.com'
        """
        original = domain
        errors = []

        if not domain or not domain.strip():
            return NormalizedResult(
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

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_url(self, url: str) -> NormalizedResult:
        """
        Normalize a URL.

        Lowercases the domain portion while preserving path case (paths can be
        case-sensitive). Normalizes protocol to lowercase and removes trailing
        slashes from paths.

        Args:
            url: The URL to normalize.

        Returns:
            NormalizedResult with normalized URL and extracted components.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_url("HTTP://WWW.Example.COM/Path/Page")
            >>> result.normalized
            'http://example.com/Path/Page'
        """
        original = url
        errors = []

        if not url or not url.strip():
            return NormalizedResult(
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

            is_valid = bool(netloc)
            if not is_valid:
                errors.append("Invalid URL: no domain found")

        except Exception as e:
            normalized = url.lower()
            is_valid = False
            errors.append(f"URL parsing error: {str(e)}")
            components = {}

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_ip(self, ip: str) -> NormalizedResult:
        """
        Normalize an IP address.

        For IPv4: Validates format and removes leading zeros from octets.
        For IPv6: Expands to full format and lowercases.

        Args:
            ip: The IP address to normalize.

        Returns:
            NormalizedResult with normalized IP address.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_ip("192.168.001.001")
            >>> result.normalized
            '192.168.1.1'
        """
        original = ip
        errors = []

        if not ip or not ip.strip():
            return NormalizedResult(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty IP address"]
            )

        ip = ip.strip()

        # Pre-process to remove leading zeros from IPv4 octets
        # (Python's ipaddress library doesn't accept leading zeros)
        if '.' in ip and ':' not in ip:
            # Looks like IPv4
            try:
                octets = ip.split('.')
                if len(octets) == 4:
                    # Remove leading zeros from each octet
                    cleaned_octets = [str(int(o)) for o in octets]
                    ip = '.'.join(cleaned_octets)
            except ValueError:
                pass  # Let ipaddress handle the error

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

        except ValueError as e:
            normalized = ip.lower()
            is_valid = False
            errors.append(f"Invalid IP address: {str(e)}")
            components = {}

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_crypto(self, address: str) -> NormalizedResult:
        """
        Normalize a cryptocurrency address.

        Preserves case (Bitcoin addresses are case-sensitive for checksum).
        Trims whitespace and validates format against known patterns.

        Args:
            address: The cryptocurrency address to normalize.

        Returns:
            NormalizedResult with normalized address and detected type.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_crypto("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
            >>> result.components.get('crypto_type')
            'ethereum'
        """
        original = address
        errors = []
        components = {}

        if not address or not address.strip():
            return NormalizedResult(
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
                'ethereum': 'Ethereum',
                'litecoin': 'Litecoin (Legacy)',
                'litecoin_bech32': 'Litecoin (Bech32)',
                'ripple': 'Ripple/XRP',
                'monero': 'Monero',
                'dogecoin': 'Dogecoin',
            }
            components['crypto_name'] = type_mapping.get(crypto_type, crypto_type)
        else:
            # Unknown format but still valid for storage
            is_valid = len(normalized) >= 20
            if not is_valid:
                errors.append("Unrecognized cryptocurrency address format")
            components['crypto_type'] = 'unknown'

        components['length'] = len(normalized)

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=is_valid,
            components=components,
            errors=errors
        )

    def normalize_mac_address(self, mac: str) -> NormalizedResult:
        """
        Normalize a MAC address.

        Converts to lowercase colon-separated format (aa:bb:cc:dd:ee:ff).

        Args:
            mac: The MAC address to normalize.

        Returns:
            NormalizedResult with normalized MAC address.

        Examples:
            >>> normalizer = DataNormalizer()
            >>> result = normalizer.normalize_mac_address("00-1A-2B-3C-4D-5E")
            >>> result.normalized
            '00:1a:2b:3c:4d:5e'
        """
        original = mac
        errors = []

        if not mac or not mac.strip():
            return NormalizedResult(
                original=original,
                normalized="",
                is_valid=False,
                errors=["Empty MAC address"]
            )

        mac = mac.strip()

        # Remove all separators and get hex digits
        hex_only = re.sub(r'[^0-9A-Fa-f]', '', mac)

        if len(hex_only) != 12:
            return NormalizedResult(
                original=original,
                normalized=mac.lower(),
                is_valid=False,
                errors=[f"Invalid MAC address length: expected 12 hex digits, got {len(hex_only)}"]
            )

        # Format as colon-separated lowercase
        hex_lower = hex_only.lower()
        normalized = ':'.join(hex_lower[i:i+2] for i in range(0, 12, 2))

        components = {
            'oui': normalized[:8],  # First 3 octets (OUI)
            'nic': normalized[9:],  # Last 3 octets (NIC)
        }

        return NormalizedResult(
            original=original,
            normalized=normalized,
            is_valid=True,
            components=components,
            errors=errors
        )


# Module-level singleton
_normalizer_instance: Optional[DataNormalizer] = None


def get_normalizer() -> DataNormalizer:
    """
    Get or create the singleton DataNormalizer instance.

    Returns:
        DataNormalizer instance.
    """
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = DataNormalizer()
    return _normalizer_instance
