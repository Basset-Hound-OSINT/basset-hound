"""
Frontend Component Specification API Router.

Provides REST endpoints for frontend developers to retrieve component
specifications for building React/Vue/vanilla JS applications.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.services.frontend_components import (
    ComponentSpec,
    ComponentType,
    Framework,
    get_all_component_specs,
    get_component_spec,
    generate_typescript_types,
    get_graph_viewer_spec,
    get_entity_card_spec,
    get_timeline_viewer_spec,
    get_import_wizard_spec,
    get_search_bar_spec,
)


router = APIRouter(prefix="/frontend", tags=["Frontend Components"])


@router.get(
    "/components",
    response_model=dict,
    summary="Get All Component Specifications",
    description="Returns specifications for all available frontend components",
)
async def get_all_components(
    framework: Framework = Query(
        default=Framework.REACT,
        description="Target frontend framework (react, vue, vanilla)"
    ),
):
    """
    Get specifications for all frontend components.

    Returns component definitions including props, state, events,
    styles, and API endpoints for each component.
    """
    specs = get_all_component_specs(framework)
    return {
        name: spec.model_dump() for name, spec in specs.items()
    }


@router.get(
    "/components/{component_type}",
    response_model=dict,
    summary="Get Component Specification",
    description="Returns specification for a specific component type",
)
async def get_component(
    component_type: str,
    framework: Framework = Query(
        default=Framework.REACT,
        description="Target frontend framework"
    ),
):
    """
    Get specification for a specific component.

    Args:
        component_type: Type of component (graph_viewer, entity_card, etc.)
        framework: Target frontend framework

    Returns:
        ComponentSpec with full component definition
    """
    # Map string to enum
    type_map = {
        "graph_viewer": ComponentType.GRAPH_VIEWER,
        "entity_card": ComponentType.ENTITY_CARD,
        "timeline_viewer": ComponentType.TIMELINE_VIEWER,
        "import_wizard": ComponentType.IMPORT_WIZARD,
        "search_bar": ComponentType.SEARCH_BAR,
    }

    comp_type = type_map.get(component_type.lower())
    if not comp_type:
        raise HTTPException(
            status_code=404,
            detail=f"Component type '{component_type}' not found. "
                   f"Available types: {list(type_map.keys())}"
        )

    spec = get_component_spec(comp_type, framework)
    if not spec:
        raise HTTPException(status_code=404, detail="Component not found")

    return spec.model_dump()


@router.get(
    "/components/types",
    response_model=List[str],
    summary="List Component Types",
    description="Returns list of available component types",
)
async def list_component_types():
    """Get list of all available component types."""
    return [ct.value for ct in ComponentType]


@router.get(
    "/typescript",
    response_model=dict,
    summary="Get TypeScript Definitions",
    description="Returns TypeScript type definitions for all components",
)
async def get_typescript_definitions():
    """
    Get TypeScript type definitions.

    Returns TypeScript code that can be saved to a .d.ts file
    for type-safe frontend development.
    """
    return {
        "types": generate_typescript_types(),
        "filename": "basset-hound.d.ts",
    }


@router.get(
    "/css-variables",
    response_model=dict,
    summary="Get CSS Variables",
    description="Returns CSS custom properties for theming",
)
async def get_css_variables():
    """
    Get all CSS custom properties used by components.

    These variables can be overridden to customize component theming.
    """
    # Collect all CSS variables from all components
    all_vars = {}
    for spec in get_all_component_specs(Framework.REACT).values():
        for style in spec.styles:
            all_vars.update(style.css_vars)

    return {
        "variables": all_vars,
        "css": "\n".join([f"  {k}: {v};" for k, v in all_vars.items()]),
        "usage": ":root {\n" + "\n".join([f"  {k}: {v};" for k, v in all_vars.items()]) + "\n}",
    }


@router.get(
    "/dependencies",
    response_model=dict,
    summary="Get NPM Dependencies",
    description="Returns NPM packages required by components",
)
async def get_dependencies():
    """
    Get all NPM dependencies required by components.

    Returns a list suitable for adding to package.json.
    """
    all_deps = set()
    for spec in get_all_component_specs(Framework.REACT).values():
        all_deps.update(spec.dependencies)

    return {
        "dependencies": sorted(list(all_deps)),
        "install_command": f"npm install {' '.join(sorted(list(all_deps)))}",
    }


@router.get(
    "/frameworks",
    response_model=List[str],
    summary="List Supported Frameworks",
    description="Returns list of supported frontend frameworks",
)
async def list_frameworks():
    """Get list of supported frontend frameworks."""
    return [f.value for f in Framework]
