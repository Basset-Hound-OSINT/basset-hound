"""
Phase 23: Saved Search Configurations Tests

Tests for the Saved Search Service and API Router.

This module provides comprehensive tests for:
- SavedSearchConfig creation and validation
- SavedSearch dataclass operations
- SavedSearchService CRUD operations
- Search execution with overrides
- Filtering and listing searches
- Favorites, recent, and popular searches
- Tag and category management
- API router endpoints
- Request/response model validation
"""

import pytest
from datetime import datetime, timedelta
from typing import Optional

# Service imports
from api.services.saved_search import (
    SavedSearchService,
    SavedSearchConfig,
    SavedSearch,
    SearchScope,
    SearchCategory,
    SearchListFilter,
    SearchExecutionResult,
    get_saved_search_service,
    set_saved_search_service,
    reset_saved_search_service,
)

# Router imports
from api.routers.saved_search import (
    router as saved_search_router,
    project_saved_search_router,
    CreateSavedSearchRequest,
    UpdateSavedSearchRequest,
    ExecuteSearchRequest,
    DuplicateSearchRequest,
    SavedSearchResponse,
    SavedSearchListResponse,
    ExecutionResultResponse,
    TagCountResponse,
    FavoriteToggleResponse,
    saved_search_to_response,
)


# ----- Test Fixtures -----

@pytest.fixture
def reset_service():
    """Reset the saved search service before and after tests."""
    reset_saved_search_service()
    yield
    reset_saved_search_service()


@pytest.fixture
def saved_search_service(reset_service):
    """Get a fresh saved search service instance."""
    return get_saved_search_service()


# ----- SearchScope Enum Tests -----

class TestSearchScope:
    """Test SearchScope enumeration."""

    def test_scope_values(self):
        """Test that all expected scope values exist."""
        assert SearchScope.GLOBAL.value == "global"
        assert SearchScope.PROJECT.value == "project"
        assert SearchScope.USER.value == "user"

    def test_scope_from_string(self):
        """Test creating scope from string value."""
        assert SearchScope("global") == SearchScope.GLOBAL
        assert SearchScope("project") == SearchScope.PROJECT
        assert SearchScope("user") == SearchScope.USER


# ----- SearchCategory Enum Tests -----

class TestSearchCategory:
    """Test SearchCategory enumeration."""

    def test_category_values(self):
        """Test that all expected category values exist."""
        assert SearchCategory.GENERAL.value == "general"
        assert SearchCategory.INVESTIGATION.value == "investigation"
        assert SearchCategory.MONITORING.value == "monitoring"
        assert SearchCategory.COMPLIANCE.value == "compliance"
        assert SearchCategory.RISK.value == "risk"
        assert SearchCategory.CUSTOM.value == "custom"

    def test_category_from_string(self):
        """Test creating category from string value."""
        assert SearchCategory("general") == SearchCategory.GENERAL
        assert SearchCategory("risk") == SearchCategory.RISK


# ----- SavedSearchConfig Tests -----

