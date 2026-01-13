"""
ML Analytics Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for ML-based analytics including:
- Query suggestions with confidence scores
- Search pattern detection
- Entity insights
- Related search recommendations
- Query clustering
- Zero-result prediction

Endpoints:
- GET /api/v1/ml/suggest - Get query suggestions
- GET /api/v1/ml/patterns - Detect search patterns
- GET /api/v1/ml/entities/{entity_id}/insights - Get entity insights
- GET /api/v1/ml/related - Get related search suggestions
- POST /api/v1/ml/cluster - Cluster provided queries
- GET /api/v1/ml/predict-zero - Predict zero results
- GET /api/v1/ml/similarity - Calculate query similarity
- GET /api/v1/ml/stats - Get ML analytics statistics
- POST /api/v1/ml/record - Record a query for ML training
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..services.ml_analytics import (
    MLAnalyticsService,
    QuerySuggestion,
    SearchPattern,
    EntityInsight,
    SuggestionSource,
    PatternType,
    InsightType,
    get_ml_analytics,
)


# ==================== Request/Response Models ====================


class QuerySuggestionResponse(BaseModel):
    """Response model for a single query suggestion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestion": "john doe email",
                "confidence": 0.85,
                "source": "history",
                "related_queries": ["john doe", "john doe phone"]
            }
        }
    )

    suggestion: str = Field(..., description="The suggested query string")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    source: str = Field(..., description="Source of the suggestion")
    related_queries: List[str] = Field(default_factory=list, description="Related queries")


class SuggestionsResponse(BaseModel):
    """Response model for query suggestions endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "joh",
                "suggestions": [
                    {
                        "suggestion": "john doe",
                        "confidence": 0.92,
                        "source": "history",
                        "related_queries": ["john smith"]
                    }
                ],
                "count": 1
            }
        }
    )

    query: str = Field(..., description="Original partial query")
    suggestions: List[QuerySuggestionResponse] = Field(
        default_factory=list, description="List of suggestions"
    )
    count: int = Field(0, ge=0, description="Number of suggestions returned")


class SearchPatternResponse(BaseModel):
    """Response model for a detected search pattern."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern_type": "trending",
                "description": "Rising interest in cryptocurrency searches",
                "frequency": 45,
                "examples": ["bitcoin wallet", "ethereum address"],
                "insight": "15% increase in crypto searches"
            }
        }
    )

    pattern_type: str = Field(..., description="Type of pattern")
    description: str = Field(..., description="Pattern description")
    frequency: int = Field(..., ge=0, description="Pattern frequency")
    examples: List[str] = Field(default_factory=list, description="Example queries")
    insight: str = Field("", description="Actionable insight")


class PatternsResponse(BaseModel):
    """Response model for patterns endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_range_days": 7,
                "patterns": [],
                "count": 0
            }
        }
    )

    time_range_days: Optional[int] = Field(None, description="Time range analyzed")
    patterns: List[SearchPatternResponse] = Field(
        default_factory=list, description="Detected patterns"
    )
    count: int = Field(0, ge=0, description="Number of patterns detected")


class EntityInsightResponse(BaseModel):
    """Response model for an entity insight."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "person-123",
                "insight_type": "related_entity",
                "description": "Frequently searched together with Jane Smith",
                "confidence": 0.78,
                "related_entities": ["person-456"],
                "recommended_actions": ["Review relationship"]
            }
        }
    )

    entity_id: str = Field(..., description="Entity ID")
    insight_type: str = Field(..., description="Type of insight")
    description: str = Field(..., description="Insight description")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    related_entities: List[str] = Field(default_factory=list, description="Related entities")
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended actions"
    )


class InsightsResponse(BaseModel):
    """Response model for entity insights endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "person-123",
                "insights": [],
                "count": 0
            }
        }
    )

    entity_id: str = Field(..., description="Entity ID analyzed")
    insights: List[EntityInsightResponse] = Field(
        default_factory=list, description="List of insights"
    )
    count: int = Field(0, ge=0, description="Number of insights")


class RelatedSearchesResponse(BaseModel):
    """Response model for related searches endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "related_searches": ["jane doe", "john smith"],
                "count": 2
            }
        }
    )

    query: str = Field(..., description="Original query")
    related_searches: List[str] = Field(
        default_factory=list, description="Related search suggestions"
    )
    count: int = Field(0, ge=0, description="Number of suggestions")


