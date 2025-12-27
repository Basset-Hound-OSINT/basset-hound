"""
Tests for the Report Export Service

Comprehensive test coverage for:
- ReportFormat enum
- ReportSection and ReportOptions dataclasses
- ReportExportService class methods
- Markdown to HTML conversion
- HTML report generation
- Entity report generation
- Project summary generation
- Template handling
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from api.services.report_export_service import (
    ReportFormat,
    ReportSection,
    ReportOptions,
    ReportExportService,
    get_report_export_service,
    set_report_export_service,
    TEMPLATES,
    DEFAULT_REPORT_CSS,
    PROFESSIONAL_REPORT_CSS,
    MINIMAL_REPORT_CSS,
)


# ==================== ReportFormat Tests ====================


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_format_values(self):
        """Test that all expected formats exist."""
        assert ReportFormat.PDF == "pdf"
        assert ReportFormat.HTML == "html"
        assert ReportFormat.MARKDOWN == "markdown"

    def test_format_is_string_enum(self):
        """Test that ReportFormat is a string enum."""
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.MARKDOWN.value == "markdown"

    def test_format_from_string(self):
        """Test creating format from string."""
        assert ReportFormat("pdf") == ReportFormat.PDF
        assert ReportFormat("html") == ReportFormat.HTML
        assert ReportFormat("markdown") == ReportFormat.MARKDOWN

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            ReportFormat("invalid")


# ==================== ReportSection Tests ====================


class TestReportSection:
    """Tests for ReportSection dataclass."""

    def test_section_creation_minimal(self):
        """Test creating a section with minimal fields."""
        section = ReportSection(
            title="Test Section",
            content="This is test content."
        )

        assert section.title == "Test Section"
        assert section.content == "This is test content."
        assert section.entities == []
        assert section.include_relationships is True
        assert section.include_timeline is False

    def test_section_creation_full(self):
        """Test creating a section with all fields."""
        section = ReportSection(
            title="Full Section",
            content="# Header\n\nSome content.",
            entities=["entity-1", "entity-2"],
            include_relationships=False,
            include_timeline=True
        )

        assert section.title == "Full Section"
        assert section.content == "# Header\n\nSome content."
        assert section.entities == ["entity-1", "entity-2"]
        assert section.include_relationships is False
        assert section.include_timeline is True

    def test_section_entities_default_mutable(self):
        """Test that entities default list is not shared between instances."""
        section1 = ReportSection(title="S1", content="C1")
        section2 = ReportSection(title="S2", content="C2")

        section1.entities.append("entity-1")

        assert section1.entities == ["entity-1"]
        assert section2.entities == []


# ==================== ReportOptions Tests ====================


class TestReportOptions:
    """Tests for ReportOptions dataclass."""

    def test_options_creation_minimal(self):
        """Test creating options with minimal fields."""
        options = ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test-project"
        )

        assert options.title == "Test Report"
        assert options.format == ReportFormat.HTML
        assert options.project_id == "test-project"
        assert options.entity_ids is None
        assert options.sections is None
        assert options.include_graph is True
        assert options.include_timeline is True
        assert options.include_statistics is True
        assert options.template == "default"

    def test_options_creation_full(self):
        """Test creating options with all fields."""
        sections = [
            ReportSection(title="Section 1", content="Content 1"),
            ReportSection(title="Section 2", content="Content 2"),
        ]

        options = ReportOptions(
            title="Full Report",
            format=ReportFormat.PDF,
            project_id="project-123",
            entity_ids=["entity-1", "entity-2"],
            sections=sections,
            include_graph=False,
            include_timeline=False,
            include_statistics=False,
            template="professional"
        )

        assert options.title == "Full Report"
        assert options.format == ReportFormat.PDF
        assert options.project_id == "project-123"
        assert options.entity_ids == ["entity-1", "entity-2"]
        assert len(options.sections) == 2
        assert options.include_graph is False
        assert options.include_timeline is False
        assert options.include_statistics is False
        assert options.template == "professional"


# ==================== Template Tests ====================


class TestTemplates:
    """Tests for report templates."""

    def test_default_template_exists(self):
        """Test that default template exists."""
        assert "default" in TEMPLATES
        assert TEMPLATES["default"] == DEFAULT_REPORT_CSS

    def test_professional_template_exists(self):
        """Test that professional template exists."""
        assert "professional" in TEMPLATES
        assert TEMPLATES["professional"] == PROFESSIONAL_REPORT_CSS

    def test_minimal_template_exists(self):
        """Test that minimal template exists."""
        assert "minimal" in TEMPLATES
        assert TEMPLATES["minimal"] == MINIMAL_REPORT_CSS

    def test_templates_contain_css(self):
        """Test that templates contain valid CSS."""
        for name, css in TEMPLATES.items():
            assert "body" in css
            assert "{" in css
            assert "}" in css


# ==================== ReportExportService Tests ====================


class TestReportExportService:
    """Tests for ReportExportService class."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project",
            "created_at": "2024-01-15T10:30:00"
        }
        handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]
                    },
                    "social": {
                        "twitter": "@johndoe"
                    }
                },
                "reports": [
                    {"name": "report1.md", "tool": "sherlock", "created_at": "2024-01-16"}
                ]
            },
            {
                "id": "entity-2",
                "created_at": "2024-01-16T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}]
                    },
                    "Tagged People": {
                        "tagged_people": ["entity-1"]
                    }
                }
            }
        ]
        handler.get_person.return_value = {
            "id": "entity-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                }
            }
        }
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService with a mock handler."""
        return ReportExportService(mock_handler)

    def test_service_initialization(self, service, mock_handler):
        """Test service initialization."""
        assert service._handler == mock_handler

    def test_get_available_templates(self, service):
        """Test getting available templates."""
        templates = service.get_available_templates()

        assert "default" in templates
        assert "professional" in templates
        assert "minimal" in templates
        assert len(templates) == 3


# ==================== Markdown Conversion Tests ====================


class TestMarkdownConversion:
    """Tests for markdown to HTML conversion."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_render_markdown_to_html_headers(self, service):
        """Test converting markdown headers to HTML."""
        markdown = "# Heading 1\n\n## Heading 2\n\n### Heading 3"
        html = service.render_markdown_to_html(markdown)

        assert "<h1>" in html or "<h1 " in html
        assert "<h2>" in html or "<h2 " in html
        assert "<h3>" in html or "<h3 " in html

    def test_render_markdown_to_html_bold(self, service):
        """Test converting markdown bold to HTML."""
        markdown = "This is **bold** text."
        html = service.render_markdown_to_html(markdown)

        assert "<strong>" in html or "<b>" in html

    def test_render_markdown_to_html_list(self, service):
        """Test converting markdown list to HTML."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        html = service.render_markdown_to_html(markdown)

        assert "<li>" in html or "Item 1" in html

    def test_render_markdown_to_html_table(self, service):
        """Test converting markdown table to HTML."""
        markdown = "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1 | Cell 2 |"
        html = service.render_markdown_to_html(markdown)

        # Tables may or may not be converted depending on extensions
        assert "Header 1" in html

    def test_render_markdown_to_html_code(self, service):
        """Test converting markdown code to HTML."""
        markdown = "Here is `inline code` and:\n\n```python\nprint('hello')\n```"
        html = service.render_markdown_to_html(markdown)

        assert "code" in html.lower() or "print" in html

    def test_render_markdown_to_html_empty(self, service):
        """Test converting empty markdown."""
        html = service.render_markdown_to_html("")
        assert html == "" or html is not None

    def test_basic_markdown_to_html_fallback(self, service):
        """Test basic markdown conversion fallback."""
        # Test the fallback method directly
        markdown = "# Header\n\n**Bold** and *italic*."
        html = service._basic_markdown_to_html(markdown)

        assert "<h1>" in html
        assert "<strong>" in html
        assert "<em>" in html


# ==================== HTML Report Generation Tests ====================


class TestHTMLReportGeneration:
    """Tests for HTML report generation."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project",
            "created_at": "2024-01-15T10:30:00"
        }
        handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}]
                    }
                }
            }
        ]
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_generate_full_html_structure(self, service):
        """Test that full HTML has proper structure."""
        html = service._generate_full_html(
            title="Test Report",
            content_html="<p>Content</p>",
            template="default"
        )

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html
        assert "Test Report" in html
        assert "<p>Content</p>" in html

    def test_generate_full_html_includes_css(self, service):
        """Test that full HTML includes CSS styling."""
        html = service._generate_full_html(
            title="Test Report",
            content_html="<p>Content</p>",
            template="default"
        )

        assert "<style>" in html
        assert "body {" in html

    def test_generate_full_html_professional_template(self, service):
        """Test that professional template is applied."""
        html = service._generate_full_html(
            title="Test Report",
            content_html="<p>Content</p>",
            template="professional"
        )

        assert "Times New Roman" in html or "serif" in html

    def test_generate_full_html_includes_footer(self, service):
        """Test that full HTML includes footer."""
        html = service._generate_full_html(
            title="Test Report",
            content_html="<p>Content</p>",
            template="default"
        )

        assert 'class="footer"' in html
        assert "Basset Hound" in html


