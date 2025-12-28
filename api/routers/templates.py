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
    TemplateType,
    VariableType,
    TemplateVariable,
    ReportTemplate,
    TemplateValidationError,
    TemplateNotFoundError,
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


class TemplateVariableCreate(BaseModel):
    """Schema for creating a template variable."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Variable name")
    type: str = Field(default="string", description="Variable type (string, list, dict, number, boolean)")
    required: bool = Field(default=True, description="Whether the variable is required")
    default_value: Optional[Any] = Field(default=None, description="Default value")
    description: str = Field(default="", description="Variable description")


class TemplateVariableResponse(BaseModel):
    """Schema for template variable response."""
    name: str
    type: str
    required: bool
    default_value: Optional[Any]
    description: str


class TemplateCreate(BaseModel):
    """Schema for creating a new template."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Custom Report",
            "template_type": "custom",
            "content": "<html><body><h1>{{ title }}</h1></body></html>",
            "description": "My custom report template",
            "variables": [
                {"name": "title", "type": "string", "required": True}
            ]
        }
    })

    name: str = Field(
        ...,
        description="Display name for the template",
        min_length=1,
        max_length=100,
    )
    template_type: str = Field(
        default="custom",
        description="Type of template (entity_report, project_summary, relationship_graph, timeline, custom)",
    )
    content: str = Field(
        ...,
        description="Jinja2 template content",
    )
    variables: Optional[List[TemplateVariableCreate]] = Field(
        default=None,
        description="List of expected variables",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the template",
        max_length=500,
    )


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Updated Template Name",
            "content": "<html><body><h1>{{ title }}</h1>{{ content }}</body></html>",
            "description": "Updated description"
        }
    })

    name: Optional[str] = Field(
        default=None,
        description="New display name",
        min_length=1,
        max_length=100,
    )
    content: Optional[str] = Field(
        default=None,
        description="New Jinja2 template content",
    )
    variables: Optional[List[TemplateVariableCreate]] = Field(
        default=None,
        description="New list of required variables",
    )
    description: Optional[str] = Field(
        default=None,
        description="New description",
        max_length=500,
    )


class TemplateResponse(BaseModel):
    """Schema for template response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Custom Report",
            "description": "My custom report template",
            "template_type": "custom",
            "content": "<html><body><h1>{{ title }}</h1></body></html>",
            "variables": [
                {"name": "title", "type": "string", "required": True, "default_value": None, "description": ""}
            ],
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00",
            "is_default": False,
            "author": None
        }
    })

    id: str
    name: str
    description: Optional[str]
    template_type: str
    content: str
    variables: List[TemplateVariableResponse]
    created_at: str
    updated_at: str
    is_default: bool
    author: Optional[str]


class TemplateListItem(BaseModel):
    """Schema for template list item (condensed)."""
    id: str
    name: str
    description: Optional[str]
    template_type: str
    is_default: bool
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
    error: Optional[str] = None


class RenderRequest(BaseModel):
    """Schema for template render request."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "context": {
                "title": "Sample Report",
                "entity": {"id": "123", "name": "John Doe"},
            }
        }
    })

    context: Dict[str, Any] = Field(
        ...,
        description="Context data to render the template with",
    )


class RenderResponse(BaseModel):
    """Schema for template render response."""
    rendered: str
    template_id: str
    template_name: str


