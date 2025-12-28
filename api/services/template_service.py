"""
Template Service for Basset Hound

This module provides comprehensive custom report template management for OSINT investigations.
It supports creating, editing, and managing Jinja2-based templates for generating reports
with support for multiple template types including entity reports, project summaries,
relationship graphs, timelines, and custom templates.
"""

import json
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, StrictUndefined, meta, UndefinedError
from jinja2.sandbox import SandboxedEnvironment, SecurityError

logger = logging.getLogger(__name__)


class TemplateType(str, Enum):
    """Types of report templates supported."""
    ENTITY_REPORT = "entity_report"
    PROJECT_SUMMARY = "project_summary"
    RELATIONSHIP_GRAPH = "relationship_graph"
    TIMELINE = "timeline"
    CUSTOM = "custom"


class VariableType(str, Enum):
    """Types of template variables."""
    STRING = "string"
    LIST = "list"
    DICT = "dict"
    NUMBER = "number"
    BOOLEAN = "boolean"


class TemplateVariable(BaseModel):
    """
    Represents a variable expected by a template.

    Attributes:
        name: Variable name as used in the template
        type: Data type of the variable
        required: Whether the variable is required for rendering
        default_value: Default value if not provided
        description: Human-readable description of the variable
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Variable name as used in the template")
    type: VariableType = Field(default=VariableType.STRING, description="Data type of the variable")
    required: bool = Field(default=True, description="Whether the variable is required")
    default_value: Optional[Any] = Field(default=None, description="Default value if not provided")
    description: str = Field(default="", description="Human-readable description")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "required": self.required,
            "default_value": self.default_value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVariable":
        """Create from dictionary."""
        var_type = data.get("type", "string")
        if isinstance(var_type, str):
            var_type = VariableType(var_type)
        return cls(
            name=data.get("name", ""),
            type=var_type,
            required=data.get("required", True),
            default_value=data.get("default_value"),
            description=data.get("description", ""),
        )


class ReportTemplate(BaseModel):
    """
    Represents a custom report template.

    Attributes:
        id: Unique identifier for the template
        name: Display name of the template
        description: Description of the template's purpose
        template_type: Type of template (entity_report, project_summary, etc.)
        content: Jinja2 template content string
        variables: List of expected variables
        created_at: Timestamp of template creation
        updated_at: Timestamp of last update
        is_default: Whether this is a default/system template
        author: Author/creator of the template
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Display name for the template")
    description: Optional[str] = Field(default=None, description="Template description")
    template_type: TemplateType = Field(default=TemplateType.CUSTOM, description="Type of template")
    content: str = Field(..., description="Jinja2 template content")
    variables: List[TemplateVariable] = Field(default_factory=list, description="Expected variables")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_default: bool = Field(default=False, description="Whether this is a default template")
    author: Optional[str] = Field(default=None, description="Template author")

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "content": self.content,
            "variables": [v.to_dict() for v in self.variables],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_default": self.is_default,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportTemplate":
        """Create template from dictionary."""
        template_type = data.get("template_type", "custom")
        if isinstance(template_type, str):
            template_type = TemplateType(template_type)

        variables = data.get("variables", [])
        if variables and isinstance(variables[0], dict):
            variables = [TemplateVariable.from_dict(v) for v in variables]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.now(timezone.utc)

        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", "Untitled Template"),
            description=data.get("description"),
            template_type=template_type,
            content=data.get("content", ""),
            variables=variables,
            created_at=created_at,
            updated_at=updated_at,
            is_default=data.get("is_default", False),
            author=data.get("author"),
        )


# ==================== Default Templates ====================

