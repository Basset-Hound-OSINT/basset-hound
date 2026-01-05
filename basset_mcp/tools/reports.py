"""
Report management tools for MCP.

Provides tools for creating and retrieving investigation reports
attached to entities in Basset Hound.
"""

import os
from datetime import datetime
from uuid import uuid4

from .base import get_neo4j_handler, get_project_safe_name, get_project_id_from_safe_name


def get_reports_dir(project_id: str, entity_id: str) -> str:
    """Get the reports directory path for an entity."""
    return os.path.join("projects", project_id, "people", entity_id, "reports")


def register_report_tools(mcp):
    """Register report management tools with the MCP server."""

    @mcp.tool()
    def create_report(project_id: str, entity_id: str, content: str, toolname: str = "mcp") -> dict:
        """
        Create a report for an entity.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to attach the report to
            content: The report content (markdown format)
            toolname: Name of the tool creating the report (for filename)

        Returns:
            Success status and report info
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify entity exists
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Get the actual project ID for file paths
        actual_project_id = get_project_id_from_safe_name(safe_name)
        if not actual_project_id:
            actual_project_id = project_id

        # Generate report name
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid4())[:8]
        report_name = f"{toolname}_{date_str}_{entity_id}_{unique_id}.md"

        # Create reports directory
        reports_dir = get_reports_dir(actual_project_id, entity_id)
        os.makedirs(reports_dir, exist_ok=True)

        # Write report file
        report_path = os.path.join(reports_dir, report_name)
        with open(report_path, "w") as f:
            f.write(content)

        # Register in Neo4j
        report_data = {
            "name": report_name,
            "path": report_name,
            "tool": toolname,
            "created_at": datetime.now().isoformat(),
            "id": unique_id
        }
        handler.add_report_to_person(safe_name, entity_id, report_data)

        return {
            "success": True,
            "report_name": report_name,
            "report_path": report_path,
            "entity_id": entity_id
        }

    @mcp.tool()
    def get_reports(project_id: str, entity_id: str) -> dict:
        """
        List all reports for an entity.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID

        Returns:
            List of reports for the entity
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify entity exists
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Get the actual project ID for file paths
        actual_project_id = get_project_id_from_safe_name(safe_name)
        if not actual_project_id:
            actual_project_id = project_id

        # Get reports from filesystem
        reports_dir = get_reports_dir(actual_project_id, entity_id)

        reports = []
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                if filename.endswith(".md"):
                    file_path = os.path.join(reports_dir, filename)
                    stat = os.stat(file_path)

                    # Read first few lines for preview
                    with open(file_path, "r") as f:
                        preview = f.read(500)
                        if len(preview) == 500:
                            preview += "..."

                    reports.append({
                        "name": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "preview": preview
                    })

        return {
            "entity_id": entity_id,
            "project_id": project_id,
            "count": len(reports),
            "reports": reports
        }
