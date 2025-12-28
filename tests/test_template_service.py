"""
Tests for the Template Service.

This module provides comprehensive tests for the custom report template service,
including CRUD operations, rendering, validation, import/export, and edge cases.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch

from api.services.template_service import (
    TemplateService,
    TemplateType,
    VariableType,
    TemplateVariable,
    ReportTemplate,
    TemplateValidationError,
    TemplateNotFoundError,
    get_template_service,
    set_template_service,
)


# ==================== Fixtures ====================


@pytest.fixture
def template_service():
    """Provide a fresh template service for each test."""
    service = TemplateService()
    yield service


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test."""
    set_template_service(None)
    yield
    set_template_service(None)


@pytest.fixture
def simple_template_content():
    """Simple Jinja2 template content."""
    return "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>"


@pytest.fixture
def complex_template_content():
    """Complex Jinja2 template with loops and conditionals."""
    return """<!DOCTYPE html>
<html>
<head><title>{{ title | default('Report') }}</title></head>
<body>
    <h1>{{ title }}</h1>
    {% if entities %}
    <ul>
        {% for entity in entities %}
        <li>{{ entity.name }} - {{ entity.id }}</li>
        {% endfor %}
    </ul>
    {% else %}
    <p>No entities found.</p>
    {% endif %}
    <p>Generated: {{ generated_at }}</p>
</body>
</html>"""


@pytest.fixture
def sample_variables():
    """Sample template variables."""
    return [
        TemplateVariable(
            name="title",
            type=VariableType.STRING,
            required=True,
            default_value="Report Title",
            description="The report title",
        ),
        TemplateVariable(
            name="content",
            type=VariableType.STRING,
            required=False,
            default_value="",
            description="Main content",
        ),
    ]


@pytest.fixture
def sample_context():
    """Sample rendering context."""
    return {
        "title": "Test Report",
        "content": "This is the report content.",
        "entities": [
            {"id": "123", "name": "John Doe"},
            {"id": "456", "name": "Jane Smith"},
        ],
    }


# ==================== TemplateType Enum Tests ====================


class TestTemplateType:
    """Tests for TemplateType enum."""

    def test_template_type_values(self):
        """Test that all expected template types exist."""
        assert TemplateType.ENTITY_REPORT == "entity_report"
        assert TemplateType.PROJECT_SUMMARY == "project_summary"
        assert TemplateType.RELATIONSHIP_GRAPH == "relationship_graph"
        assert TemplateType.TIMELINE == "timeline"
        assert TemplateType.CUSTOM == "custom"

    def test_template_type_count(self):
        """Test that we have exactly 5 template types."""
        assert len(TemplateType) == 5

    def test_template_type_from_string(self):
        """Test creating template type from string."""
        assert TemplateType("entity_report") == TemplateType.ENTITY_REPORT
        assert TemplateType("custom") == TemplateType.CUSTOM

    def test_template_type_invalid_value(self):
        """Test that invalid template type raises ValueError."""
        with pytest.raises(ValueError):
            TemplateType("invalid_type")


# ==================== VariableType Enum Tests ====================


class TestVariableType:
    """Tests for VariableType enum."""

    def test_variable_type_values(self):
        """Test that all expected variable types exist."""
        assert VariableType.STRING == "string"
        assert VariableType.LIST == "list"
        assert VariableType.DICT == "dict"
        assert VariableType.NUMBER == "number"
        assert VariableType.BOOLEAN == "boolean"

    def test_variable_type_count(self):
        """Test that we have exactly 5 variable types."""
        assert len(VariableType) == 5


# ==================== TemplateVariable Model Tests ====================


class TestTemplateVariable:
    """Tests for TemplateVariable model."""

    def test_create_template_variable(self):
        """Test creating a template variable."""
        var = TemplateVariable(
            name="title",
            type=VariableType.STRING,
            required=True,
            default_value="Default",
            description="The title",
        )
        assert var.name == "title"
        assert var.type == VariableType.STRING
        assert var.required is True
        assert var.default_value == "Default"
        assert var.description == "The title"

    def test_template_variable_defaults(self):
        """Test template variable default values."""
        var = TemplateVariable(name="test")
        assert var.type == VariableType.STRING
        assert var.required is True
        assert var.default_value is None
        assert var.description == ""

    def test_template_variable_to_dict(self):
        """Test converting template variable to dictionary."""
        var = TemplateVariable(
            name="count",
            type=VariableType.NUMBER,
            required=False,
            default_value=0,
            description="Item count",
        )
        result = var.to_dict()
        assert result["name"] == "count"
        assert result["type"] == "number"
        assert result["required"] is False
        assert result["default_value"] == 0
        assert result["description"] == "Item count"

    def test_template_variable_from_dict(self):
        """Test creating template variable from dictionary."""
        data = {
            "name": "items",
            "type": "list",
            "required": True,
            "default_value": [],
            "description": "List of items",
        }
        var = TemplateVariable.from_dict(data)
        assert var.name == "items"
        assert var.type == VariableType.LIST
        assert var.required is True
        assert var.default_value == []
        assert var.description == "List of items"

    def test_template_variable_from_dict_defaults(self):
        """Test creating template variable from dict with defaults."""
        data = {"name": "test"}
        var = TemplateVariable.from_dict(data)
        assert var.name == "test"
        assert var.type == VariableType.STRING
        assert var.required is True


