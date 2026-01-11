"""Agent Tasks endpoints for task queue management."""

import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.db.models import AgentTask

router = APIRouter()


class Priority(str, Enum):
    """Task priority levels."""

    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, Enum):
    """Task status values."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class CreateTaskRequest(BaseModel):
    """Request schema for creating a task."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Task description",
    )
    project_path: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional project path for the task",
    )
    priority: Priority = Field(
        default=Priority.normal,
        description="Task priority level",
    )


class UpdateTaskRequest(BaseModel):
    """Request schema for updating a task."""

    status: TaskStatus | None = Field(
        default=None,
        description="New task status",
    )
    result: str | None = Field(
        default=None,
        max_length=50000,
        description="Task result",
    )
    error: str | None = Field(
        default=None,
        max_length=10000,
        description="Error message if task failed",
    )


class AgentTaskResponse(BaseModel):
    """Response schema for agent task."""

    id: uuid.UUID
    description: str
    project_path: str | None
    priority: Priority
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: str | None
    error: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[AgentTaskResponse])
async def get_tasks(
    status: TaskStatus | None = Query(
        default=None,
        description="Filter by task status",
    ),
    priority: Priority | None = Query(
        default=None,
        description="Filter by priority",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of tasks to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of tasks to skip",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentTask]:
    """Get all tasks with optional filtering."""
    query = select(AgentTask)

    if status:
        query = query.where(AgentTask.status == status.value)
    if priority:
        query = query.where(AgentTask.priority == priority.value)

    query = query.order_by(AgentTask.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=AgentTaskResponse, status_code=201)
async def create_task(
    data: CreateTaskRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AgentTask:
    """Create a new task."""
    task = AgentTask(
        description=data.description,
        project_path=data.project_path,
        priority=data.priority.value,
        status=TaskStatus.pending.value,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AgentTask:
    """Get a specific task by ID."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=AgentTaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: UpdateTaskRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AgentTask:
    """Update a task's status, result, or error."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"]:
        new_status = update_data["status"]
        task.status = new_status.value if isinstance(new_status, TaskStatus) else new_status

        # Automatically set started_at when status changes to in_progress
        if task.status == TaskStatus.in_progress.value and not task.started_at:
            task.started_at = datetime.now(UTC).replace(tzinfo=None)

        # Automatically set completed_at when status changes to terminal state
        if task.status in (
            TaskStatus.completed.value,
            TaskStatus.failed.value,
            TaskStatus.cancelled.value,
        ) and not task.completed_at:
            task.completed_at = datetime.now(UTC).replace(tzinfo=None)

    if "result" in update_data:
        task.result = update_data["result"]

    if "error" in update_data:
        task.error = update_data["error"]

    await db.flush()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete a task."""
    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.flush()
    return {"message": "Task deleted"}
