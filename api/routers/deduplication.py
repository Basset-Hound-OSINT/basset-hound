"""
Deduplication Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for duplicate detection and resolution.

Endpoints:
- POST /api/v1/deduplication/find - Find duplicates for an entity
- POST /api/v1/deduplication/find-all - Find all duplicates in a set
- POST /api/v1/deduplication/preview-merge - Preview a merge operation
- POST /api/v1/deduplication/merge - Execute a merge operation
- GET /api/v1/deduplication/history - Get merge history
- GET /api/v1/deduplication/stats - Get service statistics
- GET /api/v1/deduplication/config - Get deduplication configuration
- POST /api/v1/projects/{project_id}/deduplication/report - Generate report
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..services.deduplication import (
    DeduplicationService,
    DeduplicationConfig,
    DuplicateCandidate,
    MergeStrategy,
    MergePreview,
    MergeResult,
    DeduplicationReport,
    MatchType,
    FieldConflictResolution,
    get_deduplication_service,
)


# ----- Pydantic Models -----


class FindDuplicatesRequest(BaseModel):
    """Request model for finding duplicates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "entity_id": "entity-456",
                "entity_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+1-555-123-4567"
                },
                "candidate_entities": [
                    {
                        "id": "entity-789",
                        "profile": {
                            "name": "John D.",
                            "email": "john@example.com"
                        }
                    }
                ],
                "match_types": ["exact", "fuzzy", "phonetic"]
            }
        }
    )

    project_id: str = Field(..., description="Project ID")
    entity_id: str = Field(..., description="Entity ID to find duplicates for")
    entity_data: Dict[str, Any] = Field(..., description="Entity profile data")
    candidate_entities: List[Dict[str, Any]] = Field(..., description="Entities to compare against")
    match_types: Optional[List[str]] = Field(None, description="Matching strategies to use")


class FindAllDuplicatesRequest(BaseModel):
    """Request model for finding all duplicates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "entities": [
                    {"id": "e1", "profile": {"name": "John", "email": "john@example.com"}},
                    {"id": "e2", "profile": {"name": "Jon", "email": "john@example.com"}},
                    {"id": "e3", "profile": {"name": "Jane", "email": "jane@example.com"}}
                ]
            }
        }
    )

    project_id: str = Field(..., description="Project ID")
    entities: List[Dict[str, Any]] = Field(..., description="All entities to check")
    match_types: Optional[List[str]] = Field(None, description="Matching strategies")


class DuplicateCandidateResponse(BaseModel):
    """Response model for a duplicate candidate."""

    entity_id: str
    entity_name: str
    confidence: float
    match_reasons: List[str]
    field_matches: List[Dict[str, Any]]
    suggested_action: str
    metadata: Dict[str, Any]


class FindDuplicatesResponse(BaseModel):
    """Response model for find duplicates."""

    entity_id: str
    candidates: List[DuplicateCandidateResponse]
    total: int


class FindAllDuplicatesResponse(BaseModel):
    """Response model for find all duplicates."""

    duplicate_groups: Dict[str, List[DuplicateCandidateResponse]]
    total_groups: int
    total_duplicates: int


class PreviewMergeRequest(BaseModel):
    """Request model for previewing a merge."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "primary_entity": {
                    "id": "entity-1",
                    "profile": {"name": "John Doe", "email": "john@example.com"}
                },
                "duplicate_entities": [
                    {"id": "entity-2", "profile": {"name": "John D.", "phone": "555-1234"}}
                ],
                "strategy": "keep_primary"
            }
        }
    )

    project_id: str = Field(..., description="Project ID")
    primary_entity: Dict[str, Any] = Field(..., description="Primary entity")
    duplicate_entities: List[Dict[str, Any]] = Field(..., description="Entities to merge")
    strategy: str = Field("keep_primary", description="Merge strategy")
    custom_resolutions: Optional[Dict[str, str]] = Field(None, description="Custom field resolutions")


class MergePreviewResponse(BaseModel):
    """Response model for merge preview."""

    primary_id: str
    duplicate_ids: List[str]
    strategy: str
    conflicts: List[Dict[str, Any]]
    merged_profile: Dict[str, Any]
    relationships_to_transfer: int
    files_to_transfer: int
    warnings: List[str]


