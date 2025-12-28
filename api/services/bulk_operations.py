"""
Bulk Operations Service for Basset Hound.

Provides batch import and export functionality for entities,
supporting JSON, CSV, and JSONL formats.

Phase 12 Enhancements:
- Streaming/pagination support for large exports
- Generator-based approach for memory efficiency
- Configurable batch sizes
"""

import csv
import json
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union
from uuid import uuid4


# Default batch size for streaming exports
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 10000


@dataclass
class BulkImportResult:
    """Result of a bulk import operation."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    errors: List[dict] = field(default_factory=list)
    created_ids: List[str] = field(default_factory=list)

    def add_success(self, entity_id: str) -> None:
        """Record a successful import."""
        self.successful += 1
        self.created_ids.append(entity_id)

    def add_error(self, index: int, message: str) -> None:
        """Record a failed import with error details."""
        self.failed += 1
        self.errors.append({
            "index": index,
            "error": message
        })

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "errors": self.errors,
            "created_ids": self.created_ids
        }


@dataclass
class BulkExportOptions:
    """Options for bulk export operations."""
    format: str = "json"  # "json", "csv", "jsonl"
    include_relationships: bool = True
    include_files: bool = False
    entity_ids: Optional[List[str]] = None  # None = all entities
    # Pagination parameters
    offset: int = 0
    limit: Optional[int] = None  # None = no limit
    batch_size: int = DEFAULT_BATCH_SIZE

    def __post_init__(self):
        """Validate export format and pagination parameters."""
        valid_formats = {"json", "csv", "jsonl"}
        if self.format not in valid_formats:
            raise ValueError(
                f"Invalid format '{self.format}'. Must be one of: {', '.join(valid_formats)}"
            )

        # Validate pagination parameters
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.limit is not None and self.limit < 0:
            raise ValueError("limit must be non-negative")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if self.batch_size > MAX_BATCH_SIZE:
            raise ValueError(f"batch_size must not exceed {MAX_BATCH_SIZE}")


@dataclass
class StreamingExportBatch:
    """Represents a batch of entities in a streaming export."""
    entities: List[dict]
    batch_number: int
    total_batches: Optional[int]
    offset: int
    has_more: bool

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "entities": self.entities,
            "batch_number": self.batch_number,
            "total_batches": self.total_batches,
            "offset": self.offset,
            "has_more": self.has_more,
            "count": len(self.entities)
        }


class BulkOperationsService:
    """
    Service for bulk import and export operations on entities.

    Supports batch processing of entities with validation,
    error handling, and multiple export formats.
    """

    def __init__(self, neo4j_handler):
        """
        Initialize the bulk operations service.

        Args:
            neo4j_handler: The Neo4j handler for database operations.
        """
        self.neo4j_handler = neo4j_handler

    def import_entities(
        self,
        project_id: str,
        entities: List[dict],
        update_existing: bool = False
    ) -> BulkImportResult:
        """
        Batch import entities into a project.

        Args:
            project_id: The project safe name to import into.
            entities: List of entity dictionaries to import.
            update_existing: If True, update existing entities; otherwise skip them.

        Returns:
            BulkImportResult with import statistics and any errors.
        """
        result = BulkImportResult(total=len(entities))

        # Verify project exists
        project = self.neo4j_handler.get_project(project_id)
        if not project:
            result.add_error(-1, f"Project '{project_id}' not found")
            return result

        for index, entity_data in enumerate(entities):
            try:
                # Check if entity has an ID and already exists
                entity_id = entity_data.get("id")

                if entity_id:
                    existing = self.neo4j_handler.get_person(project_id, entity_id)
                    if existing:
                        if update_existing:
                            # Update existing entity
                            updated = self.neo4j_handler.update_person(
                                project_id,
                                entity_id,
                                entity_data
                            )
                            if updated:
                                result.add_success(entity_id)
                            else:
                                result.add_error(index, f"Failed to update entity '{entity_id}'")
                        else:
                            result.add_error(index, f"Entity '{entity_id}' already exists")
                        continue

                # Create new entity
                # Ensure profile exists
                if "profile" not in entity_data:
                    entity_data["profile"] = {}

                # Generate ID if not provided
                if not entity_id:
                    entity_data["id"] = str(uuid4())

                # Set created_at if not provided
                if "created_at" not in entity_data:
                    entity_data["created_at"] = datetime.now().isoformat()

                created = self.neo4j_handler.create_person(project_id, entity_data)
                if created:
                    result.add_success(created.get("id", entity_data.get("id")))
                else:
                    result.add_error(index, "Failed to create entity")

            except Exception as e:
                result.add_error(index, str(e))

        return result

    def export_entities(
        self,
        project_id: str,
        options: BulkExportOptions
    ) -> Union[str, bytes]:
        """
        Export entities from a project in the specified format.

        Args:
            project_id: The project safe name to export from.
            options: Export options including format and filters.

        Returns:
            Exported data as string (JSON/CSV/JSONL) or bytes.

        Raises:
            ValueError: If project not found or invalid options.
        """
        # Verify project exists
        project = self.neo4j_handler.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        # Get entities
        if options.entity_ids:
            entities = []
            for entity_id in options.entity_ids:
                entity = self.neo4j_handler.get_person(project_id, entity_id)
                if entity:
                    entities.append(entity)
        else:
            entities = self.neo4j_handler.get_all_people(project_id) or []

        # Process entities based on options
        processed_entities = []
        for entity in entities:
            processed = self._process_entity_for_export(entity, options)
            processed_entities.append(processed)

        # Apply pagination if specified
        if options.offset > 0:
            processed_entities = processed_entities[options.offset:]
        if options.limit is not None:
            processed_entities = processed_entities[:options.limit]

        # Format output
        if options.format == "json":
            return json.dumps(processed_entities, indent=2, default=str)
        elif options.format == "jsonl":
            return self._to_jsonl(processed_entities)
        elif options.format == "csv":
            return self._to_csv(processed_entities)
        else:
            raise ValueError(f"Unsupported format: {options.format}")

    def export_entities_streaming(
        self,
        project_id: str,
        options: BulkExportOptions
    ) -> Generator[StreamingExportBatch, None, None]:
        """
        Stream export entities from a project in batches.

        This is a memory-efficient alternative to export_entities() for large datasets.
        Yields batches of entities rather than loading all at once.

        Args:
            project_id: The project safe name to export from.
            options: Export options including format, filters, and batch_size.

        Yields:
            StreamingExportBatch objects containing entity batches.

        Raises:
            ValueError: If project not found or invalid options.
        """
        # Verify project exists
        project = self.neo4j_handler.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        # Get entity iterator
        entity_iterator = self._get_entity_iterator(project_id, options)

        # Apply offset by consuming entities
        for _ in range(options.offset):
            try:
                next(entity_iterator)
            except StopIteration:
                # Offset exceeds total entities, yield empty batch
                yield StreamingExportBatch(
                    entities=[],
                    batch_number=0,
                    total_batches=0,
                    offset=options.offset,
                    has_more=False
                )
                return

        # Calculate total for pagination info (if possible)
        total_count = self._get_entity_count(project_id, options)
        effective_total = max(0, total_count - options.offset)
        if options.limit is not None:
            effective_total = min(effective_total, options.limit)

        total_batches = (effective_total + options.batch_size - 1) // options.batch_size if effective_total > 0 else 0

        batch_number = 0
        entities_yielded = 0
        limit = options.limit

        while True:
            batch = []
            remaining_in_limit = None
            if limit is not None:
                remaining_in_limit = limit - entities_yielded
                if remaining_in_limit <= 0:
                    break

            batch_limit = options.batch_size
            if remaining_in_limit is not None:
                batch_limit = min(batch_limit, remaining_in_limit)

            for _ in range(batch_limit):
                try:
                    entity = next(entity_iterator)
                    processed = self._process_entity_for_export(entity, options)
                    batch.append(processed)
                except StopIteration:
                    break

            if not batch:
                break

            entities_yielded += len(batch)
            has_more = (
                (limit is None and len(batch) == options.batch_size) or
                (limit is not None and entities_yielded < limit and len(batch) == batch_limit)
            )

            # Check if there are actually more entities
            if has_more:
                try:
                    # Peek ahead to see if there are more
                    peek_entity = next(entity_iterator)
                    # Put it back by recreating iterator state
                    entity_iterator = self._chain_entity(peek_entity, entity_iterator)
                except StopIteration:
                    has_more = False

            yield StreamingExportBatch(
                entities=batch,
                batch_number=batch_number,
                total_batches=total_batches if total_batches > 0 else None,
                offset=options.offset + entities_yielded - len(batch),
                has_more=has_more
            )

            batch_number += 1

            if not has_more:
                break

    def stream_jsonl_export(
        self,
        project_id: str,
        options: Optional[BulkExportOptions] = None
    ) -> Generator[str, None, None]:
        """
        Stream entities as JSONL (one JSON object per line).

        Memory-efficient generator for exporting large datasets as JSONL.
        Each yield produces one line of the JSONL output.

        Args:
            project_id: The project safe name to export from.
            options: Optional export options. Uses defaults if not provided.

        Yields:
            Individual JSON lines (entities serialized as JSON strings).

        Raises:
            ValueError: If project not found.
        """
        if options is None:
            options = BulkExportOptions(format="jsonl")
        else:
            # Ensure format is jsonl
            options = BulkExportOptions(
                format="jsonl",
                include_relationships=options.include_relationships,
                include_files=options.include_files,
                entity_ids=options.entity_ids,
                offset=options.offset,
                limit=options.limit,
                batch_size=options.batch_size
            )

        for batch in self.export_entities_streaming(project_id, options):
            for entity in batch.entities:
                yield json.dumps(entity, default=str)

    def stream_csv_export(
        self,
        project_id: str,
        options: Optional[BulkExportOptions] = None,
        fields: Optional[List[str]] = None
    ) -> Generator[str, None, None]:
        """
        Stream entities as CSV rows.

        Memory-efficient generator for exporting large datasets as CSV.
        First yield is the header row, subsequent yields are data rows.

        Args:
            project_id: The project safe name to export from.
            options: Optional export options. Uses defaults if not provided.
            fields: Optional list of field paths to include. If None,
                   automatically determines fields from first batch.

        Yields:
            CSV rows as strings (including newline characters).

        Raises:
            ValueError: If project not found.
        """
        if options is None:
            options = BulkExportOptions(format="csv")
        else:
            options = BulkExportOptions(
                format="csv",
                include_relationships=options.include_relationships,
                include_files=options.include_files,
                entity_ids=options.entity_ids,
                offset=options.offset,
                limit=options.limit,
                batch_size=options.batch_size
            )

        header_written = False
        field_names: Optional[List[str]] = fields

        for batch in self.export_entities_streaming(project_id, options):
            if not batch.entities:
                continue

            # Flatten entities for CSV
            flattened_batch = [self._flatten_entity(e) for e in batch.entities]

            # Determine fields from first batch if not specified
            if field_names is None:
                all_fields = set()
                for flat_entity in flattened_batch:
                    all_fields.update(flat_entity.keys())
                field_names = sorted(all_fields)

            # Write header on first batch
            if not header_written:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=field_names)
                writer.writeheader()
                yield output.getvalue()
                header_written = True

            # Write data rows
            for flat_entity in flattened_batch:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=field_names)
                row = {field: flat_entity.get(field, "") for field in field_names}
                writer.writerow(row)
                yield output.getvalue()

    def get_export_count(
        self,
        project_id: str,
        options: Optional[BulkExportOptions] = None
    ) -> int:
        """
        Get the count of entities that would be exported.

        Useful for progress tracking and pagination calculations.

        Args:
            project_id: The project safe name to count from.
            options: Optional export options for filtering.

        Returns:
            Count of entities that match the export criteria.

        Raises:
            ValueError: If project not found.
        """
        if options is None:
            options = BulkExportOptions()

        total = self._get_entity_count(project_id, options)

        # Apply pagination
        effective = max(0, total - options.offset)
        if options.limit is not None:
            effective = min(effective, options.limit)

        return effective

    def validate_import_data(self, entities: List[dict]) -> List[dict]:
        """
        Validate entity data before import.

        Args:
            entities: List of entity dictionaries to validate.

        Returns:
            List of validation errors (empty if all valid).
        """
        errors = []

        for index, entity in enumerate(entities):
            entity_errors = self._validate_entity(entity, index)
            errors.extend(entity_errors)

        return errors

    def import_from_csv(
        self,
        project_id: str,
        csv_content: str,
        mapping: dict
    ) -> BulkImportResult:
        """
        Import entities from CSV content with field mapping.

        Args:
            project_id: The project safe name to import into.
            csv_content: CSV content as string.
            mapping: Dictionary mapping CSV columns to entity fields.
                     Format: {"csv_column": "profile.section.field"}

        Returns:
            BulkImportResult with import statistics and any errors.
        """
        result = BulkImportResult()

        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_content))
            entities = []

            for row in reader:
                entity = self._map_csv_row_to_entity(row, mapping)
                entities.append(entity)

            result.total = len(entities)

            # Use standard import
            import_result = self.import_entities(project_id, entities)
            return import_result

        except csv.Error as e:
            result.add_error(-1, f"CSV parsing error: {str(e)}")
            return result
        except Exception as e:
            result.add_error(-1, f"Import error: {str(e)}")
            return result

    def export_to_csv(
        self,
        project_id: str,
        fields: List[str]
    ) -> str:
        """
        Export specific entity fields to CSV format.

        Args:
            project_id: The project safe name to export from.
            fields: List of field paths to export (e.g., ["id", "profile.core.name"]).

        Returns:
            CSV content as string.

        Raises:
            ValueError: If project not found.
        """
        # Verify project exists
        project = self.neo4j_handler.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        # Get all entities
        entities = self.neo4j_handler.get_all_people(project_id) or []

        # Build CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for entity in entities:
            row = {}
            for field_path in fields:
                value = self._get_nested_value(entity, field_path)
                # Convert complex values to JSON strings
                if isinstance(value, (dict, list)):
                    row[field_path] = json.dumps(value, default=str)
                else:
                    row[field_path] = value if value is not None else ""
            writer.writerow(row)

        return output.getvalue()

    # ----- Private Helper Methods -----

    def _get_entity_iterator(
        self,
        project_id: str,
        options: BulkExportOptions
    ) -> Iterator[dict]:
        """
        Get an iterator over entities for streaming export.

        Uses database-level pagination to avoid loading all entities into memory.

        Args:
            project_id: The project safe name.
            options: Export options with entity_ids filter.

        Returns:
            Iterator over entity dictionaries.
        """
        if options.entity_ids:
            # Iterate over specific entity IDs using batch query for efficiency
            def entity_id_iterator() -> Iterator[dict]:
                # Fetch in batches for efficiency
                batch_size = min(options.batch_size, 100)
                entity_ids = list(options.entity_ids)
                for i in range(0, len(entity_ids), batch_size):
                    batch_ids = entity_ids[i:i + batch_size]
                    entities_map = self.neo4j_handler.get_people_batch(project_id, batch_ids)
                    # Yield in order of requested IDs
                    for eid in batch_ids:
                        if eid in entities_map:
                            yield entities_map[eid]
            return entity_id_iterator()
        else:
            # Use database-level pagination for memory efficiency
            def paginated_iterator() -> Iterator[dict]:
                page_size = options.batch_size
                offset = 0
                while True:
                    batch = self.neo4j_handler.get_all_people_paginated(
                        project_id, offset=offset, limit=page_size
                    )
                    if not batch:
                        break
                    for entity in batch:
                        yield entity
                    if len(batch) < page_size:
                        break
                    offset += page_size
            return paginated_iterator()

    def _get_entity_count(
        self,
        project_id: str,
        options: BulkExportOptions
    ) -> int:
        """
        Get the total count of entities matching the options.

        Uses database-level count query for efficiency.

        Args:
            project_id: The project safe name.
            options: Export options with entity_ids filter.

        Returns:
            Count of matching entities.
        """
        if options.entity_ids:
            # Count specific entity IDs that exist using batch query
            entities_map = self.neo4j_handler.get_people_batch(
                project_id, options.entity_ids
            )
            return len(entities_map)
        else:
            # Use efficient count query
            return self.neo4j_handler.get_people_count(project_id)

    def _chain_entity(
        self,
        first_entity: dict,
        remaining_iterator: Iterator[dict]
    ) -> Iterator[dict]:
        """
        Chain a single entity with an iterator.

        Used for "peeking" at the next entity and then putting it back.

        Args:
            first_entity: The entity to yield first.
            remaining_iterator: The iterator to continue with.

        Returns:
            Iterator that yields first_entity, then remaining entities.
        """
        yield first_entity
        yield from remaining_iterator

    def _process_entity_for_export(
        self,
        entity: dict,
        options: BulkExportOptions
    ) -> dict:
        """Process an entity according to export options."""
        processed = dict(entity)

        # Remove relationships if not requested
        if not options.include_relationships:
            profile = processed.get("profile", {})
            if "Tagged People" in profile:
                del profile["Tagged People"]

        # Remove file references if not requested
        if not options.include_files:
            processed = self._remove_file_references(processed)

        return processed

    def _remove_file_references(self, entity: dict) -> dict:
        """Remove file references from entity data."""
        processed = dict(entity)
        profile = processed.get("profile", {})

        for section_id, section_data in profile.items():
            if isinstance(section_data, dict):
                for field_id, field_value in list(section_data.items()):
                    if self._is_file_reference(field_value):
                        del section_data[field_id]

        return processed

    def _is_file_reference(self, value: Any) -> bool:
        """Check if a value is a file reference."""
        if isinstance(value, dict) and "path" in value:
            return True
        if isinstance(value, list) and value:
            if isinstance(value[0], dict) and "path" in value[0]:
                return True
        return False

    def _to_jsonl(self, entities: List[dict]) -> str:
        """Convert entities to JSONL format."""
        lines = []
        for entity in entities:
            lines.append(json.dumps(entity, default=str))
        return "\n".join(lines)

    def _to_csv(self, entities: List[dict]) -> str:
        """Convert entities to CSV format with flattened structure."""
        if not entities:
            return ""

        # Collect all possible fields from all entities
        all_fields = set()
        flattened_entities = []

        for entity in entities:
            flat = self._flatten_entity(entity)
            flattened_entities.append(flat)
            all_fields.update(flat.keys())

        # Sort fields for consistent output
        sorted_fields = sorted(all_fields)

        # Write CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted_fields)
        writer.writeheader()

        for flat_entity in flattened_entities:
            # Ensure all fields exist (empty if missing)
            row = {field: flat_entity.get(field, "") for field in sorted_fields}
            writer.writerow(row)

        return output.getvalue()

    def _flatten_entity(self, entity: dict, prefix: str = "") -> dict:
        """Flatten nested entity structure for CSV export."""
        flat = {}

        for key, value in entity.items():
            full_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dicts
                nested = self._flatten_entity(value, f"{full_key}.")
                flat.update(nested)
            elif isinstance(value, list):
                # Convert lists to JSON strings
                flat[full_key] = json.dumps(value, default=str)
            else:
                flat[full_key] = value if value is not None else ""

        return flat

    def _validate_entity(self, entity: dict, index: int) -> List[dict]:
        """Validate a single entity and return any errors."""
        errors = []

        # Check that entity is a dictionary
        if not isinstance(entity, dict):
            errors.append({
                "index": index,
                "error": "Entity must be a dictionary"
            })
            return errors

        # Check for required profile structure if profile exists
        profile = entity.get("profile")
        if profile is not None and not isinstance(profile, dict):
            errors.append({
                "index": index,
                "error": "Profile must be a dictionary"
            })

        # Validate ID format if provided
        entity_id = entity.get("id")
        if entity_id is not None and not isinstance(entity_id, str):
            errors.append({
                "index": index,
                "error": "Entity ID must be a string"
            })

        # Validate created_at format if provided
        created_at = entity.get("created_at")
        if created_at is not None:
            if not isinstance(created_at, str):
                errors.append({
                    "index": index,
                    "error": "created_at must be an ISO 8601 string"
                })
            else:
                try:
                    datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    errors.append({
                        "index": index,
                        "error": "created_at must be a valid ISO 8601 datetime"
                    })

        return errors

    def _map_csv_row_to_entity(self, row: dict, mapping: dict) -> dict:
        """
        Map a CSV row to entity structure using the provided mapping.

        Args:
            row: CSV row as dictionary.
            mapping: Mapping of CSV columns to entity field paths.

        Returns:
            Entity dictionary.
        """
        entity = {"profile": {}}

        for csv_column, field_path in mapping.items():
            if csv_column not in row:
                continue

            value = row[csv_column]
            if not value:  # Skip empty values
                continue

            # Try to parse JSON values
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

            # Set value at the specified path
            self._set_nested_value(entity, field_path, value)

        return entity

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """
        Get a value from nested dictionaries using dot notation.

        Args:
            data: The dictionary to search.
            path: Dot-separated path (e.g., "profile.core.name").

        Returns:
            The value at the path, or None if not found.
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _set_nested_value(self, data: dict, path: str, value: Any) -> None:
        """
        Set a value in nested dictionaries using dot notation.

        Args:
            data: The dictionary to modify.
            path: Dot-separated path (e.g., "profile.core.name").
            value: The value to set.
        """
        keys = path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