class PreviewRequest(BaseModel):
    """Schema for template preview request."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "sample_data": {
                "title": "Sample Report",
                "entities": [{"id": "123", "name": "John Doe"}],
            }
        }
    })

    sample_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Sample data to preview the template with",
    )


class PreviewResponse(BaseModel):
    """Schema for template preview response."""
    rendered: str
    template_id: str
    template_name: str


class DuplicateRequest(BaseModel):
    """Schema for template duplication request."""
    new_name: str = Field(
        ...,
        description="Name for the duplicated template",
        min_length=1,
        max_length=100,
    )


class ImportRequest(BaseModel):
    """Schema for template import request."""
    template_data: Dict[str, Any] = Field(
        ...,
        description="Template data object to import",
    )


class ExportResponse(BaseModel):
    """Schema for template export response."""
    id: str
    name: str
    description: Optional[str]
    template_type: str
    content: str
    variables: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    is_default: bool
    author: Optional[str]
    exported_at: str
    export_version: str


# ==================== Helper Functions ====================


def _parse_template_type(type_str: str) -> TemplateType:
    """Parse template type string to TemplateType enum."""
    try:
        return TemplateType(type_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template type: {type_str}. Must be one of: entity_report, project_summary, relationship_graph, timeline, custom"
        )


def _parse_variable_type(type_str: str) -> VariableType:
    """Parse variable type string to VariableType enum."""
    try:
        return VariableType(type_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid variable type: {type_str}. Must be one of: string, list, dict, number, boolean"
        )


def _convert_variables(variables: Optional[List[TemplateVariableCreate]]) -> Optional[List[TemplateVariable]]:
    """Convert request variables to service variables."""
    if variables is None:
        return None
    return [
        TemplateVariable(
            name=v.name,
            type=_parse_variable_type(v.type),
            required=v.required,
            default_value=v.default_value,
            description=v.description,
        )
        for v in variables
    ]


def _template_to_response(template: ReportTemplate) -> TemplateResponse:
    """Convert ReportTemplate to TemplateResponse."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_type=template.template_type.value,
        content=template.content,
        variables=[
            TemplateVariableResponse(
                name=v.name,
                type=v.type.value,
                required=v.required,
                default_value=v.default_value,
                description=v.description,
            )
            for v in template.variables
        ],
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        is_default=template.is_default,
        author=template.author,
    )


