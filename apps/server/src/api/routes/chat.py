"""Chat endpoints with PostgreSQL storage and Redis caching."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.claude import claude_client
from src.core.config import settings
from src.db.models import ChatMessage
from src.services.analyzer import AnalyzerService

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis client for caching
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get Redis client, create if needed."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_client.ping()
        except Exception:
            redis_client = None
    return redis_client


class ChatMessageInput(BaseModel):
    """Chat message input schema."""

    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Chat response schema."""

    id: str
    message: str
    response: str
    timestamp: datetime


class ChatMessageOutput(BaseModel):
    """Chat message output schema."""

    id: str
    role: str
    content: str
    timestamp: str


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatMessageInput,
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Chat with Observer AI."""
    message_id = str(uuid4())
    session_id = data.context.get("session_id", "default")
    # Use naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE column
    timestamp = datetime.utcnow()

    # Get context from recent activity
    analyzer = AnalyzerService(db)
    activity_context = await analyzer.get_summary()

    # Build system prompt with context
    system_prompt = (
        "You are Observer, a personal AI assistant that helps users "
        "understand their work patterns and suggests automations.\n\n"
        f"Current activity context:\n"
        f"- Total events today: {activity_context.get('total_events', 0)}\n"
        f"- Top apps: {', '.join([app[0] for app in activity_context.get('top_apps', [])[:5]])}\n"
        f"- Categories: {activity_context.get('categories', {})}\n\n"
        "Be helpful, concise, and proactive in suggesting improvements. "
        "Respond in Russian. When appropriate, suggest creating automation agents."
    )

    # Load conversation history from database
    history_query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(20)  # Last 20 messages for context
    )
    history_result = await db.execute(history_query)
    history_messages = history_result.scalars().all()

    # Build messages array with history + new message
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]
    messages.append({"role": "user", "content": data.message})

    # Get response from Claude with full conversation history
    try:
        response = await claude_client.complete(
            messages=messages,
            system=system_prompt,
        )
    except Exception as e:
        response = f"Извините, произошла ошибка при подключении к AI. Ошибка: {str(e)}"

    # Store user message in database
    user_msg = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        role="user",
        content=data.message,
        timestamp=timestamp,
    )
    db.add(user_msg)

    # Store assistant message in database with slight offset for proper ordering
    assistant_timestamp = timestamp + timedelta(milliseconds=100)
    assistant_msg = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        role="assistant",
        content=response,
        timestamp=assistant_timestamp,
    )
    db.add(assistant_msg)

    try:
        await db.commit()
        logger.info(f"Chat messages saved for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to save chat messages: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save chat messages")

    # Invalidate cache for this session
    r = await get_redis()
    if r:
        try:
            await r.delete(f"chat_history:{session_id}")
        except Exception:
            pass

    return ChatResponse(
        id=message_id,
        message=data.message,
        response=response,
        timestamp=timestamp,
    )


@router.get("/history")
async def get_chat_history(
    session_id: str = "default",
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageOutput]:
    """Get chat history from database with Redis caching."""
    cache_key = f"chat_history:{session_id}"

    # Try to get from Redis cache first
    r = await get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Get from database
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    # Convert to output format (reverse to get chronological order)
    history = [
        ChatMessageOutput(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat(),
        )
        for msg in reversed(messages)
    ]

    # Cache in Redis for 5 minutes
    if r and history:
        try:
            await r.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps([h.model_dump() for h in history]),
            )
        except Exception:
            pass

    return history


@router.delete("/history")
async def clear_chat_history(
    session_id: str = "default",
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Clear chat history from database."""
    from sqlalchemy import delete

    # Delete from database
    stmt = delete(ChatMessage).where(ChatMessage.session_id == session_id)
    await db.execute(stmt)
    await db.commit()

    # Clear cache
    r = await get_redis()
    if r:
        try:
            await r.delete(f"chat_history:{session_id}")
        except Exception:
            pass

    return {"message": "Chat history cleared"}
