"""
Basset Hound MCP Tools

This package contains modular tool implementations for the MCP server.
Each module handles a specific domain of functionality.
"""

from .base import (
    get_neo4j_handler,
    get_schema_config,
    reload_schema_config,
    get_project_safe_name,
    get_project_id_from_safe_name,
)

from .schema import register_schema_tools
from .entities import register_entity_tools
from .relationships import register_relationship_tools
from .search import register_search_tools
from .projects import register_project_tools
from .reports import register_report_tools
from .analysis import register_analysis_tools
from .auto_linking import register_auto_linking_tools


def register_all_tools(mcp):
    """Register all tool modules with the MCP server."""
    register_schema_tools(mcp)
    register_entity_tools(mcp)
    register_relationship_tools(mcp)
    register_search_tools(mcp)
    register_project_tools(mcp)
    register_report_tools(mcp)
    register_analysis_tools(mcp)
    register_auto_linking_tools(mcp)


__all__ = [
    "get_neo4j_handler",
    "get_schema_config",
    "reload_schema_config",
    "get_project_safe_name",
    "get_project_id_from_safe_name",
    "register_all_tools",
]
