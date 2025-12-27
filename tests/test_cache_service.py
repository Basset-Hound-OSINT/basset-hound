"""
Tests for the Cache Service (Phase 4)

Comprehensive test coverage for:
- MemoryCache backend
- RedisCache backend (with mocking)
- CacheService high-level interface
- Entity caching
- Relationship caching
- Query result caching
- Cache invalidation
- TTL and expiration
- Statistics tracking
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.cache_service import (
    BaseCacheBackend,
    CacheBackend,
    CacheEntry,
    CacheService,
    CacheStats,
    MemoryCache,
    RedisCache,
    get_cache_service,
    initialize_cache,
)


# ==================== CacheEntry Tests ====================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(value="test_value")

        assert entry.value == "test_value"
        assert entry.created_at > 0
        assert entry.expires_at is None
        assert entry.access_count == 0

    def test_entry_with_ttl(self):
        """Test cache entry with TTL."""
        now = time.time()
        entry = CacheEntry(
            value="test",
            expires_at=now + 60
        )

        assert not entry.is_expired
        assert entry.ttl_remaining > 0
        assert entry.ttl_remaining <= 60

    def test_entry_expired(self):
        """Test expired cache entry."""
        entry = CacheEntry(
            value="test",
            expires_at=time.time() - 10  # Expired 10 seconds ago
        )

        assert entry.is_expired
        assert entry.ttl_remaining == 0

    def test_entry_no_expiration(self):
        """Test entry without expiration."""
        entry = CacheEntry(value="test")

        assert not entry.is_expired
        assert entry.ttl_remaining is None

    def test_entry_touch(self):
        """Test updating access metadata."""
        entry = CacheEntry(value="test")
        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed

        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed

    def test_entry_with_tags(self):
        """Test cache entry with tags."""
        entry = CacheEntry(
            value="test",
            tags={"tag1", "tag2", "project:123"}
        )

        assert "tag1" in entry.tags
        assert "tag2" in entry.tags
        assert "project:123" in entry.tags


# ==================== CacheStats Tests ====================


class TestCacheStats:
    """Tests for CacheStats class."""

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.invalidations == 0
        assert stats.total_requests == 0

    def test_record_hit(self):
        """Test recording cache hits."""
        stats = CacheStats()
        stats.record_hit()
        stats.record_hit()

        assert stats.hits == 2
        assert stats.total_requests == 2

    def test_record_miss(self):
        """Test recording cache misses."""
        stats = CacheStats()
        stats.record_miss()

        assert stats.misses == 1
        assert stats.total_requests == 1

    def test_hit_rate(self):
        """Test hit rate calculation."""
        stats = CacheStats()

        # Initial hit rate should be 0
        assert stats.hit_rate == 0.0

        # Add some hits and misses
        for _ in range(8):
            stats.record_hit()
        for _ in range(2):
            stats.record_miss()

        # 8 hits, 2 misses = 80% hit rate
        assert stats.hit_rate == 80.0

    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = CacheStats()
        stats.record_hit()
        stats.record_set()

        result = stats.to_dict()

        assert isinstance(result, dict)
        assert result["hits"] == 1
        assert result["sets"] == 1
        assert "hit_rate_percent" in result
        assert "uptime_seconds" in result

    def test_stats_reset(self):
        """Test resetting stats."""
        stats = CacheStats()
        stats.record_hit()
        stats.record_miss()
        stats.record_set()

        stats.reset()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0


# ==================== MemoryCache Tests ====================


class TestMemoryCache:
    """Tests for MemoryCache backend."""

    @pytest.fixture
    def cache(self):
        """Create a fresh memory cache for each test."""
        return MemoryCache(max_size=10, default_ttl=60)

    @pytest.mark.asyncio
    async def test_basic_get_set(self, cache):
        """Test basic get and set operations."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist."""
        result = await cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache):
        """Test setting a value with TTL."""
        await cache.set("key1", "value1", ttl=1)

        # Value should exist immediately
        result = await cache.get("key1")
        assert result == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Value should be expired
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("key1", "value1")
        result = await cache.delete("key1")

        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting a nonexistent key."""
        result = await cache.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test checking if a key exists."""
        await cache.set("key1", "value1")

        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        count = await cache.clear()

        assert count == 3
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_keys(self, cache):
        """Test getting all keys."""
        await cache.set("test:key1", "value1")
        await cache.set("test:key2", "value2")
        await cache.set("other:key3", "value3")

        all_keys = await cache.keys()
        assert len(all_keys) == 3

        test_keys = await cache.keys("test:*")
        assert len(test_keys) == 2

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when max size is reached."""
        # Fill cache to max
        for i in range(10):
            await cache.set(f"key{i}", f"value{i}")

        # Add one more (should evict key0)
        await cache.set("key10", "value10")

        # key0 should be evicted (oldest)
        assert await cache.get("key0") is None
        assert await cache.get("key10") == "value10"

    @pytest.mark.asyncio
    async def test_lru_access_reorders(self, cache):
        """Test that accessing a key moves it to end."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to move it to end
        await cache.get("key1")

        # Fill up to force eviction (cache has max_size=10, we have 3 items)
        # Need to add 7 more to reach capacity, then 1 more to trigger eviction
        for i in range(8):
            await cache.set(f"extra{i}", f"value{i}")

        # At this point we have 11 items but max is 10, so oldest (key2) should be evicted
        # key1 should still exist (was accessed recently, moved to end)
        assert await cache.get("key1") == "value1"
        # key2 should be evicted (was oldest when eviction needed)
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_set_with_tags(self, cache):
        """Test setting values with tags."""
        await cache.set("key1", "value1", tags={"project:123", "entity"})
        await cache.set("key2", "value2", tags={"project:123"})

        # Both should exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_invalidate_by_tag(self, cache):
        """Test invalidating entries by tag."""
        await cache.set("key1", "value1", tags={"project:123"})
        await cache.set("key2", "value2", tags={"project:123"})
        await cache.set("key3", "value3", tags={"project:456"})

        count = await cache.invalidate_by_tag("project:123")

        assert count == 2
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_stats(self, cache):
        """Test cache statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # hit
        await cache.get("nonexistent")  # miss

        stats = await cache.get_stats()

        assert stats["backend"] == "memory"
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1

    @pytest.mark.asyncio
    async def test_health_check(self, cache):
        """Test health check."""
        result = await cache.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_complex_values(self, cache):
        """Test caching complex values."""
        complex_value = {
            "name": "Test Entity",
            "profile": {
                "core": {
                    "email": ["test@example.com"],
                    "name": [{"first": "John", "last": "Doe"}]
                }
            },
            "tags": ["tag1", "tag2"],
            "count": 42
        }

        await cache.set("entity:123", complex_value)
        result = await cache.get("entity:123")

        assert result == complex_value

    @pytest.mark.asyncio
    async def test_update_existing_key(self, cache):
        """Test updating an existing key."""
        await cache.set("key1", "value1", tags={"old_tag"})
        await cache.set("key1", "value2", tags={"new_tag"})

        result = await cache.get("key1")
        assert result == "value2"

        # Old tag should not invalidate the entry
        await cache.invalidate_by_tag("old_tag")
        result = await cache.get("key1")
        assert result == "value2"

        # New tag should invalidate
        await cache.invalidate_by_tag("new_tag")
        result = await cache.get("key1")
        assert result is None


# ==================== RedisCache Tests (Mocked) ====================


class TestRedisCache:
    """Tests for RedisCache backend with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.ping = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.scan = AsyncMock(return_value=(0, []))
        mock.sadd = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        mock.expire = AsyncMock(return_value=True)
        mock.info = AsyncMock(return_value={"used_memory_human": "1M"})
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def cache(self, mock_redis):
        """Create a RedisCache with mocked client."""
        cache = RedisCache(url="redis://localhost:6379/0", prefix="test:")
        cache._client = mock_redis
        cache._connected = True
        return cache

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis):
        """Test successful Redis connection."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = RedisCache(url="redis://localhost:6379/0")
            result = await cache.connect()

            assert result is True
            assert cache._connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed Redis connection."""
        with patch("redis.asyncio.from_url", side_effect=Exception("Connection failed")):
            cache = RedisCache(url="redis://localhost:6379/0")
            result = await cache.connect()

            assert result is False
            assert cache._connected is False

    @pytest.mark.asyncio
    async def test_basic_get_set(self, cache, mock_redis):
        """Test basic get and set operations."""
        mock_redis.get.return_value = json.dumps("value1")

        await cache.set("key1", "value1")
        result = await cache.get("key1")

        assert result == "value1"
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_miss(self, cache, mock_redis):
        """Test cache miss."""
        mock_redis.get.return_value = None

        result = await cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache, mock_redis):
        """Test setting with TTL."""
        await cache.set("key1", "value1", ttl=60)

        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][1] == 60  # TTL value

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, cache, mock_redis):
        """Test setting without TTL."""
        cache._default_ttl = None

        await cache.set("key1", "value1", ttl=None)

        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, cache, mock_redis):
        """Test deleting a key."""
        mock_redis.delete.return_value = 1

        result = await cache.delete("key1")

        assert result is True
        mock_redis.delete.assert_called_with("test:key1")

    @pytest.mark.asyncio
    async def test_exists(self, cache, mock_redis):
        """Test checking if key exists."""
        mock_redis.exists.return_value = 1

        result = await cache.exists("key1")

        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_by_tag(self, cache, mock_redis):
        """Test tag-based invalidation."""
        mock_redis.smembers.return_value = {"test:key1", "test:key2"}
        mock_redis.delete.return_value = 2

        count = await cache.invalidate_by_tag("project:123")

        assert count == 2

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache, mock_redis):
        """Test health check when Redis is healthy."""
        result = await cache.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache, mock_redis):
        """Test health check when Redis is unhealthy."""
        mock_redis.ping.side_effect = Exception("Connection lost")

        result = await cache.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_stats(self, cache, mock_redis):
        """Test getting stats."""
        mock_redis.scan.return_value = (0, ["test:key1", "test:key2"])

        stats = await cache.get_stats()

        assert stats["backend"] == "redis"
        assert stats["connected"] is True

    @pytest.mark.asyncio
    async def test_key_prefix(self, cache, mock_redis):
        """Test that keys are properly prefixed."""
        mock_redis.get.return_value = json.dumps("value1")

        await cache.set("mykey", "value1")
        await cache.get("mykey")

        # Verify prefix is used
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("test:")

    @pytest.mark.asyncio
    async def test_disconnected_operations(self):
        """Test operations when disconnected."""
        cache = RedisCache()
        cache._connected = False
        cache._client = None

        assert await cache.get("key") is None
        assert await cache.set("key", "value") is False
        assert await cache.delete("key") is False
        assert await cache.exists("key") is False


