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
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CollectorRegistry, REGISTRY

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import get_settings
from api.dependencies import (
    get_app_config,
    set_neo4j_handler,
    set_app_config,
    get_neo4j_handler,
)
from api.middleware.metrics import TimedMiddleware
from api.utils.logger import configure_logging, get_logger
from api.services.cache_service import initialize_cache
from neo4j_handler import Neo4jHandler
from config_loader import load_config


# Configure structured logging
configure_logging()

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = get_logger("basset_hound")


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
    logger.info("app_starting", app_name=settings.app_name, version=settings.app_version)

    # Initialize Neo4j connection
    neo4j_handler = None
    try:
        logger.info("neo4j_connecting", uri=settings.neo4j_uri)
        neo4j_handler = Neo4jHandler()
        set_neo4j_handler(neo4j_handler)
        logger.info("neo4j_connected")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

    # Load and setup configuration
    try:
        logger.info("config_loading", path=settings.data_config_path)
        config = load_config(settings.data_config_path)
        set_app_config(config)
        neo4j_handler.setup_schema_from_config(config)
        logger.info("config_loaded", sections=len(config.get("sections", [])))

        # Seed platforms (Phase 48: Dynamic Entity Architecture)
        try:
            from api.services.neo4j_service import AsyncNeo4jService
            async_service = AsyncNeo4jService()
            await async_service.connect()
            await async_service.ensure_platforms_seeded()
            await async_service.close()
            logger.info("Platforms seeded successfully")
        except Exception as e:
            logger.warning("platform_seeding_failed", error=str(e))

    except Exception as e:
        logger.warning("config_loading_failed", error=str(e))
        set_app_config({"sections": []})

    # Ensure projects directory exists
    projects_dir = Path(settings.projects_directory)
    projects_dir.mkdir(parents=True, exist_ok=True)
    logger.info("projects_directory_ready", path=str(projects_dir.absolute()))

    # Initialize cache service
    cache_service = None
    try:
        logger.info("cache_initializing")
        cache_service = await initialize_cache(
            redis_url=settings.redis_url if hasattr(settings, 'redis_url') else None,
            cache_enabled=True
        )
        logger.info("cache_initialized", backend=cache_service.backend_type.value)
    except Exception as e:
        logger.warning("cache_initialization_failed", error=str(e))

    logger.info("app_ready", host=settings.host, port=settings.port)

    yield  # Application is running

    # Shutdown
    logger.info("app_shutdown_starting")

    # Shutdown cache service
    if cache_service:
        logger.info("cache_shutdown")
        await cache_service.shutdown()
        logger.info("cache_shutdown_complete")

    # Close Neo4j connection
    if neo4j_handler:
        logger.info("neo4j_closing")
        neo4j_handler.close()
        set_neo4j_handler(None)
        logger.info("neo4j_closed")

    logger.info("app_shutdown_complete")


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

    # Add metrics middleware (must be added before other middleware)
    app.add_middleware(TimedMiddleware)

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

    # Application startup time for uptime calculation
    app_start_time = time.time()

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Enhanced health check endpoint.

        Returns detailed application status including service health,
        metrics, and uptime information.
        """
        uptime_seconds = int(time.time() - app_start_time)

        # Check Neo4j connectivity and latency
        neo4j_status = "disconnected"
        neo4j_latency = None
        try:
            neo4j_handler = get_neo4j_handler()
            if neo4j_handler:
                start = time.time()
                with neo4j_handler.driver.session() as session:
                    session.run("MATCH (n:Project) LIMIT 1")
                neo4j_latency = int((time.time() - start) * 1000)
                neo4j_status = "connected"
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")

        # Check Redis connectivity and latency
        redis_status = "disconnected"
        redis_latency = None
        try:
            import redis
            from api.config import get_settings

            redis_url = get_settings().redis_url
            r = redis.from_url(redis_url, decode_responses=True)
            start = time.time()
            r.ping()
            redis_latency = int((time.time() - start) * 1000)
            redis_status = "connected"
            r.close()
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")

        # Check Celery workers
        celery_status = "running"
        worker_count = 0
        try:
            from api.tasks import celery_app

            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            if active_workers:
                worker_count = len(active_workers)
            else:
                celery_status = "no_workers"
        except Exception as e:
            celery_status = "unavailable"
            logger.warning(f"Celery health check failed: {e}")

        # Get entity counts
        total_projects = 0
        total_entities = 0
        try:
            neo4j_handler = get_neo4j_handler()
            if neo4j_handler:
                with neo4j_handler.driver.session() as session:
                    project_result = session.run("MATCH (n:Project) RETURN count(n) as count")
                    total_projects = project_result.single()["count"]

                    entity_result = session.run(
                        "MATCH (n:Entity) RETURN count(n) as count"
                    )
                    total_entities = entity_result.single()["count"]
        except Exception as e:
            logger.warning(f"Entity count check failed: {e}")

        return {
            "status": "healthy",
            "version": settings.app_version,
            "services": {
                "neo4j": {
                    "status": neo4j_status,
                    "latency_ms": neo4j_latency,
                },
                "redis": {
                    "status": redis_status,
                    "latency_ms": redis_latency,
                },
                "celery": {
                    "status": celery_status,
                    "workers": worker_count,
                },
            },
            "metrics": {
                "total_projects": total_projects,
                "total_entities": total_entities,
            },
            "uptime_seconds": uptime_seconds,
        }

    # Metrics endpoint (Prometheus format)
    @app.get("/metrics", tags=["Metrics"])
    async def metrics():
        """
        Prometheus metrics endpoint.

        Returns metrics in Prometheus text exposition format.
        """
        return Response(
            content=generate_latest(REGISTRY),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

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
    from api.routers.reports_pdf import router as reports_pdf_router
    from api.routers.mcp import router as mcp_router

    # Main API router with all sub-routers
    app.include_router(api_router, prefix="/api/v1")

    # MCP router - mounted at /mcp for external service integration
    # This enables PalletAI and other orchestrators to discover and invoke tools
    # Integration direction: PalletAI -> Basset Hound (one-way)
    app.include_router(mcp_router)
    logger.info("MCP endpoints enabled at /mcp/*")

    # Additional standalone routers
    app.include_router(project_relationships_router, prefix="/api/v1")
    app.include_router(file_serve_router)
    app.include_router(report_serve_router)
    app.include_router(reports_pdf_router)
    logger.info("PDF report endpoints enabled at /api/v1/projects/*/reports/pdf/*")

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
