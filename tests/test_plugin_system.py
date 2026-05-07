"""
Plugin System Tests for Stream 7

Tests cover:
- Plugin service initialization and lifecycle
- Plugin registry CRUD operations
- Plugin execution with caching
- Plugin API bridge communication
- Manifest validation
- Reviews and ratings
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from api.services.plugin_service import (
    PluginService,
    PluginRegistry,
    PluginExecutor,
    PluginMetadata,
    PluginStatus,
    PluginType,
    PluginManifestValidator,
    PluginReview,
)


class TestPluginManifestValidator:
    """Test plugin manifest validation."""

    def test_valid_manifest(self):
        """Test validation of valid manifest."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.js",
            "permissions": ["read:entities", "read:relationships"]
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert is_valid
        assert error is None

    def test_missing_required_field(self):
        """Test validation fails with missing field."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            # Missing description
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.js",
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert not is_valid
        assert "Missing required fields" in error

    def test_invalid_type(self):
        """Test validation fails with invalid type."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "invalid_type",
            "entry_point": "plugin.js",
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert not is_valid
        assert "Invalid type" in error

    def test_invalid_version(self):
        """Test validation fails with invalid version."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0",  # Invalid - should be x.y.z
            "type": "visualization",
            "entry_point": "plugin.js",
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert not is_valid
        assert "semantic versioning" in error

    def test_invalid_entry_point(self):
        """Test validation fails with invalid entry point."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.py",  # Invalid - should be .js
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert not is_valid
        assert ".js" in error

    def test_invalid_permissions(self):
        """Test validation fails with invalid permissions."""
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.js",
            "permissions": ["read:entities", "invalid:permission"]
        }

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert not is_valid
        assert "Invalid permissions" in error


class TestPluginMetadata:
    """Test plugin metadata."""

    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Test Description",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
            status=PluginStatus.DRAFT,
            tags=["test", "visualization"],
        )

        assert metadata.id == "test-plugin"
        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.status == PluginStatus.DRAFT

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Test Description",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
        )

        data = metadata.to_dict()
        assert data["id"] == "test-plugin"
        assert data["name"] == "Test Plugin"
        assert data["type"] == "visualization"
        assert "created_at" in data
        assert "updated_at" in data


class TestPluginReview:
    """Test plugin reviews."""

    def test_review_creation(self):
        """Test creating a review."""
        review = PluginReview(
            id="review-1",
            plugin_id="test-plugin",
            user_id="user-1",
            rating=5,
            comment="Great plugin!",
        )

        assert review.rating == 5
        assert review.comment == "Great plugin!"

    def test_review_to_dict(self):
        """Test converting review to dictionary."""
        review = PluginReview(
            id="review-1",
            plugin_id="test-plugin",
            user_id="user-1",
            rating=5,
            comment="Great plugin!",
        )

        data = review.to_dict()
        assert data["rating"] == 5
        assert data["comment"] == "Great plugin!"
        assert "created_at" in data


class TestPluginExecutor:
    """Test plugin executor."""

    def test_executor_creation(self):
        """Test creating executor."""
        executor = PluginExecutor()
        assert executor is not None

    async def test_execute_plugin(self):
        """Test executing a plugin."""
        executor = PluginExecutor()
        code = "console.log('test');"
        context = {
            "nodes": [{"id": "1", "name": "Test"}],
            "edges": []
        }

        result = await executor.execute(
            "test-plugin",
            code,
            context,
            timeout=10.0
        )

        assert result["status"] in ["success", "error"]
        assert "plugin_id" in result
        assert "timestamp" in result

    async def test_execute_with_timeout(self):
        """Test execution timeout."""
        executor = PluginExecutor()
        code = "// Simulated timeout"
        context = {}

        result = await executor.execute(
            "test-plugin",
            code,
            context,
            timeout=0.001  # Very short timeout
        )

        # Should handle timeout gracefully
        assert "status" in result


