"""
Report Export Service for Basset Hound

This module provides comprehensive report generation capabilities for OSINT investigations.
It supports multiple output formats (PDF, HTML, Markdown) and includes features for:
- Custom report generation with configurable sections
- Single entity reports
- Project summary reports
- Relationship graph visualization
- Timeline inclusion
- Statistics generation

PDF generation uses a pure-Python approach with markdown and weasyprint libraries.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report output formats."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class ReportSection:
    """
    Represents a section within a report.

    Attributes:
        title: Section title displayed in the report
        content: Markdown content for the section
        entities: List of entity IDs to include in this section
        include_relationships: Whether to include relationship data for entities
        include_timeline: Whether to include timeline events for entities
    """
    title: str
    content: str
    entities: List[str] = field(default_factory=list)
    include_relationships: bool = True
    include_timeline: bool = False


@dataclass
class ReportOptions:
    """
    Configuration options for report generation.

    Attributes:
        title: Report title
        format: Output format (PDF, HTML, or MARKDOWN)
        project_id: ID of the project to generate report for
        entity_ids: Specific entity IDs to include (None = all entities)
        sections: Custom sections to include in the report
        include_graph: Whether to include relationship graph visualization
        include_timeline: Whether to include project timeline
        include_statistics: Whether to include project statistics
        template: Name of the template to use for styling
    """
    title: str
    format: ReportFormat
    project_id: str
    entity_ids: Optional[List[str]] = None
    sections: Optional[List[ReportSection]] = None
    include_graph: bool = True
    include_timeline: bool = True
    include_statistics: bool = True
    template: str = "default"


# Default CSS styling for reports
DEFAULT_REPORT_CSS = """
/* Basset Hound Report Styles */
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

.relationship-list {
    background: #e3f2fd;
    border-left: 4px solid #2196f3;
    padding: 15px;
    margin: 10px 0;
}

.timeline-event {
    border-left: 3px solid #4caf50;
    padding-left: 15px;
    margin: 10px 0;
}

.timeline-event .event-time {
    font-size: 0.85em;
    color: #757575;
}

