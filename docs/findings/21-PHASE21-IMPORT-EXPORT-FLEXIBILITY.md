# Phase 21: Import/Export Flexibility

## Summary

Phase 21 enhances Basset Hound's data portability with custom import field mappings, LLM-optimized exports, and multi-format graph conversion capabilities.

## Components Implemented

### 1. Import Mapping Service

**File**: `api/services/import_mapping.py`

A flexible field mapping system for customizing data imports.

#### Features

- **18 Transformation Types**: Direct, uppercase, lowercase, trim, replace, regex, split, join, concat, default, date format, extract, hash, template, JSON path, lookup, custom function, conditional
- **Reusable Mapping Configurations**: Save and reuse mappings across imports
- **Validation & Preview**: Validate mappings before apply, preview transformations
- **CRUD Operations**: Create, read, update, delete mapping configs

#### Transformation Types

| Type | Description | Example |
|------|-------------|---------|
| DIRECT | Copy value as-is | `value` → `value` |
| UPPERCASE | Convert to uppercase | `john` → `JOHN` |
| LOWERCASE | Convert to lowercase | `JOHN` → `john` |
| TRIM | Remove whitespace | `  john  ` → `john` |
| REPLACE | String replacement | `john_doe` → `john-doe` |
| REGEX_EXTRACT | Extract via regex | `user@example.com` → `example.com` |
| SPLIT | Split into array | `a,b,c` → `["a","b","c"]` |
| JOIN | Join array | `["a","b"]` → `a, b` |
| CONCAT | Concatenate fields | `{first} {last}` |
| DEFAULT | Default if empty | `null` → `Unknown` |
| DATE_FORMAT | Reformat dates | `2024-01-15` → `Jan 15, 2024` |
| EXTRACT | Extract substring | positions 0-5 |
| HASH | Hash value | `value` → `sha256:...` |
| TEMPLATE | String template | `Hello {name}!` |
| JSON_PATH | Extract from JSON | `$.user.name` |
| LOOKUP | Map via lookup table | `US` → `United States` |
| CUSTOM | Custom function | User-defined |
| CONDITIONAL | If/then/else logic | `if value > 10...` |

#### Usage Example

```python
from api.services.import_mapping import (
    ImportMappingService,
    ImportMappingConfig,
    FieldMapping,
    TransformationType,
    get_import_mapping_service,
)

service = get_import_mapping_service()

# Create a mapping configuration
config = ImportMappingConfig(
    name="CSV Person Import",
    description="Maps CSV columns to Person entity fields",
    source_format="csv",
    target_entity_type="person",
    field_mappings=[
        FieldMapping(
            source_field="full_name",
            target_field="name",
            transformation=TransformationType.TRIM,
        ),
        FieldMapping(
            source_field="email_address",
            target_field="email",
            transformation=TransformationType.LOWERCASE,
        ),
    ],
)

# Save the mapping
mapping_id = await service.create_mapping(config)

# Apply to data
data = [{"full_name": "  John Doe  ", "email_address": "JOHN@EXAMPLE.COM"}]
result = await service.apply_mapping(mapping_id, data)
# Result: [{"name": "John Doe", "email": "john@example.com"}]

# Validate mapping
validation = await service.validate_mapping(config, sample_data)
print(f"Valid: {validation.valid}, Errors: {validation.errors}")

# Preview transformation
preview = await service.preview_mapping(config, sample_data, limit=5)
```

### 2. LLM Export Service

**File**: `api/services/llm_export.py`

Generates context-optimized output for consumption by LLMs and AI agents.

#### Features

- **Multiple Formats**: Markdown, JSON, YAML, Plain Text, XML
- **Token Estimation**: GPT-family approximation for context limits
- **Intelligent Truncation**: Prioritize important fields within token limits
- **Configurable Context**: Include/exclude entities, relationships, timeline, stats
- **Export Types**: Single entity, project summary, entity context, investigation brief

#### Export Formats

| Format | Best For | Overhead |
|--------|----------|----------|
| MARKDOWN | Human-readable reports | 1.1x |
| JSON | Structured data processing | 1.2x |
| YAML | Configuration-like output | 1.05x |
| PLAIN_TEXT | Minimal formatting | 1.0x |
| XML | Legacy system integration | 1.3x |

