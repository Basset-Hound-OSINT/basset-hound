"""
FastAPI Routers for Basset Hound OSINT Application.

This module provides RESTful API endpoints for managing:
- Projects: OSINT investigation projects
- Entities: People/persons being investigated
- Relationships: Tags and connections between entities
- Files: Document and media file management
- Reports: Investigation reports and exports
- Config: Application configuration
- Utils: Utility functions (crypto detection, validation, etc.)
- Analysis: Graph analysis tools (paths, centrality, clusters)
- Auto-Linker: Automatic entity linking and duplicate detection
- Cross-Project: Cross-project entity linking
- Bulk Operations: Batch import/export of entities
- Timeline: Timeline analysis for tracking relationship changes over time
- Crypto: Cryptocurrency ticker display and block explorer links
- Export: Report generation and export in PDF, HTML, and Markdown formats
- Search: Full-text search across entities
- Analytics: Search analytics tracking and reporting
- Templates: Custom report template management
- Schedules: Scheduled report generation management
- WebSocket: Real-time notifications via WebSocket connections
- Report Storage: Persistent storage for generated reports with version history
- Marketplace: Template marketplace for sharing and downloading community templates
- ML Analytics: Machine learning-based query suggestions and insights
- Jobs: Background job execution and management
- Audit: Change tracking for debugging and audit purposes
- Graph: Graph visualization API for D3.js, vis.js, and Cytoscape
- Visualization: Advanced graph visualization with layouts, exports, and statistics
- Import Data: Import data from OSINT tools (Maltego, SpiderFoot, TheHarvester, Shodan, HIBP)
- Timeline Visualization: Temporal graph visualization for entity and relationship evolution
- Entity Types: Entity type UI configuration, icons, colors, and form fields
- Graph Analytics: Advanced graph analytics (community detection, similarity, influence, temporal patterns)
- Saved Searches: Saved search configurations for reusable queries
- Webhooks: Webhook integrations for external notifications
- Data Quality: Entity data quality assessment and scoring
- Deduplication: Duplicate detection and resolution
"""

from fastapi import APIRouter

