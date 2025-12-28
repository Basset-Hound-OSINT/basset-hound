"""
Tests for the Report Storage Service

Comprehensive test coverage for:
- ReportFormat enum
- ReportVersion and StoredReport models
- ReportStorageService class methods
- Version management
- Version diffing
- Content deduplication
- Cleanup functionality
- Import/export
- Router endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from api.services.report_storage import (
    ReportFormat,
    ReportVersion,
    StoredReport,
    ReportStorageService,
    ReportNotFoundError,
    VersionNotFoundError,
    DuplicateContentError,
    get_report_storage_service,
    set_report_storage_service,
)


# ==================== ReportFormat Tests ====================


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_format_values(self):
        """Test that all expected formats exist."""
        assert ReportFormat.PDF == "pdf"
        assert ReportFormat.HTML == "html"
        assert ReportFormat.MARKDOWN == "markdown"
        assert ReportFormat.JSON == "json"
        assert ReportFormat.TEXT == "text"

    def test_format_is_string_enum(self):
        """Test that ReportFormat is a string enum."""
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.MARKDOWN.value == "markdown"

    def test_format_from_string(self):
        """Test creating format from string."""
        assert ReportFormat("pdf") == ReportFormat.PDF
        assert ReportFormat("html") == ReportFormat.HTML
        assert ReportFormat("markdown") == ReportFormat.MARKDOWN
        assert ReportFormat("json") == ReportFormat.JSON
        assert ReportFormat("text") == ReportFormat.TEXT

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            ReportFormat("invalid")

    def test_all_formats_enumerable(self):
        """Test that all formats can be enumerated."""
        formats = list(ReportFormat)
        assert len(formats) == 5


# ==================== ReportVersion Tests ====================


class TestReportVersion:
    """Tests for ReportVersion model."""

    def test_version_creation_minimal(self):
        """Test creating a version with minimal fields."""
        version = ReportVersion(
            report_id="report-1",
            version_number=1,
            content="<h1>Report</h1>",
        )

        assert version.report_id == "report-1"
        assert version.version_number == 1
        assert version.content == "<h1>Report</h1>"
        assert version.format == ReportFormat.HTML
        assert version.version_id is not None
        assert version.template_id is None
        assert version.context_hash == ""

    def test_version_creation_full(self):
        """Test creating a version with all fields."""
        version = ReportVersion(
            version_id="v-123",
            report_id="report-2",
            version_number=3,
            content="# Markdown Report",
            format=ReportFormat.MARKDOWN,
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            template_id="template-1",
            context_hash="abc123",
        )

        assert version.version_id == "v-123"
        assert version.report_id == "report-2"
        assert version.version_number == 3
        assert version.format == ReportFormat.MARKDOWN
        assert version.template_id == "template-1"
        assert version.context_hash == "abc123"

    def test_version_to_dict(self):
        """Test converting version to dictionary."""
        version = ReportVersion(
            version_id="v-456",
            report_id="report-3",
            version_number=2,
            content="Test content",
            format=ReportFormat.TEXT,
        )

        data = version.to_dict()

        assert data["version_id"] == "v-456"
        assert data["report_id"] == "report-3"
        assert data["version_number"] == 2
        assert data["content"] == "Test content"
        assert data["format"] == "text"
        assert "generated_at" in data

    def test_version_from_dict(self):
        """Test creating version from dictionary."""
        data = {
            "version_id": "v-789",
            "report_id": "report-4",
            "version_number": 5,
            "content": "JSON content",
            "format": "json",
            "generated_at": "2024-01-01T00:00:00",
            "template_id": "t-1",
            "context_hash": "xyz789",
        }

        version = ReportVersion.from_dict(data)

        assert version.version_id == "v-789"
        assert version.report_id == "report-4"
        assert version.version_number == 5
        assert version.format == ReportFormat.JSON
        assert version.template_id == "t-1"
        assert version.context_hash == "xyz789"

    def test_version_from_dict_defaults(self):
        """Test creating version from dict with missing fields."""
        data = {
            "report_id": "report-5",
            "version_number": 1,
            "content": "Minimal",
        }

        version = ReportVersion.from_dict(data)

        assert version.report_id == "report-5"
        assert version.content == "Minimal"
        assert version.format == ReportFormat.HTML
        assert version.template_id is None

    def test_version_number_must_be_positive(self):
        """Test that version number must be at least 1."""
        with pytest.raises(ValueError):
            ReportVersion(
                report_id="report",
                version_number=0,
                content="test",
            )


# ==================== StoredReport Tests ====================


class TestStoredReport:
    """Tests for StoredReport model."""

    def test_report_creation_minimal(self):
        """Test creating a report with minimal fields."""
        report = StoredReport(
            name="Test Report",
            project_id="project-1",
        )

        assert report.name == "Test Report"
        assert report.project_id == "project-1"
        assert report.report_id is not None
        assert report.entity_id is None
        assert report.versions == []
        assert report.current_version == 0

    def test_report_creation_full(self):
        """Test creating a report with all fields."""
        version = ReportVersion(
            report_id="r-1",
            version_number=1,
            content="Content",
        )

        report = StoredReport(
            report_id="r-1",
            name="Full Report",
            project_id="project-2",
            entity_id="entity-3",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
            versions=[version],
            current_version=1,
        )

        assert report.report_id == "r-1"
        assert report.name == "Full Report"
        assert report.entity_id == "entity-3"
        assert len(report.versions) == 1
        assert report.current_version == 1

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = StoredReport(
            report_id="r-2",
            name="Dict Report",
            project_id="p-1",
        )

        data = report.to_dict()

        assert data["report_id"] == "r-2"
        assert data["name"] == "Dict Report"
        assert data["project_id"] == "p-1"
        assert "created_at" in data
        assert "updated_at" in data
        assert data["versions"] == []

    def test_report_from_dict(self):
        """Test creating report from dictionary."""
        data = {
            "report_id": "r-3",
            "name": "From Dict",
            "project_id": "p-2",
            "entity_id": "e-1",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "versions": [
                {
                    "version_id": "v-1",
                    "report_id": "r-3",
                    "version_number": 1,
                    "content": "Test",
                    "format": "html",
                }
            ],
            "current_version": 1,
        }

        report = StoredReport.from_dict(data)

        assert report.report_id == "r-3"
        assert report.name == "From Dict"
        assert report.entity_id == "e-1"
        assert len(report.versions) == 1
        assert report.current_version == 1

    def test_report_get_version(self):
        """Test getting a specific version."""
        v1 = ReportVersion(report_id="r-1", version_number=1, content="V1")
        v2 = ReportVersion(report_id="r-1", version_number=2, content="V2")

        report = StoredReport(
            name="Test",
            project_id="p-1",
            versions=[v1, v2],
            current_version=2,
        )

        assert report.get_version(1).content == "V1"
        assert report.get_version(2).content == "V2"
        assert report.get_version(3) is None

    def test_report_get_current_version_content(self):
        """Test getting current version."""
        v1 = ReportVersion(report_id="r-1", version_number=1, content="V1")
        v2 = ReportVersion(report_id="r-1", version_number=2, content="V2")

        report = StoredReport(
            name="Test",
            project_id="p-1",
            versions=[v1, v2],
            current_version=2,
        )

        assert report.get_current_version_content().content == "V2"

    def test_report_get_version_count(self):
        """Test getting version count."""
        v1 = ReportVersion(report_id="r-1", version_number=1, content="V1")
        v2 = ReportVersion(report_id="r-1", version_number=2, content="V2")

        report = StoredReport(
            name="Test",
            project_id="p-1",
            versions=[v1, v2],
        )

        assert report.get_version_count() == 2


# ==================== ReportStorageService CRUD Tests ====================


class TestReportStorageServiceCRUD:
    """Tests for ReportStorageService CRUD operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh ReportStorageService for each test."""
        return ReportStorageService()

    def test_service_initialization(self, service):
        """Test service initializes empty."""
        assert service.get_report_count() == 0
        assert service.get_total_version_count() == 0

    def test_store_new_report(self, service):
        """Test storing a new report."""
        report = service.store_report(
            name="New Report",
            content="<h1>Hello</h1>",
            format=ReportFormat.HTML,
            project_id="project-1",
        )

        assert report.report_id is not None
        assert report.name == "New Report"
        assert report.project_id == "project-1"
        assert report.current_version == 1
        assert len(report.versions) == 1
        assert report.versions[0].content == "<h1>Hello</h1>"

    def test_store_report_with_entity_id(self, service):
        """Test storing report with entity ID."""
        report = service.store_report(
            name="Entity Report",
            content="Content",
            format=ReportFormat.TEXT,
            project_id="p-1",
            entity_id="e-1",
        )

        assert report.entity_id == "e-1"

    def test_store_report_with_template_id(self, service):
        """Test storing report with template ID."""
        report = service.store_report(
            name="Templated Report",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            template_id="t-1",
        )

        assert report.versions[0].template_id == "t-1"

    def test_store_report_with_context(self, service):
        """Test storing report with context hash."""
        report = service.store_report(
            name="Context Report",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            context={"key": "value"},
        )

        assert report.versions[0].context_hash != ""

    def test_store_report_with_custom_id(self, service):
        """Test storing report with custom ID."""
        report = service.store_report(
            name="Custom ID",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id="custom-123",
        )

        assert report.report_id == "custom-123"

    def test_store_report_adds_version(self, service):
        """Test storing to existing report adds version."""
        report1 = service.store_report(
            name="Report",
            content="V1 Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        report2 = service.store_report(
            name="Report Updated",
            content="V2 Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id=report1.report_id,
        )

        assert report2.report_id == report1.report_id
        assert report2.current_version == 2
        assert len(report2.versions) == 2
        assert report2.name == "Report Updated"

    def test_store_report_duplicate_content_raises(self, service):
        """Test storing duplicate content raises error."""
        report = service.store_report(
            name="Report",
            content="Same Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        with pytest.raises(DuplicateContentError):
            service.store_report(
                name="Report",
                content="Same Content",
                format=ReportFormat.HTML,
                project_id="p-1",
                report_id=report.report_id,
            )

    def test_store_report_skip_duplicate_check(self, service):
        """Test skipping duplicate check."""
        report = service.store_report(
            name="Report",
            content="Same Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        # Should not raise
        report2 = service.store_report(
            name="Report",
            content="Same Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id=report.report_id,
            skip_duplicate_check=True,
        )

        assert report2.current_version == 2

    def test_get_report(self, service):
        """Test getting report by ID."""
        stored = service.store_report(
            name="Get Test",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        retrieved = service.get_report(stored.report_id)

        assert retrieved.report_id == stored.report_id
        assert retrieved.name == "Get Test"

    def test_get_report_not_found(self, service):
        """Test getting non-existent report raises error."""
        with pytest.raises(ReportNotFoundError):
            service.get_report("nonexistent")

    def test_get_report_version(self, service):
        """Test getting specific version."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.HTML,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="V2",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id=report.report_id,
        )

        v1 = service.get_report_version(report.report_id, 1)
        v2 = service.get_report_version(report.report_id, 2)

        assert v1.content == "V1"
        assert v2.content == "V2"

    def test_get_report_version_not_found(self, service):
        """Test getting non-existent version raises error."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        with pytest.raises(VersionNotFoundError):
            service.get_report_version(report.report_id, 99)

    def test_list_reports_all(self, service):
        """Test listing all reports."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-2")

        reports = service.list_reports()

        assert len(reports) == 2

    def test_list_reports_filter_by_project(self, service):
        """Test listing reports filtered by project."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-2")
        service.store_report(name="R3", content="C3", format=ReportFormat.HTML, project_id="p-1")

        reports = service.list_reports(project_id="p-1")

        assert len(reports) == 2
        assert all(r.project_id == "p-1" for r in reports)

    def test_list_reports_filter_by_entity(self, service):
        """Test listing reports filtered by entity."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1", entity_id="e-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-1", entity_id="e-2")
        service.store_report(name="R3", content="C3", format=ReportFormat.HTML, project_id="p-1", entity_id="e-1")

        reports = service.list_reports(entity_id="e-1")

        assert len(reports) == 2
        assert all(r.entity_id == "e-1" for r in reports)

    def test_list_reports_filter_by_format(self, service):
        """Test listing reports filtered by format."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.PDF, project_id="p-1")
        service.store_report(name="R3", content="C3", format=ReportFormat.HTML, project_id="p-1")

        reports = service.list_reports(format_filter=ReportFormat.HTML)

        assert len(reports) == 2

    def test_list_reports_sorted_by_updated(self, service):
        """Test that reports are sorted by updated_at descending."""
        r1 = service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        r2 = service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-1")

        # Update r1 to make it more recent
        service.store_report(
            name="R1 Updated",
            content="C1 Updated",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id=r1.report_id,
        )

        reports = service.list_reports()

        assert reports[0].report_id == r1.report_id  # r1 should be first (most recently updated)

    def test_delete_report(self, service):
        """Test deleting a report."""
        report = service.store_report(
            name="To Delete",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        result = service.delete_report(report.report_id)

        assert result is True
        with pytest.raises(ReportNotFoundError):
            service.get_report(report.report_id)

    def test_delete_report_not_found(self, service):
        """Test deleting non-existent report raises error."""
        with pytest.raises(ReportNotFoundError):
            service.delete_report("nonexistent")


# ==================== Version Diffing Tests ====================


class TestVersionDiffing:
    """Tests for version comparison functionality."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_get_report_diff_basic(self, service):
        """Test basic version diffing."""
        report = service.store_report(
            name="Report",
            content="Line 1\nLine 2\nLine 3",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="Line 1\nModified\nLine 3",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
        )

        diff = service.get_report_diff(report.report_id, 1, 2)

        assert diff["version1"] == 1
        assert diff["version2"] == 2
        assert diff["is_identical"] is False
        assert diff["lines_added"] >= 1
        assert diff["lines_removed"] >= 1
        assert "Modified" in diff["diff"]

    def test_get_report_diff_identical(self, service):
        """Test diffing identical content."""
        report = service.store_report(
            name="Report",
            content="Same content",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="Same content",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
            skip_duplicate_check=True,
        )

        diff = service.get_report_diff(report.report_id, 1, 2)

        assert diff["is_identical"] is True
        assert diff["lines_added"] == 0
        assert diff["lines_removed"] == 0

    def test_get_report_diff_additions_only(self, service):
        """Test diffing with only additions."""
        report = service.store_report(
            name="Report",
            content="Line 1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="Line 1\nLine 2\nLine 3",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
        )

        diff = service.get_report_diff(report.report_id, 1, 2)

        # Lines added should be at least 2 (Line 2 and Line 3 were added)
        assert diff["lines_added"] >= 2
        assert diff["is_identical"] is False

    def test_get_report_diff_includes_timestamps(self, service):
        """Test that diff includes version timestamps."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="V2",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
        )

        diff = service.get_report_diff(report.report_id, 1, 2)

        assert "version1_generated_at" in diff
        assert "version2_generated_at" in diff

    def test_get_report_diff_report_not_found(self, service):
        """Test diffing non-existent report raises error."""
        with pytest.raises(ReportNotFoundError):
            service.get_report_diff("nonexistent", 1, 2)

    def test_get_report_diff_version_not_found(self, service):
        """Test diffing with non-existent version raises error."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        with pytest.raises(VersionNotFoundError):
            service.get_report_diff(report.report_id, 1, 99)


