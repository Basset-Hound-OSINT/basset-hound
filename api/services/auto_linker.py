"""
Auto-Linker Service for Basset Hound OSINT Platform.

This module provides automatic entity linking based on matching identifiers.
It scans entity profiles for identifier fields (email, phone, usernames, crypto
addresses, etc.) and suggests potential duplicates or related entities.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_loader import load_config


@dataclass
class IdentifierMatch:
    """Represents a matching identifier between two entities."""
    identifier_type: str  # e.g., 'email', 'phone', 'twitter.handle'
    path: str  # Full path: section.field or section.field.component
    value: str  # The matching value
    weight: float = 1.0  # Weight for confidence calculation


@dataclass
class LinkSuggestion:
    """Represents a suggested link between two entities."""
    source_entity_id: str
    target_entity_id: str
    target_entity_name: str
    matching_identifiers: List[IdentifierMatch]
    confidence_score: float
    suggested_relationship_type: str = "POTENTIAL_DUPLICATE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "target_entity_name": self.target_entity_name,
            "matching_identifiers": [
                {
                    "identifier_type": m.identifier_type,
                    "path": m.path,
                    "value": m.value,
                    "weight": m.weight
                }
                for m in self.matching_identifiers
            ],
            "confidence_score": self.confidence_score,
            "suggested_relationship_type": self.suggested_relationship_type
        }


class AutoLinker:
    """
    Automatic entity linking service.

    Extracts identifier values from entities and finds matches across
    entities in a project to suggest potential duplicates or relationships.
    """

    # Weights for different identifier types (higher = more significant match)
    IDENTIFIER_WEIGHTS = {
        # Primary identifiers (very high confidence)
        "email": 3.0,
        "phone": 2.5,
        "ssn": 5.0,
        "passport": 4.0,
        "drivers_license": 4.0,

        # Crypto addresses (high confidence - unique)
        "crypto_address": 3.5,
        "bitcoin": 3.5,
        "ethereum": 3.5,

        # Social platform usernames (medium-high)
        "twitter.handle": 2.0,
        "instagram.username": 2.0,
        "github.username": 2.5,
        "reddit.username": 2.0,
        "mastodon.full_handle": 2.0,
        "bluesky.handle": 2.0,
        "nostr.npub": 3.0,

        # Technical identifiers
        "ip_address": 1.5,
        "domain": 2.0,
        "amateur_radio.callsign": 3.0,

        # Default weight for unspecified identifiers
        "default": 1.0
    }

    # Confidence thresholds
    DUPLICATE_THRESHOLD = 5.0  # Score above this suggests same person
    LINK_THRESHOLD = 2.0  # Score above this suggests relationship

    def __init__(self, neo4j_handler=None):
        """
        Initialize the AutoLinker service.

        Args:
            neo4j_handler: Neo4j database handler instance
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
            # Normalize email: lowercase
            return value_str

        if field_type in ("phone", "string") and "phone" in field_type.lower():
            # Normalize phone: remove all non-digits except leading +
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
                # Multiple values
                for item in field_data:
                    if component_id and isinstance(item, dict):
                        # Extract component value
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
                    # Single component value
                    comp_value = field_data.get(component_id)
                    if comp_value:
                        normalized = self._normalize_value(comp_value, field_type)
                        if normalized:
                            values.append(normalized)

            else:
                # Simple value
                normalized = self._normalize_value(field_data, field_type)
                if normalized:
                    values.append(normalized)

            if values:
                identifiers[path] = values

        return identifiers

    def _get_identifier_weight(self, path: str) -> float:
        """
        Get the weight for an identifier path.

        Args:
            path: The identifier path (e.g., 'contact.email', 'social_major.twitter.handle')

        Returns:
            Weight value for confidence calculation
        """
        # Check for exact match
        if path in self.IDENTIFIER_WEIGHTS:
            return self.IDENTIFIER_WEIGHTS[path]

        # Check for partial matches (e.g., 'twitter.handle' in 'social_major.twitter.handle')
        for key, weight in self.IDENTIFIER_WEIGHTS.items():
            if key in path or path.endswith(key):
                return weight

        # Check if path contains identifier hints
        path_lower = path.lower()
        if "email" in path_lower:
            return self.IDENTIFIER_WEIGHTS["email"]
        if "phone" in path_lower:
            return self.IDENTIFIER_WEIGHTS["phone"]
        if "crypto" in path_lower or "wallet" in path_lower:
            return self.IDENTIFIER_WEIGHTS["crypto_address"]

        return self.IDENTIFIER_WEIGHTS["default"]

    def _get_entity_display_name(self, entity: Dict[str, Any]) -> str:
        """
        Get a display name for an entity.

        Args:
            entity: Entity dictionary

        Returns:
            Human-readable name string
        """
        profile = entity.get("profile", {})

        # Try core section for name
        core = profile.get("core", {})
        if core:
            # Check for name component
            names = core.get("name", [])
            if names:
                if isinstance(names, list) and names:
                    name_obj = names[0]
                    if isinstance(name_obj, dict):
                        parts = []
                        if name_obj.get("first_name"):
                            parts.append(name_obj["first_name"])
                        if name_obj.get("middle_name"):
                            parts.append(name_obj["middle_name"])
                        if name_obj.get("last_name"):
                            parts.append(name_obj["last_name"])
                        if parts:
                            return " ".join(parts)

            # Check for alias
            aliases = core.get("alias", [])
            if aliases:
                if isinstance(aliases, list) and aliases:
                    return str(aliases[0])
                return str(aliases)

        # Fall back to entity ID
        return f"Entity {entity.get('id', 'unknown')[:8]}"

    def find_matching_entities(
        self,
        project_safe_name: str,
        entity_id: str,
        min_confidence: float = None
    ) -> List[LinkSuggestion]:
        """
        Find entities that have matching identifiers with the given entity.

        Args:
            project_safe_name: The project safe name
            entity_id: The entity ID to find matches for
            min_confidence: Minimum confidence score (default: LINK_THRESHOLD)

        Returns:
            List of LinkSuggestion objects for matching entities
        """
        if min_confidence is None:
            min_confidence = self.LINK_THRESHOLD

        if not self.neo4j_handler:
            return []

        # Get the source entity
        source_entity = self.neo4j_handler.get_person(project_safe_name, entity_id)
        if not source_entity:
            return []

        # Extract source identifiers
        source_identifiers = self._extract_identifiers(source_entity)
        if not source_identifiers:
            return []

        # Get all entities in the project
        all_entities = self.neo4j_handler.get_all_people(project_safe_name)

        suggestions = []

        for target_entity in all_entities:
            target_id = target_entity.get("id")

            # Skip self
            if target_id == entity_id:
                continue

            # Extract target identifiers
            target_identifiers = self._extract_identifiers(target_entity)
            if not target_identifiers:
                continue

            # Find matches
            matches = []
            for path, source_values in source_identifiers.items():
                target_values = target_identifiers.get(path, [])

                # Find common values
                common = set(source_values) & set(target_values)
                for value in common:
                    weight = self._get_identifier_weight(path)
                    matches.append(IdentifierMatch(
                        identifier_type=path.split(".")[-1] if "." in path else path,
                        path=path,
                        value=value,
                        weight=weight
                    ))

            if matches:
                # Calculate confidence score
                confidence = sum(m.weight for m in matches)

                if confidence >= min_confidence:
                    # Determine relationship type based on confidence
                    if confidence >= self.DUPLICATE_THRESHOLD:
                        rel_type = "POTENTIAL_DUPLICATE"
                    else:
                        rel_type = "SHARED_IDENTIFIER"

                    suggestions.append(LinkSuggestion(
                        source_entity_id=entity_id,
                        target_entity_id=target_id,
                        target_entity_name=self._get_entity_display_name(target_entity),
                        matching_identifiers=matches,
                        confidence_score=confidence,
                        suggested_relationship_type=rel_type
                    ))

        # Sort by confidence score (highest first)
        suggestions.sort(key=lambda s: s.confidence_score, reverse=True)

        return suggestions

    def suggest_links(
        self,
        project_safe_name: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """
        Get link suggestions for an entity with categorized results.

        Args:
            project_safe_name: The project safe name
            entity_id: The entity ID to get suggestions for

        Returns:
            Dictionary with categorized suggestions (duplicates, links)
        """
        suggestions = self.find_matching_entities(project_safe_name, entity_id, 0)

        duplicates = []
        links = []

        for suggestion in suggestions:
            if suggestion.confidence_score >= self.DUPLICATE_THRESHOLD:
                duplicates.append(suggestion.to_dict())
            elif suggestion.confidence_score >= self.LINK_THRESHOLD:
                links.append(suggestion.to_dict())

        return {
            "entity_id": entity_id,
            "potential_duplicates": duplicates,
            "suggested_links": links,
            "total_suggestions": len(duplicates) + len(links)
        }

    def auto_link_all(
        self,
        project_safe_name: str,
        create_links: bool = False
    ) -> Dict[str, Any]:
        """
        Scan all entities in a project and find potential links.

        Args:
            project_safe_name: The project safe name
            create_links: Whether to automatically create suggested links

        Returns:
            Dictionary with all found suggestions and statistics
        """
        if not self.neo4j_handler:
            return {"error": "Database not connected"}

        all_entities = self.neo4j_handler.get_all_people(project_safe_name)

        # Build index of all identifiers
        entity_identifiers = {}
        for entity in all_entities:
            entity_id = entity.get("id")
            identifiers = self._extract_identifiers(entity)
            if identifiers:
                entity_identifiers[entity_id] = {
                    "entity": entity,
                    "identifiers": identifiers
                }

        # Find all matches
        all_suggestions = []
        processed_pairs = set()

        for entity_id, entity_data in entity_identifiers.items():
            source_identifiers = entity_data["identifiers"]

            for other_id, other_data in entity_identifiers.items():
                if other_id == entity_id:
                    continue

                # Skip if already processed (avoid duplicates)
                pair_key = tuple(sorted([entity_id, other_id]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                target_identifiers = other_data["identifiers"]

                # Find matches
                matches = []
                for path, source_values in source_identifiers.items():
                    target_values = target_identifiers.get(path, [])
                    common = set(source_values) & set(target_values)

                    for value in common:
                        weight = self._get_identifier_weight(path)
                        matches.append(IdentifierMatch(
                            identifier_type=path.split(".")[-1] if "." in path else path,
                            path=path,
                            value=value,
                            weight=weight
                        ))

                if matches:
                    confidence = sum(m.weight for m in matches)

                    if confidence >= self.LINK_THRESHOLD:
                        rel_type = "POTENTIAL_DUPLICATE" if confidence >= self.DUPLICATE_THRESHOLD else "SHARED_IDENTIFIER"

                        suggestion = LinkSuggestion(
                            source_entity_id=entity_id,
                            target_entity_id=other_id,
                            target_entity_name=self._get_entity_display_name(other_data["entity"]),
                            matching_identifiers=matches,
                            confidence_score=confidence,
                            suggested_relationship_type=rel_type
                        )
                        all_suggestions.append(suggestion)

        # Sort by confidence
        all_suggestions.sort(key=lambda s: s.confidence_score, reverse=True)

        # Categorize results
        duplicates = [s.to_dict() for s in all_suggestions if s.confidence_score >= self.DUPLICATE_THRESHOLD]
        links = [s.to_dict() for s in all_suggestions if self.LINK_THRESHOLD <= s.confidence_score < self.DUPLICATE_THRESHOLD]

        # Optionally create links
        links_created = 0
        if create_links:
            for suggestion in all_suggestions:
                if suggestion.confidence_score >= self.LINK_THRESHOLD:
                    try:
                        self._create_link(
                            project_safe_name,
                            suggestion.source_entity_id,
                            suggestion.target_entity_id,
                            suggestion.suggested_relationship_type
                        )
                        links_created += 1
                    except Exception:
                        pass

        return {
            "project": project_safe_name,
            "entities_scanned": len(all_entities),
            "entities_with_identifiers": len(entity_identifiers),
            "potential_duplicates": duplicates,
            "suggested_links": links,
            "total_suggestions": len(all_suggestions),
            "links_created": links_created if create_links else None,
            "scanned_at": datetime.now().isoformat()
        }

    def _create_link(
        self,
        project_safe_name: str,
        source_id: str,
        target_id: str,
        relationship_type: str
    ) -> bool:
        """
        Create a link between two entities.

        Args:
            project_safe_name: The project safe name
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship

        Returns:
            True if link was created successfully
        """
        if not self.neo4j_handler:
            return False

        # Get source entity
        source = self.neo4j_handler.get_person(project_safe_name, source_id)
        if not source:
            return False

        # Get existing tagged people
        profile = source.get("profile", {})
        tagged_section = profile.get("Tagged People", {})
        tagged_ids = tagged_section.get("tagged_people", [])

        if not isinstance(tagged_ids, list):
            tagged_ids = [tagged_ids] if tagged_ids else []

        # Add target if not already linked
        if target_id not in tagged_ids:
            tagged_ids.append(target_id)

        # Store relationship type
        relationship_types = tagged_section.get("relationship_types", {})
        if not isinstance(relationship_types, dict):
            relationship_types = {}
        relationship_types[target_id] = relationship_type

        # Update entity
        updated_data = {
            "profile": {
                "Tagged People": {
                    "tagged_people": tagged_ids,
                    "relationship_types": relationship_types
                }
            }
        }

        result = self.neo4j_handler.update_person(project_safe_name, source_id, updated_data)
        return result is not None

    def merge_entities(
        self,
        project_safe_name: str,
        primary_entity_id: str,
        secondary_entity_id: str,
        delete_secondary: bool = False
    ) -> Dict[str, Any]:
        """
        Merge two entities into one, combining their profile data.

        The primary entity is kept and updated with data from the secondary.
        Profile data is merged with primary entity data taking precedence
        for conflicting simple values, while arrays are combined.

        Args:
            project_safe_name: The project safe name
            primary_entity_id: The ID of the entity to keep
            secondary_entity_id: The ID of the entity to merge from
            delete_secondary: Whether to delete the secondary entity after merge

        Returns:
            Dictionary with merge results and the updated primary entity
        """
        if not self.neo4j_handler:
            return {"error": "Database not connected"}

        # Get both entities
        primary = self.neo4j_handler.get_person(project_safe_name, primary_entity_id)
        secondary = self.neo4j_handler.get_person(project_safe_name, secondary_entity_id)

        if not primary:
            return {"error": f"Primary entity not found: {primary_entity_id}"}
        if not secondary:
            return {"error": f"Secondary entity not found: {secondary_entity_id}"}

        # Merge profiles
        primary_profile = primary.get("profile", {})
        secondary_profile = secondary.get("profile", {})

        merged_profile = self._merge_profiles(primary_profile, secondary_profile)

        # Update primary entity
        update_data = {"profile": merged_profile}
        updated = self.neo4j_handler.update_person(
            project_safe_name, primary_entity_id, update_data
        )

        if not updated:
            return {"error": "Failed to update primary entity"}

        # Optionally delete secondary
        deleted = False
        if delete_secondary:
            deleted = self.neo4j_handler.delete_person(project_safe_name, secondary_entity_id)

        return {
            "success": True,
            "primary_entity_id": primary_entity_id,
            "secondary_entity_id": secondary_entity_id,
            "secondary_deleted": deleted,
            "merged_entity": updated
        }

    def _merge_profiles(
        self,
        primary: Dict[str, Any],
        secondary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two profile dictionaries.

        Args:
            primary: Primary profile (takes precedence)
            secondary: Secondary profile (fills gaps)

        Returns:
            Merged profile dictionary
        """
        merged = {}

        # Get all section keys
        all_sections = set(primary.keys()) | set(secondary.keys())

        for section_id in all_sections:
            primary_section = primary.get(section_id, {})
            secondary_section = secondary.get(section_id, {})

            if not isinstance(primary_section, dict):
                primary_section = {}
            if not isinstance(secondary_section, dict):
                secondary_section = {}

            merged_section = {}
            all_fields = set(primary_section.keys()) | set(secondary_section.keys())

            for field_id in all_fields:
                primary_value = primary_section.get(field_id)
                secondary_value = secondary_section.get(field_id)

                merged_section[field_id] = self._merge_values(primary_value, secondary_value)

            merged[section_id] = merged_section

        return merged

    def _merge_values(self, primary: Any, secondary: Any) -> Any:
        """
        Merge two values, with primary taking precedence.

        Args:
            primary: Primary value
            secondary: Secondary value

        Returns:
            Merged value
        """
        # If primary is empty/None, use secondary
        if primary is None or primary == "" or primary == []:
            return secondary

        # If secondary is empty/None, use primary
        if secondary is None or secondary == "" or secondary == []:
            return primary

        # If both are lists, combine unique values
        if isinstance(primary, list) and isinstance(secondary, list):
            combined = list(primary)  # Start with primary
            for item in secondary:
                if item not in combined:
                    combined.append(item)
            return combined

        # If both are dicts, merge recursively
        if isinstance(primary, dict) and isinstance(secondary, dict):
            merged = dict(secondary)  # Start with secondary
            merged.update(primary)  # Primary takes precedence
            return merged

        # Default: primary takes precedence
        return primary

    def get_identifier_fields(self) -> List[Dict[str, Any]]:
        """
        Get all identifier fields from the configuration.

        Returns:
            List of identifier field definitions
        """
        return self.identifier_paths.copy()


# Singleton instance for use across the application
_auto_linker_instance: Optional[AutoLinker] = None


def get_auto_linker(neo4j_handler=None) -> AutoLinker:
    """
    Get or create the AutoLinker singleton instance.

    Args:
        neo4j_handler: Optional Neo4j handler to set/update

    Returns:
        AutoLinker instance
    """
    global _auto_linker_instance

    if _auto_linker_instance is None:
        _auto_linker_instance = AutoLinker(neo4j_handler)
    elif neo4j_handler is not None:
        _auto_linker_instance.neo4j_handler = neo4j_handler

    return _auto_linker_instance
