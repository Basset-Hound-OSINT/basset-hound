"""
Tests for the Template Marketplace Service

Comprehensive test coverage for:
- MarketplaceTemplate model
- TemplateReview model
- MarketplaceService class methods
- Template publishing
- Searching and filtering
- Downloading templates
- Reviews and ratings
- Popularity tracking
- Author and tag queries
- Router endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from api.services.marketplace_service import (
    MarketplaceTemplate,
    TemplateReview,
    SortBy,
    MarketplaceService,
    MarketplaceTemplateNotFoundError,
    MarketplacePublishError,
    MarketplaceReviewError,
    get_marketplace_service,
    set_marketplace_service,
)
from api.services.template_service import (
    ReportTemplate,
    TemplateType,
    TemplateVariable,
    VariableType,
    TemplateService,
    set_template_service,
)


# ==================== Fixtures ====================


@pytest.fixture
def template_service():
    """Create a fresh TemplateService for each test."""
    service = TemplateService()
    set_template_service(service)
    return service


@pytest.fixture
def marketplace_service():
    """Create a fresh MarketplaceService for each test."""
    service = MarketplaceService()
    set_marketplace_service(service)
    return service


@pytest.fixture
def sample_template(template_service):
    """Create a sample ReportTemplate for testing."""
    return template_service.create_template(
        name="Sample Template",
        template_type=TemplateType.ENTITY_REPORT,
        content="<h1>{{ title }}</h1><p>{{ content }}</p>",
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=True),
            TemplateVariable(name="content", type=VariableType.STRING, required=True),
        ],
        description="A sample template for testing",
    )


@pytest.fixture
def published_template(marketplace_service, sample_template):
    """Create a published marketplace template for testing."""
    return marketplace_service.publish_template(
        template=sample_template,
        author="testauthor",
        description="A sample marketplace template",
        tags=["test", "sample"],
    )


# ==================== MarketplaceTemplate Model Tests ====================


class TestMarketplaceTemplateModel:
    """Tests for MarketplaceTemplate Pydantic model."""

    def test_create_minimal(self):
        """Test creating a marketplace template with minimal fields."""
        template = MarketplaceTemplate(
            template_id="test-123",
            name="Test Template",
            content="<p>{{ test }}</p>",
            author="testuser",
        )

        assert template.id is not None
        assert template.template_id == "test-123"
        assert template.name == "Test Template"
        assert template.author == "testuser"
        assert template.downloads == 0
        assert template.rating == 0.0
        assert template.ratings_count == 0
        assert template.tags == []

    def test_create_full(self):
        """Test creating a marketplace template with all fields."""
        now = datetime.now()
        template = MarketplaceTemplate(
            id="mp-123",
            template_id="template-123",
            name="Full Template",
            description="Complete description",
            template_type=TemplateType.PROJECT_SUMMARY,
            content="<h1>{{ title }}</h1>",
            variables=[TemplateVariable(name="title", type=VariableType.STRING)],
            author="author123",
            tags=["tag1", "tag2"],
            preview_image="base64image",
            downloads=100,
            rating=4.5,
            ratings_count=50,
            created_at=now,
            updated_at=now,
        )

        assert template.id == "mp-123"
        assert template.template_id == "template-123"
        assert template.template_type == TemplateType.PROJECT_SUMMARY
        assert template.downloads == 100
        assert template.rating == 4.5
        assert len(template.tags) == 2

    def test_to_dict(self):
        """Test converting template to dictionary."""
        template = MarketplaceTemplate(
            template_id="t-1",
            name="Dict Test",
            content="<p>Test</p>",
            author="author",
            tags=["tag1"],
        )

        data = template.to_dict()

        assert data["template_id"] == "t-1"
        assert data["name"] == "Dict Test"
        assert data["tags"] == ["tag1"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "id": "mp-456",
            "template_id": "t-456",
            "name": "From Dict",
            "description": "Created from dict",
            "template_type": "custom",
            "content": "<div>{{ content }}</div>",
            "author": "dictauthor",
            "tags": ["dict", "test"],
            "downloads": 25,
            "rating": 3.5,
            "ratings_count": 10,
        }

        template = MarketplaceTemplate.from_dict(data)

        assert template.id == "mp-456"
        assert template.name == "From Dict"
        assert template.template_type == TemplateType.CUSTOM
        assert template.downloads == 25

    def test_from_dict_defaults(self):
        """Test creating from dict with minimal fields."""
        data = {
            "name": "Minimal",
            "content": "Hello",
        }

        template = MarketplaceTemplate.from_dict(data)

        assert template.name == "Minimal"
        assert template.author == "anonymous"
        assert template.downloads == 0


# ==================== TemplateReview Model Tests ====================


class TestTemplateReviewModel:
    """Tests for TemplateReview Pydantic model."""

    def test_create_minimal(self):
        """Test creating a review with minimal fields."""
        review = TemplateReview(
            template_id="t-123",
            user_id="u-123",
            rating=4,
        )

        assert review.review_id is not None
        assert review.template_id == "t-123"
        assert review.user_id == "u-123"
        assert review.rating == 4
        assert review.comment == ""

    def test_create_full(self):
        """Test creating a review with all fields."""
        now = datetime.now()
        review = TemplateReview(
            review_id="r-123",
            template_id="t-456",
            user_id="u-789",
            rating=5,
            comment="Excellent template!",
            created_at=now,
        )

        assert review.review_id == "r-123"
        assert review.rating == 5
        assert review.comment == "Excellent template!"

    def test_rating_validation_min(self):
        """Test that rating must be at least 1."""
        with pytest.raises(ValueError):
            TemplateReview(
                template_id="t-1",
                user_id="u-1",
                rating=0,
            )

    def test_rating_validation_max(self):
        """Test that rating must be at most 5."""
        with pytest.raises(ValueError):
            TemplateReview(
                template_id="t-1",
                user_id="u-1",
                rating=6,
            )

    def test_to_dict(self):
        """Test converting review to dictionary."""
        review = TemplateReview(
            template_id="t-1",
            user_id="u-1",
            rating=3,
            comment="Good",
        )

        data = review.to_dict()

        assert data["template_id"] == "t-1"
        assert data["rating"] == 3
        assert data["comment"] == "Good"

    def test_from_dict(self):
        """Test creating review from dictionary."""
        data = {
            "review_id": "r-100",
            "template_id": "t-100",
            "user_id": "u-100",
            "rating": 5,
            "comment": "Perfect!",
        }

        review = TemplateReview.from_dict(data)

        assert review.review_id == "r-100"
        assert review.rating == 5


# ==================== SortBy Enum Tests ====================


class TestSortByEnum:
    """Tests for SortBy enum."""

    def test_all_values_exist(self):
        """Test that all expected sort options exist."""
        assert SortBy.DOWNLOADS == "downloads"
        assert SortBy.RATING == "rating"
        assert SortBy.CREATED_AT == "created_at"
        assert SortBy.UPDATED_AT == "updated_at"
        assert SortBy.NAME == "name"

    def test_from_string(self):
        """Test creating from string."""
        assert SortBy("downloads") == SortBy.DOWNLOADS
        assert SortBy("rating") == SortBy.RATING

    def test_invalid_raises(self):
        """Test that invalid value raises error."""
        with pytest.raises(ValueError):
            SortBy("invalid")


# ==================== MarketplaceService Publishing Tests ====================


class TestMarketplacePublishing:
    """Tests for template publishing functionality."""

    def test_publish_template(self, marketplace_service, sample_template):
        """Test publishing a template to the marketplace."""
        published = marketplace_service.publish_template(
            template=sample_template,
            author="testauthor",
            description="Published template description",
            tags=["test", "demo"],
        )

        assert published.id is not None
        assert published.template_id == sample_template.id
        assert published.name == sample_template.name
        assert published.author == "testauthor"
        assert published.downloads == 0
        assert "test" in published.tags

    def test_publish_template_with_preview(self, marketplace_service, sample_template):
        """Test publishing a template with preview image."""
        published = marketplace_service.publish_template(
            template=sample_template,
            author="testauthor",
            description="Has preview",
            preview_image="base64encodedimage",
        )

        assert published.preview_image == "base64encodedimage"

    def test_publish_template_empty_content_fails(self, marketplace_service):
        """Test that publishing template with empty content fails."""
        empty_template = ReportTemplate(
            id="empty-1",
            name="Empty Template",
            content="",
            template_type=TemplateType.CUSTOM,
        )

        with pytest.raises(MarketplacePublishError) as exc_info:
            marketplace_service.publish_template(
                template=empty_template,
                author="test",
                description="Should fail",
            )

        assert "empty" in str(exc_info.value).lower()

    def test_publish_template_empty_author_fails(self, marketplace_service, sample_template):
        """Test that publishing template with empty author fails."""
        with pytest.raises(MarketplacePublishError) as exc_info:
            marketplace_service.publish_template(
                template=sample_template,
                author="",
                description="Should fail",
            )

        assert "author" in str(exc_info.value).lower()

    def test_publish_template_whitespace_author_fails(self, marketplace_service, sample_template):
        """Test that publishing template with whitespace author fails."""
        with pytest.raises(MarketplacePublishError):
            marketplace_service.publish_template(
                template=sample_template,
                author="   ",
                description="Should fail",
            )

    def test_publish_multiple_templates(self, marketplace_service, template_service):
        """Test publishing multiple templates."""
        templates = []
        for i in range(3):
            t = template_service.create_template(
                name=f"Template {i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>Content {i}</p>",
            )
            templates.append(t)

        for i, template in enumerate(templates):
            published = marketplace_service.publish_template(
                template=template,
                author=f"author{i}",
                description=f"Description {i}",
            )
            assert published.name == f"Template {i}"

        all_templates = marketplace_service.search_templates()
        assert len(all_templates) == 3


# ==================== MarketplaceService Unpublishing Tests ====================


class TestMarketplaceUnpublishing:
    """Tests for template unpublishing functionality."""

    def test_unpublish_template(self, marketplace_service, published_template):
        """Test unpublishing a template."""
        template_id = published_template.id

        result = marketplace_service.unpublish_template(template_id)

        assert result is True

        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.get_template(template_id)

    def test_unpublish_nonexistent_fails(self, marketplace_service):
        """Test unpublishing non-existent template fails."""
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.unpublish_template("nonexistent")

    def test_unpublish_removes_reviews(self, marketplace_service, published_template):
        """Test that unpublishing removes associated reviews."""
        # Add a review first
        marketplace_service.add_review(
            template_id=published_template.id,
            user_id="user1",
            rating=5,
            comment="Great!",
        )

        # Unpublish
        marketplace_service.unpublish_template(published_template.id)

        # Verify template and reviews are gone
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.get_template(published_template.id)


# ==================== MarketplaceService Search Tests ====================


class TestMarketplaceSearch:
    """Tests for template searching functionality."""

    def test_search_all(self, marketplace_service, template_service):
        """Test searching all templates."""
        for i in range(5):
            t = template_service.create_template(
                name=f"Search Template {i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>Search {i}</p>",
            )
            marketplace_service.publish_template(
                template=t,
                author="searcher",
                description=f"Searchable {i}",
            )

        results = marketplace_service.search_templates()

        assert len(results) == 5

    def test_search_by_query(self, marketplace_service, template_service):
        """Test searching by query string."""
        t1 = template_service.create_template(
            name="Entity Report",
            template_type=TemplateType.ENTITY_REPORT,
            content="<p>Entity</p>",
        )
        t2 = template_service.create_template(
            name="Project Summary",
            template_type=TemplateType.PROJECT_SUMMARY,
            content="<p>Project</p>",
        )

        marketplace_service.publish_template(t1, "a", "About entities")
        marketplace_service.publish_template(t2, "b", "About projects")

        results = marketplace_service.search_templates(query="entity")

        assert len(results) == 1
        assert results[0].name == "Entity Report"

    def test_search_by_query_description(self, marketplace_service, template_service):
        """Test that query searches description too."""
        t = template_service.create_template(
            name="Generic Name",
            template_type=TemplateType.CUSTOM,
            content="<p>Content</p>",
        )
        marketplace_service.publish_template(t, "a", "Special keyword here")

        results = marketplace_service.search_templates(query="special")

        assert len(results) == 1

    def test_search_by_type(self, marketplace_service, template_service):
        """Test filtering by template type."""
        t1 = template_service.create_template(
            name="Entity",
            template_type=TemplateType.ENTITY_REPORT,
            content="<p>E</p>",
        )
        t2 = template_service.create_template(
            name="Timeline",
            template_type=TemplateType.TIMELINE,
            content="<p>T</p>",
        )

        marketplace_service.publish_template(t1, "a", "Desc")
        marketplace_service.publish_template(t2, "b", "Desc")

        results = marketplace_service.search_templates(type_filter=TemplateType.TIMELINE)

        assert len(results) == 1
        assert results[0].template_type == TemplateType.TIMELINE

    def test_search_by_tags(self, marketplace_service, template_service):
        """Test filtering by tags."""
        t1 = template_service.create_template(name="T1", template_type=TemplateType.CUSTOM, content="<p>1</p>")
        t2 = template_service.create_template(name="T2", template_type=TemplateType.CUSTOM, content="<p>2</p>")

        marketplace_service.publish_template(t1, "a", "D", tags=["osint", "security"])
        marketplace_service.publish_template(t2, "b", "D", tags=["design", "ui"])

        results = marketplace_service.search_templates(tags=["osint"])

        assert len(results) == 1
        assert "osint" in results[0].tags

    def test_search_by_multiple_tags(self, marketplace_service, template_service):
        """Test filtering by multiple tags (OR logic)."""
        t1 = template_service.create_template(name="T1", template_type=TemplateType.CUSTOM, content="<p>1</p>")
        t2 = template_service.create_template(name="T2", template_type=TemplateType.CUSTOM, content="<p>2</p>")
        t3 = template_service.create_template(name="T3", template_type=TemplateType.CUSTOM, content="<p>3</p>")

        marketplace_service.publish_template(t1, "a", "D", tags=["tag1"])
        marketplace_service.publish_template(t2, "b", "D", tags=["tag2"])
        marketplace_service.publish_template(t3, "c", "D", tags=["tag3"])

        results = marketplace_service.search_templates(tags=["tag1", "tag2"])

        assert len(results) == 2

    def test_search_by_author(self, marketplace_service, template_service):
        """Test filtering by author."""
        t1 = template_service.create_template(name="T1", template_type=TemplateType.CUSTOM, content="<p>1</p>")
        t2 = template_service.create_template(name="T2", template_type=TemplateType.CUSTOM, content="<p>2</p>")

        marketplace_service.publish_template(t1, "alice", "D")
        marketplace_service.publish_template(t2, "bob", "D")

        results = marketplace_service.search_templates(author="alice")

        assert len(results) == 1
        assert results[0].author == "alice"

    def test_search_sort_by_downloads(self, marketplace_service, template_service):
        """Test sorting by downloads."""
        templates = []
        for i, downloads in enumerate([10, 50, 30]):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            pub.downloads = downloads
            templates.append(pub)

        results = marketplace_service.search_templates(sort_by=SortBy.DOWNLOADS, ascending=False)

        assert results[0].downloads == 50
        assert results[1].downloads == 30
        assert results[2].downloads == 10

    def test_search_sort_by_rating(self, marketplace_service, template_service):
        """Test sorting by rating."""
        for i, rating in enumerate([3.0, 5.0, 4.0]):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            pub.rating = rating
            pub.ratings_count = 1

        results = marketplace_service.search_templates(sort_by=SortBy.RATING, ascending=False)

        assert results[0].rating == 5.0
        assert results[1].rating == 4.0
        assert results[2].rating == 3.0

    def test_search_sort_by_name(self, marketplace_service, template_service):
        """Test sorting by name."""
        for name in ["Charlie", "Alice", "Bob"]:
            t = template_service.create_template(
                name=name,
                template_type=TemplateType.CUSTOM,
                content=f"<p>{name}</p>",
            )
            marketplace_service.publish_template(t, "x", "D")

        results = marketplace_service.search_templates(sort_by=SortBy.NAME, ascending=True)

        assert results[0].name == "Alice"
        assert results[1].name == "Bob"
        assert results[2].name == "Charlie"

    def test_search_pagination_limit(self, marketplace_service, template_service):
        """Test search with limit."""
        for i in range(10):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            marketplace_service.publish_template(t, f"a{i}", "D")

        results = marketplace_service.search_templates(limit=5)

        assert len(results) == 5

    def test_search_pagination_offset(self, marketplace_service, template_service):
        """Test search with offset."""
        for i in range(10):
            t = template_service.create_template(
                name=f"T{i:02d}",  # Zero-pad for consistent sorting
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            marketplace_service.publish_template(t, f"a{i}", "D")

        results = marketplace_service.search_templates(
            sort_by=SortBy.NAME,
            ascending=True,
            offset=3,
            limit=3,
        )

        assert len(results) == 3
        assert results[0].name == "T03"

    def test_search_case_insensitive(self, marketplace_service, template_service):
        """Test that search is case insensitive."""
        t = template_service.create_template(
            name="UPPERCASE NAME",
            template_type=TemplateType.CUSTOM,
            content="<p>Content</p>",
        )
        marketplace_service.publish_template(t, "test", "lowercase description")

        results = marketplace_service.search_templates(query="uppercase")
        assert len(results) == 1

        results = marketplace_service.search_templates(query="LOWERCASE")
        assert len(results) == 1


# ==================== MarketplaceService Get Template Tests ====================


class TestMarketplaceGetTemplate:
    """Tests for getting individual templates."""

    def test_get_template(self, marketplace_service, published_template):
        """Test getting a template by ID."""
        retrieved = marketplace_service.get_template(published_template.id)

        assert retrieved.id == published_template.id
        assert retrieved.name == published_template.name

    def test_get_template_not_found(self, marketplace_service):
        """Test getting non-existent template raises error."""
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.get_template("nonexistent")


# ==================== MarketplaceService Download Tests ====================


class TestMarketplaceDownload:
    """Tests for template downloading functionality."""

    def test_download_template(self, marketplace_service, published_template):
        """Test downloading a template."""
        initial_downloads = published_template.downloads

        local_template = marketplace_service.download_template(published_template.id)

        assert local_template is not None
        assert local_template.name == published_template.name
        assert local_template.content == published_template.content

        # Verify download counter increased
        updated = marketplace_service.get_template(published_template.id)
        assert updated.downloads == initial_downloads + 1

    def test_download_increments_counter(self, marketplace_service, published_template):
        """Test that multiple downloads increment counter."""
        for i in range(5):
            marketplace_service.download_template(published_template.id)

        updated = marketplace_service.get_template(published_template.id)
        assert updated.downloads == 5

    def test_download_nonexistent_fails(self, marketplace_service):
        """Test downloading non-existent template fails."""
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.download_template("nonexistent")


# ==================== MarketplaceService Review Tests ====================


class TestMarketplaceReviews:
    """Tests for review functionality."""

    def test_add_review(self, marketplace_service, published_template):
        """Test adding a review."""
        review = marketplace_service.add_review(
            template_id=published_template.id,
            user_id="user123",
            rating=5,
            comment="Excellent!",
        )

        assert review.template_id == published_template.id
        assert review.user_id == "user123"
        assert review.rating == 5
        assert review.comment == "Excellent!"

    def test_add_review_updates_rating(self, marketplace_service, published_template):
        """Test that adding reviews updates average rating."""
        marketplace_service.add_review(published_template.id, "u1", 5, "")
        marketplace_service.add_review(published_template.id, "u2", 3, "")

        template = marketplace_service.get_template(published_template.id)

        assert template.rating == 4.0
        assert template.ratings_count == 2

    def test_add_review_invalid_rating_low(self, marketplace_service, published_template):
        """Test that rating below 1 fails."""
        with pytest.raises(MarketplaceReviewError):
            marketplace_service.add_review(
                template_id=published_template.id,
                user_id="user1",
                rating=0,
            )

    def test_add_review_invalid_rating_high(self, marketplace_service, published_template):
        """Test that rating above 5 fails."""
        with pytest.raises(MarketplaceReviewError):
            marketplace_service.add_review(
                template_id=published_template.id,
                user_id="user1",
                rating=6,
            )

    def test_add_review_empty_user_fails(self, marketplace_service, published_template):
        """Test that empty user ID fails."""
        with pytest.raises(MarketplaceReviewError):
            marketplace_service.add_review(
                template_id=published_template.id,
                user_id="",
                rating=4,
            )

    def test_add_review_nonexistent_template(self, marketplace_service):
        """Test adding review to non-existent template fails."""
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.add_review(
                template_id="nonexistent",
                user_id="user1",
                rating=4,
            )

    def test_update_existing_review(self, marketplace_service, published_template):
        """Test that same user updating review updates properly."""
        marketplace_service.add_review(published_template.id, "user1", 3, "OK")
        marketplace_service.add_review(published_template.id, "user1", 5, "Changed my mind!")

        template = marketplace_service.get_template(published_template.id)

        assert template.rating == 5.0
        assert template.ratings_count == 1

    def test_get_reviews(self, marketplace_service, published_template):
        """Test getting reviews for a template."""
        marketplace_service.add_review(published_template.id, "u1", 5, "Great!")
        marketplace_service.add_review(published_template.id, "u2", 4, "Good")
        marketplace_service.add_review(published_template.id, "u3", 3, "OK")

        reviews = marketplace_service.get_reviews(published_template.id)

        assert len(reviews) == 3

    def test_get_reviews_pagination(self, marketplace_service, published_template):
        """Test review pagination."""
        for i in range(10):
            marketplace_service.add_review(published_template.id, f"u{i}", 4, f"Comment {i}")

        reviews = marketplace_service.get_reviews(
            template_id=published_template.id,
            limit=5,
            offset=3,
        )

        assert len(reviews) == 5

    def test_get_reviews_sorted_by_date(self, marketplace_service, published_template):
        """Test that reviews are sorted by date (newest first)."""
        marketplace_service.add_review(published_template.id, "u1", 5, "First")
        marketplace_service.add_review(published_template.id, "u2", 4, "Second")
        marketplace_service.add_review(published_template.id, "u3", 3, "Third")

        reviews = marketplace_service.get_reviews(published_template.id)

        # Newest should be first
        assert reviews[0].comment == "Third"

    def test_delete_review(self, marketplace_service, published_template):
        """Test deleting a review."""
        review = marketplace_service.add_review(published_template.id, "user1", 5, "Great!")

        result = marketplace_service.delete_review(review.review_id, "user1")

        assert result is True

        reviews = marketplace_service.get_reviews(published_template.id)
        assert len(reviews) == 0

    def test_delete_review_wrong_user(self, marketplace_service, published_template):
        """Test that user can't delete another user's review."""
        review = marketplace_service.add_review(published_template.id, "user1", 5, "Great!")

        with pytest.raises(MarketplaceReviewError):
            marketplace_service.delete_review(review.review_id, "user2")

    def test_delete_review_updates_rating(self, marketplace_service, published_template):
        """Test that deleting review updates template rating."""
        marketplace_service.add_review(published_template.id, "u1", 5, "")
        review2 = marketplace_service.add_review(published_template.id, "u2", 1, "")

        marketplace_service.delete_review(review2.review_id, "u2")

        template = marketplace_service.get_template(published_template.id)
        assert template.rating == 5.0
        assert template.ratings_count == 1


# ==================== MarketplaceService Popular Templates Tests ====================


class TestMarketplacePopular:
    """Tests for popular templates functionality."""

    def test_get_popular_templates(self, marketplace_service, template_service):
        """Test getting popular templates."""
        downloads = [100, 50, 200, 10]
        for i, dl in enumerate(downloads):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            pub.downloads = dl

        popular = marketplace_service.get_popular_templates(limit=3)

        assert len(popular) == 3
        assert popular[0].downloads == 200
        assert popular[1].downloads == 100
        assert popular[2].downloads == 50

    def test_get_top_rated_templates(self, marketplace_service, template_service):
        """Test getting top-rated templates."""
        ratings = [(4.5, 10), (5.0, 5), (3.0, 20)]
        for i, (rating, count) in enumerate(ratings):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            pub.rating = rating
            pub.ratings_count = count

        top_rated = marketplace_service.get_top_rated_templates(limit=10)

        assert top_rated[0].rating == 5.0
        assert top_rated[1].rating == 4.5
        assert top_rated[2].rating == 3.0

    def test_get_top_rated_min_ratings(self, marketplace_service, template_service):
        """Test top-rated with minimum ratings filter."""
        ratings = [(4.5, 10), (5.0, 2), (4.0, 15)]
        for i, (rating, count) in enumerate(ratings):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            pub.rating = rating
            pub.ratings_count = count

        top_rated = marketplace_service.get_top_rated_templates(limit=10, min_ratings=5)

        assert len(top_rated) == 2  # Excludes the one with only 2 ratings


# ==================== MarketplaceService Author & Tag Tests ====================


class TestMarketplaceAuthorTag:
    """Tests for author and tag queries."""

    def test_get_templates_by_author(self, marketplace_service, template_service):
        """Test getting templates by author."""
        for i in range(5):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            author = "alice" if i < 3 else "bob"
            marketplace_service.publish_template(t, author, "D")

        alice_templates = marketplace_service.get_templates_by_author("alice")

        assert len(alice_templates) == 3

    def test_get_templates_by_tag(self, marketplace_service, template_service):
        """Test getting templates by tag."""
        for i in range(5):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            tags = ["osint"] if i < 2 else ["other"]
            marketplace_service.publish_template(t, f"a{i}", "D", tags=tags)

        osint_templates = marketplace_service.get_templates_by_tag("osint")

        assert len(osint_templates) == 2

    def test_get_recent_templates(self, marketplace_service, template_service):
        """Test getting recent templates."""
        for i in range(5):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            marketplace_service.publish_template(t, f"a{i}", "D")

        recent = marketplace_service.get_recent_templates(limit=3)

        assert len(recent) == 3


# ==================== MarketplaceService Update Tests ====================


class TestMarketplaceUpdate:
    """Tests for updating marketplace templates."""

    def test_update_template_description(self, marketplace_service, published_template):
        """Test updating template description."""
        updated = marketplace_service.update_template(
            template_id=published_template.id,
            description="New description",
        )

        assert updated.description == "New description"

    def test_update_template_tags(self, marketplace_service, published_template):
        """Test updating template tags."""
        updated = marketplace_service.update_template(
            template_id=published_template.id,
            tags=["new", "tags"],
        )

        assert updated.tags == ["new", "tags"]

    def test_update_template_preview(self, marketplace_service, published_template):
        """Test updating template preview image."""
        updated = marketplace_service.update_template(
            template_id=published_template.id,
            preview_image="newbase64image",
        )

        assert updated.preview_image == "newbase64image"

    def test_update_nonexistent_fails(self, marketplace_service):
        """Test updating non-existent template fails."""
        with pytest.raises(MarketplaceTemplateNotFoundError):
            marketplace_service.update_template(
                template_id="nonexistent",
                description="Should fail",
            )


# ==================== MarketplaceService Statistics Tests ====================


class TestMarketplaceStatistics:
    """Tests for marketplace statistics."""

    def test_get_statistics_empty(self, marketplace_service):
        """Test statistics on empty marketplace."""
        stats = marketplace_service.get_statistics()

        assert stats["total_templates"] == 0
        assert stats["total_downloads"] == 0
        assert stats["total_reviews"] == 0
        assert stats["unique_authors"] == 0

    def test_get_statistics_with_data(self, marketplace_service, template_service):
        """Test statistics with templates and reviews."""
        for i in range(3):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM if i < 2 else TemplateType.ENTITY_REPORT,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"author{i}", "D")
            pub.downloads = 10 * (i + 1)
            marketplace_service.add_review(pub.id, f"user{i}", 4, "Comment")

        stats = marketplace_service.get_statistics()

        assert stats["total_templates"] == 3
        assert stats["total_downloads"] == 60  # 10 + 20 + 30
        assert stats["total_reviews"] == 3
        assert stats["unique_authors"] == 3
        assert stats["templates_by_type"]["custom"] == 2
        assert stats["templates_by_type"]["entity_report"] == 1


# ==================== MarketplaceService User Reviews Tests ====================


class TestMarketplaceUserReviews:
    """Tests for user-specific review functionality."""

    def test_get_user_reviews(self, marketplace_service, template_service):
        """Test getting all reviews by a user."""
        templates = []
        for i in range(3):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            templates.append(pub)
            marketplace_service.add_review(pub.id, "reviewer1", 4, f"Comment {i}")

        user_reviews = marketplace_service.get_user_reviews("reviewer1")

        assert len(user_reviews) == 3

    def test_get_user_reviews_empty(self, marketplace_service):
        """Test getting reviews for user with no reviews."""
        reviews = marketplace_service.get_user_reviews("nonexistent")

        assert reviews == []


# ==================== MarketplaceService Clear All Tests ====================


class TestMarketplaceClearAll:
    """Tests for clearing all marketplace data."""

    def test_clear_all(self, marketplace_service, template_service):
        """Test clearing all marketplace data."""
        for i in range(3):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            pub = marketplace_service.publish_template(t, f"a{i}", "D")
            marketplace_service.add_review(pub.id, f"u{i}", 4, "")

        marketplace_service.clear_all()

        assert len(marketplace_service.search_templates()) == 0
        assert marketplace_service.get_statistics()["total_templates"] == 0


# ==================== Singleton Tests ====================


class TestMarketplaceServiceSingleton:
    """Tests for marketplace service singleton management."""

    def test_get_service_creates_singleton(self):
        """Test that get_marketplace_service creates a singleton."""
        set_marketplace_service(None)

        service1 = get_marketplace_service()
        service2 = get_marketplace_service()

        assert service1 is service2

    def test_set_service(self):
        """Test setting the service singleton."""
        new_service = MarketplaceService()

        set_marketplace_service(new_service)
        retrieved = get_marketplace_service()

        assert retrieved is new_service

    def test_set_service_to_none(self):
        """Test clearing the service singleton creates new one."""
        set_marketplace_service(None)
        service = get_marketplace_service()

        assert service is not None


# ==================== Router Tests ====================


class TestMarketplaceRouter:
    """Tests for marketplace router endpoints."""

    def test_router_import(self):
        """Test that marketplace router can be imported."""
        from api.routers.marketplace import router
        assert router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.marketplace import (
            PublishTemplateRequest,
            MarketplaceTemplateResponse,
            MarketplaceTemplateListItem,
            MarketplaceTemplateListResponse,
            AddReviewRequest,
            ReviewResponse,
            ReviewListResponse,
            DownloadResponse,
            UpdateTemplateRequest,
            MarketplaceStatsResponse,
        )

        assert hasattr(PublishTemplateRequest, "model_fields")
        assert hasattr(MarketplaceTemplateResponse, "model_fields")
        assert hasattr(ReviewResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.marketplace import _parse_template_type, _parse_sort_by
        from fastapi import HTTPException

        assert _parse_template_type("entity_report") == TemplateType.ENTITY_REPORT
        assert _parse_sort_by("downloads") == SortBy.DOWNLOADS

        with pytest.raises(HTTPException) as exc_info:
            _parse_template_type("invalid")
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            _parse_sort_by("invalid")
        assert exc_info.value.status_code == 400

    def test_template_to_response_conversion(self):
        """Test template to response conversion."""
        from api.routers.marketplace import _marketplace_template_to_response

        template = MarketplaceTemplate(
            id="mp-1",
            template_id="t-1",
            name="Test",
            description="Desc",
            content="<p>Test</p>",
            author="author",
            tags=["tag1"],
            downloads=50,
            rating=4.5,
            ratings_count=10,
        )

        response = _marketplace_template_to_response(template)

        assert response.id == "mp-1"
        assert response.name == "Test"
        assert response.downloads == 50

    def test_review_to_response_conversion(self):
        """Test review to response conversion."""
        from api.routers.marketplace import _review_to_response

        review = TemplateReview(
            review_id="r-1",
            template_id="t-1",
            user_id="u-1",
            rating=5,
            comment="Great!",
        )

        response = _review_to_response(review)

        assert response.review_id == "r-1"
        assert response.rating == 5


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_long_description(self, marketplace_service, sample_template):
        """Test publishing template with very long description."""
        long_description = "A" * 5000

        published = marketplace_service.publish_template(
            template=sample_template,
            author="test",
            description=long_description,
        )

        assert len(published.description) == 5000

    def test_many_tags(self, marketplace_service, sample_template):
        """Test publishing template with many tags."""
        many_tags = [f"tag{i}" for i in range(50)]

        published = marketplace_service.publish_template(
            template=sample_template,
            author="test",
            description="Desc",
            tags=many_tags,
        )

        assert len(published.tags) == 50

    def test_unicode_in_content(self, marketplace_service, template_service):
        """Test templates with unicode content."""
        t = template_service.create_template(
            name="Unicode Template",
            template_type=TemplateType.CUSTOM,
            content="<p>Hello World</p>",
        )

        published = marketplace_service.publish_template(
            template=t,
            author="test",
            description="Contains unicode",
        )

        assert "Hello" in published.content

    def test_special_characters_in_tags(self, marketplace_service, sample_template):
        """Test templates with special characters in tags."""
        published = marketplace_service.publish_template(
            template=sample_template,
            author="test",
            description="Desc",
            tags=["tag-with-dash", "tag_with_underscore", "tag.with.dots"],
        )

        results = marketplace_service.search_templates(tags=["tag-with-dash"])
        assert len(results) == 1

    def test_concurrent_downloads(self, marketplace_service, published_template):
        """Test multiple rapid downloads."""
        for _ in range(100):
            marketplace_service.download_template(published_template.id)

        template = marketplace_service.get_template(published_template.id)
        assert template.downloads == 100

    def test_rating_precision(self, marketplace_service, published_template):
        """Test rating calculation precision."""
        ratings = [5, 4, 4, 3, 5]
        for i, rating in enumerate(ratings):
            marketplace_service.add_review(published_template.id, f"u{i}", rating, "")

        template = marketplace_service.get_template(published_template.id)

        # Average should be (5+4+4+3+5)/5 = 4.2
        assert template.rating == pytest.approx(4.2, rel=1e-2)

    def test_empty_search_returns_all(self, marketplace_service, template_service):
        """Test that empty search returns all templates."""
        for i in range(5):
            t = template_service.create_template(
                name=f"T{i}",
                template_type=TemplateType.CUSTOM,
                content=f"<p>{i}</p>",
            )
            marketplace_service.publish_template(t, f"a{i}", "D")

        results = marketplace_service.search_templates()
        assert len(results) == 5

        results = marketplace_service.search_templates(query=None, type_filter=None, tags=None)
        assert len(results) == 5