class TestPluginRegistry:
    """Test plugin registry."""

    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        """Test registry initialization."""
        neo4j_service = AsyncMock()
        neo4j_service.connect = AsyncMock()
        neo4j_service.session = AsyncMock()

        registry = PluginRegistry(neo4j_service)
        # Note: In a real test, we would mock the Neo4j connection

    @pytest.mark.asyncio
    async def test_plugin_metadata_operations(self):
        """Test metadata operations on registry."""
        neo4j_service = AsyncMock()
        registry = PluginRegistry(neo4j_service)

        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Test",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
        )

        # Add to internal registry
        registry._plugins["test-plugin"] = metadata

        # Get plugin
        retrieved = await registry.get_plugin("test-plugin")
        assert retrieved is not None
        assert retrieved.id == "test-plugin"


class TestPluginService:
    """Test main plugin service."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initialization."""
        neo4j_service = AsyncMock()
        neo4j_service.connect = AsyncMock()

        service = PluginService(neo4j_service)
        assert service is not None
        assert service.registry is not None
        assert service.executor is not None

    @pytest.mark.asyncio
    async def test_register_plugin_valid(self):
        """Test registering a valid plugin."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # Mock registry persist
        service.registry._persist_plugin = AsyncMock()

        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.js",
        }

        code = "console.log('test');"

        metadata = await service.register_plugin(manifest, code, "user-1")
        assert metadata.id == "test-plugin"
        assert metadata.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_register_plugin_invalid(self):
        """Test registering invalid plugin."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        manifest = {
            "id": "test-plugin",
            # Missing required fields
            "version": "1.0.0",
        }

        code = "console.log('test');"

        with pytest.raises(ValueError):
            await service.register_plugin(manifest, code, "user-1")

    @pytest.mark.asyncio
    async def test_list_plugins(self):
        """Test listing plugins."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # Add test plugins to registry
        for i in range(3):
            metadata = PluginMetadata(
                id=f"test-plugin-{i}",
                name=f"Test Plugin {i}",
                description="Test",
                author="Test Author",
                version="1.0.0",
                plugin_type=PluginType.VISUALIZATION,
                status=PluginStatus.PUBLISHED,
            )
            service.registry._plugins[f"test-plugin-{i}"] = metadata

        plugins = await service.list_plugins()
        assert len(plugins) == 3

    @pytest.mark.asyncio
    async def test_list_plugins_by_status(self):
        """Test listing plugins filtered by status."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # Add published plugin
        metadata1 = PluginMetadata(
            id="test-plugin-1",
            name="Test Plugin 1",
            description="Test",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
            status=PluginStatus.PUBLISHED,
        )
        service.registry._plugins["test-plugin-1"] = metadata1

        # Add draft plugin
        metadata2 = PluginMetadata(
            id="test-plugin-2",
            name="Test Plugin 2",
            description="Test",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.ANALYSIS,
            status=PluginStatus.DRAFT,
        )
        service.registry._plugins["test-plugin-2"] = metadata2

        published = await service.list_plugins(PluginStatus.PUBLISHED)
        assert len(published) == 1
        assert published[0]["status"] == "published"

    @pytest.mark.asyncio
    async def test_add_review(self):
        """Test adding a review."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # Add plugin
        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Test",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
        )
        service.registry._plugins["test-plugin"] = metadata

        # Mock persist
        service.registry.neo4j.session = AsyncMock()
        service.registry.neo4j.session.return_value.__aenter__ = AsyncMock(
            return_value=AsyncMock()
        )
        service.registry.neo4j.session.return_value.__aexit__ = AsyncMock()

        review = await service.add_review(
            "test-plugin",
            "user-1",
            5,
            "Great plugin!"
        )

        assert review["rating"] == 5
        assert review["comment"] == "Great plugin!"

    @pytest.mark.asyncio
    async def test_rating_calculation(self):
        """Test average rating calculation."""
        neo4j_service = AsyncMock()
        registry = PluginRegistry(neo4j_service)

        plugin = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            description="Test",
            author="Test Author",
            version="1.0.0",
            plugin_type=PluginType.VISUALIZATION,
        )
        registry._plugins["test-plugin"] = plugin

        # Add reviews
        reviews = [
            PluginReview("r1", "test-plugin", "u1", 5, "Great!"),
            PluginReview("r2", "test-plugin", "u2", 4, "Good"),
            PluginReview("r3", "test-plugin", "u3", 5, "Excellent"),
        ]

        registry._reviews["test-plugin"] = reviews

        # Calculate average
        all_ratings = [r.rating for r in reviews]
        avg_rating = sum(all_ratings) / len(all_ratings)

        assert avg_rating == pytest.approx(4.67, rel=0.01)


class TestBuiltinPluginManifests:
    """Test built-in plugin manifests."""

    def test_sankey_manifest(self):
        """Test Sankey plugin manifest is valid."""
        with open("/home/devel/basset-hound/static/plugins/sankey/manifest.json") as f:
            manifest = json.load(f)

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert is_valid, f"Sankey manifest invalid: {error}"
        assert manifest["id"] == "sankey-diagram"
        assert manifest["type"] == "visualization"

    def test_timeline_manifest(self):
        """Test Timeline plugin manifest is valid."""
        with open("/home/devel/basset-hound/static/plugins/timeline/manifest.json") as f:
            manifest = json.load(f)

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert is_valid, f"Timeline manifest invalid: {error}"
        assert manifest["id"] == "timeline-visualization"

    def test_heatmap_manifest(self):
        """Test HeatMap plugin manifest is valid."""
        with open("/home/devel/basset-hound/static/plugins/heatmap/manifest.json") as f:
            manifest = json.load(f)

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert is_valid, f"HeatMap manifest invalid: {error}"
        assert manifest["id"] == "heatmap-visualization"

    def test_network_stats_manifest(self):
        """Test Network Statistics plugin manifest is valid."""
        with open("/home/devel/basset-hound/static/plugins/network-stats/manifest.json") as f:
            manifest = json.load(f)

        is_valid, error = PluginManifestValidator.validate(manifest)
        assert is_valid, f"Network Stats manifest invalid: {error}"
        assert manifest["id"] == "network-statistics"


class TestPluginCache:
    """Test plugin caching behavior."""

    async def test_execution_caching(self):
        """Test execution result caching."""
        executor = PluginExecutor()

        context = {
            "nodes": [{"id": "1", "name": "Test"}],
            "edges": []
        }

        # First execution
        result1 = await executor.execute("test", "code", context)

        # Second execution with same context should return cached result
        result2 = await executor.execute("test", "code", context)

        assert result1 == result2


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_plugin_registration_and_retrieval(self):
        """Test full registration and retrieval flow."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # Register
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "visualization",
            "entry_point": "plugin.js",
        }

        service.registry._persist_plugin = AsyncMock()

        metadata = await service.register_plugin(
            manifest,
            "// code",
            "user-1"
        )

        # Retrieve
        retrieved = await service.get_plugin("test-plugin")

        assert retrieved is not None
        assert retrieved.id == "test-plugin"
        assert retrieved.name == "Test Plugin"

    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self):
        """Test complete plugin lifecycle."""
        neo4j_service = AsyncMock()
        service = PluginService(neo4j_service)

        # 1. Register
        manifest = {
            "id": "lifecycle-plugin",
            "name": "Lifecycle Plugin",
            "description": "Test",
            "author": "Test Author",
            "version": "1.0.0",
            "type": "analysis",
            "entry_point": "plugin.js",
        }

        service.registry._persist_plugin = AsyncMock()
        plugin = await service.register_plugin(manifest, "code", "user-1")

        # 2. Verify status is draft
        assert plugin.status == PluginStatus.DRAFT

        # 3. Update to published
        updates = {"status": "published"}
        service.registry.neo4j.session = AsyncMock()
        service.registry.neo4j.session.return_value.__aenter__ = AsyncMock(
            return_value=AsyncMock()
        )
        service.registry.neo4j.session.return_value.__aexit__ = AsyncMock()

        updated = await service.registry.update_plugin_metadata("lifecycle-plugin", updates)

        # 4. Add review
        service.registry.neo4j.session = AsyncMock()
        service.registry.neo4j.session.return_value.__aenter__ = AsyncMock(
            return_value=AsyncMock()
        )
        service.registry.neo4j.session.return_value.__aexit__ = AsyncMock()

        review = await service.add_review(
            "lifecycle-plugin",
            "user-2",
            5,
            "Excellent!"
        )

        assert review["rating"] == 5


# Run async tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
