"""
Marketplace Router for Basset Hound.

Provides API endpoints for the template marketplace functionality.
Supports publishing, searching, downloading, and reviewing community templates.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, ConfigDict, Field

from ..services.marketplace_service import (
    MarketplaceService,
    MarketplaceTemplate,
    TemplateReview,
    SortBy,
    MarketplaceTemplateNotFoundError,
    MarketplacePublishError,
    MarketplaceReviewError,
    get_marketplace_service,
)
from ..services.template_service import (
    TemplateType,
    TemplateVariable,
    VariableType,
    ReportTemplate,
    TemplateNotFoundError,
    get_template_service,
)


router = APIRouter(
    prefix="/marketplace",
    tags=["marketplace"],
    responses={
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"},
    },
)


# ==================== Pydantic Models ====================


class TemplateVariableResponse(BaseModel):
    """Schema for template variable response."""
    name: str
    type: str
    required: bool
    default_value: Optional[Any]
    description: str


class PublishTemplateRequest(BaseModel):
    """Schema for publishing a template to the marketplace."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "template_id": "550e8400-e29b-41d4-a716-446655440000",
            "author": "johndoe",
            "description": "A professional entity report template with detailed styling.",
            "tags": ["entity", "professional", "osint"],
            "preview_image": None
        }
    })

    template_id: str = Field(
        ...,
        description="ID of the local template to publish",
    )
    author: str = Field(
        ...,
        description="Author username",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        default="",
        description="Detailed description for the marketplace",
        max_length=2000,
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorization tags",
        max_length=10,
    )
    preview_image: Optional[str] = Field(
        default=None,
        description="Base64 encoded preview image",
    )


class MarketplaceTemplateResponse(BaseModel):
    """Schema for marketplace template response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "template_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Professional Entity Report",
            "description": "A professional template for entity reports",
            "template_type": "entity_report",
            "author": "johndoe",
            "tags": ["entity", "professional"],
            "downloads": 150,
            "rating": 4.5,
            "ratings_count": 42,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-20T14:20:00"
        }
    })

    id: str
    template_id: str
    name: str
    description: str
    template_type: str
    content: str
    variables: List[TemplateVariableResponse]
    author: str
    tags: List[str]
    preview_image: Optional[str]
    downloads: int
    rating: float
    ratings_count: int
    created_at: str
    updated_at: str


class MarketplaceTemplateListItem(BaseModel):
    """Schema for marketplace template list item (condensed)."""
    id: str
    template_id: str
    name: str
    description: str
    template_type: str
    author: str
    tags: List[str]
    downloads: int
    rating: float
    ratings_count: int
    created_at: str
    updated_at: str


class MarketplaceTemplateListResponse(BaseModel):
    """Schema for marketplace template list response."""
    templates: List[MarketplaceTemplateListItem]
    count: int


class AddReviewRequest(BaseModel):
    """Schema for adding a review."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user123",
            "rating": 5,
            "comment": "Excellent template! Very professional and easy to use."
        }
    })

    user_id: str = Field(
        ...,
        description="User ID of the reviewer",
        min_length=1,
        max_length=100,
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating (1-5)",
    )
    comment: str = Field(
        default="",
        description="Review comment",
        max_length=1000,
    )


