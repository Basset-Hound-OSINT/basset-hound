"""
Bulk Operations Service for Basset Hound.

Provides batch import and export functionality for entities,
supporting JSON, CSV, and JSONL formats.
"""

import csv
import json
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4


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

    def __post_init__(self):
        """Validate export format."""
        valid_formats = {"json", "csv", "jsonl"}
        if self.format not in valid_formats:
            raise ValueError(
                f"Invalid format '{self.format}'. Must be one of: {', '.join(valid_formats)}"
            )


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

        # Format output
        if options.format == "json":
            return json.dumps(processed_entities, indent=2, default=str)
        elif options.format == "jsonl":
            return self._to_jsonl(processed_entities)
        elif options.format == "csv":
            return self._to_csv(processed_entities)
        else:
            raise ValueError(f"Unsupported format: {options.format}")

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
