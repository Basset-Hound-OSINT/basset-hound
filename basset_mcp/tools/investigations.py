"""
Investigation management tools for MCP.

Provides tools for managing investigations/cases in basset-hound projects.
This extends the project model with investigation-specific metadata including:
- Investigation status and phase tracking
- Subject/target management with role classification
- Task and milestone management
- Activity logging for audit compliance

Investigations are stored as enhanced project metadata in the `_investigation`
section, following the same pattern as sock puppets.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum

from .base import get_neo4j_handler, get_project_safe_name


class InvestigationStatus(str, Enum):
    """Investigation lifecycle statuses."""
    INTAKE = "intake"                    # Initial case creation
    PLANNING = "planning"                # Investigation planning
    ACTIVE = "active"                    # Under active investigation
    PENDING_INFO = "pending_info"        # Waiting for information
    PENDING_REVIEW = "pending_review"    # Awaiting supervisor review
    ON_HOLD = "on_hold"                  # Temporarily paused
    CLOSED_RESOLVED = "closed_resolved"  # Successfully completed
    CLOSED_UNFOUNDED = "closed_unfounded"  # Determined no basis
    CLOSED_REFERRED = "closed_referred"  # Referred to another entity
    REOPENED = "reopened"                # Previously closed, now active


class InvestigationPhase(str, Enum):
    """Investigation workflow phases (OSINT/digital investigation lifecycle)."""
    IDENTIFICATION = "identification"    # Define scope, identify sources
    ACQUISITION = "acquisition"          # Collect data/evidence
    AUTHENTICATION = "authentication"    # Verify authenticity
    ANALYSIS = "analysis"                # Process and analyze data
    PRESERVATION = "preservation"        # Secure and document
    VALIDATION = "validation"            # Cross-verify findings
    REPORTING = "reporting"              # Document findings
    CLOSURE = "closure"                  # Final disposition


class SubjectRole(str, Enum):
    """Role types for investigation subjects."""
    TARGET = "target"                    # Primary subject of investigation
    SUBJECT = "subject"                  # Person of interest
    SUSPECT = "suspect"                  # Suspected of wrongdoing
    WITNESS = "witness"                  # May have information
    VICTIM = "victim"                    # Harmed party
    INFORMANT = "informant"              # Providing information
    COMPLAINANT = "complainant"          # Filed complaint
    ASSOCIATE = "associate"              # Known connection
    HANDLER = "handler"                  # Managing undercover/informant
    UNDERCOVER = "undercover"            # Sock puppet identity


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def register_investigation_tools(mcp):
    """Register investigation management tools with the MCP server."""

    # =========================================================================
    # INVESTIGATION CRUD
    # =========================================================================

    @mcp.tool()
    def create_investigation(
        project_id: str,
        title: str,
        description: str = "",
        investigation_type: str = "osint",
        priority: str = "medium",
        lead_investigator_id: str = None,
        objectives: list = None,
        tags: list = None,
        confidentiality: str = "internal"
    ) -> dict:
        """
        Initialize a project as an investigation with full tracking metadata.

        Converts a standard basset-hound project into a tracked investigation
        with status, phases, subjects, tasks, and activity logging.

        Args:
            project_id: The project ID or safe_name to convert
            title: Investigation title/case name
            description: Investigation description and objectives
            investigation_type: Type of investigation (osint, fraud, missing_person, etc.)
            priority: Priority level (low, medium, high, critical)
            lead_investigator_id: Entity ID of lead investigator
            objectives: List of investigation objectives
            tags: Classification tags
            confidentiality: Classification level (public, internal, confidential, restricted)

        Returns:
            Investigation metadata
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate priority
        try:
            Priority(priority)
        except ValueError:
            valid = [p.value for p in Priority]
            return {"error": f"Invalid priority: {priority}. Valid: {valid}"}

        now = datetime.now().isoformat()
        investigation_id = str(uuid4())

        # Get existing project to update
        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        # Check if already initialized
        existing_inv = project.get("_investigation")
        if existing_inv:
            return {"error": "Project is already initialized as investigation", "investigation": existing_inv}

        investigation_data = {
            "id": investigation_id,
            "is_investigation": True,
            "title": title,
            "description": description,
            "investigation_type": investigation_type,
            "status": InvestigationStatus.INTAKE.value,
            "phase": InvestigationPhase.IDENTIFICATION.value,
            "priority": priority,
            "lead_investigator_id": lead_investigator_id,
            "objectives": objectives or [],
            "tags": tags or [],
            "confidentiality": confidentiality,

            # Lifecycle
            "created_at": now,
            "opened_at": now,
            "closed_at": None,
            "last_activity": now,

            # Collections
            "subjects": [],        # Investigation subjects with roles
            "tasks": [],           # Tasks/assignments
            "milestones": [],      # Phase milestones
            "activity_log": [],    # Audit trail

            # Statistics
            "entity_count": len(project.get("people", [])),
            "evidence_count": 0
        }

        # Log creation activity
        investigation_data["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "investigation_created",
            "description": f"Investigation '{title}' created",
            "user_id": lead_investigator_id,
            "details": {"investigation_type": investigation_type, "priority": priority}
        })

        # Store in project
        result = handler.update_project(safe_name, {"_investigation": investigation_data})

        if not result:
            return {"error": "Failed to create investigation"}

        return {
            "success": True,
            "project_id": project_id,
            "investigation_id": investigation_id,
            "investigation": investigation_data
        }

    @mcp.tool()
    def get_investigation(project_id: str) -> dict:
        """
        Get investigation details for a project.

        Args:
            project_id: The project ID or safe_name

        Returns:
            Investigation metadata and statistics
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Add computed stats
        investigation["entity_count"] = len(project.get("people", []))
        investigation["subject_count"] = len(investigation.get("subjects", []))
        investigation["task_count"] = len(investigation.get("tasks", []))
        investigation["milestone_count"] = len(investigation.get("milestones", []))
        investigation["pending_tasks"] = len([t for t in investigation.get("tasks", [])
                                               if t.get("status") == TaskStatus.PENDING.value])
        investigation["completed_tasks"] = len([t for t in investigation.get("tasks", [])
                                                 if t.get("status") == TaskStatus.COMPLETED.value])

        return {
            "project_id": project_id,
            "project_name": project.get("name"),
            "investigation": investigation
        }

    @mcp.tool()
    def update_investigation(
        project_id: str,
        title: str = None,
        description: str = None,
        priority: str = None,
        lead_investigator_id: str = None,
        objectives: list = None,
        tags: list = None,
        confidentiality: str = None
    ) -> dict:
        """
        Update investigation properties.

        Args:
            project_id: The project ID or safe_name
            title: New title (optional)
            description: New description (optional)
            priority: New priority (optional)
            lead_investigator_id: New lead investigator (optional)
            objectives: New objectives list (optional)
            tags: New tags list (optional)
            confidentiality: New confidentiality level (optional)

        Returns:
            Updated investigation metadata
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        now = datetime.now().isoformat()
        changes = []

        # Apply updates
        if title is not None:
            changes.append(f"title: {investigation.get('title')} -> {title}")
            investigation["title"] = title
        if description is not None:
            investigation["description"] = description
            changes.append("description updated")
        if priority is not None:
            try:
                Priority(priority)
            except ValueError:
                valid = [p.value for p in Priority]
                return {"error": f"Invalid priority: {priority}. Valid: {valid}"}
            changes.append(f"priority: {investigation.get('priority')} -> {priority}")
            investigation["priority"] = priority
        if lead_investigator_id is not None:
            changes.append(f"lead_investigator changed")
            investigation["lead_investigator_id"] = lead_investigator_id
        if objectives is not None:
            investigation["objectives"] = objectives
            changes.append("objectives updated")
        if tags is not None:
            investigation["tags"] = tags
            changes.append("tags updated")
        if confidentiality is not None:
            investigation["confidentiality"] = confidentiality
            changes.append(f"confidentiality: {investigation.get('confidentiality')} -> {confidentiality}")

        if not changes:
            return {"error": "No updates provided"}

        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "investigation_updated",
            "description": f"Investigation updated: {', '.join(changes)}",
            "details": {"changes": changes}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to update investigation"}

        return {
            "success": True,
            "project_id": project_id,
            "changes": changes,
            "investigation": investigation
        }

    # =========================================================================
    # STATUS AND PHASE MANAGEMENT
    # =========================================================================

    @mcp.tool()
    def set_investigation_status(
        project_id: str,
        status: str,
        notes: str = ""
    ) -> dict:
        """
        Update investigation status.

        Args:
            project_id: The project ID or safe_name
            status: New status (intake, planning, active, pending_info, pending_review,
                   on_hold, closed_resolved, closed_unfounded, closed_referred, reopened)
            notes: Notes explaining status change

        Returns:
            Updated status information
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate status
        try:
            InvestigationStatus(status)
        except ValueError:
            valid = [s.value for s in InvestigationStatus]
            return {"error": f"Invalid status: {status}. Valid: {valid}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        now = datetime.now().isoformat()
        old_status = investigation.get("status")

        investigation["status"] = status
        investigation["last_activity"] = now

        # Track closure
        if status.startswith("closed_"):
            investigation["closed_at"] = now

        # Track reopening
        if status == InvestigationStatus.REOPENED.value:
            investigation["closed_at"] = None

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "status_changed",
            "description": f"Status changed: {old_status} -> {status}",
            "details": {"old_status": old_status, "new_status": status, "notes": notes}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to update status"}

        return {
            "success": True,
            "project_id": project_id,
            "old_status": old_status,
            "new_status": status,
            "notes": notes
        }

    @mcp.tool()
    def advance_investigation_phase(
        project_id: str,
        phase: str,
        milestone_notes: str = ""
    ) -> dict:
        """
        Advance investigation to next phase.

        Args:
            project_id: The project ID or safe_name
            phase: New phase (identification, acquisition, authentication, analysis,
                  preservation, validation, reporting, closure)
            milestone_notes: Notes about phase completion

        Returns:
            Updated phase information
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate phase
        try:
            InvestigationPhase(phase)
        except ValueError:
            valid = [p.value for p in InvestigationPhase]
            return {"error": f"Invalid phase: {phase}. Valid: {valid}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        now = datetime.now().isoformat()
        old_phase = investigation.get("phase")

        investigation["phase"] = phase
        investigation["last_activity"] = now

        # Auto-create milestone for phase transition
        investigation["milestones"].append({
            "id": str(uuid4()),
            "phase": old_phase,
            "name": f"Phase '{old_phase}' completed",
            "description": milestone_notes,
            "completed_at": now,
            "status": "completed"
        })

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "phase_advanced",
            "description": f"Phase advanced: {old_phase} -> {phase}",
            "details": {"old_phase": old_phase, "new_phase": phase, "notes": milestone_notes}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to advance phase"}

        return {
            "success": True,
            "project_id": project_id,
            "old_phase": old_phase,
            "new_phase": phase,
            "milestone_created": True
        }

    @mcp.tool()
    def close_investigation(
        project_id: str,
        disposition: str,
        resolution_notes: str
    ) -> dict:
        """
        Close an investigation with final disposition.

        Args:
            project_id: The project ID or safe_name
            disposition: Final disposition (resolved, unfounded, referred)
            resolution_notes: Notes explaining resolution

        Returns:
            Closure confirmation
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Map disposition to status
        disposition_map = {
            "resolved": InvestigationStatus.CLOSED_RESOLVED.value,
            "unfounded": InvestigationStatus.CLOSED_UNFOUNDED.value,
            "referred": InvestigationStatus.CLOSED_REFERRED.value
        }

        if disposition not in disposition_map:
            return {"error": f"Invalid disposition: {disposition}. Valid: {list(disposition_map.keys())}"}

        now = datetime.now().isoformat()

        investigation["status"] = disposition_map[disposition]
        investigation["phase"] = InvestigationPhase.CLOSURE.value
        investigation["closed_at"] = now
        investigation["resolution_notes"] = resolution_notes
        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "investigation_closed",
            "description": f"Investigation closed: {disposition}",
            "details": {"disposition": disposition, "notes": resolution_notes}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to close investigation"}

        return {
            "success": True,
            "project_id": project_id,
            "status": disposition_map[disposition],
            "closed_at": now,
            "disposition": disposition
        }

    # =========================================================================
    # SUBJECT MANAGEMENT
    # =========================================================================

    @mcp.tool()
    def add_investigation_subject(
        project_id: str,
        entity_id: str,
        role: str,
        notes: str = "",
        priority: str = "medium"
    ) -> dict:
        """
        Add an entity as a subject of the investigation.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID to add as subject
            role: Subject role (target, subject, suspect, witness, victim,
                  informant, complainant, associate, handler, undercover)
            notes: Notes about subject's role
            priority: Subject priority (low, medium, high, critical)

        Returns:
            Subject addition confirmation
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Validate role
        try:
            SubjectRole(role)
        except ValueError:
            valid = [r.value for r in SubjectRole]
            return {"error": f"Invalid role: {role}. Valid: {valid}"}

        # Validate priority
        try:
            Priority(priority)
        except ValueError:
            valid = [p.value for p in Priority]
            return {"error": f"Invalid priority: {priority}. Valid: {valid}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Verify entity exists in project
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found in project: {entity_id}"}

        # Check if already a subject
        for subj in investigation.get("subjects", []):
            if subj.get("entity_id") == entity_id:
                return {"error": "Entity is already a subject in this investigation", "subject": subj}

        now = datetime.now().isoformat()

        subject = {
            "id": str(uuid4()),
            "entity_id": entity_id,
            "role": role,
            "priority": priority,
            "notes": notes,
            "added_at": now,
            "status": "active",
            "cleared_at": None
        }

        investigation["subjects"].append(subject)
        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "subject_added",
            "description": f"Entity {entity_id} added as {role}",
            "details": {"entity_id": entity_id, "role": role, "priority": priority}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to add subject"}

        return {
            "success": True,
            "project_id": project_id,
            "subject": subject
        }

    @mcp.tool()
    def update_subject_role(
        project_id: str,
        entity_id: str,
        role: str = None,
        priority: str = None,
        notes: str = None
    ) -> dict:
        """
        Update a subject's role or priority.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID of the subject
            role: New role (optional)
            priority: New priority (optional)
            notes: Updated notes (optional)

        Returns:
            Updated subject information
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if role:
            try:
                SubjectRole(role)
            except ValueError:
                valid = [r.value for r in SubjectRole]
                return {"error": f"Invalid role: {role}. Valid: {valid}"}

        if priority:
            try:
                Priority(priority)
            except ValueError:
                valid = [p.value for p in Priority]
                return {"error": f"Invalid priority: {priority}. Valid: {valid}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Find subject
        subject = None
        for subj in investigation.get("subjects", []):
            if subj.get("entity_id") == entity_id:
                subject = subj
                break

        if not subject:
            return {"error": f"Subject not found: {entity_id}"}

        now = datetime.now().isoformat()
        changes = []

        if role is not None:
            changes.append(f"role: {subject.get('role')} -> {role}")
            subject["role"] = role
        if priority is not None:
            changes.append(f"priority: {subject.get('priority')} -> {priority}")
            subject["priority"] = priority
        if notes is not None:
            subject["notes"] = notes
            changes.append("notes updated")

        if not changes:
            return {"error": "No updates provided"}

        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "subject_updated",
            "description": f"Subject {entity_id} updated: {', '.join(changes)}",
            "details": {"entity_id": entity_id, "changes": changes}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to update subject"}

        return {
            "success": True,
            "project_id": project_id,
            "subject": subject,
            "changes": changes
        }

    @mcp.tool()
    def clear_subject(
        project_id: str,
        entity_id: str,
        reason: str
    ) -> dict:
        """
        Clear a subject from the investigation (mark as not involved).

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity ID of the subject
            reason: Reason for clearing the subject

        Returns:
            Cleared subject information
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Find subject
        subject = None
        for subj in investigation.get("subjects", []):
            if subj.get("entity_id") == entity_id:
                subject = subj
                break

        if not subject:
            return {"error": f"Subject not found: {entity_id}"}

        now = datetime.now().isoformat()

        subject["status"] = "cleared"
        subject["cleared_at"] = now
        subject["cleared_reason"] = reason

        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "subject_cleared",
            "description": f"Subject {entity_id} cleared: {reason}",
            "details": {"entity_id": entity_id, "reason": reason}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to clear subject"}

        return {
            "success": True,
            "project_id": project_id,
            "subject": subject
        }

    @mcp.tool()
    def list_investigation_subjects(
        project_id: str,
        role_filter: str = None,
        status_filter: str = None
    ) -> dict:
        """
        List all subjects in an investigation.

        Args:
            project_id: The project ID or safe_name
            role_filter: Filter by role (optional)
            status_filter: Filter by status (active, cleared) (optional)

        Returns:
            List of subjects
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        subjects = investigation.get("subjects", [])

        # Apply filters
        if role_filter:
            subjects = [s for s in subjects if s.get("role") == role_filter]
        if status_filter:
            subjects = [s for s in subjects if s.get("status") == status_filter]

        return {
            "project_id": project_id,
            "count": len(subjects),
            "subjects": subjects
        }

    # =========================================================================
    # TASK MANAGEMENT
    # =========================================================================

    @mcp.tool()
    def create_investigation_task(
        project_id: str,
        title: str,
        description: str = "",
        task_type: str = "research",
        assigned_to: str = None,
        due_date: str = None,
        priority: str = "medium",
        related_entity_id: str = None
    ) -> dict:
        """
        Create a task for the investigation.

        Args:
            project_id: The project ID or safe_name
            title: Task title
            description: Task description
            task_type: Task type (research, interview, surveillance, document_review,
                       evidence_collection, analysis, reporting, other)
            assigned_to: Entity ID to assign task to (optional)
            due_date: Due date ISO string (optional)
            priority: Priority level (low, medium, high, critical)
            related_entity_id: Entity this task relates to (optional)

        Returns:
            Created task
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        try:
            Priority(priority)
        except ValueError:
            valid = [p.value for p in Priority]
            return {"error": f"Invalid priority: {priority}. Valid: {valid}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        now = datetime.now().isoformat()

        task = {
            "id": str(uuid4()),
            "title": title,
            "description": description,
            "task_type": task_type,
            "assigned_to": assigned_to,
            "due_date": due_date,
            "priority": priority,
            "status": TaskStatus.PENDING.value,
            "related_entity_id": related_entity_id,
            "created_at": now,
            "completed_at": None,
            "result": None
        }

        investigation["tasks"].append(task)
        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "task_created",
            "description": f"Task created: {title}",
            "details": {"task_id": task["id"], "assigned_to": assigned_to, "priority": priority}
        })

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to create task"}

        return {
            "success": True,
            "project_id": project_id,
            "task": task
        }

    @mcp.tool()
    def complete_investigation_task(
        project_id: str,
        task_id: str,
        result: str,
        notes: str = ""
    ) -> dict:
        """
        Mark an investigation task as completed.

        Args:
            project_id: The project ID or safe_name
            task_id: The task ID to complete
            result: Task result/findings
            notes: Additional notes

        Returns:
            Completed task
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        # Find task
        task = None
        for t in investigation.get("tasks", []):
            if t.get("id") == task_id:
                task = t
                break

        if not task:
            return {"error": f"Task not found: {task_id}"}

        now = datetime.now().isoformat()

        task["status"] = TaskStatus.COMPLETED.value
        task["completed_at"] = now
        task["result"] = result
        if notes:
            task["notes"] = notes

        investigation["last_activity"] = now

        # Log activity
        investigation["activity_log"].append({
            "id": str(uuid4()),
            "timestamp": now,
            "action": "task_completed",
            "description": f"Task completed: {task.get('title')}",
            "details": {"task_id": task_id, "result": result}
        })

        result_update = handler.update_project(safe_name, {"_investigation": investigation})

        if not result_update:
            return {"error": "Failed to complete task"}

        return {
            "success": True,
            "project_id": project_id,
            "task": task
        }

    @mcp.tool()
    def list_investigation_tasks(
        project_id: str,
        status_filter: str = None,
        assigned_to: str = None,
        priority_filter: str = None
    ) -> dict:
        """
        List tasks for an investigation.

        Args:
            project_id: The project ID or safe_name
            status_filter: Filter by status (pending, in_progress, completed, etc.)
            assigned_to: Filter by assignee entity ID
            priority_filter: Filter by priority

        Returns:
            List of tasks
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        tasks = investigation.get("tasks", [])

        # Apply filters
        if status_filter:
            tasks = [t for t in tasks if t.get("status") == status_filter]
        if assigned_to:
            tasks = [t for t in tasks if t.get("assigned_to") == assigned_to]
        if priority_filter:
            tasks = [t for t in tasks if t.get("priority") == priority_filter]

        return {
            "project_id": project_id,
            "count": len(tasks),
            "tasks": tasks
        }

    # =========================================================================
    # ACTIVITY LOG
    # =========================================================================

    @mcp.tool()
    def log_investigation_activity(
        project_id: str,
        action: str,
        description: str,
        related_entity_id: str = None,
        details: dict = None
    ) -> dict:
        """
        Log an activity for the investigation audit trail.

        Args:
            project_id: The project ID or safe_name
            action: Action type (e.g., evidence_collected, interview_conducted, etc.)
            description: Description of the activity
            related_entity_id: Entity this activity relates to (optional)
            details: Additional details dict (optional)

        Returns:
            Created activity log entry
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        now = datetime.now().isoformat()

        activity = {
            "id": str(uuid4()),
            "timestamp": now,
            "action": action,
            "description": description,
            "related_entity_id": related_entity_id,
            "details": details or {}
        }

        investigation["activity_log"].append(activity)
        investigation["last_activity"] = now

        result = handler.update_project(safe_name, {"_investigation": investigation})

        if not result:
            return {"error": "Failed to log activity"}

        return {
            "success": True,
            "project_id": project_id,
            "activity": activity
        }

    @mcp.tool()
    def get_investigation_activity_log(
        project_id: str,
        action_filter: str = None,
        limit: int = 100
    ) -> dict:
        """
        Get the investigation activity log for audit purposes.

        Args:
            project_id: The project ID or safe_name
            action_filter: Filter by action type (optional)
            limit: Maximum entries to return (default: 100)

        Returns:
            Activity log entries
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        project = handler.get_project(safe_name)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        investigation = project.get("_investigation")
        if not investigation:
            return {"error": "Project is not initialized as investigation"}

        activity_log = investigation.get("activity_log", [])

        # Apply filter
        if action_filter:
            activity_log = [a for a in activity_log if a.get("action") == action_filter]

        # Sort by timestamp descending and limit
        activity_log = sorted(activity_log, key=lambda x: x.get("timestamp", ""), reverse=True)
        activity_log = activity_log[:limit]

        return {
            "project_id": project_id,
            "count": len(activity_log),
            "activity_log": activity_log
        }

    # =========================================================================
    # INVESTIGATION SEARCH AND LISTING
    # =========================================================================

    @mcp.tool()
    def list_investigations(
        status_filter: str = None,
        phase_filter: str = None,
        priority_filter: str = None
    ) -> dict:
        """
        List all investigations across all projects.

        Args:
            status_filter: Filter by status (optional)
            phase_filter: Filter by phase (optional)
            priority_filter: Filter by priority (optional)

        Returns:
            List of investigations with summaries
        """
        handler = get_neo4j_handler()
        all_projects = handler.get_all_projects()

        investigations = []

        for project in all_projects:
            safe_name = project.get("safe_name")
            full_project = handler.get_project(safe_name)
            if not full_project:
                continue

            inv = full_project.get("_investigation")
            if not inv or not inv.get("is_investigation"):
                continue

            # Apply filters
            if status_filter and inv.get("status") != status_filter:
                continue
            if phase_filter and inv.get("phase") != phase_filter:
                continue
            if priority_filter and inv.get("priority") != priority_filter:
                continue

            investigations.append({
                "project_id": project.get("id"),
                "project_safe_name": safe_name,
                "investigation_id": inv.get("id"),
                "title": inv.get("title"),
                "status": inv.get("status"),
                "phase": inv.get("phase"),
                "priority": inv.get("priority"),
                "lead_investigator_id": inv.get("lead_investigator_id"),
                "subject_count": len(inv.get("subjects", [])),
                "task_count": len(inv.get("tasks", [])),
                "created_at": inv.get("created_at"),
                "last_activity": inv.get("last_activity")
            })

        return {
            "count": len(investigations),
            "investigations": investigations
        }