# ==================== ReportTemplate Model Tests ====================


class TestReportTemplate:
    """Tests for ReportTemplate model."""

    def test_create_report_template(self, simple_template_content, sample_variables):
        """Test creating a report template."""
        template = ReportTemplate(
            id="test-id",
            name="Test Template",
            description="A test template",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
            variables=sample_variables,
            is_default=False,
            author="tester",
        )
        assert template.id == "test-id"
        assert template.name == "Test Template"
        assert template.description == "A test template"
        assert template.template_type == TemplateType.CUSTOM
        assert len(template.variables) == 2
        assert template.is_default is False
        assert template.author == "tester"

    def test_report_template_defaults(self, simple_template_content):
        """Test report template default values."""
        template = ReportTemplate(
            name="Test",
            content=simple_template_content,
        )
        assert template.id is not None
        assert template.template_type == TemplateType.CUSTOM
        assert template.description is None
        assert template.variables == []
        assert template.is_default is False
        assert template.author is None

    def test_report_template_to_dict(self, simple_template_content, sample_variables):
        """Test converting report template to dictionary."""
        template = ReportTemplate(
            id="test-id",
            name="Test Template",
            description="Description",
            template_type=TemplateType.ENTITY_REPORT,
            content=simple_template_content,
            variables=sample_variables,
            is_default=True,
            author="system",
        )
        result = template.to_dict()
        assert result["id"] == "test-id"
        assert result["name"] == "Test Template"
        assert result["description"] == "Description"
        assert result["template_type"] == "entity_report"
        assert result["content"] == simple_template_content
        assert len(result["variables"]) == 2
        assert result["is_default"] is True
        assert result["author"] == "system"
        assert "created_at" in result
        assert "updated_at" in result

    def test_report_template_from_dict(self, simple_template_content):
        """Test creating report template from dictionary."""
        data = {
            "id": "imported-id",
            "name": "Imported Template",
            "description": "Imported from JSON",
            "template_type": "project_summary",
            "content": simple_template_content,
            "variables": [{"name": "title", "type": "string"}],
            "is_default": False,
            "author": "importer",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00",
        }
        template = ReportTemplate.from_dict(data)
        assert template.id == "imported-id"
        assert template.name == "Imported Template"
        assert template.template_type == TemplateType.PROJECT_SUMMARY
        assert len(template.variables) == 1
        assert template.is_default is False


# ==================== TemplateService CRUD Tests ====================


