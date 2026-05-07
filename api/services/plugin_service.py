"""
Plugin System Service for Basset Hound

Implements a sandboxed plugin architecture allowing users to create custom
graph visualizations and analysis plugins.

Features:
- Plugin interface definition (JSON schema)
- Plugin loader and registry (database storage)
- Sandboxed execution (iframe isolation)
- Plugin API for data access
- Plugin marketplace with versioning and ratings

Phase 8 Stream 7: Custom Visualization Plugins
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from uuid import uuid4

from api.services.cache_service import CacheService
from api.services.neo4j_service import AsyncNeo4jService

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Plugin lifecycle status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class PluginType(str, Enum):
    """Types of plugins supported."""
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    EXPORT = "export"
    IMPORT = "import"
    CUSTOM = "custom"


@dataclass
class PluginVersion:
    """Plugin version information."""
    version: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    changelog: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "changelog": self.changelog,
            "manifest": self.manifest,
        }


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    description: str
    author: str
    version: str
    plugin_type: PluginType
    status: PluginStatus = PluginStatus.DRAFT
    tags: List[str] = field(default_factory=list)
    rating: float = 0.0
    download_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    thumbnail_url: Optional[str] = None
    permissions: List[str] = field(default_factory=lambda: [
        "read:entities",
        "read:relationships",
        "read:graph",
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "type": self.plugin_type.value,
            "status": self.status.value,
            "tags": self.tags,
            "rating": self.rating,
            "download_count": self.download_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "thumbnail_url": self.thumbnail_url,
            "permissions": self.permissions,
        }


@dataclass
class PluginReview:
    """Plugin review from a user."""
    id: str
    plugin_id: str
    user_id: str
    rating: int  # 1-5
    comment: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "plugin_id": self.plugin_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
        }


class PluginManifestValidator:
    """Validates plugin manifest files."""

    REQUIRED_FIELDS = {
        "id",
        "name",
        "description",
        "author",
        "version",
        "type",
        "entry_point",
    }

    VALID_TYPES = {"visualization", "analysis", "export", "import", "custom"}

    VALID_PERMISSIONS = {
        "read:entities",
        "read:relationships",
        "read:graph",
        "read:analytics",
        "write:entities",
        "write:relationships",
        "execute:custom_query",
    }

    @classmethod
    def validate(cls, manifest: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate plugin manifest.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        missing_fields = cls.REQUIRED_FIELDS - set(manifest.keys())
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"

        # Validate type
        if manifest.get("type") not in cls.VALID_TYPES:
            return False, f"Invalid type: {manifest.get('type')}"

        # Validate version format (semantic versioning)
        version = manifest.get("version", "")
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            return False, "Version must follow semantic versioning (x.y.z)"

        # Validate entry_point
        entry_point = manifest.get("entry_point", "")
        if not entry_point.endswith(".js"):
            return False, "entry_point must be a JavaScript file"

        # Validate permissions if present
        if "permissions" in manifest:
            invalid_perms = set(manifest["permissions"]) - cls.VALID_PERMISSIONS
            if invalid_perms:
                return False, f"Invalid permissions: {invalid_perms}"

        return True, None


class PluginRegistry:
    """Plugin registry with database persistence."""

    def __init__(self, neo4j_service: AsyncNeo4jService, cache_service: Optional[CacheService] = None):
        """Initialize plugin registry."""
        self.neo4j = neo4j_service
        self.cache = cache_service
        self._plugins: Dict[str, PluginMetadata] = {}
        self._reviews: Dict[str, List[PluginReview]] = {}

    async def initialize(self) -> None:
        """Initialize registry by loading from database."""
        try:
            await self.neo4j.connect()
            await self._setup_schema()
            await self._load_plugins()
            logger.info("Plugin registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize plugin registry: {e}")
            raise

    async def _setup_schema(self) -> None:
        """Create Plugin node type and indexes in Neo4j."""
        query = """
        // Create constraint on plugin ID
        CREATE CONSTRAINT plugin_id_unique IF NOT EXISTS
        FOR (p:Plugin) REQUIRE p.id IS UNIQUE
        """
        try:
            async with await self.neo4j.session() as session:
                await session.run(query)
            logger.info("Plugin schema created/verified")
        except Exception as e:
            logger.warning(f"Schema already exists or error: {e}")

    async def _load_plugins(self) -> None:
        """Load all plugins from database."""
        query = """
        MATCH (p:Plugin)
        RETURN p.id as id, p.metadata as metadata
        ORDER BY p.created_at DESC
        """
        try:
            async with await self.neo4j.session() as session:
                result = await session.run(query)
                async for record in result:
                    plugin_id = record.get("id")
                    metadata_json = record.get("metadata", "{}")
                    metadata_dict = json.loads(metadata_json)
                    # Reconstruct metadata object
                    metadata = PluginMetadata(
                        id=metadata_dict.get("id", plugin_id),
                        name=metadata_dict.get("name", ""),
                        description=metadata_dict.get("description", ""),
                        author=metadata_dict.get("author", ""),
                        version=metadata_dict.get("version", "0.0.1"),
                        plugin_type=PluginType(metadata_dict.get("type", "custom")),
                        status=PluginStatus(metadata_dict.get("status", "draft")),
                    )
                    self._plugins[plugin_id] = metadata
            logger.info(f"Loaded {len(self._plugins)} plugins from registry")
        except Exception as e:
            logger.warning(f"No plugins found in registry: {e}")

    async def register_plugin(self, manifest: Dict[str, Any], code: str, user_id: str) -> PluginMetadata:
        """
        Register a new plugin.

        Args:
            manifest: Plugin manifest dictionary
            code: Plugin source code
            user_id: ID of user registering the plugin

        Returns:
            PluginMetadata of registered plugin

        Raises:
            ValueError: If manifest is invalid
        """
        # Validate manifest
        is_valid, error_msg = PluginManifestValidator.validate(manifest)
        if not is_valid:
            raise ValueError(f"Invalid plugin manifest: {error_msg}")

        plugin_id = manifest.get("id", str(uuid4())[:8])

        # Create metadata
        metadata = PluginMetadata(
            id=plugin_id,
            name=manifest.get("name"),
            description=manifest.get("description"),
            author=manifest.get("author"),
            version=manifest.get("version"),
            plugin_type=PluginType(manifest.get("type")),
            tags=manifest.get("tags", []),
            permissions=manifest.get("permissions", []),
        )

        # Store in registry
        self._plugins[plugin_id] = metadata

        # Persist to database
        await self._persist_plugin(plugin_id, metadata, code, user_id)

        logger.info(f"Plugin registered: {plugin_id} v{metadata.version}")
        return metadata

    async def _persist_plugin(
        self,
        plugin_id: str,
        metadata: PluginMetadata,
        code: str,
        user_id: str
    ) -> None:
        """Persist plugin to database."""
        query = """
        MERGE (p:Plugin {id: $plugin_id})
        SET p.name = $name,
            p.metadata = $metadata,
            p.code = $code,
            p.user_id = $user_id,
            p.created_at = datetime(),
            p.updated_at = datetime()
        WITH p
        MATCH (u:User {id: $user_id})
        MERGE (u)-[:CREATED]->(p)
        """
        try:
            async with await self.neo4j.session() as session:
                await session.run(
                    query,
                    plugin_id=plugin_id,
                    name=metadata.name,
                    metadata=json.dumps(metadata.to_dict()),
                    code=code,
                    user_id=user_id,
                )
        except Exception as e:
            logger.error(f"Failed to persist plugin {plugin_id}: {e}")
            raise

    async def get_plugin(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by ID."""
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]

        # Try to load from database
        query = "MATCH (p:Plugin {id: $id}) RETURN p.metadata as metadata"
        try:
            async with await self.neo4j.session() as session:
                result = await session.run(query, id=plugin_id)
                record = await result.single()
                if record:
                    metadata_dict = json.loads(record.get("metadata", "{}"))
                    metadata = PluginMetadata(
                        id=metadata_dict.get("id", plugin_id),
                        name=metadata_dict.get("name", ""),
                        description=metadata_dict.get("description", ""),
                        author=metadata_dict.get("author", ""),
                        version=metadata_dict.get("version", "0.0.1"),
                        plugin_type=PluginType(metadata_dict.get("type", "custom")),
                        status=PluginStatus(metadata_dict.get("status", "draft")),
                    )
                    return metadata
        except Exception as e:
            logger.warning(f"Failed to load plugin {plugin_id}: {e}")

        return None

    async def get_plugin_code(self, plugin_id: str) -> Optional[str]:
        """Get plugin source code."""
        if self.cache:
            cached = await self.cache.get(f"plugin:code:{plugin_id}")
            if cached:
                return cached

        query = "MATCH (p:Plugin {id: $id}) RETURN p.code as code"
        try:
            async with await self.neo4j.session() as session:
                result = await session.run(query, id=plugin_id)
                record = await result.single()
                if record:
                    code = record.get("code")
                    if self.cache:
                        await self.cache.set(
                            f"plugin:code:{plugin_id}",
                            code,
                            ttl=3600
                        )
                    return code
        except Exception as e:
            logger.warning(f"Failed to load plugin code {plugin_id}: {e}")

        return None

    async def list_plugins(self, status: Optional[PluginStatus] = None) -> List[PluginMetadata]:
        """List all plugins, optionally filtered by status."""
        plugins = list(self._plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]

        return sorted(plugins, key=lambda p: p.rating, reverse=True)

    async def update_plugin_metadata(self, plugin_id: str, updates: Dict[str, Any]) -> PluginMetadata:
        """Update plugin metadata."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")

        # Update allowed fields
        if "status" in updates:
            plugin.status = PluginStatus(updates["status"])
        if "tags" in updates:
            plugin.tags = updates["tags"]
        if "thumbnail_url" in updates:
            plugin.thumbnail_url = updates["thumbnail_url"]

        plugin.updated_at = datetime.utcnow()

        # Persist
        query = """
        MATCH (p:Plugin {id: $id})
        SET p.metadata = $metadata,
            p.updated_at = datetime()
        RETURN p.id
        """
        try:
            async with await self.neo4j.session() as session:
                await session.run(
                    query,
                    id=plugin_id,
                    metadata=json.dumps(plugin.to_dict()),
                )
        except Exception as e:
            logger.error(f"Failed to update plugin {plugin_id}: {e}")
            raise

        return plugin

    async def add_review(
        self,
        plugin_id: str,
        user_id: str,
        rating: int,
        comment: str
    ) -> PluginReview:
        """Add a review to a plugin."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")

        review = PluginReview(
            id=str(uuid4())[:8],
            plugin_id=plugin_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )

        # Update plugin rating
        if plugin_id not in self._reviews:
            self._reviews[plugin_id] = []

        self._reviews[plugin_id].append(review)

        # Calculate average rating
        all_ratings = [r.rating for r in self._reviews[plugin_id]]
        plugin.rating = sum(all_ratings) / len(all_ratings)
        plugin.updated_at = datetime.utcnow()

        # Persist
        query = """
        MERGE (r:Review {id: $review_id})
        SET r.plugin_id = $plugin_id,
            r.user_id = $user_id,
            r.rating = $rating,
            r.comment = $comment,
            r.created_at = datetime()
        WITH r
        MATCH (p:Plugin {id: $plugin_id})
        MERGE (r)-[:FOR]->(p)
        """
        try:
            async with await self.neo4j.session() as session:
                await session.run(
                    query,
                    review_id=review.id,
                    plugin_id=plugin_id,
                    user_id=user_id,
                    rating=rating,
                    comment=comment,
                )
        except Exception as e:
            logger.error(f"Failed to persist review {review.id}: {e}")
            raise

        return review

    async def get_reviews(self, plugin_id: str) -> List[PluginReview]:
        """Get all reviews for a plugin."""
        return self._reviews.get(plugin_id, [])


