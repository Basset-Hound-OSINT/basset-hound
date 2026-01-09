"""
Pydantic models for Basset Hound API.

This module provides data validation and serialization models for:
- Projects: Investigation projects containing people and data
- Entities: People/entities being investigated with profile data
- Relationships: Connections and tags between entities with named types
- Files: File uploads and references
- Reports: OSINT investigation reports
- Config: Dynamic field configuration schema
- Auth: Authentication and user management
- DataItems: Individual data pieces with unique IDs (Phase 43.1)
"""

from api.models.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectList,
)
from api.models.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityList,
)
from api.models.relationship import (
    RelationshipType,
    ConfidenceLevel,
    RelationshipProperties,
    RelationshipCreate,
    NamedRelationshipCreate,
    RelationshipInfo,
    RelationshipResponse,
    RelationshipListResponse,
    RelationshipBulkUpdate,
    get_all_relationship_types,
    get_relationship_type_categories,
)
from api.models.file import (
    FileUpload,
    FileResponse,
)
from api.models.report import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
)
from api.models.config import (
    ConfigSection,
    ConfigField,
    ConfigResponse,
)
from api.models.auth import (
    Token,
    TokenData,
    UserCreate,
    User,
)
from api.models.data_item import (
    DataItem,
    DATA_TYPES,
)

__all__ = [
    # Project models
    "ProjectCreate",
    "ProjectResponse",
    "ProjectList",
    # Entity models
    "EntityCreate",
    "EntityUpdate",
    "EntityResponse",
    "EntityList",
    # Relationship models
    "RelationshipType",
    "ConfidenceLevel",
    "RelationshipProperties",
    "RelationshipCreate",
    "NamedRelationshipCreate",
    "RelationshipInfo",
    "RelationshipResponse",
    "RelationshipListResponse",
    "RelationshipBulkUpdate",
    "get_all_relationship_types",
    "get_relationship_type_categories",
    # File models
    "FileUpload",
    "FileResponse",
    # Report models
    "ReportCreate",
    "ReportUpdate",
    "ReportResponse",
    # Config models
    "ConfigSection",
    "ConfigField",
    "ConfigResponse",
    # Auth models
    "Token",
    "TokenData",
    "UserCreate",
    "User",
    # DataItem models (Phase 43.1)
    "DataItem",
    "DATA_TYPES",
]
