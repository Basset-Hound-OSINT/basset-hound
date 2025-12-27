"""
Entity (Person) CRUD Router for Basset Hound.

Provides endpoints for creating, reading, updating, and deleting entities (persons)
within OSINT investigation projects.
"""

import os
import re
import hashlib
import io
import zipfile
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..dependencies import get_neo4j_handler, get_app_config, get_current_project


router = APIRouter(
    prefix="/projects/{project_safe_name}/entities",
    tags=["entities"],
    responses={
        404: {"description": "Entity or project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class EntityProfile(BaseModel):
    """Schema for entity profile data - flexible key-value structure."""

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "profile": {
                    "first_name": "John",
                    "last_name": "Doe"
                },
                "social_media": {
                    "twitter": "@johndoe",
                    "linkedin": "john-doe-12345"
                }
            }
        }


class EntityCreate(BaseModel):
    """Schema for creating a new entity."""
    profile: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Profile data organized by sections and fields"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "profile": {
                        "first_name": "John",
                        "last_name": "Doe"
                    }
                }
            }
        }


class EntityResponse(BaseModel):
    """Schema for entity response data."""
    id: str = Field(..., description="Unique entity identifier (UUID)")
    created_at: Optional[str] = Field(None, description="ISO 8601 creation timestamp")
    profile: dict[str, Any] = Field(default_factory=dict, description="Entity profile data")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "profile": {
                        "first_name": "John",
                        "last_name": "Doe"
                    }
                }
            }
        }


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""
    profile: Optional[dict[str, Any]] = Field(
        None,
        description="Updated profile data (partial updates supported)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "profile": {
                        "first_name": "Jane"
                    }
                }
            }
        }


