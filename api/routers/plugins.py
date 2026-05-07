"""
Plugin Management Router for Basset Hound

REST API endpoints for:
- Plugin registration and publishing
- Plugin discovery and search
- Plugin execution
- Plugin marketplace (reviews, ratings, downloads)
- Plugin versioning and management

Phase 8 Stream 7: Custom Visualization Plugins
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import get_neo4j_handler, get_app_config
from api.services.neo4j_service import AsyncNeo4jService
from api.services.plugin_service import (
    PluginService,
    PluginMetadata,
    PluginStatus,
    PluginType,
)

logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(prefix="/plugins", tags=["Plugins"])

# Global plugin service instance
_plugin_service: Optional[PluginService] = None


async def get_plugin_service() -> PluginService:
    """Get or initialize plugin service."""
    global _plugin_service

    if _plugin_service is None:
        from api.services.cache_service import get_cache_service

        neo4j_service = AsyncNeo4jService()
        cache_service = None
        try:
            cache_service = await get_cache_service()
        except Exception as e:
            logger.warning(f"Cache service not available: {e}")

        _plugin_service = PluginService(neo4j_service, cache_service)
        await _plugin_service.initialize()

    return _plugin_service


# ==================== Request/Response Models ====================


class PluginManifest(BaseModel):
    """Plugin manifest."""
    id: str = Field(..., description="Unique plugin ID")
    name: str = Field(..., description="Plugin name")
    description: str = Field(..., description="Plugin description")
    author: str = Field(..., description="Plugin author")
    version: str = Field(..., description="Semantic version (x.y.z)")
    type: str = Field(..., description="Plugin type")
    entry_point: str = Field(..., description="Entry point JS file")
    tags: List[str] = Field(default_factory=list, description="Plugin tags")
    permissions: List[str] = Field(
        default_factory=lambda: ["read:entities", "read:relationships", "read:graph"],
        description="Required permissions"
    )
    icon_url: Optional[str] = Field(None, description="Icon URL")
    homepage: Optional[str] = Field(None, description="Plugin homepage")
    repository: Optional[str] = Field(None, description="Repository URL")
    license: Optional[str] = Field(None, description="License")


class RegisterPluginRequest(BaseModel):
    """Request to register a new plugin."""
    manifest: PluginManifest = Field(..., description="Plugin manifest")
    code: str = Field(..., description="Plugin source code")


class PluginMetadataResponse(BaseModel):
    """Plugin metadata response."""
    id: str
    name: str
    description: str
    author: str
    version: str
    type: str
    status: str
    tags: List[str]
    rating: float
    download_count: int
    created_at: str
    updated_at: str
    thumbnail_url: Optional[str]
    permissions: List[str]


class PluginCodeResponse(BaseModel):
    """Plugin code response."""
    plugin_id: str
    code: str
    version: str
    manifest: Dict[str, Any]


class PluginExecutionRequest(BaseModel):
    """Request to execute a plugin."""
    plugin_id: str = Field(..., description="Plugin ID")
    graph_data: Dict[str, Any] = Field(..., description="Graph data for plugin")
    options: Optional[Dict[str, Any]] = Field(None, description="Plugin options")


class PluginExecutionResponse(BaseModel):
    """Plugin execution result."""
    plugin_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


class PluginReviewRequest(BaseModel):
    """Request to add a review."""
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    comment: str = Field(..., description="Review comment")


class PluginReviewResponse(BaseModel):
    """Plugin review response."""
    id: str
    plugin_id: str
    user_id: str
    rating: int
    comment: str
    created_at: str


class PluginListResponse(BaseModel):
    """List of plugins response."""
    total: int
    plugins: List[PluginMetadataResponse]
    status: str = "success"


# ==================== API Endpoints ====================


@router.post(
    "/register",
    response_model=PluginMetadataResponse,
    summary="Register a new plugin",
    description="Register a new visualization or analysis plugin",
)
async def register_plugin(
    request: RegisterPluginRequest,
    user_id: str = Query(..., description="User ID registering the plugin"),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginMetadataResponse:
    """
    Register a new plugin.

    Validates manifest, stores code, and initializes plugin in registry.
    """
    try:
        manifest_dict = request.manifest.model_dump()
        metadata = await plugin_service.register_plugin(
            manifest=manifest_dict,
            code=request.code,
            user_id=user_id,
        )

        return PluginMetadataResponse(**metadata.to_dict())

    except ValueError as e:
        logger.warning(f"Invalid plugin registration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Plugin registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to register plugin")


@router.get(
    "/{plugin_id}",
    response_model=PluginMetadataResponse,
    summary="Get plugin metadata",
    description="Retrieve plugin metadata and information",
)
async def get_plugin_metadata(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginMetadataResponse:
    """Get plugin metadata by ID."""
    plugin = await plugin_service.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    return PluginMetadataResponse(**plugin.to_dict())


@router.get(
    "/{plugin_id}/code",
    response_model=PluginCodeResponse,
    summary="Get plugin code",
    description="Retrieve plugin source code for execution",
)
async def get_plugin_code(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginCodeResponse:
    """Get plugin source code."""
    metadata = await plugin_service.get_plugin(plugin_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    code = await plugin_service.get_plugin_code(plugin_id)
    if not code:
        raise HTTPException(status_code=404, detail=f"Plugin code not found: {plugin_id}")

    return PluginCodeResponse(
        plugin_id=plugin_id,
        code=code,
        version=metadata.version,
        manifest={
            "name": metadata.name,
            "description": metadata.description,
            "type": metadata.plugin_type.value,
        },
    )


@router.get(
    "",
    response_model=PluginListResponse,
    summary="List plugins",
    description="List available plugins with optional filtering",
)
async def list_plugins(
    status: Optional[str] = Query(None, description="Filter by status"),
    plugin_type: Optional[str] = Query(None, description="Filter by type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginListResponse:
    """List all plugins with optional filters."""
    try:
        plugins = await plugin_service.list_plugins(status)

        # Filter by type if provided
        plugin_list = [p for p in plugins]
        if plugin_type:
            plugin_list = [p for p in plugin_list if p["type"] == plugin_type]

        # Filter by tags if provided
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            plugin_list = [
                p for p in plugin_list
                if any(tag in p.get("tags", []) for tag in tag_list)
            ]

        return PluginListResponse(
            total=len(plugin_list),
            plugins=[PluginMetadataResponse(**p) for p in plugin_list],
        )

    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(status_code=500, detail="Failed to list plugins")


@router.post(
    "/{plugin_id}/execute",
    response_model=PluginExecutionResponse,
    summary="Execute plugin",
    description="Execute a plugin with graph data context",
)
async def execute_plugin(
    plugin_id: str,
    request: PluginExecutionRequest = Body(...),
    project_id: Optional[str] = Query(None, description="Project context"),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginExecutionResponse:
    """
    Execute a plugin with context data.

    The plugin receives graph data and can perform analysis or
    visualization rendering.
    """
    try:
        result = await plugin_service.execute_plugin(
            plugin_id=plugin_id,
            graph_data=request.graph_data,
            options=request.options,
        )

        response = PluginExecutionResponse(
            plugin_id=result.get("plugin_id", plugin_id),
            status=result.get("status", "success"),
            data=result.get("data"),
            error=result.get("error"),
            timestamp=result.get("timestamp", ""),
        )

        return response

    except Exception as e:
        logger.error(f"Plugin execution error: {e}")
        return PluginExecutionResponse(
            plugin_id=plugin_id,
            status="error",
            error=str(e),
            timestamp="",
        )


@router.post(
    "/{plugin_id}/reviews",
    response_model=PluginReviewResponse,
    summary="Add plugin review",
    description="Add a review and rating to a plugin",
)
async def add_plugin_review(
    plugin_id: str,
    request: PluginReviewRequest,
    user_id: str = Query(..., description="User ID"),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginReviewResponse:
    """Add a review to a plugin."""
    try:
        review = await plugin_service.add_review(
            plugin_id=plugin_id,
            user_id=user_id,
            rating=request.rating,
            comment=request.comment,
        )

        return PluginReviewResponse(**review)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add review: {e}")
        raise HTTPException(status_code=500, detail="Failed to add review")


@router.get(
    "/{plugin_id}/reviews",
    response_model=List[PluginReviewResponse],
    summary="Get plugin reviews",
    description="Retrieve all reviews for a plugin",
)
async def get_plugin_reviews(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> List[PluginReviewResponse]:
    """Get all reviews for a plugin."""
    try:
        reviews = await plugin_service.get_reviews(plugin_id)
        return [PluginReviewResponse(**r) for r in reviews]
    except Exception as e:
        logger.error(f"Failed to get reviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reviews")


@router.post(
    "/{plugin_id}/download",
    summary="Download plugin",
    description="Download a plugin and increment download count",
)
async def download_plugin(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> Dict[str, Any]:
    """
    Download a plugin.

    Returns plugin code and metadata for client-side installation.
    """
    try:
        metadata = await plugin_service.get_plugin(plugin_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Plugin not found")

        code = await plugin_service.get_plugin_code(plugin_id)
        if not code:
            raise HTTPException(status_code=404, detail="Plugin code not found")

        # Increment download count
        metadata.download_count += 1

        return {
            "plugin_id": plugin_id,
            "manifest": metadata.to_dict(),
            "code": code,
            "status": "success",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plugin download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download plugin")


@router.get(
    "/search/by-type",
    response_model=PluginListResponse,
    summary="Search plugins by type",
    description="Find plugins by visualization type",
)
async def search_plugins_by_type(
    plugin_type: str = Query(..., description="Plugin type to search"),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginListResponse:
    """Search plugins by type."""
    try:
        plugins = await plugin_service.list_plugins()
        filtered = [
            p for p in plugins
            if p.get("type") == plugin_type
        ]

        return PluginListResponse(
            total=len(filtered),
            plugins=[PluginMetadataResponse(**p) for p in filtered],
        )

    except Exception as e:
        logger.error(f"Plugin search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search plugins")
