"""
Frontend Reports Router - FastAPI Report Management

Handles report CRUD operations for the web UI.
Migrated from Flask reports.py blueprint.

Routes:
- GET /person/{person_id}/reports - List all reports for a person
- GET /person/{person_id}/reports/{report_name} - Get a specific report
- POST /person/{person_id}/reports - Create a new report
- PUT /person/{person_id}/reports/{report_name} - Update a report
- DELETE /person/{person_id}/reports/{report_name} - Delete a report
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from api.dependencies import get_neo4j_handler
from api.routers.frontend import get_current_project, PROJECT_ROOT
from neo4j_handler import Neo4jHandler

logger = logging.getLogger("basset_hound.frontend.reports")

router = APIRouter(tags=["Frontend Reports"])


def get_reports_dir(project_id: str, person_id: str) -> Path:
    """Get the reports directory for a person."""
    return PROJECT_ROOT / "projects" / project_id / "people" / person_id / "reports"


# =============================================================================
# Report Routes
# =============================================================================

@router.get("/person/{person_id}/reports")
async def list_reports(person_id: str):
    """
    List all reports for a person.

    Returns a list of report filenames (*.md files).
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        return []

    reports_dir = get_reports_dir(project_ctx["id"], person_id)

    if not reports_dir.exists():
        return []

    files = [f.name for f in reports_dir.iterdir() if f.is_file() and f.suffix == '.md']
    return files


@router.get("/person/{person_id}/reports/{report_name}")
async def get_report(person_id: str, report_name: str):
    """
    Get a specific report file.

    Returns the report file for download.
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    reports_dir = get_reports_dir(project_ctx["id"], person_id)
    report_path = reports_dir / report_name

    # Security check - prevent path traversal
    if not str(report_path.resolve()).startswith(str(reports_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid report name")

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=report_path,
        filename=report_name,
        media_type="text/markdown"
    )


@router.post("/person/{person_id}/reports")
async def create_report(
    person_id: str,
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Create a new report for a person.

    Request body:
    - toolname: Name of the tool that generated the report
    - content: Markdown content of the report
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project safe name")

    data = await request.json()
    toolname = data.get("toolname")
    content = data.get("content", "")

    if not toolname:
        raise HTTPException(status_code=400, detail="Tool name is required")

    # Generate unique report filename
    date_str = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid4())[:8]
    report_name = f"{toolname}_{date_str}_{person_id}_{unique_id}.md"

    # Ensure reports directory exists
    reports_dir = get_reports_dir(project_ctx["id"], person_id)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Write report file
    report_path = reports_dir / report_name
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Register report in Neo4j
    try:
        neo4j_handler.add_report_to_person(
            project_ctx["safe_name"],
            person_id,
            {
                "name": report_name,
                "path": report_name,
                "tool": toolname,
                "created_at": datetime.now().isoformat(),
                "id": unique_id
            }
        )
    except Exception as e:
        logger.warning(f"Failed to register report in Neo4j: {e}")
        # Continue anyway - file is saved

    return {"success": True, "report": report_name}


@router.put("/person/{person_id}/reports/{report_name}")
async def update_report(
    person_id: str,
    report_name: str,
    request: Request,
):
    """
    Update an existing report.

    Request body:
    - content: New markdown content
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    reports_dir = get_reports_dir(project_ctx["id"], person_id)
    report_path = reports_dir / report_name

    # Security check - prevent path traversal
    if not str(report_path.resolve()).startswith(str(reports_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid report name")

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    data = await request.json()
    content = data.get("content", "")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {"success": True}


@router.delete("/person/{person_id}/reports/{report_name}")
async def delete_report(
    person_id: str,
    report_name: str,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Delete a report.

    Removes both the file and the Neo4j reference.
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project safe name")

    reports_dir = get_reports_dir(project_ctx["id"], person_id)
    report_path = reports_dir / report_name

    # Security check - prevent path traversal
    if not str(report_path.resolve()).startswith(str(reports_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid report name")

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete file
    os.remove(report_path)

    # Remove from Neo4j
    try:
        neo4j_handler.remove_report_from_person(
            project_ctx["safe_name"],
            person_id,
            report_name
        )
    except Exception as e:
        logger.warning(f"Failed to remove report from Neo4j: {e}")
        # Continue anyway - file is deleted

    return {"success": True}
