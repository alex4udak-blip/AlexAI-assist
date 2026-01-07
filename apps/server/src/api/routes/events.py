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

    device_id: str
    event_type: str
    timestamp: datetime
    app_name: str | None = None
    window_title: str | None = None
    url: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    category: str | None = None


class EventBatch(BaseModel):
    """Batch of events to create."""

    events: list[EventCreate]


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
    device_id: str | None = None,
    event_type: str | None = None,
    category: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
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
    device_id: str | None = None,
    hours: int = Query(24, le=168),
    db: AsyncSession = Depends(get_db_session),
) -> list[Event]:
    """Get activity timeline for recent hours."""
    from datetime import timedelta

    start = datetime.utcnow() - timedelta(hours=hours)
    query = (
        select(Event)
        .where(Event.timestamp >= start)
        .order_by(Event.timestamp.desc())
        .limit(500)
    )

    if device_id:
        query = query.where(Event.device_id == device_id)

    result = await db.execute(query)
    return list(result.scalars().all())
