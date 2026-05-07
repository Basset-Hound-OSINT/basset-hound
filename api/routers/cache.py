"""
Cache Management Endpoints

Stream 2: Caching Layer Enhancements

Provides REST API endpoints for:
- Cache statistics and monitoring
- Manual cache invalidation
- Cache health checks
- Cache warming
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.services.cache_service import get_cache_service, CacheService

router = APIRouter(prefix="/cache", tags=["cache"])


# ==================== Models ====================

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    backend: str
    enabled: bool
    initialized: bool
    hits: int
    misses: int
    hit_rate_percent: float
    cache_size: Optional[int] = None
    items: Optional[int] = None


class InvalidationResponse(BaseModel):
    """Cache invalidation response."""
    count: int
    message: str


class HealthCheckResponse(BaseModel):
    """Cache health check response."""
    healthy: bool
    backend_type: str
    message: str


# ==================== Dependencies ====================

def get_cache() -> CacheService:
    """Get cache service instance."""
    cache = get_cache_service()
    if cache is None or not cache.is_enabled:
        raise HTTPException(status_code=503, detail="Cache service not available")
    return cache


# ==================== Endpoints ====================

@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats(cache: CacheService = Depends(get_cache)):
    """
    Get cache statistics.

    Returns:
        - backend: Current backend type (memory, redis)
        - enabled: Whether caching is enabled
        - hits/misses: Cache hit/miss counts
        - hit_rate_percent: Hit rate percentage
        - cache_size: Size in bytes
        - items: Number of cached items
    """
    return await cache.get_stats()


@router.get("/health", response_model=HealthCheckResponse)
async def check_cache_health(cache: CacheService = Depends(get_cache)):
    """
    Check cache health.

    Returns health status and diagnostic information.
    """
    health = await cache.health_check()
    return HealthCheckResponse(
        healthy=health.get("healthy", False),
        backend_type=health.get("backend_type", "unknown"),
        message="Cache is healthy" if health.get("healthy") else "Cache is unhealthy"
    )


@router.post("/clear", response_model=InvalidationResponse)
async def clear_all_cache(cache: CacheService = Depends(get_cache)):
    """
    Clear all cache entries.

    WARNING: This invalidates all cached data. Use with caution.
    """
    count = await cache.clear_all()
    return InvalidationResponse(
        count=count,
        message=f"Cleared {count} cache entries"
    )


@router.post("/clear/project/{project_id}", response_model=InvalidationResponse)
async def clear_project_cache(
    project_id: str,
    cache: CacheService = Depends(get_cache)
):
    """
    Clear all cache entries for a specific project.

    Args:
        project_id: Project identifier
    """
    count = await cache.invalidate_project(project_id)
    return InvalidationResponse(
        count=count,
        message=f"Cleared {count} entries for project {project_id}"
    )


@router.post("/clear/entity/{entity_id}", response_model=InvalidationResponse)
async def clear_entity_cache(
    entity_id: str,
    cache: CacheService = Depends(get_cache)
):
    """
    Clear cache for a specific entity.

    Invalidates the entity and all related relationships/queries.

    Args:
        entity_id: Entity identifier
    """
    # Invalidate entity (cascade to relationships and queries)
    deleted = await cache.invalidate_entity("*", entity_id)  # project_id is wildcarded
    count = 1 if deleted else 0

    # Also invalidate by tag to catch all related entries
    count += await cache._backend.invalidate_by_tag(f"entity:{entity_id}")

    return InvalidationResponse(
        count=count,
        message=f"Cleared entity {entity_id} and {count} related entries"
    )


@router.post("/clear/relationships", response_model=InvalidationResponse)
async def clear_relationships_cache(
    project_id: Optional[str] = Query(None),
    cache: CacheService = Depends(get_cache)
):
    """
    Clear all cached relationships.

    Args:
        project_id: Optional project ID to limit clearing to specific project
    """
    if project_id:
        count = await cache._backend.invalidate_by_tag(f"project:{project_id}")
    else:
        count = await cache._backend.invalidate_by_tag("relationships")

    return InvalidationResponse(
        count=count,
        message=f"Cleared {count} relationship cache entries"
    )


@router.post("/clear/queries", response_model=InvalidationResponse)
async def clear_query_cache(cache: CacheService = Depends(get_cache)):
    """
    Clear all cached query results.
    """
    count = await cache.invalidate_queries()
    return InvalidationResponse(
        count=count,
        message=f"Cleared {count} query cache entries"
    )


@router.get("/info", response_model=Dict[str, Any])
async def get_cache_info(cache: CacheService = Depends(get_cache)):
    """
    Get detailed cache information.

    Returns:
        - backend_type: Current backend (memory, redis, hybrid)
        - enabled: Whether caching is enabled
        - l1_enabled: Whether L1 (in-memory) cache is active
        - l2_enabled: Whether L2 (Redis) cache is active
        - multi_level_enabled: Whether multi-level caching is enabled
        - stats: Current cache statistics
    """
    stats = await cache.get_stats()

    return {
        "backend_type": cache.backend_type.value,
        "enabled": cache.is_enabled,
        "l1_enabled": cache._l1_cache is not None,
        "l2_enabled": cache._l2_cache is not None,
        "multi_level_enabled": cache._enable_multi_level,
        "cascade_invalidation_enabled": cache._cascade_invalidation_enabled,
        "stats": stats,
    }


@router.post("/warm", response_model=Dict[str, str])
async def warm_cache(cache: CacheService = Depends(get_cache)):
    """
    Warm the cache with hot data.

    Preloads frequently accessed entities and queries.
    """
    try:
        await cache._warm_cache()
        return {
            "status": "success",
            "message": "Cache warming completed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache warming failed: {str(e)}"
        )
