"""
Graph Format Converter Service for Basset Hound OSINT Platform.

Provides format conversion between different graph formats for import/export:
- GraphML, GEXF, JSON Graph, Cytoscape.js, D3.js, DOT, Pajek, Adjacency List
"""

import json
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from xml.dom import minidom

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class GraphFormat(str, Enum):
    """Supported graph formats for import/export."""
    GRAPHML = "graphml"
    GEXF = "gexf"
    JSON_GRAPH = "json_graph"
    CYTOSCAPE = "cytoscape"
    D3 = "d3"
    DOT = "dot"
    PAJEK = "pajek"
    ADJACENCY_LIST = "adjacency_list"


class EdgeDirection(str, Enum):
    """Edge direction handling options."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"
    PRESERVE = "preserve"


class ConversionOptions(BaseModel):
    """Options for format conversion."""
    include_properties: bool = Field(default=True, description="Include node/edge properties")
    edge_direction: EdgeDirection = Field(default=EdgeDirection.PRESERVE)
    include_metadata: bool = Field(default=True, description="Include graph metadata")
    pretty_print: bool = Field(default=True, description="Format output for readability")
    node_id_prefix: str = Field(default="", description="Prefix for node IDs")
    default_node_label: str = Field(default="Node", description="Default node label")
    default_edge_label: str = Field(default="CONNECTED_TO", description="Default edge label")
    exclude_properties: List[str] = Field(default_factory=list)
    property_mapping: Dict[str, str] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=False)


class ConversionWarning(BaseModel):
    """Warning generated during conversion."""
    code: str
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=False)


class ConversionResult(BaseModel):
    """Result of a format conversion operation."""
    success: bool = True
    data: str = ""
    source_format: GraphFormat
    target_format: GraphFormat
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    warnings: List[ConversionWarning] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    model_config = ConfigDict(frozen=False)


class FormatValidationResult(BaseModel):
    """Result of format validation."""
    valid: bool = False
    format: GraphFormat
    errors: List[str] = Field(default_factory=list)
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    model_config = ConfigDict(frozen=False)


class FormatDetectionResult(BaseModel):
    """Result of format auto-detection."""
    detected_format: Optional[GraphFormat] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    alternative_formats: List[Tuple[GraphFormat, float]] = Field(default_factory=list)
    model_config = ConfigDict(frozen=False)


@dataclass
class InternalNode:
    """Internal representation of a graph node."""
    id: str
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "properties": self.properties.copy()}


@dataclass
class InternalEdge:
    """Internal representation of a graph edge."""
    source: str
    target: str
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    directed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target, "label": self.label,
                "properties": self.properties.copy(), "directed": self.directed}


@dataclass
class InternalGraph:
    """Internal graph representation for format conversion."""
    nodes: List[InternalNode] = field(default_factory=list)
    edges: List[InternalEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    directed: bool = True

    def get_node_ids(self) -> set:
        return {n.id for n in self.nodes}

    def get_node_by_id(self, node_id: str) -> Optional[InternalNode]:
        return next((n for n in self.nodes if n.id == node_id), None)


class GraphFormatConverter:
    """Service for converting between different graph formats."""

    def __init__(self, neo4j_handler=None):
        self.neo4j_handler = neo4j_handler
        self._parsers = {
            GraphFormat.GRAPHML: self._parse_graphml,
            GraphFormat.GEXF: self._parse_gexf,
            GraphFormat.JSON_GRAPH: self._parse_json_graph,
            GraphFormat.CYTOSCAPE: self._parse_cytoscape,
            GraphFormat.D3: self._parse_d3,
            GraphFormat.DOT: self._parse_dot,
            GraphFormat.PAJEK: self._parse_pajek,
            GraphFormat.ADJACENCY_LIST: self._parse_adjacency_list,
        }
        self._exporters = {
            GraphFormat.GRAPHML: self._export_graphml,
            GraphFormat.GEXF: self._export_gexf,
            GraphFormat.JSON_GRAPH: self._export_json_graph,
            GraphFormat.CYTOSCAPE: self._export_cytoscape,
            GraphFormat.D3: self._export_d3,
            GraphFormat.DOT: self._export_dot,
            GraphFormat.PAJEK: self._export_pajek,
            GraphFormat.ADJACENCY_LIST: self._export_adjacency_list,
        }

    def convert(self, data: str, source_format: GraphFormat, target_format: GraphFormat,
                options: Optional[ConversionOptions] = None) -> ConversionResult:
        """Convert graph data between formats."""
        options = options or ConversionOptions()
        warnings: List[ConversionWarning] = []
        try:
            graph, parse_warnings = self._parsers[source_format](data)
            warnings.extend(parse_warnings)
            graph = self._apply_options(graph, options)
            output_data, export_warnings = self._exporters[target_format](graph, options)
            warnings.extend(export_warnings)
            return ConversionResult(success=True, data=output_data, source_format=source_format,
                                   target_format=target_format, node_count=len(graph.nodes),
                                   edge_count=len(graph.edges), warnings=warnings, metadata=graph.metadata)
        except Exception as e:
            logger.error(f"Conversion failed: {e}", exc_info=True)
            return ConversionResult(success=False, source_format=source_format,
                                   target_format=target_format, error=str(e), warnings=warnings)

    def detect_format(self, data: str) -> FormatDetectionResult:
        """Auto-detect the format of graph data."""
        candidates: List[Tuple[GraphFormat, float]] = []
        d = data.strip()

        if d.startswith("<?xml") or d.startswith("<"):
            if "<graphml" in d.lower():
                candidates.append((GraphFormat.GRAPHML, 0.95))
            elif "<gexf" in d.lower():
                candidates.append((GraphFormat.GEXF, 0.95))
        if d.startswith("{") or d.startswith("["):
            try:
                parsed = json.loads(d)
                if isinstance(parsed, dict):
                    if "nodes" in parsed and "links" in parsed:
                        candidates.append((GraphFormat.D3, 0.90))
                    elif "elements" in parsed:
                        candidates.append((GraphFormat.CYTOSCAPE, 0.90))
                    elif "graph" in parsed or ("nodes" in parsed and "edges" in parsed):
                        candidates.append((GraphFormat.JSON_GRAPH, 0.85))
            except json.JSONDecodeError:
                pass
        if re.search(r'^\s*(strict\s+)?(di)?graph\s+', d, re.IGNORECASE):
            candidates.append((GraphFormat.DOT, 0.90))
        if d.lower().startswith("*vertices"):
            candidates.append((GraphFormat.PAJEK, 0.95))
        if all(re.match(r'^\s*\S+\s*:', line) or not line.strip() for line in d.split("\n")[:10]):
            candidates.append((GraphFormat.ADJACENCY_LIST, 0.70))

        candidates.sort(key=lambda x: x[1], reverse=True)
        if candidates:
            return FormatDetectionResult(detected_format=candidates[0][0], confidence=candidates[0][1],
                                        alternative_formats=candidates[1:5])
        return FormatDetectionResult()

    def validate_format(self, data: str, format: GraphFormat) -> FormatValidationResult:
        """Validate data against a specific format specification."""
        errors: List[str] = []
        try:
            graph, warnings = self._parsers[format](data)
            for w in warnings:
                if w.code.startswith("error_"):
                    errors.append(w.message)
            node_ids = graph.get_node_ids()
            for edge in graph.edges:
                if edge.source not in node_ids:
                    errors.append(f"Edge references unknown source: {edge.source}")
                if edge.target not in node_ids:
                    errors.append(f"Edge references unknown target: {edge.target}")
            return FormatValidationResult(valid=len(errors) == 0, format=format, errors=errors,
                                         node_count=len(graph.nodes), edge_count=len(graph.edges))
        except Exception as e:
            return FormatValidationResult(valid=False, format=format, errors=[f"Parse error: {e}"])

    async def export_project_as(self, project_id: str, format: GraphFormat,
                                options: Optional[ConversionOptions] = None) -> ConversionResult:
        """Export a Basset Hound project in the specified format."""
        options = options or ConversionOptions()
        if not self.neo4j_handler:
            return ConversionResult(success=False, source_format=GraphFormat.JSON_GRAPH,
                                   target_format=format, error="Neo4j handler not configured")
        try:
            graph = await self._fetch_project_graph(project_id)
            output_data, warnings = self._exporters[format](graph, options)
            return ConversionResult(success=True, data=output_data, source_format=GraphFormat.JSON_GRAPH,
                                   target_format=format, node_count=len(graph.nodes),
                                   edge_count=len(graph.edges), warnings=warnings, metadata=graph.metadata)
        except Exception as e:
            return ConversionResult(success=False, source_format=GraphFormat.JSON_GRAPH,
                                   target_format=format, error=str(e))

    async def import_from_format(self, data: str, format: GraphFormat, project_id: str,
                                 options: Optional[ConversionOptions] = None) -> ConversionResult:
        """Import graph data into a Basset Hound project."""
        options = options or ConversionOptions()
        if not self.neo4j_handler:
            return ConversionResult(success=False, source_format=format,
                                   target_format=GraphFormat.JSON_GRAPH, error="Neo4j handler not configured")
        try:
            graph, warnings = self._parsers[format](data)
            graph = self._apply_options(graph, options)
            imported_nodes, imported_edges = await self._import_to_project(graph, project_id)
            return ConversionResult(success=True, data=json.dumps({"imported_nodes": imported_nodes,
                                   "imported_edges": imported_edges}), source_format=format,
                                   target_format=GraphFormat.JSON_GRAPH, node_count=imported_nodes,
                                   edge_count=imported_edges, warnings=warnings, metadata=graph.metadata)
        except Exception as e:
            return ConversionResult(success=False, source_format=format,
                                   target_format=GraphFormat.JSON_GRAPH, error=str(e))

    def _apply_options(self, graph: InternalGraph, options: ConversionOptions) -> InternalGraph:
        """Apply conversion options to the internal graph."""
        if options.edge_direction == EdgeDirection.DIRECTED:
            graph.directed = True
            for e in graph.edges: e.directed = True
        elif options.edge_direction == EdgeDirection.UNDIRECTED:
            graph.directed = False
            for e in graph.edges: e.directed = False

        if options.node_id_prefix:
            id_map = {n.id: f"{options.node_id_prefix}{n.id}" for n in graph.nodes}
            for n in graph.nodes: n.id = id_map[n.id]
            for e in graph.edges:
                e.source = id_map.get(e.source, e.source)
                e.target = id_map.get(e.target, e.target)

        if not options.include_properties:
            for n in graph.nodes: n.properties = {}
            for e in graph.edges: e.properties = {}
        else:
            for n in graph.nodes:
                n.properties = {options.property_mapping.get(k, k): v for k, v in n.properties.items()
                               if k not in options.exclude_properties}
            for e in graph.edges:
                e.properties = {options.property_mapping.get(k, k): v for k, v in e.properties.items()
                               if k not in options.exclude_properties}

        for n in graph.nodes:
            if not n.label: n.label = options.default_node_label
        for e in graph.edges:
            if not e.label: e.label = options.default_edge_label
        return graph

    async def _fetch_project_graph(self, project_id: str) -> InternalGraph:
        """Fetch project graph data from Neo4j."""
        graph = InternalGraph(metadata={"project_id": project_id})
        async with self.neo4j_handler.driver.session() as session:
            result = await session.run(
                "MATCH (p:Project {safe_name: $pid})-[:HAS_PERSON]->(person:Person) "
                "RETURN person.id AS id, person.profile AS profile", pid=project_id)
            for r in await result.data():
                profile = r.get("profile", {}) or {}
                label = self._extract_label(profile, r["id"])
                graph.nodes.append(InternalNode(id=r["id"], label=label, properties={"profile": profile}))

            node_ids = graph.get_node_ids()
            for n in graph.nodes:
                tagged = n.properties.get("profile", {}).get("Tagged People", {})
                targets = tagged.get("tagged_people", []) or []
                rel_types = tagged.get("relationship_types", {}) or {}
                for t in (targets if isinstance(targets, list) else [targets]):
                    if t in node_ids:
                        graph.edges.append(InternalEdge(source=n.id, target=t, label=rel_types.get(t, "RELATED_TO")))
        return graph

    async def _import_to_project(self, graph: InternalGraph, project_id: str) -> Tuple[int, int]:
        """Import graph data into a project."""
        imported_nodes, imported_edges = 0, 0
        async with self.neo4j_handler.driver.session() as session:
            for n in graph.nodes:
                try:
                    await session.run(
                        "MATCH (p:Project {safe_name: $pid}) CREATE (person:Person {id: $eid, "
                        "profile: $profile, created_at: datetime()}) CREATE (p)-[:HAS_PERSON]->(person)",
                        pid=project_id, eid=n.id, profile={"profile": {"name": n.label}, **n.properties})
                    imported_nodes += 1
                except Exception as e:
                    logger.warning(f"Failed to import node {n.id}: {e}")
        return imported_nodes, imported_edges

    def _extract_label(self, profile: Dict, entity_id: str) -> str:
        """Extract display label from entity profile."""
        if "profile" in profile:
            p = profile["profile"]
            if p.get("first_name") or p.get("last_name"):
                return f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            return p.get("full_name") or p.get("name") or f"Entity_{entity_id[:8]}"
        return f"Entity_{entity_id[:8]}"

    # =========================================================================
    # PARSERS
    # =========================================================================

    def _parse_graphml(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse GraphML format."""
        warnings, graph = [], InternalGraph()
        try:
            root = ET.fromstring(data)
            ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
            graph_elem = root.find(".//g:graph", ns) or root.find(".//graph")
            if graph_elem is not None:
                graph.directed = graph_elem.get("edgedefault", "directed") == "directed"

            key_defs = {k.get("id"): k.get("attr.name", k.get("id"))
                       for k in (root.findall(".//g:key", ns) or root.findall(".//key"))}

            for n in (graph_elem.findall("g:node", ns) if graph_elem else []) or \
                     (graph_elem.findall("node") if graph_elem else []):
                props = {key_defs.get(d.get("key"), d.get("key")): d.text
                        for d in (n.findall("g:data", ns) or n.findall("data"))}
                label = props.pop("label", props.pop("name", n.get("id")))
                graph.nodes.append(InternalNode(id=n.get("id", str(uuid.uuid4())), label=label, properties=props))

            for e in (graph_elem.findall("g:edge", ns) if graph_elem else []) or \
                     (graph_elem.findall("edge") if graph_elem else []):
                props = {key_defs.get(d.get("key"), d.get("key")): d.text
                        for d in (e.findall("g:data", ns) or e.findall("data"))}
                label = props.pop("label", props.pop("type", ""))
                if e.get("source") and e.get("target"):
                    graph.edges.append(InternalEdge(source=e.get("source"), target=e.get("target"),
                                                   label=label, properties=props, directed=graph.directed))
        except ET.ParseError as e:
            warnings.append(ConversionWarning(code="error_parse", message=f"XML parse error: {e}"))
        return graph, warnings

    def _parse_gexf(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse GEXF format."""
        warnings, graph = [], InternalGraph()
        try:
            root = ET.fromstring(data)
            ns = {"g": "http://www.gexf.net/1.2draft"}
            graph_elem = root.find(".//g:graph", ns) or root.find(".//graph")
            if graph_elem:
                graph.directed = graph_elem.get("defaultedgetype", "directed") == "directed"

            nodes_elem = root.find(".//g:nodes", ns) or root.find(".//nodes")
            if nodes_elem:
                for n in nodes_elem.findall("g:node", ns) or nodes_elem.findall("node"):
                    graph.nodes.append(InternalNode(id=n.get("id"), label=n.get("label", n.get("id"))))

            edges_elem = root.find(".//g:edges", ns) or root.find(".//edges")
            if edges_elem:
                for e in edges_elem.findall("g:edge", ns) or edges_elem.findall("edge"):
                    if e.get("source") and e.get("target"):
                        graph.edges.append(InternalEdge(source=e.get("source"), target=e.get("target"),
                                                       label=e.get("label", ""), directed=graph.directed))
        except ET.ParseError as e:
            warnings.append(ConversionWarning(code="error_parse", message=f"XML parse error: {e}"))
        return graph, warnings

    def _parse_json_graph(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse JSON Graph Format."""
        warnings, graph = [], InternalGraph()
        try:
            p = json.loads(data)
            gd = p.get("graph", p)
            graph.directed = gd.get("directed", True)
            graph.metadata = gd.get("metadata", {})
            for n in gd.get("nodes", []):
                if isinstance(n, dict):
                    graph.nodes.append(InternalNode(id=str(n.get("id")), label=n.get("label", n.get("name", "")),
                                                   properties={k: v for k, v in n.items() if k not in ["id", "label", "name"]}))
                else:
                    graph.nodes.append(InternalNode(id=str(n), label=str(n)))
            for e in gd.get("edges", []):
                graph.edges.append(InternalEdge(source=str(e.get("source", e.get("from"))),
                                               target=str(e.get("target", e.get("to"))),
                                               label=e.get("label", e.get("relation", "")),
                                               directed=e.get("directed", graph.directed)))
        except json.JSONDecodeError as e:
            warnings.append(ConversionWarning(code="error_parse", message=f"JSON parse error: {e}"))
        return graph, warnings

    def _parse_cytoscape(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse Cytoscape.js JSON format."""
        warnings, graph = [], InternalGraph()
        try:
            p = json.loads(data)
            elems = p.get("elements", p)
            if isinstance(elems, list):
                nodes_data = [e for e in elems if "source" not in e.get("data", {})]
                edges_data = [e for e in elems if "source" in e.get("data", {})]
            else:
                nodes_data, edges_data = elems.get("nodes", []), elems.get("edges", [])
            for n in nodes_data:
                nd = n.get("data", n)
                graph.nodes.append(InternalNode(id=str(nd.get("id")), label=nd.get("label", nd.get("name", ""))))
            for e in edges_data:
                ed = e.get("data", e)
                graph.edges.append(InternalEdge(source=str(ed.get("source")), target=str(ed.get("target")),
                                               label=ed.get("label", "")))
        except json.JSONDecodeError as e:
            warnings.append(ConversionWarning(code="error_parse", message=f"JSON parse error: {e}"))
        return graph, warnings

    def _parse_d3(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse D3.js JSON format."""
        warnings, graph = [], InternalGraph()
        try:
            p = json.loads(data)
            idx_map = {}
            for i, n in enumerate(p.get("nodes", [])):
                nid = str(n.get("id", n.get("name", i)) if isinstance(n, dict) else n)
                idx_map[i] = nid
                graph.nodes.append(InternalNode(id=nid, label=n.get("name", nid) if isinstance(n, dict) else nid))
            for lnk in p.get("links", []):
                src = idx_map.get(lnk["source"], str(lnk["source"])) if isinstance(lnk["source"], int) else str(lnk["source"])
                tgt = idx_map.get(lnk["target"], str(lnk["target"])) if isinstance(lnk["target"], int) else str(lnk["target"])
                graph.edges.append(InternalEdge(source=src, target=tgt, label=lnk.get("type", "")))
        except json.JSONDecodeError as e:
            warnings.append(ConversionWarning(code="error_parse", message=f"JSON parse error: {e}"))
        return graph, warnings

    def _parse_dot(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse DOT (Graphviz) format."""
        warnings, graph = [], InternalGraph()
        graph.directed = "digraph" in data.lower()
        data = re.sub(r'//.*$', '', data, flags=re.MULTILINE)
        data = re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL)

        for m in re.finditer(r'(\w+)\s*\[([^\]]*)\]', data):
            if "->" not in m.group(1) and "--" not in m.group(1):
                props = dict(re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|(\w+))', m.group(2)))
                props = {k: v1 or v2 for k, (v1, v2) in [(k, (m[0], m[1])) for k, m in
                        [(k, re.match(r'(?:"([^"]*)"|(\w+))', v)) for k, v in
                         [(m[0], m[1] or m[2]) for m in re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|(\w+))', m.group(2))]]]}
                label = props.pop("label", m.group(1))
                if not graph.get_node_by_id(m.group(1)):
                    graph.nodes.append(InternalNode(id=m.group(1), label=label, properties=props))

        edge_op = "->" if graph.directed else "--"
        for m in re.finditer(rf'(\w+)\s*{re.escape(edge_op)}\s*(\w+)', data):
            src, tgt = m.group(1), m.group(2)
            if not graph.get_node_by_id(src):
                graph.nodes.append(InternalNode(id=src, label=src))
            if not graph.get_node_by_id(tgt):
                graph.nodes.append(InternalNode(id=tgt, label=tgt))
            graph.edges.append(InternalEdge(source=src, target=tgt, directed=graph.directed))
        return graph, warnings

    def _parse_pajek(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse Pajek format."""
        warnings, graph, mode = [], InternalGraph(), None
        for line in data.strip().split("\n"):
            line = line.strip()
            if not line: continue
            ll = line.lower()
            if ll.startswith("*vertices"): mode = "v"; continue
            elif ll.startswith("*arcs"): mode = "a"; graph.directed = True; continue
            elif ll.startswith("*edges"): mode = "e"; graph.directed = False; continue
            if mode == "v":
                parts = line.split(maxsplit=2)
                label = parts[1].strip('"') if len(parts) > 1 else parts[0]
                graph.nodes.append(InternalNode(id=parts[0], label=label))
            elif mode in ("a", "e"):
                parts = line.split()
                if len(parts) >= 2:
                    graph.edges.append(InternalEdge(source=parts[0], target=parts[1],
                                                   properties={"weight": float(parts[2]) if len(parts) > 2 else 1.0},
                                                   directed=(mode == "a")))
        return graph, warnings

    def _parse_adjacency_list(self, data: str) -> Tuple[InternalGraph, List[ConversionWarning]]:
        """Parse adjacency list format."""
        warnings, graph, seen = [], InternalGraph(), set()
        for line in data.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"): continue
            if ":" in line:
                src, rest = line.split(":", 1)
                src, targets = src.strip(), rest.strip().split()
            else:
                parts = line.split()
                src, targets = parts[0], parts[1:] if len(parts) > 1 else []
            if src not in seen:
                seen.add(src)
                graph.nodes.append(InternalNode(id=src, label=src))
            for t in targets:
                if t not in seen:
                    seen.add(t)
                    graph.nodes.append(InternalNode(id=t, label=t))
                graph.edges.append(InternalEdge(source=src, target=t))
        return graph, warnings

    # =========================================================================
    # EXPORTERS
    # =========================================================================

    def _export_graphml(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to GraphML format."""
        root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
        ET.SubElement(root, "key", id="label", attrib={"for": "node", "attr.name": "label", "attr.type": "string"})
        g = ET.SubElement(root, "graph", id="G", edgedefault="directed" if graph.directed else "undirected")
        for n in graph.nodes:
            ne = ET.SubElement(g, "node", id=n.id)
            d = ET.SubElement(ne, "data", key="label")
            d.text = n.label
        for i, e in enumerate(graph.edges):
            ET.SubElement(g, "edge", id=f"e{i}", source=e.source, target=e.target)
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ") if options.pretty_print else ET.tostring(root, encoding="unicode")
        return xml_str if isinstance(xml_str, str) else xml_str.decode(), []

    def _export_gexf(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to GEXF format."""
        root = ET.Element("gexf", xmlns="http://www.gexf.net/1.2draft", version="1.2")
        g = ET.SubElement(root, "graph", mode="static", defaultedgetype="directed" if graph.directed else "undirected")
        nodes = ET.SubElement(g, "nodes")
        for n in graph.nodes:
            ET.SubElement(nodes, "node", id=n.id, label=n.label)
        edges = ET.SubElement(g, "edges")
        for i, e in enumerate(graph.edges):
            ee = ET.SubElement(edges, "edge", id=str(i), source=e.source, target=e.target)
            if e.label: ee.set("label", e.label)
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ") if options.pretty_print else ET.tostring(root, encoding="unicode")
        return xml_str if isinstance(xml_str, str) else xml_str.decode(), []

    def _export_json_graph(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to JSON Graph Format."""
        out = {"graph": {"directed": graph.directed, "metadata": graph.metadata if options.include_metadata else {},
               "nodes": [{"id": n.id, "label": n.label, **({"metadata": n.properties} if options.include_properties and n.properties else {})} for n in graph.nodes],
               "edges": [{"source": e.source, "target": e.target, **({"relation": e.label} if e.label else {})} for e in graph.edges]}}
        return json.dumps(out, indent=2 if options.pretty_print else None), []

    def _export_cytoscape(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to Cytoscape.js JSON format."""
        out = {"elements": {
            "nodes": [{"data": {"id": n.id, "label": n.label}} for n in graph.nodes],
            "edges": [{"data": {"id": f"e{i}", "source": e.source, "target": e.target, **({"label": e.label} if e.label else {})}} for i, e in enumerate(graph.edges)]}}
        return json.dumps(out, indent=2 if options.pretty_print else None), []

    def _export_d3(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to D3.js JSON format."""
        out = {"nodes": [{"id": n.id, "name": n.label} for n in graph.nodes],
               "links": [{"source": e.source, "target": e.target, **({"type": e.label} if e.label else {})} for e in graph.edges]}
        return json.dumps(out, indent=2 if options.pretty_print else None), []

    def _export_dot(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to DOT format."""
        gt = "digraph" if graph.directed else "graph"
        edge_op = "->" if graph.directed else "--"
        lines = [f"{gt} G {{"]
        for n in graph.nodes:
            lines.append(f'  {n.id} [label="{n.label}"];')
        for e in graph.edges:
            lbl = f' [label="{e.label}"]' if e.label else ""
            lines.append(f"  {e.source} {edge_op} {e.target}{lbl};")
        lines.append("}")
        return "\n".join(lines), []

    def _export_pajek(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to Pajek format."""
        lines = [f"*Vertices {len(graph.nodes)}"]
        id_map = {n.id: i for i, n in enumerate(graph.nodes, 1)}
        for i, n in enumerate(graph.nodes, 1):
            lines.append(f'{i} "{n.label}"')
        lines.append("*Arcs" if graph.directed else "*Edges")
        for e in graph.edges:
            si, ti = id_map.get(e.source), id_map.get(e.target)
            if si and ti:
                lines.append(f"{si} {ti} {e.properties.get('weight', 1)}")
        return "\n".join(lines), []

    def _export_adjacency_list(self, graph: InternalGraph, options: ConversionOptions) -> Tuple[str, List[ConversionWarning]]:
        """Export to adjacency list format."""
        adj: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
        for e in graph.edges:
            if e.source in adj:
                adj[e.source].append(e.target)
            if not e.directed and e.target in adj:
                adj[e.target].append(e.source)
        return "\n".join(f"{k}: {' '.join(v)}" if v else f"{k}:" for k, v in adj.items()), []


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_graph_format_converter: Optional[GraphFormatConverter] = None


def get_graph_format_converter(neo4j_handler=None) -> GraphFormatConverter:
    """Get or create the GraphFormatConverter singleton."""
    global _graph_format_converter
    if _graph_format_converter is None:
        _graph_format_converter = GraphFormatConverter(neo4j_handler=neo4j_handler)
    elif neo4j_handler is not None:
        _graph_format_converter.neo4j_handler = neo4j_handler
    return _graph_format_converter


def set_graph_format_converter(service: Optional[GraphFormatConverter]) -> None:
    """Set the graph format converter singleton (useful for testing)."""
    global _graph_format_converter
    _graph_format_converter = service


def reset_graph_format_converter() -> None:
    """Reset the graph format converter singleton."""
    global _graph_format_converter
    _graph_format_converter = None