class ClusterRequest(BaseModel):
    """Request model for clustering queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queries": ["john doe", "john smith", "jane doe"],
                "threshold": 0.6
            }
        }
    )

    queries: List[str] = Field(..., min_length=1, description="Queries to cluster")
    threshold: float = Field(
        0.6, ge=0.0, le=1.0, description="Similarity threshold"
    )


class ClusterResponse(BaseModel):
    """Response model for query clustering endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "clusters": {
                    "john doe": ["john doe", "john smith"],
                    "jane doe": ["jane doe"]
                },
                "cluster_count": 2,
                "total_queries": 3
            }
        }
    )

    clusters: Dict[str, List[str]] = Field(
        default_factory=dict, description="Clusters (key=representative)"
    )
    cluster_count: int = Field(0, ge=0, description="Number of clusters")
    total_queries: int = Field(0, ge=0, description="Total queries clustered")


class ZeroPredictionResponse(BaseModel):
    """Response model for zero-result prediction endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "asdfghjkl",
                "zero_probability": 0.75,
                "confidence_level": "high",
                "recommendation": "Consider refining your query"
            }
        }
    )

    query: str = Field(..., description="Query analyzed")
    zero_probability: float = Field(
        ..., ge=0, le=1, description="Probability of zero results"
    )
    confidence_level: str = Field(..., description="Confidence level")
    recommendation: str = Field("", description="Recommendation based on prediction")


class SimilarityResponse(BaseModel):
    """Response model for query similarity endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query1": "john doe",
                "query2": "john smith",
                "similarity": 0.72,
                "interpretation": "Moderately similar"
            }
        }
    )

    query1: str = Field(..., description="First query")
    query2: str = Field(..., description="Second query")
    similarity: float = Field(..., ge=0, le=1, description="Similarity score")
    interpretation: str = Field(..., description="Human-readable interpretation")


class StatisticsResponse(BaseModel):
    """Response model for ML analytics statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_queries_recorded": 1500,
                "unique_queries": 450,
                "zero_result_queries": 25,
                "entities_tracked": 120,
                "vocabulary_size": 800,
                "ngram_counts": {"2": 1200, "3": 800}
            }
        }
    )

    total_queries_recorded: int = Field(0, ge=0, description="Total queries in history")
    unique_queries: int = Field(0, ge=0, description="Unique queries")
    zero_result_queries: int = Field(0, ge=0, description="Zero-result queries")
    entities_tracked: int = Field(0, ge=0, description="Entities with search data")
    vocabulary_size: int = Field(0, ge=0, description="Vocabulary size")
    ngram_counts: Dict[str, int] = Field(
        default_factory=dict, description="N-gram counts"
    )


class RecordQueryRequest(BaseModel):
    """Request model for recording a query."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "john doe",
                "result_count": 5,
                "clicked_entities": ["entity-1"],
                "entity_types": ["Person"],
                "project_id": "project-123"
            }
        }
    )

    query: str = Field(..., min_length=1, description="Query to record")
    result_count: int = Field(0, ge=0, description="Number of results")
    clicked_entities: List[str] = Field(
        default_factory=list, description="Clicked entity IDs"
    )
    entity_types: List[str] = Field(
        default_factory=list, description="Entity types searched"
    )
    project_id: Optional[str] = Field(None, description="Project ID")


