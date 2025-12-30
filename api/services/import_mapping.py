"""
Custom Import Mapping Service for Basset Hound Platform.

This service allows users to define custom field mappings for importing data
from any format. It supports various transformations including case conversion,
regex extraction, splitting/joining, default values, and template-based mapping.

Features:
- Flexible field mapping with named configurations
- Multiple transformation types (DIRECT, LOWERCASE, UPPERCASE, TRIM, etc.)
- Chained transformations for complex data processing
- In-memory storage with optional JSON file persistence
- Validation and preview capabilities
- Singleton pattern for global access

Usage:
    from api.services.import_mapping import (
        get_import_mapping_service,
        ImportMappingConfig,
        FieldMapping,
        TransformationType,
    )

    # Get the service
    service = get_import_mapping_service()

    # Create a mapping configuration
    config = ImportMappingConfig(
        name="my_csv_mapping",
        description="Mapping for vendor CSV exports",
        field_mappings=[
            FieldMapping(
                source_field="FULL_NAME",
                destination_field="name",
                transformations=[TransformationType.TRIM, TransformationType.UPPERCASE],
            ),
            FieldMapping(
                source_field="EMAIL_ADDR",
                destination_field="email",
                transformations=[TransformationType.LOWERCASE, TransformationType.TRIM],
            ),
        ],
    )

    # Create and apply the mapping
    mapping = service.create_mapping(config)
    result = service.apply_mapping(data, mapping.id)
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


logger = logging.getLogger("basset_hound.import_mapping")


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class TransformationType(str, Enum):
    """
    Enumeration of available transformation types for field mapping.

    Each transformation type defines how source field values are processed
    before being assigned to the destination field.
    """

    # Basic transformations
    DIRECT = "direct"
    """Copy value as-is without any transformation."""

    LOWERCASE = "lowercase"
    """Convert string value to lowercase."""

    UPPERCASE = "uppercase"
    """Convert string value to uppercase."""

    TRIM = "trim"
    """Remove leading and trailing whitespace."""

    # String manipulation
    REGEX_EXTRACT = "regex_extract"
    """Extract value using a regex pattern. Requires 'pattern' in options."""

    SPLIT = "split"
    """Split string into array. Requires 'delimiter' in options (default: ',')."""

    JOIN = "join"
    """Join array into string. Requires 'delimiter' in options (default: ', ')."""

    # Value handling
    DEFAULT = "default"
    """Use default value if source is empty. Requires 'default_value' in options."""

    TEMPLATE = "template"
    """
    Apply string template with placeholders. Requires 'template' in options.
    Template can use {value} for source value and {field_name} for other fields.
    Example: "{first_name} {last_name}" or "Email: {value}"
    """

    # Additional transformations
    STRIP_HTML = "strip_html"
    """Remove HTML tags from the value."""

    NORMALIZE_WHITESPACE = "normalize_whitespace"
    """Replace multiple whitespace characters with single space."""

    TRUNCATE = "truncate"
    """Truncate string to max length. Requires 'max_length' in options."""

    PREFIX = "prefix"
    """Add prefix to value. Requires 'prefix' in options."""

    SUFFIX = "suffix"
    """Add suffix to value. Requires 'suffix' in options."""

    REPLACE = "replace"
    """Replace substring. Requires 'find' and 'replace' in options."""

    REGEX_REPLACE = "regex_replace"
    """Replace using regex. Requires 'pattern' and 'replacement' in options."""

    TITLECASE = "titlecase"
    """Convert string to title case (capitalize each word)."""

    CAPITALIZE = "capitalize"
    """Capitalize first character only."""


# =============================================================================
# PYDANTIC-STYLE MODELS (using dataclasses for compatibility)
# =============================================================================

@dataclass
class TransformationOptions:
    """
    Configuration options for transformations.

    Different transformation types require different options:
    - REGEX_EXTRACT: pattern (str) - regex pattern with capturing group
    - SPLIT: delimiter (str) - character(s) to split on (default: ',')
    - JOIN: delimiter (str) - character(s) to join with (default: ', ')
    - DEFAULT: default_value (Any) - value to use when source is empty
    - TEMPLATE: template (str) - string template with {value} placeholder
    - TRUNCATE: max_length (int) - maximum string length
    - PREFIX: prefix (str) - string to prepend
    - SUFFIX: suffix (str) - string to append
    - REPLACE: find (str), replace (str) - substring replacement
    - REGEX_REPLACE: pattern (str), replacement (str) - regex replacement

    Attributes:
        pattern: Regex pattern for extraction or replacement
        delimiter: Delimiter for split/join operations
        default_value: Default value when source is empty
        template: String template with placeholders
        max_length: Maximum length for truncation
        prefix: String to prepend
        suffix: String to append
        find: Substring to find for replacement
        replace: Replacement string
        replacement: Regex replacement string
        group: Regex group number to extract (default: 1)
    """
    pattern: Optional[str] = None
    delimiter: Optional[str] = None
    default_value: Optional[Any] = None
    template: Optional[str] = None
    max_length: Optional[int] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    find: Optional[str] = None
    replace: Optional[str] = None
    replacement: Optional[str] = None
    group: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert options to dictionary, excluding None values."""
        return {
            k: v for k, v in {
                "pattern": self.pattern,
                "delimiter": self.delimiter,
                "default_value": self.default_value,
                "template": self.template,
                "max_length": self.max_length,
                "prefix": self.prefix,
                "suffix": self.suffix,
                "find": self.find,
                "replace": self.replace,
                "replacement": self.replacement,
                "group": self.group if self.group != 1 else None,
            }.items() if v is not None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformationOptions":
        """Create TransformationOptions from dictionary."""
        return cls(
            pattern=data.get("pattern"),
            delimiter=data.get("delimiter"),
            default_value=data.get("default_value"),
            template=data.get("template"),
            max_length=data.get("max_length"),
            prefix=data.get("prefix"),
            suffix=data.get("suffix"),
            find=data.get("find"),
            replace=data.get("replace"),
            replacement=data.get("replacement"),
            group=data.get("group", 1),
        )


@dataclass
class FieldMapping:
    """
    Defines a mapping from a source field to a destination field.

    Each FieldMapping specifies how data from a source field should be
    transformed and assigned to a destination field.

    Attributes:
        source_field: Name of the field in the source data
        destination_field: Name of the field in the output data
        transformations: List of transformations to apply in order
        options: Configuration options for transformations
        required: Whether the source field must be present
        skip_if_empty: Skip this mapping if source value is empty
        description: Human-readable description of this mapping

    Example:
        # Simple direct mapping
        FieldMapping(
            source_field="email",
            destination_field="contact_email",
        )

        # Mapping with transformations
        FieldMapping(
            source_field="full_name",
            destination_field="name",
            transformations=[TransformationType.TRIM, TransformationType.TITLECASE],
        )

        # Mapping with regex extraction
        FieldMapping(
            source_field="raw_phone",
            destination_field="phone",
            transformations=[TransformationType.REGEX_EXTRACT],
            options=TransformationOptions(pattern=r"\d{3}-\d{3}-\d{4}"),
        )
    """
    source_field: str
    destination_field: str
    transformations: List[TransformationType] = field(default_factory=lambda: [TransformationType.DIRECT])
    options: Optional[TransformationOptions] = None
    required: bool = False
    skip_if_empty: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize the field mapping."""
        if not self.source_field:
            raise ValueError("source_field cannot be empty")
        if not self.destination_field:
            raise ValueError("destination_field cannot be empty")

        # Ensure transformations is a list
        if not isinstance(self.transformations, list):
            self.transformations = [self.transformations]

        # Convert string transformations to enum
        normalized_transformations = []
        for t in self.transformations:
            if isinstance(t, str):
                try:
                    normalized_transformations.append(TransformationType(t))
                except ValueError:
                    raise ValueError(f"Invalid transformation type: {t}")
            else:
                normalized_transformations.append(t)
        self.transformations = normalized_transformations

        # Initialize options if needed
        if self.options is None:
            self.options = TransformationOptions()

    def to_dict(self) -> Dict[str, Any]:
        """Convert field mapping to dictionary for serialization."""
        return {
            "source_field": self.source_field,
            "destination_field": self.destination_field,
            "transformations": [t.value for t in self.transformations],
            "options": self.options.to_dict() if self.options else {},
            "required": self.required,
            "skip_if_empty": self.skip_if_empty,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldMapping":
        """Create FieldMapping from dictionary."""
        transformations = data.get("transformations", ["direct"])
        if isinstance(transformations, str):
            transformations = [transformations]

        return cls(
            source_field=data["source_field"],
            destination_field=data["destination_field"],
            transformations=[TransformationType(t) for t in transformations],
            options=TransformationOptions.from_dict(data.get("options", {})),
            required=data.get("required", False),
            skip_if_empty=data.get("skip_if_empty", True),
            description=data.get("description"),
        )


@dataclass
class ImportMappingConfig:
    """
    Full configuration for an import mapping.

    An ImportMappingConfig represents a complete, reusable mapping configuration
    that can be applied to transform source data into a target format.

    Attributes:
        name: Unique name for this mapping configuration
        description: Human-readable description of the mapping purpose
        field_mappings: List of field mappings that define the transformation
        source_format: Optional description of expected source format
        target_format: Optional description of target output format
        metadata: Additional metadata for the mapping configuration
        id: Unique identifier (auto-generated if not provided)
        created_at: Timestamp when the mapping was created
        updated_at: Timestamp when the mapping was last updated
        version: Version number for the mapping configuration
        tags: Tags for categorizing and searching mappings

    Example:
        config = ImportMappingConfig(
            name="salesforce_contacts",
            description="Map Salesforce contact exports to our entity format",
            field_mappings=[
                FieldMapping(
                    source_field="FirstName",
                    destination_field="first_name",
                    transformations=[TransformationType.TRIM],
                ),
                FieldMapping(
                    source_field="LastName",
                    destination_field="last_name",
                    transformations=[TransformationType.TRIM],
                ),
                FieldMapping(
                    source_field="Email",
                    destination_field="email",
                    transformations=[TransformationType.LOWERCASE, TransformationType.TRIM],
                ),
            ],
            source_format="Salesforce CSV Export",
            tags=["salesforce", "contacts", "crm"],
        )
    """
    name: str
    description: Optional[str] = None
    field_mappings: List[FieldMapping] = field(default_factory=list)
    source_format: Optional[str] = None
    target_format: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: int = 1
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize auto-generated fields."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping configuration to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "field_mappings": [fm.to_dict() for fm in self.field_mappings],
            "source_format": self.source_format,
            "target_format": self.target_format,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImportMappingConfig":
        """Create ImportMappingConfig from dictionary."""
        field_mappings = [
            FieldMapping.from_dict(fm) if isinstance(fm, dict) else fm
            for fm in data.get("field_mappings", [])
        ]

        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data.get("description"),
            field_mappings=field_mappings,
            source_format=data.get("source_format"),
            target_format=data.get("target_format"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            version=data.get("version", 1),
            tags=data.get("tags", []),
        )


@dataclass
class MappingValidationResult:
    """
    Result of validating a mapping configuration.

    Attributes:
        is_valid: Whether the mapping configuration is valid
        errors: List of validation error messages
        warnings: List of validation warning messages
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class MappingPreviewResult:
    """
    Result of previewing a mapping transformation.

    Attributes:
        success: Whether the preview was successful
        original_data: The original input data
        transformed_data: The transformed output data
        field_results: Per-field transformation results
        errors: List of errors encountered during preview
    """
    success: bool = True
    original_data: Dict[str, Any] = field(default_factory=dict)
    transformed_data: Dict[str, Any] = field(default_factory=dict)
    field_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_field_result(
        self,
        field_name: str,
        original_value: Any,
        transformed_value: Any,
        transformations_applied: List[str],
    ) -> None:
        """Add a field transformation result."""
        self.field_results[field_name] = {
            "original": original_value,
            "transformed": transformed_value,
            "transformations": transformations_applied,
        }

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.success = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert preview result to dictionary."""
        return {
            "success": self.success,
            "original_data": self.original_data,
            "transformed_data": self.transformed_data,
            "field_results": self.field_results,
            "errors": self.errors,
        }


# =============================================================================
# TRANSFORMATION FUNCTIONS
# =============================================================================

class TransformationEngine:
    """
    Engine for applying transformations to field values.

    This class contains the implementation of all transformation types
    and provides a unified interface for applying transformations.
    """

    # Regex pattern for matching HTML tags
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

    # Regex pattern for matching multiple whitespace
    WHITESPACE_PATTERN = re.compile(r'\s+')

    @classmethod
    def apply_transformation(
        cls,
        value: Any,
        transformation: TransformationType,
        options: TransformationOptions,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Apply a single transformation to a value.

        Args:
            value: The value to transform
            transformation: The transformation type to apply
            options: Configuration options for the transformation
            context: Additional context (e.g., other fields for template)

        Returns:
            The transformed value

        Raises:
            ValueError: If transformation fails due to invalid configuration
        """
        context = context or {}

        # Map transformation types to handler methods
        handlers: Dict[TransformationType, Callable] = {
            TransformationType.DIRECT: cls._transform_direct,
            TransformationType.LOWERCASE: cls._transform_lowercase,
            TransformationType.UPPERCASE: cls._transform_uppercase,
            TransformationType.TRIM: cls._transform_trim,
            TransformationType.REGEX_EXTRACT: cls._transform_regex_extract,
            TransformationType.SPLIT: cls._transform_split,
            TransformationType.JOIN: cls._transform_join,
            TransformationType.DEFAULT: cls._transform_default,
            TransformationType.TEMPLATE: cls._transform_template,
            TransformationType.STRIP_HTML: cls._transform_strip_html,
            TransformationType.NORMALIZE_WHITESPACE: cls._transform_normalize_whitespace,
            TransformationType.TRUNCATE: cls._transform_truncate,
            TransformationType.PREFIX: cls._transform_prefix,
            TransformationType.SUFFIX: cls._transform_suffix,
            TransformationType.REPLACE: cls._transform_replace,
            TransformationType.REGEX_REPLACE: cls._transform_regex_replace,
            TransformationType.TITLECASE: cls._transform_titlecase,
            TransformationType.CAPITALIZE: cls._transform_capitalize,
        }

        handler = handlers.get(transformation)
        if handler is None:
            raise ValueError(f"Unknown transformation type: {transformation}")

        return handler(value, options, context)

    @classmethod
    def apply_transformations(
        cls,
        value: Any,
        transformations: List[TransformationType],
        options: TransformationOptions,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, List[str]]:
        """
        Apply a chain of transformations to a value.

        Args:
            value: The value to transform
            transformations: List of transformations to apply in order
            options: Configuration options for transformations
            context: Additional context for template transformation

        Returns:
            Tuple of (transformed_value, list_of_applied_transformations)
        """
        applied = []
        current_value = value

        for transformation in transformations:
            try:
                current_value = cls.apply_transformation(
                    current_value, transformation, options, context
                )
                applied.append(transformation.value)
            except Exception as e:
                logger.warning(
                    f"Transformation {transformation.value} failed: {e}"
                )
                # Continue with current value

        return current_value, applied

    # -------------------------------------------------------------------------
    # Individual Transformation Handlers
    # -------------------------------------------------------------------------

    @staticmethod
    def _transform_direct(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Return value as-is."""
        return value

    @staticmethod
    def _transform_lowercase(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Convert string to lowercase."""
        if isinstance(value, str):
            return value.lower()
        return value

    @staticmethod
    def _transform_uppercase(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Convert string to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    @staticmethod
    def _transform_trim(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Remove leading and trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value

    @staticmethod
    def _transform_regex_extract(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Extract value using regex pattern."""
        if not isinstance(value, str):
            return value

        pattern = options.pattern
        if not pattern:
            raise ValueError("REGEX_EXTRACT requires 'pattern' in options")

        try:
            match = re.search(pattern, value)
            if match:
                # Return the specified group or the first capturing group
                group = options.group
                try:
                    return match.group(group)
                except IndexError:
                    return match.group(0)
            return value
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    @staticmethod
    def _transform_split(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Split string into array."""
        if not isinstance(value, str):
            return value

        delimiter = options.delimiter or ","
        parts = value.split(delimiter)
        # Optionally trim each part
        return [part.strip() for part in parts]

    @staticmethod
    def _transform_join(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Join array into string."""
        if not isinstance(value, (list, tuple)):
            return value

        delimiter = options.delimiter or ", "
        return delimiter.join(str(item) for item in value)

    @staticmethod
    def _transform_default(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Use default value if source is empty."""
        if value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0):
            return options.default_value
        return value

    @staticmethod
    def _transform_template(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Apply string template with placeholders."""
        template = options.template
        if not template:
            raise ValueError("TEMPLATE requires 'template' in options")

        # Build template context
        template_context = {"value": value}
        template_context.update(context)

        try:
            # Use format_map for safe formatting (missing keys won't raise errors)
            class SafeDict(dict):
                def __missing__(self, key):
                    return f"{{{key}}}"

            return template.format_map(SafeDict(template_context))
        except Exception as e:
            logger.warning(f"Template formatting failed: {e}")
            return value

    @classmethod
    def _transform_strip_html(
        cls,
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Remove HTML tags from the value."""
        if not isinstance(value, str):
            return value
        return cls.HTML_TAG_PATTERN.sub('', value)

    @classmethod
    def _transform_normalize_whitespace(
        cls,
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Replace multiple whitespace with single space."""
        if not isinstance(value, str):
            return value
        return cls.WHITESPACE_PATTERN.sub(' ', value).strip()

    @staticmethod
    def _transform_truncate(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Truncate string to max length."""
        if not isinstance(value, str):
            return value

        max_length = options.max_length
        if max_length is None:
            raise ValueError("TRUNCATE requires 'max_length' in options")

        if len(value) <= max_length:
            return value
        return value[:max_length]

    @staticmethod
    def _transform_prefix(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Add prefix to value."""
        prefix = options.prefix
        if prefix is None:
            raise ValueError("PREFIX requires 'prefix' in options")

        if isinstance(value, str):
            return f"{prefix}{value}"
        return value

    @staticmethod
    def _transform_suffix(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Add suffix to value."""
        suffix = options.suffix
        if suffix is None:
            raise ValueError("SUFFIX requires 'suffix' in options")

        if isinstance(value, str):
            return f"{value}{suffix}"
        return value

    @staticmethod
    def _transform_replace(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Replace substring."""
        if not isinstance(value, str):
            return value

        find = options.find
        replace = options.replace

        if find is None:
            raise ValueError("REPLACE requires 'find' in options")
        if replace is None:
            replace = ""

        return value.replace(find, replace)

    @staticmethod
    def _transform_regex_replace(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Replace using regex."""
        if not isinstance(value, str):
            return value

        pattern = options.pattern
        replacement = options.replacement

        if pattern is None:
            raise ValueError("REGEX_REPLACE requires 'pattern' in options")
        if replacement is None:
            replacement = ""

        try:
            return re.sub(pattern, replacement, value)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    @staticmethod
    def _transform_titlecase(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Convert string to title case."""
        if isinstance(value, str):
            return value.title()
        return value

    @staticmethod
    def _transform_capitalize(
        value: Any,
        options: TransformationOptions,
        context: Dict[str, Any],
    ) -> Any:
        """Capitalize first character."""
        if isinstance(value, str):
            return value.capitalize()
        return value


# =============================================================================
# IMPORT MAPPING SERVICE
# =============================================================================

class ImportMappingService:
    """
    Service for managing and applying import field mappings.

    This service provides CRUD operations for mapping configurations
    and the ability to apply mappings to transform data.

    Features:
    - Create, read, update, delete mapping configurations
    - Apply mappings to transform data dictionaries
    - Validate mapping configurations
    - Preview transformations on sample data
    - Optional JSON file persistence

    Usage:
        service = ImportMappingService()

        # Create a mapping
        config = ImportMappingConfig(
            name="my_mapping",
            field_mappings=[
                FieldMapping(
                    source_field="Name",
                    destination_field="full_name",
                    transformations=[TransformationType.TRIM],
                ),
            ],
        )
        mapping = service.create_mapping(config)

        # Apply the mapping
        data = {"Name": "  John Doe  "}
        result = service.apply_mapping(data, mapping.id)
        # result = {"full_name": "John Doe"}

    Attributes:
        persistence_path: Optional path to JSON file for persistence
        _mappings: In-memory storage for mapping configurations
    """

    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the import mapping service.

        Args:
            persistence_path: Optional path to JSON file for persistence.
                              If provided, mappings will be loaded from and
                              saved to this file.
        """
        self._mappings: Dict[str, ImportMappingConfig] = {}
        self._persistence_path = persistence_path

        # Load existing mappings from file if persistence is enabled
        if self._persistence_path:
            self._load_from_file()

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def create_mapping(self, config: ImportMappingConfig) -> ImportMappingConfig:
        """
        Create a new mapping configuration.

        Args:
            config: The mapping configuration to create

        Returns:
            The created mapping configuration with generated ID

        Raises:
            ValueError: If a mapping with the same name already exists
        """
        # Check for duplicate names
        for existing in self._mappings.values():
            if existing.name == config.name:
                raise ValueError(f"Mapping with name '{config.name}' already exists")

        # Ensure ID is set
        if not config.id:
            config.id = str(uuid.uuid4())

        # Set timestamps
        now = datetime.now().isoformat()
        config.created_at = now
        config.updated_at = now

        # Validate the configuration
        validation = self.validate_mapping(config)
        if not validation.is_valid:
            raise ValueError(f"Invalid mapping configuration: {', '.join(validation.errors)}")

        # Store the mapping
        self._mappings[config.id] = config

        # Persist to file if enabled
        self._save_to_file()

        logger.info(f"Created mapping configuration: {config.name} (ID: {config.id})")
        return config

    def get_mapping(self, mapping_id: str) -> Optional[ImportMappingConfig]:
        """
        Get a mapping configuration by ID.

        Args:
            mapping_id: The unique identifier of the mapping

        Returns:
            The mapping configuration or None if not found
        """
        return self._mappings.get(mapping_id)

    def get_mapping_by_name(self, name: str) -> Optional[ImportMappingConfig]:
        """
        Get a mapping configuration by name.

        Args:
            name: The name of the mapping

        Returns:
            The mapping configuration or None if not found
        """
        for mapping in self._mappings.values():
            if mapping.name == name:
                return mapping
        return None

    def list_mappings(
        self,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
    ) -> List[ImportMappingConfig]:
        """
        List all mapping configurations.

        Args:
            tags: Optional list of tags to filter by (mappings must have all tags)
            search: Optional search string to filter by name or description

        Returns:
            List of matching mapping configurations
        """
        results = list(self._mappings.values())

        # Filter by tags
        if tags:
            results = [
                m for m in results
                if all(tag in m.tags for tag in tags)
            ]

        # Filter by search string
        if search:
            search_lower = search.lower()
            results = [
                m for m in results
                if search_lower in m.name.lower() or
                (m.description and search_lower in m.description.lower())
            ]

        # Sort by name
        results.sort(key=lambda m: m.name)

        return results

    def update_mapping(
        self,
        mapping_id: str,
        config: ImportMappingConfig,
    ) -> Optional[ImportMappingConfig]:
        """
        Update an existing mapping configuration.

        Args:
            mapping_id: The ID of the mapping to update
            config: The new configuration

        Returns:
            The updated mapping configuration or None if not found

        Raises:
            ValueError: If the new configuration is invalid
        """
        if mapping_id not in self._mappings:
            return None

        existing = self._mappings[mapping_id]

        # Check for duplicate names (if name is changing)
        if config.name != existing.name:
            for other in self._mappings.values():
                if other.id != mapping_id and other.name == config.name:
                    raise ValueError(f"Mapping with name '{config.name}' already exists")

        # Validate the new configuration
        validation = self.validate_mapping(config)
        if not validation.is_valid:
            raise ValueError(f"Invalid mapping configuration: {', '.join(validation.errors)}")

        # Update fields
        config.id = mapping_id
        config.created_at = existing.created_at
        config.updated_at = datetime.now().isoformat()
        config.version = existing.version + 1

        # Store the updated mapping
        self._mappings[mapping_id] = config

        # Persist to file if enabled
        self._save_to_file()

        logger.info(f"Updated mapping configuration: {config.name} (ID: {mapping_id})")
        return config

    def delete_mapping(self, mapping_id: str) -> bool:
        """
        Delete a mapping configuration.

        Args:
            mapping_id: The ID of the mapping to delete

        Returns:
            True if the mapping was deleted, False if not found
        """
        if mapping_id not in self._mappings:
            return False

        mapping = self._mappings[mapping_id]
        del self._mappings[mapping_id]

        # Persist to file if enabled
        self._save_to_file()

        logger.info(f"Deleted mapping configuration: {mapping.name} (ID: {mapping_id})")
        return True

    # -------------------------------------------------------------------------
    # Mapping Operations
    # -------------------------------------------------------------------------

    def apply_mapping(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        mapping_id: str,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Apply a mapping configuration to transform data.

        Args:
            data: Source data dictionary or list of dictionaries
            mapping_id: ID of the mapping configuration to apply

        Returns:
            Transformed data in the same format as input (dict or list)

        Raises:
            ValueError: If mapping_id is not found
        """
        mapping = self.get_mapping(mapping_id)
        if mapping is None:
            raise ValueError(f"Mapping not found: {mapping_id}")

        if isinstance(data, list):
            return [self._apply_mapping_to_record(record, mapping) for record in data]
        else:
            return self._apply_mapping_to_record(data, mapping)

    def _apply_mapping_to_record(
        self,
        record: Dict[str, Any],
        mapping: ImportMappingConfig,
    ) -> Dict[str, Any]:
        """
        Apply a mapping configuration to a single data record.

        Args:
            record: Source data dictionary
            mapping: Mapping configuration to apply

        Returns:
            Transformed data dictionary
        """
        result: Dict[str, Any] = {}

        for field_mapping in mapping.field_mappings:
            source_field = field_mapping.source_field
            destination_field = field_mapping.destination_field

            # Get source value
            source_value = record.get(source_field)

            # Check if required field is missing
            if field_mapping.required and source_value is None:
                logger.warning(
                    f"Required field '{source_field}' is missing from record"
                )
                continue

            # Check if we should skip empty values
            if field_mapping.skip_if_empty and (
                source_value is None or
                source_value == "" or
                (isinstance(source_value, (list, dict)) and len(source_value) == 0)
            ):
                continue

            # Apply transformations
            transformed_value, _ = TransformationEngine.apply_transformations(
                source_value,
                field_mapping.transformations,
                field_mapping.options,
                context=record,
            )

            # Set the destination field
            result[destination_field] = transformed_value

        return result

    def validate_mapping(self, config: ImportMappingConfig) -> MappingValidationResult:
        """
        Validate a mapping configuration.

        Checks for:
        - Required fields (name, at least one field mapping)
        - Valid transformation types
        - Required options for specific transformations
        - Duplicate destination fields

        Args:
            config: The mapping configuration to validate

        Returns:
            MappingValidationResult with validation status and messages
        """
        result = MappingValidationResult()

        # Check required fields
        if not config.name:
            result.add_error("Mapping name is required")

        if not config.field_mappings:
            result.add_error("At least one field mapping is required")

        # Track destination fields for duplicate detection
        destination_fields: set = set()

        for i, fm in enumerate(config.field_mappings):
            field_prefix = f"Field mapping [{i}] ({fm.source_field} -> {fm.destination_field})"

            # Check for duplicate destinations
            if fm.destination_field in destination_fields:
                result.add_warning(
                    f"{field_prefix}: Duplicate destination field '{fm.destination_field}'"
                )
            destination_fields.add(fm.destination_field)

            # Validate transformations
            for transformation in fm.transformations:
                # Check for required options
                if transformation == TransformationType.REGEX_EXTRACT:
                    if not fm.options or not fm.options.pattern:
                        result.add_error(
                            f"{field_prefix}: REGEX_EXTRACT requires 'pattern' option"
                        )

                elif transformation == TransformationType.TEMPLATE:
                    if not fm.options or not fm.options.template:
                        result.add_error(
                            f"{field_prefix}: TEMPLATE requires 'template' option"
                        )

                elif transformation == TransformationType.TRUNCATE:
                    if not fm.options or fm.options.max_length is None:
                        result.add_error(
                            f"{field_prefix}: TRUNCATE requires 'max_length' option"
                        )

                elif transformation == TransformationType.PREFIX:
                    if not fm.options or fm.options.prefix is None:
                        result.add_error(
                            f"{field_prefix}: PREFIX requires 'prefix' option"
                        )

                elif transformation == TransformationType.SUFFIX:
                    if not fm.options or fm.options.suffix is None:
                        result.add_error(
                            f"{field_prefix}: SUFFIX requires 'suffix' option"
                        )

                elif transformation == TransformationType.REPLACE:
                    if not fm.options or fm.options.find is None:
                        result.add_error(
                            f"{field_prefix}: REPLACE requires 'find' option"
                        )

                elif transformation == TransformationType.REGEX_REPLACE:
                    if not fm.options or not fm.options.pattern:
                        result.add_error(
                            f"{field_prefix}: REGEX_REPLACE requires 'pattern' option"
                        )

        return result

    def preview_mapping(
        self,
        sample_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        config: ImportMappingConfig,
    ) -> MappingPreviewResult:
        """
        Preview the result of applying a mapping to sample data.

        This method applies the mapping and returns detailed information
        about each field transformation, useful for debugging and
        configuration testing.

        Args:
            sample_data: Sample data to transform (dict or first item of list used)
            config: Mapping configuration to preview

        Returns:
            MappingPreviewResult with detailed transformation results
        """
        result = MappingPreviewResult()

        # Use first record if list provided
        if isinstance(sample_data, list):
            if not sample_data:
                result.add_error("Sample data is empty")
                return result
            sample_data = sample_data[0]

        result.original_data = dict(sample_data)

        # Validate configuration first
        validation = self.validate_mapping(config)
        if not validation.is_valid:
            for error in validation.errors:
                result.add_error(f"Validation error: {error}")
            return result

        # Apply each field mapping and track results
        transformed: Dict[str, Any] = {}

        for field_mapping in config.field_mappings:
            source_field = field_mapping.source_field
            destination_field = field_mapping.destination_field

            # Get source value
            source_value = sample_data.get(source_field)

            # Skip if empty and configured to do so
            if field_mapping.skip_if_empty and (
                source_value is None or
                source_value == "" or
                (isinstance(source_value, (list, dict)) and len(source_value) == 0)
            ):
                result.add_field_result(
                    destination_field,
                    source_value,
                    None,
                    ["skipped (empty)"],
                )
                continue

            # Apply transformations
            try:
                transformed_value, applied = TransformationEngine.apply_transformations(
                    source_value,
                    field_mapping.transformations,
                    field_mapping.options,
                    context=sample_data,
                )

                transformed[destination_field] = transformed_value
                result.add_field_result(
                    destination_field,
                    source_value,
                    transformed_value,
                    applied,
                )
            except Exception as e:
                result.add_error(
                    f"Error transforming field '{source_field}': {str(e)}"
                )

        result.transformed_data = transformed
        return result

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _load_from_file(self) -> None:
        """Load mappings from persistence file."""
        if not self._persistence_path:
            return

        path = Path(self._persistence_path)
        if not path.exists():
            logger.debug(f"Persistence file not found: {path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for mapping_data in data.get("mappings", []):
                try:
                    config = ImportMappingConfig.from_dict(mapping_data)
                    self._mappings[config.id] = config
                except Exception as e:
                    logger.warning(f"Failed to load mapping: {e}")

            logger.info(f"Loaded {len(self._mappings)} mappings from {path}")
        except Exception as e:
            logger.error(f"Failed to load mappings from file: {e}")

    def _save_to_file(self) -> None:
        """Save mappings to persistence file."""
        if not self._persistence_path:
            return

        path = Path(self._persistence_path)

        try:
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": 1,
                "updated_at": datetime.now().isoformat(),
                "mappings": [m.to_dict() for m in self._mappings.values()],
            }

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._mappings)} mappings to {path}")
        except Exception as e:
            logger.error(f"Failed to save mappings to file: {e}")

    def export_mapping(self, mapping_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a mapping configuration as a dictionary.

        Args:
            mapping_id: ID of the mapping to export

        Returns:
            Dictionary representation of the mapping or None if not found
        """
        mapping = self.get_mapping(mapping_id)
        if mapping:
            return mapping.to_dict()
        return None

    def import_mapping(self, data: Dict[str, Any]) -> ImportMappingConfig:
        """
        Import a mapping configuration from a dictionary.

        Args:
            data: Dictionary representation of the mapping

        Returns:
            The imported mapping configuration

        Raises:
            ValueError: If the data is invalid
        """
        config = ImportMappingConfig.from_dict(data)
        # Generate new ID to avoid conflicts
        config.id = str(uuid.uuid4())
        return self.create_mapping(config)


# =============================================================================
# MODULE-LEVEL SINGLETON FUNCTIONS
# =============================================================================

_import_mapping_service: Optional[ImportMappingService] = None


def get_import_mapping_service(
    persistence_path: Optional[str] = None,
) -> ImportMappingService:
    """
    Get or create the ImportMappingService singleton instance.

    Args:
        persistence_path: Optional path to JSON file for persistence.
                          Only used when creating a new instance.

    Returns:
        ImportMappingService instance
    """
    global _import_mapping_service

    if _import_mapping_service is None:
        _import_mapping_service = ImportMappingService(persistence_path)

    return _import_mapping_service


def reset_import_mapping_service() -> None:
    """
    Reset the global ImportMappingService singleton.

    Useful for testing or when you need to reinitialize with different settings.
    """
    global _import_mapping_service
    _import_mapping_service = None
