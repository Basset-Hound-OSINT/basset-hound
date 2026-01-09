"""
DataItem model for Phase 43.1: Data ID System.

Every piece of data (email, phone, image, document) gets a unique ID like `data_abc123`.
This enables smart suggestions and better data management across entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass
class DataItem:
    """
    Represents a single piece of data with a unique ID.

    DataItems can be emails, phone numbers, images, documents, or any other
    discrete piece of information. Each DataItem can be linked to an entity
    or exist as an orphan.

    Attributes:
        id: Unique identifier (format: data_abc123)
        type: Type of data (email, phone, image, document, etc.)
        value: Actual data content or file path
        hash: SHA-256 hash for files (optional)
        normalized_value: Normalized version for comparison/matching
        entity_id: ID of linked entity (if any)
        orphan_id: ID of linked orphan (if any)
        created_at: Creation timestamp
        metadata: Additional metadata (source, confidence, etc.)
    """

    id: str
    type: str
    value: Any
    normalized_value: str
    created_at: datetime
    metadata: dict = field(default_factory=dict)
    hash: Optional[str] = None
    entity_id: Optional[str] = None
    orphan_id: Optional[str] = None

    @staticmethod
    def generate_id() -> str:
        """
        Generate a unique data ID with the format data_abc123.

        Returns:
            str: Unique data ID
        """
        # Generate UUID and take first 8 characters for readability
        short_id = str(uuid4()).replace('-', '')[:8]
        return f"data_{short_id}"

    @staticmethod
    def normalize_value(value: Any, data_type: str) -> str:
        """
        Normalize a value for comparison and matching.

        Args:
            value: The value to normalize
            data_type: Type of data (email, phone, etc.)

        Returns:
            str: Normalized value
        """
        if value is None:
            return ""

        value_str = str(value).strip().lower()

        # Type-specific normalization
        if data_type == "email":
            # Remove whitespace, lowercase
            return value_str.replace(" ", "")
        elif data_type == "phone":
            # Remove all non-numeric characters
            return ''.join(c for c in value_str if c.isdigit())
        elif data_type == "url":
            # Remove protocol, www, trailing slash
            normalized = value_str.replace("http://", "").replace("https://", "")
            normalized = normalized.replace("www.", "")
            normalized = normalized.rstrip("/")
            return normalized
        elif data_type == "name":
            # Remove extra whitespace, lowercase
            return ' '.join(value_str.split())
        else:
            # Default: just strip and lowercase
            return value_str

    def to_dict(self) -> dict:
        """
        Convert DataItem to dictionary representation.

        Returns:
            dict: Dictionary representation of the DataItem
        """
        return {
            "id": self.id,
            "type": self.type,
            "value": self.value,
            "hash": self.hash,
            "normalized_value": self.normalized_value,
            "entity_id": self.entity_id,
            "orphan_id": self.orphan_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DataItem":
        """
        Create a DataItem from dictionary representation.

        Args:
            data: Dictionary containing DataItem data

        Returns:
            DataItem: New DataItem instance
        """
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            id=data.get("id", cls.generate_id()),
            type=data["type"],
            value=data["value"],
            hash=data.get("hash"),
            normalized_value=data.get("normalized_value", cls.normalize_value(data["value"], data["type"])),
            entity_id=data.get("entity_id"),
            orphan_id=data.get("orphan_id"),
            created_at=created_at,
            metadata=data.get("metadata", {})
        )


# Common data types
DATA_TYPES = [
    "email",
    "phone",
    "name",
    "url",
    "address",
    "image",
    "document",
    "video",
    "audio",
    "username",
    "identifier",
    "date",
    "location",
    "organization",
    "other"
]