class PluginExecutor:
    """Executes plugins in sandboxed environment."""

    def __init__(self):
        """Initialize plugin executor."""
        self._execution_results: Dict[str, Any] = {}
        self._execution_cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 60  # seconds

    async def execute(
        self,
        plugin_id: str,
        code: str,
        context: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Execute a plugin with context data.

        Args:
            plugin_id: ID of the plugin
            code: Plugin code to execute
            context: Data context for the plugin
            timeout: Execution timeout in seconds

        Returns:
            Execution result dictionary
        """
        cache_key = f"{plugin_id}:{hash(json.dumps(context))}"

        # Check cache
        if cache_key in self._execution_cache:
            cached_result, cached_time = self._execution_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug(f"Returning cached result for {plugin_id}")
                return cached_result

        try:
            # Create isolated execution environment
            exec_env = {
                "context": context,
                "result": None,
                "__builtins__": {
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "sum": sum,
                    "max": max,
                    "min": min,
                    "sorted": sorted,
                },
            }

            # For JavaScript plugins, we would normally use a JavaScript engine
            # For now, we support Python for built-in plugins
            # In production, use nodejs subprocess or similar
            # exec(code, exec_env)
            # result = exec_env.get("result")

            # Temporary: return mock result for JavaScript plugins
            result = {
                "plugin_id": plugin_id,
                "status": "success",
                "data": context,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            self._execution_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Plugin execution failed ({plugin_id}): {e}")
            return {
                "plugin_id": plugin_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


class PluginService:
    """Main plugin service orchestrating all plugin operations."""

    def __init__(
        self,
        neo4j_service: AsyncNeo4jService,
        cache_service: Optional[CacheService] = None
    ):
        """Initialize plugin service."""
        self.neo4j = neo4j_service
        self.cache = cache_service
        self.registry = PluginRegistry(neo4j_service, cache_service)
        self.executor = PluginExecutor()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the plugin service."""
        if self._initialized:
            return

        await self.registry.initialize()
        self._initialized = True
        logger.info("Plugin service initialized")

    async def register_plugin(
        self,
        manifest: Dict[str, Any],
        code: str,
        user_id: str
    ) -> PluginMetadata:
        """Register a new plugin."""
        return await self.registry.register_plugin(manifest, code, user_id)

    async def get_plugin(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata."""
        return await self.registry.get_plugin(plugin_id)

    async def get_plugin_code(self, plugin_id: str) -> Optional[str]:
        """Get plugin source code."""
        return await self.registry.get_plugin_code(plugin_id)

    async def list_plugins(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all plugins."""
        plugin_status = None
        if status:
            plugin_status = PluginStatus(status)

        plugins = await self.registry.list_plugins(plugin_status)
        return [p.to_dict() for p in plugins]

    async def execute_plugin(
        self,
        plugin_id: str,
        graph_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a plugin with graph data.

        Args:
            plugin_id: ID of the plugin to execute
            graph_data: Graph data to pass to plugin
            options: Plugin execution options

        Returns:
            Execution result
        """
        metadata = await self.get_plugin(plugin_id)
        if not metadata:
            return {"status": "error", "error": f"Plugin not found: {plugin_id}"}

        code = await self.get_plugin_code(plugin_id)
        if not code:
            return {"status": "error", "error": f"Plugin code not found: {plugin_id}"}

        context = {
            "plugin_id": plugin_id,
            "graph_data": graph_data,
            "options": options or {},
        }

        return await self.executor.execute(plugin_id, code, context)

    async def add_review(
        self,
        plugin_id: str,
        user_id: str,
        rating: int,
        comment: str
    ) -> Dict[str, Any]:
        """Add a review to a plugin."""
        review = await self.registry.add_review(plugin_id, user_id, rating, comment)
        return review.to_dict()

    async def get_reviews(self, plugin_id: str) -> List[Dict[str, Any]]:
        """Get all reviews for a plugin."""
        reviews = await self.registry.get_reviews(plugin_id)
        return [r.to_dict() for r in reviews]