DEFAULT_ENTITY_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title | default('Entity Report') }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .entity-card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin: 15px 0; }
        .field { margin: 10px 0; }
        .field-label { font-weight: bold; color: #6c757d; }
        .footer { margin-top: 40px; text-align: center; color: #6c757d; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>{{ title | default('Entity Report') }}</h1>
    <p>Generated: {{ generated_at | default('N/A') }}</p>

    {% if entity %}
    <div class="entity-card">
        <h2>{{ entity.name | default(entity.id[:8] if entity.id else 'Unknown') }}</h2>
        {% if entity.profile %}
        {% for section_name, section_data in entity.profile.items() %}
        <h3>{{ section_name | replace('_', ' ') | title }}</h3>
        {% if section_data is mapping %}
        {% for field_name, field_value in section_data.items() %}
        {% if field_value %}
        <div class="field">
            <span class="field-label">{{ field_name | replace('_', ' ') | title }}:</span>
            <span>{{ field_value }}</span>
        </div>
        {% endif %}
        {% endfor %}
        {% endif %}
        {% endfor %}
        {% endif %}
    </div>
    {% endif %}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
    </div>
</body>
</html>
"""

DEFAULT_PROJECT_SUMMARY_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title | default('Project Summary') }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; border-radius: 8px; padding: 15px; text-align: center; }
        .stat-value { font-size: 2em; color: #3498db; font-weight: bold; }
        .stat-label { color: #6c757d; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #f8f9fa; }
        .footer { margin-top: 40px; text-align: center; color: #6c757d; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>{{ title | default('Project Summary') }}</h1>
    {% if project %}
    <p><strong>Project:</strong> {{ project.name | default(project.id) }}</p>
    {% endif %}
    <p><strong>Generated:</strong> {{ generated_at | default('N/A') }}</p>

    {% if statistics %}
    <h2>Statistics</h2>
    <div class="stats-grid">
        {% for stat_name, stat_value in statistics.items() %}
        <div class="stat-card">
            <div class="stat-value">{{ stat_value }}</div>
            <div class="stat-label">{{ stat_name | replace('_', ' ') | title }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if entities %}
    <h2>Entities ({{ entities | length }})</h2>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>ID</th>
                <th>Created</th>
            </tr>
        </thead>
        <tbody>
            {% for entity in entities %}
            <tr>
                <td>{{ entity.name | default(entity.id[:8] if entity.id else 'Unknown') }}</td>
                <td>{{ entity.id[:8] if entity.id else 'N/A' }}...</td>
                <td>{{ entity.created_at | default('N/A') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
    </div>
</body>
</html>
"""

DEFAULT_RELATIONSHIP_GRAPH_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title | default('Relationship Graph') }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .relationship { background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 10px 0; }
        .entity { font-weight: bold; color: #1976d2; }
        .rel-type { background: #bbdefb; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
        .footer { margin-top: 40px; text-align: center; color: #6c757d; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>{{ title | default('Relationship Graph') }}</h1>
    <p><strong>Generated:</strong> {{ generated_at | default('N/A') }}</p>

    {% if relationships %}
    <h2>Relationships ({{ relationships | length }})</h2>
    {% for rel in relationships %}
    <div class="relationship">
        <span class="entity">{{ rel.source | default('Unknown') }}</span>
        <span class="rel-type">{{ rel.type | default('related to') }}</span>
        <span class="entity">{{ rel.target | default('Unknown') }}</span>
        {% if rel.description %}
        <p>{{ rel.description }}</p>
        {% endif %}
    </div>
    {% endfor %}
    {% else %}
    <p>No relationships found.</p>
    {% endif %}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
    </div>
</body>
</html>
"""

DEFAULT_TIMELINE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title | default('Timeline') }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .timeline { position: relative; padding-left: 30px; }
        .timeline::before { content: ''; position: absolute; left: 10px; top: 0; bottom: 0; width: 2px; background: #3498db; }
        .event { position: relative; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .event::before { content: ''; position: absolute; left: -24px; top: 20px; width: 12px; height: 12px; background: #3498db; border-radius: 50%; }
        .event-date { color: #6c757d; font-size: 0.85em; }
        .event-title { font-weight: bold; color: #2c3e50; }
        .footer { margin-top: 40px; text-align: center; color: #6c757d; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>{{ title | default('Timeline') }}</h1>
    <p><strong>Generated:</strong> {{ generated_at | default('N/A') }}</p>

    {% if events %}
    <div class="timeline">
        {% for event in events %}
        <div class="event">
            <div class="event-date">{{ event.date | default('Unknown date') }}</div>
            <div class="event-title">{{ event.title | default('Event') }}</div>
            {% if event.description %}
            <p>{{ event.description }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p>No events found.</p>
    {% endif %}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
    </div>
</body>
</html>
"""

DEFAULT_CUSTOM_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title | default('Custom Report') }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .content { margin: 20px 0; }
        .footer { margin-top: 40px; text-align: center; color: #6c757d; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>{{ title | default('Custom Report') }}</h1>
    <p><strong>Generated:</strong> {{ generated_at | default('N/A') }}</p>

    <div class="content">
        {{ content | default('No content provided.') }}
    </div>

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
    </div>
</body>
</html>
"""


def _create_default_templates() -> Dict[str, ReportTemplate]:
    """Create the default templates for each type."""
    now = datetime.now(timezone.utc)
    templates = {}

    # Entity Report Template
    templates["default-entity-report"] = ReportTemplate(
        id="default-entity-report",
        name="Default Entity Report",
        description="Standard template for single entity reports",
        template_type=TemplateType.ENTITY_REPORT,
        content=DEFAULT_ENTITY_REPORT_TEMPLATE,
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=False, default_value="Entity Report", description="Report title"),
            TemplateVariable(name="entity", type=VariableType.DICT, required=True, description="Entity data object"),
            TemplateVariable(name="generated_at", type=VariableType.STRING, required=False, description="Generation timestamp"),
        ],
        created_at=now,
        updated_at=now,
        is_default=True,
        author="system",
    )

    # Project Summary Template
    templates["default-project-summary"] = ReportTemplate(
        id="default-project-summary",
        name="Default Project Summary",
        description="Standard template for project overview reports",
        template_type=TemplateType.PROJECT_SUMMARY,
        content=DEFAULT_PROJECT_SUMMARY_TEMPLATE,
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=False, default_value="Project Summary", description="Report title"),
            TemplateVariable(name="project", type=VariableType.DICT, required=False, description="Project data object"),
            TemplateVariable(name="entities", type=VariableType.LIST, required=False, description="List of entities"),
            TemplateVariable(name="statistics", type=VariableType.DICT, required=False, description="Statistics data"),
            TemplateVariable(name="generated_at", type=VariableType.STRING, required=False, description="Generation timestamp"),
        ],
        created_at=now,
        updated_at=now,
        is_default=True,
        author="system",
    )

    # Relationship Graph Template
    templates["default-relationship-graph"] = ReportTemplate(
        id="default-relationship-graph",
        name="Default Relationship Graph",
        description="Standard template for relationship visualization",
        template_type=TemplateType.RELATIONSHIP_GRAPH,
        content=DEFAULT_RELATIONSHIP_GRAPH_TEMPLATE,
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=False, default_value="Relationship Graph", description="Report title"),
            TemplateVariable(name="relationships", type=VariableType.LIST, required=False, description="List of relationships"),
            TemplateVariable(name="generated_at", type=VariableType.STRING, required=False, description="Generation timestamp"),
        ],
        created_at=now,
        updated_at=now,
        is_default=True,
        author="system",
    )

    # Timeline Template
    templates["default-timeline"] = ReportTemplate(
        id="default-timeline",
        name="Default Timeline",
        description="Standard template for timeline events",
        template_type=TemplateType.TIMELINE,
        content=DEFAULT_TIMELINE_TEMPLATE,
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=False, default_value="Timeline", description="Report title"),
            TemplateVariable(name="events", type=VariableType.LIST, required=False, description="List of timeline events"),
            TemplateVariable(name="generated_at", type=VariableType.STRING, required=False, description="Generation timestamp"),
        ],
        created_at=now,
        updated_at=now,
        is_default=True,
        author="system",
    )

    # Custom Template
    templates["default-custom"] = ReportTemplate(
        id="default-custom",
        name="Default Custom",
        description="Basic custom template for general use",
        template_type=TemplateType.CUSTOM,
        content=DEFAULT_CUSTOM_TEMPLATE,
        variables=[
            TemplateVariable(name="title", type=VariableType.STRING, required=False, default_value="Custom Report", description="Report title"),
            TemplateVariable(name="content", type=VariableType.STRING, required=False, description="Main content"),
            TemplateVariable(name="generated_at", type=VariableType.STRING, required=False, description="Generation timestamp"),
        ],
        created_at=now,
        updated_at=now,
        is_default=True,
        author="system",
    )

    return templates


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when a template is not found."""
    pass


class TemplateService:
    """
    Service for managing custom report templates.

    Provides methods for creating, reading, updating, and deleting templates,
    as well as template validation, rendering, and import/export functionality.

    Security Note:
        User-generated templates are rendered using Jinja2's SandboxedEnvironment
        which prevents access to private attributes, unsafe methods, and object
        modification. System/default templates use the regular Environment for
        full functionality.
    """

    def __init__(self, max_templates: int = 200):
        """
        Initialize the template service with default templates.

        Args:
            max_templates: Maximum number of templates to store in memory (LRU eviction).
                          Note: Default templates are always preserved.
        """
        self._lock = threading.RLock()
        self._templates: OrderedDict[str, ReportTemplate] = OrderedDict()
        self._max_templates = max_templates
        # Sandboxed environment for user-generated templates (security)
        # Prevents access to private attributes (_), unsafe methods, and object modification
        self._sandboxed_env = SandboxedEnvironment(loader=BaseLoader(), undefined=StrictUndefined)
        # Regular environment for system/default templates (full functionality)
        self._jinja_env = Environment(loader=BaseLoader(), undefined=StrictUndefined)

        # Load default templates
        for template_id, template in _create_default_templates().items():
            self._templates[template_id] = template

    # ==================== Memory Management ====================

    def _enforce_templates_limit(self) -> None:
        """Evict oldest non-default templates when limit is exceeded (LRU eviction)."""
        while len(self._templates) > self._max_templates:
            # Find the oldest non-default template to evict
            for key in list(self._templates.keys()):
                template = self._templates[key]
                if not template.is_default:
                    del self._templates[key]
                    logger.debug(f"LRU evicted template: {key}")
                    break
            else:
                # All templates are default, can't evict any more
                break

    def get_templates_size(self) -> int:
        """Get current number of templates in storage."""
        with self._lock:
            return len(self._templates)

    def get_templates_capacity(self) -> int:
        """Get maximum templates storage capacity."""
        return self._max_templates

    def get_custom_templates_count(self) -> int:
        """Get count of non-default (custom) templates."""
        with self._lock:
            return sum(1 for t in self._templates.values() if not t.is_default)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for this service."""
        with self._lock:
            default_count = sum(1 for t in self._templates.values() if t.is_default)
            custom_count = len(self._templates) - default_count
            return {
                "templates_count": len(self._templates),
                "templates_capacity": self._max_templates,
                "templates_usage_percent": (len(self._templates) / self._max_templates * 100) if self._max_templates > 0 else 0,
                "default_templates_count": default_count,
                "custom_templates_count": custom_count,
            }

    def create_template(
        self,
        name: str,
        template_type: TemplateType,
        content: str,
        variables: Optional[List[TemplateVariable]] = None,
        description: Optional[str] = None,
    ) -> ReportTemplate:
        """
        Create a new custom template.

        Args:
            name: Display name for the template
            template_type: Type of template
            content: Jinja2 template content
            variables: List of expected variables (extracted automatically if not provided)
            description: Optional description

        Returns:
            The created ReportTemplate

        Raises:
            TemplateValidationError: If the template content is invalid
        """
        # Validate template syntax
        is_valid, error_msg = self.validate_template(content)
        if not is_valid:
            raise TemplateValidationError(error_msg)

        # Extract variables if not provided
        if variables is None:
            extracted = self._extract_variables(content)
            variables = [
                TemplateVariable(name=var_name, type=VariableType.STRING, required=True)
                for var_name in extracted
            ]

        template_id = str(uuid4())
        now = datetime.now(timezone.utc)

        template = ReportTemplate(
            id=template_id,
            name=name,
            description=description,
            template_type=template_type,
            content=content,
            variables=variables,
            created_at=now,
            updated_at=now,
            is_default=False,
            author=None,
        )

        with self._lock:
            self._templates[template_id] = template
            self._templates.move_to_end(template_id)  # Mark as most recently used
            self._enforce_templates_limit()
        logger.info(f"Created template: {name} (ID: {template_id})")

        return template

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template ID

        Returns:
            The ReportTemplate if found, None otherwise
        """
        with self._lock:
            template = self._templates.get(template_id)
            if template is not None:
                self._templates.move_to_end(template_id)  # Mark as most recently used
            return template

    def get_templates(
        self,
        template_type: Optional[TemplateType] = None,
    ) -> List[ReportTemplate]:
        """
        List all templates with optional type filtering.

        Args:
            template_type: Optional filter by template type

        Returns:
            List of matching templates
        """
        with self._lock:
            templates = list(self._templates.values())

        if template_type is not None:
            templates = [t for t in templates if t.template_type == template_type]

        # Sort by default first, then by name
        templates.sort(key=lambda t: (not t.is_default, t.name.lower()))

        return templates

    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        variables: Optional[List[TemplateVariable]] = None,
        description: Optional[str] = None,
    ) -> ReportTemplate:
        """
        Update an existing template.

        Args:
            template_id: ID of the template to update
            name: New name (optional)
            content: New content (optional)
            variables: New variables list (optional)
            description: New description (optional)

        Returns:
            The updated ReportTemplate

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If attempting to modify a default template or invalid content
        """
        with self._lock:
            template = self._templates.get(template_id)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            if template.is_default:
                raise TemplateValidationError("Cannot modify default templates")

            # Validate new content if provided
            if content is not None:
                is_valid, error_msg = self.validate_template(content)
                if not is_valid:
                    raise TemplateValidationError(error_msg)

            # Create updated template
            updated = ReportTemplate(
                id=template.id,
                name=name if name is not None else template.name,
                description=description if description is not None else template.description,
                template_type=template.template_type,
                content=content if content is not None else template.content,
                variables=variables if variables is not None else template.variables,
                created_at=template.created_at,
                updated_at=datetime.now(timezone.utc),
                is_default=template.is_default,
                author=template.author,
            )

            # If content changed and variables not explicitly provided, re-extract
            if content is not None and variables is None:
                extracted = self._extract_variables(content)
                updated.variables = [
                    TemplateVariable(name=var_name, type=VariableType.STRING, required=True)
                    for var_name in extracted
                ]

            self._templates[template_id] = updated
            self._templates.move_to_end(template_id)  # Mark as most recently used

        logger.info(f"Updated template: {updated.name} (ID: {template_id})")

        return updated

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.

        Args:
            template_id: ID of the template to delete

        Returns:
            True if deleted successfully

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If attempting to delete a default template
        """
        with self._lock:
            template = self._templates.get(template_id)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            if template.is_default:
                raise TemplateValidationError("Cannot delete default templates")

            del self._templates[template_id]

        logger.info(f"Deleted template: {template.name} (ID: {template_id})")

        return True

    def render_template(
        self,
        template_id: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a template with provided context.

        Args:
            template_id: ID of the template to render
            context: Context dictionary with variable values

        Returns:
            Rendered template content

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If rendering fails (including sandbox security violations)
        """
        # Get template data under lock
        with self._lock:
            template = self._templates.get(template_id)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            # Copy needed data for rendering outside lock
            template_content = template.content
            template_is_default = template.is_default
            template_variables = list(template.variables)

        # Rendering is done outside lock to avoid holding lock during long operations
        try:
            # Use sandboxed environment for user-generated templates (security)
            # Use regular environment for system/default templates (full functionality)
            env = self._jinja_env if template_is_default else self._sandboxed_env
            jinja_template = env.from_string(template_content)

            # Add default values for variables that have them
            render_context = dict(context)
            for var in template_variables:
                if var.name not in render_context and var.default_value is not None:
                    render_context[var.name] = var.default_value

            # Add generated_at if not present
            if "generated_at" not in render_context:
                render_context["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            return jinja_template.render(**render_context)

        except SecurityError as e:
            raise TemplateValidationError(f"Template security violation: {e}")
        except UndefinedError as e:
            raise TemplateValidationError(f"Missing required variable: {e}")
        except Exception as e:
            raise TemplateValidationError(f"Template rendering error: {e}")

    def validate_template(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Jinja2 template syntax.

        Args:
            content: Template content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self._jinja_env.parse(content)
            return (True, None)
        except TemplateSyntaxError as e:
            return (False, f"Template syntax error at line {e.lineno}: {e.message}")

    def preview_template(
        self,
        template_id: str,
        sample_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Preview a template with sample data.

        Args:
            template_id: ID of the template to preview
            sample_data: Optional sample data (uses defaults if not provided)

        Returns:
            Rendered preview

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        with self._lock:
            template = self._templates.get(template_id)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            template_variables = list(template.variables)

        # Build sample data from variable defaults if not provided
        context = sample_data or {}

        # Add default values for all variables
        for var in template_variables:
            if var.name not in context:
                if var.default_value is not None:
                    context[var.name] = var.default_value
                else:
                    # Generate sample data based on type
                    context[var.name] = self._generate_sample_value(var)

        return self.render_template(template_id, context)

    def _generate_sample_value(self, var: TemplateVariable) -> Any:
        """Generate a sample value for a variable based on its type."""
        if var.type == VariableType.STRING:
            return f"[Sample {var.name}]"
        elif var.type == VariableType.NUMBER:
            return 42
        elif var.type == VariableType.BOOLEAN:
            return True
        elif var.type == VariableType.LIST:
            return [{"name": "Sample Item 1"}, {"name": "Sample Item 2"}]
        elif var.type == VariableType.DICT:
            return {"id": "sample-id", "name": "Sample Object", "profile": {}}
        return None

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
        with self._lock:
            template = self._templates.get(template_id)

            if template is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            export_data = template.to_dict()

        export_data["exported_at"] = datetime.now(timezone.utc).isoformat()
        export_data["export_version"] = "1.0"

        return export_data

    def import_template(self, template_data: Dict[str, Any]) -> ReportTemplate:
        """
        Import a template from JSON data.

        Args:
            template_data: Template data dictionary

        Returns:
            The imported ReportTemplate

        Raises:
            TemplateValidationError: If template data is invalid
        """
        # Validate required fields
        if "name" not in template_data:
            raise TemplateValidationError("Missing required field: name")
        if "content" not in template_data:
            raise TemplateValidationError("Missing required field: content")

        # Validate template content
        is_valid, error_msg = self.validate_template(template_data["content"])
        if not is_valid:
            raise TemplateValidationError(error_msg)

        # Parse template type
        template_type_str = template_data.get("template_type", "custom")
        try:
            template_type = TemplateType(template_type_str)
        except ValueError:
            template_type = TemplateType.CUSTOM

        # Parse variables
        variables = []
        if "variables" in template_data:
            for var_data in template_data["variables"]:
                if isinstance(var_data, dict):
                    variables.append(TemplateVariable.from_dict(var_data))

        # Create the template
        template = self.create_template(
            name=template_data["name"],
            template_type=template_type,
            content=template_data["content"],
            variables=variables if variables else None,
            description=template_data.get("description"),
        )

        return template

    def duplicate_template(
        self,
        template_id: str,
        new_name: str,
    ) -> ReportTemplate:
        """
        Duplicate an existing template with a new name.

        Args:
            template_id: ID of the template to duplicate
            new_name: Name for the new template

        Returns:
            The newly created ReportTemplate

        Raises:
            TemplateNotFoundError: If source template doesn't exist
        """
        with self._lock:
            source = self._templates.get(template_id)

            if source is None:
                raise TemplateNotFoundError(f"Template not found: {template_id}")

            # Copy needed data
            source_template_type = source.template_type
            source_content = source.content
            source_description = source.description
            source_variables = list(source.variables)

        # Create a copy with new ID and name (create_template handles its own locking)
        return self.create_template(
            name=new_name,
            template_type=source_template_type,
            content=source_content,
            variables=[
                TemplateVariable(
                    name=v.name,
                    type=v.type,
                    required=v.required,
                    default_value=v.default_value,
                    description=v.description,
                )
                for v in source_variables
            ],
            description=source_description,
        )

    def _extract_variables(self, content: str) -> Set[str]:
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
            return set()

    def get_default_template_ids(self) -> List[str]:
        """Get IDs of all default templates."""
        with self._lock:
            return [t.id for t in self._templates.values() if t.is_default]

    def reset_to_defaults(self) -> None:
        """Reset to only default templates (removes all custom templates)."""
        with self._lock:
            self._templates = _create_default_templates()
        logger.info("Template service reset to default templates")


# Singleton instance management
_template_service: Optional[TemplateService] = None
_template_service_lock = threading.RLock()


def get_template_service() -> TemplateService:
    """
    Get or create the template service singleton.

    Returns:
        TemplateService instance
    """
    global _template_service

    if _template_service is None:
        with _template_service_lock:
            # Double-check after acquiring lock
            if _template_service is None:
                _template_service = TemplateService()

    return _template_service


def set_template_service(service: Optional[TemplateService]) -> None:
    """Set the template service singleton (for testing)."""
    global _template_service
    with _template_service_lock:
        _template_service = service