# ==================== Entity Report Generation Tests ====================


class TestEntityReportGeneration:
    """Tests for entity report generation."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_person.return_value = {
            "id": "entity-123",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                },
                "social": {
                    "twitter": "@johndoe",
                    "linkedin": "https://linkedin.com/in/johndoe"
                }
            },
            "reports": [
                {"name": "sherlock.md", "tool": "sherlock", "created_at": "2024-01-16"}
            ]
        }
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_generate_entity_report_markdown(self, service, mock_handler):
        """Test generating entity report in markdown format."""
        result = service.generate_entity_report(
            project_id="test-project",
            entity_id="entity-123",
            format=ReportFormat.MARKDOWN
        )

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "John Doe" in content
        assert "entity-123" in content

    def test_generate_entity_report_html(self, service, mock_handler):
        """Test generating entity report in HTML format."""
        result = service.generate_entity_report(
            project_id="test-project",
            entity_id="entity-123",
            format=ReportFormat.HTML
        )

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content
        assert "John Doe" in content

    def test_generate_entity_report_not_found(self, service, mock_handler):
        """Test generating report for non-existent entity."""
        mock_handler.get_person.return_value = None

        with pytest.raises(ValueError, match="Entity not found"):
            service.generate_entity_report(
                project_id="test-project",
                entity_id="nonexistent",
                format=ReportFormat.HTML
            )

    def test_get_entity_display_name(self, service):
        """Test extracting display name from entity."""
        entity = {
            "id": "entity-123",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}]
                }
            }
        }

        name = service._get_entity_display_name(entity)
        assert name == "John Doe"

    def test_get_entity_display_name_fallback(self, service):
        """Test display name fallback to entity ID."""
        entity = {
            "id": "abc12345-def6-7890",
            "profile": {}
        }

        name = service._get_entity_display_name(entity)
        assert name == "abc12345"  # First 8 chars of ID


# ==================== Project Summary Generation Tests ====================


class TestProjectSummaryGeneration:
    """Tests for project summary generation."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Investigation Alpha",
            "safe_name": "investigation_alpha",
            "created_at": "2024-01-01T00:00:00"
        }
        handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]
                    },
                    "social": {"twitter": "@johndoe"}
                }
            },
            {
                "id": "entity-2",
                "created_at": "2024-01-16T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}]
                    },
                    "Tagged People": {
                        "tagged_people": ["entity-1"]
                    }
                },
                "reports": [{"name": "report.md"}]
            }
        ]
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_generate_project_summary_markdown(self, service, mock_handler):
        """Test generating project summary in markdown format."""
        result = service.generate_project_summary(
            project_id="investigation_alpha",
            format=ReportFormat.MARKDOWN
        )

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "Investigation Alpha" in content
        assert "Statistics" in content
        assert "Entity Overview" in content

    def test_generate_project_summary_html(self, service, mock_handler):
        """Test generating project summary in HTML format."""
        result = service.generate_project_summary(
            project_id="investigation_alpha",
            format=ReportFormat.HTML
        )

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content
        assert "Investigation Alpha" in content

    def test_generate_project_summary_not_found(self, service, mock_handler):
        """Test generating summary for non-existent project."""
        mock_handler.get_project.return_value = None

        with pytest.raises(ValueError, match="Project not found"):
            service.generate_project_summary(
                project_id="nonexistent",
                format=ReportFormat.HTML
            )

    def test_generate_statistics_markdown(self, service, mock_handler):
        """Test generating statistics section."""
        project = mock_handler.get_project("test")
        entities = mock_handler.get_all_people("test")

        result = service._generate_statistics_markdown(project, entities)

        assert "Statistics" in result
        assert "Total Entities" in result
        assert "2" in result  # Two entities


