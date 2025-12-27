"""
Templates Router for Basset Hound.

Provides API endpoints for managing custom report templates.
Supports CRUD operations, template validation, preview, import/export,
and duplication of templates.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, ConfigDict, Field

from ..services.template_service import (
    TemplateService,
    TemplateFormat,
    ReportTemplate,
    TemplateValidationError,
    TemplateNotFoundError,
    SystemTemplateError,
    get_template_service,
)


router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"},
    },
)


# ==================== Pydantic Models ====================


class TemplateCreate(BaseModel):
    """Schema for creating a new template."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Custom Report",
            "description": "My custom report template",
            "content": "<html><body><h1>{{ title }}</h1></body></html>",
            "styles": "body { font-family: sans-serif; }",
            "format": "html",
            "variables": ["title", "entities"]
        }
    })

    name: str = Field(
        ...,
        description="Display name for the template",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        default="",
        description="Description of the template",
        max_length=500,
    )
    content: str = Field(
        ...,
        description="Jinja2 template content (HTML/Markdown)",
    )
    styles: str = Field(
        default="",
        description="CSS styles for the template",
    )
    format: str = Field(
        default="html",
        description="Output format (html, pdf, markdown)",
    )
    variables: Optional[List[str]] = Field(
        default=None,
        description="List of required variable names",
    )


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Updated Template Name",
            "description": "Updated description",
            "content": "<html><body><h1>{{ title }}</h1>{{ content }}</body></html>"
        }
    })

    name: Optional[str] = Field(
        default=None,
        description="New display name",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="New description",
        max_length=500,
    )
    content: Optional[str] = Field(
        default=None,
        description="New Jinja2 template content",
    )
    styles: Optional[str] = Field(
        default=None,
        description="New CSS styles",
    )
    format: Optional[str] = Field(
        default=None,
        description="New output format",
    )
    variables: Optional[List[str]] = Field(
        default=None,
        description="New list of required variables",
    )


class TemplateResponse(BaseModel):
    """Schema for template response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Custom Report",
            "description": "My custom report template",
            "content": "<html><body><h1>{{ title }}</h1></body></html>",
            "styles": "body { font-family: sans-serif; }",
            "format": "html",
            "variables": ["title", "entities"],
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00",
            "created_by": "user123",
            "is_system": False
        }
    })

    id: str
    name: str
    description: str
    content: str
    styles: str
    format: str
    variables: List[str]
    created_at: str
    updated_at: str
    created_by: Optional[str]
    is_system: bool


class TemplateListItem(BaseModel):
    """Schema for template list item (condensed)."""
    id: str
    name: str
    description: str
    format: str
    is_system: bool
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    """Schema for template list response."""
    templates: List[TemplateListItem]
    count: int


class ValidationRequest(BaseModel):
    """Schema for template validation request."""
    content: str = Field(
        ...,
        description="Template content to validate",
    )


class ValidationResponse(BaseModel):
    """Schema for template validation response."""
    valid: bool
    variables: List[str]
    message: str


class PreviewRequest(BaseModel):
    """Schema for template preview request."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": {
                "title": "Sample Report",
                "entities": [{"id": "123", "name": "John Doe"}],
                "statistics": {"total_entities": 5}
            }
        }
    })

    data: Dict[str, Any] = Field(
        ...,
        description="Data to render the template with",
    )


class PreviewResponse(BaseModel):
    """Schema for template preview response."""
    rendered: str
    template_id: str
    template_name: str


class DuplicateRequest(BaseModel):
    """Schema for template duplication request."""
    new_name: Optional[str] = Field(
        default=None,
        description="Name for the duplicated template",
    )


class ExportRequest(BaseModel):
    """Schema for template export request."""
    template_ids: List[str] = Field(
        ...,
        description="List of template IDs to export",
    )


class ImportRequest(BaseModel):
    """Schema for template import request."""
    templates: List[Dict[str, Any]] = Field(
        ...,
        description="List of template data objects to import",
    )
    overwrite: bool = Field(
        default=False,
        description="Whether to overwrite existing templates with same name",
    )


class ImportResponse(BaseModel):
    """Schema for template import response."""
    imported: List[TemplateListItem]
    count: int
    message: str


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


# ==================== Helper Functions ====================


def _parse_format(format_str: str) -> TemplateFormat:
    """Parse format string to TemplateFormat enum."""
    try:
        return TemplateFormat(format_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {format_str}. Must be one of: html, pdf, markdown"
        )


