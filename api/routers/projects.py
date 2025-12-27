"""
Project CRUD Router for Basset Hound.

Provides endpoints for creating, reading, updating, and deleting OSINT investigation projects.
"""

import os
import re
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..dependencies import get_neo4j_handler, get_current_project, set_current_project


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The display name for the project",
        json_schema_extra={"example": "Operation Midnight"}
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Operation Midnight"
            }
        }


class ProjectResponse(BaseModel):
    """Schema for project response data."""
    id: str = Field(..., description="Unique project identifier (UUID)")
    name: str = Field(..., description="Project display name")
    safe_name: str = Field(..., description="URL-safe project identifier")
    created_at: Optional[str] = Field(None, description="ISO 8601 creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Operation Midnight",
                "safe_name": "operation_midnight",
                "created_at": "2024-01-15T10:30:00"
            }
        }


class ProjectDetailResponse(ProjectResponse):
    """Schema for detailed project response including people."""
    people: list = Field(default_factory=list, description="List of people in the project")


class ProjectSetCurrent(BaseModel):
    """Schema for setting the current active project."""
    safe_name: str = Field(
        ...,
        description="The safe_name of the project to set as current",
        json_schema_extra={"example": "operation_midnight"}
    )


class ProjectSetCurrentResponse(BaseModel):
    """Response schema for setting current project."""
    success: bool
    project_id: str
    message: str = "Project set as current"


# ----- Helper Functions -----

def slugify(value: str) -> str:
    """Convert a string to a URL-safe slug."""
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)


# ----- Endpoints -----

@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="List all projects",
    description="Retrieve a list of all OSINT investigation projects.",
    responses={
        200: {
            "description": "List of projects retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "Operation Midnight",
                            "safe_name": "operation_midnight",
                            "created_at": "2024-01-15T10:30:00"
                        }
                    ]
                }
            }
        }
    }
)
async def list_projects(neo4j_handler=Depends(get_neo4j_handler)):
    """
    Retrieve all projects.

    Returns a list of all projects with their basic information including
    ID, name, safe_name, and creation timestamp.
    """
    try:
        projects = neo4j_handler.get_all_projects()
        return projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new OSINT investigation project.",
    responses={
        201: {"description": "Project created successfully"},
        400: {"description": "Invalid project data or project already exists"},
    }
)
async def create_project(
    project_data: ProjectCreate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a new project.

    Creates a new OSINT investigation project with the given name.
    A safe_name is automatically generated from the project name.
    A project directory is created in the filesystem.

    - **name**: The display name for the project (required)
    """
    try:
        safe_name = slugify(project_data.name)
        project = neo4j_handler.create_project(project_data.name, safe_name)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create project"
            )

        # Create project directory
        project_id = project.get('id')
        os.makedirs(f'projects/{project_id}', exist_ok=True)

        return project

    except HTTPException:
        raise
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project with this name already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get(
    "/{safe_name}",
    response_model=ProjectDetailResponse,
    summary="Get project details",
    description="Retrieve detailed information about a specific project including all associated people.",
    responses={
        200: {"description": "Project details retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_project(
    safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get a project by its safe_name.

    Returns detailed project information including all people associated with the project.

    - **safe_name**: The URL-safe identifier for the project
    """
    project = neo4j_handler.get_project(safe_name)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{safe_name}' not found"
        )

    return project


@router.delete(
    "/{safe_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Delete a project and all its associated data.",
    responses={
        204: {"description": "Project deleted successfully"},
        404: {"description": "Project not found"},
    }
)
async def delete_project(
    safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete a project.

    Permanently deletes the project and all associated people, files, and relationships.
    This action cannot be undone.

    - **safe_name**: The URL-safe identifier for the project to delete
    """
    success = neo4j_handler.delete_project(safe_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{safe_name}' not found"
        )

    return None


@router.post(
    "/current",
    response_model=ProjectSetCurrentResponse,
    summary="Set current active project",
    description="Set the current active project for the session.",
    responses={
        200: {"description": "Current project set successfully"},
        404: {"description": "Project not found"},
    }
)
async def set_current_project(
    data: ProjectSetCurrent,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Set the current active project.

    Sets which project is currently active for operations that require
    a project context.

    - **safe_name**: The safe_name of the project to set as current
    """
    project = neo4j_handler.get_project(data.safe_name)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{data.safe_name}' not found"
        )

    # Set the current project in the global state
    set_current_project(project)

    return ProjectSetCurrentResponse(
        success=True,
        project_id=project.get('id'),
        message=f"Project '{data.safe_name}' set as current"
    )


@router.get(
    "/{safe_name}/download",
    summary="Download project as JSON",
    description="Export and download the project data as a JSON file.",
    responses={
        200: {
            "description": "Project JSON file",
            "content": {"application/json": {}}
        },
        404: {"description": "Project not found"},
    }
)
async def download_project(
    safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Download project data as JSON.

    Exports the complete project data including all people and their
    profiles as a downloadable JSON file.

    - **safe_name**: The URL-safe identifier for the project
    """
    project = neo4j_handler.get_project(safe_name)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{safe_name}' not found"
        )

    # Create download directory if it doesn't exist
    download_dir = os.path.join('static', 'downloads')
    os.makedirs(download_dir, exist_ok=True)

    # Generate filename and save
    filename = f"{project['name'].replace(' ', '_')}.json"
    temp_path = os.path.join(download_dir, filename)

    with open(temp_path, 'w') as f:
        json.dump(project, f, indent=4, default=str)

    return FileResponse(
        path=temp_path,
        filename=filename,
        media_type='application/json'
    )
