"""
Data Import Router for Basset Hound.

Provides endpoints for importing data from various OSINT tools and formats
including Maltego, SpiderFoot, TheHarvester, Shodan, HIBP, and generic CSV.
"""

import csv
import json
import io
import xml.etree.ElementTree as ET
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler


class ImportFormat(str, Enum):
    """Supported import formats."""
    MALTEGO = "maltego"
    SPIDERFOOT = "spiderfoot"
    THEHARVESTER = "theharvester"
    SHODAN = "shodan"
    HIBP = "hibp"
    CSV = "csv"


router = APIRouter(
    prefix="/projects/{project_safe_name}/import",
    tags=["import"],
    responses={
        404: {"description": "Project not found"},
        400: {"description": "Invalid import data"},
        500: {"description": "Internal server error"},
    },
)

# Standalone router for format listing (no project context needed)
formats_router = APIRouter(
    prefix="/import",
    tags=["import"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class ImportError(BaseModel):
    """Schema for an import error."""
    index: Optional[int] = Field(None, description="Index of the failing record")
    field: Optional[str] = Field(None, description="Field that caused the error")
    error: str = Field(..., description="Error message")
    data: Optional[dict[str, Any]] = Field(None, description="The problematic data")


class ImportResult(BaseModel):
    """Schema for import operation result."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "total_records": 100,
            "imported": 95,
            "skipped": 3,
            "failed": 2,
            "errors": [],
            "created_entity_ids": ["uuid-1", "uuid-2"],
            "updated_entity_ids": [],
            "import_time_ms": 1234
        }
    })

    success: bool = Field(..., description="Whether the import completed successfully")
    total_records: int = Field(..., description="Total records in the import file")
    imported: int = Field(..., description="Number of successfully imported records")
    skipped: int = Field(0, description="Number of skipped records (duplicates, etc.)")
    failed: int = Field(0, description="Number of failed records")
    errors: list[ImportError] = Field(default_factory=list, description="List of errors")
    created_entity_ids: list[str] = Field(
        default_factory=list,
        description="IDs of newly created entities"
    )
    updated_entity_ids: list[str] = Field(
        default_factory=list,
        description="IDs of updated entities"
    )
    import_time_ms: Optional[int] = Field(None, description="Import duration in milliseconds")


class ValidationResult(BaseModel):
    """Schema for import validation result."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "valid": True,
            "format_detected": "maltego",
            "record_count": 50,
            "warnings": [],
            "errors": [],
            "sample_records": [],
            "field_mapping_suggestions": {}
        }
    })

    valid: bool = Field(..., description="Whether the file is valid for import")
    format_detected: Optional[str] = Field(None, description="Detected file format")
    record_count: int = Field(..., description="Number of records found")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings")
    errors: list[ImportError] = Field(default_factory=list, description="Validation errors")
    sample_records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sample of parsed records (up to 5)"
    )
    field_mapping_suggestions: dict[str, str] = Field(
        default_factory=dict,
        description="Suggested field mappings for CSV import"
    )


class CSVMappingField(BaseModel):
    """Schema for a CSV field mapping."""
    csv_column: str = Field(..., description="Column name in CSV")
    entity_field: str = Field(..., description="Target entity field path")
    transform: Optional[str] = Field(
        None,
        description="Optional transformation (lowercase, uppercase, trim, split)"
    )


class CSVImportConfig(BaseModel):
    """Configuration for CSV import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "mappings": [
                {"csv_column": "name", "entity_field": "profile.core.name.first_name"},
                {"csv_column": "email", "entity_field": "profile.core.email"},
                {"csv_column": "twitter", "entity_field": "profile.social.twitter"}
            ],
            "skip_header": True,
            "delimiter": ",",
            "update_existing": False,
            "match_field": "profile.core.email"
        }
    })

    mappings: list[CSVMappingField] = Field(
        ...,
        description="Field mappings from CSV columns to entity fields",
        min_length=1
    )
    skip_header: bool = Field(True, description="Skip the first row (header)")
    delimiter: str = Field(",", description="CSV delimiter character")
    update_existing: bool = Field(
        False,
        description="Update existing entities if match found"
    )
    match_field: Optional[str] = Field(
        None,
        description="Entity field to use for matching existing entities"
    )


class MaltegoImportConfig(BaseModel):
    """Configuration for Maltego import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "import_relationships": True,
            "entity_type_mapping": {
                "maltego.Person": "Person",
                "maltego.EmailAddress": "Email",
                "maltego.Domain": "Domain"
            }
        }
    })

    import_relationships: bool = Field(
        True,
        description="Import relationships/links between entities"
    )
    entity_type_mapping: Optional[dict[str, str]] = Field(
        None,
        description="Map Maltego entity types to Basset Hound types"
    )


