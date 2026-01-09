"""
Tests for MCP investigation management tools.

This test suite covers:
- Investigation CRUD operations
- Status and phase management
- Subject management
- Task management
- Activity logging
- Investigation listing and filtering
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestInvestigationEnums:
    """Test investigation enum values."""

    def test_investigation_status_values(self):
        """Test all investigation status values are valid."""
        from basset_mcp.tools.investigations import InvestigationStatus

        expected = [
            "intake", "planning", "active", "pending_info", "pending_review",
            "on_hold", "closed_resolved", "closed_unfounded", "closed_referred",
            "reopened"
        ]
        actual = [s.value for s in InvestigationStatus]
        assert set(expected) == set(actual)

    def test_investigation_phase_values(self):
        """Test all investigation phase values follow OSINT lifecycle."""
        from basset_mcp.tools.investigations import InvestigationPhase

        expected = [
            "identification", "acquisition", "authentication", "analysis",
            "preservation", "validation", "reporting", "closure"
        ]
        actual = [p.value for p in InvestigationPhase]
        assert set(expected) == set(actual)

    def test_subject_role_values(self):
        """Test all subject role values are valid."""
        from basset_mcp.tools.investigations import SubjectRole

        expected = [
            "target", "subject", "suspect", "witness", "victim",
            "informant", "complainant", "associate", "handler", "undercover"
        ]
        actual = [r.value for r in SubjectRole]
        assert set(expected) == set(actual)

    def test_task_status_values(self):
        """Test all task status values are valid."""
        from basset_mcp.tools.investigations import TaskStatus

        expected = ["pending", "in_progress", "blocked", "completed", "cancelled"]
        actual = [s.value for s in TaskStatus]
        assert set(expected) == set(actual)

    def test_priority_values(self):
        """Test all priority values are valid."""
        from basset_mcp.tools.investigations import Priority

        expected = ["low", "medium", "high", "critical"]
        actual = [p.value for p in Priority]
        assert set(expected) == set(actual)


class TestInvestigationCRUD:
    """Test investigation create, read, update operations."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock Neo4j handler."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": []
        }
        handler.update_project.return_value = True
        return handler

    @pytest.fixture
    def mock_tools(self, mock_handler):
        """Create mock MCP and register tools."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                register_investigation_tools(mcp)

        return tools, mock_handler

    def test_create_investigation(self, mock_tools):
        """Test creating a new investigation."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["create_investigation"](
                    project_id="proj-001",
                    title="Test Investigation",
                    description="A test investigation",
                    investigation_type="osint",
                    priority="high"
                )

        assert result["success"] is True
        assert result["project_id"] == "proj-001"
        assert "investigation_id" in result
        assert result["investigation"]["title"] == "Test Investigation"
        assert result["investigation"]["status"] == "intake"
        assert result["investigation"]["phase"] == "identification"
        assert result["investigation"]["priority"] == "high"

    def test_create_investigation_invalid_priority(self, mock_tools):
        """Test creating investigation with invalid priority fails."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["create_investigation"](
                    project_id="proj-001",
                    title="Test Investigation",
                    priority="invalid"
                )

        assert "error" in result
        assert "Invalid priority" in result["error"]

    def test_create_investigation_already_exists(self, mock_tools):
        """Test creating investigation on already-initialized project fails."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {"is_investigation": True}
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["create_investigation"](
                    project_id="proj-001",
                    title="Test Investigation"
                )

        assert "error" in result
        assert "already initialized" in result["error"]

    def test_get_investigation(self, mock_tools):
        """Test getting investigation details."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": ["entity-1", "entity-2"],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "title": "Test Investigation",
                "status": "active",
                "phase": "analysis",
                "subjects": [{"id": "s1"}],
                "tasks": [{"id": "t1", "status": "pending"}, {"id": "t2", "status": "completed"}],
                "milestones": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["get_investigation"](project_id="proj-001")

        assert result["project_id"] == "proj-001"
        assert result["investigation"]["title"] == "Test Investigation"
        assert result["investigation"]["entity_count"] == 2
        assert result["investigation"]["subject_count"] == 1
        assert result["investigation"]["task_count"] == 2
        assert result["investigation"]["pending_tasks"] == 1
        assert result["investigation"]["completed_tasks"] == 1

    def test_update_investigation(self, mock_tools):
        """Test updating investigation properties."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "title": "Old Title",
                "priority": "medium",
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["update_investigation"](
                    project_id="proj-001",
                    title="New Title",
                    priority="critical"
                )

        assert result["success"] is True
        assert "title" in str(result["changes"])
        assert "priority" in str(result["changes"])


