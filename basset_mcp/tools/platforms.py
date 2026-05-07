"""
Platform Management Tools for Basset Hound MCP Server (Phase 48).

Provides MCP tools for managing platform entities and account relationships.
"""

from typing import Optional, List
from mcp.server.fastmcp import FastMCP


def register_platform_tools(mcp: FastMCP) -> None:
    """Register all platform-related tools with the MCP server."""

    # Import here to avoid circular dependencies
    from .base import get_neo4j_handler

    @mcp.tool()
    async def list_platforms(
        category: Optional[str] = None,
    ) -> dict:
        """
        List all platform entities.

        Args:
            category: Optional filter by category (social_media, professional, forum, etc.)

        Returns:
            Dictionary with list of platforms
        """
        try:
            neo4j = get_neo4j_handler()
            platforms = await neo4j.list_platforms(category=category)
            return {
                "success": True,
                "platforms": platforms,
                "count": len(platforms),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_platform(platform_id: str) -> dict:
        """
        Get a specific platform entity.

        Args:
            platform_id: Platform entity ID

        Returns:
            Platform details or error
        """
        try:
            neo4j = get_neo4j_handler()
            platform = await neo4j.get_platform(platform_id)
            if not platform:
                return {
                    "success": False,
                    "error": f"Platform {platform_id} not found",
                }
            return {
                "success": True,
                "platform": platform,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def create_platform(
        name: str,
        category: str = "other",
        color: Optional[str] = None,
        icon_class: Optional[str] = None,
        profile_url_template: Optional[str] = None,
        active: bool = True,
        description: Optional[str] = None,
    ) -> dict:
        """
        Create a new platform entity.

        Args:
            name: Platform name (required)
            category: Platform category (default: 'other')
            color: Brand color in hex format
            icon_class: Font Awesome icon class
            profile_url_template: Profile URL template with {username} placeholder
            active: Whether platform is active
            description: Platform description

        Returns:
            Created platform details or error
        """
        try:
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "Platform name is required",
                }

            neo4j = get_neo4j_handler()
            platform_id = await neo4j.create_platform(
                name=name,
                category=category,
                color=color,
                icon_class=icon_class,
                profile_url_template=profile_url_template,
                active=active,
                description=description,
            )

            platform = await neo4j.get_platform(platform_id)
            return {
                "success": True,
                "platform": platform,
                "message": f"Platform '{name}' created successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def update_platform(
        platform_id: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        icon_class: Optional[str] = None,
        profile_url_template: Optional[str] = None,
        active: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Update a platform entity.

        Args:
            platform_id: Platform ID to update
            name: Updated name
            category: Updated category
            color: Updated color
            icon_class: Updated icon class
            profile_url_template: Updated URL template
            active: Updated active status
            description: Updated description

        Returns:
            Updated platform details or error
        """
        try:
            neo4j = get_neo4j_handler()

            # Validate platform exists
            platform = await neo4j.get_platform(platform_id)
            if not platform:
                return {
                    "success": False,
                    "error": f"Platform {platform_id} not found",
                }

            # Build update dict from provided parameters
            updates = {}
            if name is not None:
                updates["name"] = name
            if category is not None:
                updates["category"] = category
            if color is not None:
                updates["color"] = color
            if icon_class is not None:
                updates["icon_class"] = icon_class
            if profile_url_template is not None:
                updates["profile_url_template"] = profile_url_template
            if active is not None:
                updates["active"] = active
            if description is not None:
                updates["description"] = description

            if not updates:
                return {
                    "success": True,
                    "platform": platform,
                    "message": "No changes provided",
                }

            await neo4j.update_platform(platform_id, **updates)
            updated_platform = await neo4j.get_platform(platform_id)

            return {
                "success": True,
                "platform": updated_platform,
                "message": "Platform updated successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def delete_platform(platform_id: str) -> dict:
        """
        Delete a platform entity.

        Args:
            platform_id: Platform ID to delete

        Returns:
            Success/error message
        """
        try:
            neo4j = get_neo4j_handler()

            # Check if platform has any accounts
            entities = await neo4j.get_entities_on_platform(platform_id, limit=1)
            if entities:
                return {
                    "success": False,
                    "error": f"Cannot delete platform: it has {len(entities)} account(s) linked to it",
                }

            success = await neo4j.delete_platform(platform_id)
            if not success:
                return {
                    "success": False,
                    "error": f"Platform {platform_id} not found",
                }

            return {
                "success": True,
                "message": f"Platform {platform_id} deleted successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def link_entity_to_platform(
        entity_id: str,
        platform_id: str,
        username: str,
        profile_url: Optional[str] = None,
        display_name: Optional[str] = None,
        verified: Optional[bool] = None,
        followers: Optional[int] = None,
        bio: Optional[str] = None,
        last_active: Optional[str] = None,
    ) -> dict:
        """
        Link an entity to a platform (create account).

        Args:
            entity_id: Entity ID to link
            platform_id: Platform ID to link to
            username: Account username/handle
            profile_url: Optional profile URL
            display_name: Optional display name
            verified: Optional verified status
            followers: Optional follower count
            bio: Optional bio/description
            last_active: Optional last active timestamp

        Returns:
            Success/error message with account details
        """
        try:
            neo4j = get_neo4j_handler()

            # Validate both entities exist
            entity = await neo4j.get_entity(entity_id)
            platform = await neo4j.get_platform(platform_id)

            if not entity:
                return {
                    "success": False,
                    "error": f"Entity {entity_id} not found",
                }
            if not platform:
                return {
                    "success": False,
                    "error": f"Platform {platform_id} not found",
                }

            await neo4j.link_entity_to_platform(
                entity_id=entity_id,
                platform_id=platform_id,
                username=username,
                profile_url=profile_url,
                display_name=display_name,
                verified=verified,
                followers=followers,
                bio=bio,
                last_active=last_active,
            )

            # Fetch the created account
            accounts = await neo4j.get_accounts_for_entity(entity_id)
            account = next(
                (a for a in accounts if a.get("username") == username),
                None
            )

            return {
                "success": True,
                "account": account,
                "message": f"Entity linked to {platform['name']} successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_accounts_for_entity(entity_id: str) -> dict:
        """
        Get all platform accounts for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of accounts with platform information
        """
        try:
            neo4j = get_neo4j_handler()

            # Validate entity exists
            entity = await neo4j.get_entity(entity_id)
            if not entity:
                return {
                    "success": False,
                    "error": f"Entity {entity_id} not found",
                }

            accounts = await neo4j.get_accounts_for_entity(entity_id)
            return {
                "success": True,
                "accounts": accounts,
                "count": len(accounts),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_entities_on_platform(
        platform_id: str,
        limit: int = 100,
    ) -> dict:
        """
        Get all entities with accounts on a platform.

        Args:
            platform_id: Platform ID
            limit: Maximum number of results

        Returns:
            List of entities with their accounts
        """
        try:
            neo4j = get_neo4j_handler()

            # Validate platform exists
            platform = await neo4j.get_platform(platform_id)
            if not platform:
                return {
                    "success": False,
                    "error": f"Platform {platform_id} not found",
                }

            entities = await neo4j.get_entities_on_platform(platform_id, limit=limit)
            return {
                "success": True,
                "entities": entities,
                "count": len(entities),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def update_account_on_platform(
        entity_id: str,
        platform_id: str,
        username: str,
        profile_url: Optional[str] = None,
        display_name: Optional[str] = None,
        verified: Optional[bool] = None,
        followers: Optional[int] = None,
        bio: Optional[str] = None,
        last_active: Optional[str] = None,
    ) -> dict:
        """
        Update account properties on a platform.

        Args:
            entity_id: Entity ID
            platform_id: Platform ID
            username: Account username
            profile_url: Updated profile URL
            display_name: Updated display name
            verified: Updated verified status
            followers: Updated follower count
            bio: Updated bio
            last_active: Updated last active timestamp

        Returns:
            Success/error message
        """
        try:
            neo4j = get_neo4j_handler()

            # Build update dict
            updates = {}
            if profile_url is not None:
                updates["profile_url"] = profile_url
            if display_name is not None:
                updates["display_name"] = display_name
            if verified is not None:
                updates["verified"] = verified
            if followers is not None:
                updates["followers"] = followers
            if bio is not None:
                updates["bio"] = bio
            if last_active is not None:
                updates["last_active"] = last_active

            if not updates:
                return {
                    "success": True,
                    "message": "No changes provided",
                }

            success = await neo4j.update_account_on_platform(
                entity_id=entity_id,
                platform_id=platform_id,
                username=username,
                **updates,
            )

            if not success:
                return {
                    "success": False,
                    "error": f"Account not found for entity {entity_id} on platform {platform_id}",
                }

            return {
                "success": True,
                "message": "Account updated successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def remove_account_from_platform(
        entity_id: str,
        platform_id: str,
        username: str,
    ) -> dict:
        """
        Remove an entity's account from a platform.

        Args:
            entity_id: Entity ID
            platform_id: Platform ID
            username: Account username to remove

        Returns:
            Success/error message
        """
        try:
            neo4j = get_neo4j_handler()

            success = await neo4j.remove_account_from_platform(
                entity_id=entity_id,
                platform_id=platform_id,
                username=username,
            )

            if not success:
                return {
                    "success": False,
                    "error": f"Account not found for entity {entity_id} on platform {platform_id}",
                }

            return {
                "success": True,
                "message": "Account removed successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