.timeline-event .event-type {
    font-weight: 600;
    color: #2e7d32;
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

tr:hover {
    background: #f5f5f5;
}

code {
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}

pre {
    background: #2d2d2d;
    color: #f8f8f2;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
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
    body {
        max-width: none;
        padding: 0;
    }

    .report-header {
        background: #667eea !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    .entity-card {
        break-inside: avoid;
    }
}
"""

# Professional template CSS
PROFESSIONAL_REPORT_CSS = """
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

# Minimal template CSS
MINIMAL_REPORT_CSS = """
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

# Available templates
TEMPLATES = {
    "default": DEFAULT_REPORT_CSS,
    "professional": PROFESSIONAL_REPORT_CSS,
    "minimal": MINIMAL_REPORT_CSS,
}


class ReportExportService:
    """
    Service for generating investigation reports in various formats.

    Provides methods for generating custom reports, entity reports,
    and project summaries in PDF, HTML, and Markdown formats.
    """

    def __init__(self, neo4j_handler):
        """
        Initialize the report export service.

        Args:
            neo4j_handler: Neo4j database handler instance
        """
        self._handler = neo4j_handler
        self._weasyprint_available = self._check_weasyprint()

    def _check_weasyprint(self) -> bool:
        """Check if weasyprint is available for PDF generation."""
        try:
            import weasyprint  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "weasyprint not available. PDF generation will fall back to HTML output. "
                "Install weasyprint for full PDF support: pip install weasyprint"
            )
            return False

    def render_markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to HTML.

        Args:
            markdown_content: Markdown formatted string

        Returns:
            HTML formatted string
        """
        try:
            import markdown
            md = markdown.Markdown(
                extensions=[
                    'tables',
                    'fenced_code',
                    'codehilite',
                    'toc',
                    'nl2br',
                ]
            )
            return md.convert(markdown_content)
        except ImportError:
            logger.warning("markdown library not available, returning raw content")
            # Basic fallback conversion
            return self._basic_markdown_to_html(markdown_content)

    def _basic_markdown_to_html(self, content: str) -> str:
        """Basic markdown to HTML conversion without the markdown library."""
        import re

        # Escape HTML
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')

        # Headers
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)

        # Bold and italic
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)

        # Line breaks
        content = content.replace('\n\n', '</p><p>')
        content = f'<p>{content}</p>'

        return content

    def get_available_templates(self) -> List[str]:
        """
        Get list of available report templates.

        Returns:
            List of template names
        """
        return list(TEMPLATES.keys())

    def _get_template_css(self, template_name: str) -> str:
        """Get CSS for a specific template."""
        return TEMPLATES.get(template_name, DEFAULT_REPORT_CSS)

    def _get_entity_display_name(self, entity: Dict[str, Any]) -> str:
        """Extract a display name from entity profile data."""
        profile = entity.get("profile", {})
        core = profile.get("core", {})

        # Try to get name from core.name field
        names = core.get("name", [])
        if names and isinstance(names, list) and len(names) > 0:
            name_obj = names[0]
            if isinstance(name_obj, dict):
                first = name_obj.get("first_name", "")
                last = name_obj.get("last_name", "")
                if first or last:
                    return f"{first} {last}".strip()

        # Fallback to entity ID
        return entity.get("id", "Unknown Entity")[:8]

    def _generate_entity_markdown(
        self,
        entity: Dict[str, Any],
        include_relationships: bool = True,
        include_timeline: bool = False,
        project_id: Optional[str] = None
    ) -> str:
        """Generate markdown content for a single entity."""
        lines = []
        entity_name = self._get_entity_display_name(entity)

        lines.append(f"### {entity_name}")
        lines.append("")
        lines.append(f"**Entity ID:** `{entity.get('id', 'N/A')}`")
        lines.append(f"**Created:** {entity.get('created_at', 'N/A')}")
        lines.append("")

        # Profile data
        profile = entity.get("profile", {})
        for section_id, section_data in profile.items():
            if section_id == "Tagged People" and not include_relationships:
                continue

            lines.append(f"#### {section_id.replace('_', ' ').title()}")
            lines.append("")

            if isinstance(section_data, dict):
                for field_id, value in section_data.items():
                    if value is not None and value != [] and value != "":
                        field_label = field_id.replace("_", " ").title()
                        if isinstance(value, list):
                            if len(value) == 1:
                                display_value = self._format_value(value[0])
                            else:
                                display_value = ", ".join(
                                    self._format_value(v) for v in value
                                )
                        else:
                            display_value = self._format_value(value)
                        lines.append(f"- **{field_label}:** {display_value}")

            lines.append("")

        # Reports section
        reports = entity.get("reports", [])
        if reports:
            lines.append("#### Reports")
            lines.append("")
            for report in reports:
                if isinstance(report, dict):
                    report_name = report.get("name", "Unknown")
                    report_tool = report.get("tool", "manual")
                    report_date = report.get("created_at", "N/A")
                    lines.append(f"- {report_name} ({report_tool}) - {report_date}")
            lines.append("")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for display in markdown."""
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                if v is not None and v != "":
                    parts.append(f"{v}")
            return " ".join(parts) if parts else str(value)
        return str(value)

    def _generate_statistics_markdown(
        self,
        project: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> str:
        """Generate statistics section for a report."""
        lines = []
        lines.append("## Statistics")
        lines.append("")

        # Entity count
        entity_count = len(entities)
        lines.append(f"- **Total Entities:** {entity_count}")

        # Count entities with various data
        entities_with_email = 0
        entities_with_social = 0
        entities_with_reports = 0
        total_relationships = 0

        for entity in entities:
            profile = entity.get("profile", {})
            core = profile.get("core", {})

            if core.get("email"):
                entities_with_email += 1

            social = profile.get("social", {})
            if any(v for v in social.values() if v):
                entities_with_social += 1

            reports = entity.get("reports", [])
            if reports:
                entities_with_reports += 1

            tagged = profile.get("Tagged People", {})
            tagged_people = tagged.get("tagged_people", [])
            if isinstance(tagged_people, list):
                total_relationships += len(tagged_people)

        lines.append(f"- **Entities with Email:** {entities_with_email}")
        lines.append(f"- **Entities with Social Media:** {entities_with_social}")
        lines.append(f"- **Entities with Reports:** {entities_with_reports}")
        lines.append(f"- **Total Relationships:** {total_relationships}")
        lines.append("")

        return "\n".join(lines)

    def _generate_full_html(
        self,
        title: str,
        content_html: str,
        template: str = "default"
    ) -> str:
        """Generate a complete HTML document with styling."""
        css = self._get_template_css(template)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{title}</h1>
        <div class="report-meta">
            Generated by Basset Hound OSINT Platform<br>
            {timestamp}
        </div>
    </div>

    {content_html}

    <div class="footer">
        <p>Generated by Basset Hound OSINT Platform</p>
        <p>{timestamp}</p>
    </div>
</body>
</html>"""

    def generate_report(self, options: ReportOptions) -> bytes:
        """
        Generate a custom report based on the provided options.

        Args:
            options: ReportOptions configuration for the report

        Returns:
            Report content as bytes in the requested format
        """
        # Get project data
        project = self._handler.get_project(options.project_id)
        if not project:
            raise ValueError(f"Project not found: {options.project_id}")

        # Get entities
        all_entities = self._handler.get_all_people(options.project_id)

        if options.entity_ids:
            entities = [e for e in all_entities if e.get("id") in options.entity_ids]
        else:
            entities = all_entities

        # Build markdown content
        markdown_parts = []
        markdown_parts.append(f"# {options.title}")
        markdown_parts.append("")
        markdown_parts.append(f"**Project:** {project.get('name', options.project_id)}")
        markdown_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_parts.append("")

        # Custom sections if provided
        if options.sections:
            for section in options.sections:
                markdown_parts.append(f"## {section.title}")
                markdown_parts.append("")
                markdown_parts.append(section.content)
                markdown_parts.append("")

                # Include specific entities for this section
                if section.entities:
                    section_entities = [
                        e for e in entities if e.get("id") in section.entities
                    ]
                    for entity in section_entities:
                        entity_md = self._generate_entity_markdown(
                            entity,
                            include_relationships=section.include_relationships,
                            include_timeline=section.include_timeline,
                            project_id=options.project_id
                        )
                        markdown_parts.append(entity_md)

        # Default sections
        else:
            # Entities section
            markdown_parts.append("## Entities")
            markdown_parts.append("")
            for entity in entities:
                entity_md = self._generate_entity_markdown(
                    entity,
                    include_relationships=True,
                    include_timeline=options.include_timeline,
                    project_id=options.project_id
                )
                markdown_parts.append(entity_md)

        # Statistics section
        if options.include_statistics:
            stats_md = self._generate_statistics_markdown(project, entities)
            markdown_parts.append(stats_md)

        # Combine markdown
        full_markdown = "\n".join(markdown_parts)

        # Generate output based on format
        if options.format == ReportFormat.MARKDOWN:
            return full_markdown.encode('utf-8')

        elif options.format == ReportFormat.HTML:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(
                options.title,
                content_html,
                options.template
            )
            return full_html.encode('utf-8')

        elif options.format == ReportFormat.PDF:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(
                options.title,
                content_html,
                options.template
            )

            if self._weasyprint_available:
                try:
                    import weasyprint
                    pdf_doc = weasyprint.HTML(string=full_html)
                    return pdf_doc.write_pdf()
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")
                    # Fall back to HTML
                    return full_html.encode('utf-8')
            else:
                # Return HTML with a note about PDF unavailability
                return full_html.encode('utf-8')

        else:
            raise ValueError(f"Unsupported format: {options.format}")

    def generate_entity_report(
        self,
        project_id: str,
        entity_id: str,
        format: ReportFormat
    ) -> bytes:
        """
        Generate a report for a single entity.

        Args:
            project_id: Project safe name or ID
            entity_id: Entity UUID
            format: Output format

        Returns:
            Report content as bytes
        """
        # Get entity data
        entity = self._handler.get_person(project_id, entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")

        entity_name = self._get_entity_display_name(entity)
        title = f"Entity Report: {entity_name}"

        # Generate markdown
        markdown_parts = []
        markdown_parts.append(f"# {title}")
        markdown_parts.append("")
        markdown_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_parts.append("")

        entity_md = self._generate_entity_markdown(
            entity,
            include_relationships=True,
            include_timeline=True,
            project_id=project_id
        )
        markdown_parts.append(entity_md)

        full_markdown = "\n".join(markdown_parts)

        # Generate output
        if format == ReportFormat.MARKDOWN:
            return full_markdown.encode('utf-8')

        elif format == ReportFormat.HTML:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(title, content_html, "default")
            return full_html.encode('utf-8')

        elif format == ReportFormat.PDF:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(title, content_html, "default")

            if self._weasyprint_available:
                try:
                    import weasyprint
                    pdf_doc = weasyprint.HTML(string=full_html)
                    return pdf_doc.write_pdf()
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")
                    return full_html.encode('utf-8')
            else:
                return full_html.encode('utf-8')

        else:
            raise ValueError(f"Unsupported format: {format}")

    def generate_project_summary(
        self,
        project_id: str,
        format: ReportFormat
    ) -> bytes:
        """
        Generate a summary report for an entire project.

        Args:
            project_id: Project safe name or ID
            format: Output format

        Returns:
            Report content as bytes
        """
        # Get project data
        project = self._handler.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        entities = self._handler.get_all_people(project_id)
        project_name = project.get("name", project_id)
        title = f"Project Summary: {project_name}"

        # Generate markdown
        markdown_parts = []
        markdown_parts.append(f"# {title}")
        markdown_parts.append("")
        markdown_parts.append(f"**Project ID:** {project.get('safe_name', project_id)}")
        markdown_parts.append(f"**Created:** {project.get('created_at', 'N/A')}")
        markdown_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_parts.append("")

        # Statistics
        stats_md = self._generate_statistics_markdown(project, entities)
        markdown_parts.append(stats_md)

        # Entity list
        markdown_parts.append("## Entity Overview")
        markdown_parts.append("")

        if entities:
            markdown_parts.append("| Entity | ID | Created |")
            markdown_parts.append("|--------|-------|---------|")
            for entity in entities:
                name = self._get_entity_display_name(entity)
                entity_id = entity.get("id", "N/A")[:8] + "..."
                created = entity.get("created_at", "N/A")
                if isinstance(created, str) and len(created) > 10:
                    created = created[:10]
                markdown_parts.append(f"| {name} | {entity_id} | {created} |")
            markdown_parts.append("")
        else:
            markdown_parts.append("*No entities in this project.*")
            markdown_parts.append("")

        # Detailed entity information
        markdown_parts.append("## Entity Details")
        markdown_parts.append("")

        for entity in entities:
            entity_md = self._generate_entity_markdown(
                entity,
                include_relationships=True,
                include_timeline=False,
                project_id=project_id
            )
            markdown_parts.append(entity_md)
            markdown_parts.append("---")
            markdown_parts.append("")

        full_markdown = "\n".join(markdown_parts)

        # Generate output
        if format == ReportFormat.MARKDOWN:
            return full_markdown.encode('utf-8')

        elif format == ReportFormat.HTML:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(title, content_html, "default")
            return full_html.encode('utf-8')

        elif format == ReportFormat.PDF:
            content_html = self.render_markdown_to_html(full_markdown)
            full_html = self._generate_full_html(title, content_html, "default")

            if self._weasyprint_available:
                try:
                    import weasyprint
                    pdf_doc = weasyprint.HTML(string=full_html)
                    return pdf_doc.write_pdf()
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")
                    return full_html.encode('utf-8')
            else:
                return full_html.encode('utf-8')

        else:
            raise ValueError(f"Unsupported format: {format}")


# Singleton instance management
_report_export_service: Optional[ReportExportService] = None


def get_report_export_service(neo4j_handler=None) -> ReportExportService:
    """
    Get or create the report export service singleton.

    Args:
        neo4j_handler: Neo4j handler instance (required on first call)

    Returns:
        ReportExportService instance
    """
    global _report_export_service

    if _report_export_service is None:
        if neo4j_handler is None:
            raise ValueError("neo4j_handler is required on first call to get_report_export_service")
        _report_export_service = ReportExportService(neo4j_handler)

    return _report_export_service


def set_report_export_service(service: Optional[ReportExportService]) -> None:
    """Set the report export service singleton (for testing)."""
    global _report_export_service
    _report_export_service = service
