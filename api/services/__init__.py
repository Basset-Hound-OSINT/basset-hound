"""
Basset Hound API Services

This module contains service classes for interacting with external systems
and databases. Services encapsulate business logic and data access patterns.
"""

from .neo4j_service import AsyncNeo4jService
from .auto_linker import AutoLinker, get_auto_linker
from .bulk_operations import (
    BulkOperationsService,
    BulkImportResult,
    BulkExportOptions,
)
from .timeline_service import (
    TimelineEvent,
    TimelineService,
    EventType,
    get_timeline_service,
    set_timeline_service,
)
from .search_service import (
    SearchService,
    SearchResult,
    SearchQuery,
    get_search_service,
    set_search_service,
)
from .audit_logger import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
    AuditPersistenceBackend,
    EntityType,
    InMemoryAuditBackend,
    get_audit_logger,
    set_audit_logger,
    initialize_audit_logger,
)
from .graph_visualization import (
    GraphVisualizationService,
    LayoutAlgorithm,
    ExportFormat,
    LayoutOptions,
    SubgraphExtractionOptions,
    ExportOptions,
    VisualizationGraph,
    VisualizationNode,
    VisualizationEdge,
    NodePriority,
    get_graph_visualization_service,
    set_graph_visualization_service,
)

# Timeline visualization service (Phase 17)
from .timeline_visualization import (
    TimelineVisualizationService,
    TimelineEvent,
    TimelineGranularity,
    TimelineEventType,
    ActivityHeatmapData,
    TemporalSnapshot,
    EntityEvolution,
    EntityVersion,
    PeriodComparison,
    PeriodStats,
    TimePeriod,
    GraphStats,
    get_timeline_visualization_service,
    set_timeline_visualization_service,
)

# Data import connectors (Phase 16)
from .data_import import (
    ImportConnector,
    ImportResult,
    ImportError as DataImportError,  # Renamed to avoid conflict with builtin
    ImportWarning,
    DataImportService,
    MaltegoConnector,
    SpiderFootConnector,
    TheHarvesterConnector,
    ShodanConnector,
    HIBPConnector,
    GenericCSVConnector,
    get_import_service,
    reset_import_service,
)

# Entity Type UI Service
from .entity_type_ui import (
    EntityTypeUIService,
    get_entity_type_ui_service,
    reset_entity_type_ui_service,
)

# Community Detection Service (Graph Analytics) - ARCHIVED: Out of scope for storage layer
# These services were moved to archive/out-of-scope-ml/ on 2026-01-13
# They implement intelligence analysis features and should be part of a future
# intelligence-analysis project, not the basset-hound storage layer.
#
# Archived files:
#   - community_detection.py
#   - influence_service.py
#   - ml_analytics.py
#   - temporal_patterns.py

# Similarity Service (Graph Analytics)
from .similarity_service import (
    SimilarityService,
    SimilarityMethod,
    SimilarityResult,
    EntitySimilarityReport,
    SimilarityConfig,
    PotentialLink,
    SimilarityAlgorithms,
    SimRankCalculator,
    RelationshipVectorEncoder,
    get_similarity_service,
    set_similarity_service,
    reset_similarity_service,
)

# Temporal Patterns Service (Graph Analytics) - ARCHIVED: See comment above

# Query Cache Service (Phase 20: Performance Optimization)
from .query_cache import (
    QueryCacheService,
    QueryType,
    CacheConfig,
    CacheEntry,
    CacheStats,
    cached_query,
    get_query_cache_service,
    initialize_query_cache,
    reset_query_cache_service,
)

# Import Mapping Service (Custom Field Mapping)
from .import_mapping import (
    ImportMappingService,
    ImportMappingConfig,
    FieldMapping,
    TransformationType,
    TransformationOptions,
    TransformationEngine,
    MappingValidationResult,
    MappingPreviewResult,
    get_import_mapping_service,
    reset_import_mapping_service,
)

# LLM Export Service (Phase 21: Import/Export Flexibility)
from .llm_export import (
    LLMExportService,
    LLMExportFormat,
    ExportContext,
    LLMExportConfig,
    LLMExportResult,
    get_llm_export_service,
    set_llm_export_service,
    reset_llm_export_service,
)

