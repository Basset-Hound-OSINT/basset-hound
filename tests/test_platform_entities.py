"""
Unit Tests for Platform Entities (Phase 48: Dynamic Entity Architecture).

Tests cover:
- Platform CRUD operations
- Account linking and management
- Relationship validation
- Error handling and edge cases
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.neo4j_service import AsyncNeo4jService
from api.services.platform_service import PlatformService


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def neo4j_service():
    """Create Neo4j service for testing."""
    service = AsyncNeo4jService(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4jbasset"
    )
    try:
        await service.connect()
        yield service
    finally:
        await service.close()


@pytest.fixture
async def platform_service(neo4j_service):
    """Create platform service for testing."""
    return PlatformService(neo4j_service)


# =============================================================================
# PLATFORM CRUD TESTS
# =============================================================================


class TestPlatformCRUD:
    """Tests for platform entity CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_platform_minimal(self, platform_service):
        """Test creating a platform with minimal required fields."""
        platform_id = await platform_service.create_platform(
            name="TestPlatform1"
        )

        assert platform_id is not None
        assert isinstance(platform_id, str)
        assert len(platform_id) > 0

        # Verify platform was created
        platform = await platform_service.get_platform(platform_id)
        assert platform is not None
        assert platform["name"] == "TestPlatform1"
        assert platform["category"] == "other"
        assert platform["entity_type"] == "platform"

    @pytest.mark.asyncio
    async def test_create_platform_full(self, platform_service):
        """Test creating a platform with all fields."""
        platform_id = await platform_service.create_platform(
            name="TestPlatform2",
            category="social_media",
            color="#FF0000",
            icon_class="fa-test",
            profile_url_template="https://test.com/{username}",
            active=True,
            description="Test platform description"
        )

        platform = await platform_service.get_platform(platform_id)
        assert platform["name"] == "TestPlatform2"
        assert platform["category"] == "social_media"
        assert platform["color"] == "#FF0000"
        assert platform["icon_class"] == "fa-test"
        assert platform["active"] is True
        assert platform["description"] == "Test platform description"

    @pytest.mark.asyncio
    async def test_create_platform_invalid_name(self, platform_service):
        """Test that creating platform without name raises error."""
        with pytest.raises(ValueError):
            await platform_service.create_platform(name="")

        with pytest.raises(ValueError):
            await platform_service.create_platform(name=None)

    @pytest.mark.asyncio
    async def test_get_nonexistent_platform(self, platform_service):
        """Test getting a non-existent platform returns None."""
        platform = await platform_service.get_platform("nonexistent-id")
        assert platform is None

    @pytest.mark.asyncio
    async def test_list_platforms(self, platform_service):
        """Test listing all platforms."""
        # Create multiple platforms
        id1 = await platform_service.create_platform(
            name="Platform1",
            category="social_media"
        )
        id2 = await platform_service.create_platform(
            name="Platform2",
            category="professional"
        )

        platforms = await platform_service.list_platforms()
        assert len(platforms) >= 2

        names = [p["name"] for p in platforms]
        assert "Platform1" in names
        assert "Platform2" in names

    @pytest.mark.asyncio
    async def test_list_platforms_by_category(self, platform_service):
        """Test filtering platforms by category."""
        await platform_service.create_platform(
            name="SocialPlatform",
            category="social_media"
        )
        await platform_service.create_platform(
            name="ProfPlatform",
            category="professional"
        )

        social = await platform_service.list_platforms(category="social_media")
        assert all(p["category"] == "social_media" for p in social)

        prof = await platform_service.list_platforms(category="professional")
        assert all(p["category"] == "professional" for p in prof)

    @pytest.mark.asyncio
    async def test_update_platform(self, platform_service):
        """Test updating platform properties."""
        platform_id = await platform_service.create_platform(name="UpdateTest")

        await platform_service.update_platform(
            platform_id,
            category="social_media",
            color="#0000FF",
            active=False
        )

        platform = await platform_service.get_platform(platform_id)
        assert platform["category"] == "social_media"
        assert platform["color"] == "#0000FF"
        assert platform["active"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_platform(self, platform_service):
        """Test updating non-existent platform raises error."""
        with pytest.raises(ValueError):
            await platform_service.update_platform("nonexistent-id", name="New")

    @pytest.mark.asyncio
    async def test_delete_platform(self, platform_service):
        """Test deleting a platform."""
        platform_id = await platform_service.create_platform(name="DeleteTest")

        result = await platform_service.delete_platform(platform_id)
        assert result is True

        # Verify it's gone
        platform = await platform_service.get_platform(platform_id)
        assert platform is None

    @pytest.mark.asyncio
    async def test_delete_platform_with_accounts(self, platform_service, neo4j_service):
        """Test that deleting platform with accounts raises error."""
        platform_id = await platform_service.create_platform(name="AccountTest")

        # Create an entity
        entity_id = str(uuid4())

        # Link entity to platform
        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser"
        )

        # Try to delete platform
        with pytest.raises(ValueError) as exc_info:
            await platform_service.delete_platform(platform_id)
        assert "has" in str(exc_info.value).lower()
        assert "account" in str(exc_info.value).lower()


