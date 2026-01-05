"""
OSINT Agent Integration Router for Basset Hound.

Provides API endpoints for OSINT agent operations including:
- Starting OSINT investigations
- Ingesting extracted identifiers with provenance
- Tracking investigation progress
- WebSocket notifications for real-time updates

This router enables integration with:
- basset-hound-browser (Puppeteer-based agent)
- autofill-extension (Chrome extension)
- MCP tools for AI-assisted OSINT
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from api.models.orphan import IdentifierType
from api.models.provenance import (
    CaptureMethod,
    DataProvenance,
    ProvenanceCreate,
    SourceType,
    VerificationState,
)
from api.services.verification_service import (
    VerificationLevel,
    get_verification_service,
)


router = APIRouter(
    prefix="/osint",
    tags=["OSINT"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Request/Response Models
# =============================================================================


class IdentifierIngestion(BaseModel):
    """Single identifier to ingest."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identifier_type": "email",
                "identifier_value": "john.doe@example.com",
                "confidence": 0.85,
                "context": "Found in contact page footer",
            }
        }
    )

    identifier_type: str = Field(
        ...,
        description="Type of identifier (email, phone, crypto_address, etc.)"
    )
    identifier_value: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The identifier value"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0 to 1.0)"
    )
    context: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Surrounding context where identifier was found"
    )
    element_selector: Optional[str] = Field(
        default=None,
        max_length=500,
        description="CSS selector or XPath of the source element"
    )
    force_ingest: bool = Field(
        default=False,
        description="Force ingestion even if verification fails"
    )


class IngestRequest(BaseModel):
    """Request model for data ingestion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-investigation",
                "source_url": "https://example.com/contact",
                "source_title": "Contact Us - Example",
                "captured_by": "autofill-extension",
                "identifiers": [
                    {
                        "identifier_type": "email",
                        "identifier_value": "info@example.com",
                        "confidence": 0.9,
                    }
                ],
                "verify_before_ingest": True,
            }
        }
    )

    project_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Project ID or safe_name"
    )
    source_url: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URL where data was found"
    )
    source_title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Title of source page"
    )
    source_type: str = Field(
        default="website",
        description="Type of source (website, api, manual, etc.)"
    )
    capture_method: str = Field(
        default="auto_detected",
        description="How data was captured (auto_detected, user_selected, etc.)"
    )
    captured_by: str = Field(
        default="unknown",
        max_length=100,
        description="Component that captured the data"
    )
    identifiers: List[IdentifierIngestion] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of identifiers to ingest"
    )
    verify_before_ingest: bool = Field(
        default=True,
        description="Verify identifiers before ingestion"
    )
    auto_link: bool = Field(
        default=False,
        description="Automatically attempt to link to existing entities"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class IngestResultItem(BaseModel):
    """Result for a single ingested identifier."""

    identifier_type: str
    identifier_value: str
    status: str = Field(
        ...,
        description="ingested, blocked, linked, error"
    )
    orphan_id: Optional[str] = Field(
        default=None,
        description="ID of created orphan record"
    )
    linked_entity_id: Optional[str] = Field(
        default=None,
        description="ID of entity if auto-linked"
    )
    verification_passed: Optional[bool] = None
    verification_confidence: Optional[float] = None
    error: Optional[str] = None


class IngestResponse(BaseModel):
    """Response model for ingestion operation."""

    success: bool
    project_id: str
    total_count: int
    ingested_count: int
    blocked_count: int
    linked_count: int
    error_count: int
    results: List[IngestResultItem]
    ingested_at: str


class InvestigationRequest(BaseModel):
    """Request model for starting an OSINT investigation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "my-investigation",
                "target": "https://example.com",
                "investigation_type": "web_osint",
                "depth": 2,
                "extract_types": ["email", "phone", "crypto_address"],
            }
        }
    )

    project_id: str = Field(
        ...,
        min_length=1,
        description="Project ID for storing results"
    )
    target: str = Field(
        ...,
        min_length=1,
        description="Investigation target (URL, domain, email, etc.)"
    )
    investigation_type: str = Field(
        default="web_osint",
        description="Type: web_osint, email_osint, domain_osint, social_osint"
    )
    depth: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Crawl depth for web investigations"
    )
    extract_types: List[str] = Field(
        default_factory=lambda: ["email", "phone", "crypto_address"],
        description="Identifier types to extract"
    )
    verify_results: bool = Field(
        default=True,
        description="Verify extracted data"
    )
    auto_link: bool = Field(
        default=True,
        description="Auto-link to existing entities"
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID performing investigation"
    )
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Investigation timeout"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional investigation parameters"
    )


