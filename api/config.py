"""
Configuration settings for the Basset Hound FastAPI application.

Uses pydantic-settings for environment variable loading and validation.
Settings can be overridden via environment variables or .env file.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables can be set directly or via a .env file.
    All settings have sensible defaults for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="Basset Hound API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # CORS Settings - Use str type and convert in validators
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    cors_allow_methods: str = Field(
        default="*",
        description="Comma-separated allowed HTTP methods for CORS"
    )
    cors_allow_headers: str = Field(
        default="*",
        description="Comma-separated allowed headers for CORS"
    )

    # Neo4j Database Settings
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        default="neo4jbasset",
        description="Neo4j password"
    )
    neo4j_database: Optional[str] = Field(
        default=None,
        description="Neo4j database name (optional, uses default if not set)"
    )
    neo4j_connection_timeout: int = Field(
        default=30,
        description="Neo4j connection timeout in seconds"
    )
    neo4j_max_connection_pool_size: int = Field(
        default=50,
        description="Maximum Neo4j connection pool size"
    )

    # File Storage Settings
    projects_directory: str = Field(
        default="projects",
        description="Directory for project files"
    )
    max_upload_size_mb: int = Field(
        default=100,
        description="Maximum file upload size in megabytes"
    )

    # Data Configuration
    data_config_path: str = Field(
        default="data_config.yaml",
        description="Path to data configuration YAML file"
    )

    # Security Settings (for future auth implementation)
    secret_key: str = Field(
        default="development-secret-key-change-in-production",
        description="Secret key for JWT and session signing"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )

    # Cache Settings (Phase 4)
    cache_enabled: bool = Field(
        default=True,
        description="Enable/disable caching layer"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL (e.g., redis://localhost:6379/0). If not set, uses in-memory cache."
    )
    cache_ttl: int = Field(
        default=300,
        description="Default cache TTL in seconds"
    )
    cache_entity_ttl: int = Field(
        default=600,
        description="TTL for cached entities in seconds"
    )
    cache_query_ttl: int = Field(
        default=60,
        description="TTL for cached query results in seconds"
    )
    cache_relationship_ttl: int = Field(
        default=300,
        description="TTL for cached relationships in seconds"
    )
    cache_max_memory_entries: int = Field(
        default=1000,
        description="Maximum entries for in-memory cache (when Redis unavailable)"
    )
    cache_prefer_redis: bool = Field(
        default=True,
        description="Prefer Redis over in-memory cache when available"
    )

    # Memory Limit Settings for In-Memory Caches (Phase 12: Performance Optimization)
    # JobRunner memory limits
    job_runner_max_jobs: int = Field(
        default=1000,
        description="Maximum number of jobs to store in memory"
    )
    job_runner_max_results: int = Field(
        default=1000,
        description="Maximum number of job results to store in memory"
    )

    # ReportStorage memory limits
    report_storage_max_reports: int = Field(
        default=500,
        description="Maximum number of reports to store in memory"
    )
    report_storage_max_context_hashes: int = Field(
        default=1000,
        description="Maximum number of context hashes for deduplication"
    )

    # MarketplaceService memory limits
    marketplace_max_templates: int = Field(
        default=500,
        description="Maximum number of marketplace templates to store"
    )
    marketplace_max_reviews_per_template: int = Field(
        default=100,
        description="Maximum number of reviews per template"
    )

    # TemplateService memory limits
    template_service_max_templates: int = Field(
        default=200,
        description="Maximum number of templates to store in memory"
    )

    # MLAnalytics memory limits
    ml_analytics_max_history: int = Field(
        default=10000,
        description="Maximum query history size for ML analytics"
    )
    ml_analytics_max_tfidf_cache: int = Field(
        default=5000,
        description="Maximum TF-IDF cache entries"
    )
    ml_analytics_max_entity_queries: int = Field(
        default=2000,
        description="Maximum entity query associations to track"
    )
    ml_analytics_max_cooccurrence: int = Field(
        default=5000,
        description="Maximum query co-occurrence entries"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def cors_allow_methods_list(self) -> List[str]:
        """Get CORS methods as a list."""
        return [method.strip() for method in self.cors_allow_methods.split(",")]

    @property
    def cors_allow_headers_list(self) -> List[str]:
        """Get CORS headers as a list."""
        return [header.strip() for header in self.cors_allow_headers.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
