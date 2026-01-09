"""
File Hash Computation Service for Basset Hound.

Provides SHA-256 hashing for uploaded files (images, documents, evidence)
to detect duplicates and verify file integrity. Part of Phase 43.2:
Smart Suggestions feature for intelligent data matching.

This service is focused on intelligence management - helping identify
when the same file (evidence, screenshot, document) has been uploaded
multiple times across different entities or as orphan data.
"""

import hashlib
from pathlib import Path
from typing import Optional


class FileHashService:
    """
    Service for computing and verifying SHA-256 file hashes.

    Uses SHA-256 algorithm for cryptographic-quality hashing suitable for:
    - Duplicate file detection
    - File integrity verification
    - Content-based deduplication

    The service processes files in chunks to handle large files efficiently
    without loading entire files into memory.
    """

    CHUNK_SIZE = 4096  # 4KB chunks for memory-efficient processing

    def compute_hash(self, file_path: str) -> str:
        """
        Compute SHA-256 hash for a file on disk.

        Processes file in chunks to handle large files efficiently without
        loading entire file into memory. Suitable for files up to several GB.

        Args:
            file_path: Path to the file to hash

        Returns:
            Hexadecimal string representation of SHA-256 hash (64 characters)

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            IOError: If file read fails

        Example:
            >>> service = FileHashService()
            >>> hash_value = service.compute_hash("/path/to/file.pdf")
            >>> print(hash_value)
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read file in chunks to avoid memory issues with large files
            for chunk in iter(lambda: f.read(self.CHUNK_SIZE), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    def compute_hash_from_bytes(self, data: bytes) -> str:
        """
        Compute SHA-256 hash from bytes in memory.

        Useful for hashing file content that's already loaded in memory,
        such as uploaded files received via API before saving to disk.

        Args:
            data: Bytes to hash

        Returns:
            Hexadecimal string representation of SHA-256 hash (64 characters)

        Raises:
            TypeError: If data is not bytes

        Example:
            >>> service = FileHashService()
            >>> content = b"Hello, World!"
            >>> hash_value = service.compute_hash_from_bytes(content)
            >>> print(hash_value)
            'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        """
        if not isinstance(data, bytes):
            raise TypeError(f"Expected bytes, got {type(data).__name__}")

        return hashlib.sha256(data).hexdigest()

    def verify_hash(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify that a file matches an expected hash.

        Computes the hash of the file and compares it to the expected hash.
        Useful for verifying file integrity after download or transfer.

        Args:
            file_path: Path to the file to verify
            expected_hash: Expected SHA-256 hash (64 hex characters)

        Returns:
            True if file hash matches expected hash, False otherwise

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If expected_hash is not a valid SHA-256 hex string

        Example:
            >>> service = FileHashService()
            >>> expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            >>> is_valid = service.verify_hash("/path/to/file.pdf", expected)
            >>> print(f"File integrity: {'OK' if is_valid else 'FAILED'}")
        """
        # Validate expected hash format
        if not expected_hash:
            raise ValueError("Expected hash cannot be empty")

        expected_hash = expected_hash.lower().strip()

        # SHA-256 produces 64 hex characters
        if len(expected_hash) != 64:
            raise ValueError(f"Invalid SHA-256 hash length: {len(expected_hash)} (expected 64)")

        # Verify hex characters only
        try:
            int(expected_hash, 16)
        except ValueError:
            raise ValueError(f"Invalid SHA-256 hash format: contains non-hex characters")

        actual_hash = self.compute_hash(file_path)
        return actual_hash == expected_hash

    def compute_hash_with_metadata(self, file_path: str) -> dict:
        """
        Compute hash along with file metadata.

        Returns hash plus useful metadata like file size and modification time.
        Useful for comprehensive file tracking in the database.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with:
                - hash: SHA-256 hash
                - size: File size in bytes
                - modified: Last modification timestamp
                - path: Original file path

        Raises:
            FileNotFoundError: If file doesn't exist

        Example:
            >>> service = FileHashService()
            >>> info = service.compute_hash_with_metadata("/path/to/file.pdf")
            >>> print(f"Hash: {info['hash']}")
            >>> print(f"Size: {info['size']} bytes")
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = path.stat()

        return {
            'hash': self.compute_hash(file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'path': str(path.absolute())
        }

    def batch_compute_hashes(self, file_paths: list[str]) -> dict[str, str]:
        """
        Compute hashes for multiple files.

        Processes multiple files and returns a mapping of file paths to their hashes.
        Failed files are logged but don't stop processing of remaining files.

        Args:
            file_paths: List of file paths to hash

        Returns:
            Dictionary mapping file path to hash for successfully processed files

        Example:
            >>> service = FileHashService()
            >>> files = ["/path/file1.jpg", "/path/file2.pdf"]
            >>> hashes = service.batch_compute_hashes(files)
            >>> for path, hash_val in hashes.items():
            ...     print(f"{path}: {hash_val}")
        """
        results = {}

        for file_path in file_paths:
            try:
                results[file_path] = self.compute_hash(file_path)
            except Exception as e:
                # Log error but continue processing other files
                print(f"Warning: Failed to hash {file_path}: {e}")
                continue

        return results
