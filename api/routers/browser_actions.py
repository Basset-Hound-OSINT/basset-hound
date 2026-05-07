"""
Browser Actions Router for basset-hound-browser Integration.

Provides HTTP endpoints for controlling the Electron browser and capturing evidence.
Integrates with basset-hound-browser WebSocket API to enable web automation,
screenshots, content extraction, and form filling for OSINT investigations.

Endpoints:
- GET /api/v1/browser/status - Check browser health
- POST /api/v1/browser/screenshot - Take screenshot
- POST /api/v1/browser/navigate - Navigate to URL
- POST /api/v1/browser/capture - Capture full evidence (screenshot + extraction)
- POST /api/v1/browser/fill - Auto-fill form fields
- POST /api/v1/browser/click - Click element
- GET /api/v1/browser/sessions - List active sessions
- POST /api/v1/browser/execute - Execute JavaScript
"""

import base64
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from api.clients.basset_hound_browser_client import get_browser_client
from api.dependencies import get_neo4j_handler, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/browser",
    tags=["browser"],
    responses={
        503: {"description": "Browser not available"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ScreenshotRequest(BaseModel):
    """Request model for taking a screenshot."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "full_page": False,
            }
        }
    )

    url: Optional[str] = Field(
        None, max_length=2000, description="URL to navigate to before screenshot"
    )
    full_page: bool = Field(
        False, description="Capture full page instead of viewport"
    )


class CaptureRequest(BaseModel):
    """Request model for capturing evidence."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "project_id": "my-investigation",
                "entity_id": "entity123",
                "description": "Evidence from target website",
            }
        }
    )

    url: str = Field(..., max_length=2000, description="URL to capture")
    project_id: str = Field(
        ..., min_length=1, max_length=100, description="Project ID"
    )
    entity_id: Optional[str] = Field(
        None, description="Entity ID to associate with evidence"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Evidence description"
    )


class FillRequest(BaseModel):
    """Request model for form filling."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fields": {
                    "#email": "test@example.com",
                    "#password": "password123",
                }
            }
        }
    )

    fields: Dict[str, str] = Field(
        ..., description="Dict of CSS selectors to values"
    )
    click_submit: bool = Field(
        False, description="Click submit button after filling"
    )
    submit_selector: Optional[str] = Field(
        None, description="CSS selector for submit button"
    )


class ClickRequest(BaseModel):
    """Request model for clicking element."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"selector": "button.submit"}}
    )

    selector: str = Field(..., description="CSS selector or XPath")
    wait_after: Optional[int] = Field(
        None, description="Wait time after click (ms)"
    )


class ExecuteScriptRequest(BaseModel):
    """Request model for executing JavaScript."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"script": "return window.location.href"}
        }
    )

    script: str = Field(..., description="JavaScript code to execute")


class NavigateRequest(BaseModel):
    """Request model for navigation."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"url": "https://example.com"}}
    )

    url: str = Field(..., max_length=2000, description="URL to navigate to")
    wait_until: str = Field(
        "load",
        description="Wait until: load, domcontentloaded, networkidle",
    )


class BrowserStatusResponse(BaseModel):
    """Response model for browser status."""

    status: str = Field(
        ...,
        description="Status: healthy, unhealthy, unavailable, or error",
    )
    message: Optional[str] = Field(None, description="Status message")
    browser_info: Optional[Dict[str, Any]] = Field(
        None, description="Browser status info"
    )


class ScreenshotResponse(BaseModel):
    """Response model for screenshot."""

    image: str = Field(..., description="Base64-encoded image data")
    format: str = Field(
        "base64", description="Image format (base64 for now)"
    )
    full_page: bool = Field(..., description="Whether full page was captured")
    timestamp: str = Field(..., description="Capture timestamp")


class CaptureResponse(BaseModel):
    """Response model for evidence capture."""

    evidence_id: str = Field(..., description="Generated evidence ID")
    url: str = Field(..., description="Captured URL")
    screenshot_size: int = Field(..., description="Screenshot size in bytes")
    content_extracted: bool = Field(..., description="Content extraction success")
    network_requests: int = Field(..., description="Number of network requests")
    timestamp: str = Field(..., description="Capture timestamp")


class SessionInfo(BaseModel):
    """Information about a browser session."""

    id: str = Field(..., description="Session ID")
    name: str = Field(..., description="Session name")
    url: Optional[str] = Field(None, description="Current URL")
    active: bool = Field(..., description="Is session active")