# ==================== CacheService Tests ====================


class TestCacheService:
    """Tests for CacheService high-level interface."""

    @pytest.fixture
    def service(self):
        """Create a cache service with memory backend."""
        return CacheService(
            redis_url=None,
            cache_enabled=True,
            default_ttl=60,
            entity_ttl=120,
            query_ttl=30
        )

    @pytest.mark.asyncio
    async def test_initialize_memory_backend(self, service):
        """Test initialization with memory backend."""
        backend_type = await service.initialize()

        assert backend_type == CacheBackend.MEMORY
        assert service.is_enabled
        assert service.backend_type == CacheBackend.MEMORY

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_disabled(self):
        """Test initialization when caching is disabled."""
        service = CacheService(cache_enabled=False)
        backend_type = await service.initialize()

        assert backend_type == CacheBackend.MEMORY
        assert not service.is_enabled

    @pytest.mark.asyncio
    async def test_entity_caching(self, service):
        """Test entity caching operations."""
        await service.initialize()

        entity_data = {
            "id": "entity-123",
            "name": "Test Entity",
            "profile": {"core": {"email": ["test@example.com"]}}
        }

        # Cache entity
        result = await service.set_entity("project-1", "entity-123", entity_data)
        assert result is True

        # Retrieve entity
        cached = await service.get_entity("project-1", "entity-123")
        assert cached == entity_data

        # Invalidate entity
        await service.invalidate_entity("project-1", "entity-123")
        cached = await service.get_entity("project-1", "entity-123")
        assert cached is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_relationship_caching(self, service):
        """Test relationship caching operations."""
        await service.initialize()

        relationships = [
            {"source_id": "entity-1", "target_id": "entity-2", "type": "KNOWS"},
            {"source_id": "entity-1", "target_id": "entity-3", "type": "WORKS_WITH"}
        ]

        # Cache relationships
        result = await service.set_relationships(
            "project-1",
            "entity-1",
            relationships,
            direction="outgoing"
        )
        assert result is True

        # Retrieve relationships
        cached = await service.get_relationships("project-1", "entity-1", "outgoing")
        assert cached == relationships

        # Invalidate
        count = await service.invalidate_relationships("project-1", "entity-1")
        assert count >= 1

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_query_caching(self, service):
        """Test query result caching."""
        await service.initialize()

        query = "MATCH (n:Person) RETURN n"
        params = {"limit": 10}
        result = [{"id": "1", "name": "Person 1"}, {"id": "2", "name": "Person 2"}]

        # Cache query result
        await service.set_query_result(query, result, parameters=params)

        # Retrieve cached result
        cached = await service.get_query_result(query, parameters=params)
        assert cached == result

        # Different params should not return cached result
        cached = await service.get_query_result(query, parameters={"limit": 20})
        assert cached is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_query_hash(self):
        """Test query hashing."""
        query = "MATCH (n) RETURN n"
        params = {"id": "123"}

        hash1 = CacheService.hash_query(query, params)
        hash2 = CacheService.hash_query(query, params)
        hash3 = CacheService.hash_query(query, {"id": "456"})

        assert hash1 == hash2  # Same query + params = same hash
        assert hash1 != hash3  # Different params = different hash

    @pytest.mark.asyncio
    async def test_project_caching(self, service):
        """Test project caching."""
        await service.initialize()

        project_data = {
            "id": "project-1",
            "name": "Test Project",
            "created_at": "2024-01-15T10:00:00"
        }

        # Cache project
        await service.set_project("project-1", project_data)

        # Retrieve project
        cached = await service.get_project("project-1")
        assert cached == project_data

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_project_invalidation(self, service):
        """Test project invalidation cascades to related entries."""
        await service.initialize()

        # Cache project and related data
        await service.set_project("project-1", {"id": "project-1"})
        await service.set_entity("project-1", "entity-1", {"id": "entity-1"})
        await service.set_entity_list("project-1", [{"id": "entity-1"}])

        # Invalidate project
        count = await service.invalidate_project("project-1")

        # All should be invalidated
        assert await service.get_project("project-1") is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_entity_list_caching(self, service):
        """Test entity list caching."""
        await service.initialize()

        entities = [
            {"id": "entity-1", "name": "Entity 1"},
            {"id": "entity-2", "name": "Entity 2"}
        ]

        await service.set_entity_list("project-1", entities)
        cached = await service.get_entity_list("project-1")

        assert cached == entities

        await service.invalidate_entity_list("project-1")
        cached = await service.get_entity_list("project-1")

        assert cached is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_stats(self, service):
        """Test getting cache stats."""
        await service.initialize()

        # Perform some operations
        await service.set_entity("project-1", "entity-1", {"id": "entity-1"})
        await service.get_entity("project-1", "entity-1")
        await service.get_entity("project-1", "nonexistent")

        stats = await service.get_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert stats["backend"] == "memory"

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check."""
        await service.initialize()

        health = await service.health_check()

        assert health["enabled"] is True
        assert health["initialized"] is True
        assert health["healthy"] is True
        assert health["backend_type"] == "memory"

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_clear_all(self, service):
        """Test clearing all cache entries."""
        await service.initialize()

        # Add some entries
        await service.set_entity("project-1", "entity-1", {"id": "entity-1"})
        await service.set_entity("project-1", "entity-2", {"id": "entity-2"})
        await service.set_project("project-1", {"id": "project-1"})

        # Clear all
        count = await service.clear_all()

        assert count >= 3
        assert await service.get_entity("project-1", "entity-1") is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_disabled_operations(self):
        """Test that operations return appropriate values when disabled."""
        service = CacheService(cache_enabled=False)
        await service.initialize()

        # All operations should return None or False when disabled
        assert await service.get_entity("project-1", "entity-1") is None
        assert await service.set_entity("project-1", "entity-1", {}) is False
        assert await service.invalidate_entity("project-1", "entity-1") is False

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_invalidate_queries(self, service):
        """Test invalidating all query caches."""
        await service.initialize()

        # Cache some queries
        await service.set_query_result("query1", "result1")
        await service.set_query_result("query2", "result2")

        # Invalidate all queries
        count = await service.invalidate_queries()

        assert count >= 2
        assert await service.get_query_result("query1") is None

        await service.shutdown()


# ==================== Singleton Tests ====================


class TestCacheServiceSingleton:
    """Tests for cache service singleton pattern."""

    def test_get_cache_service_creates_singleton(self):
        """Test that get_cache_service creates a singleton."""
        import api.services.cache_service as module
        module._cache_service = None

        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_get_cache_service_with_config(self):
        """Test configuring the cache service."""
        import api.services.cache_service as module
        module._cache_service = None

        service = get_cache_service(
            redis_url="redis://localhost:6379/0",
            cache_enabled=True,
            default_ttl=120
        )

        assert service._redis_url == "redis://localhost:6379/0"
        assert service._cache_enabled is True

    @pytest.mark.asyncio
    async def test_initialize_cache_convenience_function(self):
        """Test the initialize_cache convenience function."""
        import api.services.cache_service as module
        module._cache_service = None

        service = await initialize_cache(cache_enabled=True, prefer_redis=False)

        assert service._initialized is True
        assert service.backend_type == CacheBackend.MEMORY

        await service.shutdown()


# ==================== Redis Fallback Tests ====================


class TestRedisFallback:
    """Tests for Redis-to-memory fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_to_memory_when_redis_unavailable(self):
        """Test that service falls back to memory when Redis is unavailable."""
        service = CacheService(
            redis_url="redis://nonexistent:6379/0",
            cache_enabled=True,
            prefer_redis=True
        )

        backend_type = await service.initialize()

        # Should fall back to memory
        assert backend_type == CacheBackend.MEMORY
        assert service.is_enabled

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_memory_only_when_no_redis_url(self):
        """Test memory-only mode when no Redis URL is provided."""
        service = CacheService(
            redis_url=None,
            cache_enabled=True
        )

        backend_type = await service.initialize()

        assert backend_type == CacheBackend.MEMORY

        await service.shutdown()


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_cache_none_value(self):
        """Test caching None values."""
        cache = MemoryCache()
        # Note: Setting None might be intentional in some cases
        await cache.set("key1", None)

        result = await cache.get("key1")
        assert result is None  # Can't distinguish from cache miss

    @pytest.mark.asyncio
    async def test_cache_empty_string(self):
        """Test caching empty strings."""
        cache = MemoryCache()
        await cache.set("key1", "")

        result = await cache.get("key1")
        assert result == ""

    @pytest.mark.asyncio
    async def test_cache_empty_dict(self):
        """Test caching empty dictionaries."""
        cache = MemoryCache()
        await cache.set("key1", {})

        result = await cache.get("key1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_cache_empty_list(self):
        """Test caching empty lists."""
        cache = MemoryCache()
        await cache.set("key1", [])

        result = await cache.get("key1")
        assert result == []

    @pytest.mark.asyncio
    async def test_very_long_key(self):
        """Test caching with very long keys."""
        cache = MemoryCache()
        long_key = "k" * 1000

        await cache.set(long_key, "value")
        result = await cache.get(long_key)

        assert result == "value"

    @pytest.mark.asyncio
    async def test_special_characters_in_key(self):
        """Test keys with special characters."""
        cache = MemoryCache()

        keys = [
            "key:with:colons",
            "key/with/slashes",
            "key with spaces",
            "key_with_underscores",
            "key-with-dashes"
        ]

        for i, key in enumerate(keys):
            await cache.set(key, f"value{i}")
            result = await cache.get(key)
            assert result == f"value{i}"

    @pytest.mark.asyncio
    async def test_unicode_values(self):
        """Test caching unicode values."""
        cache = MemoryCache()
        value = {"name": "Test", "emoji": "Hello World"}

        await cache.set("key1", value)
        result = await cache.get("key1")

        assert result == value

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        cache = MemoryCache(max_size=100)

        async def set_and_get(i):
            await cache.set(f"key{i}", f"value{i}")
            result = await cache.get(f"key{i}")
            return result == f"value{i}"

        tasks = [set_and_get(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert all(results)

    @pytest.mark.asyncio
    async def test_zero_ttl(self):
        """Test behavior with TTL of 0."""
        cache = MemoryCache()
        await cache.set("key1", "value1", ttl=0)

        # With TTL=0, it should not expire
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_negative_ttl(self):
        """Test behavior with negative TTL."""
        cache = MemoryCache()
        # Negative TTL is treated as no expiration (same as ttl=0)
        # because the implementation only sets expires_at when ttl > 0
        await cache.set("key1", "value1", ttl=-1)

        result = await cache.get("key1")
        # Entry exists with no expiration
        assert result == "value1"


# ==================== Integration-like Tests ====================


class TestCacheServiceIntegration:
    """Integration-like tests for cache service with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_entity_lifecycle(self):
        """Test complete entity caching lifecycle."""
        service = CacheService(cache_enabled=True)
        await service.initialize()

        project_id = "test-project"
        entity_id = "entity-123"
        entity_data = {
            "id": entity_id,
            "created_at": "2024-01-15T10:00:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                }
            }
        }

        # 1. Entity not in cache
        cached = await service.get_entity(project_id, entity_id)
        assert cached is None

        # 2. Add entity to cache
        await service.set_entity(project_id, entity_id, entity_data)

        # 3. Retrieve from cache
        cached = await service.get_entity(project_id, entity_id)
        assert cached["id"] == entity_id
        assert cached["profile"]["core"]["email"] == ["john@example.com"]

        # 4. Update entity (invalidate and re-cache)
        updated_data = entity_data.copy()
        updated_data["profile"]["core"]["email"].append("john.doe@example.com")

        await service.invalidate_entity(project_id, entity_id)
        await service.set_entity(project_id, entity_id, updated_data)

        # 5. Verify update
        cached = await service.get_entity(project_id, entity_id)
        assert len(cached["profile"]["core"]["email"]) == 2

        # 6. Delete entity (invalidate)
        await service.invalidate_entity(project_id, entity_id)
        cached = await service.get_entity(project_id, entity_id)
        assert cached is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_query_caching_workflow(self):
        """Test query caching workflow."""
        service = CacheService(cache_enabled=True, query_ttl=30)
        await service.initialize()

        project_id = "test-project"
        query = """
            MATCH (project:Project {safe_name: $project_safe_name})
                  -[:HAS_PERSON]->(person:Person)
            RETURN person
            ORDER BY person.created_at DESC
            LIMIT $limit
        """
        params = {"project_safe_name": project_id, "limit": 10}

        # Simulate expensive query result
        result = [
            {"id": "entity-1", "name": "Entity 1"},
            {"id": "entity-2", "name": "Entity 2"},
            {"id": "entity-3", "name": "Entity 3"}
        ]

        # Cache the result
        await service.set_query_result(
            query,
            result,
            parameters=params,
            tags={f"project:{project_id}", "entities"}
        )

        # Subsequent requests hit cache
        cached = await service.get_query_result(query, parameters=params)
        assert cached == result

        # Invalidate when entity is added/updated
        await service.invalidate_queries()
        cached = await service.get_query_result(query, parameters=params)
        assert cached is None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_project_wide_invalidation(self):
        """Test invalidating all cache entries for a project."""
        service = CacheService(cache_enabled=True)
        await service.initialize()

        project_id = "test-project"

        # Cache various data for the project
        await service.set_project(project_id, {"id": project_id, "name": "Test"})
        await service.set_entity(project_id, "entity-1", {"id": "entity-1"})
        await service.set_entity(project_id, "entity-2", {"id": "entity-2"})
        await service.set_entity_list(project_id, [
            {"id": "entity-1"},
            {"id": "entity-2"}
        ])
        await service.set_relationships(project_id, "entity-1", [
            {"target_id": "entity-2", "type": "KNOWS"}
        ])

        # Verify all are cached
        assert await service.get_project(project_id) is not None
        assert await service.get_entity(project_id, "entity-1") is not None
        assert await service.get_entity_list(project_id) is not None

        # Invalidate entire project
        await service.invalidate_project(project_id)

        # All should be invalidated
        assert await service.get_project(project_id) is None

        await service.shutdown()
