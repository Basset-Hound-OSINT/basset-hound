"""
API Key Authentication Module

This module handles API key generation, validation, and management
for programmatic access to the Basset Hound application.

Supports:
- File-based storage (default for development)
- Neo4j storage (for production)
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class APIKeyStatus(str, Enum):
    """API key status enumeration"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class APIKey:
    """API key data model"""
    id: str
    name: str
    key_hash: str  # Stored hash, not the actual key
    key_prefix: str  # First 8 chars for identification
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    status: str = APIKeyStatus.ACTIVE
    scopes: List[str] = None
    created_by: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIKey":
        """Create from dictionary"""
        return cls(**data)

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)"""
        if self.status != APIKeyStatus.ACTIVE:
            return False

        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expiry:
                return False

        return True


class APIKeyStorage:
    """Base class for API key storage backends"""

    def save(self, api_key: APIKey) -> None:
        raise NotImplementedError

    def get_by_id(self, key_id: str) -> Optional[APIKey]:
        raise NotImplementedError

    def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        raise NotImplementedError

    def list_all(self, include_revoked: bool = False) -> List[APIKey]:
        raise NotImplementedError

    def delete(self, key_id: str) -> bool:
        raise NotImplementedError

    def update(self, api_key: APIKey) -> None:
        raise NotImplementedError


class FileBasedStorage(APIKeyStorage):
    """File-based storage for API keys (development/simple deployments)"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(os.getenv(
                "API_KEYS_FILE",
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "api_keys.json")
            ))

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.storage_path.exists():
            self._write_keys({})

    def _read_keys(self) -> Dict[str, Dict]:
        """Read all keys from file"""
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_keys(self, keys: Dict[str, Dict]) -> None:
        """Write all keys to file"""
        with open(self.storage_path, "w") as f:
            json.dump(keys, f, indent=2)

    def save(self, api_key: APIKey) -> None:
        """Save a new API key"""
        keys = self._read_keys()
        keys[api_key.id] = api_key.to_dict()
        self._write_keys(keys)

    def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by its ID"""
        keys = self._read_keys()
        if key_id in keys:
            return APIKey.from_dict(keys[key_id])
        return None

    def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        """Get an API key by its prefix"""
        keys = self._read_keys()
        for key_data in keys.values():
            if key_data.get("key_prefix") == prefix:
                return APIKey.from_dict(key_data)
        return None

    def list_all(self, include_revoked: bool = False) -> List[APIKey]:
        """List all API keys"""
        keys = self._read_keys()
        result = []
        for key_data in keys.values():
            api_key = APIKey.from_dict(key_data)
            if include_revoked or api_key.status == APIKeyStatus.ACTIVE:
                result.append(api_key)
        return result

    def delete(self, key_id: str) -> bool:
        """Delete an API key"""
        keys = self._read_keys()
        if key_id in keys:
            del keys[key_id]
            self._write_keys(keys)
            return True
        return False

    def update(self, api_key: APIKey) -> None:
        """Update an existing API key"""
        keys = self._read_keys()
        if api_key.id in keys:
            keys[api_key.id] = api_key.to_dict()
            self._write_keys(keys)


class Neo4jStorage(APIKeyStorage):
    """Neo4j-based storage for API keys (production)"""

    def __init__(self, neo4j_handler=None):
        self.neo4j_handler = neo4j_handler

    def _get_session(self):
        """Get a Neo4j session"""
        if self.neo4j_handler and self.neo4j_handler.driver:
            return self.neo4j_handler.driver.session()
        raise RuntimeError("Neo4j handler not configured")

    def save(self, api_key: APIKey) -> None:
        """Save a new API key to Neo4j"""
        with self._get_session() as session:
            session.run("""
                CREATE (k:APIKey {
                    id: $id,
                    name: $name,
                    key_hash: $key_hash,
                    key_prefix: $key_prefix,
                    created_at: $created_at,
                    expires_at: $expires_at,
                    last_used_at: $last_used_at,
                    status: $status,
                    scopes: $scopes,
                    created_by: $created_by,
                    description: $description
                })
            """, **api_key.to_dict())

    def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by its ID from Neo4j"""
        with self._get_session() as session:
            result = session.run("""
                MATCH (k:APIKey {id: $id})
                RETURN k
            """, id=key_id)
            record = result.single()
            if record:
                return APIKey.from_dict(dict(record["k"]))
        return None

    def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        """Get an API key by its prefix from Neo4j"""
        with self._get_session() as session:
            result = session.run("""
                MATCH (k:APIKey {key_prefix: $prefix})
                RETURN k
            """, prefix=prefix)
            record = result.single()
            if record:
                return APIKey.from_dict(dict(record["k"]))
        return None

    def list_all(self, include_revoked: bool = False) -> List[APIKey]:
        """List all API keys from Neo4j"""
        with self._get_session() as session:
            if include_revoked:
                result = session.run("MATCH (k:APIKey) RETURN k")
            else:
                result = session.run("""
                    MATCH (k:APIKey)
                    WHERE k.status = 'active'
                    RETURN k
                """)
            return [APIKey.from_dict(dict(record["k"])) for record in result]

    def delete(self, key_id: str) -> bool:
        """Delete an API key from Neo4j"""
        with self._get_session() as session:
            result = session.run("""
                MATCH (k:APIKey {id: $id})
                DELETE k
                RETURN count(k) as deleted
            """, id=key_id)
            record = result.single()
            return record and record["deleted"] > 0

    def update(self, api_key: APIKey) -> None:
        """Update an existing API key in Neo4j"""
        with self._get_session() as session:
            session.run("""
                MATCH (k:APIKey {id: $id})
                SET k.name = $name,
                    k.expires_at = $expires_at,
                    k.last_used_at = $last_used_at,
                    k.status = $status,
                    k.scopes = $scopes,
                    k.description = $description
            """, **api_key.to_dict())


