"""
Data Import Connectors for OSINT Tools - Basset Hound Platform (Phase 16).

This service provides import connectors for common OSINT tools, enabling
seamless integration of external investigation data into the Basset Hound platform.

Supported Tools:
- Maltego: CSV/XLSX entity exports with relationship mapping
- SpiderFoot: JSON scan results
- TheHarvester: JSON/XML email/domain/IP discoveries
- Shodan: JSON host exports with service/banner data
- Have I Been Pwned: JSON breach data exports
- Generic CSV: Configurable column mapping for custom imports

Features:
- Base ImportConnector class for extensibility
- Standardized ImportResult with counts, errors, and warnings
- Dry-run mode for validation without importing
- Automatic type detection and normalization
- Entity and orphan data creation support

Usage:
    from api.services.data_import import (
        get_import_service,
        MaltegoConnector,
        SpiderFootConnector,
        ShodanConnector,
    )

    # Get the service with all connectors
    import_service = get_import_service(neo4j_handler)

    # Import Maltego export
    result = import_service.import_maltego(
        project_id="my-project",
        file_content=csv_content,
        dry_run=False
    )

    # Import SpiderFoot scan
    result = import_service.import_spiderfoot(
        project_id="my-project",
        json_content=spiderfoot_json,
        dry_run=False
    )
"""

import csv
import io
import json
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

from api.models.orphan import IdentifierType, OrphanDataCreate
from api.models.entity_types import EntityType
from api.services.normalizer import get_normalizer, DataNormalizer, NormalizedResult


logger = logging.getLogger("basset_hound.data_import")


# =============================================================================
# IMPORT RESULT MODELS
# =============================================================================

@dataclass
class ImportWarning:
    """
    Warning generated during import (non-fatal issues).

    Attributes:
        index: Row/record index where warning occurred
        field: Field name that caused the warning
        message: Human-readable warning message
        original_value: The original value that triggered the warning
    """
    index: int
    field: str
    message: str
    original_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "field": self.field,
            "message": self.message,
            "original_value": self.original_value,
        }


@dataclass
class ImportError:
    """
    Error generated during import (record was skipped).

    Attributes:
        index: Row/record index where error occurred
        message: Human-readable error message
        record_data: Partial data from the failed record
    """
    index: int
    message: str
    record_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "message": self.message,
            "record_data": self.record_data,
        }


