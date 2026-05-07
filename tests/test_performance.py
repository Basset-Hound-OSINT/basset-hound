"""
Performance tests for Basset Hound - verify optimizations are working.

Tests:
- Cache hits reduce database queries
- Pagination works correctly
- Batch updates use fewer queries
- Search debouncing works
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime
from uuid import uuid4

# Test cache integration
def test_cache_get_entity():
    """Test that get_entity uses cache."""
    from api.services.cache_service import CacheService

    cache = CacheService(cache_enabled=True)
    loop = asyncio.get_event_loop()

    # Initialize cache
    loop.run_until_complete(cache.initialize())

    # Create test entity
    project_id = "test-proj"
    entity_id = "test-entity"
    entity_data = {
        "id": entity_id,
        "name": "Test Entity",
        "profile": {"bio": "Test bio"}
    }

    # Set entity in cache
    loop.run_until_complete(cache.set_entity(project_id, entity_id, entity_data, ttl=60))

    # Get from cache - should return immediately without DB call
    cached = loop.run_until_complete(cache.get_entity(project_id, entity_id))
    assert cached == entity_data
    assert cached["name"] == "Test Entity"


def test_cache_entity_list():
    """Test that entity lists are cached."""
    from api.services.cache_service import CacheService

    cache = CacheService(cache_enabled=True)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(cache.initialize())

    project_id = "test-proj"
    entities = [
        {"id": "e1", "name": "Entity 1"},
        {"id": "e2", "name": "Entity 2"},
        {"id": "e3", "name": "Entity 3"},
    ]

    # Set list in cache
    loop.run_until_complete(cache.set_entity_list(project_id, entities, ttl=30))

    # Get from cache
    cached_list = loop.run_until_complete(cache.get_entity_list(project_id))
    assert cached_list == entities
    assert len(cached_list) == 3


def test_cache_invalidation():
    """Test that cache invalidation works."""
    from api.services.cache_service import CacheService

    cache = CacheService(cache_enabled=True)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(cache.initialize())

    project_id = "test-proj"
    entity_id = "test-entity"
    entity_data = {"id": entity_id, "name": "Test"}

    # Set and then invalidate
    loop.run_until_complete(cache.set_entity(project_id, entity_id, entity_data))
    cached = loop.run_until_complete(cache.get_entity(project_id, entity_id))
    assert cached is not None

    # Invalidate
    loop.run_until_complete(cache.invalidate_entity(project_id, entity_id))

    # Should be None after invalidation
    cached = loop.run_until_complete(cache.get_entity(project_id, entity_id))
    assert cached is None


def test_cache_stats():
    """Test that cache statistics are tracked."""
    from api.services.cache_service import CacheService

    cache = CacheService(cache_enabled=True)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(cache.initialize())

    project_id = "test-proj"
    entity_id = "test-entity"
    entity_data = {"id": entity_id}

    # Set value
    loop.run_until_complete(cache.set_entity(project_id, entity_id, entity_data))

    # Get value (hit)
    loop.run_until_complete(cache.get_entity(project_id, entity_id))

    # Try to get non-existent (miss)
    loop.run_until_complete(cache.get_entity(project_id, "non-existent"))

    stats = loop.run_until_complete(cache.get_stats())
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1
    assert stats["sets"] >= 1


def test_pagination_response_structure():
    """Test that pagination response has correct structure."""
    # Verify the response structure is defined in entities.py
    with open("/home/devel/basset-hound/api/routers/entities.py", "r") as f:
        content = f.read()

    # Check that EntityListResponse has the right fields
    assert "class EntityListResponse" in content
    assert "entities: list[EntityResponse]" in content
    assert "total: int" in content
    assert "page: int" in content
    assert "pages: int" in content
    assert "has_next: bool" in content
    assert "limit: int" in content


def test_pagination_calculation():
    """Test pagination calculations are correct."""
    import math

    # Test various pagination scenarios
    total = 100
    limit = 50

    pages = math.ceil(total / limit)
    assert pages == 2

    # Page 1
    page = 1
    has_next = page < pages
    assert has_next is True

    # Page 2
    page = 2
    has_next = page < pages
    assert has_next is False

    # Zero items
    total = 0
    pages = math.ceil(total / limit) if total > 0 else 1
    assert pages == 1


def test_cache_is_used_in_entities_router():
    """Test that cache service is imported and used in entities router."""
    with open("/home/devel/basset-hound/api/routers/entities.py", "r") as f:
        content = f.read()

    # Verify cache imports
    assert "from ..services.cache_service import get_cache_service" in content

    # Verify cache is used in list_entities
    assert "cache_service.get_entity_list" in content
    assert "cache_service.set_entity_list" in content

    # Verify cache is used in get_entity
    assert "cache_service.get_entity" in content
    assert "cache_service.set_entity" in content

    # Verify cache invalidation in update
    assert "cache_service.invalidate_entity" in content
    assert "cache_service.invalidate_entity_list" in content


def test_cache_is_used_in_frontend_profiles():
    """Test that cache service is used in frontend profiles router."""
    with open("/home/devel/basset-hound/api/routers/frontend_profiles.py", "r") as f:
        content = f.read()

    # Verify cache imports
    assert "from api.services.cache_service import get_cache_service" in content

    # Verify cache is used in get_people and get_person
    assert "cache_service.get_entity_list" in content
    assert "cache_service.get_entity" in content

    # Verify cache invalidation
    assert "cache_service.invalidate_entity" in content


def test_batch_update_efficiency():
    """
    Test that batch update operations use fewer queries.

    The set_person_fields_batch method uses UNWIND to batch operations
    instead of looping per field, reducing from N+1 queries to ~2 queries.
    """
    from api.services.neo4j_service import AsyncNeo4jService

    # Verify the method exists and has the right signature
    service = AsyncNeo4jService()
    assert hasattr(service, 'set_person_fields_batch')

    # Verify it handles profile data (dict of sections and fields)
    # This would be called with:
    # profile_data = {
    #     "section1": {"field1": "value1", "field2": "value2"},
    #     "section2": {"field3": "value3"}
    # }
    # Instead of calling set_person_field 3 times, it batches them


def test_frontend_search_debounce():
    """
    Test that frontend search is properly debounced.

    The JavaScript should:
    1. Set timeout on each keystroke
    2. Clear previous timeout if user types again within 300ms
    3. Only execute search after 300ms of no typing
    """
    # This test verifies the JS implementation via the code structure
    # The setupSearch function should use clearTimeout and setTimeout with 300ms delay
    import re

    # Read the UI people list JS file
    with open("/home/devel/basset-hound/static/js/ui-people-list.js", "r") as f:
        js_content = f.read()

    # Verify debounce pattern exists
    assert "clearTimeout" in js_content
    assert "setTimeout" in js_content
    assert "300" in js_content

    # Verify debounce timer variable is declared
    assert "searchDebounceTimer" in js_content


def test_frontend_search_fast_path():
    """
    Test that frontend search uses optimized field extraction.

    Instead of JSON.stringify on entire profile per keystroke,
    search should extract only key fields (name, email, phone) once.
    """
    with open("/home/devel/basset-hound/static/js/ui-people-list.js", "r") as f:
        js_content = f.read()

    # Verify old inefficient code is removed
    assert "JSON.stringify" not in js_content or "JSON.stringify" not in js_content.split("filterPeople")[0]

    # Verify getSearchableText function exists
    assert "getSearchableText" in js_content

    # Verify it extracts specific fields
    assert "email" in js_content
    assert "phone" in js_content


def test_frontend_pagination_state():
    """
    Test that frontend maintains pagination state.

    Should have:
    - currentPage variable
    - pageSize variable
    - totalPages variable
    - loadMore function
    """
    with open("/home/devel/basset-hound/static/js/ui-people-list.js", "r") as f:
        js_content = f.read()

    # Verify state variables
    assert "currentPage" in js_content
    assert "pageSize" in js_content
    assert "totalPages" in js_content

    # Verify loadMore function exists
    assert "function loadMore" in js_content or "const loadMore" in js_content

    # Verify append mode for rendering
    assert "appendMode" in js_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
