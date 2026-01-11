"""Automation API endpoints for device control."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.api.middleware import validate_websocket_auth
from src.core.logging import get_logger, log_error
from src.core.websocket import broadcast_command_result, broadcast_device_update
from src.db.models import CommandResult as DBCommandResult
from src.db.models import DeviceStatus as DBDeviceStatus
from src.db.models import Screenshot as DBScreenshot
from src.db.models.audit_log import AuditLog
from src.db.models.device import Device

router = APIRouter()
logger = get_logger(__name__)

# WebSocket connections (runtime state, not persisted)
connected_devices: dict[str, WebSocket] = {}


async def send_suggestion_to_all_devices(suggestion: dict) -> int:
    """Send automation suggestion to all connected devices."""
    sent_count = 0
    disconnected = []

    for device_id, websocket in connected_devices.items():
        try:
            await websocket.send_json({
                "type": "automation_suggestion",
                "suggestion": suggestion,
            })
            sent_count += 1
            logger.info(f"Sent suggestion to device {device_id}")
        except Exception as e:
            logger.warning(f"Failed to send suggestion to {device_id}: {e}")
            disconnected.append(device_id)

    # Clean up disconnected
    for device_id in disconnected:
        connected_devices.pop(device_id, None)

    return sent_count


# Database session for background tasks
_db_session_factory: Any = None


def set_db_session_factory(factory: Any) -> None:
    """Set the database session factory for background operations."""
    global _db_session_factory
    _db_session_factory = factory


async def get_or_create_device(db: AsyncSession, device_id: str) -> Device:
    """Get or create a device record."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        device = Device(
            id=device_id,
            name=f"Device-{device_id[:8]}",
            os="unknown",
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
    return device


async def get_or_create_device_status(db: AsyncSession, device_id: str) -> DBDeviceStatus:
    """Get or create device status record."""
    result = await db.execute(
        select(DBDeviceStatus).where(DBDeviceStatus.device_id == device_id)
    )
    status = result.scalar_one_or_none()
    if not status:
        # Ensure device exists first
        await get_or_create_device(db, device_id)
        status = DBDeviceStatus(
            device_id=device_id,
            connected=False,
            status="idle",
        )
        db.add(status)
        await db.commit()
        await db.refresh(status)
    return status


async def update_device_status(
    db: AsyncSession,
    device_id: str,
    connected: bool | None = None,
    status: str | None = None,
    status_data: dict[str, Any] | None = None,
) -> DBDeviceStatus:
    """Update device status in database."""
    device_status = await get_or_create_device_status(db, device_id)

    now = utc_now()
    if connected is not None:
        device_status.connected = connected
    if status is not None:
        device_status.status = status
    if status_data is not None:
        device_status.status_data = status_data
    device_status.last_seen_at = now
    device_status.last_sync_at = now
    device_status.updated_at = now

    await db.commit()
    await db.refresh(device_status)
    return device_status


async def save_command_result_to_db(
    db: AsyncSession,
    command_id: str,
    device_id: str,
    command_type: str,
    command_params: dict[str, Any] | None,
    success: bool,
    result_data: dict[str, Any] | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
) -> DBCommandResult:
    """Save command result to database."""
    # Check if command already exists
    result = await db.execute(
        select(DBCommandResult).where(DBCommandResult.id == command_id)
    )
    cmd_result = result.scalar_one_or_none()

    now = utc_now()
    if cmd_result:
        # Update existing
        cmd_result.success = success
        cmd_result.result_data = result_data
        cmd_result.error = error
        cmd_result.duration_ms = duration_ms
        cmd_result.status = "completed" if success else "failed"
        cmd_result.completed_at = now
    else:
        # Create new
        cmd_result = DBCommandResult(
            id=command_id,
            device_id=device_id,
            command_type=command_type,
            command_params=command_params,
            success=success,
            result_data=result_data,
            error=error,
            duration_ms=duration_ms,
            status="completed" if success else "failed",
            completed_at=now,
        )
        db.add(cmd_result)

    await db.commit()
    await db.refresh(cmd_result)
    return cmd_result


