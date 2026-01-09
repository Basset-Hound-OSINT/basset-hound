"""
Browser integration tools for MCP.

Provides tools for browser extensions and Electron apps to integrate with
basset-hound for form autofill, evidence capture, and investigation context.

These tools enable:
- Form field mapping and autofill data
- Evidence storage with chain of custody
- Sock puppet profile retrieval
- Browser session tracking
- Investigation context for decision-making
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import uuid4
import base64
import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.services.file_hash_service import FileHashService
from .base import get_neo4j_handler, get_project_safe_name


def register_browser_integration_tools(mcp):
    """Register browser integration tools with the MCP server."""

    # Initialize hash service
    hash_service = FileHashService()

    # =========================================================================
    # AUTOFILL DATA TOOLS
    # =========================================================================

    @mcp.tool()
    def get_autofill_data(
        project_id: str,
        entity_id: str,
        include_sock_puppet: bool = False
    ) -> dict:
        """
        Get flattened entity data formatted for form autofill.

        Returns entity data in a flat structure suitable for browser form filling.
        Field names follow common HTML form conventions (firstName, lastName, email, etc.).

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to get data from
            include_sock_puppet: Include sock puppet override data if entity is a puppet

        Returns:
            Flattened dictionary with autofill-friendly field names:
            {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "company": "Acme Inc",
                "jobTitle": "CEO",
                "address": {...},
                "city": "Seattle",
                "country": "US",
                ...
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        profile = entity.get("profile", {})
        autofill_data = {}

        # Core fields
        core = profile.get("core", {})
        names = core.get("name", [])
        if names and isinstance(names, list) and len(names) > 0:
            name_data = names[0]
            if isinstance(name_data, dict):
                autofill_data["firstName"] = name_data.get("first_name", "")
                autofill_data["lastName"] = name_data.get("last_name", "")
                autofill_data["middleName"] = name_data.get("middle_name", "")
                autofill_data["fullName"] = " ".join(filter(None, [
                    name_data.get("first_name", ""),
                    name_data.get("middle_name", ""),
                    name_data.get("last_name", "")
                ]))

        # Contact fields
        contact = profile.get("contact", {})
        emails = contact.get("email", [])
        if emails and isinstance(emails, list):
            autofill_data["email"] = emails[0] if isinstance(emails[0], str) else emails[0].get("address", "")

        phones = contact.get("phone", [])
        if phones and isinstance(phones, list):
            autofill_data["phone"] = phones[0] if isinstance(phones[0], str) else phones[0].get("number", "")

        # Professional fields
        professional = profile.get("professional", {})
        autofill_data["company"] = professional.get("company", "")
        autofill_data["jobTitle"] = professional.get("job_title", "")

        # Location fields
        locations = profile.get("location", {}).get("addresses", [])
        if locations and isinstance(locations, list) and len(locations) > 0:
            address = locations[0]
            if isinstance(address, dict):
                autofill_data["address"] = address.get("street", "")
                autofill_data["address2"] = address.get("street2", "")
                autofill_data["city"] = address.get("city", "")
                autofill_data["state"] = address.get("state", "")
                autofill_data["zipCode"] = address.get("zip", "")
                autofill_data["country"] = address.get("country", "")

        # Sock puppet override
        if include_sock_puppet:
            sock_puppet = profile.get("_sock_puppet", {})
            if sock_puppet.get("is_sock_puppet"):
                # Override with sock puppet identity
                if sock_puppet.get("alias_name"):
                    parts = sock_puppet["alias_name"].split()
                    if len(parts) >= 2:
                        autofill_data["firstName"] = parts[0]
                        autofill_data["lastName"] = " ".join(parts[1:])
                    autofill_data["fullName"] = sock_puppet["alias_name"]

                # Use sock puppet-specific contact info if available
                platform_accounts = sock_puppet.get("platform_accounts", [])
                if platform_accounts:
                    # Use first platform account's email
                    autofill_data["email"] = platform_accounts[0].get("email", autofill_data.get("email", ""))

        return {
            "success": True,
            "entity_id": entity_id,
            "data": autofill_data,
            "is_sock_puppet": include_sock_puppet and profile.get("_sock_puppet", {}).get("is_sock_puppet", False)
        }

    @mcp.tool()
    def suggest_form_mapping(
        project_id: str,
        entity_id: str,
        form_fields: list
    ) -> dict:
        """
        Suggest mappings between form fields and entity data paths.

        Uses heuristics to match form field names/labels to entity profile paths.
        Returns confidence scores for each mapping.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to map to
            form_fields: List of field descriptors:
                [
                    {
                        "id": "email_input",
                        "name": "email",
                        "type": "email",
                        "label": "Email Address",
                        "placeholder": "Enter your email"
                    }
                ]

        Returns:
            {
                "mappings": [
                    {
                        "field_id": "email_input",
                        "entity_path": "contact.email",
                        "autofill_key": "email",
                        "confidence": 0.95
                    }
                ]
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        mappings = []

        # Field type to entity path mapping patterns
        patterns = {
            "email": {
                "keywords": ["email", "e-mail", "mail"],
                "path": "contact.email",
                "autofill_key": "email",
                "confidence": 0.95
            },
            "tel": {
                "keywords": ["phone", "tel", "mobile", "cell"],
                "path": "contact.phone",
                "autofill_key": "phone",
                "confidence": 0.90
            },
            "text": {
                "first_name": {
                    "keywords": ["first", "fname", "given", "forename"],
                    "path": "core.name[0].first_name",
                    "autofill_key": "firstName",
                    "confidence": 0.90
                },
                "last_name": {
                    "keywords": ["last", "lname", "surname", "family"],
                    "path": "core.name[0].last_name",
                    "autofill_key": "lastName",
                    "confidence": 0.90
                },
                "full_name": {
                    "keywords": ["full.?name", "name", "display.?name"],
                    "path": "core.name[0]",
                    "autofill_key": "fullName",
                    "confidence": 0.80
                },
                "company": {
                    "keywords": ["company", "organization", "employer"],
                    "path": "professional.company",
                    "autofill_key": "company",
                    "confidence": 0.85
                },
                "job_title": {
                    "keywords": ["job", "title", "position", "role"],
                    "path": "professional.job_title",
                    "autofill_key": "jobTitle",
                    "confidence": 0.80
                },
                "address": {
                    "keywords": ["address", "street"],
                    "path": "location.addresses[0].street",
                    "autofill_key": "address",
                    "confidence": 0.85
                },
                "city": {
                    "keywords": ["city", "town"],
                    "path": "location.addresses[0].city",
                    "autofill_key": "city",
                    "confidence": 0.90
                },
                "state": {
                    "keywords": ["state", "province", "region"],
                    "path": "location.addresses[0].state",
                    "autofill_key": "state",
                    "confidence": 0.85
                },
                "zip": {
                    "keywords": ["zip", "postal", "postcode"],
                    "path": "location.addresses[0].zip",
                    "autofill_key": "zipCode",
                    "confidence": 0.90
                },
                "country": {
                    "keywords": ["country", "nation"],
                    "path": "location.addresses[0].country",
                    "autofill_key": "country",
                    "confidence": 0.90
                }
            }
        }

        for field in form_fields:
            field_id = field.get("id", "")
            field_name = field.get("name", "").lower()
            field_type = field.get("type", "text").lower()
            field_label = field.get("label", "").lower()
            field_placeholder = field.get("placeholder", "").lower()

            # Combine all text for matching
            combined = f"{field_name} {field_label} {field_placeholder}"

            # Try type-specific patterns first
            if field_type in patterns:
                pattern = patterns[field_type]
                if isinstance(pattern, dict) and "keywords" in pattern:
                    # Simple type match (email, tel)
                    for keyword in pattern["keywords"]:
                        if keyword in combined:
                            mappings.append({
                                "field_id": field_id,
                                "entity_path": pattern["path"],
                                "autofill_key": pattern["autofill_key"],
                                "confidence": pattern["confidence"]
                            })
                            break
                else:
                    # Complex type match (text with sub-patterns)
                    for subtype, subpattern in pattern.items():
                        for keyword in subpattern["keywords"]:
                            if keyword in combined:
                                mappings.append({
                                    "field_id": field_id,
                                    "entity_path": subpattern["path"],
                                    "autofill_key": subpattern["autofill_key"],
                                    "confidence": subpattern["confidence"]
                                })
                                break

        return {
            "success": True,
            "entity_id": entity_id,
            "mappings": mappings,
            "field_count": len(form_fields),
            "mapped_count": len(mappings)
        }

    # =========================================================================
    # EVIDENCE CAPTURE TOOLS
    # =========================================================================

    @mcp.tool()
    def capture_evidence(
        project_id: str,
        investigation_id: str = None,
        evidence_type: str = "screenshot",
        content_base64: str = None,
        url: str = None,
        metadata: dict = None,
        captured_by: str = "browser"
    ) -> dict:
        """
        Store evidence captured by browser with chain of custody.

        Stores evidence in project with automatic provenance tracking and
        SHA-256 hash for integrity verification. Creates chain of custody record.

        Args:
            project_id: The project ID or safe_name
            investigation_id: Optional investigation ID to link evidence
            evidence_type: Type of evidence (screenshot, page_archive, network_har,
                          dom_snapshot, console_log, cookies, local_storage, metadata)
            content_base64: Base64 encoded evidence content
            url: Source URL where evidence was captured
            metadata: Additional metadata dict (title, timestamp, viewport, etc.)
            captured_by: Source identifier (browser, extension, agent name)

        Returns:
            {
                "evidence_id": "ev_123",
                "sha256": "abc...",
                "provenance_id": "prov_456",
                "chain_of_custody_started": true,
                "stored_at": "2026-01-08T..."
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not content_base64:
            return {"error": "content_base64 is required"}

        # Generate evidence ID
        evidence_id = f"ev_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

        # Decode and hash content using FileHashService
        try:
            content_bytes = base64.b64decode(content_base64)
            sha256_hash = hash_service.compute_hash_from_bytes(content_bytes)
        except Exception as e:
            return {"error": f"Failed to decode content_base64: {str(e)}"}

        now = datetime.now().isoformat()

        # Check for duplicate evidence with same hash
        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        existing_evidence = project.get("_evidence", [])
        duplicates = [ev for ev in existing_evidence if ev.get("sha256") == sha256_hash]

        # Create evidence record
        evidence_record = {
            "id": evidence_id,
            "type": evidence_type,
            "sha256": sha256_hash,
            "content_size": len(content_bytes),
            "url": url,
            "metadata": metadata or {},
            "captured_by": captured_by,
            "captured_at": now,
            "investigation_id": investigation_id,

            # Chain of custody
            "custody_chain": [
                {
                    "timestamp": now,
                    "action": "captured",
                    "actor": captured_by,
                    "details": f"Evidence captured from {url or 'unknown source'}"
                }
            ]
        }

        # Store in project's _evidence section
        if "_evidence" not in project:
            project["_evidence"] = []

        project["_evidence"].append(evidence_record)

        # Update project
        result = handler.update_project(safe_name, {"_evidence": project["_evidence"]})

        if not result:
            return {"error": "Failed to store evidence"}

        # TODO: In production, store actual content_bytes to filesystem or S3
        # For now, just track metadata in Neo4j

        response = {
            "success": True,
            "evidence_id": evidence_id,
            "sha256": sha256_hash,
            "content_size": len(content_bytes),
            "chain_of_custody_started": True,
            "stored_at": now
        }

        # Add duplicate warning if found
        if duplicates:
            response["duplicate_detected"] = True
            response["duplicate_count"] = len(duplicates)
            response["duplicate_evidence_ids"] = [d["id"] for d in duplicates[:5]]
            response["warning"] = f"This evidence matches {len(duplicates)} existing evidence item(s)"
        else:
            response["duplicate_detected"] = False

        return response

    @mcp.tool()
    def get_evidence(
        project_id: str,
        evidence_id: str
    ) -> dict:
        """
        Retrieve stored evidence metadata.

        Args:
            project_id: The project ID or safe_name
            evidence_id: The evidence ID to retrieve

        Returns:
            Evidence record with metadata and custody chain
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        evidence_list = project.get("_evidence", [])
        for evidence in evidence_list:
            if evidence.get("id") == evidence_id:
                return {
                    "success": True,
                    "evidence": evidence
                }

        return {"error": f"Evidence not found: {evidence_id}"}

    @mcp.tool()
    def list_evidence(
        project_id: str,
        investigation_id: str = None,
        evidence_type: str = None,
        limit: int = 100
    ) -> dict:
        """
        List evidence for a project or investigation.

        Args:
            project_id: The project ID or safe_name
            investigation_id: Filter by investigation (optional)
            evidence_type: Filter by type (optional)
            limit: Maximum results to return (default: 100)

        Returns:
            List of evidence records
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        evidence_list = project.get("_evidence", [])

        # Apply filters
        if investigation_id:
            evidence_list = [e for e in evidence_list if e.get("investigation_id") == investigation_id]
        if evidence_type:
            evidence_list = [e for e in evidence_list if e.get("type") == evidence_type]

        # Sort by captured_at descending
        evidence_list = sorted(evidence_list, key=lambda x: x.get("captured_at", ""), reverse=True)

        # Limit
        evidence_list = evidence_list[:limit]

        return {
            "success": True,
            "count": len(evidence_list),
            "evidence": evidence_list
        }

    @mcp.tool()
    def verify_evidence_integrity(
        project_id: str,
        evidence_id: str,
        content_base64: str
    ) -> dict:
        """
        Verify evidence integrity by comparing SHA-256 hashes.

        Args:
            project_id: The project ID or safe_name
            evidence_id: The evidence ID to verify
            content_base64: Current content to verify against stored hash

        Returns:
            {
                "verified": true/false,
                "stored_hash": "abc...",
                "computed_hash": "abc...",
                "match": true/false
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Get stored evidence
        evidence_result = get_evidence(project_id, evidence_id)
        if "error" in evidence_result:
            return evidence_result

        stored_hash = evidence_result["evidence"].get("sha256")

        # Compute current hash
        try:
            content_bytes = base64.b64decode(content_base64)
            computed_hash = hashlib.sha256(content_bytes).hexdigest()
        except Exception as e:
            return {"error": f"Failed to decode content: {str(e)}"}

        match = (stored_hash == computed_hash)

        return {
            "success": True,
            "evidence_id": evidence_id,
            "verified": match,
            "stored_hash": stored_hash,
            "computed_hash": computed_hash,
            "match": match
        }

    # =========================================================================
    # SOCK PUPPET PROFILE TOOLS
    # =========================================================================

    @mcp.tool()
    def get_sock_puppet_profile(
        project_id: str,
        puppet_id: str,
        platform: str = None,
        include_credentials_ref: bool = False
    ) -> dict:
        """
        Get sock puppet identity profile for browser use.

        Returns identity suitable for form filling and authentication.
        DOES NOT return actual credentials - only references to credential vault.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet ID
            platform: Filter platform accounts (optional)
            include_credentials_ref: Include credential vault references

        Returns:
            {
                "alias_name": "Cover Identity",
                "backstory": "IT Consultant from Seattle...",
                "birth_date": "1985-03-15",
                "nationality": "US",
                "occupation": "IT Consultant",
                "platform_accounts": [
                    {
                        "platform": "linkedin",
                        "username": "cover.identity",
                        "email": "cover@protonmail.com",
                        "credential_vault_ref": "keepass://..."  # Only if include_credentials_ref
                    }
                ]
            }
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        # Find sock puppet in project
        puppets = project.get("_sock_puppets", [])
        puppet = None
        for p in puppets:
            if p.get("id") == puppet_id:
                puppet = p
                break

        if not puppet:
            return {"error": f"Sock puppet not found: {puppet_id}"}

        # Build profile
        profile = {
            "id": puppet_id,
            "alias_name": puppet.get("alias_name"),
            "backstory": puppet.get("backstory"),
            "purpose": puppet.get("purpose"),
            "birth_date": puppet.get("birth_date"),
            "nationality": puppet.get("nationality"),
            "occupation": puppet.get("occupation"),
            "platform_accounts": []
        }

        # Platform accounts
        accounts = puppet.get("platform_accounts", [])
        for account in accounts:
            # Filter by platform if specified
            if platform and account.get("platform") != platform:
                continue

            account_data = {
                "platform": account.get("platform"),
                "username": account.get("username"),
                "email": account.get("email"),
                "account_status": account.get("account_status")
            }

            # Include credential reference if requested
            if include_credentials_ref:
                account_data["credential_vault_ref"] = account.get("credential_vault_ref")

            profile["platform_accounts"].append(account_data)

        return {
            "success": True,
            "profile": profile,
            "is_active": puppet.get("status") == "active"
        }

    # =========================================================================
    # BROWSER SESSION TOOLS
    # =========================================================================

    @mcp.tool()
    def register_browser_session(
        project_id: str,
        session_id: str,
        browser_type: str,
        user_agent: str = None,
        fingerprint_hash: str = None
    ) -> dict:
        """
        Register a browser session for tracking.

        Enables correlation of evidence to browser instances and
        tracking of investigation activities across sessions.

        Args:
            project_id: The project ID or safe_name
            session_id: Unique session identifier
            browser_type: Type of browser (electron, chrome_extension, firefox_extension)
            user_agent: Browser user agent string
            fingerprint_hash: Browser fingerprint hash for tracking

        Returns:
            Session registration confirmation
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        now = datetime.now().isoformat()

        # Create session record
        session = {
            "id": session_id,
            "browser_type": browser_type,
            "user_agent": user_agent,
            "fingerprint_hash": fingerprint_hash,
            "started_at": now,
            "last_activity": now,
            "status": "active",
            "page_visits": 0,
            "evidence_captured": 0
        }

        # Store in project's _browser_sessions section
        if "_browser_sessions" not in project:
            project["_browser_sessions"] = []

        # Check if session already exists
        for existing_session in project["_browser_sessions"]:
            if existing_session.get("id") == session_id:
                return {"error": f"Session already registered: {session_id}"}

        project["_browser_sessions"].append(session)

        # Update project
        result = handler.update_project(safe_name, {"_browser_sessions": project["_browser_sessions"]})

        if not result:
            return {"error": "Failed to register session"}

        return {
            "success": True,
            "session_id": session_id,
            "registered_at": now
        }

    @mcp.tool()
    def update_browser_session(
        project_id: str,
        session_id: str,
        page_visits: int = None,
        evidence_captured: int = None
    ) -> dict:
        """
        Update browser session activity counters.

        Args:
            project_id: The project ID or safe_name
            session_id: The session ID to update
            page_visits: Total page visits (optional)
            evidence_captured: Total evidence items captured (optional)

        Returns:
            Updated session information
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        sessions = project.get("_browser_sessions", [])
        session = None
        for s in sessions:
            if s.get("id") == session_id:
                session = s
                break

        if not session:
            return {"error": f"Session not found: {session_id}"}

        now = datetime.now().isoformat()

        # Update fields
        if page_visits is not None:
            session["page_visits"] = page_visits
        if evidence_captured is not None:
            session["evidence_captured"] = evidence_captured

        session["last_activity"] = now

        # Update project
        result = handler.update_project(safe_name, {"_browser_sessions": project["_browser_sessions"]})

        if not result:
            return {"error": "Failed to update session"}

        return {
            "success": True,
            "session": session
        }

    @mcp.tool()
    def end_browser_session(
        project_id: str,
        session_id: str
    ) -> dict:
        """
        End a browser session.

        Args:
            project_id: The project ID or safe_name
            session_id: The session ID to end

        Returns:
            Session summary
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        sessions = project.get("_browser_sessions", [])
        session = None
        for s in sessions:
            if s.get("id") == session_id:
                session = s
                break

        if not session:
            return {"error": f"Session not found: {session_id}"}

        now = datetime.now().isoformat()

        session["status"] = "ended"
        session["ended_at"] = now

        # Calculate duration
        started_at = datetime.fromisoformat(session.get("started_at"))
        ended_at = datetime.fromisoformat(now)
        duration_seconds = (ended_at - started_at).total_seconds()
        session["duration_seconds"] = duration_seconds

        # Update project
        result = handler.update_project(safe_name, {"_browser_sessions": project["_browser_sessions"]})

        if not result:
            return {"error": "Failed to end session"}

        return {
            "success": True,
            "session_id": session_id,
            "duration_seconds": duration_seconds,
            "page_visits": session.get("page_visits", 0),
            "evidence_captured": session.get("evidence_captured", 0)
        }

    @mcp.tool()
    def get_investigation_context(
        project_id: str,
        investigation_id: str = None,
        include_subjects: bool = True,
        include_recent_activity: bool = True
    ) -> dict:
        """
        Get investigation context for browser/agent decision-making.

        Returns current investigation state useful for:
        - Deciding what to capture
        - Identifying known entities on page
        - Suggesting next investigation steps

        Args:
            project_id: The project ID or safe_name
            investigation_id: The investigation ID (optional, returns project context if None)
            include_subjects: Include subject list
            include_recent_activity: Include recent activity log

        Returns:
            Investigation context with subjects, targets, and recent activity
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        context = {
            "project_id": project_id,
            "project_name": project.get("name")
        }

        if investigation_id:
            # Get specific investigation
            investigation = project.get("_investigation")
            if not investigation or investigation.get("id") != investigation_id:
                return {"error": f"Investigation not found: {investigation_id}"}

            context["investigation_id"] = investigation_id
            context["investigation_title"] = investigation.get("title")
            context["status"] = investigation.get("status")
            context["phase"] = investigation.get("phase")
            context["priority"] = investigation.get("priority")

            if include_subjects:
                context["subjects"] = investigation.get("subjects", [])

            if include_recent_activity:
                activity_log = investigation.get("activity_log", [])
                # Get last 10 activities
                context["recent_activity"] = sorted(
                    activity_log,
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True
                )[:10]
        else:
            # Project-level context
            context["entity_count"] = len(project.get("people", []))
            context["investigation_count"] = 1 if project.get("_investigation") else 0

        return {
            "success": True,
            "context": context
        }
