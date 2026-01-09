# MCP Server Enhancement - Phase 40.6 Implementation

**Date:** 2026-01-08
**Phase:** 40.6 (Investigation Management)
**Status:** Completed

---

## Executive Summary

This document captures the implementation of Phase 40.6 MCP server enhancements, which adds comprehensive investigation lifecycle management tools. These tools enable basset-hound to function as a full-featured case management system for OSINT investigations, supporting law enforcement workflows and CJIS compliance requirements.

---

## 1. Investigation Management Overview

### Purpose

Investigation management tools extend basset-hound projects with structured case management capabilities, including:

- Investigation lifecycle status tracking (intake → closure)
- OSINT investigation phase management (8 phases)
- Subject/target role classification
- Task and milestone management
- Full audit trail for compliance

### Design Philosophy

Investigations are stored as enhanced project metadata in the `_investigation` section, following the same pattern as sock puppets. This allows:

- Any project to be "upgraded" to an investigation
- Standard entity/relationship operations to work unchanged
- Separation of investigation metadata from entity data
- Full backward compatibility with non-investigation projects

---

## 2. Tools Implemented (17 total)

| Tool | Description |
|------|-------------|
| `create_investigation` | Initialize project as investigation |
| `get_investigation` | Retrieve investigation details with stats |
| `update_investigation` | Update investigation properties |
| `set_investigation_status` | Change investigation status |
| `advance_investigation_phase` | Move to next phase with milestone |
| `close_investigation` | Close with final disposition |
| `add_investigation_subject` | Add entity as investigation subject |
| `update_subject_role` | Update subject's role/priority |
| `clear_subject` | Mark subject as not involved |
| `list_investigation_subjects` | List subjects with filtering |
| `create_investigation_task` | Create investigation task |
| `complete_investigation_task` | Mark task as completed |
| `list_investigation_tasks` | List tasks with filtering |
| `log_investigation_activity` | Log custom audit activity |
| `get_investigation_activity_log` | Get audit log with filtering |
| `list_investigations` | List all investigations across projects |

---

## 3. Data Models

### Investigation Status Lifecycle

```
INTAKE → PLANNING → ACTIVE → PENDING_INFO/PENDING_REVIEW → ON_HOLD
                            ↓
         CLOSED_RESOLVED / CLOSED_UNFOUNDED / CLOSED_REFERRED
                            ↓
                        REOPENED → ACTIVE
```

### Investigation Phases (OSINT Lifecycle)

| Phase | Description |
|-------|-------------|
| `identification` | Define scope, identify sources |
| `acquisition` | Collect data/evidence |
| `authentication` | Verify authenticity |
| `analysis` | Process and analyze data |
| `preservation` | Secure and document |
| `validation` | Cross-verify findings |
| `reporting` | Document findings |
| `closure` | Final disposition |

### Subject Roles

| Role | Description |
|------|-------------|
| `target` | Primary subject of investigation |
| `subject` | Person of interest |
| `suspect` | Suspected of wrongdoing |
| `witness` | May have information |
| `victim` | Harmed party |
| `informant` | Providing information |
| `complainant` | Filed complaint |
| `associate` | Known connection |
| `handler` | Managing undercover/informant |
| `undercover` | Sock puppet identity |

### Investigation Metadata Structure

```python
_investigation: {
    "id": "uuid",
    "is_investigation": True,
    "title": "Case Title",
    "description": "Investigation description",
    "investigation_type": "osint",  # fraud, missing_person, etc.
    "status": "active",
    "phase": "analysis",
    "priority": "high",  # low, medium, high, critical
    "lead_investigator_id": "entity-uuid",
    "objectives": ["Objective 1", "Objective 2"],
    "tags": ["fraud", "corporate"],
    "confidentiality": "confidential",  # public, internal, confidential, restricted

    # Lifecycle timestamps
    "created_at": "2026-01-08T10:00:00",
    "opened_at": "2026-01-08T10:00:00",
    "closed_at": None,
    "last_activity": "2026-01-08T15:30:00",

    # Collections
    "subjects": [...],      # Investigation subjects with roles
    "tasks": [...],         # Tasks/assignments
    "milestones": [...],    # Phase milestones
    "activity_log": [...],  # Audit trail

    # Statistics
    "entity_count": 25,
    "evidence_count": 150
}
```

