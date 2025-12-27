"""
Template Service for Basset Hound

This module provides comprehensive custom report template management for OSINT investigations.
It supports creating, editing, and managing Jinja2-based templates for generating reports
in PDF, HTML, and Markdown formats.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from jinja2 import Environment, BaseLoader, TemplateSyntaxError, StrictUndefined, meta, UndefinedError

logger = logging.getLogger(__name__)


class TemplateFormat(str, Enum):
    """Supported template output formats."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class TemplateSection:
    """
    Represents a section within a template.

    Attributes:
        id: Unique identifier for the section
        name: Display name of the section
        template_content: Jinja2 template content for this section
        order: Order of the section in the template (lower numbers first)
    """
    id: str
    name: str
    template_content: str
    order: int = 0


@dataclass
class ReportTemplate:
    """
    Represents a custom report template.

    Attributes:
        id: Unique identifier for the template
        name: Display name of the template
        description: Description of the template's purpose
        content: HTML/Jinja2 template content for the main body
        styles: CSS styles for PDF/HTML formatting
        format: Output format (PDF, HTML, or MARKDOWN)
        variables: List of required variable names
        created_at: Timestamp of template creation
        updated_at: Timestamp of last update
        created_by: User ID who created the template
        is_system: Whether this is a built-in system template
    """
    id: str
    name: str
    description: str
    content: str
    styles: str
    format: TemplateFormat
    variables: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: Optional[str] = None
    is_system: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "styles": self.styles,
            "format": self.format.value if isinstance(self.format, TemplateFormat) else self.format,
            "variables": self.variables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "is_system": self.is_system,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportTemplate":
        """Create template from dictionary."""
        format_value = data.get("format", "html")
        if isinstance(format_value, str):
            format_value = TemplateFormat(format_value)

        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", "Untitled Template"),
            description=data.get("description", ""),
            content=data.get("content", ""),
            styles=data.get("styles", ""),
            format=format_value,
            variables=data.get("variables", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            created_by=data.get("created_by"),
            is_system=data.get("is_system", False),
        )


# ==================== System Templates ====================

DEFAULT_TEMPLATE_CSS = """
/* Basset Hound Default Report Styles */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
    background-color: #fff;
}

h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-bottom: 20px;
}

h2 {
    color: #34495e;
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 5px;
    margin-top: 30px;
}

h3 {
    color: #7f8c8d;
    margin-top: 20px;
}

.report-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 10px;
    margin-bottom: 30px;
}

.report-header h1 {
    color: white;
    border-bottom: none;
    margin: 0;
}

.report-meta {
    font-size: 0.9em;
    opacity: 0.9;
    margin-top: 10px;
}

.entity-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 20px;
    margin: 15px 0;
}

.entity-card h3 {
    margin-top: 0;
    color: #495057;
}

.field-label {
    font-weight: 600;
    color: #6c757d;
    display: inline-block;
    min-width: 150px;
}

.field-value {
    color: #212529;
}

.statistics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.stat-card {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}

.stat-value {
    font-size: 2em;
    font-weight: 700;
    color: #3498db;
}

.stat-label {
    color: #6c757d;
    font-size: 0.9em;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #dee2e6;
}

th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
}

.footer {
    margin-top: 50px;
    padding-top: 20px;
    border-top: 1px solid #dee2e6;
    text-align: center;
    color: #6c757d;
    font-size: 0.85em;
}

@media print {
    body { max-width: none; padding: 0; }
    .entity-card { break-inside: avoid; }
}
"""

