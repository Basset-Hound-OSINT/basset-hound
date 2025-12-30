"""
LLM Export Service for Basset Hound OSINT Platform.

Generates context-optimized output for consumption by LLMs and AI agents.
Supports multiple formats (Markdown, JSON, YAML, Plain Text, XML) with
intelligent token optimization and configurable context building.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

import yaml

logger = logging.getLogger("basset_hound.llm_export")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class LLMExportFormat(str, Enum):
    """Supported export formats for LLM consumption."""
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    PLAIN_TEXT = "plain_text"
    XML = "xml"


class ExportContext(BaseModel):
    """Configuration for what context to include in exports."""
    include_entities: bool = Field(default=True, description="Include entity profile data")
    include_relationships: bool = Field(default=True, description="Include relationship information")
    include_timeline: bool = Field(default=False, description="Include timeline events")
    include_orphan_data: bool = Field(default=False, description="Include related orphan data")
    include_statistics: bool = Field(default=True, description="Include summary statistics")
    include_metadata: bool = Field(default=True, description="Include export metadata")


class LLMExportConfig(BaseModel):
    """Configuration for LLM export operations."""
    format: LLMExportFormat = Field(default=LLMExportFormat.MARKDOWN, description="Output format")
    max_tokens: Optional[int] = Field(default=None, ge=100, description="Max tokens (None = unlimited)")
    context: ExportContext = Field(default_factory=ExportContext, description="Context to include")
    prioritize_fields: List[str] = Field(default_factory=lambda: ["core", "profile", "contact", "social"])
    max_field_length: int = Field(default=500, ge=50, description="Max length for field values")
    max_relationships: int = Field(default=50, ge=1, description="Max relationships to include")
    max_timeline_events: int = Field(default=20, ge=1, description="Max timeline events")
    include_raw_data: bool = Field(default=False, description="Include raw data in output")


class LLMExportResult(BaseModel):
    """Result of an LLM export operation."""
    content: str = Field(..., description="Exported content in requested format")
    format: LLMExportFormat = Field(..., description="Format of exported content")
    token_estimate: int = Field(..., ge=0, description="Estimated token count")
    truncated: bool = Field(default=False, description="Whether content was truncated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Export metadata")
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw data if requested")
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# TOKEN ESTIMATION
# =============================================================================

class TokenEstimator:
    """Estimates token counts using GPT-family approximation."""
    CHARS_PER_TOKEN = 4.0
    FORMAT_OVERHEAD = {
        LLMExportFormat.MARKDOWN: 1.1, LLMExportFormat.JSON: 1.2,
        LLMExportFormat.YAML: 1.05, LLMExportFormat.XML: 1.3, LLMExportFormat.PLAIN_TEXT: 1.0
    }

    @classmethod
    def estimate(cls, content: str, fmt: LLMExportFormat = LLMExportFormat.PLAIN_TEXT) -> int:
        if not content:
            return 0
        return int((len(content) / cls.CHARS_PER_TOKEN) * cls.FORMAT_OVERHEAD.get(fmt, 1.0))


# =============================================================================
# FORMATTERS
# =============================================================================

class ContentFormatter:
    """Base formatter with utility methods."""

    @staticmethod
    def truncate(value: Any, max_len: int) -> str:
        if value is None:
            return ""
        s = str(value) if not isinstance(value, str) else value
        return s if len(s) <= max_len else s[:max_len - 3] + "..."

    @staticmethod
    def extract_name(entity: Dict[str, Any]) -> str:
        """Extract display name from entity profile."""
        profile = entity.get('profile', {})
        for section in ['core', 'profile', 'Core', 'Profile']:
            if section in profile:
                data = profile[section]
                first, last = data.get('first_name', ''), data.get('last_name', '')
                if first or last:
                    return f"{first} {last}".strip()
                for f in ['name', 'full_name', 'display_name']:
                    if f in data:
                        val = data[f]
                        if isinstance(val, list) and val:
                            v = val[0]
                            if isinstance(v, dict):
                                return f"{v.get('first_name', '')} {v.get('last_name', '')}".strip() or str(v)
                            return str(v)
                        elif val:
                            return str(val)
        return f"Entity {entity.get('id', 'Unknown')[:8]}"

    @staticmethod
    def format_name(s: str) -> str:
        return s.replace('_', ' ').title()


class MarkdownFormatter(ContentFormatter):
    """Formats export data as Markdown."""

    @classmethod
    def entity(cls, entity: Dict, config: LLMExportConfig, rels: List[Dict] = None) -> str:
        lines = [f"# Entity: {cls.extract_name(entity)}", "",
                 f"**ID:** `{entity.get('id', 'Unknown')}`"]
        if entity.get('created_at'):
            lines.append(f"**Created:** {entity.get('created_at')}")
        lines.append("")

        profile = entity.get('profile', {})
        if profile:
            lines.extend(["## Profile Data", ""])
            for sec_id, sec_data in sorted(profile.items(), key=lambda x: (
                config.prioritize_fields.index(x[0].lower())
                if x[0].lower() in config.prioritize_fields else 999, x[0]
            )):
                if isinstance(sec_data, dict) and sec_data:
                    lines.extend([f"### {cls.format_name(sec_id)}", ""])
                    for fid, val in sec_data.items():
                        lines.append(f"- **{cls.format_name(fid)}:** {cls.truncate(val, config.max_field_length)}")
                    lines.append("")

        if rels and config.context.include_relationships:
            lines.extend(["## Relationships", ""])
            for rel in rels[:config.max_relationships]:
                lines.append(f"- {rel.get('type', 'RELATED_TO')}: **{rel.get('target_name', rel.get('target_id', 'Unknown'))}**")
            if len(rels) > config.max_relationships:
                lines.append(f"- *... and {len(rels) - config.max_relationships} more*")
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def project(cls, proj: Dict, entities: List, rels: List, config: LLMExportConfig, stats: Dict = None) -> str:
        lines = [f"# Project: {proj.get('name', 'Unknown')}", "",
                 f"**Safe Name:** `{proj.get('safe_name', 'unknown')}`"]
        if proj.get('created_at'):
            lines.append(f"**Created:** {proj.get('created_at')}")
        lines.append("")

        if config.context.include_statistics and stats:
            lines.extend(["## Statistics", "",
                f"- **Entities:** {stats.get('entity_count', len(entities))}",
                f"- **Relationships:** {stats.get('relationship_count', len(rels))}", ""])

        if entities:
            lines.extend(["## Entities", ""])
            for e in entities:
                lines.append(f"- **{cls.extract_name(e)}** (`{e.get('id', 'Unknown')[:8]}...`)")
            lines.append("")

        if rels and config.context.include_relationships:
            lines.extend(["## Relationship Summary", ""])
            types = {}
            for r in rels:
                t = r.get('type', 'RELATED_TO')
                types[t] = types.get(t, 0) + 1
            for t, c in sorted(types.items(), key=lambda x: -x[1]):
                lines.append(f"- {t}: {c}")
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def graph(cls, nodes: List, edges: List, config: LLMExportConfig) -> str:
        lines = ["# Relationship Graph", "", "## Nodes", ""]
        for n in nodes:
            lines.append(f"- **{n.get('label', n.get('id', 'Unknown'))}** ({n.get('type', 'Entity')})")
        lines.extend(["", "## Edges", ""])
        for e in edges[:config.max_relationships]:
            lines.append(f"- `{e.get('source', 'Unknown')}` --[{e.get('type', 'RELATED_TO')}]--> `{e.get('target', 'Unknown')}`")
        if len(edges) > config.max_relationships:
            lines.append(f"- *... and {len(edges) - config.max_relationships} more*")
        return "\n".join(lines)


class StructuredFormatter(ContentFormatter):
    """Formats export data as JSON, YAML, or XML."""

    @classmethod
    def _truncate_profile(cls, profile: Dict, config: LLMExportConfig) -> Dict:
        return {
            sid: {fid: cls.truncate(v, config.max_field_length) for fid, v in sd.items()}
            if isinstance(sd, dict) else cls.truncate(sd, config.max_field_length)
            for sid, sd in profile.items()
        }

    @classmethod
    def entity(cls, entity: Dict, config: LLMExportConfig, rels: List[Dict] = None, fmt: LLMExportFormat = LLMExportFormat.JSON) -> str:
        data = {"entity": {
            "id": entity.get('id'), "name": cls.extract_name(entity),
            "created_at": str(entity.get('created_at')) if entity.get('created_at') else None,
            "profile": cls._truncate_profile(entity.get('profile', {}), config)
        }}
        if rels and config.context.include_relationships:
            data["relationships"] = rels[:config.max_relationships]

        if fmt == LLMExportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        elif fmt == LLMExportFormat.YAML:
            return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:  # XML
            return cls._to_xml(data, "export")

    @classmethod
    def project(cls, proj: Dict, entities: List, rels: List, config: LLMExportConfig, stats: Dict = None, fmt: LLMExportFormat = LLMExportFormat.JSON) -> str:
        data = {
            "project": {"name": proj.get('name'), "safe_name": proj.get('safe_name'),
                       "created_at": str(proj.get('created_at')) if proj.get('created_at') else None},
            "entities": [{"id": e.get('id'), "name": cls.extract_name(e)} for e in entities]
        }
        if config.context.include_statistics and stats:
            data["statistics"] = stats
        if config.context.include_relationships:
            data["relationships"] = rels[:config.max_relationships]

        if fmt == LLMExportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        elif fmt == LLMExportFormat.YAML:
            return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            return cls._to_xml(data, "project_export")

    @classmethod
    def _to_xml(cls, data: Dict, root: str) -> str:
        def escape(s):
            return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;") if s else ""

        def to_xml(obj, tag, indent=0):
            sp = "  " * indent
            if isinstance(obj, dict):
                lines = [f"{sp}<{tag}>"]
                for k, v in obj.items():
                    lines.append(to_xml(v, k, indent + 1))
                lines.append(f"{sp}</{tag}>")
                return "\n".join(lines)
            elif isinstance(obj, list):
                return "\n".join(to_xml(i, tag[:-1] if tag.endswith('s') else 'item', indent) for i in obj)
            else:
                return f"{sp}<{tag}>{escape(obj)}</{tag}>"

        return f'<?xml version="1.0" encoding="UTF-8"?>\n{to_xml(data, root)}'


class PlainTextFormatter(ContentFormatter):
    """Formats export data as plain text."""

    @classmethod
    def entity(cls, entity: Dict, config: LLMExportConfig, rels: List[Dict] = None) -> str:
        lines = [f"ENTITY: {cls.extract_name(entity)}", f"ID: {entity.get('id', 'Unknown')}"]
        if entity.get('created_at'):
            lines.append(f"Created: {entity.get('created_at')}")
        lines.extend(["", "PROFILE:"])
        for sid, sd in entity.get('profile', {}).items():
            if isinstance(sd, dict) and sd:
                lines.append(f"  [{sid.upper()}]")
                for fid, v in sd.items():
                    lines.append(f"    {fid}: {cls.truncate(v, config.max_field_length)}")
        if rels and config.context.include_relationships:
            lines.extend(["", "RELATIONSHIPS:"])
            for r in rels[:config.max_relationships]:
                lines.append(f"  - {r.get('type', 'RELATED_TO')}: {r.get('target_name', r.get('target_id', 'Unknown'))}")
        return "\n".join(lines)

    @classmethod
    def project(cls, proj: Dict, entities: List, rels: List, config: LLMExportConfig, stats: Dict = None) -> str:
        lines = [f"PROJECT: {proj.get('name', 'Unknown')}", f"Safe Name: {proj.get('safe_name', 'unknown')}"]
        if proj.get('created_at'):
            lines.append(f"Created: {proj.get('created_at')}")
        lines.append("")
        if config.context.include_statistics and stats:
            lines.extend(["STATISTICS:", f"  Entities: {stats.get('entity_count', len(entities))}",
                         f"  Relationships: {stats.get('relationship_count', len(rels))}", ""])
        lines.append("ENTITIES:")
        for e in entities:
            lines.append(f"  - {cls.extract_name(e)} ({e.get('id', 'Unknown')[:8]}...)")
        return "\n".join(lines)


# =============================================================================
# LLM EXPORT SERVICE
# =============================================================================

class LLMExportService:
    """Service for generating LLM-optimized exports of OSINT data."""

    def __init__(self, neo4j_handler):
        self.neo4j = neo4j_handler
        self._graph_service = None
        logger.info("LLM Export Service initialized")

    @property
    def graph_service(self):
        if self._graph_service is None:
            from api.services.graph_service import GraphService
            self._graph_service = GraphService(self.neo4j)
        return self._graph_service

    def estimate_tokens(self, content: str, fmt: LLMExportFormat = LLMExportFormat.PLAIN_TEXT) -> int:
        return TokenEstimator.estimate(content, fmt)

    def _format(self, fmt: LLMExportFormat, method: str, *args, **kwargs) -> str:
        if fmt == LLMExportFormat.MARKDOWN:
            return getattr(MarkdownFormatter, method)(*args, **kwargs)
        elif fmt == LLMExportFormat.PLAIN_TEXT:
            return getattr(PlainTextFormatter, method)(*args, **kwargs)
        else:
            return getattr(StructuredFormatter, method)(*args, fmt=fmt, **kwargs)

    def _check_truncate(self, content: str, config: LLMExportConfig) -> tuple:
        truncated = False
        if config.max_tokens:
            est = self.estimate_tokens(content, config.format)
            if est > config.max_tokens:
                overhead = TokenEstimator.FORMAT_OVERHEAD.get(config.format, 1.0)
                max_chars = int((config.max_tokens * TokenEstimator.CHARS_PER_TOKEN) / overhead)
                content = content[:max_chars - 50] + "\n\n[Content truncated due to token limit]"
                truncated = True
        return content, truncated

    async def export_entity(self, entity_id: str, project_safe_name: str, config: LLMExportConfig = None) -> LLMExportResult:
        """Export a single entity for LLM consumption."""
        config = config or LLMExportConfig()
        entity = await self._get_entity(project_safe_name, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found in project {project_safe_name}")

        rels = await self._get_entity_relationships(project_safe_name, entity_id) if config.context.include_relationships else []

        if config.format in (LLMExportFormat.MARKDOWN,):
            content = MarkdownFormatter.entity(entity, config, rels)
        elif config.format == LLMExportFormat.PLAIN_TEXT:
            content = PlainTextFormatter.entity(entity, config, rels)
        else:
            content = StructuredFormatter.entity(entity, config, rels, config.format)

        content, truncated = self._check_truncate(content, config)
        return LLMExportResult(
            content=content, format=config.format, token_estimate=self.estimate_tokens(content, config.format),
            truncated=truncated, metadata={"exported_at": datetime.now().isoformat(), "entity_id": entity_id,
                "project": project_safe_name, "relationship_count": len(rels)},
            raw_data={"entity": entity, "relationships": rels} if config.include_raw_data else None
        )

    async def export_project_summary(self, project_safe_name: str, config: LLMExportConfig = None) -> LLMExportResult:
        """Export a project summary for LLM consumption."""
        config = config or LLMExportConfig()
        project = await self._get_project(project_safe_name)
        if not project:
            raise ValueError(f"Project {project_safe_name} not found")

        entities = await self._get_project_entities(project_safe_name)
        rels = self.graph_service.get_project_graph(project_safe_name).get('edges', []) if config.context.include_relationships else []
        stats = {"entity_count": len(entities), "relationship_count": len(rels)}

        if config.format == LLMExportFormat.MARKDOWN:
            content = MarkdownFormatter.project(project, entities, rels, config, stats)
        elif config.format == LLMExportFormat.PLAIN_TEXT:
            content = PlainTextFormatter.project(project, entities, rels, config, stats)
        else:
            content = StructuredFormatter.project(project, entities, rels, config, stats, config.format)

        content, truncated = self._check_truncate(content, config)
        return LLMExportResult(
            content=content, format=config.format, token_estimate=self.estimate_tokens(content, config.format),
            truncated=truncated, metadata={"exported_at": datetime.now().isoformat(), "project": project_safe_name,
                "entity_count": len(entities), "relationship_count": len(rels)},
            raw_data={"project": project, "entities": entities} if config.include_raw_data else None
        )

    async def export_entity_context(self, entity_id: str, project_safe_name: str, depth: int = 2, config: LLMExportConfig = None) -> LLMExportResult:
        """Export entity with N-hop relationship context."""
        config = config or LLMExportConfig()
        subgraph = self.graph_service.get_entity_subgraph(project_safe_name, entity_id, depth=depth)
        nodes, edges = subgraph.get('nodes', []), subgraph.get('edges', [])
        entity = await self._get_entity(project_safe_name, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        if config.format == LLMExportFormat.JSON:
            data = {"center_entity": {"id": entity.get('id'), "name": ContentFormatter.extract_name(entity), "profile": entity.get('profile', {})},
                    "context_depth": depth, "connected_entities": [{"id": n.get('id'), "name": n.get('label')} for n in nodes if n.get('id') != entity_id],
                    "relationships": edges[:config.max_relationships]}
            content = json.dumps(data, indent=2, default=str)
        elif config.format == LLMExportFormat.YAML:
            data = {"center_entity": {"id": entity.get('id'), "name": ContentFormatter.extract_name(entity)},
                    "context_depth": depth, "connected_entities": [{"id": n.get('id'), "name": n.get('label')} for n in nodes if n.get('id') != entity_id]}
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        else:
            content = MarkdownFormatter.entity(entity, config, edges)
            content += f"\n\n## Relationship Context\n\n**Depth:** {depth} hops\n**Connected Entities:** {len(nodes) - 1}\n\n"
            content += "\n".join(f"- {n.get('label', n.get('id'))} ({n.get('type', 'Entity')})" for n in nodes if n.get('id') != entity_id)

        content, truncated = self._check_truncate(content, config)
        return LLMExportResult(
            content=content, format=config.format, token_estimate=self.estimate_tokens(content, config.format),
            truncated=truncated, metadata={"exported_at": datetime.now().isoformat(), "entity_id": entity_id,
                "project": project_safe_name, "context_depth": depth, "connected_entity_count": len(nodes) - 1},
            raw_data=subgraph if config.include_raw_data else None
        )

    async def export_investigation_brief(self, project_safe_name: str, entity_ids: List[str], config: LLMExportConfig = None) -> LLMExportResult:
        """Export a focused investigation brief on specific entities."""
        config = config or LLMExportConfig()
        entities = [e for eid in entity_ids if (e := await self._get_entity(project_safe_name, eid))]
        if not entities:
            raise ValueError("No valid entities found for the provided IDs")

        entity_set = set(entity_ids)
        all_rels = [e for e in self.graph_service.get_project_graph(project_safe_name).get('edges', [])
                    if e.get('source') in entity_set or e.get('target') in entity_set]

        if config.format == LLMExportFormat.JSON:
            inter = [r for r in all_rels if r.get('source') in entity_set and r.get('target') in entity_set]
            ext = [r for r in all_rels if r not in inter]
            data = {"investigation_brief": {"project": project_safe_name,
                "focus_entities": [{"id": e.get('id'), "name": ContentFormatter.extract_name(e),
                    "profile": StructuredFormatter._truncate_profile(e.get('profile', {}), config)} for e in entities],
                "interconnections": inter[:config.max_relationships], "external_connections": ext[:config.max_relationships]}}
            content = json.dumps(data, indent=2, default=str)
        else:
            lines = ["# Investigation Brief", "", f"**Project:** {project_safe_name}",
                     f"**Focus Entities:** {len(entities)}", f"**Generated:** {datetime.now().isoformat()}", "",
                     "## Subjects of Interest", ""]
            for e in entities:
                lines.extend([f"### {ContentFormatter.extract_name(e)}", f"**ID:** `{e.get('id')}`", ""])
                for sid, sd in e.get('profile', {}).items():
                    if isinstance(sd, dict) and sd:
                        lines.append(f"**{sid.title()}:**")
                        for fid, v in list(sd.items())[:5]:
                            lines.append(f"- {fid}: {ContentFormatter.truncate(v, config.max_field_length)}")
                        lines.append("")
            inter = [r for r in all_rels if r.get('source') in entity_set and r.get('target') in entity_set]
            if inter:
                lines.extend(["## Interconnections", ""])
                for r in inter[:config.max_relationships]:
                    lines.append(f"- {r.get('source')[:8]}... --[{r.get('type')}]--> {r.get('target')[:8]}...")
            content = "\n".join(lines)

        content, truncated = self._check_truncate(content, config)
        return LLMExportResult(
            content=content, format=config.format, token_estimate=self.estimate_tokens(content, config.format),
            truncated=truncated, metadata={"exported_at": datetime.now().isoformat(), "project": project_safe_name,
                "focus_entity_count": len(entities), "relationship_count": len(all_rels)},
            raw_data={"entities": entities, "relationships": all_rels} if config.include_raw_data else None
        )

    async def export_relationship_graph(self, project_safe_name: str, config: LLMExportConfig = None) -> LLMExportResult:
        """Export the relationship graph structure for LLM analysis."""
        config = config or LLMExportConfig()
        graph = self.graph_service.get_project_graph(project_safe_name, include_orphans=False)
        nodes, edges = graph.get('nodes', []), graph.get('edges', [])

        if config.format == LLMExportFormat.JSON:
            data = {"graph": {"nodes": [{"id": n.get('id'), "label": n.get('label'), "type": n.get('type')} for n in nodes],
                    "edges": edges[:config.max_relationships]}, "statistics": {"node_count": len(nodes), "edge_count": len(edges)}}
            content = json.dumps(data, indent=2, default=str)
        elif config.format == LLMExportFormat.YAML:
            data = {"graph": {"node_count": len(nodes), "edge_count": len(edges),
                    "nodes": [{"id": n.get('id'), "label": n.get('label')} for n in nodes],
                    "edges": [{"source": e.get('source'), "target": e.get('target'), "type": e.get('type')} for e in edges[:config.max_relationships]]}}
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        else:
            content = MarkdownFormatter.graph(nodes, edges, config)

        content, truncated = self._check_truncate(content, config)
        return LLMExportResult(
            content=content, format=config.format, token_estimate=self.estimate_tokens(content, config.format),
            truncated=truncated, metadata={"exported_at": datetime.now().isoformat(), "project": project_safe_name,
                "node_count": len(nodes), "edge_count": len(edges)},
            raw_data=graph if config.include_raw_data else None
        )

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    async def _get_entity(self, project_safe_name: str, entity_id: str) -> Optional[Dict]:
        if hasattr(self.neo4j, 'get_person'):
            return await self.neo4j.get_person(project_safe_name, entity_id)
        if hasattr(self.neo4j, '_execute_query'):
            result = await self.neo4j._execute_query(
                """MATCH (project:Project {safe_name: $psn})-[:HAS_PERSON]->(person:Person {id: $pid})
                   OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                   WITH person, COLLECT({section_id: fv.section_id, field_id: fv.field_id, value: fv.value}) AS fvs
                   RETURN person, fvs""",
                {"psn": project_safe_name, "pid": entity_id}, fetch_one=True)
            if result:
                data = dict(result.get('person', {}))
                data['profile'] = {}
                for fv in result.get('fvs', []):
                    if fv.get('section_id'):
                        data['profile'].setdefault(fv['section_id'], {})[fv['field_id']] = fv['value']
                return data
        return None

    async def _get_project(self, project_safe_name: str) -> Optional[Dict]:
        if hasattr(self.neo4j, 'get_project'):
            return await self.neo4j.get_project(project_safe_name)
        if hasattr(self.neo4j, '_execute_query'):
            result = await self.neo4j._execute_query(
                "MATCH (p:Project {safe_name: $sn}) RETURN p", {"sn": project_safe_name}, fetch_one=True)
            return dict(result.get('p', {})) if result else None
        return None

    async def _get_project_entities(self, project_safe_name: str) -> List[Dict]:
        if hasattr(self.neo4j, 'get_all_people'):
            return await self.neo4j.get_all_people(project_safe_name)
        if hasattr(self.neo4j, '_execute_query'):
            results = await self.neo4j._execute_query(
                """MATCH (project:Project {safe_name: $psn})-[:HAS_PERSON]->(person:Person)
                   RETURN person ORDER BY person.created_at DESC""", {"psn": project_safe_name})
            return [dict(r.get('person', {})) for r in (results or [])]
        return []

    async def _get_entity_relationships(self, project_safe_name: str, entity_id: str) -> List[Dict]:
        graph = self.graph_service.get_project_graph(project_safe_name)
        rels = []
        node_map = {n.get('id'): n.get('label') for n in graph.get('nodes', [])}
        for e in graph.get('edges', []):
            if e.get('source') == entity_id:
                rels.append({'type': e.get('type', 'RELATED_TO'), 'target_id': e.get('target'),
                            'target_name': node_map.get(e.get('target'), e.get('target')), 'properties': e.get('properties', {})})
            elif e.get('target') == entity_id:
                rels.append({'type': e.get('type', 'RELATED_TO'), 'target_id': e.get('source'),
                            'target_name': node_map.get(e.get('source'), e.get('source')), 'direction': 'incoming', 'properties': e.get('properties', {})})
        return rels


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_llm_export_service: Optional[LLMExportService] = None


def get_llm_export_service(neo4j_handler=None) -> LLMExportService:
    """Get or create the LLM export service singleton."""
    global _llm_export_service
    if _llm_export_service is None:
        if neo4j_handler is None:
            raise ValueError("neo4j_handler is required on first call to get_llm_export_service")
        _llm_export_service = LLMExportService(neo4j_handler)
    return _llm_export_service


def set_llm_export_service(service: Optional[LLMExportService]) -> None:
    """Set the LLM export service singleton (for testing)."""
    global _llm_export_service
    _llm_export_service = service


def reset_llm_export_service() -> None:
    """Reset the LLM export service singleton."""
    global _llm_export_service
    _llm_export_service = None