# =============================================================================
# ACCOUNT LINKING TESTS
# =============================================================================


class TestAccountLinking:
    """Tests for account linking and management."""

    @pytest.mark.asyncio
    async def test_link_entity_to_platform(self, platform_service, neo4j_service):
        """Test linking an entity to a platform."""
        platform_id = await platform_service.create_platform(name="LinkTest")
        entity_id = str(uuid4())

        result = await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser"
        )

        assert result is True

        # Verify account exists
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) > 0
        assert any(a["username"] == "testuser" for a in accounts)

    @pytest.mark.asyncio
    async def test_link_entity_with_full_properties(self, platform_service):
        """Test linking entity with all account properties."""
        platform_id = await platform_service.create_platform(name="FullTest")
        entity_id = str(uuid4())

        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="johndoe",
            profile_url="https://example.com/johndoe",
            display_name="John Doe",
            verified=True,
            followers=5000,
            bio="Software engineer"
        )

        accounts = await platform_service.get_accounts_for_entity(entity_id)
        account = accounts[0]

        assert account["username"] == "johndoe"
        assert account["display_name"] == "John Doe"
        assert account["verified"] is True
        assert account["followers"] == 5000
        assert account["bio"] == "Software engineer"

    @pytest.mark.asyncio
    async def test_link_nonexistent_entity(self, platform_service):
        """Test linking non-existent entity raises error."""
        platform_id = await platform_service.create_platform(name="ErrorTest")

        with pytest.raises(ValueError) as exc_info:
            await platform_service.link_entity_to_platform(
                entity_id="nonexistent",
                platform_id=platform_id,
                username="testuser"
            )
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_link_to_nonexistent_platform(self, platform_service):
        """Test linking to non-existent platform raises error."""
        entity_id = str(uuid4())

        with pytest.raises(ValueError) as exc_info:
            await platform_service.link_entity_to_platform(
                entity_id=entity_id,
                platform_id="nonexistent",
                username="testuser"
            )
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_accounts_for_entity(self, platform_service):
        """Test getting all accounts for an entity."""
        platform1 = await platform_service.create_platform(name="Platform1")
        platform2 = await platform_service.create_platform(name="Platform2")
        entity_id = str(uuid4())

        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform1,
            username="user1"
        )
        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform2,
            username="user2"
        )

        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) == 2
        usernames = [a["username"] for a in accounts]
        assert "user1" in usernames
        assert "user2" in usernames

    @pytest.mark.asyncio
    async def test_get_entities_on_platform(self, platform_service):
        """Test getting all entities on a platform."""
        platform_id = await platform_service.create_platform(name="PopularPlatform")

        entity1 = str(uuid4())
        entity2 = str(uuid4())

        await platform_service.link_entity_to_platform(
            entity_id=entity1,
            platform_id=platform_id,
            username="user1"
        )
        await platform_service.link_entity_to_platform(
            entity_id=entity2,
            platform_id=platform_id,
            username="user2"
        )

        entities = await platform_service.get_entities_on_platform(platform_id)
        assert len(entities) >= 2

    @pytest.mark.asyncio
    async def test_update_account_properties(self, platform_service):
        """Test updating account properties."""
        platform_id = await platform_service.create_platform(name="UpdateAcctTest")
        entity_id = str(uuid4())

        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser",
            followers=100
        )

        await platform_service.update_account_on_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser",
            followers=5000,
            verified=True
        )

        accounts = await platform_service.get_accounts_for_entity(entity_id)
        account = accounts[0]
        assert account["followers"] == 5000
        assert account["verified"] is True

    @pytest.mark.asyncio
    async def test_remove_account(self, platform_service):
        """Test removing an account from a platform."""
        platform_id = await platform_service.create_platform(name="RemoveTest")
        entity_id = str(uuid4())

        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="removeuser"
        )

        # Verify account exists
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) > 0

        # Remove account
        result = await platform_service.remove_account_from_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="removeuser"
        )

        assert result is True

        # Verify account is gone
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple operations."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, platform_service):
        """Test complete workflow: create platform, link entity, update, remove."""
        # Create platform
        platform_id = await platform_service.create_platform(
            name="CompleteTest",
            category="social_media",
            color="#FF0000",
            icon_class="fa-test"
        )

        # Create entity
        entity_id = str(uuid4())

        # Link to platform
        await platform_service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser",
            followers=100
        )

        # Get accounts
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) == 1

        # Update account
        await platform_service.update_account_on_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser",
            followers=5000
        )

        # Verify update
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert accounts[0]["followers"] == 5000

        # Remove account
        await platform_service.remove_account_from_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username="testuser"
        )

        # Verify removal
        accounts = await platform_service.get_accounts_for_entity(entity_id)
        assert len(accounts) == 0

        # Delete platform
        await platform_service.delete_platform(platform_id)

        # Verify deletion
        platform = await platform_service.get_platform(platform_id)
        assert platform is None


