"""
Pydantic models for Smart Suggestions REST API (Phase 44).

These models define the request/response schemas for the suggestions API
following 2026 best practices with HATEOAS support.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ConfidenceLevelEnum(str, Enum):
    """Confidence levels for suggestions."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MatchTypeEnum(str, Enum):
    """Types of matches."""
    EXACT_HASH = "exact_hash"
    EXACT_STRING = "exact_string"
    PARTIAL_STRING = "partial_string"


class ActionTypeEnum(str, Enum):
    """Types of linking actions."""
    LINK_DATA_ITEMS = "link_data_items"
    MERGE_ENTITIES = "merge_entities"
    CREATE_RELATIONSHIP = "create_relationship"
    LINK_ORPHAN_TO_ENTITY = "link_orphan_to_entity"
    DISMISS_SUGGESTION = "dismiss_suggestion"


# Request Models

class DismissSuggestionRequest(BaseModel):
    """Request model for dismissing a suggestion."""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for dismissing")
    dismissed_by: str = Field(..., min_length=1, max_length=100, description="User ID or name")


class LinkDataItemsRequest(BaseModel):
    """Request model for linking two data items."""
    data_id_1: str = Field(..., description="First data item ID")
    data_id_2: str = Field(..., description="Second data item ID")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for linking")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Confidence score")
    created_by: str = Field("system", max_length=100, description="User ID or name")


class MergeEntitiesRequest(BaseModel):
    """Request model for merging two entities."""
    entity_id_1: str = Field(..., description="First entity ID")
    entity_id_2: str = Field(..., description="Second entity ID")
    keep_entity_id: str = Field(..., description="Entity ID to keep")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for merging")
    created_by: str = Field("system", max_length=100, description="User ID or name")

    @field_validator("keep_entity_id")
    @classmethod
    def validate_keep_entity_id(cls, v: str, info) -> str:
        """Validate that keep_entity_id is one of the entity IDs."""
        # Note: Full validation happens in the endpoint with entity_id_1 and entity_id_2
        return v


class CreateRelationshipRequest(BaseModel):
    """Request model for creating a relationship."""
    entity_id_1: str = Field(..., description="Source entity ID")
    entity_id_2: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Type of relationship (KNOWS, WORKS_WITH, etc.)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for relationship")
    confidence: Optional[str] = Field(None, description="Confidence level (confirmed, high, medium, low, unverified)")
    created_by: str = Field("system", max_length=100, description="User ID or name")


class LinkOrphanToEntityRequest(BaseModel):
    """Request model for linking orphan data to entity."""
    orphan_id: str = Field(..., description="Orphan data ID")
    entity_id: str = Field(..., description="Entity ID to link to")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for linking")
    created_by: str = Field("system", max_length=100, description="User ID or name")


# Batch/Auto-Accept Models

class BatchSuggestionItem(BaseModel):
    """Single suggestion to accept in batch operation."""
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: Optional[str] = Field(None, description="Target entity ID (for relationships/merges)")
    target_orphan_id: Optional[str] = Field(None, description="Target orphan ID (for orphan linking)")
    data_id: Optional[str] = Field(None, description="Data item ID that triggered the suggestion")
    action: str = Field(..., description="Action to take: 'link', 'merge', 'relationship', 'dismiss'")
    relationship_type: Optional[str] = Field(None, description="Relationship type (for relationship action)")


class BatchAcceptSuggestionsRequest(BaseModel):
    """Request model for batch accepting suggestions."""
    suggestions: List[BatchSuggestionItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of suggestions to accept (max 100)"
    )
    reason: str = Field("Batch accepted", max_length=500, description="Reason for batch accept")
    created_by: str = Field("system", max_length=100, description="User ID or name")


class AutoAcceptConfigRequest(BaseModel):
    """Configuration for auto-accepting suggestions."""
    enabled: bool = Field(False, description="Enable auto-accept")
    min_confidence: float = Field(0.95, ge=0.5, le=1.0, description="Minimum confidence to auto-accept")
    match_types: List[str] = Field(
        default=["exact_hash"],
        description="Match types to auto-accept (exact_hash, exact_string, partial_string)"
    )
    data_types: List[str] = Field(
        default=[],
        description="Data types to auto-accept (empty = all)"
    )
    action: str = Field("link", description="Default action: 'link', 'relationship'")
    relationship_type: Optional[str] = Field(
        "RELATED_TO",
        description="Default relationship type when action='relationship'"
    )
    dry_run: bool = Field(True, description="If true, only preview what would be accepted")


class AutoAcceptPreviewItem(BaseModel):
    """Single item in auto-accept preview."""
    source_entity_id: str = Field(..., description="Source entity ID")
    source_entity_name: Optional[str] = Field(None, description="Source entity name")
    target_entity_id: Optional[str] = Field(None, description="Target entity ID")
    target_entity_name: Optional[str] = Field(None, description="Target entity name")
    data_id: str = Field(..., description="Data item ID")
    data_type: str = Field(..., description="Data type")
    data_value: str = Field(..., description="Data value")
    confidence_score: float = Field(..., description="Confidence score")
    match_type: str = Field(..., description="Match type")
    proposed_action: str = Field(..., description="Action that would be taken")