@dataclass
class ImportResult:
    """
    Result of an import operation.

    Provides comprehensive statistics and details about the import operation,
    including counts, created IDs, errors, and warnings.

    Attributes:
        total_records: Total number of records processed
        entities_created: Number of entities successfully created
        orphans_created: Number of orphan data records created
        relationships_created: Number of relationships created
        skipped: Number of records skipped (duplicates, invalid, etc.)
        errors: List of ImportError objects for failed records
        warnings: List of ImportWarning objects for non-fatal issues
        entity_ids: List of created entity IDs
        orphan_ids: List of created orphan data IDs
        dry_run: Whether this was a dry-run (validation only)
        source_tool: Name of the source tool (maltego, spiderfoot, etc.)
        import_timestamp: When the import was performed
    """
    total_records: int = 0
    entities_created: int = 0
    orphans_created: int = 0
    relationships_created: int = 0
    skipped: int = 0
    errors: List[ImportError] = field(default_factory=list)
    warnings: List[ImportWarning] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    orphan_ids: List[str] = field(default_factory=list)
    dry_run: bool = False
    source_tool: str = ""
    import_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_entity(self, entity_id: str) -> None:
        """Record a successfully created entity."""
        self.entities_created += 1
        self.entity_ids.append(entity_id)

    def add_orphan(self, orphan_id: str) -> None:
        """Record a successfully created orphan data record."""
        self.orphans_created += 1
        self.orphan_ids.append(orphan_id)

    def add_relationship(self) -> None:
        """Record a successfully created relationship."""
        self.relationships_created += 1

    def add_error(self, index: int, message: str, record_data: Optional[Dict] = None) -> None:
        """Record an error (record was skipped)."""
        self.errors.append(ImportError(index=index, message=message, record_data=record_data))

    def add_warning(
        self,
        index: int,
        field: str,
        message: str,
        original_value: Optional[str] = None
    ) -> None:
        """Record a warning (non-fatal issue)."""
        self.warnings.append(ImportWarning(
            index=index,
            field=field,
            message=message,
            original_value=original_value
        ))

    def skip_record(self) -> None:
        """Record a skipped record (duplicate, invalid, etc.)."""
        self.skipped += 1

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_records == 0:
            return 0.0
        successful = self.entities_created + self.orphans_created
        return (successful / self.total_records) * 100

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were generated."""
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "total_records": self.total_records,
            "entities_created": self.entities_created,
            "orphans_created": self.orphans_created,
            "relationships_created": self.relationships_created,
            "skipped": self.skipped,
            "success_rate": round(self.success_rate, 2),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "entity_ids": self.entity_ids,
            "orphan_ids": self.orphan_ids,
            "dry_run": self.dry_run,
            "source_tool": self.source_tool,
            "import_timestamp": self.import_timestamp,
        }


# =============================================================================
# BASE IMPORT CONNECTOR
# =============================================================================

class ImportConnector(ABC):
    """
    Abstract base class for OSINT tool import connectors.

    Provides common functionality for parsing, validating, and importing
    data from external OSINT tools into Basset Hound.

    Subclasses must implement:
    - parse(): Parse the raw input data into normalized records
    - get_tool_name(): Return the name of the source tool

    Usage:
        class MyToolConnector(ImportConnector):
            def parse(self, content: str) -> Generator[Dict, None, None]:
                # Parse content and yield records
                for record in parse_my_format(content):
                    yield record

            def get_tool_name(self) -> str:
                return "my_tool"
    """

    def __init__(self, neo4j_handler, orphan_service=None):
        """
        Initialize the connector.

        Args:
            neo4j_handler: Neo4j database handler for entity operations
            orphan_service: Optional OrphanService for orphan data operations
        """
        self.neo4j = neo4j_handler
        self.orphan_service = orphan_service
        self.normalizer: DataNormalizer = get_normalizer()

    @abstractmethod
    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse the input content and yield normalized records.

        Each yielded record should be a dictionary with:
        - 'type': 'entity' or 'orphan'
        - 'data': The record data
        - 'relationships': Optional list of relationship definitions

        Args:
            content: Raw content from the tool export

        Yields:
            Dictionaries containing parsed record data
        """
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the name of the source tool."""
        pass

    def import_data(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False,
        create_entities: bool = True,
        create_orphans: bool = True
    ) -> ImportResult:
        """
        Import data from the tool export.

        Args:
            project_id: Target project ID or safe_name
            content: Raw content from the tool export
            dry_run: If True, validate without actually importing
            create_entities: Whether to create entity records
            create_orphans: Whether to create orphan data records

        Returns:
            ImportResult with statistics and details
        """
        result = ImportResult(
            dry_run=dry_run,
            source_tool=self.get_tool_name()
        )

        # Verify project exists
        project = self._get_project(project_id)
        if not project:
            result.add_error(-1, f"Project '{project_id}' not found")
            return result

        project_safe_name = project.get("safe_name", project_id)

        # Parse and process records
        try:
            for index, record in enumerate(self.parse(content)):
                result.total_records += 1

                try:
                    record_type = record.get("type", "orphan")
                    record_data = record.get("data", {})
                    relationships = record.get("relationships", [])

                    if record_type == "entity" and create_entities:
                        if not dry_run:
                            entity_id = self._create_entity(project_safe_name, record_data)
                            if entity_id:
                                result.add_entity(entity_id)

                                # Create relationships if any
                                for rel in relationships:
                                    if self._create_relationship(
                                        project_safe_name,
                                        entity_id,
                                        rel
                                    ):
                                        result.add_relationship()
                            else:
                                result.add_error(index, "Failed to create entity", record_data)
                        else:
                            # Dry run - just count
                            result.entities_created += 1

                    elif record_type == "orphan" and create_orphans:
                        if not dry_run:
                            orphan_id = self._create_orphan(project_id, record_data)
                            if orphan_id:
                                result.add_orphan(orphan_id)
                            else:
                                result.add_error(index, "Failed to create orphan", record_data)
                        else:
                            result.orphans_created += 1

                    else:
                        result.skip_record()

                except Exception as e:
                    result.add_error(index, f"Processing error: {str(e)}", record.get("data"))

        except Exception as e:
            result.add_error(-1, f"Parse error: {str(e)}")
            logger.error(f"Import parse error for {self.get_tool_name()}: {e}")

        logger.info(
            f"Import from {self.get_tool_name()} complete: "
            f"{result.entities_created} entities, {result.orphans_created} orphans, "
            f"{len(result.errors)} errors (dry_run={dry_run})"
        )

        return result

    def validate(self, content: Union[str, bytes]) -> ImportResult:
        """
        Validate content without importing (shorthand for dry_run=True).

        Args:
            content: Raw content to validate

        Returns:
            ImportResult with validation results
        """
        return self.import_data(
            project_id="__validation__",
            content=content,
            dry_run=True
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID or safe_name."""
        if project_id == "__validation__":
            # Return dummy project for validation
            return {"id": "__validation__", "safe_name": "__validation__"}

        try:
            projects = self.neo4j.get_all_projects()
            for project in projects:
                if project.get("id") == project_id or project.get("safe_name") == project_id:
                    return project
            return None
        except Exception:
            return None

    def _create_entity(
        self,
        project_safe_name: str,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """Create an entity from parsed data."""
        try:
            entity_id = data.get("id") or str(uuid4())
            profile = data.get("profile", {})
            entity_type = data.get("entity_type", EntityType.PERSON.value)

            entity_data = {
                "id": entity_id,
                "profile": profile,
                "entity_type": entity_type,
                "created_at": datetime.now().isoformat(),
            }

            created = self.neo4j.create_person(project_safe_name, entity_data)
            return created.get("id") if created else None

        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            return None

    def _create_orphan(
        self,
        project_id: str,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """Create an orphan data record from parsed data."""
        if not self.orphan_service:
            logger.warning("OrphanService not available for orphan creation")
            return None

        try:
            orphan_create = OrphanDataCreate(
                id=data.get("id") or f"orphan-{uuid4()}",
                identifier_type=IdentifierType(data.get("identifier_type", "other")),
                identifier_value=data.get("identifier_value", ""),
                source=data.get("source", self.get_tool_name()),
                notes=data.get("notes"),
                tags=data.get("tags", []),
                confidence_score=data.get("confidence_score"),
                metadata=data.get("metadata", {}),
                discovered_date=data.get("discovered_date"),
            )

            created = self.orphan_service.create_orphan(project_id, orphan_create)
            return created.id if created else None

        except Exception as e:
            logger.error(f"Failed to create orphan: {e}")
            return None

    def _create_relationship(
        self,
        project_safe_name: str,
        source_entity_id: str,
        relationship: Dict[str, Any]
    ) -> bool:
        """Create a relationship between entities."""
        try:
            target_id = relationship.get("target_id")
            rel_type = relationship.get("type", "RELATED_TO")

            if not target_id:
                return False

            # Use Neo4j handler to create relationship
            self.neo4j.create_relationship(
                project_safe_name,
                source_entity_id,
                target_id,
                rel_type,
                relationship.get("properties", {})
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

    def _detect_identifier_type(self, value: str) -> IdentifierType:
        """
        Auto-detect the identifier type from a value.

        Args:
            value: The identifier value to analyze

        Returns:
            IdentifierType enum value
        """
        if not value:
            return IdentifierType.OTHER

        value = value.strip()

        # Email pattern
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            return IdentifierType.EMAIL

        # Phone pattern (various formats)
        if re.match(r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,}$', value):
            return IdentifierType.PHONE

        # IP address (IPv4 or IPv6)
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', value):
            return IdentifierType.IP_ADDRESS
        if re.match(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$', value):
            return IdentifierType.IP_ADDRESS

        # Domain pattern
        if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}$', value):
            return IdentifierType.DOMAIN

        # URL pattern
        if re.match(r'^https?://', value, re.IGNORECASE):
            return IdentifierType.URL

        # Crypto address patterns
        if re.match(r'^(0x)?[a-fA-F0-9]{40}$', value):  # Ethereum
            return IdentifierType.CRYPTO_ADDRESS
        if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', value):  # Bitcoin
            return IdentifierType.CRYPTO_ADDRESS
        if re.match(r'^bc1[a-zA-HJ-NP-Z0-9]{25,90}$', value):  # Bitcoin Bech32
            return IdentifierType.CRYPTO_ADDRESS

        # MAC address
        if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', value):
            return IdentifierType.MAC_ADDRESS

        # Username pattern (starts with @ or simple alphanumeric)
        if value.startswith('@'):
            return IdentifierType.USERNAME

        return IdentifierType.OTHER


# =============================================================================
# MALTEGO CONNECTOR
# =============================================================================

class MaltegoConnector(ImportConnector):
    """
    Import connector for Maltego CSV/XLSX exports.

    Maltego exports contain entity data with types and properties, plus
    relationship information (links between entities).

    Supported Formats:
    - CSV export from Maltego graph
    - XLSX export from Maltego graph

    Sample Maltego CSV Format:
    ```
    Entity Type,Entity Value,Property Name,Property Value,Link Entity,Link Direction
    Person,John Doe,email,john@example.com,,
    EmailAddress,john@example.com,,,,
    Person,John Doe,,,,EmailAddress:john@example.com,outgoing
    Domain,example.com,registrar,GoDaddy,,
    ```

    Type Mapping:
    - Person -> EntityType.PERSON
    - Organization/Company -> EntityType.ORGANIZATION
    - Domain/Website -> Creates orphan with domain type
    - EmailAddress -> Creates orphan with email type
    - PhoneNumber -> Creates orphan with phone type
    - IPAddress -> Creates orphan with ip_address type
    - Location/Address -> EntityType.LOCATION
    - Device -> EntityType.DEVICE

    Usage:
        connector = MaltegoConnector(neo4j_handler, orphan_service)
        result = connector.import_data(
            project_id="my-project",
            content=csv_content,
            dry_run=False
        )
    """

    # Maltego entity type to Basset Hound type mapping
    ENTITY_TYPE_MAP = {
        # Person entities
        "person": EntityType.PERSON,
        "maltego.person": EntityType.PERSON,
        "maltego.affiliation": EntityType.PERSON,

        # Organization entities
        "organization": EntityType.ORGANIZATION,
        "company": EntityType.ORGANIZATION,
        "maltego.organization": EntityType.ORGANIZATION,
        "maltego.company": EntityType.ORGANIZATION,

        # Location entities
        "location": EntityType.LOCATION,
        "address": EntityType.LOCATION,
        "maltego.location": EntityType.LOCATION,

        # Device entities
        "device": EntityType.DEVICE,
        "maltego.device": EntityType.DEVICE,
    }

    # Maltego types that map to orphan data
    ORPHAN_TYPE_MAP = {
        "emailaddress": IdentifierType.EMAIL,
        "maltego.emailaddress": IdentifierType.EMAIL,
        "email": IdentifierType.EMAIL,

        "phonenumber": IdentifierType.PHONE,
        "maltego.phonenumber": IdentifierType.PHONE,
        "phone": IdentifierType.PHONE,

        "domain": IdentifierType.DOMAIN,
        "maltego.domain": IdentifierType.DOMAIN,
        "website": IdentifierType.DOMAIN,
        "maltego.website": IdentifierType.DOMAIN,
        "dns": IdentifierType.DOMAIN,

        "ipaddress": IdentifierType.IP_ADDRESS,
        "maltego.ipv4address": IdentifierType.IP_ADDRESS,
        "maltego.ipv6address": IdentifierType.IP_ADDRESS,
        "ip": IdentifierType.IP_ADDRESS,

        "url": IdentifierType.URL,
        "maltego.url": IdentifierType.URL,

        "alias": IdentifierType.USERNAME,
        "maltego.alias": IdentifierType.USERNAME,
        "username": IdentifierType.USERNAME,
        "socialprofile": IdentifierType.SOCIAL_MEDIA,
        "maltego.facebook.affiliation": IdentifierType.SOCIAL_MEDIA,
        "maltego.twitter.affiliation": IdentifierType.SOCIAL_MEDIA,

        "cryptocurrency": IdentifierType.CRYPTO_ADDRESS,
        "bitcoinaddress": IdentifierType.CRYPTO_ADDRESS,
        "ethereumaddress": IdentifierType.CRYPTO_ADDRESS,
    }

    def get_tool_name(self) -> str:
        return "maltego"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse Maltego CSV export.

        Yields entity and orphan records with extracted properties
        and relationship information.
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))

        # Track entities and their relationships
        entities: Dict[str, Dict[str, Any]] = {}
        relationships: List[Dict[str, Any]] = []

        for row in reader:
            entity_type = (row.get("Entity Type", "") or row.get("type", "")).lower().strip()
            entity_value = row.get("Entity Value", "") or row.get("value", "")
            prop_name = row.get("Property Name", "") or row.get("property", "")
            prop_value = row.get("Property Value", "") or row.get("property_value", "")
            link_entity = row.get("Link Entity", "") or row.get("link", "")
            link_direction = row.get("Link Direction", "") or row.get("direction", "")

            if not entity_type or not entity_value:
                continue

            # Create unique key for entity
            entity_key = f"{entity_type}:{entity_value}"

            # Initialize entity if new
            if entity_key not in entities:
                entities[entity_key] = {
                    "maltego_type": entity_type,
                    "value": entity_value,
                    "properties": {},
                    "links": [],
                }

            # Add property
            if prop_name and prop_value:
                entities[entity_key]["properties"][prop_name] = prop_value

            # Track relationship
            if link_entity:
                entities[entity_key]["links"].append({
                    "target": link_entity,
                    "direction": link_direction,
                })

        # Convert to Basset Hound records
        for entity_key, entity_data in entities.items():
            maltego_type = entity_data["maltego_type"]
            value = entity_data["value"]
            properties = entity_data["properties"]

            # Check if this maps to an entity type
            if maltego_type in self.ENTITY_TYPE_MAP:
                entity_type = self.ENTITY_TYPE_MAP[maltego_type]
                profile = self._build_entity_profile(entity_type, value, properties)

                yield {
                    "type": "entity",
                    "data": {
                        "entity_type": entity_type.value,
                        "profile": profile,
                    },
                    "relationships": [],  # TODO: Map Maltego links to relationships
                }

            # Check if this maps to orphan data
            elif maltego_type in self.ORPHAN_TYPE_MAP:
                identifier_type = self.ORPHAN_TYPE_MAP[maltego_type]

                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": identifier_type.value,
                        "identifier_value": value,
                        "source": "Maltego Export",
                        "tags": ["maltego", maltego_type],
                        "metadata": {
                            "maltego_type": maltego_type,
                            "properties": properties,
                        },
                    },
                }

            # Unknown type - create as orphan with auto-detected type
            else:
                detected_type = self._detect_identifier_type(value)

                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": detected_type.value,
                        "identifier_value": value,
                        "source": "Maltego Export",
                        "tags": ["maltego", maltego_type],
                        "notes": f"Unknown Maltego type: {maltego_type}",
                        "metadata": {
                            "maltego_type": maltego_type,
                            "properties": properties,
                        },
                    },
                }

    def _build_entity_profile(
        self,
        entity_type: EntityType,
        value: str,
        properties: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build entity profile from Maltego properties."""
        profile: Dict[str, Dict[str, Any]] = {"core": {}}

        if entity_type == EntityType.PERSON:
            # Parse name from value
            name_parts = value.split()
            profile["core"]["name"] = [{
                "first_name": name_parts[0] if name_parts else value,
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            }]

            # Map common Maltego properties
            if "email" in properties:
                profile["core"]["email"] = [properties["email"]]
            if "phone" in properties:
                profile["core"]["phone"] = [properties["phone"]]
            if "title" in properties:
                profile.setdefault("professional", {})["title"] = [properties["title"]]

        elif entity_type == EntityType.ORGANIZATION:
            profile["core"]["name"] = [value]

            if "website" in properties:
                profile.setdefault("online", {})["website"] = [properties["website"]]
            if "industry" in properties:
                profile["core"]["industry"] = [properties["industry"]]

        elif entity_type == EntityType.LOCATION:
            profile["core"]["name"] = [value]

            if "address" in properties:
                profile.setdefault("address", {})["full_address"] = [properties["address"]]
            if "country" in properties:
                profile.setdefault("address", {})["country"] = [properties["country"]]
            if "city" in properties:
                profile.setdefault("address", {})["city"] = [properties["city"]]

        elif entity_type == EntityType.DEVICE:
            profile["core"]["name"] = [value]

            if "mac" in properties:
                profile.setdefault("technical", {})["mac_address"] = [properties["mac"]]
            if "ip" in properties:
                profile.setdefault("technical", {})["ip_address"] = [properties["ip"]]

        return profile


# =============================================================================
# SPIDERFOOT CONNECTOR
# =============================================================================

class SpiderFootConnector(ImportConnector):
    """
    Import connector for SpiderFoot JSON scan results.

    SpiderFoot produces structured JSON output containing discovered
    data points from its various modules.

    Sample SpiderFoot JSON Format:
    ```json
    {
        "generated": "2024-01-15 10:30:00",
        "scan_name": "example.com scan",
        "data": [
            {
                "type": "EMAILADDR",
                "data": "admin@example.com",
                "module": "sfp_emailformat",
                "source": "example.com"
            },
            {
                "type": "IP_ADDRESS",
                "data": "192.168.1.1",
                "module": "sfp_dnsresolve",
                "source": "example.com"
            },
            {
                "type": "DOMAIN_NAME",
                "data": "mail.example.com",
                "module": "sfp_dnsraw",
                "source": "example.com"
            }
        ]
    }
    ```

    SpiderFoot Type Mapping:
    - EMAILADDR -> email orphan
    - IP_ADDRESS, IPV6_ADDRESS -> ip_address orphan
    - DOMAIN_NAME, INTERNET_NAME -> domain orphan
    - PHONE_NUMBER -> phone orphan
    - USERNAME, ACCOUNT -> username orphan
    - BITCOIN_ADDRESS, ETHEREUM_ADDRESS -> crypto_address orphan
    - HUMAN_NAME -> person entity

    Usage:
        connector = SpiderFootConnector(neo4j_handler, orphan_service)
        result = connector.import_data(
            project_id="my-project",
            content=json_content
        )
    """

    # SpiderFoot data type mapping
    TYPE_MAP = {
        # Email
        "EMAILADDR": IdentifierType.EMAIL,
        "EMAILADDR_GENERIC": IdentifierType.EMAIL,

        # Phone
        "PHONE_NUMBER": IdentifierType.PHONE,

        # IP Addresses
        "IP_ADDRESS": IdentifierType.IP_ADDRESS,
        "IPV6_ADDRESS": IdentifierType.IP_ADDRESS,
        "NETBLOCK_OWNER": IdentifierType.IP_ADDRESS,

        # Domains
        "DOMAIN_NAME": IdentifierType.DOMAIN,
        "INTERNET_NAME": IdentifierType.DOMAIN,
        "AFFILIATE_DOMAIN_NAME": IdentifierType.DOMAIN,
        "CO_HOSTED_SITE": IdentifierType.DOMAIN,
        "SIMILARDOMAIN": IdentifierType.DOMAIN,

        # URLs
        "URL": IdentifierType.URL,
        "LINKED_URL_INTERNAL": IdentifierType.URL,
        "LINKED_URL_EXTERNAL": IdentifierType.URL,

        # Usernames/Social
        "USERNAME": IdentifierType.USERNAME,
        "ACCOUNT_EXTERNAL_OWNED": IdentifierType.USERNAME,
        "SOCIAL_MEDIA": IdentifierType.SOCIAL_MEDIA,

        # Crypto
        "BITCOIN_ADDRESS": IdentifierType.CRYPTO_ADDRESS,
        "ETHEREUM_ADDRESS": IdentifierType.CRYPTO_ADDRESS,

        # MAC Address
        "PHYSICAL_ADDRESS": IdentifierType.MAC_ADDRESS,
    }

    # SpiderFoot types that should create entities
    ENTITY_TYPES = {
        "HUMAN_NAME": EntityType.PERSON,
        "COMPANY_NAME": EntityType.ORGANIZATION,
    }

    def get_tool_name(self) -> str:
        return "spiderfoot"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse SpiderFoot JSON scan results.

        Supports both single scan format and multi-scan format.
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SpiderFoot JSON: {e}")
            return

        # Handle different SpiderFoot output formats
        scan_data = []
        scan_name = "SpiderFoot Scan"

        if isinstance(data, dict):
            scan_name = data.get("scan_name", data.get("name", scan_name))
            scan_data = data.get("data", data.get("results", []))

            # Some versions have nested structure
            if not scan_data and "scans" in data:
                for scan in data["scans"]:
                    scan_data.extend(scan.get("data", []))

        elif isinstance(data, list):
            scan_data = data

        # Process each data point
        for item in scan_data:
            if not isinstance(item, dict):
                continue

            sf_type = item.get("type", "").upper()
            value = item.get("data", "")
            module = item.get("module", "")
            source = item.get("source", "")

            if not sf_type or not value:
                continue

            # Check if this creates an entity
            if sf_type in self.ENTITY_TYPES:
                entity_type = self.ENTITY_TYPES[sf_type]
                profile = self._build_entity_profile(entity_type, value, item)

                yield {
                    "type": "entity",
                    "data": {
                        "entity_type": entity_type.value,
                        "profile": profile,
                    },
                    "relationships": [],
                }

            # Map to orphan identifier type
            elif sf_type in self.TYPE_MAP:
                identifier_type = self.TYPE_MAP[sf_type]

                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": identifier_type.value,
                        "identifier_value": value,
                        "source": f"SpiderFoot: {module}" if module else "SpiderFoot",
                        "tags": ["spiderfoot", sf_type.lower()],
                        "metadata": {
                            "spiderfoot_type": sf_type,
                            "module": module,
                            "scan_source": source,
                            "scan_name": scan_name,
                        },
                    },
                }

            # Unknown type - try to auto-detect
            else:
                detected_type = self._detect_identifier_type(value)

                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": detected_type.value,
                        "identifier_value": value,
                        "source": f"SpiderFoot: {module}" if module else "SpiderFoot",
                        "tags": ["spiderfoot", sf_type.lower()],
                        "notes": f"Auto-detected from SpiderFoot type: {sf_type}",
                        "metadata": {
                            "spiderfoot_type": sf_type,
                            "module": module,
                            "scan_source": source,
                        },
                    },
                }

    def _build_entity_profile(
        self,
        entity_type: EntityType,
        value: str,
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build entity profile from SpiderFoot data."""
        profile: Dict[str, Dict[str, Any]] = {"core": {}}

        if entity_type == EntityType.PERSON:
            name_parts = value.split()
            profile["core"]["name"] = [{
                "first_name": name_parts[0] if name_parts else value,
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            }]

        elif entity_type == EntityType.ORGANIZATION:
            profile["core"]["name"] = [value]

        return profile


# =============================================================================
# THEHARVESTER CONNECTOR
# =============================================================================

class TheHarvesterConnector(ImportConnector):
    """
    Import connector for TheHarvester JSON/XML output.

    TheHarvester discovers emails, subdomains, IPs, and other data
    from various public sources.

    Sample TheHarvester JSON Format:
    ```json
    {
        "emails": [
            "admin@example.com",
            "info@example.com"
        ],
        "hosts": [
            "www.example.com:192.168.1.1",
            "mail.example.com:192.168.1.2"
        ],
        "ips": [
            "192.168.1.1",
            "192.168.1.2"
        ],
        "shodan": [
            {
                "ip": "192.168.1.1",
                "port": 80,
                "banner": "Apache/2.4"
            }
        ],
        "asns": ["AS12345"],
        "interesting_urls": [
            "https://example.com/admin",
            "https://example.com/login"
        ]
    }
    ```

    Sample TheHarvester XML Format:
    ```xml
    <theHarvester>
        <email>admin@example.com</email>
        <email>info@example.com</email>
        <host>www.example.com:192.168.1.1</host>
        <ip>192.168.1.1</ip>
    </theHarvester>
    ```

    Data Mapping:
    - emails -> email orphan
    - hosts -> domain orphan (with IP in metadata)
    - ips -> ip_address orphan
    - shodan results -> ip_address orphan with port/banner metadata
    - interesting_urls -> url orphan

    Usage:
        connector = TheHarvesterConnector(neo4j_handler, orphan_service)
        result = connector.import_data(
            project_id="my-project",
            content=json_or_xml_content
        )
    """

    def get_tool_name(self) -> str:
        return "theharvester"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse TheHarvester JSON or XML output.

        Auto-detects format based on content.
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        content = content.strip()

        # Detect format
        if content.startswith('{') or content.startswith('['):
            yield from self._parse_json(content)
        elif content.startswith('<'):
            yield from self._parse_xml(content)
        else:
            logger.error("Unknown TheHarvester format")

    def _parse_json(self, content: str) -> Generator[Dict[str, Any], None, None]:
        """Parse TheHarvester JSON format."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse TheHarvester JSON: {e}")
            return

        # Parse emails
        for email in data.get("emails", []):
            if email:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.EMAIL.value,
                        "identifier_value": email,
                        "source": "TheHarvester",
                        "tags": ["theharvester", "email"],
                    },
                }

        # Parse hosts (domain:ip format)
        for host in data.get("hosts", []):
            if not host:
                continue

            parts = host.split(":")
            domain = parts[0]
            ip = parts[1] if len(parts) > 1 else None

            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.DOMAIN.value,
                    "identifier_value": domain,
                    "source": "TheHarvester",
                    "tags": ["theharvester", "domain", "host"],
                    "metadata": {"resolved_ip": ip} if ip else {},
                },
            }

        # Parse IPs
        for ip in data.get("ips", []):
            if ip:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.IP_ADDRESS.value,
                        "identifier_value": ip,
                        "source": "TheHarvester",
                        "tags": ["theharvester", "ip"],
                    },
                }

        # Parse Shodan results
        for shodan in data.get("shodan", []):
            if isinstance(shodan, dict):
                ip = shodan.get("ip", "")
                if ip:
                    yield {
                        "type": "orphan",
                        "data": {
                            "identifier_type": IdentifierType.IP_ADDRESS.value,
                            "identifier_value": ip,
                            "source": "TheHarvester (Shodan)",
                            "tags": ["theharvester", "shodan", "ip"],
                            "metadata": {
                                "port": shodan.get("port"),
                                "banner": shodan.get("banner"),
                                "product": shodan.get("product"),
                                "version": shodan.get("version"),
                            },
                        },
                    }

        # Parse URLs
        for url in data.get("interesting_urls", data.get("urls", [])):
            if url:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.URL.value,
                        "identifier_value": url,
                        "source": "TheHarvester",
                        "tags": ["theharvester", "url"],
                    },
                }

        # Parse ASNs (stored as metadata on related IPs if available)
        asns = data.get("asns", [])
        for asn in asns:
            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.OTHER.value,
                    "identifier_value": asn,
                    "source": "TheHarvester",
                    "tags": ["theharvester", "asn"],
                    "notes": f"Autonomous System Number: {asn}",
                },
            }

    def _parse_xml(self, content: str) -> Generator[Dict[str, Any], None, None]:
        """Parse TheHarvester XML format."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse TheHarvester XML: {e}")
            return

        # Parse emails
        for elem in root.findall(".//email"):
            if elem.text:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.EMAIL.value,
                        "identifier_value": elem.text.strip(),
                        "source": "TheHarvester",
                        "tags": ["theharvester", "email"],
                    },
                }

        # Parse hosts
        for elem in root.findall(".//host"):
            if elem.text:
                parts = elem.text.strip().split(":")
                domain = parts[0]
                ip = parts[1] if len(parts) > 1 else None

                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.DOMAIN.value,
                        "identifier_value": domain,
                        "source": "TheHarvester",
                        "tags": ["theharvester", "domain", "host"],
                        "metadata": {"resolved_ip": ip} if ip else {},
                    },
                }

        # Parse IPs
        for elem in root.findall(".//ip"):
            if elem.text:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.IP_ADDRESS.value,
                        "identifier_value": elem.text.strip(),
                        "source": "TheHarvester",
                        "tags": ["theharvester", "ip"],
                    },
                }