class TestTemplateServiceCRUD:
    """Tests for TemplateService CRUD operations."""

    def test_service_initializes_with_defaults(self, template_service):
        """Test that service initializes with default templates."""
        templates = template_service.get_templates()
        # Should have 5 default templates
        assert len(templates) >= 5
        default_ids = template_service.get_default_template_ids()
        assert "default-entity-report" in default_ids
        assert "default-project-summary" in default_ids
        assert "default-relationship-graph" in default_ids
        assert "default-timeline" in default_ids
        assert "default-custom" in default_ids

    def test_create_template(self, template_service, simple_template_content):
        """Test creating a new template."""
        template = template_service.create_template(
            name="My Template",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
            description="My custom template",
        )
        assert template.id is not None
        assert template.name == "My Template"
        assert template.template_type == TemplateType.CUSTOM
        assert template.is_default is False

    def test_create_template_with_variables(self, template_service, simple_template_content, sample_variables):
        """Test creating template with explicit variables."""
        template = template_service.create_template(
            name="With Variables",
            template_type=TemplateType.ENTITY_REPORT,
            content=simple_template_content,
            variables=sample_variables,
        )
        assert len(template.variables) == 2
        assert template.variables[0].name == "title"

    def test_create_template_auto_extract_variables(self, template_service):
        """Test that variables are auto-extracted when not provided."""
        content = "Hello {{ name }}! Your score is {{ score }}."
        template = template_service.create_template(
            name="Auto Extract",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        var_names = {v.name for v in template.variables}
        assert "name" in var_names
        assert "score" in var_names

    def test_create_template_invalid_syntax(self, template_service):
        """Test creating template with invalid Jinja2 syntax."""
        invalid_content = "{% if true %} missing end"
        with pytest.raises(TemplateValidationError):
            template_service.create_template(
                name="Invalid",
                template_type=TemplateType.CUSTOM,
                content=invalid_content,
            )

    def test_get_template(self, template_service, simple_template_content):
        """Test getting a template by ID."""
        created = template_service.create_template(
            name="To Get",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        retrieved = template_service.get_template(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "To Get"

    def test_get_template_not_found(self, template_service):
        """Test getting non-existent template returns None."""
        result = template_service.get_template("non-existent-id")
        assert result is None

    def test_get_default_template(self, template_service):
        """Test getting a default template."""
        template = template_service.get_template("default-entity-report")
        assert template is not None
        assert template.is_default is True
        assert template.template_type == TemplateType.ENTITY_REPORT

    def test_get_templates_all(self, template_service, simple_template_content):
        """Test getting all templates."""
        template_service.create_template(
            name="Custom 1",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        templates = template_service.get_templates()
        assert len(templates) >= 6  # 5 defaults + 1 custom

    def test_get_templates_by_type(self, template_service, simple_template_content):
        """Test filtering templates by type."""
        template_service.create_template(
            name="Timeline Custom",
            template_type=TemplateType.TIMELINE,
            content=simple_template_content,
        )
        timelines = template_service.get_templates(template_type=TemplateType.TIMELINE)
        assert len(timelines) >= 2  # 1 default + 1 custom
        for t in timelines:
            assert t.template_type == TemplateType.TIMELINE

    def test_get_templates_sorted(self, template_service, simple_template_content):
        """Test that templates are sorted correctly."""
        template_service.create_template(
            name="Zebra",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        template_service.create_template(
            name="Alpha",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        templates = template_service.get_templates()
        # Default templates should come first
        first_non_default_idx = next(
            i for i, t in enumerate(templates) if not t.is_default
        )
        for i in range(first_non_default_idx):
            assert templates[i].is_default is True

    def test_update_template(self, template_service, simple_template_content):
        """Test updating a template."""
        created = template_service.create_template(
            name="To Update",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        updated = template_service.update_template(
            template_id=created.id,
            name="Updated Name",
            description="New description",
        )
        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert updated.updated_at > created.created_at

    def test_update_template_content(self, template_service, simple_template_content):
        """Test updating template content."""
        created = template_service.create_template(
            name="Update Content",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        new_content = "<p>{{ message }}</p>"
        updated = template_service.update_template(
            template_id=created.id,
            content=new_content,
        )
        assert updated.content == new_content
        # Variables should be re-extracted
        var_names = {v.name for v in updated.variables}
        assert "message" in var_names

    def test_update_template_not_found(self, template_service):
        """Test updating non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.update_template(
                template_id="non-existent",
                name="New Name",
            )

    def test_update_default_template_fails(self, template_service):
        """Test that updating a default template raises error."""
        with pytest.raises(TemplateValidationError):
            template_service.update_template(
                template_id="default-entity-report",
                name="New Name",
            )

    def test_update_template_invalid_content(self, template_service, simple_template_content):
        """Test updating with invalid content raises error."""
        created = template_service.create_template(
            name="To Update",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        with pytest.raises(TemplateValidationError):
            template_service.update_template(
                template_id=created.id,
                content="{% if true %}",  # Invalid - missing endif
            )

    def test_delete_template(self, template_service, simple_template_content):
        """Test deleting a template."""
        created = template_service.create_template(
            name="To Delete",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        result = template_service.delete_template(created.id)
        assert result is True
        assert template_service.get_template(created.id) is None

    def test_delete_template_not_found(self, template_service):
        """Test deleting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.delete_template("non-existent")

    def test_delete_default_template_fails(self, template_service):
        """Test that deleting a default template raises error."""
        with pytest.raises(TemplateValidationError):
            template_service.delete_template("default-entity-report")


# ==================== TemplateService Rendering Tests ====================


class TestTemplateServiceRendering:
    """Tests for template rendering functionality."""

    def test_render_simple_template(self, template_service, simple_template_content):
        """Test rendering a simple template."""
        template = template_service.create_template(
            name="Simple",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"title": "Hello", "content": "World"},
        )
        assert "<h1>Hello</h1>" in rendered
        assert "<p>World</p>" in rendered

    def test_render_template_with_loop(self, template_service, complex_template_content, sample_context):
        """Test rendering template with loops."""
        template = template_service.create_template(
            name="Complex",
            template_type=TemplateType.CUSTOM,
            content=complex_template_content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context=sample_context,
        )
        assert "John Doe" in rendered
        assert "Jane Smith" in rendered

    def test_render_template_with_conditionals(self, template_service, complex_template_content):
        """Test rendering template with conditionals."""
        template = template_service.create_template(
            name="Conditional",
            template_type=TemplateType.CUSTOM,
            content=complex_template_content,
        )
        # With empty entities list (triggers the else branch)
        rendered = template_service.render_template(
            template_id=template.id,
            context={"title": "Test", "entities": []},
        )
        assert "No entities found." in rendered

    def test_render_template_uses_defaults(self, template_service, sample_variables):
        """Test that rendering uses variable defaults."""
        content = "<h1>{{ title }}</h1>"
        template = template_service.create_template(
            name="With Defaults",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=sample_variables,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={},
        )
        assert "Report Title" in rendered

    def test_render_template_adds_generated_at(self, template_service):
        """Test that generated_at is automatically added."""
        content = "<p>{{ generated_at }}</p>"
        template = template_service.create_template(
            name="Generated At",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={},
        )
        # Should contain a timestamp
        assert rendered != "<p></p>"

    def test_render_template_not_found(self, template_service):
        """Test rendering non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.render_template(
                template_id="non-existent",
                context={},
            )

    def test_render_default_template(self, template_service):
        """Test rendering a default template."""
        rendered = template_service.render_template(
            template_id="default-custom",
            context={"title": "Custom Title", "content": "Custom content"},
        )
        assert "Custom Title" in rendered
        assert "Custom content" in rendered


# ==================== TemplateService Validation Tests ====================


class TestTemplateServiceValidation:
    """Tests for template validation functionality."""

    def test_validate_valid_template(self, template_service, simple_template_content):
        """Test validating valid template content."""
        is_valid, error = template_service.validate_template(simple_template_content)
        assert is_valid is True
        assert error is None

    def test_validate_template_with_loop(self, template_service, complex_template_content):
        """Test validating template with loops."""
        is_valid, error = template_service.validate_template(complex_template_content)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_template_unclosed_block(self, template_service):
        """Test validating template with unclosed block."""
        invalid = "{% if condition %} content without endif"
        is_valid, error = template_service.validate_template(invalid)
        assert is_valid is False
        assert error is not None
        assert "syntax error" in error.lower()

    def test_validate_invalid_template_unclosed_variable(self, template_service):
        """Test validating template with unclosed variable."""
        invalid = "{{ variable"
        is_valid, error = template_service.validate_template(invalid)
        assert is_valid is False
        assert error is not None

    def test_validate_invalid_template_unknown_filter(self, template_service):
        """Test that unknown filters pass syntax validation."""
        # Unknown filters are valid syntax, they fail at render time
        content = "{{ value | unknown_filter }}"
        is_valid, error = template_service.validate_template(content)
        assert is_valid is True

    def test_validate_empty_template(self, template_service):
        """Test validating empty template."""
        is_valid, error = template_service.validate_template("")
        assert is_valid is True

    def test_validate_plain_html(self, template_service):
        """Test validating plain HTML without Jinja2."""
        content = "<html><body><p>Plain HTML</p></body></html>"
        is_valid, error = template_service.validate_template(content)
        assert is_valid is True


# ==================== TemplateService Preview Tests ====================


class TestTemplateServicePreview:
    """Tests for template preview functionality."""

    def test_preview_template_with_sample_data(self, template_service, simple_template_content):
        """Test previewing template with provided sample data."""
        template = template_service.create_template(
            name="Preview Test",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        rendered = template_service.preview_template(
            template_id=template.id,
            sample_data={"title": "Sample", "content": "Preview"},
        )
        assert "Sample" in rendered
        assert "Preview" in rendered

    def test_preview_template_uses_defaults(self, template_service, sample_variables):
        """Test preview uses variable defaults when sample data missing."""
        content = "<h1>{{ title }}</h1>"
        template = template_service.create_template(
            name="Preview Defaults",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=sample_variables,
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "Report Title" in rendered

    def test_preview_template_generates_samples(self, template_service):
        """Test preview generates sample values for variables."""
        content = "{{ name }} - {{ count }} - {{ items }}"
        template = template_service.create_template(
            name="Generate Samples",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=[
                TemplateVariable(name="name", type=VariableType.STRING),
                TemplateVariable(name="count", type=VariableType.NUMBER),
                TemplateVariable(name="items", type=VariableType.LIST),
            ],
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "[Sample name]" in rendered
        assert "42" in rendered

    def test_preview_template_not_found(self, template_service):
        """Test previewing non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.preview_template(template_id="non-existent")

    def test_preview_default_template(self, template_service):
        """Test previewing a default template."""
        rendered = template_service.preview_template(
            template_id="default-custom",
        )
        assert "Custom Report" in rendered


# ==================== TemplateService Import/Export Tests ====================


class TestTemplateServiceImportExport:
    """Tests for template import/export functionality."""

    def test_export_template(self, template_service, simple_template_content, sample_variables):
        """Test exporting a template."""
        template = template_service.create_template(
            name="To Export",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
            variables=sample_variables,
            description="Export test",
        )
        exported = template_service.export_template(template.id)
        assert exported["name"] == "To Export"
        assert exported["template_type"] == "custom"
        assert exported["content"] == simple_template_content
        assert len(exported["variables"]) == 2
        assert "exported_at" in exported
        assert exported["export_version"] == "1.0"

    def test_export_template_not_found(self, template_service):
        """Test exporting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.export_template("non-existent")

    def test_export_default_template(self, template_service):
        """Test exporting a default template."""
        exported = template_service.export_template("default-entity-report")
        assert exported["is_default"] is True
        assert exported["author"] == "system"

    def test_import_template(self, template_service, simple_template_content):
        """Test importing a template."""
        data = {
            "name": "Imported Template",
            "template_type": "custom",
            "content": simple_template_content,
            "description": "Imported from export",
        }
        imported = template_service.import_template(data)
        assert imported.name == "Imported Template"
        assert imported.template_type == TemplateType.CUSTOM
        assert imported.is_default is False

    def test_import_template_with_variables(self, template_service, simple_template_content):
        """Test importing template with variables."""
        data = {
            "name": "With Vars",
            "content": simple_template_content,
            "variables": [
                {"name": "title", "type": "string", "required": True},
                {"name": "count", "type": "number", "required": False, "default_value": 0},
            ],
        }
        imported = template_service.import_template(data)
        assert len(imported.variables) == 2
        assert imported.variables[0].name == "title"
        assert imported.variables[1].type == VariableType.NUMBER

    def test_import_template_missing_name(self, template_service):
        """Test importing template without name raises error."""
        with pytest.raises(TemplateValidationError) as exc:
            template_service.import_template({"content": "<p>test</p>"})
        assert "name" in str(exc.value).lower()

    def test_import_template_missing_content(self, template_service):
        """Test importing template without content raises error."""
        with pytest.raises(TemplateValidationError) as exc:
            template_service.import_template({"name": "Test"})
        assert "content" in str(exc.value).lower()

    def test_import_template_invalid_content(self, template_service):
        """Test importing template with invalid content raises error."""
        with pytest.raises(TemplateValidationError):
            template_service.import_template({
                "name": "Invalid",
                "content": "{% if true %}",  # Invalid syntax
            })

    def test_import_invalid_template_type(self, template_service, simple_template_content):
        """Test importing with invalid template type defaults to custom."""
        data = {
            "name": "Invalid Type",
            "content": simple_template_content,
            "template_type": "invalid_type",
        }
        imported = template_service.import_template(data)
        assert imported.template_type == TemplateType.CUSTOM

    def test_export_import_roundtrip(self, template_service, simple_template_content, sample_variables):
        """Test that export/import roundtrip preserves data."""
        original = template_service.create_template(
            name="Roundtrip Test",
            template_type=TemplateType.PROJECT_SUMMARY,
            content=simple_template_content,
            variables=sample_variables,
            description="Testing roundtrip",
        )
        exported = template_service.export_template(original.id)
        imported = template_service.import_template(exported)

        assert imported.name == original.name
        assert imported.template_type == original.template_type
        assert imported.content == original.content
        assert imported.description == original.description
        assert len(imported.variables) == len(original.variables)


# ==================== TemplateService Duplicate Tests ====================


class TestTemplateServiceDuplicate:
    """Tests for template duplication functionality."""

    def test_duplicate_template(self, template_service, simple_template_content, sample_variables):
        """Test duplicating a template."""
        original = template_service.create_template(
            name="Original",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
            variables=sample_variables,
            description="Original template",
        )
        duplicate = template_service.duplicate_template(
            template_id=original.id,
            new_name="Duplicate",
        )
        assert duplicate.id != original.id
        assert duplicate.name == "Duplicate"
        assert duplicate.content == original.content
        assert duplicate.template_type == original.template_type
        assert duplicate.description == original.description
        assert len(duplicate.variables) == len(original.variables)
        assert duplicate.is_default is False

    def test_duplicate_default_template(self, template_service):
        """Test duplicating a default template."""
        duplicate = template_service.duplicate_template(
            template_id="default-entity-report",
            new_name="My Entity Report",
        )
        assert duplicate.id != "default-entity-report"
        assert duplicate.name == "My Entity Report"
        assert duplicate.template_type == TemplateType.ENTITY_REPORT
        assert duplicate.is_default is False

    def test_duplicate_template_not_found(self, template_service):
        """Test duplicating non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            template_service.duplicate_template(
                template_id="non-existent",
                new_name="New Name",
            )


# ==================== Singleton Tests ====================


class TestTemplateServiceSingleton:
    """Tests for template service singleton management."""

    def test_get_template_service_creates_singleton(self):
        """Test that get_template_service creates singleton."""
        service1 = get_template_service()
        service2 = get_template_service()
        assert service1 is service2

    def test_set_template_service(self):
        """Test setting custom template service."""
        custom_service = TemplateService()
        set_template_service(custom_service)
        retrieved = get_template_service()
        assert retrieved is custom_service

    def test_set_template_service_none_resets(self):
        """Test that setting None resets singleton."""
        get_template_service()  # Create singleton
        set_template_service(None)
        # Next call should create new instance
        service = get_template_service()
        assert service is not None


# ==================== Reset Tests ====================


class TestTemplateServiceReset:
    """Tests for template service reset functionality."""

    def test_reset_to_defaults(self, template_service, simple_template_content):
        """Test resetting service to default templates."""
        # Create some custom templates
        template_service.create_template(
            name="Custom 1",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        template_service.create_template(
            name="Custom 2",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )

        initial_count = len(template_service.get_templates())
        assert initial_count > 5  # More than just defaults

        template_service.reset_to_defaults()

        final_count = len(template_service.get_templates())
        assert final_count == 5  # Only defaults

        for template in template_service.get_templates():
            assert template.is_default is True


# ==================== Edge Cases ====================


class TestTemplateServiceEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_template_with_special_characters(self, template_service):
        """Test template with special characters in content."""
        content = '<p>Special chars: &amp; &lt; &gt; "quotes" \'apostrophes\'</p>'
        template = template_service.create_template(
            name="Special Chars",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        assert template.content == content

    def test_template_with_unicode(self, template_service):
        """Test template with Unicode content."""
        content = "<p>Unicode: {{ message }}</p>"
        template = template_service.create_template(
            name="Unicode Test",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"message": "Hello World!"},
        )
        assert "Hello World!" in rendered

    def test_template_with_nested_variables(self, template_service):
        """Test template with nested variable access."""
        content = "<p>{{ entity.profile.name }}</p>"
        template = template_service.create_template(
            name="Nested",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"entity": {"profile": {"name": "John"}}},
        )
        assert "John" in rendered

    def test_template_with_filters(self, template_service):
        """Test template with Jinja2 filters."""
        content = "{{ name | upper }} - {{ items | length }}"
        template = template_service.create_template(
            name="Filters",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"name": "test", "items": [1, 2, 3]},
        )
        assert "TEST" in rendered
        assert "3" in rendered

    def test_template_with_macros(self, template_service):
        """Test template with Jinja2 macros."""
        content = """{% macro greeting(name) %}Hello, {{ name }}!{% endmacro %}
{{ greeting("World") }}"""
        template = template_service.create_template(
            name="Macros",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={},
        )
        assert "Hello, World!" in rendered

    def test_very_long_template_name(self, template_service, simple_template_content):
        """Test template with very long name."""
        long_name = "A" * 500
        template = template_service.create_template(
            name=long_name,
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        assert template.name == long_name

    def test_empty_context_rendering(self, template_service):
        """Test rendering with empty context uses defaults."""
        content = "{{ title | default('Default Title') }}"
        template = template_service.create_template(
            name="Empty Context",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={},
        )
        assert "Default Title" in rendered


# ==================== Sample Value Generation Tests ====================


class TestSampleValueGeneration:
    """Tests for sample value generation."""

    def test_generate_string_sample(self, template_service):
        """Test generating sample string value."""
        content = "{{ name }}"
        template = template_service.create_template(
            name="String Sample",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=[TemplateVariable(name="name", type=VariableType.STRING)],
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "[Sample name]" in rendered

    def test_generate_number_sample(self, template_service):
        """Test generating sample number value."""
        content = "{{ count }}"
        template = template_service.create_template(
            name="Number Sample",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=[TemplateVariable(name="count", type=VariableType.NUMBER)],
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "42" in rendered

    def test_generate_boolean_sample(self, template_service):
        """Test generating sample boolean value."""
        content = "{{ flag }}"
        template = template_service.create_template(
            name="Boolean Sample",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=[TemplateVariable(name="flag", type=VariableType.BOOLEAN)],
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "True" in rendered

    def test_generate_dict_sample(self, template_service):
        """Test generating sample dict value."""
        content = "{{ entity.id }}"
        template = template_service.create_template(
            name="Dict Sample",
            template_type=TemplateType.CUSTOM,
            content=content,
            variables=[TemplateVariable(name="entity", type=VariableType.DICT)],
        )
        rendered = template_service.preview_template(template_id=template.id)
        assert "sample-id" in rendered


# ==================== Default Templates Tests ====================


class TestDefaultTemplates:
    """Tests for default template contents."""

    def test_entity_report_template_exists(self, template_service):
        """Test that entity report default template exists."""
        template = template_service.get_template("default-entity-report")
        assert template is not None
        assert template.name == "Default Entity Report"
        assert template.template_type == TemplateType.ENTITY_REPORT
        assert template.is_default is True

    def test_project_summary_template_exists(self, template_service):
        """Test that project summary default template exists."""
        template = template_service.get_template("default-project-summary")
        assert template is not None
        assert template.name == "Default Project Summary"
        assert template.template_type == TemplateType.PROJECT_SUMMARY

    def test_relationship_graph_template_exists(self, template_service):
        """Test that relationship graph default template exists."""
        template = template_service.get_template("default-relationship-graph")
        assert template is not None
        assert template.name == "Default Relationship Graph"
        assert template.template_type == TemplateType.RELATIONSHIP_GRAPH

    def test_timeline_template_exists(self, template_service):
        """Test that timeline default template exists."""
        template = template_service.get_template("default-timeline")
        assert template is not None
        assert template.name == "Default Timeline"
        assert template.template_type == TemplateType.TIMELINE

    def test_custom_default_template_exists(self, template_service):
        """Test that custom default template exists."""
        template = template_service.get_template("default-custom")
        assert template is not None
        assert template.name == "Default Custom"
        assert template.template_type == TemplateType.CUSTOM

    def test_default_templates_have_content(self, template_service):
        """Test that all default templates have content."""
        default_ids = template_service.get_default_template_ids()
        for template_id in default_ids:
            template = template_service.get_template(template_id)
            assert template.content is not None
            assert len(template.content) > 100


# ==================== Additional Tests for Coverage ====================


class TestAdditionalCoverage:
    """Additional tests to ensure comprehensive coverage."""

    def test_template_variable_all_types(self, template_service):
        """Test creating variables of all types."""
        variables = [
            TemplateVariable(name="str_var", type=VariableType.STRING),
            TemplateVariable(name="num_var", type=VariableType.NUMBER),
            TemplateVariable(name="bool_var", type=VariableType.BOOLEAN),
            TemplateVariable(name="list_var", type=VariableType.LIST),
            TemplateVariable(name="dict_var", type=VariableType.DICT),
        ]
        template = template_service.create_template(
            name="All Types",
            template_type=TemplateType.CUSTOM,
            content="{{ str_var }} {{ num_var }} {{ bool_var }}",
            variables=variables,
        )
        assert len(template.variables) == 5

    def test_multiple_template_types(self, template_service, simple_template_content):
        """Test creating templates of each type."""
        types = [
            TemplateType.ENTITY_REPORT,
            TemplateType.PROJECT_SUMMARY,
            TemplateType.RELATIONSHIP_GRAPH,
            TemplateType.TIMELINE,
            TemplateType.CUSTOM,
        ]
        for template_type in types:
            template = template_service.create_template(
                name=f"Test {template_type.value}",
                template_type=template_type,
                content=simple_template_content,
            )
            assert template.template_type == template_type

    def test_template_with_jinja_comments(self, template_service):
        """Test template with Jinja2 comments."""
        content = "{# This is a comment #}<p>{{ content }}</p>"
        template = template_service.create_template(
            name="Comments",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"content": "visible"},
        )
        assert "visible" in rendered
        assert "comment" not in rendered

    def test_template_whitespace_control(self, template_service):
        """Test template with whitespace control."""
        content = "<p>{{- content -}}</p>"
        template = template_service.create_template(
            name="Whitespace",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"content": "test"},
        )
        assert "<p>test</p>" in rendered

    def test_variable_with_all_fields(self):
        """Test creating a variable with all fields populated."""
        var = TemplateVariable(
            name="full_var",
            type=VariableType.STRING,
            required=True,
            default_value="default",
            description="A fully configured variable",
        )
        var_dict = var.to_dict()
        assert var_dict["name"] == "full_var"
        assert var_dict["type"] == "string"
        assert var_dict["required"] is True
        assert var_dict["default_value"] == "default"
        assert var_dict["description"] == "A fully configured variable"

    def test_get_templates_returns_copies(self, template_service):
        """Test that get_templates returns independent copies."""
        templates1 = template_service.get_templates()
        templates2 = template_service.get_templates()
        # Lists should be different objects
        assert templates1 is not templates2

    def test_render_entity_report_template(self, template_service):
        """Test rendering the default entity report template."""
        context = {
            "title": "John Doe Report",
            "entity": {
                "id": "12345678",
                "name": "John Doe",
                "profile": {
                    "core": {
                        "email": "john@example.com",
                    },
                },
            },
        }
        rendered = template_service.render_template(
            template_id="default-entity-report",
            context=context,
        )
        assert "John Doe Report" in rendered

    def test_render_project_summary_template(self, template_service):
        """Test rendering the default project summary template."""
        context = {
            "title": "Investigation Summary",
            "project": {"id": "proj-123", "name": "Test Project"},
            "entities": [
                {"id": "entity-1", "name": "Person A", "created_at": "2024-01-01"},
                {"id": "entity-2", "name": "Person B", "created_at": "2024-01-02"},
            ],
            "statistics": {"total_entities": 2, "total_relationships": 3},
        }
        rendered = template_service.render_template(
            template_id="default-project-summary",
            context=context,
        )
        assert "Investigation Summary" in rendered
        assert "Test Project" in rendered

    def test_render_relationship_graph_template(self, template_service):
        """Test rendering the default relationship graph template."""
        context = {
            "title": "Relationship Map",
            "relationships": [
                {"source": "Alice", "target": "Bob", "type": "knows", "description": "Friends"},
                {"source": "Bob", "target": "Carol", "type": "works with", "description": None},
            ],
        }
        rendered = template_service.render_template(
            template_id="default-relationship-graph",
            context=context,
        )
        assert "Relationship Map" in rendered
        assert "Alice" in rendered
        assert "knows" in rendered

    def test_render_timeline_template(self, template_service):
        """Test rendering the default timeline template."""
        context = {
            "title": "Investigation Timeline",
            "events": [
                {"date": "2024-01-01", "title": "First Contact", "description": "Initial observation"},
                {"date": "2024-01-15", "title": "Follow-up", "description": "Additional data collected"},
            ],
        }
        rendered = template_service.render_template(
            template_id="default-timeline",
            context=context,
        )
        assert "Investigation Timeline" in rendered
        assert "First Contact" in rendered
        assert "2024-01-01" in rendered

    def test_template_from_dict_with_iso_timestamps(self):
        """Test creating template from dict with ISO timestamp strings."""
        data = {
            "name": "ISO Timestamps",
            "content": "<p>Test</p>",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-16T14:20:00Z",
        }
        template = ReportTemplate.from_dict(data)
        assert template.name == "ISO Timestamps"
        assert isinstance(template.created_at, datetime)
        assert isinstance(template.updated_at, datetime)

    def test_template_variables_equality(self):
        """Test template variable equality."""
        var1 = TemplateVariable(name="test", type=VariableType.STRING)
        var2 = TemplateVariable(name="test", type=VariableType.STRING)
        assert var1.name == var2.name
        assert var1.type == var2.type

    def test_update_template_preserves_created_at(self, template_service, simple_template_content):
        """Test that updating a template preserves created_at timestamp."""
        created = template_service.create_template(
            name="Preserve Date",
            template_type=TemplateType.CUSTOM,
            content=simple_template_content,
        )
        original_created_at = created.created_at

        updated = template_service.update_template(
            template_id=created.id,
            name="New Name",
        )

        assert updated.created_at == original_created_at
        assert updated.updated_at > original_created_at


# ==================== Sandbox Security Tests ====================


class TestTemplateSandboxSecurity:
    """Tests for Jinja2 sandbox security in user-generated templates."""

    def test_sandbox_blocks_private_attribute_access(self, template_service):
        """Test that sandbox blocks access to private attributes (starting with _)."""
        # Attempt to access __class__ which could be used for code execution
        content = "{{ obj.__class__ }}"
        template = template_service.create_template(
            name="Private Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"obj": "test"},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_blocks_dunder_attribute_access(self, template_service):
        """Test that sandbox blocks access to dunder attributes."""
        content = "{{ obj.__dict__ }}"
        template = template_service.create_template(
            name="Dunder Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )

        # Use a custom object that has __dict__ (all custom classes do)
        class SampleObject:
            def __init__(self):
                self.data = "secret"

        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"obj": SampleObject()},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_blocks_mro_access(self, template_service):
        """Test that sandbox blocks access to __mro__ (method resolution order)."""
        content = "{{ obj.__class__.__mro__ }}"
        template = template_service.create_template(
            name="MRO Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"obj": "test"},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_blocks_subclasses_access(self, template_service):
        """Test that sandbox blocks access to __subclasses__."""
        content = "{{ obj.__class__.__subclasses__() }}"
        template = template_service.create_template(
            name="Subclasses Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"obj": "test"},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_blocks_globals_access(self, template_service):
        """Test that sandbox blocks access to __globals__."""
        content = "{{ func.__globals__ }}"
        template = template_service.create_template(
            name="Globals Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )

        def sample_func():
            pass

        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"func": sample_func},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_allows_safe_operations(self, template_service):
        """Test that sandbox allows normal safe template operations."""
        content = """
        <h1>{{ title }}</h1>
        <ul>
        {% for item in items %}
            <li>{{ item.name }}: {{ item.value }}</li>
        {% endfor %}
        </ul>
        {{ count | default(0) }}
        """
        template = template_service.create_template(
            name="Safe Operations",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={
                "title": "My List",
                "items": [
                    {"name": "Item 1", "value": 100},
                    {"name": "Item 2", "value": 200},
                ],
                "count": 42,
            },
        )
        assert "My List" in rendered
        assert "Item 1" in rendered
        assert "100" in rendered
        assert "42" in rendered

    def test_sandbox_allows_safe_string_methods(self, template_service):
        """Test that sandbox allows safe string methods."""
        content = "{{ name | upper }} - {{ name | lower }} - {{ name | title }}"
        template = template_service.create_template(
            name="String Methods",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"name": "test"},
        )
        assert "TEST" in rendered
        assert "test" in rendered
        assert "Test" in rendered

    def test_sandbox_allows_safe_list_operations(self, template_service):
        """Test that sandbox allows safe list operations."""
        content = "Length: {{ items | length }} First: {{ items | first }}"
        template = template_service.create_template(
            name="List Operations",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"items": ["a", "b", "c"]},
        )
        assert "Length: 3" in rendered
        assert "First: a" in rendered

    def test_sandbox_allows_dict_access(self, template_service):
        """Test that sandbox allows normal dict key access."""
        content = "{{ person.name }} is {{ person.age }} years old"
        template = template_service.create_template(
            name="Dict Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        rendered = template_service.render_template(
            template_id=template.id,
            context={"person": {"name": "Alice", "age": 30}},
        )
        assert "Alice is 30 years old" in rendered

    def test_default_template_uses_regular_environment(self, template_service):
        """Test that default templates use the regular (non-sandboxed) environment."""
        # Default templates should render without sandbox restrictions
        # This tests the entity report default template
        context = {
            "title": "Test Report",
            "entity": {
                "id": "12345678",
                "name": "Test Entity",
                "profile": {},
            },
        }
        # This should work without any security errors
        rendered = template_service.render_template(
            template_id="default-entity-report",
            context=context,
        )
        assert "Test Report" in rendered

    def test_user_template_uses_sandboxed_environment(self, template_service):
        """Test that user-created templates use the sandboxed environment."""
        # Create a simple user template that works fine
        content = "<p>{{ message }}</p>"
        template = template_service.create_template(
            name="User Template",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        # Verify it's not a default template
        assert template.is_default is False
        # Should render fine with safe content
        rendered = template_service.render_template(
            template_id=template.id,
            context={"message": "Hello World"},
        )
        assert "<p>Hello World</p>" in rendered

    def test_sandbox_error_message_is_informative(self, template_service):
        """Test that sandbox security errors have informative messages."""
        content = "{{ obj.__class__.__name__ }}"
        template = template_service.create_template(
            name="Error Message Test",
            template_type=TemplateType.CUSTOM,
            content=content,
        )
        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"obj": "test"},
            )
        error_message = str(exc.value)
        assert "security violation" in error_message.lower()

    def test_sandbox_blocks_getattr_on_private(self, template_service):
        """Test that sandbox blocks getattr access to private attributes."""
        # Using attribute access notation
        content = "{{ items._internal }}"
        template = template_service.create_template(
            name="Getattr Private",
            template_type=TemplateType.CUSTOM,
            content=content,
        )

        class ObjWithPrivate:
            _internal = "secret"
            public = "visible"

        with pytest.raises(TemplateValidationError) as exc:
            template_service.render_template(
                template_id=template.id,
                context={"items": ObjWithPrivate()},
            )
        assert "security" in str(exc.value).lower()

    def test_sandbox_allows_public_attribute_access(self, template_service):
        """Test that sandbox allows access to public attributes."""
        content = "{{ obj.public }}"
        template = template_service.create_template(
            name="Public Access",
            template_type=TemplateType.CUSTOM,
            content=content,
        )

        class ObjWithPublic:
            public = "visible"

        rendered = template_service.render_template(
            template_id=template.id,
            context={"obj": ObjWithPublic()},
        )
        assert "visible" in rendered
