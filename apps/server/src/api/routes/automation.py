"""Automation API endpoints for device control."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.api.middleware import validate_websocket_auth
from src.core.logging import get_logger, log_error

router = APIRouter()
logger = get_logger(__name__)

# In-memory storage for automation state
connected_devices: dict[str, WebSocket] = {}
device_statuses: dict[str, dict[str, Any]] = {}
pending_commands: dict[str, dict[str, Any]] = {}
command_results: dict[str, dict[str, Any]] = {}


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CommandRequest(BaseModel):
    """Command request schema."""

    command_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of command (e.g., click, type, screenshot)",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Command parameters",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Command timeout in seconds",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether command requires user confirmation",
    )


class CommandResponse(BaseModel):
    """Command response schema."""

    command_id: str = Field(..., description="Unique command ID")
    status: str = Field(..., description="Command status (pending, executing, completed, failed, timeout)")
    device_id: str = Field(..., description="Target device ID")
    created_at: datetime = Field(..., description="Command creation timestamp")


class CommandResult(BaseModel):
    """Command result schema."""

    success: bool = Field(..., description="Whether command succeeded")
    result: Any = Field(default=None, description="Command result data")
    error: str | None = Field(default=None, description="Error message if failed")
    screenshot_url: str | None = Field(default=None, description="Screenshot URL if captured")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")


class DeviceStatus(BaseModel):
    """Device status schema."""

    device_id: str = Field(..., description="Device ID")
    connected: bool = Field(..., description="Whether device is connected")
    last_seen_at: datetime | None = Field(default=None, description="Last seen timestamp")
    status_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional status data",
    )


class TaskRequest(BaseModel):
    """Compound task request schema."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language task description",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the task",
    )


@router.websocket("/ws/automation/{device_id}")
async def automation_websocket(websocket: WebSocket, device_id: str) -> None:
    """WebSocket endpoint for real-time device control."""
    # Validate authentication
    if not await validate_websocket_auth(websocket):
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning(
            "Automation WebSocket rejected: unauthorized",
            extra={"device_id": device_id},
        )
        return

    await websocket.accept()
    connected_devices[device_id] = websocket
    device_statuses[device_id] = {
        "connected": True,
        "last_seen_at": utc_now(),
        "status": "idle",
    }

    logger.info(
        "Device connected to automation WebSocket",
        extra={"device_id": device_id, "total_devices": len(connected_devices)},
    )

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "status_update":
                # Update device status
                device_statuses[device_id].update(
                    {
                        "last_seen_at": utc_now(),
                        "status": data.get("status", "idle"),
                        **data.get("data", {}),
                    }
                )
                logger.debug(
                    "Device status updated",
                    extra={"device_id": device_id, "status": data.get("status")},
                )

            elif message_type == "command_result":
                # Store command result
                command_id = data.get("command_id")
                if command_id:
                    command_results[command_id] = {
                        "success": data.get("success", False),
                        "result": data.get("result"),
                        "error": data.get("error"),
                        "screenshot_url": data.get("screenshot_url"),
                        "duration_ms": data.get("duration_ms"),
                        "completed_at": utc_now(),
                    }
                    logger.info(
                        "Command result received",
                        extra={
                            "device_id": device_id,
                            "command_id": command_id,
                            "success": data.get("success"),
                        },
                    )

            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
                device_statuses[device_id]["last_seen_at"] = utc_now()

    except WebSocketDisconnect:
        connected_devices.pop(device_id, None)
        if device_id in device_statuses:
            device_statuses[device_id]["connected"] = False
        logger.info(
            "Device disconnected from automation WebSocket",
            extra={"device_id": device_id},
        )
    except Exception as e:
        log_error(
            logger,
            "Automation WebSocket error",
            error=e,
            extra={"device_id": device_id},
        )
        connected_devices.pop(device_id, None)
        if device_id in device_statuses:
            device_statuses[device_id]["connected"] = False