# =============================================================================
# SHODAN CONNECTOR
# =============================================================================

class ShodanConnector(ImportConnector):
    """
    Import connector for Shodan JSON host exports.

    Shodan provides detailed information about hosts including
    open ports, services, banners, and vulnerabilities.

    Sample Shodan JSON Format (single host):
    ```json
    {
        "ip_str": "192.168.1.1",
        "hostnames": ["example.com", "www.example.com"],
        "org": "Example Organization",
        "isp": "Example ISP",
        "asn": "AS12345",
        "ports": [22, 80, 443],
        "data": [
            {
                "port": 80,
                "transport": "tcp",
                "product": "Apache",
                "version": "2.4.41",
                "banner": "HTTP/1.1 200 OK..."
            },
            {
                "port": 443,
                "transport": "tcp",
                "product": "Apache",
                "ssl": {
                    "cert": {
                        "subject": {"CN": "example.com"},
                        "issuer": {"CN": "Let's Encrypt"}
                    }
                }
            }
        ],
        "vulns": ["CVE-2021-1234"],
        "location": {
            "city": "San Francisco",
            "country_name": "United States",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    }
    ```

    Data Mapping:
    - ip_str -> ip_address orphan or device entity
    - hostnames -> domain orphans
    - data[].port, product, version -> metadata on IP orphan
    - vulns -> stored in metadata
    - org -> organization entity (optional)

    Usage:
        connector = ShodanConnector(neo4j_handler, orphan_service)
        result = connector.import_data(
            project_id="my-project",
            content=json_content,
            create_device_entities=True  # Create device entities for hosts
        )
    """

    def __init__(
        self,
        neo4j_handler,
        orphan_service=None,
        create_device_entities: bool = False
    ):
        """
        Initialize Shodan connector.

        Args:
            neo4j_handler: Neo4j database handler
            orphan_service: OrphanService instance
            create_device_entities: If True, create Device entities for hosts
        """
        super().__init__(neo4j_handler, orphan_service)
        self.create_device_entities = create_device_entities

    def get_tool_name(self) -> str:
        return "shodan"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse Shodan JSON export.

        Supports single host, array of hosts, or JSONL format.
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        content = content.strip()

        # Try to parse as JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                hosts = data
            else:
                hosts = [data]
        except json.JSONDecodeError:
            # Try JSONL format (one JSON object per line)
            hosts = []
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    try:
                        hosts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Process each host
        for host in hosts:
            yield from self._parse_host(host)

    def _parse_host(self, host: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """Parse a single Shodan host record."""
        ip = host.get("ip_str", "")
        if not ip:
            return

        hostnames = host.get("hostnames", [])
        org = host.get("org", "")
        isp = host.get("isp", "")
        asn = host.get("asn", "")
        ports = host.get("ports", [])
        vulns = host.get("vulns", [])
        location = host.get("location", {})

        # Build service information from data array
        services = []
        for service in host.get("data", []):
            service_info = {
                "port": service.get("port"),
                "transport": service.get("transport", "tcp"),
                "product": service.get("product"),
                "version": service.get("version"),
                "banner": service.get("banner", "")[:500],  # Truncate long banners
            }

            # Extract SSL certificate info
            ssl = service.get("ssl", {})
            if ssl:
                cert = ssl.get("cert", {})
                service_info["ssl_subject"] = cert.get("subject", {}).get("CN")
                service_info["ssl_issuer"] = cert.get("issuer", {}).get("CN")

            services.append(service_info)

        # Build metadata
        metadata = {
            "org": org,
            "isp": isp,
            "asn": asn,
            "ports": ports,
            "services": services,
            "vulns": vulns,
            "location": {
                "city": location.get("city"),
                "country": location.get("country_name"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            } if location else {},
        }

        # Create Device entity or IP orphan
        if self.create_device_entities:
            profile = {
                "core": {
                    "name": [hostnames[0] if hostnames else ip],
                },
                "technical": {
                    "ip_address": [ip],
                    "ports": ports,
                },
                "network": {
                    "org": [org] if org else [],
                    "isp": [isp] if isp else [],
                    "asn": [asn] if asn else [],
                },
            }

            if location:
                profile["location"] = {
                    "city": [location.get("city")] if location.get("city") else [],
                    "country": [location.get("country_name")] if location.get("country_name") else [],
                    "coordinates": [{
                        "latitude": location.get("latitude"),
                        "longitude": location.get("longitude"),
                    }] if location.get("latitude") else [],
                }

            yield {
                "type": "entity",
                "data": {
                    "entity_type": EntityType.DEVICE.value,
                    "profile": profile,
                },
                "relationships": [],
            }
        else:
            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.IP_ADDRESS.value,
                    "identifier_value": ip,
                    "source": "Shodan",
                    "tags": ["shodan", "ip", "host"],
                    "metadata": metadata,
                },
            }

        # Create domain orphans for hostnames
        for hostname in hostnames:
            if hostname:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.DOMAIN.value,
                        "identifier_value": hostname,
                        "source": "Shodan",
                        "tags": ["shodan", "hostname", "domain"],
                        "metadata": {
                            "resolved_ip": ip,
                            "org": org,
                        },
                    },
                }


