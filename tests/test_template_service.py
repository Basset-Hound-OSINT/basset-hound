"""
Tests for the Template Service

Comprehensive test coverage for:
- TemplateFormat enum
- TemplateSection and ReportTemplate dataclasses
- TemplateService class methods
- Template validation
- Template rendering
- System template protection
- Import/export functionality
- Router endpoints
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from api.services.template_service import (
    TemplateFormat,
    TemplateSection,
    ReportTemplate,
    TemplateService,
    TemplateValidationError,
    TemplateNotFoundError,
    SystemTemplateError,
    get_template_service,
    set_template_service,
    SYSTEM_TEMPLATES,
    DEFAULT_TEMPLATE_CSS,
    PROFESSIONAL_TEMPLATE_CSS,
    MINIMAL_TEMPLATE_CSS,
)


# ==================== TemplateFormat Tests ====================


class TestTemplateFormat:
    """Tests for TemplateFormat enum."""

    def test_format_values(self):
        """Test that all expected formats exist."""
        assert TemplateFormat.PDF == "pdf"
        assert TemplateFormat.HTML == "html"
        assert TemplateFormat.MARKDOWN == "markdown"

    def test_format_is_string_enum(self):
        """Test that TemplateFormat is a string enum."""
        assert TemplateFormat.PDF.value == "pdf"
        assert TemplateFormat.HTML.value == "html"
        assert TemplateFormat.MARKDOWN.value == "markdown"

    def test_format_from_string(self):
        """Test creating format from string."""
        assert TemplateFormat("pdf") == TemplateFormat.PDF
        assert TemplateFormat("html") == TemplateFormat.HTML
        assert TemplateFormat("markdown") == TemplateFormat.MARKDOWN

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            TemplateFormat("invalid")


# ==================== TemplateSection Tests ====================


class TestTemplateSection:
    """Tests for TemplateSection dataclass."""

    def test_section_creation_minimal(self):
        """Test creating a section with minimal fields."""
        section = TemplateSection(
            id="section-1",
            name="Test Section",
            template_content="<p>{{ content }}</p>"
        )

        assert section.id == "section-1"
        assert section.name == "Test Section"
        assert section.template_content == "<p>{{ content }}</p>"
        assert section.order == 0

    def test_section_creation_full(self):
        """Test creating a section with all fields."""
        section = TemplateSection(
            id="section-2",
            name="Full Section",
            template_content="<h1>{{ title }}</h1>",
            order=5
        )

        assert section.id == "section-2"
        assert section.name == "Full Section"
        assert section.template_content == "<h1>{{ title }}</h1>"
        assert section.order == 5

    def test_section_order_sorting(self):
        """Test that sections can be sorted by order."""
        sections = [
            TemplateSection(id="s3", name="Third", template_content="", order=3),
            TemplateSection(id="s1", name="First", template_content="", order=1),
            TemplateSection(id="s2", name="Second", template_content="", order=2),
        ]

        sorted_sections = sorted(sections, key=lambda s: s.order)

        assert sorted_sections[0].name == "First"
        assert sorted_sections[1].name == "Second"
        assert sorted_sections[2].name == "Third"


# ==================== ReportTemplate Tests ====================


class TestReportTemplate:
    """Tests for ReportTemplate dataclass."""

    def test_template_creation_minimal(self):
        """Test creating a template with minimal fields."""
        template = ReportTemplate(
            id="template-1",
            name="Test Template",
            description="A test template",
            content="<h1>{{ title }}</h1>",
            styles="body { color: black; }",
            format=TemplateFormat.HTML,
        )

        assert template.id == "template-1"
        assert template.name == "Test Template"
        assert template.description == "A test template"
        assert template.content == "<h1>{{ title }}</h1>"
        assert template.styles == "body { color: black; }"
        assert template.format == TemplateFormat.HTML
        assert template.variables == []
        assert template.is_system is False
        assert template.created_by is None

    def test_template_creation_full(self):
        """Test creating a template with all fields."""
        template = ReportTemplate(
            id="template-2",
            name="Full Template",
            description="A complete template",
            content="<html>{{ body }}</html>",
            styles="* { margin: 0; }",
            format=TemplateFormat.PDF,
            variables=["title", "body", "footer"],
            created_at="2024-01-15T10:30:00",
            updated_at="2024-01-16T14:20:00",
            created_by="user123",
            is_system=True,
        )

        assert template.id == "template-2"
        assert template.name == "Full Template"
        assert template.format == TemplateFormat.PDF
        assert template.variables == ["title", "body", "footer"]
        assert template.created_at == "2024-01-15T10:30:00"
        assert template.updated_at == "2024-01-16T14:20:00"
        assert template.created_by == "user123"
        assert template.is_system is True

    def test_template_to_dict(self):
        """Test converting template to dictionary."""
        template = ReportTemplate(
            id="template-3",
            name="Dict Template",
            description="For dict test",
            content="<p>Test</p>",
            styles="",
            format=TemplateFormat.HTML,
            variables=["var1"],
        )

        data = template.to_dict()

        assert data["id"] == "template-3"
        assert data["name"] == "Dict Template"
        assert data["format"] == "html"
        assert data["variables"] == ["var1"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_template_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "id": "template-4",
            "name": "From Dict",
            "description": "Created from dict",
            "content": "<div>{{ content }}</div>",
            "styles": "div { padding: 10px; }",
            "format": "html",
            "variables": ["content"],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "created_by": "admin",
            "is_system": False,
        }

        template = ReportTemplate.from_dict(data)

        assert template.id == "template-4"
        assert template.name == "From Dict"
        assert template.format == TemplateFormat.HTML
        assert template.variables == ["content"]
        assert template.created_by == "admin"

    def test_template_from_dict_defaults(self):
        """Test creating template from dict with missing fields."""
        data = {
            "name": "Minimal",
            "content": "Hello",
        }

        template = ReportTemplate.from_dict(data)

        assert template.name == "Minimal"
        assert template.content == "Hello"
        assert template.description == ""
        assert template.styles == ""
        assert template.format == TemplateFormat.HTML
        assert template.is_system is False


# ==================== System Templates Tests ====================


class TestSystemTemplates:
    """Tests for system templates."""

    def test_default_template_exists(self):
        """Test that default system template exists."""
        assert "default" in SYSTEM_TEMPLATES
        template = SYSTEM_TEMPLATES["default"]
        assert template.name == "Default"
        assert template.is_system is True

    def test_professional_template_exists(self):
        """Test that professional system template exists."""
        assert "professional" in SYSTEM_TEMPLATES
        template = SYSTEM_TEMPLATES["professional"]
        assert template.name == "Professional"
        assert template.is_system is True

    def test_minimal_template_exists(self):
        """Test that minimal system template exists."""
        assert "minimal" in SYSTEM_TEMPLATES
        template = SYSTEM_TEMPLATES["minimal"]
        assert template.name == "Minimal"
        assert template.is_system is True

    def test_system_templates_have_valid_content(self):
        """Test that system templates have content and styles."""
        for name, template in SYSTEM_TEMPLATES.items():
            assert template.content, f"{name} template has no content"
            assert template.styles, f"{name} template has no styles"
            assert "{{ title }}" in template.content or "{{title}}" in template.content

    def test_system_template_css_contains_body(self):
        """Test that CSS templates contain body styles."""
        assert "body" in DEFAULT_TEMPLATE_CSS
        assert "body" in PROFESSIONAL_TEMPLATE_CSS
        assert "body" in MINIMAL_TEMPLATE_CSS


# ==================== TemplateService CRUD Tests ====================


class TestTemplateServiceCRUD:
    """Tests for TemplateService CRUD operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh TemplateService for each test."""
        return TemplateService()

    def test_service_initialization(self, service):
        """Test service initializes with system templates."""
        templates = service.list_templates()
        system_templates = [t for t in templates if t.is_system]

        assert len(system_templates) == 3

    def test_create_template(self, service):
        """Test creating a new template."""
        template = service.create_template(
            name="New Template",
            description="A new custom template",
            content="<h1>{{ title }}</h1>",
            styles="h1 { color: blue; }",
            format=TemplateFormat.HTML,
        )

        assert template.id is not None
        assert template.name == "New Template"
        assert template.is_system is False

    def test_create_template_extracts_variables(self, service):
        """Test that creating a template extracts variables."""
        template = service.create_template(
            name="Variable Template",
            description="Has variables",
            content="{{ title }} - {{ subtitle }} - {% for item in items %}{{ item }}{% endfor %}",
        )

        assert "title" in template.variables
        assert "subtitle" in template.variables
        assert "items" in template.variables

    def test_create_template_with_explicit_variables(self, service):
        """Test creating template with explicit variables list."""
        template = service.create_template(
            name="Explicit Vars",
            description="Explicit variables",
            content="{{ a }} {{ b }}",
            variables=["x", "y", "z"],
        )

        assert template.variables == ["x", "y", "z"]

    def test_get_template_by_id(self, service):
        """Test getting template by ID."""
        created = service.create_template(
            name="Get By ID",
            description="Test",
            content="<p>Test</p>",
        )

        retrieved = service.get_template(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Get By ID"

    def test_get_template_by_name(self, service):
        """Test getting template by name."""
        service.create_template(
            name="Get By Name",
            description="Test",
            content="<p>Test</p>",
        )

        retrieved = service.get_template("Get By Name")

        assert retrieved is not None
        assert retrieved.name == "Get By Name"

    def test_get_template_by_name_case_insensitive(self, service):
        """Test getting template by name is case insensitive."""
        service.create_template(
            name="CamelCase",
            description="Test",
            content="<p>Test</p>",
        )

        retrieved = service.get_template("camelcase")

        assert retrieved is not None
        assert retrieved.name == "CamelCase"

    def test_get_template_not_found(self, service):
        """Test getting non-existent template returns None."""
        result = service.get_template("nonexistent-id")
        assert result is None

    def test_list_templates_all(self, service):
        """Test listing all templates."""
        service.create_template(name="Custom 1", description="", content="<p>1</p>")
        service.create_template(name="Custom 2", description="", content="<p>2</p>")

        templates = service.list_templates()

        assert len(templates) == 5  # 3 system + 2 custom

    def test_list_templates_filter_by_format(self, service):
        """Test listing templates filtered by format."""
        service.create_template(
            name="PDF Template",
            description="",
            content="<p>PDF</p>",
            format=TemplateFormat.PDF,
        )

        pdf_templates = service.list_templates(format=TemplateFormat.PDF)

        assert all(t.format == TemplateFormat.PDF for t in pdf_templates)

    def test_list_templates_filter_by_system(self, service):
        """Test listing templates filtered by system status."""
        service.create_template(name="Custom", description="", content="<p>Custom</p>")

        system_only = service.list_templates(is_system=True)
        custom_only = service.list_templates(is_system=False)

        assert all(t.is_system for t in system_only)
        assert all(not t.is_system for t in custom_only)
        assert len(system_only) == 3
        assert len(custom_only) == 1

    def test_update_template(self, service):
        """Test updating a template."""
        template = service.create_template(
            name="Original",
            description="Original description",
            content="<p>Original</p>",
        )

        updated = service.update_template(
            template_id=template.id,
            name="Updated",
            description="Updated description",
        )

        assert updated.name == "Updated"
        assert updated.description == "Updated description"
        assert updated.content == "<p>Original</p>"  # Unchanged

    def test_update_template_content(self, service):
        """Test updating template content re-extracts variables."""
        template = service.create_template(
            name="Content Update",
            description="",
            content="{{ old_var }}",
        )

        assert "old_var" in template.variables

        updated = service.update_template(
            template_id=template.id,
            content="{{ new_var }} {{ another_var }}",
        )

        assert "new_var" in updated.variables
        assert "another_var" in updated.variables
        assert "old_var" not in updated.variables

    def test_update_template_not_found(self, service):
        """Test updating non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            service.update_template(
                template_id="nonexistent",
                name="New Name",
            )

    def test_update_system_template_raises(self, service):
        """Test updating system template raises error."""
        system_template = service.get_template("Default")

        with pytest.raises(SystemTemplateError):
            service.update_template(
                template_id=system_template.id,
                name="New Name",
            )

    def test_delete_template(self, service):
        """Test deleting a template."""
        template = service.create_template(
            name="To Delete",
            description="",
            content="<p>Delete me</p>",
        )

        result = service.delete_template(template.id)

        assert result is True
        assert service.get_template(template.id) is None

    def test_delete_template_not_found(self, service):
        """Test deleting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            service.delete_template("nonexistent")

    def test_delete_system_template_raises(self, service):
        """Test deleting system template raises error."""
        system_template = service.get_template("Default")

        with pytest.raises(SystemTemplateError):
            service.delete_template(system_template.id)


# ==================== Template Validation Tests ====================


class TestTemplateValidation:
    """Tests for template validation."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_validate_valid_template(self, service):
        """Test validating a valid template."""
        result = service.validate_template("<h1>{{ title }}</h1>")

        assert result["valid"] is True
        assert "title" in result["variables"]
        assert "Template is valid" in result["message"]

    def test_validate_template_with_loops(self, service):
        """Test validating template with for loops."""
        content = "{% for item in items %}<p>{{ item.name }}</p>{% endfor %}"
        result = service.validate_template(content)

        assert result["valid"] is True
        assert "items" in result["variables"]

    def test_validate_template_with_conditionals(self, service):
        """Test validating template with if statements."""
        content = "{% if show_title %}<h1>{{ title }}</h1>{% endif %}"
        result = service.validate_template(content)

        assert result["valid"] is True
        assert "show_title" in result["variables"]
        assert "title" in result["variables"]

    def test_validate_invalid_template_unclosed_tag(self, service):
        """Test validating template with unclosed tag."""
        with pytest.raises(TemplateValidationError) as exc_info:
            service.validate_template("{% if condition %}<p>Missing endif</p>")

        assert "syntax error" in str(exc_info.value).lower()

    def test_validate_invalid_template_unclosed_variable(self, service):
        """Test validating template with unclosed variable."""
        with pytest.raises(TemplateValidationError) as exc_info:
            service.validate_template("<p>{{ unclosed</p>")

        assert "syntax error" in str(exc_info.value).lower()

    def test_validate_empty_template(self, service):
        """Test validating empty template."""
        result = service.validate_template("")

        assert result["valid"] is True
        assert result["variables"] == []

    def test_create_template_validates(self, service):
        """Test that creating template validates content."""
        with pytest.raises(TemplateValidationError):
            service.create_template(
                name="Invalid",
                description="",
                content="{% invalid syntax",
            )