# ==================== Cleanup Tests ====================


class TestVersionCleanup:
    """Tests for version cleanup functionality."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_cleanup_old_versions(self, service):
        """Test cleaning up old versions."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        for i in range(2, 11):
            service.store_report(
                name="Report",
                content=f"V{i}",
                format=ReportFormat.TEXT,
                project_id="p-1",
                report_id=report.report_id,
            )

        deleted = service.cleanup_old_versions(report.report_id, keep_count=3)

        assert deleted == 7
        updated = service.get_report(report.report_id)
        assert updated.get_version_count() == 3

    def test_cleanup_keeps_most_recent(self, service):
        """Test that cleanup keeps most recent versions."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        for i in range(2, 6):
            service.store_report(
                name="Report",
                content=f"V{i}",
                format=ReportFormat.TEXT,
                project_id="p-1",
                report_id=report.report_id,
            )

        service.cleanup_old_versions(report.report_id, keep_count=2)

        updated = service.get_report(report.report_id)
        versions = [v.version_number for v in updated.versions]

        assert 4 in versions
        assert 5 in versions
        assert 1 not in versions

    def test_cleanup_no_op_when_fewer_versions(self, service):
        """Test cleanup does nothing when fewer versions than keep_count."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="V2",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
        )

        deleted = service.cleanup_old_versions(report.report_id, keep_count=5)

        assert deleted == 0
        updated = service.get_report(report.report_id)
        assert updated.get_version_count() == 2

    def test_cleanup_invalid_keep_count(self, service):
        """Test cleanup with keep_count < 1 raises error."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        with pytest.raises(ValueError):
            service.cleanup_old_versions(report.report_id, keep_count=0)

    def test_cleanup_report_not_found(self, service):
        """Test cleanup on non-existent report raises error."""
        with pytest.raises(ReportNotFoundError):
            service.cleanup_old_versions("nonexistent", keep_count=5)


# ==================== Content Deduplication Tests ====================


class TestContentDeduplication:
    """Tests for content deduplication."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_context_hash_computed(self, service):
        """Test that context hash is computed."""
        report = service.store_report(
            name="Report",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            context={"key": "value", "number": 42},
        )

        assert report.versions[0].context_hash != ""

    def test_context_hash_consistent(self, service):
        """Test that same context produces same hash."""
        context = {"a": 1, "b": 2}

        report1 = service.store_report(
            name="Report 1",
            content="Content 1",
            format=ReportFormat.HTML,
            project_id="p-1",
            context=context,
        )
        report2 = service.store_report(
            name="Report 2",
            content="Content 2",
            format=ReportFormat.HTML,
            project_id="p-1",
            context=context,
        )

        assert report1.versions[0].context_hash == report2.versions[0].context_hash

    def test_context_hash_different_for_different_context(self, service):
        """Test that different context produces different hash."""
        report1 = service.store_report(
            name="Report 1",
            content="Content 1",
            format=ReportFormat.HTML,
            project_id="p-1",
            context={"key": "value1"},
        )
        report2 = service.store_report(
            name="Report 2",
            content="Content 2",
            format=ReportFormat.HTML,
            project_id="p-1",
            context={"key": "value2"},
        )

        assert report1.versions[0].context_hash != report2.versions[0].context_hash

    def test_find_by_context_hash(self, service):
        """Test finding report by context hash."""
        context = {"entity_id": "123", "template": "default"}

        report = service.store_report(
            name="Report",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            context=context,
        )

        found = service.find_by_context_hash(context)

        assert found is not None
        assert found.report_id == report.report_id

    def test_find_by_context_hash_not_found(self, service):
        """Test finding by non-existent context hash returns None."""
        result = service.find_by_context_hash({"nonexistent": "context"})

        assert result is None