def _template_to_list_item(template: ReportTemplate) -> TemplateListItem:
    """Convert ReportTemplate to TemplateListItem."""
    return TemplateListItem(
        id=template.id,
        name=template.name,
        description=template.description,
        template_type=template.template_type.value,
        is_default=template.is_default,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
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

    The template content should be valid Jinja2 syntax.
    Variables like {{ title }}, {{ entities }}, {% for entity in entities %} are supported.

    - **name**: Display name for the template
    - **template_type**: Type of template (entity_report, project_summary, relationship_graph, timeline, custom)
    - **content**: Jinja2 template content
    - **variables**: List of expected variables (optional, auto-extracted if not provided)
    - **description**: Optional description
    """
    service = get_template_service()

    try:
        template_type = _parse_template_type(template_data.template_type)
        variables = _convert_variables(template_data.variables)

        template = service.create_template(
            name=template_data.name,
            template_type=template_type,
            content=template_data.content,
            variables=variables,
            description=template_data.description,
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
    description="Retrieve a list of all available templates with optional type filtering.",
    responses={
        200: {"description": "List of templates"},
    },
)
async def list_templates(
    template_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by template type (entity_report, project_summary, relationship_graph, timeline, custom)",
    ),
) -> TemplateListResponse:
    """
    List all available templates.

    Templates are sorted with default templates first, then by name.

    - **type**: Optional filter by template type
    """
    service = get_template_service()

    parsed_type = None
    if template_type is not None:
        parsed_type = _parse_template_type(template_type)

    templates = service.get_templates(template_type=parsed_type)

    items = [_template_to_list_item(t) for t in templates]

    return TemplateListResponse(
        templates=items,
        count=len(items),
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get template by ID",
    description="Retrieve a specific template by its ID.",
    responses={
        200: {"description": "Template found"},
        404: {"description": "Template not found"},
    },
)
async def get_template(
    template_id: str,
) -> TemplateResponse:
    """
    Get a template by ID.

    - **template_id**: The template UUID
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
    description="Update an existing custom template. Default templates cannot be modified.",
    responses={
        200: {"description": "Template updated successfully"},
        400: {"description": "Invalid template data or cannot modify default template"},
        404: {"description": "Template not found"},
    },
)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
) -> TemplateResponse:
    """
    Update an existing template.

    Only custom templates can be modified. Default templates are read-only.

    - **template_id**: The template UUID
    - **name**: New display name (optional)
    - **content**: New Jinja2 content (optional)
    - **variables**: New variable list (optional)
    - **description**: New description (optional)
    """
    service = get_template_service()

    try:
        variables = _convert_variables(template_data.variables)

        template = service.update_template(
            template_id=template_id,
            name=template_data.name,
            content=template_data.content,
            variables=variables,
            description=template_data.description,
        )

        return _template_to_response(template)

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
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
    description="Delete a custom template. Default templates cannot be deleted.",
    responses={
        204: {"description": "Template deleted successfully"},
        400: {"description": "Cannot delete default template"},
        404: {"description": "Template not found"},
    },
)
async def delete_template(
    template_id: str,
) -> None:
    """
    Delete a template.

    Only custom templates can be deleted. Default templates are protected.

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
    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{template_id}/render",
    response_model=RenderResponse,
    summary="Render template with context",
    description="Render a template with provided context data.",
    responses={
        200: {"description": "Rendered template"},
        400: {"description": "Rendering error"},
        404: {"description": "Template not found"},
    },
)
async def render_template(
    template_id: str,
    request: RenderRequest,
) -> RenderResponse:
    """
    Render a template with the provided context.

    Provide context matching the template's expected variables.

    - **template_id**: The template UUID
    - **context**: Dictionary of data to render the template with
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
            context=request.context,
        )

        return RenderResponse(
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

    is_valid, error_msg = service.validate_template(request.content)

    return ValidationResponse(
        valid=is_valid,
        error=error_msg,
    )


@router.post(
    "/{template_id}/preview",
    response_model=PreviewResponse,
    summary="Preview template with sample data",
    description="Render a template with sample data to preview the output.",
    responses={
        200: {"description": "Rendered preview"},
        400: {"description": "Rendering error"},
        404: {"description": "Template not found"},
    },
)
async def preview_template(
    template_id: str,
    request: PreviewRequest = Body(default=PreviewRequest()),
) -> PreviewResponse:
    """
    Preview a template by rendering it with sample data.

    If no sample data is provided, default/generated values will be used.

    - **template_id**: The template UUID
    - **sample_data**: Optional dictionary of sample data
    """
    service = get_template_service()

    template = service.get_template(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )

    try:
        rendered = service.preview_template(
            template_id=template_id,
            sample_data=request.sample_data,
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
    request: DuplicateRequest,
) -> TemplateResponse:
    """
    Duplicate a template to create a new custom template.

    This works with both default and custom templates.

    - **template_id**: The template UUID to duplicate
    - **new_name**: Name for the new template
    """
    service = get_template_service()

    try:
        template = service.duplicate_template(
            template_id=template_id,
            new_name=request.new_name,
        )

        return _template_to_response(template)

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )


@router.get(
    "/{template_id}/export",
    response_model=ExportResponse,
    summary="Export template",
    description="Export a template as JSON for sharing or backup.",
    responses={
        200: {"description": "Exported template data"},
        404: {"description": "Template not found"},
    },
)
async def export_template(
    template_id: str,
) -> ExportResponse:
    """
    Export a template as JSON.

    The exported data can be imported into another Basset Hound instance.

    - **template_id**: The template UUID to export
    """
    service = get_template_service()

    try:
        export_data = service.export_template(template_id)

        return ExportResponse(
            id=export_data["id"],
            name=export_data["name"],
            description=export_data["description"],
            template_type=export_data["template_type"],
            content=export_data["content"],
            variables=export_data["variables"],
            created_at=export_data["created_at"],
            updated_at=export_data["updated_at"],
            is_default=export_data["is_default"],
            author=export_data["author"],
            exported_at=export_data["exported_at"],
            export_version=export_data["export_version"],
        )

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )


@router.post(
    "/import",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import template",
    description="Import a template from JSON data.",
    responses={
        201: {"description": "Template imported successfully"},
        400: {"description": "Invalid template data"},
    },
)
async def import_template(
    request: ImportRequest,
) -> TemplateResponse:
    """
    Import a template from JSON data.

    - **template_data**: Template data object containing name, content, etc.
    """
    service = get_template_service()

    try:
        template = service.import_template(request.template_data)

        return _template_to_response(template)

    except TemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
