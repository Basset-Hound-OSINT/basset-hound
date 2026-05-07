"""
LaTeX Report Service for PDF generation.

Handles:
- LaTeX template rendering with Jinja2
- pdflatex compilation
- PDF byte generation for download
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from api.services.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)


class LatexReportService:
    """Generate LaTeX-based PDF reports for OSINT investigations."""

    def __init__(self):
        """Initialize LaTeX report service."""
        self.template_dir = Path(__file__).parent.parent / "templates" / "latex"
        self.temp_dir = Path(tempfile.gettempdir()) / "basset_reports"
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize Jinja2 environment
        if self.template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            logger.warning(f"LaTeX template directory not found: {self.template_dir}")
            self.jinja_env = None

        self.chart_generator = ChartGenerator(format="pdf")

    def generate_entity_profile_pdf(
        self, entity_id: str, entity_data: Dict[str, Any], project_name: str = "Unknown"
    ) -> bytes:
        """
        Generate entity profile PDF.

        Args:
            entity_id: Entity identifier
            entity_data: Dictionary with entity information
            project_name: Project name for header

        Returns:
            PDF file contents as bytes
        """
        try:
            # Prepare context
            relationships = entity_data.get("relationships", [])
            network_chart = None

            if relationships:
                entities = [{"id": entity_id, "name": entity_data.get("name", entity_id)}]
                for rel in relationships:
                    entities.append(
                        {
                            "id": rel.get("target_id", "unknown"),
                            "name": rel.get("target_name", rel.get("target_id", "unknown")),
                        }
                    )

                try:
                    network_chart = self.chart_generator.relationship_network_chart(
                        entities, relationships
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate network chart: {e}")

            context = {
                "title": f"Entity Profile: {entity_data.get('name', entity_id)}",
                "project_name": project_name,
                "entity": entity_data,
                "network_image": network_chart,
            }

            # Render and compile
            tex_content = self._render_template("entity_profile.tex.j2", context)
            pdf_bytes = self._compile_latex(tex_content)

            logger.info(f"Generated entity profile PDF for {entity_id}")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate entity profile PDF: {e}")
            raise

    def generate_investigation_pdf(
        self, entities: List[Dict[str, Any]], project_name: str = "Unknown"
    ) -> bytes:
        """
        Generate multi-entity investigation summary PDF.

        Args:
            entities: List of entity dictionaries
            project_name: Project name for header

        Returns:
            PDF file contents as bytes
        """
        try:
            # Build entity type distribution
            entity_types = {}
            for entity in entities:
                etype = entity.get("entity_type", "Unknown")
                entity_types[etype] = entity_types.get(etype, 0) + 1

            distribution_chart = None
            try:
                distribution_chart = self.chart_generator.entity_distribution_chart(
                    entity_types
                )
            except Exception as e:
                logger.warning(f"Failed to generate distribution chart: {e}")

            # Build relationship summary
            relationship_summary = self._build_relationship_summary(entities)

            context = {
                "title": f"Investigation Report: {project_name}",
                "project_name": project_name,
                "entities": entities,
                "entity_types": entity_types,
                "distribution_image": distribution_chart,
                "relationship_summary": relationship_summary,
            }

            # Render and compile
            tex_content = self._render_template("investigation_summary.tex.j2", context)
            pdf_bytes = self._compile_latex(tex_content)

            logger.info(f"Generated investigation PDF for {len(entities)} entities")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate investigation PDF: {e}")
            raise

    def generate_relationship_report(
        self, entity_id: str, entity_data: Dict[str, Any], depth: int = 2, project_name: str = "Unknown"
    ) -> bytes:
        """
        Generate relationship network PDF.

        Args:
            entity_id: Central entity ID
            entity_data: Entity data with relationships
            depth: Relationship depth to include
            project_name: Project name for header

        Returns:
            PDF file contents as bytes
        """
        try:
            relationships = entity_data.get("relationships", [])
            network_chart = None

            if relationships:
                entities = [{"id": entity_id, "name": entity_data.get("name", entity_id)}]
                for rel in relationships:
                    entities.append(
                        {
                            "id": rel.get("target_id", "unknown"),
                            "name": rel.get("target_name", rel.get("target_id", "unknown")),
                        }
                    )

                try:
                    network_chart = self.chart_generator.relationship_network_chart(
                        entities, relationships
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate network chart: {e}")

            context = {
                "title": f"Relationship Report: {entity_data.get('name', entity_id)}",
                "project_name": project_name,
                "entity": entity_data,
                "relationship_count": len(relationships),
                "network_image": network_chart,
                "relationships": relationships[:10],  # Show first 10
            }

            tex_content = self._render_template("entity_profile.tex.j2", context)
            pdf_bytes = self._compile_latex(tex_content)

            logger.info(f"Generated relationship report for {entity_id}")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate relationship report: {e}")
            raise

    def generate_timeline_report(
        self, entity_id: str, events: List[Dict[str, Any]], project_name: str = "Unknown"
    ) -> bytes:
        """
        Generate timeline report PDF.

        Args:
            entity_id: Entity identifier
            events: List of timeline events
            project_name: Project name for header

        Returns:
            PDF file contents as bytes
        """
        try:
            timeline_chart = None
            if events:
                try:
                    timeline_chart = self.chart_generator.timeline_chart(events)
                except Exception as e:
                    logger.warning(f"Failed to generate timeline chart: {e}")

            context = {
                "title": f"Timeline Report: {entity_id}",
                "project_name": project_name,
                "events": events,
                "timeline_image": timeline_chart,
            }

            tex_content = self._render_template("timeline.tex.j2", context)
            pdf_bytes = self._compile_latex(tex_content)

            logger.info(f"Generated timeline report for {entity_id}")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to generate timeline report: {e}")
            raise

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render Jinja2 LaTeX template.

        Args:
            template_name: Template filename
            context: Context dictionary

        Returns:
            Rendered LaTeX content as string
        """
        try:
            if not self.jinja_env:
                raise RuntimeError("Jinja2 environment not initialized")

            template = self.jinja_env.get_template(template_name)
            return template.render(**context)

        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise

    def _compile_latex(self, tex_content: str) -> bytes:
        """
        Compile LaTeX to PDF using pdflatex.

        Args:
            tex_content: LaTeX source code

        Returns:
            PDF file contents as bytes
        """
        temp_work_dir = None
        try:
            # Create temporary work directory
            temp_work_dir = Path(tempfile.mkdtemp(prefix="basset_latex_"))

            # Write .tex file
            tex_file = temp_work_dir / "report.tex"
            tex_file.write_text(tex_content, encoding="utf-8")

            # Compile with pdflatex
            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={temp_work_dir}",
                str(tex_file),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"pdflatex compilation failed: {result.stderr}")
                logger.error(f"pdflatex stdout: {result.stdout}")

            # Read PDF output
            pdf_file = temp_work_dir / "report.pdf"
            if pdf_file.exists():
                pdf_bytes = pdf_file.read_bytes()
                logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
                return pdf_bytes
            else:
                raise RuntimeError("PDF file not generated by pdflatex")

        except subprocess.TimeoutExpired:
            logger.error("pdflatex compilation timeout")
            raise
        except Exception as e:
            logger.error(f"Failed to compile LaTeX: {e}")
            raise
        finally:
            # Cleanup temporary files
            if temp_work_dir and temp_work_dir.exists():
                try:
                    import shutil

                    shutil.rmtree(temp_work_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    def _build_relationship_summary(self, entities: List[Dict[str, Any]]) -> str:
        """
        Build a text summary of relationships between entities.

        Args:
            entities: List of entity dictionaries

        Returns:
            Summary text
        """
        summary_lines = []

        for entity in entities:
            rel_count = len(entity.get("relationships", []))
            if rel_count > 0:
                summary_lines.append(
                    f"\\item {entity.get('name', 'Unknown')} has {rel_count} relationship(s)"
                )

        if summary_lines:
            return "\\begin{itemize}\n" + "\n".join(summary_lines) + "\n\\end{itemize}"
        else:
            return "No relationships found."

    def cleanup(self):
        """Clean up temporary report files and charts."""
        try:
            self.chart_generator.cleanup()

            import shutil

            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up report directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directories: {e}")
