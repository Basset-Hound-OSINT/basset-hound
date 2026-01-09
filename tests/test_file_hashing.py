"""
Tests for File Hash Computation Service (Phase 43.2).

Tests cover:
- Hash computation for files
- Hash computation from bytes
- Hash verification
- Duplicate detection
- Performance benchmarks
- Different file types
- Edge cases (empty files, large files)
"""

import pytest
import os
import tempfile
import hashlib
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.file_hash_service import FileHashService


class TestFileHashService:
    """Tests for FileHashService."""

    @pytest.fixture
    def hash_service(self):
        """Create FileHashService instance."""
        return FileHashService()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"Hello, World! This is test content.")
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def empty_file(self):
        """Create an empty temporary file."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def large_file(self):
        """Create a large temporary file (10MB)."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Write 10MB of data
            chunk = b"A" * 1024  # 1KB
            for _ in range(10 * 1024):  # 10MB
                f.write(chunk)
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    # =========================================================================
    # Basic Hash Computation Tests
    # =========================================================================

    def test_compute_hash_basic(self, hash_service, temp_file):
        """Test basic hash computation."""
        hash_value = hash_service.compute_hash(temp_file)

        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)

        # Hash should be deterministic
        hash_value2 = hash_service.compute_hash(temp_file)
        assert hash_value == hash_value2

    def test_compute_hash_from_bytes(self, hash_service):
        """Test hash computation from bytes."""
        data = b"Hello, World! This is test content."
        hash_value = hash_service.compute_hash_from_bytes(data)

        # Verify against manual computation
        expected = hashlib.sha256(data).hexdigest()
        assert hash_value == expected

        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64

    def test_compute_hash_empty_file(self, hash_service, empty_file):
        """Test hash computation for empty file."""
        hash_value = hash_service.compute_hash(empty_file)

        # Empty file has known SHA-256 hash
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert hash_value == expected

    def test_compute_hash_with_metadata(self, hash_service, temp_file):
        """Test hash computation with file metadata."""
        result = hash_service.compute_hash_with_metadata(temp_file)

        assert 'hash' in result
        assert 'size' in result
        assert 'modified' in result
        assert 'path' in result

        # Verify hash is correct
        assert len(result['hash']) == 64

        # Verify size is positive
        assert result['size'] > 0

        # Verify path is absolute
        assert os.path.isabs(result['path'])

    # =========================================================================
    # Hash Verification Tests
    # =========================================================================

    def test_verify_hash_valid(self, hash_service, temp_file):
        """Test hash verification with valid hash."""
        # Compute the hash first
        expected_hash = hash_service.compute_hash(temp_file)

        # Verify it
        is_valid = hash_service.verify_hash(temp_file, expected_hash)
        assert is_valid is True

    def test_verify_hash_invalid(self, hash_service, temp_file):
        """Test hash verification with invalid hash."""
        # Use a different hash
        wrong_hash = "0" * 64

        is_valid = hash_service.verify_hash(temp_file, wrong_hash)
        assert is_valid is False

    def test_verify_hash_case_insensitive(self, hash_service, temp_file):
        """Test that hash verification is case-insensitive."""
        expected_hash = hash_service.compute_hash(temp_file)

        # Test uppercase
        is_valid = hash_service.verify_hash(temp_file, expected_hash.upper())
        assert is_valid is True

        # Test mixed case
        mixed_case = ''.join(
            c.upper() if i % 2 == 0 else c.lower()
            for i, c in enumerate(expected_hash)
        )
        is_valid = hash_service.verify_hash(temp_file, mixed_case)
        assert is_valid is True

    def test_verify_hash_with_whitespace(self, hash_service, temp_file):
        """Test that hash verification strips whitespace."""
        expected_hash = hash_service.compute_hash(temp_file)

        # Add whitespace
        is_valid = hash_service.verify_hash(temp_file, f"  {expected_hash}  ")
        assert is_valid is True

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_compute_hash_nonexistent_file(self, hash_service):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            hash_service.compute_hash("/nonexistent/file.txt")

    def test_compute_hash_directory(self, hash_service):
        """Test error handling when path is a directory."""
        with pytest.raises(ValueError, match="not a file"):
            hash_service.compute_hash(tempfile.gettempdir())

    def test_compute_hash_from_bytes_invalid_type(self, hash_service):
        """Test error handling for non-bytes input."""
        with pytest.raises(TypeError, match="Expected bytes"):
            hash_service.compute_hash_from_bytes("not bytes")

    def test_verify_hash_invalid_format(self, hash_service, temp_file):
        """Test error handling for invalid hash format."""
        # Too short
        with pytest.raises(ValueError, match="Invalid SHA-256 hash length"):
            hash_service.verify_hash(temp_file, "abc123")

        # Too long
        with pytest.raises(ValueError, match="Invalid SHA-256 hash length"):
            hash_service.verify_hash(temp_file, "a" * 100)

        # Non-hex characters
        with pytest.raises(ValueError, match="non-hex characters"):
            hash_service.verify_hash(temp_file, "z" * 64)

        # Empty hash
        with pytest.raises(ValueError, match="cannot be empty"):
            hash_service.verify_hash(temp_file, "")

    # =========================================================================
    # Different File Types Tests
    # =========================================================================

    def test_hash_image_file(self, hash_service):
        """Test hashing a mock image file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
            # Write some binary data (simulated JPEG header)
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            hash_value = hash_service.compute_hash(temp_path)
            assert len(hash_value) == 64
        finally:
            os.unlink(temp_path)

    def test_hash_pdf_file(self, hash_service):
        """Test hashing a mock PDF file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # Write PDF header
            f.write(b'%PDF-1.4\n' + b'\x00' * 100)
            temp_path = f.name

        try:
            hash_value = hash_service.compute_hash(temp_path)
            assert len(hash_value) == 64
        finally:
            os.unlink(temp_path)

    def test_hash_text_file(self, hash_service):
        """Test hashing a text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file\nWith multiple lines\nAnd some content")
            temp_path = f.name

        try:
            hash_value = hash_service.compute_hash(temp_path)
            assert len(hash_value) == 64
        finally:
            os.unlink(temp_path)

    # =========================================================================
    # Duplicate Detection Tests
    # =========================================================================

    def test_identical_files_same_hash(self, hash_service):
        """Test that identical files produce the same hash."""
        content = b"Identical content for testing"

        # Create two files with identical content
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            hash1 = hash_service.compute_hash(path1)
            hash2 = hash_service.compute_hash(path2)

            assert hash1 == hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_different_files_different_hash(self, hash_service):
        """Test that different files produce different hashes."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(b"Content A")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(b"Content B")
            path2 = f2.name

        try:
            hash1 = hash_service.compute_hash(path1)
            hash2 = hash_service.compute_hash(path2)

            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_minor_change_different_hash(self, hash_service):
        """Test that even minor changes produce different hashes."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(b"The quick brown fox")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(b"The quick brown fox.")  # Added period
            path2 = f2.name

        try:
            hash1 = hash_service.compute_hash(path1)
            hash2 = hash_service.compute_hash(path2)

            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    # =========================================================================
    # Batch Operations Tests
    # =========================================================================

    def test_batch_compute_hashes(self, hash_service):
        """Test batch hash computation."""
        # Create multiple test files
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(f"File {i} content".encode())
                files.append(f.name)

        try:
            results = hash_service.batch_compute_hashes(files)

            # Should have hash for each file
            assert len(results) == len(files)

            # All hashes should be valid
            for file_path, hash_value in results.items():
                assert len(hash_value) == 64
                assert file_path in files
        finally:
            for f in files:
                os.unlink(f)

    def test_batch_compute_hashes_with_error(self, hash_service, temp_file):
        """Test batch processing continues despite errors."""
        # Create a second valid file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"Second file content")
            temp_file2 = f.name

        try:
            files = [temp_file, "/nonexistent/file.txt", temp_file2]

            results = hash_service.batch_compute_hashes(files)

            # Should have results for valid files only (2 valid files)
            assert len(results) == 2
            assert temp_file in results
            assert temp_file2 in results
        finally:
            os.unlink(temp_file2)

    # =========================================================================
    # Performance Tests
    # =========================================================================

    def test_performance_small_file(self, hash_service, temp_file, benchmark=None):
        """Test hash computation performance for small file."""
        # If pytest-benchmark is available, use it
        if benchmark:
            result = benchmark(hash_service.compute_hash, temp_file)
            assert len(result) == 64
        else:
            # Simple timing
            import time
            start = time.time()
            hash_value = hash_service.compute_hash(temp_file)
            elapsed = time.time() - start

            assert len(hash_value) == 64
            # Should be fast for small file
            assert elapsed < 0.1, f"Small file hash took {elapsed:.3f}s"

    def test_performance_large_file(self, hash_service, large_file):
        """Test hash computation performance for 10MB file."""
        import time
        start = time.time()
        hash_value = hash_service.compute_hash(large_file)
        elapsed = time.time() - start

        assert len(hash_value) == 64
        # Should complete within 1 second for 10MB file
        assert elapsed < 1.0, f"10MB file hash took {elapsed:.3f}s"

        print(f"\nPerformance: 10MB file hashed in {elapsed:.3f}s")

    def test_performance_chunk_size(self, hash_service, large_file):
        """Test that chunk processing works efficiently."""
        # The service should use chunks, not load entire file
        # This test verifies it doesn't fail with large files
        hash_value = hash_service.compute_hash(large_file)
        assert len(hash_value) == 64

    # =========================================================================
    # Integration Tests
    # =========================================================================

    def test_end_to_end_workflow(self, hash_service):
        """Test complete workflow: create, hash, verify, compare."""
        # Create file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            content = b"Evidence data for investigation"
            f.write(content)
            file_path = f.name

        try:
            # Compute hash
            original_hash = hash_service.compute_hash(file_path)

            # Verify hash
            is_valid = hash_service.verify_hash(file_path, original_hash)
            assert is_valid

            # Get metadata
            metadata = hash_service.compute_hash_with_metadata(file_path)
            assert metadata['hash'] == original_hash

            # Create duplicate file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
                f2.write(content)
                dup_path = f2.name

            try:
                # Verify duplicate has same hash
                dup_hash = hash_service.compute_hash(dup_path)
                assert dup_hash == original_hash

                # Verify duplicate
                assert hash_service.verify_hash(dup_path, original_hash)
            finally:
                os.unlink(dup_path)
        finally:
            os.unlink(file_path)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
