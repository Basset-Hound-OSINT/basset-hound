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
from .analytics import router as analytics_router, project_analytics_router
from .templates import router as templates_router
from .schedule import router as schedule_router
from .websocket import router as websocket_router

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
api_router.include_router(schedule_router)
api_router.include_router(websocket_router)

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
    "schedule_router",
    "websocket_router",
]
