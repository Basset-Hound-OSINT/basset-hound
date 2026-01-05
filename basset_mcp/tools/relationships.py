"""
Relationship management tools for MCP.

Provides tools for creating, updating, and querying relationships
between entities in the Basset Hound graph database.
"""

from datetime import datetime

from .base import get_neo4j_handler, get_project_safe_name


# Valid relationship types for reference
VALID_RELATIONSHIP_TYPES = [
    # Generic
    "RELATED_TO", "KNOWS",
    # Professional
    "WORKS_WITH", "BUSINESS_PARTNER", "REPORTS_TO", "MANAGES",
    "COLLEAGUE", "CLIENT", "EMPLOYER", "EMPLOYEE",
    # Family
    "FAMILY", "MARRIED_TO", "PARENT_OF", "CHILD_OF", "SIBLING_OF", "SPOUSE",
    # Social
    "FRIEND", "ACQUAINTANCE", "NEIGHBOR",
    # Organizational
    "MEMBER_OF", "AFFILIATED_WITH",
    # Investigative
    "ASSOCIATED_WITH", "SUSPECTED_ASSOCIATE", "ALIAS_OF",
    # Communication
    "COMMUNICATES_WITH", "CONTACTED"
]

# Confidence levels
VALID_CONFIDENCE_LEVELS = ["confirmed", "high", "medium", "low", "unverified"]


