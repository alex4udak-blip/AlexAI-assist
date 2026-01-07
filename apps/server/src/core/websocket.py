"""WebSocket management module."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

# WebSocket connections store
active_connections: set["WebSocket"] = set()


async def broadcast_event(event_type: str, data: dict) -> None:
    """Broadcast event to all connected WebSocket clients."""
    if not active_connections:
        return

    message = {"type": event_type, "data": data}
    disconnected = set()

    for websocket in active_connections:
        try:
            await websocket.send_json(message)
        except Exception:
            disconnected.add(websocket)

    # Clean up disconnected clients
    for ws in disconnected:
        active_connections.discard(ws)
