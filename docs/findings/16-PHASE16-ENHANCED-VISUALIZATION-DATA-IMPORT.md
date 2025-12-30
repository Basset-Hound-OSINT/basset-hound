# Phase 16: Enhanced Visualization & Data Import Connectors

**Date:** 2025-12-29
**Status:** COMPLETED

## Overview

Phase 16 focuses on enhanced graph visualization capabilities and data import connectors for common OSINT tools. This phase enables:

1. **Graph Visualization Service** - Layout algorithms, export formats, and graph metrics
2. **Data Import Connectors** - Import data from Maltego, SpiderFoot, TheHarvester, Shodan, HIBP, and generic CSV/JSON formats

## Graph Visualization Service

### Layout Algorithms Implemented

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| **Force-Directed** | Fruchterman-Reingold physics simulation | General graphs, relationship networks |
| **Hierarchical** | Tree-like level-based arrangement | Organizational charts, family trees |
| **Circular** | Nodes arranged on a circle | Small networks, showing all connections equally |
| **Radial** | Concentric circles based on distance from center | Ego networks, influence analysis |
| **Grid** | Simple grid arrangement | Large datasets, quick overview |

### Export Formats Supported

| Format | Description | Output Type |
|--------|-------------|-------------|
| **D3.js JSON** | Force-simulation compatible format | Dict with `nodes` and `links` |
| **Cytoscape.js JSON** | Graph library format | Dict with `elements` containing nodes/edges |
| **GraphML** | XML-based graph markup | String (XML) |
| **DOT** | Graphviz format | String (DOT language) |

### Graph Metrics

- **Degree Centrality** - Fraction of nodes each node is connected to
- **Betweenness Centrality** - How often node appears on shortest paths
- **Node Degrees** - Count of incoming/outgoing connections

### Key Classes

```python
from api.services.graph_visualization import (
    GraphVisualizationService,
    LayoutEngine,
    GraphMetrics,
    GraphExporter,
    LayoutAlgorithm,
    ExportFormat,
    LayoutOptions,
    ExportOptions,
    VisualizationGraph,
    VisualizationNode,
    VisualizationEdge,
)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/visualization/{project}/graph` | GET | Get project visualization with layout |
| `/visualization/{project}/entity/{id}/neighborhood` | GET | Get entity neighborhood graph |
| `/visualization/{project}/clusters` | GET | Get cluster visualization |
| `/visualization/{project}/export` | POST | Export graph in specified format |
| `/visualization/legend` | GET | Get visual legend (colors, shapes) |

### Usage Example

```python
from api.services.graph_visualization import (
    GraphVisualizationService,
    LayoutOptions,
    LayoutAlgorithm,
    ExportOptions,
    ExportFormat,
)

# Get visualization service
service = GraphVisualizationService()

# Get project graph with force-directed layout
layout_opts = LayoutOptions(
    algorithm=LayoutAlgorithm.FORCE_DIRECTED,
    iterations=100,
    width=1200,
    height=800,
)
graph = await service.get_project_visualization(
    project_safe_name="my-project",
    layout_options=layout_opts,
)

# Export to D3.js format
export_opts = ExportOptions(format=ExportFormat.D3_JSON)
d3_json = service.export_graph(graph, export_opts)
```

## Data Import Connectors

### Supported OSINT Tools

| Tool | Format | Description |
|------|--------|-------------|
| **Maltego** | CSV | Entity exports with types, properties, links |
| **SpiderFoot** | JSON | Scan results with module attribution |
| **TheHarvester** | JSON | Email, subdomain, and host discovery |
| **Shodan** | JSON | Host exports with service/banner data |
| **HIBP** | JSON | Have I Been Pwned breach data |
| **Generic CSV** | CSV | Configurable column mapping |
| **Generic JSON** | JSON | Flexible entity import |

### Connector Architecture

All connectors extend the `ImportConnector` base class:

```python
class ImportConnector(ABC):
    """Base class for OSINT tool import connectors."""

    @abstractmethod
    def parse(self, content: Union[str, bytes]) -> Generator[Dict, None, None]:
        """Parse content and yield normalized records."""
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the source tool name."""
        pass

    def import_data(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False,
        create_entities: bool = True,
        create_orphans: bool = True
    ) -> ImportResult:
        """Import data from tool export."""
        pass
```

### Import Result