class TestSavedSearchConfig:
    """Test SavedSearchConfig dataclass."""

    def test_basic_config(self):
        """Test creating a basic config."""
        config = SavedSearchConfig(
            name="Test Search",
            query="test query",
            scope=SearchScope.GLOBAL,
        )
        assert config.name == "Test Search"
        assert config.query == "test query"
        assert config.scope == SearchScope.GLOBAL
        assert config.description == ""
        assert config.limit == 20
        assert config.fuzzy is True
        assert config.highlight is True
        assert config.tags == []
        assert config.category == SearchCategory.GENERAL

    def test_project_scoped_config(self):
        """Test project-scoped config requires project_id."""
        config = SavedSearchConfig(
            name="Project Search",
            query="project:query",
            scope=SearchScope.PROJECT,
            project_id="project-123",
        )
        assert config.project_id == "project-123"

    def test_project_scope_without_project_id_raises(self):
        """Test that project scope without project_id raises ValueError."""
        with pytest.raises(ValueError, match="Project ID required"):
            SavedSearchConfig(
                name="Test",
                query="test",
                scope=SearchScope.PROJECT,
            )

    def test_user_scope_without_user_id_raises(self):
        """Test that user scope without user_id raises ValueError."""
        with pytest.raises(ValueError, match="User ID required"):
            SavedSearchConfig(
                name="Test",
                query="test",
                scope=SearchScope.USER,
            )

    def test_empty_name_raises(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Search name is required"):
            SavedSearchConfig(
                name="",
                query="test",
                scope=SearchScope.GLOBAL,
            )

    def test_empty_query_raises(self):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query is required"):
            SavedSearchConfig(
                name="Test",
                query="",
                scope=SearchScope.GLOBAL,
            )

    def test_limit_validation(self):
        """Test that limit is clamped to valid range."""
        config = SavedSearchConfig(
            name="Test",
            query="test",
            scope=SearchScope.GLOBAL,
            limit=0,
        )
        assert config.limit == 1

        config = SavedSearchConfig(
            name="Test",
            query="test",
            scope=SearchScope.GLOBAL,
            limit=200,
        )
        assert config.limit == 100

    def test_full_config(self):
        """Test config with all fields."""
        config = SavedSearchConfig(
            name="Full Search",
            query="tag:risk AND type:person",
            description="Find risky persons",
            scope=SearchScope.PROJECT,
            project_id="proj-1",
            user_id="user-1",
            is_advanced=True,
            entity_types=["Person", "Organization"],
            fields=["core.name", "core.email"],
            limit=50,
            fuzzy=False,
            highlight=True,
            tags=["risk", "monitoring"],
            category=SearchCategory.RISK,
            is_favorite=True,
            icon="alert",
            color="#ff0000",
        )
        assert config.is_advanced is True
        assert config.entity_types == ["Person", "Organization"]
        assert config.is_favorite is True


# ----- SavedSearch Tests -----

class TestSavedSearch:
    """Test SavedSearch dataclass."""

    def test_create_saved_search(self):
        """Test creating a SavedSearch."""
        config = SavedSearchConfig(
            name="Test",
            query="test",
            scope=SearchScope.GLOBAL,
        )
        now = datetime.utcnow()
        search = SavedSearch(
            id="search-1",
            config=config,
            created_at=now,
            updated_at=now,
        )
        assert search.id == "search-1"
        assert search.config.name == "Test"
        assert search.execution_count == 0
        assert search.last_executed_at is None

    def test_to_dict(self):
        """Test converting to dictionary."""
        config = SavedSearchConfig(
            name="Test",
            query="test",
            scope=SearchScope.GLOBAL,
            tags=["tag1"],
        )
        now = datetime.utcnow()
        search = SavedSearch(
            id="search-1",
            config=config,
            created_at=now,
            updated_at=now,
            created_by="user-1",
        )
        d = search.to_dict()
        assert d["id"] == "search-1"
        assert d["name"] == "Test"
        assert d["query"] == "test"
        assert d["scope"] == "global"
        assert d["tags"] == ["tag1"]
        assert d["created_by"] == "user-1"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "search-2",
            "name": "From Dict",
            "query": "dict query",
            "scope": "project",
            "project_id": "proj-1",
            "tags": ["tag2"],
            "category": "risk",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T11:00:00",
            "execution_count": 5,
        }
        search = SavedSearch.from_dict(data)
        assert search.id == "search-2"
        assert search.config.name == "From Dict"
        assert search.config.scope == SearchScope.PROJECT
        assert search.config.category == SearchCategory.RISK
        assert search.execution_count == 5


# ----- SavedSearchService Tests -----

