"""
Auto-linking tools for MCP.

Provides tools for automatically detecting duplicate entities and
suggesting/creating relationships based on shared identifiers.
"""

import os
import sys

from .base import get_neo4j_handler, get_project_safe_name

# Lazy initialization of AutoLinker
_auto_linker = None


def get_auto_linker():
    """Get or create AutoLinker instance."""
    global _auto_linker
    if _auto_linker is None:
        # Import here to avoid circular imports
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from api.services.auto_linker import AutoLinker
        _auto_linker = AutoLinker(get_neo4j_handler())
    return _auto_linker


def register_auto_linking_tools(mcp):
    """Register auto-linking tools with the MCP server."""

    @mcp.tool()
    def find_duplicates(project_id: str, entity_id: str = None, min_confidence: float = 5.0) -> dict:
        """
        Find potential duplicate entities based on matching identifiers.

        Scans entities for matching identifiers such as email addresses, phone numbers,
        usernames, crypto addresses, and other identifier fields marked in the schema.
        Returns entities that likely represent the same person based on shared identifiers.

        If entity_id is provided, finds duplicates for that specific entity.
        If entity_id is not provided, scans all entities in the project for duplicates.

        Confidence scoring:
        - 5.0+: Very likely the same person (multiple matching identifiers)
        - 3.0-5.0: Probably the same person (key identifiers match)
        - 2.0-3.0: Possibly related (some shared identifiers)

        Args:
            project_id: The project ID or safe_name
            entity_id: Optional entity ID to find duplicates for. If None, scans entire project.
            min_confidence: Minimum confidence score to consider as duplicate (default: 5.0)

        Returns:
            Dictionary with:
            - duplicates: List of potential duplicate pairs with matching identifiers
            - confidence_scores: Confidence level for each match
            - matching_identifiers: Specific identifiers that matched
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        auto_linker = get_auto_linker()

        if entity_id:
            # Find duplicates for specific entity
            suggestions = auto_linker.find_matching_entities(
                safe_name, entity_id, min_confidence=min_confidence
            )

            return {
                "entity_id": entity_id,
                "project_id": project_id,
                "duplicates": [s.to_dict() for s in suggestions],
                "count": len(suggestions)
            }
        else:
            # Scan entire project for duplicates
            result = auto_linker.auto_link_all(safe_name, create_links=False)

            # Filter to only high-confidence duplicates
            duplicates = [d for d in result.get("potential_duplicates", [])
                         if d.get("confidence_score", 0) >= min_confidence]

            return {
                "project_id": project_id,
                "entities_scanned": result.get("entities_scanned", 0),
                "duplicates": duplicates,
                "count": len(duplicates),
                "scanned_at": result.get("scanned_at")
            }

    @mcp.tool()
    def suggest_entity_links(project_id: str, entity_id: str) -> dict:
        """
        Suggest potential connections for an entity based on shared identifiers.

        Analyzes the entity's profile for identifier fields (emails, phones, usernames,
        etc.) and finds other entities that share any of these identifiers. Returns
        categorized suggestions:

        - potential_duplicates: High confidence matches (likely same person)
        - suggested_links: Lower confidence matches (possibly related/connected)

        This is useful for:
        - Identifying duplicate profiles that should be merged
        - Discovering connections between entities
        - Finding related accounts across platforms

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to find suggestions for

        Returns:
            Dictionary with:
            - potential_duplicates: High-confidence matches (confidence >= 5.0)
            - suggested_links: Lower-confidence matches (confidence 2.0-5.0)
            - total_suggestions: Total number of suggestions found
            - matching_identifiers: Details of which identifiers matched
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify entity exists
        handler = get_neo4j_handler()
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        auto_linker = get_auto_linker()
        result = auto_linker.suggest_links(safe_name, entity_id)

        return result

    @mcp.tool()
    def merge_entities(
        project_id: str,
        primary_entity_id: str,
        secondary_entity_id: str,
        delete_secondary: bool = False
    ) -> dict:
        """
        Merge two entities that represent the same person.

        Combines profile data from the secondary entity into the primary entity.
        The primary entity is preserved and updated, while the secondary entity
        can optionally be deleted after the merge.

        Merge behavior:
        - For simple values: Primary entity values take precedence
        - For lists/arrays: Values are combined (duplicates removed)
        - For nested objects: Merged recursively, primary takes precedence

        Common use cases:
        - Merging duplicate profiles discovered through find_duplicates
        - Consolidating data from multiple investigation sources
        - Cleaning up accidentally split profiles

        Args:
            project_id: The project ID or safe_name
            primary_entity_id: The entity to keep and merge into
            secondary_entity_id: The entity to merge from
            delete_secondary: Whether to delete the secondary entity after merge (default: False)

        Returns:
            Dictionary with:
            - success: Boolean indicating if merge succeeded
            - merged_entity: The updated primary entity with merged data
            - secondary_deleted: Whether the secondary was deleted
            - merge_details: Information about what data was merged
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        auto_linker = get_auto_linker()
        result = auto_linker.merge_entities(
            safe_name,
            primary_entity_id,
            secondary_entity_id,
            delete_secondary=delete_secondary
        )

        return result

    @mcp.tool()
    def auto_link_project(project_id: str, create_links: bool = False) -> dict:
        """
        Scan all entities in a project for potential links and duplicates.

        Performs a comprehensive scan of all entities in the project, extracting
        identifier values and finding matches across the entire dataset. This is
        useful for:

        - Initial data quality assessment
        - Discovering hidden connections in imported data
        - Bulk duplicate detection
        - Automated relationship creation

        The scan extracts values from all identifier fields defined in the schema,
        including emails, phone numbers, social media usernames, crypto addresses,
        and other unique identifiers.

        Args:
            project_id: The project ID or safe_name
            create_links: Whether to automatically create links for suggestions (default: False)
                         If True, creates "Tagged People" relationships for matches

        Returns:
            Dictionary with:
            - entities_scanned: Total number of entities analyzed
            - entities_with_identifiers: Entities that have identifier values
            - potential_duplicates: High-confidence duplicate pairs
            - suggested_links: Lower-confidence relationship suggestions
            - total_suggestions: Total suggestions found
            - links_created: Number of links created (if create_links=True)
            - scanned_at: Timestamp of the scan
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        auto_linker = get_auto_linker()
        result = auto_linker.auto_link_all(safe_name, create_links=create_links)

        return result
