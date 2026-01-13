"""
External service clients for basset-hound.

This module provides async HTTP clients for communicating with
external microservices in the basset ecosystem.
"""

from api.clients.basset_verify_client import (
    BassetVerifyClient,
    get_basset_verify_client,
    VerificationResult,
    VerificationLevel,
    IdentifierType,
)

__all__ = [
    "BassetVerifyClient",
    "get_basset_verify_client",
    "VerificationResult",
    "VerificationLevel",
    "IdentifierType",
]