def register_relationship_tools(mcp):
    """Register relationship management tools with the MCP server."""

    @mcp.tool()
    def get_relationship_types() -> dict:
        """
        Get all available relationship types and their categories.

        Returns a list of valid relationship types that can be used when
        creating or updating relationships between entities.

        Returns:
            Dictionary with:
            - types: List of all valid relationship type names
            - categories: Relationship types organized by category
            - confidence_levels: Valid confidence level values
        """
        return {
            "types": VALID_RELATIONSHIP_TYPES,
            "categories": {
                "generic": ["RELATED_TO", "KNOWS"],
                "professional": [
                    "WORKS_WITH", "BUSINESS_PARTNER", "REPORTS_TO", "MANAGES",
                    "COLLEAGUE", "CLIENT", "EMPLOYER", "EMPLOYEE"
                ],
                "family": [
                    "FAMILY", "MARRIED_TO", "PARENT_OF", "CHILD_OF", "SIBLING_OF", "SPOUSE"
                ],
                "social": ["FRIEND", "ACQUAINTANCE", "NEIGHBOR"],
                "organizational": ["MEMBER_OF", "AFFILIATED_WITH"],
                "investigative": ["ASSOCIATED_WITH", "SUSPECTED_ASSOCIATE", "ALIAS_OF"],
                "communication": ["COMMUNICATES_WITH", "CONTACTED"]
            },
            "confidence_levels": VALID_CONFIDENCE_LEVELS
        }

    @mcp.tool()
    def link_entities(
        project_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str = "RELATED_TO",
        confidence: str = "unverified",
        source: str = None,
        notes: str = None,
        bidirectional: bool = False
    ) -> dict:
        """
        Create a named relationship between two entities with properties.

        Uses the "Tagged People" section to store relationships, which provides
        bidirectional relationship tracking with transitive relationship detection.

        Args:
            project_id: The project ID or safe_name
            source_id: The source entity ID
            target_id: The target entity ID
            relationship_type: Type of relationship (e.g., WORKS_WITH, FRIEND, FAMILY)
                Valid types: RELATED_TO, KNOWS, WORKS_WITH, BUSINESS_PARTNER,
                REPORTS_TO, MANAGES, COLLEAGUE, CLIENT, EMPLOYER, EMPLOYEE,
                FAMILY, MARRIED_TO, PARENT_OF, CHILD_OF, SIBLING_OF, SPOUSE,
                FRIEND, ACQUAINTANCE, NEIGHBOR, MEMBER_OF, AFFILIATED_WITH,
                ASSOCIATED_WITH, SUSPECTED_ASSOCIATE, ALIAS_OF, COMMUNICATES_WITH, CONTACTED
            confidence: Confidence level (confirmed, high, medium, low, unverified)
            source: Source of the relationship information (e.g., "LinkedIn", "public records")
            notes: Additional notes about the relationship
            bidirectional: Whether to create the inverse relationship on target entity

        Returns:
            Success status and relationship info
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Build properties
        properties = {
            "timestamp": datetime.now().isoformat()
        }
        if confidence:
            properties["confidence"] = confidence
        if source:
            properties["source"] = source
        if notes:
            properties["notes"] = notes

        # Create the relationship using the new handler method
        if bidirectional:
            result = handler.create_bidirectional_relationship(
                safe_name, source_id, target_id,
                relationship_type, properties
            )
            if not result:
                return {"error": "Failed to create bidirectional relationship"}

            return {
                "success": True,
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "bidirectional": True,
                "forward": result.get("forward"),
                "reverse": result.get("reverse")
            }
        else:
            result = handler.create_relationship(
                safe_name, source_id, target_id,
                relationship_type, properties
            )

            if not result:
                return {"error": "Failed to create relationship"}

            return {
                "success": True,
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "properties": result.get("properties", {})
            }

    @mcp.tool()
    def update_relationship(
        project_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str = None,
        confidence: str = None,
        source: str = None,
        notes: str = None
    ) -> dict:
        """
        Update an existing relationship between two entities.

        Args:
            project_id: The project ID or safe_name
            source_id: The source entity ID
            target_id: The target entity ID
            relationship_type: New relationship type (optional)
            confidence: New confidence level (optional)
            source: New source information (optional)
            notes: New notes (optional)

        Returns:
            Updated relationship info or error
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Build properties update
        properties = {}
        if confidence is not None:
            properties["confidence"] = confidence
        if source is not None:
            properties["source"] = source
        if notes is not None:
            properties["notes"] = notes

        result = handler.update_relationship(
            safe_name, source_id, target_id,
            relationship_type,
            properties if properties else None
        )

        if not result:
            return {"error": f"Relationship between {source_id} and {target_id} not found"}

        return {
            "success": True,
            "source_id": result["source_id"],
            "target_id": result["target_id"],
            "relationship_type": result["relationship_type"],
            "properties": result.get("properties", {})
        }

    @mcp.tool()
    def get_single_relationship(
        project_id: str,
        source_id: str,
        target_id: str
    ) -> dict:
        """
        Get details of a specific relationship between two entities.

        Args:
            project_id: The project ID or safe_name
            source_id: The source entity ID
            target_id: The target entity ID

        Returns:
            Relationship details including type and properties
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        result = handler.get_relationship(safe_name, source_id, target_id)

        if not result:
            return {"error": f"Relationship between {source_id} and {target_id} not found"}

        return result

    @mcp.tool()
    def list_relationships(
        project_id: str,
        entity_id: str = None,
        relationship_type: str = None
    ) -> dict:
        """
        List all relationships in a project, optionally filtered.

        Args:
            project_id: The project ID or safe_name
            entity_id: Filter to relationships involving this entity (optional)
            relationship_type: Filter to this relationship type (optional)

        Returns:
            List of relationships with their types and properties
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        relationships = handler.get_all_relationships(
            safe_name,
            entity_id=entity_id,
            relationship_type=relationship_type
        )

        # Get type counts
        type_counts = handler.get_relationship_type_counts(safe_name)

        return {
            "project_id": project_id,
            "count": len(relationships),
            "relationships": relationships,
            "relationship_type_counts": type_counts
        }

    @mcp.tool()
    def unlink_entities(project_id: str, source_id: str, target_id: str, bidirectional: bool = False) -> dict:
        """
        Remove a relationship between two entities.

        Args:
            project_id: The project ID or safe_name
            source_id: The source entity ID
            target_id: The target entity ID to unlink
            bidirectional: Also remove the reverse relationship from target entity

        Returns:
            Success status
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Delete the relationship using the new handler method
        result = handler.delete_relationship(safe_name, source_id, target_id)

        if not result:
            return {"error": f"No relationship found between {source_id} and {target_id}"}

        # Optionally delete reverse relationship
        if bidirectional:
            handler.delete_relationship(safe_name, target_id, source_id)

        return {
            "success": True,
            "source_id": source_id,
            "unlinked_id": target_id,
            "bidirectional": bidirectional
        }

    @mcp.tool()
    def get_related(project_id: str, entity_id: str) -> dict:
        """
        Get all entities related to a given entity.

        Returns both direct relationships (entities this entity tagged) and
        reverse relationships (entities that tagged this entity), including
        relationship types and properties.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to find relationships for

        Returns:
            Dictionary with direct and reverse relationships, including types and properties
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Get the entity
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Get direct relationships (entities this entity tagged)
        tagged_section = entity.get("profile", {}).get("Tagged People", {})
        direct_ids = tagged_section.get("tagged_people", [])
        relationship_types = tagged_section.get("relationship_types", {})
        relationship_properties = tagged_section.get("relationship_properties", {})

        if not isinstance(direct_ids, list):
            direct_ids = [direct_ids] if direct_ids else []
        if not isinstance(relationship_types, dict):
            relationship_types = {}
        if not isinstance(relationship_properties, dict):
            relationship_properties = {}

        direct_relationships = []
        for related_id in direct_ids:
            related_entity = handler.get_person(safe_name, related_id)
            if related_entity:
                direct_relationships.append({
                    "id": related_id,
                    "relationship_type": relationship_types.get(related_id, "RELATED_TO"),
                    "properties": relationship_properties.get(related_id, {}),
                    "entity": related_entity
                })

        # Get reverse relationships (entities that tagged this entity)
        all_entities = handler.get_all_people(safe_name)
        reverse_relationships = []

        for other_entity in all_entities:
            if other_entity.get("id") == entity_id:
                continue

            other_tagged = other_entity.get("profile", {}).get("Tagged People", {})
            other_tagged_ids = other_tagged.get("tagged_people", [])
            other_rel_types = other_tagged.get("relationship_types", {})
            other_rel_props = other_tagged.get("relationship_properties", {})

            if not isinstance(other_tagged_ids, list):
                other_tagged_ids = [other_tagged_ids] if other_tagged_ids else []
            if not isinstance(other_rel_types, dict):
                other_rel_types = {}
            if not isinstance(other_rel_props, dict):
                other_rel_props = {}

            if entity_id in other_tagged_ids:
                reverse_relationships.append({
                    "id": other_entity.get("id"),
                    "relationship_type": other_rel_types.get(entity_id, "RELATED_TO"),
                    "properties": other_rel_props.get(entity_id, {}),
                    "entity": other_entity
                })

        return {
            "entity_id": entity_id,
            "direct_relationships": direct_relationships,
            "reverse_relationships": reverse_relationships,
            "total_direct": len(direct_relationships),
            "total_reverse": len(reverse_relationships)
        }