```python
@dataclass
class ImportResult:
    total_records: int
    entities_created: int
    orphans_created: int
    relationships_created: int
    skipped: int
    errors: List[ImportError]
    warnings: List[ImportWarning]
    entity_ids: List[str]
    orphan_ids: List[str]
    dry_run: bool
    source_tool: str
    import_timestamp: str

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/import/{project}/maltego` | POST | Import Maltego CSV export |
| `/import/{project}/spiderfoot` | POST | Import SpiderFoot JSON |
| `/import/{project}/theharvester` | POST | Import TheHarvester results |
| `/import/{project}/shodan` | POST | Import Shodan host export |
| `/import/{project}/hibp` | POST | Import HIBP breach data |
| `/import/{project}/csv` | POST | Import generic CSV |
| `/import/{project}/json` | POST | Import generic JSON |
| `/import/formats` | GET | List supported formats |
| `/import/{project}/validate` | POST | Validate import without importing |

### Type Detection

The connectors auto-detect identifier types from values:

| Pattern | Detected Type |
|---------|--------------|
| `user@domain.com` | EMAIL |
| `+1-555-123-4567` | PHONE |
| `192.168.1.1` | IP_ADDRESS |
| `example.com` | DOMAIN |
| `https://...` | URL |
| `@username` | USERNAME |
| `0x...` (40 hex) | CRYPTO_ADDRESS |
| `AA:BB:CC:DD:EE:FF` | MAC_ADDRESS |

### Usage Example

```python
from api.services.data_import import (
    DataImportService,
    MaltegoConnector,
    SpiderFootConnector,
    get_import_service,
)

# Get import service
import_service = get_import_service(neo4j_handler, orphan_service)

# Import Maltego CSV
maltego_csv = """Entity Type,Entity Value,Property Name,Property Value
Person,John Doe,email,john@example.com
EmailAddress,john@example.com,,"""

result = import_service.import_maltego(
    project_id="my-project",
    content=maltego_csv,
    dry_run=False,
)

print(f"Created {result.entities_created} entities, {result.orphans_created} orphans")
print(f"Success rate: {result.success_rate}%")
```

## Files Created

```
api/models/
├── visualization.py         # Pydantic models for visualization
└── data_import.py          # Pydantic models for data import

api/services/
├── graph_visualization.py   # Layout engine, metrics, exporters (1900+ lines)
└── data_import.py          # Import connectors for 7 tools (2000+ lines)

api/routers/
├── visualization.py        # Visualization API endpoints
└── import_data.py          # Data import API endpoints
```

## Testing

All Phase 16 components were verified:

```
✓ Normalizer service - All identifier types working
✓ Graph visualization service - All layout algorithms working
✓ Layout engine - Force-directed, hierarchical, circular, radial, grid
✓ Graph exporter - D3, Cytoscape, GraphML, DOT formats
✓ Data import connectors - Maltego, SpiderFoot, TheHarvester, Shodan, HIBP, CSV
✓ Type detection - Email, phone, IP, domain, URL, username, crypto, MAC
```

## Bug Fixes

### LayoutEngine Pydantic Compatibility

Fixed the `LayoutEngine.compute_layout()` method to handle both dict and Pydantic model inputs:

```python
# Added helper methods
def _to_dict(self, obj: Any) -> Dict[str, Any]:
    """Convert object to dict if it's a Pydantic model."""

def _get_id(self, node: Any) -> str:
    """Get node ID from either dict or Pydantic model."""

def _get_edge_endpoints(self, edge: Any) -> tuple:
    """Get source and target from either dict or Pydantic model."""
```

The method now:
1. Converts all inputs to dicts for internal processing
2. Computes positions using the selected algorithm
3. Updates original objects (Pydantic or dict) with new positions
4. Returns list of nodes with updated positions

## Performance Considerations

- **Layout iterations**: Default 100 for force-directed, configurable
- **Batch export**: Export entire graphs in single operation
- **Memory efficient**: Parse imports as generators, not lists
- **Dry run mode**: Validate without database writes

## Dependencies

No new dependencies required - uses existing:
- `pydantic` for data validation
- Standard library for CSV/JSON parsing
- `xml.etree.ElementTree` for GraphML export

## Next Steps (Phase 17+)

1. **Frontend Integration** - React/Vue components for graph visualization
2. **Timeline View** - Temporal graph visualization
3. **Real-time Updates** - WebSocket push for graph changes
4. **Custom Import Mappings** - User-defined field mappings
5. **Export Templates** - Customizable report templates with graphs