class RecordQueryResponse(BaseModel):
    """Response model for recording a query."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Query recorded successfully"
            }
        }
    )

    success: bool = Field(..., description="Whether recording succeeded")
    message: str = Field(..., description="Status message")


# ==================== Dependency ====================


def get_ml_service() -> MLAnalyticsService:
    """
    Dependency to get the MLAnalyticsService instance.

    Returns the singleton MLAnalyticsService.
    """
    return get_ml_analytics()


# ==================== Router ====================


router = APIRouter(
    prefix="/ml",
    tags=["ml-analytics"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ==================== Endpoints ====================


@router.get(
    "/suggest",
    response_model=SuggestionsResponse,
    summary="Get query suggestions",
    description=(
        "Returns intelligent query suggestions based on partial input. "
        "Combines prefix matching, historical patterns, and semantic similarity."
    ),
    responses={
        200: {"description": "Suggestions returned successfully"},
    }
)
async def get_suggestions(
    q: str = Query(..., min_length=1, description="Partial query to get suggestions for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions to return"),
    project_id: Optional[str] = Query(None, description="Optional project ID for scoping"),
    user_history: Optional[str] = Query(
        None, description="Comma-separated list of user's recent queries"
    ),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Get query suggestions based on partial input.

    - **q**: Partial query string to complete (required)
    - **limit**: Maximum number of suggestions (1-50, default 10)
    - **project_id**: Optional project ID for project-specific suggestions
    - **user_history**: Comma-separated recent user queries for personalization
    """
    try:
        # Parse user history
        history = None
        if user_history:
            history = [h.strip() for h in user_history.split(",") if h.strip()]

        suggestions = ml_service.suggest_queries(
            partial_query=q,
            user_history=history,
            limit=limit,
            project_id=project_id,
        )

        return SuggestionsResponse(
            query=q,
            suggestions=[
                QuerySuggestionResponse(
                    suggestion=s.suggestion,
                    confidence=s.confidence,
                    source=s.source.value,
                    related_queries=s.related_queries,
                )
                for s in suggestions
            ],
            count=len(suggestions),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get(
    "/patterns",
    response_model=PatternsResponse,
    summary="Detect search patterns",
    description=(
        "Identifies common search patterns including trending topics, "
        "seasonal patterns, and common query types."
    ),
    responses={
        200: {"description": "Patterns returned successfully"},
    }
)
async def detect_patterns(
    days: Optional[int] = Query(
        None, ge=1, le=365, description="Time range in days (None = all time)"
    ),
    project_id: Optional[str] = Query(None, description="Optional project ID"),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Detect search patterns from query history.

    - **days**: Number of days to analyze (default: all time)
    - **project_id**: Optional project ID for project-specific patterns
    """
    try:
        patterns = ml_service.detect_search_patterns(
            time_range=days,
            project_id=project_id,
        )

        return PatternsResponse(
            time_range_days=days,
            patterns=[
                SearchPatternResponse(
                    pattern_type=p.pattern_type.value,
                    description=p.description,
                    frequency=p.frequency,
                    examples=p.examples,
                    insight=p.insight,
                )
                for p in patterns
            ],
            count=len(patterns),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect patterns: {str(e)}"
        )


@router.get(
    "/entities/{entity_id}/insights",
    response_model=InsightsResponse,
    summary="Get entity insights",
    description=(
        "Returns ML-generated insights about an entity including "
        "related entities, search frequency, and data quality issues."
    ),
    responses={
        200: {"description": "Insights returned successfully"},
    }
)
async def get_entity_insights(
    entity_id: str,
    project_id: Optional[str] = Query(None, description="Optional project ID"),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Get insights about a specific entity.

    - **entity_id**: Entity ID to analyze (path parameter)
    - **project_id**: Optional project ID for context
    """
    try:
        insights = ml_service.get_entity_insights(
            entity_id=entity_id,
            project_id=project_id,
        )

        return InsightsResponse(
            entity_id=entity_id,
            insights=[
                EntityInsightResponse(
                    entity_id=i.entity_id,
                    insight_type=i.insight_type.value,
                    description=i.description,
                    confidence=i.confidence,
                    related_entities=i.related_entities,
                    recommended_actions=i.recommended_actions,
                )
                for i in insights
            ],
            count=len(insights),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity insights: {str(e)}"
        )


@router.get(
    "/related",
    response_model=RelatedSearchesResponse,
    summary="Get related search suggestions",
    description=(
        "Returns related search suggestions based on query and optional results."
    ),
    responses={
        200: {"description": "Related searches returned successfully"},
    }
)
async def get_related_searches(
    q: str = Query(..., min_length=1, description="Query to find related searches for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum related searches"),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Get related search suggestions.

    - **q**: Original query (required)
    - **limit**: Maximum number of related searches (1-20, default 5)
    """
    try:
        related = ml_service.recommend_related_searches(
            query=q,
            limit=limit,
        )

        return RelatedSearchesResponse(
            query=q,
            related_searches=related,
            count=len(related),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related searches: {str(e)}"
        )


@router.post(
    "/cluster",
    response_model=ClusterResponse,
    summary="Cluster similar queries",
    description=(
        "Groups similar queries together using similarity-based clustering."
    ),
    responses={
        200: {"description": "Clustering completed successfully"},
    }
)
async def cluster_queries(
    request: ClusterRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Cluster similar queries together.

    - **queries**: List of queries to cluster (required)
    - **threshold**: Similarity threshold for clustering (0-1, default 0.6)
    """
    try:
        clusters = ml_service.cluster_similar_queries(
            queries=request.queries,
            threshold=request.threshold,
        )

        return ClusterResponse(
            clusters=clusters,
            cluster_count=len(clusters),
            total_queries=len(request.queries),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cluster queries: {str(e)}"
        )


@router.get(
    "/predict-zero",
    response_model=ZeroPredictionResponse,
    summary="Predict zero results",
    description=(
        "Predicts the likelihood that a query will return zero results "
        "based on historical patterns and similarity analysis."
    ),
    responses={
        200: {"description": "Prediction returned successfully"},
    }
)
async def predict_zero_results(
    q: str = Query(..., min_length=1, description="Query to analyze"),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Predict likelihood of zero results for a query.

    - **q**: Query to analyze (required)
    """
    try:
        probability = ml_service.predict_zero_results(q)

        # Determine confidence level
        if probability >= 0.8:
            confidence_level = "high"
            recommendation = "Consider refining your query or checking for typos"
        elif probability >= 0.5:
            confidence_level = "medium"
            recommendation = "Results uncertain - try alternative search terms"
        else:
            confidence_level = "low"
            recommendation = "Query is likely to return results"

        return ZeroPredictionResponse(
            query=q,
            zero_probability=round(probability, 3),
            confidence_level=confidence_level,
            recommendation=recommendation,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to predict zero results: {str(e)}"
        )


@router.get(
    "/similarity",
    response_model=SimilarityResponse,
    summary="Calculate query similarity",
    description=(
        "Calculates similarity between two queries using a combination of "
        "Jaccard similarity, edit distance, and TF-IDF cosine similarity."
    ),
    responses={
        200: {"description": "Similarity calculated successfully"},
    }
)
async def calculate_similarity(
    q1: str = Query(..., min_length=1, description="First query"),
    q2: str = Query(..., min_length=1, description="Second query"),
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Calculate similarity between two queries.

    - **q1**: First query (required)
    - **q2**: Second query (required)
    """
    try:
        similarity = ml_service.calculate_query_similarity(q1, q2)

        # Interpret similarity
        if similarity >= 0.9:
            interpretation = "Very similar (near-duplicates)"
        elif similarity >= 0.7:
            interpretation = "Highly similar"
        elif similarity >= 0.5:
            interpretation = "Moderately similar"
        elif similarity >= 0.3:
            interpretation = "Somewhat similar"
        else:
            interpretation = "Not similar"

        return SimilarityResponse(
            query1=q1,
            query2=q2,
            similarity=round(similarity, 4),
            interpretation=interpretation,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate similarity: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=StatisticsResponse,
    summary="Get ML analytics statistics",
    description="Returns statistics about the ML analytics service state.",
    responses={
        200: {"description": "Statistics returned successfully"},
    }
)
async def get_statistics(
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Get ML analytics service statistics.
    """
    try:
        stats = ml_service.get_statistics()

        # Convert ngram_counts keys to strings for JSON compatibility
        ngram_counts = {str(k): v for k, v in stats.get("ngram_counts", {}).items()}

        return StatisticsResponse(
            total_queries_recorded=stats.get("total_queries_recorded", 0),
            unique_queries=stats.get("unique_queries", 0),
            zero_result_queries=stats.get("zero_result_queries", 0),
            entities_tracked=stats.get("entities_tracked", 0),
            vocabulary_size=stats.get("vocabulary_size", 0),
            ngram_counts=ngram_counts,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post(
    "/record",
    response_model=RecordQueryResponse,
    summary="Record a query for ML training",
    description=(
        "Records a search query and its results for ML model training. "
        "This data is used to improve suggestions and predictions."
    ),
    responses={
        200: {"description": "Query recorded successfully"},
    }
)
async def record_query(
    request: RecordQueryRequest,
    ml_service: MLAnalyticsService = Depends(get_ml_service),
):
    """
    Record a query for ML training.

    - **query**: Query string (required)
    - **result_count**: Number of results returned
    - **clicked_entities**: IDs of clicked entities
    - **entity_types**: Entity types searched
    - **project_id**: Optional project ID
    """
    try:
        ml_service.record_query(
            query=request.query,
            result_count=request.result_count,
            clicked_entities=request.clicked_entities,
            entity_types=request.entity_types,
            project_id=request.project_id,
        )

        return RecordQueryResponse(
            success=True,
            message="Query recorded successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record query: {str(e)}"
        )