class InvestigationResponse(BaseModel):
    """Response for starting an investigation."""

    job_id: str
    status: str
    project_id: str
    target: str
    investigation_type: str
    created_at: str
    estimated_duration_seconds: Optional[int] = None


class PageExtractRequest(BaseModel):
    """Request for extracting data from a page (sent by browser extension)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/contact",
                "title": "Contact Us",
                "html": "<html>...</html>",
                "extract_types": ["email", "phone"],
            }
        }
    )

    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(default=None, description="Page title")
    html: str = Field(..., description="Page HTML content")
    extract_types: List[str] = Field(
        default_factory=lambda: ["email", "phone", "crypto_address"],
        description="Identifier types to extract"
    )
    verify: bool = Field(default=True, description="Verify extracted data")


class ExtractedIdentifier(BaseModel):
    """A single extracted identifier."""

    identifier_type: str
    identifier_value: str
    confidence: float
    context: Optional[str] = None
    is_valid: Optional[bool] = None
    verification_details: Optional[Dict[str, Any]] = None


class PageExtractResponse(BaseModel):
    """Response for page extraction."""

    url: str
    extracted_count: int
    identifiers: List[ExtractedIdentifier]
    extracted_at: str


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest OSINT data",
    description="Ingest extracted identifiers with full provenance tracking.",
)
async def ingest_data(request: IngestRequest) -> IngestResponse:
    """
    Ingest OSINT data with provenance tracking.

    This endpoint is the primary integration point for:
    - Browser extension (autofill-extension)
    - OSINT agent (basset-hound-browser)
    - MCP tools

    Each identifier is optionally verified before ingestion.
    Provenance is automatically tracked for audit purposes.
    """
    verification_service = get_verification_service()

    results: List[IngestResultItem] = []
    ingested_count = 0
    blocked_count = 0
    linked_count = 0
    error_count = 0

    # Parse source type and capture method
    try:
        source_type = SourceType(request.source_type)
    except ValueError:
        source_type = SourceType.OTHER

    try:
        capture_method = CaptureMethod(request.capture_method)
    except ValueError:
        capture_method = CaptureMethod.AUTO_DETECTED

    # Create provenance record
    provenance = DataProvenance(
        source_type=source_type,
        source_url=request.source_url,
        source_title=request.source_title,
        capture_method=capture_method,
        captured_at=datetime.utcnow(),
        captured_by=request.captured_by,
        metadata=request.metadata,
    )

    for item in request.identifiers:
        result_item = IngestResultItem(
            identifier_type=item.identifier_type,
            identifier_value=item.identifier_value,
            status="pending",
        )

        try:
            # Verify if requested
            if request.verify_before_ingest and not item.force_ingest:
                verification = await verification_service.verify(
                    item.identifier_value,
                    item.identifier_type,
                    VerificationLevel.FORMAT,
                )
                result_item.verification_passed = verification.is_valid
                result_item.verification_confidence = verification.confidence

                if not verification.is_valid:
                    result_item.status = "blocked"
                    result_item.error = "Verification failed"
                    blocked_count += 1
                    results.append(result_item)
                    continue

            # In a full implementation, this would:
            # 1. Create orphan data in Neo4j
            # 2. Optionally auto-link to entities
            # 3. Store provenance
            # For now, we simulate success

            # Simulate orphan creation
            import uuid
            orphan_id = f"orphan-{uuid.uuid4()}"
            result_item.orphan_id = orphan_id
            result_item.status = "ingested"
            ingested_count += 1

            # Auto-link simulation (in real impl, would check for matches)
            if request.auto_link:
                # Would check for matching entities here
                pass

        except Exception as e:
            result_item.status = "error"
            result_item.error = str(e)
            error_count += 1

        results.append(result_item)

    return IngestResponse(
        success=error_count == 0,
        project_id=request.project_id,
        total_count=len(request.identifiers),
        ingested_count=ingested_count,
        blocked_count=blocked_count,
        linked_count=linked_count,
        error_count=error_count,
        results=results,
        ingested_at=datetime.utcnow().isoformat(),
    )


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    summary="Start OSINT investigation",
    description="Queue an OSINT investigation job for processing by an agent.",
)
async def start_investigation(request: InvestigationRequest) -> InvestigationResponse:
    """
    Start an OSINT investigation.

    Creates a background job that will be picked up by an OSINT agent
    (basset-hound-browser or similar). The agent will:

    1. Navigate to the target
    2. Extract identifiers based on extract_types
    3. Verify extracted data
    4. Store results with provenance
    5. Optionally auto-link to entities

    Use the /jobs/{job_id} endpoint to monitor progress.
    """
    import uuid

    # In full implementation, this would enqueue to job runner
    job_id = f"osint-{uuid.uuid4()}"

    # Estimate duration based on depth and type
    estimated_duration = 30 * request.depth  # 30 seconds per depth level

    return InvestigationResponse(
        job_id=job_id,
        status="queued",
        project_id=request.project_id,
        target=request.target,
        investigation_type=request.investigation_type,
        created_at=datetime.utcnow().isoformat(),
        estimated_duration_seconds=estimated_duration,
    )


@router.post(
    "/extract",
    response_model=PageExtractResponse,
    summary="Extract identifiers from HTML",
    description="Extract and optionally verify identifiers from page HTML.",
)
async def extract_from_page(request: PageExtractRequest) -> PageExtractResponse:
    """
    Extract identifiers from page HTML.

    This endpoint is used by the browser extension to:
    1. Send captured page content
    2. Server-side extraction with better patterns
    3. Optional verification
    4. Return extracted identifiers for user review

    The extension can then call /ingest with selected identifiers.
    """
    import re

    verification_service = get_verification_service()

    # Define extraction patterns
    patterns = {
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "phone": re.compile(r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"),
        "crypto_address": re.compile(r"\b(bc1|[13])[a-km-zA-HJ-NP-Z1-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b"),
        "username": re.compile(r"@[a-zA-Z0-9_]{3,30}"),
        "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "domain": re.compile(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})"),
    }

    extracted: List[ExtractedIdentifier] = []
    seen = set()

    for id_type in request.extract_types:
        if id_type not in patterns:
            continue

        matches = patterns[id_type].findall(request.html)
        for match in matches:
            # Handle tuple matches from groups
            value = match if isinstance(match, str) else match[0] if match else None
            if not value or value in seen:
                continue

            seen.add(value)

            # Get context (simplified - in real impl would use HTML parsing)
            context_match = re.search(
                rf".{{0,50}}{re.escape(value)}.{{0,50}}",
                request.html,
                re.IGNORECASE
            )
            context = context_match.group(0) if context_match else None

            item = ExtractedIdentifier(
                identifier_type=id_type,
                identifier_value=value,
                confidence=0.7,  # Base confidence for pattern match
                context=context[:100] if context else None,
            )

            # Verify if requested
            if request.verify:
                try:
                    result = await verification_service.verify(
                        value, id_type, VerificationLevel.FORMAT
                    )
                    item.is_valid = result.is_valid
                    item.confidence = result.confidence
                    item.verification_details = result.details
                except Exception:
                    pass

            extracted.append(item)

    return PageExtractResponse(
        url=request.url,
        extracted_count=len(extracted),
        identifiers=extracted,
        extracted_at=datetime.utcnow().isoformat(),
    )


@router.get(
    "/capabilities",
    summary="Get OSINT capabilities",
    description="Returns the supported identifier types and investigation types.",
)
async def get_capabilities() -> Dict[str, Any]:
    """
    Get OSINT capabilities.

    Returns information about:
    - Supported identifier types
    - Investigation types
    - Verification levels
    - Agent requirements
    """
    return {
        "identifier_types": [t.value for t in IdentifierType],
        "investigation_types": [
            {
                "type": "web_osint",
                "description": "Extract identifiers from web pages",
                "requires_agent": True,
            },
            {
                "type": "email_osint",
                "description": "Investigate email address",
                "requires_agent": False,
            },
            {
                "type": "domain_osint",
                "description": "Investigate domain/website",
                "requires_agent": True,
            },
            {
                "type": "social_osint",
                "description": "Investigate social media presence",
                "requires_agent": True,
            },
        ],
        "verification_levels": ["format", "network", "external"],
        "source_types": [t.value for t in SourceType],
        "capture_methods": [m.value for m in CaptureMethod],
        "max_identifiers_per_request": 100,
        "max_investigation_depth": 5,
    }


@router.get(
    "/stats",
    summary="Get OSINT statistics",
    description="Returns statistics about OSINT operations.",
)
async def get_stats(
    project_id: Optional[str] = Query(None, description="Filter by project")
) -> Dict[str, Any]:
    """
    Get OSINT statistics.

    Returns aggregate statistics about:
    - Total ingestions
    - Ingestions by type
    - Verification success rates
    - Active investigations
    """
    # In full implementation, this would query the database
    return {
        "total_ingestions": 0,
        "ingestions_by_type": {},
        "verification_success_rate": 0.0,
        "active_investigations": 0,
        "completed_investigations": 0,
        "unique_identifiers": 0,
        "linked_to_entities": 0,
        "project_filter": project_id,
    }
