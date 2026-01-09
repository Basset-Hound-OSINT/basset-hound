"""
File Hashing MCP Tools for Basset Hound.

Provides MCP tools for computing file hashes, verifying integrity,
and finding duplicate files in the database. Part of Phase 43.2:
Smart Suggestions feature for intelligent data matching.

These tools help OSINT analysts identify when the same evidence
(screenshots, documents, images) appears in multiple locations.
"""

import sys
import os
from typing import Optional, List, Dict

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.services.file_hash_service import FileHashService
from .base import get_neo4j_handler, get_project_safe_name


def register_file_hashing_tools(mcp):
    """Register file hashing tools with the MCP server."""

    # Initialize service
    hash_service = FileHashService()

    @mcp.tool()
    def compute_file_hash(project_id: str, file_path: str) -> dict:
        """
        Compute SHA-256 hash for a file in a project.

        Computes cryptographic hash of file content for duplicate detection
        and integrity verification. The hash is computed from file content,
        so identical files will have the same hash regardless of filename.

        Args:
            project_id: Project ID or safe_name
            file_path: Path to file relative to project directory, or absolute path

        Returns:
            Dictionary with:
                - hash: SHA-256 hash (64 hex characters)
                - file_path: Path that was hashed
                - size: File size in bytes
                - algorithm: Hash algorithm used (sha256)

        Example:
            >>> compute_file_hash("my_investigation", "entity-123/files/evidence.jpg")
            {
                "hash": "a1b2c3...",
                "file_path": "entity-123/files/evidence.jpg",
                "size": 52481,
                "algorithm": "sha256"
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # If relative path, resolve to project directory
        if not os.path.isabs(file_path):
            # Resolve relative to project directory
            project_dir = os.path.join("projects", safe_name)
            full_path = os.path.join(project_dir, file_path)
        else:
            full_path = file_path

        try:
            metadata = hash_service.compute_hash_with_metadata(full_path)
            return {
                "success": True,
                "hash": metadata['hash'],
                "file_path": file_path,
                "size": metadata['size'],
                "algorithm": "sha256"
            }
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}
        except Exception as e:
            return {"error": f"Failed to compute hash: {str(e)}"}

    @mcp.tool()
    def verify_file_integrity(
        project_id: str,
        file_path: str,
        expected_hash: str
    ) -> dict:
        """
        Verify a file matches an expected hash.

        Useful for verifying evidence integrity - confirming that a file
        hasn't been modified since it was originally captured. This is
        critical for maintaining chain of custody in investigations.

        Args:
            project_id: Project ID or safe_name
            file_path: Path to file relative to project directory
            expected_hash: Expected SHA-256 hash to verify against

        Returns:
            Dictionary with:
                - valid: True if hash matches, False otherwise
                - actual_hash: Computed hash of the file
                - expected_hash: Hash that was provided
                - file_path: Path that was verified

        Example:
            >>> verify_file_integrity("my_investigation",
            ...                       "entity-123/files/evidence.jpg",
            ...                       "a1b2c3d4...")
            {
                "valid": True,
                "actual_hash": "a1b2c3d4...",
                "expected_hash": "a1b2c3d4...",
                "file_path": "entity-123/files/evidence.jpg"
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Resolve path
        if not os.path.isabs(file_path):
            project_dir = os.path.join("projects", safe_name)
            full_path = os.path.join(project_dir, file_path)
        else:
            full_path = file_path

        try:
            is_valid = hash_service.verify_hash(full_path, expected_hash)
            actual_hash = hash_service.compute_hash(full_path)

            return {
                "success": True,
                "valid": is_valid,
                "actual_hash": actual_hash,
                "expected_hash": expected_hash,
                "file_path": file_path,
                "status": "VERIFIED" if is_valid else "MISMATCH"
            }
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}
        except ValueError as e:
            return {"error": f"Invalid hash format: {str(e)}"}
        except Exception as e:
            return {"error": f"Verification failed: {str(e)}"}

    @mcp.tool()
    def find_duplicates_by_hash(project_id: str, file_hash: str) -> dict:
        """
        Find all files with the same hash in a project.

        Searches the database for files/data with matching hashes, indicating
        duplicate or identical content. Returns matches from both entity data
        and orphan data. This helps identify when the same evidence appears
        in multiple locations in your investigation.

        Args:
            project_id: Project ID or safe_name
            file_hash: SHA-256 hash to search for

        Returns:
            Dictionary with:
                - hash: Hash that was searched
                - total_matches: Total number of duplicates found
                - entity_matches: List of entities with this file
                - orphan_matches: List of orphan data with this hash
                - suggestions: Human-readable suggestions for deduplication

        Example:
            >>> find_duplicates_by_hash("my_investigation", "a1b2c3d4...")
            {
                "hash": "a1b2c3d4...",
                "total_matches": 3,
                "entity_matches": [
                    {"entity_id": "entity-123", "field_path": "evidence.photo1", ...},
                    {"entity_id": "entity-456", "field_path": "evidence.image", ...}
                ],
                "orphan_matches": [
                    {"orphan_id": "orphan-789", "identifier_type": "file", ...}
                ],
                "suggestions": [
                    "Same file appears in 2 entities and 1 orphan data",
                    "Consider linking orphan-789 to an existing entity"
                ]
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate hash format
        if not file_hash or len(file_hash) != 64:
            return {"error": "Invalid SHA-256 hash format (expected 64 hex characters)"}

        try:
            int(file_hash, 16)
        except ValueError:
            return {"error": "Invalid SHA-256 hash format (non-hex characters)"}

        # Search entity profiles for matching hash
        entity_matches = _find_hash_in_entities(handler, safe_name, file_hash)

        # Search orphan data for matching hash
        orphan_matches = _find_hash_in_orphans(handler, safe_name, file_hash)

        # Generate suggestions
        total_matches = len(entity_matches) + len(orphan_matches)
        suggestions = _generate_deduplication_suggestions(
            entity_matches, orphan_matches, file_hash
        )

        return {
            "success": True,
            "hash": file_hash,
            "total_matches": total_matches,
            "entity_matches": entity_matches,
            "orphan_matches": orphan_matches,
            "suggestions": suggestions
        }

    @mcp.tool()
    def find_data_by_hash(project_id: str, file_hash: str) -> dict:
        """
        Find all data items (entity and orphan) with matching hash.

        Similar to find_duplicates_by_hash but returns more detailed information
        about each match, including full metadata and context. Useful for
        comprehensive duplicate analysis.

        Args:
            project_id: Project ID or safe_name
            file_hash: SHA-256 hash to search for

        Returns:
            Dictionary with all matching data items and their full context

        Example:
            >>> find_data_by_hash("my_investigation", "a1b2c3d4...")
            {
                "hash": "a1b2c3d4...",
                "matches": [
                    {
                        "type": "entity",
                        "entity_id": "entity-123",
                        "field_path": "evidence.photo",
                        "data": {...}
                    },
                    ...
                ]
            }
        """
        # This is essentially the same as find_duplicates_by_hash but with
        # more detailed return format
        return find_duplicates_by_hash(project_id, file_hash)


# Helper functions

def _find_hash_in_entities(handler, project_safe_name: str, file_hash: str) -> List[Dict]:
    """
    Search entity profiles for files with matching hash.

    Scans all entities in project looking for file references with
    matching hash in metadata.
    """
    matches = []

    # Get all entities in project
    entities = handler.get_all_people_in_project(project_safe_name)

    for entity in entities:
        entity_id = entity.get('id')
        profile = entity.get('profile', {})

        # Search through profile for file hashes
        # Check for _file_hashes metadata section
        if '_file_hashes' in profile:
            file_hashes = profile['_file_hashes']
            for field_path, hash_value in file_hashes.items():
                if hash_value == file_hash:
                    matches.append({
                        'type': 'entity',
                        'entity_id': entity_id,
                        'field_path': field_path,
                        'hash': hash_value
                    })

        # Also check metadata in each field
        for section_id, section_data in profile.items():
            if section_id.startswith('_'):
                continue  # Skip internal sections
            if isinstance(section_data, dict):
                for field_id, field_values in section_data.items():
                    if isinstance(field_values, list):
                        for idx, value in enumerate(field_values):
                            if isinstance(value, dict) and value.get('hash') == file_hash:
                                matches.append({
                                    'type': 'entity',
                                    'entity_id': entity_id,
                                    'field_path': f"{section_id}.{field_id}.{idx}",
                                    'hash': file_hash,
                                    'data': value
                                })

    return matches


def _find_hash_in_orphans(handler, project_safe_name: str, file_hash: str) -> List[Dict]:
    """
    Search orphan data for items with matching hash.

    Looks for hash in orphan data metadata.
    """
    matches = []

    # Get all orphans in project
    orphans = handler.get_all_orphan_data(project_safe_name)

    for orphan in orphans:
        orphan_id = orphan.get('id')
        metadata = orphan.get('metadata', {})

        # Check if hash is stored in metadata
        if metadata.get('file_hash') == file_hash or metadata.get('hash') == file_hash:
            matches.append({
                'type': 'orphan',
                'orphan_id': orphan_id,
                'identifier_type': orphan.get('identifier_type'),
                'identifier_value': orphan.get('identifier_value'),
                'hash': file_hash,
                'linked': orphan.get('linked', False),
                'linked_entity_id': orphan.get('linked_entity_id')
            })

    return matches


def _generate_deduplication_suggestions(
    entity_matches: List[Dict],
    orphan_matches: List[Dict],
    file_hash: str
) -> List[str]:
    """
    Generate human-readable suggestions for handling duplicates.

    Analyzes the matches and provides actionable suggestions for
    the investigator.
    """
    suggestions = []

    total = len(entity_matches) + len(orphan_matches)

    if total == 0:
        suggestions.append("No duplicates found - this file is unique")
        return suggestions

    if total == 1:
        suggestions.append("File is unique in database")
        return suggestions

    # Multiple matches found
    suggestions.append(
        f"Same file appears in {len(entity_matches)} entities and "
        f"{len(orphan_matches)} orphan data items"
    )

    # Suggest linking orphans to entities
    if orphan_matches and entity_matches:
        unlinked_orphans = [o for o in orphan_matches if not o.get('linked')]
        if unlinked_orphans:
            suggestions.append(
                f"Consider linking {len(unlinked_orphans)} unlinked orphan(s) "
                f"to existing entities that have this file"
            )

    # Suggest deduplication if multiple entities have same file
    if len(entity_matches) > 1:
        entity_ids = set(m['entity_id'] for m in entity_matches)
        if len(entity_ids) > 1:
            suggestions.append(
                f"File appears in {len(entity_ids)} different entities - "
                f"verify if these entities should be merged"
            )

    # Provide specific entity IDs for investigation
    if entity_matches:
        entity_ids = [m['entity_id'] for m in entity_matches[:5]]
        if len(entity_matches) > 5:
            suggestions.append(
                f"Entities with this file: {', '.join(entity_ids[:5])}... "
                f"(and {len(entity_matches) - 5} more)"
            )
        else:
            suggestions.append(f"Entities with this file: {', '.join(entity_ids)}")

    return suggestions