# ==================== Import/Export Tests ====================


class TestImportExport:
    """Tests for import/export functionality."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_export_report(self, service):
        """Test exporting a report."""
        report = service.store_report(
            name="Export Test",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        exported = service.export_report(report.report_id)

        assert "report" in exported
        assert exported["report"]["name"] == "Export Test"
        assert "exported_at" in exported
        assert exported["export_version"] == "1.0"

    def test_export_report_not_found(self, service):
        """Test exporting non-existent report raises error."""
        with pytest.raises(ReportNotFoundError):
            service.export_report("nonexistent")

    def test_import_report(self, service):
        """Test importing a report."""
        data = {
            "report": {
                "report_id": "imported-1",
                "name": "Imported Report",
                "project_id": "p-1",
                "versions": [
                    {
                        "version_id": "v-1",
                        "report_id": "imported-1",
                        "version_number": 1,
                        "content": "Imported content",
                        "format": "html",
                    }
                ],
                "current_version": 1,
            }
        }

        imported = service.import_report(data)

        assert imported.report_id == "imported-1"
        assert imported.name == "Imported Report"
        assert len(imported.versions) == 1

    def test_import_report_existing_raises(self, service):
        """Test importing existing report without overwrite raises error."""
        service.store_report(
            name="Existing",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id="existing-1",
        )

        data = {
            "report": {
                "report_id": "existing-1",
                "name": "New Name",
                "project_id": "p-1",
                "versions": [],
                "current_version": 0,
            }
        }

        with pytest.raises(ValueError):
            service.import_report(data, overwrite=False)

    def test_import_report_overwrite(self, service):
        """Test importing with overwrite replaces existing."""
        service.store_report(
            name="Original",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id="to-replace",
        )

        data = {
            "report": {
                "report_id": "to-replace",
                "name": "Replaced",
                "project_id": "p-1",
                "versions": [],
                "current_version": 0,
            }
        }

        imported = service.import_report(data, overwrite=True)

        assert imported.name == "Replaced"

    def test_import_invalid_data(self, service):
        """Test importing invalid data raises error."""
        with pytest.raises(ValueError):
            service.import_report({})


# ==================== Template Queries Tests ====================


class TestTemplateQueries:
    """Tests for template-based queries."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_get_reports_by_template(self, service):
        """Test getting reports by template ID."""
        service.store_report(
            name="R1",
            content="C1",
            format=ReportFormat.HTML,
            project_id="p-1",
            template_id="t-1",
        )
        service.store_report(
            name="R2",
            content="C2",
            format=ReportFormat.HTML,
            project_id="p-1",
            template_id="t-2",
        )
        service.store_report(
            name="R3",
            content="C3",
            format=ReportFormat.HTML,
            project_id="p-1",
            template_id="t-1",
        )

        reports = service.get_reports_by_template("t-1")

        assert len(reports) == 2

    def test_get_reports_by_template_none_found(self, service):
        """Test getting reports by non-existent template returns empty."""
        service.store_report(
            name="R1",
            content="C1",
            format=ReportFormat.HTML,
            project_id="p-1",
            template_id="t-1",
        )

        reports = service.get_reports_by_template("nonexistent")

        assert len(reports) == 0


