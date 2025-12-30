"""
Pydantic models for Data Import operations.

Provides data structures for importing data from various OSINT tools
including Maltego, SpiderFoot, TheHarvester, Shodan, and HIBP.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ImportFormat(str, Enum):
    """Supported import formats/sources."""
    MALTEGO = "maltego"
    SPIDERFOOT = "spiderfoot"
    THEHARVESTER = "theharvester"
    SHODAN = "shodan"
    HIBP = "hibp"
    GENERIC_CSV = "csv"
    GENERIC_JSON = "json"


class ImportMode(str, Enum):
    """How to handle imported data."""
    ENTITIES = "entities"           # Create full entities
    ORPHANS = "orphans"             # Create orphan data only
    AUTO = "auto"                   # Auto-detect based on data quality


class DuplicateHandling(str, Enum):
    """How to handle duplicate records."""
    SKIP = "skip"                   # Skip duplicates
    UPDATE = "update"               # Update existing with new data
    CREATE_ORPHAN = "create_orphan" # Create orphan for review
    ERROR = "error"                 # Fail on duplicate


class ImportStatus(str, Enum):
    """Status of an import operation."""
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ColumnMapping(BaseModel):
    """Mapping of source column to target field."""
    source_column: str = Field(
        ...,
        description="Column name in source file"
    )
    target_field: str = Field(
        ...,
        description="Target field path (e.g., 'core.email', 'contact.phone')"
    )
    identifier_type: Optional[str] = Field(
        default=None,
        description="Identifier type for orphan data (email, phone, etc.)"
    )
    transform: Optional[str] = Field(
        default=None,
        description="Optional transformation (lowercase, uppercase, trim)"
    )


class CSVImportOptions(BaseModel):
    """Options for CSV import."""
    delimiter: str = Field(
        default=",",
        description="Field delimiter"
    )
    quote_char: str = Field(
        default='"',
        description="Quote character"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding"
    )
    has_header: bool = Field(
        default=True,
        description="Whether first row is header"
    )
    skip_rows: int = Field(
        default=0,
        ge=0,
        description="Number of rows to skip at start"
    )
    column_mappings: List[ColumnMapping] = Field(
        default_factory=list,
        description="Column to field mappings"
    )
    entity_type: str = Field(
        default="person",
        description="Entity type to create"
    )


class MaltegoImportOptions(BaseModel):
    """Options for Maltego import."""
    include_transforms: bool = Field(
        default=True,
        description="Include transform results"
    )
    entity_type_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Map Maltego entity types to Basset Hound types"
    )


class SpiderFootImportOptions(BaseModel):
    """Options for SpiderFoot import."""
    scan_id: Optional[str] = Field(
        default=None,
        description="Specific scan ID to import"
    )
    module_filter: Optional[List[str]] = Field(
        default=None,
        description="Only import from these modules"
    )
    data_type_filter: Optional[List[str]] = Field(
        default=None,
        description="Only import these data types"
    )


class ShodanImportOptions(BaseModel):
    """Options for Shodan import."""
    create_device_entities: bool = Field(
        default=True,
        description="Create device entities for hosts"
    )
    include_services: bool = Field(
        default=True,
        description="Include service/port information"
    )
    include_vulns: bool = Field(
        default=True,
        description="Include vulnerability data"
    )
    include_banners: bool = Field(
        default=False,
        description="Include raw service banners"
    )


class HIBPImportOptions(BaseModel):
    """Options for Have I Been Pwned import."""
    include_breach_details: bool = Field(
        default=True,
        description="Include breach metadata"
    )
    breach_filter: Optional[List[str]] = Field(
        default=None,
        description="Only import from specific breaches"
    )


class ImportOptions(BaseModel):
    """Combined import options."""
    format: ImportFormat = Field(
        ...,
        description="Import format"
    )
    mode: ImportMode = Field(
        default=ImportMode.AUTO,
        description="Import mode"
    )
    duplicate_handling: DuplicateHandling = Field(
        default=DuplicateHandling.SKIP,
        description="How to handle duplicates"
    )
    dry_run: bool = Field(
        default=False,
        description="Validate only, don't import"
    )
    normalize_data: bool = Field(
        default=True,
        description="Apply data normalization"
    )
    auto_link: bool = Field(
        default=False,
        description="Auto-link orphans to matching entities"
    )
    csv_options: Optional[CSVImportOptions] = Field(
        default=None,
        description="CSV-specific options"
    )
    maltego_options: Optional[MaltegoImportOptions] = Field(
        default=None,
        description="Maltego-specific options"
    )
    spiderfoot_options: Optional[SpiderFootImportOptions] = Field(
        default=None,
        description="SpiderFoot-specific options"
    )
    shodan_options: Optional[ShodanImportOptions] = Field(
        default=None,
        description="Shodan-specific options"
    )
    hibp_options: Optional[HIBPImportOptions] = Field(
        default=None,
        description="HIBP-specific options"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "csv",
                "mode": "auto",
                "duplicate_handling": "skip",
                "dry_run": False,
                "normalize_data": True,
                "csv_options": {
                    "delimiter": ",",
                    "has_header": True,
                    "column_mappings": [
                        {"source_column": "email", "target_field": "core.email"}
                    ]
                }
            }
        }
    )


class ImportWarning(BaseModel):
    """Warning generated during import."""
    row: Optional[int] = Field(
        default=None,
        description="Row number if applicable"
    )
    field: Optional[str] = Field(
        default=None,
        description="Field name if applicable"
    )
    message: str = Field(
        ...,
        description="Warning message"
    )
    value: Optional[str] = Field(
        default=None,
        description="Problematic value"
    )


class ImportError(BaseModel):
    """Error generated during import."""
    row: Optional[int] = Field(
        default=None,
        description="Row number if applicable"
    )
    field: Optional[str] = Field(
        default=None,
        description="Field name if applicable"
    )
    message: str = Field(
        ...,
        description="Error message"
    )
    value: Optional[str] = Field(
        default=None,
        description="Problematic value"
    )
    fatal: bool = Field(
        default=False,
        description="Whether error caused import to stop"
    )


class ImportedRecord(BaseModel):
    """Details of an imported record."""
    source_row: Optional[int] = Field(
        default=None,
        description="Source row number"
    )
    record_type: str = Field(
        ...,
        description="Type of record (entity, orphan, relationship)"
    )
    record_id: str = Field(
        ...,
        description="ID of created record"
    )
    action: str = Field(
        ...,
        description="Action taken (created, updated, skipped)"
    )
    source_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original source data"
    )


class ImportResult(BaseModel):
    """Result of an import operation."""
    success: bool = Field(
        ...,
        description="Whether import was successful"
    )
    status: ImportStatus = Field(
        ...,
        description="Import status"
    )
    format: ImportFormat = Field(
        ...,
        description="Import format used"
    )
    dry_run: bool = Field(
        default=False,
        description="Whether this was a dry run"
    )
    total_records: int = Field(
        default=0,
        ge=0,
        description="Total records in source"
    )
    entities_created: int = Field(
        default=0,
        ge=0,
        description="Number of entities created"
    )
    entities_updated: int = Field(
        default=0,
        ge=0,
        description="Number of entities updated"
    )
    orphans_created: int = Field(
        default=0,
        ge=0,
        description="Number of orphan records created"
    )
    relationships_created: int = Field(
        default=0,
        ge=0,
        description="Number of relationships created"
    )
    skipped: int = Field(
        default=0,
        ge=0,
        description="Number of records skipped"
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Number of records that failed"
    )
    warnings: List[ImportWarning] = Field(
        default_factory=list,
        description="Warnings generated"
    )
    errors: List[ImportError] = Field(
        default_factory=list,
        description="Errors generated"
    )
    records: List[ImportedRecord] = Field(
        default_factory=list,
        description="Details of imported records"
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Import duration in seconds"
    )
    message: str = Field(
        default="",
        description="Summary message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "status": "completed",
                "format": "csv",
                "dry_run": False,
                "total_records": 100,
                "entities_created": 85,
                "entities_updated": 5,
                "orphans_created": 10,
                "skipped": 0,
                "failed": 0,
                "warnings": [],
                "errors": [],
                "duration_seconds": 2.5,
                "message": "Successfully imported 100 records"
            }
        }
    )


class ImportFormatInfo(BaseModel):
    """Information about a supported import format."""
    format: ImportFormat = Field(
        ...,
        description="Format identifier"
    )
    name: str = Field(
        ...,
        description="Human-readable name"
    )
    description: str = Field(
        ...,
        description="Format description"
    )
    file_extensions: List[str] = Field(
        default_factory=list,
        description="Supported file extensions"
    )
    mime_types: List[str] = Field(
        default_factory=list,
        description="Supported MIME types"
    )
    example_url: Optional[str] = Field(
        default=None,
        description="URL to example/documentation"
    )
    supports_relationships: bool = Field(
        default=False,
        description="Whether format includes relationship data"
    )


class ImportFormatsResponse(BaseModel):
    """Response listing supported import formats."""
    formats: List[ImportFormatInfo] = Field(
        default_factory=list,
        description="List of supported formats"
    )
    count: int = Field(
        default=0,
        ge=0,
        description="Number of formats"
    )


# Default format information
IMPORT_FORMAT_INFO = {
    ImportFormat.MALTEGO: ImportFormatInfo(
        format=ImportFormat.MALTEGO,
        name="Maltego",
        description="Maltego entity export files",
        file_extensions=[".csv", ".xlsx", ".mtgx"],
        mime_types=["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        example_url="https://docs.maltego.com/support/solutions/articles/15000014095",
        supports_relationships=True
    ),
    ImportFormat.SPIDERFOOT: ImportFormatInfo(
        format=ImportFormat.SPIDERFOOT,
        name="SpiderFoot",
        description="SpiderFoot scan results (JSON export)",
        file_extensions=[".json"],
        mime_types=["application/json"],
        example_url="https://github.com/smicallef/spiderfoot",
        supports_relationships=False
    ),
    ImportFormat.THEHARVESTER: ImportFormatInfo(
        format=ImportFormat.THEHARVESTER,
        name="TheHarvester",
        description="TheHarvester output (JSON/XML)",
        file_extensions=[".json", ".xml"],
        mime_types=["application/json", "application/xml"],
        example_url="https://github.com/laramies/theHarvester",
        supports_relationships=False
    ),
    ImportFormat.SHODAN: ImportFormatInfo(
        format=ImportFormat.SHODAN,
        name="Shodan",
        description="Shodan host export (JSON)",
        file_extensions=[".json"],
        mime_types=["application/json"],
        example_url="https://shodan.io",
        supports_relationships=False
    ),
    ImportFormat.HIBP: ImportFormatInfo(
        format=ImportFormat.HIBP,
        name="Have I Been Pwned",
        description="HIBP breach data export",
        file_extensions=[".json"],
        mime_types=["application/json"],
        example_url="https://haveibeenpwned.com",
        supports_relationships=False
    ),
    ImportFormat.GENERIC_CSV: ImportFormatInfo(
        format=ImportFormat.GENERIC_CSV,
        name="Generic CSV",
        description="Custom CSV with configurable column mapping",
        file_extensions=[".csv", ".tsv"],
        mime_types=["text/csv", "text/tab-separated-values"],
        supports_relationships=False
    ),
    ImportFormat.GENERIC_JSON: ImportFormatInfo(
        format=ImportFormat.GENERIC_JSON,
        name="Generic JSON",
        description="Custom JSON with entity/orphan structure",
        file_extensions=[".json", ".jsonl"],
        mime_types=["application/json", "application/jsonlines"],
        supports_relationships=True
    ),
}


def get_format_info(format: ImportFormat) -> ImportFormatInfo:
    """Get information about an import format."""
    return IMPORT_FORMAT_INFO.get(format, ImportFormatInfo(
        format=format,
        name=format.value,
        description=f"Import format: {format.value}",
        file_extensions=[],
        mime_types=[]
    ))


def get_all_format_info() -> ImportFormatsResponse:
    """Get information about all supported import formats."""
    formats = list(IMPORT_FORMAT_INFO.values())
    return ImportFormatsResponse(formats=formats, count=len(formats))
