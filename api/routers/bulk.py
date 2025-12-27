"""
Bulk Operations Router for Basset Hound.

Provides endpoints for batch import and export of entities,
supporting JSON, CSV, and JSONL formats.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.bulk_operations import (
    BulkOperationsService,
    BulkExportOptions,
    BulkImportResult,
)


router = APIRouter(
    prefix="/projects/{project_safe_name}/bulk",
    tags=["bulk-operations"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class BulkImportRequest(BaseModel):
    """Request schema for bulk entity import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entities": [
                {
                    "profile": {
                        "core": {
                            "name": [{"first_name": "John", "last_name": "Doe"}],
                            "email": ["john@example.com"]
                        }
                    }
                },
                {
                    "profile": {
                        "core": {
                            "name": [{"first_name": "Jane", "last_name": "Smith"}],
                            "email": ["jane@example.com"]
                        }
                    }
                }
            ],
            "update_existing": False
        }
    })

    entities: List[dict] = Field(
        ...,
        description="List of entity dictionaries to import",
        min_length=1
    )
    update_existing: bool = Field(
        default=False,
        description="If True, update existing entities with matching IDs"
    )


class BulkImportResultResponse(BaseModel):
    """Response schema for bulk import results."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 10,
            "successful": 8,
            "failed": 2,
            "errors": [
                {"index": 3, "error": "Entity already exists"},
                {"index": 7, "error": "Invalid profile format"}
            ],
            "created_ids": [
                "uuid-1", "uuid-2", "uuid-3", "uuid-4",
                "uuid-5", "uuid-6", "uuid-8", "uuid-9"
            ]
        }
    })

    total: int = Field(..., description="Total number of entities in the import")
    successful: int = Field(..., description="Number of successfully imported entities")
    failed: int = Field(..., description="Number of failed imports")
    errors: List[dict] = Field(
        default_factory=list,
        description="List of errors with entity index and message"
    )
    created_ids: List[str] = Field(
        default_factory=list,
        description="List of IDs for successfully created/updated entities"
    )


class CSVImportRequest(BaseModel):
    """Request schema for CSV import with field mapping."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "csv_content": "first_name,last_name,email\nJohn,Doe,john@example.com\nJane,Smith,jane@example.com",
            "mapping": {
                "first_name": "profile.core.first_name",
                "last_name": "profile.core.last_name",
                "email": "profile.core.email"
            }
        }
    })

    csv_content: str = Field(
        ...,
        description="CSV content as string"
    )
    mapping: dict = Field(
        ...,
        description="Mapping of CSV columns to entity field paths (e.g., 'profile.core.name')"
    )


class ValidationRequest(BaseModel):
    """Request schema for import validation."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entities": [
                {
                    "profile": {
                        "core": {
                            "name": [{"first_name": "John", "last_name": "Doe"}]
                        }
                    }
                }
            ]
        }
    })

    entities: List[dict] = Field(
        ...,
        description="List of entity dictionaries to validate",
        min_length=1
    )


class ValidationResponse(BaseModel):
    """Response schema for validation results."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "valid": True,
            "errors": []
        }
    })

    valid: bool = Field(..., description="Whether all entities passed validation")
    errors: List[dict] = Field(
        default_factory=list,
        description="List of validation errors"
    )


class CSVExportRequest(BaseModel):
    """Request schema for CSV export with specific fields."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "fields": ["id", "created_at", "profile.core.name", "profile.core.email"]
        }
    })

    fields: List[str] = Field(
        ...,
        description="List of field paths to include in CSV export",
        min_length=1
    )


# ----- Endpoints -----

@router.post(
    "/import",
    response_model=BulkImportResultResponse,
    summary="Bulk import entities",
    description="Import multiple entities at once from JSON data.",
    responses={
        200: {"description": "Import completed (may have partial success)"},
        400: {"description": "Invalid request data"},
        404: {"description": "Project not found"},
    }
)
async def bulk_import_entities(
    project_safe_name: str,
    request: BulkImportRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Bulk import entities into a project.

    Imports multiple entities at once. Each entity can optionally include
    an ID; if not provided, one will be generated.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entities**: List of entity dictionaries to import
    - **update_existing**: If True, update entities with existing IDs

    Returns import statistics including success/failure counts and any errors.
    """
    try:
        service = BulkOperationsService(neo4j_handler)
        result = service.import_entities(
            project_safe_name,
            request.entities,
            request.update_existing
        )

        # Check if project was not found
        if result.total == 0 and result.failed == 0 and result.errors:
            first_error = result.errors[0].get("error", "")
            if "not found" in first_error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=first_error
                )

        return BulkImportResultResponse(
            total=result.total,
            successful=result.successful,
            failed=result.failed,
            errors=result.errors,
            created_ids=result.created_ids
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk import failed: {str(e)}"
        )


