"""
Data Provenance models for Basset Hound OSINT Platform.

Provenance tracking captures the origin, chain of custody, and
verification history of data in the platform. This is critical for:
- OSINT investigations requiring source attribution
- Audit trails for compliance
- Data quality assessment
- Integration with browser extension and agents
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class SourceType(str, Enum):
    """Types of data sources."""
    WEBSITE = "website"           # Data captured from a web page
    API = "api"                   # Data from an external API
    FILE_IMPORT = "file_import"   # Data imported from a file
    MANUAL_ENTRY = "manual"       # Manually entered by user
    BROWSER_EXTENSION = "browser_extension"  # Captured via autofill-extension
    OSINT_AGENT = "osint_agent"   # Captured by basset-hound-browser agent
    MCP_TOOL = "mcp_tool"         # Ingested via MCP tool
    THIRD_PARTY = "third_party"   # External OSINT tool (Maltego, SpiderFoot, etc.)
    CLIPBOARD = "clipboard"       # Pasted from clipboard
    OCR = "ocr"                   # Extracted via OCR
    SCREENSHOT = "screenshot"     # Extracted from screenshot
    OTHER = "other"


class CaptureMethod(str, Enum):
    """How the data was captured."""
    AUTO_DETECTED = "auto_detected"      # Automatically detected by system
    USER_SELECTED = "user_selected"      # User manually selected element
    FORM_AUTOFILL = "form_autofill"      # Captured from form fill
    CLIPBOARD_PASTE = "clipboard"        # Pasted content
    FILE_UPLOAD = "file_upload"          # Uploaded file
    API_FETCH = "api_fetch"              # Fetched from API
    SCRAPE = "scrape"                    # Web scraping
    MANUAL_INPUT = "manual"              # Typed manually


class VerificationState(str, Enum):
    """Data verification state."""
    UNVERIFIED = "unverified"            # Not yet verified
    FORMAT_VALID = "format_valid"        # Format validation passed
    NETWORK_VERIFIED = "network_verified"  # Network checks passed
    API_VERIFIED = "api_verified"        # External API verification passed
    HUMAN_VERIFIED = "human_verified"    # Verified by human analyst
    USER_OVERRIDE = "user_override"      # User overrode verification result
    FAILED = "failed"                    # Verification failed
    EXPIRED = "expired"                  # Previous verification expired


class DataProvenance(BaseModel):
    """
    Data provenance information for tracking data origin and history.

    This model captures comprehensive metadata about where data came from,
    how it was captured, and its verification history.

    Used by:
    - OrphanData for tracking unlinked identifiers
    - Entity profiles for tracking data sources
    - Relationships for tracking connection sources
    """

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "source_type": "website",
                "source_url": "https://example.com/about",
                "source_title": "About Us - Example Company",
                "capture_method": "auto_detected",
                "captured_at": "2026-01-05T10:30:00Z",
                "captured_by": "autofill-extension",
                "user_agent": "Mozilla/5.0...",
                "confidence": 0.85,
                "verification_state": "format_valid",
            }
        }
    )

    # Source identification
    source_type: SourceType = Field(
        default=SourceType.OTHER,
        description="Type of data source (website, api, file, manual, etc.)"
    )
    source_url: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URL where the data was found"
    )
    source_title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Title of the source page/document"
    )
    source_domain: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Domain of the source (extracted from URL)"
    )

    # Capture details
    capture_method: CaptureMethod = Field(
        default=CaptureMethod.MANUAL_INPUT,
        description="How the data was captured"
    )
    captured_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the data was captured"
    )
    captured_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Component/agent that captured the data (e.g., 'autofill-extension', 'osint-agent')"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User agent string if captured from browser"
    )

    # Context information
    page_context: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Surrounding text/context where data was found"
    )
    element_selector: Optional[str] = Field(
        default=None,
        max_length=500,
        description="CSS selector or XPath of the source element"
    )
    screenshot_path: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path to screenshot evidence if captured"
    )

    # Verification and confidence
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    verification_state: VerificationState = Field(
        default=VerificationState.UNVERIFIED,
        description="Current verification state"
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="When the data was last verified"
    )
    verification_method: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Method used for verification"
    )

    # User override flags - verification is advisory, user is authoritative
    user_verified: bool = Field(
        default=False,
        description="User explicitly confirmed this data is correct"
    )
    user_override: bool = Field(
        default=False,
        description="User overrode automatic verification result"
    )
    override_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User's explanation for override (e.g., 'Valid on internal network', 'Known alias')"
    )
    override_at: Optional[datetime] = Field(
        default=None,
        description="When the user override was applied"
    )

    # Chain of custody
    original_source_id: Optional[str] = Field(
        default=None,
        description="ID of original source record if this is derived data"
    )
    transformation_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notes about any transformations applied to the data"
    )

    # External tool information (for third-party imports)
    external_tool: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of external tool (Maltego, SpiderFoot, etc.)"
    )
    external_tool_version: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Version of external tool"
    )
    external_record_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Record ID in external tool"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "source_type": self.source_type,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_domain": self.source_domain,
            "capture_method": self.capture_method,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "captured_by": self.captured_by,
            "user_agent": self.user_agent,
            "page_context": self.page_context,
            "element_selector": self.element_selector,
            "screenshot_path": self.screenshot_path,
            "confidence": self.confidence,
            "verification_state": self.verification_state,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_method": self.verification_method,
            "user_verified": self.user_verified,
            "user_override": self.user_override,
            "override_reason": self.override_reason,
            "override_at": self.override_at.isoformat() if self.override_at else None,
            "original_source_id": self.original_source_id,
            "transformation_notes": self.transformation_notes,
            "external_tool": self.external_tool,
            "external_tool_version": self.external_tool_version,
            "external_record_id": self.external_record_id,
            "metadata": self.metadata,
        }


class ProvenanceCreate(BaseModel):
    """
    Model for creating provenance records.

    Simplified version for API usage.
    """

    model_config = ConfigDict(use_enum_values=True)

    source_type: SourceType = Field(
        default=SourceType.MANUAL_ENTRY,
        description="Type of data source"
    )
    source_url: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="URL where the data was found"
    )
    source_title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Title of the source page/document"
    )
    capture_method: CaptureMethod = Field(
        default=CaptureMethod.MANUAL_INPUT,
        description="How the data was captured"
    )
    captured_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Component/agent that captured the data"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    page_context: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Surrounding context"
    )
    element_selector: Optional[str] = Field(
        default=None,
        max_length=500,
        description="CSS selector"
    )
    external_tool: Optional[str] = Field(
        default=None,
        max_length=100,
        description="External tool name"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    def to_provenance(self) -> DataProvenance:
        """Convert to full DataProvenance model."""
        # Extract domain from URL if present
        source_domain = None
        if self.source_url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(self.source_url)
                source_domain = parsed.netloc
            except Exception:
                pass

        return DataProvenance(
            source_type=self.source_type,
            source_url=self.source_url,
            source_title=self.source_title,
            source_domain=source_domain,
            capture_method=self.capture_method,
            captured_at=datetime.utcnow(),
            captured_by=self.captured_by,
            page_context=self.page_context,
            element_selector=self.element_selector,
            confidence=self.confidence,
            verification_state=VerificationState.UNVERIFIED,
            external_tool=self.external_tool,
            metadata=self.metadata,
        )


class ProvenanceResponse(DataProvenance):
    """Response model for provenance data."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )


class ProvenanceChain(BaseModel):
    """
    Model representing the full chain of provenance for a piece of data.

    Tracks the complete history from original source through any
    transformations or derivations.
    """

    model_config = ConfigDict(use_enum_values=True)

    current: DataProvenance = Field(
        ...,
        description="Current provenance record"
    )
    history: list[DataProvenance] = Field(
        default_factory=list,
        description="Previous provenance records (oldest first)"
    )
    derived_from: Optional[str] = Field(
        default=None,
        description="ID of parent record if this was derived from another"
    )
    derivatives: list[str] = Field(
        default_factory=list,
        description="IDs of records derived from this one"
    )

    def add_transformation(
        self,
        transformation_notes: str,
        new_captured_by: str,
    ) -> "ProvenanceChain":
        """
        Create a new provenance record for a transformation.

        Preserves the current record in history and creates a new current.
        """
        # Archive current to history
        updated_history = self.history + [self.current]

        # Create new current with transformation notes
        new_current = DataProvenance(
            source_type=self.current.source_type,
            source_url=self.current.source_url,
            source_title=self.current.source_title,
            source_domain=self.current.source_domain,
            capture_method=CaptureMethod.API_FETCH,  # Transformation
            captured_at=datetime.utcnow(),
            captured_by=new_captured_by,
            confidence=self.current.confidence,
            verification_state=self.current.verification_state,
            original_source_id=self.derived_from,
            transformation_notes=transformation_notes,
            metadata=self.current.metadata.copy(),
        )

        return ProvenanceChain(
            current=new_current,
            history=updated_history,
            derived_from=self.derived_from,
            derivatives=self.derivatives,
        )
