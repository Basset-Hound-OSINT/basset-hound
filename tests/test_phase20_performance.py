"""
Phase 20: Query & Performance Optimization Tests

Tests for:
- Query cache service and decorator
- Batch orphan data operations
- Result streaming utilities
- Pagination helpers
- Neo4j index verification
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# QUERY CACHE SERVICE TESTS
# =============================================================================


class TestQueryCacheModels:
    """Test query cache Pydantic models."""

    def test_query_type_enum(self):
        """Test QueryType enum values."""
        from api.services.query_cache import QueryType

        assert QueryType.COMMUNITY_DETECTION == "community_detection"
        assert QueryType.INFLUENCE_METRICS == "influence_metrics"
        assert QueryType.SIMILARITY_ANALYSIS == "similarity_analysis"
        assert QueryType.SEARCH_RESULTS == "search_results"

    def test_cache_config_defaults(self):
        """Test CacheConfig default values."""
        from api.services.query_cache import CacheConfig

        config = CacheConfig()

        assert config.enabled is True
        assert config.default_ttl == 300
        assert config.community_detection_ttl == 3600
        assert config.search_results_ttl == 300

    def test_cache_config_custom(self):
        """Test CacheConfig with custom values."""
        from api.services.query_cache import CacheConfig

        config = CacheConfig(
            enabled=False,
            community_detection_ttl=7200,
            search_results_ttl=60,
        )

        assert config.enabled is False
        assert config.community_detection_ttl == 7200
        assert config.search_results_ttl == 60

    def test_cache_entry_model(self):
        """Test CacheEntry model."""
        from api.services.query_cache import CacheEntry, QueryType

        entry = CacheEntry(
            key="test-key",
            value={"result": "data"},
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="test-project",
            entity_ids=["e1", "e2"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            computation_time_ms=150.5,
        )

        assert entry.key == "test-key"
        assert entry.value == {"result": "data"}
        assert entry.query_type == QueryType.COMMUNITY_DETECTION
        assert entry.computation_time_ms == 150.5

    def test_cache_stats_model(self):
        """Test CacheStats model and hit rate calculation."""
        from api.services.query_cache import CacheStats

        stats = CacheStats(hits=80, misses=20, sets=100)

        assert stats.hit_rate == 80.0

    def test_cache_stats_zero_requests(self):
        """Test CacheStats hit rate with zero requests."""
        from api.services.query_cache import CacheStats

        stats = CacheStats()

        assert stats.hit_rate == 0.0


class TestQueryCacheService:
    """Test QueryCacheService operations."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service for testing."""
        from api.services.query_cache import CacheConfig, QueryCacheService

        config = CacheConfig(enabled=True)
        return QueryCacheService(config=config, max_entries=100)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_service):
        """Test basic set and get operations."""
        from api.services.query_cache import QueryType

        # Set a value
        key = await cache_service.set(
            value={"communities": [1, 2, 3]},
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="test-project",
            computation_time_ms=100.0,
        )

        assert key is not None

        # Get the value
        result = await cache_service.get(
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="test-project",
        )

        assert result == {"communities": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service):
        """Test cache miss returns None."""
        from api.services.query_cache import QueryType

        result = await cache_service.get(
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="nonexistent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_service):
        """Test that expired entries return None."""
        import asyncio
        from api.services.query_cache import QueryType

        # Set with very short TTL
        await cache_service.set(
            value={"data": "test"},
            query_type=QueryType.SEARCH_RESULTS,
            project_id="test",
            ttl_override=1,  # 1 second expiration
        )

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        result = await cache_service.get(
            query_type=QueryType.SEARCH_RESULTS,
            project_id="test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_project(self, cache_service):
        """Test project-wide invalidation."""
        from api.services.query_cache import QueryType

        # Add multiple entries for the same project
        await cache_service.set(
            value={"data": 1},
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="project1",
        )
        await cache_service.set(
            value={"data": 2},
            query_type=QueryType.INFLUENCE_METRICS,
            project_id="project1",
        )
        await cache_service.set(
            value={"data": 3},
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="project2",
        )

        # Invalidate project1
        count = await cache_service.invalidate_project("project1")

        assert count == 2

        # Verify project1 entries are gone
        assert await cache_service.get(QueryType.COMMUNITY_DETECTION, "project1") is None
        assert await cache_service.get(QueryType.INFLUENCE_METRICS, "project1") is None

        # Verify project2 entry still exists
        assert await cache_service.get(QueryType.COMMUNITY_DETECTION, "project2") is not None

    @pytest.mark.asyncio
    async def test_invalidate_entity(self, cache_service):
        """Test entity-specific invalidation."""
        from api.services.query_cache import QueryType

        # Add entry with entity IDs
        await cache_service.set(
            value={"data": 1},
            query_type=QueryType.SIMILARITY_ANALYSIS,
            project_id="project1",
            entity_ids=["e1", "e2"],
        )

        # Invalidate by entity
        count = await cache_service.invalidate_entity("e1")

        assert count == 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when max entries exceeded."""
        from api.services.query_cache import CacheConfig, QueryCacheService, QueryType

        # Create cache with small max size
        config = CacheConfig(enabled=True)
        cache = QueryCacheService(config=config, max_entries=3)

        # Add 4 entries (should evict oldest)
        await cache.set(value=1, query_type=QueryType.COMMUNITY_DETECTION, project_id="p1")
        await cache.set(value=2, query_type=QueryType.COMMUNITY_DETECTION, project_id="p2")
        await cache.set(value=3, query_type=QueryType.COMMUNITY_DETECTION, project_id="p3")
        await cache.set(value=4, query_type=QueryType.COMMUNITY_DETECTION, project_id="p4")

        stats = await cache.get_stats()
        assert stats.cache_size <= 3
        assert stats.evictions >= 1

    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache_service):
        """Test cache statistics tracking."""
        from api.services.query_cache import QueryType

        # Generate hits and misses
        await cache_service.set(
            value={"data": "test"},
            query_type=QueryType.COMMUNITY_DETECTION,
            project_id="stats-test",
            computation_time_ms=50.0,
        )

        # Hit
        await cache_service.get(QueryType.COMMUNITY_DETECTION, "stats-test")
        await cache_service.get(QueryType.COMMUNITY_DETECTION, "stats-test")

        # Miss
        await cache_service.get(QueryType.COMMUNITY_DETECTION, "nonexistent")

        stats = await cache_service.get_stats()

        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.sets == 1
        assert stats.hit_rate == pytest.approx(66.67, abs=0.1)

    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Test that disabled cache bypasses operations."""
        from api.services.query_cache import CacheConfig, QueryCacheService, QueryType

        config = CacheConfig(enabled=False)
        cache = QueryCacheService(config=config)

        # Set should return empty string
        key = await cache.set(value={"data": "test"}, query_type=QueryType.COMMUNITY_DETECTION)
        assert key == ""

        # Get should return None
        result = await cache.get(QueryType.COMMUNITY_DETECTION)
        assert result is None


class TestCachedQueryDecorator:
    """Test the @cached_query decorator."""

    @pytest.mark.asyncio
    async def test_decorator_caches_result(self):
        """Test that decorator caches function results."""
        from api.services.query_cache import (
            QueryType,
            cached_query,
            initialize_query_cache,
            reset_query_cache_service,
        )

        # Initialize cache
        reset_query_cache_service()
        initialize_query_cache()

        call_count = 0

        @cached_query(QueryType.COMMUNITY_DETECTION, project_id_param="project_id")
        async def expensive_operation(project_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": call_count}

        # First call - should execute
        result1 = await expensive_operation(project_id="test")
        assert result1 == {"result": 1}
        assert call_count == 1

        # Second call - should use cache
        result2 = await expensive_operation(project_id="test")
        assert result2 == {"result": 1}
        assert call_count == 1  # Not incremented

        # Cleanup
        reset_query_cache_service()


# =============================================================================
# RESULT STREAMING TESTS
# =============================================================================


class TestPaginationModels:
    """Test pagination models."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams default values."""
        from api.services.result_streaming import PaginationParams

        params = PaginationParams()

        assert params.offset == 0
        assert params.limit == 100
        assert params.sort_order == "asc"

    def test_pagination_params_validation(self):
        """Test PaginationParams validation."""
        from api.services.result_streaming import PaginationParams

        # Valid params
        params = PaginationParams(offset=10, limit=50, sort_order="desc")
        assert params.offset == 10
        assert params.limit == 50

    def test_paginated_result_from_list(self):
        """Test PaginatedResult.from_list factory method."""
        from api.services.result_streaming import PaginatedResult

        items = list(range(10))
        result = PaginatedResult.from_list(items, total=100, offset=0, limit=10)

        assert len(result.items) == 10
        assert result.total == 100
        assert result.has_more is True
        assert result.page == 1
        assert result.total_pages == 10

    def test_paginated_result_last_page(self):
        """Test PaginatedResult for last page."""
        from api.services.result_streaming import PaginatedResult

        items = list(range(5))
        result = PaginatedResult.from_list(items, total=25, offset=20, limit=10)

        assert len(result.items) == 5
        assert result.has_more is False
        assert result.page == 3
        assert result.total_pages == 3


class TestChunkedIterator:
    """Test ChunkedIterator for memory-efficient processing."""

    def test_chunked_iteration(self):
        """Test basic chunked iteration."""
        from api.services.result_streaming import ChunkedIterator

        items = list(range(25))
        iterator = ChunkedIterator(items, chunk_size=10)

        chunks = list(iterator)

        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5

    def test_chunked_iterator_with_transform(self):
        """Test chunked iteration with transformation."""
        from api.services.result_streaming import ChunkedIterator

        items = [1, 2, 3, 4, 5]
        iterator = ChunkedIterator(items, chunk_size=2, transform=lambda x: x * 2)

        chunks = list(iterator)

        assert chunks[0] == [2, 4]
        assert chunks[1] == [6, 8]
        assert chunks[2] == [10]

    def test_chunked_iterator_properties(self):
        """Test ChunkedIterator properties."""
        from api.services.result_streaming import ChunkedIterator

        items = list(range(23))
        iterator = ChunkedIterator(items, chunk_size=10)

        assert iterator.total_items == 23
        assert iterator.total_chunks == 3


class TestAsyncResultStream:
    """Test AsyncResultStream for streaming large results."""

    @pytest.mark.asyncio
    async def test_stream_items(self):
        """Test streaming individual items."""
        from api.services.result_streaming import AsyncResultStream

        def fetch_page(offset, limit):
            all_items = list(range(25))
            return all_items[offset:offset + limit]

        stream = AsyncResultStream(fetch_page, page_size=10)

        items = []
        async for item in stream.stream():
            items.append(item)

        assert len(items) == 25
        assert items == list(range(25))

    @pytest.mark.asyncio
    async def test_stream_chunks(self):
        """Test streaming in chunks."""
        from api.services.result_streaming import AsyncResultStream

        def fetch_page(offset, limit):
            all_items = list(range(25))
            return all_items[offset:offset + limit]

        stream = AsyncResultStream(fetch_page, page_size=10)

        chunks = []
        async for chunk in stream.stream_chunks():
            chunks.append(chunk)

        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[2]) == 5

    @pytest.mark.asyncio
    async def test_stream_with_max_items(self):
        """Test streaming with max items limit."""
        from api.services.result_streaming import AsyncResultStream

        def fetch_page(offset, limit):
            all_items = list(range(100))
            return all_items[offset:offset + limit]

        stream = AsyncResultStream(fetch_page, page_size=10, max_items=15)

        items = []
        async for item in stream.stream():
            items.append(item)

        assert len(items) == 15

    @pytest.mark.asyncio
    async def test_stream_statistics(self):
        """Test streaming statistics tracking."""
        from api.services.result_streaming import AsyncResultStream

        def fetch_page(offset, limit):
            all_items = list(range(25))
            return all_items[offset:offset + limit]

        stream = AsyncResultStream(fetch_page, page_size=10)

        async for _ in stream.stream():
            pass

        stats = stream.get_stats()
        assert stats.items_processed == 25
        assert stats.chunks_processed == 3


class TestPaginationUtilities:
    """Test pagination utility functions."""

    def test_paginate_list(self):
        """Test paginate_list function."""
        from api.services.result_streaming import paginate_list

        items = list(range(50))
        result = paginate_list(items, offset=10, limit=10)

        assert len(result.items) == 10
        assert result.items[0] == 10
        assert result.total == 50
        assert result.has_more is True

    def test_paginate_list_with_sorting(self):
        """Test paginate_list with sorting."""
        from api.services.result_streaming import paginate_list

        items = [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}]
        result = paginate_list(items, sort_by="name", sort_order="asc")

        assert result.items[0]["name"] == "Alice"
        assert result.items[2]["name"] == "Charlie"

    def test_calculate_pagination(self):
        """Test calculate_pagination function."""
        from api.services.result_streaming import calculate_pagination

        result = calculate_pagination(total=100, page=3, per_page=10)

        assert result["offset"] == 20
        assert result["limit"] == 10
        assert result["page"] == 3
        assert result["total_pages"] == 10
        assert result["has_prev"] is True
        assert result["has_next"] is True


class TestBatchProcessing:
    """Test batch processing utilities."""

    @pytest.mark.asyncio
    async def test_process_in_batches(self):
        """Test process_in_batches function."""
        from api.services.result_streaming import process_in_batches

        items = list(range(25))
        batches_processed = []

        def processor(batch):
            batches_processed.append(len(batch))
            return sum(batch)

        results = await process_in_batches(items, processor, batch_size=10)

        assert len(results) == 3
        assert batches_processed == [10, 10, 5]


class TestMemoryEstimation:
    """Test memory estimation utilities."""

    def test_estimate_memory_usage(self):
        """Test memory usage estimation."""
        from api.services.result_streaming import estimate_memory_usage

        items = [{"data": "x" * 100} for _ in range(100)]
        memory_mb = estimate_memory_usage(items)

        assert memory_mb > 0
        assert memory_mb < 10  # Should be less than 10 MB for this small list


# =============================================================================
# SERVICE EXPORTS TESTS
# =============================================================================


class TestServicesExports:
    """Test that Phase 20 services export correctly."""

    def test_query_cache_exports(self):
        """Test query cache service exports."""
        from api.services import (
            CacheConfig,
            CacheEntry,
            CacheStats,
            QueryCacheService,
            QueryType,
            cached_query,
            get_query_cache_service,
            initialize_query_cache,
            reset_query_cache_service,
        )

        assert QueryCacheService is not None
        assert QueryType is not None
        assert CacheConfig is not None
        assert cached_query is not None

    def test_result_streaming_imports(self):
        """Test result streaming module imports."""
        from api.services.result_streaming import (
            AsyncResultStream,
            ChunkedIterator,
            PaginatedResult,
            PaginationParams,
            StreamingStats,
            calculate_pagination,
            estimate_memory_usage,
            paginate_list,
            process_in_batches,
        )

        assert PaginationParams is not None
        assert PaginatedResult is not None
        assert ChunkedIterator is not None
        assert AsyncResultStream is not None


# =============================================================================
# NEO4J INDEX VERIFICATION TESTS
# =============================================================================


class TestNeo4jIndexes:
    """Test Neo4j index definitions."""

    def test_index_definitions_exist(self):
        """Test that index definitions are in neo4j_handler."""
        import neo4j_handler

        # Read the source to verify indexes are defined
        import inspect
        source = inspect.getsource(neo4j_handler.Neo4jHandler.ensure_constraints)

        # Check for Phase 20 optimization indexes
        assert "FieldValue" in source
        assert "fv.section_id, fv.field_id" in source
        assert "identifier_type, o.linked" in source
        assert "TAGGED" in source


# =============================================================================
# BATCH ORPHAN OPERATIONS TESTS
# =============================================================================


class TestBatchOrphanOperations:
    """Test batch orphan data operations."""

    def test_batch_methods_exist(self):
        """Test that batch methods exist in neo4j_handler."""
        import neo4j_handler

        handler_class = neo4j_handler.Neo4jHandler

        assert hasattr(handler_class, "create_orphan_data_batch")
        assert hasattr(handler_class, "link_orphan_data_batch")

    def test_batch_methods_signatures(self):
        """Test batch method signatures."""
        import inspect
        import neo4j_handler

        # Check create_orphan_data_batch signature
        sig = inspect.signature(neo4j_handler.Neo4jHandler.create_orphan_data_batch)
        params = list(sig.parameters.keys())
        assert "project_id" in params
        assert "orphan_data_list" in params

        # Check link_orphan_data_batch signature
        sig = inspect.signature(neo4j_handler.Neo4jHandler.link_orphan_data_batch)
        params = list(sig.parameters.keys())
        assert "project_id" in params
        assert "links" in params
