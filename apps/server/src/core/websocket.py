"""WebSocket management module."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)

# WebSocket connections store
active_connections: set["WebSocket"] = set()


async def broadcast_event(event_type: str, data: dict[str, Any]) -> None:
    """Broadcast event to all connected WebSocket clients."""
    if not active_connections:
        return

    message = {"type": event_type, "data": data}
    disconnected = set()

    for websocket in active_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(
                "WebSocket broadcast failed, marking client for removal",
                extra={"event_type": event_type, "error": str(e)},
            )
            disconnected.add(websocket)

    # Clean up disconnected clients
    for ws in disconnected:
        active_connections.discard(ws)


async def broadcast_device_update(device_id: str, status: dict[str, Any]) -> None:
    """Broadcast device status update to all connected clients."""
    await broadcast_event("device_updated", {
        "device_id": device_id,
        "status": status,
    })


async def broadcast_command_result(command_id: str, device_id: str, result: dict[str, Any]) -> None:
    """Broadcast command execution result to all connected clients."""
    await broadcast_event("command_result", {
        "command_id": command_id,
        "device_id": device_id,
        "result": result,
    })


async def broadcast_events_batch(events: list[dict[str, Any]], device_ids: list[str]) -> None:
    """Broadcast new events batch to all connected clients."""
    await broadcast_event("events_created", {
        "count": len(events),
        "device_ids": device_ids,
        "events": events[:10],  # Send first 10 events for preview
    })


async def broadcast_suggestion(suggestion: dict[str, Any]) -> None:
    """Broadcast new automation suggestion to all connected clients."""
    await broadcast_event("suggestion_created", {
        "id": suggestion.get("id"),
        "title": suggestion.get("title"),
        "description": suggestion.get("description"),
        "confidence": suggestion.get("confidence"),
        "impact": suggestion.get("impact"),
        "pattern_type": suggestion.get("agent_type"),
    })
