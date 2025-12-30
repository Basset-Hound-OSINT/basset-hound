"""
Query Cache Service for Basset Hound OSINT Platform.

Provides intelligent caching for expensive graph analytics queries with:
- Decorator-based caching for service methods
- TTL configuration per query type
- Project-aware cache invalidation
- Cache statistics and monitoring

Phase 20: Query & Performance Optimization
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND MODELS
# =============================================================================


class QueryType(str, Enum):
    """Types of graph queries with different caching strategies."""

    # Long TTL - structural analysis (rarely changes)
    COMMUNITY_DETECTION = "community_detection"
    INFLUENCE_METRICS = "influence_metrics"
    GRAPH_STRUCTURE = "graph_structure"

    # Medium TTL - changes with entity/relationship updates
    SIMILARITY_ANALYSIS = "similarity_analysis"
    PATH_FINDING = "path_finding"
    COMMON_NEIGHBORS = "common_neighbors"

    # Short TTL - user-driven, volatile
    SEARCH_RESULTS = "search_results"
    ENTITY_NEIGHBORHOOD = "entity_neighborhood"

    # Very short TTL - real-time data
    ENTITY_DETAILS = "entity_details"
    RELATIONSHIP_LIST = "relationship_list"


class CacheConfig(BaseModel):
    """Configuration for query cache behavior."""

    enabled: bool = Field(default=True, description="Enable/disable caching")
    default_ttl: int = Field(default=300, description="Default TTL in seconds")

    # TTL by query type (seconds)
    community_detection_ttl: int = Field(default=3600, description="Community detection TTL")
    influence_metrics_ttl: int = Field(default=3600, description="Influence metrics TTL")
    graph_structure_ttl: int = Field(default=1800, description="Graph structure TTL")
    similarity_analysis_ttl: int = Field(default=1200, description="Similarity analysis TTL")
    path_finding_ttl: int = Field(default=900, description="Path finding TTL")
    common_neighbors_ttl: int = Field(default=600, description="Common neighbors TTL")
    search_results_ttl: int = Field(default=300, description="Search results TTL")
    entity_neighborhood_ttl: int = Field(default=300, description="Entity neighborhood TTL")
    entity_details_ttl: int = Field(default=120, description="Entity details TTL")
    relationship_list_ttl: int = Field(default=120, description="Relationship list TTL")

    model_config = {"extra": "allow"}


class CacheEntry(BaseModel):
    """A cached query result entry."""

    key: str
    value: Any
    query_type: QueryType
    project_id: Optional[str] = None
    entity_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    computation_time_ms: float = 0.0

    model_config = {"extra": "allow"}


class CacheStats(BaseModel):
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    invalidations: int = 0
    evictions: int = 0
    total_computation_time_saved_ms: float = 0.0
    avg_computation_time_ms: float = 0.0
    cache_size: int = 0
    enabled: bool = True

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    model_config = {"extra": "allow"}


# =============================================================================
# QUERY CACHE SERVICE
# =============================================================================


class QueryCacheService:
    """
    Intelligent query cache for graph analytics.

    Features:
    - In-memory LRU cache with configurable max size
    - TTL-based expiration per query type
    - Project-aware invalidation
    - Entity-aware invalidation
    - Performance statistics
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        max_entries: int = 500,
    ):
        """
        Initialize the query cache service.

        Args:
            config: Cache configuration settings
            max_entries: Maximum cache entries before LRU eviction
        """
        self.config = config or CacheConfig()
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats(enabled=self.config.enabled)
        self._lock = asyncio.Lock()

        # TTL mapping by query type
        self._ttl_map = {
            QueryType.COMMUNITY_DETECTION: self.config.community_detection_ttl,
            QueryType.INFLUENCE_METRICS: self.config.influence_metrics_ttl,
            QueryType.GRAPH_STRUCTURE: self.config.graph_structure_ttl,
            QueryType.SIMILARITY_ANALYSIS: self.config.similarity_analysis_ttl,
            QueryType.PATH_FINDING: self.config.path_finding_ttl,
            QueryType.COMMON_NEIGHBORS: self.config.common_neighbors_ttl,
            QueryType.SEARCH_RESULTS: self.config.search_results_ttl,
            QueryType.ENTITY_NEIGHBORHOOD: self.config.entity_neighborhood_ttl,
            QueryType.ENTITY_DETAILS: self.config.entity_details_ttl,
            QueryType.RELATIONSHIP_LIST: self.config.relationship_list_ttl,
        }

    def _generate_key(
        self,
        query_type: QueryType,
        project_id: Optional[str] = None,
        **params: Any,
    ) -> str:
        """Generate a unique cache key from query parameters."""
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_parts = [query_type.value]
        if project_id:
            key_parts.append(project_id)
        key_parts.append(sorted_params)

        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def _get_ttl(self, query_type: QueryType) -> int:
        """Get TTL for a specific query type."""
        return self._ttl_map.get(query_type, self.config.default_ttl)

    async def get(
        self,
        query_type: QueryType,
        project_id: Optional[str] = None,
        **params: Any,
    ) -> Optional[Any]:
        """
        Get a cached query result.

        Args:
            query_type: Type of query
            project_id: Project ID for scoping
            **params: Query parameters for key generation

        Returns:
            Cached value or None if not found/expired
        """
        if not self.config.enabled:
            return None

        key = self._generate_key(query_type, project_id, **params)

        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check expiration
            now = datetime.now(timezone.utc)
            if entry.expires_at < now:
                # Expired - remove and return None
                del self._cache[key]
                self._stats.misses += 1
                return None

            # Cache hit
            self._stats.hits += 1
            self._stats.total_computation_time_saved_ms += entry.computation_time_ms
            entry.access_count += 1
            entry.last_accessed = now

            logger.debug(
                f"Cache hit: {query_type.value} "
                f"(saved {entry.computation_time_ms:.2f}ms)"
            )
            return entry.value

    async def set(
        self,
        value: Any,
        query_type: QueryType,
        project_id: Optional[str] = None,
        entity_ids: Optional[List[str]] = None,
        computation_time_ms: float = 0.0,
        ttl_override: Optional[int] = None,
        **params: Any,
    ) -> str:
        """
        Cache a query result.

        Args:
            value: The result to cache
            query_type: Type of query
            project_id: Project ID for scoping
            entity_ids: Entity IDs involved (for invalidation)
            computation_time_ms: How long the query took
            ttl_override: Override default TTL
            **params: Query parameters for key generation

        Returns:
            The cache key
        """
        if not self.config.enabled:
            return ""

        key = self._generate_key(query_type, project_id, **params)
        ttl = ttl_override or self._get_ttl(query_type)
        now = datetime.now(timezone.utc)

        entry = CacheEntry(
            key=key,
            value=value,
            query_type=query_type,
            project_id=project_id,
            entity_ids=entity_ids or [],
            created_at=now,
            expires_at=datetime.fromtimestamp(
                now.timestamp() + ttl, tz=timezone.utc
            ),
            computation_time_ms=computation_time_ms,
        )

        async with self._lock:
            # Check if we need to evict (LRU)
            if len(self._cache) >= self.max_entries and key not in self._cache:
                await self._evict_lru()

            self._cache[key] = entry
            self._stats.sets += 1
            self._stats.cache_size = len(self._cache)

            # Update average computation time
            total_sets = self._stats.sets
            if total_sets > 0:
                self._stats.avg_computation_time_ms = (
                    (self._stats.avg_computation_time_ms * (total_sets - 1) + computation_time_ms)
                    / total_sets
                )

        logger.debug(
            f"Cached: {query_type.value} "
            f"(computation: {computation_time_ms:.2f}ms, ttl: {ttl}s)"
        )
        return key

    async def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._cache:
            return

        # Find entry with oldest access time
        oldest_key = None
        oldest_time = None

        for key, entry in self._cache.items():
            access_time = entry.last_accessed or entry.created_at
            if oldest_time is None or access_time < oldest_time:
                oldest_time = access_time
                oldest_key = key

        if oldest_key:
            del self._cache[oldest_key]
            self._stats.evictions += 1
            self._stats.cache_size = len(self._cache)

    async def invalidate_project(self, project_id: str) -> int:
        """
        Invalidate all cached entries for a project.

        Args:
            project_id: Project ID to invalidate

        Returns:
            Number of entries invalidated
        """
        if not self.config.enabled:
            return 0

        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.project_id == project_id
            ]

            for key in keys_to_remove:
                del self._cache[key]

            self._stats.invalidations += len(keys_to_remove)
            self._stats.cache_size = len(self._cache)

            logger.info(f"Invalidated {len(keys_to_remove)} entries for project {project_id}")
            return len(keys_to_remove)

    async def invalidate_entity(self, entity_id: str) -> int:
        """
        Invalidate all cached entries involving an entity.

        Args:
            entity_id: Entity ID to invalidate

        Returns:
            Number of entries invalidated
        """
        if not self.config.enabled:
            return 0

        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entity_id in entry.entity_ids
            ]

            for key in keys_to_remove:
                del self._cache[key]

            self._stats.invalidations += len(keys_to_remove)
            self._stats.cache_size = len(self._cache)

            logger.debug(f"Invalidated {len(keys_to_remove)} entries for entity {entity_id}")
            return len(keys_to_remove)

    async def invalidate_query_type(self, query_type: QueryType) -> int:
        """
        Invalidate all cached entries of a specific query type.

        Args:
            query_type: Query type to invalidate

        Returns:
            Number of entries invalidated
        """
        if not self.config.enabled:
            return 0

        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.query_type == query_type
            ]

            for key in keys_to_remove:
                del self._cache[key]

            self._stats.invalidations += len(keys_to_remove)
            self._stats.cache_size = len(self._cache)

            return len(keys_to_remove)

    async def clear(self) -> int:
        """Clear all cached entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.invalidations += count
            self._stats.cache_size = 0
            return count

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        async with self._lock:
            self._stats.cache_size = len(self._cache)
            return self._stats.model_copy()

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        if not self.config.enabled:
            return 0

        now = datetime.now(timezone.utc)
        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.expires_at < now
            ]

            for key in keys_to_remove:
                del self._cache[key]

            self._stats.cache_size = len(self._cache)
            return len(keys_to_remove)


# =============================================================================
# DECORATOR FOR CACHED QUERIES
# =============================================================================

T = TypeVar("T")


def cached_query(
    query_type: QueryType,
    project_id_param: str = "project_id",
    entity_id_params: Optional[List[str]] = None,
    ttl_override: Optional[int] = None,
):
    """
    Decorator for caching async query methods.

    Usage:
        @cached_query(QueryType.COMMUNITY_DETECTION, project_id_param="project_safe_name")
        async def detect_communities(self, project_safe_name: str, ...):
            ...

    Args:
        query_type: Type of query for TTL and invalidation
        project_id_param: Name of the parameter containing project ID
        entity_id_params: Names of parameters containing entity IDs
        ttl_override: Optional TTL override
    """
    entity_params = entity_id_params or []

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get cache service
            cache = get_query_cache_service()
            if cache is None or not cache.config.enabled:
                return await func(*args, **kwargs)

            # Extract project ID from args/kwargs
            # Handle both positional and keyword arguments
            project_id = kwargs.get(project_id_param)
            if project_id is None and len(args) > 1:
                # Try to get from positional args (args[0] is self)
                func_params = list(func.__code__.co_varnames)
                if project_id_param in func_params:
                    idx = func_params.index(project_id_param)
                    if idx < len(args):
                        project_id = args[idx]

            # Extract entity IDs
            entity_ids = []
            for param in entity_params:
                val = kwargs.get(param)
                if val:
                    if isinstance(val, list):
                        entity_ids.extend(val)
                    else:
                        entity_ids.append(val)

            # Generate cache key from all kwargs
            cache_params = {k: v for k, v in kwargs.items() if k != project_id_param}

            # Check cache
            cached = await cache.get(
                query_type=query_type,
                project_id=project_id,
                **cache_params,
            )
            if cached is not None:
                return cached

            # Execute query and measure time
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            computation_time_ms = (time.perf_counter() - start_time) * 1000

            # Cache result
            await cache.set(
                value=result,
                query_type=query_type,
                project_id=project_id,
                entity_ids=entity_ids,
                computation_time_ms=computation_time_ms,
                ttl_override=ttl_override,
                **cache_params,
            )

            return result

        return wrapper
    return decorator


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

_query_cache_service: Optional[QueryCacheService] = None


def get_query_cache_service() -> Optional[QueryCacheService]:
    """Get the singleton query cache service instance."""
    return _query_cache_service


def initialize_query_cache(
    config: Optional[CacheConfig] = None,
    max_entries: int = 500,
) -> QueryCacheService:
    """Initialize the query cache service singleton."""
    global _query_cache_service
    _query_cache_service = QueryCacheService(config=config, max_entries=max_entries)
    logger.info(
        f"Query cache initialized (enabled={_query_cache_service.config.enabled}, "
        f"max_entries={max_entries})"
    )
    return _query_cache_service


def reset_query_cache_service() -> None:
    """Reset the query cache service singleton (for testing)."""
    global _query_cache_service
    _query_cache_service = None
