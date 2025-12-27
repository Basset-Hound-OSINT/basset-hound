"""
File Management Router for Basset Hound.

Provides endpoints for uploading, downloading, and managing files
associated with entities in OSINT investigation projects.
"""

import os
import hashlib
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..dependencies import get_neo4j_handler


router = APIRouter(
    prefix="/projects/{project_safe_name}/entities/{entity_id}/files",
    tags=["files"],
    responses={
        404: {"description": "File, entity, or project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class FileInfo(BaseModel):
    """Schema for file information."""
    id: str = Field(..., description="Unique file identifier")
    name: str = Field(..., description="Original filename")
    path: str = Field(..., description="Storage path/filename")
    section_id: Optional[str] = Field(None, description="Profile section ID")
    field_id: Optional[str] = Field(None, description="Profile field ID")
    uploaded_at: Optional[str] = Field(None, description="Upload timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4e5f6",
                "name": "profile_photo.jpg",
                "path": "a1b2c3d4e5f6_profile_photo.jpg",
                "section_id": "profile",
                "field_id": "profile_picture",
                "uploaded_at": "2024-01-15T10:30:00"
            }
        }


class FileUploadResponse(BaseModel):
    """Schema for file upload response."""
    success: bool = True
    files: list[FileInfo] = Field(default_factory=list)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


class DirectoryEntry(BaseModel):
    """Schema for directory entry (file or folder)."""
    name: str = Field(..., description="Entry name")
    type: str = Field(..., description="Entry type: 'file' or 'folder'")
    path: str = Field(..., description="Relative path from entity root")
    date: Optional[str] = Field(None, description="Last modified date")
    url: Optional[str] = Field(None, description="Download URL (files only)")
    id: Optional[str] = Field(None, description="File ID (files only)")


class DirectoryTreeNode(BaseModel):
    """Schema for directory tree node."""
    name: str
    type: str
    path: str
    open: Optional[bool] = False
    url: Optional[str] = None
    children: Optional[list["DirectoryTreeNode"]] = None


class ExploreResponse(BaseModel):
    """Schema for file explorer response."""
    entries: list[DirectoryEntry] = Field(default_factory=list)
    tree: list[DirectoryTreeNode] = Field(default_factory=list)


# Allow recursive model reference
DirectoryTreeNode.model_rebuild()


# ----- Helper Functions -----

def generate_file_id() -> str:
    """Generate a unique file identifier."""
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def is_image_file(filename: str) -> bool:
    """Check if a file is an allowed image type."""
    return os.path.splitext(filename)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ----- Endpoints -----

@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload files",
    description="Upload one or more files for an entity.",
    responses={
        201: {"description": "Files uploaded successfully"},
        400: {"description": "Invalid upload or path"},
        404: {"description": "Entity or project not found"},
    }
)
async def upload_files(
    project_safe_name: str,
    entity_id: str,
    files: list[UploadFile] = File(..., description="Files to upload"),
    path: str = Query("/files", description="Target directory path"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Upload files for an entity.

    Uploads one or more files to the entity's file storage.
    Files are stored in the 'files' subdirectory by default.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **files**: List of files to upload
    - **path**: Target directory path (must be within 'files' folder)
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entity exists
    person = neo4j_handler.get_person(project_safe_name, entity_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    project_id = project.get('id')
    safe_rel_path = path.strip('/')

    person_root = os.path.join("projects", project_id, "people", entity_id)
    files_root = os.path.join(person_root, "files")
    target_dir = os.path.join(person_root, safe_rel_path)

    abs_files_root = os.path.abspath(files_root)
    abs_target_dir = os.path.abspath(target_dir)

    # Only allow uploads to files folder or subfolders
    if not abs_target_dir.startswith(abs_files_root):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploads only allowed in 'files' folder"
        )

    os.makedirs(abs_target_dir, exist_ok=True)

    uploaded_files = []
    try:
        for file in files:
            if file and file.filename:
                # Generate unique file ID
                file_id = generate_file_id()
                filename = f"{file_id}_{file.filename}"
                file_path = os.path.join(abs_target_dir, filename)

                # Save file
                content = await file.read()
                with open(file_path, 'wb') as f:
                    f.write(content)

                uploaded_files.append(FileInfo(
                    id=file_id,
                    name=file.filename,
                    path=filename,
                    uploaded_at=datetime.now().isoformat()
                ))

        return FileUploadResponse(success=True, files=uploaded_files)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.get(
    "/{filename:path}",
    summary="Download a file",
    description="Download a specific file from an entity's storage.",
    responses={
        200: {
            "description": "File content",
            "content": {"application/octet-stream": {}}
        },
        404: {"description": "File not found"},
    }
)
async def download_file(
    project_safe_name: str,
    entity_id: str,
    filename: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Download a file.

    Returns the file content for the specified filename.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **filename**: The filename or path to download
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')

    # Try direct path first
    direct_path = os.path.join("projects", project_id, "people", entity_id, "files", filename)
    if os.path.exists(direct_path) and os.path.isfile(direct_path):
        return FileResponse(
            path=direct_path,
            filename=os.path.basename(filename)
        )

    # Search through entity files if not found directly
    people = neo4j_handler.get_all_people(project_safe_name)
    for person in people:
        if not person or not person.get('profile'):
            continue

        for section_id, section_data in person['profile'].items():
            if not isinstance(section_data, dict):
                continue
            for field_id, field_data in section_data.items():
                if not field_data:
                    continue

                file_entries = field_data if isinstance(field_data, list) else [field_data]

                for entry in file_entries:
                    if isinstance(entry, dict) and entry.get('path') == filename:
                        actual_person_id = entry.get('person_id', person['id'])
                        actual_path = os.path.join(
                            "projects", project_id, "people",
                            actual_person_id, "files", filename
                        )

                        if os.path.exists(actual_path):
                            return FileResponse(
                                path=actual_path,
                                filename=os.path.basename(filename)
                            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"File '{filename}' not found"
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file from the entity's storage and database.",
    responses={
        204: {"description": "File deleted successfully"},
        404: {"description": "File not found"},
    }
)
async def delete_file(
    project_safe_name: str,
    entity_id: str,
    file_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete a file.

    Removes the file from both the filesystem and the database.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **file_id**: The unique file identifier
    """
    # Get file info from Neo4j
    file_info = neo4j_handler.get_file(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{file_id}' not found"
        )

    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')

    # Try to delete from filesystem
    file_path = file_info.get('full_path') or os.path.join(
        "projects", project_id, "people", entity_id, "files",
        file_info.get('path', '')
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    neo4j_handler.delete_file(file_id)

    return None


# ----- Standalone file serving router -----

file_serve_router = APIRouter(
    prefix="/projects/{project_id}/people/{person_id}",
    tags=["files"],
    responses={
        404: {"description": "File not found"},
    },
)


@file_serve_router.get(
    "/files/{filename:path}",
    summary="Serve entity file",
    description="Serve a file from an entity's files directory.",
    responses={
        200: {
            "description": "File content",
            "content": {"application/octet-stream": {}}
        },
        404: {"description": "File not found"},
    }
)
async def serve_entity_file(
    project_id: str,
    person_id: str,
    filename: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Serve an entity file.

    Direct file serving endpoint for entity files.

    - **project_id**: The project UUID
    - **person_id**: The entity UUID
    - **filename**: The filename to serve
    """
    file_path = os.path.join("projects", project_id, "people", person_id, "files", filename)

    if not os.path.exists(file_path):
        # Try searching all entities if direct path fails
        projects = neo4j_handler.get_all_projects()
        for proj in projects:
            if proj.get('id') == project_id:
                project_safe_name = proj.get('safe_name')
                people = neo4j_handler.get_all_people(project_safe_name)

                for person in people:
                    if not person or not person.get('profile'):
                        continue

                    for section_id, section_data in person['profile'].items():
                        if not isinstance(section_data, dict):
                            continue
                        for field_id, field_data in section_data.items():
                            if not field_data:
                                continue

                            file_entries = field_data if isinstance(field_data, list) else [field_data]

                            for entry in file_entries:
                                if isinstance(entry, dict) and entry.get('path') == filename:
                                    actual_person_id = entry.get('person_id', person['id'])
                                    actual_path = os.path.join(
                                        "projects", project_id, "people",
                                        actual_person_id, "files", filename
                                    )

                                    if os.path.exists(actual_path):
                                        return FileResponse(
                                            path=actual_path,
                                            filename=os.path.basename(filename)
                                        )
                break

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=os.path.basename(filename)
    )
