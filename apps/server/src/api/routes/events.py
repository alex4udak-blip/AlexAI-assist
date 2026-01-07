"""Event endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.websocket import broadcast_event
from src.db.models import Device, Event

router = APIRouter()


class EventCreate(BaseModel):
    """Event creation schema."""

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Device identifier",
    )
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of event (e.g., app_focus, window_change)",
    )
    timestamp: datetime = Field(
        ...,
        description="Event timestamp",
    )
    app_name: str | None = Field(
        default=None,
        max_length=255,
        description="Application name",
    )
    window_title: str | None = Field(
        default=None,
        max_length=500,
        description="Window title",
    )
    url: str | None = Field(
        default=None,
        max_length=2000,
        description="URL if applicable",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event data",
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        description="Event category",
    )


class EventBatch(BaseModel):
    """Batch of events to create."""

    events: list[EventCreate] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of events to create",
    )


class EventResponse(BaseModel):
    """Event response schema."""

    id: UUID
    device_id: str
    event_type: str
    timestamp: datetime
    app_name: str | None
    window_title: str | None
    url: str | None
    data: dict[str, Any]
    category: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=dict[str, int])
async def create_events(
    batch: EventBatch,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    """Receive events from collector."""
    # Ensure device exists
    device_ids = {e.device_id for e in batch.events}
    for device_id in device_ids:
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            device = Device(
                id=device_id,
                name=f"Device {device_id[:8]}",
                os="unknown",
            )
            db.add(device)

        device.last_seen_at = datetime.utcnow()

    # Create events
    for event_data in batch.events:
        event = Event(
            device_id=event_data.device_id,
            event_type=event_data.event_type,
            timestamp=event_data.timestamp,
            app_name=event_data.app_name,
            window_title=event_data.window_title,
            url=event_data.url,
            data=event_data.data,
            category=event_data.category,
        )
        db.add(event)

    await db.commit()

    # Broadcast new events to WebSocket clients
    await broadcast_event("events_created", {
        "count": len(batch.events),
        "device_ids": list(device_ids),
    })

    return {"created": len(batch.events)}


@router.get("", response_model=list[EventResponse])
async def get_events(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    event_type: str | None = Query(
        default=None,
        max_length=100,
        description="Filter by event type",
    ),
    category: str | None = Query(
        default=None,
        max_length=100,
        description="Filter by category",
    ),
    start: datetime | None = Query(
        default=None,
        description="Start datetime for filtering",
    ),
    end: datetime | None = Query(
        default=None,
        description="End datetime for filtering",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of events to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[Event]:
    """Query events with filters."""
    query = select(Event).order_by(Event.timestamp.desc()).limit(limit).offset(offset)

    if device_id:
        query = query.where(Event.device_id == device_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if category:
        query = query.where(Event.category == category)
    if start:
        query = query.where(Event.timestamp >= start)
    if end:
        query = query.where(Event.timestamp <= end)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/timeline", response_model=list[EventResponse])
async def get_timeline(
    device_id: str | None = Query(
        default=None,
        max_length=255,
        description="Filter by device ID",
    ),
    hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Number of hours to look back",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[Event]:
    """Get activity timeline for recent hours."""
    from datetime import timedelta

    start = datetime.utcnow() - timedelta(hours=hours)
    query = (
        select(Event)
        .where(Event.timestamp >= start)
        .order_by(Event.timestamp.desc())
        .limit(2000)
    )

    if device_id:
        query = query.where(Event.device_id == device_id)

    result = await db.execute(query)
    return list(result.scalars().all())
