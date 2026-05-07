"""
PDF Report Generation Endpoints for LaTeX-based reporting.

Provides REST endpoints for generating and downloading PDF reports
for entities and investigations.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.dependencies import get_neo4j_handler
from api.services.latex_report_service import LatexReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["Reports PDF"])


@router.post("/{project_name}/reports/pdf/entity/{entity_id}")
async def generate_entity_pdf(
    project_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler),
) -> StreamingResponse:
    """
    Generate PDF report for a single entity.

    Args:
        project_name: Project identifier
        entity_id: Entity identifier
        neo4j_handler: Neo4j database handler (dependency)

    Returns:
        PDF file as StreamingResponse with attachment header
    """
    try:
        if not neo4j_handler:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Fetch entity from Neo4j
        entity_data = neo4j_handler.get_person(project_name, entity_id)
        if not entity_data:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        # Fetch relationships
        relationships = neo4j_handler.get_all_relationships(project_name, entity_id)
        entity_data["relationships"] = relationships

        # Generate PDF
        service = LatexReportService()
        pdf_bytes = service.generate_entity_profile_pdf(
            entity_id, entity_data, project_name
        )
        service.cleanup()

        # Return as download
        filename = f"{entity_id}_profile.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate entity PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/reports/pdf/investigation")
async def generate_investigation_pdf(
    project_name: str,
    entity_ids: List[str] = Query(...),
    neo4j_handler=Depends(get_neo4j_handler),
) -> StreamingResponse:
    """
    Generate multi-entity investigation summary PDF.

    Args:
        project_name: Project identifier
        entity_ids: List of entity IDs to include
        neo4j_handler: Neo4j database handler (dependency)

    Returns:
        PDF file as StreamingResponse with attachment header
    """
    try:
        if not neo4j_handler:
            raise HTTPException(status_code=500, detail="Database connection failed")

        if not entity_ids:
            raise HTTPException(status_code=400, detail="No entities specified")

        # Fetch entities
        entities = []
        for eid in entity_ids:
            entity = neo4j_handler.get_person(project_name, eid)
            if entity:
                entity["relationships"] = neo4j_handler.get_all_relationships(
                    project_name, eid
                )
                entities.append(entity)

        if not entities:
            raise HTTPException(status_code=404, detail="No entities found")

        # Generate PDF
        service = LatexReportService()
        pdf_bytes = service.generate_investigation_pdf(entities, project_name)
        service.cleanup()

        # Return as download
        filename = f"investigation_{project_name}.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate investigation PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/reports/pdf/relationship/{entity_id}")
async def generate_relationship_pdf(
    project_name: str,
    entity_id: str,
    depth: int = Query(2, ge=1, le=5),
    neo4j_handler=Depends(get_neo4j_handler),
) -> StreamingResponse:
    """
    Generate relationship network PDF for an entity.

    Args:
        project_name: Project identifier
        entity_id: Central entity ID
        depth: Relationship depth to include (1-5)
        neo4j_handler: Neo4j database handler (dependency)

    Returns:
        PDF file as StreamingResponse with attachment header
    """
    try:
        if not neo4j_handler:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Fetch entity
        entity_data = neo4j_handler.get_person(project_name, entity_id)
        if not entity_data:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        # Fetch relationships
        relationships = neo4j_handler.get_all_relationships(project_name, entity_id)
        entity_data["relationships"] = relationships

        # Generate PDF
        service = LatexReportService()
        pdf_bytes = service.generate_relationship_report(
            entity_id, entity_data, depth, project_name
        )
        service.cleanup()

        # Return as download
        filename = f"{entity_id}_relationships.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate relationship PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/reports/pdf/timeline/{entity_id}")
async def generate_timeline_pdf(
    project_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler),
) -> StreamingResponse:
    """
    Generate timeline report PDF for an entity.

    Args:
        project_name: Project identifier
        entity_id: Entity identifier
        neo4j_handler: Neo4j database handler (dependency)

    Returns:
        PDF file as StreamingResponse with attachment header
    """
    try:
        if not neo4j_handler:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Fetch entity
        entity_data = neo4j_handler.get_person(project_name, entity_id)
        if not entity_data:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        # Fetch events/timeline
        # This would typically come from a timeline service
        events = entity_data.get("timeline_events", [])

        # Generate PDF
        service = LatexReportService()
        pdf_bytes = service.generate_timeline_report(entity_id, events, project_name)
        service.cleanup()

        # Return as download
        filename = f"{entity_id}_timeline.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate timeline PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