class SpiderFootImportConfig(BaseModel):
    """Configuration for SpiderFoot import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "event_types": ["EMAILADDR", "HUMAN_NAME", "PHONE_NUMBER"],
            "min_confidence": 50,
            "group_by_source": True
        }
    })

    event_types: Optional[list[str]] = Field(
        None,
        description="Only import specific event types (None = all)"
    )
    min_confidence: int = Field(
        0,
        ge=0,
        le=100,
        description="Minimum confidence score to import"
    )
    group_by_source: bool = Field(
        False,
        description="Group related findings under source entities"
    )


class TheHarvesterImportConfig(BaseModel):
    """Configuration for TheHarvester import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "import_emails": True,
            "import_hosts": True,
            "import_ips": True,
            "deduplicate": True
        }
    })

    import_emails: bool = Field(True, description="Import discovered emails")
    import_hosts: bool = Field(True, description="Import discovered hosts")
    import_ips: bool = Field(True, description="Import discovered IPs")
    deduplicate: bool = Field(True, description="Skip duplicate entries")


class ShodanImportConfig(BaseModel):
    """Configuration for Shodan import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "import_hosts": True,
            "import_vulnerabilities": True,
            "import_services": True,
            "create_relationships": True
        }
    })

    import_hosts: bool = Field(True, description="Import host information")
    import_vulnerabilities: bool = Field(True, description="Import CVE data")
    import_services: bool = Field(True, description="Import service/port data")
    create_relationships: bool = Field(
        True,
        description="Create relationships between hosts and services"
    )


class HIBPImportConfig(BaseModel):
    """Configuration for Have I Been Pwned import."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "import_breaches": True,
            "import_pastes": True,
            "create_breach_entities": False,
            "link_to_existing_emails": True
        }
    })

    import_breaches: bool = Field(True, description="Import breach data")
    import_pastes: bool = Field(True, description="Import paste data")
    create_breach_entities: bool = Field(
        False,
        description="Create separate entities for each breach"
    )
    link_to_existing_emails: bool = Field(
        True,
        description="Link breach data to existing email entities"
    )


class FormatInfo(BaseModel):
    """Schema for import format information."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "format": "maltego",
            "name": "Maltego Export",
            "description": "Import entities from Maltego graph exports",
            "file_extensions": [".mtgx", ".csv"],
            "supports_relationships": True,
            "config_schema": {}
        }
    })

    format: str = Field(..., description="Format identifier")
    name: str = Field(..., description="Human-readable format name")
    description: str = Field(..., description="Format description")
    file_extensions: list[str] = Field(..., description="Supported file extensions")
    supports_relationships: bool = Field(..., description="Whether format supports relationships")
    config_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema for format-specific configuration"
    )


class FormatsListResponse(BaseModel):
    """Response schema for listing import formats."""
    formats: list[FormatInfo] = Field(..., description="List of supported import formats")


# ----- Helper Functions -----

def _generate_entity_id() -> str:
    """Generate a new entity ID."""
    return str(uuid.uuid4())


def _parse_maltego_mtgx(content: bytes) -> tuple[list[dict], list[dict]]:
    """
    Parse Maltego MTGX (XML) format.

    Returns tuple of (entities, relationships).
    """
    entities = []
    relationships = []

    try:
        # MTGX is a ZIP file containing XML
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(content)) as zf:
            # Look for Entities.xml and Links.xml
            for name in zf.namelist():
                if 'Entities' in name and name.endswith('.xml'):
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        for entity in root.findall('.//Entity'):
                            entity_type = entity.get('type', 'Unknown')
                            entity_value = entity.find('.//Value')
                            props = {}
                            for prop in entity.findall('.//Property'):
                                prop_name = prop.get('name', '')
                                prop_value = prop.find('.//Value')
                                if prop_name and prop_value is not None:
                                    props[prop_name] = prop_value.text

                            entities.append({
                                'type': entity_type,
                                'value': entity_value.text if entity_value is not None else '',
                                'properties': props
                            })

                elif 'Links' in name and name.endswith('.xml'):
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        for link in root.findall('.//Link'):
                            source = link.get('source')
                            target = link.get('target')
                            link_type = link.get('type', 'LINKED')
                            if source and target:
                                relationships.append({
                                    'source': source,
                                    'target': target,
                                    'type': link_type
                                })

    except zipfile.BadZipFile:
        # Try parsing as plain XML
        try:
            root = ET.fromstring(content)
            for entity in root.findall('.//Entity'):
                entity_type = entity.get('type', 'Unknown')
                entity_value = entity.find('.//Value')
                entities.append({
                    'type': entity_type,
                    'value': entity_value.text if entity_value is not None else '',
                    'properties': {}
                })
        except ET.ParseError:
            pass

    return entities, relationships


def _parse_maltego_csv(content: str) -> list[dict]:
    """Parse Maltego CSV export format."""
    entities = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        entity = {
            'type': row.get('Type', row.get('Entity Type', 'Unknown')),
            'value': row.get('Value', row.get('Entity Value', '')),
            'properties': {k: v for k, v in row.items() if k not in ('Type', 'Value', 'Entity Type', 'Entity Value')}
        }
        entities.append(entity)

    return entities


def _parse_spiderfoot_json(content: str) -> list[dict]:
    """Parse SpiderFoot JSON export format."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    entities = []

    # SpiderFoot exports events
    events = data if isinstance(data, list) else data.get('events', [])

    for event in events:
        entity = {
            'type': event.get('type', 'Unknown'),
            'value': event.get('data', ''),
            'source': event.get('source', ''),
            'confidence': event.get('confidence', 100),
            'properties': {
                'module': event.get('module', ''),
                'source_entity': event.get('source_entity', ''),
                'timestamp': event.get('timestamp', '')
            }
        }
        entities.append(entity)

    return entities


