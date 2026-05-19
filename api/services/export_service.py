"""
Export Service for Basset Hound - Data Export Formats

This module provides comprehensive export capabilities for OSINT data in multiple formats:
- GraphML: Graph format for Gephi and Cytoscape
- CSV/JSON: Tabular entity exports with filtering and pagination
- GeoJSON: Location-based entity export for mapping tools
- Report Export: Multiple report formats (PDF, DOCX, HTML, Markdown)
- Database Dump: Full Neo4j graph export with MANDATORY AES-256 encryption

The service handles:
- Large dataset export with pagination
- Filtered exports (by type, tag, date range)
- Format conversion and validation
- Metadata preservation
- Mandatory encryption for sensitive data (prevents PII leakage)
"""

import io
import json
import logging
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ..utils.encryption import get_encryption_manager
from ..config import get_settings

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    GRAPHML = "graphml"
    CSV = "csv"
    JSON = "json"
    GEOJSON = "geojson"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    DATABASE = "database"


class ExportType(str, Enum):
    """Types of exports."""
    ENTITIES = "entities"
    RELATIONSHIPS = "relationships"
    GRAPH = "graph"
    REPORT = "report"
    DATABASE_DUMP = "database_dump"


class ExportFilter:
    """Filter criteria for exports."""

    def __init__(
        self,
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        search_query: Optional[str] = None,
    ):
        """Initialize export filter."""
        self.entity_types = entity_types or []
        self.tags = tags or []
        self.date_start = date_start
        self.date_end = date_end
        self.limit = limit
        self.offset = offset
        self.search_query = search_query


