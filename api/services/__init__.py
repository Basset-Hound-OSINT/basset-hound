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
]