---

## 4. Compliance Features

### CJIS Alignment

The investigation tools support Criminal Justice Information Services (CJIS) compliance requirements:

1. **Audit Trail**: Every action is logged with timestamp, action type, user, and details
2. **Chain of Custody**: Provenance tools (Phase 40) track data origin
3. **Access Control**: Confidentiality levels support need-to-know restrictions
4. **Case Disposition**: Formal closure with documented resolution

### Law Enforcement Workflow Support

```
1. Case Intake
   └── create_investigation() with priority, lead investigator

2. Subject Identification
   └── add_investigation_subject() with role classification

3. Evidence Collection (using provenance tools)
   └── record_provenance() for each data source

4. Investigation Tasks
   └── create_investigation_task() assigned to team members

5. Phase Advancement
   └── advance_investigation_phase() with milestone documentation

6. Case Closure
   └── close_investigation() with disposition (resolved/unfounded/referred)
```

---

## 5. Integration with Existing Tools

### Sock Puppet Integration

Investigation subjects can be linked to sock puppet handlers:

```python
# Add sock puppet as undercover subject
add_investigation_subject(
    project_id="case-001",
    entity_id="sock-puppet-001",
    role="undercover",
    notes="Assigned to infiltrate target's LinkedIn network"
)

# Record sock puppet activity
record_puppet_activity(
    project_id="case-001",
    puppet_id="sock-puppet-001",
    platform="linkedin",
    activity_type="connection_request"
)
```

### Provenance Integration

All evidence collection can be tracked with full provenance:

```python
# Record evidence source
record_provenance(
    project_id="case-001",
    entity_id="evidence-001",
    source_type="web_scrape",
    source_url="https://target-website.com/profile",
    acquisition_method="screenshot",
    collected_by="investigator-001"
)

# Log in investigation activity
log_investigation_activity(
    project_id="case-001",
    action="evidence_collected",
    description="Captured profile screenshot",
    related_entity_id="evidence-001"
)
```

---

## 6. Updated Tool Count

| Module | Tool Count | Status |
|--------|-----------|--------|
| schema | 6 | Existing |
| entities | 6 | Enhanced |
| relationships | 7 | Existing |
| search | 2 | Existing |
| projects | 3 | Existing |
| reports | 2 | Existing |
| analysis | 5 | Enhanced |
| auto_linking | 4 | Existing |
| orphans | 11 | Phase 40 |
| provenance | 8 | Phase 40 |
| sock_puppets | 15 | Phase 40.5 |
| verification | 12 | Phase 40.5 |
| **investigations** | **17** | **Phase 40.6** |
| **analysis** | **6** | Enhanced (+1 get_entity_type_schema) |
| **TOTAL** | **99** | +18 new tools |

---

## 7. Test Coverage

Created test suite: `tests/test_mcp_investigations.py`

**Test Classes:**
- `TestInvestigationEnums` - 5 tests for enum validation
- `TestInvestigationCRUD` - 5 tests for CRUD operations
- `TestStatusAndPhaseManagement` - 5 tests for lifecycle management
- `TestSubjectManagement` - 6 tests for subject operations
- `TestTaskManagement` - 3 tests for task operations
- `TestActivityLog` - 2 tests for audit logging
- `TestInvestigationListing` - 1 test for cross-project listing
- `TestIntegrationScenarios` - 1 test for full lifecycle
- `TestErrorHandling` - 2 tests for error cases

**Results:** 30 passed

**Entity Type Detection Tests (in test_mcp_enhanced_tools.py):**
- `TestEntityTypeDetection` - 8 tests for visualization schema

**Full MCP Test Suite:** 98 passed, 1 skipped

