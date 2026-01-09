"""User settings endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.config import settings as app_settings
from src.db.models.user_settings import UserSettings
from src.services.cleanup import CleanupService

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


class CleanupRequest(BaseModel):
    """Cleanup request schema."""

    retention_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Number of days to retain data. If not specified, uses default from config.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, only count records without deleting them.",
    )


class CleanupResponse(BaseModel):
    """Cleanup response schema."""

    retention_days: int
    cutoff_date: str
    dry_run: bool
    tables: dict[str, Any]
    total_deleted: int | None = None
    total_would_delete: int | None = None


class StorageStatsResponse(BaseModel):
    """Storage statistics response schema."""

    tables: dict[str, Any]
    total_records: int


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_data(
    request: CleanupRequest,
    db: AsyncSession = Depends(get_db_session),
) -> CleanupResponse:
    """Clean up data older than the retention period.

    This endpoint deletes events, sessions, chat messages, and audit logs
    that are older than the specified retention period.
    """
    retention_days = request.retention_days or app_settings.retention_days

    cleanup_service = CleanupService(db)
    result = await cleanup_service.cleanup(
        retention_days=retention_days,
        dry_run=request.dry_run,
    )

    return CleanupResponse(**result)


@router.get("/storage-stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    db: AsyncSession = Depends(get_db_session),
) -> StorageStatsResponse:
    """Get storage statistics for all tables.

    Returns record counts and date ranges for each table.
    """
    cleanup_service = CleanupService(db)
    result = await cleanup_service.get_storage_stats()

    return StorageStatsResponse(**result)