# ==================== Template Rendering Tests ====================


class TestTemplateRendering:
    """Tests for template rendering."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_render_template_simple(self, service):
        """Test rendering a simple template."""
        template = service.create_template(
            name="Simple",
            description="",
            content="<h1>{{ title }}</h1>",
            styles="",
        )

        result = service.render_template(
            template_id=template.id,
            data={"title": "Hello World"},
        )

        assert "<h1>Hello World</h1>" in result

    def test_render_template_with_loop(self, service):
        """Test rendering template with loop."""
        template = service.create_template(
            name="Loop Template",
            description="",
            content="{% for item in items %}<li>{{ item }}</li>{% endfor %}",
        )

        result = service.render_template(
            template_id=template.id,
            data={"items": ["A", "B", "C"]},
        )

        assert "<li>A</li>" in result
        assert "<li>B</li>" in result
        assert "<li>C</li>" in result

    def test_render_template_with_conditionals(self, service):
        """Test rendering template with conditionals."""
        template = service.create_template(
            name="Conditional",
            description="",
            content="{% if show %}<p>Visible</p>{% else %}<p>Hidden</p>{% endif %}",
        )

        result_show = service.render_template(
            template_id=template.id,
            data={"show": True},
        )

        result_hide = service.render_template(
            template_id=template.id,
            data={"show": False},
        )

        assert "<p>Visible</p>" in result_show
        assert "<p>Hidden</p>" in result_hide

    def test_render_template_includes_styles(self, service):
        """Test that rendering includes styles by default."""
        template = service.create_template(
            name="Styled",
            description="",
            content="<style>{{ styles }}</style><p>{{ content }}</p>",
            styles="body { color: red; }",
        )

        result = service.render_template(
            template_id=template.id,
            data={"content": "Test"},
            include_styles=True,
        )

        assert "body { color: red; }" in result

    def test_render_template_not_found(self, service):
        """Test rendering non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            service.render_template(
                template_id="nonexistent",
                data={},
            )

    def test_render_template_missing_variable(self, service):
        """Test rendering with missing required variable."""
        template = service.create_template(
            name="Required Var",
            description="",
            content="{{ required_var }}",
        )

        with pytest.raises(TemplateValidationError) as exc_info:
            service.render_template(
                template_id=template.id,
                data={},
            )

        assert "Missing required variable" in str(exc_info.value)

    def test_render_template_adds_generated_at(self, service):
        """Test that rendering adds generated_at if not present."""
        template = service.create_template(
            name="With Date",
            description="",
            content="Generated: {{ generated_at }}",
        )

        result = service.render_template(
            template_id=template.id,
            data={},
        )

        # Should contain a date-like string
        assert "Generated:" in result
        assert "20" in result  # Year prefix


