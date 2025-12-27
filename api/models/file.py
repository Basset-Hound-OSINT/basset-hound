"""
Pydantic models for File management.

Files are stored in the filesystem under the project/person directory
structure and referenced in Neo4j. Files can be associated with
specific profile fields or stored in general files/reports folders.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Allowed image extensions for profile pictures
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Allowed file extensions for general uploads
ALLOWED_FILE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",  # Images
    ".pdf", ".doc", ".docx", ".txt", ".md",     # Documents
    ".xls", ".xlsx", ".csv",                     # Spreadsheets
    ".zip", ".tar", ".gz",                       # Archives
    ".json", ".xml", ".yaml", ".yml",            # Data files
}


class FileUpload(BaseModel):
    """
    Model for file upload metadata.

    Used when uploading files through the API. The actual file content
    is handled separately via multipart form data.
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename of the uploaded file",
        examples=["profile_photo.jpg", "background_report.pdf"]
    )
    section_id: Optional[str] = Field(
        default=None,
        description="Profile section this file belongs to (e.g., 'core', 'social')",
        examples=["Profile Picture Section", "social"]
    )
    field_id: Optional[str] = Field(
        default=None,
        description="Profile field this file belongs to",
        examples=["profilepicturefile", "social files"]
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional comment or description for the file",
        examples=["Screenshot from LinkedIn profile, captured 2024-01-15"]
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """
        Validate filename for security and format.

        Prevents directory traversal and ensures valid characters.
        """
        v = v.strip()
        if not v:
            raise ValueError("Filename cannot be empty")

        # Prevent directory traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid filename - path traversal not allowed")

        # Check for valid characters (alphanumeric, dash, underscore, dot, space)
        import re
        if not re.match(r"^[\w\-. ]+$", v):
            raise ValueError("Filename contains invalid characters")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "profile_photo.jpg",
                "section_id": "Profile Picture Section",
                "field_id": "profilepicturefile",
                "comment": "Primary profile photo"
            }
        }
    )


class FileResponse(BaseModel):
    """
    Model for file data returned by the API.

    Contains file metadata and access information. The actual file
    content is served separately via a file serving endpoint.
    """

    id: str = Field(
        ...,
        description="Unique file identifier (hash-based)",
        examples=["a1b2c3d4e5f6"]
    )
    name: str = Field(
        ...,
        description="Original filename",
        examples=["profile_photo.jpg"]
    )
    path: str = Field(
        ...,
        description="Stored filename (includes ID prefix)",
        examples=["a1b2c3d4e5f6_profile_photo.jpg"]
    )
    full_path: Optional[str] = Field(
        default=None,
        description="Full filesystem path (internal use)",
        examples=["projects/uuid-project/people/uuid-person/files/a1b2c3d4e5f6_profile_photo.jpg"]
    )
    url: Optional[str] = Field(
        default=None,
        description="URL to access the file",
        examples=["/projects/uuid-project/people/uuid-person/files/a1b2c3d4e5f6_profile_photo.jpg"]
    )
    section_id: Optional[str] = Field(
        default=None,
        description="Profile section this file belongs to"
    )
    field_id: Optional[str] = Field(
        default=None,
        description="Profile field this file belongs to"
    )
    person_id: Optional[str] = Field(
        default=None,
        description="ID of the entity this file belongs to"
    )
    uploaded_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the file was uploaded"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional comment or description"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional file metadata"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4e5f6",
                "name": "profile_photo.jpg",
                "path": "a1b2c3d4e5f6_profile_photo.jpg",
                "full_path": "projects/uuid-project/people/uuid-person/files/a1b2c3d4e5f6_profile_photo.jpg",
                "url": "/projects/uuid-project/people/uuid-person/files/a1b2c3d4e5f6_profile_photo.jpg",
                "section_id": "Profile Picture Section",
                "field_id": "profilepicturefile",
                "person_id": "550e8400-e29b-41d4-a716-446655440000",
                "uploaded_at": "2024-01-15T10:30:00",
                "comment": "Primary profile photo"
            }
        }
    )


class FileList(BaseModel):
    """
    Model for a list of files.

    Used when listing all files for an entity or in a directory.
    """

    files: list[FileResponse] = Field(
        default_factory=list,
        description="List of file records"
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of files"
    )
    entity_id: Optional[str] = Field(
        default=None,
        description="Entity ID if listing entity files"
    )
    path: Optional[str] = Field(
        default=None,
        description="Directory path if listing directory contents"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    {
                        "id": "a1b2c3d4e5f6",
                        "name": "profile_photo.jpg",
                        "path": "a1b2c3d4e5f6_profile_photo.jpg",
                        "person_id": "550e8400-e29b-41d4-a716-446655440000"
                    }
                ],
                "total": 1,
                "entity_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class DirectoryEntry(BaseModel):
    """
    Model for a directory listing entry.

    Used in file explorer functionality to represent files and folders.
    """

    name: str = Field(
        ...,
        description="Name of the file or folder"
    )
    path: str = Field(
        ...,
        description="Relative path from entity root"
    )
    type: str = Field(
        ...,
        pattern="^(file|folder)$",
        description="Type of entry: 'file' or 'folder'"
    )
    date: Optional[str] = Field(
        default=None,
        description="Last modified date"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL to access (for files only)"
    )
    id: Optional[str] = Field(
        default=None,
        description="File ID (for files only)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "profile_photo.jpg",
                "path": "files/profile_photo.jpg",
                "type": "file",
                "date": "2024-01-15 10:30",
                "url": "/projects/uuid/people/uuid/files/profile_photo.jpg",
                "id": "a1b2c3d4e5f6"
            }
        }
    )


class DirectoryTree(BaseModel):
    """
    Model for file explorer tree structure.

    Represents the hierarchical folder/file structure for an entity.
    """

    entries: list[DirectoryEntry] = Field(
        default_factory=list,
        description="List of entries in the current directory"
    )
    tree: list[dict] = Field(
        default_factory=list,
        description="Hierarchical tree structure of all folders/files"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entries": [
                    {"name": "report.md", "path": "reports/report.md", "type": "file"}
                ],
                "tree": [
                    {
                        "name": "files",
                        "type": "folder",
                        "path": "files",
                        "children": []
                    },
                    {
                        "name": "reports",
                        "type": "folder",
                        "path": "reports",
                        "open": True,
                        "children": [
                            {"name": "report.md", "type": "file", "path": "reports/report.md"}
                        ]
                    }
                ]
            }
        }
    )