class MergeRequest(BaseModel):
    """Request model for executing a merge."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "primary_entity": {
                    "id": "entity-1",
                    "profile": {"name": "John Doe", "email": "john@example.com"}
                },
                "duplicate_entities": [
                    {"id": "entity-2", "profile": {"name": "John D."}}
                ],
                "strategy": "keep_primary"
            }
        }
    )

    project_id: str = Field(..., description="Project ID")
    primary_entity: Dict[str, Any] = Field(..., description="Primary entity")
    duplicate_entities: List[Dict[str, Any]] = Field(..., description="Entities to merge")
    strategy: str = Field("keep_primary", description="Merge strategy")
    custom_resolutions: Optional[Dict[str, Any]] = Field(None, description="Custom resolutions")


class MergeResultResponse(BaseModel):
    """Response model for merge result."""

    success: bool
    merge_id: str
    merged_entity_id: str
    deleted_entity_ids: List[str]
    relationships_transferred: int
    files_transferred: int
    conflicts_resolved: int
    warnings: List[str]
    merged_at: str


class DeduplicationReportResponse(BaseModel):
    """Response model for deduplication report."""

    project_id: str
    total_entities: int
    duplicate_groups: int
    total_duplicates: int
    high_confidence_matches: int
    medium_confidence_matches: int
    low_confidence_matches: int
    top_duplicate_fields: Dict[str, int]
    estimated_reduction: float
    generated_at: str


class DeduplicationConfigResponse(BaseModel):
    """Response model for deduplication configuration."""

    exact_match_weight: float
    fuzzy_match_threshold: float
    phonetic_match_weight: float
    auto_merge_threshold: float
    review_threshold: float
    ignore_threshold: float
    field_weights: Dict[str, float]
    identifier_fields: List[str]


class StatsResponse(BaseModel):
    """Response model for service statistics."""

    cached_candidates: int
    merge_history_count: int
    config: Dict[str, float]


# ----- Helper Functions -----


def candidate_to_response(candidate: DuplicateCandidate) -> DuplicateCandidateResponse:
    """Convert DuplicateCandidate to response model."""
    data = candidate.to_dict()
    return DuplicateCandidateResponse(**data)


def parse_match_types(match_types: Optional[List[str]]) -> List[MatchType]:
    """Parse match type strings to enums."""
    if not match_types:
        return [MatchType.EXACT, MatchType.CASE_INSENSITIVE, MatchType.FUZZY, MatchType.PHONETIC]

    result = []
    for mt in match_types:
        try:
            result.append(MatchType(mt))
        except ValueError:
            pass  # Skip invalid match types
    return result if result else [MatchType.EXACT, MatchType.FUZZY]


def parse_merge_strategy(strategy: str) -> MergeStrategy:
    """Parse merge strategy string to enum."""
    try:
        return MergeStrategy(strategy)
    except ValueError:
        return MergeStrategy.KEEP_PRIMARY


# ----- Dependencies -----


def get_service() -> DeduplicationService:
    """Dependency to get DeduplicationService instance."""
    return get_deduplication_service()


# ----- Router -----


router = APIRouter(
    prefix="/deduplication",
    tags=["deduplication"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Endpoints -----


@router.post(
    "/find",
    response_model=FindDuplicatesResponse,
    summary="Find duplicates for entity",
    description="Find potential duplicate entities for a given entity.",
    responses={
        200: {"description": "Duplicate candidates found"},
    }
)
async def find_duplicates(
    request: FindDuplicatesRequest,
    service: DeduplicationService = Depends(get_service),
):
    """
    Find potential duplicates for an entity.

    Returns candidates sorted by confidence with suggested actions.
    """
    match_types = parse_match_types(request.match_types)

    candidates = await service.find_duplicates(
        project_id=request.project_id,
        entity_id=request.entity_id,
        entity_data=request.entity_data,
        candidate_entities=request.candidate_entities,
        match_types=match_types,
    )

    return FindDuplicatesResponse(
        entity_id=request.entity_id,
        candidates=[candidate_to_response(c) for c in candidates],
        total=len(candidates),
    )


@router.post(
    "/find-all",
    response_model=FindAllDuplicatesResponse,
    summary="Find all duplicates",
    description="Find all duplicate pairs in a set of entities.",
    responses={
        200: {"description": "All duplicates found"},
    }
)
async def find_all_duplicates(
    request: FindAllDuplicatesRequest,
    service: DeduplicationService = Depends(get_service),
):
    """Find all duplicates in a set of entities."""
    match_types = parse_match_types(request.match_types)

    all_duplicates = await service.find_all_duplicates(
        project_id=request.project_id,
        entities=request.entities,
        match_types=match_types,
    )

    # Convert to response
    duplicate_groups = {
        entity_id: [candidate_to_response(c) for c in candidates]
        for entity_id, candidates in all_duplicates.items()
    }

    total_duplicates = sum(len(candidates) for candidates in all_duplicates.values())

    return FindAllDuplicatesResponse(
        duplicate_groups=duplicate_groups,
        total_groups=len(duplicate_groups),
        total_duplicates=total_duplicates,
    )


@router.post(
    "/preview-merge",
    response_model=MergePreviewResponse,
    summary="Preview merge operation",
    description="Preview what a merge operation would do without executing it.",
    responses={
        200: {"description": "Merge preview generated"},
    }
)
async def preview_merge(
    request: PreviewMergeRequest,
    service: DeduplicationService = Depends(get_service),
):
    """Preview a merge operation."""
    strategy = parse_merge_strategy(request.strategy)

    # Convert custom resolutions
    custom_res = None
    if request.custom_resolutions:
        custom_res = {}
        for field_id, res in request.custom_resolutions.items():
            try:
                custom_res[field_id] = FieldConflictResolution(res)
            except ValueError:
                pass

    preview = await service.preview_merge(
        project_id=request.project_id,
        primary_entity=request.primary_entity,
        duplicate_entities=request.duplicate_entities,
        strategy=strategy,
        custom_resolutions=custom_res,
    )

    return MergePreviewResponse(**preview.to_dict())


@router.post(
    "/merge",
    response_model=MergeResultResponse,
    summary="Execute merge operation",
    description="Merge duplicate entities into the primary entity.",
    responses={
        200: {"description": "Merge completed"},
    }
)
async def merge_entities(
    request: MergeRequest,
    service: DeduplicationService = Depends(get_service),
):
    """
    Execute a merge operation.

    Note: This generates merge instructions but doesn't directly modify
    the database. The caller should apply the merged profile and delete
    duplicates using the entity management APIs.
    """
    strategy = parse_merge_strategy(request.strategy)

    result = await service.merge_entities(
        project_id=request.project_id,
        primary_entity=request.primary_entity,
        duplicate_entities=request.duplicate_entities,
        strategy=strategy,
        custom_resolutions=request.custom_resolutions,
    )

    return MergeResultResponse(**result.to_dict())


@router.get(
    "/history",
    response_model=List[MergeResultResponse],
    summary="Get merge history",
    description="Get history of merge operations.",
)
async def get_merge_history(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    service: DeduplicationService = Depends(get_service),
):
    """Get merge history."""
    history = await service.get_merge_history(project_id, limit)
    return [MergeResultResponse(**r.to_dict()) for r in history]


@router.get(
    "/config",
    response_model=DeduplicationConfigResponse,
    summary="Get deduplication configuration",
    description="Get current deduplication configuration.",
)
async def get_config(
    service: DeduplicationService = Depends(get_service),
):
    """Get deduplication configuration."""
    config = service._config
    return DeduplicationConfigResponse(
        exact_match_weight=config.exact_match_weight,
        fuzzy_match_threshold=config.fuzzy_match_threshold,
        phonetic_match_weight=config.phonetic_match_weight,
        auto_merge_threshold=config.auto_merge_threshold,
        review_threshold=config.review_threshold,
        ignore_threshold=config.ignore_threshold,
        field_weights=config.field_weights,
        identifier_fields=config.identifier_fields,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get service statistics",
    description="Get deduplication service statistics.",
)
async def get_stats(
    service: DeduplicationService = Depends(get_service),
):
    """Get service statistics."""
    stats = service.get_stats()
    return StatsResponse(**stats)


@router.post(
    "/clear-cache",
    summary="Clear candidate cache",
    description="Clear cached duplicate candidates.",
    responses={
        200: {"description": "Cache cleared"},
    }
)
async def clear_cache(
    service: DeduplicationService = Depends(get_service),
):
    """Clear the candidate cache."""
    count = service.clear_cache()
    return {"cleared": count, "message": f"Cleared {count} cached candidates"}


@router.get(
    "/match-types",
    summary="List available match types",
    description="List all available matching strategies.",
)
async def list_match_types():
    """List available match types."""
    return {
        "match_types": [
            {"type": mt.value, "description": _get_match_type_description(mt)}
            for mt in MatchType
        ]
    }


@router.get(
    "/merge-strategies",
    summary="List available merge strategies",
    description="List all available merge strategies.",
)
async def list_merge_strategies():
    """List available merge strategies."""
    descriptions = {
        MergeStrategy.KEEP_PRIMARY: "Keep primary entity values when conflicts occur",
        MergeStrategy.KEEP_DUPLICATE: "Keep duplicate entity values when conflicts occur",
        MergeStrategy.KEEP_NEWEST: "Keep the most recently updated values",
        MergeStrategy.KEEP_OLDEST: "Keep the oldest values",
        MergeStrategy.KEEP_LONGEST: "Keep the longest string values",
        MergeStrategy.KEEP_ALL: "Combine all values into arrays",
        MergeStrategy.MANUAL: "Require manual selection for each conflict",
    }
    return {
        "strategies": [
            {"strategy": s.value, "description": descriptions.get(s, "")}
            for s in MergeStrategy
        ]
    }


def _get_match_type_description(mt: MatchType) -> str:
    """Get description for a match type."""
    descriptions = {
        MatchType.EXACT: "Exact string match",
        MatchType.CASE_INSENSITIVE: "Case-insensitive match",
        MatchType.FUZZY: "Fuzzy string matching with Levenshtein distance",
        MatchType.PHONETIC: "Sounds-alike matching",
        MatchType.NORMALIZED: "Match after normalization (lowercase, remove special chars)",
        MatchType.PARTIAL: "Partial string containment",
        MatchType.TOKEN_SET: "Token set ratio matching (word overlap)",
    }
    return descriptions.get(mt, "")


# ----- Project-scoped Router -----


project_dedup_router = APIRouter(
    prefix="/projects/{project_id}/deduplication",
    tags=["deduplication", "projects"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@project_dedup_router.post(
    "/report",
    response_model=DeduplicationReportResponse,
    summary="Generate deduplication report",
    description="Generate a deduplication analysis report for a project.",
)
async def generate_report(
    project_id: str,
    entities: List[Dict[str, Any]],
    service: DeduplicationService = Depends(get_service),
):
    """
    Generate a deduplication report for a project.

    Requires entities to be passed in the request body.
    """
    report = await service.generate_report(
        project_id=project_id,
        entities=entities,
    )

    return DeduplicationReportResponse(**report.to_dict())


@project_dedup_router.post(
    "/scan",
    response_model=FindAllDuplicatesResponse,
    summary="Scan project for duplicates",
    description="Scan all entities in a project for duplicates.",
)
async def scan_project(
    project_id: str,
    entities: List[Dict[str, Any]],
    match_types: Optional[List[str]] = Query(None, description="Match types to use"),
    service: DeduplicationService = Depends(get_service),
):
    """Scan all entities in a project for duplicates."""
    parsed_match_types = parse_match_types(match_types)

    all_duplicates = await service.find_all_duplicates(
        project_id=project_id,
        entities=entities,
        match_types=parsed_match_types,
    )

    duplicate_groups = {
        entity_id: [candidate_to_response(c) for c in candidates]
        for entity_id, candidates in all_duplicates.items()
    }

    total_duplicates = sum(len(candidates) for candidates in all_duplicates.values())

    return FindAllDuplicatesResponse(
        duplicate_groups=duplicate_groups,
        total_groups=len(duplicate_groups),
        total_duplicates=total_duplicates,
    )
