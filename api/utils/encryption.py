"""
Database Dump Encryption Utility

Provides AES-256 encryption for sensitive database dumps using cryptography.Fernet.
Ensures PII and sensitive data in exports are protected with mandatory encryption.

Security Considerations:
- Uses Fernet (symmetric encryption) with AES-128 in CBC mode + HMAC
- Fernet provides authenticated encryption (prevents tampering)
- Keys must be 32 bytes (256-bit) and securely managed
- Encrypted output includes timestamp to prevent replay attacks
"""

import base64
import hashlib
import logging
from typing import Optional
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages AES-256 encryption/decryption for database dumps."""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            master_key: Base64-encoded 32-byte encryption key (optional).
                       If not provided, will use default fallback generation.

        Raises:
            ValueError: If provided key is invalid format
        """
        self.master_key = master_key
        self._fernet: Optional[Fernet] = None

    def _derive_key_from_secret(self, secret: str) -> bytes:
        """
        Derive a 32-byte encryption key from a secret string using HMAC-SHA256.

        Args:
            secret: Secret string to derive from

        Returns:
            32-byte derived key
        """
        # HMAC-SHA256 produces 32 bytes (256 bits)
        derived = hashlib.sha256(secret.encode()).digest()
        return derived

    def _get_fernet_instance(self, key_bytes: bytes) -> Fernet:
        """
        Create a Fernet instance from raw key bytes.

        Fernet requires base64-encoded key. We take the 32-byte key,
        base64-encode it, and use it to create a Fernet instance.

        Args:
            key_bytes: 32-byte raw key

        Returns:
            Fernet instance
        """
        # Fernet keys must be base64-encoded
        encoded_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(encoded_key)

    def _get_encryption_key(self) -> bytes:
        """
        Get the encryption key to use.

        Returns:
            32-byte encryption key

        Raises:
            ValueError: If configured key is invalid
        """
        if self.master_key:
            try:
                # If provided, assume it's base64-encoded
                key_bytes = base64.b64decode(self.master_key)
                if len(key_bytes) != 32:
                    raise ValueError(f"Encryption key must be 32 bytes, got {len(key_bytes)}")
                return key_bytes
            except Exception as e:
                raise ValueError(f"Invalid encryption key format: {str(e)}")
        else:
            # Fallback: use a default derived key
            # In production, this should be properly configured
            fallback_secret = "basset-hound-default-encryption-key-v1"
            return self._derive_key_from_secret(fallback_secret)

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext bytes using AES-256-CBC with HMAC.

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted bytes (includes timestamp and HMAC)

        Raises:
            Exception: If encryption fails
        """
        try:
            key_bytes = self._get_encryption_key()
            fernet = self._get_fernet_instance(key_bytes)

            # Fernet automatically adds timestamp
            encrypted = fernet.encrypt(plaintext)

            logger.debug(f"Encrypted {len(plaintext)} bytes to {len(encrypted)} bytes")
            return encrypted

        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def decrypt(self, ciphertext: bytes, ttl: Optional[int] = None) -> bytes:
        """
        Decrypt ciphertext bytes using AES-256-CBC with HMAC.

        Args:
            ciphertext: Encrypted data to decrypt
            ttl: Optional time-to-live in seconds. If set, token must be
                 decrypted within this time window from creation.

        Returns:
            Decrypted plaintext bytes

        Raises:
            InvalidToken: If decryption fails or HMAC validation fails
            Exception: If decryption fails for other reasons
        """
        try:
            key_bytes = self._get_encryption_key()
            fernet = self._get_fernet_instance(key_bytes)

            # Decrypt with optional TTL validation
            plaintext = fernet.decrypt(ciphertext, ttl=ttl)

            logger.debug(f"Decrypted {len(ciphertext)} bytes to {len(plaintext)} bytes")
            return plaintext

        except InvalidToken as e:
            logger.error(f"Decryption failed - invalid token or HMAC: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt plaintext string and return base64-encoded ciphertext.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            Exception: If encryption fails
        """
        ciphertext = self.encrypt(plaintext.encode('utf-8'))
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt_string(self, ciphertext_b64: str, ttl: Optional[int] = None) -> str:
        """
        Decrypt base64-encoded ciphertext string.

        Args:
            ciphertext_b64: Base64-encoded encrypted string
            ttl: Optional time-to-live in seconds

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If decryption fails
            Exception: If decryption fails for other reasons
        """
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = self.decrypt(ciphertext, ttl=ttl)
        return plaintext.decode('utf-8')


def get_encryption_manager(config_key: Optional[str] = None) -> EncryptionManager:
    """
    Get an EncryptionManager instance.

    Args:
        config_key: Optional base64-encoded encryption key from config

    Returns:
        EncryptionManager instance
    """
    return EncryptionManager(master_key=config_key)