# ==================== Statistics Tests ====================


class TestStatistics:
    """Tests for statistics methods."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_get_report_count(self, service):
        """Test getting total report count."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R3", content="C3", format=ReportFormat.HTML, project_id="p-1")

        assert service.get_report_count() == 3

    def test_get_total_version_count(self, service):
        """Test getting total version count."""
        report = service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(
            name="R1",
            content="C1 V2",
            format=ReportFormat.HTML,
            project_id="p-1",
            report_id=report.report_id,
        )
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-1")

        assert service.get_total_version_count() == 3

    def test_clear_all(self, service):
        """Test clearing all reports."""
        service.store_report(name="R1", content="C1", format=ReportFormat.HTML, project_id="p-1")
        service.store_report(name="R2", content="C2", format=ReportFormat.HTML, project_id="p-1")

        cleared = service.clear_all()

        assert cleared == 2
        assert service.get_report_count() == 0


# ==================== Singleton Tests ====================


class TestReportStorageServiceSingleton:
    """Tests for singleton management."""

    def test_get_service_creates_singleton(self):
        """Test that get_report_storage_service creates a singleton."""
        set_report_storage_service(None)

        service1 = get_report_storage_service()
        service2 = get_report_storage_service()

        assert service1 is service2

    def test_set_service(self):
        """Test setting the service singleton."""
        new_service = ReportStorageService()

        set_report_storage_service(new_service)
        retrieved = get_report_storage_service()

        assert retrieved is new_service

    def test_set_service_to_none(self):
        """Test clearing the service singleton creates new one."""
        set_report_storage_service(None)
        service = get_report_storage_service()

        assert service is not None