class ReviewResponse(BaseModel):
    """Schema for review response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "review_id": "550e8400-e29b-41d4-a716-446655440002",
            "template_id": "550e8400-e29b-41d4-a716-446655440001",
            "user_id": "user123",
            "rating": 5,
            "comment": "Excellent template!",
            "created_at": "2024-01-16T09:15:00"
        }
    })

    review_id: str
    template_id: str
    user_id: str
    rating: int
    comment: str
    created_at: str


class ReviewListResponse(BaseModel):
    """Schema for review list response."""
    reviews: List[ReviewResponse]
    count: int


class DownloadResponse(BaseModel):
    """Schema for download response."""
    local_template_id: str
    name: str
    message: str


class UpdateTemplateRequest(BaseModel):
    """Schema for updating a marketplace template."""
    description: Optional[str] = Field(
        default=None,
        description="New description",
        max_length=2000,
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="New tags list",
        max_length=10,
    )
    preview_image: Optional[str] = Field(
        default=None,
        description="New preview image",
    )


class MarketplaceStatsResponse(BaseModel):
    """Schema for marketplace statistics response."""
    total_templates: int
    total_downloads: int
    total_reviews: int
    unique_authors: int
    templates_by_type: Dict[str, int]
    average_rating: float


# ==================== Helper Functions ====================


def _parse_template_type(type_str: str) -> TemplateType:
    """Parse template type string to TemplateType enum."""
    try:
        return TemplateType(type_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template type: {type_str}. Must be one of: entity_report, project_summary, relationship_graph, timeline, custom"
        )


def _parse_sort_by(sort_str: str) -> SortBy:
    """Parse sort by string to SortBy enum."""
    try:
        return SortBy(sort_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field: {sort_str}. Must be one of: downloads, rating, created_at, updated_at, name"
        )


def _marketplace_template_to_response(template: MarketplaceTemplate) -> MarketplaceTemplateResponse:
    """Convert MarketplaceTemplate to response model."""
    return MarketplaceTemplateResponse(
        id=template.id,
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        template_type=template.template_type.value,
        content=template.content,
        variables=[
            TemplateVariableResponse(
                name=v.name,
                type=v.type.value,
                required=v.required,
                default_value=v.default_value,
                description=v.description,
            )
            for v in template.variables
        ],
        author=template.author,
        tags=template.tags,
        preview_image=template.preview_image,
        downloads=template.downloads,
        rating=template.rating,
        ratings_count=template.ratings_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


def _marketplace_template_to_list_item(template: MarketplaceTemplate) -> MarketplaceTemplateListItem:
    """Convert MarketplaceTemplate to list item model."""
    return MarketplaceTemplateListItem(
        id=template.id,
        template_id=template.template_id,
        name=template.name,
        description=template.description[:200] + "..." if len(template.description) > 200 else template.description,
        template_type=template.template_type.value,
        author=template.author,
        tags=template.tags,
        downloads=template.downloads,
        rating=template.rating,
        ratings_count=template.ratings_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


def _review_to_response(review: TemplateReview) -> ReviewResponse:
    """Convert TemplateReview to response model."""
    return ReviewResponse(
        review_id=review.review_id,
        template_id=review.template_id,
        user_id=review.user_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at.isoformat(),
    )


# ==================== Endpoints ====================


@router.post(
    "/templates",
    response_model=MarketplaceTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish template to marketplace",
    description="Publish a local template to the community marketplace.",
    responses={
        201: {"description": "Template published successfully"},
        400: {"description": "Invalid request or publishing error"},
        404: {"description": "Local template not found"},
    },
)
async def publish_template(
    request: PublishTemplateRequest,
) -> MarketplaceTemplateResponse:
    """
    Publish a template to the marketplace.

    The template must exist locally before it can be published.

    - **template_id**: ID of the local template to publish
    - **author**: Author username
    - **description**: Detailed description for the marketplace
    - **tags**: List of categorization tags
    - **preview_image**: Optional base64 encoded preview image
    """
    template_service = get_template_service()
    marketplace_service = get_marketplace_service()

    # Get the local template
    local_template = template_service.get_template(request.template_id)
    if local_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Local template not found: {request.template_id}"
        )

    try:
        marketplace_template = marketplace_service.publish_template(
            template=local_template,
            author=request.author,
            description=request.description,
            tags=request.tags,
            preview_image=request.preview_image,
        )

        return _marketplace_template_to_response(marketplace_template)

    except MarketplacePublishError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/templates",
    response_model=MarketplaceTemplateListResponse,
    summary="Search marketplace templates",
    description="Search and filter templates in the marketplace.",
    responses={
        200: {"description": "List of matching templates"},
    },
)
async def search_templates(
    query: Optional[str] = Query(
        default=None,
        alias="q",
        description="Text search query",
    ),
    template_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by template type",
    ),
    tags: Optional[str] = Query(
        default=None,
        description="Comma-separated list of tags to filter by",
    ),
    author: Optional[str] = Query(
        default=None,
        description="Filter by author",
    ),
    sort_by: str = Query(
        default="downloads",
        description="Sort by field (downloads, rating, created_at, updated_at, name)",
    ),
    ascending: bool = Query(
        default=False,
        description="Sort in ascending order",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of results to skip",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Search and filter marketplace templates.

    - **q**: Text search query (searches name and description)
    - **type**: Filter by template type
    - **tags**: Comma-separated tags to filter by
    - **author**: Filter by author
    - **sort_by**: Field to sort by
    - **ascending**: Sort direction
    - **limit**: Maximum results per page
    - **offset**: Results to skip for pagination
    """
    marketplace_service = get_marketplace_service()

    # Parse template type
    type_filter = None
    if template_type is not None:
        type_filter = _parse_template_type(template_type)

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Parse sort by
    sort_by_enum = _parse_sort_by(sort_by)

    templates = marketplace_service.search_templates(
        query=query,
        type_filter=type_filter,
        tags=tag_list,
        author=author,
        sort_by=sort_by_enum,
        ascending=ascending,
        limit=limit,
        offset=offset,
    )

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/templates/{template_id}",
    response_model=MarketplaceTemplateResponse,
    summary="Get marketplace template",
    description="Retrieve a specific marketplace template by ID.",
    responses={
        200: {"description": "Template found"},
        404: {"description": "Template not found"},
    },
)
async def get_template(
    template_id: str,
) -> MarketplaceTemplateResponse:
    """
    Get a marketplace template by ID.

    - **template_id**: The marketplace template ID
    """
    marketplace_service = get_marketplace_service()

    try:
        template = marketplace_service.get_template(template_id)
        return _marketplace_template_to_response(template)

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )


@router.post(
    "/templates/{template_id}/download",
    response_model=DownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Download template from marketplace",
    description="Download a template from the marketplace and import it locally.",
    responses={
        201: {"description": "Template downloaded and imported successfully"},
        404: {"description": "Marketplace template not found"},
    },
)
async def download_template(
    template_id: str,
) -> DownloadResponse:
    """
    Download a template from the marketplace.

    The template will be imported to your local template library.
    The download counter will be incremented.

    - **template_id**: The marketplace template ID
    """
    marketplace_service = get_marketplace_service()

    try:
        local_template = marketplace_service.download_template(template_id)

        return DownloadResponse(
            local_template_id=local_template.id,
            name=local_template.name,
            message=f"Template '{local_template.name}' downloaded successfully",
        )

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unpublish template from marketplace",
    description="Remove a template from the marketplace.",
    responses={
        204: {"description": "Template unpublished successfully"},
        404: {"description": "Template not found"},
    },
)
async def unpublish_template(
    template_id: str,
) -> None:
    """
    Unpublish a template from the marketplace.

    This removes the template from the marketplace but does not affect
    any local copies that have been downloaded.

    - **template_id**: The marketplace template ID
    """
    marketplace_service = get_marketplace_service()

    try:
        marketplace_service.unpublish_template(template_id)
        return None

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )


@router.post(
    "/templates/{template_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add review for template",
    description="Add or update a review for a marketplace template.",
    responses={
        201: {"description": "Review added/updated successfully"},
        400: {"description": "Invalid review data"},
        404: {"description": "Template not found"},
    },
)
async def add_review(
    template_id: str,
    request: AddReviewRequest,
) -> ReviewResponse:
    """
    Add a review for a marketplace template.

    If the user has already reviewed this template, their previous
    review will be updated.

    - **template_id**: The marketplace template ID
    - **user_id**: User ID of the reviewer
    - **rating**: Rating (1-5)
    - **comment**: Optional review comment
    """
    marketplace_service = get_marketplace_service()

    try:
        review = marketplace_service.add_review(
            template_id=template_id,
            user_id=request.user_id,
            rating=request.rating,
            comment=request.comment,
        )

        return _review_to_response(review)

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )
    except MarketplaceReviewError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/templates/{template_id}/reviews",
    response_model=ReviewListResponse,
    summary="Get reviews for template",
    description="Retrieve all reviews for a marketplace template.",
    responses={
        200: {"description": "List of reviews"},
        404: {"description": "Template not found"},
    },
)
async def get_reviews(
    template_id: str,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of reviews",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of reviews to skip",
    ),
) -> ReviewListResponse:
    """
    Get reviews for a marketplace template.

    - **template_id**: The marketplace template ID
    - **limit**: Maximum reviews per page
    - **offset**: Reviews to skip for pagination
    """
    marketplace_service = get_marketplace_service()

    try:
        reviews = marketplace_service.get_reviews(
            template_id=template_id,
            limit=limit,
            offset=offset,
        )

        items = [_review_to_response(r) for r in reviews]

        return ReviewListResponse(
            reviews=items,
            count=len(items),
        )

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )


@router.get(
    "/popular",
    response_model=MarketplaceTemplateListResponse,
    summary="Get popular templates",
    description="Retrieve the most downloaded templates from the marketplace.",
    responses={
        200: {"description": "List of popular templates"},
    },
)
async def get_popular_templates(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of templates",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Get the most popular templates by download count.

    - **limit**: Maximum number of templates to return
    """
    marketplace_service = get_marketplace_service()

    templates = marketplace_service.get_popular_templates(limit=limit)

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/top-rated",
    response_model=MarketplaceTemplateListResponse,
    summary="Get top-rated templates",
    description="Retrieve the highest-rated templates from the marketplace.",
    responses={
        200: {"description": "List of top-rated templates"},
    },
)
async def get_top_rated_templates(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of templates",
    ),
    min_ratings: int = Query(
        default=1,
        ge=1,
        description="Minimum number of ratings required",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Get the top-rated templates.

    - **limit**: Maximum number of templates to return
    - **min_ratings**: Minimum number of ratings required
    """
    marketplace_service = get_marketplace_service()

    templates = marketplace_service.get_top_rated_templates(
        limit=limit,
        min_ratings=min_ratings,
    )

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/recent",
    response_model=MarketplaceTemplateListResponse,
    summary="Get recent templates",
    description="Retrieve recently published templates from the marketplace.",
    responses={
        200: {"description": "List of recent templates"},
    },
)
async def get_recent_templates(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of templates",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Get recently published templates.

    - **limit**: Maximum number of templates to return
    """
    marketplace_service = get_marketplace_service()

    templates = marketplace_service.get_recent_templates(limit=limit)

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/authors/{author}",
    response_model=MarketplaceTemplateListResponse,
    summary="Get templates by author",
    description="Retrieve all templates published by a specific author.",
    responses={
        200: {"description": "List of templates by author"},
    },
)
async def get_templates_by_author(
    author: str,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of templates",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Get all templates by a specific author.

    - **author**: Author username
    - **limit**: Maximum number of templates to return
    """
    marketplace_service = get_marketplace_service()

    templates = marketplace_service.get_templates_by_author(
        author=author,
        limit=limit,
    )

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/tags/{tag}",
    response_model=MarketplaceTemplateListResponse,
    summary="Get templates by tag",
    description="Retrieve all templates with a specific tag.",
    responses={
        200: {"description": "List of templates with tag"},
    },
)
async def get_templates_by_tag(
    tag: str,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of templates",
    ),
) -> MarketplaceTemplateListResponse:
    """
    Get all templates with a specific tag.

    - **tag**: Tag to filter by
    - **limit**: Maximum number of templates to return
    """
    marketplace_service = get_marketplace_service()

    templates = marketplace_service.get_templates_by_tag(
        tag=tag,
        limit=limit,
    )

    items = [_marketplace_template_to_list_item(t) for t in templates]

    return MarketplaceTemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.patch(
    "/templates/{template_id}",
    response_model=MarketplaceTemplateResponse,
    summary="Update marketplace template",
    description="Update a marketplace template's metadata.",
    responses={
        200: {"description": "Template updated successfully"},
        404: {"description": "Template not found"},
    },
)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
) -> MarketplaceTemplateResponse:
    """
    Update a marketplace template's metadata.

    Only description, tags, and preview image can be updated.

    - **template_id**: The marketplace template ID
    - **description**: New description (optional)
    - **tags**: New tags list (optional)
    - **preview_image**: New preview image (optional)
    """
    marketplace_service = get_marketplace_service()

    try:
        template = marketplace_service.update_template(
            template_id=template_id,
            description=request.description,
            tags=request.tags,
            preview_image=request.preview_image,
        )

        return _marketplace_template_to_response(template)

    except MarketplaceTemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace template not found: {template_id}"
        )


@router.get(
    "/stats",
    response_model=MarketplaceStatsResponse,
    summary="Get marketplace statistics",
    description="Retrieve overall statistics about the marketplace.",
    responses={
        200: {"description": "Marketplace statistics"},
    },
)
async def get_marketplace_stats() -> MarketplaceStatsResponse:
    """
    Get overall marketplace statistics.

    Returns total templates, downloads, reviews, authors, and breakdown by type.
    """
    marketplace_service = get_marketplace_service()

    stats = marketplace_service.get_statistics()

    return MarketplaceStatsResponse(
        total_templates=stats["total_templates"],
        total_downloads=stats["total_downloads"],
        total_reviews=stats["total_reviews"],
        unique_authors=stats["unique_authors"],
        templates_by_type=stats["templates_by_type"],
        average_rating=stats["average_rating"],
    )
