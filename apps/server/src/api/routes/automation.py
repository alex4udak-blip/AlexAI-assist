"""Automation API endpoints for device control."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.api.middleware import validate_websocket_auth
from src.core.logging import get_logger, log_error
from src.core.websocket import broadcast_device_update, broadcast_command_result
from src.db.models.audit_log import AuditLog

router = APIRouter()
logger = get_logger(__name__)

# In-memory storage for automation state
connected_devices: dict[str, WebSocket] = {}
device_statuses: dict[str, dict[str, Any]] = {}
pending_commands: dict[str, dict[str, Any]] = {}
command_results: dict[str, dict[str, Any]] = {}
screenshot_history: dict[str, list[dict[str, Any]]] = {}  # device_id -> list of screenshots


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def create_audit_log(
    db: AsyncSession,
    action_type: str,
    actor: str,
    result: str,
    device_id: str | None = None,
    command_type: str | None = None,
    command_params: dict[str, Any] | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
    ip_address: str | None = None,
) -> None:
    """Create an audit log entry."""
    try:
        audit_log = AuditLog(
            timestamp=utc_now(),
            action_type=action_type,
            actor=actor,
            device_id=device_id,
            command_type=command_type,
            command_params=command_params,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            ip_address=ip_address,
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        log_error(logger, "Failed to create audit log", error=e)
        await db.rollback()


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


def translate_command_to_task(command_id: str, command_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Translate web command format to desktop AutomationTask format.

    The desktop expects tasks in the format:
    {
        "id": "...",
        "priority": "Normal",
        "command": {
            "type": "Screenshot",
            "params": { "save_path": null }
        },
        "created_at": "..."
    }
    """
    # Map command types to desktop TaskCommand format
    command_mapping: dict[str, dict[str, Any]] = {
        "click": {
            "type": "Click",
            "params": {
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "button": params.get("button", "left"),
            },
        },
        "type": {
            "type": "Type",
            "params": {
                "text": params.get("text", ""),
            },
        },
        "hotkey": {
            "type": "Hotkey",
            "params": {
                "modifiers": params.get("modifiers", []),
                "key": params.get("key", ""),
            },
        },
        "screenshot": {
            "type": "Screenshot",
            "params": {
                "save_path": params.get("save_path"),
            },
        },
        "navigate": {
            "type": "BrowserNavigate",
            "params": {
                "browser": params.get("browser", "chrome"),
                "url": params.get("url", ""),
            },
        },
        "get_url": {
            "type": "BrowserGetUrl",
            "params": {
                "browser": params.get("browser", "chrome"),
            },
        },
        "wait": {
            "type": "Wait",
            "params": {
                "milliseconds": params.get("milliseconds", 1000),
            },
        },
        "ocr": {
            "type": "Custom",
            "params": {
                "name": "ocr",
                "params": params,
            },
        },
    }

    # Get the translated command or use Custom for unknown types
    translated = command_mapping.get(
        command_type.lower(),
        {
            "type": "Custom",
            "params": {
                "name": command_type,
                "params": params,
            },
        },
    )

    return {
        "id": command_id,
        "priority": "Normal",
        "command": translated,
        "created_at": utc_now().isoformat() + "Z",
    }


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
    now = utc_now()
    device_statuses[device_id] = {
        "connected": True,
        "last_seen_at": now,
        "last_sync_at": now,
        "status": "idle",
    }

    logger.info(
        "Device connected to automation WebSocket",
        extra={"device_id": device_id, "total_devices": len(connected_devices)},
    )

    # Broadcast device connection to web clients
    await broadcast_device_update(device_id, device_statuses[device_id])

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "status_update":
                # Update device status
                now = utc_now()
                device_statuses[device_id].update(
                    {
                        "last_seen_at": now,
                        "last_sync_at": now,
                        "status": data.get("status", "idle"),
                        **data.get("data", {}),
                    }
                )
                logger.debug(
                    "Device status updated",
                    extra={"device_id": device_id, "status": data.get("status")},
                )
                # Broadcast status update to web clients
                await broadcast_device_update(device_id, device_statuses[device_id])

            elif message_type == "command_result":
                # Store command result
                command_id = data.get("command_id")
                if command_id:
                    result_data = data.get("result", {})
                    command_results[command_id] = {
                        "success": data.get("success", False),
                        "result": result_data,
                        "error": data.get("error"),
                        "screenshot_url": data.get("screenshot_url"),
                        "duration_ms": data.get("duration_ms"),
                        "completed_at": utc_now(),
                    }

                    # Store screenshot in history if present
                    if isinstance(result_data, dict) and result_data.get("screenshot"):
                        if device_id not in screenshot_history:
                            screenshot_history[device_id] = []
                        screenshot_history[device_id].insert(0, {
                            "screenshot": result_data["screenshot"],
                            "timestamp": utc_now().isoformat() + "Z",
                            "command_id": command_id,
                        })
                        # Keep only last 10 screenshots
                        screenshot_history[device_id] = screenshot_history[device_id][:10]

                    logger.info(
                        "Command result received",
                        extra={
                            "device_id": device_id,
                            "command_id": command_id,
                            "success": data.get("success"),
                        },
                    )

                    # Broadcast command result to web clients
                    await broadcast_command_result(command_id, device_id, command_results[command_id])

            elif message_type == "task_result":
                # Store task result from desktop (WsMessage::TaskResult format)
                # Desktop sends: {"type": "task_result", "result": {"task_id": "...", "success": bool, "error": Option<String>, "output": Option<Value>}}
                result_data = data.get("result", {})
                task_id = result_data.get("task_id")
                if task_id:
                    output_data = result_data.get("output")
                    command_results[task_id] = {
                        "success": result_data.get("success", False),
                        "result": output_data,
                        "error": result_data.get("error"),
                        "screenshot_url": result_data.get("screenshot_url"),
                        "duration_ms": result_data.get("duration_ms"),
                        "completed_at": utc_now(),
                    }

                    # Store screenshot in history if present
                    if isinstance(output_data, dict) and output_data.get("screenshot"):
                        if device_id not in screenshot_history:
                            screenshot_history[device_id] = []
                        screenshot_history[device_id].insert(0, {
                            "screenshot": output_data["screenshot"],
                            "timestamp": utc_now().isoformat() + "Z",
                            "command_id": task_id,
                        })
                        # Keep only last 10 screenshots
                        screenshot_history[device_id] = screenshot_history[device_id][:10]

                    logger.info(
                        "Task result received from desktop",
                        extra={
                            "device_id": device_id,
                            "task_id": task_id,
                            "success": result_data.get("success"),
                        },
                    )

                    # Broadcast task result to web clients
                    await broadcast_command_result(task_id, device_id, command_results[task_id])

            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
                device_statuses[device_id]["last_seen_at"] = utc_now()

    except WebSocketDisconnect:
        connected_devices.pop(device_id, None)
        if device_id in device_statuses:
            device_statuses[device_id]["connected"] = False
            # Broadcast device disconnection to web clients
            await broadcast_device_update(device_id, device_statuses[device_id])
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
            # Broadcast device disconnection to web clients
            await broadcast_device_update(device_id, device_statuses[device_id])