async def save_screenshot_to_db(
    db: AsyncSession,
    device_id: str,
    screenshot_data: str,
    command_id: str | None = None,
    ocr_text: str | None = None,
) -> DBScreenshot:
    """Save screenshot to database."""
    screenshot = DBScreenshot(
        device_id=device_id,
        command_id=command_id,
        screenshot_data=screenshot_data,
        ocr_text=ocr_text,
    )
    db.add(screenshot)
    await db.commit()
    await db.refresh(screenshot)
    return screenshot


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


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


class CommandResult(BaseModel):  # type: ignore[no-redef]
    """Command result schema."""

    success: bool = Field(..., description="Whether command succeeded")
    result: Any = Field(default=None, description="Command result data")
    error: str | None = Field(default=None, description="Error message if failed")
    screenshot_url: str | None = Field(default=None, description="Screenshot URL if captured")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")


class DeviceStatus(BaseModel):  # type: ignore[no-redef]
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


# WebSocket endpoint - registered directly on app in main.py for clean URL
async def automation_websocket(
    websocket: WebSocket,
    device_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
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

    # Update device status in database
    device_status = await update_device_status(
        db, device_id, connected=True, status="idle"
    )

    logger.info(
        "Device connected to automation WebSocket",
        extra={"device_id": device_id, "total_devices": len(connected_devices)},
    )

    # Broadcast device connection to web clients
    await broadcast_device_update(device_id, {
        "connected": True,
        "last_seen_at": device_status.last_seen_at,
        "status": device_status.status,
    })

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "status_update":
                # Update device status in database
                status_data = data.get("data", {})
                device_status = await update_device_status(
                    db,
                    device_id,
                    status=data.get("status", "idle"),
                    status_data=status_data,
                )
                logger.debug(
                    "Device status updated",
                    extra={"device_id": device_id, "status": data.get("status")},
                )
                # Broadcast status update to web clients
                await broadcast_device_update(device_id, {
                    "connected": device_status.connected,
                    "last_seen_at": device_status.last_seen_at,
                    "status": device_status.status,
                    **(device_status.status_data or {}),
                })

            elif message_type == "command_result":
                # Store command result in database
                command_id = data.get("command_id")
                if command_id:
                    result_data = data.get("result", {})
                    success = data.get("success", False)

                    # Save to database
                    await save_command_result_to_db(
                        db,
                        command_id=command_id,
                        device_id=device_id,
                        command_type="unknown",  # Will be updated from pending
                        command_params=None,
                        success=success,
                        result_data=result_data,
                        error=data.get("error"),
                        duration_ms=data.get("duration_ms"),
                    )

                    # Store screenshot if present
                    if isinstance(result_data, dict) and result_data.get("screenshot"):
                        await save_screenshot_to_db(
                            db,
                            device_id=device_id,
                            screenshot_data=result_data["screenshot"],
                            command_id=command_id,
                        )

                    logger.info(
                        "Command result received and persisted",
                        extra={
                            "device_id": device_id,
                            "command_id": command_id,
                            "success": success,
                        },
                    )

                    # Broadcast command result to web clients
                    await broadcast_command_result(command_id, device_id, {
                        "success": success,
                        "result": result_data,
                        "error": data.get("error"),
                        "duration_ms": data.get("duration_ms"),
                        "completed_at": utc_now(),
                    })

            elif message_type == "task_result":
                # Store task result from desktop
                result_data = data.get("result", {})
                task_id = result_data.get("task_id")
                if task_id:
                    output_data = result_data.get("output")
                    success = result_data.get("success", False)

                    # Save to database
                    await save_command_result_to_db(
                        db,
                        command_id=task_id,
                        device_id=device_id,
                        command_type="task",
                        command_params=None,
                        success=success,
                        result_data=output_data if isinstance(output_data, dict) else {"output": output_data},
                        error=result_data.get("error"),
                        duration_ms=result_data.get("duration_ms"),
                    )

                    # Store screenshot if present
                    if isinstance(output_data, dict) and output_data.get("screenshot"):
                        await save_screenshot_to_db(
                            db,
                            device_id=device_id,
                            screenshot_data=output_data["screenshot"],
                            command_id=task_id,
                        )

                    logger.info(
                        "Task result received and persisted",
                        extra={
                            "device_id": device_id,
                            "task_id": task_id,
                            "success": success,
                        },
                    )

                    # Broadcast task result to web clients
                    await broadcast_command_result(task_id, device_id, {
                        "success": success,
                        "result": output_data,
                        "error": result_data.get("error"),
                        "duration_ms": result_data.get("duration_ms"),
                        "completed_at": utc_now(),
                    })

            elif message_type == "ping":
                # Respond to ping and update last_seen
                import time
                await websocket.send_json({"type": "pong", "timestamp": int(time.time())})
                await update_device_status(db, device_id)

    except WebSocketDisconnect:
        connected_devices.pop(device_id, None)
        await update_device_status(db, device_id, connected=False)
        # Broadcast device disconnection
        await broadcast_device_update(device_id, {"connected": False})
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
        try:
            await update_device_status(db, device_id, connected=False)
            await broadcast_device_update(device_id, {"connected": False})
        except Exception as cleanup_err:
            logger.warning(
                "Failed to update device status during error cleanup",
                extra={"device_id": device_id, "error": str(cleanup_err)},
            )


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

    # Store pending command in database
    cmd_result = DBCommandResult(
        id=command_id,
        device_id=device_id,
        command_type=command.command_type,
        command_params=command.params,
        status="pending",
    )
    db.add(cmd_result)
    await db.commit()

    # Send command to device as AutomationTask format
    try:
        websocket = connected_devices.get(device_id)
        if websocket is None:
            # Device disconnected between initial check and websocket access
            raise HTTPException(
                status_code=404,
                detail=f"Device {device_id} disconnected",
            )

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
            "created_at": start_time,
        }

    except Exception as e:
        # Update command status to failed
        cmd_result.status = "failed"
        cmd_result.error = str(e)
        await db.commit()

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
        ) from e