#### Configuration Options

```python
from api.services.llm_export import (
    LLMExportService,
    LLMExportConfig,
    LLMExportFormat,
    ExportContext,
    get_llm_export_service,
)

config = LLMExportConfig(
    format=LLMExportFormat.MARKDOWN,
    max_tokens=4000,  # None = unlimited
    context=ExportContext(
        include_entities=True,
        include_relationships=True,
        include_timeline=False,
        include_orphan_data=False,
        include_statistics=True,
        include_metadata=True,
    ),
    prioritize_fields=["core", "profile", "contact", "social"],
    max_field_length=500,
    max_relationships=50,
    max_timeline_events=20,
)

service = get_llm_export_service()

# Export single entity
result = await service.export_entity(entity_id, project_id, config)
print(f"Tokens: {result.token_estimate}, Truncated: {result.truncated}")

# Export project summary
summary = await service.export_project_summary(project_id, config)

# Export entity with context (neighbors, relationships)
context = await service.export_entity_context(entity_id, project_id, depth=2)

# Export investigation brief
brief = await service.export_investigation_brief(project_id, focus_entities)
```

#### Token Estimation

```python
from api.services.llm_export import TokenEstimator, LLMExportFormat

# Estimate tokens for content
tokens = TokenEstimator.estimate(content, LLMExportFormat.MARKDOWN)
```

### 3. Graph Format Converter

**File**: `api/services/graph_format_converter.py`

Converts between different graph formats for import/export interoperability.

#### Supported Formats

| Format | Extension | Read | Write | Description |
|--------|-----------|------|-------|-------------|
| GraphML | .graphml | ✓ | ✓ | XML-based, widely supported |
| GEXF | .gexf | ✓ | ✓ | Gephi format |
| JSON Graph | .json | ✓ | ✓ | JSON-based graph structure |
| Cytoscape | .json | ✓ | ✓ | Cytoscape.js format |
| D3 | .json | ✓ | ✓ | D3.js force layout format |
| DOT | .dot | ✓ | ✓ | Graphviz format |
| Pajek | .net | ✓ | ✓ | Pajek network format |
| Adjacency List | .txt | ✓ | ✓ | Simple text format |

#### Features

- **Format Auto-Detection**: Detect format from content
- **Validation**: Validate format before conversion
- **Property Preservation**: Maintain node/edge properties
- **Direction Handling**: Directed, undirected, or preserve
- **Metadata Support**: Include/exclude graph metadata
- **Warnings**: Track conversion issues non-fatally

#### Usage Example

```python
from api.services.graph_format_converter import (
    GraphFormatConverter,
    GraphFormat,
    ConversionOptions,
    EdgeDirection,
    get_graph_format_converter,
)

converter = get_graph_format_converter()

# Auto-detect format
detection = converter.detect_format(data)
print(f"Format: {detection.detected_format}, Confidence: {detection.confidence}")

# Validate format
validation = converter.validate_format(data, GraphFormat.GRAPHML)
print(f"Valid: {validation.valid}, Errors: {validation.errors}")

# Convert between formats
options = ConversionOptions(
    include_properties=True,
    edge_direction=EdgeDirection.PRESERVE,
    include_metadata=True,
    pretty_print=True,
)

result = converter.convert(
    data=graphml_content,
    source_format=GraphFormat.GRAPHML,
    target_format=GraphFormat.D3,
    options=options,
)

if result.success:
    print(f"Converted {result.node_count} nodes, {result.edge_count} edges")
    print(result.data)
else:
    print(f"Error: {result.error}")
```

#### Internal Graph Representation

```python
from api.services.graph_format_converter import (
    InternalGraph,
    InternalNode,
    InternalEdge,
)

# Build graph programmatically
graph = InternalGraph(
    nodes=[
        InternalNode(id="1", label="Person", properties={"name": "Alice"}),
        InternalNode(id="2", label="Person", properties={"name": "Bob"}),
    ],
    edges=[
        InternalEdge(source="1", target="2", label="KNOWS", directed=True),
    ],
    metadata={"name": "Social Network"},
    directed=True,
)

# Convert to any format
result = converter.convert_from_internal(graph, GraphFormat.D3)
```

## API Exports

All Phase 21 exports are available from `api.services`:

