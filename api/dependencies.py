"""
Dependency injection for the Basset Hound FastAPI application.

Provides dependency functions for Neo4j database connections,
authentication, and other shared resources.
"""

import sys
from pathlib import Path
from typing import Annotated, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j_handler import Neo4jHandler
from config.config_loader import load_config

from api.config import Settings, get_settings
from api.auth.jwt import verify_token, TokenValidationError
from api.models.auth import TokenData


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


# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    scopes={
        "read:projects": "Read project data",
        "write:projects": "Write/modify project data",
        "read:entities": "Read entity data",
        "write:entities": "Write/modify entity data",
        "read:collaborations": "Read collaboration data",
        "write:collaborations": "Write/modify collaboration data",
        "admin": "Administrative access",
    }
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Get the current authenticated user from JWT token.

    Extracts and validates JWT token from Authorization header.
    Returns user information embedded in the token.

    Args:
        token: JWT token from Authorization header (Bearer scheme)

    Returns:
        Dictionary containing:
        - id: User ID from token subject
        - username: Username from token
        - scopes: List of permission scopes
        - exp: Token expiration time

    Raises:
        HTTPException: If token is invalid, expired, or missing required claims

    Security:
        - Validates JWT signature using secret key from settings
        - Checks token expiration
        - Verifies token type is "access"
        - Requires either 'sub' (subject) or 'user_id' claim
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify and decode token
        token_data = verify_token(token, expected_type="access", verify_exp=True)

        # Extract user identifier from token claims
        user_id = token_data.user_id or token_data.username
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Build user context dictionary
        user = {
            "id": user_id,
            "username": token_data.username,
            "scopes": token_data.scopes,
            "exp": token_data.exp,
            "authenticated": True,
        }
        return user

    except TokenValidationError as e:
        if e.code == "invalid_token_type":
            detail = "Invalid token type. Access token required."
        elif e.code == "missing_subject":
            detail = "Invalid token: missing user identifier"
        elif "expired" in e.message.lower():
            detail = "Token has expired"
        else:
            detail = "Could not validate credentials"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require authentication for an endpoint.

    This dependency enforces that a user must be authenticated to access
    the endpoint. It validates the JWT token and extracts user information.

    Args:
        current_user: User object from get_current_user dependency

    Returns:
        Dictionary with authenticated user information:
        - id: User ID
        - username: Username
        - scopes: Permission scopes
        - exp: Token expiration time
        - authenticated: True

    Raises:
        HTTPException: If user is not authenticated (from get_current_user)

    Usage:
        @router.post("/projects")
        async def create_project(
            current_user: dict = Depends(require_auth)
        ):
            # current_user is guaranteed to be authenticated here
            project_owner = current_user["id"]
            ...
    """
    if not current_user or not current_user.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_scope(*required_scopes: str):
    """
    Create a dependency that requires specific permission scopes.

    This higher-order function creates a dependency that validates
    that the authenticated user has all required scopes.

    Args:
        required_scopes: One or more scope strings required for access

    Returns:
        Dependency function that validates scopes

    Raises:
        HTTPException with 403 Forbidden if user lacks required scopes

    Example:
        @router.post("/admin/users")
        async def manage_users(
            current_user: dict = Depends(require_scope("admin", "write:users"))
        ):
            # User must have both "admin" and "write:users" scopes
            ...
    """
    async def check_scopes(current_user: dict = Depends(require_auth)) -> dict:
        """Validate that user has all required scopes."""
        user_scopes = set(current_user.get("scopes", []))
        missing_scopes = set(required_scopes) - user_scopes

        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {', '.join(required_scopes)}",
            )
        return current_user

    return check_scopes


# Type aliases for dependency injection
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
AuthRequiredDep = Annotated[dict, Depends(require_auth)]