class SessionsResponse(BaseModel):
    """Response model for sessions list."""

    sessions: list[SessionInfo] = Field(default_factory=list)


class ExecuteScriptResponse(BaseModel):
    """Response model for script execution."""

    success: bool = Field(..., description="Execution success")
    result: Any = Field(None, description="Script result")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=BrowserStatusResponse)
async def browser_status():
    """
    Check if browser is running and responsive.

    Returns:
        BrowserStatusResponse with health status
    """
    async with get_browser_client() as client:
        if not client:
            return BrowserStatusResponse(
                status="unavailable",
                message="Browser not running or connection failed",
            )

        try:
            is_healthy = await client.health_check()
            if is_healthy:
                status_info = await client.status()
                return BrowserStatusResponse(
                    status="healthy",
                    browser_info=status_info,
                )
            else:
                return BrowserStatusResponse(
                    status="unhealthy",
                    message="Browser did not respond to health check",
                )
        except Exception as e:
            logger.error(f"Browser status check failed: {e}")
            return BrowserStatusResponse(
                status="error",
                message=str(e),
            )


@router.post("/screenshot", response_model=ScreenshotResponse)
async def take_screenshot(request: ScreenshotRequest):
    """
    Take a screenshot of current or specified URL.

    Args:
        request: Screenshot request with optional URL

    Returns:
        ScreenshotResponse with base64-encoded image

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Screenshot capture failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            if request.url:
                logger.info(f"Navigating to {request.url}")
                await client.navigate(request.url)

            logger.info(
                f"Taking screenshot (full_page={request.full_page})"
            )
            image_base64 = await client.screenshot(
                full_page=request.full_page
            )

            if not image_base64:
                raise ValueError("Screenshot returned empty data")

            return ScreenshotResponse(
                image=image_base64,
                format="base64",
                full_page=request.full_page,
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to capture screenshot: {str(e)}",
            )


@router.post("/navigate", response_model=Dict[str, Any])
async def navigate(request: NavigateRequest):
    """
    Navigate to URL in browser.

    Args:
        request: Navigation request with URL

    Returns:
        Dict with navigation result

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Navigation failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            logger.info(f"Navigating to {request.url}")
            result = await client.navigate(request.url)
            return {
                "url": request.url,
                "success": result.get("success", True),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to navigate: {str(e)}",
            )


@router.post("/capture", response_model=CaptureResponse)
async def capture_evidence(request: CaptureRequest):
    """
    Capture full evidence: screenshot + page extraction.

    Stores screenshot and extracted content as file evidence attached to entity.

    Args:
        request: Capture request with URL, project, and entity IDs

    Returns:
        CaptureResponse with evidence info

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Capture failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            # Navigate to URL
            logger.info(f"Navigating to {request.url}")
            await client.navigate(request.url)

            # Capture screenshot
            logger.info("Capturing screenshot")
            screenshot_base64 = await client.screenshot(full_page=True)

            if not screenshot_base64:
                raise ValueError("Screenshot capture returned empty data")

            # Extract page content
            logger.info("Extracting page content")
            extracted = await client.extract_all()

            # Get network logs
            logger.info("Retrieving network logs")
            network_logs = await client.get_network_logs()

            # Store screenshot as file
            neo4j = get_neo4j_handler()
            evidence_id = _store_screenshot_evidence(
                neo4j,
                request.project_id,
                request.entity_id,
                request.url,
                screenshot_base64,
                extracted,
                network_logs,
                request.description,
            )

            logger.info(
                f"Evidence captured: {evidence_id} for {request.url}"
            )
            return CaptureResponse(
                evidence_id=evidence_id,
                url=request.url,
                screenshot_size=len(screenshot_base64),
                content_extracted=bool(extracted),
                network_requests=len(network_logs),
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"Evidence capture failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to capture evidence: {str(e)}",
            )


@router.get("/sessions", response_model=SessionsResponse)
async def list_sessions():
    """
    List active browser sessions.

    Returns:
        SessionsResponse with list of sessions

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Failed to retrieve sessions
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            sessions_data = await client.list_sessions()
            sessions = [
                SessionInfo(
                    id=s.get("id", ""),
                    name=s.get("name", ""),
                    url=s.get("url"),
                    active=s.get("active", False),
                )
                for s in sessions_data
            ]
            return SessionsResponse(sessions=sessions)
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve sessions: {str(e)}",
            )


