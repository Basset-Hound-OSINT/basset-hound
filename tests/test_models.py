"""
Tests for Pydantic models.
"""

import pytest
from pydantic import ValidationError


class TestProjectModels:
    """Tests for project-related Pydantic models."""

    def test_project_create_valid(self):
        """Test creating a valid project."""
        from api.models.project import ProjectCreate

        project = ProjectCreate(name="Test Project")
        assert project.name == "Test Project"
        assert project.safe_name is None  # Auto-generated server-side

    def test_project_create_with_safe_name(self):
        """Test creating a project with explicit safe_name."""
        from api.models.project import ProjectCreate

        project = ProjectCreate(name="Test Project", safe_name="test_project")
        assert project.name == "Test Project"
        assert project.safe_name == "test_project"

    def test_project_create_empty_name_fails(self):
        """Test that empty project name fails validation."""
        from api.models.project import ProjectCreate

        with pytest.raises(ValidationError):
            ProjectCreate(name="")

    def test_project_create_whitespace_name_fails(self):
        """Test that whitespace-only project name fails validation."""
        from api.models.project import ProjectCreate

        with pytest.raises(ValidationError):
            ProjectCreate(name="   ")

    def test_project_response(self):
        """Test project response model."""
        from api.models.project import ProjectResponse

        project = ProjectResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Project",
            safe_name="test_project",
            created_at="2024-01-15T10:30:00Z"
        )
        assert project.id == "550e8400-e29b-41d4-a716-446655440000"
        assert project.name == "Test Project"


class TestEntityModels:
    """Tests for entity-related Pydantic models."""

    def test_entity_create_empty(self):
        """Test creating an entity with empty profile."""
        from api.models.entity import EntityCreate

        entity = EntityCreate()
        assert entity.profile == {}

    def test_entity_create_with_profile(self):
        """Test creating an entity with profile data."""
        from api.models.entity import EntityCreate

        profile = {
            "core": {
                "name": [{"first_name": "John", "last_name": "Doe"}]
            }
        }
        entity = EntityCreate(profile=profile)
        assert entity.profile == profile

    def test_entity_update_partial(self):
        """Test partial entity update."""
        from api.models.entity import EntityUpdate

        update = EntityUpdate(profile={"core": {"email": ["new@example.com"]}})
        assert update.profile is not None
        assert "core" in update.profile

    def test_entity_response(self, sample_entity):
        """Test entity response model."""
        from api.models.entity import EntityResponse

        entity = EntityResponse(**sample_entity)
        assert entity.id == sample_entity["id"]
        assert entity.profile == sample_entity["profile"]


class TestRelationshipModels:
    """Tests for relationship-related Pydantic models."""

    def test_relationship_create(self):
        """Test creating a relationship."""
        from api.models.relationship import RelationshipCreate

        rel = RelationshipCreate(
            tagged_ids=["id1", "id2"],
            transitive_relationships=["id3"]
        )
        assert len(rel.tagged_ids) == 2
        assert len(rel.transitive_relationships) == 1

    def test_relationship_create_empty_lists(self):
        """Test creating a relationship with empty lists."""
        from api.models.relationship import RelationshipCreate

        rel = RelationshipCreate()
        assert rel.tagged_ids == []
        assert rel.transitive_relationships == []

    def test_relationship_duplicate_ids_fails(self):
        """Test that duplicate IDs fail validation."""
        from api.models.relationship import RelationshipCreate

        with pytest.raises(ValidationError):
            RelationshipCreate(tagged_ids=["id1", "id1"])


class TestFileModels:
    """Tests for file-related Pydantic models."""

    def test_file_upload_valid(self):
        """Test valid file upload model."""
        from api.models.file import FileUpload

        upload = FileUpload(
            filename="test_photo.jpg",
            section_id="profile",
            field_id="profile_picture"
        )
        assert upload.filename == "test_photo.jpg"

    def test_file_upload_path_traversal_fails(self):
        """Test that path traversal in filename fails."""
        from api.models.file import FileUpload

        with pytest.raises(ValidationError):
            FileUpload(filename="../../../etc/passwd")

    def test_file_response(self):
        """Test file response model."""
        from api.models.file import FileResponse

        response = FileResponse(
            id="abc123",
            name="test.jpg",
            path="abc123_test.jpg"
        )
        assert response.id == "abc123"


class TestReportModels:
    """Tests for report-related Pydantic models."""

    def test_report_create_valid(self):
        """Test creating a valid report."""
        from api.models.report import ReportCreate

        report = ReportCreate(
            filename="investigation.md",
            content="# Investigation\n\nFindings..."
        )
        assert report.filename == "investigation.md"

    def test_report_create_invalid_extension(self):
        """Test that non-.md extension fails."""
        from api.models.report import ReportCreate

        with pytest.raises(ValidationError):
            ReportCreate(filename="investigation.txt")

    def test_report_update(self):
        """Test report update model."""
        from api.models.report import ReportUpdate

        update = ReportUpdate(content="# Updated\n\nNew content...")
        assert "Updated" in update.content


class TestAuthModels:
    """Tests for authentication-related Pydantic models."""

    def test_token_model(self):
        """Test token model."""
        from api.models.auth import Token

        token = Token(access_token="eyJhbGc...")
        assert token.access_token == "eyJhbGc..."
        assert token.token_type == "bearer"

    def test_user_create_valid(self):
        """Test creating a valid user."""
        from api.models.auth import UserCreate

        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecureP@ss123!"
        )
        assert user.username == "testuser"

    def test_user_create_weak_password_fails(self):
        """Test that weak password fails validation."""
        from api.models.auth import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="weak"
            )

    def test_user_create_reserved_username_fails(self):
        """Test that reserved username fails validation."""
        from api.models.auth import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                username="admin",
                email="test@example.com",
                password="SecureP@ss123!"
            )


class TestConfigModels:
    """Tests for configuration-related Pydantic models."""

    def test_config_section(self):
        """Test config section model."""
        from api.models.config import ConfigSection, ConfigField

        section = ConfigSection(
            id="core",
            name="Personal Information",
            fields=[
                ConfigField(id="name", type="string"),
                ConfigField(id="email", type="email", multiple=True)
            ]
        )
        assert section.id == "core"
        assert len(section.fields) == 2

    def test_config_field_invalid_type(self):
        """Test that invalid field type fails."""
        from api.models.config import ConfigField

        with pytest.raises(ValidationError):
            ConfigField(id="test", type="invalid_type")

    def test_config_response(self, mock_config):
        """Test config response model."""
        from api.models.config import ConfigResponse, ConfigSection, ConfigField

        sections = [
            ConfigSection(
                id=s["id"],
                name=s["name"],
                fields=[ConfigField(**f) for f in s["fields"]]
            )
            for s in mock_config["sections"]
        ]

        response = ConfigResponse(sections=sections)
        assert len(response.sections) == 2
