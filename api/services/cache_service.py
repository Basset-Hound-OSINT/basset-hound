"""
Cache Service for Basset Hound

This module provides a caching layer with Redis as the primary backend
and an in-memory fallback when Redis is unavailable.

Features:
- TTL-based expiration
- Entity caching
- Relationship caching
- Query result caching
- Smart cache invalidation
- Automatic Redis/memory fallback

Phase 4: Performance & Scalability - Caching Layer
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheBackend(str, Enum):
    """Available cache backends."""
    REDIS = "redis"
    MEMORY = "memory"


@dataclass
class CacheEntry(Generic[T]):
    """
    Represents a cached entry with metadata.

    Attributes:
        value: The cached value
        created_at: Timestamp when the entry was created
        expires_at: Timestamp when the entry expires (None = never)
        tags: Set of tags for invalidation grouping
        access_count: Number of times the entry was accessed
        last_accessed: Last access timestamp
    """
    value: T
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> Optional[float]:
        """Get remaining TTL in seconds."""
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0, remaining)

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class CacheStats:
    """
    Cache statistics tracker.

    Tracks hits, misses, and other cache metrics.
    """

    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.sets: int = 0
        self.deletes: int = 0
        self.invalidations: int = 0
        self.expirations: int = 0
        self._start_time: float = time.time()
        self._lock = Lock()

    @property
    def total_requests(self) -> int:
        """Total cache requests (hits + misses)."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        total = self.total_requests
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    @property
    def uptime_seconds(self) -> float:
        """Time since stats tracking started."""
        return time.time() - self._start_time

    def record_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.misses += 1

    def record_set(self) -> None:
        """Record a cache set operation."""
        with self._lock:
            self.sets += 1

    def record_delete(self) -> None:
        """Record a cache delete operation."""
        with self._lock:
            self.deletes += 1

    def record_invalidation(self) -> None:
        """Record a cache invalidation."""
        with self._lock:
            self.invalidations += 1

    def record_expiration(self) -> None:
        """Record an entry expiration."""
        with self._lock:
            self.expirations += 1

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.sets = 0
            self.deletes = 0
            self.invalidations = 0
            self.expirations = 0
            self._start_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate_percent": round(self.hit_rate, 2),
            "sets": self.sets,
            "deletes": self.deletes,
            "invalidations": self.invalidations,
            "expirations": self.expirations,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


class BaseCacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in the cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries from the cache."""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        pass

    @abstractmethod
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the cache backend is healthy."""
        pass


class MemoryCache(BaseCacheBackend):
    """
    In-memory cache implementation using OrderedDict for LRU behavior.

    Features:
    - LRU eviction when max_size is reached
    - TTL support
    - Tag-based invalidation
    - Thread-safe operations
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = 300,
        cleanup_interval: int = 60
    ):
        """
        Initialize the memory cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (None = no expiration)
            cleanup_interval: Interval for cleanup task in seconds
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._tags: Dict[str, Set[str]] = {}  # tag -> set of keys
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._lock = Lock()
        self._stats = CacheStats()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Background loop to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> int:
        """Remove expired entries from the cache."""
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired:
                    expired_keys.append(key)

        count = 0
        for key in expired_keys:
            if await self.delete(key):
                self._stats.record_expiration()
                count += 1

        if count > 0:
            logger.debug(f"Cleaned up {count} expired cache entries")

        return count

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        oldest_key = next(iter(self._cache))
        entry = self._cache.pop(oldest_key)

        # Remove from tags
        for tag in entry.tags:
            if tag in self._tags:
                self._tags[tag].discard(oldest_key)
                if not self._tags[tag]:
                    del self._tags[tag]

        logger.debug(f"Evicted LRU cache entry: {oldest_key}")

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            if key not in self._cache:
                self._stats.record_miss()
                return None

            entry = self._cache[key]

            if entry.is_expired:
                self._stats.record_miss()
                # Schedule deletion
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats.record_hit()

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in the cache."""
        with self._lock:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self._default_ttl

            expires_at = None
            if ttl is not None and ttl > 0:
                expires_at = time.time() + ttl

            # Evict if at max size and key is new
            if key not in self._cache and len(self._cache) >= self._max_size:
                self._evict_lru()

            # Remove old entry from tags if it exists
            if key in self._cache:
                old_entry = self._cache[key]
                for tag in old_entry.tags:
                    if tag in self._tags:
                        self._tags[tag].discard(key)

            # Create new entry
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                tags=tags or set()
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Add to tags index
            for tag in entry.tags:
                if tag not in self._tags:
                    self._tags[tag] = set()
                self._tags[tag].add(key)

            self._stats.record_set()
            return True

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache.pop(key)

            # Remove from tags
            for tag in entry.tags:
                if tag in self._tags:
                    self._tags[tag].discard(key)
                    if not self._tags[tag]:
                        del self._tags[tag]

            self._stats.record_delete()
            return True

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired:
                return False

            return True

    async def clear(self) -> int:
        """Clear all entries from the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._tags.clear()
            return count

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        import fnmatch

        with self._lock:
            if pattern == "*":
                return list(self._cache.keys())

            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        with self._lock:
            if tag not in self._tags:
                return 0

            keys_to_delete = list(self._tags[tag])

        count = 0
        for key in keys_to_delete:
            if await self.delete(key):
                count += 1

        self._stats.record_invalidation()
        logger.debug(f"Invalidated {count} entries with tag: {tag}")
        return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                **self._stats.to_dict(),
                "backend": "memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "tag_count": len(self._tags),
            }

    async def health_check(self) -> bool:
        """Check if the cache backend is healthy."""
        return True


