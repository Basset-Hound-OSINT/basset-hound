"""
Frontend Router - FastAPI Template Serving

Serves Jinja2 templates for the basset-hound web UI.
Replaces Flask's template rendering with FastAPI's Jinja2Templates.

Migration from Flask:
- app.py routes → this module
- Uses same templates in templates/ directory
- Serves same static files from static/ directory
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from api.dependencies import get_neo4j_handler, get_app_config
from neo4j_handler import Neo4jHandler

logger = logging.getLogger("basset_hound.frontend")

router = APIRouter(tags=["Frontend"])

# Get project root directory (parent of api/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Session state (in-memory for single-user local-first operation)
# In production, this would use proper session management
_current_project: dict = {
    "id": None,
    "safe_name": None,
}


def get_current_project() -> dict:
    """Get current project context."""
    return _current_project


def set_current_project(project_id: Optional[str], safe_name: Optional[str]) -> None:
    """Set current project context."""
    _current_project["id"] = project_id
    _current_project["safe_name"] = safe_name


def slugify(value: str) -> str:
    """Convert string to URL-safe slug."""
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)


# =============================================================================
# Page Routes (HTML Templates)
# =============================================================================

@router.get("/", response_class=HTMLResponse, name="index")
async def index(request: Request):
    """
    Home page - Project selection.

    Renders the index template for selecting or creating projects.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/map.html", response_class=HTMLResponse, name="map_page")
async def map_page(request: Request):
    """
    Map visualization page.
    """
    return templates.TemplateResponse("map.html", {"request": request})


@router.get("/osint.html", response_class=HTMLResponse, name="osint_page")
async def osint_page(request: Request):
    """
    OSINT tools page.
    """
    return templates.TemplateResponse("osint.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
    config: dict = Depends(get_app_config),
):
    """
    Main dashboard page.

    Shows the current project's dashboard with people/entities list.
    Redirects to index if no project is selected.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    project = neo4j_handler.get_project(project_ctx["safe_name"])
    if not project:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "project": project,
            "config": config,
            "person": None,
            "current_project_id": project_ctx["id"],
            "current_project_safe_name": project_ctx["safe_name"],
        }
    )


# =============================================================================
# Project Management Routes
# =============================================================================

@router.post("/new_project")
async def new_project(
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Create a new project.

    Creates a project in Neo4j and sets it as the current project.
    """
    form_data = await request.form()
    project_name = form_data.get("project_name")

    if not project_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name is required"
        )

    project_safe_name = slugify(project_name)

    try:
        # Create project in Neo4j
        project = neo4j_handler.create_project(project_name, project_safe_name)

        if not project:
            return {"success": False, "error": "Failed to create project"}

        project_id = project.get("id")

        # Set current project
        set_current_project(project_id, project_safe_name)

        # Create project directory
        projects_dir = PROJECT_ROOT / "projects" / project_id
        projects_dir.mkdir(parents=True, exist_ok=True)

        return {
            "success": True,
            "redirect": "/dashboard",
            "project_id": project_id,
            "project_safe_name": project_safe_name,
        }

    except Exception as e:
        if "already exists" in str(e):
            return {"success": False, "error": "A project with this name already exists"}
        logger.error(f"Error creating project: {e}")
        return {"success": False, "error": str(e)}


@router.get("/get_projects")
async def get_projects(
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Get all projects.

    Returns a list of all projects for the project selector.
    """
    try:
        projects = neo4j_handler.get_all_projects()
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/set_current_project")
async def set_current_project_route(
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Set the current active project.

    Updates the session context to the specified project.
    """
    data = await request.json()
    safe_name = data.get("safe_name")

    if not safe_name:
        return {"success": False, "error": "No project specified"}

    project = neo4j_handler.get_project(safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    project_id = project.get("id")
    set_current_project(project_id, safe_name)

    return {
        "success": True,
        "project_id": project_id,
        "project_safe_name": safe_name,
        "redirect": "/dashboard",
    }


# =============================================================================
# Configuration Routes
# =============================================================================

@router.get("/get_config")
async def get_config(config: dict = Depends(get_app_config)):
    """
    Get the current data configuration.

    Returns the YAML configuration for entity types and fields.
    """
    return config


@router.post("/save_config")
async def save_config(
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Save updated configuration.

    Saves the configuration to data_config.yaml and updates the Neo4j schema.
    """
    import yaml
    from api.dependencies import set_app_config

    config_data = await request.json()

    if "sections" not in config_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration format"
        )

    # Save to YAML file
    config_path = PROJECT_ROOT / "data_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)

    # Update app config
    set_app_config(config_data)

    # Update Neo4j schema
    neo4j_handler.setup_schema_from_config(config_data)

    return {"success": True}


# =============================================================================
# File Download Routes
# =============================================================================

@router.get("/download_project")
async def download_project(
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Download the current project as JSON.
    """
    import json
    from fastapi.responses import Response

    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    project = neo4j_handler.get_project(project_ctx["safe_name"])
    if not project:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    filename = f"{project['name'].replace(' ', '_')}.json"
    content = json.dumps(project, indent=4)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# =============================================================================
# Tagging Routes
# =============================================================================

@router.post("/tag_person/{person_id}")
async def tag_person(
    person_id: str,
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Tag a person with relationships to other people.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        return {"success": False, "error": "No project selected"}

    data = await request.json()
    if not data or "tagged_ids" not in data:
        return {"success": False, "error": "Invalid request data"}

    try:
        updated_person = neo4j_handler.update_person(
            project_ctx["safe_name"],
            person_id,
            {
                "profile": {
                    "Tagged People": {
                        "tagged_people": data["tagged_ids"],
                        "transitive_relationships": data.get("transitive_relationships", [])
                    }
                }
            }
        )

        if not updated_person:
            return {"success": False, "error": "Person not found or update failed"}

        return {"success": True}

    except Exception as e:
        logger.error(f"Error tagging person: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "An error occurred while saving tags"
        }