# Graph Format Converter (Phase 21: Import/Export Flexibility)
from .graph_format_converter import (
    GraphFormatConverter,
    GraphFormat,
    EdgeDirection,
    ConversionOptions,
    ConversionResult,
    ConversionWarning,
    FormatValidationResult,
    FormatDetectionResult,
    InternalNode,
    InternalEdge,
    InternalGraph,
    get_graph_format_converter,
    set_graph_format_converter,
    reset_graph_format_converter,
)

# Saved Search Service (Phase 23: Saved Search Configurations)
from .saved_search import (
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

# Webhook Service (Phase 24: Webhook Integrations)
from .webhook_service import (
    WebhookService,
    WebhookConfig,
    Webhook,
    WebhookEvent,
    WebhookDelivery,
    DeliveryStatus,
    RetryConfig,
    get_webhook_service,
    set_webhook_service,
    reset_webhook_service,
)

# Data Quality Service (Phase 25: Deduplication & Data Quality)
from .data_quality import (
    DataQualityService,
    DataSource,
    QualityConfig,
    QualityDimension,
    QualityScore,
    FieldQuality,
    DimensionScore,
    ProjectQualityReport,
    get_data_quality_service,
    set_data_quality_service,
    reset_data_quality_service,
)

# Deduplication Service (Phase 25: Deduplication & Data Quality)
from .deduplication import (
    DeduplicationService,
    DeduplicationConfig,
    DuplicateCandidate,
    MergeStrategy,
    MergePreview,
    MergeResult,
    DeduplicationReport,
    MatchType as DeduplicationMatchType,
    FieldConflictResolution,
    MatchResult,
    FieldConflict,
    get_deduplication_service,
    set_deduplication_service,
    reset_deduplication_service,
)

# Fuzzy matcher imports - gracefully handle if rapidfuzz not installed
try:
    from .fuzzy_matcher import (
        FuzzyMatcher,
        FuzzyMatch,
        MatchType,
        MatchStrategy,
        get_fuzzy_matcher,
        double_metaphone,
    )
    _fuzzy_matcher_available = True
except ImportError:
    _fuzzy_matcher_available = False
    FuzzyMatcher = None
    FuzzyMatch = None
    MatchType = None
    MatchStrategy = None
    get_fuzzy_matcher = None
    double_metaphone = None

__all__ = [
    "AsyncNeo4jService",
    "AutoLinker",
    "get_auto_linker",
    # Bulk operations exports
    "BulkOperationsService",
    "BulkImportResult",
    "BulkExportOptions",
    # Timeline service exports
    "TimelineEvent",
    "TimelineService",
    "EventType",
    "get_timeline_service",
    "set_timeline_service",
    # Fuzzy matcher exports
    "FuzzyMatcher",
    "FuzzyMatch",
    "MatchType",
    "MatchStrategy",
    "get_fuzzy_matcher",
    "double_metaphone",
    # Search service exports
    "SearchService",
    "SearchResult",
    "SearchQuery",
    "get_search_service",
    "set_search_service",
    # Audit logger exports
    "AuditAction",
    "AuditLogEntry",
    "AuditLogger",
    "AuditPersistenceBackend",
    "EntityType",
    "InMemoryAuditBackend",
    "get_audit_logger",
    "set_audit_logger",
    "initialize_audit_logger",
    # Graph visualization exports
    "GraphVisualizationService",
    "LayoutAlgorithm",
    "ExportFormat",
    "LayoutOptions",
    "SubgraphExtractionOptions",
    "ExportOptions",
    "VisualizationGraph",
    "VisualizationNode",
    "VisualizationEdge",
    "NodePriority",
    "get_graph_visualization_service",
    "set_graph_visualization_service",
    # Data import exports (Phase 16)
    "ImportConnector",
    "ImportResult",
    "DataImportError",
    "ImportWarning",
    "DataImportService",
    "MaltegoConnector",
    "SpiderFootConnector",
    "TheHarvesterConnector",
    "ShodanConnector",
    "HIBPConnector",
    "GenericCSVConnector",
    "get_import_service",
    "reset_import_service",
    # Timeline visualization exports (Phase 17)
    "TimelineVisualizationService",
    "TimelineGranularity",
    "TimelineEventType",
    "ActivityHeatmapData",
    "TemporalSnapshot",
    "EntityEvolution",
    "EntityVersion",
    "PeriodComparison",
    "PeriodStats",
    "TimePeriod",
    "GraphStats",
    "get_timeline_visualization_service",
    "set_timeline_visualization_service",
    # Entity Type UI Service exports
    "EntityTypeUIService",
    "get_entity_type_ui_service",
    "reset_entity_type_ui_service",
    # Community Detection Service exports (Graph Analytics) - ARCHIVED
    # Influence Propagation Service exports (Graph Analytics) - ARCHIVED
    # Similarity Service exports (Graph Analytics)
    "SimilarityService",
    "SimilarityMethod",
    "SimilarityResult",
    "EntitySimilarityReport",
    "SimilarityConfig",
    "PotentialLink",
    "SimilarityAlgorithms",
    "SimRankCalculator",
    "RelationshipVectorEncoder",
    "get_similarity_service",
    "set_similarity_service",
    "reset_similarity_service",
    # Temporal Patterns Service exports (Graph Analytics) - ARCHIVED
    # Query Cache Service exports (Phase 20)
    "QueryCacheService",
    "QueryType",
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    "cached_query",
    "get_query_cache_service",
    "initialize_query_cache",
    "reset_query_cache_service",
    # Import Mapping Service exports
    "ImportMappingService",
    "ImportMappingConfig",
    "FieldMapping",
    "TransformationType",
    "TransformationOptions",
    "TransformationEngine",
    "MappingValidationResult",
    "MappingPreviewResult",
    "get_import_mapping_service",
    "reset_import_mapping_service",
    # LLM Export Service exports (Phase 21)
    "LLMExportService",
    "LLMExportFormat",
    "ExportContext",
    "LLMExportConfig",
    "LLMExportResult",
    "get_llm_export_service",
    "set_llm_export_service",
    "reset_llm_export_service",
    # Graph Format Converter exports (Phase 21)
    "GraphFormatConverter",
    "GraphFormat",
    "EdgeDirection",
    "ConversionOptions",
    "ConversionResult",
    "ConversionWarning",
    "FormatValidationResult",
    "FormatDetectionResult",
    "InternalNode",
    "InternalEdge",
    "InternalGraph",
    "get_graph_format_converter",
    "set_graph_format_converter",
    "reset_graph_format_converter",
    # Saved Search Service exports (Phase 23)
    "SavedSearchService",
    "SavedSearchConfig",
    "SavedSearch",
    "SearchScope",
    "SearchCategory",
    "SearchListFilter",
    "SearchExecutionResult",
    "get_saved_search_service",
    "set_saved_search_service",
    "reset_saved_search_service",
    # Webhook Service exports (Phase 24)
    "WebhookService",
    "WebhookConfig",
    "Webhook",
    "WebhookEvent",
    "WebhookDelivery",
    "DeliveryStatus",
    "RetryConfig",
    "get_webhook_service",
    "set_webhook_service",
    "reset_webhook_service",
    # Data Quality Service exports (Phase 25)
    "DataQualityService",
    "DataSource",
    "QualityConfig",
    "QualityDimension",
    "QualityScore",
    "FieldQuality",
    "DimensionScore",
    "ProjectQualityReport",
    "get_data_quality_service",
    "set_data_quality_service",
    "reset_data_quality_service",
    # Deduplication Service exports (Phase 25)
    "DeduplicationService",
    "DeduplicationConfig",
    "DuplicateCandidate",
    "MergeStrategy",
    "MergePreview",
    "MergeResult",
    "DeduplicationReport",
    "DeduplicationMatchType",
    "FieldConflictResolution",
    "MatchResult",
    "FieldConflict",
    "get_deduplication_service",
    "set_deduplication_service",
    "reset_deduplication_service",
]