class RedisCache(BaseCacheBackend):
    """
    Redis-based cache implementation.

    Features:
    - Distributed caching
    - Automatic serialization/deserialization
    - TTL support via Redis EXPIRE
    - Tag-based invalidation using Redis Sets
    - Connection pooling
    - Automatic reconnection
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "basset:",
        default_ttl: Optional[int] = 300,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        """
        Initialize the Redis cache.

        Args:
            url: Redis connection URL
            prefix: Key prefix for all cache entries
            default_ttl: Default TTL in seconds
            max_connections: Maximum connections in the pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
        """
        self._url = url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._client = None
        self._stats = CacheStats()
        self._connected = False

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    def _make_tag_key(self, tag: str) -> str:
        """Create a key for tag set."""
        return f"{self._prefix}__tags__:{tag}"

    async def connect(self) -> bool:
        """
        Connect to Redis.

        Returns:
            True if connected successfully, False otherwise.
        """
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                decode_responses=True,
            )

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self._url}")
            return True

        except ImportError:
            logger.warning("redis-py not installed. Install with: pip install redis")
            return False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False

    def _serialize(self, value: Any) -> str:
        """Serialize a value for Redis storage."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: Optional[str]) -> Any:
        """Deserialize a value from Redis storage."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if not self._client or not self._connected:
            self._stats.record_miss()
            return None

        try:
            value = await self._client.get(self._make_key(key))

            if value is None:
                self._stats.record_miss()
                return None

            self._stats.record_hit()
            return self._deserialize(value)

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._stats.record_miss()
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a value in the cache."""
        if not self._client or not self._connected:
            return False

        try:
            redis_key = self._make_key(key)
            serialized = self._serialize(value)

            # Use default TTL if not specified
            if ttl is None:
                ttl = self._default_ttl

            # Set value with TTL
            if ttl and ttl > 0:
                await self._client.setex(redis_key, ttl, serialized)
            else:
                await self._client.set(redis_key, serialized)

            # Add to tag sets
            if tags:
                for tag in tags:
                    tag_key = self._make_tag_key(tag)
                    await self._client.sadd(tag_key, redis_key)
                    # Set TTL on tag set slightly longer than entry TTL
                    if ttl and ttl > 0:
                        await self._client.expire(tag_key, ttl + 60)

            self._stats.record_set()
            return True

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        if not self._client or not self._connected:
            return False

        try:
            result = await self._client.delete(self._make_key(key))

            if result > 0:
                self._stats.record_delete()
                return True
            return False

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        if not self._client or not self._connected:
            return False

        try:
            return await self._client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def clear(self) -> int:
        """Clear all entries from the cache."""
        if not self._client or not self._connected:
            return 0

        try:
            # Get all keys with our prefix
            pattern = f"{self._prefix}*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    count += await self._client.delete(*keys)
                if cursor == 0:
                    break

            return count

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        if not self._client or not self._connected:
            return []

        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            all_keys = []

            while True:
                cursor, keys = await self._client.scan(cursor, match=full_pattern, count=100)
                # Remove prefix from keys
                prefix_len = len(self._prefix)
                all_keys.extend(k[prefix_len:] for k in keys)
                if cursor == 0:
                    break

            return all_keys

        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        if not self._client or not self._connected:
            return 0

        try:
            tag_key = self._make_tag_key(tag)

            # Get all keys with this tag
            keys = await self._client.smembers(tag_key)

            if not keys:
                return 0

            # Delete all tagged keys
            count = await self._client.delete(*keys)

            # Delete the tag set itself
            await self._client.delete(tag_key)

            self._stats.record_invalidation()
            logger.debug(f"Invalidated {count} entries with tag: {tag}")
            return count

        except Exception as e:
            logger.error(f"Redis invalidate_by_tag error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            **self._stats.to_dict(),
            "backend": "redis",
            "connected": self._connected,
        }

        if self._client and self._connected:
            try:
                info = await self._client.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")

                # Count keys with our prefix
                stats["key_count"] = len(await self.keys("*"))

            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")

        return stats

    async def health_check(self) -> bool:
        """Check if the cache backend is healthy."""
        if not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False


