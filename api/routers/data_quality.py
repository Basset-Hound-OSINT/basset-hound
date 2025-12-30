"""
Data Quality Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for data quality assessment and reporting.

Endpoints:
- POST /api/v1/data-quality/score - Score a single entity
- POST /api/v1/data-quality/score/batch - Score multiple entities
- GET /api/v1/data-quality/config - Get quality configuration
- PUT /api/v1/data-quality/config - Update quality configuration
- GET /api/v1/data-quality/sources - List data sources with reliability
- PUT /api/v1/data-quality/sources/{source} - Update source reliability
- GET /api/v1/data-quality/stats - Get service statistics
- POST /api/v1/data-quality/compare - Compare two entities' quality
- GET /api/v1/projects/{project_id}/data-quality/report - Get project quality report
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..services.data_quality import (
    DataQualityService,
    DataSource,
    QualityConfig,
    QualityDimension,
    QualityScore,
    ProjectQualityReport,
    SOURCE_RELIABILITY,
    get_data_quality_service,
)


# ----- Pydantic Models -----


class EntityScoreRequest(BaseModel):
    """Request model for scoring an entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "entity-123",
                "project_id": "project-456",
                "entity_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+1-555-123-4567"
                },
                "metadata": {
                    "source": "manual_entry",
                    "updated_at": "2024-01-15T10:00:00Z"
                }
            }
        }
    )

    entity_id: str = Field(..., description="Entity ID")
    project_id: str = Field(..., description="Project ID")
    entity_data: Dict[str, Any] = Field(..., description="Entity profile data")
    field_schema: Optional[List[Dict[str, Any]]] = Field(None, description="Optional field schema", alias="schema")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class BatchScoreRequest(BaseModel):
    """Request model for scoring multiple entities."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-456",
                "entities": [
                    {
                        "id": "entity-1",
                        "profile": {"name": "John Doe", "email": "john@example.com"}
                    },
                    {
                        "id": "entity-2",
                        "profile": {"name": "Jane Smith"}
                    }
                ]
            }
        }
    )

    project_id: str = Field(..., description="Project ID")
    entities: List[Dict[str, Any]] = Field(..., description="Entities to score")
    field_schema: Optional[List[Dict[str, Any]]] = Field(None, description="Optional schema", alias="schema")


class QualityScoreResponse(BaseModel):
    """Response model for a quality score."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "entity-123",
                "project_id": "project-456",
                "overall_score": 85.5,
                "grade": "B",
                "dimensions": {
                    "completeness": {"score": 90.0, "weight": 0.3, "details": "9/10 fields filled"},
                    "freshness": {"score": 80.0, "weight": 0.2, "details": "Updated 5 days ago"},
                },
                "recommendations": ["Fill in missing phone number"],
                "issues": [],
                "scored_at": "2024-01-15T10:00:00Z"
            }
        }
    )

    entity_id: str
    project_id: str
    overall_score: float
    grade: str
    dimensions: Dict[str, Dict[str, Any]]
    field_count: int
    filled_fields: int
    recommendations: List[str]
    issues: List[str]
    scored_at: str


class BatchScoreResponse(BaseModel):
    """Response model for batch scoring."""

    scores: List[QualityScoreResponse]
    total: int
    average_score: float
    grade_distribution: Dict[str, int]


class QualityConfigResponse(BaseModel):
    """Response model for quality configuration."""

    completeness_weight: float
    freshness_weight: float
    accuracy_weight: float
    consistency_weight: float
    uniqueness_weight: float
    validity_weight: float
    freshness_days_excellent: int
    freshness_days_good: int
    freshness_days_acceptable: int
    freshness_days_stale: int
    grade_a_threshold: float
    grade_b_threshold: float
    grade_c_threshold: float
    grade_d_threshold: float


class UpdateConfigRequest(BaseModel):
    """Request model for updating configuration."""

    completeness_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    freshness_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    accuracy_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    consistency_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    uniqueness_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    validity_weight: Optional[float] = Field(None, ge=0.0, le=1.0)


class DataSourceResponse(BaseModel):
    """Response model for a data source."""

    source: str
    reliability: float
    description: str


class UpdateSourceRequest(BaseModel):
    """Request model for updating source reliability."""

    reliability: float = Field(..., ge=0.0, le=1.0, description="Reliability score")


class CompareRequest(BaseModel):
    """Request model for comparing two entities."""

    entity1: EntityScoreRequest
    entity2: EntityScoreRequest


class CompareResponse(BaseModel):
    """Response model for entity comparison."""

    entity1: Dict[str, Any]
    entity2: Dict[str, Any]
    difference: float
    better_entity: str
    dimension_comparison: Dict[str, Dict[str, Any]]