# ==================== Router Tests ====================


class TestReportStorageRouter:
    """Tests for report storage router."""

    def test_router_import(self):
        """Test that report storage router can be imported."""
        from api.routers.report_storage import router
        assert router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.report_storage import (
            StoreReportRequest,
            ReportVersionResponse,
            ReportVersionSummary,
            StoredReportResponse,
            StoredReportListItem,
            ReportListResponse,
            DiffRequest,
            DiffResponse,
            CleanupRequest,
            CleanupResponse,
            ExportResponse,
            ImportRequest,
            StatsResponse,
        )

        assert hasattr(StoreReportRequest, "model_fields")
        assert hasattr(StoredReportResponse, "model_fields")
        assert hasattr(DiffResponse, "model_fields")

    def test_parse_format_valid(self):
        """Test parsing valid format strings."""
        from api.routers.report_storage import _parse_format

        assert _parse_format("html") == ReportFormat.HTML
        assert _parse_format("pdf") == ReportFormat.PDF
        assert _parse_format("markdown") == ReportFormat.MARKDOWN
        assert _parse_format("json") == ReportFormat.JSON
        assert _parse_format("text") == ReportFormat.TEXT

    def test_parse_format_invalid(self):
        """Test parsing invalid format raises HTTPException."""
        from api.routers.report_storage import _parse_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_format("invalid")

        assert exc_info.value.status_code == 400

    def test_version_to_response(self):
        """Test converting version to response model."""
        from api.routers.report_storage import _version_to_response

        version = ReportVersion(
            version_id="v-1",
            report_id="r-1",
            version_number=1,
            content="Test",
            format=ReportFormat.HTML,
        )

        response = _version_to_response(version)

        assert response.version_id == "v-1"
        assert response.format == "html"

    def test_version_to_summary(self):
        """Test converting version to summary model."""
        from api.routers.report_storage import _version_to_summary

        version = ReportVersion(
            version_id="v-1",
            report_id="r-1",
            version_number=1,
            content="Test content that should not appear in summary",
            format=ReportFormat.HTML,
        )

        summary = _version_to_summary(version)

        assert summary.version_id == "v-1"
        assert not hasattr(summary, "content")

    def test_report_to_response(self):
        """Test converting report to response model."""
        from api.routers.report_storage import _report_to_response

        version = ReportVersion(
            version_id="v-1",
            report_id="r-1",
            version_number=1,
            content="Test",
        )

        report = StoredReport(
            report_id="r-1",
            name="Test Report",
            project_id="p-1",
            versions=[version],
            current_version=1,
        )

        response = _report_to_response(report)

        assert response.report_id == "r-1"
        assert response.version_count == 1
        assert len(response.versions) == 1

    def test_report_to_list_item(self):
        """Test converting report to list item model."""
        from api.routers.report_storage import _report_to_list_item

        version = ReportVersion(
            report_id="r-1",
            version_number=1,
            content="Test",
            format=ReportFormat.PDF,
        )

        report = StoredReport(
            report_id="r-1",
            name="Test Report",
            project_id="p-1",
            versions=[version],
            current_version=1,
        )

        item = _report_to_list_item(report)

        assert item.report_id == "r-1"
        assert item.current_format == "pdf"


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def service(self):
        """Create a ReportStorageService for each test."""
        return ReportStorageService()

    def test_empty_content(self, service):
        """Test storing report with empty content."""
        report = service.store_report(
            name="Empty",
            content="",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        assert report.versions[0].content == ""

    def test_large_content(self, service):
        """Test storing report with large content."""
        large_content = "x" * 1000000  # 1MB

        report = service.store_report(
            name="Large",
            content=large_content,
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        assert len(report.versions[0].content) == 1000000

    def test_special_characters_in_content(self, service):
        """Test storing report with special characters."""
        content = "<script>alert('XSS')</script> & < > \" '"

        report = service.store_report(
            name="Special",
            content=content,
            format=ReportFormat.HTML,
            project_id="p-1",
        )

        assert report.versions[0].content == content

    def test_unicode_content(self, service):
        """Test storing report with unicode content."""
        content = "Hello World - Emoji: Test"

        report = service.store_report(
            name="Unicode",
            content=content,
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        assert "Hello" in report.versions[0].content

    def test_multiline_content(self, service):
        """Test storing report with multiline content."""
        content = "Line 1\nLine 2\nLine 3\r\nLine 4"

        report = service.store_report(
            name="Multiline",
            content=content,
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        assert "Line 1" in report.versions[0].content
        assert "Line 4" in report.versions[0].content

    def test_context_with_nested_objects(self, service):
        """Test context hashing with nested objects."""
        context = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"]
                }
            }
        }

        report = service.store_report(
            name="Nested",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            context=context,
        )

        assert report.versions[0].context_hash != ""

    def test_context_with_datetime(self, service):
        """Test context hashing with datetime objects."""
        context = {
            "timestamp": datetime.now(),
            "date": datetime.now().date(),
        }

        report = service.store_report(
            name="DateTime",
            content="Content",
            format=ReportFormat.HTML,
            project_id="p-1",
            context=context,
        )

        # Should not raise, and should produce a hash
        assert report.versions[0].context_hash != ""

    def test_rapid_version_creation(self, service):
        """Test rapidly creating many versions."""
        report = service.store_report(
            name="Rapid",
            content="V0",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )

        for i in range(1, 101):
            service.store_report(
                name="Rapid",
                content=f"V{i}",
                format=ReportFormat.TEXT,
                project_id="p-1",
                report_id=report.report_id,
            )

        updated = service.get_report(report.report_id)
        assert updated.current_version == 101
        assert len(updated.versions) == 101

    def test_diff_with_empty_versions(self, service):
        """Test diffing when one version is empty."""
        report = service.store_report(
            name="Report",
            content="",
            format=ReportFormat.TEXT,
            project_id="p-1",
        )
        service.store_report(
            name="Report",
            content="Now has content",
            format=ReportFormat.TEXT,
            project_id="p-1",
            report_id=report.report_id,
        )

        diff = service.get_report_diff(report.report_id, 1, 2)

        assert diff["lines_added"] > 0
        assert diff["is_identical"] is False

    def test_cleanup_clears_context_hashes(self, service):
        """Test that cleanup removes context hashes."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
            context={"version": 1},
        )

        for i in range(2, 6):
            service.store_report(
                name="Report",
                content=f"V{i}",
                format=ReportFormat.TEXT,
                project_id="p-1",
                report_id=report.report_id,
                context={"version": i},
            )

        # Cleanup old versions
        service.cleanup_old_versions(report.report_id, keep_count=2)

        # Old context hashes should be cleaned up
        # (Testing internal state, but important for memory management)
        assert len(service._context_hashes) <= 2

    def test_delete_clears_context_hashes(self, service):
        """Test that delete removes all context hashes."""
        report = service.store_report(
            name="Report",
            content="V1",
            format=ReportFormat.TEXT,
            project_id="p-1",
            context={"key": "value"},
        )

        initial_hash_count = len(service._context_hashes)

        service.delete_report(report.report_id)

        assert len(service._context_hashes) < initial_hash_count