class CacheService:
    """
    High-level cache service with multi-level caching support.

    Provides a unified interface for caching with:
    - L1 Cache: In-memory, 1s TTL (hot data)
    - L2 Cache: Redis, 30s TTL (larger datasets)
    - L3 Cache: Database indexes (query optimization)
    - Automatic fallback when Redis unavailable
    - Entity-specific caching methods
    - Query result caching
    - Smart invalidation strategies with cascade support
    """

    # Key prefixes for different cache types
    PREFIX_ENTITY = "entity:"
    PREFIX_RELATIONSHIP = "rel:"
    PREFIX_QUERY = "query:"
    PREFIX_PROJECT = "project:"
    PREFIX_LIST = "list:"
    PREFIX_STATIC = "static:"  # For CDN-cached assets
    PREFIX_REPORT = "report:"  # For PDF reports

    # Cache level TTL values (Stream 2: Multi-Level Caching)
    L1_TTL = 1  # In-memory: 1 second
    L2_TTL = 30  # Redis: 30 seconds
    L3_TTL = 300  # Database indexes: 5 minutes

    def __init__(
        self,
        redis_url: Optional[str] = None,
        cache_enabled: bool = True,
        default_ttl: int = 300,
        entity_ttl: int = 600,
        query_ttl: int = 60,
        relationship_ttl: int = 300,
        max_memory_entries: int = 1000,
        prefer_redis: bool = True,
        enable_multi_level: bool = True,
        cache_warm_entities: Optional[List[str]] = None,
    ):
        """
        Initialize the cache service.

        Args:
            redis_url: Redis connection URL (None to use memory only)
            cache_enabled: Whether caching is enabled
            default_ttl: Default TTL in seconds
            entity_ttl: TTL for entity cache entries
            query_ttl: TTL for query result cache entries
            relationship_ttl: TTL for relationship cache entries
            max_memory_entries: Maximum entries for memory cache
            prefer_redis: Whether to prefer Redis over memory cache
            enable_multi_level: Enable multi-level caching (L1/L2/L3)
            cache_warm_entities: Entity keys to warm on startup
        """
        self._redis_url = redis_url
        self._cache_enabled = cache_enabled
        self._default_ttl = default_ttl
        self._entity_ttl = entity_ttl
        self._query_ttl = query_ttl
        self._relationship_ttl = relationship_ttl
        self._max_memory_entries = max_memory_entries
        self._prefer_redis = prefer_redis
        self._enable_multi_level = enable_multi_level
        self._cache_warm_entities = cache_warm_entities or []

        self._backend: Optional[BaseCacheBackend] = None
        self._l1_cache: Optional[MemoryCache] = None  # L1 in-memory cache
        self._l2_cache: Optional[RedisCache] = None  # L2 Redis cache
        self._backend_type: CacheBackend = CacheBackend.MEMORY
        self._initialized = False
        self._cascade_invalidation_enabled = True
        self._invalidation_queue: List[Dict[str, Any]] = []

    async def initialize(self) -> CacheBackend:
        """
        Initialize the cache backend with multi-level support.

        Setup hierarchy:
        - L1 Cache: In-memory, 1s TTL (hot data)
        - L2 Cache: Redis, 30s TTL (larger datasets)
        - Falls back to single-level if L2 unavailable

        Returns:
            The type of backend that was initialized.
        """
        if self._initialized:
            return self._backend_type

        if not self._cache_enabled:
            logger.info("Caching is disabled")
            self._initialized = True
            return self._backend_type

        # Initialize L1 cache (always in-memory)
        l1_cache = MemoryCache(
            max_size=max(self._max_memory_entries // 2, 500),  # 50% for L1
            default_ttl=self.L1_TTL,  # 1 second for hot data
        )
        await l1_cache.start_cleanup_task()
        self._l1_cache = l1_cache
        logger.info("L1 cache initialized (in-memory, 1s TTL)")

        # Try Redis for L2 cache if URL is provided and Redis is preferred
        if self._redis_url and self._prefer_redis and self._enable_multi_level:
            redis_cache = RedisCache(
                url=self._redis_url,
                default_ttl=self.L2_TTL,  # 30 seconds for Redis
            )

            if await redis_cache.connect():
                self._l2_cache = redis_cache
                self._backend = redis_cache
                self._backend_type = CacheBackend.REDIS
                self._initialized = True
                logger.info("Multi-level caching initialized (L1=memory 1s, L2=Redis 30s)")

                # Warm cache on startup
                await self._warm_cache()
                return self._backend_type
            else:
                logger.warning("Redis unavailable for L2, using single-level memory cache")
                self._backend = l1_cache
                self._backend_type = CacheBackend.MEMORY
                self._initialized = True
                logger.info("Using in-memory cache backend (Redis unavailable)")
                return self._backend_type

        # Fall back to single-level memory cache
        self._backend = l1_cache
        self._backend_type = CacheBackend.MEMORY
        self._initialized = True
        logger.info("Using in-memory cache backend")
        return self._backend_type

    async def _warm_cache(self) -> None:
        """
        Warm the cache on startup with hot data.

        Preloads frequently accessed entities and queries.
        """
        if not self._cache_warm_entities:
            return

        logger.info(f"Warming cache with {len(self._cache_warm_entities)} entries")
        # This would typically populate with hot data from database
        # Implemented by external callers after initialization

    async def _get_from_l1(self, key: str) -> Optional[Any]:
        """Get value from L1 cache (in-memory)."""
        if not self._l1_cache:
            return None
        return await self._l1_cache.get(key)

    async def _set_l1(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in L1 cache with TTL."""
        if not self._l1_cache:
            return False
        # Force L1 TTL to 1 second for hot data
        return await self._l1_cache.set(key, value, ttl=self.L1_TTL, tags=tags)

    async def _get_from_l2(self, key: str) -> Optional[Any]:
        """Get value from L2 cache (Redis)."""
        if not self._l2_cache:
            return None
        return await self._l2_cache.get(key)

    async def _set_l2(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in L2 cache with TTL."""
        if not self._l2_cache:
            return False
        # Use provided TTL or L2 default (30 seconds)
        effective_ttl = ttl or self.L2_TTL
        return await self._l2_cache.set(key, value, ttl=effective_ttl, tags=tags)

    async def _cascade_invalidate(
        self,
        key: str,
        tags: Optional[Set[str]] = None
    ) -> int:
        """
        Cascade invalidation across all cache levels.

        Invalidates the key across L1 and L2 caches.
        """
        if not self._cascade_invalidation_enabled:
            return 0

        count = 0

        # Invalidate from L1
        if self._l1_cache and await self._l1_cache.delete(key):
            count += 1

        # Invalidate from L2
        if self._l2_cache and await self._l2_cache.delete(key):
            count += 1

        # Invalidate by tags if provided
        if tags:
            for tag in tags:
                if self._l1_cache:
                    count += await self._l1_cache.invalidate_by_tag(tag)
                if self._l2_cache:
                    count += await self._l2_cache.invalidate_by_tag(tag)

        if count > 0:
            logger.debug(f"Cascade invalidated {count} entries for key: {key}")

        return count

    async def shutdown(self) -> None:
        """Shutdown the cache service."""
        if self._l1_cache:
            await self._l1_cache.stop_cleanup_task()

        if self._l2_cache:
            if isinstance(self._l2_cache, RedisCache):
                await self._l2_cache.disconnect()

        if self._backend:
            if isinstance(self._backend, RedisCache):
                await self._backend.disconnect()
            elif isinstance(self._backend, MemoryCache):
                await self._backend.stop_cleanup_task()

        self._initialized = False

    @property
    def is_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._cache_enabled and self._backend is not None

    @property
    def backend_type(self) -> CacheBackend:
        """Get the current backend type."""
        return self._backend_type

    # ==================== Entity Caching ====================

    def _entity_key(self, project_id: str, entity_id: str) -> str:
        """Generate cache key for an entity."""
        return f"{self.PREFIX_ENTITY}{project_id}:{entity_id}"

    async def get_entity(
        self,
        project_id: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached entity with multi-level lookup.

        Checks L1 (memory) first, then L2 (Redis), returns from backend.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier

        Returns:
            Cached entity data or None if not cached.
        """
        if not self.is_enabled:
            return None

        key = self._entity_key(project_id, entity_id)

        # Try L1 cache first (hottest data)
        if self._enable_multi_level:
            l1_result = await self._get_from_l1(key)
            if l1_result is not None:
                return l1_result

            # Try L2 cache
            l2_result = await self._get_from_l2(key)
            if l2_result is not None:
                # Populate L1 for next access
                await self._set_l1(key, l2_result)
                return l2_result

        # Fall back to main backend
        return await self._backend.get(key)

    async def set_entity(
        self,
        project_id: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache an entity across multiple levels.

        Stores in L1 (1s) and L2 (30s) for multi-level efficiency.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier
            entity_data: Entity data to cache
            ttl: Optional TTL override

        Returns:
            True if cached successfully.
        """
        if not self.is_enabled:
            return False

        key = self._entity_key(project_id, entity_id)
        ttl = ttl or self._entity_ttl

        # Tags for invalidation
        tags = {
            f"project:{project_id}",
            f"entity:{entity_id}",
            "entities",
        }

        # Multi-level caching
        if self._enable_multi_level:
            # L1: Fast access (1 second)
            await self._set_l1(key, entity_data, tags=tags)
            # L2: Longer retention (30 seconds)
            await self._set_l2(key, entity_data, ttl=self.L2_TTL, tags=tags)

        # Also set in main backend for consistency
        return await self._backend.set(key, entity_data, ttl=ttl, tags=tags)

    async def invalidate_entity(
        self,
        project_id: str,
        entity_id: str
    ) -> bool:
        """
        Invalidate a cached entity with cascade invalidation.

        Removes from L1, L2, and invalidates related queries/lists.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier

        Returns:
            True if entry was deleted.
        """
        if not self.is_enabled:
            return False

        key = self._entity_key(project_id, entity_id)

        # Tags to invalidate (cascade invalidation)
        tags = {
            f"entity:{entity_id}",
            f"project:{project_id}",
        }

        # Cascade invalidate across L1 and L2
        await self._cascade_invalidate(key, tags)

        # Also invalidate from main backend
        deleted = await self._backend.delete(key)

        # Invalidate related queries and lists
        await self._backend.invalidate_by_tag(f"entity:{entity_id}")

        return deleted

    # ==================== Relationship Caching ====================

    def _relationship_key(
        self,
        project_id: str,
        entity_id: str,
        direction: str = "all"
    ) -> str:
        """Generate cache key for entity relationships."""
        return f"{self.PREFIX_RELATIONSHIP}{project_id}:{entity_id}:{direction}"

    async def get_relationships(
        self,
        project_id: str,
        entity_id: str,
        direction: str = "all"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached relationships for an entity with multi-level lookup.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier
            direction: Relationship direction (all, incoming, outgoing)

        Returns:
            Cached relationships or None if not cached.
        """
        if not self.is_enabled:
            return None

        key = self._relationship_key(project_id, entity_id, direction)

        # Try L1 cache first
        if self._enable_multi_level:
            l1_result = await self._get_from_l1(key)
            if l1_result is not None:
                return l1_result

            # Try L2 cache
            l2_result = await self._get_from_l2(key)
            if l2_result is not None:
                # Populate L1
                await self._set_l1(key, l2_result)
                return l2_result

        # Fall back to main backend
        return await self._backend.get(key)

    async def set_relationships(
        self,
        project_id: str,
        entity_id: str,
        relationships: List[Dict[str, Any]],
        direction: str = "all",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache relationships for an entity across multiple levels.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier
            relationships: Relationship data to cache
            direction: Relationship direction
            ttl: Optional TTL override

        Returns:
            True if cached successfully.
        """
        if not self.is_enabled:
            return False

        key = self._relationship_key(project_id, entity_id, direction)
        ttl = ttl or self._relationship_ttl

        # Tags for invalidation (cascade invalidation for related entities)
        tags = {
            f"project:{project_id}",
            f"entity:{entity_id}",
            "relationships",
        }

        # Add tags for all related entities (for cascade invalidation)
        for rel in relationships:
            target_id = rel.get("target_id") or rel.get("source_id")
            if target_id:
                tags.add(f"entity:{target_id}")

        # Multi-level caching
        if self._enable_multi_level:
            # L1: Hot data (1 second)
            await self._set_l1(key, relationships, tags=tags)
            # L2: Longer retention (30 seconds)
            await self._set_l2(key, relationships, ttl=self.L2_TTL, tags=tags)

        # Also set in main backend
        return await self._backend.set(key, relationships, ttl=ttl, tags=tags)

    async def invalidate_relationships(
        self,
        project_id: str,
        entity_id: str
    ) -> int:
        """
        Invalidate cached relationships for an entity with cascade.

        Removes from L1, L2, and main backend.

        Args:
            project_id: Project identifier
            entity_id: Entity identifier

        Returns:
            Number of invalidated entries.
        """
        if not self.is_enabled:
            return 0

        count = 0
        tags = {f"entity:{entity_id}", f"project:{project_id}"}

        for direction in ["all", "incoming", "outgoing"]:
            key = self._relationship_key(project_id, entity_id, direction)
            # Cascade invalidate across L1 and L2
            await self._cascade_invalidate(key, tags)
            # Also delete from main backend
            if await self._backend.delete(key):
                count += 1

        return count

    # ==================== Query Result Caching ====================

    def _query_key(self, query_hash: str) -> str:
        """Generate cache key for a query result."""
        return f"{self.PREFIX_QUERY}{query_hash}"

    @staticmethod
    def hash_query(
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a hash for a query and its parameters.

        Args:
            query: The query string
            parameters: Query parameters

        Returns:
            Hash string for the query.
        """
        content = query
        if parameters:
            content += json.dumps(parameters, sort_keys=True, default=str)

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get_query_result(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get a cached query result.

        Args:
            query: The query string
            parameters: Query parameters

        Returns:
            Cached result or None if not cached.
        """
        if not self.is_enabled:
            return None

        query_hash = self.hash_query(query, parameters)
        key = self._query_key(query_hash)
        return await self._backend.get(key)

    async def set_query_result(
        self,
        query: str,
        result: Any,
        parameters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """
        Cache a query result.

        Args:
            query: The query string
            result: Result to cache
            parameters: Query parameters
            ttl: Optional TTL override
            tags: Optional tags for invalidation

        Returns:
            True if cached successfully.
        """
        if not self.is_enabled:
            return False

        query_hash = self.hash_query(query, parameters)
        key = self._query_key(query_hash)
        ttl = ttl or self._query_ttl

        # Default tags
        cache_tags = {"queries"}
        if tags:
            cache_tags.update(tags)

        return await self._backend.set(key, result, ttl=ttl, tags=cache_tags)

    async def invalidate_queries(self) -> int:
        """
        Invalidate all cached query results.

        Returns:
            Number of invalidated entries.
        """
        if not self.is_enabled:
            return 0

        return await self._backend.invalidate_by_tag("queries")

    # ==================== Project Caching ====================

    def _project_key(self, project_id: str) -> str:
        """Generate cache key for a project."""
        return f"{self.PREFIX_PROJECT}{project_id}"

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a cached project."""
        if not self.is_enabled:
            return None

        key = self._project_key(project_id)
        return await self._backend.get(key)

    async def set_project(
        self,
        project_id: str,
        project_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache a project."""
        if not self.is_enabled:
            return False

        key = self._project_key(project_id)
        ttl = ttl or self._entity_ttl

        tags = {f"project:{project_id}", "projects"}

        return await self._backend.set(key, project_data, ttl=ttl, tags=tags)

    async def invalidate_project(self, project_id: str) -> int:
        """
        Invalidate all cache entries for a project.

        This invalidates:
        - The project itself
        - All entities in the project
        - All relationships in the project
        - All queries tagged with the project

        Args:
            project_id: Project identifier

        Returns:
            Number of invalidated entries.
        """
        if not self.is_enabled:
            return 0

        # Invalidate by project tag (catches all related entries)
        count = await self._backend.invalidate_by_tag(f"project:{project_id}")

        # Also delete the project key explicitly
        key = self._project_key(project_id)
        if await self._backend.delete(key):
            count += 1

        return count

    # ==================== List Caching ====================

    def _list_key(self, list_type: str, project_id: str) -> str:
        """Generate cache key for a list."""
        return f"{self.PREFIX_LIST}{list_type}:{project_id}"

    async def get_entity_list(
        self,
        project_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get a cached entity list."""
        if not self.is_enabled:
            return None

        key = self._list_key("entities", project_id)
        return await self._backend.get(key)

    async def set_entity_list(
        self,
        project_id: str,
        entities: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache an entity list."""
        if not self.is_enabled:
            return False

        key = self._list_key("entities", project_id)
        ttl = ttl or self._entity_ttl

        tags = {f"project:{project_id}", "entities", "lists"}

        return await self._backend.set(key, entities, ttl=ttl, tags=tags)

    async def invalidate_entity_list(self, project_id: str) -> bool:
        """Invalidate a cached entity list."""
        if not self.is_enabled:
            return False

        key = self._list_key("entities", project_id)
        return await self._backend.delete(key)

    # ==================== Search Result Caching ====================

    def _search_key(self, search_query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for search results."""
        search_hash = self.hash_query(search_query, filters)
        return f"{self.PREFIX_QUERY}search:{search_hash}"

    async def get_search_results(
        self,
        search_query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        if not self.is_enabled:
            return None

        key = self._search_key(search_query, filters)
        return await self._backend.get(key)

    async def set_search_results(
        self,
        search_query: str,
        results: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache search results."""
        if not self.is_enabled:
            return False

        key = self._search_key(search_query, filters)
        ttl = ttl or self._query_ttl

        tags = {"searches", "queries"}

        return await self._backend.set(key, results, ttl=ttl, tags=tags)

    async def invalidate_search_results(self) -> int:
        """Invalidate all cached search results."""
        if not self.is_enabled:
            return 0

        return await self._backend.invalidate_by_tag("searches")

    # ==================== Graph Query Caching ====================

    def _graph_key(self, query_type: str, entity_id: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for graph queries."""
        params_hash = self.hash_query(query_type, params or {})
        return f"{self.PREFIX_QUERY}graph:{query_type}:{entity_id}:{params_hash}"

    async def get_graph_query(
        self,
        query_type: str,
        entity_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get cached graph query result."""
        if not self.is_enabled:
            return None

        key = self._graph_key(query_type, entity_id, params)
        return await self._backend.get(key)

    async def set_graph_query(
        self,
        query_type: str,
        entity_id: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache a graph query result."""
        if not self.is_enabled:
            return False

        key = self._graph_key(query_type, entity_id, params)
        ttl = ttl or (self._relationship_ttl if query_type == "neighbors" else 60)

        tags = {
            "graph_queries",
            f"entity:{entity_id}",
            query_type,
        }

        return await self._backend.set(key, result, ttl=ttl, tags=tags)

    async def invalidate_graph_queries_for_entity(self, entity_id: str) -> int:
        """Invalidate all graph queries for an entity."""
        if not self.is_enabled:
            return 0

        return await self._backend.invalidate_by_tag(f"entity:{entity_id}")

    async def invalidate_all_graph_queries(self) -> int:
        """Invalidate all cached graph queries."""
        if not self.is_enabled:
            return 0

        return await self._backend.invalidate_by_tag("graph_queries")

    # ==================== Static Asset & Report Caching (CDN) ====================

    async def cache_static_asset(
        self,
        asset_path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        ttl: int = 3600,  # 1 hour default
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> bool:
        """
        Cache a static asset for CDN distribution.

        Args:
            asset_path: Path to the asset (e.g., '/static/js/app.js')
            content: Asset content bytes
            content_type: MIME type
            ttl: TTL in seconds (default 1 hour)
            etag: ETag for cache validation
            last_modified: Last-Modified header value

        Returns:
            True if cached successfully.
        """
        if not self.is_enabled:
            return False

        key = f"{self.PREFIX_STATIC}{asset_path}"

        # Store asset metadata with content
        asset_data = {
            "content": content.hex(),  # Serialize bytes as hex
            "content_type": content_type,
            "etag": etag,
            "last_modified": last_modified,
            "size": len(content),
        }

        tags = {"static_assets", "cdn"}

        # L1 cache (hot assets)
        await self._set_l1(key, asset_data, tags=tags)

        # L2 cache with longer TTL
        await self._set_l2(key, asset_data, ttl=ttl, tags=tags)

        return await self._backend.set(key, asset_data, ttl=ttl, tags=tags)

    async def get_static_asset(self, asset_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached static asset.

        Args:
            asset_path: Path to the asset

        Returns:
            Asset data with metadata or None if not cached.
        """
        if not self.is_enabled:
            return None

        key = f"{self.PREFIX_STATIC}{asset_path}"

        # Multi-level lookup
        if self._enable_multi_level:
            l1_result = await self._get_from_l1(key)
            if l1_result is not None:
                return l1_result

            l2_result = await self._get_from_l2(key)
            if l2_result is not None:
                await self._set_l1(key, l2_result)
                return l2_result

        return await self._backend.get(key)

    async def cache_pdf_report(
        self,
        report_id: str,
        pdf_content: bytes,
        ttl: int = 3600,  # 1 hour (from spec: 60min)
    ) -> bool:
        """
        Cache a generated PDF report.

        Args:
            report_id: Unique report identifier
            pdf_content: PDF file bytes
            ttl: TTL in seconds (default 1 hour)

        Returns:
            True if cached successfully.
        """
        if not self.is_enabled:
            return False

        key = f"{self.PREFIX_REPORT}{report_id}"

        report_data = {
            "content": pdf_content.hex(),
            "size": len(pdf_content),
            "type": "application/pdf",
        }

        tags = {"pdf_reports", "reports"}

        # Cache in L2 and backend with longer TTL
        await self._set_l2(key, report_data, ttl=ttl, tags=tags)
        return await self._backend.set(key, report_data, ttl=ttl, tags=tags)

    async def get_pdf_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a cached PDF report."""
        if not self.is_enabled:
            return None

        key = f"{self.PREFIX_REPORT}{report_id}"

        # Check L2 first (longer TTL for reports)
        if self._enable_multi_level:
            l2_result = await self._get_from_l2(key)
            if l2_result is not None:
                return l2_result

        return await self._backend.get(key)

    # ==================== Utility Methods ====================

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._backend:
            return {
                "enabled": self._cache_enabled,
                "initialized": self._initialized,
                "backend": None,
            }

        return await self._backend.get_stats()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the cache.

        Returns:
            Health status dictionary.
        """
        result = {
            "enabled": self._cache_enabled,
            "initialized": self._initialized,
            "backend_type": self._backend_type.value,
        }

        if self._backend:
            result["healthy"] = await self._backend.health_check()
        else:
            result["healthy"] = False

        return result

    async def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        if not self.is_enabled:
            return 0

        return await self._backend.clear()


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service(
    redis_url: Optional[str] = None,
    cache_enabled: bool = True,
    **kwargs
) -> CacheService:
    """
    Get or create the cache service singleton.

    Args:
        redis_url: Redis connection URL
        cache_enabled: Whether caching is enabled
        **kwargs: Additional configuration options

    Returns:
        The cache service instance.
    """
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService(
            redis_url=redis_url,
            cache_enabled=cache_enabled,
            **kwargs
        )
    elif redis_url is not None:
        # Update configuration if provided
        _cache_service._redis_url = redis_url
        _cache_service._cache_enabled = cache_enabled

    return _cache_service


async def initialize_cache(
    redis_url: Optional[str] = None,
    cache_enabled: bool = True,
    **kwargs
) -> CacheService:
    """
    Initialize and return the cache service.

    This is a convenience function that gets the singleton and
    initializes it in one call.

    Args:
        redis_url: Redis connection URL
        cache_enabled: Whether caching is enabled
        **kwargs: Additional configuration options

    Returns:
        The initialized cache service.
    """
    service = get_cache_service(redis_url, cache_enabled, **kwargs)
    await service.initialize()
    return service
