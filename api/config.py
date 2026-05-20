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
        default=500,
        description="Maximum Neo4j connection pool size. "
                    "Optimized for 1000+ concurrent connections with <1% timeout rate. "
                    "Set via NEO4J_MAX_CONNECTION_POOL_SIZE environment variable. "
                    "Recommended: 500 for production (supports 1000+ concurrent users). "
                    "CRITICAL FIX: Increased from 150 to 500 to handle chaos testing findings."
    )
    neo4j_connection_lifetime: int = Field(
        default=3600,
        description="Maximum Neo4j connection lifetime in seconds (1 hour default)"
    )
    neo4j_max_retry_time: int = Field(
        default=60,
        description="Neo4j maximum retry time in seconds for transient failures"
    )

    # Redis Connection Pool Settings (Phase 8: Connection Pool Optimization)
    redis_max_connections: int = Field(
        default=300,
        description="Maximum Redis connection pool size (default 300 for 1000+ concurrent). "
                    "CRITICAL FIX: Increased from 100 to 300 to handle chaos testing findings."
    )
    redis_socket_keepalive: bool = Field(
        default=True,
        description="Enable TCP keepalive for Redis connections to detect dead connections"
    )
    redis_health_check_interval: int = Field(
        default=30,
        description="Redis health check interval in seconds to maintain pool health"
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

    # Security Settings (JWT Authentication - Phase 8)
    secret_key: str = Field(
        default="development-secret-key-change-in-production",
        description="Secret key for JWT token signing and validation. "
                    "CRITICAL: Must be changed in production. "
                    "Set via JWT_SECRET_KEY environment variable."
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="JWT access token expiration time in minutes. "
                    "Set via JWT_ACCESS_TOKEN_EXPIRE_MINUTES environment variable."
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="JWT refresh token expiration time in days. "
                    "Set via JWT_REFRESH_TOKEN_EXPIRE_DAYS environment variable."
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm. Supported: HS256 (HMAC-SHA256). "
                    "Set via JWT_ALGORITHM environment variable."
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

    # Basset Verify Integration Settings (Phase 4.1)
    basset_verify_url: str = Field(
        default="http://localhost:8001",
        description="Base URL for basset-verify microservice"
    )
    basset_verify_timeout: float = Field(
        default=10.0,
        description="Request timeout for basset-verify in seconds"
    )
    basset_verify_enabled: bool = Field(
        default=True,
        description="Enable/disable basset-verify integration"
    )

    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds. Set via REQUEST_TIMEOUT environment variable."
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

    # ML Analytics Feature Flag (Phase 8, Stream 5)
    enable_ml_analytics: bool = Field(
        default=True,
        description="Enable/disable ML analytics features (feature engineering, duplicate detection, etc.)"
    )

    # MLAnalytics memory limits - ARCHIVED (2026-01-13)
    # These settings were for the ML analytics service which has been moved to
    # archive/out-of-scope-ml/ as it's out of scope for the storage layer.
    # Keeping these fields for backwards compatibility with existing .env files.
    ml_analytics_max_history: int = Field(
        default=10000,
        description="[ARCHIVED] Maximum query history size for ML analytics"
    )
    ml_analytics_max_tfidf_cache: int = Field(
        default=5000,
        description="[ARCHIVED] Maximum TF-IDF cache entries"
    )
    ml_analytics_max_entity_queries: int = Field(
        default=2000,
        description="[ARCHIVED] Maximum entity query associations to track"
    )
    ml_analytics_max_cooccurrence: int = Field(
        default=5000,
        description="[ARCHIVED] Maximum query co-occurrence entries"
    )

    # Database Dump Encryption Settings (Security Enhancement)
    dump_encryption_enabled: bool = Field(
        default=True,
        description="Enable AES-256 encryption for database dumps"
    )
    dump_encryption_key: Optional[str] = Field(
        default=None,
        description="Master encryption key for database dumps (base64-encoded 32 bytes). "
                    "If not set, a key will be generated from SECRET_KEY. "
                    "Set via DUMP_ENCRYPTION_KEY environment variable."
    )

    # WebSocket Configuration (Phase 8: Production Stability)
    websocket_heartbeat_interval: int = Field(
        default=30,
        description="WebSocket heartbeat/ping interval in seconds. Set via WEBSOCKET_HEARTBEAT_INTERVAL."
    )
    websocket_timeout: int = Field(
        default=60,
        description="WebSocket timeout for unresponsive connections in seconds. Set via WEBSOCKET_TIMEOUT."
    )
    websocket_max_connections: Optional[int] = Field(
        default=None,
        description="Maximum concurrent WebSocket connections (None = unlimited). Set via WEBSOCKET_MAX_CONNECTIONS."
    )
    websocket_missed_pings_threshold: int = Field(
        default=3,
        description="Close connection after this many missed pings. Set via WEBSOCKET_MISSED_PINGS_THRESHOLD."
    )
    websocket_enable_metrics: bool = Field(
        default=True,
        description="Enable detailed WebSocket connection metrics. Set via WEBSOCKET_ENABLE_METRICS."
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
