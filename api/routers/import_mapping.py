"""
Import Mapping Router for Basset Hound.

Provides REST API endpoints for managing custom import field mappings.
Allows users to create, retrieve, update, and delete mapping configurations,
as well as apply mappings to transform data and preview results.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, ConfigDict, Field

from api.services.import_mapping import (
    get_import_mapping_service,
    ImportMappingConfig,
    FieldMapping,
    TransformationType,
    TransformationOptions,
    MappingValidationResult,
    MappingPreviewResult,
)


# Initialize the router
router = APIRouter(
    tags=["import-mapping"],
    responses={
        400: {"description": "Invalid request"},
        404: {"description": "Mapping not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateMappingRequest(BaseModel):
    """Request model for creating a new mapping."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "salesforce_contacts",
            "description": "Map Salesforce contact exports to entity format",
            "field_mappings": [
                {
                    "source_field": "FirstName",
                    "destination_field": "first_name",
                    "transformations": ["trim"],
                    "options": {},
                    "required": False,
                    "skip_if_empty": True
                }
            ],
            "source_format": "Salesforce CSV",
            "target_format": "Entity",
            "tags": ["salesforce", "contacts"]
        }
    })

    name: str = Field(..., description="Unique name for the mapping")
    description: Optional[str] = Field(None, description="Human-readable description")
    field_mappings: List[Dict[str, Any]] = Field(
        ...,
        description="List of field mappings",
        min_length=1
    )
    source_format: Optional[str] = Field(None, description="Source format description")
    target_format: Optional[str] = Field(None, description="Target format description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class UpdateMappingRequest(BaseModel):
    """Request model for updating an existing mapping."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "salesforce_contacts_v2",
            "description": "Updated Salesforce mapping",
            "field_mappings": [
                {
                    "source_field": "Email",
                    "destination_field": "email",
                    "transformations": ["lowercase", "trim"],
                    "options": {},
                    "required": True,
                    "skip_if_empty": False
                }
            ],
            "tags": ["salesforce", "contacts", "v2"]
        }
    })

    name: str = Field(..., description="Mapping name")
    description: Optional[str] = Field(None, description="Description")
    field_mappings: List[Dict[str, Any]] = Field(
        ...,
        description="Field mappings",
        min_length=1
    )
    source_format: Optional[str] = Field(None, description="Source format")
    target_format: Optional[str] = Field(None, description="Target format")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    tags: List[str] = Field(default_factory=list, description="Tags")


class ApplyMappingRequest(BaseModel):
    """Request model for applying a mapping to data."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": [
                {
                    "FirstName": "  John  ",
                    "LastName": "Doe",
                    "Email": "JOHN.DOE@EXAMPLE.COM"
                }
            ]
        }
    })

    data: List[Dict[str, Any]] = Field(
        ...,
        description="Data to transform (list of dictionaries)",
        min_length=1
    )


class ValidateMappingRequest(BaseModel):
    """Request model for validating a mapping configuration."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "config": {
                "name": "test_mapping",
                "field_mappings": [
                    {
                        "source_field": "email",
                        "destination_field": "contact_email",
                        "transformations": ["lowercase", "trim"]
                    }
                ]
            },
            "sample_data": [
                {"email": "  TEST@EXAMPLE.COM  "}
            ]
        }
    })

    config: Dict[str, Any] = Field(..., description="Mapping configuration to validate")
    sample_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional sample data for validation testing"
    )


class PreviewMappingRequest(BaseModel):
    """Request model for previewing a mapping transformation."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "config": {
                "name": "preview_test",
                "field_mappings": [
                    {
                        "source_field": "full_name",
                        "destination_field": "name",
                        "transformations": ["trim", "titlecase"]
                    }
                ]
            },
            "sample_data": [
                {"full_name": "  john doe  "}
            ],
            "limit": 5
        }
    })

    config: Dict[str, Any] = Field(..., description="Mapping configuration")
    sample_data: List[Dict[str, Any]] = Field(
        ...,
        description="Sample data to preview",
        min_length=1
    )
    limit: int = Field(5, ge=1, le=100, description="Maximum number of records to preview")


class MappingResponse(BaseModel):
    """Response model for a single mapping."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "salesforce_contacts",
            "description": "Salesforce contact mapping",
            "field_mappings": [],
            "source_format": "CSV",
            "target_format": "Entity",
            "metadata": {},
            "created_at": "2025-01-15T10:30:00",
            "updated_at": "2025-01-15T10:30:00",
            "version": 1,
            "tags": ["salesforce"]
        }
    })

    id: str
    name: str
    description: Optional[str]
    field_mappings: List[Dict[str, Any]]
    source_format: Optional[str]
    target_format: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: int
    tags: List[str]


class MappingListResponse(BaseModel):
    """Response model for listing mappings."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "mappings": [],
            "total": 0
        }
    })

    mappings: List[MappingResponse] = Field(..., description="List of mappings")
    total: int = Field(..., description="Total number of mappings")