def _template_to_response(template: ReportTemplate) -> TemplateResponse:
    """Convert ReportTemplate to TemplateResponse."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        content=template.content,
        styles=template.styles,
        format=template.format.value if isinstance(template.format, TemplateFormat) else template.format,
        variables=template.variables,
        created_at=template.created_at,
        updated_at=template.updated_at,
        created_by=template.created_by,
        is_system=template.is_system,
    )


def _template_to_list_item(template: ReportTemplate) -> TemplateListItem:
    """Convert ReportTemplate to TemplateListItem."""
    return TemplateListItem(
        id=template.id,
        name=template.name,
        description=template.description,
        format=template.format.value if isinstance(template.format, TemplateFormat) else template.format,
        is_system=template.is_system,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ==================== Endpoints ====================


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new template",
    description="Create a new custom report template with Jinja2 content.",
    responses={
        201: {"description": "Template created successfully"},
        400: {"description": "Invalid template data or syntax"},
    },
)
async def create_template(
    template_data: TemplateCreate,
) -> TemplateResponse:
    """
    Create a new custom report template.

    The template content should be valid Jinja2 syntax with HTML or Markdown.
    Variables like {{ title }}, {{ entities }}, {% for entity in entities %} are supported.

    - **name**: Display name for the template
    - **description**: Description of the template's purpose
    - **content**: Jinja2 template content
    - **styles**: CSS styles for PDF/HTML output
    - **format**: Output format (html, pdf, markdown)
    - **variables**: List of required variable names
    """
    service = get_template_service()

    try:
        template_format = _parse_format(template_data.format)

        template = service.create_template(
            name=template_data.name,
            description=template_data.description,
            content=template_data.content,
            styles=template_data.styles,
            format=template_format,
            variables=template_data.variables,
            created_by=None,  # Could be extracted from auth
        )

        return _template_to_response(template)

    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "",
    response_model=TemplateListResponse,
    summary="List all templates",
    description="Retrieve a list of all available templates with optional filtering.",
    responses={
        200: {"description": "List of templates"},
    },
)
async def list_templates(
    format: Optional[str] = Query(
        default=None,
        description="Filter by output format (html, pdf, markdown)",
    ),
    is_system: Optional[bool] = Query(
        default=None,
        description="Filter by system (True) or custom (False) templates",
    ),
) -> TemplateListResponse:
    """
    List all available templates.

    Templates are sorted with system templates first, then by name.

    - **format**: Optional filter by output format
    - **is_system**: Optional filter by system/custom template
    """
    service = get_template_service()

    template_format = None
    if format is not None:
        template_format = _parse_format(format)

    templates = service.list_templates(
        format=template_format,
        is_system=is_system,
    )

    items = [_template_to_list_item(t) for t in templates]

    return TemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get template by ID",
    description="Retrieve a specific template by its ID or name.",
    responses={
        200: {"description": "Template found"},
        404: {"description": "Template not found"},
    },
)
async def get_template(
    template_id: str,
) -> TemplateResponse:
    """
    Get a template by ID or name.

    - **template_id**: The template UUID or name
    """
    service = get_template_service()

    template = service.get_template(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )

    return _template_to_response(template)


@router.patch(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Update template",
    description="Update an existing custom template. System templates cannot be modified.",
    responses={
        200: {"description": "Template updated successfully"},
        400: {"description": "Invalid template data"},
        403: {"description": "Cannot modify system template"},
        404: {"description": "Template not found"},
    },
)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
) -> TemplateResponse:
    """
    Update an existing template.

    Only custom templates can be modified. System templates are read-only.

    - **template_id**: The template UUID
    - **name**: New display name (optional)
    - **description**: New description (optional)
    - **content**: New Jinja2 content (optional)
    - **styles**: New CSS styles (optional)
    - **format**: New output format (optional)
    - **variables**: New variable list (optional)
    """
    service = get_template_service()

    try:
        template_format = None
        if template_data.format is not None:
            template_format = _parse_format(template_data.format)

        template = service.update_template(
            template_id=template_id,
            name=template_data.name,
            description=template_data.description,
            content=template_data.content,
            styles=template_data.styles,
            format=template_format,
            variables=template_data.variables,
        )

        return _template_to_response(template)

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )
    except SystemTemplateError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system templates"
        )
    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description="Delete a custom template. System templates cannot be deleted.",
    responses={
        204: {"description": "Template deleted successfully"},
        403: {"description": "Cannot delete system template"},
        404: {"description": "Template not found"},
    },
)
async def delete_template(
    template_id: str,
) -> None:
    """
    Delete a template.

    Only custom templates can be deleted. System templates are protected.

    - **template_id**: The template UUID
    """
    service = get_template_service()

    try:
        service.delete_template(template_id)
        return None

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )
    except SystemTemplateError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system templates"
        )


@router.post(
    "/{template_id}/validate",
    response_model=ValidationResponse,
    summary="Validate template syntax",
    description="Validate the Jinja2 syntax of a template.",
    responses={
        200: {"description": "Validation result"},
        404: {"description": "Template not found"},
    },
)
async def validate_template(
    template_id: str,
) -> ValidationResponse:
    """
    Validate the syntax of an existing template.

    Returns validation status and list of variables found in the template.

    - **template_id**: The template UUID
    """
    service = get_template_service()

    template = service.get_template(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )

    try:
        result = service.validate_template(template.content)
        return ValidationResponse(
            valid=result["valid"],
            variables=result["variables"],
            message=result["message"],
        )
    except TemplateValidationError as e:
        return ValidationResponse(
            valid=False,
            variables=[],
            message=str(e),
        )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate template content",
    description="Validate arbitrary Jinja2 template content without saving.",
    responses={
        200: {"description": "Validation result"},
    },
)
async def validate_template_content(
    request: ValidationRequest,
) -> ValidationResponse:
    """
    Validate Jinja2 template content without saving.

    Useful for checking template syntax before creating or updating.

    - **content**: Template content to validate
    """
    service = get_template_service()

    try:
        result = service.validate_template(request.content)
        return ValidationResponse(
            valid=result["valid"],
            variables=result["variables"],
            message=result["message"],
        )
    except TemplateValidationError as e:
        return ValidationResponse(
            valid=False,
            variables=[],
            message=str(e),
        )


@router.post(
    "/{template_id}/preview",
    response_model=PreviewResponse,
    summary="Preview template with sample data",
    description="Render a template with provided data to preview the output.",
    responses={
        200: {"description": "Rendered preview"},
        400: {"description": "Rendering error"},
        404: {"description": "Template not found"},
    },
)
async def preview_template(
    template_id: str,
    request: PreviewRequest,
) -> PreviewResponse:
    """
    Preview a template by rendering it with sample data.

    Provide data matching the template's expected variables.

    - **template_id**: The template UUID
    - **data**: Dictionary of data to render the template with
    """
    service = get_template_service()

    template = service.get_template(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )

    try:
        rendered = service.render_template(
            template_id=template_id,
            data=request.data,
            include_styles=True,
        )

        return PreviewResponse(
            rendered=rendered,
            template_id=template.id,
            template_name=template.name,
        )

    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{template_id}/duplicate",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate template",
    description="Create a copy of an existing template as a new custom template.",
    responses={
        201: {"description": "Template duplicated successfully"},
        404: {"description": "Template not found"},
    },
)
async def duplicate_template(
    template_id: str,
    request: DuplicateRequest = Body(default=DuplicateRequest()),
) -> TemplateResponse:
    """
    Duplicate a template to create a new custom template.

    This works with both system and custom templates.

    - **template_id**: The template UUID to duplicate
    - **new_name**: Optional name for the new template
    """
    service = get_template_service()

    try:
        template = service.duplicate_template(
            template_id=template_id,
            new_name=request.new_name,
            created_by=None,
        )

        return _template_to_response(template)

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )


@router.post(
    "/export",
    summary="Export templates",
    description="Export multiple templates as JSON for backup or sharing.",
    responses={
        200: {"description": "Exported template data"},
    },
)
async def export_templates(
    request: ExportRequest,
) -> Dict[str, Any]:
    """
    Export multiple templates as JSON.

    The exported data can be imported into another Basset Hound instance.

    - **template_ids**: List of template IDs to export
    """
    service = get_template_service()

    return service.export_templates(request.template_ids)


@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import templates",
    description="Import templates from JSON data.",
    responses={
        201: {"description": "Templates imported successfully"},
        400: {"description": "Invalid template data"},
    },
)
async def import_templates(
    request: ImportRequest,
) -> ImportResponse:
    """
    Import templates from JSON data.

    Templates with invalid syntax or missing required fields will be skipped.

    - **templates**: List of template data objects
    - **overwrite**: Whether to overwrite existing templates with same name
    """
    service = get_template_service()

    try:
        imported = service.import_templates(
            data={"templates": request.templates},
            created_by=None,
            overwrite=request.overwrite,
        )

        items = [_template_to_list_item(t) for t in imported]

        return ImportResponse(
            imported=items,
            count=len(items),
            message=f"Successfully imported {len(items)} template(s)",
        )

    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
