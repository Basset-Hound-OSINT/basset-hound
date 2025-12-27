"""
Dependency injection for the Basset Hound FastAPI application.

Provides dependency functions for Neo4j database connections,
authentication, and other shared resources.
"""

import sys
from pathlib import Path
from typing import Annotated, Generator, Optional

from fastapi import Depends, HTTPException, status

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j_handler import Neo4jHandler
from config_loader import load_config

from api.config import Settings, get_settings


# Global Neo4j handler instance (managed by lifespan)
_neo4j_handler: Optional[Neo4jHandler] = None

# Global configuration cache
_app_config: Optional[dict] = None

# Current project context (in-memory state)
_current_project: Optional[dict] = None


def get_neo4j_handler() -> Neo4jHandler:
    """
    Get the Neo4j handler instance.

    Raises:
        HTTPException: If Neo4j handler is not initialized.
    """
    if _neo4j_handler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    return _neo4j_handler


def set_neo4j_handler(handler: Optional[Neo4jHandler]) -> None:
    """
    Set the global Neo4j handler instance.

    Called by lifespan events to initialize/cleanup the handler.
    """
    global _neo4j_handler
    _neo4j_handler = handler


def get_app_config() -> dict:
    """
    Get the application configuration from data_config.yaml.

    Returns:
        dict: The loaded configuration dictionary.

    Raises:
        HTTPException: If configuration cannot be loaded.
    """
    global _app_config

    if _app_config is None:
        try:
            _app_config = load_config()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load configuration: {str(e)}"
            )

    return _app_config


def refresh_app_config() -> dict:
    """
    Reload and return the application configuration.

    Forces a fresh load of the configuration file.
    """
    global _app_config
    _app_config = None
    return get_app_config()


def set_app_config(config: dict) -> None:
    """
    Update the cached application configuration.
    """
    global _app_config
    _app_config = config


def load_config_file() -> dict:
    """
    Load configuration directly from the YAML file.

    Unlike get_app_config, this always reads from the file,
    useful for configuration endpoints that need fresh data.

    Returns:
        dict: The configuration dictionary from the file.
    """
    return load_config()


# Alias for compatibility
get_config = get_app_config


def get_current_project() -> Optional[dict]:
    """
    Get the current project context.

    Returns:
        Optional[dict]: Current project data or None if no project is selected.
    """
    return _current_project


def set_current_project(project: Optional[dict]) -> None:
    """
    Set the current project context.
    """
    global _current_project
    _current_project = project


def require_current_project() -> dict:
    """
    Get the current project, raising an error if none is selected.

    Raises:
        HTTPException: If no project is currently selected.
    """
    project = get_current_project()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No project selected. Please select or create a project first."
        )
    return project


# Type aliases for dependency injection
Neo4jDep = Annotated[Neo4jHandler, Depends(get_neo4j_handler)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ConfigDep = Annotated[dict, Depends(get_app_config)]
CurrentProjectDep = Annotated[dict, Depends(require_current_project)]


class ProjectContext:
    """
    Context manager for project-scoped operations.

    Provides easy access to project ID and safe name.
    """

    def __init__(self, project: dict):
        self.project = project
        self.id: str = project.get("id", "")
        self.safe_name: str = project.get("safe_name", "")
        self.name: str = project.get("name", "")

    @classmethod
    def from_current(cls) -> "ProjectContext":
        """Create context from the current project."""
        project = require_current_project()
        return cls(project)


def get_project_context() -> ProjectContext:
    """
    Get a ProjectContext for the current project.

    Raises:
        HTTPException: If no project is currently selected.
    """
    return ProjectContext.from_current()


ProjectContextDep = Annotated[ProjectContext, Depends(get_project_context)]


# Placeholder for future authentication dependencies
async def get_current_user() -> Optional[dict]:
    """
    Get the current authenticated user.

    This is a placeholder for future authentication implementation.
    Currently returns None (no authentication).
    """
    # TODO: Implement JWT/OAuth authentication
    return None


async def require_auth() -> dict:
    """
    Require authentication for an endpoint.

    This is a placeholder for future authentication implementation.
    Currently allows all requests (development mode).

    Raises:
        HTTPException: If authentication is required but not provided.
    """
    user = await get_current_user()
    # For development, allow unauthenticated access
    # In production, uncomment the following:
    # if user is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Authentication required",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    return user or {"id": "anonymous", "role": "user"}


CurrentUserDep = Annotated[Optional[dict], Depends(get_current_user)]
AuthRequiredDep = Annotated[dict, Depends(require_auth)]