@router.post("/fill", response_model=Dict[str, str])
async def fill_form(request: FillRequest):
    """
    Fill form fields with provided values.

    Args:
        request: Form fill request with selector->value mapping

    Returns:
        Dict mapping selectors to result status

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Fill operation failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        results = {}
        try:
            for selector, value in request.fields.items():
                logger.info(f"Filling {selector}")
                try:
                    await client.fill(selector, str(value))
                    results[selector] = "filled"
                except Exception as e:
                    results[selector] = f"error: {str(e)}"
                    logger.warning(f"Failed to fill {selector}: {e}")

            if request.click_submit and request.submit_selector:
                logger.info(f"Clicking submit button: {request.submit_selector}")
                try:
                    await client.click(request.submit_selector)
                    results["__submit__"] = "clicked"
                except Exception as e:
                    results["__submit__"] = f"error: {str(e)}"
                    logger.warning(f"Failed to click submit: {e}")

            return results
        except Exception as e:
            logger.error(f"Form fill failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fill form: {str(e)}",
            )


@router.post("/click", response_model=Dict[str, Any])
async def click_element(request: ClickRequest):
    """
    Click an element on the page.

    Args:
        request: Click request with CSS selector

    Returns:
        Dict with click result

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Click failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            logger.info(f"Clicking {request.selector}")
            result = await client.click(request.selector)
            return {
                "selector": request.selector,
                "success": result.get("success", True),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Click failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to click element: {str(e)}",
            )


@router.post("/execute", response_model=ExecuteScriptResponse)
async def execute_script(request: ExecuteScriptRequest):
    """
    Execute arbitrary JavaScript in the browser.

    Args:
        request: Script execution request

    Returns:
        ExecuteScriptResponse with execution result

    Raises:
        HTTPException 503: Browser not available
        HTTPException 500: Script execution failed
    """
    async with get_browser_client() as client:
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser not available",
            )

        try:
            logger.info("Executing JavaScript")
            result = await client.execute_script(request.script)
            return ExecuteScriptResponse(
                success=result.get("success", True),
                result=result.get("result"),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute script: {str(e)}",
            )


# =============================================================================
# Helper Functions
# =============================================================================


def _store_screenshot_evidence(
    neo4j,
    project_id: str,
    entity_id: Optional[str],
    url: str,
    screenshot_base64: str,
    extracted_content: Dict[str, Any],
    network_logs: list,
    description: Optional[str] = None,
) -> str:
    """
    Store screenshot evidence in Neo4j and file system.

    Creates a file node linked to the entity with screenshot metadata.

    Args:
        neo4j: Neo4j handler
        project_id: Project ID
        entity_id: Entity ID (optional)
        url: Source URL
        screenshot_base64: Base64-encoded screenshot
        extracted_content: Extracted page content
        network_logs: Network request logs
        description: Optional description

    Returns:
        Evidence ID (file node ID)
    """
    # Generate evidence ID
    import hashlib
    evidence_id = hashlib.sha256(
        f"{url}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]

    # Store screenshot data
    settings = get_settings()
    evidence_dir = Path(settings.projects_directory) / project_id / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    screenshot_filename = f"{evidence_id}_screenshot.png"
    screenshot_path = evidence_dir / screenshot_filename

    # Decode and write screenshot
    screenshot_bytes = base64.b64decode(screenshot_base64)
    screenshot_path.write_bytes(screenshot_bytes)

    logger.info(f"Stored screenshot at {screenshot_path}")

    # Create evidence metadata file
    metadata = {
        "id": evidence_id,
        "url": url,
        "timestamp": datetime.utcnow().isoformat(),
        "description": description,
        "screenshot_file": screenshot_filename,
        "screenshot_size": len(screenshot_bytes),
        "extracted_content": extracted_content,
        "network_requests": len(network_logs),
    }

    import json

    metadata_path = evidence_dir / f"{evidence_id}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    logger.info(f"Stored evidence metadata at {metadata_path}")

    # TODO: Create Neo4j nodes and relationships
    # If entity_id is provided:
    #   - Create EVIDENCE node
    #   - Link to entity with CAPTURED_FROM relationship
    # Store metadata as properties

    return evidence_id
