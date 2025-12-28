"""
Search Analytics Router for Basset Hound OSINT Platform.

DEPRECATED: This module is deprecated. Use analytics_v2 instead.

This module now re-exports from analytics_v2 for backward compatibility.
All new development should use the analytics_v2 module directly.

The v2 analytics router provides more comprehensive endpoints including:
- Recording search events with more metadata
- Analytics summaries (global and per-project)
- Top queries and zero-result queries
- Slow query detection
- Time-based search analysis
- Popular fields tracking
- Query stats and suggestions
- Analytics export and cleanup
"""

import warnings

# Emit deprecation warning when this module is imported
warnings.warn(
    "The analytics router is deprecated. Use analytics_v2 instead. "
    "Import from api.routers.analytics_v2 for the latest analytics endpoints.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from analytics_v2 for backward compatibility
from .analytics_v2 import (
    router,
    project_router as project_analytics_router,
    # Request/Response models
    RecordSearchRequest,
    RecordSearchResponse,
    QueryStatsResponse,
    TopQueriesResponse,
    SearchEventResponse,
    SlowQueriesResponse,
    SearchesByTimeResponse,
    PopularFieldsResponse,
    RelatedQueriesResponse,
    SuggestionsResponse,
    ClearAnalyticsResponse,
    AnalyticsSummaryResponse,
    # Helper functions
    get_analytics,
)

__all__ = [
    "router",
    "project_analytics_router",
    "RecordSearchRequest",
    "RecordSearchResponse",
    "QueryStatsResponse",
    "TopQueriesResponse",
    "SearchEventResponse",
    "SlowQueriesResponse",
    "SearchesByTimeResponse",
    "PopularFieldsResponse",
    "RelatedQueriesResponse",
    "SuggestionsResponse",
    "ClearAnalyticsResponse",
    "AnalyticsSummaryResponse",
    "get_analytics",
]
