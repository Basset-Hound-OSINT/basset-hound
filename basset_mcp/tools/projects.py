"""
Project management tools for MCP.

Provides tools for creating and managing investigation projects
in Basset Hound.
"""

import os

from .base import get_neo4j_handler, get_project_safe_name


def register_project_tools(mcp):
    """Register project management tools with the MCP server."""

    @mcp.tool()
    def create_project(name: str) -> dict:
        """
        Create a new project.

        Args:
            name: The project name

        Returns:
            The created project data
        """
        handler = get_neo4j_handler()

        # Create project
        project = handler.create_project(name)

        if not project:
            return {"error": f"Failed to create project: {name}"}

        # Create project directory
        project_id = project.get("id")
        if project_id:
            os.makedirs(f"projects/{project_id}", exist_ok=True)

        return {
            "success": True,
            "project": project
        }

    @mcp.tool()
    def list_projects() -> dict:
        """
        List all projects.

        Returns:
            List of all projects with basic info
        """
        handler = get_neo4j_handler()

        projects = handler.get_all_projects()

        return {
            "count": len(projects),
            "projects": projects
        }

    @mcp.tool()
    def get_project(project_id: str) -> dict:
        """
        Get detailed project information.

        Args:
            project_id: The project ID or safe_name

        Returns:
            Full project data including all entities
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)

        if not project:
            return {"error": f"Project not found: {project_id}"}

        return project