class TestStatusAndPhaseManagement:
    """Test investigation status and phase management."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock Neo4j handler with active investigation."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "status": "active",
                "phase": "analysis",
                "activity_log": [],
                "milestones": []
            }
        }
        handler.update_project.return_value = True
        return handler

    @pytest.fixture
    def mock_tools(self, mock_handler):
        """Create mock MCP and register tools."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                register_investigation_tools(mcp)

        return tools, mock_handler

    def test_set_investigation_status(self, mock_tools):
        """Test changing investigation status."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["set_investigation_status"](
                    project_id="proj-001",
                    status="pending_review",
                    notes="Awaiting supervisor approval"
                )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "pending_review"

    def test_set_investigation_status_invalid(self, mock_tools):
        """Test setting invalid status fails."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["set_investigation_status"](
                    project_id="proj-001",
                    status="invalid_status"
                )

        assert "error" in result
        assert "Invalid status" in result["error"]

    def test_advance_investigation_phase(self, mock_tools):
        """Test advancing investigation phase creates milestone."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["advance_investigation_phase"](
                    project_id="proj-001",
                    phase="validation",
                    milestone_notes="Analysis phase completed with key findings"
                )

        assert result["success"] is True
        assert result["old_phase"] == "analysis"
        assert result["new_phase"] == "validation"
        assert result["milestone_created"] is True

    def test_close_investigation(self, mock_tools):
        """Test closing investigation with disposition."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["close_investigation"](
                    project_id="proj-001",
                    disposition="resolved",
                    resolution_notes="Target identified and case completed successfully"
                )

        assert result["success"] is True
        assert result["status"] == "closed_resolved"
        assert result["disposition"] == "resolved"
        assert "closed_at" in result

    def test_close_investigation_invalid_disposition(self, mock_tools):
        """Test closing with invalid disposition fails."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["close_investigation"](
                    project_id="proj-001",
                    disposition="invalid",
                    resolution_notes="Test"
                )

        assert "error" in result
        assert "Invalid disposition" in result["error"]


class TestSubjectManagement:
    """Test investigation subject management."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock Neo4j handler with investigation and entity."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "subjects": [],
                "activity_log": []
            }
        }
        handler.get_person.return_value = {"id": "entity-001", "profile": {"name": "John Doe"}}
        handler.update_project.return_value = True
        return handler

    @pytest.fixture
    def mock_tools(self, mock_handler):
        """Create mock MCP and register tools."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                register_investigation_tools(mcp)

        return tools, mock_handler

    def test_add_investigation_subject(self, mock_tools):
        """Test adding a subject to investigation."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["add_investigation_subject"](
                    project_id="proj-001",
                    entity_id="entity-001",
                    role="target",
                    notes="Primary target of investigation",
                    priority="high"
                )

        assert result["success"] is True
        assert result["subject"]["entity_id"] == "entity-001"
        assert result["subject"]["role"] == "target"
        assert result["subject"]["priority"] == "high"
        assert result["subject"]["status"] == "active"

    def test_add_investigation_subject_invalid_role(self, mock_tools):
        """Test adding subject with invalid role fails."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["add_investigation_subject"](
                    project_id="proj-001",
                    entity_id="entity-001",
                    role="invalid_role"
                )

        assert "error" in result
        assert "Invalid role" in result["error"]

    def test_add_investigation_subject_entity_not_found(self, mock_tools):
        """Test adding non-existent entity fails."""
        tools, handler = mock_tools
        handler.get_person.return_value = None

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["add_investigation_subject"](
                    project_id="proj-001",
                    entity_id="nonexistent",
                    role="target"
                )

        assert "error" in result
        assert "Entity not found" in result["error"]

    def test_update_subject_role(self, mock_tools):
        """Test updating subject role."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "subjects": [
                    {"entity_id": "entity-001", "role": "subject", "priority": "medium"}
                ],
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["update_subject_role"](
                    project_id="proj-001",
                    entity_id="entity-001",
                    role="suspect",
                    priority="critical"
                )

        assert result["success"] is True
        assert result["subject"]["role"] == "suspect"
        assert result["subject"]["priority"] == "critical"

    def test_clear_subject(self, mock_tools):
        """Test clearing a subject from investigation."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "subjects": [
                    {"entity_id": "entity-001", "role": "suspect", "status": "active"}
                ],
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["clear_subject"](
                    project_id="proj-001",
                    entity_id="entity-001",
                    reason="Alibi verified, not involved"
                )

        assert result["success"] is True
        assert result["subject"]["status"] == "cleared"
        assert result["subject"]["cleared_reason"] == "Alibi verified, not involved"

    def test_list_investigation_subjects(self, mock_tools):
        """Test listing investigation subjects with filtering."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "subjects": [
                    {"entity_id": "e1", "role": "target", "status": "active"},
                    {"entity_id": "e2", "role": "witness", "status": "active"},
                    {"entity_id": "e3", "role": "suspect", "status": "cleared"}
                ],
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                # All subjects
                result = tools["list_investigation_subjects"](project_id="proj-001")
                assert result["count"] == 3

                # Filter by role
                result = tools["list_investigation_subjects"](
                    project_id="proj-001",
                    role_filter="target"
                )
                assert result["count"] == 1

                # Filter by status
                result = tools["list_investigation_subjects"](
                    project_id="proj-001",
                    status_filter="active"
                )
                assert result["count"] == 2