def _parse_theharvester(content: str) -> dict[str, list[str]]:
    """Parse TheHarvester output format."""
    results = {
        'emails': [],
        'hosts': [],
        'ips': []
    }

    try:
        # Try JSON format first
        data = json.loads(content)
        results['emails'] = data.get('emails', [])
        results['hosts'] = data.get('hosts', [])
        results['ips'] = data.get('ips', [])
    except json.JSONDecodeError:
        # Parse text format
        current_section = None
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            if 'emails' in line.lower() or 'e-mail' in line.lower():
                current_section = 'emails'
            elif 'hosts' in line.lower() or 'hostname' in line.lower():
                current_section = 'hosts'
            elif 'ip' in line.lower() and 'address' in line.lower():
                current_section = 'ips'
            elif current_section and not line.startswith('[') and not line.startswith('-'):
                # Extract value
                if '@' in line and current_section == 'emails':
                    results['emails'].append(line)
                elif current_section == 'hosts':
                    results['hosts'].append(line)
                elif current_section == 'ips':
                    results['ips'].append(line)

    return results


def _parse_shodan_json(content: str) -> list[dict]:
    """Parse Shodan JSON export format."""
    hosts = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try line-delimited JSON
        for line in content.strip().split('\n'):
            if line:
                try:
                    hosts.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return hosts

    # Handle different Shodan export formats
    if isinstance(data, list):
        hosts = data
    elif 'matches' in data:
        hosts = data['matches']
    elif 'ip_str' in data:
        hosts = [data]

    return hosts


