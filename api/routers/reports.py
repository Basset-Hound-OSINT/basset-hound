"""
Reports Router for Basset Hound.

Provides endpoints for creating, reading, updating, and deleting
investigation reports associated with entities.
"""

import os
from typing import Optional
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler


router = APIRouter(
    prefix="/projects/{project_safe_name}/entities/{entity_id}/reports",
    tags=["reports"],
    responses={
        404: {"description": "Report, entity, or project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class ReportCreate(BaseModel):
    """Schema for creating a new report."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "toolname": "sherlock",
            "content": "# Sherlock Report\n\nFindings from username search..."
        }
    })

    toolname: str = Field(
        ...,
        description="Name of the OSINT tool that generated the report",
        json_schema_extra={"example": "sherlock"}
    )
    content: str = Field(
        default="",
        description="Markdown content of the report"
    )


class ReportCreateFromFile(BaseModel):
    """Schema for creating a report with a specific filename."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "filename": "investigation_notes.md",
            "content": "# Investigation Notes\n\n..."
        }
    })

    filename: str = Field(
        ...,
        description="Filename for the report (must end in .md)",
        json_schema_extra={"example": "investigation_notes.md"}
    )
    content: str = Field(
        default="",
        description="Markdown content of the report"
    )


class ReportUpdate(BaseModel):
    """Schema for updating a report."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content": "# Updated Report\n\nNew findings..."
        }
    })

    content: str = Field(
        ...,
        description="Updated markdown content"
    )


class ReportRename(BaseModel):
    """Schema for renaming a report."""
    new_name: str = Field(
        ...,
        description="New filename (must end in .md)",
        json_schema_extra={"example": "renamed_report.md"}
    )


class ReportInfo(BaseModel):
    """Schema for report information."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "sherlock_20240115_abc12345.md",
            "path": "sherlock_20240115_abc12345.md",
            "tool": "sherlock",
            "created_at": "2024-01-15T10:30:00",
            "id": "abc12345"
        }
    })

    name: str = Field(..., description="Report filename")
    path: str = Field(..., description="Storage path")
    tool: Optional[str] = Field(None, description="Source OSINT tool")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    id: Optional[str] = Field(None, description="Unique report identifier")


class ReportCreateResponse(BaseModel):
    """Schema for report creation response."""
    success: bool = True
    report: str = Field(..., description="Created report filename")


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None
    filename: Optional[str] = None


# ----- Helper Functions -----

def get_reports_dir(project_id: str, entity_id: str) -> str:
    """Get the reports directory path for an entity."""
    return os.path.join("projects", project_id, "people", entity_id, "reports")


def validate_filename(filename: str) -> bool:
    """Validate that a filename is safe and ends in .md."""
    if not filename or not filename.endswith('.md'):
        return False
    # Check for safe characters only
    base = filename.replace('.md', '')
    return base.replace('_', '').replace('-', '').isalnum()


# ----- Endpoints -----