class TestTaskManagement:
    """Test investigation task management."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock Neo4j handler with investigation."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "tasks": [],
                "activity_log": []
            }
        }
        handler.update_project.return_value = True
        return handler

    @pytest.fixture
    def mock_tools(self, mock_handler):
        """Create mock MCP and register tools."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                register_investigation_tools(mcp)

        return tools, mock_handler

    def test_create_investigation_task(self, mock_tools):
        """Test creating an investigation task."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["create_investigation_task"](
                    project_id="proj-001",
                    title="Research target's social media",
                    description="Identify all social media accounts",
                    task_type="research",
                    priority="high",
                    assigned_to="investigator-001"
                )

        assert result["success"] is True
        assert result["task"]["title"] == "Research target's social media"
        assert result["task"]["status"] == "pending"
        assert result["task"]["priority"] == "high"
        assert result["task"]["assigned_to"] == "investigator-001"

    def test_complete_investigation_task(self, mock_tools):
        """Test completing an investigation task."""
        tools, handler = mock_tools

        task_id = str(uuid4())
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "tasks": [
                    {"id": task_id, "title": "Research task", "status": "pending"}
                ],
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["complete_investigation_task"](
                    project_id="proj-001",
                    task_id=task_id,
                    result="Found 5 social media accounts linked to target",
                    notes="LinkedIn, Twitter, Instagram, Facebook, TikTok"
                )

        assert result["success"] is True
        assert result["task"]["status"] == "completed"
        assert result["task"]["result"] == "Found 5 social media accounts linked to target"

    def test_list_investigation_tasks(self, mock_tools):
        """Test listing investigation tasks with filters."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "tasks": [
                    {"id": "t1", "status": "pending", "priority": "high", "assigned_to": "inv-1"},
                    {"id": "t2", "status": "completed", "priority": "medium", "assigned_to": "inv-1"},
                    {"id": "t3", "status": "pending", "priority": "high", "assigned_to": "inv-2"}
                ],
                "activity_log": []
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                # All tasks
                result = tools["list_investigation_tasks"](project_id="proj-001")
                assert result["count"] == 3

                # Filter by status
                result = tools["list_investigation_tasks"](
                    project_id="proj-001",
                    status_filter="pending"
                )
                assert result["count"] == 2

                # Filter by assignee
                result = tools["list_investigation_tasks"](
                    project_id="proj-001",
                    assigned_to="inv-1"
                )
                assert result["count"] == 2

                # Filter by priority
                result = tools["list_investigation_tasks"](
                    project_id="proj-001",
                    priority_filter="high"
                )
                assert result["count"] == 2