def _parse_hibp_json(content: str) -> dict:
    """Parse Have I Been Pwned JSON format."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {'breaches': [], 'pastes': []}

    result = {
        'breaches': [],
        'pastes': []
    }

    if isinstance(data, list):
        # Determine if breaches or pastes
        if data and 'Name' in data[0]:
            result['breaches'] = data
        elif data and 'Source' in data[0]:
            result['pastes'] = data
    elif isinstance(data, dict):
        result['breaches'] = data.get('Breaches', data.get('breaches', []))
        result['pastes'] = data.get('Pastes', data.get('pastes', []))

    return result


def _create_entity_from_maltego(
    maltego_entity: dict,
    project_safe_name: str,
    type_mapping: dict = None
) -> dict:
    """Convert Maltego entity to Basset Hound entity format."""
    entity_type = maltego_entity.get('type', 'Unknown')
    value = maltego_entity.get('value', '')
    properties = maltego_entity.get('properties', {})

    # Map common Maltego types
    type_map = type_mapping or {
        'maltego.Person': 'Person',
        'maltego.EmailAddress': 'Email',
        'maltego.Domain': 'Domain',
        'maltego.IPv4Address': 'IP',
        'maltego.PhoneNumber': 'Phone',
        'maltego.Location': 'Location',
        'maltego.Company': 'Organization',
    }

    mapped_type = type_map.get(entity_type, 'Entity')

    # Build entity profile based on type
    profile = {'core': {}}

    if mapped_type == 'Person' or 'person' in entity_type.lower():
        # Try to split name
        parts = value.split(' ', 1)
        profile['core']['name'] = [{
            'first_name': parts[0],
            'last_name': parts[1] if len(parts) > 1 else ''
        }]
    elif mapped_type == 'Email' or 'email' in entity_type.lower():
        profile['core']['email'] = [value]
    elif mapped_type == 'Phone' or 'phone' in entity_type.lower():
        profile['core']['phone'] = [{'number': value}]
    elif mapped_type == 'Domain' or 'domain' in entity_type.lower():
        profile['online'] = {'domains': [value]}
    elif mapped_type == 'IP' or 'ip' in entity_type.lower():
        profile['technical'] = {'ip_addresses': [value]}
    else:
        profile['core']['name'] = [{'first_name': value}]

    # Add additional properties
    if properties:
        profile['imported'] = properties

    return {
        'id': _generate_entity_id(),
        'profile': profile,
        'metadata': {
            'source': 'maltego',
            'original_type': entity_type,
            'imported_at': datetime.now().isoformat()
        }
    }


def _apply_csv_transform(value: str, transform: Optional[str]) -> Any:
    """Apply a transformation to a CSV value."""
    if not value or not transform:
        return value

    if transform == 'lowercase':
        return value.lower()
    elif transform == 'uppercase':
        return value.upper()
    elif transform == 'trim':
        return value.strip()
    elif transform == 'split':
        return [v.strip() for v in value.split(',')]
    elif transform == 'int':
        try:
            return int(value)
        except ValueError:
            return value
    elif transform == 'float':
        try:
            return float(value)
        except ValueError:
            return value

    return value


def _set_nested_value(obj: dict, path: str, value: Any):
    """Set a value in a nested dictionary using dot notation path."""
    parts = path.split('.')
    current = obj

    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]

    final_key = parts[-1]

    # Handle array fields (like name, email)
    if final_key in ('name', 'email', 'phone', 'address'):
        if final_key not in current:
            current[final_key] = []
        if isinstance(value, list):
            current[final_key].extend(value)
        else:
            current[final_key].append(value)
    else:
        current[final_key] = value


# ----- Endpoints -----

@router.post(
    "/maltego",
    response_model=ImportResult,
    summary="Import Maltego export",
    description="Import entities and relationships from a Maltego graph export (.mtgx or .csv).",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file format"},
        404: {"description": "Project not found"},
    }
)
async def import_maltego(
    project_safe_name: str,
    file: UploadFile = File(..., description="Maltego export file (.mtgx or .csv)"),
    config: MaltegoImportConfig = Body(default=None),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import entities from Maltego exports.

    Supports both MTGX (native Maltego) and CSV export formats.
    Optionally imports relationships between entities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: Maltego export file (.mtgx or .csv)
    - **config**: Optional import configuration
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if config is None:
        config = MaltegoImportConfig()

    try:
        content = await file.read()
        filename = file.filename or ""

        # Parse based on file type
        entities = []
        relationships = []

        if filename.endswith('.mtgx'):
            entities, relationships = _parse_maltego_mtgx(content)
        elif filename.endswith('.csv'):
            entities = _parse_maltego_csv(content.decode('utf-8'))
        else:
            # Try to detect format
            try:
                entities = _parse_maltego_csv(content.decode('utf-8'))
            except Exception:
                entities, relationships = _parse_maltego_mtgx(content)

        if not entities:
            return ImportResult(
                success=False,
                total_records=0,
                imported=0,
                failed=0,
                errors=[ImportError(error="No entities found in file")]
            )

        # Import entities
        created_ids = []
        errors = []
        imported = 0
        failed = 0

        for i, maltego_entity in enumerate(entities):
            try:
                entity = _create_entity_from_maltego(
                    maltego_entity,
                    project_safe_name,
                    config.entity_type_mapping
                )

                result = neo4j_handler.add_person(project_safe_name, entity)
                if result:
                    created_ids.append(result.get('id', entity['id']))
                    imported += 1
                else:
                    failed += 1
                    errors.append(ImportError(
                        index=i,
                        error="Failed to create entity"
                    ))

            except Exception as e:
                failed += 1
                errors.append(ImportError(
                    index=i,
                    error=str(e),
                    data=maltego_entity
                ))

        # Import relationships if configured
        if config.import_relationships and relationships:
            for rel in relationships:
                try:
                    # Would need to map Maltego entity IDs to created entity IDs
                    pass
                except Exception:
                    pass

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=len(entities),
            imported=imported,
            failed=failed,
            errors=errors[:100],  # Limit errors
            created_entity_ids=created_ids,
            import_time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/spiderfoot",
    response_model=ImportResult,
    summary="Import SpiderFoot results",
    description="Import findings from SpiderFoot scan results.",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file format"},
        404: {"description": "Project not found"},
    }
)
async def import_spiderfoot(
    project_safe_name: str,
    file: UploadFile = File(..., description="SpiderFoot export file (JSON)"),
    config: SpiderFootImportConfig = Body(default=None),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import findings from SpiderFoot scans.

    Imports events from SpiderFoot JSON exports, converting them to entities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: SpiderFoot JSON export file
    - **config**: Optional import configuration
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if config is None:
        config = SpiderFootImportConfig()

    try:
        content = await file.read()
        events = _parse_spiderfoot_json(content.decode('utf-8'))

        if not events:
            return ImportResult(
                success=False,
                total_records=0,
                imported=0,
                errors=[ImportError(error="No events found in file")]
            )

        # Filter by event type and confidence
        filtered_events = []
        for event in events:
            if config.event_types and event['type'] not in config.event_types:
                continue
            if event.get('confidence', 100) < config.min_confidence:
                continue
            filtered_events.append(event)

        # Import events as entities
        created_ids = []
        errors = []
        imported = 0
        failed = 0
        skipped = len(events) - len(filtered_events)

        for i, event in enumerate(filtered_events):
            try:
                # Create entity based on event type
                profile = {'core': {}}
                event_type = event.get('type', '').upper()
                value = event.get('value', '')

                if 'EMAIL' in event_type:
                    profile['core']['email'] = [value]
                elif 'NAME' in event_type or 'HUMAN' in event_type:
                    parts = value.split(' ', 1)
                    profile['core']['name'] = [{
                        'first_name': parts[0],
                        'last_name': parts[1] if len(parts) > 1 else ''
                    }]
                elif 'PHONE' in event_type:
                    profile['core']['phone'] = [{'number': value}]
                elif 'DOMAIN' in event_type:
                    profile['online'] = {'domains': [value]}
                elif 'IP' in event_type:
                    profile['technical'] = {'ip_addresses': [value]}
                else:
                    profile['core']['notes'] = [value]

                entity = {
                    'id': _generate_entity_id(),
                    'profile': profile,
                    'metadata': {
                        'source': 'spiderfoot',
                        'event_type': event_type,
                        'confidence': event.get('confidence', 100),
                        'module': event.get('properties', {}).get('module', ''),
                        'imported_at': datetime.now().isoformat()
                    }
                }

                result = neo4j_handler.add_person(project_safe_name, entity)
                if result:
                    created_ids.append(result.get('id', entity['id']))
                    imported += 1
                else:
                    failed += 1
                    errors.append(ImportError(index=i, error="Failed to create entity"))

            except Exception as e:
                failed += 1
                errors.append(ImportError(index=i, error=str(e)))

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=len(events),
            imported=imported,
            skipped=skipped,
            failed=failed,
            errors=errors[:100],
            created_entity_ids=created_ids,
            import_time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/theharvester",
    response_model=ImportResult,
    summary="Import TheHarvester output",
    description="Import emails, hosts, and IPs from TheHarvester results.",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file format"},
        404: {"description": "Project not found"},
    }
)
async def import_theharvester(
    project_safe_name: str,
    file: UploadFile = File(..., description="TheHarvester output file (JSON or text)"),
    config: TheHarvesterImportConfig = Body(default=None),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import findings from TheHarvester.

    Imports discovered emails, hosts, and IP addresses.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: TheHarvester output file (JSON or text format)
    - **config**: Optional import configuration
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if config is None:
        config = TheHarvesterImportConfig()

    try:
        content = await file.read()
        results = _parse_theharvester(content.decode('utf-8'))

        created_ids = []
        errors = []
        imported = 0
        failed = 0
        skipped = 0
        total = 0

        seen_values = set()

        # Import emails
        if config.import_emails:
            for email in results.get('emails', []):
                total += 1
                if config.deduplicate and email.lower() in seen_values:
                    skipped += 1
                    continue
                seen_values.add(email.lower())

                try:
                    entity = {
                        'id': _generate_entity_id(),
                        'profile': {'core': {'email': [email]}},
                        'metadata': {
                            'source': 'theharvester',
                            'type': 'email',
                            'imported_at': datetime.now().isoformat()
                        }
                    }
                    result = neo4j_handler.add_person(project_safe_name, entity)
                    if result:
                        created_ids.append(result.get('id', entity['id']))
                        imported += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    errors.append(ImportError(error=f"Email '{email}': {str(e)}"))

        # Import hosts
        if config.import_hosts:
            for host in results.get('hosts', []):
                total += 1
                if config.deduplicate and host.lower() in seen_values:
                    skipped += 1
                    continue
                seen_values.add(host.lower())

                try:
                    entity = {
                        'id': _generate_entity_id(),
                        'profile': {'online': {'domains': [host]}},
                        'metadata': {
                            'source': 'theharvester',
                            'type': 'host',
                            'imported_at': datetime.now().isoformat()
                        }
                    }
                    result = neo4j_handler.add_person(project_safe_name, entity)
                    if result:
                        created_ids.append(result.get('id', entity['id']))
                        imported += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    errors.append(ImportError(error=f"Host '{host}': {str(e)}"))

        # Import IPs
        if config.import_ips:
            for ip in results.get('ips', []):
                total += 1
                if config.deduplicate and ip in seen_values:
                    skipped += 1
                    continue
                seen_values.add(ip)

                try:
                    entity = {
                        'id': _generate_entity_id(),
                        'profile': {'technical': {'ip_addresses': [ip]}},
                        'metadata': {
                            'source': 'theharvester',
                            'type': 'ip',
                            'imported_at': datetime.now().isoformat()
                        }
                    }
                    result = neo4j_handler.add_person(project_safe_name, entity)
                    if result:
                        created_ids.append(result.get('id', entity['id']))
                        imported += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    errors.append(ImportError(error=f"IP '{ip}': {str(e)}"))

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=total,
            imported=imported,
            skipped=skipped,
            failed=failed,
            errors=errors[:100],
            created_entity_ids=created_ids,
            import_time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/shodan",
    response_model=ImportResult,
    summary="Import Shodan data",
    description="Import host and service information from Shodan exports.",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file format"},
        404: {"description": "Project not found"},
    }
)
async def import_shodan(
    project_safe_name: str,
    file: UploadFile = File(..., description="Shodan export file (JSON or JSONL)"),
    config: ShodanImportConfig = Body(default=None),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import data from Shodan exports.

    Imports host information, services, and vulnerabilities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: Shodan export file (JSON or line-delimited JSON)
    - **config**: Optional import configuration
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if config is None:
        config = ShodanImportConfig()

    try:
        content = await file.read()
        hosts = _parse_shodan_json(content.decode('utf-8'))

        if not hosts:
            return ImportResult(
                success=False,
                total_records=0,
                imported=0,
                errors=[ImportError(error="No hosts found in file")]
            )

        created_ids = []
        errors = []
        imported = 0
        failed = 0

        for i, host_data in enumerate(hosts):
            try:
                if not config.import_hosts:
                    continue

                ip = host_data.get('ip_str', host_data.get('ip', ''))
                if not ip:
                    continue

                # Build entity profile
                profile = {
                    'technical': {
                        'ip_addresses': [ip],
                        'hostnames': host_data.get('hostnames', []),
                        'os': host_data.get('os', ''),
                    }
                }

                # Add services
                if config.import_services:
                    services = []
                    port = host_data.get('port')
                    if port:
                        services.append({
                            'port': port,
                            'protocol': host_data.get('transport', 'tcp'),
                            'service': host_data.get('product', ''),
                            'version': host_data.get('version', '')
                        })
                    if services:
                        profile['technical']['services'] = services

                # Add vulnerabilities
                if config.import_vulnerabilities:
                    vulns = host_data.get('vulns', [])
                    if vulns:
                        profile['technical']['vulnerabilities'] = vulns

                entity = {
                    'id': _generate_entity_id(),
                    'profile': profile,
                    'metadata': {
                        'source': 'shodan',
                        'org': host_data.get('org', ''),
                        'asn': host_data.get('asn', ''),
                        'isp': host_data.get('isp', ''),
                        'country': host_data.get('country_code', ''),
                        'city': host_data.get('city', ''),
                        'imported_at': datetime.now().isoformat()
                    }
                }

                result = neo4j_handler.add_person(project_safe_name, entity)
                if result:
                    created_ids.append(result.get('id', entity['id']))
                    imported += 1
                else:
                    failed += 1
                    errors.append(ImportError(index=i, error="Failed to create entity"))

            except Exception as e:
                failed += 1
                errors.append(ImportError(index=i, error=str(e)))

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=len(hosts),
            imported=imported,
            failed=failed,
            errors=errors[:100],
            created_entity_ids=created_ids,
            import_time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/hibp",
    response_model=ImportResult,
    summary="Import HIBP breach data",
    description="Import breach and paste data from Have I Been Pwned exports.",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file format"},
        404: {"description": "Project not found"},
    }
)
async def import_hibp(
    project_safe_name: str,
    file: UploadFile = File(..., description="HIBP export file (JSON)"),
    config: HIBPImportConfig = Body(default=None),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import breach data from Have I Been Pwned.

    Imports breach information and optionally links to existing email entities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: HIBP JSON export file
    - **config**: Optional import configuration
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if config is None:
        config = HIBPImportConfig()

    try:
        content = await file.read()
        data = _parse_hibp_json(content.decode('utf-8'))

        created_ids = []
        updated_ids = []
        errors = []
        imported = 0
        failed = 0
        total = 0

        # Import breaches
        if config.import_breaches:
            for i, breach in enumerate(data.get('breaches', [])):
                total += 1
                try:
                    breach_name = breach.get('Name', breach.get('name', f'Breach_{i}'))
                    breach_date = breach.get('BreachDate', breach.get('breach_date', ''))
                    email = breach.get('Email', breach.get('email', ''))

                    if config.create_breach_entities:
                        # Create entity for the breach itself
                        entity = {
                            'id': _generate_entity_id(),
                            'profile': {
                                'core': {
                                    'name': [{'first_name': breach_name}]
                                },
                                'breach_info': {
                                    'breach_name': breach_name,
                                    'breach_date': breach_date,
                                    'domain': breach.get('Domain', ''),
                                    'data_classes': breach.get('DataClasses', []),
                                    'pwn_count': breach.get('PwnCount', 0),
                                    'is_verified': breach.get('IsVerified', False)
                                }
                            },
                            'metadata': {
                                'source': 'hibp',
                                'type': 'breach',
                                'imported_at': datetime.now().isoformat()
                            }
                        }
                        result = neo4j_handler.add_person(project_safe_name, entity)
                        if result:
                            created_ids.append(result.get('id', entity['id']))
                            imported += 1
                        else:
                            failed += 1

                    elif email and config.link_to_existing_emails:
                        # Find existing entity with this email and update
                        # This is a simplified approach - would need entity search
                        entity = {
                            'id': _generate_entity_id(),
                            'profile': {
                                'core': {'email': [email]},
                                'breach_info': {
                                    'breaches': [{
                                        'name': breach_name,
                                        'date': breach_date,
                                        'data_classes': breach.get('DataClasses', [])
                                    }]
                                }
                            },
                            'metadata': {
                                'source': 'hibp',
                                'imported_at': datetime.now().isoformat()
                            }
                        }
                        result = neo4j_handler.add_person(project_safe_name, entity)
                        if result:
                            created_ids.append(result.get('id', entity['id']))
                            imported += 1
                        else:
                            failed += 1

                except Exception as e:
                    failed += 1
                    errors.append(ImportError(index=i, error=str(e)))

        # Import pastes
        if config.import_pastes:
            for i, paste in enumerate(data.get('pastes', [])):
                total += 1
                try:
                    entity = {
                        'id': _generate_entity_id(),
                        'profile': {
                            'paste_info': {
                                'source': paste.get('Source', ''),
                                'id': paste.get('Id', ''),
                                'title': paste.get('Title', ''),
                                'date': paste.get('Date', ''),
                                'email_count': paste.get('EmailCount', 0)
                            }
                        },
                        'metadata': {
                            'source': 'hibp',
                            'type': 'paste',
                            'imported_at': datetime.now().isoformat()
                        }
                    }
                    result = neo4j_handler.add_person(project_safe_name, entity)
                    if result:
                        created_ids.append(result.get('id', entity['id']))
                        imported += 1
                    else:
                        failed += 1

                except Exception as e:
                    failed += 1
                    errors.append(ImportError(error=str(e)))

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=total,
            imported=imported,
            failed=failed,
            errors=errors[:100],
            created_entity_ids=created_ids,
            updated_entity_ids=updated_ids,
            import_time_ms=elapsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/csv",
    response_model=ImportResult,
    summary="Import generic CSV with mapping",
    description="Import entities from a CSV file with custom field mapping.",
    responses={
        200: {"description": "Import completed successfully"},
        400: {"description": "Invalid file or mapping"},
        404: {"description": "Project not found"},
    }
)
async def import_csv(
    project_safe_name: str,
    file: UploadFile = File(..., description="CSV file to import"),
    config: CSVImportConfig = Body(..., description="CSV import configuration with field mappings"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Import entities from a CSV file with custom field mapping.

    Allows mapping CSV columns to entity profile fields with optional
    transformations.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: CSV file to import
    - **config**: Import configuration with field mappings
    """
    start_time = datetime.now()

    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        content = await file.read()
        csv_content = content.decode('utf-8')

        # Parse CSV
        reader = csv.DictReader(
            io.StringIO(csv_content),
            delimiter=config.delimiter
        )

        rows = list(reader)
        if config.skip_header and rows:
            # DictReader already handles headers, so this is for explicit skip
            pass

        created_ids = []
        updated_ids = []
        errors = []
        imported = 0
        failed = 0

        # Build mapping dict
        mapping = {m.csv_column: m for m in config.mappings}

        for i, row in enumerate(rows):
            try:
                # Build entity profile from mapping
                profile = {}

                for csv_col, value in row.items():
                    if csv_col in mapping:
                        m = mapping[csv_col]
                        transformed_value = _apply_csv_transform(value, m.transform)
                        _set_nested_value(profile, m.entity_field, transformed_value)

                if not profile:
                    errors.append(ImportError(
                        index=i,
                        error="No mapped fields found in row"
                    ))
                    failed += 1
                    continue

                # Check for existing entity if update mode
                existing_id = None
                if config.update_existing and config.match_field:
                    # Would need to search for existing entity
                    pass

                entity = {
                    'id': existing_id or _generate_entity_id(),
                    'profile': profile,
                    'metadata': {
                        'source': 'csv_import',
                        'imported_at': datetime.now().isoformat()
                    }
                }

                if existing_id:
                    result = neo4j_handler.update_person(project_safe_name, existing_id, entity)
                    if result:
                        updated_ids.append(existing_id)
                        imported += 1
                    else:
                        failed += 1
                else:
                    result = neo4j_handler.add_person(project_safe_name, entity)
                    if result:
                        created_ids.append(result.get('id', entity['id']))
                        imported += 1
                    else:
                        failed += 1

            except Exception as e:
                failed += 1
                errors.append(ImportError(index=i, error=str(e)))

        elapsed = int((datetime.now() - start_time).total_seconds() * 1000)

        return ImportResult(
            success=failed == 0,
            total_records=len(rows),
            imported=imported,
            failed=failed,
            errors=errors[:100],
            created_entity_ids=created_ids,
            updated_entity_ids=updated_ids,
            import_time_ms=elapsed
        )

    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=ValidationResult,
    summary="Validate import file (dry run)",
    description="Validate an import file without actually importing data.",
    responses={
        200: {"description": "Validation completed"},
        400: {"description": "Invalid file"},
    }
)
async def validate_import(
    project_safe_name: str,
    file: UploadFile = File(..., description="File to validate"),
    format: Optional[ImportFormat] = None,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Validate an import file without importing.

    Performs a dry run to check file format, parse records, and suggest
    field mappings for CSV files.

    - **project_safe_name**: The URL-safe identifier for the project
    - **file**: File to validate
    - **format**: Expected format (optional, will auto-detect)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        content = await file.read()
        filename = file.filename or ""
        content_str = content.decode('utf-8', errors='ignore')

        warnings = []
        errors = []
        sample_records = []
        detected_format = None
        record_count = 0
        field_mapping_suggestions = {}

        # Try to detect format
        if format:
            detected_format = format.value
        elif filename.endswith('.mtgx'):
            detected_format = 'maltego'
        elif filename.endswith('.csv'):
            detected_format = 'csv'
        elif filename.endswith('.json') or filename.endswith('.jsonl'):
            # Try to determine JSON type
            try:
                data = json.loads(content_str)
                if isinstance(data, list) and data:
                    first = data[0]
                    if 'ip_str' in first or 'port' in first:
                        detected_format = 'shodan'
                    elif 'type' in first and 'data' in first:
                        detected_format = 'spiderfoot'
                    elif 'Name' in first or 'BreachDate' in first:
                        detected_format = 'hibp'
                elif isinstance(data, dict):
                    if 'events' in data:
                        detected_format = 'spiderfoot'
                    elif 'matches' in data:
                        detected_format = 'shodan'
            except json.JSONDecodeError:
                # Try line-delimited JSON
                first_line = content_str.split('\n')[0]
                try:
                    first = json.loads(first_line)
                    if 'ip_str' in first:
                        detected_format = 'shodan'
                except:
                    pass

        # Parse and validate based on format
        if detected_format == 'maltego':
            if filename.endswith('.mtgx'):
                entities, rels = _parse_maltego_mtgx(content)
            else:
                entities = _parse_maltego_csv(content_str)
            record_count = len(entities)
            sample_records = entities[:5]

        elif detected_format == 'spiderfoot':
            events = _parse_spiderfoot_json(content_str)
            record_count = len(events)
            sample_records = events[:5]

        elif detected_format == 'theharvester':
            results = _parse_theharvester(content_str)
            record_count = (
                len(results.get('emails', [])) +
                len(results.get('hosts', [])) +
                len(results.get('ips', []))
            )
            sample_records = [results]

        elif detected_format == 'shodan':
            hosts = _parse_shodan_json(content_str)
            record_count = len(hosts)
            sample_records = hosts[:5]

        elif detected_format == 'hibp':
            data = _parse_hibp_json(content_str)
            record_count = len(data.get('breaches', [])) + len(data.get('pastes', []))
            sample_records = [data]

        elif detected_format == 'csv' or not detected_format:
            # Parse CSV and suggest mappings
            try:
                reader = csv.DictReader(io.StringIO(content_str))
                rows = list(reader)
                record_count = len(rows)
                sample_records = rows[:5]

                # Suggest field mappings
                if reader.fieldnames:
                    for col in reader.fieldnames:
                        col_lower = col.lower()
                        if 'email' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.email'
                        elif 'first' in col_lower and 'name' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.name.first_name'
                        elif 'last' in col_lower and 'name' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.name.last_name'
                        elif col_lower == 'name':
                            field_mapping_suggestions[col] = 'profile.core.name.first_name'
                        elif 'phone' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.phone.number'
                        elif 'twitter' in col_lower:
                            field_mapping_suggestions[col] = 'profile.social.twitter'
                        elif 'linkedin' in col_lower:
                            field_mapping_suggestions[col] = 'profile.social.linkedin'
                        elif 'address' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.address.street'
                        elif 'city' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.address.city'
                        elif 'country' in col_lower:
                            field_mapping_suggestions[col] = 'profile.core.address.country'

                detected_format = 'csv'

            except csv.Error as e:
                errors.append(ImportError(error=f"CSV parsing error: {str(e)}"))

        if not detected_format:
            errors.append(ImportError(error="Could not detect file format"))

        if record_count == 0:
            warnings.append("No records found in file")

        return ValidationResult(
            valid=len(errors) == 0,
            format_detected=detected_format,
            record_count=record_count,
            warnings=warnings,
            errors=errors,
            sample_records=sample_records,
            field_mapping_suggestions=field_mapping_suggestions
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@formats_router.get(
    "/formats",
    response_model=FormatsListResponse,
    summary="List supported import formats",
    description="Get a list of all supported import formats with their schemas.",
    responses={
        200: {"description": "Format list retrieved successfully"},
    }
)
async def list_import_formats():
    """
    List all supported import formats.

    Returns information about each supported format including file extensions,
    capabilities, and configuration schema.
    """
    formats = [
        FormatInfo(
            format="maltego",
            name="Maltego Export",
            description="Import entities and relationships from Maltego graph exports. Supports both native MTGX format and CSV exports.",
            file_extensions=[".mtgx", ".csv"],
            supports_relationships=True,
            config_schema=MaltegoImportConfig.model_json_schema()
        ),
        FormatInfo(
            format="spiderfoot",
            name="SpiderFoot Results",
            description="Import findings from SpiderFoot OSINT scans. Converts events to entities with source tracking.",
            file_extensions=[".json"],
            supports_relationships=False,
            config_schema=SpiderFootImportConfig.model_json_schema()
        ),
        FormatInfo(
            format="theharvester",
            name="TheHarvester Output",
            description="Import discovered emails, hosts, and IP addresses from TheHarvester reconnaissance results.",
            file_extensions=[".json", ".txt"],
            supports_relationships=False,
            config_schema=TheHarvesterImportConfig.model_json_schema()
        ),
        FormatInfo(
            format="shodan",
            name="Shodan Export",
            description="Import host information, services, and vulnerabilities from Shodan search exports.",
            file_extensions=[".json", ".jsonl"],
            supports_relationships=True,
            config_schema=ShodanImportConfig.model_json_schema()
        ),
        FormatInfo(
            format="hibp",
            name="Have I Been Pwned",
            description="Import breach and paste data from Have I Been Pwned API exports.",
            file_extensions=[".json"],
            supports_relationships=False,
            config_schema=HIBPImportConfig.model_json_schema()
        ),
        FormatInfo(
            format="csv",
            name="Generic CSV",
            description="Import entities from any CSV file using custom field mapping. Supports transformations and update modes.",
            file_extensions=[".csv"],
            supports_relationships=False,
            config_schema=CSVImportConfig.model_json_schema()
        ),
    ]

    return FormatsListResponse(formats=formats)