from .projects import router as projects_router
from .entities import router as entities_router
from .relationships import router as relationships_router, project_relationships_router
from .files import router as files_router, file_serve_router
from .reports import router as reports_router, report_serve_router
from .config import router as config_router
from .utils import router as utils_router
from .analysis import router as analysis_router
from .auto_linker import router as auto_linker_router
from .cross_project import router as cross_project_router, entity_router as cross_project_entity_router
from .bulk import router as bulk_router
from .timeline import router as timeline_router
from .crypto import router as crypto_router
from .export import router as export_router, entity_export_router, templates_router as export_templates_router
from .search import router as search_router, project_search_router
# Use analytics_v2 as the primary analytics module (analytics.py is deprecated and re-exports from analytics_v2)
from .analytics_v2 import router as analytics_router, project_router as project_analytics_router
from .templates import router as templates_router
# Use scheduler as the primary scheduling module (schedule.py is deprecated and re-exports from scheduler)
from .scheduler import router as scheduler_router
from .websocket import router as websocket_router
from api.websocket.suggestion_events import router as suggestion_ws_router
from .report_storage import router as report_storage_router
from .marketplace import router as marketplace_router
# ML Analytics router - ARCHIVED: Out of scope for storage layer (2026-01-13)
# The ML analytics service and router have been moved to archive/out-of-scope-ml/
# They implement intelligence analysis features and should be part of a future
# intelligence-analysis project, not the basset-hound storage layer.
# from .ml_analytics import router as ml_analytics_router
from .jobs import router as jobs_router, schedule_jobs_router
from .audit import router as audit_router, project_audit_router, entity_audit_router
from .graph import router as graph_router
from .visualization import router as visualization_router
from .import_data import router as import_data_router, formats_router as import_formats_router
from .timeline_visualization import router as timeline_visualization_router
from .entity_types import router as entity_types_router, project_entity_types_router
from .frontend_components import router as frontend_components_router
from .graph_analytics import router as graph_analytics_router
from .import_mapping import router as import_mapping_router
from .llm_export import router as llm_export_router
from .graph_format import router as graph_format_router
from .saved_search import router as saved_search_router, project_saved_search_router
from .webhooks import router as webhooks_router, project_webhooks_router
from .data_quality import router as data_quality_router, project_data_quality_router
from .deduplication import router as deduplication_router, project_dedup_router
from .verification import router as verification_router
from .osint import router as osint_router
from .suggestions import router as suggestions_router
from .integrations import router as integrations_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(projects_router)
api_router.include_router(entities_router)
api_router.include_router(relationships_router)
api_router.include_router(project_relationships_router)
api_router.include_router(files_router)
api_router.include_router(file_serve_router)
api_router.include_router(reports_router)
api_router.include_router(report_serve_router)
api_router.include_router(config_router)
api_router.include_router(utils_router)
api_router.include_router(analysis_router)
api_router.include_router(auto_linker_router)
api_router.include_router(cross_project_router)
api_router.include_router(cross_project_entity_router)
api_router.include_router(bulk_router)
api_router.include_router(timeline_router)
api_router.include_router(crypto_router)
api_router.include_router(export_router)
api_router.include_router(entity_export_router)
api_router.include_router(export_templates_router)
api_router.include_router(search_router)
api_router.include_router(project_search_router)
api_router.include_router(analytics_router)
api_router.include_router(project_analytics_router)
api_router.include_router(templates_router)
api_router.include_router(scheduler_router)
api_router.include_router(websocket_router)
api_router.include_router(suggestion_ws_router)  # Phase 45: Suggestion WebSocket events
api_router.include_router(report_storage_router)
api_router.include_router(marketplace_router)
# api_router.include_router(ml_analytics_router)  # ARCHIVED
api_router.include_router(jobs_router)
api_router.include_router(schedule_jobs_router)
api_router.include_router(audit_router)
api_router.include_router(project_audit_router)
api_router.include_router(entity_audit_router)
api_router.include_router(graph_router)
api_router.include_router(visualization_router)
api_router.include_router(import_data_router)
api_router.include_router(import_formats_router)
api_router.include_router(timeline_visualization_router)
api_router.include_router(entity_types_router)
api_router.include_router(project_entity_types_router)
api_router.include_router(frontend_components_router)
api_router.include_router(graph_analytics_router)
api_router.include_router(import_mapping_router)
api_router.include_router(llm_export_router)
api_router.include_router(graph_format_router)
api_router.include_router(saved_search_router)
api_router.include_router(project_saved_search_router)
api_router.include_router(webhooks_router)
api_router.include_router(project_webhooks_router)
api_router.include_router(data_quality_router)
api_router.include_router(project_data_quality_router)
api_router.include_router(deduplication_router)
api_router.include_router(project_dedup_router)
api_router.include_router(verification_router)
api_router.include_router(osint_router)
api_router.include_router(suggestions_router)
api_router.include_router(integrations_router)

__all__ = [
    "api_router",
    "projects_router",
    "entities_router",
    "relationships_router",
    "project_relationships_router",
    "files_router",
    "file_serve_router",
    "reports_router",
    "report_serve_router",
    "config_router",
    "utils_router",
    "analysis_router",
    "auto_linker_router",
    "cross_project_router",
    "cross_project_entity_router",
    "bulk_router",
    "timeline_router",
    "crypto_router",
    "export_router",
    "entity_export_router",
    "export_templates_router",
    "search_router",
    "project_search_router",
    "analytics_router",
    "project_analytics_router",
    "templates_router",
    "scheduler_router",
    "websocket_router",
    "report_storage_router",
    "marketplace_router",
    # "ml_analytics_router",  # ARCHIVED
    "jobs_router",
    "schedule_jobs_router",
    "audit_router",
    "project_audit_router",
    "entity_audit_router",
    "graph_router",
    "visualization_router",
    "import_data_router",
    "import_formats_router",
    "timeline_visualization_router",
    "entity_types_router",
    "project_entity_types_router",
    "frontend_components_router",
    "graph_analytics_router",
    "import_mapping_router",
    "llm_export_router",
    "graph_format_router",
    "saved_search_router",
    "project_saved_search_router",
    "webhooks_router",
    "project_webhooks_router",
    "data_quality_router",
    "project_data_quality_router",
    "deduplication_router",
    "project_dedup_router",
    "verification_router",
    "osint_router",
    "suggestions_router",
    "integrations_router",
]