class TestActivityLog:
    """Test investigation activity logging."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock Neo4j handler with investigation."""
        handler = MagicMock()
        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "activity_log": []
            }
        }
        handler.update_project.return_value = True
        return handler

    @pytest.fixture
    def mock_tools(self, mock_handler):
        """Create mock MCP and register tools."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                register_investigation_tools(mcp)

        return tools, mock_handler

    def test_log_investigation_activity(self, mock_tools):
        """Test logging custom activity."""
        tools, handler = mock_tools

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                result = tools["log_investigation_activity"](
                    project_id="proj-001",
                    action="evidence_collected",
                    description="Collected social media screenshots",
                    related_entity_id="entity-001",
                    details={"platform": "twitter", "screenshot_count": 15}
                )

        assert result["success"] is True
        assert result["activity"]["action"] == "evidence_collected"
        assert result["activity"]["related_entity_id"] == "entity-001"
        assert result["activity"]["details"]["platform"] == "twitter"

    def test_get_investigation_activity_log(self, mock_tools):
        """Test retrieving activity log with filtering."""
        tools, handler = mock_tools

        handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Test Project",
            "safe_name": "test-project",
            "people": [],
            "_investigation": {
                "id": "inv-001",
                "is_investigation": True,
                "activity_log": [
                    {"id": "a1", "action": "evidence_collected", "timestamp": "2026-01-08T10:00:00"},
                    {"id": "a2", "action": "subject_added", "timestamp": "2026-01-08T11:00:00"},
                    {"id": "a3", "action": "evidence_collected", "timestamp": "2026-01-08T12:00:00"}
                ]
            }
        }

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="test-project"):
                # All activities
                result = tools["get_investigation_activity_log"](project_id="proj-001")
                assert result["count"] == 3
                # Should be sorted by timestamp descending
                assert result["activity_log"][0]["id"] == "a3"

                # Filter by action
                result = tools["get_investigation_activity_log"](
                    project_id="proj-001",
                    action_filter="evidence_collected"
                )
                assert result["count"] == 2


class TestInvestigationListing:
    """Test listing investigations across projects."""

    def test_list_investigations(self):
        """Test listing all investigations with filtering."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mock_handler = MagicMock()
        mock_handler.get_all_projects.return_value = [
            {"id": "p1", "safe_name": "project-1"},
            {"id": "p2", "safe_name": "project-2"},
            {"id": "p3", "safe_name": "project-3"}
        ]

        # Mock get_project to return different investigations
        def mock_get_project(safe_name):
            projects = {
                "project-1": {
                    "id": "p1",
                    "safe_name": "project-1",
                    "_investigation": {
                        "id": "inv-1",
                        "is_investigation": True,
                        "title": "Investigation 1",
                        "status": "active",
                        "phase": "analysis",
                        "priority": "high",
                        "subjects": [],
                        "tasks": []
                    }
                },
                "project-2": {
                    "id": "p2",
                    "safe_name": "project-2",
                    "_investigation": {
                        "id": "inv-2",
                        "is_investigation": True,
                        "title": "Investigation 2",
                        "status": "closed_resolved",
                        "phase": "closure",
                        "priority": "medium",
                        "subjects": [{"id": "s1"}],
                        "tasks": []
                    }
                },
                "project-3": {
                    "id": "p3",
                    "safe_name": "project-3"
                    # Not an investigation
                }
            }
            return projects.get(safe_name)

        mock_handler.get_project.side_effect = mock_get_project

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value=None):
                register_investigation_tools(mcp)

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            # List all investigations
            result = tools["list_investigations"]()
            assert result["count"] == 2

            # Filter by status
            result = tools["list_investigations"](status_filter="active")
            assert result["count"] == 1
            assert result["investigations"][0]["title"] == "Investigation 1"

            # Filter by priority
            result = tools["list_investigations"](priority_filter="high")
            assert result["count"] == 1


