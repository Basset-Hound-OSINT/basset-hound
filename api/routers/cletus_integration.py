"""
Router for Cletus news aggregation integration.

Provides endpoints for:
- Health status of Cletus connection
- Listing available events from Cletus
- Ingesting events into the project graph
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.dependencies import get_neo4j_handler
from api.clients.cletus_client import get_cletus_client
from api.services.cletus_ingestion import CletusIngestionService

logger = logging.getLogger("basset_hound.routers.cletus_integration")

router = APIRouter(
    prefix="/api/v1/cletus",
    tags=["cletus"],
    responses={
        503: {"description": "Cletus service unavailable"},
        500: {"description": "Internal server error"},
    },
)


class CletusStatusResponse(BaseModel):
    """Response model for Cletus status check."""
    status: str
    message: str


class CletusEventListResponse(BaseModel):
    """Response model for event list."""
    success: bool
    total: int
    events: list = []


class CletusIngestionResponse(BaseModel):
    """Response model for ingestion results."""
    success: bool
    message: str
    total: int
    created: int
    errors: list = []


@router.get("/status", response_model=CletusStatusResponse, summary="Check Cletus availability")
async def cletus_status():
    """
    Check if Cletus is running and responding.

    Returns:
        Current status of the Cletus service (available, unavailable, unhealthy).
    """
    logger.debug("Checking Cletus health status")

    async with get_cletus_client() as client:
        if not client:
            logger.warning("Failed to connect to Cletus")
            return CletusStatusResponse(
                status="unavailable",
                message="Cannot connect to Cletus service"
            )

        try:
            is_healthy = await client.health_check()
            if is_healthy:
                return CletusStatusResponse(
                    status="available",
                    message="Cletus is healthy and responding"
                )
            else:
                return CletusStatusResponse(
                    status="unhealthy",
                    message="Cletus is responding but unhealthy"
                )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return CletusStatusResponse(
                status="unavailable",
                message=str(e)
            )


@router.get("/stats", summary="Get Cletus event statistics")
async def cletus_stats():
    """
    Get summary statistics about events in Cletus.

    Returns:
        Statistics including total events, by category, by status, etc.
    """
    logger.debug("Fetching Cletus statistics")

    async with get_cletus_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cletus unavailable"
            )

        try:
            stats = await client.get_event_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to fetch stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/events", response_model=CletusEventListResponse, summary="List available events")
async def list_events(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status (active, dormant, closed)"),
    severity: Optional[str] = Query(None, description="Filter by severity level")
):
    """
    List available event timelines from Cletus.

    Args:
        category: Optional category filter.
        status: Optional status filter (active, dormant, closed).
        severity: Optional severity filter.

    Returns:
        List of event timelines available in Cletus.
    """
    logger.debug(f"Listing events with filters: category={category}, status={status}")

    async with get_cletus_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cletus unavailable"
            )

        try:
            events = await client.list_events(
                category=category,
                status=status,
                severity=severity
            )
            return CletusEventListResponse(
                success=True,
                total=len(events),
                events=events
            )
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/events/search", response_model=CletusEventListResponse, summary="Search events")
async def search_events(
    q: str = Query(..., description="Search query")
):
    """
    Search events by title/summary.

    Args:
        q: Search query string.

    Returns:
        List of matching event timelines.
    """
    logger.debug(f"Searching events: {q}")

    async with get_cletus_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cletus unavailable"
            )

        try:
            events = await client.search_events(q)
            return CletusEventListResponse(
                success=True,
                total=len(events),
                events=events
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/events/{event_id}", summary="Get event details")
async def get_event(event_id: str):
    """
    Get a specific event timeline by ID.

    Args:
        event_id: The Cletus event ID.

    Returns:
        Full event timeline with all entries.
    """
    logger.debug(f"Fetching event: {event_id}")

    async with get_cletus_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cletus unavailable"
            )

        try:
            event = await client.get_event(event_id)
            return {
                "success": True,
                "event": event
            }
        except Exception as e:
            logger.error(f"Failed to fetch event {event_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.post("/ingest", response_model=CletusIngestionResponse, summary="Ingest all events")
async def ingest_all_events(
    project_safe_name: str = Query(..., description="Target project safe name"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Pull all events from Cletus and ingest them into a project.

    Creates entities for events, categories, and organizations,
    establishing relationships between them.

    Args:
        project_safe_name: URL-safe name of the target project.

    Returns:
        Ingestion results with total events, created count, and errors.
    """
    logger.info(f"Starting full ingestion for project: {project_safe_name}")

    try:
        ingestion = CletusIngestionService(neo4j_handler, project_safe_name)
        results = await ingestion.ingest_all_events()

        if results.get("success"):
            return CletusIngestionResponse(
                success=True,
                message=f"Successfully ingested {results['created']}/{results['total']} events",
                total=results["total"],
                created=results["created"],
                errors=results.get("errors", [])
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=results.get("error", "Ingestion failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/ingest/{event_id}", summary="Ingest specific event")
async def ingest_event(
    event_id: str,
    project_safe_name: str = Query(..., description="Target project safe name"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Ingest a specific event by ID from Cletus.

    Args:
        event_id: The Cletus event ID to ingest.
        project_safe_name: URL-safe name of the target project.

    Returns:
        Created entity ID and source event ID.
    """
    logger.info(f"Ingesting specific event {event_id} into project {project_safe_name}")

    try:
        ingestion = CletusIngestionService(neo4j_handler, project_safe_name)
        entity_id = await ingestion.ingest_event_by_id(event_id)

        return {
            "success": True,
            "message": f"Event {event_id} ingested successfully",
            "entity_id": entity_id,
            "event_id": event_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
