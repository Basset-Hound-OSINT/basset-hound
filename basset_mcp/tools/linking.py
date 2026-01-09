"""
Linking action tools for MCP - Phase 43.5: Linking Actions.

Provides tools for acting on smart suggestions with proper audit trails
and human accountability.
"""

import asyncio
from typing import Optional

from .base import get_neo4j_handler, get_project_safe_name


def register_linking_tools(mcp):
    """Register linking action tools with the MCP server."""

    @mcp.tool()
    def link_data_items(
        project_id: str,
        data_id_1: str,
        data_id_2: str,
        reason: str,
        confidence: float = 0.8,
    ) -> dict:
        """
        Link two DataItems together with a LINKED_TO relationship.

        Use this when two data items represent the same information, such as:
        - Same email appearing in different contexts
        - Same image uploaded multiple times
        - Same phone number in different formats
        - Duplicate documents

        This creates a bidirectional LINKED_TO relationship with audit trail.
        The reason parameter is REQUIRED for human accountability.

        Args:
            project_id: The project ID or safe_name
            data_id_1: First DataItem ID (format: data_abc123)
            data_id_2: Second DataItem ID (format: data_abc123)
            reason: Human-readable reason for linking (REQUIRED)
            confidence: Confidence score 0.0-1.0 (default: 0.8)

        Returns:
            Dictionary with:
            - success: Boolean indicating if link succeeded
            - action_id: Unique ID for this linking action (for audit trail)
            - linked_data_items: List of the two linked data IDs
            - reason: The reason provided
            - confidence: Confidence score
            - created_at: Timestamp of the action

        Example:
            link_data_items(
                project_id="my_project",
                data_id_1="data_abc123",
                data_id_2="data_xyz789",
                reason="Same email address found in different sources",
                confidence=0.9
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not reason or not reason.strip():
            return {"error": "Reason is required for linking data items"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _link():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                result = await service.link_data_items(
                    data_id_1=data_id_1,
                    data_id_2=data_id_2,
                    reason=reason,
                    confidence=confidence,
                    created_by="mcp_user",
                )
                return result

        try:
            result = asyncio.run(_link())
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to link data items: {str(e)}"}

    @mcp.tool()
    def merge_entities(
        project_id: str,
        entity_id_1: str,
        entity_id_2: str,
        keep_entity_id: str,
        reason: str,
    ) -> dict:
        """
        Merge two entities that represent the same person.

        ⚠️ WARNING: This operation is IRREVERSIBLE (except via audit trail rollback).
        All data, relationships, and profile information from the discarded entity
        are moved to the kept entity. The discarded entity is marked as merged.

        Use this when:
        - Two profiles represent the same person (duplicates)
        - High-confidence data matching indicates same entity
        - Manual investigation confirms they are the same person

        The reason parameter is REQUIRED for human accountability.

        Args:
            project_id: The project ID or safe_name
            entity_id_1: First entity ID
            entity_id_2: Second entity ID
            keep_entity_id: Which entity to keep (must be entity_id_1 or entity_id_2)
            reason: Human-readable reason for merge (REQUIRED)

        Returns:
            Dictionary with:
            - success: Boolean indicating if merge succeeded
            - action_id: Unique ID for this merge action
            - kept_entity_id: The entity that was kept
            - merged_entity_id: The entity that was merged and discarded
            - data_items_moved: Number of DataItems moved
            - relationships_moved: Number of relationships moved
            - warning: Reminder that merge is irreversible

        Example:
            merge_entities(
                project_id="my_project",
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                keep_entity_id="ent_abc123",
                reason="Same person confirmed via multiple matching identifiers and manual review"
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not reason or not reason.strip():
            return {"error": "Reason is required for merging entities"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _merge():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                result = await service.merge_entities(
                    entity_id_1=entity_id_1,
                    entity_id_2=entity_id_2,
                    keep_entity_id=keep_entity_id,
                    reason=reason,
                    created_by="mcp_user",
                )
                return result

        try:
            result = asyncio.run(_merge())
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to merge entities: {str(e)}"}

    @mcp.tool()
    def create_relationship_from_match(
        project_id: str,
        entity_id_1: str,
        entity_id_2: str,
        relationship_type: str,
        reason: str,
        confidence: Optional[str] = None,
    ) -> dict:
        """
        Create a relationship between two entities based on a suggestion.

        Use this when entities are related but NOT duplicates. For example:
        - Two people sharing an address (might be FAMILY, NEIGHBOR, or WORKS_WITH)
        - Two people with same employer (COLLEAGUE, WORKS_WITH)
        - Two people communicating (KNOWS, COMMUNICATES_WITH)

        Common relationship types:
        - WORKS_WITH: Professional colleagues
        - KNOWS: General acquaintance
        - FAMILY: Family members
        - FRIEND: Social friends
        - NEIGHBOR: Live nearby
        - COLLEAGUE: Work together
        - BUSINESS_PARTNER: Business relationship
        - ASSOCIATED_WITH: General association

        The reason parameter is REQUIRED for human accountability.

        Args:
            project_id: The project ID or safe_name
            entity_id_1: First entity ID (source)
            entity_id_2: Second entity ID (target)
            relationship_type: Type of relationship (see list above)
            reason: Human-readable reason for creating relationship (REQUIRED)
            confidence: Confidence level (confirmed, high, medium, low, unverified)

        Returns:
            Dictionary with:
            - success: Boolean indicating if relationship was created
            - action_id: Unique ID for this action
            - source_entity_id: Source entity
            - target_entity_id: Target entity
            - relationship_type: Type of relationship created
            - confidence: Confidence level
            - is_symmetric: Whether inverse relationship was also created

        Example:
            create_relationship_from_match(
                project_id="my_project",
                entity_id_1="ent_abc123",
                entity_id_2="ent_xyz789",
                relationship_type="WORKS_WITH",
                confidence="high",
                reason="Both listed as employees at same company on LinkedIn"
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not reason or not reason.strip():
            return {"error": "Reason is required for creating relationships"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _create_relationship():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                result = await service.create_relationship_from_suggestion(
                    entity_id_1=entity_id_1,
                    entity_id_2=entity_id_2,
                    relationship_type=relationship_type,
                    reason=reason,
                    confidence=confidence,
                    created_by="mcp_user",
                )
                return result

        try:
            result = asyncio.run(_create_relationship())
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to create relationship: {str(e)}"}

    @mcp.tool()
    def link_orphan_to_entity(
        project_id: str,
        orphan_id: str,
        entity_id: str,
        reason: str,
    ) -> dict:
        """
        Convert orphan data to entity data by linking it to an entity.

        Use this when:
        - A suggestion indicates orphan data matches an entity
        - Manual investigation confirms orphan belongs to entity
        - Importing data that should be associated with existing entity

        This moves all DataItems from the orphan to the entity and marks
        the orphan as resolved.

        The reason parameter is REQUIRED for human accountability.

        Args:
            project_id: The project ID or safe_name
            orphan_id: Orphan ID to link (format: orphan_abc123)
            entity_id: Entity ID to link to
            reason: Human-readable reason for linking (REQUIRED)

        Returns:
            Dictionary with:
            - success: Boolean indicating if linking succeeded
            - action_id: Unique ID for this action
            - orphan_id: The orphan that was linked
            - entity_id: The entity it was linked to
            - data_items_moved: Number of DataItems moved from orphan to entity

        Example:
            link_orphan_to_entity(
                project_id="my_project",
                orphan_id="orphan_abc123",
                entity_id="ent_xyz789",
                reason="Orphan email matches entity email exactly"
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not reason or not reason.strip():
            return {"error": "Reason is required for linking orphans to entities"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _link_orphan():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                result = await service.link_orphan_to_entity(
                    orphan_id=orphan_id,
                    entity_id=entity_id,
                    reason=reason,
                    created_by="mcp_user",
                )
                return result

        try:
            result = asyncio.run(_link_orphan())
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to link orphan to entity: {str(e)}"}

    @mcp.tool()
    def dismiss_suggestion(
        project_id: str,
        entity_id: str,
        data_id: str,
        reason: str,
    ) -> dict:
        """
        Dismiss a suggestion so it doesn't reappear.

        Use this when:
        - A suggestion is incorrect or not relevant
        - Manual investigation confirms data doesn't match
        - User explicitly rejects a match

        This creates a DISMISSED_SUGGESTION relationship to track that
        the user has explicitly rejected this suggestion. The suggestion
        will not reappear unless the underlying data changes.

        The reason parameter is REQUIRED for human accountability.

        Args:
            project_id: The project ID or safe_name
            entity_id: Entity ID
            data_id: DataItem ID that was suggested (format: data_abc123)
            reason: Human-readable reason for dismissal (REQUIRED)

        Returns:
            Dictionary with:
            - success: Boolean indicating if dismissal succeeded
            - action_id: Unique ID for this action
            - entity_id: The entity
            - data_id: The dismissed data item
            - dismissed_at: Timestamp of dismissal

        Example:
            dismiss_suggestion(
                project_id="my_project",
                entity_id="ent_abc123",
                data_id="data_xyz789",
                reason="Same name but different person - verified via other identifiers"
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not reason or not reason.strip():
            return {"error": "Reason is required for dismissing suggestions"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _dismiss():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                result = await service.dismiss_suggestion(
                    entity_id=entity_id,
                    data_id=data_id,
                    reason=reason,
                    created_by="mcp_user",
                )
                return result

        try:
            result = asyncio.run(_dismiss())
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to dismiss suggestion: {str(e)}"}

    @mcp.tool()
    def get_linking_history(
        project_id: str,
        entity_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        Get audit trail of linking actions for accountability and review.

        Use this to:
        - Review recent linking actions
        - Audit entity merge history
        - Track who made what decisions
        - Prepare for potential rollback

        Action types:
        - link_data_items: Data item linking actions
        - merge_entities: Entity merge actions
        - create_relationship: Relationship creation actions
        - link_orphan_to_entity: Orphan linking actions
        - dismiss_suggestion: Suggestion dismissal actions

        Args:
            project_id: The project ID or safe_name
            entity_id: Optional entity ID to filter by
            action_type: Optional action type to filter by
            limit: Maximum number of results (default: 50)

        Returns:
            Dictionary with:
            - actions: List of linking actions with full details
            - count: Number of actions returned
            - filtered_by: What filters were applied

        Example:
            get_linking_history(
                project_id="my_project",
                entity_id="ent_abc123",
                action_type="merge_entities",
                limit=20
            )
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Import here to avoid circular imports
        from api.services.linking_service import LinkingService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _get_history():
            async with AsyncNeo4jService() as neo4j:
                service = LinkingService(neo4j)
                actions = await service.get_linking_history(
                    entity_id=entity_id,
                    action_type=action_type,
                    limit=limit,
                )
                return {
                    "actions": actions,
                    "count": len(actions),
                    "filtered_by": {
                        "entity_id": entity_id,
                        "action_type": action_type,
                    },
                }

        try:
            result = asyncio.run(_get_history())
            return result
        except Exception as e:
            return {"error": f"Failed to get linking history: {str(e)}"}