---

## 8. Files Changed

### New Files
- `basset_mcp/tools/investigations.py` - Investigation management (17 tools)
- `tests/test_mcp_investigations.py` - Test suite (30 tests)
- `docs/findings/MCP-PHASE40.6-2026-01-08.md` - This document

### Modified Files
- `basset_mcp/tools/__init__.py` - Register investigation module
- `basset_mcp/tools/analysis.py` - Added entity type detection and `get_entity_type_schema` tool
- `tests/test_mcp_enhanced_tools.py` - Added 8 entity type detection tests

---

## 9. Example Workflows

### Corporate Fraud Investigation

```python
# 1. Create investigation
await mcp_client.call("create_investigation", {
    "project_id": "proj-001",
    "title": "Acme Corp Fraud Investigation",
    "description": "Investigating suspected embezzlement by CFO",
    "investigation_type": "fraud",
    "priority": "critical",
    "lead_investigator_id": "inv-001"
})

# 2. Add suspect
await mcp_client.call("add_investigation_subject", {
    "project_id": "proj-001",
    "entity_id": "cfo-john-doe",
    "role": "suspect",
    "priority": "critical",
    "notes": "Primary target - CFO with signing authority"
})

# 3. Create task for financial review
await mcp_client.call("create_investigation_task", {
    "project_id": "proj-001",
    "title": "Review Q3 2025 financial statements",
    "task_type": "document_review",
    "assigned_to": "analyst-001",
    "priority": "high"
})

# 4. Advance to analysis phase
await mcp_client.call("advance_investigation_phase", {
    "project_id": "proj-001",
    "phase": "analysis",
    "milestone_notes": "Evidence collection complete - 500 documents reviewed"
})

# 5. Close investigation
await mcp_client.call("close_investigation", {
    "project_id": "proj-001",
    "disposition": "resolved",
    "resolution_notes": "Evidence confirmed embezzlement. Referred to legal."
})
```

### Missing Person Investigation

```python
# 1. Create investigation
await mcp_client.call("create_investigation", {
    "project_id": "missing-jane",
    "title": "Jane Doe Missing Person",
    "investigation_type": "missing_person",
    "priority": "critical"
})

# 2. Add subjects with different roles
await mcp_client.call("add_investigation_subject", {
    "project_id": "missing-jane",
    "entity_id": "jane-doe",
    "role": "victim",
    "notes": "Missing since 2026-01-01"
})

await mcp_client.call("add_investigation_subject", {
    "project_id": "missing-jane",
    "entity_id": "john-smith",
    "role": "witness",
    "notes": "Last person to see victim"
})

# 3. Deploy sock puppet for social media monitoring
await mcp_client.call("create_sock_puppet", {
    "project_id": "missing-jane",
    "alias_name": "Sarah Miller",
    "purpose": "passive_surveillance",
    "handler_id": "inv-001"
})

# 4. Clear witness after interview
await mcp_client.call("clear_subject", {
    "project_id": "missing-jane",
    "entity_id": "john-smith",
    "reason": "Verified alibi - not involved"
})
```

---

## 10. Future Considerations

### Phase 41: Browser Integration APIs

The investigation tools are designed to integrate with browser extensions:

- Auto-capture evidence with provenance tracking
- Link captured data to investigations
- Real-time sock puppet activity logging

### Investigation Templates

Future enhancement could include:

- Pre-defined investigation types with standard phases
- Template-based task creation
- Automated milestone triggers

### Reporting Integration

Investigation data can feed into reports:

- Timeline generation from activity log
- Subject network visualization
- Evidence chain documentation

---

## 11. Migration Notes

### For Existing Projects

Existing projects can be upgraded to investigations:

```python
# Upgrade existing project
create_investigation(
    project_id="existing-project",
    title="Case Name",
    investigation_type="osint"
)
```

### Backward Compatibility

- Non-investigation projects continue to work unchanged
- All entity/relationship operations remain compatible
- Investigation metadata is isolated in `_investigation` section
