"""
Report Storage Service for Basset Hound

This module provides comprehensive report storage and version management for OSINT investigations.
It supports storing generated reports with version history, content deduplication via context hashing,
version comparison (diffing), and cleanup of old versions.
"""

import hashlib
import json
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from difflib import unified_diff
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report output formats."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"


class ReportVersion(BaseModel):
    """
    Represents a single version of a stored report.

    Attributes:
        version_id: Unique identifier for this version
        report_id: ID of the parent report
        version_number: Sequential version number (1, 2, 3, ...)
        content: The actual report content (text/HTML/markdown)
        format: Output format of the report
        generated_at: When this version was generated
        template_id: ID of the template used to generate the report (if any)
        context_hash: Hash of the context data used for deduplication
    """
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(default_factory=lambda: str(uuid4()))
    report_id: str = Field(..., description="Parent report ID")
    version_number: int = Field(..., ge=1, description="Sequential version number")
    content: str = Field(..., description="Report content")
    format: ReportFormat = Field(default=ReportFormat.HTML, description="Report format")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    template_id: Optional[str] = Field(default=None, description="Template ID used for generation")
    context_hash: str = Field(default="", description="Hash of context data for deduplication")

    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            "version_id": self.version_id,
            "report_id": self.report_id,
            "version_number": self.version_number,
            "content": self.content,
            "format": self.format.value,
            "generated_at": self.generated_at.isoformat(),
            "template_id": self.template_id,
            "context_hash": self.context_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportVersion":
        """Create version from dictionary."""
        fmt = data.get("format", "html")
        if isinstance(fmt, str):
            fmt = ReportFormat(fmt)

        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        elif generated_at is None:
            generated_at = datetime.now(timezone.utc)

        return cls(
            version_id=data.get("version_id", str(uuid4())),
            report_id=data.get("report_id", ""),
            version_number=data.get("version_number", 1),
            content=data.get("content", ""),
            format=fmt,
            generated_at=generated_at,
            template_id=data.get("template_id"),
            context_hash=data.get("context_hash", ""),
        )


