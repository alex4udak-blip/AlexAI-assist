"""User settings endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models.user_settings import UserSettings

router = APIRouter()


class SettingsRequest(BaseModel):
    """Settings update request."""

    device_id: str
    settings: dict[str, Any]


class SettingsResponse(BaseModel):
    """Settings response."""

    device_id: str
    settings: dict[str, Any]


@router.get("", response_model=SettingsResponse)
async def get_settings(
    device_id: str = Query(
        ...,
        max_length=255,
        description="Device ID",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Get user settings for a device."""
    query = select(UserSettings).where(UserSettings.device_id == device_id)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()

    if not user_settings:
        # Return empty settings if not found
        return SettingsResponse(device_id=device_id, settings={})

    return SettingsResponse(
        device_id=user_settings.device_id,
        settings=user_settings.settings,
    )


@router.post("", response_model=SettingsResponse)
async def save_settings(
    request: SettingsRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SettingsResponse:
    """Save user settings for a device."""
    # Check if settings already exist
    query = select(UserSettings).where(UserSettings.device_id == request.device_id)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()

    if user_settings:
        # Update existing settings
        user_settings.settings = request.settings
    else:
        # Create new settings
        user_settings = UserSettings(
            device_id=request.device_id,
            settings=request.settings,
        )
        db.add(user_settings)

    await db.commit()
    await db.refresh(user_settings)

    return SettingsResponse(
        device_id=user_settings.device_id,
        settings=user_settings.settings,
    )