class ApplyMappingResponse(BaseModel):
    """Response model for applying a mapping."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "transformed_data": [
                {"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com"}
            ],
            "records_processed": 1
        }
    })

    success: bool = Field(..., description="Whether the operation succeeded")
    transformed_data: List[Dict[str, Any]] = Field(..., description="Transformed data")
    records_processed: int = Field(..., description="Number of records processed")


class ValidationResponse(BaseModel):
    """Response model for validation results."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
    })

    is_valid: bool = Field(..., description="Whether the configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class PreviewResponse(BaseModel):
    """Response model for preview results."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "original_data": {"full_name": "  john doe  "},
            "transformed_data": {"name": "John Doe"},
            "field_results": {},
            "errors": []
        }
    })

    success: bool = Field(..., description="Whether preview succeeded")
    original_data: Dict[str, Any] = Field(..., description="Original input data")
    transformed_data: Dict[str, Any] = Field(..., description="Transformed output data")
    field_results: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-field transformation details"
    )
    errors: List[str] = Field(default_factory=list, description="Preview errors")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Mapping deleted successfully"
        }
    })

    success: bool = Field(..., description="Whether deletion succeeded")
    message: str = Field(..., description="Status message")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _convert_to_field_mapping(data: Dict[str, Any]) -> FieldMapping:
    """Convert dictionary to FieldMapping object."""
    return FieldMapping.from_dict(data)


def _convert_to_import_mapping_config(data: Dict[str, Any]) -> ImportMappingConfig:
    """Convert dictionary to ImportMappingConfig object."""
    return ImportMappingConfig.from_dict(data)


def _mapping_to_response(config: ImportMappingConfig) -> MappingResponse:
    """Convert ImportMappingConfig to MappingResponse."""
    config_dict = config.to_dict()
    return MappingResponse(
        id=config_dict["id"],
        name=config_dict["name"],
        description=config_dict.get("description"),
        field_mappings=config_dict.get("field_mappings", []),
        source_format=config_dict.get("source_format"),
        target_format=config_dict.get("target_format"),
        metadata=config_dict.get("metadata", {}),
        created_at=config_dict.get("created_at", ""),
        updated_at=config_dict.get("updated_at", ""),
        version=config_dict.get("version", 1),
        tags=config_dict.get("tags", [])
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/import-mappings",
    response_model=MappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new import mapping",
    description="Create a new field mapping configuration for transforming imported data.",
    responses={
        201: {"description": "Mapping created successfully"},
        400: {"description": "Invalid mapping configuration"},
    }
)
async def create_mapping(request: CreateMappingRequest = Body(...)):
    """
    Create a new import mapping configuration.

    Creates a reusable mapping that defines how to transform source data fields
    to destination fields with optional transformations.

    - **name**: Unique name for the mapping
    - **description**: Human-readable description (optional)
    - **field_mappings**: List of field mapping definitions
    - **source_format**: Description of source format (optional)
    - **target_format**: Description of target format (optional)
    - **metadata**: Additional metadata (optional)
    - **tags**: Tags for categorization (optional)
    """
    try:
        service = get_import_mapping_service()

        # Build the config
        config_data = {
            "name": request.name,
            "description": request.description,
            "field_mappings": request.field_mappings,
            "source_format": request.source_format,
            "target_format": request.target_format,
            "metadata": request.metadata,
            "tags": request.tags,
        }

        config = _convert_to_import_mapping_config(config_data)
        created_config = service.create_mapping(config)

        return _mapping_to_response(created_config)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create mapping: {str(e)}"
        )


@router.get(
    "/import-mappings",
    response_model=MappingListResponse,
    summary="List all import mappings",
    description="Retrieve all import mapping configurations with optional filtering.",
    responses={
        200: {"description": "Mappings retrieved successfully"},
    }
)
async def list_mappings(
    tags: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List all import mapping configurations.

    Supports filtering by tags and search query.

    - **tags**: Comma-separated list of tags to filter by (optional)
    - **search**: Search string to match in name or description (optional)
    """
    try:
        service = get_import_mapping_service()

        # Parse tags parameter
        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        mappings = service.list_mappings(tags=tags_list, search=search)

        return MappingListResponse(
            mappings=[_mapping_to_response(m) for m in mappings],
            total=len(mappings)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list mappings: {str(e)}"
        )


@router.get(
    "/import-mappings/{mapping_id}",
    response_model=MappingResponse,
    summary="Get a specific import mapping",
    description="Retrieve a single import mapping configuration by ID.",
    responses={
        200: {"description": "Mapping retrieved successfully"},
        404: {"description": "Mapping not found"},
    }
)
async def get_mapping(mapping_id: str):
    """
    Get a specific import mapping configuration.

    Retrieves the full configuration including all field mappings and metadata.

    - **mapping_id**: Unique identifier of the mapping
    """
    try:
        service = get_import_mapping_service()
        mapping = service.get_mapping(mapping_id)

        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID '{mapping_id}' not found"
            )

        return _mapping_to_response(mapping)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mapping: {str(e)}"
        )