class TestSavedSearchService:
    """Test SavedSearchService operations."""

    @pytest.mark.asyncio
    async def test_create_search(self, saved_search_service):
        """Test creating a saved search."""
        config = SavedSearchConfig(
            name="Test Search",
            query="test query",
            scope=SearchScope.GLOBAL,
        )
        search_id = await saved_search_service.create_search(config)
        assert search_id is not None
        assert len(search_id) > 0

    @pytest.mark.asyncio
    async def test_get_search(self, saved_search_service):
        """Test retrieving a saved search."""
        config = SavedSearchConfig(
            name="Get Test",
            query="get query",
            scope=SearchScope.GLOBAL,
        )
        search_id = await saved_search_service.create_search(config)
        search = await saved_search_service.get_search(search_id)
        assert search is not None
        assert search.config.name == "Get Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_search(self, saved_search_service):
        """Test getting a search that doesn't exist."""
        search = await saved_search_service.get_search("nonexistent-id")
        assert search is None

    @pytest.mark.asyncio
    async def test_update_search(self, saved_search_service):
        """Test updating a saved search."""
        config = SavedSearchConfig(
            name="Original",
            query="original query",
            scope=SearchScope.GLOBAL,
        )
        search_id = await saved_search_service.create_search(config)

        updated = await saved_search_service.update_search(
            search_id,
            {"name": "Updated", "query": "updated query"}
        )
        assert updated is not None
        assert updated.config.name == "Updated"
        assert updated.config.query == "updated query"

    @pytest.mark.asyncio
    async def test_delete_search(self, saved_search_service):
        """Test deleting a saved search."""
        config = SavedSearchConfig(
            name="Delete Me",
            query="delete",
            scope=SearchScope.GLOBAL,
        )
        search_id = await saved_search_service.create_search(config)

        deleted = await saved_search_service.delete_search(search_id)
        assert deleted is True

        search = await saved_search_service.get_search(search_id)
        assert search is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, saved_search_service):
        """Test deleting a search that doesn't exist."""
        deleted = await saved_search_service.delete_search("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_searches(self, saved_search_service):
        """Test listing saved searches."""
        for i in range(3):
            config = SavedSearchConfig(
                name=f"Search {i}",
                query=f"query {i}",
                scope=SearchScope.GLOBAL,
            )
            await saved_search_service.create_search(config)

        searches, total = await saved_search_service.list_searches()
        assert total == 3
        assert len(searches) == 3

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, saved_search_service):
        """Test listing with pagination."""
        for i in range(10):
            config = SavedSearchConfig(
                name=f"Search {i}",
                query=f"query {i}",
                scope=SearchScope.GLOBAL,
            )
            await saved_search_service.create_search(config)

        searches, total = await saved_search_service.list_searches(
            offset=0, limit=5
        )
        assert total == 10
        assert len(searches) == 5

    @pytest.mark.asyncio
    async def test_list_with_project_filter(self, saved_search_service):
        """Test listing with project filter."""
        # Create global search
        await saved_search_service.create_search(
            SavedSearchConfig(name="Global", query="g", scope=SearchScope.GLOBAL)
        )
        # Create project search
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Project",
                query="p",
                scope=SearchScope.PROJECT,
                project_id="proj-1"
            )
        )

        filters = SearchListFilter(project_id="proj-1", include_global=True)
        searches, total = await saved_search_service.list_searches(filters)
        assert total == 2  # Both global and project

        filters = SearchListFilter(project_id="proj-1", include_global=False)
        searches, total = await saved_search_service.list_searches(filters)
        assert total == 1  # Only project

    @pytest.mark.asyncio
    async def test_list_with_category_filter(self, saved_search_service):
        """Test listing with category filter."""
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Risk 1",
                query="risk",
                scope=SearchScope.GLOBAL,
                category=SearchCategory.RISK
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="General 1",
                query="general",
                scope=SearchScope.GLOBAL,
                category=SearchCategory.GENERAL
            )
        )

        filters = SearchListFilter(category=SearchCategory.RISK)
        searches, total = await saved_search_service.list_searches(filters)
        assert total == 1
        assert searches[0].config.category == SearchCategory.RISK

    @pytest.mark.asyncio
    async def test_toggle_favorite(self, saved_search_service):
        """Test toggling favorite status."""
        config = SavedSearchConfig(
            name="Favorite Test",
            query="fav",
            scope=SearchScope.GLOBAL,
            is_favorite=False,
        )
        search_id = await saved_search_service.create_search(config)

        # Toggle to true
        new_status = await saved_search_service.toggle_favorite(search_id)
        assert new_status is True

        # Toggle back to false
        new_status = await saved_search_service.toggle_favorite(search_id)
        assert new_status is False

    @pytest.mark.asyncio
    async def test_duplicate_search(self, saved_search_service):
        """Test duplicating a saved search."""
        config = SavedSearchConfig(
            name="Original",
            query="original",
            scope=SearchScope.GLOBAL,
            tags=["tag1", "tag2"],
            is_favorite=True,
        )
        original_id = await saved_search_service.create_search(config)

        new_id = await saved_search_service.duplicate_search(original_id, "Copy")
        assert new_id is not None
        assert new_id != original_id

        copy = await saved_search_service.get_search(new_id)
        assert copy.config.name == "Copy"
        assert copy.config.query == "original"
        assert copy.config.tags == ["tag1", "tag2"]
        assert copy.config.is_favorite is False  # Reset

    @pytest.mark.asyncio
    async def test_get_favorites(self, saved_search_service):
        """Test getting favorite searches."""
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Fav 1",
                query="f1",
                scope=SearchScope.GLOBAL,
                is_favorite=True
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Not Fav",
                query="nf",
                scope=SearchScope.GLOBAL,
                is_favorite=False
            )
        )

        favorites = await saved_search_service.get_favorites()
        assert len(favorites) == 1
        assert favorites[0].config.name == "Fav 1"

    @pytest.mark.asyncio
    async def test_get_by_tags(self, saved_search_service):
        """Test getting searches by tags."""
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Tagged 1",
                query="t1",
                scope=SearchScope.GLOBAL,
                tags=["risk", "osint"]
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Tagged 2",
                query="t2",
                scope=SearchScope.GLOBAL,
                tags=["osint", "other"]
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="No Tags",
                query="nt",
                scope=SearchScope.GLOBAL
            )
        )

        searches = await saved_search_service.get_by_tags(["risk"])
        assert len(searches) == 1

        searches = await saved_search_service.get_by_tags(["osint"])
        assert len(searches) == 2

    @pytest.mark.asyncio
    async def test_get_all_tags(self, saved_search_service):
        """Test getting all tags with counts."""
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="T1",
                query="t1",
                scope=SearchScope.GLOBAL,
                tags=["a", "b"]
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="T2",
                query="t2",
                scope=SearchScope.GLOBAL,
                tags=["b", "c"]
            )
        )

        tags = await saved_search_service.get_all_tags()
        tag_dict = dict(tags)
        assert tag_dict["b"] == 2
        assert tag_dict["a"] == 1
        assert tag_dict["c"] == 1

    @pytest.mark.asyncio
    async def test_search_saved_searches(self, saved_search_service):
        """Test searching through saved searches."""
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Find High Risk",
                description="Finds high risk entities",
                query="tag:risk",
                scope=SearchScope.GLOBAL
            )
        )
        await saved_search_service.create_search(
            SavedSearchConfig(
                name="Other Search",
                query="other",
                scope=SearchScope.GLOBAL
            )
        )

        # Search by name
        results = await saved_search_service.search_saved_searches("risk")
        assert len(results) == 1
        assert results[0].config.name == "Find High Risk"

    @pytest.mark.asyncio
    async def test_clear_all(self, saved_search_service):
        """Test clearing all searches."""
        for i in range(5):
            await saved_search_service.create_search(
                SavedSearchConfig(
                    name=f"S{i}",
                    query=f"q{i}",
                    scope=SearchScope.GLOBAL
                )
            )

        count = saved_search_service.clear_all()
        assert count == 5

        searches, total = await saved_search_service.list_searches()
        assert total == 0


# ----- API Router Tests -----

class TestSavedSearchRouter:
    """Test saved search router configuration."""

    def test_router_exists(self):
        """Test that the router is configured."""
        assert saved_search_router is not None
        assert saved_search_router.prefix == "/saved-searches"
        assert "saved-searches" in saved_search_router.tags

    def test_project_router_exists(self):
        """Test that the project router is configured."""
        assert project_saved_search_router is not None
        assert "/saved-searches" in project_saved_search_router.prefix


# ----- Request Model Tests -----

class TestRequestModels:
    """Test request Pydantic models."""

    def test_create_request(self):
        """Test CreateSavedSearchRequest model."""
        request = CreateSavedSearchRequest(
            name="Test",
            query="test query",
            description="A test search",
            scope="project",
            project_id="proj-1",
        )
        assert request.name == "Test"
        assert request.query == "test query"
        assert request.scope == "project"
        assert request.limit == 20
        assert request.fuzzy is True

    def test_update_request_partial(self):
        """Test UpdateSavedSearchRequest with partial data."""
        request = UpdateSavedSearchRequest(name="New Name")
        assert request.name == "New Name"
        assert request.query is None
        assert request.limit is None

    def test_execute_request(self):
        """Test ExecuteSearchRequest model."""
        request = ExecuteSearchRequest(
            query="override query",
            limit=10,
            offset=5,
        )
        assert request.query == "override query"
        assert request.limit == 10
        assert request.offset == 5

    def test_duplicate_request(self):
        """Test DuplicateSearchRequest model."""
        request = DuplicateSearchRequest(new_name="Copy Name")
        assert request.new_name == "Copy Name"


# ----- Response Model Tests -----