class StoredReport(BaseModel):
    """
    Represents a stored report with version history.

    Attributes:
        report_id: Unique identifier for the report
        name: Display name for the report
        project_id: Associated project ID
        entity_id: Associated entity ID (optional)
        created_at: When the report was first created
        updated_at: When the report was last updated
        versions: List of all versions of this report
        current_version: The current/latest version number
    """
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Report display name")
    project_id: str = Field(..., description="Associated project ID")
    entity_id: Optional[str] = Field(default=None, description="Associated entity ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    versions: List[ReportVersion] = Field(default_factory=list, description="Version history")
    current_version: int = Field(default=0, description="Current version number")

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "name": self.name,
            "project_id": self.project_id,
            "entity_id": self.entity_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "versions": [v.to_dict() for v in self.versions],
            "current_version": self.current_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredReport":
        """Create report from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.now(timezone.utc)

        versions = data.get("versions", [])
        if versions and isinstance(versions[0], dict):
            versions = [ReportVersion.from_dict(v) for v in versions]

        return cls(
            report_id=data.get("report_id", str(uuid4())),
            name=data.get("name", "Untitled Report"),
            project_id=data.get("project_id", ""),
            entity_id=data.get("entity_id"),
            created_at=created_at,
            updated_at=updated_at,
            versions=versions,
            current_version=data.get("current_version", 0),
        )

    def get_version(self, version_number: int) -> Optional[ReportVersion]:
        """Get a specific version by number."""
        for version in self.versions:
            if version.version_number == version_number:
                return version
        return None

    def get_current_version_content(self) -> Optional[ReportVersion]:
        """Get the current (latest) version."""
        return self.get_version(self.current_version)

    def get_version_count(self) -> int:
        """Get the number of versions."""
        return len(self.versions)


class ReportNotFoundError(Exception):
    """Raised when a report is not found."""
    pass


class VersionNotFoundError(Exception):
    """Raised when a version is not found."""
    pass


class DuplicateContentError(Exception):
    """Raised when trying to store duplicate content."""
    pass


class ReportStorageService:
    """
    Service for storing and managing reports with version history.

    Provides methods for storing, retrieving, and managing reports
    with automatic versioning and content deduplication.
    """

    def __init__(
        self,
        max_reports: int = 500,
        max_context_hashes: int = 1000,
    ):
        """
        Initialize the report storage service.

        Args:
            max_reports: Maximum number of reports to store in memory (LRU eviction)
            max_context_hashes: Maximum number of context hashes for deduplication
        """
        self._lock = threading.RLock()
        self._reports: OrderedDict[str, StoredReport] = OrderedDict()
        self._context_hashes: OrderedDict[str, str] = OrderedDict()  # hash -> report_id for deduplication
        self._max_reports = max_reports
        self._max_context_hashes = max_context_hashes

    # ==================== Memory Management ====================

    def _enforce_reports_limit(self) -> None:
        """Evict oldest reports when limit is exceeded (LRU eviction)."""
        while len(self._reports) > self._max_reports:
            oldest_key = next(iter(self._reports))
            oldest_report = self._reports.pop(oldest_key)
            # Also clean up context hashes for this report
            for version in oldest_report.versions:
                if version.context_hash and version.context_hash in self._context_hashes:
                    del self._context_hashes[version.context_hash]
            logger.debug(f"LRU evicted report: {oldest_key}")

    def _enforce_context_hashes_limit(self) -> None:
        """Evict oldest context hashes when limit is exceeded (LRU eviction)."""
        while len(self._context_hashes) > self._max_context_hashes:
            oldest_key = next(iter(self._context_hashes))
            del self._context_hashes[oldest_key]
            logger.debug(f"LRU evicted context hash: {oldest_key[:16]}...")

    def get_reports_size(self) -> int:
        """Get current number of reports in storage."""
        with self._lock:
            return len(self._reports)

    def get_reports_capacity(self) -> int:
        """Get maximum reports storage capacity."""
        return self._max_reports

    def get_context_hashes_size(self) -> int:
        """Get current number of context hashes in storage."""
        with self._lock:
            return len(self._context_hashes)

    def get_context_hashes_capacity(self) -> int:
        """Get maximum context hashes capacity."""
        return self._max_context_hashes

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for this service."""
        with self._lock:
            return {
                "reports_count": len(self._reports),
                "reports_capacity": self._max_reports,
                "reports_usage_percent": (len(self._reports) / self._max_reports * 100) if self._max_reports > 0 else 0,
                "context_hashes_count": len(self._context_hashes),
                "context_hashes_capacity": self._max_context_hashes,
                "context_hashes_usage_percent": (len(self._context_hashes) / self._max_context_hashes * 100) if self._max_context_hashes > 0 else 0,
                "total_versions": sum(len(r.versions) for r in self._reports.values()),
            }

    def _compute_context_hash(self, context: Optional[Dict[str, Any]]) -> str:
        """Compute a hash of the context data for deduplication."""
        if context is None:
            return ""
        try:
            # Sort keys for consistent hashing
            serialized = json.dumps(context, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode()).hexdigest()[:16]
        except (TypeError, ValueError):
            return ""

    def _compute_content_hash(self, content: str) -> str:
        """Compute a hash of the content for detecting duplicates."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def store_report(
        self,
        name: str,
        content: str,
        format: ReportFormat,
        project_id: str,
        entity_id: Optional[str] = None,
        template_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        report_id: Optional[str] = None,
        skip_duplicate_check: bool = False,
    ) -> StoredReport:
        """
        Store a new report or add a new version to an existing report.

        If report_id is provided and exists, a new version is added.
        If report_id is provided but doesn't exist, a new report is created with that ID.
        If report_id is not provided, a new report is created.

        Args:
            name: Display name for the report
            content: Report content
            format: Output format of the report
            project_id: Associated project ID
            entity_id: Associated entity ID (optional)
            template_id: Template ID used for generation (optional)
            context: Context data used for generation (optional)
            report_id: Existing report ID to add version to (optional)
            skip_duplicate_check: Skip duplicate content check

        Returns:
            The stored/updated StoredReport

        Raises:
            DuplicateContentError: If content is duplicate and skip_duplicate_check is False
        """
        context_hash = self._compute_context_hash(context)
        content_hash = self._compute_content_hash(content)

        with self._lock:
            # Check for duplicate content within the same report
            if report_id and report_id in self._reports and not skip_duplicate_check:
                existing_report = self._reports[report_id]
                for version in existing_report.versions:
                    if self._compute_content_hash(version.content) == content_hash:
                        logger.info(f"Skipping duplicate content for report {report_id}")
                        raise DuplicateContentError(
                            f"Content is identical to version {version.version_number}"
                        )

            now = datetime.now(timezone.utc)

            if report_id and report_id in self._reports:
                # Add new version to existing report
                report = self._reports[report_id]
                new_version_number = report.current_version + 1

                version = ReportVersion(
                    version_id=str(uuid4()),
                    report_id=report_id,
                    version_number=new_version_number,
                    content=content,
                    format=format,
                    generated_at=now,
                    template_id=template_id,
                    context_hash=context_hash,
                )

                report.versions.append(version)
                report.current_version = new_version_number
                report.updated_at = now
                report.name = name  # Allow name update

                logger.info(f"Added version {new_version_number} to report {report_id}")

            else:
                # Create new report
                new_report_id = report_id or str(uuid4())

                version = ReportVersion(
                    version_id=str(uuid4()),
                    report_id=new_report_id,
                    version_number=1,
                    content=content,
                    format=format,
                    generated_at=now,
                    template_id=template_id,
                    context_hash=context_hash,
                )

                report = StoredReport(
                    report_id=new_report_id,
                    name=name,
                    project_id=project_id,
                    entity_id=entity_id,
                    created_at=now,
                    updated_at=now,
                    versions=[version],
                    current_version=1,
                )

                self._reports[new_report_id] = report
                logger.info(f"Created new report {new_report_id} with version 1")

            # Mark as most recently used
            self._reports.move_to_end(report.report_id)
            self._enforce_reports_limit()

            # Track context hash for deduplication lookup
            if context_hash:
                self._context_hashes[context_hash] = report.report_id
                self._context_hashes.move_to_end(context_hash)
                self._enforce_context_hashes_limit()

            return report

    def get_report(self, report_id: str) -> StoredReport:
        """
        Get a report by ID.

        Args:
            report_id: The report ID to retrieve

        Returns:
            The StoredReport

        Raises:
            ReportNotFoundError: If report doesn't exist
        """
        with self._lock:
            if report_id not in self._reports:
                raise ReportNotFoundError(f"Report not found: {report_id}")

            self._reports.move_to_end(report_id)  # Mark as most recently used
            return self._reports[report_id]

    def get_report_version(self, report_id: str, version_number: int) -> ReportVersion:
        """
        Get a specific version of a report.

        Args:
            report_id: The report ID
            version_number: The version number to retrieve

        Returns:
            The ReportVersion

        Raises:
            ReportNotFoundError: If report doesn't exist
            VersionNotFoundError: If version doesn't exist
        """
        report = self.get_report(report_id)

        version = report.get_version(version_number)
        if version is None:
            raise VersionNotFoundError(
                f"Version {version_number} not found for report {report_id}"
            )

        return version

    def list_reports(
        self,
        project_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        format_filter: Optional[ReportFormat] = None,
    ) -> List[StoredReport]:
        """
        List stored reports with optional filters.

        Args:
            project_id: Filter by project ID
            entity_id: Filter by entity ID
            format_filter: Filter by report format

        Returns:
            List of matching StoredReports
        """
        with self._lock:
            reports = list(self._reports.values())

        if project_id is not None:
            reports = [r for r in reports if r.project_id == project_id]

        if entity_id is not None:
            reports = [r for r in reports if r.entity_id == entity_id]

        if format_filter is not None:
            reports = [
                r for r in reports
                if r.versions and r.get_current_version_content() and
                r.get_current_version_content().format == format_filter
            ]

        # Sort by updated_at descending (most recent first)
        reports.sort(key=lambda r: r.updated_at, reverse=True)

        return reports

    def delete_report(self, report_id: str) -> bool:
        """
        Delete a report and all its versions.

        Args:
            report_id: The report ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ReportNotFoundError: If report doesn't exist
        """
        with self._lock:
            if report_id not in self._reports:
                raise ReportNotFoundError(f"Report not found: {report_id}")

            report = self._reports[report_id]

            # Remove context hashes
            for version in report.versions:
                if version.context_hash and version.context_hash in self._context_hashes:
                    del self._context_hashes[version.context_hash]

            del self._reports[report_id]

        logger.info(f"Deleted report {report_id}")

        return True

    def get_report_diff(
        self,
        report_id: str,
        version1: int,
        version2: int,
    ) -> Dict[str, Any]:
        """
        Compare two versions of a report.

        Args:
            report_id: The report ID
            version1: First version number to compare
            version2: Second version number to compare

        Returns:
            Dictionary containing:
                - version1: First version number
                - version2: Second version number
                - diff: Unified diff string
                - lines_added: Number of lines added
                - lines_removed: Number of lines removed
                - is_identical: Whether versions are identical

        Raises:
            ReportNotFoundError: If report doesn't exist
            VersionNotFoundError: If either version doesn't exist
        """
        v1 = self.get_report_version(report_id, version1)
        v2 = self.get_report_version(report_id, version2)

        # Split content into lines for diff
        lines1 = v1.content.splitlines(keepends=True)
        lines2 = v2.content.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = list(unified_diff(
            lines1,
            lines2,
            fromfile=f"Version {version1}",
            tofile=f"Version {version2}",
            lineterm="",
        ))

        diff_text = "".join(diff_lines)

        # Count added/removed lines
        lines_added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        lines_removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        is_identical = v1.content == v2.content

        return {
            "version1": version1,
            "version2": version2,
            "version1_generated_at": v1.generated_at.isoformat(),
            "version2_generated_at": v2.generated_at.isoformat(),
            "diff": diff_text,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "is_identical": is_identical,
        }

    def cleanup_old_versions(self, report_id: str, keep_count: int = 5) -> int:
        """
        Remove old versions of a report, keeping the most recent ones.

        Args:
            report_id: The report ID
            keep_count: Number of recent versions to keep (minimum 1)

        Returns:
            Number of versions deleted

        Raises:
            ReportNotFoundError: If report doesn't exist
            ValueError: If keep_count is less than 1
        """
        if keep_count < 1:
            raise ValueError("keep_count must be at least 1")

        with self._lock:
            report = self._reports.get(report_id)
            if report is None:
                raise ReportNotFoundError(f"Report not found: {report_id}")

            if len(report.versions) <= keep_count:
                return 0

            # Sort versions by version number
            sorted_versions = sorted(report.versions, key=lambda v: v.version_number, reverse=True)

            # Keep the most recent versions
            versions_to_keep = sorted_versions[:keep_count]
            versions_to_delete = sorted_versions[keep_count:]

            # Remove context hashes for deleted versions
            for version in versions_to_delete:
                if version.context_hash and version.context_hash in self._context_hashes:
                    del self._context_hashes[version.context_hash]

            # Update report
            report.versions = sorted(versions_to_keep, key=lambda v: v.version_number)

            deleted_count = len(versions_to_delete)

        logger.info(f"Cleaned up {deleted_count} old versions from report {report_id}")

        return deleted_count

    def find_by_context_hash(self, context: Dict[str, Any]) -> Optional[StoredReport]:
        """
        Find a report by context hash for deduplication.

        Args:
            context: The context data to hash and look up

        Returns:
            StoredReport if found, None otherwise
        """
        context_hash = self._compute_context_hash(context)
        with self._lock:
            if context_hash and context_hash in self._context_hashes:
                report_id = self._context_hashes[context_hash]
                if report_id in self._reports:
                    # Mark as most recently used
                    self._context_hashes.move_to_end(context_hash)
                    self._reports.move_to_end(report_id)
                    return self._reports[report_id]
            return None

    def get_report_count(self) -> int:
        """Get the total number of stored reports."""
        with self._lock:
            return len(self._reports)

    def get_total_version_count(self) -> int:
        """Get the total number of versions across all reports."""
        with self._lock:
            return sum(len(r.versions) for r in self._reports.values())

    def get_reports_by_template(self, template_id: str) -> List[StoredReport]:
        """
        Get all reports that were generated using a specific template.

        Args:
            template_id: The template ID to search for

        Returns:
            List of StoredReports using that template
        """
        with self._lock:
            matching_reports = []
            for report in self._reports.values():
                for version in report.versions:
                    if version.template_id == template_id:
                        matching_reports.append(report)
                        break
            return matching_reports

    def export_report(self, report_id: str) -> Dict[str, Any]:
        """
        Export a report with all versions for backup/transfer.

        Args:
            report_id: The report ID to export

        Returns:
            Dictionary containing report data and metadata

        Raises:
            ReportNotFoundError: If report doesn't exist
        """
        report = self.get_report(report_id)

        return {
            "report": report.to_dict(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "export_version": "1.0",
        }

    def import_report(
        self,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> StoredReport:
        """
        Import a report from exported data.

        Args:
            data: Exported report data
            overwrite: Whether to overwrite if report ID exists

        Returns:
            The imported StoredReport

        Raises:
            ValueError: If data is invalid or report exists without overwrite
        """
        if "report" not in data:
            raise ValueError("Invalid import data: missing 'report' key")

        report = StoredReport.from_dict(data["report"])

        with self._lock:
            if report.report_id in self._reports and not overwrite:
                raise ValueError(f"Report {report.report_id} already exists. Use overwrite=True to replace.")

            self._reports[report.report_id] = report
            self._reports.move_to_end(report.report_id)
            self._enforce_reports_limit()

            # Rebuild context hash index
            for version in report.versions:
                if version.context_hash:
                    self._context_hashes[version.context_hash] = report.report_id
                    self._context_hashes.move_to_end(version.context_hash)
            self._enforce_context_hashes_limit()

        logger.info(f"Imported report {report.report_id}")

        return report

    def clear_all(self) -> int:
        """
        Clear all stored reports (for testing).

        Returns:
            Number of reports cleared
        """
        with self._lock:
            count = len(self._reports)
            self._reports.clear()
            self._context_hashes.clear()
        logger.info(f"Cleared {count} reports")
        return count


# Singleton instance management
_report_storage_service: Optional[ReportStorageService] = None
_report_storage_lock = threading.RLock()


def get_report_storage_service() -> ReportStorageService:
    """
    Get or create the report storage service singleton.

    Returns:
        ReportStorageService instance
    """
    global _report_storage_service

    if _report_storage_service is None:
        with _report_storage_lock:
            # Double-check after acquiring lock
            if _report_storage_service is None:
                _report_storage_service = ReportStorageService()

    return _report_storage_service


def set_report_storage_service(service: Optional[ReportStorageService]) -> None:
    """Set the report storage service singleton (for testing)."""
    global _report_storage_service
    with _report_storage_lock:
        _report_storage_service = service
