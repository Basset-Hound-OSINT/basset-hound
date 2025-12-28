"""
Template Marketplace Service for Basset Hound

This module provides a marketplace for sharing and downloading community templates.
It supports publishing, searching, rating, and downloading templates from a central
marketplace repository.
"""

import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .template_service import (
    ReportTemplate,
    TemplateType,
    TemplateVariable,
    VariableType,
    get_template_service,
)

logger = logging.getLogger(__name__)


class SortBy(str, Enum):
    """Sorting options for marketplace templates."""
    DOWNLOADS = "downloads"
    RATING = "rating"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"


class MarketplaceTemplate(BaseModel):
    """
    Represents a template published to the marketplace.

    Extends the base template with marketplace-specific metadata including
    author information, ratings, download counts, and tags.

    Attributes:
        id: Unique marketplace identifier
        template_id: Reference to the original template
        name: Display name of the template
        description: Detailed description of the template
        template_type: Type of template (entity_report, project_summary, etc.)
        content: Jinja2 template content
        variables: List of expected variables
        author: Author/publisher username
        tags: List of categorization tags
        preview_image: Optional base64 encoded preview image
        downloads: Number of times template has been downloaded
        rating: Average rating (1-5 scale)
        ratings_count: Number of ratings received
        created_at: Timestamp of publication
        updated_at: Timestamp of last update
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str = Field(..., description="Original template ID")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="Detailed description")
    template_type: TemplateType = Field(default=TemplateType.CUSTOM, description="Template type")
    content: str = Field(..., description="Jinja2 template content")
    variables: List[TemplateVariable] = Field(default_factory=list, description="Template variables")
    author: str = Field(..., description="Author username")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    preview_image: Optional[str] = Field(default=None, description="Base64 preview image")
    downloads: int = Field(default=0, description="Download count")
    rating: float = Field(default=0.0, description="Average rating (1-5)")
    ratings_count: int = Field(default=0, description="Number of ratings")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "content": self.content,
            "variables": [v.to_dict() for v in self.variables],
            "author": self.author,
            "tags": self.tags,
            "preview_image": self.preview_image,
            "downloads": self.downloads,
            "rating": self.rating,
            "ratings_count": self.ratings_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplaceTemplate":
        """Create from dictionary."""
        template_type = data.get("template_type", "custom")
        if isinstance(template_type, str):
            template_type = TemplateType(template_type)

        variables = data.get("variables", [])
        if variables and isinstance(variables[0], dict):
            variables = [TemplateVariable.from_dict(v) for v in variables]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.now(timezone.utc)

        return cls(
            id=data.get("id", str(uuid4())),
            template_id=data.get("template_id", ""),
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            template_type=template_type,
            content=data.get("content", ""),
            variables=variables,
            author=data.get("author", "anonymous"),
            tags=data.get("tags", []),
            preview_image=data.get("preview_image"),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            ratings_count=data.get("ratings_count", 0),
            created_at=created_at,
            updated_at=updated_at,
        )


class TemplateReview(BaseModel):
    """
    Represents a review for a marketplace template.

    Attributes:
        review_id: Unique review identifier
        template_id: ID of the reviewed template
        user_id: ID of the user who submitted the review
        rating: Rating score (1-5)
        comment: Optional review comment
        created_at: Timestamp of review submission
    """
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str = Field(..., description="Template being reviewed")
    user_id: str = Field(..., description="Reviewer user ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    comment: str = Field(default="", description="Review comment")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_id": self.review_id,
            "template_id": self.template_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateReview":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            review_id=data.get("review_id", str(uuid4())),
            template_id=data.get("template_id", ""),
            user_id=data.get("user_id", ""),
            rating=data.get("rating", 3),
            comment=data.get("comment", ""),
            created_at=created_at,
        )


class MarketplaceTemplateNotFoundError(Exception):
    """Raised when a marketplace template is not found."""
    pass


class MarketplacePublishError(Exception):
    """Raised when template publishing fails."""
    pass


class MarketplaceReviewError(Exception):
    """Raised when a review operation fails."""
    pass


class MarketplaceService:
    """
    Service for managing the template marketplace.

    Provides methods for publishing, searching, downloading, and reviewing
    templates in a community marketplace.
    """

    def __init__(
        self,
        max_templates: int = 500,
        max_reviews_per_template: int = 100,
    ):
        """
        Initialize the marketplace service with empty storage.

        Args:
            max_templates: Maximum number of marketplace templates to store (LRU eviction)
            max_reviews_per_template: Maximum number of reviews per template
        """
        self._lock = threading.RLock()
        self._templates: OrderedDict[str, MarketplaceTemplate] = OrderedDict()
        self._reviews: Dict[str, List[TemplateReview]] = {}  # template_id -> reviews
        self._user_reviews: Dict[str, Dict[str, str]] = {}  # user_id -> {template_id: review_id}
        self._max_templates = max_templates
        self._max_reviews_per_template = max_reviews_per_template

    # ==================== Memory Management ====================

    def _enforce_templates_limit(self) -> None:
        """Evict oldest templates when limit is exceeded (LRU eviction)."""
        while len(self._templates) > self._max_templates:
            oldest_key = next(iter(self._templates))
            self._templates.pop(oldest_key)
            # Clean up reviews for this template
            if oldest_key in self._reviews:
                del self._reviews[oldest_key]
            # Clean up user review references
            for user_id in list(self._user_reviews.keys()):
                if oldest_key in self._user_reviews[user_id]:
                    del self._user_reviews[user_id][oldest_key]
            logger.debug(f"LRU evicted marketplace template: {oldest_key}")

    def _enforce_reviews_limit(self, template_id: str) -> None:
        """Evict oldest reviews for a template when limit is exceeded."""
        if template_id not in self._reviews:
            return
        reviews = self._reviews[template_id]
        while len(reviews) > self._max_reviews_per_template:
            # Remove oldest review (first in list, sorted by created_at)
            oldest_review = reviews.pop(0)
            # Clean up user reference
            if oldest_review.user_id in self._user_reviews:
                if template_id in self._user_reviews[oldest_review.user_id]:
                    del self._user_reviews[oldest_review.user_id][template_id]
            logger.debug(f"LRU evicted review for template {template_id}")

    def get_templates_size(self) -> int:
        """Get current number of templates in storage."""
        with self._lock:
            return len(self._templates)

    def get_templates_capacity(self) -> int:
        """Get maximum templates storage capacity."""
        return self._max_templates

    def get_reviews_capacity_per_template(self) -> int:
        """Get maximum reviews per template capacity."""
        return self._max_reviews_per_template

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for this service."""
        with self._lock:
            total_reviews = sum(len(reviews) for reviews in self._reviews.values())
            return {
                "templates_count": len(self._templates),
                "templates_capacity": self._max_templates,
                "templates_usage_percent": (len(self._templates) / self._max_templates * 100) if self._max_templates > 0 else 0,
                "total_reviews": total_reviews,
                "reviews_capacity_per_template": self._max_reviews_per_template,
                "unique_users_with_reviews": len(self._user_reviews),
            }

    def publish_template(
        self,
        template: ReportTemplate,
        author: str,
        description: str,
        tags: Optional[List[str]] = None,
        preview_image: Optional[str] = None,
    ) -> MarketplaceTemplate:
        """
        Publish a template to the marketplace.

        Args:
            template: The ReportTemplate to publish
            author: Author/publisher username
            description: Detailed description for the marketplace
            tags: Optional list of categorization tags
            preview_image: Optional base64 encoded preview image

        Returns:
            The created MarketplaceTemplate

        Raises:
            MarketplacePublishError: If publishing fails
        """
        if not template.content:
            raise MarketplacePublishError("Template content cannot be empty")

        if not author or not author.strip():
            raise MarketplacePublishError("Author name is required")

        now = datetime.now(timezone.utc)
        marketplace_id = str(uuid4())

        marketplace_template = MarketplaceTemplate(
            id=marketplace_id,
            template_id=template.id,
            name=template.name,
            description=description or template.description or "",
            template_type=template.template_type,
            content=template.content,
            variables=template.variables.copy() if template.variables else [],
            author=author.strip(),
            tags=tags or [],
            preview_image=preview_image,
            downloads=0,
            rating=0.0,
            ratings_count=0,
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self._templates[marketplace_id] = marketplace_template
            self._templates.move_to_end(marketplace_id)  # Mark as most recently used
            self._enforce_templates_limit()
            self._reviews[marketplace_id] = []

        logger.info(f"Published template to marketplace: {template.name} (ID: {marketplace_id})")

        return marketplace_template

    def unpublish_template(self, template_id: str) -> bool:
        """
        Remove a template from the marketplace.

        Args:
            template_id: The marketplace template ID to remove

        Returns:
            True if successfully unpublished

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
        """
        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            template = self._templates.pop(template_id)

            # Clean up reviews
            if template_id in self._reviews:
                del self._reviews[template_id]

            # Clean up user review references
            for user_id in list(self._user_reviews.keys()):
                if template_id in self._user_reviews[user_id]:
                    del self._user_reviews[user_id][template_id]

        logger.info(f"Unpublished template from marketplace: {template.name} (ID: {template_id})")

        return True

    def search_templates(
        self,
        query: Optional[str] = None,
        type_filter: Optional[TemplateType] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        sort_by: SortBy = SortBy.DOWNLOADS,
        ascending: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[MarketplaceTemplate]:
        """
        Search and filter marketplace templates.

        Args:
            query: Text search query (searches name and description)
            type_filter: Filter by template type
            tags: Filter by tags (matches any)
            author: Filter by author
            sort_by: Field to sort by
            ascending: Sort in ascending order if True
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching MarketplaceTemplates
        """
        with self._lock:
            results = list(self._templates.values())

        # Filter by query (case-insensitive search in name and description)
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower() or query_lower in t.description.lower()
            ]

        # Filter by template type
        if type_filter is not None:
            results = [t for t in results if t.template_type == type_filter]

        # Filter by tags (match any)
        if tags:
            tags_lower = [tag.lower() for tag in tags]
            results = [
                t for t in results
                if any(tag.lower() in tags_lower for tag in t.tags)
            ]

        # Filter by author
        if author:
            author_lower = author.lower()
            results = [t for t in results if t.author.lower() == author_lower]

        # Sort results
        sort_key_map = {
            SortBy.DOWNLOADS: lambda t: t.downloads,
            SortBy.RATING: lambda t: t.rating,
            SortBy.CREATED_AT: lambda t: t.created_at,
            SortBy.UPDATED_AT: lambda t: t.updated_at,
            SortBy.NAME: lambda t: t.name.lower(),
        }
        sort_key = sort_key_map.get(sort_by, lambda t: t.downloads)
        results.sort(key=sort_key, reverse=not ascending)

        # Apply pagination
        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return results

    def get_template(self, template_id: str) -> MarketplaceTemplate:
        """
        Get a marketplace template by ID.

        Args:
            template_id: The marketplace template ID

        Returns:
            The MarketplaceTemplate

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
        """
        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            self._templates.move_to_end(template_id)  # Mark as most recently used
            return self._templates[template_id]

    def download_template(self, template_id: str) -> ReportTemplate:
        """
        Download a template from the marketplace.

        Increments the download counter and imports the template
        to the local template service.

        Args:
            template_id: The marketplace template ID

        Returns:
            The imported ReportTemplate

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
        """
        # Get template info and increment counter under lock
        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            marketplace_template = self._templates[template_id]

            # Increment download counter
            marketplace_template.downloads += 1
            marketplace_template.updated_at = datetime.now(timezone.utc)

            # Copy data needed for template creation
            template_name = marketplace_template.name
            template_type = marketplace_template.template_type
            template_content = marketplace_template.content
            template_description = marketplace_template.description
            template_variables = list(marketplace_template.variables)

        # Create local template outside of lock (may involve I/O or other services)
        template_service = get_template_service()

        # Prepare variables for creation
        variables = [
            TemplateVariable(
                name=v.name,
                type=v.type,
                required=v.required,
                default_value=v.default_value,
                description=v.description,
            )
            for v in template_variables
        ]

        # Create the local template
        local_template = template_service.create_template(
            name=template_name,
            template_type=template_type,
            content=template_content,
            variables=variables,
            description=template_description,
        )

        logger.info(f"Downloaded template from marketplace: {template_name} (ID: {template_id})")

        return local_template

    def add_review(
        self,
        template_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> TemplateReview:
        """
        Add a review for a marketplace template.

        If the user has already reviewed this template, their previous
        review will be updated.

        Args:
            template_id: The marketplace template ID
            user_id: The reviewing user's ID
            rating: Rating score (1-5)
            comment: Optional review comment

        Returns:
            The created or updated TemplateReview

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
            MarketplaceReviewError: If rating is invalid
        """
        if rating < 1 or rating > 5:
            raise MarketplaceReviewError("Rating must be between 1 and 5")

        if not user_id or not user_id.strip():
            raise MarketplaceReviewError("User ID is required")

        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            # Check if user already reviewed this template
            if user_id in self._user_reviews and template_id in self._user_reviews[user_id]:
                # Update existing review
                existing_review_id = self._user_reviews[user_id][template_id]
                reviews = self._reviews.get(template_id, [])

                for review in reviews:
                    if review.review_id == existing_review_id:
                        old_rating = review.rating
                        review.rating = rating
                        review.comment = comment

                        # Update template rating
                        self._update_template_rating(template_id, old_rating, rating, is_update=True)

                        logger.info(f"Updated review for template {template_id} by user {user_id}")
                        return review

            # Create new review
            review = TemplateReview(
                review_id=str(uuid4()),
                template_id=template_id,
                user_id=user_id.strip(),
                rating=rating,
                comment=comment,
                created_at=datetime.now(timezone.utc),
            )

            # Store review
            if template_id not in self._reviews:
                self._reviews[template_id] = []
            self._reviews[template_id].append(review)
            # Sort by created_at for proper LRU eviction (oldest first)
            self._reviews[template_id].sort(key=lambda r: r.created_at)
            self._enforce_reviews_limit(template_id)

            # Track user's review
            if user_id not in self._user_reviews:
                self._user_reviews[user_id] = {}
            self._user_reviews[user_id][template_id] = review.review_id

            # Update template rating
            self._update_template_rating(template_id, 0, rating, is_update=False)

            # Mark template as recently used
            self._templates.move_to_end(template_id)

        logger.info(f"Added review for template {template_id} by user {user_id}")

        return review

    def _update_template_rating(
        self,
        template_id: str,
        old_rating: int,
        new_rating: int,
        is_update: bool,
    ) -> None:
        """Update the template's aggregate rating."""
        template = self._templates[template_id]

        if is_update:
            # Remove old rating contribution and add new
            total = template.rating * template.ratings_count
            total = total - old_rating + new_rating
            template.rating = total / template.ratings_count if template.ratings_count > 0 else 0.0
        else:
            # Add new rating
            total = template.rating * template.ratings_count
            template.ratings_count += 1
            template.rating = (total + new_rating) / template.ratings_count

        template.updated_at = datetime.now(timezone.utc)

    def get_reviews(
        self,
        template_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[TemplateReview]:
        """
        Get reviews for a marketplace template.

        Args:
            template_id: The marketplace template ID
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip

        Returns:
            List of TemplateReviews

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
        """
        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            reviews = list(self._reviews.get(template_id, []))

        # Sort by created_at descending (newest first)
        reviews = sorted(reviews, key=lambda r: r.created_at, reverse=True)

        # Apply pagination
        if offset:
            reviews = reviews[offset:]
        if limit is not None:
            reviews = reviews[:limit]

        return reviews

    def get_popular_templates(
        self,
        limit: int = 10,
    ) -> List[MarketplaceTemplate]:
        """
        Get the most popular templates by download count.

        Args:
            limit: Maximum number of templates to return

        Returns:
            List of popular MarketplaceTemplates
        """
        return self.search_templates(
            sort_by=SortBy.DOWNLOADS,
            ascending=False,
            limit=limit,
        )

    def get_top_rated_templates(
        self,
        limit: int = 10,
        min_ratings: int = 1,
    ) -> List[MarketplaceTemplate]:
        """
        Get the top-rated templates.

        Args:
            limit: Maximum number of templates to return
            min_ratings: Minimum number of ratings required

        Returns:
            List of top-rated MarketplaceTemplates
        """
        with self._lock:
            templates = [
                t for t in self._templates.values()
                if t.ratings_count >= min_ratings
            ]

        templates.sort(key=lambda t: t.rating, reverse=True)

        return templates[:limit]

    def get_templates_by_author(
        self,
        author: str,
        limit: Optional[int] = None,
    ) -> List[MarketplaceTemplate]:
        """
        Get all templates by a specific author.

        Args:
            author: Author username
            limit: Maximum number of templates to return

        Returns:
            List of MarketplaceTemplates by the author
        """
        return self.search_templates(
            author=author,
            sort_by=SortBy.CREATED_AT,
            ascending=False,
            limit=limit,
        )

    def get_templates_by_tag(
        self,
        tag: str,
        limit: Optional[int] = None,
    ) -> List[MarketplaceTemplate]:
        """
        Get templates with a specific tag.

        Args:
            tag: Tag to filter by
            limit: Maximum number of templates to return

        Returns:
            List of MarketplaceTemplates with the tag
        """
        return self.search_templates(
            tags=[tag],
            sort_by=SortBy.DOWNLOADS,
            ascending=False,
            limit=limit,
        )

    def get_recent_templates(
        self,
        limit: int = 10,
    ) -> List[MarketplaceTemplate]:
        """
        Get recently published templates.

        Args:
            limit: Maximum number of templates to return

        Returns:
            List of recent MarketplaceTemplates
        """
        return self.search_templates(
            sort_by=SortBy.CREATED_AT,
            ascending=False,
            limit=limit,
        )

    def update_template(
        self,
        template_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        preview_image: Optional[str] = None,
    ) -> MarketplaceTemplate:
        """
        Update a marketplace template's metadata.

        Args:
            template_id: The marketplace template ID
            description: New description (optional)
            tags: New tags list (optional)
            preview_image: New preview image (optional)

        Returns:
            The updated MarketplaceTemplate

        Raises:
            MarketplaceTemplateNotFoundError: If template not found
        """
        with self._lock:
            if template_id not in self._templates:
                raise MarketplaceTemplateNotFoundError(f"Template not found: {template_id}")

            template = self._templates[template_id]

            if description is not None:
                template.description = description

            if tags is not None:
                template.tags = tags

            if preview_image is not None:
                template.preview_image = preview_image

            template.updated_at = datetime.now(timezone.utc)

        logger.info(f"Updated marketplace template: {template.name} (ID: {template_id})")

        return template

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get marketplace statistics.

        Returns:
            Dictionary with marketplace statistics
        """
        with self._lock:
            templates = list(self._templates.values())
            total_reviews = sum(len(reviews) for reviews in self._reviews.values())

        total_downloads = sum(t.downloads for t in templates)

        # Count templates by type
        type_counts = {}
        for t in templates:
            type_name = t.template_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Get unique authors
        authors = set(t.author for t in templates)

        return {
            "total_templates": len(templates),
            "total_downloads": total_downloads,
            "total_reviews": total_reviews,
            "unique_authors": len(authors),
            "templates_by_type": type_counts,
            "average_rating": (
                sum(t.rating for t in templates) / len(templates)
                if templates else 0.0
            ),
        }

    def get_user_reviews(self, user_id: str) -> List[TemplateReview]:
        """
        Get all reviews by a specific user.

        Args:
            user_id: The user's ID

        Returns:
            List of TemplateReviews by the user
        """
        with self._lock:
            if user_id not in self._user_reviews:
                return []

            reviews = []
            for template_id, review_id in self._user_reviews[user_id].items():
                template_reviews = self._reviews.get(template_id, [])
                for review in template_reviews:
                    if review.review_id == review_id:
                        reviews.append(review)
                        break

            return reviews

    def delete_review(self, review_id: str, user_id: str) -> bool:
        """
        Delete a review.

        Args:
            review_id: The review ID to delete
            user_id: The user ID (must match the review owner)

        Returns:
            True if deleted successfully

        Raises:
            MarketplaceReviewError: If review not found or user doesn't own it
        """
        with self._lock:
            # Find the review
            for template_id, reviews in self._reviews.items():
                for i, review in enumerate(reviews):
                    if review.review_id == review_id:
                        if review.user_id != user_id:
                            raise MarketplaceReviewError("User does not own this review")

                        # Update template rating before removal
                        template = self._templates.get(template_id)
                        if template and template.ratings_count > 1:
                            total = template.rating * template.ratings_count
                            total -= review.rating
                            template.ratings_count -= 1
                            template.rating = total / template.ratings_count
                            template.updated_at = datetime.now(timezone.utc)
                        elif template:
                            template.rating = 0.0
                            template.ratings_count = 0
                            template.updated_at = datetime.now(timezone.utc)

                        # Remove review
                        reviews.pop(i)

                        # Remove user tracking
                        if user_id in self._user_reviews and template_id in self._user_reviews[user_id]:
                            del self._user_reviews[user_id][template_id]

                        logger.info(f"Deleted review {review_id}")
                        return True

            raise MarketplaceReviewError(f"Review not found: {review_id}")

    def clear_all(self) -> None:
        """Clear all marketplace data (for testing)."""
        with self._lock:
            self._templates.clear()
            self._reviews.clear()
            self._user_reviews.clear()
        logger.info("Cleared all marketplace data")


# Singleton instance management
_marketplace_service: Optional[MarketplaceService] = None
_marketplace_service_lock = threading.RLock()


def get_marketplace_service() -> MarketplaceService:
    """
    Get or create the marketplace service singleton.

    Returns:
        MarketplaceService instance
    """
    global _marketplace_service

    if _marketplace_service is None:
        with _marketplace_service_lock:
            # Double-check after acquiring lock
            if _marketplace_service is None:
                _marketplace_service = MarketplaceService()

    return _marketplace_service


def set_marketplace_service(service: Optional[MarketplaceService]) -> None:
    """Set the marketplace service singleton (for testing)."""
    global _marketplace_service
    with _marketplace_service_lock:
        _marketplace_service = service
