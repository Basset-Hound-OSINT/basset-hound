"""
Platform Router for Basset Hound (Phase 48: Dynamic Entity Architecture).

Provides REST API endpoints for managing platform entities.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..services.neo4j_service import AsyncNeo4jService
from ..services.platform_service import PlatformService

router = APIRouter(
    prefix="/platforms",
    tags=["platforms"],
    responses={
        404: {"description": "Platform not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class PlatformCreate(BaseModel):
    """Request model for creating a platform."""
    name: str = Field(..., description="Platform name (required)")
    category: Optional[str] = Field(
        "other",
        description="Platform category (social_media, professional, forum, etc.)"
    )
    color: Optional[str] = Field(None, description="Brand color in hex format")
    icon_class: Optional[str] = Field(None, description="Font Awesome icon class")
    profile_url_template: Optional[str] = Field(
        None,
        description="Profile URL template with {username} placeholder"
    )
    active: Optional[bool] = Field(True, description="Platform is active")
    description: Optional[str] = Field(None, description="Platform description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Mastodon",
                "category": "social_media",
                "color": "#563ACC",
                "icon_class": "fa-mastodon",
                "profile_url_template": "https://mastodon.social/@{username}",
                "active": True,
                "description": "Decentralized social network"
            }
        }
    )


class PlatformUpdate(BaseModel):
    """Request model for updating a platform."""
    name: Optional[str] = Field(None, description="Platform name")
    category: Optional[str] = Field(None, description="Platform category")
    color: Optional[str] = Field(None, description="Brand color")
    icon_class: Optional[str] = Field(None, description="Icon class")
    profile_url_template: Optional[str] = Field(None, description="Profile URL template")
    active: Optional[bool] = Field(None, description="Active status")
    description: Optional[str] = Field(None, description="Description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Mastodon",
                "active": True
            }
        }
    )


class PlatformResponse(BaseModel):
    """Response model for platform entity."""
    id: str = Field(..., description="Platform entity ID")
    name: str = Field(..., description="Platform name")
    category: str = Field(..., description="Platform category")
    color: Optional[str] = Field(None, description="Brand color")
    icon_class: Optional[str] = Field(None, description="Icon class")
    profile_url_template: Optional[str] = Field(None, description="Profile URL template")
    active: bool = Field(True, description="Active status")
    description: Optional[str] = Field(None, description="Description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    entity_type: str = Field("platform", description="Entity type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Mastodon",
                "category": "social_media",
                "color": "#563ACC",
                "icon_class": "fa-mastodon",
                "profile_url_template": "https://mastodon.social/@{username}",
                "active": True,
                "created_at": "2024-05-06T12:00:00",
                "entity_type": "platform"
            }
        }
    )


class PlatformListResponse(BaseModel):
    """Response model for platform list."""
    platforms: List[PlatformResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of platforms")


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(True)
    message: Optional[str] = Field(None)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


async def get_platform_service(
    neo4j_handler: AsyncNeo4jService = Depends(get_neo4j_handler),
) -> PlatformService:
    """Get platform service."""
    return PlatformService(neo4j_handler)


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/",
    response_model=PlatformListResponse,
    summary="List all platforms",
    description="Retrieve a list of all platform entities, optionally filtered by category.",
)
async def list_platforms(
    category: Optional[str] = Query(
        None,
        description="Filter by category (social_media, professional, forum, etc.)"
    ),
    service: PlatformService = Depends(get_platform_service),
) -> PlatformListResponse:
    """List all platforms."""
    try:
        platforms = await service.list_platforms(category=category)
        return PlatformListResponse(
            platforms=[PlatformResponse(**p) for p in platforms],
            count=len(platforms),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing platforms: {str(e)}"
        )


@router.get(
    "/{platform_id}",
    response_model=PlatformResponse,
    summary="Get platform by ID",
    description="Retrieve details for a specific platform entity.",
)
async def get_platform(
    platform_id: str,
    service: PlatformService = Depends(get_platform_service),
) -> PlatformResponse:
    """Get a specific platform."""
    try:
        platform = await service.get_platform(platform_id)
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform {platform_id} not found"
            )
        return PlatformResponse(**platform)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching platform: {str(e)}"
        )


@router.post(
    "/",
    response_model=PlatformResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new platform",
    description="Create a new platform entity.",
)
async def create_platform(
    data: PlatformCreate,
    service: PlatformService = Depends(get_platform_service),
) -> PlatformResponse:
    """Create a new platform."""
    try:
        platform_id = await service.create_platform(
            name=data.name,
            category=data.category or "other",
            color=data.color,
            icon_class=data.icon_class,
            profile_url_template=data.profile_url_template,
            active=data.active,
            description=data.description,
        )
        platform = await service.get_platform(platform_id)
        return PlatformResponse(**platform)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating platform: {str(e)}"
        )


@router.put(
    "/{platform_id}",
    response_model=PlatformResponse,
    summary="Update platform",
    description="Update properties of an existing platform.",
)
async def update_platform(
    platform_id: str,
    data: PlatformUpdate,
    service: PlatformService = Depends(get_platform_service),
) -> PlatformResponse:
    """Update a platform."""
    try:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if not update_data:
            platform = await service.get_platform(platform_id)
            if not platform:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Platform {platform_id} not found"
                )
            return PlatformResponse(**platform)

        await service.update_platform(platform_id, **update_data)
        platform = await service.get_platform(platform_id)

        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform {platform_id} not found"
            )

        return PlatformResponse(**platform)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating platform: {str(e)}"
        )


@router.delete(
    "/{platform_id}",
    response_model=SuccessResponse,
    summary="Delete platform",
    description="Delete a platform entity (only if no accounts are linked).",
)
async def delete_platform(
    platform_id: str,
    service: PlatformService = Depends(get_platform_service),
) -> SuccessResponse:
    """Delete a platform."""
    try:
        await service.delete_platform(platform_id)
        return SuccessResponse(
            success=True,
            message=f"Platform {platform_id} deleted successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting platform: {str(e)}"
        )