@router.get("/result/{command_id}")
async def get_command_result(
    command_id: str,
    timeout: int = Query(default=30, ge=1, le=300, description="Timeout in seconds"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get command result with timeout."""
    # Wait for result with timeout
    start_time = utc_now()
    while (utc_now() - start_time).total_seconds() < timeout:
        # Query from database
        result = await db.execute(
            select(DBCommandResult).where(DBCommandResult.id == command_id)
        )
        cmd_result = result.scalar_one_or_none()

        if cmd_result and cmd_result.status in ("completed", "failed"):
            return {
                "success": cmd_result.success or False,
                "result": cmd_result.result_data,
                "error": cmd_result.error,
                "duration_ms": cmd_result.duration_ms,
            }

        await asyncio.sleep(0.5)
        await db.refresh(cmd_result) if cmd_result else None

    # Timeout - update command status
    result = await db.execute(
        select(DBCommandResult).where(DBCommandResult.id == command_id)
    )
    cmd_result = result.scalar_one_or_none()
    if cmd_result:
        cmd_result.status = "timeout"
        await db.commit()

    raise HTTPException(
        status_code=408,
        detail="Command execution timeout",
    )


@router.get("/status/{device_id}")
async def get_device_status(
    device_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get device status from database."""
    result = await db.execute(
        select(DBDeviceStatus).where(DBDeviceStatus.device_id == device_id)
    )
    status = result.scalar_one_or_none()

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    # Check if actually connected via WebSocket
    is_connected = device_id in connected_devices

    return {
        "device_id": device_id,
        "connected": is_connected,
        "last_seen_at": status.last_seen_at,
        "status_data": {
            "status": status.status,
            **(status.status_data or {}),
        },
    }


@router.get("/devices")
async def list_devices(
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List all devices from database."""
    result = await db.execute(
        select(DBDeviceStatus).order_by(desc(DBDeviceStatus.last_seen_at))
    )
    statuses = result.scalars().all()

    return [
        {
            "device_id": status.device_id,
            "connected": status.device_id in connected_devices,
            "last_seen_at": status.last_seen_at,
            "status_data": {
                "status": status.status,
                **(status.status_data or {}),
            },
        }
        for status in statuses
    ]


class SyncStatus(BaseModel):
    """Sync status schema."""

    last_sync_at: datetime | None = Field(default=None, description="Last sync timestamp")
    events_since_sync: int = Field(default=0, description="Number of events since last sync")
    sync_status: str = Field(..., description="Sync status (connected/disconnected)")


@router.get("/devices/{device_id}/sync-status", response_model=SyncStatus)
async def get_sync_status(
    device_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get device sync status from database."""
    # Get device status from DB
    result = await db.execute(
        select(DBDeviceStatus).where(DBDeviceStatus.device_id == device_id)
    )
    status = result.scalar_one_or_none()

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    # Count pending commands for this device
    pending_result = await db.execute(
        select(func.count(DBCommandResult.id))
        .where(DBCommandResult.device_id == device_id)
        .where(DBCommandResult.success.is_(None))  # Pending = no result yet
    )
    events_since_sync = pending_result.scalar() or 0

    return {
        "last_sync_at": status.last_seen_at,
        "events_since_sync": events_since_sync,
        "sync_status": "connected" if status.connected else "disconnected",
    }


class Screenshot(BaseModel):  # type: ignore[no-redef]
    """Screenshot schema."""

    screenshot: str = Field(..., description="Base64 encoded screenshot")
    timestamp: str = Field(..., description="Screenshot timestamp")
    command_id: str = Field(..., description="Associated command ID")


@router.get("/devices/{device_id}/screenshots")
async def get_screenshot_history(
    device_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get screenshot history for a device from database."""
    # Check device exists
    result = await db.execute(
        select(DBDeviceStatus).where(DBDeviceStatus.device_id == device_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )

    # Get screenshots from database
    screenshot_result = await db.execute(
        select(DBScreenshot)
        .where(DBScreenshot.device_id == device_id)
        .order_by(desc(DBScreenshot.captured_at))
        .limit(limit)
    )
    screenshots: list[DBScreenshot] = list(screenshot_result.scalars().all())

    return [
        {
            "screenshot": s.screenshot_data,
            "timestamp": s.captured_at.isoformat() + "Z",
            "command_id": s.command_id,
        }
        for s in screenshots
    ]


class CommandResultInput(BaseModel):
    """Input schema for command result (different from DB model)."""

    success: bool = Field(..., description="Whether command succeeded")
    result: Any = Field(default=None, description="Command result data")
    error: str | None = Field(default=None, description="Error message if failed")
    screenshot_url: str | None = Field(default=None, description="Screenshot URL if captured")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")


class DeviceStatusInput(BaseModel):
    """Input schema for device status."""

    connected: bool = Field(..., description="Whether device is connected")
    last_seen_at: datetime | None = Field(default=None, description="Last seen timestamp")
    status_data: dict[str, Any] = Field(default_factory=dict, description="Additional status data")


@router.post("/results")
async def save_command_result_endpoint(
    result: CommandResultInput,
    command_id: str = Query(..., description="Command ID"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Save command result from device (alternative to WebSocket)."""
    # Find device_id from existing command or create new
    existing = await db.execute(
        select(DBCommandResult).where(DBCommandResult.id == command_id)
    )
    cmd = existing.scalar_one_or_none()

    if cmd:
        # Update existing
        cmd.success = result.success
        cmd.result_data = {"result": result.result} if result.result else None
        cmd.error = result.error
        cmd.duration_ms = result.duration_ms
        cmd.status = "completed" if result.success else "failed"
        cmd.completed_at = utc_now()
    else:
        # Create new with unknown device
        cmd = DBCommandResult(
            id=command_id,
            device_id="unknown",
            command_type="unknown",
            success=result.success,
            result_data={"result": result.result} if result.result else None,
            error=result.error,
            duration_ms=result.duration_ms,
            status="completed" if result.success else "failed",
            completed_at=utc_now(),
        )
        db.add(cmd)

    await db.commit()

    logger.info(
        "Command result saved via REST",
        extra={"command_id": command_id, "success": result.success},
    )

    return {"message": "Result saved"}


@router.post("/status")
async def save_device_status_endpoint(
    status: DeviceStatusInput,
    device_id: str = Query(..., description="Device ID"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Save device status (alternative to WebSocket)."""
    await update_device_status(
        db,
        device_id,
        connected=status.connected,
        status_data=status.status_data,
    )

    logger.debug(
        "Device status saved via REST",
        extra={"device_id": device_id},
    )

    return {"message": "Status saved"}


@router.post("/task/{device_id}")
async def execute_task(
    device_id: str,
    task: TaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute compound task using AI to break down into steps."""
    import json as json_module

    from src.services.ai_router import AIRouter, TaskComplexity

    # Check if device is connected
    if device_id not in connected_devices:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not connected",
        )

    task_id = str(uuid4())
    websocket = connected_devices[device_id]

    logger.info(
        "Task execution requested",
        extra={
            "device_id": device_id,
            "task_id": task_id,
            "description": task.description,
        },
    )

    # Use AI router to break down task into automation commands
    try:
        ai_router = AIRouter()

        # Create prompt for task breakdown
        context_str = json_module.dumps(task.context) if task.context else "{}"
        prompt = f"""You are an automation assistant. Break down this task into specific automation commands.

Task: {task.description}

Context: {context_str}

Available commands:
- click: {{x, y, button}} - Click at coordinates
- type: {{text}} - Type text
- hotkey: {{modifiers, key}} - Press keyboard shortcut (modifiers: ctrl, alt, shift, meta)
- screenshot: {{save_path}} - Take screenshot
- navigate: {{browser, url}} - Navigate browser to URL
- wait: {{milliseconds}} - Wait for specified time

Return a JSON array of commands in order. Each command should have:
- command_type: one of the available commands
- params: the parameters for that command
- description: what this step does

Example response:
[
  {{"command_type": "navigate", "params": {{"browser": "chrome", "url": "https://example.com"}},
   "description": "Open example.com"}},
  {{"command_type": "wait", "params": {{"milliseconds": 2000}}, "description": "Wait for page to load"}},
  {{"command_type": "click", "params": {{"x": 500, "y": 300}}, "description": "Click on the button"}}
]

Return ONLY the JSON array, no other text."""

        result = await ai_router.query(
            prompt=prompt,
            complexity=TaskComplexity.MEDIUM,
            max_tokens=2048,
            use_cache=False,  # Each task is unique
        )

        # Parse AI response
        response_text = result.get("response", "[]")

        # Try to extract JSON from response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            commands = json_module.loads(response_text.strip())
        except json_module.JSONDecodeError:
            logger.warning(
                "Failed to parse AI response as JSON, using single command",
                extra={"response": response_text[:200]},
            )
            # Fallback: treat the whole task as a single custom command
            commands = [{
                "command_type": "custom",
                "params": {"description": task.description},
                "description": task.description,
            }]

        # Store parent task
        parent_cmd = DBCommandResult(
            id=task_id,
            device_id=device_id,
            command_type="compound_task",
            command_params={"description": task.description, "steps": len(commands)},
            status="executing",
        )
        db.add(parent_cmd)
        await db.commit()

        # Execute each command in sequence
        executed_commands = []
        for i, cmd in enumerate(commands):
            cmd_id = f"{task_id}-step-{i+1}"
            cmd_type = cmd.get("command_type", "custom")
            cmd_params = cmd.get("params", {})

            # Store command
            step_cmd = DBCommandResult(
                id=cmd_id,
                device_id=device_id,
                command_type=cmd_type,
                command_params=cmd_params,
                status="pending",
            )
            db.add(step_cmd)
            await db.commit()

            # Translate and send to device
            translated_task = translate_command_to_task(cmd_id, cmd_type, cmd_params)

            await websocket.send_json({
                "type": "automation_task",
                "task": translated_task,
            })

            executed_commands.append({
                "command_id": cmd_id,
                "command_type": cmd_type,
                "description": cmd.get("description", ""),
            })

            logger.info(
                f"Task step {i+1}/{len(commands)} sent",
                extra={
                    "task_id": task_id,
                    "command_id": cmd_id,
                    "command_type": cmd_type,
                },
            )

        # Log to audit trail
        await create_audit_log(
            db=db,
            action_type="task_executed",
            actor="user",
            result="pending",
            device_id=device_id,
            command_type="compound_task",
            command_params={"description": task.description, "steps": len(commands)},
            ip_address=request.client.host if request.client else None,
        )

        return {
            "task_id": task_id,
            "status": "executing",
            "steps": len(commands),
            "commands": executed_commands,
            "ai_model": result.get("model"),
            "ai_cost": result.get("cost"),
        }

    except Exception as e:
        log_error(
            logger,
            "Failed to execute task with AI router",
            error=e,
            extra={"device_id": device_id, "task_id": task_id},
        )

        # Fallback: send task description as a single custom command
        fallback_cmd = DBCommandResult(
            id=task_id,
            device_id=device_id,
            command_type="custom",
            command_params={"description": task.description},
            status="pending",
        )
        db.add(fallback_cmd)
        await db.commit()

        return {
            "task_id": task_id,
            "status": "pending",
            "message": f"AI breakdown failed ({str(e)}), sent as custom task",
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
