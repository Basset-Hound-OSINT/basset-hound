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
]