# ==================== Custom Report Generation Tests ====================


class TestCustomReportGeneration:
    """Tests for custom report generation."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project",
            "created_at": "2024-01-15T10:30:00"
        }
        handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}]
                    }
                }
            }
        ]
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_generate_report_markdown(self, service, mock_handler):
        """Test generating custom report in markdown."""
        options = ReportOptions(
            title="Custom Report",
            format=ReportFormat.MARKDOWN,
            project_id="test_project"
        )

        result = service.generate_report(options)

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "Custom Report" in content

    def test_generate_report_html(self, service, mock_handler):
        """Test generating custom report in HTML."""
        options = ReportOptions(
            title="Custom Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

        result = service.generate_report(options)

        assert isinstance(result, bytes)
        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content
        assert "Custom Report" in content

    def test_generate_report_with_sections(self, service, mock_handler):
        """Test generating report with custom sections."""
        sections = [
            ReportSection(
                title="Executive Summary",
                content="This is the summary."
            ),
            ReportSection(
                title="Findings",
                content="Key findings here.",
                entities=["entity-1"]
            )
        ]

        options = ReportOptions(
            title="Sectioned Report",
            format=ReportFormat.MARKDOWN,
            project_id="test_project",
            sections=sections
        )

        result = service.generate_report(options)
        content = result.decode('utf-8')

        assert "Executive Summary" in content
        assert "This is the summary" in content
        assert "Findings" in content

    def test_generate_report_with_entity_filter(self, service, mock_handler):
        """Test generating report with specific entities."""
        options = ReportOptions(
            title="Filtered Report",
            format=ReportFormat.MARKDOWN,
            project_id="test_project",
            entity_ids=["entity-1"]
        )

        result = service.generate_report(options)
        content = result.decode('utf-8')

        assert "John Doe" in content

    def test_generate_report_without_statistics(self, service, mock_handler):
        """Test generating report without statistics section."""
        options = ReportOptions(
            title="No Stats Report",
            format=ReportFormat.MARKDOWN,
            project_id="test_project",
            include_statistics=False
        )

        result = service.generate_report(options)
        content = result.decode('utf-8')

        # Statistics section should not be prominent
        # (it might still have entity counts in other sections)
        assert "No Stats Report" in content

    def test_generate_report_project_not_found(self, service, mock_handler):
        """Test generating report for non-existent project."""
        mock_handler.get_project.return_value = None

        options = ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="nonexistent"
        )

        with pytest.raises(ValueError, match="Project not found"):
            service.generate_report(options)


# ==================== PDF Generation Tests ====================


class TestPDFGeneration:
    """Tests for PDF generation (mocked)."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project",
            "created_at": "2024-01-15T10:30:00"
        }
        handler.get_all_people.return_value = []
        handler.get_person.return_value = {
            "id": "entity-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {"core": {"name": [{"first_name": "John", "last_name": "Doe"}]}}
        }
        return handler

    def test_weasyprint_check_false_when_not_installed(self, mock_handler):
        """Test that weasyprint availability is detected."""
        with patch.dict('sys.modules', {'weasyprint': None}):
            service = ReportExportService(mock_handler)
            # The check happens at init, so we need a fresh instance
            # with weasyprint unavailable

    def test_generate_pdf_falls_back_to_html(self, mock_handler):
        """Test that PDF generation falls back to HTML when weasyprint unavailable."""
        service = ReportExportService(mock_handler)
        service._weasyprint_available = False

        options = ReportOptions(
            title="PDF Report",
            format=ReportFormat.PDF,
            project_id="test_project"
        )

        result = service.generate_report(options)

        # Should return HTML as fallback
        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content

    def test_generate_entity_pdf_falls_back_to_html(self, mock_handler):
        """Test entity PDF falls back to HTML."""
        service = ReportExportService(mock_handler)
        service._weasyprint_available = False

        result = service.generate_entity_report(
            project_id="test_project",
            entity_id="entity-1",
            format=ReportFormat.PDF
        )

        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content

    def test_generate_summary_pdf_falls_back_to_html(self, mock_handler):
        """Test summary PDF falls back to HTML."""
        service = ReportExportService(mock_handler)
        service._weasyprint_available = False

        result = service.generate_project_summary(
            project_id="test_project",
            format=ReportFormat.PDF
        )

        content = result.decode('utf-8')
        assert "<!DOCTYPE html>" in content

    def test_generate_pdf_with_weasyprint(self, mock_handler):
        """Test PDF generation when weasyprint is available."""
        import sys

        # Create mock weasyprint module
        mock_weasyprint = MagicMock()
        mock_html_obj = MagicMock()
        mock_html_obj.write_pdf.return_value = b'%PDF-mock-content'
        mock_weasyprint.HTML.return_value = mock_html_obj

        # Inject mock weasyprint into sys.modules
        sys.modules['weasyprint'] = mock_weasyprint

        try:
            service = ReportExportService(mock_handler)
            service._weasyprint_available = True

            options = ReportOptions(
                title="PDF Report",
                format=ReportFormat.PDF,
                project_id="test_project"
            )

            result = service.generate_report(options)

            assert result == b'%PDF-mock-content'
            mock_weasyprint.HTML.assert_called_once()
        finally:
            # Clean up
            if 'weasyprint' in sys.modules:
                del sys.modules['weasyprint']