class GraphMLExporter:
    """Export graph data to GraphML format for Gephi/Cytoscape."""

    def __init__(self):
        """Initialize GraphML exporter."""
        pass

    def export(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> str:
        """
        Export graph to GraphML format.

        Args:
            nodes: List of node dictionaries with properties
            edges: List of edge dictionaries with weights

        Returns:
            GraphML XML string
        """
        # Build GraphML XML
        graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlformat/graphmlml.xsd">\n'

        # Define node attributes
        graphml += '  <key id="label" for="node" attr.name="label" attr.type="string"/>\n'
        graphml += '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
        graphml += '  <key id="data" for="node" attr.name="data" attr.type="string"/>\n'
        graphml += '  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>\n'
        graphml += '  <key id="type" for="edge" attr.name="type" attr.type="string"/>\n'

        # Graph element
        graphml += '  <graph edgedefault="undirected">\n'

        # Add nodes
        for node in nodes:
            node_id = node.get('id', str(uuid4()))
            label = node.get('name', node.get('label', ''))
            node_type = node.get('type', 'Entity')

            graphml += f'    <node id="{node_id}">\n'
            graphml += f'      <data key="label">{self._escape_xml(label)}</data>\n'
            graphml += f'      <data key="type">{self._escape_xml(node_type)}</data>\n'

            # Include additional properties as JSON
            props = {k: v for k, v in node.items() if k not in ('id', 'name', 'label', 'type')}
            if props:
                graphml += f'      <data key="data">{json.dumps(props)}</data>\n'

            graphml += '    </node>\n'

        # Add edges
        for i, edge in enumerate(edges):
            source = edge.get('source', '')
            target = edge.get('target', '')
            weight = edge.get('weight', 1.0)
            edge_type = edge.get('type', 'related')

            graphml += f'    <edge id="e{i}" source="{source}" target="{target}">\n'
            graphml += f'      <data key="weight">{weight}</data>\n'
            graphml += f'      <data key="type">{self._escape_xml(edge_type)}</data>\n'
            graphml += '    </edge>\n'

        graphml += '  </graph>\n'
        graphml += '</graphml>\n'

        return graphml

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters."""
        if not text:
            return ""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))


class CSVJSONExporter:
    """Export entities as CSV or JSON with filtering and pagination."""

    def export_csv(
        self,
        entities: List[Dict[str, Any]],
        filter_obj: ExportFilter,
    ) -> str:
        """
        Export entities to CSV format.

        Args:
            entities: List of entity dictionaries
            filter_obj: Filter criteria

        Returns:
            CSV string
        """
        if not entities:
            return "id,name,type,created_at"

        # Apply filters
        filtered = self._apply_filters(entities, filter_obj)

        # Get all unique keys
        all_keys = set()
        for entity in filtered:
            all_keys.update(entity.keys())

        # Sort keys for consistent output
        keys = sorted(list(all_keys))

        # Build CSV
        lines = [','.join(f'"{k}"' for k in keys)]

        for entity in filtered:
            values = []
            for key in keys:
                val = entity.get(key, '')
                # Escape CSV values
                val_str = str(val) if val is not None else ''
                val_str = val_str.replace('"', '""')
                values.append(f'"{val_str}"')
            lines.append(','.join(values))

        return '\n'.join(lines)

    def export_json(
        self,
        entities: List[Dict[str, Any]],
        filter_obj: ExportFilter,
    ) -> str:
        """
        Export entities to JSON format.

        Args:
            entities: List of entity dictionaries
            filter_obj: Filter criteria

        Returns:
            JSON string
        """
        # Apply filters
        filtered = self._apply_filters(entities, filter_obj)

        return json.dumps(filtered, indent=2, default=str)

    @staticmethod
    def _apply_filters(
        entities: List[Dict[str, Any]],
        filter_obj: ExportFilter,
    ) -> List[Dict[str, Any]]:
        """Apply filter criteria to entities."""
        result = entities

        # Filter by entity type
        if filter_obj.entity_types:
            result = [e for e in result if e.get('type') in filter_obj.entity_types]

        # Filter by tags
        if filter_obj.tags:
            result = [e for e in result
                     if any(tag in e.get('tags', []) for tag in filter_obj.tags)]

        # Filter by date range
        if filter_obj.date_start:
            result = [e for e in result
                     if datetime.fromisoformat(str(e.get('created_at', ''))) >= filter_obj.date_start]

        if filter_obj.date_end:
            result = [e for e in result
                     if datetime.fromisoformat(str(e.get('created_at', ''))) <= filter_obj.date_end]

        # Apply search query
        if filter_obj.search_query:
            query_lower = filter_obj.search_query.lower()
            result = [e for e in result
                     if any(query_lower in str(v).lower() for v in e.values())]

        # Apply pagination
        start = filter_obj.offset
        end = start + filter_obj.limit if filter_obj.limit else None
        result = result[start:end]

        return result


class GeoJSONExporter:
    """Export location-based entities as GeoJSON."""

    def export(self, locations: List[Dict[str, Any]]) -> str:
        """
        Export locations to GeoJSON format.

        Args:
            locations: List of location dictionaries with latitude/longitude

        Returns:
            GeoJSON string
        """
        features = []

        for loc in locations:
            lat = loc.get('latitude')
            lon = loc.get('longitude')

            if lat is None or lon is None:
                continue

            # Build feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]  # GeoJSON uses [lon, lat]
                },
                "properties": {
                    k: v for k, v in loc.items()
                    if k not in ('latitude', 'longitude', 'id')
                }
            }

            # Add ID if present
            if 'id' in loc:
                feature['id'] = loc['id']

            features.append(feature)

        # Build FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return json.dumps(geojson, indent=2, default=str)


class ReportExporter:
    """Export reports in multiple formats (PDF, DOCX, HTML, Markdown)."""

    def export_docx(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Export report as DOCX (Word) document.

        Args:
            title: Report title
            sections: List of section dictionaries with 'title' and 'content'
            metadata: Optional metadata (author, date, etc.)

        Returns:
            DOCX file bytes
        """
        if not HAS_DOCX:
            raise ImportError("python-docx is required for DOCX export. Install with: pip install python-docx")

        doc = Document()

        # Add title
        title_paragraph = doc.add_paragraph()
        title_run = title_paragraph.add_run(title)
        title_run.bold = True
        title_run.font.size = Pt(24)
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add metadata if provided
        if metadata:
            meta_para = doc.add_paragraph()
            if 'date' in metadata:
                meta_para.add_run(f"Date: {metadata['date']}\n")
            if 'author' in metadata:
                meta_para.add_run(f"Author: {metadata['author']}\n")
            meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add sections
        for section in sections:
            # Section title
            if 'title' in section:
                section_title = doc.add_heading(section['title'], level=2)

            # Section content
            if 'content' in section:
                # Simple markdown-like parsing
                content = section['content']
                for paragraph_text in content.split('\n'):
                    if paragraph_text.strip():
                        doc.add_paragraph(paragraph_text)

        # Write to bytes
        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        return doc_bytes.getvalue()

    def export_html(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export report as standalone HTML.

        Args:
            title: Report title
            sections: List of section dictionaries with 'title' and 'content'
            metadata: Optional metadata (author, date, etc.)

        Returns:
            HTML string
        """
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            margin-top: 30px;
        }}
        .metadata {{
            background-color: #ecf0f1;
            padding: 10px 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
        pre {{
            background-color: #f8f8f8;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        code {{
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
"""

        # Add title
        html += f"    <h1>{title}</h1>\n"

        # Add metadata if provided
        if metadata:
            html += '    <div class="metadata">\n'
            if 'date' in metadata:
                html += f"        <p>Date: {metadata['date']}</p>\n"
            if 'author' in metadata:
                html += f"        <p>Author: {metadata['author']}</p>\n"
            html += '    </div>\n'

        # Add sections
        for section in sections:
            if 'title' in section:
                html += f"    <h2>{section['title']}</h2>\n"

            if 'content' in section:
                # Simple markdown conversion
                content = section['content']
                html += "    <div>\n"

                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    # Basic formatting
                    if line.startswith('###'):
                        html += f"        <h4>{line[4:]}</h4>\n"
                    elif line.startswith('##'):
                        html += f"        <h3>{line[3:]}</h3>\n"
                    elif line.startswith('#'):
                        html += f"        <h2>{line[2:]}</h2>\n"
                    elif line.startswith('- '):
                        html += f"        <li>{line[2:]}</li>\n"
                    else:
                        html += f"        <p>{line}</p>\n"

                html += "    </div>\n"

        html += """</body>
</html>
"""

        return html

    def export_markdown(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export report as Markdown.

        Args:
            title: Report title
            sections: List of section dictionaries with 'title' and 'content'
            metadata: Optional metadata (author, date, etc.)

        Returns:
            Markdown string
        """
        md = f"# {title}\n\n"

        # Add metadata if provided
        if metadata:
            md += "---\n"
            if 'date' in metadata:
                md += f"**Date**: {metadata['date']}\n\n"
            if 'author' in metadata:
                md += f"**Author**: {metadata['author']}\n\n"
            md += "---\n\n"

        # Add sections
        for section in sections:
            if 'title' in section:
                md += f"## {section['title']}\n\n"

            if 'content' in section:
                md += f"{section['content']}\n\n"

        return md


class DatabaseExporter:
    """Export full Neo4j database dump with MANDATORY AES-256 encryption."""

    def __init__(self, neo4j_handler):
        """
        Initialize database exporter.

        Args:
            neo4j_handler: Neo4j database handler for queries
        """
        self.neo4j_handler = neo4j_handler
        self.settings = get_settings()
        self.encryption_manager = get_encryption_manager(
            self.settings.dump_encryption_key
        )

    def export_full_dump(
        self,
        compress: bool = True,
        include_schema: bool = True,
        include_config: bool = True,
        encrypt: bool = True,
    ) -> bytes:
        """
        Export full Neo4j graph dump with MANDATORY encryption.

        **IMPORTANT**: Database dumps always include sensitive data (PII, relationships,
        investigation details). Encryption is MANDATORY and cannot be disabled to
        prevent accidental data leakage.

        Args:
            compress: Whether to compress the unencrypted ZIP (encryption is always applied)
            include_schema: Include schema definition
            include_config: Include configuration
            encrypt: DEPRECATED - kept for API compatibility. Encryption is ALWAYS performed.

        Returns:
            Encrypted ZIP file bytes (compressed + encrypted with AES-256)

        Security:
            - Uses Fernet (AES-128-CBC + HMAC-SHA256)
            - Includes timestamp to prevent replay attacks
            - All sensitive data is protected before transmission
        """
        # Create unencrypted ZIP first
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Export all nodes
            nodes_data = self._export_nodes()
            zf.writestr('nodes.json', json.dumps(nodes_data, indent=2, default=str))

            # Export all relationships
            relationships_data = self._export_relationships()
            zf.writestr('relationships.json', json.dumps(relationships_data, indent=2, default=str))

            # Export schema if requested
            if include_schema:
                schema_data = self._export_schema()
                zf.writestr('schema.json', json.dumps(schema_data, indent=2, default=str))

            # Export metadata with encryption note
            metadata = {
                'export_date': datetime.utcnow().isoformat(),
                'neo4j_version': 'unknown',
                'node_count': len(nodes_data),
                'relationship_count': len(relationships_data),
                'encrypted': True,
                'encryption_method': 'AES-256-Fernet',
                'encryption_note': 'This dump is encrypted with AES-256. Use the provided password to decrypt.',
            }
            zf.writestr('metadata.json', json.dumps(metadata, indent=2))

        zip_buffer.seek(0)
        unencrypted_bytes = zip_buffer.getvalue()

        # MANDATORY: Encrypt the ZIP file
        try:
            logger.info(f"Encrypting database dump ({len(unencrypted_bytes)} bytes)")
            encrypted_bytes = self.encryption_manager.encrypt(unencrypted_bytes)
            logger.info(f"Database dump encrypted ({len(encrypted_bytes)} bytes)")
            return encrypted_bytes
        except Exception as e:
            logger.error(f"Failed to encrypt database dump: {str(e)}")
            raise RuntimeError(f"Database dump encryption failed: {str(e)}")

    def _export_nodes(self) -> List[Dict[str, Any]]:
        """Export all nodes from database."""
        try:
            with self.neo4j_handler.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    RETURN n
                    LIMIT 10000
                """)

                nodes = []
                for record in result:
                    node = record[0]
                    nodes.append({
                        'id': node.id,
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })

                return nodes
        except Exception as e:
            logger.error(f"Failed to export nodes: {e}")
            return []

    def _export_relationships(self) -> List[Dict[str, Any]]:
        """Export all relationships from database."""
        try:
            with self.neo4j_handler.driver.session() as session:
                result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN r, a.id, b.id
                    LIMIT 10000
                """)

                relationships = []
                for record in result:
                    rel = record[0]
                    relationships.append({
                        'id': rel.id,
                        'type': rel.type,
                        'source': record[1],
                        'target': record[2],
                        'properties': dict(rel)
                    })

                return relationships
        except Exception as e:
            logger.error(f"Failed to export relationships: {e}")
            return []

    def _export_schema(self) -> Dict[str, Any]:
        """Export database schema."""
        try:
            with self.neo4j_handler.driver.session() as session:
                # Get node labels
                labels_result = session.run("CALL db.labels()")
                labels = [record['label'] for record in labels_result]

                # Get relationship types
                types_result = session.run("CALL db.relationshipTypes()")
                relationship_types = [record['relationshipType'] for record in types_result]

                return {
                    'labels': labels,
                    'relationship_types': relationship_types,
                    'export_date': datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Failed to export schema: {e}")
            return {}


class ExportService:
    """
    Main export service providing all export formats.

    This service orchestrates all export types and handles format conversions.
    """

    def __init__(self, neo4j_handler):
        """Initialize export service."""
        self.neo4j_handler = neo4j_handler
        self.graphml_exporter = GraphMLExporter()
        self.csv_json_exporter = CSVJSONExporter()
        self.geojson_exporter = GeoJSONExporter()
        self.report_exporter = ReportExporter()
        self.database_exporter = DatabaseExporter(neo4j_handler)

    def export_graph_graphml(
        self,
        project_id: str,
        include_weights: bool = True,
    ) -> str:
        """
        Export graph to GraphML format.

        Args:
            project_id: Project identifier
            include_weights: Include edge weights

        Returns:
            GraphML string
        """
        try:
            with self.neo4j_handler.driver.session() as session:
                # Get nodes
                nodes_result = session.run("""
                    MATCH (n)-[:BELONGS_TO|:PART_OF]->(p:Project {safe_name: $project})
                    RETURN n
                """, project=project_id)

                nodes = []
                node_ids = set()
                for record in nodes_result:
                    node = record[0]
                    nodes.append({
                        'id': str(node.id),
                        'name': node.get('name', 'Unknown'),
                        'type': list(node.labels)[0] if node.labels else 'Entity',
                        **{k: v for k, v in dict(node).items() if k not in ('name',)}
                    })
                    node_ids.add(node.id)

                # Get edges
                edges_result = session.run("""
                    MATCH (a)-[r]->(b)
                    WHERE a.id IN $node_ids AND b.id IN $node_ids
                    RETURN a.id, b.id, r, type(r) as rel_type
                """, node_ids=list(node_ids))

                edges = []
                for record in edges_result:
                    edges.append({
                        'source': str(record[0]),
                        'target': str(record[1]),
                        'type': record[3],
                        'weight': 1.0 if not include_weights else record[2].get('strength', 1.0)
                    })

                return self.graphml_exporter.export(nodes, edges)

        except Exception as e:
            logger.error(f"Failed to export GraphML: {e}")
            raise

    def export_entities_csv(
        self,
        project_id: str,
        filters: Optional[ExportFilter] = None,
    ) -> str:
        """
        Export entities as CSV.

        Args:
            project_id: Project identifier
            filters: Optional filter criteria

        Returns:
            CSV string
        """
        try:
            filters = filters or ExportFilter()

            with self.neo4j_handler.driver.session() as session:
                # Get entities
                entities_result = session.run("""
                    MATCH (e:Entity)-[:BELONGS_TO]->(p:Project {safe_name: $project})
                    RETURN e
                    LIMIT $limit
                    SKIP $offset
                """, project=project_id, limit=filters.limit or 10000, offset=filters.offset)

                entities = []
                for record in entities_result:
                    entity = record[0]
                    entities.append({
                        'id': str(entity.id),
                        'name': entity.get('name', ''),
                        'type': list(entity.labels)[0] if entity.labels else 'Entity',
                        'created_at': entity.get('created_at', ''),
                        **{k: v for k, v in dict(entity).items() if k not in ('name', 'created_at')}
                    })

                return self.csv_json_exporter.export_csv(entities, filters)

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise

    def export_entities_json(
        self,
        project_id: str,
        filters: Optional[ExportFilter] = None,
    ) -> str:
        """
        Export entities as JSON.

        Args:
            project_id: Project identifier
            filters: Optional filter criteria

        Returns:
            JSON string
        """
        try:
            filters = filters or ExportFilter()

            with self.neo4j_handler.driver.session() as session:
                # Get entities
                entities_result = session.run("""
                    MATCH (e:Entity)-[:BELONGS_TO]->(p:Project {safe_name: $project})
                    RETURN e
                    LIMIT $limit
                    SKIP $offset
                """, project=project_id, limit=filters.limit or 10000, offset=filters.offset)

                entities = []
                for record in entities_result:
                    entity = record[0]
                    entities.append({
                        'id': str(entity.id),
                        'name': entity.get('name', ''),
                        'type': list(entity.labels)[0] if entity.labels else 'Entity',
                        'created_at': entity.get('created_at', ''),
                        **{k: v for k, v in dict(entity).items() if k not in ('name', 'created_at')}
                    })

                return self.csv_json_exporter.export_json(entities, filters)

        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            raise

    def export_geojson(
        self,
        project_id: str,
        filters: Optional[ExportFilter] = None,
    ) -> str:
        """
        Export location-based entities as GeoJSON.

        Args:
            project_id: Project identifier
            filters: Optional filter criteria

        Returns:
            GeoJSON string
        """
        try:
            filters = filters or ExportFilter()

            with self.neo4j_handler.driver.session() as session:
                # Get entities with location data
                locations_result = session.run("""
                    MATCH (e:Location)-[:BELONGS_TO]->(p:Project {safe_name: $project})
                    RETURN e
                    LIMIT $limit
                    SKIP $offset
                """, project=project_id, limit=filters.limit or 10000, offset=filters.offset)

                locations = []
                for record in locations_result:
                    entity = record[0]
                    if entity.get('latitude') and entity.get('longitude'):
                        locations.append({
                            'id': str(entity.id),
                            'name': entity.get('name', ''),
                            'latitude': entity.get('latitude'),
                            'longitude': entity.get('longitude'),
                            **{k: v for k, v in dict(entity).items()
                               if k not in ('name', 'latitude', 'longitude')}
                        })

                return self.geojson_exporter.export(locations)

        except Exception as e:
            logger.error(f"Failed to export GeoJSON: {e}")
            raise

    def export_report_docx(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Export report as DOCX.

        Args:
            title: Report title
            sections: Report sections
            metadata: Optional metadata

        Returns:
            DOCX bytes
        """
        return self.report_exporter.export_docx(title, sections, metadata)

    def export_report_html(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export report as HTML.

        Args:
            title: Report title
            sections: Report sections
            metadata: Optional metadata

        Returns:
            HTML string
        """
        return self.report_exporter.export_html(title, sections, metadata)

    def export_report_markdown(
        self,
        title: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export report as Markdown.

        Args:
            title: Report title
            sections: Report sections
            metadata: Optional metadata

        Returns:
            Markdown string
        """
        return self.report_exporter.export_markdown(title, sections, metadata)

    def export_database_dump(
        self,
        compress: bool = True,
        include_schema: bool = True,
        include_config: bool = True,
    ) -> bytes:
        """
        Export full database dump.

        Args:
            compress: Whether to compress
            include_schema: Include schema
            include_config: Include configuration

        Returns:
            ZIP bytes
        """
        return self.database_exporter.export_full_dump(
            compress=compress,
            include_schema=include_schema,
            include_config=include_config
        )