class TestIntegrationScenarios:
    """Test complete investigation workflows."""

    def test_full_investigation_lifecycle(self):
        """Test creating and managing a complete investigation."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mock_handler = MagicMock()
        project_data = {
            "id": "proj-001",
            "name": "Fraud Investigation",
            "safe_name": "fraud-investigation",
            "people": []
        }

        mock_handler.get_project.return_value = project_data.copy()
        mock_handler.get_person.return_value = {"id": "entity-001", "profile": {"name": "John Doe"}}
        mock_handler.update_project.return_value = True

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="fraud-investigation"):
                register_investigation_tools(mcp)

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="fraud-investigation"):
                # 1. Create investigation
                result = tools["create_investigation"](
                    project_id="proj-001",
                    title="Corporate Fraud Investigation",
                    description="Investigating suspected embezzlement",
                    investigation_type="fraud",
                    priority="critical"
                )
                assert result["success"] is True
                investigation_data = result["investigation"]

                # Update mock to include investigation
                project_data["_investigation"] = investigation_data
                mock_handler.get_project.return_value = project_data

                # 2. Set status to active
                result = tools["set_investigation_status"](
                    project_id="proj-001",
                    status="active",
                    notes="Investigation approved by supervisor"
                )
                assert result["success"] is True

                # 3. Add subject
                result = tools["add_investigation_subject"](
                    project_id="proj-001",
                    entity_id="entity-001",
                    role="suspect",
                    notes="Primary suspect - CFO",
                    priority="critical"
                )
                assert result["success"] is True

                # 4. Create task
                result = tools["create_investigation_task"](
                    project_id="proj-001",
                    title="Review financial records",
                    task_type="document_review",
                    priority="high"
                )
                assert result["success"] is True

                # 5. Log activity
                result = tools["log_investigation_activity"](
                    project_id="proj-001",
                    action="evidence_collected",
                    description="Obtained bank statements"
                )
                assert result["success"] is True

                # 6. Advance phase
                result = tools["advance_investigation_phase"](
                    project_id="proj-001",
                    phase="analysis",
                    milestone_notes="Evidence collection complete"
                )
                assert result["success"] is True


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_operations_on_non_investigation_project(self):
        """Test that operations fail gracefully on non-investigation projects."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mock_handler = MagicMock()
        mock_handler.get_project.return_value = {
            "id": "proj-001",
            "name": "Regular Project",
            "safe_name": "regular-project",
            "people": []
            # No _investigation field
        }

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="regular-project"):
                register_investigation_tools(mcp)

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value="regular-project"):
                # Try to get investigation
                result = tools["get_investigation"](project_id="proj-001")
                assert "error" in result
                assert "not initialized" in result["error"]

                # Try to set status
                result = tools["set_investigation_status"](
                    project_id="proj-001",
                    status="active"
                )
                assert "error" in result

                # Try to add subject
                result = tools["add_investigation_subject"](
                    project_id="proj-001",
                    entity_id="e1",
                    role="target"
                )
                assert "error" in result

    def test_project_not_found(self):
        """Test operations on non-existent project."""
        from basset_mcp.tools.investigations import register_investigation_tools

        mock_handler = MagicMock()
        mock_handler.get_project.return_value = None

        mcp = MagicMock()
        tools = {}

        def tool_decorator():
            def decorator(func):
                tools[func.__name__] = func
                return func
            return decorator

        mcp.tool = tool_decorator

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value=None):
                register_investigation_tools(mcp)

        with patch('basset_mcp.tools.investigations.get_neo4j_handler', return_value=mock_handler):
            with patch('basset_mcp.tools.investigations.get_project_safe_name', return_value=None):
                result = tools["create_investigation"](
                    project_id="nonexistent",
                    title="Test"
                )
                assert "error" in result
                assert "not found" in result["error"]