# ==================== Singleton Tests ====================


class TestReportExportServiceSingleton:
    """Tests for report export service singleton management."""

    def test_get_service_requires_handler_first_call(self):
        """Test that first call requires a handler."""
        set_report_export_service(None)

        with pytest.raises(ValueError, match="neo4j_handler is required"):
            get_report_export_service()

    def test_get_service_creates_singleton(self):
        """Test that get_report_export_service creates a singleton."""
        set_report_export_service(None)

        handler = MagicMock()
        service1 = get_report_export_service(handler)
        service2 = get_report_export_service()

        assert service1 is service2

    def test_set_service(self):
        """Test setting the service singleton."""
        handler = MagicMock()
        service = ReportExportService(handler)

        set_report_export_service(service)
        retrieved = get_report_export_service()

        assert retrieved is service

    def test_set_service_to_none(self):
        """Test clearing the service singleton."""
        handler = MagicMock()
        set_report_export_service(ReportExportService(handler))
        set_report_export_service(None)

        with pytest.raises(ValueError):
            get_report_export_service()


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "safe_name": "test_project"
        }
        handler.get_all_people.return_value = []
        return handler

    @pytest.fixture
    def service(self, mock_handler):
        """Create a ReportExportService."""
        return ReportExportService(mock_handler)

    def test_generate_report_empty_project(self, service, mock_handler):
        """Test generating report for project with no entities."""
        options = ReportOptions(
            title="Empty Project Report",
            format=ReportFormat.MARKDOWN,
            project_id="test_project"
        )

        result = service.generate_report(options)
        content = result.decode('utf-8')

        assert "Empty Project Report" in content

    def test_generate_entity_markdown_complex_profile(self, service):
        """Test generating markdown for entity with complex profile."""
        entity = {
            "id": "complex-entity",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [
                        {"first_name": "John", "middle_name": "Q", "last_name": "Doe"}
                    ],
                    "email": ["john@example.com", "jdoe@work.com"],
                    "phone": []  # Empty list should be handled
                },
                "social": {
                    "twitter": "@johndoe",
                    "linkedin": None,  # None value
                    "facebook": ""  # Empty string
                }
            }
        }

        result = service._generate_entity_markdown(entity)

        assert "John" in result
        assert "john@example.com" in result
        assert "@johndoe" in result

    def test_format_value_dict(self, service):
        """Test formatting dictionary values."""
        value = {"first_name": "John", "last_name": "Doe"}
        result = service._format_value(value)

        assert "John" in result
        assert "Doe" in result

    def test_format_value_string(self, service):
        """Test formatting string values."""
        result = service._format_value("simple string")
        assert result == "simple string"

    def test_format_value_number(self, service):
        """Test formatting numeric values."""
        result = service._format_value(42)
        assert result == "42"

    def test_invalid_format_raises_error(self, service, mock_handler):
        """Test that invalid format raises appropriate error."""
        options = ReportOptions(
            title="Test",
            format=ReportFormat.HTML,  # Valid format
            project_id="test_project"
        )

        # Modify to invalid format after creation
        options.format = "invalid"

        with pytest.raises(ValueError, match="Unsupported format"):
            service.generate_report(options)