class APIKeyManager:
    """
    Manager class for API key operations.

    Handles key generation, validation, and lifecycle management.
    """

    # Key format: bh_<random_32_chars>
    KEY_PREFIX = "bh_"
    KEY_LENGTH = 32

    def __init__(
        self,
        storage: Optional[APIKeyStorage] = None,
        neo4j_handler=None,
    ):
        """
        Initialize the API key manager.

        Args:
            storage: Optional custom storage backend
            neo4j_handler: Optional Neo4j handler for database storage
        """
        if storage:
            self.storage = storage
        elif neo4j_handler:
            self.storage = Neo4jStorage(neo4j_handler)
        else:
            self.storage = FileBasedStorage()

    def generate_key(self) -> str:
        """Generate a new random API key"""
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)
        return f"{self.KEY_PREFIX}{random_part}"

    def hash_key(self, key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(key.encode()).hexdigest()

    def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Args:
            name: Human-readable name for the key
            scopes: Optional list of permission scopes
            expires_in_days: Optional expiration in days
            created_by: Optional user ID who created the key
            description: Optional description

        Returns:
            Tuple of (raw_key, APIKey object)
            Note: The raw key is only returned once and cannot be retrieved later
        """
        raw_key = self.generate_key()
        key_hash = self.hash_key(raw_key)
        key_prefix = raw_key[:8]

        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()

        api_key = APIKey(
            id=secrets.token_urlsafe(16),
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            created_at=now.isoformat(),
            expires_at=expires_at,
            status=APIKeyStatus.ACTIVE,
            scopes=scopes or [],
            created_by=created_by,
            description=description,
        )

        self.storage.save(api_key)

        return raw_key, api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key to validate

        Returns:
            APIKey object if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith(self.KEY_PREFIX):
            return None

        key_prefix = raw_key[:8]
        api_key = self.storage.get_by_prefix(key_prefix)

        if not api_key:
            return None

        # Verify the full key hash
        key_hash = self.hash_key(raw_key)
        if key_hash != api_key.key_hash:
            return None

        # Check if key is valid (active and not expired)
        if not api_key.is_valid():
            return None

        # Update last used timestamp
        api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        self.storage.update(api_key)

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: The ID of the key to revoke

        Returns:
            True if revoked successfully, False otherwise
        """
        api_key = self.storage.get_by_id(key_id)
        if not api_key:
            return False

        api_key.status = APIKeyStatus.REVOKED
        self.storage.update(api_key)
        return True

    def delete_key(self, key_id: str) -> bool:
        """
        Permanently delete an API key.

        Args:
            key_id: The ID of the key to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        return self.storage.delete(key_id)

    def list_keys(
        self,
        include_revoked: bool = False,
        created_by: Optional[str] = None,
    ) -> List[APIKey]:
        """
        List API keys.

        Args:
            include_revoked: Whether to include revoked keys
            created_by: Optional filter by creator

        Returns:
            List of APIKey objects
        """
        keys = self.storage.list_all(include_revoked=include_revoked)

        if created_by:
            keys = [k for k in keys if k.created_by == created_by]

        return keys

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """
        Get an API key by ID.

        Args:
            key_id: The ID of the key

        Returns:
            APIKey object if found, None otherwise
        """
        return self.storage.get_by_id(key_id)


# Import timedelta for create_api_key
from datetime import timedelta

# Global manager instance (initialized lazily)
_manager: Optional[APIKeyManager] = None


def get_api_key_manager(neo4j_handler=None) -> APIKeyManager:
    """Get or create the global API key manager instance"""
    global _manager
    if _manager is None:
        _manager = APIKeyManager(neo4j_handler=neo4j_handler)
    return _manager


def create_api_key(
    name: str,
    scopes: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
    created_by: Optional[str] = None,
    description: Optional[str] = None,
    neo4j_handler=None,
) -> tuple[str, APIKey]:
    """Convenience function to create an API key"""
    manager = get_api_key_manager(neo4j_handler)
    return manager.create_api_key(
        name=name,
        scopes=scopes,
        expires_in_days=expires_in_days,
        created_by=created_by,
        description=description,
    )


def validate_api_key(raw_key: str, neo4j_handler=None) -> Optional[APIKey]:
    """Convenience function to validate an API key"""
    manager = get_api_key_manager(neo4j_handler)
    return manager.validate_key(raw_key)


def revoke_api_key(key_id: str, neo4j_handler=None) -> bool:
    """Convenience function to revoke an API key"""
    manager = get_api_key_manager(neo4j_handler)
    return manager.revoke_key(key_id)


def list_api_keys(
    include_revoked: bool = False,
    created_by: Optional[str] = None,
    neo4j_handler=None,
) -> List[APIKey]:
    """Convenience function to list API keys"""
    manager = get_api_key_manager(neo4j_handler)
    return manager.list_keys(include_revoked=include_revoked, created_by=created_by)