class TestResponseModels:
    """Test response Pydantic models."""

    def test_saved_search_response(self):
        """Test SavedSearchResponse model."""
        response = SavedSearchResponse(
            id="search-1",
            name="Test",
            description="Test search",
            query="query",
            scope="global",
            is_advanced=False,
            limit=20,
            fuzzy=True,
            highlight=True,
            tags=["tag1"],
            category="general",
            is_favorite=False,
            created_at="2024-01-15T10:00:00",
            updated_at="2024-01-15T10:00:00",
            execution_count=0,
        )
        assert response.id == "search-1"
        assert response.tags == ["tag1"]

    def test_list_response(self):
        """Test SavedSearchListResponse model."""
        response = SavedSearchListResponse(
            searches=[],
            total=0,
            limit=50,
            offset=0,
        )
        assert response.total == 0

    def test_execution_result_response(self):
        """Test ExecutionResultResponse model."""
        response = ExecutionResultResponse(
            search_id="search-1",
            search_name="Test",
            results=[],
            total_count=0,
            execution_time_ms=10.5,
            executed_at="2024-01-15T10:00:00",
            query_used="test",
        )
        assert response.execution_time_ms == 10.5

    def test_tag_count_response(self):
        """Test TagCountResponse model."""
        response = TagCountResponse(
            tags=[{"tag": "risk", "count": 5}],
            total_unique_tags=1,
        )
        assert response.total_unique_tags == 1

    def test_favorite_toggle_response(self):
        """Test FavoriteToggleResponse model."""
        response = FavoriteToggleResponse(
            search_id="search-1",
            is_favorite=True,
        )
        assert response.is_favorite is True


# ----- Helper Function Tests -----

class TestHelperFunctions:
    """Test helper functions."""

    def test_saved_search_to_response(self):
        """Test saved_search_to_response function."""
        config = SavedSearchConfig(
            name="Test",
            query="query",
            scope=SearchScope.GLOBAL,
            tags=["tag1"],
        )
        now = datetime.utcnow()
        search = SavedSearch(
            id="search-1",
            config=config,
            created_at=now,
            updated_at=now,
        )

        response = saved_search_to_response(search)
        assert isinstance(response, SavedSearchResponse)
        assert response.id == "search-1"
        assert response.name == "Test"
        assert response.tags == ["tag1"]


# ----- Service Singleton Tests -----

class TestServiceSingleton:
    """Test service singleton behavior."""

    def test_get_service_returns_same_instance(self, reset_service):
        """Test that get_saved_search_service returns singleton."""
        service1 = get_saved_search_service()
        service2 = get_saved_search_service()
        assert service1 is service2

    def test_set_service(self, reset_service):
        """Test setting a custom service instance."""
        custom_service = SavedSearchService()
        set_saved_search_service(custom_service)
        service = get_saved_search_service()
        assert service is custom_service

    def test_reset_service(self, reset_service):
        """Test resetting the service."""
        service1 = get_saved_search_service()
        reset_saved_search_service()
        service2 = get_saved_search_service()
        assert service1 is not service2


# ----- Integration Tests -----

class TestServiceIntegration:
    """Integration tests for saved search service."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, saved_search_service):
        """Test full CRUD lifecycle."""
        # Create
        config = SavedSearchConfig(
            name="Lifecycle Test",
            query="lifecycle:query",
            scope=SearchScope.GLOBAL,
            tags=["lifecycle"],
        )
        search_id = await saved_search_service.create_search(config, "user-1")

        # Read
        search = await saved_search_service.get_search(search_id)
        assert search.created_by == "user-1"

        # Update
        await saved_search_service.update_search(
            search_id,
            {"name": "Updated Lifecycle", "tags": ["updated"]}
        )
        search = await saved_search_service.get_search(search_id)
        assert search.config.name == "Updated Lifecycle"
        assert search.config.tags == ["updated"]

        # Toggle favorite
        await saved_search_service.toggle_favorite(search_id)
        search = await saved_search_service.get_search(search_id)
        assert search.config.is_favorite is True

        # Duplicate
        copy_id = await saved_search_service.duplicate_search(search_id)
        copy = await saved_search_service.get_search(copy_id)
        assert copy.config.name == "Updated Lifecycle (Copy)"

        # Delete original
        deleted = await saved_search_service.delete_search(search_id)
        assert deleted is True

        # Verify original is gone
        search = await saved_search_service.get_search(search_id)
        assert search is None

        # Copy still exists
        copy = await saved_search_service.get_search(copy_id)
        assert copy is not None


# ----- Service Export Tests -----

class TestServiceExports:
    """Test that service exports are available."""

    def test_service_exports_from_services_module(self):
        """Test imports from api.services."""
        from api.services import (
            SavedSearchService,
            SavedSearchConfig,
            SavedSearch,
            SearchScope,
            SearchCategory,
            SearchListFilter,
            SearchExecutionResult,
            get_saved_search_service,
            set_saved_search_service,
            reset_saved_search_service,
        )
        assert SavedSearchService is not None
        assert SearchScope.GLOBAL.value == "global"


class TestRouterExports:
    """Test that router exports are available."""

    def test_router_exports_from_routers_module(self):
        """Test imports from api.routers."""
        from api.routers import (
            saved_search_router,
            project_saved_search_router,
        )
        assert saved_search_router is not None
        assert project_saved_search_router is not None
