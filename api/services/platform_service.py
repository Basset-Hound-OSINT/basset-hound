"""
Platform Service for Basset Hound (Phase 48: Dynamic Entity Architecture).

Provides business logic for managing platform entities and account relationships.
"""

from typing import Optional, List, Dict, Any
from .neo4j_service import AsyncNeo4jService
import logging

logger = logging.getLogger(__name__)


class PlatformService:
    """Service for platform entity management."""

    def __init__(self, neo4j_service: AsyncNeo4jService):
        """Initialize platform service."""
        self.neo4j = neo4j_service

    async def list_platforms(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all platforms, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of platform entities
        """
        return await self.neo4j.list_platforms(category=category)

    async def get_platform(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """
        Get platform details by ID.

        Args:
            platform_id: Platform entity ID

        Returns:
            Platform properties or None if not found
        """
        return await self.neo4j.get_platform(platform_id)

    async def create_platform(
        self,
        name: str,
        category: str = "other",
        **kwargs,
    ) -> str:
        """
        Create a new platform entity.

        Args:
            name: Platform name (required)
            category: Platform category
            **kwargs: Additional properties

        Returns:
            Platform entity ID
        """
        if not name or not name.strip():
            raise ValueError("Platform name is required")

        return await self.neo4j.create_platform(
            name=name,
            category=category,
            **kwargs,
        )

    async def update_platform(
        self,
        platform_id: str,
        **kwargs,
    ) -> bool:
        """
        Update platform properties.

        Args:
            platform_id: Platform entity ID
            **kwargs: Properties to update

        Returns:
            True if updated, False if not found
        """
        if not kwargs:
            return True

        # Validate platform exists
        platform = await self.get_platform(platform_id)
        if not platform:
            raise ValueError(f"Platform {platform_id} not found")

        return await self.neo4j.update_platform(platform_id, **kwargs)

    async def delete_platform(self, platform_id: str) -> bool:
        """
        Delete a platform entity.

        Args:
            platform_id: Platform entity ID

        Returns:
            True if deleted, False if not found or has accounts

        Raises:
            ValueError: If platform has accounts linked to it
        """
        # Check if platform has any accounts
        entities = await self.neo4j.get_entities_on_platform(platform_id, limit=1)
        if entities:
            raise ValueError(
                f"Cannot delete platform {platform_id}: it has {len(entities)} account(s) linked to it"
            )

        return await self.neo4j.delete_platform(platform_id)

    async def link_entity_to_platform(
        self,
        entity_id: str,
        platform_id: str,
        username: str,
        **account_properties,
    ) -> bool:
        """
        Link an entity to a platform (create account).

        Args:
            entity_id: Entity ID
            platform_id: Platform ID
            username: Account username/handle
            **account_properties: Additional account properties

        Returns:
            True if linked, False otherwise

        Raises:
            ValueError: If entity or platform not found
        """
        # Validate both entities exist
        entity = await self.neo4j.get_entity(entity_id)
        platform = await self.get_platform(platform_id)

        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        if not platform:
            raise ValueError(f"Platform {platform_id} not found")

        return await self.neo4j.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username=username,
            **account_properties,
        )

    async def get_accounts_for_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all platform accounts for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of accounts with platform information
        """
        return await self.neo4j.get_accounts_for_entity(entity_id)

    async def get_entities_on_platform(
        self,
        platform_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all entities with accounts on a platform.

        Args:
            platform_id: Platform ID
            limit: Maximum number of results

        Returns:
            List of entities with their accounts
        """
        return await self.neo4j.get_entities_on_platform(platform_id, limit=limit)

    async def update_account_on_platform(
        self,
        entity_id: str,
        platform_id: str,
        username: str,
        **account_properties,
    ) -> bool:
        """
        Update account properties.

        Args:
            entity_id: Entity ID
            platform_id: Platform ID
            username: Account username
            **account_properties: Properties to update

        Returns:
            True if updated, False otherwise
        """
        if not account_properties:
            return True

        return await self.neo4j.update_account_on_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username=username,
            **account_properties,
        )

    async def remove_account_from_platform(
        self,
        entity_id: str,
        platform_id: str,
        username: str,
    ) -> bool:
        """
        Remove an account from a platform.

        Args:
            entity_id: Entity ID
            platform_id: Platform ID
            username: Account username to remove

        Returns:
            True if removed, False otherwise
        """
        return await self.neo4j.remove_account_from_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username=username,
        )


# Global service instance
_platform_service: Optional[PlatformService] = None


def get_platform_service(neo4j_service: AsyncNeo4jService) -> PlatformService:
    """Get or create platform service instance."""
    global _platform_service
    if _platform_service is None:
        _platform_service = PlatformService(neo4j_service)
    return _platform_service
