"""
Data provenance tools for MCP.

Provides tools for recording and managing data provenance in Basset Hound.
Provenance tracking captures the origin, chain of custody, and verification
history of data - critical for OSINT investigations requiring source attribution.
"""

import sys
import os
from datetime import datetime
from typing import Optional, Any
from uuid import uuid4

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.models.provenance import (
    DataProvenance,
    ProvenanceCreate,
    SourceType,
    CaptureMethod,
    VerificationState,
)
from .base import get_neo4j_handler, get_project_safe_name


def register_provenance_tools(mcp):
    """Register data provenance tools with the MCP server."""

    @mcp.tool()
    def get_source_types() -> dict:
        """
        Get available source types for provenance tracking.

        Returns:
            List of source types with descriptions
        """
        return {
            "source_types": [
                {"value": st.value, "name": st.name, "description": _get_source_type_description(st)}
                for st in SourceType
            ]
        }

    @mcp.tool()
    def get_capture_methods() -> dict:
        """
        Get available capture methods for provenance tracking.

        Returns:
            List of capture methods with descriptions
        """
        return {
            "capture_methods": [
                {"value": cm.value, "name": cm.name, "description": _get_capture_method_description(cm)}
                for cm in CaptureMethod
            ]
        }

    @mcp.tool()
    def get_verification_states() -> dict:
        """
        Get available verification states for provenance tracking.

        Returns:
            List of verification states with descriptions
        """
        return {
            "verification_states": [
                {"value": vs.value, "name": vs.name, "description": _get_verification_state_description(vs)}
                for vs in VerificationState
            ]
        }

    @mcp.tool()
    def record_entity_provenance(
        project_id: str,
        entity_id: str,
        source_type: str,
        capture_method: str = "manual",
        source_url: str = None,
        source_title: str = None,
        captured_by: str = None,
        confidence: float = 0.5,
        page_context: str = None,
        element_selector: str = None,
        external_tool: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Record provenance information for an entity.

        Attaches source attribution and chain of custody data to an entity,
        documenting where and how the entity data was discovered.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity to attach provenance to
            source_type: Type of source (website, api, file_import, manual, browser_extension,
                        osint_agent, mcp_tool, third_party, clipboard, ocr, screenshot, other)
            capture_method: How data was captured (auto_detected, user_selected, form_autofill,
                           clipboard, file_upload, api_fetch, scrape, manual)
            source_url: URL where data was found (optional)
            source_title: Title of source page/document (optional)
            captured_by: Component/agent that captured data (optional)
            confidence: Confidence score 0.0 to 1.0 (default: 0.5)
            page_context: Surrounding text/context (optional)
            element_selector: CSS selector or XPath (optional)
            external_tool: External tool name if applicable (optional)
            metadata: Additional metadata dict (optional)

        Returns:
            The recorded provenance data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify entity exists
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Validate source_type
        try:
            source_type_enum = SourceType(source_type)
        except ValueError:
            valid_types = [st.value for st in SourceType]
            return {"error": f"Invalid source_type: {source_type}. Valid types: {valid_types}"}

        # Validate capture_method
        try:
            capture_method_enum = CaptureMethod(capture_method)
        except ValueError:
            valid_methods = [cm.value for cm in CaptureMethod]
            return {"error": f"Invalid capture_method: {capture_method}. Valid methods: {valid_methods}"}

        # Create provenance object
        provenance_create = ProvenanceCreate(
            source_type=source_type_enum,
            source_url=source_url,
            source_title=source_title,
            capture_method=capture_method_enum,
            captured_by=captured_by,
            confidence=confidence,
            page_context=page_context,
            element_selector=element_selector,
            external_tool=external_tool,
            metadata=metadata or {}
        )

        provenance = provenance_create.to_provenance()
        provenance_dict = provenance.to_dict()

        # Store provenance in entity profile
        profile = entity.get("profile", {})
        if "_provenance" not in profile:
            profile["_provenance"] = []

        # Add new provenance record with ID
        provenance_record = {
            "id": str(uuid4()),
            **provenance_dict
        }
        profile["_provenance"].append(provenance_record)

        # Update entity
        result = handler.update_person(safe_name, entity_id, {"profile": profile})

        if not result:
            return {"error": "Failed to record provenance"}

        return {
            "success": True,
            "entity_id": entity_id,
            "provenance": provenance_record
        }

    @mcp.tool()
    def record_field_provenance(
        project_id: str,
        entity_id: str,
        field_path: str,
        source_type: str,
        capture_method: str = "manual",
        source_url: str = None,
        source_title: str = None,
        captured_by: str = None,
        confidence: float = 0.5,
        page_context: str = None,
        external_tool: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Record provenance for a specific field in an entity profile.

        Attaches source attribution to a specific field, enabling field-level
        provenance tracking for granular data quality assessment.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID
            field_path: Dot-notation path to field (e.g., "contact.email.0" or "core.name")
            source_type: Type of source
            capture_method: How data was captured
            source_url: URL where data was found (optional)
            source_title: Title of source page/document (optional)
            captured_by: Component/agent that captured data (optional)
            confidence: Confidence score 0.0 to 1.0 (default: 0.5)
            page_context: Surrounding text/context (optional)
            external_tool: External tool name if applicable (optional)
            metadata: Additional metadata dict (optional)

        Returns:
            The recorded field provenance data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Validate source_type
        try:
            source_type_enum = SourceType(source_type)
        except ValueError:
            valid_types = [st.value for st in SourceType]
            return {"error": f"Invalid source_type: {source_type}. Valid types: {valid_types}"}

        # Validate capture_method
        try:
            capture_method_enum = CaptureMethod(capture_method)
        except ValueError:
            valid_methods = [cm.value for cm in CaptureMethod]
            return {"error": f"Invalid capture_method: {capture_method}. Valid methods: {valid_methods}"}

        # Create provenance object
        provenance_create = ProvenanceCreate(
            source_type=source_type_enum,
            source_url=source_url,
            source_title=source_title,
            capture_method=capture_method_enum,
            captured_by=captured_by,
            confidence=confidence,
            page_context=page_context,
            external_tool=external_tool,
            metadata=metadata or {}
        )

        provenance = provenance_create.to_provenance()
        provenance_dict = provenance.to_dict()

        # Store field-level provenance
        profile = entity.get("profile", {})
        if "_field_provenance" not in profile:
            profile["_field_provenance"] = {}

        provenance_record = {
            "id": str(uuid4()),
            "field_path": field_path,
            **provenance_dict
        }

        if field_path not in profile["_field_provenance"]:
            profile["_field_provenance"][field_path] = []
        profile["_field_provenance"][field_path].append(provenance_record)

        # Update entity
        result = handler.update_person(safe_name, entity_id, {"profile": profile})

        if not result:
            return {"error": "Failed to record field provenance"}

        return {
            "success": True,
            "entity_id": entity_id,
            "field_path": field_path,
            "provenance": provenance_record
        }

    @mcp.tool()
    def get_entity_provenance(project_id: str, entity_id: str) -> dict:
        """
        Get all provenance records for an entity.

        Returns both entity-level and field-level provenance data.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID

        Returns:
            Dictionary with entity and field provenance records
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        profile = entity.get("profile", {})

        return {
            "entity_id": entity_id,
            "entity_provenance": profile.get("_provenance", []),
            "field_provenance": profile.get("_field_provenance", {}),
            "provenance_count": len(profile.get("_provenance", [])),
            "fields_with_provenance": len(profile.get("_field_provenance", {}))
        }

    @mcp.tool()
    def update_verification_state(
        project_id: str,
        entity_id: str,
        provenance_id: str,
        verification_state: str,
        verification_method: str = None,
        user_verified: bool = False,
        user_override: bool = False,
        override_reason: str = None
    ) -> dict:
        """
        Update the verification state of a provenance record.

        Used to mark data as verified through various methods or to record
        user overrides of automatic verification results.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID
            provenance_id: The provenance record ID to update
            verification_state: New state (unverified, format_valid, network_verified,
                               api_verified, human_verified, user_override, failed, expired)
            verification_method: Method used for verification (optional)
            user_verified: Whether user explicitly verified (default: False)
            user_override: Whether this is a user override (default: False)
            override_reason: Explanation for override (optional)

        Returns:
            Updated provenance record
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Validate verification_state
        try:
            vs_enum = VerificationState(verification_state)
        except ValueError:
            valid_states = [vs.value for vs in VerificationState]
            return {"error": f"Invalid verification_state: {verification_state}. Valid states: {valid_states}"}

        profile = entity.get("profile", {})
        provenance_list = profile.get("_provenance", [])

        # Find and update the provenance record
        found = False
        for prov in provenance_list:
            if prov.get("id") == provenance_id:
                prov["verification_state"] = verification_state
                prov["verified_at"] = datetime.utcnow().isoformat()
                if verification_method:
                    prov["verification_method"] = verification_method
                if user_verified:
                    prov["user_verified"] = True
                if user_override:
                    prov["user_override"] = True
                    prov["override_at"] = datetime.utcnow().isoformat()
                if override_reason:
                    prov["override_reason"] = override_reason
                found = True
                updated_prov = prov
                break

        if not found:
            # Check field provenance
            field_provenance = profile.get("_field_provenance", {})
            for field_path, field_provs in field_provenance.items():
                for prov in field_provs:
                    if prov.get("id") == provenance_id:
                        prov["verification_state"] = verification_state
                        prov["verified_at"] = datetime.utcnow().isoformat()
                        if verification_method:
                            prov["verification_method"] = verification_method
                        if user_verified:
                            prov["user_verified"] = True
                        if user_override:
                            prov["user_override"] = True
                            prov["override_at"] = datetime.utcnow().isoformat()
                        if override_reason:
                            prov["override_reason"] = override_reason
                        found = True
                        updated_prov = prov
                        break
                if found:
                    break

        if not found:
            return {"error": f"Provenance record not found: {provenance_id}"}

        # Update entity
        result = handler.update_person(safe_name, entity_id, {"profile": profile})

        if not result:
            return {"error": "Failed to update verification state"}

        return {
            "success": True,
            "entity_id": entity_id,
            "provenance": updated_prov
        }

    @mcp.tool()
    def create_provenance_record(
        source_type: str,
        capture_method: str = "manual",
        source_url: str = None,
        source_title: str = None,
        captured_by: str = None,
        confidence: float = 0.5,
        page_context: str = None,
        element_selector: str = None,
        external_tool: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Create a standalone provenance record without attaching to an entity.

        Useful for preparing provenance data that will be attached later,
        or for including in entity creation calls.

        Args:
            source_type: Type of source (website, api, file_import, manual, etc.)
            capture_method: How data was captured
            source_url: URL where data was found (optional)
            source_title: Title of source page/document (optional)
            captured_by: Component/agent that captured data (optional)
            confidence: Confidence score 0.0 to 1.0 (default: 0.5)
            page_context: Surrounding text/context (optional)
            element_selector: CSS selector or XPath (optional)
            external_tool: External tool name if applicable (optional)
            metadata: Additional metadata dict (optional)

        Returns:
            The provenance record ready to attach to entities
        """
        # Validate source_type
        try:
            source_type_enum = SourceType(source_type)
        except ValueError:
            valid_types = [st.value for st in SourceType]
            return {"error": f"Invalid source_type: {source_type}. Valid types: {valid_types}"}

        # Validate capture_method
        try:
            capture_method_enum = CaptureMethod(capture_method)
        except ValueError:
            valid_methods = [cm.value for cm in CaptureMethod]
            return {"error": f"Invalid capture_method: {capture_method}. Valid methods: {valid_methods}"}

        # Create provenance object
        provenance_create = ProvenanceCreate(
            source_type=source_type_enum,
            source_url=source_url,
            source_title=source_title,
            capture_method=capture_method_enum,
            captured_by=captured_by,
            confidence=confidence,
            page_context=page_context,
            element_selector=element_selector,
            external_tool=external_tool,
            metadata=metadata or {}
        )

        provenance = provenance_create.to_provenance()
        provenance_dict = provenance.to_dict()

        return {
            "id": str(uuid4()),
            **provenance_dict
        }


# Helper functions for descriptions
def _get_source_type_description(st: SourceType) -> str:
    """Get description for a source type."""
    descriptions = {
        SourceType.WEBSITE: "Data captured from a web page",
        SourceType.API: "Data from an external API",
        SourceType.FILE_IMPORT: "Data imported from a file",
        SourceType.MANUAL_ENTRY: "Manually entered by user",
        SourceType.BROWSER_EXTENSION: "Captured via autofill-extension",
        SourceType.OSINT_AGENT: "Captured by basset-hound-browser agent",
        SourceType.MCP_TOOL: "Ingested via MCP tool",
        SourceType.THIRD_PARTY: "External OSINT tool (Maltego, SpiderFoot, etc.)",
        SourceType.CLIPBOARD: "Pasted from clipboard",
        SourceType.OCR: "Extracted via OCR",
        SourceType.SCREENSHOT: "Extracted from screenshot",
        SourceType.OTHER: "Other source type",
    }
    return descriptions.get(st, "")


def _get_capture_method_description(cm: CaptureMethod) -> str:
    """Get description for a capture method."""
    descriptions = {
        CaptureMethod.AUTO_DETECTED: "Automatically detected by system",
        CaptureMethod.USER_SELECTED: "User manually selected element",
        CaptureMethod.FORM_AUTOFILL: "Captured from form fill",
        CaptureMethod.CLIPBOARD_PASTE: "Pasted content",
        CaptureMethod.FILE_UPLOAD: "Uploaded file",
        CaptureMethod.API_FETCH: "Fetched from API",
        CaptureMethod.SCRAPE: "Web scraping",
        CaptureMethod.MANUAL_INPUT: "Typed manually",
    }
    return descriptions.get(cm, "")


def _get_verification_state_description(vs: VerificationState) -> str:
    """Get description for a verification state."""
    descriptions = {
        VerificationState.UNVERIFIED: "Not yet verified",
        VerificationState.FORMAT_VALID: "Format validation passed",
        VerificationState.NETWORK_VERIFIED: "Network checks passed",
        VerificationState.API_VERIFIED: "External API verification passed",
        VerificationState.HUMAN_VERIFIED: "Verified by human analyst",
        VerificationState.USER_OVERRIDE: "User overrode verification result",
        VerificationState.FAILED: "Verification failed",
        VerificationState.EXPIRED: "Previous verification expired",
    }
    return descriptions.get(vs, "")