# ==================== Template Variables Tests ====================


class TestTemplateVariables:
    """Tests for template variable extraction."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_get_variables_simple(self, service):
        """Test extracting simple variables."""
        variables = service.get_template_variables("{{ a }} {{ b }} {{ c }}")

        assert variables == {"a", "b", "c"}

    def test_get_variables_nested(self, service):
        """Test extracting from nested structures."""
        content = "{{ entity.name }} {{ entity.profile.email }}"
        variables = service.get_template_variables(content)

        assert "entity" in variables

    def test_get_variables_from_loop(self, service):
        """Test extracting loop variables."""
        content = "{% for item in items %}{{ item }}{% endfor %}"
        variables = service.get_template_variables(content)

        assert "items" in variables
        # 'item' is a loop variable, not an undeclared variable

    def test_get_variables_complex(self, service):
        """Test extracting from complex template."""
        content = """
        {% if show_header %}
        <h1>{{ title }}</h1>
        {% endif %}
        {% for entity in entities %}
        <p>{{ entity.name }}</p>
        {% endfor %}
        <footer>{{ footer_text }}</footer>
        """
        variables = service.get_template_variables(content)

        assert "show_header" in variables
        assert "title" in variables
        assert "entities" in variables
        assert "footer_text" in variables

    def test_get_variables_invalid_template(self, service):
        """Test extracting from invalid template returns empty set."""
        variables = service.get_template_variables("{% invalid")

        assert variables == set()


# ==================== Template Duplication Tests ====================


class TestTemplateDuplication:
    """Tests for template duplication."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_duplicate_template(self, service):
        """Test duplicating a custom template."""
        original = service.create_template(
            name="Original",
            description="Original template",
            content="<p>{{ content }}</p>",
            styles="p { color: blue; }",
        )

        duplicate = service.duplicate_template(original.id)

        assert duplicate.id != original.id
        assert duplicate.name == "Original (Copy)"
        assert duplicate.content == original.content
        assert duplicate.styles == original.styles
        assert duplicate.is_system is False

    def test_duplicate_template_custom_name(self, service):
        """Test duplicating with custom name."""
        original = service.create_template(
            name="Original",
            description="",
            content="<p>Test</p>",
        )

        duplicate = service.duplicate_template(
            template_id=original.id,
            new_name="My Custom Copy",
        )

        assert duplicate.name == "My Custom Copy"

    def test_duplicate_system_template(self, service):
        """Test duplicating a system template."""
        system_template = service.get_template("Default")

        duplicate = service.duplicate_template(
            template_id=system_template.id,
            new_name="My Default",
        )

        assert duplicate.is_system is False
        assert duplicate.name == "My Default"
        assert duplicate.content == system_template.content

    def test_duplicate_template_not_found(self, service):
        """Test duplicating non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            service.duplicate_template("nonexistent")


# ==================== Template Export Tests ====================


class TestTemplateExport:
    """Tests for template export functionality."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_export_template(self, service):
        """Test exporting a single template."""
        template = service.create_template(
            name="Export Me",
            description="For export",
            content="<p>{{ content }}</p>",
            styles="p { margin: 10px; }",
            format=TemplateFormat.HTML,
        )

        exported = service.export_template(template.id)

        assert exported["name"] == "Export Me"
        assert exported["content"] == "<p>{{ content }}</p>"
        assert exported["styles"] == "p { margin: 10px; }"
        assert exported["format"] == "html"
        assert "exported_at" in exported
        assert exported["export_version"] == "1.0"

    def test_export_template_not_found(self, service):
        """Test exporting non-existent template raises error."""
        with pytest.raises(TemplateNotFoundError):
            service.export_template("nonexistent")

    def test_export_multiple_templates(self, service):
        """Test exporting multiple templates."""
        t1 = service.create_template(name="T1", description="", content="<p>1</p>")
        t2 = service.create_template(name="T2", description="", content="<p>2</p>")

        exported = service.export_templates([t1.id, t2.id])

        assert exported["count"] == 2
        assert len(exported["templates"]) == 2
        assert "exported_at" in exported

    def test_export_templates_skips_not_found(self, service):
        """Test export skips non-existent templates."""
        t1 = service.create_template(name="T1", description="", content="<p>1</p>")

        exported = service.export_templates([t1.id, "nonexistent"])

        assert exported["count"] == 1


