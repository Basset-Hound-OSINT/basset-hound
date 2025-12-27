"""
Advanced Search Service for Basset Hound OSINT Platform.

This module provides full-text search capabilities across entities using
Neo4j's full-text search indexes and fuzzy matching for enhanced results.

Features:
- Full-text search with Neo4j full-text indexes
- Fuzzy matching for sparse results
- Highlighted snippets showing matched text
- Relevance-based scoring
- Field-specific search
- Multi-project search support
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Fuzzy matcher is optional but enhances search
try:
    from .fuzzy_matcher import FuzzyMatcher, get_fuzzy_matcher, RAPIDFUZZ_AVAILABLE
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    FuzzyMatcher = None
    get_fuzzy_matcher = None


# Default searchable field types
DEFAULT_SEARCHABLE_TYPES = {"string", "email", "url", "comment", "ip_address"}

# Index name for full-text search
FULLTEXT_INDEX_NAME = "entity_fulltext_index"


@dataclass
class SearchResult:
    """
    Represents a single search result.

    Attributes:
        entity_id: Unique identifier of the matched entity
        project_id: Project ID the entity belongs to
        entity_type: Type of entity (e.g., 'Person')
        score: Relevance score (higher is more relevant)
        highlights: Field name -> list of matching snippets
        matched_fields: List of field names that matched
        entity_data: Basic entity information (id, profile snippet, etc.)
    """
    entity_id: str
    project_id: str
    entity_type: str
    score: float
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    matched_fields: List[str] = field(default_factory=list)
    entity_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_id": self.entity_id,
            "project_id": self.project_id,
            "entity_type": self.entity_type,
            "score": self.score,
            "highlights": self.highlights,
            "matched_fields": self.matched_fields,
            "entity_data": self.entity_data,
        }


@dataclass
class SearchQuery:
    """
    Represents a search query with filtering options.

    Attributes:
        query: The search text
        project_id: Optional project ID to scope the search (None = all projects)
        entity_types: Optional list of entity types to filter by
        fields: Optional list of specific fields to search in
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        fuzzy: Whether to enable fuzzy matching for sparse results
        highlight: Whether to generate highlighted snippets
    """
    query: str
    project_id: Optional[str] = None
    entity_types: Optional[List[str]] = None
    fields: Optional[List[str]] = None
    limit: int = 20
    offset: int = 0
    fuzzy: bool = True
    highlight: bool = True

    def __post_init__(self):
        """Validate query parameters."""
        if self.limit < 1:
            self.limit = 1
        if self.limit > 100:
            self.limit = 100
        if self.offset < 0:
            self.offset = 0


class SearchService:
    """
    Advanced search service providing full-text search across entities.

    This service combines Neo4j's full-text search capabilities with
    fuzzy matching to provide comprehensive search results.

    Usage:
        service = SearchService(neo4j_handler, config)

        # Basic search
        query = SearchQuery(query="John Doe")
        results, total = await service.search(query)

        # Project-scoped search
        query = SearchQuery(query="email", project_id="my-project")
        results, total = await service.search(query)

        # Build search index
        count = await service.build_search_index("project-id")
    """

    def __init__(
        self,
        neo4j_handler,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the search service.

        Args:
            neo4j_handler: Neo4j database handler instance
            config: Application configuration dictionary
        """
        self.neo4j = neo4j_handler
        self.config = config or {}
        self._fuzzy_matcher: Optional[FuzzyMatcher] = None
        self._searchable_fields: Optional[List[str]] = None

    @property
    def fuzzy_matcher(self) -> Optional[FuzzyMatcher]:
        """Get or create the fuzzy matcher instance."""
        if self._fuzzy_matcher is None and RAPIDFUZZ_AVAILABLE and get_fuzzy_matcher:
            try:
                self._fuzzy_matcher = get_fuzzy_matcher()
            except Exception:
                pass
        return self._fuzzy_matcher

    async def search(self, query: SearchQuery) -> Tuple[List[SearchResult], int]:
        """
        Execute a full-text search across entities.

        This method first attempts to use Neo4j's full-text search,
        then enhances results with fuzzy matching if enabled and
        results are sparse.

        Args:
            query: SearchQuery object containing search parameters

        Returns:
            Tuple of (list of SearchResult, total count)
        """
        if not query.query or not query.query.strip():
            return [], 0

        search_text = query.query.strip()

        # Try full-text search first
        results, total = await self._fulltext_search(query, search_text)

        # If results are sparse and fuzzy matching is enabled, enhance with fuzzy
        if query.fuzzy and len(results) < query.limit and self.fuzzy_matcher:
            fuzzy_results = await self._fuzzy_search(query, search_text, results)
            results.extend(fuzzy_results)
            # Deduplicate by entity_id
            seen = set()
            unique_results = []
            for r in results:
                if r.entity_id not in seen:
                    seen.add(r.entity_id)
                    unique_results.append(r)
            results = unique_results
            total = len(results)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply pagination
        paginated = results[query.offset:query.offset + query.limit]

        return paginated, total

    async def _fulltext_search(
        self,
        query: SearchQuery,
        search_text: str
    ) -> Tuple[List[SearchResult], int]:
        """
        Execute Neo4j full-text search.

        Args:
            query: Search query parameters
            search_text: Cleaned search text

        Returns:
            Tuple of (results, total_count)
        """
        results = []

        # Escape special Lucene characters for safe search
        escaped_text = self._escape_lucene_query(search_text)

        # Build the Cypher query
        # First, try to use full-text index if available
        try:
            # Check if index exists and use it
            cypher = self._build_fulltext_query(query, escaped_text)
            records = self.neo4j.execute_query(cypher["query"], cypher["params"])

            for record in records:
                result = self._record_to_search_result(
                    record,
                    search_text,
                    query.highlight
                )
                if result:
                    results.append(result)

            return results, len(records)

        except Exception:
            # Fall back to property-based search if full-text index fails
            return await self._property_search(query, search_text)

    async def _property_search(
        self,
        query: SearchQuery,
        search_text: str
    ) -> Tuple[List[SearchResult], int]:
        """
        Fallback search using property matching.

        This is used when full-text indexes are not available.

        Args:
            query: Search query parameters
            search_text: Search text

        Returns:
            Tuple of (results, total_count)
        """
        results = []
        search_lower = search_text.lower()

        # Get all entities and search through them
        if query.project_id:
            # Get project by ID
            project = self._get_project_by_id(query.project_id)
            if not project:
                return [], 0
            projects = [project]
        else:
            projects = self.neo4j.get_all_projects()

        for project in projects:
            project_safe_name = project.get("safe_name")
            project_id = project.get("id", project_safe_name)

            entities = self.neo4j.get_all_people(project_safe_name)

            for entity in entities:
                entity_id = entity.get("id", "")
                profile = entity.get("profile", {})

                # Search through profile fields
                matched_fields = []
                highlights = {}
                max_score = 0.0

                for section_id, fields in profile.items():
                    if not isinstance(fields, dict):
                        continue

                    for field_id, value in fields.items():
                        # Check if we should search this field
                        if query.fields and field_id not in query.fields:
                            continue

                        # Search in value
                        field_path = f"{section_id}.{field_id}"
                        match_result = self._search_in_value(
                            value,
                            search_lower,
                            search_text,
                            query.highlight
                        )

                        if match_result["matched"]:
                            matched_fields.append(field_path)
                            if match_result["highlights"]:
                                highlights[field_path] = match_result["highlights"]
                            max_score = max(max_score, match_result["score"])

                if matched_fields:
                    results.append(SearchResult(
                        entity_id=entity_id,
                        project_id=project_id,
                        entity_type="Person",
                        score=max_score,
                        highlights=highlights,
                        matched_fields=matched_fields,
                        entity_data=self._extract_entity_summary(entity),
                    ))

        return results, len(results)

    async def _fuzzy_search(
        self,
        query: SearchQuery,
        search_text: str,
        existing_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Enhance search with fuzzy matching.

        Args:
            query: Search query parameters
            search_text: Search text
            existing_results: Results already found

        Returns:
            Additional fuzzy-matched results
        """
        if not self.fuzzy_matcher:
            return []

        existing_ids = {r.entity_id for r in existing_results}
        fuzzy_results = []

        # Get all entities to search
        if query.project_id:
            project = self._get_project_by_id(query.project_id)
            if not project:
                return []
            projects = [project]
        else:
            projects = self.neo4j.get_all_projects()

        for project in projects:
            project_safe_name = project.get("safe_name")
            project_id = project.get("id", project_safe_name)

            entities = self.neo4j.get_all_people(project_safe_name)

            for entity in entities:
                entity_id = entity.get("id", "")

                # Skip if already in results
                if entity_id in existing_ids:
                    continue

                profile = entity.get("profile", {})
                matched_fields = []
                highlights = {}
                max_score = 0.0

                # Extract all text values and compare with fuzzy matching
                for section_id, fields in profile.items():
                    if not isinstance(fields, dict):
                        continue

                    for field_id, value in fields.items():
                        if query.fields and field_id not in query.fields:
                            continue

                        field_path = f"{section_id}.{field_id}"
                        fuzzy_result = self._fuzzy_match_value(
                            value,
                            search_text,
                            query.highlight
                        )

                        if fuzzy_result["matched"]:
                            matched_fields.append(field_path)
                            if fuzzy_result["highlights"]:
                                highlights[field_path] = fuzzy_result["highlights"]
                            # Reduce score for fuzzy matches
                            max_score = max(max_score, fuzzy_result["score"] * 0.8)

                if matched_fields and max_score >= 0.6:
                    fuzzy_results.append(SearchResult(
                        entity_id=entity_id,
                        project_id=project_id,
                        entity_type="Person",
                        score=max_score,
                        highlights=highlights,
                        matched_fields=matched_fields,
                        entity_data=self._extract_entity_summary(entity),
                    ))

        return fuzzy_results

    async def search_entity(
        self,
        project_id: str,
        entity_id: str,
        query_text: str
    ) -> List[SearchResult]:
        """
        Search within a specific entity.

        Args:
            project_id: Project ID or safe_name
            entity_id: Entity ID to search within
            query_text: Search text

        Returns:
            List of SearchResult with matched fields
        """
        if not query_text or not query_text.strip():
            return []

        search_text = query_text.strip()
        search_lower = search_text.lower()

        # Get the project
        project = self._get_project_by_id(project_id)
        if not project:
            # Try safe_name
            project = self.neo4j.get_project(project_id)

        if not project:
            return []

        project_safe_name = project.get("safe_name", project_id)
        actual_project_id = project.get("id", project_id)

        entity = self.neo4j.get_person(project_safe_name, entity_id)
        if not entity:
            return []

        profile = entity.get("profile", {})
        matched_fields = []
        highlights = {}
        max_score = 0.0

        for section_id, fields in profile.items():
            if not isinstance(fields, dict):
                continue

            for field_id, value in fields.items():
                field_path = f"{section_id}.{field_id}"
                match_result = self._search_in_value(
                    value,
                    search_lower,
                    search_text,
                    highlight=True
                )

                if match_result["matched"]:
                    matched_fields.append(field_path)
                    if match_result["highlights"]:
                        highlights[field_path] = match_result["highlights"]
                    max_score = max(max_score, match_result["score"])

        if matched_fields:
            return [SearchResult(
                entity_id=entity_id,
                project_id=actual_project_id,
                entity_type="Person",
                score=max_score,
                highlights=highlights,
                matched_fields=matched_fields,
                entity_data=self._extract_entity_summary(entity),
            )]

        return []

    def get_searchable_fields(self) -> List[str]:
        """
        Get list of field IDs marked as searchable in config.

        Returns fields of types that support text search.

        Returns:
            List of searchable field identifiers
        """
        if self._searchable_fields is not None:
            return self._searchable_fields

        searchable = []
        sections = self.config.get("sections", [])

        for section in sections:
            section_id = section.get("id", "")
            for field_def in section.get("fields", []):
                field_id = field_def.get("id", "")
                field_type = field_def.get("type", "string")

                if field_type in DEFAULT_SEARCHABLE_TYPES:
                    searchable.append(f"{section_id}.{field_id}")

                # Include component fields for complex types
                for component in field_def.get("components", []):
                    comp_id = component.get("id", "")
                    comp_type = component.get("type", "string")
                    if comp_type in DEFAULT_SEARCHABLE_TYPES:
                        searchable.append(f"{section_id}.{field_id}.{comp_id}")

        self._searchable_fields = searchable
        return searchable

    async def build_search_index(self, project_id: str) -> int:
        """
        Rebuild the search index for a project.

        Creates or updates the Neo4j full-text index for the project's entities.

        Args:
            project_id: Project ID or safe_name

        Returns:
            Number of entities indexed
        """
        project = self._get_project_by_id(project_id)
        if not project:
            project = self.neo4j.get_project(project_id)

        if not project:
            return 0

        project_safe_name = project.get("safe_name", project_id)
        entities = self.neo4j.get_all_people(project_safe_name)

        indexed_count = 0
        for entity in entities:
            entity_id = entity.get("id", "")
            if await self.index_entity(project_id, entity_id, entity):
                indexed_count += 1

        # Try to create/update full-text index
        await self._ensure_fulltext_index()

        return indexed_count

    async def index_entity(
        self,
        project_id: str,
        entity_id: str,
        entity_data: Dict[str, Any]
    ) -> bool:
        """
        Index a single entity for search.

        Extracts searchable text from entity profile and stores
        it in a format optimized for full-text search.

        Args:
            project_id: Project ID
            entity_id: Entity ID
            entity_data: Entity data dictionary

        Returns:
            True if indexing succeeded
        """
        try:
            # Extract all text from profile for indexing
            search_text = self._extract_searchable_text(entity_data)

            # Update the entity with searchable text property
            # This allows full-text index to work on the property
            cypher = """
                MATCH (person:Person {id: $entity_id})
                SET person.search_text = $search_text
                RETURN person
            """

            result = self.neo4j.execute_query(
                cypher,
                {"entity_id": entity_id, "search_text": search_text}
            )

            return len(result) > 0

        except Exception:
            return False

    async def _ensure_fulltext_index(self) -> bool:
        """
        Ensure the full-text search index exists.

        Returns:
            True if index exists or was created
        """
        try:
            # Create full-text index on Person.search_text
            cypher = f"""
                CREATE FULLTEXT INDEX {FULLTEXT_INDEX_NAME} IF NOT EXISTS
                FOR (p:Person)
                ON EACH [p.search_text]
            """
            self.neo4j.execute_query(cypher, {})
            return True
        except Exception:
            return False

    def _build_fulltext_query(
        self,
        query: SearchQuery,
        search_text: str
    ) -> Dict[str, Any]:
        """
        Build a Cypher query for full-text search.

        Args:
            query: Search query parameters
            search_text: Escaped search text

        Returns:
            Dict with 'query' and 'params' keys
        """
        # Build the CALL clause for full-text search
        cypher = f"""
            CALL db.index.fulltext.queryNodes('{FULLTEXT_INDEX_NAME}', $search_text)
            YIELD node, score
            MATCH (project:Project)-[:HAS_PERSON]->(node)
        """

        params = {"search_text": f"*{search_text}*"}

        # Add project filter if specified
        if query.project_id:
            cypher += " WHERE project.id = $project_id OR project.safe_name = $project_id"
            params["project_id"] = query.project_id

        cypher += """
            RETURN node.id as entity_id,
                   project.id as project_id,
                   'Person' as entity_type,
                   score,
                   node as entity
            ORDER BY score DESC
        """

        return {"query": cypher, "params": params}

    def _record_to_search_result(
        self,
        record: Dict[str, Any],
        search_text: str,
        highlight: bool
    ) -> Optional[SearchResult]:
        """
        Convert a Neo4j record to a SearchResult.

        Args:
            record: Neo4j query result record
            search_text: Original search text
            highlight: Whether to generate highlights

        Returns:
            SearchResult or None
        """
        try:
            entity_id = record.get("entity_id", "")
            project_id = record.get("project_id", "")
            entity_type = record.get("entity_type", "Person")
            score = float(record.get("score", 0.0))
            entity = record.get("entity", {})

            if isinstance(entity, dict):
                entity_data = self._extract_entity_summary(entity)
            else:
                entity_data = {"id": entity_id}

            # Generate highlights if requested
            highlights = {}
            matched_fields = []

            if highlight and entity:
                profile = entity.get("profile", {}) if isinstance(entity, dict) else {}
                for section_id, fields in profile.items():
                    if isinstance(fields, dict):
                        for field_id, value in fields.items():
                            match_result = self._search_in_value(
                                value,
                                search_text.lower(),
                                search_text,
                                highlight=True
                            )
                            if match_result["matched"]:
                                field_path = f"{section_id}.{field_id}"
                                matched_fields.append(field_path)
                                if match_result["highlights"]:
                                    highlights[field_path] = match_result["highlights"]

            return SearchResult(
                entity_id=entity_id,
                project_id=project_id,
                entity_type=entity_type,
                score=score,
                highlights=highlights,
                matched_fields=matched_fields,
                entity_data=entity_data,
            )

        except Exception:
            return None

    def _search_in_value(
        self,
        value: Any,
        search_lower: str,
        search_text: str,
        highlight: bool
    ) -> Dict[str, Any]:
        """
        Search for text in a value and optionally generate highlights.

        Args:
            value: Value to search in
            search_lower: Lowercase search text
            search_text: Original search text for highlighting
            highlight: Whether to generate highlights

        Returns:
            Dict with 'matched', 'score', 'highlights' keys
        """
        result = {"matched": False, "score": 0.0, "highlights": []}

        if value is None:
            return result

        # Convert value to searchable strings
        text_values = self._value_to_strings(value)

        for text in text_values:
            if not text:
                continue

            text_lower = text.lower()
            if search_lower in text_lower:
                result["matched"] = True
                # Score based on match quality
                if text_lower == search_lower:
                    result["score"] = max(result["score"], 1.0)
                elif text_lower.startswith(search_lower):
                    result["score"] = max(result["score"], 0.9)
                else:
                    result["score"] = max(result["score"], 0.7)

                if highlight:
                    snippet = self._generate_highlight(text, search_text)
                    if snippet and snippet not in result["highlights"]:
                        result["highlights"].append(snippet)

        return result

    def _fuzzy_match_value(
        self,
        value: Any,
        search_text: str,
        highlight: bool
    ) -> Dict[str, Any]:
        """
        Fuzzy match search text against a value.

        Args:
            value: Value to search in
            search_text: Search text
            highlight: Whether to generate highlights

        Returns:
            Dict with 'matched', 'score', 'highlights' keys
        """
        result = {"matched": False, "score": 0.0, "highlights": []}

        if not self.fuzzy_matcher or value is None:
            return result

        text_values = self._value_to_strings(value)

        for text in text_values:
            if not text or len(text) < 2:
                continue

            # Calculate fuzzy similarity
            try:
                similarity = self.fuzzy_matcher.calculate_similarity(
                    search_text,
                    text,
                    normalize=True
                )

                if similarity >= 0.7:
                    result["matched"] = True
                    result["score"] = max(result["score"], similarity)

                    if highlight:
                        snippet = f"~{text[:100]}..." if len(text) > 100 else f"~{text}"
                        if snippet not in result["highlights"]:
                            result["highlights"].append(snippet)
            except Exception:
                continue

        return result

    def _value_to_strings(self, value: Any) -> List[str]:
        """
        Convert a value to a list of searchable strings.

        Args:
            value: Value to convert

        Returns:
            List of string representations
        """
        if value is None:
            return []

        if isinstance(value, str):
            return [value] if value.strip() else []

        if isinstance(value, (int, float)):
            return [str(value)]

        if isinstance(value, list):
            strings = []
            for item in value:
                strings.extend(self._value_to_strings(item))
            return strings

        if isinstance(value, dict):
            strings = []
            for v in value.values():
                strings.extend(self._value_to_strings(v))
            return strings

        return [str(value)]

    def _generate_highlight(
        self,
        text: str,
        search_text: str,
        context_chars: int = 50
    ) -> str:
        """
        Generate a highlighted snippet showing matched text.

        Args:
            text: Full text containing the match
            search_text: Search text to highlight
            context_chars: Number of context characters around match

        Returns:
            Highlighted snippet with match surrounded by **
        """
        if not text or not search_text:
            return ""

        # Find match position (case insensitive)
        text_lower = text.lower()
        search_lower = search_text.lower()
        pos = text_lower.find(search_lower)

        if pos == -1:
            return ""

        # Calculate snippet boundaries
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(search_text) + context_chars)

        # Extract snippet
        snippet = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        # Highlight the match
        match_start = pos - start + (3 if start > 0 else 0)
        match_end = match_start + len(search_text)

        highlighted = (
            snippet[:match_start] +
            "**" + snippet[match_start:match_end] + "**" +
            snippet[match_end:]
        )

        return highlighted

    def _extract_entity_summary(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a summary of entity data for search results.

        Args:
            entity: Full entity data

        Returns:
            Dict with essential entity info
        """
        summary = {
            "id": entity.get("id", ""),
            "created_at": entity.get("created_at", ""),
        }

        profile = entity.get("profile", {})

        # Try to extract name
        if "core" in profile:
            core = profile["core"]
            if "name" in core:
                names = core["name"]
                if isinstance(names, list) and names:
                    summary["name"] = names[0]
                elif isinstance(names, dict):
                    summary["name"] = names

            # Include email if present
            if "email" in core:
                emails = core["email"]
                if isinstance(emails, list) and emails:
                    summary["email"] = emails[0]
                elif isinstance(emails, str):
                    summary["email"] = emails

        return summary

    def _extract_searchable_text(self, entity: Dict[str, Any]) -> str:
        """
        Extract all searchable text from an entity.

        Args:
            entity: Entity data

        Returns:
            Concatenated searchable text
        """
        texts = []
        profile = entity.get("profile", {})

        for section_id, fields in profile.items():
            if not isinstance(fields, dict):
                continue

            for field_id, value in fields.items():
                strings = self._value_to_strings(value)
                texts.extend(strings)

        return " ".join(texts)

    def _escape_lucene_query(self, text: str) -> str:
        """
        Escape special Lucene query characters.

        Args:
            text: Raw search text

        Returns:
            Escaped text safe for Lucene queries
        """
        special_chars = r'+-&|!(){}[]^"~*?:\\'
        escaped = ""
        for char in text:
            if char in special_chars:
                escaped += "\\" + char
            else:
                escaped += char
        return escaped

    def _get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a project by its ID or safe_name.

        Args:
            project_id: Project ID or safe_name

        Returns:
            Project dict or None
        """
        try:
            projects = self.neo4j.get_all_projects()
            for project in projects:
                if project.get("id") == project_id:
                    return project
                if project.get("safe_name") == project_id:
                    return project
            return None
        except Exception:
            return None


# Module-level singleton instance
_search_service_instance: Optional[SearchService] = None


def get_search_service(
    neo4j_handler=None,
    config: Optional[Dict[str, Any]] = None
) -> SearchService:
    """
    Get or create the SearchService singleton instance.

    Args:
        neo4j_handler: Neo4j handler (required for first call)
        config: Application config (optional)

    Returns:
        SearchService instance
    """
    global _search_service_instance

    if _search_service_instance is None:
        if neo4j_handler is None:
            raise ValueError("neo4j_handler required for first initialization")
        _search_service_instance = SearchService(neo4j_handler, config)

    return _search_service_instance


def set_search_service(service: Optional[SearchService]) -> None:
    """
    Set the global SearchService instance.

    Args:
        service: SearchService instance or None to clear
    """
    global _search_service_instance
    _search_service_instance = service