# Response Models

class LinkModel(BaseModel):
    """HATEOAS link model."""
    href: str = Field(..., description="URL for the resource")
    method: Optional[str] = Field(None, description="HTTP method (for action links)")


class PaginationModel(BaseModel):
    """Pagination metadata model."""
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
    total: int = Field(..., description="Total number of items")
    next: Optional[str] = Field(None, description="URL for next page")
    prev: Optional[str] = Field(None, description="URL for previous page")


class SuggestionMatchResponse(BaseModel):
    """Single suggestion match response."""
    data_id: str = Field(..., description="Data item ID")
    data_type: str = Field(..., description="Type of data")
    data_value: str = Field(..., description="Data value")
    match_type: MatchTypeEnum = Field(..., description="Type of match")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    matched_entity_id: Optional[str] = Field(None, description="Matched entity ID")
    matched_entity_name: Optional[str] = Field(None, description="Matched entity name")
    matched_orphan_id: Optional[str] = Field(None, description="Matched orphan ID")


class ConfidenceGroupResponse(BaseModel):
    """Group of suggestions at a confidence level."""
    confidence: ConfidenceLevelEnum = Field(..., description="Confidence level")
    matches: List[SuggestionMatchResponse] = Field(..., description="Matches at this level")


class EntitySuggestionsData(BaseModel):
    """Data section for entity suggestions response."""
    entity_id: str = Field(..., description="Entity ID")
    suggestions: List[ConfidenceGroupResponse] = Field(..., description="Suggestions grouped by confidence")
    total_count: int = Field(..., description="Total number of suggestions")
    high_confidence_count: int = Field(..., description="Number of HIGH confidence suggestions")
    medium_confidence_count: int = Field(..., description="Number of MEDIUM confidence suggestions")
    low_confidence_count: int = Field(..., description="Number of LOW confidence suggestions")
    dismissed_count: int = Field(..., description="Number of dismissed suggestions")


class EntitySuggestionsResponse(BaseModel):
    """Complete response for entity suggestions."""
    model_config = {"populate_by_name": True}

    data: EntitySuggestionsData = Field(..., description="Response data")
    pagination: Optional[PaginationModel] = Field(None, description="Pagination metadata")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class OrphanSuggestionsData(BaseModel):
    """Data section for orphan suggestions response."""
    orphan_id: str = Field(..., description="Orphan ID")
    suggestions: List[ConfidenceGroupResponse] = Field(..., description="Entity suggestions")
    total_count: int = Field(..., description="Total number of suggestions")
    high_confidence_count: int = Field(..., description="Number of HIGH confidence suggestions")
    medium_confidence_count: int = Field(..., description="Number of MEDIUM confidence suggestions")
    low_confidence_count: int = Field(..., description="Number of LOW confidence suggestions")


class OrphanSuggestionsResponse(BaseModel):
    """Complete response for orphan suggestions."""
    model_config = {"populate_by_name": True}

    data: OrphanSuggestionsData = Field(..., description="Response data")
    pagination: Optional[PaginationModel] = Field(None, description="Pagination metadata")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class DismissedSuggestionItem(BaseModel):
    """Single dismissed suggestion."""
    data_id: str = Field(..., description="Data item ID")
    data_type: str = Field(..., description="Type of data")
    data_value: str = Field(..., description="Data value")
    reason: str = Field(..., description="Reason for dismissal")
    dismissed_at: str = Field(..., description="When dismissed (ISO 8601)")
    dismissed_by: str = Field(..., description="Who dismissed it")


class DismissedSuggestionsData(BaseModel):
    """Data section for dismissed suggestions response."""
    entity_id: str = Field(..., description="Entity ID")
    dismissed_suggestions: List[DismissedSuggestionItem] = Field(..., description="Dismissed suggestions")
    count: int = Field(..., description="Total count")


