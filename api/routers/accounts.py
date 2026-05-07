"""
Accounts Router for Basset Hound (Phase 48: Dynamic Entity Architecture).

Provides REST API endpoints for managing HAS_ACCOUNT_ON relationships
between entities and platforms.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler, get_current_project
from ..services.neo4j_service import AsyncNeo4jService
from ..services.platform_service import PlatformService

router = APIRouter(
    prefix="/projects/{project_safe_name}/entities/{entity_id}/accounts",
    tags=["accounts"],
    responses={
        404: {"description": "Entity, platform, or project not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class AccountCreate(BaseModel):
    """Request model for creating an account (linking to platform)."""
    platform_id: str = Field(..., description="Platform entity ID")
    username: str = Field(..., description="Account username/handle")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    display_name: Optional[str] = Field(None, description="Display name")
    verified: Optional[bool] = Field(False, description="Account verified status")
    followers: Optional[int] = Field(None, description="Number of followers")
    bio: Optional[str] = Field(None, description="Account bio/description")
    last_active: Optional[str] = Field(None, description="Last active timestamp")
    password_ref: Optional[str] = Field(None, description="Password reference")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform_id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "johndoe",
                "profile_url": "https://twitter.com/johndoe",
                "display_name": "John Doe",
                "verified": True,
                "followers": 1234
            }
        }
    )


class AccountUpdate(BaseModel):
    """Request model for updating account properties."""
    username: Optional[str] = Field(None, description="Account username")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    display_name: Optional[str] = Field(None, description="Display name")
    verified: Optional[bool] = Field(None, description="Verified status")
    followers: Optional[int] = Field(None, description="Number of followers")
    bio: Optional[str] = Field(None, description="Bio/description")
    last_active: Optional[str] = Field(None, description="Last active timestamp")
    password_ref: Optional[str] = Field(None, description="Password reference")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "followers": 2000,
                "verified": True
            }
        }
    )


class PlatformInfo(BaseModel):
    """Platform information in account response."""
    id: str
    name: str
    category: str
    icon_class: Optional[str] = None
    color: Optional[str] = None
    profile_url_template: Optional[str] = None


class AccountResponse(BaseModel):
    """Response model for account."""
    username: str = Field(..., description="Account username")
    platform_id: str = Field(..., description="Platform entity ID")
    platform: PlatformInfo = Field(..., description="Platform information")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    display_name: Optional[str] = Field(None, description="Display name")
    verified: Optional[bool] = Field(None, description="Verified status")
    followers: Optional[int] = Field(None, description="Number of followers")
    bio: Optional[str] = Field(None, description="Bio")
    last_active: Optional[str] = Field(None, description="Last active timestamp")
    created_at: Optional[str] = Field(None, description="Account created timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "platform_id": "550e8400-e29b-41d4-a716-446655440000",
                "platform": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Twitter/X",
                    "category": "social_media",
                    "icon_class": "fa-x-twitter",
                    "color": "#000000"
                },
                "profile_url": "https://twitter.com/johndoe",
                "display_name": "John Doe",
                "verified": True,
                "created_at": "2024-05-06T12:00:00"
            }
        }
    )


class AccountListResponse(BaseModel):
    """Response model for account list."""
    accounts: List[AccountResponse] = Field(default_factory=list)
    count: int = Field(0, description="Total number of accounts")


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(True)
    message: Optional[str] = Field(None)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


async def get_platform_service(
    neo4j_handler: AsyncNeo4jService = Depends(get_neo4j_handler),
) -> PlatformService:
    """Get platform service."""
    return PlatformService(neo4j_handler)


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/",
    response_model=AccountListResponse,
    summary="List entity accounts",
    description="Retrieve all platform accounts for a specific entity.",
)
async def list_accounts(
    project_safe_name: str,
    entity_id: str,
    service: PlatformService = Depends(get_platform_service),
    project_id: str = Depends(get_current_project),
) -> AccountListResponse:
    """List all accounts for an entity."""
    try:
        accounts_data = await service.get_accounts_for_entity(entity_id)
        accounts = []

        for account in accounts_data:
            platform = account.pop("platform", {})
            platform_id = platform.get("id")

            account_response = AccountResponse(
                username=account.get("username"),
                platform_id=platform_id,
                platform=PlatformInfo(**platform),
                profile_url=account.get("profile_url"),
                display_name=account.get("display_name"),
                verified=account.get("verified"),
                followers=account.get("followers"),
                bio=account.get("bio"),
                last_active=account.get("last_active"),
                created_at=account.get("created_at"),
            )
            accounts.append(account_response)

        return AccountListResponse(accounts=accounts, count=len(accounts))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing accounts: {str(e)}"
        )


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
    description="Link an entity to a platform (create account).",
)
async def create_account(
    project_safe_name: str,
    entity_id: str,
    data: AccountCreate,
    service: PlatformService = Depends(get_platform_service),
    project_id: str = Depends(get_current_project),
) -> AccountResponse:
    """Create a new account link."""
    try:
        await service.link_entity_to_platform(
            entity_id=entity_id,
            platform_id=data.platform_id,
            username=data.username,
            profile_url=data.profile_url,
            display_name=data.display_name,
            verified=data.verified,
            followers=data.followers,
            bio=data.bio,
            last_active=data.last_active,
            password_ref=data.password_ref,
        )

        # Fetch the created account
        accounts = await service.get_accounts_for_entity(entity_id)
        account = next(
            (a for a in accounts if a.get("username") == data.username),
            None
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account created but could not be retrieved"
            )

        platform = account.pop("platform", {})

        return AccountResponse(
            username=account.get("username"),
            platform_id=data.platform_id,
            platform=PlatformInfo(**platform),
            profile_url=account.get("profile_url"),
            display_name=account.get("display_name"),
            verified=account.get("verified"),
            followers=account.get("followers"),
            bio=account.get("bio"),
            last_active=account.get("last_active"),
            created_at=account.get("created_at"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating account: {str(e)}"
        )


@router.put(
    "/{platform_id}",
    response_model=AccountResponse,
    summary="Update account",
    description="Update properties of an existing account.",
)
async def update_account(
    project_safe_name: str,
    entity_id: str,
    platform_id: str,
    data: AccountUpdate,
    service: PlatformService = Depends(get_platform_service),
    project_id: str = Depends(get_current_project),
) -> AccountResponse:
    """Update an account."""
    try:
        # Get current account to extract username
        accounts = await service.get_accounts_for_entity(entity_id)
        account = next(
            (a for a in accounts if a.get("platform", {}).get("id") == platform_id),
            None
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found for platform {platform_id}"
            )

        current_username = account.get("username")
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if update_data:
            await service.update_account_on_platform(
                entity_id=entity_id,
                platform_id=platform_id,
                username=current_username,
                **update_data,
            )

        # Fetch updated account
        accounts = await service.get_accounts_for_entity(entity_id)
        updated_account = next(
            (a for a in accounts if a.get("platform", {}).get("id") == platform_id),
            None
        )

        if not updated_account:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account updated but could not be retrieved"
            )

        platform = updated_account.pop("platform", {})

        return AccountResponse(
            username=updated_account.get("username"),
            platform_id=platform_id,
            platform=PlatformInfo(**platform),
            profile_url=updated_account.get("profile_url"),
            display_name=updated_account.get("display_name"),
            verified=updated_account.get("verified"),
            followers=updated_account.get("followers"),
            bio=updated_account.get("bio"),
            last_active=updated_account.get("last_active"),
            created_at=updated_account.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating account: {str(e)}"
        )


@router.delete(
    "/{platform_id}",
    response_model=SuccessResponse,
    summary="Delete account",
    description="Remove an entity's account from a platform.",
)
async def delete_account(
    project_safe_name: str,
    entity_id: str,
    platform_id: str,
    service: PlatformService = Depends(get_platform_service),
    project_id: str = Depends(get_current_project),
) -> SuccessResponse:
    """Delete an account."""
    try:
        # Get current account to extract username
        accounts = await service.get_accounts_for_entity(entity_id)
        account = next(
            (a for a in accounts if a.get("platform", {}).get("id") == platform_id),
            None
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found for platform {platform_id}"
            )

        username = account.get("username")

        await service.remove_account_from_platform(
            entity_id=entity_id,
            platform_id=platform_id,
            username=username,
        )

        return SuccessResponse(
            success=True,
            message=f"Account removed from platform {platform_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting account: {str(e)}"
        )
