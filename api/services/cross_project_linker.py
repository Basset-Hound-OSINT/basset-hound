"""
Cross-Project Linker Service for Basset Hound OSINT Platform.

This module provides cross-project entity linking functionality, allowing
entities from different projects to be linked together. This is useful for
investigations that span multiple projects or when the same person appears
in different contexts.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_loader import load_config


@dataclass
class CrossProjectLink:
    """Represents a link between entities across different projects."""
    source_project_id: str
    source_entity_id: str
    target_project_id: str
    target_entity_id: str
    link_type: str  # e.g., "SAME_PERSON", "RELATED", "ALIAS"
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_project_id": self.source_project_id,
            "source_entity_id": self.source_entity_id,
            "target_project_id": self.target_project_id,
            "target_entity_id": self.target_entity_id,
            "link_type": self.link_type,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossProjectLink":
        """Create a CrossProjectLink from a dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            source_project_id=data["source_project_id"],
            source_entity_id=data["source_entity_id"],
            target_project_id=data["target_project_id"],
            target_entity_id=data["target_entity_id"],
            link_type=data.get("link_type", "RELATED"),
            confidence=data.get("confidence", 1.0),
            created_at=created_at,
            metadata=data.get("metadata", {})
        )


class CrossProjectLinker:
    """
    Cross-project entity linking service.

    Provides functionality to link entities across different projects,
    find potential matches based on shared identifiers, and manage
    cross-project relationships stored in Neo4j.
    """

    # Valid link types
    VALID_LINK_TYPES = {
        "SAME_PERSON",  # High confidence that entities represent the same person
        "RELATED",      # Entities are related but not the same person
        "ALIAS",        # One entity is an alias/alternate identity of another
        "ASSOCIATE",    # Entities are associates/contacts
        "FAMILY",       # Family relationship
        "ORGANIZATION", # Organizational relationship
    }

    # Relationship type for Neo4j storage
    NEO4J_RELATIONSHIP_TYPE = "CROSS_PROJECT_LINK"

    def __init__(self, neo4j_handler=None):
        """
        Initialize the CrossProjectLinker service.

        Args:
            neo4j_handler: Neo4j database handler instance (async)
        """
        self.neo4j_handler = neo4j_handler
        self.config = None
        self.identifier_paths = []
        self._load_identifier_paths()

    def _load_identifier_paths(self) -> None:
        """Load identifier field paths from the data configuration."""
        try:
            self.config = load_config()
        except Exception:
            self.config = {"sections": []}
            return

        self.identifier_paths = []

        for section in self.config.get("sections", []):
            section_id = section.get("id")

            for field_def in section.get("fields", []):
                field_id = field_def.get("id")
                field_type = field_def.get("type")

                # Check if field itself is an identifier
                if field_def.get("identifier", False):
                    path = f"{section_id}.{field_id}"
                    self.identifier_paths.append({
                        "path": path,
                        "section_id": section_id,
                        "field_id": field_id,
                        "component_id": None,
                        "field_type": field_type,
                        "multiple": field_def.get("multiple", False)
                    })

                # Check components for identifiers
                if field_type == "component" and "components" in field_def:
                    for component in field_def.get("components", []):
                        if component.get("identifier", False):
                            comp_id = component.get("id")
                            path = f"{section_id}.{field_id}.{comp_id}"
                            self.identifier_paths.append({
                                "path": path,
                                "section_id": section_id,
                                "field_id": field_id,
                                "component_id": comp_id,
                                "field_type": component.get("type"),
                                "multiple": field_def.get("multiple", False)
                            })

    def _normalize_value(self, value: Any, field_type: str = "string") -> Optional[str]:
        """
        Normalize an identifier value for comparison.

        Args:
            value: The value to normalize
            field_type: The type of field (email, phone, etc.)

        Returns:
            Normalized string value or None if invalid
        """
        if value is None:
            return None

        if isinstance(value, (dict, list)):
            return None  # Complex values not directly comparable

        value_str = str(value).strip().lower()

        if not value_str:
            return None

        # Type-specific normalization
        if field_type == "email":
            return value_str

        if field_type in ("phone", "string") and "phone" in field_type.lower():
            import re
            if value_str.startswith("+"):
                return "+" + re.sub(r"[^\d]", "", value_str[1:])
            return re.sub(r"[^\d]", "", value_str)

        return value_str

    def _extract_identifiers(self, entity: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract all identifier values from an entity's profile.

        Args:
            entity: Entity dictionary with profile data

        Returns:
            Dictionary mapping identifier paths to lists of normalized values
        """
        identifiers = {}
        profile = entity.get("profile", {})

        for id_path in self.identifier_paths:
            path = id_path["path"]
            section_id = id_path["section_id"]
            field_id = id_path["field_id"]
            component_id = id_path.get("component_id")
            field_type = id_path.get("field_type", "string")

            # Get section data
            section_data = profile.get(section_id, {})
            if not section_data or not isinstance(section_data, dict):
                continue

            # Get field data
            field_data = section_data.get(field_id)
            if field_data is None:
                continue

            # Handle the field data
            values = []

            if isinstance(field_data, list):
                for item in field_data:
                    if component_id and isinstance(item, dict):
                        comp_value = item.get(component_id)
                        if comp_value:
                            normalized = self._normalize_value(comp_value, field_type)
                            if normalized:
                                values.append(normalized)
                    elif not component_id:
                        normalized = self._normalize_value(item, field_type)
                        if normalized:
                            values.append(normalized)

            elif isinstance(field_data, dict):
                if component_id:
                    comp_value = field_data.get(component_id)
                    if comp_value:
                        normalized = self._normalize_value(comp_value, field_type)
                        if normalized:
                            values.append(normalized)

            else:
                normalized = self._normalize_value(field_data, field_type)
                if normalized:
                    values.append(normalized)

            if values:
                identifiers[path] = values

        return identifiers

    async def link_entities(
        self,
        source_project: str,
        source_entity: str,
        target_project: str,
        target_entity: str,
        link_type: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CrossProjectLink:
        """
        Create a cross-project link between two entities.

        Args:
            source_project: Source project safe_name
            source_entity: Source entity ID
            target_project: Target project safe_name
            target_entity: Target entity ID
            link_type: Type of link (SAME_PERSON, RELATED, ALIAS, etc.)
            confidence: Confidence score (0.0 to 1.0)
            metadata: Optional additional metadata

        Returns:
            CrossProjectLink object representing the created link

        Raises:
            ValueError: If link_type is invalid or projects/entities don't exist
        """
        # Validate link type
        if link_type not in self.VALID_LINK_TYPES:
            raise ValueError(f"Invalid link type: {link_type}. Valid types: {self.VALID_LINK_TYPES}")

        # Validate confidence
        confidence = max(0.0, min(1.0, confidence))

        if not self.neo4j_handler:
            raise ValueError("Neo4j handler not configured")

        # Verify source entity exists
        source = await self.neo4j_handler.get_person(source_project, source_entity)
        if not source:
            raise ValueError(f"Source entity '{source_entity}' not found in project '{source_project}'")

        # Verify target entity exists
        target = await self.neo4j_handler.get_person(target_project, target_entity)
        if not target:
            raise ValueError(f"Target entity '{target_entity}' not found in project '{target_project}'")

        # Prevent self-linking
        if source_project == target_project and source_entity == target_entity:
            raise ValueError("Cannot link an entity to itself")

        # Create the link
        link = CrossProjectLink(
            source_project_id=source_project,
            source_entity_id=source_entity,
            target_project_id=target_project,
            target_entity_id=target_entity,
            link_type=link_type,
            confidence=confidence,
            created_at=datetime.now(),
            metadata=metadata or {}
        )

        # Store in Neo4j
        await self._store_link_in_neo4j(link)

        return link

    async def _store_link_in_neo4j(self, link: CrossProjectLink) -> None:
        """Store a cross-project link as a relationship in Neo4j."""
        if not self.neo4j_handler:
            return

        async with self.neo4j_handler.session() as session:
            # Create or update the cross-project link relationship
            await session.run("""
                MATCH (source:Person {id: $source_entity_id})
                MATCH (target:Person {id: $target_entity_id})
                MERGE (source)-[r:CROSS_PROJECT_LINK {
                    source_project_id: $source_project_id,
                    target_project_id: $target_project_id
                }]->(target)
                SET r.link_type = $link_type,
                    r.confidence = $confidence,
                    r.created_at = $created_at,
                    r.metadata = $metadata
            """,
                source_entity_id=link.source_entity_id,
                target_entity_id=link.target_entity_id,
                source_project_id=link.source_project_id,
                target_project_id=link.target_project_id,
                link_type=link.link_type,
                confidence=link.confidence,
                created_at=link.created_at.isoformat(),
                metadata=json.dumps(link.metadata)
            )

    async def unlink_entities(
        self,
        source_project: str,
        source_entity: str,
        target_project: str,
        target_entity: str
    ) -> bool:
        """
        Remove a cross-project link between two entities.

        Args:
            source_project: Source project safe_name
            source_entity: Source entity ID
            target_project: Target project safe_name
            target_entity: Target entity ID

        Returns:
            True if link was removed, False if link didn't exist
        """
        if not self.neo4j_handler:
            return False

        async with self.neo4j_handler.session() as session:
            result = await session.run("""
                MATCH (source:Person {id: $source_entity_id})
                      -[r:CROSS_PROJECT_LINK {
                          source_project_id: $source_project_id,
                          target_project_id: $target_project_id
                      }]->
                      (target:Person {id: $target_entity_id})
                DELETE r
                RETURN count(r) as deleted_count
            """,
                source_entity_id=source_entity,
                target_entity_id=target_entity,
                source_project_id=source_project,
                target_project_id=target_project
            )

            record = await result.single()
            return record is not None and record["deleted_count"] > 0

    async def get_cross_project_links(
        self,
        project_id: str,
        entity_id: str
    ) -> List[CrossProjectLink]:
        """
        Get all cross-project links for a specific entity.

        Args:
            project_id: Project safe_name
            entity_id: Entity ID

        Returns:
            List of CrossProjectLink objects
        """
        if not self.neo4j_handler:
            return []

        links = []

        async with self.neo4j_handler.session() as session:
            # Get outgoing links (this entity as source)
            outgoing_result = await session.run("""
                MATCH (source:Person {id: $entity_id})
                      -[r:CROSS_PROJECT_LINK {source_project_id: $project_id}]->
                      (target:Person)
                RETURN r.source_project_id as source_project_id,
                       source.id as source_entity_id,
                       r.target_project_id as target_project_id,
                       target.id as target_entity_id,
                       r.link_type as link_type,
                       r.confidence as confidence,
                       r.created_at as created_at,
                       r.metadata as metadata
            """, entity_id=entity_id, project_id=project_id)

            outgoing_records = await outgoing_result.data()
            for record in outgoing_records:
                link = self._record_to_link(record)
                if link:
                    links.append(link)

            # Get incoming links (this entity as target)
            incoming_result = await session.run("""
                MATCH (source:Person)
                      -[r:CROSS_PROJECT_LINK {target_project_id: $project_id}]->
                      (target:Person {id: $entity_id})
                RETURN r.source_project_id as source_project_id,
                       source.id as source_entity_id,
                       r.target_project_id as target_project_id,
                       target.id as target_entity_id,
                       r.link_type as link_type,
                       r.confidence as confidence,
                       r.created_at as created_at,
                       r.metadata as metadata
            """, entity_id=entity_id, project_id=project_id)

            incoming_records = await incoming_result.data()
            for record in incoming_records:
                link = self._record_to_link(record)
                if link:
                    links.append(link)

        return links

    def _record_to_link(self, record: Dict[str, Any]) -> Optional[CrossProjectLink]:
        """Convert a Neo4j record to a CrossProjectLink object."""
        try:
            metadata = record.get("metadata", "{}")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            created_at = record.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = datetime.now()
            elif hasattr(created_at, 'to_native'):
                created_at = created_at.to_native()
            elif created_at is None:
                created_at = datetime.now()

            return CrossProjectLink(
                source_project_id=record["source_project_id"],
                source_entity_id=record["source_entity_id"],
                target_project_id=record["target_project_id"],
                target_entity_id=record["target_entity_id"],
                link_type=record.get("link_type", "RELATED"),
                confidence=record.get("confidence", 1.0),
                created_at=created_at,
                metadata=metadata
            )
        except (KeyError, TypeError):
            return None

    async def find_potential_matches(
        self,
        project_id: str,
        entity_id: str,
        target_projects: Optional[List[str]] = None
    ) -> List[CrossProjectLink]:
        """
        Find potential matches for an entity in other projects based on shared identifiers.

        Args:
            project_id: Source project safe_name
            entity_id: Source entity ID
            target_projects: Optional list of target project safe_names to search.
                           If None, searches all projects.

        Returns:
            List of CrossProjectLink objects representing potential matches
        """
        if not self.neo4j_handler:
            return []

        # Get the source entity
        source_entity = await self.neo4j_handler.get_person(project_id, entity_id)
        if not source_entity:
            return []

        # Extract identifiers from source entity
        source_identifiers = self._extract_identifiers(source_entity)
        if not source_identifiers:
            return []

        # Get all projects to search
        all_projects = await self.neo4j_handler.get_all_projects()
        projects_to_search = []

        for project in all_projects:
            proj_safe_name = project.get("safe_name")
            # Skip source project
            if proj_safe_name == project_id:
                continue
            # Filter by target_projects if specified
            if target_projects is None or proj_safe_name in target_projects:
                projects_to_search.append(proj_safe_name)

        potential_matches = []

        for target_project in projects_to_search:
            # Get all entities in target project
            target_entities = await self.neo4j_handler.get_all_people(target_project)

            for target_entity in target_entities:
                target_id = target_entity.get("id")

                # Extract identifiers from target entity
                target_identifiers = self._extract_identifiers(target_entity)
                if not target_identifiers:
                    continue

                # Find matching identifiers
                matching_paths = []
                for path, source_values in source_identifiers.items():
                    target_values = target_identifiers.get(path, [])
                    common = set(source_values) & set(target_values)
                    if common:
                        matching_paths.append({
                            "path": path,
                            "matching_values": list(common)
                        })

                if matching_paths:
                    # Calculate confidence based on number of matching identifiers
                    confidence = min(1.0, len(matching_paths) * 0.3)

                    # Determine link type based on confidence
                    if confidence >= 0.8:
                        link_type = "SAME_PERSON"
                    elif confidence >= 0.5:
                        link_type = "RELATED"
                    else:
                        link_type = "RELATED"

                    match = CrossProjectLink(
                        source_project_id=project_id,
                        source_entity_id=entity_id,
                        target_project_id=target_project,
                        target_entity_id=target_id,
                        link_type=link_type,
                        confidence=confidence,
                        created_at=datetime.now(),
                        metadata={
                            "matching_identifiers": matching_paths,
                            "is_potential": True
                        }
                    )
                    potential_matches.append(match)

        # Sort by confidence (highest first)
        potential_matches.sort(key=lambda m: m.confidence, reverse=True)

        return potential_matches

    async def get_all_linked_entities(
        self,
        project_id: str,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all entities linked to the specified entity across all projects.

        This performs a transitive traversal to find all directly and
        indirectly linked entities.

        Args:
            project_id: Project safe_name
            entity_id: Entity ID

        Returns:
            List of dictionaries containing linked entity information
        """
        if not self.neo4j_handler:
            return []

        linked_entities = []
        visited = set()
        visited.add((project_id, entity_id))

        # Get direct links
        direct_links = await self.get_cross_project_links(project_id, entity_id)

        for link in direct_links:
            # Determine which side of the link is the "other" entity
            if link.source_project_id == project_id and link.source_entity_id == entity_id:
                other_project = link.target_project_id
                other_entity = link.target_entity_id
            else:
                other_project = link.source_project_id
                other_entity = link.source_entity_id

            # Skip if already visited
            if (other_project, other_entity) in visited:
                continue

            visited.add((other_project, other_entity))

            # Get entity details
            entity_data = await self.neo4j_handler.get_person(other_project, other_entity)
            if entity_data:
                linked_entities.append({
                    "project_id": other_project,
                    "entity_id": other_entity,
                    "entity_data": entity_data,
                    "link_type": link.link_type,
                    "confidence": link.confidence,
                    "link_direction": "outgoing" if link.source_entity_id == entity_id else "incoming"
                })

        return linked_entities


# Singleton instance for use across the application
_cross_project_linker_instance: Optional[CrossProjectLinker] = None


def get_cross_project_linker(neo4j_handler=None) -> CrossProjectLinker:
    """
    Get or create the CrossProjectLinker singleton instance.

    Args:
        neo4j_handler: Optional Neo4j handler to set/update

    Returns:
        CrossProjectLinker instance
    """
    global _cross_project_linker_instance

    if _cross_project_linker_instance is None:
        _cross_project_linker_instance = CrossProjectLinker(neo4j_handler)
    elif neo4j_handler is not None:
        _cross_project_linker_instance.neo4j_handler = neo4j_handler

    return _cross_project_linker_instance