class DismissedSuggestionsResponse(BaseModel):
    """Complete response for dismissed suggestions."""
    data: DismissedSuggestionsData = Field(..., description="Response data")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class DismissSuggestionResponse(BaseModel):
    """Response for dismissing a suggestion."""
    success: bool = Field(..., description="Success status")
    action_id: str = Field(..., description="Action ID for audit trail")
    entity_id: str = Field(..., description="Entity ID")
    data_id: str = Field(..., description="Data item ID")
    reason: str = Field(..., description="Reason for dismissal")
    dismissed_at: str = Field(..., description="When dismissed (ISO 8601)")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class LinkDataItemsResponse(BaseModel):
    """Response for linking data items."""
    success: bool = Field(..., description="Success status")
    action_id: str = Field(..., description="Action ID for audit trail")
    linked_data_items: List[str] = Field(..., description="IDs of linked data items")
    reason: str = Field(..., description="Reason for linking")
    confidence: float = Field(..., description="Confidence score")
    created_at: str = Field(..., description="When created (ISO 8601)")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class MergeEntitiesResponse(BaseModel):
    """Response for merging entities."""
    success: bool = Field(..., description="Success status")
    action_id: str = Field(..., description="Action ID for audit trail")
    kept_entity_id: str = Field(..., description="Entity ID that was kept")
    merged_entity_id: str = Field(..., description="Entity ID that was merged")
    data_items_moved: int = Field(..., description="Number of data items moved")
    relationships_moved: int = Field(..., description="Number of relationships moved")
    reason: str = Field(..., description="Reason for merging")
    created_at: str = Field(..., description="When created (ISO 8601)")
    warning: str = Field(..., description="Warning message")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class CreateRelationshipResponse(BaseModel):
    """Response for creating a relationship."""
    success: bool = Field(..., description="Success status")
    action_id: str = Field(..., description="Action ID for audit trail")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: str = Field(..., description="Confidence level")
    reason: str = Field(..., description="Reason for relationship")
    is_symmetric: bool = Field(..., description="Whether relationship is symmetric")
    created_at: str = Field(..., description="When created (ISO 8601)")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class LinkOrphanToEntityResponse(BaseModel):
    """Response for linking orphan to entity."""
    success: bool = Field(..., description="Success status")
    action_id: str = Field(..., description="Action ID for audit trail")
    orphan_id: str = Field(..., description="Orphan ID")
    entity_id: str = Field(..., description="Entity ID")
    data_items_moved: int = Field(..., description="Number of data items moved")
    reason: str = Field(..., description="Reason for linking")
    created_at: str = Field(..., description="When created (ISO 8601)")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class LinkingActionItem(BaseModel):
    """Single linking action in history."""
    action_id: str = Field(..., description="Action ID")
    action_type: ActionTypeEnum = Field(..., description="Type of action")
    created_at: str = Field(..., description="When created (ISO 8601)")
    created_by: str = Field(..., description="Who created it")
    reason: str = Field(..., description="Reason for action")
    details: Dict[str, Any] = Field(..., description="Action-specific details")
    confidence: float = Field(..., description="Confidence score")


class LinkingHistoryData(BaseModel):
    """Data section for linking history response."""
    entity_id: Optional[str] = Field(None, description="Entity ID (if filtered)")
    actions: List[LinkingActionItem] = Field(..., description="Linking actions")
    count: int = Field(..., description="Total count")


class LinkingHistoryResponse(BaseModel):
    """Complete response for linking history."""
    data: LinkingHistoryData = Field(..., description="Response data")
    pagination: Optional[PaginationModel] = Field(None, description="Pagination metadata")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


# Batch/Auto-Accept Response Models

class BatchActionResult(BaseModel):
    """Result of a single batch action."""
    suggestion_index: int = Field(..., description="Index in the request array")
    success: bool = Field(..., description="Whether action succeeded")
    action_id: Optional[str] = Field(None, description="Action ID if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchAcceptSuggestionsResponse(BaseModel):
    """Response for batch accepting suggestions."""
    model_config = {"populate_by_name": True}

    success: bool = Field(..., description="Overall success (all actions succeeded)")
    total_processed: int = Field(..., description="Total suggestions processed")
    successful_count: int = Field(..., description="Number of successful actions")
    failed_count: int = Field(..., description="Number of failed actions")
    results: List[BatchActionResult] = Field(..., description="Individual results")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class AutoAcceptPreviewResponse(BaseModel):
    """Response for auto-accept preview."""
    model_config = {"populate_by_name": True}

    config: AutoAcceptConfigRequest = Field(..., description="Config used for preview")
    preview: List[AutoAcceptPreviewItem] = Field(..., description="Items that would be accepted")
    total_matches: int = Field(..., description="Total matches found")
    would_accept: int = Field(..., description="Number that would be auto-accepted")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


class AutoAcceptExecuteResponse(BaseModel):
    """Response for auto-accept execution."""
    model_config = {"populate_by_name": True}

    success: bool = Field(..., description="Overall success")
    config: AutoAcceptConfigRequest = Field(..., description="Config used")
    total_processed: int = Field(..., description="Total suggestions processed")
    successful_count: int = Field(..., description="Number of successful actions")
    failed_count: int = Field(..., description="Number of failed actions")
    results: List[BatchActionResult] = Field(..., description="Individual results")
    links: Dict[str, LinkModel] = Field(..., description="HATEOAS links", alias="_links")


# Error Response Models

class ErrorDetail(BaseModel):
    """Error detail model."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Detailed errors")
    status_code: int = Field(..., description="HTTP status code")
