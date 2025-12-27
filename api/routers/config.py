"""
FastAPI router for configuration management.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
import yaml
import os

from ..dependencies import Neo4jDep, ConfigDep, get_neo4j_handler, get_app_config
from config_loader import load_config


router = APIRouter(
    prefix="/config",
    tags=["config"],
)


# Pydantic models for configuration
class FieldConfig(BaseModel):
    """Configuration for a single field."""
    id: str
    label: str
    type: str = "text"
    placeholder: Optional[str] = None
    required: Optional[bool] = False
    icon: Optional[str] = None
    url_pattern: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None


class SectionConfig(BaseModel):
    """Configuration for a section of fields."""
    id: str
    label: str
    icon: Optional[str] = None
    description: Optional[str] = None
    fields: List[FieldConfig]


class DataConfig(BaseModel):
    """Full data configuration schema."""
    version: Optional[str] = "1.0"
    sections: List[SectionConfig]
    metadata: Optional[Dict[str, Any]] = None


class ConfigResponse(BaseModel):
    """Response model for configuration."""
    sections: List[Dict[str, Any]]
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AvailableIdentifiersResponse(BaseModel):
    """Response model for available identifier types."""
    identifiers: List[Dict[str, Any]]
    total: int


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    Get the current data configuration.
    """
    try:
        config = load_config()
        return ConfigResponse(
            sections=config.get('sections', []),
            version=config.get('version'),
            metadata=config.get('metadata')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {str(e)}"
        )


@router.get("/enhanced", response_model=ConfigResponse)
async def get_enhanced_config():
    """
    Get the enhanced data configuration with all social networks.
    """
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data_config_enhanced.yaml')

        if not os.path.exists(config_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enhanced configuration file not found"
            )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        return ConfigResponse(
            sections=config.get('sections', []),
            version=config.get('version'),
            metadata=config.get('metadata')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load enhanced configuration: {str(e)}"
        )


@router.put("/", response_model=ConfigResponse)
async def update_config(
    config: DataConfig,
    neo4j: Neo4jDep
):
    """
    Update the data configuration.

    This will also update the Neo4j schema to match the new configuration.
    """
    try:
        config_data = {
            'sections': [s.model_dump() for s in config.sections],
            'version': config.version,
            'metadata': config.metadata
        }

        # Save to YAML file
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data_config.yaml')

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Update Neo4j schema
        neo4j.setup_schema_from_config(config_data)

        return ConfigResponse(
            sections=config_data['sections'],
            version=config_data.get('version'),
            metadata=config_data.get('metadata')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.get("/sections", response_model=List[Dict[str, Any]])
async def get_sections():
    """
    Get list of all configuration sections.
    """
    try:
        config = load_config()
        sections = []

        for section in config.get('sections', []):
            sections.append({
                'id': section.get('id'),
                'label': section.get('label'),
                'icon': section.get('icon'),
                'description': section.get('description'),
                'field_count': len(section.get('fields', []))
            })

        return sections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sections: {str(e)}"
        )


@router.get("/sections/{section_id}", response_model=Dict[str, Any])
async def get_section(section_id: str):
    """
    Get a specific section by ID.
    """
    try:
        config = load_config()

        for section in config.get('sections', []):
            if section.get('id') == section_id:
                return section

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get section: {str(e)}"
        )


@router.get("/identifiers", response_model=AvailableIdentifiersResponse)
async def get_available_identifiers():
    """
    Get all available identifier types from the enhanced configuration.

    This is useful for external applications to know what types of
    identifiers can be stored for entities.
    """
    try:
        # Try enhanced config first, fall back to regular
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data_config_enhanced.yaml')

        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data_config.yaml')

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        identifiers = []

        for section in config.get('sections', []):
            section_info = {
                'section_id': section.get('id'),
                'section_label': section.get('label')
            }

            for field in section.get('fields', []):
                identifiers.append({
                    **section_info,
                    'field_id': field.get('id'),
                    'field_label': field.get('label'),
                    'field_type': field.get('type', 'text'),
                    'url_pattern': field.get('url_pattern'),
                    'required': field.get('required', False)
                })

        return AvailableIdentifiersResponse(
            identifiers=identifiers,
            total=len(identifiers)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get identifiers: {str(e)}"
        )


@router.get("/field-types", response_model=List[str])
async def get_field_types():
    """
    Get list of supported field types.
    """
    return [
        "text",
        "textarea",
        "number",
        "email",
        "url",
        "date",
        "datetime",
        "phone",
        "file",
        "image",
        "select",
        "multiselect",
        "checkbox",
        "radio",
        "location",
        "address",
        "cryptocurrency",
        "social_handle"
    ]


@router.post("/validate", response_model=Dict[str, Any])
async def validate_config(config: DataConfig):
    """
    Validate a configuration without saving it.
    """
    errors = []
    warnings = []

    section_ids = set()
    field_ids = set()

    for section in config.sections:
        # Check for duplicate section IDs
        if section.id in section_ids:
            errors.append(f"Duplicate section ID: {section.id}")
        section_ids.add(section.id)

        if not section.fields:
            warnings.append(f"Section '{section.label}' has no fields")

        for field in section.fields:
            # Check for duplicate field IDs within section
            full_field_id = f"{section.id}.{field.id}"
            if full_field_id in field_ids:
                errors.append(f"Duplicate field ID: {full_field_id}")
            field_ids.add(full_field_id)

            # Validate URL patterns
            if field.url_pattern:
                if '{value}' not in field.url_pattern:
                    warnings.append(f"Field '{field.label}' URL pattern missing {{value}} placeholder")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'section_count': len(config.sections),
        'field_count': len(field_ids)
    }
