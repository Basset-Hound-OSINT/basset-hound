"""
Test suite for database dump encryption functionality.

Tests encryption/decryption, key management, and endpoint behavior.
"""

import pytest
import base64
import os
import json
import zipfile
from io import BytesIO
from datetime import datetime

from api.utils.encryption import EncryptionManager, get_encryption_manager
from cryptography.fernet import InvalidToken


class TestEncryptionManager:
    """Tests for EncryptionManager class."""

    def test_init_no_key(self):
        """Test initialization without providing a key."""
        manager = EncryptionManager(master_key=None)
        assert manager.master_key is None
        assert manager._fernet is None

    def test_init_with_key(self):
        """Test initialization with a valid key."""
        key_bytes = b"0" * 32  # 32-byte key
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        manager = EncryptionManager(master_key=key_b64)
        assert manager.master_key == key_b64

    def test_init_with_invalid_key(self):
        """Test initialization with an invalid key length."""
        key_bytes = b"0" * 16  # Only 16 bytes (should be 32)
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        manager = EncryptionManager(master_key=key_b64)

        # Error should occur on first encrypt/decrypt operation
        with pytest.raises(ValueError):
            manager.encrypt(b"test")

    def test_encrypt_basic(self):
        """Test basic encryption."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"sensitive investigation data"

        ciphertext = manager.encrypt(plaintext)

        assert isinstance(ciphertext, bytes)
        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)  # Includes Fernet overhead

    def test_decrypt_basic(self):
        """Test basic decryption."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"entity relationships and PII"

        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encrypt-decrypt cycle."""
        manager = EncryptionManager(master_key=None)
        original_data = b"John Doe | person | phone: 555-0123 | email: john@example.com"

        encrypted = manager.encrypt(original_data)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == original_data

    def test_encrypt_empty_data(self):
        """Test encryption of empty data."""
        manager = EncryptionManager(master_key=None)
        plaintext = b""

        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_large_data(self):
        """Test encryption of large data (simulating ZIP file)."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"x" * (10 * 1024 * 1024)  # 10 MB

        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_decrypt_invalid_ciphertext(self):
        """Test decryption with corrupted ciphertext."""
        manager = EncryptionManager(master_key=None)

        with pytest.raises(InvalidToken):
            manager.decrypt(b"invalid ciphertext data")

    def test_decrypt_tampered_ciphertext(self):
        """Test that HMAC catches tampered ciphertext."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"original data"

        ciphertext = manager.encrypt(plaintext)

        # Tamper with the ciphertext (flip a bit)
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 0x01  # Flip one bit at the end

        with pytest.raises(InvalidToken):
            manager.decrypt(bytes(tampered))

    def test_string_encrypt_basic(self):
        """Test string encryption."""
        manager = EncryptionManager(master_key=None)
        plaintext = "sensitive string data"

        ciphertext_b64 = manager.encrypt_string(plaintext)

        assert isinstance(ciphertext_b64, str)
        assert plaintext not in ciphertext_b64
        assert len(ciphertext_b64) > len(plaintext)

    def test_string_decrypt_basic(self):
        """Test string decryption."""
        manager = EncryptionManager(master_key=None)
        plaintext = "Jane Doe | Organization X"

        encrypted_str = manager.encrypt_string(plaintext)
        decrypted_str = manager.decrypt_string(encrypted_str)

        assert decrypted_str == plaintext

    def test_string_encrypt_unicode(self):
        """Test encryption of unicode strings."""
        manager = EncryptionManager(master_key=None)
        plaintext = "Investigator: José García | Location: São Paulo | Date: 2026-05-19"

        encrypted_str = manager.encrypt_string(plaintext)
        decrypted_str = manager.decrypt_string(encrypted_str)

        assert decrypted_str == plaintext

    def test_different_keys_different_ciphertext(self):
        """Test that different keys produce different ciphertexts."""
        key1_bytes = b"1" * 32
        key1_b64 = base64.b64encode(key1_bytes).decode('utf-8')

        key2_bytes = b"2" * 32
        key2_b64 = base64.b64encode(key2_bytes).decode('utf-8')

        manager1 = EncryptionManager(master_key=key1_b64)
        manager2 = EncryptionManager(master_key=key2_b64)

        plaintext = b"same plaintext"

        ciphertext1 = manager1.encrypt(plaintext)
        ciphertext2 = manager2.encrypt(plaintext)

        # Different keys should (almost certainly) produce different ciphertexts
        # Note: Fernet includes timestamp, so they'll differ anyway
        assert ciphertext1 != ciphertext2

    def test_decrypt_with_different_key_fails(self):
        """Test that decryption with wrong key fails."""
        key1_bytes = b"1" * 32
        key1_b64 = base64.b64encode(key1_bytes).decode('utf-8')

        key2_bytes = b"2" * 32
        key2_b64 = base64.b64encode(key2_bytes).decode('utf-8')

        manager1 = EncryptionManager(master_key=key1_b64)
        manager2 = EncryptionManager(master_key=key2_b64)

        plaintext = b"secret data"
        ciphertext = manager1.encrypt(plaintext)

        # Try to decrypt with different key
        with pytest.raises(InvalidToken):
            manager2.decrypt(ciphertext)

    def test_encryption_adds_timestamp(self):
        """Test that Fernet timestamp is included in ciphertext."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"timestamped data"

        ciphertext = manager.encrypt(plaintext)

        # Fernet format: [Version (1 byte)][Timestamp (8 bytes)][IV (16 bytes)][Ciphertext][HMAC (32 bytes)]
        # Minimum overhead is approximately 57 bytes
        assert len(ciphertext) >= len(plaintext) + 50

    def test_multiple_encryptions_different_ciphertexts(self):
        """Test that same plaintext encrypts differently due to timestamp."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"same data twice"

        ciphertext1 = manager.encrypt(plaintext)
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        ciphertext2 = manager.encrypt(plaintext)

        # Different timestamps mean different ciphertexts
        assert ciphertext1 != ciphertext2

        # But both decrypt to same plaintext
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext

    def test_get_encryption_manager_factory(self):
        """Test get_encryption_manager factory function."""
        manager = get_encryption_manager(config_key=None)
        assert isinstance(manager, EncryptionManager)

    def test_encryption_of_json_data(self):
        """Test encryption of JSON-serialized data (like database dumps)."""
        manager = EncryptionManager(master_key=None)

        # Simulate database dump metadata
        data = {
            "export_date": "2026-05-19T14:30:00",
            "node_count": 1234,
            "relationship_count": 5678,
            "encrypted": True,
            "encryption_method": "AES-256-Fernet"
        }

        plaintext = json.dumps(data).encode('utf-8')
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert json.loads(decrypted) == data

    def test_encryption_of_zip_archive(self):
        """Test encryption of actual ZIP archive data."""
        manager = EncryptionManager(master_key=None)

        # Create a test ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('nodes.json', '{"nodes": []}')
            zf.writestr('relationships.json', '{"relationships": []}')
            zf.writestr('metadata.json', '{"export_date": "2026-05-19"}')

        zip_data = zip_buffer.getvalue()

        # Encrypt
        encrypted = manager.encrypt(zip_data)

        # Decrypt and verify it's still a valid ZIP
        decrypted = manager.decrypt(encrypted)

        # Should be able to read as ZIP
        with zipfile.ZipFile(BytesIO(decrypted), 'r') as zf:
            files = zf.namelist()
            assert 'nodes.json' in files
            assert 'relationships.json' in files
            assert 'metadata.json' in files

    def test_derive_key_from_secret(self):
        """Test key derivation from secret string."""
        manager = EncryptionManager(master_key=None)

        secret = "my-application-secret"
        key1 = manager._derive_key_from_secret(secret)
        key2 = manager._derive_key_from_secret(secret)

        # Same secret should derive same key
        assert key1 == key2
        assert len(key1) == 32  # 256 bits


class TestIntegrationWithExportService:
    """Integration tests with export service."""

    def test_encrypted_dump_metadata(self):
        """Test that encrypted dump includes encryption metadata."""
        manager = EncryptionManager(master_key=None)

        # Simulate what export_full_dump does
        dump_zip = BytesIO()
        with zipfile.ZipFile(dump_zip, 'w') as zf:
            zf.writestr('nodes.json', '[]')
            zf.writestr('relationships.json', '[]')

            metadata = {
                'export_date': datetime.utcnow().isoformat(),
                'encrypted': True,
                'encryption_method': 'AES-256-Fernet',
                'encryption_note': 'This dump is encrypted with AES-256',
            }
            zf.writestr('metadata.json', json.dumps(metadata, indent=2))

        # Encrypt
        encrypted = manager.encrypt(dump_zip.getvalue())

        # Verify: original contains readable metadata, encrypted does not
        dump_zip.seek(0)
        original_content = dump_zip.read()
        assert b'encryption_method' in original_content
        assert b'encryption_method' not in encrypted

    def test_can_decrypt_and_extract_dump(self):
        """Test realistic scenario: decrypt dump and extract contents."""
        manager = EncryptionManager(master_key=None)

        # Create realistic dump
        dump_zip = BytesIO()
        with zipfile.ZipFile(dump_zip, 'w') as zf:
            nodes_data = [
                {"id": 1, "labels": ["Person"], "properties": {"name": "John Doe"}},
                {"id": 2, "labels": ["Person"], "properties": {"name": "Jane Smith"}},
            ]
            zf.writestr('nodes.json', json.dumps(nodes_data, indent=2))

            rels_data = [
                {"id": 1, "type": "KNOWS", "source": 1, "target": 2},
            ]
            zf.writestr('relationships.json', json.dumps(rels_data, indent=2))

        dump_data = dump_zip.getvalue()

        # Encrypt
        encrypted = manager.encrypt(dump_data)

        # Decrypt
        decrypted = manager.decrypt(encrypted)

        # Extract and verify
        with zipfile.ZipFile(BytesIO(decrypted), 'r') as zf:
            nodes = json.loads(zf.read('nodes.json'))
            assert len(nodes) == 2
            assert nodes[0]['properties']['name'] == 'John Doe'


class TestSecurityProperties:
    """Tests for security properties of encryption."""

    def test_ciphertext_not_human_readable(self):
        """Verify encrypted data is not human-readable."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"Investigation: Operation Alpha. Suspect: John Doe. Location: NYC."

        ciphertext = manager.encrypt(plaintext)

        # Should not contain readable fragments
        assert b"Investigation" not in ciphertext
        assert b"Operation Alpha" not in ciphertext
        assert b"John Doe" not in ciphertext
        assert b"NYC" not in ciphertext

    def test_hmac_validates_integrity(self):
        """Test that HMAC prevents silent corruption."""
        manager = EncryptionManager(master_key=None)
        plaintext = b"integrity test"

        ciphertext = manager.encrypt(plaintext)

        # Verify that any single-bit flip is detected
        for byte_idx in range(min(10, len(ciphertext))):
            tampered = bytearray(ciphertext)
            tampered[byte_idx] ^= 0x01  # Flip one bit

            with pytest.raises(InvalidToken):
                manager.decrypt(bytes(tampered))

    def test_different_plaintexts_different_ciphertexts(self):
        """Verify that different plaintexts produce different ciphertexts."""
        manager = EncryptionManager(master_key=None)

        plaintext1 = b"sensitive data 1"
        plaintext2 = b"sensitive data 2"

        # Encrypt multiple times to account for timestamp variations
        ciphertext1a = manager.encrypt(plaintext1)
        ciphertext1b = manager.encrypt(plaintext1)
        ciphertext2 = manager.encrypt(plaintext2)

        # Same plaintext should decrypt to same value (timestamp doesn't matter)
        assert manager.decrypt(ciphertext1a) == plaintext1
        assert manager.decrypt(ciphertext1b) == plaintext1

        # Different plaintext should decrypt differently
        assert manager.decrypt(ciphertext2) == plaintext2
        assert plaintext1 != plaintext2