class EntityListResponse(BaseModel):
    """Schema for list of entities."""
    entities: list[EntityResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of entities")


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


# ----- Helper Functions -----

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def is_image_file(filename: str) -> bool:
    """Check if a file is an allowed image type."""
    return os.path.splitext(filename)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def generate_file_id() -> str:
    """Generate a unique file identifier."""
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


# ----- Endpoints -----

@router.get(
    "/",
    response_model=list[EntityResponse],
    summary="List all entities in a project",
    description="Retrieve a list of all entities (persons) within a specific project.",
    responses={
        200: {"description": "List of entities retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def list_entities(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List all entities in a project.

    Returns all people/entities associated with the specified project
    including their complete profile data.

    - **project_safe_name**: The URL-safe identifier for the project
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        people = neo4j_handler.get_all_people(project_safe_name)
        return people if people else []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entities: {str(e)}"
        )


@router.post(
    "/",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity",
    description="Create a new entity (person) within a project.",
    responses={
        201: {"description": "Entity created successfully"},
        400: {"description": "Invalid entity data"},
        404: {"description": "Project not found"},
    }
)
async def create_entity(
    project_safe_name: str,
    entity_data: EntityCreate,
    neo4j_handler=Depends(get_neo4j_handler),
    config=Depends(get_app_config)
):
    """
    Create a new entity.

    Creates a new person/entity within the specified project.
    Automatically generates a unique ID and sets up required directories.

    - **project_safe_name**: The URL-safe identifier for the project
    - **profile**: Optional initial profile data
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Generate person ID
        person_id = str(uuid4())

        # Prepare person data
        person_data = {
            "id": person_id,
            "created_at": datetime.now().isoformat(),
            "profile": entity_data.profile or {}
        }

        # Get project ID for directory creation
        project_id = project.get('id')

        # Create directories for files and reports
        person_files_dir = os.path.join("projects", project_id, "people", person_id, "files")
        person_reports_dir = os.path.join("projects", project_id, "people", person_id, "reports")
        os.makedirs(person_files_dir, exist_ok=True)
        os.makedirs(person_reports_dir, exist_ok=True)

        # Create person in Neo4j
        person = neo4j_handler.create_person(project_safe_name, person_data)

        if not person:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create entity"
            )

        return person

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity: {str(e)}"
        )


@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Get entity details",
    description="Retrieve detailed information about a specific entity.",
    responses={
        200: {"description": "Entity details retrieved successfully"},
        404: {"description": "Entity or project not found"},
    }
)
async def get_entity(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get an entity by ID.

    Returns the complete entity data including all profile information.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    """
    person = neo4j_handler.get_person(project_safe_name, entity_id)

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    return person


@router.put(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Update an entity",
    description="Update an existing entity's profile data.",
    responses={
        200: {"description": "Entity updated successfully"},
        400: {"description": "Invalid update data"},
        404: {"description": "Entity or project not found"},
    }
)
async def update_entity(
    project_safe_name: str,
    entity_id: str,
    entity_data: EntityUpdate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update an entity.

    Updates the entity's profile data. Supports partial updates.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **profile**: The profile data to update
    """
    # Verify entity exists
    existing = neo4j_handler.get_person(project_safe_name, entity_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        update_data = {}
        if entity_data.profile is not None:
            update_data["profile"] = entity_data.profile

        updated_person = neo4j_handler.update_person(
            project_safe_name,
            entity_id,
            update_data
        )

        if not updated_person:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update entity"
            )

        return updated_person

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity: {str(e)}"
        )


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entity",
    description="Delete an entity and all associated data.",
    responses={
        204: {"description": "Entity deleted successfully"},
        404: {"description": "Entity or project not found"},
    }
)
async def delete_entity(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete an entity.

    Permanently deletes the entity and all associated files, reports,
    and relationships. This action cannot be undone.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity to delete
    """
    success = neo4j_handler.delete_person(project_safe_name, entity_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    return None


@router.post(
    "/{entity_id}/export",
    summary="Export entity as ZIP",
    description="Export entity data, files, and reports as a ZIP archive.",
    responses={
        200: {
            "description": "Entity ZIP archive",
            "content": {"application/zip": {}}
        },
        404: {"description": "Entity or project not found"},
    }
)
async def export_entity(
    project_safe_name: str,
    entity_id: str,
    request: Request,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export entity as ZIP archive.

    Creates a ZIP file containing the entity's profile report (markdown),
    all associated files, and reports.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **Request body**: Optional markdown content for the profile report
    """
    # Get project to verify and get project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    person = neo4j_handler.get_person(project_safe_name, entity_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        # Get markdown content from request body
        body = await request.body()
        markdown_content = body.decode('utf-8') if body else ""

        project_id = project.get('id')
        person_root = os.path.join("projects", project_id, "people", entity_id)
        files_dir = os.path.join(person_root, "files")
        reports_dir = os.path.join(person_root, "reports")

        # Create in-memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add markdown report at root
            zipf.writestr(f"profile_report_{entity_id}.md", markdown_content)

            # Helper to add directory contents recursively
            def add_dir_to_zip(base_dir: str, arc_prefix: str):
                if not os.path.exists(base_dir):
                    return
                for root, dirs, files in os.walk(base_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, base_dir)
                        arcname = os.path.join(arc_prefix, rel_path)
                        zipf.write(abs_path, arcname=arcname)

            # Add files and reports directories
            add_dir_to_zip(files_dir, "files")
            add_dir_to_zip(reports_dir, "reports")

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="profile_{entity_id}_report.zip"'
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export entity: {str(e)}"
        )


@router.get(
    "/{entity_id}/explore",
    summary="Explore entity file structure",
    description="Get the directory structure and files for an entity.",
    responses={
        200: {"description": "File structure retrieved successfully"},
        404: {"description": "Entity or project not found"},
    }
)
async def explore_entity_files(
    project_safe_name: str,
    entity_id: str,
    path: str = "/",
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Explore entity file structure.

    Returns the directory tree and file entries for the entity's
    file storage area.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **path**: The relative path to explore (default: root)
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    safe_rel_path = path.strip('/')

    person_root = os.path.join("projects", project_id, "people", entity_id)
    abs_path = os.path.join(person_root, safe_rel_path)

    try:
        abs_person_root = os.path.abspath(person_root)

        # Ensure root and subfolders exist
        if not os.path.exists(abs_person_root):
            os.makedirs(os.path.join(abs_person_root, "files"), exist_ok=True)
            os.makedirs(os.path.join(abs_person_root, "reports"), exist_ok=True)

        abs_abs_path = os.path.abspath(abs_path)
        if not abs_abs_path.startswith(abs_person_root):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path"
            )

        entries = []
        tree = []

        if os.path.exists(abs_abs_path):
            for name in sorted(os.listdir(abs_abs_path)):
                full_path = os.path.join(abs_abs_path, name)
                stat = os.stat(full_path)
                entry = {
                    "name": name,
                    "path": os.path.relpath(full_path, abs_person_root),
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                }
                if os.path.isdir(full_path):
                    entry["type"] = "folder"
                else:
                    entry["type"] = "file"
                    entry["url"] = f"/projects/{project_id}/people/{entity_id}/{entry['path']}".replace("\\", "/")
                    entry["id"] = ""
                entries.append(entry)

        def build_tree(base_path: str, rel_path: str = '') -> list:
            nodes = []
            if not os.path.exists(base_path):
                return nodes
            for name in sorted(os.listdir(base_path)):
                full_path = os.path.join(base_path, name)
                node_path = os.path.join(rel_path, name)
                if os.path.isdir(full_path):
                    nodes.append({
                        "name": name,
                        "type": "folder",
                        "path": node_path.replace("\\", "/"),
                        "open": node_path.strip('/') == safe_rel_path,
                        "children": build_tree(full_path, node_path) if node_path.strip('/') == safe_rel_path else []
                    })
                else:
                    nodes.append({
                        "name": name,
                        "type": "file",
                        "path": node_path.replace("\\", "/"),
                        "url": f"/projects/{project_id}/people/{entity_id}/{node_path.replace(chr(92), '/')}"
                    })
            return nodes

        tree = build_tree(abs_person_root)

        return {
            "entries": entries,
            "tree": tree
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explore files: {str(e)}"
        )