# =============================================================================
# HAVE I BEEN PWNED CONNECTOR
# =============================================================================

class HIBPConnector(ImportConnector):
    """
    Import connector for Have I Been Pwned (HIBP) breach data.

    HIBP provides information about data breaches and compromised
    accounts. This connector imports breach data and creates orphan
    records for discovered emails.

    Sample HIBP JSON Format (breach check response):
    ```json
    [
        {
            "Name": "Adobe",
            "Title": "Adobe",
            "Domain": "adobe.com",
            "BreachDate": "2013-10-04",
            "AddedDate": "2013-12-04T00:00:00Z",
            "ModifiedDate": "2022-05-15T23:52:49Z",
            "PwnCount": 152445165,
            "Description": "In October 2013...",
            "DataClasses": [
                "Email addresses",
                "Password hints",
                "Passwords",
                "Usernames"
            ],
            "IsVerified": true,
            "IsSensitive": false,
            "IsRetired": false,
            "IsSpamList": false
        }
    ]
    ```

    Sample HIBP paste data format:
    ```json
    [
        {
            "Source": "Pastebin",
            "Id": "AbcD123",
            "Title": "Leaked data",
            "Date": "2023-01-15T10:30:00Z",
            "EmailCount": 500
        }
    ]
    ```

    Custom breach export format (email list with metadata):
    ```json
    {
        "breach_name": "Example Breach 2024",
        "breach_date": "2024-01-15",
        "emails": [
            "user1@example.com",
            "user2@example.com"
        ],
        "metadata": {
            "source": "darkweb",
            "data_types": ["email", "password"]
        }
    }
    ```

    Usage:
        connector = HIBPConnector(neo4j_handler, orphan_service)
        result = connector.import_data(
            project_id="my-project",
            content=json_content
        )
    """

    def get_tool_name(self) -> str:
        return "hibp"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse HIBP JSON data.

        Supports multiple formats:
        - Breach list (from breach endpoint)
        - Paste list (from paste endpoint)
        - Custom email list with breach metadata
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse HIBP JSON: {e}")
            return

        # Detect format and parse accordingly
        if isinstance(data, list):
            # Could be breach list or paste list
            if data and isinstance(data[0], dict):
                if "Name" in data[0] and "BreachDate" in data[0]:
                    # Breach list format
                    yield from self._parse_breaches(data)
                elif "Source" in data[0] and "EmailCount" in data[0]:
                    # Paste list format
                    yield from self._parse_pastes(data)
                else:
                    # Unknown list format - try to extract emails
                    yield from self._parse_generic_list(data)
            elif data and isinstance(data[0], str):
                # Simple email list
                yield from self._parse_email_list(data, {})

        elif isinstance(data, dict):
            # Custom breach export format
            if "emails" in data:
                breach_info = {
                    "breach_name": data.get("breach_name", "Unknown Breach"),
                    "breach_date": data.get("breach_date"),
                    "source": data.get("metadata", {}).get("source", "HIBP"),
                    "data_types": data.get("metadata", {}).get("data_types", []),
                }
                yield from self._parse_email_list(data["emails"], breach_info)

            # Single breach detail
            elif "Name" in data and "DataClasses" in data:
                yield from self._parse_breaches([data])

    def _parse_breaches(
        self,
        breaches: List[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Parse HIBP breach records (metadata only, no emails)."""
        for breach in breaches:
            # Create an orphan record representing the breach itself
            breach_name = breach.get("Name", "Unknown")
            domain = breach.get("Domain", "")

            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.DOMAIN.value,
                    "identifier_value": domain or breach_name,
                    "source": "Have I Been Pwned",
                    "tags": ["hibp", "breach", breach_name.lower()],
                    "notes": breach.get("Description", ""),
                    "metadata": {
                        "breach_name": breach_name,
                        "breach_title": breach.get("Title"),
                        "breach_date": breach.get("BreachDate"),
                        "added_date": breach.get("AddedDate"),
                        "pwn_count": breach.get("PwnCount"),
                        "data_classes": breach.get("DataClasses", []),
                        "is_verified": breach.get("IsVerified"),
                        "is_sensitive": breach.get("IsSensitive"),
                    },
                },
            }

    def _parse_pastes(
        self,
        pastes: List[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Parse HIBP paste records."""
        for paste in pastes:
            source = paste.get("Source", "Unknown")
            paste_id = paste.get("Id", "")

            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.URL.value,
                    "identifier_value": f"{source}:{paste_id}" if paste_id else source,
                    "source": "Have I Been Pwned (Paste)",
                    "tags": ["hibp", "paste", source.lower()],
                    "notes": paste.get("Title", ""),
                    "metadata": {
                        "paste_source": source,
                        "paste_id": paste_id,
                        "paste_title": paste.get("Title"),
                        "paste_date": paste.get("Date"),
                        "email_count": paste.get("EmailCount"),
                    },
                },
            }

    def _parse_email_list(
        self,
        emails: List[str],
        breach_info: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """Parse a list of emails with breach context."""
        for email in emails:
            if not email or not isinstance(email, str):
                continue

            email = email.strip().lower()
            if not email:
                continue

            tags = ["hibp", "breach", "email"]
            if breach_info.get("breach_name"):
                tags.append(breach_info["breach_name"].lower().replace(" ", "_"))

            yield {
                "type": "orphan",
                "data": {
                    "identifier_type": IdentifierType.EMAIL.value,
                    "identifier_value": email,
                    "source": f"HIBP: {breach_info.get('breach_name', 'Unknown')}",
                    "tags": tags,
                    "metadata": {
                        "breach_name": breach_info.get("breach_name"),
                        "breach_date": breach_info.get("breach_date"),
                        "data_types": breach_info.get("data_types", []),
                    },
                },
            }

    def _parse_generic_list(
        self,
        items: List[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Parse generic list format, extracting any identifiable data."""
        for item in items:
            if not isinstance(item, dict):
                continue

            # Look for email fields
            email = (
                item.get("email") or
                item.get("Email") or
                item.get("email_address") or
                item.get("EmailAddress")
            )

            if email:
                yield {
                    "type": "orphan",
                    "data": {
                        "identifier_type": IdentifierType.EMAIL.value,
                        "identifier_value": str(email).strip().lower(),
                        "source": "HIBP",
                        "tags": ["hibp", "email"],
                        "metadata": {k: v for k, v in item.items() if k.lower() != "email"},
                    },
                }


# =============================================================================
# GENERIC CSV CONNECTOR
# =============================================================================

class GenericCSVConnector(ImportConnector):
    """
    Generic CSV import connector with configurable column mapping.

    Supports flexible mapping of CSV columns to entity profile fields
    or orphan data fields. Includes auto-detection of identifier types.

    Column Mapping Format:
    ```python
    mapping = {
        "Name": "entity:profile.core.name",           # Map to entity name
        "Email": "entity:profile.core.email",         # Map to entity email
        "Phone": "orphan:phone",                      # Create phone orphan
        "IP Address": "orphan:ip_address",            # Create IP orphan
        "Notes": "entity:profile.core.notes",         # Map to entity notes
    }
    ```

    Mapping Syntax:
    - "entity:profile.<section>.<field>" - Map to entity profile field
    - "orphan:<identifier_type>" - Create orphan with specified type
    - "orphan:auto" - Create orphan with auto-detected type
    - "meta:<key>" - Add to metadata

    Sample CSV:
    ```csv
    Name,Email,Phone,Company,IP Address,Notes
    John Doe,john@example.com,555-1234,Acme Corp,192.168.1.1,Test user
    Jane Smith,jane@example.com,555-5678,Example Inc,10.0.0.1,Another user
    ```

    Usage:
        connector = GenericCSVConnector(neo4j_handler, orphan_service)
        mapping = {
            "Name": "entity:profile.core.name",
            "Email": "entity:profile.core.email",
            "Phone": "orphan:phone",
            "IP Address": "orphan:ip_address",
        }
        connector.set_mapping(mapping)
        result = connector.import_data(project_id="my-project", content=csv_content)
    """

    def __init__(self, neo4j_handler, orphan_service=None):
        super().__init__(neo4j_handler, orphan_service)
        self._column_mapping: Dict[str, str] = {}
        self._entity_type: EntityType = EntityType.PERSON
        self._create_entity_per_row: bool = True
        self._primary_key_column: Optional[str] = None

    def set_mapping(self, mapping: Dict[str, str]) -> None:
        """
        Set the column mapping configuration.

        Args:
            mapping: Dictionary mapping CSV column names to target paths
        """
        self._column_mapping = mapping

    def set_entity_type(self, entity_type: EntityType) -> None:
        """Set the entity type for created entities."""
        self._entity_type = entity_type

    def set_create_entity_per_row(self, create: bool) -> None:
        """
        Set whether to create an entity for each row.

        If False, only orphan data will be created.
        """
        self._create_entity_per_row = create

    def set_primary_key_column(self, column: Optional[str]) -> None:
        """
        Set the primary key column for deduplication.

        Rows with the same primary key value will be merged.
        """
        self._primary_key_column = column

    def get_tool_name(self) -> str:
        return "generic_csv"

    def parse(self, content: Union[str, bytes]) -> Generator[Dict[str, Any], None, None]:
        """
        Parse CSV content using configured mapping.
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        reader = csv.DictReader(io.StringIO(content))

        # Track entities by primary key for deduplication
        entities: Dict[str, Dict[str, Any]] = {}

        for row in reader:
            # Determine primary key for this row
            pk = None
            if self._primary_key_column and self._primary_key_column in row:
                pk = row[self._primary_key_column]

            # Initialize entity profile if creating entities
            entity_profile: Dict[str, Dict[str, Any]] = {}
            orphan_records: List[Dict[str, Any]] = []

            # Process each mapped column
            for csv_column, target in self._column_mapping.items():
                value = row.get(csv_column, "")
                if not value or not value.strip():
                    continue

                value = value.strip()

                if target.startswith("entity:"):
                    # Map to entity profile
                    path = target[7:]  # Remove "entity:" prefix
                    self._set_profile_value(entity_profile, path, value)

                elif target.startswith("orphan:"):
                    # Create orphan data
                    orphan_type = target[7:]  # Remove "orphan:" prefix

                    if orphan_type == "auto":
                        identifier_type = self._detect_identifier_type(value)
                    else:
                        try:
                            identifier_type = IdentifierType(orphan_type)
                        except ValueError:
                            identifier_type = IdentifierType.OTHER

                    orphan_records.append({
                        "identifier_type": identifier_type.value,
                        "identifier_value": value,
                        "source": "CSV Import",
                        "tags": ["csv_import"],
                        "metadata": {"csv_column": csv_column},
                    })

                elif target.startswith("meta:"):
                    # Add to metadata (for orphans)
                    meta_key = target[5:]
                    # Store in a temporary location
                    for orphan in orphan_records:
                        orphan.setdefault("metadata", {})[meta_key] = value

            # Yield entity if creating entities
            if self._create_entity_per_row and entity_profile:
                if pk and pk in entities:
                    # Merge with existing entity
                    self._merge_profiles(entities[pk]["profile"], entity_profile)
                else:
                    entity_data = {
                        "entity_type": self._entity_type.value,
                        "profile": entity_profile,
                    }

                    if pk:
                        entities[pk] = entity_data
                    else:
                        yield {
                            "type": "entity",
                            "data": entity_data,
                            "relationships": [],
                        }

            # Yield orphan records
            for orphan_data in orphan_records:
                yield {
                    "type": "orphan",
                    "data": orphan_data,
                }

        # Yield deduplicated entities
        for entity_data in entities.values():
            yield {
                "type": "entity",
                "data": entity_data,
                "relationships": [],
            }

    def _set_profile_value(
        self,
        profile: Dict[str, Any],
        path: str,
        value: str
    ) -> None:
        """Set a value in the profile at the given dot-notation path."""
        # Expected format: "profile.<section>.<field>"
        parts = path.split(".")

        if len(parts) < 2:
            return

        # Skip "profile" prefix if present
        if parts[0] == "profile":
            parts = parts[1:]

        if len(parts) < 2:
            return

        section = parts[0]
        field = ".".join(parts[1:])

        # Initialize section if needed
        if section not in profile:
            profile[section] = {}

        # Add value to field (as list for multi-value support)
        if field not in profile[section]:
            profile[section][field] = []

        # Handle name field specially
        if field == "name":
            name_parts = value.split()
            profile[section][field].append({
                "first_name": name_parts[0] if name_parts else value,
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            })
        else:
            profile[section][field].append(value)

    def _merge_profiles(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any]
    ) -> None:
        """Merge source profile into target profile."""
        for section, fields in source.items():
            if section not in target:
                target[section] = {}

            for field, values in fields.items():
                if field not in target[section]:
                    target[section][field] = []

                # Add new values
                existing = target[section][field]
                for val in values:
                    if val not in existing:
                        existing.append(val)


# =============================================================================
# DATA IMPORT SERVICE
# =============================================================================

class DataImportService:
    """
    Central service for importing data from OSINT tools.

    Provides a unified interface for all import connectors and
    handles common functionality like project validation and
    result aggregation.

    Usage:
        service = DataImportService(neo4j_handler, orphan_service)

        # Import from specific tools
        result = service.import_maltego(project_id, content)
        result = service.import_spiderfoot(project_id, content)
        result = service.import_shodan(project_id, content)

        # Use generic CSV import
        result = service.import_csv(
            project_id,
            content,
            mapping={
                "Email": "orphan:email",
                "Name": "entity:profile.core.name",
            }
        )

        # Get available connectors
        connectors = service.get_available_connectors()
    """

    def __init__(self, neo4j_handler, orphan_service=None):
        """
        Initialize the data import service.

        Args:
            neo4j_handler: Neo4j database handler
            orphan_service: Optional OrphanService for orphan data creation
        """
        self.neo4j = neo4j_handler
        self.orphan_service = orphan_service

        # Initialize connectors
        self._connectors: Dict[str, Type[ImportConnector]] = {
            "maltego": MaltegoConnector,
            "spiderfoot": SpiderFootConnector,
            "theharvester": TheHarvesterConnector,
            "shodan": ShodanConnector,
            "hibp": HIBPConnector,
            "generic_csv": GenericCSVConnector,
        }

    def get_available_connectors(self) -> List[str]:
        """Get list of available connector names."""
        return list(self._connectors.keys())

    def get_connector(self, name: str) -> Optional[ImportConnector]:
        """
        Get an instantiated connector by name.

        Args:
            name: Connector name (maltego, spiderfoot, etc.)

        Returns:
            Instantiated connector or None if not found
        """
        connector_class = self._connectors.get(name.lower())
        if connector_class:
            return connector_class(self.neo4j, self.orphan_service)
        return None

    def import_maltego(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False
    ) -> ImportResult:
        """
        Import data from Maltego CSV export.

        Args:
            project_id: Target project ID
            content: Maltego CSV content
            dry_run: If True, validate without importing

        Returns:
            ImportResult with statistics
        """
        connector = MaltegoConnector(self.neo4j, self.orphan_service)
        return connector.import_data(project_id, content, dry_run)

    def import_spiderfoot(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False
    ) -> ImportResult:
        """
        Import data from SpiderFoot JSON scan results.

        Args:
            project_id: Target project ID
            content: SpiderFoot JSON content
            dry_run: If True, validate without importing

        Returns:
            ImportResult with statistics
        """
        connector = SpiderFootConnector(self.neo4j, self.orphan_service)
        return connector.import_data(project_id, content, dry_run)

    def import_theharvester(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False
    ) -> ImportResult:
        """
        Import data from TheHarvester JSON/XML output.

        Args:
            project_id: Target project ID
            content: TheHarvester JSON or XML content
            dry_run: If True, validate without importing

        Returns:
            ImportResult with statistics
        """
        connector = TheHarvesterConnector(self.neo4j, self.orphan_service)
        return connector.import_data(project_id, content, dry_run)

    def import_shodan(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False,
        create_device_entities: bool = False
    ) -> ImportResult:
        """
        Import data from Shodan JSON host export.

        Args:
            project_id: Target project ID
            content: Shodan JSON content
            dry_run: If True, validate without importing
            create_device_entities: If True, create Device entities for hosts

        Returns:
            ImportResult with statistics
        """
        connector = ShodanConnector(
            self.neo4j,
            self.orphan_service,
            create_device_entities=create_device_entities
        )
        return connector.import_data(project_id, content, dry_run)

    def import_hibp(
        self,
        project_id: str,
        content: Union[str, bytes],
        dry_run: bool = False
    ) -> ImportResult:
        """
        Import data from Have I Been Pwned breach export.

        Args:
            project_id: Target project ID
            content: HIBP JSON content
            dry_run: If True, validate without importing

        Returns:
            ImportResult with statistics
        """
        connector = HIBPConnector(self.neo4j, self.orphan_service)
        return connector.import_data(project_id, content, dry_run)

    def import_csv(
        self,
        project_id: str,
        content: Union[str, bytes],
        mapping: Dict[str, str],
        entity_type: EntityType = EntityType.PERSON,
        create_entities: bool = True,
        dry_run: bool = False
    ) -> ImportResult:
        """
        Import data from generic CSV with custom mapping.

        Args:
            project_id: Target project ID
            content: CSV content
            mapping: Column mapping configuration
            entity_type: Entity type for created entities
            create_entities: Whether to create entities
            dry_run: If True, validate without importing

        Returns:
            ImportResult with statistics
        """
        connector = GenericCSVConnector(self.neo4j, self.orphan_service)
        connector.set_mapping(mapping)
        connector.set_entity_type(entity_type)
        connector.set_create_entity_per_row(create_entities)
        return connector.import_data(
            project_id,
            content,
            dry_run,
            create_entities=create_entities
        )

    def auto_detect_format(self, content: Union[str, bytes]) -> Optional[str]:
        """
        Auto-detect the import format from content.

        Args:
            content: File content to analyze

        Returns:
            Connector name or None if format not detected
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')

        content = content.strip()

        # Check for JSON
        if content.startswith('{') or content.startswith('['):
            try:
                data = json.loads(content)

                # SpiderFoot signatures
                if isinstance(data, dict):
                    if "scan_name" in data or "scans" in data:
                        return "spiderfoot"

                    # TheHarvester signatures
                    if any(k in data for k in ["emails", "hosts", "ips"]):
                        return "theharvester"

                    # Shodan signatures
                    if "ip_str" in data or "data" in data:
                        return "shodan"

                    # HIBP signatures
                    if "Name" in data and "DataClasses" in data:
                        return "hibp"
                    if "breach_name" in data or "emails" in data:
                        return "hibp"

                elif isinstance(data, list) and data:
                    first = data[0]
                    if isinstance(first, dict):
                        # SpiderFoot array format
                        if "type" in first and "module" in first:
                            return "spiderfoot"

                        # Shodan array format
                        if "ip_str" in first:
                            return "shodan"

                        # HIBP breach list
                        if "Name" in first and "BreachDate" in first:
                            return "hibp"

            except json.JSONDecodeError:
                pass

        # Check for XML (TheHarvester)
        if content.startswith('<'):
            if '<theHarvester' in content or '<email>' in content:
                return "theharvester"

        # Check for CSV (Maltego or generic)
        if ',' in content.split('\n')[0]:
            first_line = content.split('\n')[0].lower()
            if any(x in first_line for x in ["entity type", "maltego", "entity value"]):
                return "maltego"
            return "generic_csv"

        return None


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

_import_service: Optional[DataImportService] = None


def get_import_service(neo4j_handler, orphan_service=None) -> DataImportService:
    """
    Get or create the DataImportService instance.

    Args:
        neo4j_handler: Neo4j database handler
        orphan_service: Optional OrphanService for orphan data creation

    Returns:
        DataImportService instance
    """
    global _import_service
    if _import_service is None:
        _import_service = DataImportService(neo4j_handler, orphan_service)
    return _import_service


def reset_import_service() -> None:
    """Reset the global import service (useful for testing)."""
    global _import_service
    _import_service = None
