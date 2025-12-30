"""
Saved Search Service for Basset Hound OSINT Platform.

This module provides functionality to save, manage, and execute
reusable search configurations for entities.

Features:
- Save search configurations with parameters
- Organize searches with tags and categories
- Execute saved searches with optional overrides
- Track search usage and last execution time
- Share searches across projects (global) or scope to project
- Search history and favorites

Usage:
    from api.services.saved_search import (
        SavedSearchService,
        SavedSearchConfig,
        SearchScope,
        get_saved_search_service,
    )

    service = get_saved_search_service()

    # Create a saved search
    config = SavedSearchConfig(
        name="High-Risk Entities",
        description="Find entities with risk indicators",
        query="tag:high-risk OR tag:suspicious",
        scope=SearchScope.PROJECT,
        project_id="project-123",
        is_advanced=True,
        tags=["risk", "monitoring"],
    )

    search_id = await service.create_search(config)

    # Execute saved search
    results = await service.execute_search(search_id)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .search_service import SearchQuery, SearchResult, SearchService


class SearchScope(str, Enum):
    """Scope of a saved search."""
    GLOBAL = "global"  # Available across all projects
    PROJECT = "project"  # Scoped to a specific project
    USER = "user"  # User-specific saved search


class SearchCategory(str, Enum):
    """Category of saved search for organization."""
    GENERAL = "general"
    INVESTIGATION = "investigation"
    MONITORING = "monitoring"
    COMPLIANCE = "compliance"
    RISK = "risk"
    CUSTOM = "custom"


@dataclass
class SavedSearchConfig:
    """
    Configuration for a saved search.

    Attributes:
        name: Display name for the search
        description: Optional description of what the search finds
        query: The search query string
        scope: Where this search is available (global, project, user)
        project_id: Project ID if scope is PROJECT
        user_id: User ID if scope is USER
        is_advanced: Whether to use advanced boolean query parsing
        entity_types: Optional filter by entity types
        fields: Optional list of specific fields to search
        limit: Default result limit
        fuzzy: Whether to enable fuzzy matching
        highlight: Whether to generate highlights
        tags: Tags for organizing searches
        category: Category for organization
        is_favorite: Whether this is a favorite search
        icon: Optional icon identifier
        color: Optional color for UI display
    """
    name: str
    query: str
    description: str = ""
    scope: SearchScope = SearchScope.PROJECT
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    is_advanced: bool = False
    entity_types: Optional[List[str]] = None
    fields: Optional[List[str]] = None
    limit: int = 20
    fuzzy: bool = True
    highlight: bool = True
    tags: List[str] = field(default_factory=list)
    category: SearchCategory = SearchCategory.GENERAL
    is_favorite: bool = False
    icon: Optional[str] = None
    color: Optional[str] = None

    def __post_init__(self):
        """Validate configuration."""
        if not self.name or not self.name.strip():
            raise ValueError("Search name is required")
        if not self.query or not self.query.strip():
            raise ValueError("Search query is required")
        if self.scope == SearchScope.PROJECT and not self.project_id:
            raise ValueError("Project ID required for project-scoped search")
        if self.scope == SearchScope.USER and not self.user_id:
            raise ValueError("User ID required for user-scoped search")
        if self.limit < 1:
            self.limit = 1
        if self.limit > 100:
            self.limit = 100


@dataclass
class SavedSearch:
    """
    A saved search with metadata.

    Attributes:
        id: Unique identifier
        config: Search configuration
        created_at: When the search was created
        updated_at: When the search was last modified
        last_executed_at: When the search was last run
        execution_count: Number of times executed
        created_by: User who created the search
    """
    id: str
    config: SavedSearchConfig
    created_at: datetime
    updated_at: datetime
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.config.name,
            "description": self.config.description,
            "query": self.config.query,
            "scope": self.config.scope.value,
            "project_id": self.config.project_id,
            "user_id": self.config.user_id,
            "is_advanced": self.config.is_advanced,
            "entity_types": self.config.entity_types,
            "fields": self.config.fields,
            "limit": self.config.limit,
            "fuzzy": self.config.fuzzy,
            "highlight": self.config.highlight,
            "tags": self.config.tags,
            "category": self.config.category.value,
            "is_favorite": self.config.is_favorite,
            "icon": self.config.icon,
            "color": self.config.color,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_count": self.execution_count,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedSearch":
        """Create from dictionary."""
        config = SavedSearchConfig(
            name=data["name"],
            description=data.get("description", ""),
            query=data["query"],
            scope=SearchScope(data.get("scope", "project")),
            project_id=data.get("project_id"),
            user_id=data.get("user_id"),
            is_advanced=data.get("is_advanced", False),
            entity_types=data.get("entity_types"),
            fields=data.get("fields"),
            limit=data.get("limit", 20),
            fuzzy=data.get("fuzzy", True),
            highlight=data.get("highlight", True),
            tags=data.get("tags", []),
            category=SearchCategory(data.get("category", "general")),
            is_favorite=data.get("is_favorite", False),
            icon=data.get("icon"),
            color=data.get("color"),
        )

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()

        last_executed_at = data.get("last_executed_at")
        if isinstance(last_executed_at, str):
            last_executed_at = datetime.fromisoformat(last_executed_at)

        return cls(
            id=data["id"],
            config=config,
            created_at=created_at,
            updated_at=updated_at,
            last_executed_at=last_executed_at,
            execution_count=data.get("execution_count", 0),
            created_by=data.get("created_by"),
        )


@dataclass
class SearchExecutionResult:
    """
    Result of executing a saved search.

    Attributes:
        search_id: ID of the saved search
        search_name: Name of the search
        results: List of search results
        total_count: Total number of matches
        execution_time_ms: How long the search took
        executed_at: When the search was executed
        query_used: The actual query that was executed
    """
    search_id: str
    search_name: str
    results: List[SearchResult]
    total_count: int
    execution_time_ms: float
    executed_at: datetime
    query_used: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "search_id": self.search_id,
            "search_name": self.search_name,
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "execution_time_ms": self.execution_time_ms,
            "executed_at": self.executed_at.isoformat(),
            "query_used": self.query_used,
        }


@dataclass
class SearchListFilter:
    """
    Filter options for listing saved searches.

    Attributes:
        scope: Filter by scope
        project_id: Filter by project
        user_id: Filter by user
        category: Filter by category
        tags: Filter by tags (any match)
        is_favorite: Filter favorites only
        name_contains: Filter by name substring
        include_global: Include global searches when filtering by project
    """
    scope: Optional[SearchScope] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    category: Optional[SearchCategory] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    name_contains: Optional[str] = None
    include_global: bool = True


class SavedSearchService:
    """
    Service for managing saved search configurations.

    This service provides CRUD operations for saved searches and
    integrates with the SearchService for execution.
    """

    def __init__(
        self,
        search_service: Optional[SearchService] = None,
        neo4j_handler: Optional[Any] = None,
    ):
        """
        Initialize the service.

        Args:
            search_service: SearchService instance for executing searches
            neo4j_handler: Neo4j handler for persistence (optional)
        """
        self._search_service = search_service
        self._neo4j = neo4j_handler
        # In-memory storage for saved searches
        self._searches: Dict[str, SavedSearch] = {}

    @property
    def search_service(self) -> Optional[SearchService]:
        """Get the search service instance."""
        return self._search_service

    def set_search_service(self, service: SearchService) -> None:
        """Set the search service instance."""
        self._search_service = service

    async def create_search(
        self,
        config: SavedSearchConfig,
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a new saved search.

        Args:
            config: Search configuration
            created_by: User ID of creator

        Returns:
            ID of the created search

        Raises:
            ValueError: If config is invalid
        """
        search_id = str(uuid.uuid4())
        now = datetime.utcnow()

        saved_search = SavedSearch(
            id=search_id,
            config=config,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )

        self._searches[search_id] = saved_search

        return search_id

    async def get_search(self, search_id: str) -> Optional[SavedSearch]:
        """
        Get a saved search by ID.

        Args:
            search_id: Search ID

        Returns:
            SavedSearch or None if not found
        """
        return self._searches.get(search_id)

    async def update_search(
        self,
        search_id: str,
        updates: Dict[str, Any]
    ) -> Optional[SavedSearch]:
        """
        Update a saved search.

        Args:
            search_id: Search ID
            updates: Dictionary of fields to update

        Returns:
            Updated SavedSearch or None if not found
        """
        search = self._searches.get(search_id)
        if not search:
            return None

        # Update config fields
        config = search.config
        config_updates = {}

        for key in ["name", "description", "query", "is_advanced", "entity_types",
                    "fields", "limit", "fuzzy", "highlight", "tags", "is_favorite",
                    "icon", "color"]:
            if key in updates:
                config_updates[key] = updates[key]

        # Handle scope changes
        if "scope" in updates:
            config_updates["scope"] = SearchScope(updates["scope"])
        if "category" in updates:
            config_updates["category"] = SearchCategory(updates["category"])
        if "project_id" in updates:
            config_updates["project_id"] = updates["project_id"]
        if "user_id" in updates:
            config_updates["user_id"] = updates["user_id"]

        # Create updated config
        if config_updates:
            new_config = SavedSearchConfig(
                name=config_updates.get("name", config.name),
                description=config_updates.get("description", config.description),
                query=config_updates.get("query", config.query),
                scope=config_updates.get("scope", config.scope),
                project_id=config_updates.get("project_id", config.project_id),
                user_id=config_updates.get("user_id", config.user_id),
                is_advanced=config_updates.get("is_advanced", config.is_advanced),
                entity_types=config_updates.get("entity_types", config.entity_types),
                fields=config_updates.get("fields", config.fields),
                limit=config_updates.get("limit", config.limit),
                fuzzy=config_updates.get("fuzzy", config.fuzzy),
                highlight=config_updates.get("highlight", config.highlight),
                tags=config_updates.get("tags", config.tags),
                category=config_updates.get("category", config.category),
                is_favorite=config_updates.get("is_favorite", config.is_favorite),
                icon=config_updates.get("icon", config.icon),
                color=config_updates.get("color", config.color),
            )
            search.config = new_config

        search.updated_at = datetime.utcnow()
        return search

    async def delete_search(self, search_id: str) -> bool:
        """
        Delete a saved search.

        Args:
            search_id: Search ID

        Returns:
            True if deleted, False if not found
        """
        if search_id in self._searches:
            del self._searches[search_id]
            return True
        return False

    async def list_searches(
        self,
        filter_options: Optional[SearchListFilter] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[SavedSearch], int]:
        """
        List saved searches with optional filtering.

        Args:
            filter_options: Filter criteria
            offset: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (list of searches, total count)
        """
        searches = list(self._searches.values())

        if filter_options:
            searches = self._apply_filters(searches, filter_options)

        # Sort by updated_at descending
        searches.sort(key=lambda s: s.updated_at, reverse=True)

        total = len(searches)
        paginated = searches[offset:offset + limit]

        return paginated, total

    def _apply_filters(
        self,
        searches: List[SavedSearch],
        filters: SearchListFilter
    ) -> List[SavedSearch]:
        """Apply filter criteria to search list."""
        result = searches

        if filters.scope:
            result = [s for s in result if s.config.scope == filters.scope]

        if filters.project_id:
            if filters.include_global:
                result = [
                    s for s in result
                    if s.config.project_id == filters.project_id
                    or s.config.scope == SearchScope.GLOBAL
                ]
            else:
                result = [s for s in result if s.config.project_id == filters.project_id]

        if filters.user_id:
            result = [s for s in result if s.config.user_id == filters.user_id]

        if filters.category:
            result = [s for s in result if s.config.category == filters.category]

        if filters.tags:
            result = [
                s for s in result
                if any(tag in s.config.tags for tag in filters.tags)
            ]

        if filters.is_favorite is not None:
            result = [s for s in result if s.config.is_favorite == filters.is_favorite]

        if filters.name_contains:
            search_term = filters.name_contains.lower()
            result = [
                s for s in result
                if search_term in s.config.name.lower()
                or search_term in s.config.description.lower()
            ]

        return result

    async def execute_search(
        self,
        search_id: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[SearchExecutionResult]:
        """
        Execute a saved search.

        Args:
            search_id: ID of the saved search
            overrides: Optional parameter overrides for this execution

        Returns:
            SearchExecutionResult or None if search not found
        """
        search = await self.get_search(search_id)
        if not search:
            return None

        if not self._search_service:
            raise RuntimeError("SearchService not configured")

        config = search.config
        overrides = overrides or {}

        # Build search query with overrides
        query = SearchQuery(
            query=overrides.get("query", config.query),
            project_id=overrides.get("project_id", config.project_id),
            entity_types=overrides.get("entity_types", config.entity_types),
            fields=overrides.get("fields", config.fields),
            limit=overrides.get("limit", config.limit),
            offset=overrides.get("offset", 0),
            fuzzy=overrides.get("fuzzy", config.fuzzy),
            highlight=overrides.get("highlight", config.highlight),
            advanced=config.is_advanced,
        )

        # Execute and time the search
        import time
        start_time = time.time()

        results, total = await self._search_service.search(query)

        execution_time_ms = (time.time() - start_time) * 1000

        # Update execution stats
        now = datetime.utcnow()
        search.last_executed_at = now
        search.execution_count += 1

        return SearchExecutionResult(
            search_id=search_id,
            search_name=config.name,
            results=results,
            total_count=total,
            execution_time_ms=execution_time_ms,
            executed_at=now,
            query_used=query.query,
        )

    async def duplicate_search(
        self,
        search_id: str,
        new_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a copy of an existing saved search.

        Args:
            search_id: ID of search to duplicate
            new_name: Name for the new search

        Returns:
            ID of the new search or None if original not found
        """
        original = await self.get_search(search_id)
        if not original:
            return None

        config = original.config
        new_config = SavedSearchConfig(
            name=new_name or f"{config.name} (Copy)",
            description=config.description,
            query=config.query,
            scope=config.scope,
            project_id=config.project_id,
            user_id=config.user_id,
            is_advanced=config.is_advanced,
            entity_types=config.entity_types.copy() if config.entity_types else None,
            fields=config.fields.copy() if config.fields else None,
            limit=config.limit,
            fuzzy=config.fuzzy,
            highlight=config.highlight,
            tags=config.tags.copy(),
            category=config.category,
            is_favorite=False,  # Reset favorite status
            icon=config.icon,
            color=config.color,
        )

        return await self.create_search(new_config, original.created_by)

    async def toggle_favorite(self, search_id: str) -> Optional[bool]:
        """
        Toggle the favorite status of a search.

        Args:
            search_id: Search ID

        Returns:
            New favorite status or None if not found
        """
        search = await self.get_search(search_id)
        if not search:
            return None

        search.config.is_favorite = not search.config.is_favorite
        search.updated_at = datetime.utcnow()
        return search.config.is_favorite

    async def get_favorites(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[SavedSearch]:
        """
        Get favorite saved searches.

        Args:
            project_id: Optional project filter
            user_id: Optional user filter
            limit: Maximum results

        Returns:
            List of favorite searches
        """
        filters = SearchListFilter(
            project_id=project_id,
            user_id=user_id,
            is_favorite=True,
            include_global=True,
        )

        searches, _ = await self.list_searches(filters, limit=limit)
        return searches

    async def get_recent(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[SavedSearch]:
        """
        Get recently executed searches.

        Args:
            project_id: Optional project filter
            user_id: Optional user filter
            limit: Maximum results

        Returns:
            List of recently executed searches
        """
        searches = list(self._searches.values())

        if project_id:
            searches = [
                s for s in searches
                if s.config.project_id == project_id
                or s.config.scope == SearchScope.GLOBAL
            ]

        if user_id:
            searches = [s for s in searches if s.config.user_id == user_id]

        # Filter to only executed searches and sort by last_executed_at
        executed = [s for s in searches if s.last_executed_at is not None]
        executed.sort(key=lambda s: s.last_executed_at, reverse=True)

        return executed[:limit]

    async def get_popular(
        self,
        project_id: Optional[str] = None,
        limit: int = 10
    ) -> List[SavedSearch]:
        """
        Get most frequently executed searches.

        Args:
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of popular searches sorted by execution count
        """
        searches = list(self._searches.values())

        if project_id:
            searches = [
                s for s in searches
                if s.config.project_id == project_id
                or s.config.scope == SearchScope.GLOBAL
            ]

        # Sort by execution count descending
        searches.sort(key=lambda s: s.execution_count, reverse=True)

        return searches[:limit]

    async def get_by_category(
        self,
        category: SearchCategory,
        project_id: Optional[str] = None
    ) -> List[SavedSearch]:
        """
        Get searches by category.

        Args:
            category: Category to filter by
            project_id: Optional project filter

        Returns:
            List of searches in the category
        """
        filters = SearchListFilter(
            category=category,
            project_id=project_id,
            include_global=True,
        )

        searches, _ = await self.list_searches(filters, limit=100)
        return searches

    async def get_by_tags(
        self,
        tags: List[str],
        project_id: Optional[str] = None
    ) -> List[SavedSearch]:
        """
        Get searches that have any of the specified tags.

        Args:
            tags: Tags to search for
            project_id: Optional project filter

        Returns:
            List of matching searches
        """
        filters = SearchListFilter(
            tags=tags,
            project_id=project_id,
            include_global=True,
        )

        searches, _ = await self.list_searches(filters, limit=100)
        return searches

    async def get_all_tags(
        self,
        project_id: Optional[str] = None
    ) -> List[Tuple[str, int]]:
        """
        Get all unique tags with usage counts.

        Args:
            project_id: Optional project filter

        Returns:
            List of (tag, count) tuples sorted by count
        """
        searches = list(self._searches.values())

        if project_id:
            searches = [
                s for s in searches
                if s.config.project_id == project_id
                or s.config.scope == SearchScope.GLOBAL
            ]

        tag_counts: Dict[str, int] = {}
        for search in searches:
            for tag in search.config.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags

    async def search_saved_searches(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 20
    ) -> List[SavedSearch]:
        """
        Search through saved search names and descriptions.

        Args:
            query: Search query
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of matching saved searches
        """
        filters = SearchListFilter(
            name_contains=query,
            project_id=project_id,
            include_global=True,
        )

        searches, _ = await self.list_searches(filters, limit=limit)
        return searches

    def clear_all(self) -> int:
        """
        Clear all saved searches (for testing).

        Returns:
            Number of searches cleared
        """
        count = len(self._searches)
        self._searches.clear()
        return count


# Module-level singleton instance
_saved_search_service: Optional[SavedSearchService] = None


def get_saved_search_service(
    search_service: Optional[SearchService] = None,
    neo4j_handler: Optional[Any] = None
) -> SavedSearchService:
    """
    Get or create the SavedSearchService singleton instance.

    Args:
        search_service: SearchService instance (required for first call)
        neo4j_handler: Optional Neo4j handler for persistence

    Returns:
        SavedSearchService instance
    """
    global _saved_search_service

    if _saved_search_service is None:
        _saved_search_service = SavedSearchService(search_service, neo4j_handler)
    elif search_service is not None and _saved_search_service.search_service is None:
        _saved_search_service.set_search_service(search_service)

    return _saved_search_service


def set_saved_search_service(service: Optional[SavedSearchService]) -> None:
    """
    Set the global SavedSearchService instance.

    Args:
        service: SavedSearchService instance or None to clear
    """
    global _saved_search_service
    _saved_search_service = service


def reset_saved_search_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _saved_search_service
    _saved_search_service = None
