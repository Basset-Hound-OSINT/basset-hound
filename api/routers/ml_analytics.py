"""
Advanced ML Analytics REST API Router (Phase 8, Stream 5).

Provides REST API endpoints for ML analytics including:
- Feature engineering endpoints
- Duplicate detection
- Link prediction
- Community detection
- Anomaly detection

All endpoints include feature flag checking (ENABLE_ML_ANALYTICS).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.config import get_settings
from api.services.ml_analytics_service import get_ml_analytics_service, MLAnalyticsService

logger = logging.getLogger("basset_hound.ml_analytics_api")

router = APIRouter(prefix="/ml-analytics", tags=["ML Analytics"])


# ===== Request/Response Models =====


class FeatureEngineeringRequest(BaseModel):
    """Request for feature engineering."""

    project_id: str = Field(..., description="Project ID")


class FeatureEngineeringResponse(BaseModel):
    """Response for feature engineering."""

    success: bool
    features_extracted: int = 0
    error: Optional[str] = None


class DuplicateDetectionRequest(BaseModel):
    """Request for duplicate detection."""

    project_id: str = Field(..., description="Project ID")
    min_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1) for flagging duplicates",
    )


class DuplicateResult(BaseModel):
    """Single duplicate detection result."""

    entity_id_1: str
    entity_id_2: str
    similarity_score: float
    duplicate_probability: float
    reasoning: dict


class DuplicateDetectionResponse(BaseModel):
    """Response for duplicate detection."""

    success: bool
    count: int = 0
    duplicates: list[DuplicateResult] = []
    error: Optional[str] = None


class LinkPredictionRequest(BaseModel):
    """Request for link prediction."""

    project_id: str = Field(..., description="Project ID")
    entity_id: str = Field(..., description="Entity ID to predict links for")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of predictions to return")


class LinkPredictionResult(BaseModel):
    """Single link prediction result."""

    entity_id_1: str
    entity_id_2: str
    relationship_type: str
    prediction_score: float
    confidence: float
    reasoning: str


class LinkPredictionResponse(BaseModel):
    """Response for link prediction."""

    success: bool
    count: int = 0
    predictions: list[LinkPredictionResult] = []
    error: Optional[str] = None


class CommunityDetectionRequest(BaseModel):
    """Request for community detection."""

    project_id: str = Field(..., description="Project ID")


class CommunityResult(BaseModel):
    """Single community detection result."""

    community_id: int
    entities: list[str]
    size: int
    modularity: float


class CommunityDetectionResponse(BaseModel):
    """Response for community detection."""

    success: bool
    count: int = 0
    communities: list[CommunityResult] = []
    avg_modularity: float = 0.0
    error: Optional[str] = None


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""

    project_id: str = Field(..., description="Project ID")


class AnomalyAlert(BaseModel):
    """Single anomaly alert."""

    entity_id: str
    entity_type: str
    anomaly_type: str
    severity: str
    details: dict


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection."""

    success: bool
    count: int = 0
    alerts: list[AnomalyAlert] = []
    error: Optional[str] = None


# ===== Helper Functions =====


def check_ml_analytics_enabled() -> bool:
    """Check if ML analytics is enabled via feature flag."""
    settings = get_settings()
    enabled = getattr(settings, "enable_ml_analytics", True)
    return enabled


# ===== Endpoints =====


@router.post(
    "/features/extract",
    response_model=FeatureEngineeringResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract ML Features",
    description="Extract and normalize features from entities (name, email, phone, etc.)",
)
async def extract_features(
    request: FeatureEngineeringRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_analytics_service),
) -> FeatureEngineeringResponse:
    """
    Extract ML features from all entities in a project.

    Features extracted:
    - Normalized name
    - Email domain
    - Normalized phone
    - Entity type

    All features are normalized to 0-1 scale.
    """
    if not check_ml_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ML Analytics is disabled (ENABLE_ML_ANALYTICS=false)",
        )

    try:
        result = await ml_service.extract_and_store_features(request.project_id)

        if result.get("success"):
            return FeatureEngineeringResponse(
                success=True,
                features_extracted=result.get("features_extracted", 0),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Feature extraction failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feature extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature extraction failed: {str(e)}",
        )


@router.post(
    "/duplicates/detect",
    response_model=DuplicateDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Duplicates",
    description="Detect potential duplicate entities using ML similarity scoring",
)
async def detect_duplicates(
    request: DuplicateDetectionRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_analytics_service),
) -> DuplicateDetectionResponse:
    """
    Detect potential duplicate entities in a project.

    Uses multiple similarity metrics:
    - Levenshtein distance (names)
    - Email exact match and domain matching
    - Phone exact match
    - Entity type matching

    Scores are computed on 0-100 scale.
    Accuracy target: >90%
    """
    if not check_ml_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ML Analytics is disabled (ENABLE_ML_ANALYTICS=false)",
        )

    try:
        result = await ml_service.detect_duplicates(
            request.project_id, min_score=request.min_score
        )

        if result.get("success"):
            duplicates = [DuplicateResult(**d) for d in result.get("duplicates", [])]
            return DuplicateDetectionResponse(
                success=True,
                count=result.get("count", 0),
                duplicates=duplicates,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Duplicate detection failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Duplicate detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Duplicate detection failed: {str(e)}",
        )


@router.post(
    "/links/predict",
    response_model=LinkPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict Links",
    description="Predict likely relationships for an entity",
)
async def predict_links(
    request: LinkPredictionRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_analytics_service),
) -> LinkPredictionResponse:
    """
    Predict likely relationships for an entity.

    Relationship types:
    - likely_duplicate: High confidence duplicate (>80% similarity)
    - likely_related: Probable connection (60-80% similarity)
    - possibly_related: Potential connection (40-60% similarity)

    Recall target: >70%
    """
    if not check_ml_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ML Analytics is disabled (ENABLE_ML_ANALYTICS=false)",
        )

    try:
        result = await ml_service.predict_relationships(
            request.project_id, request.entity_id, request.top_k
        )

        if result.get("success"):
            predictions = [
                LinkPredictionResult(**p) for p in result.get("predictions", [])
            ]
            return LinkPredictionResponse(
                success=True,
                count=result.get("count", 0),
                predictions=predictions,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Link prediction failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Link prediction failed: {str(e)}",
        )


@router.post(
    "/communities/detect",
    response_model=CommunityDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Communities",
    description="Detect entity clusters using Louvain community detection",
)
async def detect_communities(
    request: CommunityDetectionRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_analytics_service),
) -> CommunityDetectionResponse:
    """
    Detect communities (clusters) in the entity graph.

    Uses Louvain algorithm for optimal community detection.
    Returns communities with modularity scores.

    Modularity interpretation:
    - 0.8-1.0: Strong community structure
    - 0.6-0.8: Good community structure
    - 0.4-0.6: Moderate community structure
    - 0.0-0.4: Weak community structure
    """
    if not check_ml_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ML Analytics is disabled (ENABLE_ML_ANALYTICS=false)",
        )

    try:
        result = await ml_service.detect_communities(request.project_id)

        if result.get("success"):
            communities = [
                CommunityResult(**c) for c in result.get("communities", [])
            ]
            return CommunityDetectionResponse(
                success=True,
                count=result.get("count", 0),
                communities=communities,
                avg_modularity=result.get("avg_modularity", 0.0),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Community detection failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Community detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Community detection failed: {str(e)}",
        )


@router.post(
    "/anomalies/detect",
    response_model=AnomalyDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Anomalies",
    description="Detect unusual entity patterns (rapid updates, sparse data, etc.)",
)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_analytics_service),
) -> AnomalyDetectionResponse:
    """
    Detect anomalies in entity data patterns.

    Detected anomalies:
    - rapid_updates: >50 updates per hour (severity: medium/high)
    - sparse_data: Missing >50% of required fields (severity: low)

    Alerts can be integrated into monitoring/alerting systems.
    """
    if not check_ml_analytics_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ML Analytics is disabled (ENABLE_ML_ANALYTICS=false)",
        )

    try:
        result = await ml_service.detect_anomalies(request.project_id)

        if result.get("success"):
            alerts = [AnomalyAlert(**a) for a in result.get("alerts", [])]
            return AnomalyDetectionResponse(
                success=True,
                count=result.get("count", 0),
                alerts=alerts,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Anomaly detection failed"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}",
        )


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Check ML Analytics Status",
    description="Check if ML Analytics is enabled and available",
)
async def check_status() -> dict:
    """Check ML Analytics availability and status."""
    enabled = check_ml_analytics_enabled()

    return {
        "enabled": enabled,
        "status": "active" if enabled else "disabled",
        "features": {
            "feature_engineering": enabled,
            "duplicate_detection": enabled,
            "link_prediction": enabled,
            "community_detection": enabled,
            "anomaly_detection": enabled,
        },
    }