# ==================== Template Import Tests ====================


class TestTemplateImport:
    """Tests for template import functionality."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_import_template(self, service):
        """Test importing a template."""
        data = {
            "name": "Imported Template",
            "description": "Imported from JSON",
            "content": "<h1>{{ title }}</h1>",
            "styles": "h1 { font-size: 24px; }",
            "format": "html",
        }

        imported = service.import_template(data)

        assert imported.name == "Imported Template"
        assert imported.content == "<h1>{{ title }}</h1>"
        assert imported.is_system is False

    def test_import_template_missing_required_field(self, service):
        """Test importing template without required field raises error."""
        data = {
            "description": "Missing name and content",
        }

        with pytest.raises(TemplateValidationError) as exc_info:
            service.import_template(data)

        assert "Missing required field" in str(exc_info.value)

    def test_import_template_invalid_content(self, service):
        """Test importing template with invalid content raises error."""
        data = {
            "name": "Invalid",
            "content": "{% unclosed",
        }

        with pytest.raises(TemplateValidationError):
            service.import_template(data)

    def test_import_template_duplicate_name_raises(self, service):
        """Test importing duplicate name without overwrite raises error."""
        service.create_template(name="Existing", description="", content="<p>1</p>")

        data = {
            "name": "Existing",
            "content": "<p>2</p>",
        }

        with pytest.raises(TemplateValidationError) as exc_info:
            service.import_template(data, overwrite=False)

        assert "already exists" in str(exc_info.value)

    def test_import_template_overwrite(self, service):
        """Test importing with overwrite replaces existing."""
        original = service.create_template(
            name="ToReplace",
            description="Original",
            content="<p>Original</p>",
        )

        data = {
            "name": "ToReplace",
            "content": "<p>Replaced</p>",
            "description": "Updated",
        }

        imported = service.import_template(data, overwrite=True)

        assert imported.id == original.id
        assert imported.content == "<p>Replaced</p>"
        assert imported.description == "Updated"

    def test_import_multiple_templates(self, service):
        """Test importing multiple templates."""
        data = {
            "templates": [
                {"name": "Import1", "content": "<p>1</p>"},
                {"name": "Import2", "content": "<p>2</p>"},
            ]
        }

        imported = service.import_templates(data)

        assert len(imported) == 2

    def test_import_templates_skips_invalid(self, service):
        """Test import skips invalid templates."""
        data = {
            "templates": [
                {"name": "Valid", "content": "<p>Valid</p>"},
                {"name": "Invalid", "content": "{% unclosed"},
            ]
        }

        imported = service.import_templates(data)

        assert len(imported) == 1
        assert imported[0].name == "Valid"


# ==================== Singleton Tests ====================


class TestTemplateServiceSingleton:
    """Tests for template service singleton management."""

    def test_get_service_creates_singleton(self):
        """Test that get_template_service creates a singleton."""
        set_template_service(None)

        service1 = get_template_service()
        service2 = get_template_service()

        assert service1 is service2

    def test_set_service(self):
        """Test setting the service singleton."""
        new_service = TemplateService()

        set_template_service(new_service)
        retrieved = get_template_service()

        assert retrieved is new_service

    def test_set_service_to_none(self):
        """Test clearing the service singleton creates new one."""
        set_template_service(None)
        service = get_template_service()

        assert service is not None


# ==================== Reset Tests ====================


class TestServiceReset:
    """Tests for service reset functionality."""

    def test_reset_to_defaults(self):
        """Test resetting service removes custom templates."""
        service = TemplateService()

        # Add custom templates
        service.create_template(name="Custom1", description="", content="<p>1</p>")
        service.create_template(name="Custom2", description="", content="<p>2</p>")

        assert len(service.list_templates(is_system=False)) == 2

        # Reset
        service.reset_to_defaults()

        assert len(service.list_templates(is_system=False)) == 0
        assert len(service.list_templates(is_system=True)) == 3

    def test_get_system_template_names(self):
        """Test getting system template names."""
        service = TemplateService()

        names = service.get_system_template_names()

        assert "Default" in names
        assert "Professional" in names
        assert "Minimal" in names


# ==================== Router Tests ====================


class TestTemplatesRouter:
    """Tests for templates router endpoints."""

    def test_router_import(self):
        """Test that templates router can be imported."""
        from api.routers.templates import router
        assert router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.templates import (
            TemplateCreate,
            TemplateUpdate,
            TemplateResponse,
            TemplateListItem,
            TemplateListResponse,
            ValidationRequest,
            ValidationResponse,
            PreviewRequest,
            PreviewResponse,
            DuplicateRequest,
            ExportRequest,
            ImportRequest,
            ImportResponse,
        )

        assert hasattr(TemplateCreate, "model_fields")
        assert hasattr(TemplateResponse, "model_fields")
        assert hasattr(ValidationResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.templates import _parse_format
        from fastapi import HTTPException

        assert _parse_format("html") == TemplateFormat.HTML
        assert _parse_format("pdf") == TemplateFormat.PDF
        assert _parse_format("markdown") == TemplateFormat.MARKDOWN

        with pytest.raises(HTTPException) as exc_info:
            _parse_format("invalid")

        assert exc_info.value.status_code == 400

    def test_template_to_response_conversion(self):
        """Test template to response conversion."""
        from api.routers.templates import _template_to_response

        template = ReportTemplate(
            id="test-id",
            name="Test",
            description="Desc",
            content="<p>Test</p>",
            styles="p {}",
            format=TemplateFormat.HTML,
            variables=["var1"],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
            created_by="user",
            is_system=False,
        )

        response = _template_to_response(template)

        assert response.id == "test-id"
        assert response.name == "Test"
        assert response.format == "html"

    def test_template_to_list_item_conversion(self):
        """Test template to list item conversion."""
        from api.routers.templates import _template_to_list_item

        template = ReportTemplate(
            id="test-id",
            name="Test",
            description="Desc",
            content="<p>Test</p>",
            styles="",
            format=TemplateFormat.PDF,
        )

        item = _template_to_list_item(template)

        assert item.id == "test-id"
        assert item.name == "Test"
        assert item.format == "pdf"


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def service(self):
        """Create a TemplateService for each test."""
        return TemplateService()

    def test_template_with_filters(self, service):
        """Test template with Jinja2 filters."""
        template = service.create_template(
            name="Filters",
            description="",
            content="{{ name | upper }} - {{ items | length }}",
        )

        result = service.render_template(
            template_id=template.id,
            data={"name": "test", "items": [1, 2, 3]},
        )

        assert "TEST" in result
        assert "3" in result

    def test_template_with_default_filter(self, service):
        """Test template with default filter."""
        template = service.create_template(
            name="Default Filter",
            description="",
            content="{{ value | default('N/A') }}",
        )

        result = service.render_template(
            template_id=template.id,
            data={},
        )

        assert "N/A" in result

    def test_template_with_nested_loops(self, service):
        """Test template with nested loops."""
        template = service.create_template(
            name="Nested",
            description="",
            content="{% for a in outer %}{% for b in inner %}{{ a }}-{{ b }}{% endfor %}{% endfor %}",
        )

        result = service.render_template(
            template_id=template.id,
            data={"outer": ["X", "Y"], "inner": [1, 2]},
        )

        assert "X-1" in result
        assert "Y-2" in result

    def test_large_template_content(self, service):
        """Test template with large content."""
        large_content = "<p>{{ var }}</p>" * 1000

        template = service.create_template(
            name="Large",
            description="",
            content=large_content,
        )

        assert len(template.content) > 10000

    def test_special_characters_in_content(self, service):
        """Test template with special characters."""
        template = service.create_template(
            name="Special",
            description="",
            content="<p>&amp; &lt; &gt; {{ data }}</p>",
        )

        result = service.render_template(
            template_id=template.id,
            data={"data": "test <script>"},
        )

        assert "&amp;" in result

    def test_unicode_content(self, service):
        """Test template with unicode characters."""
        template = service.create_template(
            name="Unicode",
            description="Unicode template",
            content="<p>{{ greeting }}</p>",
        )

        result = service.render_template(
            template_id=template.id,
            data={"greeting": "Hello World"},
        )

        assert "Hello" in result

    def test_template_with_comments(self, service):
        """Test template with Jinja2 comments."""
        template = service.create_template(
            name="Comments",
            description="",
            content="{# This is a comment #}<p>{{ content }}</p>",
        )

        result = service.render_template(
            template_id=template.id,
            data={"content": "visible"},
        )

        assert "visible" in result
        assert "comment" not in result

    def test_template_whitespace_control(self, service):
        """Test template with whitespace control."""
        template = service.create_template(
            name="Whitespace",
            description="",
            content="<p>{{- content -}}</p>",
        )

        result = service.render_template(
            template_id=template.id,
            data={"content": "test"},
        )

        assert "<p>test</p>" in result