@router.get(
    "/",
    response_model=list[str],
    summary="List all reports",
    description="Retrieve a list of all report filenames for an entity.",
    responses={
        200: {
            "description": "List of report filenames",
            "content": {
                "application/json": {
                    "example": [
                        "sherlock_20240115_abc12345.md",
                        "maigret_20240115_def67890.md"
                    ]
                }
            }
        },
    }
)
async def list_reports(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List all reports for an entity.

    Returns a list of report filenames (markdown files) in the
    entity's reports directory.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)

    if not os.path.exists(reports_dir):
        return []

    files = [f for f in os.listdir(reports_dir) if f.endswith('.md')]
    return files


@router.post(
    "/",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report",
    description="Create a new investigation report for an entity.",
    responses={
        201: {"description": "Report created successfully"},
        400: {"description": "Invalid report data"},
        404: {"description": "Entity or project not found"},
    }
)
async def create_report(
    project_safe_name: str,
    entity_id: str,
    report_data: ReportCreate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a new report.

    Creates a new markdown report file with an auto-generated filename
    based on the tool name, date, and unique ID.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **toolname**: Name of the OSINT tool that generated the report
    - **content**: Markdown content of the report
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)

    try:
        # Generate report filename
        date_str = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid4())[:8]
        report_name = f"{report_data.toolname}_{date_str}_{entity_id}_{unique_id}.md"

        # Ensure directory exists
        os.makedirs(reports_dir, exist_ok=True)

        # Write report file
        report_path = os.path.join(reports_dir, report_name)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_data.content)

        # Register in Neo4j
        neo4j_handler.add_report_to_person(
            project_safe_name,
            entity_id,
            {
                "name": report_name,
                "path": report_name,
                "tool": report_data.toolname,
                "created_at": datetime.now().isoformat(),
                "id": unique_id
            }
        )

        return ReportCreateResponse(success=True, report=report_name)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.post(
    "/file",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report with custom filename",
    description="Create a report with a specific filename.",
    responses={
        201: {"description": "Report created successfully"},
        400: {"description": "Invalid filename or file already exists"},
        404: {"description": "Entity or project not found"},
    }
)
async def create_report_file(
    project_safe_name: str,
    entity_id: str,
    report_data: ReportCreateFromFile,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a report with a custom filename.

    Creates a new markdown report with the specified filename.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **filename**: Desired filename (must end in .md)
    - **content**: Markdown content of the report
    """
    # Validate filename
    if not report_data.filename.endswith('.md'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end in .md"
        )

    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)
    report_path = os.path.abspath(os.path.join(reports_dir, report_data.filename))

    # Security check - ensure path is within reports dir
    abs_reports_dir = os.path.abspath(reports_dir)
    if not report_path.startswith(abs_reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid filename path"
        )

    # Check if file already exists
    if os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File already exists"
        )

    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_data.content)

        return SuccessResponse(success=True, filename=report_data.filename)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.get(
    "/{report_name}",
    summary="Get report content",
    description="Retrieve the content of a specific report.",
    responses={
        200: {
            "description": "Report content",
            "content": {"text/markdown": {}}
        },
        404: {"description": "Report not found"},
    }
)
async def get_report(
    project_safe_name: str,
    entity_id: str,
    report_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get a report by name.

    Returns the markdown content of the specified report.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **report_name**: The report filename
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)
    report_path = os.path.join(reports_dir, report_name)

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_name}' not found"
        )

    return FileResponse(
        path=report_path,
        media_type='text/markdown',
        filename=report_name
    )


@router.put(
    "/{report_name}",
    response_model=SuccessResponse,
    summary="Update report content",
    description="Update the content of an existing report.",
    responses={
        200: {"description": "Report updated successfully"},
        404: {"description": "Report not found"},
    }
)
async def update_report(
    project_safe_name: str,
    entity_id: str,
    report_name: str,
    report_data: ReportUpdate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update a report.

    Updates the markdown content of an existing report.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **report_name**: The report filename to update
    - **content**: New markdown content
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)
    report_path = os.path.abspath(os.path.join(reports_dir, report_name))

    # Security check
    abs_reports_dir = os.path.abspath(reports_dir)
    if not report_path.startswith(abs_reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid report path"
        )

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_name}' not found"
        )

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_data.content)

        return SuccessResponse(success=True, message="Report updated successfully")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update report: {str(e)}"
        )


@router.delete(
    "/{report_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a report",
    description="Delete a report file.",
    responses={
        204: {"description": "Report deleted successfully"},
        404: {"description": "Report not found"},
    }
)
async def delete_report(
    project_safe_name: str,
    entity_id: str,
    report_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete a report.

    Removes the report file from the filesystem and the database.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **report_name**: The report filename to delete
    """
    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)
    report_path = os.path.join(reports_dir, report_name)

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_name}' not found"
        )

    try:
        os.remove(report_path)

        # Remove from Neo4j
        neo4j_handler.remove_report_from_person(
            project_safe_name,
            entity_id,
            report_name
        )

        return None

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}"
        )