@router.post("/command/{device_id}", response_model=CommandResponse)
async def send_command(
    device_id: str,
    command: CommandRequest,
) -> dict[str, Any]:
    """Send command to device."""
    # Check if device is connected
    if device_id not in connected_devices:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not connected",
        )

    # Generate command ID
    command_id = str(uuid4())

    # Store pending command
    pending_commands[command_id] = {
        "device_id": device_id,
        "command_type": command.command_type,
        "params": command.params,
        "timeout": command.timeout,
        "requires_confirmation": command.requires_confirmation,
        "status": "pending",
        "created_at": utc_now(),
    }

    # Send command to device
    try:
        websocket = connected_devices[device_id]
        await websocket.send_json(
            {
                "type": "command",
                "command_id": command_id,
                "command_type": command.command_type,
                "params": command.params,
                "requires_confirmation": command.requires_confirmation,
            }
        )

        logger.info(
            "Command sent to device",
            extra={
                "device_id": device_id,
                "command_id": command_id,
                "command_type": command.command_type,
            },
        )

        return {
            "command_id": command_id,
            "status": "pending",
            "device_id": device_id,
            "created_at": pending_commands[command_id]["created_at"],
        }

    except Exception as e:
        # Clean up pending command
        pending_commands.pop(command_id, None)
        log_error(
            logger,
            "Failed to send command to device",
            error=e,
            extra={"device_id": device_id, "command_id": command_id},
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to send command to device",
        )


@router.get("/result/{command_id}", response_model=CommandResult)
async def get_command_result(
    command_id: str,
    timeout: int = Query(default=30, ge=1, le=300, description="Timeout in seconds"),
) -> dict[str, Any]:
    """Get command result with timeout."""
    # Wait for result with timeout
    start_time = utc_now()
    while (utc_now() - start_time).total_seconds() < timeout:
        if command_id in command_results:
            result = command_results.pop(command_id)
            pending_commands.pop(command_id, None)
            return result

        await asyncio.sleep(0.5)

    # Timeout
    pending_commands.pop(command_id, None)
    raise HTTPException(
        status_code=408,
        detail="Command execution timeout",
    )


@router.get("/status/{device_id}", response_model=DeviceStatus)
async def get_device_status(device_id: str) -> dict[str, Any]:
    """Get device status."""
    status = device_statuses.get(device_id)
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    return {
        "device_id": device_id,
        "connected": status.get("connected", False),
        "last_seen_at": status.get("last_seen_at"),
        "status_data": {
            k: v
            for k, v in status.items()
            if k not in ("connected", "last_seen_at")
        },
    }


@router.get("/devices", response_model=list[DeviceStatus])
async def list_devices() -> list[dict[str, Any]]:
    """List all connected devices."""
    return [
        {
            "device_id": device_id,
            "connected": status.get("connected", False),
            "last_seen_at": status.get("last_seen_at"),
            "status_data": {
                k: v
                for k, v in status.items()
                if k not in ("connected", "last_seen_at")
            },
        }
        for device_id, status in device_statuses.items()
    ]


@router.post("/results")
async def save_command_result(
    command_id: str = Query(..., description="Command ID"),
    result: CommandResult = ...,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Save command result from device (alternative to WebSocket)."""
    command_results[command_id] = {
        "success": result.success,
        "result": result.result,
        "error": result.error,
        "screenshot_url": result.screenshot_url,
        "duration_ms": result.duration_ms,
        "completed_at": utc_now(),
    }

    logger.info(
        "Command result saved via REST",
        extra={"command_id": command_id, "success": result.success},
    )

    return {"message": "Result saved"}


@router.post("/status")
async def save_device_status(
    device_id: str = Query(..., description="Device ID"),
    status: DeviceStatus = ...,
) -> dict[str, str]:
    """Save device status (alternative to WebSocket)."""
    device_statuses[device_id] = {
        "connected": status.connected,
        "last_seen_at": status.last_seen_at or utc_now(),
        **status.status_data,
    }

    logger.debug(
        "Device status saved via REST",
        extra={"device_id": device_id},
    )

    return {"message": "Status saved"}


@router.post("/task/{device_id}")
async def execute_task(
    device_id: str,
    task: TaskRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute compound task using AI to break down into steps."""
    # Check if device is connected
    if device_id not in connected_devices:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not connected",
        )

    # TODO: Use AI router to break down task into commands
    # For now, return a placeholder response
    task_id = str(uuid4())

    logger.info(
        "Task execution requested",
        extra={
            "device_id": device_id,
            "task_id": task_id,
            "description": task.description,
        },
    )

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task execution will be implemented with AI router",
        "description": task.description,
    }