```python
from api.services import (
    # Import Mapping Service
    ImportMappingService,
    ImportMappingConfig,
    FieldMapping,
    TransformationType,
    TransformationOptions,
    TransformationEngine,
    MappingValidationResult,
    MappingPreviewResult,
    get_import_mapping_service,
    reset_import_mapping_service,

    # LLM Export Service
    LLMExportService,
    LLMExportFormat,
    ExportContext,
    LLMExportConfig,
    LLMExportResult,
    get_llm_export_service,
    set_llm_export_service,
    reset_llm_export_service,

    # Graph Format Converter
    GraphFormatConverter,
    GraphFormat,
    EdgeDirection,
    ConversionOptions,
    ConversionResult,
    ConversionWarning,
    FormatValidationResult,
    FormatDetectionResult,
    InternalNode,
    InternalEdge,
    InternalGraph,
    get_graph_format_converter,
    set_graph_format_converter,
    reset_graph_format_converter,
)
```

## Test Coverage

**File**: `tests/test_phase21_import_export.py`

39 comprehensive tests covering:

- Transformation type enumeration
- Field mapping creation and options
- Import mapping config validation
- Transformation engine (7 transformation types)
- Import mapping service CRUD operations
- Mapping application and validation
- LLM export format enumeration
- Export context and config models
- LLM export result creation
- Token estimation
- Graph format enumeration
- Conversion options and results
- Internal graph representation
- Format detection and conversion
- Service exports verification

```
tests/test_phase21_import_export.py ... 39 passed in 0.63s
```

## Integration Points

### With Phase 16 (Data Import)

```python
from api.services import get_import_service, get_import_mapping_service

# Use custom mapping with existing connectors
import_service = get_import_service()
mapping_service = get_import_mapping_service()

# Create mapping for Maltego connector
mapping = await mapping_service.create_mapping(maltego_config)

# Apply mapping during import
raw_data = await import_service.import_from_maltego(file_path)
mapped_data = await mapping_service.apply_mapping(mapping, raw_data)
```

### With Phase 18 (Graph Analytics)

```python
from api.services import get_community_detection_service, get_graph_format_converter

# Export community detection results to Gephi
communities = await get_community_detection_service().detect_communities(project_id)
converter = get_graph_format_converter()
gexf_data = converter.convert(community_graph, GraphFormat.JSON_GRAPH, GraphFormat.GEXF)
```

### With Phase 20 (Query Cache)

```python
from api.services import cached_query, QueryType, get_llm_export_service

# Cache LLM exports
@cached_query(QueryType.ENTITY_DETAILS, project_id_param="project_id")
async def get_cached_entity_export(entity_id: str, project_id: str):
    service = get_llm_export_service()
    return await service.export_entity(entity_id, project_id)
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `api/services/import_mapping.py` | Created | Import mapping service (~500 lines) |
| `api/services/llm_export.py` | Created | LLM export service (~580 lines) |
| `api/services/graph_format_converter.py` | Created | Graph format converter (~660 lines) |
| `api/services/__init__.py` | Modified | Added Phase 21 exports |
| `tests/test_phase21_import_export.py` | Created | 39 tests |

## Metrics

| Metric | Value |
|--------|-------|
| New tests | 39 |
| All Phase 21 tests passing | Yes |
| Transformation types | 18 |
| Export formats | 5 |
| Graph formats | 8 |
| Total lines of code | ~1,740 |

## Future Enhancements

1. **Streaming Exports**: Stream large exports to avoid memory issues
2. **Batch Format Conversion**: Convert multiple files in batch
3. **Custom Format Plugins**: Plugin system for custom formats
4. **Export Templates**: Pre-built templates for common LLM use cases
5. **Format Validation Rules**: Configurable validation rules per format
6. **Compression Support**: gzip/zip for large exports

## Conclusion

Phase 21 significantly enhances Basset Hound's data portability:

- **Import Mapping Service** enables flexible data transformation with 18 transformation types
- **LLM Export Service** optimizes exports for AI/LLM consumption with token estimation
- **Graph Format Converter** supports 8 graph formats for interoperability with tools like Gephi, Cytoscape, and D3.js

These capabilities enable seamless data exchange with external tools and AI systems, making Basset Hound more versatile for OSINT workflows.