class ProjectQualityReportResponse(BaseModel):
    """Response model for project quality report."""

    project_id: str
    entity_count: int
    average_score: float
    grade_distribution: Dict[str, int]
    dimension_averages: Dict[str, float]
    top_issues: List[str]
    top_recommendations: List[str]
    low_quality_entities: List[str]
    high_quality_entities: List[str]
    generated_at: str


class StatsResponse(BaseModel):
    """Response model for service statistics."""

    cached_scores: int
    cache_ttl_seconds: int
    config: Dict[str, float]


# ----- Helper Functions -----


def score_to_response(score: QualityScore) -> QualityScoreResponse:
    """Convert QualityScore to response model."""
    data = score.to_dict()
    return QualityScoreResponse(**data)


# ----- Dependencies -----


def get_service() -> DataQualityService:
    """Dependency to get DataQualityService instance."""
    return get_data_quality_service()


# ----- Router -----


router = APIRouter(
    prefix="/data-quality",
    tags=["data-quality"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Endpoints -----


@router.post(
    "/score",
    response_model=QualityScoreResponse,
    summary="Score entity quality",
    description="Calculate quality score for a single entity.",
    responses={
        200: {"description": "Quality score calculated"},
    }
)
async def score_entity(
    request: EntityScoreRequest,
    service: DataQualityService = Depends(get_service),
):
    """
    Score a single entity's data quality.

    Returns overall score (0-100), letter grade, and dimension breakdowns.
    """
    score = await service.score_entity(
        project_id=request.project_id,
        entity_id=request.entity_id,
        entity_data=request.entity_data,
        schema=request.field_schema,
        metadata=request.metadata,
    )

    return score_to_response(score)


@router.post(
    "/score/batch",
    response_model=BatchScoreResponse,
    summary="Score multiple entities",
    description="Calculate quality scores for multiple entities.",
    responses={
        200: {"description": "Quality scores calculated"},
    }
)
async def score_entities_batch(
    request: BatchScoreRequest,
    service: DataQualityService = Depends(get_service),
):
    """Score multiple entities in batch."""
    scores = await service.score_entities_batch(
        project_id=request.project_id,
        entities=request.entities,
        schema=request.field_schema,
    )

    # Calculate statistics
    total = len(scores)
    avg_score = sum(s.overall_score for s in scores) / total if total > 0 else 0.0

    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for score in scores:
        grade_dist[score.grade] = grade_dist.get(score.grade, 0) + 1

    return BatchScoreResponse(
        scores=[score_to_response(s) for s in scores],
        total=total,
        average_score=round(avg_score, 2),
        grade_distribution=grade_dist,
    )


@router.get(
    "/config",
    response_model=QualityConfigResponse,
    summary="Get quality configuration",
    description="Get current quality scoring configuration.",
)
async def get_config(
    service: DataQualityService = Depends(get_service),
):
    """Get quality configuration."""
    config = service._config
    return QualityConfigResponse(
        completeness_weight=config.completeness_weight,
        freshness_weight=config.freshness_weight,
        accuracy_weight=config.accuracy_weight,
        consistency_weight=config.consistency_weight,
        uniqueness_weight=config.uniqueness_weight,
        validity_weight=config.validity_weight,
        freshness_days_excellent=config.freshness_days_excellent,
        freshness_days_good=config.freshness_days_good,
        freshness_days_acceptable=config.freshness_days_acceptable,
        freshness_days_stale=config.freshness_days_stale,
        grade_a_threshold=config.grade_a_threshold,
        grade_b_threshold=config.grade_b_threshold,
        grade_c_threshold=config.grade_c_threshold,
        grade_d_threshold=config.grade_d_threshold,
    )


@router.put(
    "/config",
    response_model=QualityConfigResponse,
    summary="Update quality configuration",
    description="Update quality scoring weights. Weights should sum to 1.0.",
)
async def update_config(
    request: UpdateConfigRequest,
    service: DataQualityService = Depends(get_service),
):
    """Update quality configuration."""
    config = service._config

    if request.completeness_weight is not None:
        config.completeness_weight = request.completeness_weight
    if request.freshness_weight is not None:
        config.freshness_weight = request.freshness_weight
    if request.accuracy_weight is not None:
        config.accuracy_weight = request.accuracy_weight
    if request.consistency_weight is not None:
        config.consistency_weight = request.consistency_weight
    if request.uniqueness_weight is not None:
        config.uniqueness_weight = request.uniqueness_weight
    if request.validity_weight is not None:
        config.validity_weight = request.validity_weight

    # Validate weights sum to ~1.0
    total = (
        config.completeness_weight +
        config.freshness_weight +
        config.accuracy_weight +
        config.consistency_weight +
        config.uniqueness_weight +
        config.validity_weight
    )
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weights must sum to 1.0 (current sum: {total:.2f})"
        )

    return await get_config(service)


@router.get(
    "/sources",
    response_model=List[DataSourceResponse],
    summary="List data sources",
    description="List all data sources with their reliability scores.",
)
async def list_sources(
    service: DataQualityService = Depends(get_service),
):
    """List data sources with reliability."""
    sources = []
    descriptions = {
        DataSource.MANUAL_ENTRY: "User-entered data",
        DataSource.MALTEGO: "Maltego investigations",
        DataSource.SPIDERFOOT: "SpiderFoot scans",
        DataSource.THEHARVESTER: "TheHarvester discovery",
        DataSource.SHODAN: "Shodan network data",
        DataSource.HIBP: "Have I Been Pwned breach data",
        DataSource.CSV_IMPORT: "Generic CSV imports",
        DataSource.JSON_IMPORT: "Generic JSON imports",
        DataSource.API_ENRICHMENT: "External API enrichment",
        DataSource.OSINT_TOOL: "Generic OSINT tools",
        DataSource.UNKNOWN: "Unknown source",
    }

    for source in DataSource:
        reliability = service.get_source_reliability(source)
        sources.append(DataSourceResponse(
            source=source.value,
            reliability=reliability,
            description=descriptions.get(source, ""),
        ))

    return sources


@router.put(
    "/sources/{source}",
    response_model=DataSourceResponse,
    summary="Update source reliability",
    description="Update reliability score for a data source.",
    responses={
        200: {"description": "Source reliability updated"},
        404: {"description": "Unknown data source"},
    }
)
async def update_source_reliability(
    source: str,
    request: UpdateSourceRequest,
    service: DataQualityService = Depends(get_service),
):
    """Update source reliability."""
    try:
        data_source = DataSource(source)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown data source: {source}"
        )

    service.set_source_reliability(data_source, request.reliability)

    return DataSourceResponse(
        source=data_source.value,
        reliability=request.reliability,
        description="",
    )


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare entity quality",
    description="Compare quality scores of two entities.",
)
async def compare_entities(
    request: CompareRequest,
    service: DataQualityService = Depends(get_service),
):
    """Compare quality between two entities."""
    # Score both entities
    score1 = await service.score_entity(
        project_id=request.entity1.project_id,
        entity_id=request.entity1.entity_id,
        entity_data=request.entity1.entity_data,
        schema=request.entity1.field_schema,
        metadata=request.entity1.metadata,
    )

    score2 = await service.score_entity(
        project_id=request.entity2.project_id,
        entity_id=request.entity2.entity_id,
        entity_data=request.entity2.entity_data,
        schema=request.entity2.field_schema,
        metadata=request.entity2.metadata,
    )

    # Compare
    comparison = await service.compare_quality(score1, score2)

    return CompareResponse(**comparison)


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get service statistics",
    description="Get data quality service statistics.",
)
async def get_stats(
    service: DataQualityService = Depends(get_service),
):
    """Get service statistics."""
    stats = service.get_stats()
    return StatsResponse(**stats)


