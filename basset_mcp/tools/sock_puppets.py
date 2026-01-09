"""
Sock puppet identity management tools for MCP.

Provides tools for managing undercover/sock puppet identities in OSINT investigations.
Sock puppets are specialized entities with cover identities, operational metadata,
platform accounts, and lifecycle tracking for OPSEC compliance.

SECURITY NOTE: This module stores metadata and vault references only.
Actual credentials should NEVER be stored in basset-hound - use external
password managers (KeePass, HashiCorp Vault, etc.) and store only references.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum

from .base import get_neo4j_handler, get_project_safe_name


# Sock Puppet Status Enum
class SockPuppetStatus(str, Enum):
    PLANNING = "planning"       # Being set up, not yet deployed
    ACTIVE = "active"           # Currently in operational use
    DORMANT = "dormant"         # Not currently used but available
    BURNED = "burned"           # Compromised, no longer safe to use
    RETIRED = "retired"         # Voluntarily decommissioned


# Sock Puppet Purpose Enum
class SockPuppetPurpose(str, Enum):
    PASSIVE_SURVEILLANCE = "passive_surveillance"   # Observation only
    ACTIVE_ENGAGEMENT = "active_engagement"         # Direct interaction
    INFILTRATION = "infiltration"                   # Deep cover
    RESEARCH = "research"                           # OSINT research accounts


# Risk Level Enum
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def register_sock_puppet_tools(mcp):
    """Register sock puppet management tools with the MCP server."""

    @mcp.tool()
    def create_sock_puppet(
        project_id: str,
        alias_name: str,
        backstory: str = "",
        birth_date: str = None,
        nationality: str = None,
        occupation: str = None,
        location: dict = None,
        handler_id: str = None,
        operation_id: str = None,
        purpose: str = "research",
        risk_level: str = "low",
        burn_date: str = None,
        notes: str = "",
        profile_data: dict = None
    ) -> dict:
        """
        Create a new sock puppet identity.

        Sock puppets are specialized PERSON entities with additional operational
        metadata for managing undercover identities in OSINT investigations.

        Args:
            project_id: The project ID or safe_name
            alias_name: The persona's display name/alias
            backstory: Detailed cover story/legend
            birth_date: Fictitious date of birth (ISO format)
            nationality: Claimed nationality
            occupation: Cover occupation
            location: Claimed location dict (city, country, etc.)
            handler_id: Entity ID of the handler/operator
            operation_id: Associated operation/investigation ID
            purpose: Purpose enum (passive_surveillance, active_engagement, infiltration, research)
            risk_level: Risk assessment (low, medium, high, critical)
            burn_date: Scheduled retirement date (ISO format)
            notes: Additional notes
            profile_data: Additional profile data following schema

        Returns:
            The created sock puppet entity with operational metadata
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate purpose
        try:
            purpose_enum = SockPuppetPurpose(purpose)
        except ValueError:
            valid = [p.value for p in SockPuppetPurpose]
            return {"error": f"Invalid purpose: {purpose}. Valid: {valid}"}

        # Validate risk_level
        try:
            risk_enum = RiskLevel(risk_level)
        except ValueError:
            valid = [r.value for r in RiskLevel]
            return {"error": f"Invalid risk_level: {risk_level}. Valid: {valid}"}

        now = datetime.now().isoformat()
        puppet_id = str(uuid4())

        # Build profile with sock puppet sections
        profile = profile_data or {}

        # Add sock puppet operational section
        profile["_sock_puppet"] = {
            "is_sock_puppet": True,
            "alias_name": alias_name,
            "backstory": backstory,
            "birth_date": birth_date,
            "nationality": nationality,
            "occupation": occupation,
            "location": location or {},
            "handler_id": handler_id,
            "operation_id": operation_id,
            "purpose": purpose,
            "status": SockPuppetStatus.PLANNING.value,
            "risk_level": risk_level,
            "created_date": now,
            "activated_date": None,
            "burn_date": burn_date,
            "burned_date": None,
            "retirement_reason": None,
            "last_activity": None,
            "notes": notes,
            "platform_accounts": [],
            "activity_log": []
        }

        # Add core identity fields
        if "core" not in profile:
            profile["core"] = {}
        profile["core"]["name"] = [{"first_name": alias_name.split()[0] if alias_name else "Unknown"}]
        if alias_name and " " in alias_name:
            profile["core"]["name"][0]["last_name"] = " ".join(alias_name.split()[1:])

        # Create the entity
        result = handler.create_person(safe_name, {"profile": profile})

        if not result:
            return {"error": "Failed to create sock puppet"}

        return {
            "id": result.get("id"),
            "alias_name": alias_name,
            "status": SockPuppetStatus.PLANNING.value,
            "purpose": purpose,
            "risk_level": risk_level,
            "created_at": now,
            "entity": result
        }

    @mcp.tool()
    def get_sock_puppet(project_id: str, puppet_id: str) -> dict:
        """
        Get a sock puppet by ID.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID

        Returns:
            The sock puppet entity with operational metadata
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)

        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sock_puppet_data = profile.get("_sock_puppet")

        if not sock_puppet_data or not sock_puppet_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        return {
            "id": puppet_id,
            "operational_data": sock_puppet_data,
            "entity": entity
        }

    @mcp.tool()
    def list_sock_puppets(
        project_id: str,
        status: str = None,
        handler_id: str = None,
        purpose: str = None,
        risk_level: str = None
    ) -> dict:
        """
        List sock puppets with optional filtering.

        Args:
            project_id: The project ID or safe_name
            status: Filter by status (planning, active, dormant, burned, retired)
            handler_id: Filter by handler ID
            purpose: Filter by purpose
            risk_level: Filter by risk level

        Returns:
            List of sock puppet summaries
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        all_entities = handler.get_all_people(safe_name)
        puppets = []

        for entity in all_entities:
            profile = entity.get("profile", {})
            sp_data = profile.get("_sock_puppet")

            if not sp_data or not sp_data.get("is_sock_puppet"):
                continue

            # Apply filters
            if status and sp_data.get("status") != status:
                continue
            if handler_id and sp_data.get("handler_id") != handler_id:
                continue
            if purpose and sp_data.get("purpose") != purpose:
                continue
            if risk_level and sp_data.get("risk_level") != risk_level:
                continue

            puppets.append({
                "id": entity.get("id"),
                "alias_name": sp_data.get("alias_name"),
                "status": sp_data.get("status"),
                "purpose": sp_data.get("purpose"),
                "risk_level": sp_data.get("risk_level"),
                "handler_id": sp_data.get("handler_id"),
                "platform_count": len(sp_data.get("platform_accounts", [])),
                "last_activity": sp_data.get("last_activity"),
                "burn_date": sp_data.get("burn_date")
            })

        return {
            "project_id": project_id,
            "count": len(puppets),
            "sock_puppets": puppets
        }

    @mcp.tool()
    def activate_sock_puppet(
        project_id: str,
        puppet_id: str,
        operation_id: str = None
    ) -> dict:
        """
        Activate a sock puppet for operational use.

        Changes status from planning/dormant to active and records activation timestamp.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            operation_id: Optional operation/investigation to associate

        Returns:
            Updated sock puppet data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        current_status = sp_data.get("status")
        if current_status == SockPuppetStatus.BURNED.value:
            return {"error": "Cannot activate a burned sock puppet"}
        if current_status == SockPuppetStatus.ACTIVE.value:
            return {"error": "Sock puppet is already active", "sock_puppet": sp_data}

        now = datetime.now().isoformat()
        sp_data["status"] = SockPuppetStatus.ACTIVE.value
        sp_data["activated_date"] = now
        sp_data["last_activity"] = now
        if operation_id:
            sp_data["operation_id"] = operation_id

        # Log activation
        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "activated",
            "details": {"operation_id": operation_id}
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to activate sock puppet"}

        return {
            "success": True,
            "id": puppet_id,
            "status": SockPuppetStatus.ACTIVE.value,
            "activated_date": now,
            "sock_puppet": sp_data
        }

    @mcp.tool()
    def deactivate_sock_puppet(
        project_id: str,
        puppet_id: str,
        reason: str = ""
    ) -> dict:
        """
        Deactivate a sock puppet (set to dormant).

        Use this when temporarily stopping use of a puppet but it's not compromised.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            reason: Reason for deactivation

        Returns:
            Updated sock puppet data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()
        sp_data["status"] = SockPuppetStatus.DORMANT.value
        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "deactivated",
            "details": {"reason": reason}
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to deactivate sock puppet"}

        return {
            "success": True,
            "id": puppet_id,
            "status": SockPuppetStatus.DORMANT.value,
            "sock_puppet": sp_data
        }

    @mcp.tool()
    def burn_sock_puppet(
        project_id: str,
        puppet_id: str,
        compromise_details: str,
        compromised_platforms: list = None
    ) -> dict:
        """
        Mark a sock puppet as burned/compromised.

        Use this when a puppet identity has been discovered or compromised.
        This is a permanent status change - burned puppets cannot be reactivated.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            compromise_details: Description of how/why the puppet was compromised
            compromised_platforms: List of platforms where compromise was detected

        Returns:
            Updated sock puppet data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()
        sp_data["status"] = SockPuppetStatus.BURNED.value
        sp_data["burned_date"] = now
        sp_data["retirement_reason"] = f"BURNED: {compromise_details}"
        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "burned",
            "details": {
                "compromise_details": compromise_details,
                "compromised_platforms": compromised_platforms or []
            }
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to burn sock puppet"}

        return {
            "success": True,
            "id": puppet_id,
            "status": SockPuppetStatus.BURNED.value,
            "burned_date": now,
            "warning": "This sock puppet is now permanently marked as compromised",
            "sock_puppet": sp_data
        }

    @mcp.tool()
    def retire_sock_puppet(
        project_id: str,
        puppet_id: str,
        reason: str
    ) -> dict:
        """
        Voluntarily retire a sock puppet.

        Use this when a puppet is no longer needed but wasn't compromised.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            reason: Reason for retirement

        Returns:
            Updated sock puppet data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()
        sp_data["status"] = SockPuppetStatus.RETIRED.value
        sp_data["retirement_reason"] = reason
        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "retired",
            "details": {"reason": reason}
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to retire sock puppet"}

        return {
            "success": True,
            "id": puppet_id,
            "status": SockPuppetStatus.RETIRED.value,
            "sock_puppet": sp_data
        }

    @mcp.tool()
    def add_platform_account(
        project_id: str,
        puppet_id: str,
        platform: str,
        username: str,
        email: str = None,
        phone_number: str = None,
        credential_vault_ref: str = None,
        profile_url: str = None,
        account_status: str = "active",
        notes: str = ""
    ) -> dict:
        """
        Add a platform account to a sock puppet.

        SECURITY: Store only metadata and vault references here.
        Actual passwords/2FA seeds should be in external password manager.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            platform: Platform name (facebook, linkedin, twitter, etc.)
            username: Platform username/handle
            email: Associated email address
            phone_number: Associated phone number
            credential_vault_ref: Reference to credentials in password manager
            profile_url: Direct URL to profile
            account_status: Account status (active, suspended, banned, dormant)
            notes: Platform-specific notes

        Returns:
            Updated sock puppet with new platform account
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()

        # Check if platform already exists
        for acct in sp_data.get("platform_accounts", []):
            if acct.get("platform") == platform and acct.get("username") == username:
                return {"error": f"Account already exists for {platform}:{username}"}

        account = {
            "id": str(uuid4()),
            "platform": platform,
            "username": username,
            "email": email,
            "phone_number": phone_number,
            "credential_vault_ref": credential_vault_ref,
            "profile_url": profile_url,
            "account_created": now,
            "last_login": None,
            "account_status": account_status,
            "connection_count": 0,
            "notes": notes
        }

        sp_data["platform_accounts"].append(account)
        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "platform_added",
            "details": {"platform": platform, "username": username}
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to add platform account"}

        return {
            "success": True,
            "id": puppet_id,
            "account": account,
            "platform_count": len(sp_data["platform_accounts"])
        }

    @mcp.tool()
    def update_platform_account(
        project_id: str,
        puppet_id: str,
        platform: str,
        username: str = None,
        credential_vault_ref: str = None,
        account_status: str = None,
        last_login: str = None,
        connection_count: int = None,
        notes: str = None
    ) -> dict:
        """
        Update a platform account for a sock puppet.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            platform: Platform name to update
            username: Optional new username (if account was renamed)
            credential_vault_ref: Updated vault reference
            account_status: New status (active, suspended, banned, dormant)
            last_login: Last login timestamp
            connection_count: Updated connection/follower count
            notes: Updated notes

        Returns:
            Updated platform account
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        # Find the platform account
        account = None
        for acct in sp_data.get("platform_accounts", []):
            if acct.get("platform") == platform:
                account = acct
                break

        if not account:
            return {"error": f"Platform account not found: {platform}"}

        now = datetime.now().isoformat()

        # Apply updates
        if username is not None:
            account["username"] = username
        if credential_vault_ref is not None:
            account["credential_vault_ref"] = credential_vault_ref
        if account_status is not None:
            account["account_status"] = account_status
        if last_login is not None:
            account["last_login"] = last_login
        if connection_count is not None:
            account["connection_count"] = connection_count
        if notes is not None:
            account["notes"] = notes

        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "platform_updated",
            "details": {"platform": platform}
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to update platform account"}

        return {
            "success": True,
            "id": puppet_id,
            "platform": platform,
            "account": account
        }

    @mcp.tool()
    def record_puppet_activity(
        project_id: str,
        puppet_id: str,
        platform: str,
        activity_type: str,
        details: dict = None
    ) -> dict:
        """
        Record activity for a sock puppet.

        Use this to log interactions, posts, messages, etc. for audit trail.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            platform: Platform where activity occurred
            activity_type: Type of activity (login, post, message, connection, profile_view)
            details: Activity-specific details

        Returns:
            Activity record confirmation
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()

        activity_record = {
            "timestamp": now,
            "action": activity_type,
            "platform": platform,
            "details": details or {}
        }

        sp_data["activity_log"].append(activity_record)
        sp_data["last_activity"] = now

        # Update last_login for platform if this is a login activity
        if activity_type == "login":
            for acct in sp_data.get("platform_accounts", []):
                if acct.get("platform") == platform:
                    acct["last_login"] = now
                    break

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to record activity"}

        return {
            "success": True,
            "id": puppet_id,
            "activity": activity_record,
            "activity_log_count": len(sp_data["activity_log"])
        }

    @mcp.tool()
    def assign_handler(
        project_id: str,
        puppet_id: str,
        handler_id: str,
        notes: str = ""
    ) -> dict:
        """
        Assign or change the handler for a sock puppet.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            handler_id: Entity ID of the new handler/operator

        Returns:
            Updated handler assignment
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        now = datetime.now().isoformat()
        old_handler = sp_data.get("handler_id")
        sp_data["handler_id"] = handler_id
        sp_data["last_activity"] = now

        sp_data["activity_log"].append({
            "timestamp": now,
            "action": "handler_assigned",
            "details": {
                "old_handler": old_handler,
                "new_handler": handler_id,
                "notes": notes
            }
        })

        profile["_sock_puppet"] = sp_data
        result = handler.update_person(safe_name, puppet_id, {"profile": profile})

        if not result:
            return {"error": "Failed to assign handler"}

        return {
            "success": True,
            "id": puppet_id,
            "handler_id": handler_id,
            "previous_handler": old_handler
        }

    @mcp.tool()
    def get_puppet_activity_log(
        project_id: str,
        puppet_id: str,
        action_filter: str = None,
        platform_filter: str = None,
        limit: int = 100
    ) -> dict:
        """
        Get activity log for a sock puppet.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID
            action_filter: Filter by action type
            platform_filter: Filter by platform
            limit: Maximum entries to return

        Returns:
            Activity log entries
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        activity_log = sp_data.get("activity_log", [])

        # Apply filters
        if action_filter:
            activity_log = [a for a in activity_log if a.get("action") == action_filter]
        if platform_filter:
            activity_log = [a for a in activity_log if a.get("platform") == platform_filter]

        # Sort by timestamp descending and limit
        activity_log = sorted(activity_log, key=lambda x: x.get("timestamp", ""), reverse=True)
        activity_log = activity_log[:limit]

        return {
            "id": puppet_id,
            "alias_name": sp_data.get("alias_name"),
            "count": len(activity_log),
            "activity_log": activity_log
        }

    @mcp.tool()
    def assess_puppet_risk(project_id: str, puppet_id: str) -> dict:
        """
        Assess the current risk level of a sock puppet.

        Analyzes activity patterns, account status, and age to suggest risk level.

        Args:
            project_id: The project ID or safe_name
            puppet_id: The sock puppet entity ID

        Returns:
            Risk assessment with recommendations
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        entity = handler.get_person(safe_name, puppet_id)
        if not entity:
            return {"error": f"Entity not found: {puppet_id}"}

        profile = entity.get("profile", {})
        sp_data = profile.get("_sock_puppet")

        if not sp_data or not sp_data.get("is_sock_puppet"):
            return {"error": f"Entity {puppet_id} is not a sock puppet"}

        risks = []
        warnings = []
        score = 0  # Higher = more risk

        # Check account age vs activity
        created = sp_data.get("created_date")
        activated = sp_data.get("activated_date")
        if created and activated:
            try:
                created_dt = datetime.fromisoformat(created)
                activated_dt = datetime.fromisoformat(activated)
                age_days = (activated_dt - created_dt).days
                if age_days < 7:
                    risks.append("Account activated within 7 days of creation (not aged)")
                    score += 20
                elif age_days < 30:
                    warnings.append("Account only aged for less than 30 days")
                    score += 10
            except ValueError:
                pass

        # Check for burned date approaching
        burn_date = sp_data.get("burn_date")
        if burn_date:
            try:
                burn_dt = datetime.fromisoformat(burn_date)
                days_until_burn = (burn_dt - datetime.now()).days
                if days_until_burn < 0:
                    risks.append("PAST BURN DATE - should be retired immediately")
                    score += 50
                elif days_until_burn < 7:
                    warnings.append(f"Burn date in {days_until_burn} days")
                    score += 15
            except ValueError:
                pass

        # Check platform account status
        for acct in sp_data.get("platform_accounts", []):
            status = acct.get("account_status")
            if status == "suspended":
                risks.append(f"{acct.get('platform')} account is suspended")
                score += 30
            elif status == "banned":
                risks.append(f"{acct.get('platform')} account is banned")
                score += 40

        # Check for missing credential references
        for acct in sp_data.get("platform_accounts", []):
            if not acct.get("credential_vault_ref"):
                warnings.append(f"{acct.get('platform')} missing credential vault reference")

        # Determine overall risk level
        if score >= 50:
            risk_level = "critical"
        elif score >= 30:
            risk_level = "high"
        elif score >= 15:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "id": puppet_id,
            "alias_name": sp_data.get("alias_name"),
            "current_status": sp_data.get("status"),
            "assessed_risk_level": risk_level,
            "risk_score": score,
            "risks": risks,
            "warnings": warnings,
            "platform_count": len(sp_data.get("platform_accounts", [])),
            "recommendation": _get_risk_recommendation(risk_level, risks)
        }


def _get_risk_recommendation(risk_level: str, risks: list) -> str:
    """Generate recommendation based on risk assessment."""
    if "PAST BURN DATE" in str(risks):
        return "IMMEDIATE ACTION: Retire this sock puppet now. It's past its scheduled retirement."
    if risk_level == "critical":
        return "Consider retiring this sock puppet. Multiple critical risk factors detected."
    if risk_level == "high":
        return "Review this sock puppet's operational status. Address identified risks before continued use."
    if risk_level == "medium":
        return "Monitor this sock puppet more closely. Address warnings when possible."
    return "Sock puppet appears to be in good standing. Continue normal operations."