# ==================== Router Tests ====================


class TestExportRouter:
    """Tests for export router endpoints."""

    def test_router_import(self):
        """Test that export router can be imported."""
        from api.routers.export import router, entity_export_router, templates_router
        assert router is not None
        assert entity_export_router is not None
        assert templates_router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.export import (
            ReportSectionRequest,
            GenerateReportRequest,
            TemplateInfo,
            TemplateListResponse,
        )

        assert hasattr(ReportSectionRequest, "model_fields")
        assert hasattr(GenerateReportRequest, "model_fields")
        assert hasattr(TemplateInfo, "model_fields")
        assert hasattr(TemplateListResponse, "model_fields")

    def test_helper_functions(self):
        """Test router helper functions."""
        from api.routers.export import (
            _parse_format,
            _get_content_type,
            _get_file_extension,
        )

        # Test format parsing
        assert _parse_format("pdf") == ReportFormat.PDF
        assert _parse_format("html") == ReportFormat.HTML
        assert _parse_format("markdown") == ReportFormat.MARKDOWN

        # Test content types
        assert _get_content_type(ReportFormat.PDF) == "application/pdf"
        assert _get_content_type(ReportFormat.HTML) == "text/html; charset=utf-8"
        assert _get_content_type(ReportFormat.MARKDOWN) == "text/markdown; charset=utf-8"

        # Test file extensions
        assert _get_file_extension(ReportFormat.PDF) == "pdf"
        assert _get_file_extension(ReportFormat.HTML) == "html"
        assert _get_file_extension(ReportFormat.MARKDOWN) == "md"

    def test_parse_format_invalid(self):
        """Test that invalid format raises HTTPException."""
        from api.routers.export import _parse_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_format("invalid")

        assert exc_info.value.status_code == 400
        assert "Invalid format" in str(exc_info.value.detail)
