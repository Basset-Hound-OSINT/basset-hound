"""
Basset Hound API - FastAPI Application Entry Point

This module creates and configures the FastAPI application for the
Basset Hound OSINT investigation platform.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import get_settings
from api.dependencies import (
    get_app_config,
    set_neo4j_handler,
    set_app_config,
)
from neo4j_handler import Neo4jHandler
from config_loader import load_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("basset_hound")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.

    Handles:
    - Neo4j connection initialization
    - Configuration loading
    - Schema setup
    - Graceful shutdown and resource cleanup
    """
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize Neo4j connection
    neo4j_handler = None
    try:
        logger.info(f"Connecting to Neo4j at {settings.neo4j_uri}...")
        neo4j_handler = Neo4jHandler()
        set_neo4j_handler(neo4j_handler)
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

    # Load and setup configuration
    try:
        logger.info(f"Loading configuration from {settings.data_config_path}")
        config = load_config(settings.data_config_path)
        set_app_config(config)
        neo4j_handler.setup_schema_from_config(config)
        logger.info("Configuration loaded and schema initialized")
    except Exception as e:
        logger.warning(f"Error loading configuration: {e}")
        set_app_config({"sections": []})

    # Ensure projects directory exists
    projects_dir = Path(settings.projects_directory)
    projects_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Projects directory: {projects_dir.absolute()}")

    logger.info(f"Application ready on port {settings.port}")

    yield  # Application is running

    # Shutdown
    logger.info("Shutting down application...")

    # Close Neo4j connection
    if neo4j_handler:
        logger.info("Closing Neo4j connection...")
        neo4j_handler.close()
        set_neo4j_handler(None)
        logger.info("Neo4j connection closed")

    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API for Basset Hound OSINT Investigation Platform. "
            "Manage projects, people profiles, relationships, and files "
            "for open-source intelligence investigations."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
    )

    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(
        request: Request, call_next: Callable
    ) -> Any:
        """Add X-Process-Time header to all responses."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Global exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions."""
        logger.warning(f"ValueError: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred",
                "error": str(exc) if settings.debug else None,
            },
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint.

        Returns the application status and version information.
        """
        from api.dependencies import get_neo4j_handler

        try:
            neo4j = get_neo4j_handler()
            db_status = "connected"
        except Exception:
            db_status = "disconnected"

        return {
            "status": "healthy",
            "version": settings.app_version,
            "database": db_status,
        }

    # API Root endpoint (moved to /api to avoid conflict with frontend)
    @app.get("/api", tags=["Root"])
    async def api_root():
        """
        API root endpoint.

        Returns basic API information and links to documentation.
        """
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
        }

    # API info endpoint
    @app.get("/api/info", tags=["Info"])
    async def api_info():
        """
        Get API information and configuration status.
        """
        try:
            config = get_app_config()
            sections_count = len(config.get("sections", []))
        except Exception:
            sections_count = 0

        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "configuration": {
                "sections_loaded": sections_count,
                "projects_directory": settings.projects_directory,
            },
        }

    # Include all API routers
    from api.routers import api_router
    from api.routers.relationships import project_relationships_router
    from api.routers.files import file_serve_router
    from api.routers.reports import report_serve_router

    # Main API router with all sub-routers
    app.include_router(api_router, prefix="/api/v1")

    # Additional standalone routers
    app.include_router(project_relationships_router, prefix="/api/v1")
    app.include_router(file_serve_router)
    app.include_router(report_serve_router)

    # Include Frontend routers (migrated from Flask)
    from api.routers.frontend import router as frontend_router
    from api.routers.frontend_profiles import router as frontend_profiles_router
    from api.routers.frontend_reports import router as frontend_reports_router

    # Frontend routes - these serve HTML templates and handle form submissions
    app.include_router(frontend_router)
    app.include_router(frontend_profiles_router)
    app.include_router(frontend_reports_router)

    # Mount static files directory
    # This serves CSS, JS, images, etc. from /static/*
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Mounted static files from {static_dir}")

    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
