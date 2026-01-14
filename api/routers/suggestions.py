"""
Smart Suggestions REST API Router (Phase 44).

Provides production-ready REST API endpoints for the Smart Suggestions system
following 2026 best practices with HATEOAS support, pagination, rate limiting,
and comprehensive error handling.

Key Features:
- 9 REST endpoints for suggestions and linking actions
- HATEOAS-compliant responses with navigation links
- Smart pagination with next/prev links
- Rate limiting (100 requests/minute per IP)
- Input validation with Pydantic models
- Comprehensive error handling
- Performance optimized (<500ms response time)
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from api.dependencies import get_neo4j_handler
from api.models.suggestion import (
    ActionTypeEnum,
    AutoAcceptConfigRequest,
    AutoAcceptExecuteResponse,
    AutoAcceptPreviewItem,
    AutoAcceptPreviewResponse,
    BatchAcceptSuggestionsRequest,
    BatchAcceptSuggestionsResponse,
    BatchActionResult,
    ConfidenceLevelEnum,
    ConfidenceGroupResponse,
    CreateRelationshipRequest,
    CreateRelationshipResponse,
    DismissedSuggestionsData,
    DismissedSuggestionsResponse,
    DismissSuggestionRequest,
    DismissSuggestionResponse,
    EntitySuggestionsData,
    EntitySuggestionsResponse,
    ErrorResponse,
    LinkDataItemsRequest,
    LinkDataItemsResponse,
    LinkingHistoryData,
    LinkingHistoryResponse,
    LinkModel,
    LinkOrphanToEntityRequest,
    LinkOrphanToEntityResponse,
    MergeEntitiesRequest,
    MergeEntitiesResponse,
    OrphanSuggestionsData,
    OrphanSuggestionsResponse,
    PaginationModel,
    SuggestionMatchResponse,
)
from api.services.linking_service import LinkingService
from api.services.neo4j_service import AsyncNeo4jService
from api.services.suggestion_service import SuggestionService

logger = logging.getLogger("basset_hound.suggestions_api")

# Create router
router = APIRouter(prefix="/suggestions", tags=["Smart Suggestions"])

# Rate limiting storage (in production, use Redis or similar)
_rate_limit_storage: dict = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100


# Rate limiting middleware
def check_rate_limit(request: Request) -> None:
    """
    Check if the request exceeds rate limits.

    Rate limit: 100 requests per minute per IP.

    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    # Clean up old entries
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    _rate_limit_storage[client_ip] = [
        t for t in _rate_limit_storage.get(client_ip, []) if t > cutoff_time
    ]

    # Check rate limit
    request_times = _rate_limit_storage.get(client_ip, [])
    if len(request_times) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per minute.",
        )

    # Record this request
    request_times.append(current_time)
    _rate_limit_storage[client_ip] = request_times


# Helper functions for HATEOAS links
def build_entity_suggestions_links(entity_id: str, base_url: str) -> dict:
    """Build HATEOAS links for entity suggestions response."""
    return {
        "self": LinkModel(href=f"{base_url}/api/v1/suggestions/entity/{entity_id}"),
        "entity": LinkModel(href=f"{base_url}/api/v1/entities/{entity_id}"),
        "dismiss": LinkModel(
            href=f"{base_url}/api/v1/suggestions/{{suggestion_id}}/dismiss",
            method="POST"
        ),
        "dismissed": LinkModel(href=f"{base_url}/api/v1/suggestions/dismissed/{entity_id}"),
    }


def build_orphan_suggestions_links(orphan_id: str, base_url: str) -> dict:
    """Build HATEOAS links for orphan suggestions response."""
    return {
        "self": LinkModel(href=f"{base_url}/api/v1/suggestions/orphan/{orphan_id}"),
        "link_to_entity": LinkModel(
            href=f"{base_url}/api/v1/linking/orphan-to-entity",
            method="POST"
        ),
    }


def build_dismissed_suggestions_links(entity_id: str, base_url: str) -> dict:
    """Build HATEOAS links for dismissed suggestions response."""
    return {
        "self": LinkModel(href=f"{base_url}/api/v1/suggestions/dismissed/{entity_id}"),
        "entity": LinkModel(href=f"{base_url}/api/v1/entities/{entity_id}"),
        "suggestions": LinkModel(href=f"{base_url}/api/v1/suggestions/entity/{entity_id}"),
    }


def build_action_links(action_id: str, base_url: str) -> dict:
    """Build HATEOAS links for action responses."""
    return {
        "self": LinkModel(href=f"{base_url}/api/v1/linking/history?action_id={action_id}"),
        "history": LinkModel(href=f"{base_url}/api/v1/linking/history"),
    }


