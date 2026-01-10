"""Event endpoints."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.cache import get_cache
from src.core.websocket import broadcast_events_batch
from src.db.models import Device, Event
from src.services.session_tracker import SessionTracker

# Cache TTL for timeline endpoint (in seconds)
TIMELINE_CACHE_TTL = 10


def normalize_datetime(dt: datetime | None) -> datetime | None:
    """Convert any datetime to UTC naive datetime for PostgreSQL.

    This handles both timezone-aware and naive datetimes,
    converting everything to UTC without timezone info.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC and remove timezone info
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt

router = APIRouter()
session_tracker = SessionTracker()


class EventCreate(BaseModel):
    """Event creation schema."""

    event_id: str | None = Field(
        default=None,
        max_length=255,
        description="Client-generated event ID for deduplication",
    )
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


@router.post("")
async def create_events(
    batch: EventBatch,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
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

        device.last_seen_at = datetime.now(UTC).replace(tzinfo=None)

    # Create events with deduplication
    session_events = []
    acked_event_ids = []
    skipped_count = 0
    created_events: list[Event] = []  # Track created events for batch processing

    for event_data in batch.events:
        # Check for duplicates if event_id is provided
        if event_data.event_id:
            result = await db.execute(
                select(Event).where(Event.event_id == event_data.event_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Event already exists, skip but acknowledge
                acked_event_ids.append(event_data.event_id)
                skipped_count += 1
                continue

        event = Event(
            event_id=event_data.event_id,
            device_id=event_data.device_id,
            event_type=event_data.event_type,
            timestamp=normalize_datetime(event_data.timestamp),
            app_name=event_data.app_name,
            window_title=event_data.window_title,
            url=event_data.url,
            data=event_data.data,
            category=event_data.category,
        )
        db.add(event)
        created_events.append(event)  # Track for batch fetch after commit

        # Track acknowledged event ID
        if event_data.event_id:
            acked_event_ids.append(event_data.event_id)

    await db.commit()

    # Process events for session tracking
    # Fetch all created events in a single batch query (avoids N+1 problem)
    if created_events:
        event_ids = [e.id for e in created_events]
        events_result = await db.execute(
            select(Event).where(Event.id.in_(event_ids))
        )
        fetched_events: list[Event] = list(events_result.scalars().all())
        fetched_events_map: dict[UUID, Event] = {e.id: e for e in fetched_events}

        # Process events in timestamp order
        sorted_created = sorted(
            created_events,
            key=lambda e: e.timestamp or datetime.min
        )
        for event in sorted_created:
            fetched_event = fetched_events_map.get(event.id)
            if fetched_event:
                # Process event for session tracking
                session_event = await session_tracker.process_event(fetched_event, db)
                if session_event:
                    session_events.append(session_event)

    # Broadcast new events to WebSocket clients
    # Convert events to dict format for JSON serialization
    events_data = [
        {
            "device_id": e.device_id,
            "event_type": e.event_type,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "app_name": e.app_name,
            "window_title": e.window_title,
            "url": e.url,
            "category": e.category,
            "data": e.data,
        }
        for e in batch.events
        if not e.event_id or e.event_id in acked_event_ids
    ]
    await broadcast_events_batch(events_data, list(device_ids))

    # Invalidate timeline cache for affected devices
    cache = get_cache()
    await cache.delete_pattern("timeline:*")

    return {
        "created": len(batch.events) - skipped_count,
        "skipped": skipped_count,
        "acked_event_ids": acked_event_ids,
        "session_events": session_events,
    }


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
    nocache: bool = Query(
        default=False,
        description="Bypass cache for fresh data (use on page navigation)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get activity timeline for recent hours.

    Results are cached for TIMELINE_CACHE_TTL seconds.
    Cache is invalidated when new events are created.
    Use nocache=true query parameter to bypass cache on page navigation.
    """
    from datetime import timedelta

    cache = get_cache()

    # Skip cache if nocache parameter is set
    if not nocache:
        # Build cache key based on query parameters
        cache_key = f"timeline:{hours}:{device_id or 'all'}"

        # Try to get from cache
        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            return cached_data

    # Cache miss - fetch from database
    start = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    query = (
        select(Event)
        .where(Event.timestamp >= start)
        .order_by(Event.timestamp.desc())
        .limit(2000)
    )

    if device_id:
        query = query.where(Event.device_id == device_id)

    result = await db.execute(query)
    events = list(result.scalars().all())

    # Convert to serializable format for caching
    events_data = [
        {
            "id": str(e.id),
            "device_id": e.device_id,
            "event_type": e.event_type,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "app_name": e.app_name,
            "window_title": e.window_title,
            "url": e.url,
            "data": e.data,
            "category": e.category,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]

    # Store in cache (only if not bypassing cache)
    if not nocache:
        cache_key = f"timeline:{hours}:{device_id or 'all'}"
        await cache.set(cache_key, events_data, TIMELINE_CACHE_TTL)

    return events_data