# =============================================================================
# SEEDING TESTS
# =============================================================================


class TestPlatformSeeding:
    """Tests for platform seeding functionality."""

    @pytest.mark.asyncio
    async def test_major_platforms_seeded(self, neo4j_service):
        """Test that major platforms are seeded on startup."""
        await neo4j_service.ensure_platforms_seeded()

        platforms = await neo4j_service.list_platforms()

        # Check for some expected platforms
        names = [p["name"] for p in platforms]

        expected = ["Facebook", "Twitter/X", "Instagram", "LinkedIn", "Reddit"]
        for name in expected:
            assert name in names, f"{name} not in seeded platforms"

    @pytest.mark.asyncio
    async def test_platform_categories(self, neo4j_service):
        """Test that seeded platforms have correct categories."""
        await neo4j_service.ensure_platforms_seeded()

        platforms = await neo4j_service.list_platforms()

        # Verify categories are set
        for platform in platforms:
            assert "category" in platform
            assert platform["category"] in [
                "social_media",
                "professional",
                "forum",
                "messaging",
                "video",
                "blogging",
                "other"
            ]

    @pytest.mark.asyncio
    async def test_idempotent_seeding(self, neo4j_service):
        """Test that seeding is idempotent."""
        await neo4j_service.ensure_platforms_seeded()
        count1 = len(await neo4j_service.list_platforms())

        await neo4j_service.ensure_platforms_seeded()
        count2 = len(await neo4j_service.list_platforms())

        # Count should not increase on second seed
        assert count1 == count2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