DEFAULT_TEMPLATE_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>{{ styles }}</style>
</head>
<body>
    <div class="report-header">
        <h1>{{ title }}</h1>
        <div class="report-meta">
            {% if project %}Project: {{ project.name }}<br>{% endif %}
            Generated: {{ generated_at }}
        </div>
    </div>

    {% if entities %}
    <h2>Entities</h2>
    {% for entity in entities %}
    <div class="entity-card">
        <h3>{{ entity.name | default(entity.id[:8]) }}</h3>
        <p><span class="field-label">Entity ID:</span> <span class="field-value">{{ entity.id }}</span></p>
        {% if entity.profile %}
        {% for section_name, section_data in entity.profile.items() %}
        <h4>{{ section_name | replace('_', ' ') | title }}</h4>
        {% if section_data is mapping %}
        {% for field_name, field_value in section_data.items() %}
        {% if field_value %}
        <p><span class="field-label">{{ field_name | replace('_', ' ') | title }}:</span>
           <span class="field-value">{{ field_value }}</span></p>
        {% endif %}
        {% endfor %}
        {% endif %}
        {% endfor %}
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}

    {% if statistics %}
    <h2>Statistics</h2>
    <div class="statistics-grid">
        {% for stat_name, stat_value in statistics.items() %}
        <div class="stat-card">
            <div class="stat-value">{{ stat_value }}</div>
            <div class="stat-label">{{ stat_name | replace('_', ' ') | title }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
        <p>{{ generated_at }}</p>
    </div>
</body>
</html>
"""

PROFESSIONAL_TEMPLATE_CSS = """
/* Professional Report Template */
body {
    font-family: 'Times New Roman', Times, serif;
    line-height: 1.8;
    color: #000;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
    background-color: #fff;
}

h1 {
    font-size: 24pt;
    text-align: center;
    margin-bottom: 30px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

h2 {
    font-size: 14pt;
    border-bottom: 2px solid #000;
    padding-bottom: 5px;
    margin-top: 40px;
    text-transform: uppercase;
}

h3 {
    font-size: 12pt;
    margin-top: 25px;
}

.report-header {
    border: 2px solid #000;
    padding: 30px;
    margin-bottom: 40px;
    text-align: center;
}

.report-header h1 {
    margin: 0;
}

.report-meta {
    margin-top: 15px;
    font-style: italic;
}

.entity-card {
    border: 1px solid #ccc;
    padding: 20px;
    margin: 20px 0;
    page-break-inside: avoid;
}

.field-label {
    font-weight: bold;
    display: inline-block;
    min-width: 180px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

th, td {
    padding: 10px;
    border: 1px solid #000;
    text-align: left;
}

th {
    background: #f0f0f0;
}

.footer {
    margin-top: 60px;
    text-align: center;
    font-size: 10pt;
    border-top: 1px solid #000;
    padding-top: 20px;
}
"""

PROFESSIONAL_TEMPLATE_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>{{ styles }}</style>
</head>
<body>
    <div class="report-header">
        <h1>{{ title }}</h1>
        <div class="report-meta">
            {% if project %}Project: {{ project.name }}<br>{% endif %}
            Date: {{ generated_at }}
        </div>
    </div>

    {% if entities %}
    <h2>Investigation Subjects</h2>
    {% for entity in entities %}
    <div class="entity-card">
        <h3>Subject: {{ entity.name | default(entity.id[:8]) }}</h3>
        <p><span class="field-label">Reference ID:</span> {{ entity.id }}</p>
        {% if entity.profile %}
        {% for section_name, section_data in entity.profile.items() %}
        <h4>{{ section_name | replace('_', ' ') | title }}</h4>
        {% if section_data is mapping %}
        {% for field_name, field_value in section_data.items() %}
        {% if field_value %}
        <p><span class="field-label">{{ field_name | replace('_', ' ') | title }}:</span> {{ field_value }}</p>
        {% endif %}
        {% endfor %}
        {% endif %}
        {% endfor %}
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}

    {% if statistics %}
    <h2>Summary Statistics</h2>
    <table>
        <thead>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
            {% for stat_name, stat_value in statistics.items() %}
            <tr>
                <td>{{ stat_name | replace('_', ' ') | title }}</td>
                <td>{{ stat_value }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    <div class="footer">
        <p>CONFIDENTIAL - Generated by Basset Hound OSINT Platform</p>
        <p>Report Date: {{ generated_at }}</p>
    </div>
</body>
</html>
"""

MINIMAL_TEMPLATE_CSS = """
/* Minimal Report Template */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.5;
    color: #1a1a1a;
    max-width: 700px;
    margin: 0 auto;
    padding: 20px;
}

h1, h2, h3 {
    font-weight: 600;
}

h1 { font-size: 1.75rem; margin-bottom: 1.5rem; }
h2 { font-size: 1.25rem; margin-top: 2rem; }
h3 { font-size: 1rem; margin-top: 1.5rem; }

.entity-card {
    padding: 15px 0;
    border-bottom: 1px solid #eee;
}

.field-label {
    color: #666;
    font-size: 0.875rem;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

th { font-weight: 600; }

.footer {
    margin-top: 40px;
    color: #999;
    font-size: 0.875rem;
}
"""

MINIMAL_TEMPLATE_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>{{ styles }}</style>
</head>
<body>
    <h1>{{ title }}</h1>
    {% if project %}<p>Project: {{ project.name }}</p>{% endif %}
    <p>{{ generated_at }}</p>

    {% if entities %}
    <h2>Entities</h2>
    {% for entity in entities %}
    <div class="entity-card">
        <h3>{{ entity.name | default(entity.id[:8]) }}</h3>
        {% if entity.profile %}
        {% for section_name, section_data in entity.profile.items() %}
        {% if section_data is mapping %}
        {% for field_name, field_value in section_data.items() %}
        {% if field_value %}
        <p><span class="field-label">{{ field_name | replace('_', ' ') | title }}:</span> {{ field_value }}</p>
        {% endif %}
        {% endfor %}
        {% endif %}
        {% endfor %}
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}

    {% if statistics %}
    <h2>Statistics</h2>
    <ul>
        {% for stat_name, stat_value in statistics.items() %}
        <li>{{ stat_name | replace('_', ' ') | title }}: {{ stat_value }}</li>
        {% endfor %}
    </ul>
    {% endif %}

    <div class="footer">
        <p>Basset Hound - {{ generated_at }}</p>
    </div>
</body>
</html>
"""


# System templates
SYSTEM_TEMPLATES: Dict[str, ReportTemplate] = {
    "default": ReportTemplate(
        id="system-default",
        name="Default",
        description="Standard report template with modern styling and entity cards",
        content=DEFAULT_TEMPLATE_CONTENT,
        styles=DEFAULT_TEMPLATE_CSS,
        format=TemplateFormat.HTML,
        variables=["title", "project", "entities", "statistics", "generated_at"],
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        created_by="system",
        is_system=True,
    ),
    "professional": ReportTemplate(
        id="system-professional",
        name="Professional",
        description="Formal report template suitable for official documentation",
        content=PROFESSIONAL_TEMPLATE_CONTENT,
        styles=PROFESSIONAL_TEMPLATE_CSS,
        format=TemplateFormat.HTML,
        variables=["title", "project", "entities", "statistics", "generated_at"],
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        created_by="system",
        is_system=True,
    ),
    "minimal": ReportTemplate(
        id="system-minimal",
        name="Minimal",
        description="Clean, minimal template focusing on content over styling",
        content=MINIMAL_TEMPLATE_CONTENT,
        styles=MINIMAL_TEMPLATE_CSS,
        format=TemplateFormat.HTML,
        variables=["title", "project", "entities", "statistics", "generated_at"],
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        created_by="system",
        is_system=True,
    ),
}


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when a template is not found."""
    pass


class SystemTemplateError(Exception):
    """Raised when attempting to modify a system template."""
    pass


class TemplateService:
    """
    Service for managing custom report templates.

    Provides methods for creating, reading, updating, and deleting templates,
    as well as template validation, rendering, and import/export functionality.
    """

    def __init__(self):
        """Initialize the template service."""
        self._templates: Dict[str, ReportTemplate] = {}
        self._jinja_env = Environment(loader=BaseLoader(), undefined=StrictUndefined)

        # Load system templates
        for name, template in SYSTEM_TEMPLATES.items():
            self._templates[template.id] = template

    def create_template(
        self,
        name: str,
        description: str,
        content: str,
        styles: str = "",
        format: TemplateFormat = TemplateFormat.HTML,
        variables: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> ReportTemplate:
        """
        Create a new custom template.

        Args:
            name: Display name for the template
            description: Description of the template
            content: Jinja2 template content
            styles: CSS styles for the template
            format: Output format (PDF, HTML, MARKDOWN)
            variables: List of required variable names
            created_by: User ID of the creator

        Returns:
            The created ReportTemplate

        Raises:
            TemplateValidationError: If the template content is invalid
        """
        # Validate template syntax
        self.validate_template(content)

        # Extract variables if not provided
        if variables is None:
            variables = list(self.get_template_variables(content))

        template_id = str(uuid4())
        now = datetime.now().isoformat()

        template = ReportTemplate(
            id=template_id,
            name=name,
            description=description,
            content=content,
            styles=styles,
            format=format,
            variables=variables,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            is_system=False,
        )

        self._templates[template_id] = template
        logger.info(f"Created template: {name} (ID: {template_id})")

        return template

    def get_template(self, id_or_name: str) -> Optional[ReportTemplate]:
        """
        Get a template by ID or name.

        Args:
            id_or_name: Template ID or name to search for

        Returns:
            The ReportTemplate if found, None otherwise
        """
        # Try by ID first
        if id_or_name in self._templates:
            return self._templates[id_or_name]

        # Try by name (case-insensitive)
        for template in self._templates.values():
            if template.name.lower() == id_or_name.lower():
                return template

        return None

    def list_templates(
        self,
        format: Optional[TemplateFormat] = None,
        is_system: Optional[bool] = None,
    ) -> List[ReportTemplate]:
        """
        List all templates with optional filtering.

        Args:
            format: Filter by output format
            is_system: Filter by system/custom template

        Returns:
            List of matching templates
        """
        templates = list(self._templates.values())

        if format is not None:
            templates = [t for t in templates if t.format == format]

        if is_system is not None:
            templates = [t for t in templates if t.is_system == is_system]

        # Sort by name
        templates.sort(key=lambda t: (not t.is_system, t.name.lower()))

        return templates

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        styles: Optional[str] = None,
        format: Optional[TemplateFormat] = None,
        variables: Optional[List[str]] = None,
    ) -> ReportTemplate:
        """
        Update an existing template.

        Args:
            template_id: ID of the template to update
            name: New name (optional)
            description: New description (optional)
            content: New content (optional)
            styles: New styles (optional)
            format: New format (optional)
            variables: New variables list (optional)

        Returns:
            The updated ReportTemplate

        Raises:
            TemplateNotFoundError: If template doesn't exist
            SystemTemplateError: If attempting to modify a system template
            TemplateValidationError: If new content is invalid
        """
        template = self._templates.get(template_id)

        if template is None:
            raise TemplateNotFoundError(f"Template not found: {template_id}")

        if template.is_system:
            raise SystemTemplateError("Cannot modify system templates")

        # Validate new content if provided
        if content is not None:
            self.validate_template(content)

        # Update fields
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if content is not None:
            template.content = content
            # Re-extract variables if content changed and variables not provided
            if variables is None:
                template.variables = list(self.get_template_variables(content))
        if styles is not None:
            template.styles = styles
        if format is not None:
            template.format = format
        if variables is not None:
            template.variables = variables

        template.updated_at = datetime.now().isoformat()

        logger.info(f"Updated template: {template.name} (ID: {template_id})")

        return template

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.

        Args:
            template_id: ID of the template to delete

        Returns:
            True if deleted successfully

        Raises:
            TemplateNotFoundError: If template doesn't exist
            SystemTemplateError: If attempting to delete a system template
        """
        template = self._templates.get(template_id)

        if template is None:
            raise TemplateNotFoundError(f"Template not found: {template_id}")

        if template.is_system:
            raise SystemTemplateError("Cannot delete system templates")

        del self._templates[template_id]
        logger.info(f"Deleted template: {template.name} (ID: {template_id})")

        return True

    def validate_template(self, content: str) -> Dict[str, Any]:
        """
        Validate Jinja2 template syntax.

        Args:
            content: Template content to validate

        Returns:
            Dictionary with validation results including extracted variables

        Raises:
            TemplateValidationError: If template syntax is invalid
        """
        try:
            # Parse the template to check syntax
            parsed = self._jinja_env.parse(content)

            # Extract variables
            variables = meta.find_undeclared_variables(parsed)

            return {
                "valid": True,
                "variables": list(variables),
                "message": "Template is valid",
            }

        except TemplateSyntaxError as e:
            raise TemplateValidationError(
                f"Template syntax error at line {e.lineno}: {e.message}"
            )

    def render_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        include_styles: bool = True,
    ) -> str:
        """
        Render a template with provided data.

        Args:
            template_id: ID of the template to render
            data: Data dictionary to pass to the template
            include_styles: Whether to include styles in data

        Returns:
            Rendered template content

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If rendering fails
        """
        template = self._templates.get(template_id)

        if template is None:
            raise TemplateNotFoundError(f"Template not found: {template_id}")

        try:
            jinja_template = self._jinja_env.from_string(template.content)

            # Add styles to data if requested
            render_data = dict(data)
            if include_styles and "styles" not in render_data:
                render_data["styles"] = template.styles

            # Add generated_at if not present
            if "generated_at" not in render_data:
                render_data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return jinja_template.render(**render_data)

        except UndefinedError as e:
            raise TemplateValidationError(f"Missing required variable: {e}")
        except Exception as e:
            raise TemplateValidationError(f"Template rendering error: {e}")

    def get_template_variables(self, content: str) -> Set[str]:
        """
        Extract variable names from template content.

        Args:
            content: Template content to analyze

        Returns:
            Set of variable names used in the template
        """
        try:
            parsed = self._jinja_env.parse(content)
            return meta.find_undeclared_variables(parsed)
        except TemplateSyntaxError:
            # Return empty set for invalid templates
            return set()

    def duplicate_template(
        self,
        template_id: str,
        new_name: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> ReportTemplate:
        """
        Duplicate a template as a new custom template.

        Args:
            template_id: ID of the template to duplicate
            new_name: Name for the new template (optional)
            created_by: User ID of the creator

        Returns:
            The newly created ReportTemplate

        Raises:
            TemplateNotFoundError: If source template doesn't exist
        """
        source = self._templates.get(template_id)

        if source is None:
            raise TemplateNotFoundError(f"Template not found: {template_id}")

        # Generate new name if not provided
        if new_name is None:
            new_name = f"{source.name} (Copy)"

        return self.create_template(
            name=new_name,
            description=source.description,
            content=source.content,
            styles=source.styles,
            format=source.format,
            variables=list(source.variables),
            created_by=created_by,
        )

    def export_template(self, template_id: str) -> Dict[str, Any]:
        """
        Export a template as a JSON-serializable dictionary.

        Args:
            template_id: ID of the template to export

        Returns:
            Dictionary representation of the template

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = self._templates.get(template_id)

        if template is None:
            raise TemplateNotFoundError(f"Template not found: {template_id}")

        export_data = template.to_dict()
        export_data["exported_at"] = datetime.now().isoformat()
        export_data["export_version"] = "1.0"

        return export_data

    def export_templates(self, template_ids: List[str]) -> Dict[str, Any]:
        """
        Export multiple templates.

        Args:
            template_ids: List of template IDs to export

        Returns:
            Dictionary containing all exported templates
        """
        templates = []
        for template_id in template_ids:
            try:
                templates.append(self.export_template(template_id))
            except TemplateNotFoundError:
                logger.warning(f"Template not found for export: {template_id}")

        return {
            "templates": templates,
            "exported_at": datetime.now().isoformat(),
            "export_version": "1.0",
            "count": len(templates),
        }

    def import_template(
        self,
        data: Dict[str, Any],
        created_by: Optional[str] = None,
        overwrite: bool = False,
    ) -> ReportTemplate:
        """
        Import a template from JSON data.

        Args:
            data: Template data dictionary
            created_by: User ID of the importer
            overwrite: Whether to overwrite existing template with same name

        Returns:
            The imported ReportTemplate

        Raises:
            TemplateValidationError: If template data is invalid
        """
        # Validate required fields
        required_fields = ["name", "content"]
        for field in required_fields:
            if field not in data:
                raise TemplateValidationError(f"Missing required field: {field}")

        # Validate template content
        self.validate_template(data["content"])

        # Check for existing template with same name
        existing = None
        for template in self._templates.values():
            if template.name.lower() == data["name"].lower() and not template.is_system:
                existing = template
                break

        if existing and not overwrite:
            raise TemplateValidationError(
                f"Template with name '{data['name']}' already exists. "
                "Use overwrite=True to replace it."
            )

        if existing and overwrite:
            # Update existing template
            return self.update_template(
                template_id=existing.id,
                name=data.get("name"),
                description=data.get("description", ""),
                content=data["content"],
                styles=data.get("styles", ""),
                format=TemplateFormat(data.get("format", "html")),
                variables=data.get("variables"),
            )

        # Create new template
        return self.create_template(
            name=data["name"],
            description=data.get("description", ""),
            content=data["content"],
            styles=data.get("styles", ""),
            format=TemplateFormat(data.get("format", "html")),
            variables=data.get("variables"),
            created_by=created_by,
        )

    def import_templates(
        self,
        data: Dict[str, Any],
        created_by: Optional[str] = None,
        overwrite: bool = False,
    ) -> List[ReportTemplate]:
        """
        Import multiple templates from JSON data.

        Args:
            data: Dictionary containing templates list
            created_by: User ID of the importer
            overwrite: Whether to overwrite existing templates

        Returns:
            List of imported templates
        """
        templates_data = data.get("templates", [])
        imported = []

        for template_data in templates_data:
            try:
                template = self.import_template(
                    data=template_data,
                    created_by=created_by,
                    overwrite=overwrite,
                )
                imported.append(template)
            except (TemplateValidationError, TemplateNotFoundError) as e:
                logger.warning(f"Failed to import template: {e}")

        return imported

    def get_system_template_names(self) -> List[str]:
        """Get names of all system templates."""
        return [t.name for t in self._templates.values() if t.is_system]

    def reset_to_defaults(self):
        """Reset to only system templates (removes all custom templates)."""
        self._templates = {}
        for name, template in SYSTEM_TEMPLATES.items():
            self._templates[template.id] = template
        logger.info("Template service reset to default system templates")


# Singleton instance management
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """
    Get or create the template service singleton.

    Returns:
        TemplateService instance
    """
    global _template_service

    if _template_service is None:
        _template_service = TemplateService()

    return _template_service


def set_template_service(service: Optional[TemplateService]) -> None:
    """Set the template service singleton (for testing)."""
    global _template_service
    _template_service = service