@router.post(
    "/{report_name}/rename",
    response_model=SuccessResponse,
    summary="Rename a report",
    description="Rename an existing report file.",
    responses={
        200: {"description": "Report renamed successfully"},
        400: {"description": "Invalid new filename or file already exists"},
        404: {"description": "Report not found"},
    }
)
async def rename_report(
    project_safe_name: str,
    entity_id: str,
    report_name: str,
    rename_data: ReportRename,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Rename a report.

    Renames an existing report file to a new name.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **report_name**: Current report filename
    - **new_name**: New filename (must end in .md)
    """
    # Validate new filename
    if not validate_filename(rename_data.new_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    # Get project for project_id
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    project_id = project.get('id')
    reports_dir = get_reports_dir(project_id, entity_id)

    old_path = os.path.abspath(os.path.join(reports_dir, report_name))
    new_path = os.path.abspath(os.path.join(reports_dir, rename_data.new_name))

    # Security check
    abs_reports_dir = os.path.abspath(reports_dir)
    if not old_path.startswith(abs_reports_dir) or not new_path.startswith(abs_reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    if not os.path.exists(old_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_name}' not found"
        )

    if os.path.exists(new_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with the new name already exists"
        )

    try:
        os.rename(old_path, new_path)
        return SuccessResponse(success=True, filename=rename_data.new_name)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename report: {str(e)}"
        )


# ----- Standalone report serving router -----

report_serve_router = APIRouter(
    prefix="/projects/{project_id}/people/{person_id}/reports",
    tags=["reports"],
    responses={
        404: {"description": "Report not found"},
    },
)


@report_serve_router.get(
    "/{filename:path}",
    summary="Serve report file",
    description="Direct endpoint to serve a report file.",
    responses={
        200: {
            "description": "Report content",
            "content": {"text/markdown": {}}
        },
        404: {"description": "Report not found"},
    }
)
async def serve_report_file(
    project_id: str,
    person_id: str,
    filename: str
):
    """
    Serve a report file directly.

    - **project_id**: The project UUID
    - **person_id**: The entity UUID
    - **filename**: The report filename
    """
    reports_dir = os.path.abspath(os.path.join("projects", project_id, "people", person_id, "reports"))
    file_path = os.path.abspath(os.path.join(reports_dir, filename))

    # Security check
    if not file_path.startswith(reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return FileResponse(
        path=file_path,
        media_type='text/markdown',
        filename=os.path.basename(filename)
    )


@report_serve_router.put(
    "/{filename:path}",
    response_model=SuccessResponse,
    summary="Update report file directly",
    description="Direct endpoint to update a report file.",
    responses={
        200: {"description": "Report updated successfully"},
        404: {"description": "Report not found"},
    }
)
async def update_report_file_direct(
    project_id: str,
    person_id: str,
    filename: str,
    report_data: ReportUpdate
):
    """
    Update a report file directly.

    - **project_id**: The project UUID
    - **person_id**: The entity UUID
    - **filename**: The report filename
    - **content**: New markdown content
    """
    reports_dir = os.path.abspath(os.path.join("projects", project_id, "people", person_id, "reports"))
    file_path = os.path.abspath(os.path.join(reports_dir, filename))

    # Security check
    if not file_path.startswith(reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_data.content)

        return SuccessResponse(success=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update report: {str(e)}"
        )


@report_serve_router.post(
    "/",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report file directly",
    description="Direct endpoint to create a report file.",
    responses={
        201: {"description": "Report created successfully"},
        400: {"description": "Invalid filename or file already exists"},
    }
)
async def create_report_file_direct(
    project_id: str,
    person_id: str,
    report_data: ReportCreateFromFile
):
    """
    Create a report file directly.

    - **project_id**: The project UUID
    - **person_id**: The entity UUID
    - **filename**: Desired filename (must end in .md)
    - **content**: Markdown content
    """
    if not report_data.filename.endswith('.md'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    reports_dir = os.path.abspath(os.path.join("projects", project_id, "people", person_id, "reports"))
    file_path = os.path.abspath(os.path.join(reports_dir, report_data.filename))

    # Security check
    if not file_path.startswith(reports_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    if os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File already exists"
        )

    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_data.content)

        return SuccessResponse(success=True, filename=report_data.filename)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )
