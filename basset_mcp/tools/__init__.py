"""
Basset Hound MCP Tools

This package contains modular tool implementations for the MCP server.
Each module handles a specific domain of functionality.

Modules:
- schema: Schema introspection and validation
- entities: Entity CRUD operations with query support
- relationships: Entity relationship management
- search: Full-text and identifier search
- projects: Project management
- reports: Report generation
- analysis: Graph analysis and visualization
- auto_linking: Duplicate detection and entity merging
- orphans: Orphan data management (unlinked identifiers)
- provenance: Data provenance and chain of custody tracking
- sock_puppets: Sock puppet identity management for investigations
- verification: Identifier verification (email, phone, crypto, etc.)
- investigations: Investigation lifecycle and case management
- browser_integration: Browser integration (autofill, evidence capture, session tracking)
- file_hashing: File hash computation and duplicate detection
- data_management: Data ID system for smart suggestions (Phase 43.1)
- suggestions: On-demand suggestion computation for entity relationships (Phase 43.4)
- linking: Linking actions for acting on suggestions (Phase 43.5)
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
from .orphans import register_orphan_tools
from .provenance import register_provenance_tools
from .sock_puppets import register_sock_puppet_tools
from .verification import register_verification_tools
from .investigations import register_investigation_tools
from .browser_integration import register_browser_integration_tools
from .file_hashing import register_file_hashing_tools
from .data_management import register_data_management_tools
from .suggestions import register_suggestion_tools
from .linking import register_linking_tools


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
    register_orphan_tools(mcp)
    register_provenance_tools(mcp)
    register_sock_puppet_tools(mcp)
    register_verification_tools(mcp)
    register_investigation_tools(mcp)
    register_browser_integration_tools(mcp)
    register_file_hashing_tools(mcp)
    register_data_management_tools(mcp)
    register_suggestion_tools(mcp)
    register_linking_tools(mcp)


__all__ = [
    "get_neo4j_handler",
    "get_schema_config",
    "reload_schema_config",
    "get_project_safe_name",
    "get_project_id_from_safe_name",
    "register_all_tools",
]