@router.post("/command/{device_id}", response_model=CommandResponse)
async def send_command(
    device_id: str,
    command: CommandRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Send command to device."""
    # Check if device is connected
    if device_id not in connected_devices:
        await create_audit_log(
            db=db,
            action_type="command_executed",
            actor="user",
            result="failure",
            device_id=device_id,
            command_type=command.command_type,
            command_params=command.params,
            error_message=f"Device {device_id} not connected",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not connected",
        )

    # Generate command ID
    command_id = str(uuid4())
    start_time = utc_now()

    # Store pending command
    pending_commands[command_id] = {
        "device_id": device_id,
        "command_type": command.command_type,
        "params": command.params,
        "timeout": command.timeout,
        "requires_confirmation": command.requires_confirmation,
        "status": "pending",
        "created_at": start_time,
    }

    # Send command to device as AutomationTask format
    try:
        websocket = connected_devices[device_id]

        # Translate web command to desktop task format
        task = translate_command_to_task(command_id, command.command_type, command.params)

        # Send as automation_task message type (matches desktop WsMessage::AutomationTask)
        await websocket.send_json(
            {
                "type": "automation_task",
                "task": task,
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

        # Log to audit trail
        await create_audit_log(
            db=db,
            action_type="command_executed",
            actor="user",
            result="pending",
            device_id=device_id,
            command_type=command.command_type,
            command_params=command.params,
            ip_address=request.client.host if request.client else None,
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

        # Log failure to audit trail
        duration = int((utc_now() - start_time).total_seconds() * 1000)
        await create_audit_log(
            db=db,
            action_type="command_executed",
            actor="user",
            result="failure",
            device_id=device_id,
            command_type=command.command_type,
            command_params=command.params,
            error_message=str(e),
            duration_ms=duration,
            ip_address=request.client.host if request.client else None,
        )

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


class SyncStatus(BaseModel):
    """Sync status schema."""

    last_sync_at: datetime | None = Field(default=None, description="Last sync timestamp")
    events_since_sync: int = Field(default=0, description="Number of events since last sync")
    sync_status: str = Field(..., description="Sync status (connected/disconnected)")


@router.get("/devices/{device_id}/sync-status", response_model=SyncStatus)
async def get_sync_status(device_id: str) -> dict[str, Any]:
    """Get device sync status."""
    status = device_statuses.get(device_id)
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    last_sync = status.get("last_sync_at")
    connected = status.get("connected", False)

    # Count pending commands for this device as events since sync
    events_since_sync = sum(
        1 for cmd in pending_commands.values()
        if cmd.get("device_id") == device_id
    )

    return {
        "last_sync_at": last_sync,
        "events_since_sync": events_since_sync,
        "sync_status": "connected" if connected else "disconnected",
    }


class Screenshot(BaseModel):
    """Screenshot schema."""

    screenshot: str = Field(..., description="Base64 encoded screenshot")
    timestamp: str = Field(..., description="Screenshot timestamp")
    command_id: str = Field(..., description="Associated command ID")


@router.get("/devices/{device_id}/screenshots", response_model=list[Screenshot])
async def get_screenshot_history(device_id: str) -> list[dict[str, Any]]:
    """Get screenshot history for a device."""
    if device_id not in device_statuses:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    return screenshot_history.get(device_id, [])


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


class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: str = Field(..., description="Audit log ID")
    timestamp: datetime = Field(..., description="Action timestamp")
    action_type: str = Field(..., description="Type of action")
    actor: str = Field(..., description="Who initiated the action")
    device_id: str | None = Field(default=None, description="Device ID")
    command_type: str | None = Field(default=None, description="Command type")
    command_params: dict[str, Any] | None = Field(default=None, description="Command parameters")
    result: str = Field(..., description="Result status")
    error_message: str | None = Field(default=None, description="Error message if failed")
    duration_ms: int | None = Field(default=None, description="Execution duration")
    ip_address: str | None = Field(default=None, description="IP address")


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    device_id: str | None = Query(default=None, description="Filter by device ID"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
    actor: str | None = Query(default=None, description="Filter by actor"),
    result: str | None = Query(default=None, description="Filter by result status"),
    start_date: datetime | None = Query(default=None, description="Start date filter"),
    end_date: datetime | None = Query(default=None, description="End date filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get audit logs with optional filters."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    # Apply filters
    if device_id:
        query = query.where(AuditLog.device_id == device_id)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if actor:
        query = query.where(AuditLog.actor == actor)
    if result:
        query = query.where(AuditLog.result == result)
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result_data = await db.execute(query)
    logs = result_data.scalars().all()

    return [
        {
            "id": str(log.id),
            "timestamp": log.timestamp,
            "action_type": log.action_type,
            "actor": log.actor,
            "device_id": log.device_id,
            "command_type": log.command_type,
            "command_params": log.command_params,
            "result": log.result,
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
            "ip_address": log.ip_address,
        }
        for log in logs
    ]