@router.post(
    "/clear-cache",
    summary="Clear score cache",
    description="Clear cached quality scores.",
    responses={
        200: {"description": "Cache cleared"},
    }
)
async def clear_cache(
    service: DataQualityService = Depends(get_service),
):
    """Clear the score cache."""
    count = service.clear_cache()
    return {"cleared": count, "message": f"Cleared {count} cached scores"}


# ----- Project-scoped Router -----


project_data_quality_router = APIRouter(
    prefix="/projects/{project_id}/data-quality",
    tags=["data-quality", "projects"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@project_data_quality_router.post(
    "/report",
    response_model=ProjectQualityReportResponse,
    summary="Generate project quality report",
    description="Generate a data quality report for a project.",
)
async def generate_project_report(
    project_id: str,
    entities: List[Dict[str, Any]],
    service: DataQualityService = Depends(get_service),
):
    """
    Generate a quality report for a project.

    Requires entities to be passed in the request body.
    """
    # Score all entities
    scores = await service.score_entities_batch(
        project_id=project_id,
        entities=entities,
    )

    # Generate report
    report = await service.get_project_quality_report(
        project_id=project_id,
        entity_scores=scores,
    )

    return ProjectQualityReportResponse(**report.to_dict())


@project_data_quality_router.get(
    "/trends",
    summary="Get quality trends",
    description="Get quality trends over time for a project.",
)
async def get_quality_trends(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    service: DataQualityService = Depends(get_service),
):
    """Get quality trends for a project."""
    trends = await service.get_quality_trends(project_id, days)
    return trends