@router.put(
    "/import-mappings/{mapping_id}",
    response_model=MappingResponse,
    summary="Update an import mapping",
    description="Update an existing import mapping configuration.",
    responses={
        200: {"description": "Mapping updated successfully"},
        400: {"description": "Invalid mapping configuration"},
        404: {"description": "Mapping not found"},
    }
)
async def update_mapping(
    mapping_id: str,
    request: UpdateMappingRequest = Body(...)
):
    """
    Update an existing import mapping configuration.

    Updates the mapping configuration while preserving the ID and creation timestamp.
    Version number is automatically incremented.

    - **mapping_id**: Unique identifier of the mapping to update
    - **request**: Updated mapping configuration
    """
    try:
        service = get_import_mapping_service()

        # Build the updated config
        config_data = {
            "name": request.name,
            "description": request.description,
            "field_mappings": request.field_mappings,
            "source_format": request.source_format,
            "target_format": request.target_format,
            "metadata": request.metadata,
            "tags": request.tags,
        }

        config = _convert_to_import_mapping_config(config_data)
        updated_config = service.update_mapping(mapping_id, config)

        if updated_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID '{mapping_id}' not found"
            )

        return _mapping_to_response(updated_config)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update mapping: {str(e)}"
        )


@router.delete(
    "/import-mappings/{mapping_id}",
    response_model=DeleteResponse,
    summary="Delete an import mapping",
    description="Delete an import mapping configuration.",
    responses={
        200: {"description": "Mapping deleted successfully"},
        404: {"description": "Mapping not found"},
    }
)
async def delete_mapping(mapping_id: str):
    """
    Delete an import mapping configuration.

    Permanently removes the mapping configuration from storage.

    - **mapping_id**: Unique identifier of the mapping to delete
    """
    try:
        service = get_import_mapping_service()
        success = service.delete_mapping(mapping_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID '{mapping_id}' not found"
            )

        return DeleteResponse(
            success=True,
            message=f"Mapping '{mapping_id}' deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete mapping: {str(e)}"
        )


@router.post(
    "/import-mappings/{mapping_id}/apply",
    response_model=ApplyMappingResponse,
    summary="Apply a mapping to data",
    description="Apply an import mapping to transform data.",
    responses={
        200: {"description": "Mapping applied successfully"},
        400: {"description": "Invalid data"},
        404: {"description": "Mapping not found"},
    }
)
async def apply_mapping(
    mapping_id: str,
    request: ApplyMappingRequest = Body(...)
):
    """
    Apply a mapping configuration to transform data.

    Transforms the provided data according to the mapping configuration,
    applying all defined field mappings and transformations.

    - **mapping_id**: Unique identifier of the mapping to apply
    - **data**: List of data records to transform
    """
    try:
        service = get_import_mapping_service()

        # Verify mapping exists
        mapping = service.get_mapping(mapping_id)
        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID '{mapping_id}' not found"
            )

        # Apply the mapping
        transformed_data = service.apply_mapping(request.data, mapping_id)

        return ApplyMappingResponse(
            success=True,
            transformed_data=transformed_data,
            records_processed=len(request.data)
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply mapping: {str(e)}"
        )


@router.post(
    "/import-mappings/validate",
    response_model=ValidationResponse,
    summary="Validate a mapping configuration",
    description="Validate a mapping configuration without creating it.",
    responses={
        200: {"description": "Validation completed"},
        400: {"description": "Invalid request"},
    }
)
async def validate_mapping(request: ValidateMappingRequest = Body(...)):
    """
    Validate a mapping configuration.

    Checks the mapping configuration for errors and warnings without
    creating or persisting it. Optionally tests against sample data.

    - **config**: Mapping configuration to validate
    - **sample_data**: Optional sample data for validation testing
    """
    try:
        service = get_import_mapping_service()

        # Convert config to ImportMappingConfig
        config = _convert_to_import_mapping_config(request.config)

        # Validate the configuration
        validation_result = service.validate_mapping(config)

        return ValidationResponse(
            is_valid=validation_result.is_valid,
            errors=validation_result.errors,
            warnings=validation_result.warnings
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post(
    "/import-mappings/preview",
    response_model=PreviewResponse,
    summary="Preview a mapping transformation",
    description="Preview how a mapping will transform sample data.",
    responses={
        200: {"description": "Preview completed"},
        400: {"description": "Invalid request"},
    }
)
async def preview_mapping(request: PreviewMappingRequest = Body(...)):
    """
    Preview a mapping transformation on sample data.

    Shows detailed information about how each field will be transformed,
    useful for testing and debugging mapping configurations.

    - **config**: Mapping configuration to preview
    - **sample_data**: Sample data to transform (first record used)
    - **limit**: Maximum number of records to preview (default: 5)
    """
    try:
        service = get_import_mapping_service()

        # Convert config to ImportMappingConfig
        config = _convert_to_import_mapping_config(request.config)

        # Get the first record for preview
        sample_data = request.sample_data[0] if request.sample_data else {}

        # Preview the mapping
        preview_result = service.preview_mapping(sample_data, config)

        return PreviewResponse(
            success=preview_result.success,
            original_data=preview_result.original_data,
            transformed_data=preview_result.transformed_data,
            field_results=preview_result.field_results,
            errors=preview_result.errors
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}"
        )