def build_pagination_model(
    total: int, limit: int, offset: int, base_url: str, query_params: dict
) -> Optional[PaginationModel]:
    """Build pagination metadata with next/prev links."""
    if total == 0:
        return None

    # Build query string
    query_parts = [f"{k}={v}" for k, v in query_params.items()]
    query_string = "&".join(query_parts) if query_parts else ""

    # Calculate next/prev
    next_url = None
    prev_url = None

    if offset + limit < total:
        next_offset = offset + limit
        next_url = f"{base_url}?{query_string}&limit={limit}&offset={next_offset}"

    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_url = f"{base_url}?{query_string}&limit={limit}&offset={prev_offset}"

    return PaginationModel(
        limit=limit,
        offset=offset,
        total=total,
        next=next_url,
        prev=prev_url,
    )


def count_by_confidence(groups: list) -> tuple:
    """Count suggestions by confidence level."""
    high_count = 0
    medium_count = 0
    low_count = 0

    for group in groups:
        if group["confidence"] == "HIGH":
            high_count = len(group["matches"])
        elif group["confidence"] == "MEDIUM":
            medium_count = len(group["matches"])
        elif group["confidence"] == "LOW":
            low_count = len(group["matches"])

    return high_count, medium_count, low_count


# Endpoints

@router.get(
    "/entity/{entity_id}",
    response_model=EntitySuggestionsResponse,
    summary="Get entity suggestions",
    description="Get smart suggestions for an entity based on matching data",
    responses={
        200: {"description": "Suggestions retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Entity not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_entity_suggestions(
    request: Request,
    entity_id: str,
    confidence_level: Optional[ConfidenceLevelEnum] = Query(
        None, description="Filter by confidence level"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    include_partial: bool = Query(True, description="Include partial matches"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    _rate_limit: None = Depends(check_rate_limit),
) -> EntitySuggestionsResponse:
    """
    Get smart suggestions for an entity based on matching data.

    Returns matching DataItems from other entities that could indicate:
    - Potential relationships
    - Duplicate entities
    - Related entities

    Results are grouped by confidence level (HIGH/MEDIUM/LOW) and paginated.
    Response includes HATEOAS links for navigation and actions.
    """
    start_time = time.time()

    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Get suggestions
        async with AsyncNeo4jService() as neo4j:
            suggestion_service = SuggestionService(neo4j)
            result = await suggestion_service.get_entity_suggestions(
                entity_id=entity_id,
                include_partial=include_partial,
                min_confidence=min_confidence,
            )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found or error: {result['error']}",
            )

        # Filter by confidence level if specified
        suggestions = result["suggestions"]
        if confidence_level:
            suggestions = [
                group for group in suggestions
                if group["confidence"] == confidence_level.value
            ]

        # Apply pagination
        all_matches = []
        for group in suggestions:
            all_matches.extend(group["matches"])

        total_count = len(all_matches)
        paginated_matches = all_matches[offset:offset + limit]

        # Rebuild groups with paginated matches
        paginated_groups = []
        if paginated_matches:
            # Group paginated matches by confidence
            groups_dict = {"HIGH": [], "MEDIUM": [], "LOW": []}
            for match in paginated_matches:
                # Determine confidence level
                score = match["confidence_score"]
                if score >= 0.9:
                    conf = "HIGH"
                elif score >= 0.7:
                    conf = "MEDIUM"
                else:
                    conf = "LOW"
                groups_dict[conf].append(SuggestionMatchResponse(**match))

            # Build confidence groups
            for conf_level in ["HIGH", "MEDIUM", "LOW"]:
                if groups_dict[conf_level]:
                    paginated_groups.append(
                        ConfidenceGroupResponse(
                            confidence=ConfidenceLevelEnum(conf_level),
                            matches=groups_dict[conf_level],
                        )
                    )

        # Count by confidence
        high_count, medium_count, low_count = count_by_confidence(result["suggestions"])

        # Build response
        data = EntitySuggestionsData(
            entity_id=entity_id,
            suggestions=paginated_groups,
            total_count=total_count,
            high_confidence_count=high_count,
            medium_confidence_count=medium_count,
            low_confidence_count=low_count,
            dismissed_count=result.get("dismissed_count", 0),
        )

        # Build pagination
        pagination = build_pagination_model(
            total=total_count,
            limit=limit,
            offset=offset,
            base_url=f"{base_url}/api/v1/suggestions/entity/{entity_id}",
            query_params={
                "include_partial": str(include_partial).lower(),
                "min_confidence": str(min_confidence),
            },
        )

        # Build HATEOAS links
        links = build_entity_suggestions_links(entity_id, base_url)

        # Log response time
        elapsed = time.time() - start_time
        logger.info(f"Entity suggestions for {entity_id}: {elapsed:.3f}s")

        return EntitySuggestionsResponse(
            data=data,
            pagination=pagination,
            _links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}",
        )


@router.get(
    "/orphan/{orphan_id}",
    response_model=OrphanSuggestionsResponse,
    summary="Get orphan suggestions",
    description="Get entity suggestions for orphan data",
    responses={
        200: {"description": "Suggestions retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Orphan not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_orphan_suggestions(
    request: Request,
    orphan_id: str,
    confidence_level: Optional[ConfidenceLevelEnum] = Query(
        None, description="Filter by confidence level"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    include_partial: bool = Query(True, description="Include partial matches"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    _rate_limit: None = Depends(check_rate_limit),
) -> OrphanSuggestionsResponse:
    """
    Get entity suggestions for orphan data.

    Returns entities that match the orphan's data, useful for linking
    orphan data to existing entities.

    Results are grouped by confidence level (HIGH/MEDIUM/LOW) and paginated.
    Response includes HATEOAS links for navigation and actions.
    """
    start_time = time.time()

    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Get suggestions
        async with AsyncNeo4jService() as neo4j:
            suggestion_service = SuggestionService(neo4j)
            result = await suggestion_service.get_orphan_suggestions(
                orphan_id=orphan_id,
                include_partial=include_partial,
                min_confidence=min_confidence,
            )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orphan not found or error: {result['error']}",
            )

        # Filter by confidence level if specified
        suggestions = result["suggestions"]
        if confidence_level:
            suggestions = [
                group for group in suggestions
                if group["confidence"] == confidence_level.value
            ]

        # Apply pagination
        all_matches = []
        for group in suggestions:
            all_matches.extend(group["matches"])

        total_count = len(all_matches)
        paginated_matches = all_matches[offset:offset + limit]

        # Rebuild groups with paginated matches
        paginated_groups = []
        if paginated_matches:
            # Group paginated matches by confidence
            groups_dict = {"HIGH": [], "MEDIUM": [], "LOW": []}
            for match in paginated_matches:
                # Determine confidence level
                score = match["confidence_score"]
                if score >= 0.9:
                    conf = "HIGH"
                elif score >= 0.7:
                    conf = "MEDIUM"
                else:
                    conf = "LOW"
                groups_dict[conf].append(SuggestionMatchResponse(**match))

            # Build confidence groups
            for conf_level in ["HIGH", "MEDIUM", "LOW"]:
                if groups_dict[conf_level]:
                    paginated_groups.append(
                        ConfidenceGroupResponse(
                            confidence=ConfidenceLevelEnum(conf_level),
                            matches=groups_dict[conf_level],
                        )
                    )

        # Count by confidence
        high_count, medium_count, low_count = count_by_confidence(result["suggestions"])

        # Build response
        data = OrphanSuggestionsData(
            orphan_id=orphan_id,
            suggestions=paginated_groups,
            total_count=total_count,
            high_confidence_count=high_count,
            medium_confidence_count=medium_count,
            low_confidence_count=low_count,
        )

        # Build pagination
        pagination = build_pagination_model(
            total=total_count,
            limit=limit,
            offset=offset,
            base_url=f"{base_url}/api/v1/suggestions/orphan/{orphan_id}",
            query_params={
                "include_partial": str(include_partial).lower(),
                "min_confidence": str(min_confidence),
            },
        )

        # Build HATEOAS links
        links = build_orphan_suggestions_links(orphan_id, base_url)

        # Log response time
        elapsed = time.time() - start_time
        logger.info(f"Orphan suggestions for {orphan_id}: {elapsed:.3f}s")

        return OrphanSuggestionsResponse(
            data=data,
            pagination=pagination,
            _links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orphan suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}",
        )


@router.post(
    "/{suggestion_id}/dismiss",
    response_model=DismissSuggestionResponse,
    summary="Dismiss a suggestion",
    description="Mark a suggestion as dismissed so it doesn't reappear",
    responses={
        200: {"description": "Suggestion dismissed successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Suggestion not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def dismiss_suggestion(
    request: Request,
    suggestion_id: str,
    body: DismissSuggestionRequest,
    entity_id: str = Query(..., description="Entity ID"),
    _rate_limit: None = Depends(check_rate_limit),
) -> DismissSuggestionResponse:
    """
    Mark a suggestion as dismissed so it doesn't reappear.

    Creates a DISMISSED_SUGGESTION relationship between the entity and
    the suggested data item, tracking the reason and who dismissed it.
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Dismiss suggestion using LinkingService
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            result = await linking_service.dismiss_suggestion(
                entity_id=entity_id,
                data_id=suggestion_id,
                reason=body.reason,
                created_by=body.dismissed_by,
            )

        # Build HATEOAS links
        links = build_action_links(result["action_id"], base_url)
        links["entity"] = LinkModel(href=f"{base_url}/api/v1/entities/{entity_id}")
        links["suggestions"] = LinkModel(href=f"{base_url}/api/v1/suggestions/entity/{entity_id}")

        return DismissSuggestionResponse(
            success=result["success"],
            action_id=result["action_id"],
            entity_id=entity_id,
            data_id=suggestion_id,
            reason=body.reason,
            dismissed_at=result["dismissed_at"],
            _links=links,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error dismissing suggestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss suggestion: {str(e)}",
        )


@router.get(
    "/dismissed/{entity_id}",
    response_model=DismissedSuggestionsResponse,
    summary="Get dismissed suggestions",
    description="Get list of dismissed suggestions for an entity",
    responses={
        200: {"description": "Dismissed suggestions retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Entity not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_dismissed_suggestions(
    request: Request,
    entity_id: str,
    _rate_limit: None = Depends(check_rate_limit),
) -> DismissedSuggestionsResponse:
    """
    Get list of all dismissed suggestions for an entity.

    Returns suggestions that have been manually dismissed, including
    the reason and when they were dismissed.
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Get dismissed suggestions
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)

            # Get dismissed list from Neo4j
            async with neo4j.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})-[r:DISMISSED_SUGGESTION]->(d:DataItem)
                    RETURN d.id as data_id,
                           d.type as data_type,
                           d.value as data_value,
                           r.reason as reason,
                           r.dismissed_at as dismissed_at,
                           r.dismissed_by as dismissed_by
                    ORDER BY r.dismissed_at DESC
                    """,
                    entity_id=entity_id
                )
                records = await result.data()

        # Build response
        from api.models.suggestion import DismissedSuggestionItem

        dismissed_items = [
            DismissedSuggestionItem(
                data_id=record["data_id"],
                data_type=record["data_type"],
                data_value=str(record["data_value"]),
                reason=record.get("reason", "No reason provided"),
                dismissed_at=record["dismissed_at"],
                dismissed_by=record.get("dismissed_by", "unknown"),
            )
            for record in records
        ]

        data = DismissedSuggestionsData(
            entity_id=entity_id,
            dismissed_suggestions=dismissed_items,
            count=len(dismissed_items),
        )

        # Build HATEOAS links
        links = build_dismissed_suggestions_links(entity_id, base_url)

        return DismissedSuggestionsResponse(
            data=data,
            _links=links,
        )

    except Exception as e:
        logger.error(f"Error getting dismissed suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dismissed suggestions: {str(e)}",
        )


# Linking action endpoints

@router.post(
    "/linking/data-items",
    response_model=LinkDataItemsResponse,
    summary="Link two data items",
    description="Create a LINKED_TO relationship between two data items",
    responses={
        200: {"description": "Data items linked successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Data item not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def link_data_items(
    request: Request,
    body: LinkDataItemsRequest,
    _rate_limit: None = Depends(check_rate_limit),
) -> LinkDataItemsResponse:
    """
    Link two DataItems together with a LINKED_TO relationship.

    Useful when two data items represent the same information
    (e.g., same email, same image uploaded twice).
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Link data items
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            result = await linking_service.link_data_items(
                data_id_1=body.data_id_1,
                data_id_2=body.data_id_2,
                reason=body.reason,
                confidence=body.confidence,
                created_by=body.created_by,
            )

        # Build HATEOAS links
        links = build_action_links(result["action_id"], base_url)

        return LinkDataItemsResponse(
            success=result["success"],
            action_id=result["action_id"],
            linked_data_items=result["linked_data_items"],
            reason=result["reason"],
            confidence=result["confidence"],
            created_at=result["created_at"],
            _links=links,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error linking data items: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link data items: {str(e)}",
        )


@router.post(
    "/linking/merge-entities",
    response_model=MergeEntitiesResponse,
    summary="Merge two entities",
    description="Merge two entities, moving all data to the kept entity",
    responses={
        200: {"description": "Entities merged successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Entity not found"},
        409: {"model": ErrorResponse, "description": "Cannot merge (conflict)"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def merge_entities(
    request: Request,
    body: MergeEntitiesRequest,
    _rate_limit: None = Depends(check_rate_limit),
) -> MergeEntitiesResponse:
    """
    Merge two entities, moving all data to the kept entity.

    This operation is IRREVERSIBLE. All DataItems, relationships, and
    profile data from the discarded entity are moved to the kept entity.
    """
    try:
        # Validate keep_entity_id
        if body.keep_entity_id not in [body.entity_id_1, body.entity_id_2]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"keep_entity_id must be either {body.entity_id_1} or {body.entity_id_2}",
            )

        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Merge entities
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            result = await linking_service.merge_entities(
                entity_id_1=body.entity_id_1,
                entity_id_2=body.entity_id_2,
                keep_entity_id=body.keep_entity_id,
                reason=body.reason,
                created_by=body.created_by,
            )

        # Build HATEOAS links
        links = build_action_links(result["action_id"], base_url)
        links["kept_entity"] = LinkModel(
            href=f"{base_url}/api/v1/entities/{result['kept_entity_id']}"
        )

        return MergeEntitiesResponse(
            success=result["success"],
            action_id=result["action_id"],
            kept_entity_id=result["kept_entity_id"],
            merged_entity_id=result["merged_entity_id"],
            data_items_moved=result["data_items_moved"],
            relationships_moved=result["relationships_moved"],
            reason=result["reason"],
            created_at=result["created_at"],
            warning=result["warning"],
            _links=links,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge entities: {str(e)}",
        )


@router.post(
    "/linking/create-relationship",
    response_model=CreateRelationshipResponse,
    summary="Create a relationship",
    description="Create a relationship between two entities based on a suggestion",
    responses={
        200: {"description": "Relationship created successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Entity not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_relationship(
    request: Request,
    body: CreateRelationshipRequest,
    _rate_limit: None = Depends(check_rate_limit),
) -> CreateRelationshipResponse:
    """
    Create a relationship between two entities based on a suggestion.

    Used when a suggestion indicates entities are related but NOT duplicates.
    For example, two people sharing an address might work together or be family.
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Create relationship
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            result = await linking_service.create_relationship_from_suggestion(
                entity_id_1=body.entity_id_1,
                entity_id_2=body.entity_id_2,
                relationship_type=body.relationship_type,
                reason=body.reason,
                confidence=body.confidence,
                created_by=body.created_by,
            )

        # Build HATEOAS links
        links = build_action_links(result["action_id"], base_url)
        links["source_entity"] = LinkModel(
            href=f"{base_url}/api/v1/entities/{result['source_entity_id']}"
        )
        links["target_entity"] = LinkModel(
            href=f"{base_url}/api/v1/entities/{result['target_entity_id']}"
        )

        return CreateRelationshipResponse(
            success=result["success"],
            action_id=result["action_id"],
            source_entity_id=result["source_entity_id"],
            target_entity_id=result["target_entity_id"],
            relationship_type=result["relationship_type"],
            confidence=result["confidence"],
            reason=result["reason"],
            is_symmetric=result["is_symmetric"],
            created_at=result["created_at"],
            _links=links,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating relationship: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}",
        )


@router.post(
    "/linking/orphan-to-entity",
    response_model=LinkOrphanToEntityResponse,
    summary="Link orphan to entity",
    description="Convert orphan data to entity data by linking it to an entity",
    responses={
        200: {"description": "Orphan linked successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Orphan or entity not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def link_orphan_to_entity(
    request: Request,
    body: LinkOrphanToEntityRequest,
    _rate_limit: None = Depends(check_rate_limit),
) -> LinkOrphanToEntityResponse:
    """
    Convert orphan data to entity data by linking it to an entity.

    Moves all DataItems from the orphan to the entity and marks the orphan
    as resolved.
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Link orphan to entity
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            result = await linking_service.link_orphan_to_entity(
                orphan_id=body.orphan_id,
                entity_id=body.entity_id,
                reason=body.reason,
                created_by=body.created_by,
            )

        # Build HATEOAS links
        links = build_action_links(result["action_id"], base_url)
        links["entity"] = LinkModel(href=f"{base_url}/api/v1/entities/{result['entity_id']}")

        return LinkOrphanToEntityResponse(
            success=result["success"],
            action_id=result["action_id"],
            orphan_id=result["orphan_id"],
            entity_id=result["entity_id"],
            data_items_moved=result["data_items_moved"],
            reason=result["reason"],
            created_at=result["created_at"],
            _links=links,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error linking orphan to entity: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link orphan to entity: {str(e)}",
        )


@router.get(
    "/linking/history/{entity_id}",
    response_model=LinkingHistoryResponse,
    summary="Get linking history",
    description="Get audit trail of linking actions for an entity",
    responses={
        200: {"description": "History retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_linking_history(
    request: Request,
    entity_id: str,
    action_type: Optional[ActionTypeEnum] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _rate_limit: None = Depends(check_rate_limit),
) -> LinkingHistoryResponse:
    """
    Get audit trail of linking actions for an entity.

    Returns the history of all linking actions (merges, links, relationships)
    for accountability and debugging purposes.
    """
    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # Get linking history
        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)
            actions = await linking_service.get_linking_history(
                entity_id=entity_id,
                action_type=action_type.value if action_type else None,
                limit=limit + offset,  # Get more to support pagination
            )

        # Apply offset
        total_count = len(actions)
        paginated_actions = actions[offset:offset + limit]

        # Convert to response models
        from api.models.suggestion import LinkingActionItem

        action_items = [
            LinkingActionItem(
                action_id=action["action_id"],
                action_type=ActionTypeEnum(action["action_type"]),
                created_at=action["created_at"],
                created_by=action["created_by"],
                reason=action["reason"],
                details=action["details"],
                confidence=action["confidence"],
            )
            for action in paginated_actions
        ]

        # Build response
        data = LinkingHistoryData(
            entity_id=entity_id,
            actions=action_items,
            count=len(action_items),
        )

        # Build pagination
        pagination = build_pagination_model(
            total=total_count,
            limit=limit,
            offset=offset,
            base_url=f"{base_url}/api/v1/suggestions/linking/history/{entity_id}",
            query_params={
                "action_type": action_type.value if action_type else "",
            },
        )

        # Build HATEOAS links
        links = {
            "self": LinkModel(href=f"{base_url}/api/v1/suggestions/linking/history/{entity_id}"),
            "entity": LinkModel(href=f"{base_url}/api/v1/entities/{entity_id}"),
        }

        return LinkingHistoryResponse(
            data=data,
            pagination=pagination,
            _links=links,
        )

    except Exception as e:
        logger.error(f"Error getting linking history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get linking history: {str(e)}",
        )


# =============================================================================
# Batch/Auto-Accept Endpoints
# =============================================================================

@router.post(
    "/batch/accept",
    response_model=BatchAcceptSuggestionsResponse,
    summary="Batch accept suggestions",
    description="Accept multiple suggestions in a single request",
    responses={
        200: {"description": "Batch processed successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def batch_accept_suggestions(
    request: Request,
    body: BatchAcceptSuggestionsRequest,
    _rate_limit: None = Depends(check_rate_limit),
) -> BatchAcceptSuggestionsResponse:
    """
    Batch accept multiple suggestions in a single request.

    This endpoint allows automation scripts or frontends to accept multiple
    suggestions at once, supporting different action types:
    - link: Link two data items together
    - merge: Merge two entities
    - relationship: Create relationship between entities
    - dismiss: Dismiss a suggestion

    Each suggestion in the batch is processed independently. If one fails,
    others continue to process.

    **Use Cases:**
    - Human operator selects multiple suggestions to accept
    - Automation script processes suggestions meeting criteria
    - Frontend batch operations
    """
    start_time = time.time()

    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        results: list[BatchActionResult] = []
        successful_count = 0
        failed_count = 0

        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)

            for idx, suggestion in enumerate(body.suggestions):
                try:
                    action_id = None

                    if suggestion.action == "link":
                        # Link data items
                        if not suggestion.data_id:
                            raise ValueError("data_id required for link action")

                        result = await linking_service.link_data_items(
                            data_id_1=suggestion.data_id,
                            data_id_2=suggestion.source_entity_id,  # Entity's data
                            reason=body.reason,
                            confidence=0.9,
                            created_by=body.created_by,
                        )
                        action_id = result["action_id"]

                    elif suggestion.action == "merge":
                        # Merge entities
                        if not suggestion.target_entity_id:
                            raise ValueError("target_entity_id required for merge action")

                        result = await linking_service.merge_entities(
                            entity_id_1=suggestion.source_entity_id,
                            entity_id_2=suggestion.target_entity_id,
                            keep_entity_id=suggestion.source_entity_id,  # Keep source
                            reason=body.reason,
                            created_by=body.created_by,
                        )
                        action_id = result["action_id"]

                    elif suggestion.action == "relationship":
                        # Create relationship
                        if not suggestion.target_entity_id:
                            raise ValueError("target_entity_id required for relationship action")

                        relationship_type = suggestion.relationship_type or "RELATED_TO"

                        result = await linking_service.create_relationship_from_suggestion(
                            entity_id_1=suggestion.source_entity_id,
                            entity_id_2=suggestion.target_entity_id,
                            relationship_type=relationship_type,
                            reason=body.reason,
                            confidence="high",
                            created_by=body.created_by,
                        )
                        action_id = result["action_id"]

                    elif suggestion.action == "dismiss":
                        # Dismiss suggestion
                        if not suggestion.data_id:
                            raise ValueError("data_id required for dismiss action")

                        result = await linking_service.dismiss_suggestion(
                            entity_id=suggestion.source_entity_id,
                            data_id=suggestion.data_id,
                            reason=body.reason,
                            created_by=body.created_by,
                        )
                        action_id = result["action_id"]

                    else:
                        raise ValueError(f"Unknown action: {suggestion.action}")

                    results.append(BatchActionResult(
                        suggestion_index=idx,
                        success=True,
                        action_id=action_id,
                        error=None,
                    ))
                    successful_count += 1

                except Exception as e:
                    results.append(BatchActionResult(
                        suggestion_index=idx,
                        success=False,
                        action_id=None,
                        error=str(e),
                    ))
                    failed_count += 1
                    logger.warning(f"Batch item {idx} failed: {e}")

        # Build HATEOAS links
        links = {
            "self": LinkModel(href=f"{base_url}/api/v1/suggestions/batch/accept", method="POST"),
            "history": LinkModel(href=f"{base_url}/api/v1/suggestions/linking/history"),
        }

        # Log response time
        elapsed = time.time() - start_time
        logger.info(f"Batch accept: {len(body.suggestions)} items, {successful_count} succeeded, {elapsed:.3f}s")

        return BatchAcceptSuggestionsResponse(
            success=(failed_count == 0),
            total_processed=len(body.suggestions),
            successful_count=successful_count,
            failed_count=failed_count,
            results=results,
            _links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch accept: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch: {str(e)}",
        )


@router.post(
    "/auto-accept/preview",
    response_model=AutoAcceptPreviewResponse,
    summary="Preview auto-accept matches",
    description="Preview what suggestions would be auto-accepted with given config",
    responses={
        200: {"description": "Preview generated successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def preview_auto_accept(
    request: Request,
    body: AutoAcceptConfigRequest,
    project_id: str = Query(..., description="Project ID to scan"),
    limit: int = Query(100, ge=1, le=500, description="Maximum matches to preview"),
    _rate_limit: None = Depends(check_rate_limit),
) -> AutoAcceptPreviewResponse:
    """
    Preview what suggestions would be auto-accepted with given configuration.

    This is a **dry-run** endpoint - no changes are made. Use this to:
    - See what suggestions match your auto-accept criteria
    - Tune your configuration before executing
    - Verify the results before committing

    **Configuration Options:**
    - min_confidence: Minimum confidence score to accept (0.5-1.0)
    - match_types: Types of matches to accept (exact_hash, exact_string, partial_string)
    - data_types: Specific data types to auto-accept (empty = all)
    - action: Default action to take (link, relationship)

    **Example Use:**
    ```json
    {
      "enabled": true,
      "min_confidence": 0.95,
      "match_types": ["exact_hash", "exact_string"],
      "data_types": ["email"],
      "action": "link"
    }
    ```
    """
    start_time = time.time()

    try:
        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        preview_items: list[AutoAcceptPreviewItem] = []

        async with AsyncNeo4jService() as neo4j:
            suggestion_service = SuggestionService(neo4j)

            # Get all entities in project
            async with neo4j.session() as session:
                # Find all matches meeting criteria
                result = await session.run(
                    """
                    MATCH (e:Person)-[:HAS_DATA]->(d:DataItem)
                    WHERE d.project_id = $project_id
                    WITH e, d
                    MATCH (d2:DataItem)
                    WHERE d2.id <> d.id
                      AND (
                        (d.hash IS NOT NULL AND d2.hash = d.hash)
                        OR (d.value IS NOT NULL AND d2.value = d.value)
                      )
                    OPTIONAL MATCH (e2:Person)-[:HAS_DATA]->(d2)
                    RETURN e.id as source_entity_id,
                           e.name as source_entity_name,
                           e2.id as target_entity_id,
                           e2.name as target_entity_name,
                           d.id as data_id,
                           d.type as data_type,
                           d.value as data_value,
                           CASE
                             WHEN d.hash IS NOT NULL AND d2.hash = d.hash THEN 1.0
                             WHEN d.value = d2.value THEN 0.95
                             ELSE 0.7
                           END as confidence_score,
                           CASE
                             WHEN d.hash IS NOT NULL AND d2.hash = d.hash THEN 'exact_hash'
                             WHEN d.value = d2.value THEN 'exact_string'
                             ELSE 'partial_string'
                           END as match_type
                    LIMIT $limit
                    """,
                    project_id=project_id,
                    limit=limit * 2,  # Get extra for filtering
                )
                records = await result.data()

        # Filter by config criteria
        for record in records:
            # Check confidence threshold
            if record["confidence_score"] < body.min_confidence:
                continue

            # Check match type filter
            if body.match_types and record["match_type"] not in body.match_types:
                continue

            # Check data type filter
            if body.data_types and record["data_type"] not in body.data_types:
                continue

            preview_items.append(AutoAcceptPreviewItem(
                source_entity_id=record["source_entity_id"],
                source_entity_name=record.get("source_entity_name"),
                target_entity_id=record.get("target_entity_id"),
                target_entity_name=record.get("target_entity_name"),
                data_id=record["data_id"],
                data_type=record["data_type"] or "unknown",
                data_value=str(record["data_value"] or ""),
                confidence_score=record["confidence_score"],
                match_type=record["match_type"],
                proposed_action=body.action,
            ))

            if len(preview_items) >= limit:
                break

        # Build HATEOAS links
        links = {
            "self": LinkModel(href=f"{base_url}/api/v1/suggestions/auto-accept/preview", method="POST"),
            "execute": LinkModel(href=f"{base_url}/api/v1/suggestions/auto-accept/execute", method="POST"),
        }

        # Log response time
        elapsed = time.time() - start_time
        logger.info(f"Auto-accept preview: {len(preview_items)} matches, {elapsed:.3f}s")

        return AutoAcceptPreviewResponse(
            config=body,
            preview=preview_items,
            total_matches=len(records) if records else 0,
            would_accept=len(preview_items),
            _links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-accept preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}",
        )


@router.post(
    "/auto-accept/execute",
    response_model=AutoAcceptExecuteResponse,
    summary="Execute auto-accept",
    description="Execute auto-accept for suggestions matching criteria",
    responses={
        200: {"description": "Auto-accept executed successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def execute_auto_accept(
    request: Request,
    body: AutoAcceptConfigRequest,
    project_id: str = Query(..., description="Project ID to process"),
    limit: int = Query(100, ge=1, le=500, description="Maximum suggestions to process"),
    _rate_limit: None = Depends(check_rate_limit),
) -> AutoAcceptExecuteResponse:
    """
    Execute auto-accept for suggestions matching the given criteria.

    **WARNING**: This endpoint makes PERMANENT changes. Use /preview first
    to verify what will be accepted.

    **Safety Features:**
    - Requires dry_run=false in config to actually execute
    - Each action is logged with full audit trail
    - Actions can be reviewed via /linking/history endpoint
    - Rate limited to prevent abuse

    **Recommended Workflow:**
    1. Call /auto-accept/preview with your config
    2. Review the preview results
    3. If satisfied, call /auto-accept/execute with dry_run=false
    """
    start_time = time.time()

    try:
        # Safety check: require explicit dry_run=false
        if body.dry_run:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Set dry_run=false to execute. Use /preview first to review matches.",
            )

        # Get base URL for HATEOAS links
        base_url = str(request.base_url).rstrip("/")

        # First, get the preview to know what to process
        preview_response = await preview_auto_accept(
            request=request,
            body=AutoAcceptConfigRequest(
                enabled=body.enabled,
                min_confidence=body.min_confidence,
                match_types=body.match_types,
                data_types=body.data_types,
                action=body.action,
                relationship_type=body.relationship_type,
                dry_run=True,  # Preview mode
            ),
            project_id=project_id,
            limit=limit,
            _rate_limit=None,  # Already checked
        )

        # Now execute each action
        results: list[BatchActionResult] = []
        successful_count = 0
        failed_count = 0

        async with AsyncNeo4jService() as neo4j:
            linking_service = LinkingService(neo4j)

            for idx, item in enumerate(preview_response.preview):
                try:
                    action_id = None

                    if body.action == "link":
                        # Link data items (if there's a target entity)
                        if item.target_entity_id:
                            result = await linking_service.create_relationship_from_suggestion(
                                entity_id_1=item.source_entity_id,
                                entity_id_2=item.target_entity_id,
                                relationship_type="LINKED_DATA",
                                reason=f"Auto-accepted: {item.match_type} match with {item.confidence_score:.0%} confidence",
                                confidence="high",
                                created_by="auto_accept",
                            )
                            action_id = result["action_id"]

                    elif body.action == "relationship":
                        # Create relationship
                        if item.target_entity_id:
                            relationship_type = body.relationship_type or "RELATED_TO"
                            result = await linking_service.create_relationship_from_suggestion(
                                entity_id_1=item.source_entity_id,
                                entity_id_2=item.target_entity_id,
                                relationship_type=relationship_type,
                                reason=f"Auto-accepted: {item.match_type} match with {item.confidence_score:.0%} confidence",
                                confidence="high",
                                created_by="auto_accept",
                            )
                            action_id = result["action_id"]

                    results.append(BatchActionResult(
                        suggestion_index=idx,
                        success=True,
                        action_id=action_id,
                        error=None,
                    ))
                    successful_count += 1

                except Exception as e:
                    results.append(BatchActionResult(
                        suggestion_index=idx,
                        success=False,
                        action_id=None,
                        error=str(e),
                    ))
                    failed_count += 1
                    logger.warning(f"Auto-accept item {idx} failed: {e}")

        # Build HATEOAS links
        links = {
            "self": LinkModel(href=f"{base_url}/api/v1/suggestions/auto-accept/execute", method="POST"),
            "preview": LinkModel(href=f"{base_url}/api/v1/suggestions/auto-accept/preview", method="POST"),
            "history": LinkModel(href=f"{base_url}/api/v1/suggestions/linking/history"),
        }

        # Log response time
        elapsed = time.time() - start_time
        logger.info(f"Auto-accept execute: {successful_count} succeeded, {failed_count} failed, {elapsed:.3f}s")

        return AutoAcceptExecuteResponse(
            success=(failed_count == 0),
            config=body,
            total_processed=len(preview_response.preview),
            successful_count=successful_count,
            failed_count=failed_count,
            results=results,
            _links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-accept execute: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute auto-accept: {str(e)}",
        )
