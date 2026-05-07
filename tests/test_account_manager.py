"""
Tests for Account Management UI (Phase 4).

Tests the account-manager.js functionality and API integration.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from api.main import create_application
    app = create_application()
    return TestClient(app)


@pytest.fixture
def sample_project(client):
    """Create a sample project for testing."""
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Test Account Manager Project",
            "start_date": "2024-01-01",
            "description": "Test project for account manager UI"
        }
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_entity(client, sample_project):
    """Create a sample entity for testing."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    response = client.post(
        f"/api/v1/projects/{project_name}/entities",
        json={
            "entity_type": "person",
            "name": {
                "first_name": "John",
                "last_name": "Doe"
            }
        }
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_platform(client):
    """Create a sample platform for testing."""
    response = client.post(
        "/api/v1/platforms",
        json={
            "name": "Test Platform",
            "category": "social_media",
            "color": "#0066cc",
            "icon_class": "fas fa-test",
            "profile_url_template": "https://test.com/{username}",
            "active": True
        }
    )
    assert response.status_code == 201
    return response.json()


def test_platforms_list_endpoint(client):
    """Test that platforms list endpoint works."""
    response = client.get("/api/v1/platforms")
    assert response.status_code == 200
    data = response.json()
    assert "platforms" in data
    assert "count" in data
    assert isinstance(data["platforms"], list)


def test_create_platform(client):
    """Test creating a platform."""
    response = client.post(
        "/api/v1/platforms",
        json={
            "name": "Twitter Clone",
            "category": "social_media",
            "color": "#1DA1F2",
            "icon_class": "fas fa-x-twitter",
            "profile_url_template": "https://twitter.com/{username}",
            "active": True,
            "description": "Test Twitter-like platform"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Twitter Clone"
    assert data["category"] == "social_media"
    assert data["icon_class"] == "fas fa-x-twitter"


def test_list_accounts_empty(client, sample_project, sample_entity):
    """Test listing accounts for an entity with no accounts."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")

    response = client.get(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["accounts"] == []


def test_create_account(client, sample_project, sample_entity, sample_platform):
    """Test creating an account for an entity."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")
    platform_id = sample_platform.get("id")

    response = client.post(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
        json={
            "platform_id": platform_id,
            "username": "johndoe",
            "display_name": "John Doe",
            "profile_url": "https://test.com/johndoe",
            "verified": True,
            "followers": 1000,
            "bio": "Test user"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "johndoe"
    assert data["display_name"] == "John Doe"
    assert data["verified"] is True
    assert data["followers"] == 1000


def test_list_accounts_with_data(client, sample_project, sample_entity, sample_platform):
    """Test listing accounts after creating one."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")
    platform_id = sample_platform.get("id")

    # Create account first
    client.post(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
        json={
            "platform_id": platform_id,
            "username": "testuser",
            "display_name": "Test User",
            "verified": False
        }
    )

    # Now list accounts
    response = client.get(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["accounts"]) == 1
    account = data["accounts"][0]
    assert account["username"] == "testuser"
    assert account["platform_id"] == platform_id


def test_update_account(client, sample_project, sample_entity, sample_platform):
    """Test updating an account."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")
    platform_id = sample_platform.get("id")

    # Create account first
    client.post(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
        json={
            "platform_id": platform_id,
            "username": "oldname",
            "followers": 100
        }
    )

    # Update account
    response = client.put(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts/{platform_id}",
        json={
            "username": "newname",
            "followers": 2000,
            "verified": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newname"
    assert data["followers"] == 2000
    assert data["verified"] is True


def test_delete_account(client, sample_project, sample_entity, sample_platform):
    """Test deleting an account."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")
    platform_id = sample_platform.get("id")

    # Create account first
    client.post(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
        json={
            "platform_id": platform_id,
            "username": "tobedeleted",
        }
    )

    # Delete account
    response = client.delete(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts/{platform_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify it's deleted
    accounts_response = client.get(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts"
    )
    assert accounts_response.status_code == 200
    accounts_data = accounts_response.json()
    assert accounts_data["count"] == 0


def test_account_properties_persistence(client, sample_project, sample_entity, sample_platform):
    """Test that all account properties are properly persisted and retrieved."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")
    platform_id = sample_platform.get("id")

    # Create account with all properties
    create_response = client.post(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
        json={
            "platform_id": platform_id,
            "username": "fullprofile",
            "display_name": "Full Profile User",
            "profile_url": "https://test.com/fullprofile",
            "verified": True,
            "followers": 5000,
            "bio": "A complete test profile",
            "last_active": "2024-05-06T12:00:00",
            "password_ref": "vault://passwords/test"
        }
    )
    assert create_response.status_code == 201

    # Retrieve and verify all properties
    list_response = client.get(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts"
    )
    assert list_response.status_code == 200
    data = list_response.json()
    account = data["accounts"][0]

    assert account["username"] == "fullprofile"
    assert account["display_name"] == "Full Profile User"
    assert account["profile_url"] == "https://test.com/fullprofile"
    assert account["verified"] is True
    assert account["followers"] == 5000
    assert account["bio"] == "A complete test profile"
    assert "2024-05-06" in account["last_active"]


def test_multiple_platforms_per_entity(client, sample_project, sample_entity):
    """Test linking an entity to multiple platforms."""
    project_name = sample_project.get("safe_name", "test-account-manager-project")
    entity_id = sample_entity.get("id")

    # Create multiple platforms
    platforms = []
    for i in range(3):
        response = client.post(
            "/api/v1/platforms",
            json={
                "name": f"Platform {i}",
                "category": "social_media",
                "color": "#000000",
                "icon_class": f"fas fa-platform-{i}"
            }
        )
        platforms.append(response.json())

    # Link to all platforms
    for platform in platforms:
        response = client.post(
            f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts",
            json={
                "platform_id": platform["id"],
                "username": f"user_on_platform_{platform['name']}"
            }
        )
        assert response.status_code == 201

    # Verify all are listed
    list_response = client.get(
        f"/api/v1/projects/{project_name}/entities/{entity_id}/accounts"
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["count"] == 3
    assert len(data["accounts"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
