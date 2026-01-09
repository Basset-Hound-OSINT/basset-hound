"""
Suggestion tools for MCP - Phase 43.4: Suggestion System.

Provides on-demand suggestion computation tools for "Suggested Tags" on entity profiles.
Shows matching DataItems from other entities and suggests entities for orphan data.

Tools:
- get_entity_suggestions: Get all suggestions for an entity
- get_orphan_suggestions: Get suggestions to link orphan data
- dismiss_suggestion: Mark suggestion as dismissed
- get_dismissed_suggestions: List dismissed suggestions for an entity
"""

import asyncio
from typing import Optional

from .base import get_project_safe_name


def register_suggestion_tools(mcp):
    """Register suggestion tools with the MCP server."""

    @mcp.tool()
    def get_entity_suggestions(
        project_id: str,
        entity_id: str,
        include_partial: bool = True,
        min_confidence: float = 0.5
    ) -> dict:
        """
        Get on-demand suggestions for an entity based on matching data.

        Finds DataItems from other entities that match this entity's data.
        This is useful for:
        - Finding potential relationships between entities
        - Detecting potential duplicates
        - Suggesting related entities based on shared data

        Suggestions are grouped by confidence level:
        - HIGH (0.9-1.0): Exact hash or exact string matches
        - MEDIUM (0.7-0.89): High similarity fuzzy matches
        - LOW (0.5-0.69): Lower similarity matches

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to get suggestions for
            include_partial: Whether to include partial/fuzzy matches (default: True)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.5)

        Returns:
            Dictionary with suggestions grouped by confidence level, including:
            - entity_id: The entity ID
            - suggestions: List of confidence groups (HIGH/MEDIUM/LOW)
            - dismissed_count: Number of dismissed suggestions
            Each match includes: data_id, data_type, data_value, match_type,
            confidence_score, matched_entity_id, matched_entity_name

        Example:
            {
                "entity_id": "ent_abc123",
                "suggestions": [
                    {
                        "confidence": "HIGH",
                        "matches": [
                            {
                                "data_id": "data_xyz789",
                                "data_type": "email",
                                "data_value": "test@example.com",
                                "match_type": "exact_hash",
                                "confidence_score": 1.0,
                                "matched_entity_id": "ent_def456",
                                "matched_entity_name": "John Doe"
                            }
                        ]
                    }
                ],
                "dismissed_count": 3
            }
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.suggestion_service import SuggestionService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _get_suggestions():
            async with AsyncNeo4jService() as neo4j:
                async with SuggestionService(neo4j_service=neo4j) as service:
                    return await service.get_entity_suggestions(
                        entity_id=entity_id,
                        include_partial=include_partial,
                        min_confidence=min_confidence
                    )

        try:
            result = asyncio.run(_get_suggestions())
            return result
        except Exception as e:
            return {"error": f"Failed to get entity suggestions: {str(e)}"}

    @mcp.tool()
    def get_orphan_suggestions(
        project_id: str,
        orphan_id: str,
        include_partial: bool = True,
        min_confidence: float = 0.5
    ) -> dict:
        """
        Get entity suggestions for orphan data.

        Finds entities that match the orphan's data. This is useful for
        linking orphan data to existing entities.

        Suggestions are grouped by confidence level:
        - HIGH (0.9-1.0): Exact hash or exact string matches
        - MEDIUM (0.7-0.89): High similarity fuzzy matches
        - LOW (0.5-0.69): Lower similarity matches

        Args:
            project_id: The project ID or safe_name
            orphan_id: The orphan ID to get suggestions for
            include_partial: Whether to include partial/fuzzy matches (default: True)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.5)

        Returns:
            Dictionary with suggestions grouped by confidence level, including:
            - orphan_id: The orphan ID
            - suggestions: List of confidence groups (HIGH/MEDIUM/LOW)
            Each match includes: data_id, data_type, data_value, match_type,
            confidence_score, matched_entity_id, matched_entity_name

        Example:
            {
                "orphan_id": "orphan_xyz789",
                "suggestions": [
                    {
                        "confidence": "HIGH",
                        "matches": [
                            {
                                "data_id": "data_abc123",
                                "data_type": "email",
                                "data_value": "test@example.com",
                                "match_type": "exact_string",
                                "confidence_score": 0.95,
                                "matched_entity_id": "ent_def456",
                                "matched_entity_name": "John Doe"
                            }
                        ]
                    }
                ]
            }
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.suggestion_service import SuggestionService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _get_suggestions():
            async with AsyncNeo4jService() as neo4j:
                async with SuggestionService(neo4j_service=neo4j) as service:
                    return await service.get_orphan_suggestions(
                        orphan_id=orphan_id,
                        include_partial=include_partial,
                        min_confidence=min_confidence
                    )

        try:
            result = asyncio.run(_get_suggestions())
            return result
        except Exception as e:
            return {"error": f"Failed to get orphan suggestions: {str(e)}"}

    @mcp.tool()
    def dismiss_suggestion(
        project_id: str,
        entity_id: str,
        data_id: str
    ) -> dict:
        """
        Mark a suggestion as dismissed for an entity.

        Creates a DISMISSED_SUGGESTION relationship between the entity
        and the data item so it won't appear in future suggestions.
        This allows human operators to manually filter out irrelevant suggestions.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID
            data_id: The data ID to dismiss (from a suggestion)

        Returns:
            Success status or error message

        Example:
            {
                "success": True,
                "entity_id": "ent_abc123",
                "data_id": "data_xyz789",
                "message": "Suggestion dismissed successfully"
            }
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.suggestion_service import SuggestionService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _dismiss():
            async with AsyncNeo4jService() as neo4j:
                async with SuggestionService(neo4j_service=neo4j) as service:
                    success = await service.dismiss_suggestion(
                        entity_id=entity_id,
                        data_id=data_id
                    )

                    if success:
                        return {
                            "success": True,
                            "entity_id": entity_id,
                            "data_id": data_id,
                            "message": "Suggestion dismissed successfully"
                        }
                    else:
                        return {
                            "error": "Failed to dismiss suggestion. "
                                     "Check that entity_id and data_id are valid."
                        }

        try:
            result = asyncio.run(_dismiss())
            return result
        except Exception as e:
            return {"error": f"Failed to dismiss suggestion: {str(e)}"}

    @mcp.tool()
    def get_dismissed_suggestions(
        project_id: str,
        entity_id: str
    ) -> dict:
        """
        Get list of all dismissed suggestions for an entity.

        Shows all suggestions that have been manually dismissed by the
        human operator for this entity.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID

        Returns:
            Dictionary with list of dismissed suggestions, including:
            - entity_id: The entity ID
            - dismissed_suggestions: List of dismissed suggestions
            - count: Number of dismissed suggestions
            Each dismissed suggestion includes: data_id, data_type,
            data_value, dismissed_at

        Example:
            {
                "entity_id": "ent_abc123",
                "dismissed_suggestions": [
                    {
                        "data_id": "data_xyz789",
                        "data_type": "email",
                        "data_value": "test@example.com",
                        "dismissed_at": "2026-01-09T12:34:56"
                    }
                ],
                "count": 1
            }
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.suggestion_service import SuggestionService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _get_dismissed():
            async with AsyncNeo4jService() as neo4j:
                async with SuggestionService(neo4j_service=neo4j) as service:
                    return await service.get_dismissed_suggestions_list(entity_id=entity_id)

        try:
            result = asyncio.run(_get_dismissed())
            return result
        except Exception as e:
            return {"error": f"Failed to get dismissed suggestions: {str(e)}"}

    @mcp.tool()
    def undismiss_suggestion(
        project_id: str,
        entity_id: str,
        data_id: str
    ) -> dict:
        """
        Remove a dismissed suggestion to make it appear again.

        Removes the DISMISSED_SUGGESTION relationship so the suggestion
        can appear in future suggestion results.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID
            data_id: The data ID to undismiss

        Returns:
            Success status or error message

        Example:
            {
                "success": True,
                "entity_id": "ent_abc123",
                "data_id": "data_xyz789",
                "message": "Suggestion undismissed successfully"
            }
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.neo4j_service import AsyncNeo4jService

        async def _undismiss():
            async with AsyncNeo4jService() as neo4j:
                async with neo4j.session() as session:
                    result = await session.run(
                        """
                        MATCH (p:Person {id: $entity_id})-[r:DISMISSED_SUGGESTION]->(d:DataItem {id: $data_id})
                        DELETE r
                        RETURN count(r) as deleted
                        """,
                        entity_id=entity_id,
                        data_id=data_id
                    )
                    record = await result.single()

                    if record and record["deleted"] > 0:
                        return {
                            "success": True,
                            "entity_id": entity_id,
                            "data_id": data_id,
                            "message": "Suggestion undismissed successfully"
                        }
                    else:
                        return {
                            "error": "Dismissed suggestion not found. "
                                     "Check that entity_id and data_id are valid."
                        }

        try:
            result = asyncio.run(_undismiss())
            return result
        except Exception as e:
            return {"error": f"Failed to undismiss suggestion: {str(e)}"}