@router.post(
    "/import/csv",
    response_model=BulkImportResultResponse,
    summary="Import entities from CSV",
    description="Import entities from CSV content with field mapping.",
    responses={
        200: {"description": "Import completed (may have partial success)"},
        400: {"description": "Invalid CSV or mapping"},
        404: {"description": "Project not found"},
    }
)
async def bulk_import_csv(
    project_safe_name: str,
    request: CSVImportRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import entities from CSV content.

    Imports entities from CSV data using a field mapping to convert
    CSV columns to entity profile fields.

    - **project_safe_name**: The URL-safe identifier for the project
    - **csv_content**: The CSV data as a string
    - **mapping**: Dictionary mapping CSV column names to entity field paths

    Example mapping:
    ```json
    {
        "first_name": "profile.core.first_name",
        "email": "profile.core.email",
        "twitter": "profile.social.twitter"
    }
    ```
    """
    try:
        service = BulkOperationsService(neo4j_handler)
        result = service.import_from_csv(
            project_safe_name,
            request.csv_content,
            request.mapping
        )

        # Check for project not found or CSV errors
        if result.errors:
            first_error = result.errors[0].get("error", "")
            if "not found" in first_error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=first_error
                )
            if "csv parsing error" in first_error.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=first_error
                )

        return BulkImportResultResponse(
            total=result.total,
            successful=result.successful,
            failed=result.failed,
            errors=result.errors,
            created_ids=result.created_ids
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV import failed: {str(e)}"
        )


@router.get(
    "/export",
    summary="Export entities",
    description="Export entities from a project in various formats.",
    responses={
        200: {
            "description": "Export successful",
            "content": {
                "application/json": {},
                "text/csv": {},
                "application/x-ndjson": {}
            }
        },
        400: {"description": "Invalid export options"},
        404: {"description": "Project not found"},
    }
)
async def bulk_export_entities(
    project_safe_name: str,
    format: str = Query(
        "json",
        description="Export format: json, csv, or jsonl"
    ),
    include_relationships: bool = Query(
        True,
        description="Include relationship data in export"
    ),
    include_files: bool = Query(
        False,
        description="Include file references in export"
    ),
    entity_ids: Optional[str] = Query(
        None,
        description="Comma-separated list of entity IDs to export (empty = all)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export entities from a project.

    Exports entity data in the specified format with optional filters.

    - **project_safe_name**: The URL-safe identifier for the project
    - **format**: Export format (json, csv, jsonl)
    - **include_relationships**: Include relationship/tag data
    - **include_files**: Include file reference data
    - **entity_ids**: Specific entity IDs to export (comma-separated)
    """
    try:
        # Parse entity IDs if provided
        entity_id_list = None
        if entity_ids:
            entity_id_list = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]

        # Validate format
        valid_formats = {"json", "csv", "jsonl"}
        if format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}"
            )

        options = BulkExportOptions(
            format=format,
            include_relationships=include_relationships,
            include_files=include_files,
            entity_ids=entity_id_list
        )

        service = BulkOperationsService(neo4j_handler)
        content = service.export_entities(project_safe_name, options)

        # Set appropriate content type
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "jsonl": "application/x-ndjson"
        }

        return Response(
            content=content,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f'attachment; filename="entities.{format}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post(
    "/export/csv",
    summary="Export specific fields to CSV",
    description="Export specific entity fields to CSV format.",
    responses={
        200: {
            "description": "CSV export successful",
            "content": {"text/csv": {}}
        },
        400: {"description": "Invalid field specification"},
        404: {"description": "Project not found"},
    }
)
async def export_entities_to_csv(
    project_safe_name: str,
    request: CSVExportRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export specific entity fields to CSV.

    Exports only the specified fields from all entities in CSV format.

    - **project_safe_name**: The URL-safe identifier for the project
    - **fields**: List of field paths to export (e.g., ["id", "profile.core.name"])
    """
    try:
        service = BulkOperationsService(neo4j_handler)
        content = service.export_to_csv(project_safe_name, request.fields)

        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="entities.csv"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate import data",
    description="Validate entity data before importing.",
    responses={
        200: {"description": "Validation completed"},
        400: {"description": "Invalid request data"},
    }
)
async def validate_import_data(
    project_safe_name: str,
    request: ValidationRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Validate entity data before import.

    Validates the structure and format of entity data without
    actually importing it. Useful for checking data before bulk import.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entities**: List of entity dictionaries to validate

    Returns validation results including any errors found.
    """
    try:
        service = BulkOperationsService(neo4j_handler)
        errors = service.validate_import_data(request.entities)

        return ValidationResponse(
            valid=len(errors) == 0,
            errors=errors
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )
