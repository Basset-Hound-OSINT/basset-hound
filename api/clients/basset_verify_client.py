"""
Async HTTP client for basset-verify microservice.

This module provides a robust client for communicating with the basset-verify
identifier verification service, with proper error handling and graceful degradation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger("basset_hound.clients.basset_verify")


class VerificationLevel(str, Enum):
    """Verification levels supported by basset-verify."""
    FORMAT = "format"
    NETWORK = "network"
    EXTERNAL_API = "external_api"


class IdentifierType(str, Enum):
    """Identifier types supported by basset-verify."""
    EMAIL = "email"
    PHONE = "phone"
    CRYPTO_ADDRESS = "crypto_address"
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    URL = "url"
    USERNAME = "username"


class VerificationStatus(str, Enum):
    """Verification status values."""
    VALID = "valid"
    INVALID = "invalid"
    PLAUSIBLE = "plausible"
    UNVERIFIABLE = "unverifiable"
    ERROR = "error"
    UNAVAILABLE = "verification_unavailable"


@dataclass
class VerificationResult:
    """Result of an identifier verification."""
    identifier_type: str
    identifier_value: str
    status: str
    verification_level: str
    is_valid: Optional[bool]
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    verified_at: Optional[datetime] = None
    allows_override: bool = True
    override_hint: Optional[str] = None

    @classmethod
    def unavailable(
        cls,
        identifier_type: str,
        identifier_value: str,
        message: str = "basset-verify service is unavailable"
    ) -> "VerificationResult":
        """Create an unavailable result for graceful degradation."""
        return cls(
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            status=VerificationStatus.UNAVAILABLE.value,
            verification_level="none",
            is_valid=None,
            confidence=0.0,
            details={},
            warnings=[message],
            errors=[],
            verified_at=datetime.utcnow(),
            allows_override=True,
            override_hint="Verification service unavailable. Manual verification recommended."
        )

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "VerificationResult":
        """Create a VerificationResult from API response data."""
        verified_at = data.get("verified_at")
        if verified_at and isinstance(verified_at, str):
            try:
                verified_at = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
            except ValueError:
                verified_at = None

        return cls(
            identifier_type=data.get("identifier_type", "unknown"),
            identifier_value=data.get("identifier_value", ""),
            status=data.get("status", "error"),
            verification_level=data.get("verification_level", "none"),
            is_valid=data.get("is_valid"),
            confidence=data.get("confidence", 0.0),
            details=data.get("details", {}),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            verified_at=verified_at,
            allows_override=data.get("allows_override", True),
            override_hint=data.get("override_hint"),
        )


@dataclass
class BatchVerificationResult:
    """Result of a batch verification request."""
    results: list[VerificationResult]
    count: int
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ServiceStatus:
    """Status of the basset-verify service."""
    available: bool
    status: str
    version: Optional[str] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None


class BassetVerifyClient:
    """
    Async HTTP client for basset-verify microservice.

    Provides methods for identifier verification with graceful degradation
    when the service is unavailable.

    Usage:
        async with BassetVerifyClient() as client:
            result = await client.verify_email("test@example.com")
            if result.is_valid:
                print("Email is valid!")
    """

    DEFAULT_BASE_URL = "http://localhost:8001"
    DEFAULT_TIMEOUT = 10.0  # seconds

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """
        Initialize the basset-verify client.

        Args:
            base_url: Base URL for basset-verify service (default: http://localhost:8001)
            timeout: Request timeout in seconds (default: 10.0)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BassetVerifyClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> ServiceStatus:
        """
        Check if basset-verify service is available.

        Returns:
            ServiceStatus with availability information
        """
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            data = response.json()

            timestamp = data.get("timestamp")
            if timestamp and isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = None

            return ServiceStatus(
                available=True,
                status=data.get("status", "healthy"),
                version=data.get("version"),
                timestamp=timestamp,
            )
        except httpx.ConnectError as e:
            logger.warning(f"basset-verify connection error: {e}")
            return ServiceStatus(
                available=False,
                status="unreachable",
                error_message=f"Connection error: {e}",
            )
        except httpx.TimeoutException as e:
            logger.warning(f"basset-verify timeout: {e}")
            return ServiceStatus(
                available=False,
                status="timeout",
                error_message=f"Request timeout: {e}",
            )
        except Exception as e:
            logger.error(f"basset-verify health check error: {e}")
            return ServiceStatus(
                available=False,
                status="error",
                error_message=str(e),
            )

    async def verify(
        self,
        value: str,
        identifier_type: str | IdentifierType,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a generic identifier.

        Args:
            value: The identifier value to verify
            identifier_type: Type of identifier (email, phone, etc.)
            level: Verification level (format, network, external_api)

        Returns:
            VerificationResult with verification details
        """
        if isinstance(identifier_type, IdentifierType):
            identifier_type = identifier_type.value
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify",
                json={
                    "value": value,
                    "type": identifier_type,
                    "level": level,
                },
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for {identifier_type}: {e}")
            return VerificationResult.unavailable(
                identifier_type=identifier_type,
                identifier_value=value,
                message=f"Service unavailable: {e}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"basset-verify HTTP error: {e}")
            return VerificationResult(
                identifier_type=identifier_type,
                identifier_value=value,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[f"HTTP error: {e.response.status_code}"],
                verified_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"basset-verify error: {e}")
            return VerificationResult(
                identifier_type=identifier_type,
                identifier_value=value,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_email(
        self,
        email: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify an email address.

        Args:
            email: Email address to verify
            level: Verification level (format or network)

        Returns:
            VerificationResult with email verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/email",
                json={"email": email, "level": level},
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for email: {e}")
            return VerificationResult.unavailable(
                identifier_type="email",
                identifier_value=email,
            )
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return VerificationResult(
                identifier_type="email",
                identifier_value=email,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_phone(
        self,
        phone: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
        default_region: str = "US",
    ) -> VerificationResult:
        """
        Verify a phone number.

        Args:
            phone: Phone number to verify
            level: Verification level (format or network)
            default_region: Default region code (ISO 3166-1 alpha-2)

        Returns:
            VerificationResult with phone verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/phone",
                json={
                    "phone": phone,
                    "level": level,
                    "default_region": default_region,
                },
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for phone: {e}")
            return VerificationResult.unavailable(
                identifier_type="phone",
                identifier_value=phone,
            )
        except Exception as e:
            logger.error(f"Phone verification error: {e}")
            return VerificationResult(
                identifier_type="phone",
                identifier_value=phone,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_crypto(
        self,
        address: str,
        validate_checksum: bool = True,
    ) -> VerificationResult:
        """
        Verify a cryptocurrency address.

        Args:
            address: Cryptocurrency address to verify
            validate_checksum: Whether to validate checksum

        Returns:
            VerificationResult with crypto verification details
        """
        try:
            response = await self.client.post(
                "/verify/crypto",
                json={
                    "address": address,
                    "validate_checksum": validate_checksum,
                },
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for crypto: {e}")
            return VerificationResult.unavailable(
                identifier_type="crypto_address",
                identifier_value=address,
            )
        except Exception as e:
            logger.error(f"Crypto verification error: {e}")
            return VerificationResult(
                identifier_type="crypto_address",
                identifier_value=address,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_domain(
        self,
        domain: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a domain name.

        Args:
            domain: Domain name to verify
            level: Verification level (format or network)

        Returns:
            VerificationResult with domain verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/domain",
                json={"domain": domain, "level": level},
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for domain: {e}")
            return VerificationResult.unavailable(
                identifier_type="domain",
                identifier_value=domain,
            )
        except Exception as e:
            logger.error(f"Domain verification error: {e}")
            return VerificationResult(
                identifier_type="domain",
                identifier_value=domain,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_ip(
        self,
        ip: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify an IP address.

        Args:
            ip: IP address to verify (IPv4 or IPv6)
            level: Verification level

        Returns:
            VerificationResult with IP verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/ip",
                json={"ip": ip, "level": level},
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for ip: {e}")
            return VerificationResult.unavailable(
                identifier_type="ip_address",
                identifier_value=ip,
            )
        except Exception as e:
            logger.error(f"IP verification error: {e}")
            return VerificationResult(
                identifier_type="ip_address",
                identifier_value=ip,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_url(
        self,
        url: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a URL.

        Args:
            url: URL to verify
            level: Verification level

        Returns:
            VerificationResult with URL verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/url",
                json={"url": url, "level": level},
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for url: {e}")
            return VerificationResult.unavailable(
                identifier_type="url",
                identifier_value=url,
            )
        except Exception as e:
            logger.error(f"URL verification error: {e}")
            return VerificationResult(
                identifier_type="url",
                identifier_value=url,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def verify_username(
        self,
        username: str,
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a username.

        Args:
            username: Username to verify
            level: Verification level

        Returns:
            VerificationResult with username verification details
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        try:
            response = await self.client.post(
                "/verify/username",
                json={"username": username, "level": level},
            )
            response.raise_for_status()
            return VerificationResult.from_response(response.json())
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for username: {e}")
            return VerificationResult.unavailable(
                identifier_type="username",
                identifier_value=username,
            )
        except Exception as e:
            logger.error(f"Username verification error: {e}")
            return VerificationResult(
                identifier_type="username",
                identifier_value=username,
                status="error",
                verification_level="none",
                is_valid=None,
                confidence=0.0,
                errors=[str(e)],
                verified_at=datetime.utcnow(),
            )

    async def batch_verify(
        self,
        items: list[dict[str, str]],
        level: str | VerificationLevel = VerificationLevel.FORMAT,
    ) -> BatchVerificationResult:
        """
        Verify multiple identifiers in batch.

        Args:
            items: List of dicts with "value" and "type" keys
            level: Verification level for all items

        Returns:
            BatchVerificationResult with all verification results
        """
        if isinstance(level, VerificationLevel):
            level = level.value

        if len(items) > 100:
            return BatchVerificationResult(
                results=[],
                count=0,
                success=False,
                error_message="Batch size cannot exceed 100 items",
            )

        try:
            response = await self.client.post(
                "/verify/batch",
                json={"items": items, "level": level},
            )
            response.raise_for_status()
            data = response.json()

            results = [
                VerificationResult.from_response(r)
                for r in data.get("results", [])
            ]

            return BatchVerificationResult(
                results=results,
                count=data.get("count", len(results)),
                success=True,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for batch: {e}")
            # Return unavailable results for all items
            results = [
                VerificationResult.unavailable(
                    identifier_type=item.get("type", "unknown"),
                    identifier_value=item.get("value", ""),
                )
                for item in items
            ]
            return BatchVerificationResult(
                results=results,
                count=len(results),
                success=False,
                error_message=f"Service unavailable: {e}",
            )
        except Exception as e:
            logger.error(f"Batch verification error: {e}")
            return BatchVerificationResult(
                results=[],
                count=0,
                success=False,
                error_message=str(e),
            )

    async def get_crypto_matches(self, address: str) -> dict[str, Any]:
        """
        Get all possible cryptocurrency matches for an address.

        Args:
            address: Cryptocurrency address to analyze

        Returns:
            Dict with address, matches list, and count
        """
        try:
            response = await self.client.get(f"/crypto/matches/{address}")
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for crypto matches: {e}")
            return {
                "address": address,
                "matches": [],
                "count": 0,
                "error": f"Service unavailable: {e}",
            }
        except Exception as e:
            logger.error(f"Crypto matches error: {e}")
            return {
                "address": address,
                "matches": [],
                "count": 0,
                "error": str(e),
            }

    async def get_supported_cryptocurrencies(self) -> dict[str, Any]:
        """
        Get list of supported cryptocurrencies.

        Returns:
            Dict with cryptocurrencies list and count
        """
        try:
            response = await self.client.get("/crypto/supported")
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for crypto list: {e}")
            return {
                "cryptocurrencies": [],
                "count": 0,
                "error": f"Service unavailable: {e}",
            }
        except Exception as e:
            logger.error(f"Crypto list error: {e}")
            return {
                "cryptocurrencies": [],
                "count": 0,
                "error": str(e),
            }

    async def get_verification_types(self) -> dict[str, Any]:
        """
        Get supported identifier types and verification levels.

        Returns:
            Dict with identifier_types and verification_levels lists
        """
        try:
            response = await self.client.get("/types")
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"basset-verify unavailable for types: {e}")
            return {
                "identifier_types": [],
                "verification_levels": [],
                "error": f"Service unavailable: {e}",
            }
        except Exception as e:
            logger.error(f"Types error: {e}")
            return {
                "identifier_types": [],
                "verification_levels": [],
                "error": str(e),
            }


# Global client instance for dependency injection
_client_instance: Optional[BassetVerifyClient] = None


def get_basset_verify_client(
    base_url: Optional[str] = None,
    timeout: float = BassetVerifyClient.DEFAULT_TIMEOUT,
) -> BassetVerifyClient:
    """
    Get or create a basset-verify client instance.

    This function provides a singleton-like pattern for the client,
    suitable for use with FastAPI dependency injection.

    Args:
        base_url: Optional base URL override
        timeout: Request timeout in seconds

    Returns:
        BassetVerifyClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = BassetVerifyClient(base_url=base_url, timeout=timeout)
    return _client_instance


async def close_basset_verify_client() -> None:
    """Close the global basset-verify client instance."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
