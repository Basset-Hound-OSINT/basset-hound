"""
Base utilities for MCP tools.

Provides shared functionality for Neo4j handler access, schema configuration,
and project resolution used across all tool modules.
"""

import os
import sys
from typing import Optional, Dict, List

# Add parent directory to path to import neo4j_handler and config_loader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from neo4j_handler import Neo4jHandler
from config_loader import load_config, get_section_by_id, get_field_by_id

# Lazy initialization of Neo4j handler
_neo4j_handler: Optional[Neo4jHandler] = None

# Lazy initialization of schema config
_schema_config: Optional[Dict] = None


def get_schema_config() -> Dict:
    """
    Get or load the schema configuration from data_config.yaml.

    The config is loaded once and cached for the lifetime of the server.
    This enables dynamic schema introspection without repeated file reads.

    Returns:
        The parsed data_config.yaml as a dictionary
    """
    global _schema_config
    if _schema_config is None:
        _schema_config = load_config()
    return _schema_config


def reload_schema_config() -> Dict:
    """
    Force reload the schema configuration from data_config.yaml.

    Useful when the config file has been modified and needs to be refreshed.

    Returns:
        The freshly parsed data_config.yaml as a dictionary
    """
    global _schema_config
    _schema_config = load_config()
    return _schema_config


def get_neo4j_handler() -> Neo4jHandler:
    """Get or create Neo4j handler instance."""
    global _neo4j_handler
    if _neo4j_handler is None:
        _neo4j_handler = Neo4jHandler()
    return _neo4j_handler


def get_project_safe_name(project_id: str) -> Optional[str]:
    """Get project safe_name from project_id (which could be id or safe_name)."""
    handler = get_neo4j_handler()

    # First try treating project_id as safe_name
    project = handler.get_project(project_id)
    if project:
        return project_id

    # Otherwise search through all projects
    projects = handler.get_all_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p.get("safe_name")

    return None


def get_project_id_from_safe_name(safe_name: str) -> Optional[str]:
    """Get project id from safe_name."""
    handler = get_neo4j_handler()
    project = handler.get_project(safe_name)
    if project:
        return project.get("id")
    return None


def validate_entity_profile(profile: dict) -> tuple[bool, List[str]]:
    """
    Internal helper to validate entity profile data against schema.

    Args:
        profile: Profile data dictionary

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    from .schema import validate_profile_data
    result = validate_profile_data(profile)
    return result["valid"], result["errors"]
